"""
Stripe Billing Router
──────────────────────
Endpoints:
  POST /billing/checkout        → Create Stripe checkout session
  POST /billing/portal          → Customer billing portal link
  POST /billing/webhook         → Stripe webhook (subscription events)
  GET  /billing/plans           → Available plans + features
"""
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from typing import Optional

from app.db import get_db
from app.config import settings
from app.models.orm import User, Workspace, WorkspaceMember
from app.routers.auth import get_current_user, get_current_workspace_id

stripe.api_key = settings.stripe_secret_key

router = APIRouter(prefix="/billing", tags=["billing"])

# ─── Plan definitions ─────────────────────────────────────────────────────────

PLANS = {
    "free": {
        "name": "Free",
        "price_usd": 0,
        "price_inr": 0,
        "eval_runs_per_month": 50,
        "team_members": 1,
        "baselines": 1,
        "alert_rules": 0,
        "data_retention_days": 7,
        "api_access": False,
        "jailbreak_probes": 20,
        "features": [
            "50 eval runs / month",
            "1 team member",
            "1 baseline",
            "20 jailbreak probes",
            "7-day data retention",
        ],
    },
    "pro": {
        "name": "Pro",
        "price_usd": 29,
        "price_inr": 4999,
        "stripe_price_id": settings.stripe_pro_price_id,
        "eval_runs_per_month": -1,       # unlimited
        "team_members": 1,
        "baselines": -1,
        "alert_rules": 5,
        "data_retention_days": 90,
        "api_access": True,
        "jailbreak_probes": -1,
        "features": [
            "Unlimited eval runs",
            "All 200+ jailbreak probes",
            "Unlimited baselines",
            "5 alert rules",
            "90-day data retention",
            "API access (CI/CD)",
        ],
    },
    "team": {
        "name": "Team",
        "price_usd": 99,
        "price_inr": 24999,
        "stripe_price_id": settings.stripe_team_price_id,
        "eval_runs_per_month": -1,
        "team_members": 10,
        "baselines": -1,
        "alert_rules": -1,
        "data_retention_days": 365,
        "api_access": True,
        "jailbreak_probes": -1,
        "features": [
            "Everything in Pro",
            "10 team members",
            "Unlimited alert rules",
            "1-year data retention",
            "Priority support",
        ],
    },
}


# ─── Schemas ──────────────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    plan: str   # "pro" or "team"

class PortalRequest(BaseModel):
    return_url: Optional[str] = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_workspace(db: AsyncSession, workspace_id: str) -> Workspace:
    ws = await db.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(404, "Workspace not found")
    return ws


async def _get_or_create_stripe_customer(
    db: AsyncSession,
    workspace: Workspace,
    user: User,
) -> str:
    """Get existing Stripe customer ID or create a new one."""
    if workspace.stripe_customer_id:
        return workspace.stripe_customer_id

    customer = stripe.Customer.create(
        email=user.email,
        name=user.name or user.email,
        metadata={
            "workspace_id": str(workspace.id),
            "workspace_slug": workspace.slug,
        },
    )
    workspace.stripe_customer_id = customer.id
    await db.commit()
    return customer.id


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/plans")
async def get_plans():
    """Return all available plans and their features."""
    return {"plans": PLANS}


@router.post("/checkout")
async def create_checkout_session(
    body: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
):
    """Create a Stripe Checkout session for plan upgrade."""
    if body.plan not in ("pro", "team"):
        raise HTTPException(400, "Invalid plan. Choose 'pro' or 'team'")

    plan = PLANS[body.plan]
    price_id = plan.get("stripe_price_id")
    if not price_id:
        raise HTTPException(500, f"Stripe price ID not configured for plan '{body.plan}'")

    workspace = await _get_workspace(db, workspace_id)
    customer_id = await _get_or_create_stripe_customer(db, workspace, user)

    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{settings.frontend_url}/settings?upgraded=true&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.frontend_url}/settings?upgrade_cancelled=true",
            metadata={
                "workspace_id": str(workspace.id),
                "plan": body.plan,
            },
            subscription_data={
                "metadata": {
                    "workspace_id": str(workspace.id),
                    "plan": body.plan,
                }
            },
            allow_promotion_codes=True,
        )
        return {"checkout_url": session.url, "session_id": session.id}

    except stripe.error.StripeError as e:
        raise HTTPException(400, str(e.user_message))


