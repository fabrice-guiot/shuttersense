"""Change collection name unique constraint to team-scoped.

Revision ID: 063_collection_name_team
Revises: 062_category_name_team
Create Date: 2026-02-09

Changes unique constraint on collections.name from global to team-scoped (team_id, name).
In a multi-tenant application, different teams should be able to have collections
with the same name (e.g., each team can have their own "Wedding Photos" collection).
"""
from alembic import op
import sqlalchemy as sa


revision = '063_collection_name_team'
down_revision = '062_category_name_team'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Change collection name uniqueness from global to team-scoped.

    Steps:
    1. Drop the existing unique constraint on name (collections_name_key)
    2. Drop the unique index on name (ix_collections_name) if it exists
    3. Create a new composite unique constraint on (team_id, name)
    """
    bind = op.get_bind()

    if bind.dialect.name == 'postgresql':
        # Check and drop unique constraint (PostgreSQL names it 'collections_name_key')
        result = bind.execute(sa.text(
            "SELECT 1 FROM pg_constraint WHERE conname = 'collections_name_key'"
        ))
        if result.fetchone():
            op.drop_constraint('collections_name_key', 'collections', type_='unique')

        # Check and drop unique index if exists
        result = bind.execute(sa.text(
            "SELECT 1 FROM pg_indexes WHERE indexname = 'ix_collections_name'"
        ))
        if result.fetchone():
            op.drop_index('ix_collections_name', table_name='collections')

        # Check if team-scoped constraint already exists
        result = bind.execute(sa.text(
            "SELECT 1 FROM pg_constraint WHERE conname = 'uq_collections_team_name'"
        ))
        if not result.fetchone():
            op.create_unique_constraint(
                'uq_collections_team_name',
                'collections',
                ['team_id', 'name']
            )
    else:
        # SQLite: use try/except pattern
        try:
            op.drop_constraint('collections_name_key', 'collections', type_='unique')
        except Exception:
            pass  # Constraint may not exist

        try:
            op.drop_index('ix_collections_name', table_name='collections')
        except Exception:
            pass  # Index may not exist

        try:
            op.create_unique_constraint(
                'uq_collections_team_name',
                'collections',
                ['team_id', 'name']
            )
        except Exception:
            pass  # Constraint may already exist


def downgrade() -> None:
    """
    Revert to global name uniqueness.

    WARNING: This will fail if duplicate collection names exist across different teams.
    """
    op.drop_constraint('uq_collections_team_name', 'collections', type_='unique')
    op.create_index('ix_collections_name', 'collections', ['name'], unique=True)
