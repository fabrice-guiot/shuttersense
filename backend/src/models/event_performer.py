"""
EventPerformer model for event-performer associations.

Junction table linking performers to events with attendance status.
Allows tracking which performers are scheduled for which events and
their confirmation/cancellation status.

Design Rationale:
- Many-to-many relationship between events and performers
- Status tracks whether performer is confirmed or cancelled
- Unique constraint prevents duplicate assignments
- CASCADE on event delete, RESTRICT on performer delete
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, DateTime,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship

from backend.src.models import Base


class PerformerStatus(enum.Enum):
    """Performer attendance status at an event."""
    ANNOUNCED = "announced"   # Default - performer announced but not yet confirmed
    CONFIRMED = "confirmed"   # Performer attendance confirmed
    CANCELLED = "cancelled"   # Performer cancelled


class EventPerformer(Base):
    """
    Event-Performer junction model.

    Links performers to events with attendance status tracking.
    Note: This is a junction table without its own GUID.

    Attributes:
        id: Primary key
        event_id: FK to events (CASCADE on delete)
        performer_id: FK to performers (RESTRICT on delete)
        status: Performer status (confirmed, cancelled)
        created_at: When performer was added to event

    Relationships:
        event: Parent event (many-to-one, CASCADE on delete)
        performer: Associated performer (many-to-one, RESTRICT on delete)

    Constraints:
        - Unique (event_id, performer_id) - performer can only be added once per event
        - Performer category must match event category (validated in service)

    Indexes:
        - event_id (for listing performers at an event)
        - performer_id (for listing events with a performer)
    """

    __tablename__ = "event_performers"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    performer_id = Column(
        Integer,
        ForeignKey("performers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Status
    status = Column(String(50), default="announced", nullable=False)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    event = relationship("Event", back_populates="event_performers")
    performer = relationship("Performer", back_populates="event_performers")

    # Table-level constraints
    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "performer_id",
            name="uq_event_performer"
        ),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<EventPerformer("
            f"event_id={self.event_id}, "
            f"performer_id={self.performer_id}, "
            f"status={self.status}"
            f")>"
        )
