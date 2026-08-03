"""Add columns needed to actually wire jailbreak eval into the run pipeline

Jailbreak red-team runs have no dataset (they run a fixed probe list against
the endpoint directly), and each result needs to record which probe produced
it and in which language. Previously the pipeline had no way to store this,
which was one reason jailbreak/hallucination evals were never invoked at all.

Revision ID: 0004_jailbreak_pipeline
Revises: 0003_stripe
Create Date: 2026-07-30 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_jailbreak_pipeline"
down_revision = "0003_stripe"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Which probes were selected for a red-team (jailbreak) run.
    op.add_column(
        "eval_runs",
        sa.Column("probe_ids", sa.ARRAY(sa.String()), nullable=True),
    )
    # Which probe produced this specific result, and in what language
    # (en / hi / mr / hinglish). Defaults to "en" so existing rows and
    # non-jailbreak results (factual/hallucination) aren't affected.
    op.add_column(
        "eval_results",
        sa.Column("jailbreak_probe_id", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "eval_results",
        sa.Column("language", sa.String(length=20), nullable=True, server_default="en"),
    )


def downgrade() -> None:
    op.drop_column("eval_results", "language")
    op.drop_column("eval_results", "jailbreak_probe_id")
    op.drop_column("eval_runs", "probe_ids")
