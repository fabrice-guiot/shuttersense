"""Add parent_event_id to events table

Revision ID: 024_add_parent_event_id_to_events
Revises: 023_add_deadline_time_to_events
Create Date: 2026-01-14

Adds parent_event_id field to events table. This allows deadline entries
to be linked to standalone events (not just series). For series events,
deadline entries use series_id. For standalone events, deadline entries
use parent_event_id.

Issue #68 - Make Event Deadline appear in the Calendar view
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '024_parent_event_id'
down_revision = '023_deadline_time_events'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Add parent_event_id column to events table.

    Column spec:
    - parent_event_id: Integer FK to events.id, nullable
    - Used to link deadline entries to standalone events
    - CASCADE on delete (if parent event is deleted, deadline entry is too)
    """
    op.add_column(
        'events',
        sa.Column(
            'parent_event_id',
            sa.Integer(),
            sa.ForeignKey('events.id', ondelete='CASCADE'),
            nullable=True
        )
    )

    # Create index for efficient lookups
    op.create_index(
        'idx_events_parent_event_id',
        'events',
        ['parent_event_id']
    )


def downgrade() -> None:
    """Remove parent_event_id column and index from events table."""
    op.drop_index('idx_events_parent_event_id', table_name='events')
    op.drop_column('events', 'parent_event_id')
