"""Change configuration unique constraint to team-scoped.

Revision ID: 052_config_team_scoped
Revises: 051_add_no_change_result_status
Create Date: 2026-01-23

Changes unique constraint on configurations from (category, key) to
(team_id, category, key). This allows different teams to have their own
retention settings and other per-team configurations without conflicts.

Part of Issue #92 - Storage Optimization for Analysis Results.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '052_config_team_scoped'
down_revision = '051_add_no_change_result_status'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Change configuration uniqueness from (category, key) to (team_id, category, key).

    Steps:
    1. Drop the existing unique index on (category, key) if it exists
    2. Create a new composite unique index on (team_id, category, key)
    """
    bind = op.get_bind()

    # Check if the old index exists before trying to drop it
    # Note: Original index name from migration 005 is 'ix_configurations_category_key'
    if bind.dialect.name == 'postgresql':
        result = bind.execute(sa.text(
            "SELECT 1 FROM pg_indexes WHERE indexname = 'ix_configurations_category_key'"
        ))
        if result.fetchone():
            op.drop_index('ix_configurations_category_key', table_name='configurations')
    else:
        # SQLite: use if_exists pattern via execute
        op.drop_index('ix_configurations_category_key', table_name='configurations', if_exists=True)

    # Create composite unique index on (team_id, category, key)
    op.create_index(
        'uq_config_team_category_key',
        'configurations',
        ['team_id', 'category', 'key'],
        unique=True
    )


def downgrade() -> None:
    """
    Revert to global (category, key) uniqueness.

    WARNING: This may fail if duplicate (category, key) pairs exist
    across different teams.
    """
    # Drop composite unique index
    op.drop_index('uq_config_team_category_key', table_name='configurations')

    # Restore global unique index on (category, key)
    op.create_index(
        'ix_configurations_category_key',
        'configurations',
        ['category', 'key'],
        unique=True
    )
