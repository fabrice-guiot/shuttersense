"""Seed default conflict rules and scoring weights for existing teams.

Revision ID: 066_seed_conflict_defaults
Revises: 065_add_website_social
Create Date: 2026-02-13

Issue #182: Calendar Conflict Visualization & Event Picker
Seeds default conflict detection rules and scoring dimension weights
for all existing teams that don't have these configurations yet.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column


# revision identifiers, used by Alembic.
revision = '066_seed_conflict_defaults'
down_revision = '065_add_website_social'
branch_labels = None
depends_on = None


# Default conflict detection rules
DEFAULT_CONFLICT_RULES = [
    ("distance_threshold_miles", {"value": 50, "label": "Distance Threshold (miles)"}, "Maximum miles between events before flagging a distance conflict"),
    ("consecutive_window_days", {"value": 1, "label": "Consecutive Window (days)"}, "Days forward to check for distance conflicts"),
    ("travel_buffer_days", {"value": 3, "label": "Travel Buffer (days)"}, "Minimum days between two non-co-located travel events"),
    ("colocation_radius_miles", {"value": 10, "label": "Co-location Radius (miles)"}, "Two locations within this radius are co-located"),
    ("performer_ceiling", {"value": 5, "label": "Performer Ceiling"}, "Confirmed performer count that maps to 100% on Performer Lineup"),
]

# Default scoring dimension weights
DEFAULT_SCORING_WEIGHTS = [
    ("weight_venue_quality", {"value": 20, "label": "Venue Quality"}, "Weight for Venue Quality dimension"),
    ("weight_organizer_reputation", {"value": 20, "label": "Organizer Reputation"}, "Weight for Organizer Reputation dimension"),
    ("weight_performer_lineup", {"value": 20, "label": "Performer Lineup"}, "Weight for Performer Lineup dimension"),
    ("weight_logistics_ease", {"value": 20, "label": "Logistics Ease"}, "Weight for Logistics Ease dimension"),
    ("weight_readiness", {"value": 20, "label": "Readiness"}, "Weight for Readiness dimension"),
]


def _seed_category(bind, configurations_table, teams_table, category, defaults):
    """Seed a category of defaults for all existing teams."""
    result = bind.execute(sa.select(teams_table.c.id))
    team_ids = [row[0] for row in result]

    if not team_ids:
        return

    for team_id in team_ids:
        for key, value_json, description in defaults:
            existing = bind.execute(
                sa.select(configurations_table.c.id).where(
                    sa.and_(
                        configurations_table.c.team_id == team_id,
                        configurations_table.c.category == category,
                        configurations_table.c.key == key,
                    )
                )
            ).first()

            if not existing:
                bind.execute(
                    configurations_table.insert().values(
                        team_id=team_id,
                        category=category,
                        key=key,
                        value_json=value_json,
                        description=description,
                        source='database',
                        created_at=sa.func.now(),
                        updated_at=sa.func.now(),
                    )
                )


def upgrade() -> None:
    """Seed default conflict rules and scoring weights for existing teams."""
    bind = op.get_bind()

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

    _seed_category(bind, configurations_table, teams_table, "conflict_rules", DEFAULT_CONFLICT_RULES)
    _seed_category(bind, configurations_table, teams_table, "scoring_weights", DEFAULT_SCORING_WEIGHTS)


def downgrade() -> None:
    """Remove only seeded conflict rules and scoring weights (not user edits)."""
    bind = op.get_bind()

    configurations_table = table(
        'configurations',
        column('category', sa.String),
        column('key', sa.String),
        column('source', sa.String),
    )

    # Only delete rows that were seeded by this migration (source='database' and matching keys)
    seeded_conflict_keys = [key for key, _, _ in DEFAULT_CONFLICT_RULES]
    seeded_scoring_keys = [key for key, _, _ in DEFAULT_SCORING_WEIGHTS]

    bind.execute(
        configurations_table.delete().where(
            sa.and_(
                configurations_table.c.category.in_(["conflict_rules", "scoring_weights"]),
                configurations_table.c.source == 'database',
                configurations_table.c.key.in_(seeded_conflict_keys + seeded_scoring_keys),
            )
        )
    )
