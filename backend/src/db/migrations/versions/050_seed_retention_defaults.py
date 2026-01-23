"""Seed default retention settings for existing teams.

Revision ID: 050_seed_retention_defaults
Revises: 049_storage_metrics_table
Create Date: 2026-01-23

Issue #92: Storage Optimization for Analysis Results
Seeds default retention settings for all existing teams that don't have
retention configuration yet.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision = '050_seed_retention_defaults'
down_revision = '049_storage_metrics_table'
branch_labels = None
depends_on = None


# Default retention settings
DEFAULT_SETTINGS = [
    ("job_completed_days", 2, "Days to retain completed jobs"),
    ("job_failed_days", 7, "Days to retain failed jobs"),
    ("result_completed_days", 0, "Days to retain completed results (0 = unlimited)"),
    ("preserve_per_collection", 1, "Minimum results to keep per collection+tool"),
]

RETENTION_CATEGORY = "result_retention"


def upgrade() -> None:
    """Seed default retention settings for existing teams."""
    bind = op.get_bind()

    # Define table references for raw SQL operations
    teams_table = table('teams', column('id', sa.Integer))
    configurations_table = table(
        'configurations',
        column('id', sa.Integer),
        column('team_id', sa.Integer),
        column('category', sa.String),
        column('key', sa.String),
        column('value_json', sa.JSON),
        column('description', sa.Text),
        column('source', sa.String),
        column('created_at', sa.DateTime),
        column('updated_at', sa.DateTime),
    )

    # Get all team IDs
    result = bind.execute(sa.select(teams_table.c.id))
    team_ids = [row[0] for row in result]

    if not team_ids:
        # No teams exist yet, nothing to seed
        return

    # For each team, seed default retention settings if they don't exist
    for team_id in team_ids:
        for key, value, description in DEFAULT_SETTINGS:
            # Check if setting already exists
            existing = bind.execute(
                sa.select(configurations_table.c.id).where(
                    sa.and_(
                        configurations_table.c.team_id == team_id,
                        configurations_table.c.category == RETENTION_CATEGORY,
                        configurations_table.c.key == key
                    )
                )
            ).first()

            if not existing:
                # Insert default setting
                bind.execute(
                    configurations_table.insert().values(
                        team_id=team_id,
                        category=RETENTION_CATEGORY,
                        key=key,
                        value_json=value,
                        description=description,
                        source='database',
                        created_at=sa.func.now(),
                        updated_at=sa.func.now(),
                    )
                )


def downgrade() -> None:
    """Remove seeded retention settings."""
    bind = op.get_bind()

    configurations_table = table(
        'configurations',
        column('category', sa.String),
    )

    # Delete all retention settings
    bind.execute(
        configurations_table.delete().where(
            configurations_table.c.category == RETENTION_CATEGORY
        )
    )
