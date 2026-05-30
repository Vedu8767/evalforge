from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_db
from app.models.orm import Baseline, AlertRule, EvalRun
from app.schemas.schemas import BaselineCreate, BaselineOut, AlertRuleCreate, AlertRuleOut
from app.routers.auth import get_current_user, get_current_workspace_id

# ─── Baselines ────────────────────────────────────────────────────────────────

baselines_router = APIRouter(prefix="/baselines", tags=["baselines"])


@baselines_router.get("", response_model=list[BaselineOut])
async def list_baselines(
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(get_current_workspace_id),
):
    result = await db.execute(
        select(Baseline)
        .where(Baseline.workspace_id == UUID(workspace_id))
        .order_by(Baseline.pinned_at.desc())
    )
    return result.scalars().all()


@baselines_router.post("", response_model=BaselineOut, status_code=201)
async def create_baseline(
    data: BaselineCreate,
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(get_current_workspace_id),
):
    # Verify eval run belongs to workspace and is completed
    run = await db.get(EvalRun, data.eval_run_id)
    if not run or str(run.workspace_id) != workspace_id:
        raise HTTPException(404, "Eval run not found")
    if run.status != "completed":
        raise HTTPException(400, "Can only pin completed eval runs as baselines")

    baseline = Baseline(
        workspace_id=UUID(workspace_id),
        dataset_id=run.dataset_id,
        model_endpoint_id=run.model_endpoint_id,
        eval_run_id=data.eval_run_id,
        name=data.name,
    )
    db.add(baseline)
    await db.commit()
    await db.refresh(baseline)
    return baseline


@baselines_router.delete("/{baseline_id}", status_code=204)
async def delete_baseline(
    baseline_id: UUID,
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(get_current_workspace_id),
):
    b = await db.get(Baseline, baseline_id)
    if not b or str(b.workspace_id) != workspace_id:
        raise HTTPException(404, "Not found")
    await db.delete(b)
    await db.commit()


# ─── Alert Rules ─────────────────────────────────────────────────────────────

alerts_router = APIRouter(prefix="/alerts", tags=["alerts"])

VALID_METRICS = {"overall_score", "hallucination_score", "jailbreak_resistance_score", "factual_accuracy_score"}
VALID_OPERATORS = {"lt", "gt", "lte", "gte"}


@alerts_router.get("", response_model=list[AlertRuleOut])
async def list_alerts(
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(get_current_workspace_id),
):
    result = await db.execute(
        select(AlertRule)
        .where(AlertRule.workspace_id == UUID(workspace_id))
        .order_by(AlertRule.created_at.desc())
    )
    return result.scalars().all()


@alerts_router.post("", response_model=AlertRuleOut, status_code=201)
async def create_alert(
    data: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(get_current_workspace_id),
):
    if data.metric not in VALID_METRICS:
        raise HTTPException(400, f"metric must be one of: {', '.join(VALID_METRICS)}")
    if data.operator not in VALID_OPERATORS:
        raise HTTPException(400, f"operator must be one of: {', '.join(VALID_OPERATORS)}")

    alert = AlertRule(
        workspace_id=UUID(workspace_id),
        name=data.name,
        metric=data.metric,
        operator=data.operator,
        threshold=data.threshold,
        notify_email=data.notify_email,
        notify_slack_webhook=data.notify_slack_webhook,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


@alerts_router.put("/{alert_id}", response_model=AlertRuleOut)
async def update_alert(
    alert_id: UUID,
    data: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(get_current_workspace_id),
):
    alert = await db.get(AlertRule, alert_id)
    if not alert or str(alert.workspace_id) != workspace_id:
        raise HTTPException(404, "Not found")
    for k, v in data.model_dump().items():
        setattr(alert, k, v)
    await db.commit()
    await db.refresh(alert)
    return alert


@alerts_router.delete("/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: UUID,
    db: AsyncSession = Depends(get_db),
    workspace_id: str = Depends(get_current_workspace_id),
):
    alert = await db.get(AlertRule, alert_id)
    if not alert or str(alert.workspace_id) != workspace_id:
        raise HTTPException(404, "Not found")
    await db.delete(alert)
    await db.commit()
