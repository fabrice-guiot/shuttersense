"""Change collection name unique constraint to team-scoped.

Revision ID: 063_collection_name_team
Revises: 062_category_name_team
Create Date: 2026-02-09

Changes unique constraint on collections.name from global to team-scoped (team_id, name).
In a multi-tenant application, different teams should be able to have collections
with the same name (e.g., each team can have their own "Wedding Photos" collection).
"""
import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError

logger = logging.getLogger('alembic.runtime.migration')

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
        # SQLite: use try/except pattern with specific exceptions
        try:
            op.drop_constraint('collections_name_key', 'collections', type_='unique')
        except (OperationalError, ProgrammingError) as e:
            logger.warning(f"Could not drop constraint 'collections_name_key' (may not exist): {e}")

        try:
            op.drop_index('ix_collections_name', table_name='collections')
        except (OperationalError, ProgrammingError) as e:
            logger.warning(f"Could not drop index 'ix_collections_name' (may not exist): {e}")

        try:
            op.create_unique_constraint(
                'uq_collections_team_name',
                'collections',
                ['team_id', 'name']
            )
        except (OperationalError, ProgrammingError) as e:
            logger.warning(f"Could not create constraint 'uq_collections_team_name' (may already exist): {e}")


def downgrade() -> None:
    """
    Revert to global name uniqueness.

    WARNING: This will fail if duplicate collection names exist across different teams.
    """
    bind = op.get_bind()

    if bind.dialect.name == 'postgresql':
        # Check and drop team-scoped constraint
        result = bind.execute(sa.text(
            "SELECT 1 FROM pg_constraint WHERE conname = 'uq_collections_team_name'"
        ))
        if result.fetchone():
            op.drop_constraint('uq_collections_team_name', 'collections', type_='unique')

        # Check if global index already exists
        result = bind.execute(sa.text(
            "SELECT 1 FROM pg_indexes WHERE indexname = 'ix_collections_name'"
        ))
        if not result.fetchone():
            op.create_index('ix_collections_name', 'collections', ['name'], unique=True)
    else:
        # SQLite: use try/except pattern with specific exceptions
        try:
            op.drop_constraint('uq_collections_team_name', 'collections', type_='unique')
        except (OperationalError, ProgrammingError) as e:
            logger.warning(f"Could not drop constraint 'uq_collections_team_name' (may not exist): {e}")

        try:
            op.create_index('ix_collections_name', 'collections', ['name'], unique=True)
        except (OperationalError, ProgrammingError) as e:
            logger.warning(f"Could not create index 'ix_collections_name' (may already exist): {e}")
