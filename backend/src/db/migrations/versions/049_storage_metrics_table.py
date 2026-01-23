"""Add storage_metrics table.

Revision ID: 049_storage_metrics_table
Revises: 048_storage_optimization_fields
Create Date: 2026-01-23

Issue #92: Storage Optimization for Analysis Results
- Create storage_metrics table for cumulative cleanup statistics
- One row per team, created on first cleanup or job completion
- Tracks total reports generated, purged counts, and bytes freed
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '049_storage_metrics_table'
down_revision = '048_storage_optimization_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create storage_metrics table for cumulative cleanup statistics."""
    op.create_table(
        'storage_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column(
            'total_reports_generated',
            sa.BigInteger(),
            server_default='0',
            nullable=False,
            comment='Cumulative count of all job completions (COMPLETED, NO_CHANGE, FAILED)'
        ),
        sa.Column(
            'completed_jobs_purged',
            sa.BigInteger(),
            server_default='0',
            nullable=False,
            comment='Cumulative count of completed jobs deleted by cleanup'
        ),
        sa.Column(
            'failed_jobs_purged',
            sa.BigInteger(),
            server_default='0',
            nullable=False,
            comment='Cumulative count of failed jobs deleted by cleanup'
        ),
        sa.Column(
            'completed_results_purged_original',
            sa.BigInteger(),
            server_default='0',
            nullable=False,
            comment='Cumulative count of original results purged (no_change_copy=false)'
        ),
        sa.Column(
            'completed_results_purged_copy',
            sa.BigInteger(),
            server_default='0',
            nullable=False,
            comment='Cumulative count of copy results purged (no_change_copy=true)'
        ),
        sa.Column(
            'estimated_bytes_purged',
            sa.BigInteger(),
            server_default='0',
            nullable=False,
            comment='Cumulative estimated bytes freed from DB (JSON + HTML sizes)'
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False
        ),
        sa.ForeignKeyConstraint(
            ['team_id'],
            ['teams.id'],
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id', name='uq_storage_metrics_team')
    )
    op.create_index('idx_storage_metrics_team', 'storage_metrics', ['team_id'])


def downgrade() -> None:
    """Drop storage_metrics table."""
    op.drop_index('idx_storage_metrics_team', table_name='storage_metrics')
    op.drop_table('storage_metrics')
