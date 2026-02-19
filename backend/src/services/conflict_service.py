"""
Conflict detection and event scoring service.

Provides:
- Three conflict detection types: time overlap, distance, travel buffer
- Five-dimension event quality scoring with configurable weights
- Union-Find grouping for connected conflict components
- Conflict resolution via attendance updates

Design:
- Conflicts are computed at query time (not persisted)
- Configuration stored in existing configurations table
- Scoring dimensions are extensible via (name, scorer_fn, weight_key) tuples
"""

from datetime import date, time
from typing import List, Optional, Dict, Any, Tuple, Callable

from sqlalchemy.orm import Session, joinedload

from backend.src.models import Event, EventPerformer, EventSeries, Configuration, ConfigSource
from backend.src.services.event_service import EventService
from backend.src.services.config_service import ConfigService
from backend.src.services.guid import GuidService
from backend.src.services.geo_utils import haversine_miles
from backend.src.services.exceptions import NotFoundError, ValidationError
from backend.src.schemas.conflict import (
    ConflictType,
    ConflictGroupStatus,
    EventScores,
    ScoredEvent,
    ConflictEdge,
    ConflictGroup,
    ConflictSummary,
    ConflictDetectionResponse,
    EventScoreResponse,
    ConflictRulesResponse,
    ScoringWeightsResponse,
    CategoryInfo,
    LocationInfo,
    OrganizerInfo,
)
from backend.src.utils.logging_config import get_logger


logger = get_logger("services")


# Default conflict rules (used when team config is missing)
DEFAULT_CONFLICT_RULES = {
    "distance_threshold_miles": 150,
    "consecutive_window_days": 1,
    "travel_buffer_days": 3,
    "colocation_radius_miles": 70,
    "performer_ceiling": 5,
}

# Default scoring weights (used when team config is missing)
DEFAULT_SCORING_WEIGHTS = {
    "weight_venue_quality": 20,
    "weight_organizer_reputation": 20,
    "weight_performer_lineup": 20,
    "weight_logistics_ease": 20,
    "weight_readiness": 20,
}


