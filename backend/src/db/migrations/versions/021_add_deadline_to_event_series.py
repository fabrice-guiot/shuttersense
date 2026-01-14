"""Add deadline_date and deadline_time to event_series table

Revision ID: 021_add_deadline_to_event_series
Revises: 020_add_instagram_handle
Create Date: 2026-01-14

Adds deadline_date and deadline_time fields to event_series table.
These are Series-level properties that trigger automatic creation
of deadline entries in the events table.

Issue #68 - Make Event Deadline appear in the Calendar view
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '021_deadline_event_series'
down_revision = '020_add_instagram_handle'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add deadline_date and deadline_time columns to event_series table.

    Column specs:
    - deadline_date: Date, nullable, stores the deadline date for deliverables
    - deadline_time: Time, nullable, stores optional deadline time (e.g., 11:59 PM)
    """
    # Add deadline_date column
    op.add_column(
        'event_series',
        sa.Column('deadline_date', sa.Date(), nullable=True)
    )

    # Add deadline_time column
    op.add_column(
        'event_series',
        sa.Column('deadline_time', sa.Time(), nullable=True)
    )


def downgrade() -> None:
    """Remove deadline columns from event_series table."""
    op.drop_column('event_series', 'deadline_time')
    op.drop_column('event_series', 'deadline_date')
