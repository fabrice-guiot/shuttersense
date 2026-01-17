"""Populate team_id and enforce NOT NULL constraint

Revision ID: 031_team_id_not_null
Revises: 030_user_type_api_tokens
Create Date: 2026-01-16

Phase 11: Finalize multi-tenancy by enforcing team_id NOT NULL.

Prerequisites:
- A default team MUST exist (created via seed_first_team.py)
- This migration will fail if no team exists

Changes:
1. Update all existing records with NULL team_id to use the first team
2. Add NOT NULL constraint to team_id column
3. Add foreign key constraint to teams table

Affected tables:
- collections
- configurations
- connectors
- pipelines
- analysis_results
- events
- event_series
- categories
- locations
- organizers
- performers
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '031_team_id_not_null'
down_revision = '030_user_type_api_tokens'
branch_labels = None
depends_on = None


# Tables that require team_id for multi-tenancy
TENANT_SCOPED_TABLES = [
    'collections',
    'configurations',
    'connectors',
    'pipelines',
    'analysis_results',
    'events',
    'event_series',
    'categories',
    'locations',
    'organizers',
    'performers',
]


def upgrade() -> None:
    """
    Populate team_id for existing records and enforce NOT NULL.

    This migration:
    1. Finds the first team (expected to be the default team)
    2. Updates all NULL team_id values to use that team
    3. Adds NOT NULL constraint
    4. Adds foreign key constraint
    """
    # Get a connection to execute raw SQL
    connection = op.get_bind()

    # Find the first team (should be the default team created by seed script)
    result = connection.execute(sa.text("SELECT id FROM teams ORDER BY id LIMIT 1"))
    row = result.fetchone()

    if row is None:
        raise RuntimeError(
            "No team found in database. "
            "Please run 'python -m backend.src.scripts.seed_first_team' first "
            "to create a default team before running this migration."
        )

    default_team_id = row[0]

    # Update all NULL team_id values to use the default team
    for table_name in TENANT_SCOPED_TABLES:
        connection.execute(
            sa.text(f"UPDATE {table_name} SET team_id = :team_id WHERE team_id IS NULL"),
            {"team_id": default_team_id}
        )

    # Now add NOT NULL constraint and foreign key to each table
    for table_name in TENANT_SCOPED_TABLES:
        # Alter column to NOT NULL
        op.alter_column(
            table_name,
            'team_id',
            existing_type=sa.Integer(),
            nullable=False
        )

        # Add foreign key constraint
        op.create_foreign_key(
            f'fk_{table_name}_team_id',
            table_name,
            'teams',
            ['team_id'],
            ['id']
        )


def downgrade() -> None:
    """
    Remove NOT NULL constraint and foreign key (but keep the column).

    Note: This does NOT remove the team_id values, just the constraints.
    """
    for table_name in reversed(TENANT_SCOPED_TABLES):
        # Drop foreign key constraint
        op.drop_constraint(f'fk_{table_name}_team_id', table_name, type_='foreignkey')

        # Make column nullable again
        op.alter_column(
            table_name,
            'team_id',
            existing_type=sa.Integer(),
            nullable=True
        )
