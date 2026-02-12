"""Add website and social fields to locations, event_series, and events.

Revision ID: 065_add_website_social
Revises: 064_pipeline_name_team
Create Date: 2026-02-12

Adds:
- locations.website (String 500, nullable) - website URL for locations
- event_series.website (String 500, nullable) - event-specific website
- event_series.instagram_handle (String 100, nullable) - event-specific Instagram
- events.website (String 500, nullable) - synced from series
- events.instagram_handle (String 100, nullable) - synced from series
"""

from alembic import op
import sqlalchemy as sa

revision = '065_add_website_social'
down_revision = '064_pipeline_name_team'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add website and social fields."""
    # Location: add website
    op.add_column('locations', sa.Column('website', sa.String(500), nullable=True))

    # EventSeries: add website and instagram_handle
    op.add_column('event_series', sa.Column('website', sa.String(500), nullable=True))
    op.add_column('event_series', sa.Column('instagram_handle', sa.String(100), nullable=True))

    # Event: add website and instagram_handle (synced from series)
    op.add_column('events', sa.Column('website', sa.String(500), nullable=True))
    op.add_column('events', sa.Column('instagram_handle', sa.String(100), nullable=True))


def downgrade() -> None:
    """Remove website and social fields."""
    op.drop_column('events', 'instagram_handle')
    op.drop_column('events', 'website')
    op.drop_column('event_series', 'instagram_handle')
    op.drop_column('event_series', 'website')
    op.drop_column('locations', 'website')
