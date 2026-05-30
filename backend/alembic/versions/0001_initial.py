"""Initial schema — all tables

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Enable pgvector ───────────────────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── workspaces ────────────────────────────────────────────────────────────
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("plan", sa.String(50), server_default="free"),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_workspaces_slug", "workspaces", ["slug"], unique=True)

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── workspace_members ─────────────────────────────────────────────────────
    op.create_table(
        "workspace_members",
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(50), server_default="member"),
        sa.Column("joined_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ── model_endpoints ───────────────────────────────────────────────────────
    op.create_table(
        "model_endpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(255), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("temperature", sa.Float(), server_default="0.0"),
        sa.Column("max_tokens", sa.Integer(), server_default="1000"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_model_endpoints_workspace", "model_endpoints", ["workspace_id"])

    # ── datasets ──────────────────────────────────────────────────────────────
    op.create_table(
        "datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("row_count", sa.Integer(), server_default="0"),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_datasets_workspace", "datasets", ["workspace_id"])

    # ── dataset_rows ──────────────────────────────────────────────────────────
    op.create_table(
        "dataset_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("input_prompt", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=True),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), server_default="{}"),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_dataset_rows_dataset", "dataset_rows", ["dataset_id"])

    # ── baselines (created before eval_runs because eval_runs FK references it)
    op.create_table(
        "baselines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        ),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model_endpoint_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("eval_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("pinned_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ── eval_runs ─────────────────────────────────────────────────────────────
    op.create_table(
        "eval_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        ),
        sa.Column("dataset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datasets.id")),
        sa.Column("model_endpoint_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("model_endpoints.id")),
        sa.Column("triggered_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("status", sa.String(50), server_default="queued"),
        sa.Column("eval_types", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("concurrency", sa.Integer(), server_default="5"),
        sa.Column("baseline_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("baselines.id"), nullable=True),
        sa.Column("total_rows", sa.Integer(), server_default="0"),
        sa.Column("completed_rows", sa.Integer(), server_default="0"),
        sa.Column("hallucination_score", sa.Float(), nullable=True),
        sa.Column("jailbreak_resistance_score", sa.Float(), nullable=True),
        sa.Column("factual_accuracy_score", sa.Float(), nullable=True),
        sa.Column("regression_pass_rate", sa.Float(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_eval_runs_workspace", "eval_runs", ["workspace_id"])
    op.create_index("ix_eval_runs_status", "eval_runs", ["status"])
    op.create_index("ix_eval_runs_created_at", "eval_runs", ["created_at"])

    # ── eval_results ──────────────────────────────────────────────────────────
    op.create_table(
        "eval_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "eval_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("eval_runs.id", ondelete="CASCADE"),
        ),
        sa.Column("dataset_row_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("dataset_rows.id")),
        sa.Column("actual_output", sa.Text(), nullable=False),
        sa.Column("hallucination_detected", sa.Boolean(), nullable=True),
        sa.Column("hallucination_confidence", sa.Float(), nullable=True),
        sa.Column("hallucination_reason", sa.Text(), nullable=True),
        sa.Column("jailbreak_succeeded", sa.Boolean(), nullable=True),
        sa.Column("jailbreak_category", sa.String(100), nullable=True),
        sa.Column("factual_score", sa.Float(), nullable=True),
        sa.Column("similarity_score", sa.Float(), nullable=True),
        # pgvector column — 1536 dims for text-embedding-3-small
        sa.Column(
            "output_embedding",
            sa.Text(),   # placeholder; real vector type added below
            nullable=True,
        ),
        sa.Column("judge_verdict", sa.String(50), nullable=True),
        sa.Column("judge_reasoning", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_eval_results_run", "eval_results", ["eval_run_id"])
    op.create_index("ix_eval_results_verdict", "eval_results", ["judge_verdict"])

    # Convert output_embedding from Text to vector(1536)
    op.execute("ALTER TABLE eval_results ALTER COLUMN output_embedding TYPE vector(1536) USING NULL")

    # ── alert_rules ───────────────────────────────────────────────────────────
    op.create_table(
        "alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("metric", sa.String(100), nullable=False),
        sa.Column("operator", sa.String(10), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("notify_email", postgresql.ARRAY(sa.String()), server_default="{}"),
        sa.Column("notify_slack_webhook", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ── Add FK from baselines → eval_runs (now that eval_runs exists) ─────────
    op.create_foreign_key(
        "fk_baselines_eval_run",
        "baselines", "eval_runs",
        ["eval_run_id"], ["id"],
    )
    op.create_foreign_key(
        "fk_baselines_dataset",
        "baselines", "datasets",
        ["dataset_id"], ["id"],
    )
    op.create_foreign_key(
        "fk_baselines_model_endpoint",
        "baselines", "model_endpoints",
        ["model_endpoint_id"], ["id"],
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("alert_rules")
    op.drop_table("eval_results")
    op.drop_table("eval_runs")
    op.drop_table("baselines")
    op.drop_table("dataset_rows")
    op.drop_table("datasets")
    op.drop_table("model_endpoints")
    op.drop_table("workspace_members")
    op.drop_table("users")
    op.drop_table("workspaces")
    op.execute("DROP EXTENSION IF EXISTS vector")
