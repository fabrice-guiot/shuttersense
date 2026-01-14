"""
Event model for calendar events.

Events represent individual calendar entries. They can be standalone or part
of an EventSeries. Events support soft delete and extensive logistics tracking.

Design Rationale:
- Standalone events have required title/category; series events can inherit
- Soft delete via deleted_at preserves event history
- Nullable logistics fields allow inheritance from series/organizer/location
- Status and attendance enable workflow and visual tracking
- Times stored with input_timezone for proper display
"""

import enum
from datetime import datetime, date, time
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Date, Time, Text,
    ForeignKey, Index
)
from sqlalchemy.orm import relationship

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin


class EventStatus(enum.Enum):
    """Event status enumeration (configurable via Settings)."""
    FUTURE = "future"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AttendanceStatus(enum.Enum):
    """Attendance status with associated colors."""
    PLANNED = "planned"    # Yellow
    ATTENDED = "attended"  # Green
    SKIPPED = "skipped"    # Red


class TicketStatus(enum.Enum):
    """Ticket procurement status."""
    NOT_PURCHASED = "not_purchased"  # Red
    PURCHASED = "purchased"          # Yellow
    READY = "ready"                  # Green


class TimeoffStatus(enum.Enum):
    """Time-off booking status."""
    PLANNED = "planned"    # Red
    BOOKED = "booked"      # Yellow
    APPROVED = "approved"  # Green


class TravelStatus(enum.Enum):
    """Travel booking status."""
    PLANNED = "planned"  # Red
    BOOKED = "booked"    # Green


