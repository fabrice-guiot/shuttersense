"""
Pydantic schemas for event API request/response validation.

Provides data validation and serialization for:
- Event creation requests (single and series)
- Event update requests (with scope for series)
- Event API responses (list and detail)
- Event statistics

Design:
- Events can be standalone or part of a series
- Series events inherit properties from EventSeries
- Response schemas include computed fields (effective_title, series_indicator)
- GUIDs are exposed via guid property, never internal IDs
"""

import enum
from datetime import datetime, date, time
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, field_serializer


# ============================================================================
# Enums
# ============================================================================


class EventStatus(str, enum.Enum):
    """Event status enumeration."""
    FUTURE = "future"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AttendanceStatus(str, enum.Enum):
    """Attendance status with associated colors."""
    PLANNED = "planned"    # Yellow
    ATTENDED = "attended"  # Green
    SKIPPED = "skipped"    # Red


class TicketStatus(str, enum.Enum):
    """Ticket procurement status."""
    NOT_PURCHASED = "not_purchased"  # Red
    PURCHASED = "purchased"          # Yellow
    READY = "ready"                  # Green


class TimeoffStatus(str, enum.Enum):
    """Time-off booking status."""
    PLANNED = "planned"    # Red
    BOOKED = "booked"      # Yellow
    APPROVED = "approved"  # Green


class TravelStatus(str, enum.Enum):
    """Travel booking status."""
    PLANNED = "planned"  # Red
    BOOKED = "booked"    # Green


class UpdateScope(str, enum.Enum):
    """Scope for update/delete operations on series events."""
    SINGLE = "single"          # Only this event
    THIS_AND_FUTURE = "this_and_future"  # This and all future events
    ALL = "all"                # All events in series


# ============================================================================
# Request Schemas
# ============================================================================


class EventCreate(BaseModel):
    """
    Schema for creating a new standalone event.

    Required:
        title: Event title
        category_guid: Category GUID
        event_date: Date of the event

    Optional:
        description: Event description
        location_guid: Location GUID
        organizer_guid: Organizer GUID
        start_time: Start time (HH:MM format)
        end_time: End time (HH:MM format)
        is_all_day: Whether event spans full day
        input_timezone: IANA timezone for display
        status: Event status (default: future)
        attendance: Attendance status (default: planned)
        ticket_required: Whether ticket is needed
        timeoff_required: Whether time-off is needed
        travel_required: Whether travel is needed
        deadline_date: Workflow completion deadline
    """

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    category_guid: str = Field(..., description="Category GUID (cat_xxx)")
    event_date: date = Field(..., description="Date of the event")

    location_guid: Optional[str] = Field(default=None, description="Location GUID")
    organizer_guid: Optional[str] = Field(default=None, description="Organizer GUID")

    start_time: Optional[time] = Field(default=None, description="Start time")
    end_time: Optional[time] = Field(default=None, description="End time")
    is_all_day: bool = Field(default=False)
    input_timezone: Optional[str] = Field(default=None, max_length=64)

    status: EventStatus = Field(default=EventStatus.FUTURE)
    attendance: AttendanceStatus = Field(default=AttendanceStatus.PLANNED)

    ticket_required: Optional[bool] = Field(default=None)
    timeoff_required: Optional[bool] = Field(default=None)
    travel_required: Optional[bool] = Field(default=None)
    deadline_date: Optional[date] = Field(default=None)
    deadline_time: Optional[time] = Field(default=None)

    @field_validator("title")
    @classmethod
    def validate_title_not_whitespace(cls, v: str) -> str:
        """Ensure title is not just whitespace."""
        if not v.strip():
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Airshow Day 1",
                "category_guid": "cat_01hgw2bbg0000000000000001",
                "event_date": "2026-03-15",
                "start_time": "09:00",
                "end_time": "17:00",
                "status": "future",
                "attendance": "planned",
            }
        }
    }


