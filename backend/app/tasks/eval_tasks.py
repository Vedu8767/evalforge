"""
Eval Tasks with debug logging to diagnose empty output issue.
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
                raise ValueError(f"Model endpoint not found")

            print(f"🔧 Using model: {endpoint.model_name} at {endpoint.base_url}")

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

            eval_types = run.eval_types or ["factual"]
            print(f"🎯 Eval types: {eval_types}")
            all_scores = []

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

                    if "factual" in eval_types and not llm_response.error and llm_response.content:
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
                            print(f"  Factual score: {factual.factual_score} verdict: {factual.verdict}")
                        except Exception as fe:
                            print(f"  ⚠️ Factual check error: {fe}")

                    db.add(result)
                    run.completed_rows = i + 1

                    if score_count > 0:
                        all_scores.append(row_score / score_count)

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

            run.overall_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
            run.factual_accuracy_score = run.overall_score
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
