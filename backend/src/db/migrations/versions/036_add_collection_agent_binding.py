"""Add agent binding fields to collections

Revision ID: 036_collection_agent
Revises: 035_connector_cred_loc
Create Date: 2026-01-18

Adds agent binding and auto-refresh fields to collections table.
Part of Issue #90 - Distributed Agent Architecture.

New fields support:
- Binding LOCAL collections to specific agents
- Auto-refresh scheduling for collections
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '036_collection_agent'
down_revision = '035_connector_cred_loc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add agent binding and auto-refresh fields to collections table.

    New columns:
    - bound_agent_id: Agent for LOCAL collections (FK to agents)
    - auto_refresh: Enable auto-refresh scheduling (default true)
    - refresh_interval_hours: Hours between refreshes (NULL = no auto-refresh)
    - last_refresh_at: Last completed refresh timestamp
    - next_refresh_at: Computed next scheduled refresh time
    """
    # Add bound_agent_id column
    op.add_column(
        'collections',
        sa.Column('bound_agent_id', sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        'fk_collections_bound_agent_id',
        'collections',
        'agents',
        ['bound_agent_id'],
        ['id']
    )

    # Add auto-refresh columns
    op.add_column(
        'collections',
        sa.Column('auto_refresh', sa.Boolean(), nullable=False, server_default='true')
    )
    op.add_column(
        'collections',
        sa.Column('refresh_interval_hours', sa.Integer(), nullable=True)
    )
    op.add_column(
        'collections',
        sa.Column('last_refresh_at', sa.DateTime(), nullable=True)
    )
    op.add_column(
        'collections',
        sa.Column('next_refresh_at', sa.DateTime(), nullable=True)
    )

    # Create indexes
    op.create_index('ix_collections_bound_agent_id', 'collections', ['bound_agent_id'])
    op.create_index('ix_collections_next_refresh_at', 'collections', ['next_refresh_at'])


def downgrade() -> None:
    """Remove agent binding and auto-refresh fields from collections table."""
    # Drop indexes
    op.drop_index('ix_collections_next_refresh_at', table_name='collections')
    op.drop_index('ix_collections_bound_agent_id', table_name='collections')

    # Drop foreign key
    op.drop_constraint('fk_collections_bound_agent_id', 'collections', type_='foreignkey')

    # Drop columns
    op.drop_column('collections', 'next_refresh_at')
    op.drop_column('collections', 'last_refresh_at')
    op.drop_column('collections', 'refresh_interval_hours')
    op.drop_column('collections', 'auto_refresh')
    op.drop_column('collections', 'bound_agent_id')
