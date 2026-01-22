"""Add pending_commands_json column to agents table

Revision ID: 041_agent_pending_commands
Revises: 040_connector_name_unique
Create Date: 2026-01-20

Adds pending_commands_json JSONB column to agents table for storing
commands to be sent to the agent on the next heartbeat.

Part of Issue #90 - Distributed Agent Architecture (Phase 10).
Task: T156 - Job cancellation via pending_commands mechanism.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '041_agent_pending_commands'
down_revision = '040_connector_name_team'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add pending_commands_json column to agents table.

    This column stores commands to be sent to the agent on the next
    heartbeat response. Commands are strings like "cancel_job:job_xxx".

    After the agent receives the commands in the heartbeat response,
    the commands are cleared from this column.

    The column is a JSONB array (with Text fallback for SQLite).
    Default is an empty array [].
    """
    op.add_column(
        'agents',
        sa.Column(
            'pending_commands_json',
            JSONB().with_variant(sa.Text, 'sqlite'),
            nullable=False,
            server_default='[]'
        )
    )


def downgrade() -> None:
    """Remove pending_commands_json column from agents table."""
    op.drop_column('agents', 'pending_commands_json')
