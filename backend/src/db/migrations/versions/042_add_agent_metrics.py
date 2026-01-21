"""Add metrics_json column to agents table

Revision ID: 042_agent_metrics
Revises: 041_agent_pending_commands
Create Date: 2026-01-21

Adds metrics_json JSONB column to agents table for storing
system resource metrics (CPU, memory, disk) reported by agents.

Part of Issue #90 - Distributed Agent Architecture (Phase 11).
Task: T167 - Store agent metrics in Agent model.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '042_agent_metrics'
down_revision = '041_agent_pending_commands'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add metrics_json column to agents table.

    This column stores system resource metrics reported by agents:
    - cpu_percent: CPU usage percentage (0-100)
    - memory_percent: Memory usage percentage (0-100)
    - disk_free_gb: Free disk space in GB
    - metrics_updated_at: Timestamp of last metrics update

    The column is a JSONB object (with Text fallback for SQLite).
    Default is null (no metrics reported yet).
    """
    op.add_column(
        'agents',
        sa.Column(
            'metrics_json',
            JSONB().with_variant(sa.Text, 'sqlite'),
            nullable=True,
            server_default=None
        )
    )


def downgrade() -> None:
    """Remove metrics_json column from agents table."""
    op.drop_column('agents', 'metrics_json')
