"""Add GIN index for JSONB queries

Revision ID: 009_add_jsonb_gin_index
Revises: 008_nullable_collection_id
Create Date: 2026-01-09

Adds GIN index on results_json for efficient JSONB queries used by trend analysis.
This improves performance when extracting metrics from stored analysis results.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '009_add_jsonb_gin_index'
down_revision = '008_nullable_collection_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add GIN index for JSONB queries on analysis_results.results_json.

    The GIN index enables efficient queries for:
    - Trend analysis JSONB metric extraction
    - Searching within results_json content
    - Path-based JSONB queries (e.g., results_json->'metric_name')

    Performance impact:
    - Improves read performance for trend queries
    - Slight increase in write time for INSERT/UPDATE
    - Index size scales with data volume

    PostgreSQL-specific: GIN indexes are not available in SQLite.
    """
    # Add GIN index for JSONB queries (T177)
    # Using postgresql_using='gin' for PostgreSQL GIN index
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_analysis_results_results_json_gin
        ON analysis_results USING gin (results_json jsonb_path_ops)
    """)


def downgrade() -> None:
    """
    Drop GIN index on results_json.
    """
    op.execute("""
        DROP INDEX IF EXISTS ix_analysis_results_results_json_gin
    """)
