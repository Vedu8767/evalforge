"""Add performance indexes

Revision ID: 0002_indexes
Revises: 0001_initial
Create Date: 2025-01-01 00:01:00.000000
"""
from alembic import op

revision = "0002_indexes"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Partial index: find all running/queued eval runs fast
    op.execute("""
        CREATE INDEX ix_eval_runs_active
        ON eval_runs (workspace_id, created_at DESC)
        WHERE status IN ('queued', 'running')
    """)

    # Index for fetching results of a run ordered by time (for SSE stream)
    op.execute("""
        CREATE INDEX ix_eval_results_run_time
        ON eval_results (eval_run_id, created_at ASC)
    """)

    # Index for hallucination filtering
    op.execute("""
        CREATE INDEX ix_eval_results_hallucination
        ON eval_results (eval_run_id, hallucination_detected)
        WHERE hallucination_detected IS NOT NULL
    """)

    # pgvector HNSW index for fast approximate nearest-neighbor search
    # Used when comparing embeddings for regression testing
    op.execute("""
        CREATE INDEX ix_eval_results_embedding_hnsw
        ON eval_results USING hnsw (output_embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        WHERE output_embedding IS NOT NULL
    """)

    # Index for dataset rows lookup
    op.execute("""
        CREATE INDEX ix_dataset_rows_dataset_created
        ON dataset_rows (dataset_id, created_at ASC)
    """)

    # GIN index on tags array for fast tag filtering
    op.execute("""
        CREATE INDEX ix_dataset_rows_tags
        ON dataset_rows USING gin (tags)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_eval_runs_active")
    op.execute("DROP INDEX IF EXISTS ix_eval_results_run_time")
    op.execute("DROP INDEX IF EXISTS ix_eval_results_hallucination")
    op.execute("DROP INDEX IF EXISTS ix_eval_results_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_dataset_rows_dataset_created")
    op.execute("DROP INDEX IF EXISTS ix_dataset_rows_tags")
