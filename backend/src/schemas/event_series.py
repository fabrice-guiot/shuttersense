"""
Pydantic schemas for event series API request/response validation.

Provides data validation and serialization for:
- Event series responses
- Event series statistics

Design:
- EventSeries groups related events spanning multiple days
- Events inherit properties from the series unless overridden
- GUIDs are exposed via guid property, never internal IDs
"""

from datetime import datetime, date, time
from typing import Optional, List
from pydantic import BaseModel, Field, field_serializer


# ============================================================================
# Response Schemas
# ============================================================================


class EventSeriesEventSummary(BaseModel):
    """Summary of an event within a series."""

    guid: str = Field(..., description="Event GUID (evt_xxx)")
    event_date: str  # ISO date string
    sequence_number: int
    attendance: str

    model_config = {"from_attributes": True}


class EventSeriesResponse(BaseModel):
    """
    Schema for event series API responses.

    Includes series properties and list of associated events.
    """

    guid: str = Field(..., description="Series GUID (ser_xxx)")
    title: str
    description: Optional[str]

    # Category
    category_guid: str
    category_name: Optional[str]

    # Defaults
    location_guid: Optional[str]
    organizer_guid: Optional[str]
    input_timezone: Optional[str]

    # Logistics defaults
    ticket_required: bool
    timeoff_required: bool
    travel_required: bool

    # Deadline for deliverables
    deadline_date: Optional[date] = Field(
        default=None,
        description="Deadline date for deliverables"
    )
    deadline_time: Optional[time] = Field(
        default=None,
        description="Optional deadline time"
    )
    deadline_entry_guid: Optional[str] = Field(
        default=None,
        description="GUID of the deadline entry event if deadline is set"
    )

    # Series metadata
    total_events: int

    # Events in series
    events: List[EventSeriesEventSummary] = Field(default_factory=list)

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
                "guid": "ser_01hgw2bbg0000000000000001",
                "title": "Oshkosh Airshow 2026",
                "description": "Annual EAA AirVenture",
                "category_guid": "cat_01hgw2bbg0000000000000001",
                "category_name": "Airshow",
                "total_events": 3,
                "ticket_required": True,
                "travel_required": True,
                "timeoff_required": True,
                "deadline_date": "2026-08-15",
                "deadline_time": None,
                "deadline_entry_guid": "evt_01hgw2bbg0000000000000004",
                "events": [
                    {"guid": "evt_xxx1", "event_date": "2026-07-27", "sequence_number": 1, "attendance": "planned"},
                    {"guid": "evt_xxx2", "event_date": "2026-07-28", "sequence_number": 2, "attendance": "planned"},
                    {"guid": "evt_xxx3", "event_date": "2026-07-29", "sequence_number": 3, "attendance": "planned"},
                ],
                "created_at": "2026-01-10T10:00:00Z",
                "updated_at": "2026-01-10T10:00:00Z",
            }
        },
    }


class EventSeriesStatsResponse(BaseModel):
    """
    Schema for event series statistics response.
    """

    total_series: int = Field(..., ge=0, description="Total number of series")
    total_events_in_series: int = Field(..., ge=0, description="Total events across all series")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_series": 5,
                "total_events_in_series": 18,
            }
        }
    }
