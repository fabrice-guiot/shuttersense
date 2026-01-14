"""Add deadline_time to events table

Revision ID: 023_add_deadline_time_to_events
Revises: 022_add_is_deadline_to_events
Create Date: 2026-01-14

Adds deadline_time field to events table. For series events, deadline_time
is synced across all events from the series-level deadline_time, allowing
the form to correctly load the deadline time when reopening an event.

Issue #68 - Make Event Deadline appear in the Calendar view
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '023_deadline_time_events'
down_revision = '022_is_deadline_events'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add deadline_time column to events table.

    Column spec:
    - deadline_time: Time, nullable
    - Stores the time component of the deadline for series events
    - Synced from EventSeries.deadline_time to all events in the series
    """
    op.add_column(
        'events',
        sa.Column('deadline_time', sa.Time(), nullable=True)
    )


def downgrade() -> None:
    """Remove deadline_time column from events table."""
    op.drop_column('events', 'deadline_time')
