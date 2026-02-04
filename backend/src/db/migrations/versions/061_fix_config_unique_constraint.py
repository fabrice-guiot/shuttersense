"""Fix configuration unique constraint for multi-tenancy.

Revision ID: 061_fix_config_unique
Revises: 060_add_release_artifacts
Create Date: 2026-02-04

This migration fixes a bug in migration 052 where the wrong index name was used.
Migration 052 tried to drop 'idx_config_category_key' but the actual index name
created in migration 005 was 'ix_configurations_category_key'.

This caused the original global unique constraint to remain in place, preventing
multiple teams from having their own retention configurations (duplicate key error).

This migration:
1. Drops the old 'ix_configurations_category_key' index if it still exists
2. Creates the correct team-scoped unique index if it doesn't exist
"""
from alembic import op
import sqlalchemy as sa


revision = '061_fix_config_unique'
down_revision = '060_add_release_artifacts'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Fix configuration unique constraint to be team-scoped.

    For databases where migration 052 ran but didn't fix the constraint
    (due to wrong index name), this drops the old index and ensures the
    new team-scoped index exists.
    """
    bind = op.get_bind()

    if bind.dialect.name == 'postgresql':
        # Check if the OLD index still exists (migration 052 bug didn't drop it)
        result = bind.execute(sa.text(
            "SELECT 1 FROM pg_indexes WHERE indexname = 'ix_configurations_category_key'"
        ))
        if result.fetchone():
            op.drop_index('ix_configurations_category_key', table_name='configurations')

        # Check if the NEW team-scoped index exists
        result = bind.execute(sa.text(
            "SELECT 1 FROM pg_indexes WHERE indexname = 'uq_config_team_category_key'"
        ))
        if not result.fetchone():
            op.create_index(
                'uq_config_team_category_key',
                'configurations',
                ['team_id', 'category', 'key'],
                unique=True
            )
    else:
        # SQLite: use try/except pattern
        try:
            op.drop_index('ix_configurations_category_key', table_name='configurations')
        except Exception:
            pass  # Index doesn't exist, already dropped

        # Create new index if not exists (SQLite doesn't support IF NOT EXISTS for indexes)
        try:
            op.create_index(
                'uq_config_team_category_key',
                'configurations',
                ['team_id', 'category', 'key'],
                unique=True
            )
        except Exception:
            pass  # Index already exists


def downgrade() -> None:
    """
    This is a bugfix migration - downgrade is a no-op.

    The correct state is maintained by migration 052 (now fixed).
    """
    pass