class EventSeriesCreate(BaseModel):
    """
    Schema for creating a multi-day event series.

    Creates an EventSeries and individual Event records for each date.

    Required:
        title: Series title (shared by all events)
        category_guid: Category GUID
        event_dates: List of dates (2+ dates required)

    Optional:
        description: Series description
        location_guid: Default location GUID
        organizer_guid: Default organizer GUID
        start_time: Default start time
        end_time: Default end time
        is_all_day: Whether events span full day
        input_timezone: IANA timezone for display
        ticket_required: Default ticket requirement
        timeoff_required: Default time-off requirement
        travel_required: Default travel requirement
        deadline_date: Series-level deadline date for deliverables
        deadline_time: Optional deadline time (e.g., 11:59 PM for competitions)
    """

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    category_guid: str = Field(..., description="Category GUID")
    event_dates: List[date] = Field(
        ...,
        min_length=2,
        description="List of dates for the series (minimum 2)"
    )

    location_guid: Optional[str] = Field(default=None)
    organizer_guid: Optional[str] = Field(default=None)

    start_time: Optional[time] = Field(default=None)
    end_time: Optional[time] = Field(default=None)
    is_all_day: bool = Field(default=False)
    input_timezone: Optional[str] = Field(default=None, max_length=64)

    ticket_required: bool = Field(default=False)
    timeoff_required: bool = Field(default=False)
    travel_required: bool = Field(default=False)

    # Deadline for deliverables (creates a deadline entry in the calendar)
    deadline_date: Optional[date] = Field(
        default=None,
        description="Deadline date for deliverables (e.g., client delivery date)"
    )
    deadline_time: Optional[time] = Field(
        default=None,
        description="Optional deadline time (e.g., competition cutoff time)"
    )

    # Initial status/attendance for all events in series
    status: EventStatus = Field(default=EventStatus.FUTURE)
    attendance: AttendanceStatus = Field(default=AttendanceStatus.PLANNED)

    @field_validator("title")
    @classmethod
    def validate_title_not_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip()

    @field_validator("event_dates")
    @classmethod
    def validate_dates_sorted(cls, v: List[date]) -> List[date]:
        """Ensure dates are sorted chronologically."""
        return sorted(v)

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Oshkosh Airshow 2026",
                "category_guid": "cat_01hgw2bbg0000000000000001",
                "event_dates": ["2026-07-27", "2026-07-28", "2026-07-29"],
                "start_time": "08:00",
                "end_time": "18:00",
                "ticket_required": True,
                "travel_required": True,
            }
        }
    }


class EventUpdate(BaseModel):
    """
    Schema for updating an existing event.

    All fields are optional - only provided fields will be updated.
    For series events, use `scope` to specify update behavior.

    Fields:
        title: New event title
        description: New description
        category_guid: New category GUID
        location_guid: New location GUID
        organizer_guid: New organizer GUID
        event_date: New event date
        start_time: New start time
        end_time: New end time
        is_all_day: New all-day flag
        input_timezone: New timezone
        status: New event status
        attendance: New attendance status
        ticket_required: New ticket requirement
        ticket_status: New ticket status
        ticket_purchase_date: New ticket purchase date
        timeoff_required: New time-off requirement
        timeoff_status: New time-off status
        timeoff_booking_date: New time-off booking date
        travel_required: New travel requirement
        travel_status: New travel status
        travel_booking_date: New travel booking date
        deadline_date: New deadline date
        scope: Update scope for series events (default: single)
    """

    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None)
    category_guid: Optional[str] = Field(default=None)
    location_guid: Optional[str] = Field(default=None)
    organizer_guid: Optional[str] = Field(default=None)

    event_date: Optional[date] = Field(default=None)
    start_time: Optional[time] = Field(default=None)
    end_time: Optional[time] = Field(default=None)
    is_all_day: Optional[bool] = Field(default=None)
    input_timezone: Optional[str] = Field(default=None, max_length=64)

    status: Optional[EventStatus] = Field(default=None)
    attendance: Optional[AttendanceStatus] = Field(default=None)

    ticket_required: Optional[bool] = Field(default=None)
    ticket_status: Optional[TicketStatus] = Field(default=None)
    ticket_purchase_date: Optional[date] = Field(default=None)

    timeoff_required: Optional[bool] = Field(default=None)
    timeoff_status: Optional[TimeoffStatus] = Field(default=None)
    timeoff_booking_date: Optional[date] = Field(default=None)

    travel_required: Optional[bool] = Field(default=None)
    travel_status: Optional[TravelStatus] = Field(default=None)
    travel_booking_date: Optional[date] = Field(default=None)

    deadline_date: Optional[date] = Field(default=None)
    deadline_time: Optional[time] = Field(default=None)

    scope: UpdateScope = Field(default=UpdateScope.SINGLE)

    @field_validator("title")
    @classmethod
    def validate_title_not_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip() if v else None

    model_config = {
        "json_schema_extra": {
            "example": {
                "attendance": "attended",
                "ticket_status": "ready",
            }
        }
    }


