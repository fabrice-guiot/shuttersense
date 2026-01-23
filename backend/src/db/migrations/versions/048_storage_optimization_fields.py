"""Add storage optimization fields to analysis_results.

Revision ID: 048_storage_optimization_fields
Revises: 047_fix_manifests_uuid
Create Date: 2026-01-23

Issue #92: Storage Optimization for Analysis Results
- Add input_state_hash for detecting unchanged collections
- Add input_state_json for debugging (optional, DEBUG mode only)
- Add no_change_copy flag for deduplicated results
- Add download_report_from reference to source result
- Add indexes for optimization queries
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '048_storage_optimization_fields'
down_revision = '047_fix_manifests_uuid'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add storage optimization columns and indexes to analysis_results."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Add new columns to analysis_results
    op.add_column('analysis_results', sa.Column(
        'input_state_hash',
        sa.String(64),
        nullable=True,
        comment='SHA-256 hash of Input State components'
    ))

    # JSONB for PostgreSQL, JSON for SQLite
    if dialect == 'postgresql':
        op.add_column('analysis_results', sa.Column(
            'input_state_json',
            postgresql.JSONB(),
            nullable=True,
            comment='Full Input State for debugging'
        ))
    else:
        op.add_column('analysis_results', sa.Column(
            'input_state_json',
            sa.JSON(),
            nullable=True,
            comment='Full Input State for debugging'
        ))

    op.add_column('analysis_results', sa.Column(
        'no_change_copy',
        sa.Boolean(),
        server_default='false',
        nullable=False,
        comment='True if this result references another'
    ))
    op.add_column('analysis_results', sa.Column(
        'download_report_from',
        sa.String(50),
        nullable=True,
        comment='GUID of source result for report download'
    ))

    # Add new indexes for optimization queries
    # Note: Partial indexes only supported in PostgreSQL
    if dialect == 'postgresql':
        op.create_index(
            'idx_results_input_state',
            'analysis_results',
            ['collection_id', 'tool', 'input_state_hash'],
            postgresql_where=sa.text('input_state_hash IS NOT NULL')
        )
        op.create_index(
            'idx_results_no_change_source',
            'analysis_results',
            ['download_report_from'],
            postgresql_where=sa.text('download_report_from IS NOT NULL')
        )
    else:
        # SQLite: create regular indexes (no partial index support)
        op.create_index(
            'idx_results_input_state',
            'analysis_results',
            ['collection_id', 'tool', 'input_state_hash']
        )
        op.create_index(
            'idx_results_no_change_source',
            'analysis_results',
            ['download_report_from']
        )

    # Cleanup index (works for both PostgreSQL and SQLite)
    op.create_index(
        'idx_results_cleanup',
        'analysis_results',
        ['team_id', 'status', 'created_at']
    )


def downgrade() -> None:
    """Remove storage optimization columns and indexes."""
    op.drop_index('idx_results_cleanup', table_name='analysis_results')
    op.drop_index('idx_results_no_change_source', table_name='analysis_results')
    op.drop_index('idx_results_input_state', table_name='analysis_results')
    op.drop_column('analysis_results', 'download_report_from')
    op.drop_column('analysis_results', 'no_change_copy')
    op.drop_column('analysis_results', 'input_state_json')
    op.drop_column('analysis_results', 'input_state_hash')
