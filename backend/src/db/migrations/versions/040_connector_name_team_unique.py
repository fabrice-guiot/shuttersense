"""Change connector name unique constraint to team-scoped

Revision ID: 040_connector_name_team
Revises: 039_collection_accessible
Create Date: 2026-01-20

Changes unique constraint on connectors.name from global to team-scoped.
In a multi-tenant application, different teams should be able to have
connectors with the same name without conflicts.

Part of Issue #90 - Distributed Agent Architecture.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '040_connector_name_team'
down_revision = '039_is_accessible_nullable'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Change connector name uniqueness from global to team-scoped.

    Steps:
    1. Drop the existing unique constraint on name (connectors_name_key)
    2. Drop the unique index on name (ix_connectors_name) if it exists
    3. Create a new composite unique constraint on (team_id, name)
    """
    # Drop the existing unique constraint on name
    # PostgreSQL auto-generates constraint name as 'connectors_name_key'
    try:
        op.drop_constraint('connectors_name_key', 'connectors', type_='unique')
    except Exception:
        pass  # Constraint may not exist

    # Drop the unique index on name (created by SQLAlchemy's unique=True + index=True)
    try:
        op.drop_index('ix_connectors_name', table_name='connectors')
    except Exception:
        pass  # Index may not exist

    # Create composite unique constraint on (team_id, name)
    op.create_unique_constraint(
        'uq_connectors_team_name',
        'connectors',
        ['team_id', 'name']
    )


def downgrade() -> None:
    """Revert to global name uniqueness (may fail if duplicate names exist)."""
    # Drop composite unique constraint
    op.drop_constraint('uq_connectors_team_name', 'connectors', type_='unique')

    # Restore global unique index on name
    op.create_index('ix_connectors_name', 'connectors', ['name'], unique=True)