class EventSeriesUpdate(BaseModel):
    """
    Schema for updating an existing event series.

    Updates series-level properties. Changes to deadline_date/deadline_time
    will automatically sync the deadline calendar entry.

    All fields are optional - only provided fields will be updated.
    """

    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None)
    category_guid: Optional[str] = Field(default=None)
    location_guid: Optional[str] = Field(default=None)
    organizer_guid: Optional[str] = Field(default=None)
    input_timezone: Optional[str] = Field(default=None, max_length=64)

    ticket_required: Optional[bool] = Field(default=None)
    timeoff_required: Optional[bool] = Field(default=None)
    travel_required: Optional[bool] = Field(default=None)

    # Deadline for deliverables (changes will sync the deadline entry)
    deadline_date: Optional[date] = Field(
        default=None,
        description="Deadline date for deliverables"
    )
    deadline_time: Optional[time] = Field(
        default=None,
        description="Optional deadline time"
    )

    @field_validator("title")
    @classmethod
    def validate_title_not_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip() if v else None

    model_config = {
        "json_schema_extra": {
            "example": {
                "deadline_date": "2026-08-15",
                "deadline_time": "23:59",
            }
        }
    }


# ============================================================================
# Response Schemas
# ============================================================================


class EventSeriesSummary(BaseModel):
    """Summary of event series for inclusion in event responses."""

    guid: str = Field(..., description="Series GUID (ser_xxx)")
    title: str
    total_events: int

    model_config = {"from_attributes": True}


class CategorySummary(BaseModel):
    """Summary of category for inclusion in event responses."""

    guid: str = Field(..., description="Category GUID (cat_xxx)")
    name: str
    icon: Optional[str]
    color: Optional[str]

    model_config = {"from_attributes": True}


class LocationSummary(BaseModel):
    """Summary of location for inclusion in event responses."""

    guid: str = Field(..., description="Location GUID (loc_xxx)")
    name: str
    city: Optional[str]
    country: Optional[str]
    timezone: Optional[str]

    model_config = {"from_attributes": True}


class EventResponse(BaseModel):
    """
    Schema for event API responses (list view).

    Includes core event fields and computed properties.
    Use EventDetailResponse for full event details.
    """

    guid: str = Field(..., description="Event GUID (evt_xxx)")

    # Computed/effective fields
    title: str = Field(..., description="Effective title (own or from series)")

    # Date/time
    event_date: date
    start_time: Optional[time]
    end_time: Optional[time]
    is_all_day: bool
    input_timezone: Optional[str]

    # Status
    status: EventStatus
    attendance: AttendanceStatus

    # Category (always included for display)
    category: Optional[CategorySummary]

    # Location (included for calendar/list display)
    location: Optional[LocationSummary]

    # Series info (for "x/n" display)
    series_guid: Optional[str] = Field(default=None, description="Series GUID if part of series")
    sequence_number: Optional[int] = Field(default=None)
    series_total: Optional[int] = Field(default=None)

    # Logistics summary (for card display indicators)
    ticket_required: Optional[bool] = Field(default=None)
    ticket_status: Optional[TicketStatus] = Field(default=None)
    timeoff_required: Optional[bool] = Field(default=None)
    timeoff_status: Optional[TimeoffStatus] = Field(default=None)
    travel_required: Optional[bool] = Field(default=None)
    travel_status: Optional[TravelStatus] = Field(default=None)

    # Deadline entry flag (True = this event represents a series deadline)
    is_deadline: bool = Field(default=False, description="True if this is a deadline entry")

    # Timestamps
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    @classmethod
    def serialize_datetime_utc(cls, v: datetime) -> str:
        """Serialize datetime as ISO 8601 with explicit UTC timezone."""
        return v.isoformat() + "Z" if v else None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "guid": "evt_01hgw2bbg0000000000000001",
                "title": "Oshkosh Airshow 2026",
                "event_date": "2026-07-27",
                "start_time": "08:00:00",
                "end_time": "18:00:00",
                "is_all_day": False,
                "status": "future",
                "attendance": "planned",
                "category": {
                    "guid": "cat_01hgw2bbg0000000000000001",
                    "name": "Airshow",
                    "icon": "plane",
                    "color": "#3B82F6",
                },
                "series_guid": "ser_01hgw2bbg0000000000000001",
                "sequence_number": 1,
                "series_total": 3,
                "is_deadline": False,
                "created_at": "2026-01-10T10:00:00Z",
                "updated_at": "2026-01-10T10:00:00Z",
            }
        },
    }


