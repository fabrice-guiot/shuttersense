"""Add is_deadline to events table

Revision ID: 022_add_is_deadline_to_events
Revises: 021_add_deadline_to_event_series
Create Date: 2026-01-14

Adds is_deadline boolean field to events table. Events with is_deadline=True
are "deadline entries" - derived events that represent EventSeries deadlines
and are protected from direct modification.

Issue #68 - Make Event Deadline appear in the Calendar view
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '022_is_deadline_events'
down_revision = '021_deadline_event_series'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add is_deadline column to events table.

    Column spec:
    - is_deadline: Boolean, NOT NULL, default False
    - Distinguishes deadline entries from regular events
    - Events with is_deadline=True are protected from direct modification
    """
    # Add is_deadline column with default value
    op.add_column(
        'events',
        sa.Column('is_deadline', sa.Boolean(), nullable=False, server_default='false')
    )

    # Create partial index for quick lookup of deadline entries
    # PostgreSQL-specific: partial index where is_deadline = TRUE
    op.create_index(
        'idx_events_is_deadline',
        'events',
        ['is_deadline'],
        postgresql_where=text('is_deadline = true')
    )


def downgrade() -> None:
    """Remove is_deadline column and index from events table."""
    op.drop_index('idx_events_is_deadline', table_name='events')
    op.drop_column('events', 'is_deadline')
