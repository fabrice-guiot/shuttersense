"""Change category name unique constraint to team-scoped.

Revision ID: 062_category_name_team
Revises: 061_fix_config_unique
Create Date: 2026-02-09

Changes unique constraint on categories.name from global to team-scoped (team_id, name).
In a multi-tenant application, different teams should be able to have categories
with the same name (e.g., each team gets their own "Airshow" category).

Fixes production error when seeding default categories for a second team:
    duplicate key value violates unique constraint "categories_name_key"
"""
from alembic import op
import sqlalchemy as sa


revision = '062_category_name_team'
down_revision = '061_fix_config_unique'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Change category name uniqueness from global to team-scoped.

    Steps:
    1. Drop the existing unique constraint on name (categories_name_key)
    2. Drop the unique index on name (ix_categories_name) if it exists
    3. Create a new composite unique constraint on (team_id, name)
    """
    bind = op.get_bind()

    if bind.dialect.name == 'postgresql':
        # Check and drop unique constraint (PostgreSQL names it 'categories_name_key')
        result = bind.execute(sa.text(
            "SELECT 1 FROM pg_constraint WHERE conname = 'categories_name_key'"
        ))
        if result.fetchone():
            op.drop_constraint('categories_name_key', 'categories', type_='unique')

        # Check and drop unique index if exists
        result = bind.execute(sa.text(
            "SELECT 1 FROM pg_indexes WHERE indexname = 'ix_categories_name'"
        ))
        if result.fetchone():
            op.drop_index('ix_categories_name', table_name='categories')

        # Check if team-scoped constraint already exists
        result = bind.execute(sa.text(
            "SELECT 1 FROM pg_constraint WHERE conname = 'uq_categories_team_name'"
        ))
        if not result.fetchone():
            op.create_unique_constraint(
                'uq_categories_team_name',
                'categories',
                ['team_id', 'name']
            )
    else:
        # SQLite: use try/except pattern
        try:
            op.drop_constraint('categories_name_key', 'categories', type_='unique')
        except Exception:
            pass  # Constraint may not exist

        try:
            op.drop_index('ix_categories_name', table_name='categories')
        except Exception:
            pass  # Index may not exist

        try:
            op.create_unique_constraint(
                'uq_categories_team_name',
                'categories',
                ['team_id', 'name']
            )
        except Exception:
            pass  # Constraint may already exist


def downgrade() -> None:
    """
    Revert to global name uniqueness.

    WARNING: This will fail if duplicate category names exist across different teams.
    """
    op.drop_constraint('uq_categories_team_name', 'categories', type_='unique')
    op.create_index('ix_categories_name', 'categories', ['name'], unique=True)
