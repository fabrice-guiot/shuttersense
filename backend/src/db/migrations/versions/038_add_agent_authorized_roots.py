"""Add authorized_roots_json column to agents table

Revision ID: 038_agent_auth_roots
Revises: 037_agent_api_key_prefix
Create Date: 2026-01-19

Adds authorized_roots_json JSONB column to agents table for storing
the local filesystem roots that an agent is authorized to access.

Part of Issue #90 - Distributed Agent Architecture (Phase 6b).
Task: T118
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision = '038_agent_auth_roots'
down_revision = '037_agent_api_key_prefix'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add authorized_roots_json column to agents table.

    This column stores the list of local filesystem paths that the agent
    is authorized to access. Used for path validation when:
    - Creating/updating LOCAL collections bound to the agent
    - Running accessibility tests for LOCAL collections

    The column is a JSONB array (with Text fallback for SQLite).
    Default is an empty array [].
    """
    op.add_column(
        'agents',
        sa.Column(
            'authorized_roots_json',
            JSONB().with_variant(sa.Text, 'sqlite'),
            nullable=False,
            server_default='[]'
        )
    )


def downgrade() -> None:
    """Remove authorized_roots_json column from agents table."""
    op.drop_column('agents', 'authorized_roots_json')
