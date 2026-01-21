"""Remove unused collection auto-refresh fields.

These fields were added in 036_add_collection_agent_binding but never used.
Phase 13 implemented team-level TTL configuration instead of per-collection
auto_refresh, refresh_interval_hours, and next_refresh_at settings.

Revision ID: 044
Revises: 043
Create Date: 2026-01-21
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '044_rm_coll_refresh_fields'
down_revision = '043_collection_ttl_config'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove unused auto-refresh columns."""
    op.drop_index('ix_collections_next_refresh_at', table_name='collections')
    op.drop_column('collections', 'auto_refresh')
    op.drop_column('collections', 'refresh_interval_hours')
    op.drop_column('collections', 'next_refresh_at')


def downgrade() -> None:
    """Re-add auto-refresh columns."""
    op.add_column(
        'collections',
        sa.Column('next_refresh_at', sa.DateTime(), nullable=True)
    )
    op.add_column(
        'collections',
        sa.Column('refresh_interval_hours', sa.Integer(), nullable=True)
    )
    op.add_column(
        'collections',
        sa.Column('auto_refresh', sa.Boolean(), nullable=False, server_default='true')
    )
    op.create_index('ix_collections_next_refresh_at', 'collections', ['next_refresh_at'])