@router.post("/portal")
async def create_billing_portal(
    body: PortalRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    workspace_id: str = Depends(get_current_workspace_id),
):
    """Create Stripe Customer Portal link (manage subscription, invoices, cancel)."""
    workspace = await _get_workspace(db, workspace_id)

    if not workspace.stripe_customer_id:
        raise HTTPException(400, "No billing account found. Please upgrade first.")

    try:
        session = stripe.billing_portal.Session.create(
            customer=workspace.stripe_customer_id,
            return_url=body.return_url or f"{settings.frontend_url}/settings",
        )
        return {"portal_url": session.url}

    except stripe.error.StripeError as e:
        raise HTTPException(400, str(e.user_message))


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    stripe_signature: str = Header(None, alias="stripe-signature"),
):
    """
    Stripe webhook handler.
    Stripe sends events here when subscriptions change.
    Verify signature to ensure event is from Stripe (not spoofed).
    """
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid Stripe signature")
    except Exception as e:
        raise HTTPException(400, f"Webhook error: {str(e)}")

    event_type = event["type"]
    data = event["data"]["object"]

    # ── Handle subscription lifecycle events ─────────────────────────────────

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(db, data)

    elif event_type in (
        "customer.subscription.updated",
        "customer.subscription.created",
    ):
        await _handle_subscription_updated(db, data)

    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(db, data)

    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(db, data)

    # Always return 200 — Stripe retries on non-200
    return {"received": True}


# ─── Webhook handlers ────────────────────────────────────────────────────────

async def _handle_checkout_completed(db: AsyncSession, session: dict):
    """User completed checkout — upgrade workspace plan."""
    workspace_id = session.get("metadata", {}).get("workspace_id")
    plan = session.get("metadata", {}).get("plan", "pro")
    subscription_id = session.get("subscription")

    if not workspace_id:
        return

    workspace = await db.get(Workspace, workspace_id)
    if workspace:
        workspace.plan = plan
        workspace.stripe_subscription_id = subscription_id
        await db.commit()
        print(f"✅ Upgraded workspace {workspace_id} to {plan}")


async def _handle_subscription_updated(db: AsyncSession, subscription: dict):
    """Subscription changed — sync plan status."""
    workspace_id = subscription.get("metadata", {}).get("workspace_id")
    plan = subscription.get("metadata", {}).get("plan", "pro")
    status = subscription.get("status")

    if not workspace_id:
        return

    workspace = await db.get(Workspace, workspace_id)
    if workspace:
        if status == "active":
            workspace.plan = plan
        elif status in ("canceled", "unpaid", "past_due"):
            workspace.plan = "free"
        workspace.stripe_subscription_id = subscription.get("id")
        await db.commit()


async def _handle_subscription_deleted(db: AsyncSession, subscription: dict):
    """Subscription cancelled — downgrade to free."""
    workspace_id = subscription.get("metadata", {}).get("workspace_id")
    if not workspace_id:
        return

    workspace = await db.get(Workspace, workspace_id)
    if workspace:
        workspace.plan = "free"
        workspace.stripe_subscription_id = None
        await db.commit()
        print(f"⬇️  Downgraded workspace {workspace_id} to free (subscription cancelled)")


async def _handle_payment_failed(db: AsyncSession, invoice: dict):
    """Payment failed — log it (Stripe will retry automatically)."""
    customer_id = invoice.get("customer")
    amount = invoice.get("amount_due", 0) / 100
    print(f"⚠️  Payment failed for customer {customer_id}: ${amount}")
    # Could send email notification here via Resend