class Event(Base, GuidMixin):
    """
    Calendar event model.

    Represents an individual calendar event, either standalone or part of a series.
    Supports soft delete, timezone handling, and logistics tracking.

    Attributes:
        id: Primary key (internal, never exposed)
        uuid: UUIDv7 for external identification (inherited from GuidMixin)
        guid: GUID string property (evt_xxx, inherited from GuidMixin)

        Series Fields:
            series_id: FK to EventSeries (NULL for standalone events)
            sequence_number: Position in series (1, 2, 3...)

        Core Fields:
            title: Event title (NULL = inherit from series)
            description: Event description
            category_id: FK to Category (NULL = inherit from series)
            location_id: FK to Location
            organizer_id: FK to Organizer

        Time Fields:
            event_date: Date of the event
            start_time: Start time (NULL for all-day)
            end_time: End time (NULL for all-day)
            is_all_day: Whether event spans full day
            input_timezone: IANA timezone for input/display

        Status Fields:
            status: Event status (future, confirmed, completed, cancelled)
            attendance: Attendance status (planned, attended, skipped)

        Logistics Fields:
            ticket_required: Whether ticket is needed
            ticket_status: Ticket procurement status
            ticket_purchase_date: Date ticket was purchased
            timeoff_required: Whether time-off is needed
            timeoff_status: Time-off booking status
            timeoff_booking_date: Date time-off was booked
            travel_required: Whether travel is needed
            travel_status: Travel booking status
            travel_booking_date: Date travel was booked
            deadline_date: Workflow completion deadline
            deadline_time: Workflow completion deadline time (synced from series)
            is_deadline: True if this event is a deadline entry
            parent_event_id: FK to parent Event (for standalone event deadline entries)

        Soft Delete:
            deleted_at: Soft delete timestamp (NULL = not deleted)

        Timestamps:
            created_at: Creation timestamp
            updated_at: Last update timestamp

    Relationships:
        series: Parent EventSeries (many-to-one, CASCADE on delete)
        category: Event category (many-to-one, RESTRICT on delete)
        location: Event location (many-to-one, SET NULL on delete)
        organizer: Event organizer (many-to-one, SET NULL on delete)
        event_performers: Junction to performers (one-to-many, CASCADE on delete)

    Computed Properties:
        effective_title: Returns title or falls back to series.title
        effective_description: Returns description or falls back to series.description
        effective_category_id: Returns category_id or falls back to series.category_id
        series_indicator: Returns "x/n" notation or None for standalone

    Indexes:
        - uuid (unique, for GUID lookups)
        - event_date (for calendar queries)
        - event_date, deleted_at (for date range queries)
        - series_id (for series queries)
        - category_id (for category filtering)
    """

    __tablename__ = "events"

    # GUID prefix for Event entities
    GUID_PREFIX = "evt"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Series relationship
    series_id = Column(
        Integer,
        ForeignKey("event_series.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    sequence_number = Column(Integer, nullable=True)

    # Core foreign keys
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=True,  # Can be NULL for series events (inherit from series)
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
    title = Column(String(255), nullable=True)  # NULL = inherit from series
    description = Column(Text, nullable=True)

    # Time fields
    event_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    is_all_day = Column(Boolean, default=False, nullable=False)
    input_timezone = Column(String(64), nullable=True)

    # Status fields
    status = Column(String(50), default="future", nullable=False)
    attendance = Column(String(50), default="planned", nullable=False)

    # Ticket logistics
    ticket_required = Column(Boolean, nullable=True)  # NULL = inherit
    ticket_status = Column(String(50), nullable=True)
    ticket_purchase_date = Column(Date, nullable=True)

    # Time-off logistics
    timeoff_required = Column(Boolean, nullable=True)  # NULL = inherit
    timeoff_status = Column(String(50), nullable=True)
    timeoff_booking_date = Column(Date, nullable=True)

    # Travel logistics
    travel_required = Column(Boolean, nullable=True)  # NULL = inherit
    travel_status = Column(String(50), nullable=True)
    travel_booking_date = Column(Date, nullable=True)

    # Workflow
    deadline_date = Column(Date, nullable=True)
    deadline_time = Column(Time, nullable=True)

    # Deadline entry flag (True = this event represents a series/event deadline)
    # Deadline entries are protected from direct modification
    is_deadline = Column(Boolean, default=False, nullable=False)

    # Parent event (for standalone event deadline entries)
    # Links deadline entry to standalone event (series events use series_id instead)
    parent_event_id = Column(
        Integer,
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Soft delete
    deleted_at = Column(DateTime, nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    series = relationship("EventSeries", back_populates="events")
    category = relationship("Category", back_populates="events")
    location = relationship("Location", back_populates="events")
    organizer = relationship("Organizer", back_populates="events")
    event_performers = relationship(
        "EventPerformer",
        back_populates="event",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    # Self-referential relationship for standalone event deadline entries
    parent_event = relationship(
        "Event",
        remote_side=[id],
        foreign_keys=[parent_event_id],
        backref="deadline_entry"
    )

    # Table-level indexes
    __table_args__ = (
        Index(
            "idx_events_date_not_deleted",
            "event_date",
            postgresql_where=(deleted_at.is_(None))
        ),
        Index(
            "idx_events_date_deleted",
            "event_date",
            "deleted_at",
        ),
        Index(
            "idx_events_category_not_deleted",
            "category_id",
            postgresql_where=(deleted_at.is_(None))
        ),
    )

    @property
    def effective_title(self) -> str:
        """Get title, falling back to series title if part of a series."""
        if self.title:
            return self.title
        if self.series:
            return self.series.title
        return ""

    @property
    def effective_description(self) -> Optional[str]:
        """Get description, falling back to series description if part of a series."""
        if self.description:
            return self.description
        if self.series:
            return self.series.description
        return None

    @property
    def effective_category_id(self) -> Optional[int]:
        """Get category_id, falling back to series category if part of a series."""
        if self.category_id:
            return self.category_id
        if self.series:
            return self.series.category_id
        return None

    @property
    def series_indicator(self) -> Optional[str]:
        """Get 'x/n' notation for series events, None for standalone."""
        if self.series and self.sequence_number:
            return f"{self.sequence_number}/{self.series.total_events}"
        return None

    @property
    def is_deleted(self) -> bool:
        """Check if event is soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self) -> None:
        """Mark event as deleted."""
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """Restore a soft-deleted event."""
        self.deleted_at = None

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Event("
            f"id={self.id}, "
            f"title='{self.effective_title}', "
            f"date={self.event_date}, "
            f"status={self.status}"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        indicator = f" [{self.series_indicator}]" if self.series_indicator else ""
        return f"{self.effective_title}{indicator} - {self.event_date}"
