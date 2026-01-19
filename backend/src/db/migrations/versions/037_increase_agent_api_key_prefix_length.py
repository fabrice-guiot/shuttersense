"""Increase agent api_key_prefix column length

Revision ID: 037_agent_api_key_prefix
Revises: 036_add_collection_agent_binding
Create Date: 2026-01-19

Fixes api_key_prefix column being too short (10 chars) for the actual prefix
which is "agt_key_" (8 chars) + 8 random chars = 16 chars.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '037_agent_api_key_prefix'
down_revision = '036_collection_agent'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Increase api_key_prefix column length from 10 to 20."""
    op.alter_column(
        'agents',
        'api_key_prefix',
        type_=sa.String(length=20),
        existing_type=sa.String(length=10),
        existing_nullable=False
    )


def downgrade() -> None:
    """Revert api_key_prefix column length to 10."""
    op.alter_column(
        'agents',
        'api_key_prefix',
        type_=sa.String(length=10),
        existing_type=sa.String(length=20),
        existing_nullable=False
    )