class OrganizerSummary(BaseModel):
    """Summary of organizer for inclusion in event detail responses."""

    guid: str
    name: str

    model_config = {"from_attributes": True}


class PerformerStatusType(str, enum.Enum):
    """Performer status at an event."""
    ANNOUNCED = "announced"   # Default - performer announced but not yet confirmed
    CONFIRMED = "confirmed"   # Performer attendance confirmed
    CANCELLED = "cancelled"   # Performer cancelled


class PerformerSummary(BaseModel):
    """Summary of performer for inclusion in event detail responses."""

    guid: str
    name: str
    instagram_handle: Optional[str] = None
    status: PerformerStatusType

    model_config = {"from_attributes": True}


class EventDetailResponse(EventResponse):
    """
    Schema for event API detail responses.

    Extends EventResponse with full event details including:
    - Description
    - Organizer, performers
    - All logistics fields
    - Soft delete status

    Note: Location is inherited from EventResponse (included in list views).
    """

    description: Optional[str]

    # Related entities (location inherited from EventResponse)
    organizer: Optional[OrganizerSummary]
    performers: List[PerformerSummary] = Field(default_factory=list)

    # Series details (if part of series)
    series: Optional[EventSeriesSummary]

    # Logistics
    ticket_required: Optional[bool]
    ticket_status: Optional[TicketStatus]
    ticket_purchase_date: Optional[date]

    timeoff_required: Optional[bool]
    timeoff_status: Optional[TimeoffStatus]
    timeoff_booking_date: Optional[date]

    travel_required: Optional[bool]
    travel_status: Optional[TravelStatus]
    travel_booking_date: Optional[date]

    deadline_date: Optional[date]
    deadline_time: Optional[time]

    # Soft delete
    deleted_at: Optional[datetime]

    @field_serializer("deleted_at")
    @classmethod
    def serialize_deleted_at_utc(cls, v: Optional[datetime]) -> Optional[str]:
        """Serialize deleted_at as ISO 8601 with explicit UTC timezone."""
        return v.isoformat() + "Z" if v else None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "guid": "evt_01hgw2bbg0000000000000001",
                "title": "Oshkosh Airshow 2026",
                "description": "Annual EAA AirVenture",
                "event_date": "2026-07-27",
                "start_time": "08:00:00",
                "end_time": "18:00:00",
                "is_all_day": False,
                "status": "future",
                "attendance": "planned",
                "category": {
                    "guid": "cat_01hgw2bbg0000000000000001",
                    "name": "Airshow",
                    "icon": "plane",
                    "color": "#3B82F6",
                },
                "location": {
                    "guid": "loc_01hgw2bbg0000000000000001",
                    "name": "Wittman Regional Airport",
                    "city": "Oshkosh",
                    "country": "USA",
                    "timezone": "America/Chicago",
                },
                "ticket_required": True,
                "ticket_status": "purchased",
                "travel_required": True,
                "travel_status": "booked",
                "created_at": "2026-01-10T10:00:00Z",
                "updated_at": "2026-01-10T10:00:00Z",
            }
        },
    }


class EventStatsResponse(BaseModel):
    """
    Schema for event statistics response.

    Provides aggregated statistics for dashboard KPIs.
    """

    total_count: int = Field(..., ge=0, description="Total number of events")
    upcoming_count: int = Field(..., ge=0, description="Events in the future")
    this_month_count: int = Field(..., ge=0, description="Events this month")
    attended_count: int = Field(..., ge=0, description="Events marked as attended")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_count": 42,
                "upcoming_count": 15,
                "this_month_count": 3,
                "attended_count": 27,
            }
        }
    }


# ============================================================================
# Query Parameters
# ============================================================================


class EventListParams(BaseModel):
    """Query parameters for listing events."""

    start_date: Optional[date] = Field(default=None, description="Start of date range")
    end_date: Optional[date] = Field(default=None, description="End of date range")
    category_guid: Optional[str] = Field(default=None, description="Filter by category")
    status: Optional[EventStatus] = Field(default=None, description="Filter by status")
    attendance: Optional[AttendanceStatus] = Field(default=None, description="Filter by attendance")
    include_deleted: bool = Field(default=False, description="Include soft-deleted events")

    model_config = {
        "json_schema_extra": {
            "example": {
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "category_guid": "cat_01hgw2bbg0000000000000001",
            }
        }
    }
