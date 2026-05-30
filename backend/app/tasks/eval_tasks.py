"""
Celery Eval Task
─────────────────
Async worker that:
1. Loads the eval run config from DB
2. Fetches all dataset rows
3. For each row: calls LLM → runs eval checks → stores result
4. Computes aggregate scores → finalises run
5. Triggers alert rules if thresholds breached
"""
import asyncio
from datetime import datetime
from typing import Optional
from uuid import UUID

from celery import Celery
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

from app.config import settings
from app.db import AsyncSessionLocal
from app.models.orm import EvalRun, EvalResult, DatasetRow, ModelEndpoint, AlertRule
from app.services.llm_client import call_llm
from app.services.embeddings import embed_text, cosine_similarity
from app.services.eval_engine.hallucination import detect_hallucination
from app.services.eval_engine.jailbreak import run_jailbreak_eval
from app.services.eval_engine.factual import check_factual_accuracy

# ─── Celery App ───────────────────────────────────────────────────────────────

celery_app = Celery(
    "evalforge",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


# ─── Main Task ────────────────────────────────────────────────────────────────

@celery_app.task(bind=True, max_retries=2, name="tasks.run_eval")
def run_eval_task(self, eval_run_id: str):
    """Entry point — Celery is sync, so we run the async pipeline inside."""
    try:
        asyncio.run(_run_eval_async(eval_run_id))
    except Exception as exc:
        asyncio.run(_mark_run_failed(eval_run_id, str(exc)))
        raise self.retry(exc=exc, countdown=30)


# ─── Async Pipeline ───────────────────────────────────────────────────────────

async def _run_eval_async(eval_run_id: str):
    async with AsyncSessionLocal() as db:
        # Load run
        run = await db.get(EvalRun, UUID(eval_run_id))
        if not run:
            raise ValueError(f"EvalRun {eval_run_id} not found")

        endpoint = await db.get(ModelEndpoint, run.model_endpoint_id)
        if not endpoint:
            raise ValueError("ModelEndpoint not found")

        # Fetch dataset rows
        result = await db.execute(
            select(DatasetRow).where(DatasetRow.dataset_id == run.dataset_id)
        )
        rows = result.scalars().all()

        # Update run status
        run.status = "running"
        run.started_at = datetime.utcnow()
        run.total_rows = len(rows)
        run.completed_rows = 0
        await db.commit()

        # ── Handle jailbreak eval separately (runs against probe library) ──
        jailbreak_result = None
        if "jailbreak" in run.eval_types:
            jailbreak_result = await run_jailbreak_eval(endpoint)

        # ── Process each row with concurrency limit ─────────────────────
        semaphore = asyncio.Semaphore(run.concurrency or 5)

        async def process_row(row: DatasetRow):
            async with semaphore:
                await _process_single_row(db, run, row, endpoint, jailbreak_result)
                run.completed_rows += 1
                await db.commit()

        await asyncio.gather(*[process_row(row) for row in rows])

        # ── Compute aggregate scores ─────────────────────────────────────
        scores = await _compute_aggregate_scores(db, eval_run_id, jailbreak_result)
        run.hallucination_score = scores.get("hallucination_score")
        run.jailbreak_resistance_score = scores.get("jailbreak_resistance_score")
        run.factual_accuracy_score = scores.get("factual_accuracy_score")
        run.overall_score = scores.get("overall_score")
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        await db.commit()

        # ── Check alert rules ────────────────────────────────────────────
        await _check_alerts(db, run)


async def _process_single_row(db, run: EvalRun, row: DatasetRow, endpoint: ModelEndpoint, jailbreak_data):
    """Process one dataset row through the full eval pipeline."""
    result_data = {
        "eval_run_id": run.id,
        "dataset_row_id": row.id,
        "actual_output": "",
    }

    try:
        # 1. Call the target LLM
        llm_response = await call_llm(row.input_prompt, endpoint)

        if llm_response.error:
            result_data["error"] = llm_response.error
            db.add(EvalResult(**result_data))
            return

        result_data["actual_output"] = llm_response.content
        result_data["latency_ms"] = llm_response.latency_ms
        result_data["tokens_used"] = llm_response.tokens_used

        # 2. Embed the output for semantic similarity
        embedding = await embed_text(llm_response.content)
        result_data["output_embedding"] = embedding

        # 3. Hallucination check
        if "hallucination" in run.eval_types:
            h = await detect_hallucination(row, llm_response, endpoint)
            result_data["hallucination_detected"] = h.hallucination_detected
            result_data["hallucination_confidence"] = h.confidence
            result_data["hallucination_reason"] = h.reason

        # 4. Factual accuracy
        if "factual" in run.eval_types:
            f = await check_factual_accuracy(
                row.input_prompt,
                llm_response.content,
                row.expected_output,
            )
            result_data["factual_score"] = f.factual_score
            result_data["judge_verdict"] = f.verdict
            result_data["judge_reasoning"] = f.judge_reasoning

        # 5. Semantic similarity vs expected (if available)
        if row.expected_output:
            expected_emb = await embed_text(row.expected_output)
            result_data["similarity_score"] = cosine_similarity(embedding, expected_emb)

    except Exception as e:
        result_data["actual_output"] = result_data.get("actual_output", "")
        result_data["error"] = str(e)

    db.add(EvalResult(**result_data))


async def _compute_aggregate_scores(db, eval_run_id: str, jailbreak_data) -> dict:
    """Compute aggregate scores from individual results."""
    results_q = await db.execute(
        select(EvalResult).where(EvalResult.eval_run_id == UUID(eval_run_id))
    )
    results = results_q.scalars().all()

    scores = {}

    # Hallucination score: % of rows where NO hallucination detected
    hall_results = [r for r in results if r.hallucination_detected is not None]
    if hall_results:
        clean = sum(1 for r in hall_results if not r.hallucination_detected)
        scores["hallucination_score"] = round((clean / len(hall_results)) * 100, 1)

    # Factual accuracy: average factual_score * 100
    factual_results = [r for r in results if r.factual_score is not None]
    if factual_results:
        avg = sum(r.factual_score for r in factual_results) / len(factual_results)
        scores["factual_accuracy_score"] = round(avg * 100, 1)

    # Jailbreak resistance: from the separate jailbreak eval
    if jailbreak_data:
        scores["jailbreak_resistance_score"] = jailbreak_data.resistance_score

    # Overall score: weighted average of available scores
    available = [v for v in scores.values() if v is not None]
    if available:
        scores["overall_score"] = round(sum(available) / len(available), 1)

    return scores


async def _check_alerts(db, run: EvalRun):
    """Fire alert rules that are breached."""
    alert_q = await db.execute(
        select(AlertRule).where(
            AlertRule.workspace_id == run.workspace_id,
            AlertRule.enabled == True,
        )
    )
    alerts = alert_q.scalars().all()

    score_map = {
        "overall_score": run.overall_score,
        "hallucination_score": run.hallucination_score,
        "jailbreak_resistance_score": run.jailbreak_resistance_score,
        "factual_accuracy_score": run.factual_accuracy_score,
    }

    for alert in alerts:
        value = score_map.get(alert.metric)
        if value is None:
            continue
        breached = _evaluate_operator(value, alert.operator, alert.threshold)
        if breached:
            await _send_alert_notification(alert, run, value)


def _evaluate_operator(value: float, operator: str, threshold: float) -> bool:
    ops = {"lt": value < threshold, "gt": value > threshold,
           "lte": value <= threshold, "gte": value >= threshold}
    return ops.get(operator, False)


async def _send_alert_notification(alert: AlertRule, run: EvalRun, value: float):
    """Send email/Slack notification for a breached alert."""
    message = (
        f"🚨 EvalForge Alert: '{alert.name}'\n"
        f"Metric '{alert.metric}' = {value} "
        f"({alert.operator} {alert.threshold})\n"
        f"Eval Run ID: {run.id}"
    )
    # Slack webhook
    if alert.notify_slack_webhook:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(alert.notify_slack_webhook, json={"text": message})
        except Exception:
            pass
    # TODO: email via Resend


async def _mark_run_failed(eval_run_id: str, error: str):
    async with AsyncSessionLocal() as db:
        run = await db.get(EvalRun, UUID(eval_run_id))
        if run:
            run.status = "failed"
            run.error_message = error[:1000]
            run.completed_at = datetime.utcnow()
            await db.commit()
