"""
Eval Tasks — Celery task definitions.
Imports celery_app from celery_app.py to avoid circular imports.
"""
import asyncio
from celery_app import celery_app


@celery_app.task(name="tasks.run_eval", bind=True, max_retries=3)
def run_eval_task(self, run_id: str):
    """Entry point called by Celery — bridges sync Celery to async eval pipeline."""
    try:
        asyncio.run(_run_eval_async(run_id))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)


async def _run_eval_async(run_id: str):
    """Full async eval pipeline — runs inside a fresh event loop per task."""
    from uuid import UUID
    from sqlalchemy import select
    from app.db import AsyncSessionLocal
    from app.models.orm import EvalRun, ModelEndpoint, DatasetRow, EvalResult
    from app.services.llm_client import call_llm
    from app.services.eval_engine.factual import check_factual_accuracy
    from app.services.eval_engine.hallucination import detect_hallucination

    async with AsyncSessionLocal() as db:
        run = await db.get(EvalRun, UUID(run_id))
        if not run:
            print(f"❌ EvalRun {run_id} not found")
            return

        run.status = "running"
        await db.commit()

        try:
            endpoint = await db.get(ModelEndpoint, run.model_endpoint_id)
            if not endpoint:
                raise ValueError(f"Model endpoint {run.model_endpoint_id} not found")

            rows_result = await db.execute(
                select(DatasetRow)
                .where(DatasetRow.dataset_id == run.dataset_id)
                .order_by(DatasetRow.row_index)
            )
            rows = rows_result.scalars().all()

            if not rows:
                raise ValueError("Dataset has 0 rows — please upload CSV first")

            run.total_rows = len(rows)
            await db.commit()

            eval_types = run.eval_types or ["factual"]
            all_scores = []

            for i, row in enumerate(rows):
                try:
                    llm_response = await call_llm(row.input_prompt, endpoint)

                    result = EvalResult(
                        eval_run_id=run.id,
                        dataset_row_id=row.id,
                        actual_output=llm_response.content,
                        latency_ms=llm_response.latency_ms,
                        tokens_used=llm_response.tokens_used,
                        error=llm_response.error,
                    )

                    row_score = 0.0
                    score_count = 0

                    if "factual" in eval_types and not llm_response.error:
                        factual = await check_factual_accuracy(
                            question=row.input_prompt,
                            actual_output=llm_response.content,
                            endpoint=endpoint,
                            expected_output=row.expected_output,
                        )
                        result.factual_score = factual.factual_score
                        result.judge_verdict = factual.verdict
                        result.judge_reasoning = factual.judge_reasoning
                        row_score += factual.factual_score * 100
                        score_count += 1

                    if "hallucination" in eval_types and not llm_response.error:
                        hall = await detect_hallucination(row, llm_response, endpoint)
                        result.hallucination_detected = hall.hallucination_detected
                        result.hallucination_confidence = hall.confidence
                        result.hallucination_reason = hall.reason
                        result.similarity_score = hall.consistency_score

                    db.add(result)
                    run.completed_rows = i + 1

                    if score_count > 0:
                        all_scores.append(row_score / score_count)

                    await db.commit()
                    print(f"✅ Row {i+1}/{len(rows)} completed")

                except Exception as row_err:
                    print(f"⚠️ Row {i+1} error: {row_err}")
                    result = EvalResult(
                        eval_run_id=run.id,
                        dataset_row_id=row.id,
                        actual_output="",
                        error=str(row_err),
                    )
                    db.add(result)
                    run.completed_rows = i + 1
                    await db.commit()

            run.overall_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
            run.status = "completed"
            await db.commit()
            print(f"🎉 EvalRun {run_id} completed! Score: {run.overall_score:.1f}")

        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)
            await db.commit()
            print(f"❌ EvalRun {run_id} failed: {e}")
            raise
