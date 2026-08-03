"""
Eval Tasks — dispatches to whichever eval engines were requested.

IMPORTANT: previously this only ever ran the "factual" engine, no matter what
eval_types were selected — jailbreak and hallucination were implemented but
never wired in. Jailbreak in particular needs no dataset (it runs a fixed
probe list against the endpoint directly), which is why red-team runs
(dataset_id=null) used to fail immediately with "Dataset has 0 rows".
"""
import asyncio
from celery_app import celery_app


@celery_app.task(name="tasks.run_eval", bind=True, max_retries=3)
def run_eval_task(self, run_id: str):
    try:
        asyncio.run(_run_eval_async(run_id))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)


async def _run_eval_async(run_id: str):
    from uuid import UUID
    from sqlalchemy import select
    from app.db import AsyncSessionLocal
    from app.models.orm import EvalRun, ModelEndpoint, DatasetRow, EvalResult
    from app.services.llm_client import call_llm
    from app.services.eval_engine.factual import check_factual_accuracy
    from app.services.eval_engine.hallucination import detect_hallucination
    from app.services.eval_engine.jailbreak import run_jailbreak_eval

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
                raise ValueError("Model endpoint not found")

            print(f"🔧 Using model: {endpoint.model_name} at {endpoint.base_url}")

            eval_types = run.eval_types or ["factual"]
            print(f"🎯 Eval types: {eval_types}")

            row_driven_scores: list[float] = []   # combined factual+hallucination per-row score
            factual_scores: list[float] = []
            hallucination_flags: list[bool] = []

            # ── Jailbreak red-team run — no dataset needed ─────────────────────
            if "jailbreak" in eval_types:
                print("🛡️  Running jailbreak probes...")
                jb_result = await run_jailbreak_eval(endpoint, probe_ids=run.probe_ids)

                for probe_result in jb_result.probe_results:
                    db.add(EvalResult(
                        eval_run_id=run.id,
                        dataset_row_id=None,
                        actual_output=probe_result.response or "",
                        jailbreak_succeeded=probe_result.jailbreak_succeeded,
                        jailbreak_category=probe_result.category,
                        jailbreak_probe_id=probe_result.probe_id,
                        language=probe_result.language,
                        judge_verdict=probe_result.compliance_type,
                        judge_reasoning=probe_result.reasoning,
                    ))

                run.jailbreak_resistance_score = jb_result.resistance_score
                run.total_rows = jb_result.total_probes
                run.completed_rows = jb_result.total_probes
                await db.commit()
                print(f"🛡️  Jailbreak resistance score: {jb_result.resistance_score}")

            # ── Row-driven evals: factual / hallucination ──────────────────────
            row_eval_types = [t for t in eval_types if t != "jailbreak"]
            if row_eval_types:
                if not run.dataset_id:
                    raise ValueError("dataset_id is required for factual/hallucination evals")

                rows_result = await db.execute(
                    select(DatasetRow)
                    .where(DatasetRow.dataset_id == run.dataset_id)
                    .order_by(DatasetRow.created_at)
                )
                rows = rows_result.scalars().all()
                print(f"📊 Found {len(rows)} rows in dataset")

                if not rows:
                    raise ValueError("Dataset has 0 rows")

                run.total_rows = len(rows)
                await db.commit()

                for i, row in enumerate(rows):
                    try:
                        print(f"▶ Row {i+1}: prompt='{row.input_prompt[:50]}...'")

                        llm_response = await call_llm(row.input_prompt, endpoint)

                        print(f"  LLM response: content='{llm_response.content[:100] if llm_response.content else 'EMPTY'}' error={llm_response.error} latency={llm_response.latency_ms}ms")

                        result = EvalResult(
                            eval_run_id=run.id,
                            dataset_row_id=row.id,
                            actual_output=llm_response.content or "",
                            latency_ms=llm_response.latency_ms,
                            tokens_used=llm_response.tokens_used,
                            error=llm_response.error,
                        )

                        row_score = 0.0
                        score_count = 0

                        if "factual" in row_eval_types and not llm_response.error and llm_response.content:
                            print(f"  Running factual check...")
                            try:
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
                                factual_scores.append(factual.factual_score * 100)
                                print(f"  Factual score: {factual.factual_score} verdict: {factual.verdict}")
                            except Exception as fe:
                                print(f"  ⚠️ Factual check error: {fe}")

                        if "hallucination" in row_eval_types and not llm_response.error and llm_response.content:
                            print(f"  Running hallucination check...")
                            try:
                                halluc = await detect_hallucination(
                                    row=row,
                                    primary_response=llm_response,
                                    endpoint=endpoint,
                                )
                                result.hallucination_detected = halluc.hallucination_detected
                                result.hallucination_confidence = halluc.confidence
                                result.hallucination_reason = halluc.reason
                                halluc_row_score = 0.0 if halluc.hallucination_detected else 100.0
                                row_score += halluc_row_score
                                score_count += 1
                                hallucination_flags.append(halluc.hallucination_detected)
                                print(f"  Hallucination detected: {halluc.hallucination_detected} confidence: {halluc.confidence}")
                            except Exception as he:
                                print(f"  ⚠️ Hallucination check error: {he}")

                        db.add(result)
                        run.completed_rows = i + 1

                        if score_count > 0:
                            row_driven_scores.append(row_score / score_count)

                        await db.commit()
                        print(f"✅ Row {i+1}/{len(rows)} saved")

                    except Exception as row_err:
                        print(f"⚠️ Row {i+1} error: {row_err}")
                        import traceback
                        traceback.print_exc()
                        result = EvalResult(
                            eval_run_id=run.id,
                            dataset_row_id=row.id,
                            actual_output="",
                            error=str(row_err),
                        )
                        db.add(result)
                        run.completed_rows = i + 1
                        await db.commit()

                if factual_scores:
                    run.factual_accuracy_score = round(sum(factual_scores) / len(factual_scores), 1)
                if hallucination_flags:
                    clean_rate = 1 - (sum(hallucination_flags) / len(hallucination_flags))
                    run.hallucination_score = round(clean_rate * 100, 1)

            # ── Overall score: average of whichever engines actually ran ───────
            component_scores = [
                s for s in (
                    run.factual_accuracy_score,
                    run.hallucination_score,
                    run.jailbreak_resistance_score,
                ) if s is not None
            ]
            run.overall_score = round(sum(component_scores) / len(component_scores), 1) if component_scores else 0.0
            run.status = "completed"
            await db.commit()
            print(f"🎉 EvalRun completed! Overall score: {run.overall_score:.1f}")

        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)
            await db.commit()
            print(f"❌ EvalRun failed: {e}")
            import traceback
            traceback.print_exc()
            raise
