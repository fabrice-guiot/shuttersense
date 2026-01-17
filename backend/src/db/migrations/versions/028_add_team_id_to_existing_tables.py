"""Add team_id to existing tables

Revision ID: 028_add_team_id_to_existing_tables
Revises: 027_create_api_tokens_table
Create Date: 2026-01-15

Adds nullable team_id column to all existing tenant-scoped tables.
Part of Issue #73 - Teams/Tenants and User Management.

This migration adds the team_id column as NULLABLE to allow existing
data to be migrated. A follow-up migration (after seeding a default
team and updating existing records) will add the NOT NULL constraint.

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
revision = '028_add_team_id'
down_revision = '027_create_api_tokens'
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
    Add nullable team_id column to all tenant-scoped tables.

    The column is nullable to support existing data migration.
    A follow-up process should:
    1. Create a default team using seed_first_team.py
    2. Update all existing records to use the default team
    3. Run a migration to add NOT NULL constraint and FK
    """
    for table_name in TENANT_SCOPED_TABLES:
        # Add nullable team_id column
        op.add_column(
            table_name,
            sa.Column('team_id', sa.Integer(), nullable=True)
        )
        # Create index for team-scoped queries
        op.create_index(
            f'ix_{table_name}_team_id',
            table_name,
            ['team_id']
        )


def downgrade() -> None:
    """Remove team_id column from all tenant-scoped tables."""
    for table_name in reversed(TENANT_SCOPED_TABLES):
        op.drop_index(f'ix_{table_name}_team_id', table_name=table_name)
        op.drop_column(table_name, 'team_id')
