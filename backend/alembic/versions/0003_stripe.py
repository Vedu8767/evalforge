"""Add Stripe columns to workspaces + plan enforcement

Revision ID: 0003_stripe
Revises: 0002_indexes
Create Date: 2025-01-01 00:02:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_stripe"
down_revision = "0002_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # stripe_customer_id + stripe_subscription_id already in initial migration
    # This migration adds a check constraint on the plan column
    # and a monthly_eval_count helper view

    # ── Add plan constraint ───────────────────────────────────────────────────
    op.execute("""
        ALTER TABLE workspaces
        ADD CONSTRAINT valid_plan
        CHECK (plan IN ('free', 'pro', 'team'))
    """)

    # ── Monthly eval usage view (useful for dashboards) ───────────────────────
    op.execute("""
        CREATE OR REPLACE VIEW monthly_eval_usage AS
        SELECT
            workspace_id,
            DATE_TRUNC('month', created_at) AS month,
            COUNT(*) AS eval_run_count,
            COUNT(*) FILTER (WHERE status = 'completed') AS completed_count,
            COUNT(*) FILTER (WHERE status = 'failed') AS failed_count,
            AVG(overall_score) AS avg_overall_score
        FROM eval_runs
        GROUP BY workspace_id, DATE_TRUNC('month', created_at)
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS monthly_eval_usage")
    op.execute("ALTER TABLE workspaces DROP CONSTRAINT IF EXISTS valid_plan")
