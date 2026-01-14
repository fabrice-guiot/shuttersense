"""
EventSeries model for multi-day event groupings.

EventSeries groups related events spanning multiple days. When a user selects
a date range for an event, individual Event records are created for each day,
all linked to the same EventSeries.

Design Rationale:
- Stores shared properties that apply to all events in the series
- Events can override series properties (title, location, etc.) if needed
- total_events tracks the number of events in the series for "x/n" display
- Deleting a series cascades to delete all associated events
"""

from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Time, Text,
    ForeignKey
)
from sqlalchemy.orm import relationship

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin


class EventSeries(Base, GuidMixin):
    """
    Multi-day event series model.

    Groups related events spanning multiple days with shared properties.
    Individual events inherit properties from the series unless overridden.

    Attributes:
        id: Primary key (internal, never exposed)
        uuid: UUIDv7 for external identification (inherited from GuidMixin)
        guid: GUID string property (ser_xxx, inherited from GuidMixin)
        title: Series title (shared by all events)
        description: Series description
        category_id: Category for all events in series
        location_id: Default location (events can override)
        organizer_id: Default organizer (events can override)
        input_timezone: Timezone for time input display
        ticket_required: Default ticket requirement
        timeoff_required: Default time-off requirement
        travel_required: Default travel requirement
        deadline_date: Series-level deadline date for deliverables
        deadline_time: Optional deadline time (e.g., 11:59 PM for competitions)
        total_events: Number of events in series
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Relationships:
        category: Parent category (many-to-one, RESTRICT on delete)
        location: Default location (many-to-one, SET NULL on delete)
        organizer: Default organizer (many-to-one, SET NULL on delete)
        events: Events in this series (one-to-many, CASCADE on delete)

    Constraints:
        - category_id is required
        - total_events must be >= 2 (otherwise not a series)
        - Location category must match series category
        - Organizer category must match series category

    Indexes:
        - uuid (unique, for GUID lookups)
        - category_id (for filtering by category)
    """

    __tablename__ = "event_series"

    # GUID prefix for EventSeries entities
    GUID_PREFIX = "ser"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    location_id = Column(
        Integer,
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    organizer_id = Column(
        Integer,
        ForeignKey("organizers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Core fields
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Timezone for input display
    input_timezone = Column(String(64), nullable=True)

    # Logistics defaults (inherited by events unless overridden)
    ticket_required = Column(Boolean, default=False, nullable=False)
    timeoff_required = Column(Boolean, default=False, nullable=False)
    travel_required = Column(Boolean, default=False, nullable=False)

    # Deadline for deliverables (triggers creation of deadline entry event)
    deadline_date = Column(Date, nullable=True)
    deadline_time = Column(Time, nullable=True)

    # Series metadata
    total_events = Column(Integer, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    category = relationship("Category", back_populates="event_series")
    location = relationship("Location", back_populates="event_series")
    organizer = relationship("Organizer", back_populates="event_series")
    events = relationship(
        "Event",
        back_populates="series",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<EventSeries("
            f"id={self.id}, "
            f"title='{self.title}', "
            f"total_events={self.total_events}"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.title} ({self.total_events} days)"
