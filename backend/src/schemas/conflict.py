"""
Pydantic schemas for conflict detection, event scoring, and resolution.

Matches the OpenAPI contract at contracts/conflict-api.yaml.

Provides data validation and serialization for:
- Conflict detection (groups, edges, summaries)
- Event quality scoring (5 dimensions + composite)
- Conflict resolution (batch attendance updates)
- Configuration (conflict rules, scoring weights)
"""

import enum
from datetime import date
from typing import Optional, List

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================


class ConflictType(str, enum.Enum):
    """Type of conflict between two events."""
    TIME_OVERLAP = "time_overlap"
    DISTANCE = "distance"
    TRAVEL_BUFFER = "travel_buffer"


class ConflictGroupStatus(str, enum.Enum):
    """Resolution status derived from member events' attendance."""
    UNRESOLVED = "unresolved"
    PARTIALLY_RESOLVED = "partially_resolved"
    RESOLVED = "resolved"


# ============================================================================
# Scoring
# ============================================================================


class EventScores(BaseModel):
    """Five dimension scores and weighted composite for an event."""

    venue_quality: float = Field(..., ge=0, le=100, description="Location rating * 20 (null rating → 50)")
    organizer_reputation: float = Field(..., ge=0, le=100, description="Organizer rating * 20 (null rating → 50)")
    performer_lineup: float = Field(..., ge=0, le=100, description="Confirmed performers / ceiling * 100")
    logistics_ease: float = Field(..., ge=0, le=100, description="Each not-required logistics item → +33.3")
    readiness: float = Field(..., ge=0, le=100, description="Each resolved required item → proportional share of 100")
    composite: float = Field(..., ge=0, le=100, description="Weighted average of all dimension scores")


class EventScoreResponse(BaseModel):
    """Response for GET /events/{guid}/score."""

    guid: str
    title: str
    event_date: date
    scores: EventScores


# ============================================================================
# Conflict Groups
# ============================================================================


class CategoryInfo(BaseModel):
    """Category info embedded in scored event."""
    guid: str
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None


class LocationInfo(BaseModel):
    """Location info embedded in scored event."""
    guid: str
    name: str
    city: Optional[str] = None
    country: Optional[str] = None


class OrganizerInfo(BaseModel):
    """Organizer info embedded in scored event."""
    guid: str
    name: str


class ScoredEvent(BaseModel):
    """An event within a conflict group, including quality scores."""

    guid: str
    title: str
    event_date: date
    start_time: Optional[str] = Field(default=None, description="HH:MM or HH:MM:SS format (24-hour)")
    end_time: Optional[str] = Field(default=None, description="HH:MM or HH:MM:SS format (24-hour)")
    is_all_day: bool
    category: Optional[CategoryInfo] = None
    location: Optional[LocationInfo] = None
    organizer: Optional[OrganizerInfo] = None
    performer_count: int = Field(..., description="Number of confirmed performers")
    travel_required: Optional[bool] = None
    attendance: str
    scores: EventScores


class ConflictEdge(BaseModel):
    """A pairwise conflict relationship between two events."""

    event_a_guid: str
    event_b_guid: str
    conflict_type: ConflictType
    detail: str = Field(..., description="Human-readable conflict description")


class ConflictGroup(BaseModel):
    """A connected component of conflicting events."""

    group_id: str = Field(..., description="Ephemeral identifier (e.g., cg_1)")
    status: ConflictGroupStatus
    events: List[ScoredEvent]
    edges: List[ConflictEdge]


class ConflictSummary(BaseModel):
    """Aggregate counts of conflict groups by status."""

    total_groups: int
    unresolved: int
    partially_resolved: int
    resolved: int


class ConflictDetectionResponse(BaseModel):
    """Response for GET /events/conflicts."""

    conflict_groups: List[ConflictGroup]
    summary: ConflictSummary


# ============================================================================
# Conflict Resolution
# ============================================================================


class ConflictDecision(BaseModel):
    """A single event's desired attendance status for resolution."""

    event_guid: str
    attendance: str = Field(..., description="Desired attendance: planned or skipped")


class ConflictResolveRequest(BaseModel):
    """Request for POST /events/conflicts/resolve."""

    group_id: str = Field(..., description="Ephemeral group identifier (for tracking)")
    decisions: List[ConflictDecision] = Field(..., min_length=1)


class ConflictResolveResponse(BaseModel):
    """Response for POST /events/conflicts/resolve."""

    success: bool
    updated_count: int = Field(..., description="Number of events whose attendance was updated")
    message: Optional[str] = None


# ============================================================================
# Configuration — Conflict Rules
# ============================================================================


class ConflictRulesResponse(BaseModel):
    """Response for GET /config/conflict_rules."""

    distance_threshold_miles: int = Field(default=50, ge=0)
    consecutive_window_days: int = Field(default=1, ge=0)
    travel_buffer_days: int = Field(default=3, ge=0)
    colocation_radius_miles: int = Field(default=10, ge=0)
    performer_ceiling: int = Field(default=5, ge=1)


class ConflictRulesUpdateRequest(BaseModel):
    """Request for PUT /config/conflict_rules (partial update)."""

    distance_threshold_miles: Optional[int] = Field(default=None, ge=0)
    consecutive_window_days: Optional[int] = Field(default=None, ge=0)
    travel_buffer_days: Optional[int] = Field(default=None, ge=0)
    colocation_radius_miles: Optional[int] = Field(default=None, ge=0)
    performer_ceiling: Optional[int] = Field(default=None, ge=1)


# ============================================================================
# Configuration — Scoring Weights
# ============================================================================


class ScoringWeightsResponse(BaseModel):
    """Response for GET /config/scoring_weights."""

    weight_venue_quality: int = Field(default=20, ge=0, le=100)
    weight_organizer_reputation: int = Field(default=20, ge=0, le=100)
    weight_performer_lineup: int = Field(default=20, ge=0, le=100)
    weight_logistics_ease: int = Field(default=20, ge=0, le=100)
    weight_readiness: int = Field(default=20, ge=0, le=100)


class ScoringWeightsUpdateRequest(BaseModel):
    """Request for PUT /config/scoring_weights (partial update)."""

    weight_venue_quality: Optional[int] = Field(default=None, ge=0, le=100)
    weight_organizer_reputation: Optional[int] = Field(default=None, ge=0, le=100)
    weight_performer_lineup: Optional[int] = Field(default=None, ge=0, le=100)
    weight_logistics_ease: Optional[int] = Field(default=None, ge=0, le=100)
    weight_readiness: Optional[int] = Field(default=None, ge=0, le=100)
