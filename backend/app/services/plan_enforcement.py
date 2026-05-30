"""
Plan Enforcement Service
─────────────────────────
Checks workspace plan limits before allowing actions.
Called by routers before creating eval runs, adding team members, etc.
"""
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException

from app.models.orm import Workspace, EvalRun, WorkspaceMember
from app.routers.billing import PLANS


class PlanLimitError(HTTPException):
    def __init__(self, message: str, upgrade_required: bool = True):
        super().__init__(
            status_code=402,  # Payment Required
            detail={
                "message": message,
                "upgrade_required": upgrade_required,
                "upgrade_url": "/settings?tab=billing",
            },
        )


async def check_eval_run_limit(db: AsyncSession, workspace: Workspace) -> None:
    """
    Check if workspace has eval runs remaining this month.
    Free plan: 50/month. Pro/Team: unlimited.
    """
    plan = PLANS.get(workspace.plan, PLANS["free"])
    limit = plan["eval_runs_per_month"]

    if limit == -1:
        return  # Unlimited

    # Count runs this calendar month
    start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(EvalRun.id)).where(
            EvalRun.workspace_id == workspace.id,
            EvalRun.created_at >= start_of_month,
        )
    )
    count = result.scalar() or 0

    if count >= limit:
        raise PlanLimitError(
            f"You've used {count}/{limit} eval runs this month. "
            f"Upgrade to Pro for unlimited eval runs."
        )


async def check_team_member_limit(db: AsyncSession, workspace: Workspace) -> None:
    """Check if workspace can add more team members."""
    plan = PLANS.get(workspace.plan, PLANS["free"])
    limit = plan["team_members"]

    if limit == -1:
        return

    result = await db.execute(
        select(func.count(WorkspaceMember.user_id)).where(
            WorkspaceMember.workspace_id == workspace.id,
        )
    )
    count = result.scalar() or 0

    if count >= limit:
        raise PlanLimitError(
            f"Your plan allows {limit} team member(s). "
            f"Upgrade to Team plan for up to 10 members."
        )


async def check_alert_rule_limit(db: AsyncSession, workspace: Workspace) -> None:
    """Check alert rule limit."""
    from app.models.orm import AlertRule

    plan = PLANS.get(workspace.plan, PLANS["free"])
    limit = plan["alert_rules"]

    if limit == -1:
        return
    if limit == 0:
        raise PlanLimitError(
            "Alert rules require a Pro or Team plan. Upgrade to get notified automatically."
        )

    result = await db.execute(
        select(func.count(AlertRule.id)).where(AlertRule.workspace_id == workspace.id)
    )
    count = result.scalar() or 0
    if count >= limit:
        raise PlanLimitError(f"Pro plan allows {limit} alert rules. Upgrade to Team for unlimited.")


def get_plan_features(workspace: Workspace) -> dict:
    """Return what the workspace is allowed to do."""
    plan = PLANS.get(workspace.plan, PLANS["free"])
    return {
        "plan": workspace.plan,
        "eval_runs_per_month": plan["eval_runs_per_month"],
        "team_members": plan["team_members"],
        "baselines": plan["baselines"],
        "alert_rules": plan["alert_rules"],
        "api_access": plan["api_access"],
        "jailbreak_probes": plan["jailbreak_probes"],
        "data_retention_days": plan["data_retention_days"],
    }
