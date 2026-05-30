import asyncio
import json
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db import get_db
from app.models.orm import EvalRun, EvalResult, Dataset, ModelEndpoint
from app.schemas.schemas import EvalRunCreate, EvalRunOut, EvalResultOut
from app.routers.auth import get_current_user, get_current_workspace_id
from app.tasks.eval_tasks import run_eval_task

router = APIRouter(prefix="/eval-runs", tags=["eval-runs"])


@router.post("", response_model=EvalRunOut, status_code=201)
async def create_eval_run(
    data: EvalRunCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
):
    # Validate dataset belongs to workspace
    dataset = await db.get(Dataset, data.dataset_id)
    if not dataset or str(dataset.workspace_id) != workspace_id:
        raise HTTPException(404, "Dataset not found")

    endpoint = await db.get(ModelEndpoint, data.model_endpoint_id)
    if not endpoint or str(endpoint.workspace_id) != workspace_id:
        raise HTTPException(404, "Model endpoint not found")

    run = EvalRun(
        workspace_id=UUID(workspace_id),
        dataset_id=data.dataset_id,
        model_endpoint_id=data.model_endpoint_id,
        triggered_by=user.id,
        eval_types=data.eval_types,
        concurrency=data.concurrency,
        baseline_id=data.baseline_id,
        status="queued",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    # Enqueue Celery task
    task = run_eval_task.delay(str(run.id))
    run.celery_task_id = task.id
    await db.commit()
    await db.refresh(run)

    return run


@router.get("", response_model=list[EvalRunOut])
async def list_eval_runs(
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(get_current_workspace_id),
    status: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    q = select(EvalRun).where(EvalRun.workspace_id == UUID(workspace_id))
    if status:
        q = q.where(EvalRun.status == status)
    q = q.order_by(EvalRun.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{run_id}", response_model=EvalRunOut)
async def get_eval_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(get_current_workspace_id),
):
    run = await db.get(EvalRun, run_id)
    if not run or str(run.workspace_id) != workspace_id:
        raise HTTPException(404, "Eval run not found")
    return run


@router.get("/{run_id}/results", response_model=list[EvalResultOut])
async def get_eval_results(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(get_current_workspace_id),
    verdict: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    # Verify run ownership
    run = await db.get(EvalRun, run_id)
    if not run or str(run.workspace_id) != workspace_id:
        raise HTTPException(404, "Not found")

    q = select(EvalResult).where(EvalResult.eval_run_id == run_id)
    if verdict:
        q = q.where(EvalResult.judge_verdict == verdict)
    q = q.order_by(EvalResult.created_at.asc()).limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{run_id}/stream")
async def stream_eval_results(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(get_current_workspace_id),
):
    """SSE endpoint — streams new results as they are written by the Celery worker."""
    run = await db.get(EvalRun, run_id)
    if not run or str(run.workspace_id) != workspace_id:
        raise HTTPException(404, "Not found")

    async def event_generator():
        seen_ids = set()
        poll_interval = 1.5  # seconds between polls

        while True:
            async with db.begin():
                # Get new results since last poll
                q = select(EvalResult).where(
                    EvalResult.eval_run_id == run_id,
                    ~EvalResult.id.in_(seen_ids) if seen_ids else True,
                ).order_by(EvalResult.created_at.asc()).limit(20)
                result = await db.execute(q)
                new_results = result.scalars().all()

                for r in new_results:
                    seen_ids.add(r.id)
                    data = {
                        "id": str(r.id),
                        "row_id": str(r.dataset_row_id),
                        "output": r.actual_output[:200],
                        "hallucination": r.hallucination_detected,
                        "verdict": r.judge_verdict,
                        "factual_score": r.factual_score,
                        "latency_ms": r.latency_ms,
                    }
                    yield f"data: {json.dumps(data)}\n\n"

                # Check if run completed
                run_check = await db.get(EvalRun, run_id)
                if run_check and run_check.status in ("completed", "failed", "cancelled"):
                    yield f"event: done\ndata: {json.dumps({'status': run_check.status})}\n\n"
                    break

            await asyncio.sleep(poll_interval)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.delete("/{run_id}", status_code=204)
async def cancel_eval_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(get_current_workspace_id),
):
    run = await db.get(EvalRun, run_id)
    if not run or str(run.workspace_id) != workspace_id:
        raise HTTPException(404, "Not found")
    if run.status not in ("queued", "running"):
        raise HTTPException(400, "Can only cancel queued or running evals")
    if run.celery_task_id:
        from app.tasks.eval_tasks import celery_app
        celery_app.control.revoke(run.celery_task_id, terminate=True)
    run.status = "cancelled"
    await db.commit()