class ConflictService:
    """
    Service for conflict detection and event quality scoring.

    Detects scheduling conflicts between events using three methods:
    - Time overlap (same-day overlapping time windows)
    - Distance (geographically distant events on consecutive days)
    - Travel buffer (insufficient gap between travel-required events)

    Scores events across five quality dimensions with team-configurable weights.

    Usage:
        >>> service = ConflictService(db_session)
        >>> result = service.detect_conflicts(team_id=1, start_date=..., end_date=...)
    """

    def __init__(self, db: Session):
        self.db = db
        self.event_service = EventService(db)
        self.config_service = ConfigService(db)

    # =========================================================================
    # Configuration
    # =========================================================================

    def get_conflict_rules(self, team_id: int) -> ConflictRulesResponse:
        """Get team's conflict rules, falling back to defaults."""
        values = {}
        for key, default in DEFAULT_CONFLICT_RULES.items():
            config = self.config_service.get("conflict_rules", key, team_id=team_id)
            if config and isinstance(config.value, dict):
                values[key] = config.value.get("value", default)
            else:
                values[key] = default
        return ConflictRulesResponse(**values)

    def get_scoring_weights(self, team_id: int) -> ScoringWeightsResponse:
        """Get team's scoring weights, falling back to defaults."""
        values = {}
        for key, default in DEFAULT_SCORING_WEIGHTS.items():
            config = self.config_service.get("scoring_weights", key, team_id=team_id)
            if config and isinstance(config.value, dict):
                values[key] = config.value.get("value", default)
            else:
                values[key] = default
        return ScoringWeightsResponse(**values)

    # =========================================================================
    # Scoring — Extensible Dimension Registry
    # =========================================================================

    @staticmethod
    def _score_venue_quality(event: Event, **kwargs) -> float:
        """Location rating * 20, null → 50."""
        if event.location is None or event.location.rating is None:
            return 50.0
        return float(event.location.rating * 20)

    @staticmethod
    def _score_organizer_reputation(event: Event, **kwargs) -> float:
        """Organizer rating * 20, null → 50."""
        if event.organizer is None or event.organizer.rating is None:
            return 50.0
        return float(event.organizer.rating * 20)

    @staticmethod
    def _score_performer_lineup(event: Event, performer_ceiling: int = 5, **kwargs) -> float:
        """Confirmed performers / ceiling * 100."""
        confirmed = sum(
            1 for ep in event.event_performers
            if ep.status == "confirmed"
        )
        return min(confirmed / max(performer_ceiling, 1), 1.0) * 100

    @staticmethod
    def _score_logistics_ease(event: Event, **kwargs) -> float:
        """Cumulative logistics commitment score.

        Scoring matrix (additive milestones):
        - Ticket: not_required=+25, purchased=+25, ready=+25 (max 50 if required)
        - PTO:    not_required=+25, booked=+10, approved=+15 (max 25)
        - Travel: not_required=+25, booked=+25 (max 25)

        None/unknown fields contribute 0. Maximum total: 100.
        """
        score = 0.0

        # Ticket (max 50 if required+ready, 25 if not required)
        if event.ticket_required is False:
            score += 25
        elif event.ticket_required is True:
            if event.ticket_status in ("purchased", "ready"):
                score += 25
            if event.ticket_status == "ready":
                score += 25

        # PTO/Timeoff (max 25 either way)
        if event.timeoff_required is False:
            score += 25
        elif event.timeoff_required is True:
            if event.timeoff_status in ("booked", "approved"):
                score += 10
            if event.timeoff_status == "approved":
                score += 15

        # Travel (max 25 either way)
        if event.travel_required is False:
            score += 25
        elif event.travel_required is True:
            if event.travel_status == "booked":
                score += 25

        return score

    @staticmethod
    def _score_readiness(event: Event, **kwargs) -> float:
        """Each resolved required item → proportional share of 100."""
        required_items: List[bool] = []
        if event.ticket_required:
            required_items.append(event.ticket_status in ("ready",))
        if event.timeoff_required:
            required_items.append(event.timeoff_status in ("approved",))
        if event.travel_required:
            required_items.append(event.travel_status in ("booked",))

        if not required_items:
            return 100.0  # Nothing required = fully ready
        return (sum(1 for r in required_items if r) / len(required_items)) * 100

    def _get_scoring_dimensions(self) -> List[Tuple[str, Callable, str]]:
        """
        Return the list of scoring dimensions as (name, scorer_fn, weight_key) tuples.

        Extensible: add new dimensions by appending to this list.
        """
        return [
            ("venue_quality", self._score_venue_quality, "weight_venue_quality"),
            ("organizer_reputation", self._score_organizer_reputation, "weight_organizer_reputation"),
            ("performer_lineup", self._score_performer_lineup, "weight_performer_lineup"),
            ("logistics_ease", self._score_logistics_ease, "weight_logistics_ease"),
            ("readiness", self._score_readiness, "weight_readiness"),
        ]

    def score_event(
        self,
        event: Event,
        weights: ScoringWeightsResponse,
        performer_ceiling: int = 5,
    ) -> EventScores:
        """
        Compute five dimension scores and weighted composite for an event.

        Args:
            event: Event model instance (with relationships loaded)
            weights: Team's scoring weights
            performer_ceiling: Max confirmed performers for 100% lineup score

        Returns:
            EventScores with all dimensions and composite
        """
        dimensions = self._get_scoring_dimensions()
        dim_scores: Dict[str, float] = {}

        for name, scorer_fn, _weight_key in dimensions:
            dim_scores[name] = scorer_fn(
                event,
                performer_ceiling=performer_ceiling,
            )

        # Compute weighted composite
        weight_values = []
        score_values = []
        for name, _scorer_fn, weight_key in dimensions:
            w = getattr(weights, weight_key, 0)
            weight_values.append(w)
            score_values.append(dim_scores[name])

        total_weight = sum(weight_values)
        if total_weight == 0:
            composite = 50.0  # Neutral default when all weights are zero
        else:
            composite = sum(s * w for s, w in zip(score_values, weight_values)) / total_weight

        return EventScores(
            **dim_scores,
            composite=round(composite, 1),
        )

    # =========================================================================
    # Conflict Detection
    # =========================================================================

    def detect_conflicts(
        self,
        team_id: int,
        start_date: date,
        end_date: date,
    ) -> ConflictDetectionResponse:
        """
        Detect conflicts for a date range.

        Runs three detection passes (time overlap, distance, travel buffer),
        groups edges via Union-Find, scores events, and derives group status.

        Args:
            team_id: Team ID for tenant isolation
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            ConflictDetectionResponse with groups and summary
        """
        rules = self.get_conflict_rules(team_id)
        weights = self.get_scoring_weights(team_id)

        # Pre-compute forces_skip statuses for this team (Issue #238)
        forces_skip_statuses = self.config_service.get_forces_skip_statuses(team_id)

        # Load events with relationships needed for conflict detection and scoring
        events = self._load_events(team_id, start_date, end_date)

        if not events:
            return ConflictDetectionResponse(
                conflict_groups=[],
                summary=ConflictSummary(
                    total_groups=0, unresolved=0,
                    partially_resolved=0, resolved=0,
                ),
            )

        # Three detection passes
        edges: List[ConflictEdge] = []
        edges.extend(self._detect_time_overlaps(events))
        edges.extend(self._detect_distance_conflicts(events, rules))
        edges.extend(self._detect_travel_buffer_violations(events, rules))

        # Pre-compute scores for all events (used for both all_scored and groups)
        performer_ceiling = rules.performer_ceiling
        scores_by_guid: Dict[str, EventScores] = {
            event.guid: self.score_event(event, weights, performer_ceiling)
            for event in events
        }

        # Build scored events for planner view
        all_scored = [
            self._build_scored_event(event, scores_by_guid[event.guid], forces_skip_statuses)
            for event in events
        ]

        if not edges:
            return ConflictDetectionResponse(
                conflict_groups=[],
                scored_events=all_scored,
                summary=ConflictSummary(
                    total_groups=0, unresolved=0,
                    partially_resolved=0, resolved=0,
                ),
            )

        # Build groups via Union-Find (reuse pre-computed scores)
        groups = self._build_groups(events, edges, scores_by_guid, forces_skip_statuses)

        # Summary
        unresolved = sum(1 for g in groups if g.status == ConflictGroupStatus.UNRESOLVED)
        partially = sum(1 for g in groups if g.status == ConflictGroupStatus.PARTIALLY_RESOLVED)
        resolved = sum(1 for g in groups if g.status == ConflictGroupStatus.RESOLVED)

        logger.info(
            f"Detected conflicts for team {team_id}",
            extra={
                "start_date": str(start_date),
                "end_date": str(end_date),
                "events_checked": len(events),
                "edges_found": len(edges),
                "groups": len(groups),
            },
        )

        return ConflictDetectionResponse(
            conflict_groups=groups,
            scored_events=all_scored,
            summary=ConflictSummary(
                total_groups=len(groups),
                unresolved=unresolved,
                partially_resolved=partially,
                resolved=resolved,
            ),
        )

    def _load_events(self, team_id: int, start_date: date, end_date: date) -> List[Event]:
        """Load non-deleted, non-deadline events with relationships for conflict detection."""
        events = self.db.query(Event).options(
            joinedload(Event.category),
            joinedload(Event.location),
            joinedload(Event.organizer),
            joinedload(Event.series).joinedload(EventSeries.location),
            # Note: event_performers uses lazy="dynamic" and cannot be eagerly loaded
        ).filter(
            Event.team_id == team_id,
            Event.deleted_at.is_(None),
            Event.is_deadline.is_(False),
            Event.event_date >= start_date,
            Event.event_date <= end_date,
        ).all()
        return events

    def _detect_time_overlaps(self, events: List[Event]) -> List[ConflictEdge]:
        """Detect time overlap conflicts between same-day events."""
        edges = []
        # Group events by date for efficiency
        by_date: Dict[date, List[Event]] = {}
        for event in events:
            by_date.setdefault(event.event_date, []).append(event)

        for day_events in by_date.values():
            for i in range(len(day_events)):
                for j in range(i + 1, len(day_events)):
                    a, b = day_events[i], day_events[j]
                    if self._times_overlap(a, b):
                        detail = self._time_overlap_detail(a, b)
                        edges.append(ConflictEdge(
                            event_a_guid=a.guid,
                            event_b_guid=b.guid,
                            conflict_type=ConflictType.TIME_OVERLAP,
                            detail=detail,
                        ))
        return edges

    @staticmethod
    def _times_overlap(a: Event, b: Event) -> bool:
        """Check if two same-day events have overlapping times."""
        if a.is_all_day or b.is_all_day:
            return True
        if a.start_time is None or a.end_time is None or b.start_time is None or b.end_time is None:
            return True  # Conservative: missing times = potential overlap
        return a.start_time < b.end_time and b.start_time < a.end_time

    @staticmethod
    def _time_overlap_detail(a: Event, b: Event) -> str:
        """Generate human-readable detail for a time overlap."""
        date_str = f"{a.event_date.strftime('%b')} {a.event_date.day}"
        if a.is_all_day or b.is_all_day:
            return f"All-day event conflict on {date_str}"
        if a.start_time and a.end_time and b.start_time and b.end_time:
            a_range = f"{a.start_time.strftime('%H:%M')}\u2013{a.end_time.strftime('%H:%M')}"
            b_range = f"{b.start_time.strftime('%H:%M')}\u2013{b.end_time.strftime('%H:%M')}"
            return f"Time overlap on {date_str}: {a_range} vs {b_range}"
        return f"Potential time conflict on {date_str} (missing time data)"

    def _detect_distance_conflicts(
        self, events: List[Event], rules: ConflictRulesResponse,
    ) -> List[ConflictEdge]:
        """Detect distance conflicts between events on consecutive days.

        Events within consecutive_window_days that are farther apart than
        colocation_radius_miles are flagged — they are not co-located and
        attending both may be difficult.
        """
        if rules.colocation_radius_miles <= 0:
            return []

        edges = []
        for i in range(len(events)):
            for j in range(i + 1, len(events)):
                a, b = events[i], events[j]
                days_apart = abs((a.event_date - b.event_date).days)
                if days_apart > rules.consecutive_window_days:
                    continue

                coords_a = self._get_coordinates(a)
                coords_b = self._get_coordinates(b)
                if coords_a is None or coords_b is None:
                    continue

                distance = haversine_miles(coords_a, coords_b)
                if distance > rules.colocation_radius_miles:
                    edges.append(ConflictEdge(
                        event_a_guid=a.guid,
                        event_b_guid=b.guid,
                        conflict_type=ConflictType.DISTANCE,
                        detail=f"{distance:.0f} miles apart within {days_apart} day(s)",
                    ))
        return edges

    def _detect_travel_buffer_violations(
        self, events: List[Event], rules: ConflictRulesResponse,
    ) -> List[ConflictEdge]:
        """Detect travel buffer violations between distant events.

        Triggers when at least one event requires travel and the events
        are farther apart than distance_threshold_miles with fewer than
        travel_buffer_days between them.
        """
        if rules.travel_buffer_days <= 0:
            return []

        edges = []

        for i in range(len(events)):
            for j in range(i + 1, len(events)):
                a, b = events[i], events[j]

                # At least one event must require travel
                if not (a.travel_required or b.travel_required):
                    continue

                days_between = abs((a.event_date - b.event_date).days)
                if days_between >= rules.travel_buffer_days:
                    continue

                coords_a = self._get_coordinates(a)
                coords_b = self._get_coordinates(b)
                if coords_a is None or coords_b is None:
                    continue

                # Only flag events that are truly distant (beyond threshold)
                distance = haversine_miles(coords_a, coords_b)
                if distance <= rules.distance_threshold_miles:
                    continue

                edges.append(ConflictEdge(
                    event_a_guid=a.guid,
                    event_b_guid=b.guid,
                    conflict_type=ConflictType.TRAVEL_BUFFER,
                    detail=f"Only {days_between} day(s) between travel events ({distance:.0f} mi apart)",
                ))
        return edges

    @staticmethod
    def _effective_location(event: Event):
        """Get event's location, falling back to series location if missing."""
        if event.location is not None:
            return event.location
        if event.series and event.series.location is not None:
            return event.series.location
        return None

    @staticmethod
    def _get_coordinates(event: Event) -> Optional[Tuple[float, float]]:
        """Extract (lat, lon) from event's effective location, or None if unavailable."""
        loc = ConflictService._effective_location(event)
        if loc is None:
            return None
        lat = loc.latitude
        lon = loc.longitude
        if lat is None or lon is None:
            return None
        return (float(lat), float(lon))

    # =========================================================================
    # Group Construction — Union-Find
    # =========================================================================

    def _build_groups(
        self,
        events: List[Event],
        edges: List[ConflictEdge],
        scores_by_guid: Dict[str, EventScores],
        forces_skip_statuses: set[str] | None = None,
    ) -> List[ConflictGroup]:
        """Build conflict groups from edges using Union-Find."""
        # Map GUIDs to events
        event_map: Dict[str, Event] = {e.guid: e for e in events}

        # Collect all GUIDs involved in edges
        involved_guids = set()
        for edge in edges:
            involved_guids.add(edge.event_a_guid)
            involved_guids.add(edge.event_b_guid)

        # Union-Find
        parent: Dict[str, str] = {g: g for g in involved_guids}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]  # Path compression
                x = parent[x]
            return x

        def union(x: str, y: str) -> None:
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        for edge in edges:
            # Normalize edge ordering for deterministic conflict identity
            if edge.event_a_guid > edge.event_b_guid:
                edge.event_a_guid, edge.event_b_guid = edge.event_b_guid, edge.event_a_guid
            union(edge.event_a_guid, edge.event_b_guid)

        # Group edges and events by component root
        component_events: Dict[str, set] = {}
        component_edges: Dict[str, List[ConflictEdge]] = {}

        for edge in edges:
            root = find(edge.event_a_guid)
            component_edges.setdefault(root, []).append(edge)
            component_events.setdefault(root, set()).add(edge.event_a_guid)
            component_events.setdefault(root, set()).add(edge.event_b_guid)

        # Build ConflictGroup objects
        groups = []
        for idx, (root, guids) in enumerate(sorted(component_events.items()), start=1):
            group_events = []
            for guid in sorted(guids):
                event = event_map.get(guid)
                if event is None:
                    continue
                scores = scores_by_guid.get(guid)
                if scores is None:
                    continue
                group_events.append(self._build_scored_event(event, scores, forces_skip_statuses))

            group_edges = component_edges.get(root, [])
            status = self._derive_group_status(group_events, group_edges)
            groups.append(ConflictGroup(
                group_id=f"cg_{idx}",
                status=status,
                events=group_events,
                edges=group_edges,
            ))

        return groups

    @staticmethod
    def _derive_group_status(
        events: List[ScoredEvent], edges: List[ConflictEdge],
    ) -> ConflictGroupStatus:
        """Derive group resolution status from edges and member attendance.

        A conflict edge is resolved when at least one of its two events is skipped.
        - RESOLVED: all edges have at least one skipped event
        - PARTIALLY_RESOLVED: some edges resolved, some not
        - UNRESOLVED: no edges have a skipped event
        """
        if not edges:
            return ConflictGroupStatus.RESOLVED

        skipped_guids = {e.guid for e in events if e.attendance == "skipped"}
        unresolved_count = sum(
            1
            for e in edges
            if e.event_a_guid not in skipped_guids
            and e.event_b_guid not in skipped_guids
        )

        if unresolved_count == 0:
            return ConflictGroupStatus.RESOLVED
        if unresolved_count < len(edges):
            return ConflictGroupStatus.PARTIALLY_RESOLVED
        return ConflictGroupStatus.UNRESOLVED

    def _build_scored_event(
        self,
        event: Event,
        scores: EventScores,
        forces_skip_statuses: set[str] | None = None,
    ) -> ScoredEvent:
        """Build a ScoredEvent from an Event model and its scores."""
        confirmed_count = sum(
            1 for ep in event.event_performers
            if ep.status == "confirmed"
        )

        # Effective category: fall back to series category (same as EventService)
        category = event.category
        if not category and event.series:
            category = event.series.category

        category_info = None
        if category:
            category_info = CategoryInfo(
                guid=category.guid,
                name=category.name,
                icon=category.icon,
                color=category.color,
            )

        # Effective location: fall back to series location (same pattern as category)
        location = self._effective_location(event)
        location_info = None
        if location:
            location_info = LocationInfo(
                guid=location.guid,
                name=location.name,
                city=location.city,
                country=location.country,
            )

        organizer_info = None
        if event.organizer:
            organizer_info = OrganizerInfo(
                guid=event.organizer.guid,
                name=event.organizer.name,
            )

        return ScoredEvent(
            guid=event.guid,
            title=event.effective_title,
            event_date=event.event_date,
            start_time=event.start_time.strftime("%H:%M") if event.start_time else None,
            end_time=event.end_time.strftime("%H:%M") if event.end_time else None,
            is_all_day=event.is_all_day,
            category=category_info,
            location=location_info,
            organizer=organizer_info,
            performer_count=confirmed_count,
            travel_required=event.travel_required,
            attendance=event.attendance,
            status=event.status,
            forces_skip=event.status in (forces_skip_statuses or set()),
            scores=scores,
        )

    # =========================================================================
    # Single Event Score
    # =========================================================================

    def get_event_score(self, guid: str, team_id: int) -> EventScoreResponse:
        """
        Get quality scores for a single event.

        Args:
            guid: Event GUID
            team_id: Team ID for tenant isolation

        Returns:
            EventScoreResponse with scores

        Raises:
            NotFoundError: If event not found
        """
        if not GuidService.validate_guid(guid, "evt"):
            raise NotFoundError("Event", guid)
        try:
            uuid_value = GuidService.parse_guid(guid, "evt")
        except ValueError as err:
            raise NotFoundError("Event", guid) from err

        event = self.db.query(Event).options(
            joinedload(Event.location),
            joinedload(Event.organizer),
            joinedload(Event.category),
            joinedload(Event.series).joinedload(EventSeries.location),
            # Note: event_performers uses lazy="dynamic" and cannot be eagerly loaded
        ).filter(
            Event.uuid == uuid_value,
            Event.team_id == team_id,
            Event.deleted_at.is_(None),
        ).first()

        if not event:
            raise NotFoundError("Event", guid)

        weights = self.get_scoring_weights(team_id)
        rules = self.get_conflict_rules(team_id)
        scores = self.score_event(event, weights, rules.performer_ceiling)

        return EventScoreResponse(
            guid=event.guid,
            title=event.effective_title,
            event_date=event.event_date,
            scores=scores,
        )

    # =========================================================================
    # Conflict Resolution
    # =========================================================================

    def resolve_conflict(
        self,
        team_id: int,
        decisions: List[Dict[str, str]],
        user_id: int,
        group_id: Optional[str] = None,
    ) -> int:
        """
        Batch-update attendance for events in a conflict group.

        Args:
            team_id: Team ID for tenant isolation
            decisions: List of {"event_guid": ..., "attendance": "planned"|"skipped"}
            user_id: User ID for audit attribution
            group_id: Ephemeral group identifier for logging (optional)

        Returns:
            Number of events whose attendance was updated

        Raises:
            NotFoundError: If any event not found
        """
        # Allowed attendance values from AttendanceStatus enum
        ALLOWED_ATTENDANCE = {"planned", "attended", "skipped"}

        # Pre-compute forces_skip statuses for this team (Issue #238)
        forces_skip_statuses = self.config_service.get_forces_skip_statuses(team_id)

        updated = 0
        for decision in decisions:
            # Safely extract and validate decision fields
            event_guid = decision.get("event_guid")
            attendance = decision.get("attendance")

            if not event_guid:
                raise ValidationError("Decision missing required 'event_guid' field")
            if not attendance:
                raise ValidationError("Decision missing required 'attendance' field")
            if attendance not in ALLOWED_ATTENDANCE:
                raise ValidationError(
                    f"Invalid attendance value '{attendance}'. "
                    f"Must be one of: {', '.join(sorted(ALLOWED_ATTENDANCE))}"
                )

            if not GuidService.validate_guid(event_guid, "evt"):
                raise NotFoundError("Event", event_guid)
            try:
                uuid_value = GuidService.parse_guid(event_guid, "evt")
            except ValueError as err:
                raise NotFoundError("Event", event_guid) from err

            event = self.db.query(Event).filter(
                Event.uuid == uuid_value,
                Event.team_id == team_id,
                Event.deleted_at.is_(None),
            ).first()

            if not event:
                raise NotFoundError("Event", event_guid)

            # Enforce forces_skip: reject attendance changes away from 'skipped'
            # when the event's status forces skip (Issue #238)
            if event.status in forces_skip_statuses and attendance != "skipped":
                raise ValidationError(
                    f"Cannot change attendance away from 'skipped' while status "
                    f"'{event.status}' forces skip"
                )

            if event.attendance != attendance:
                event.attendance = attendance
                event.updated_by_user_id = user_id
                updated += 1

        if updated > 0:
            self.db.commit()

        logger.info(
            f"Resolved conflict for team {team_id}",
            extra={"group_id": group_id, "decisions": len(decisions), "updated": updated},
        )

        return updated
