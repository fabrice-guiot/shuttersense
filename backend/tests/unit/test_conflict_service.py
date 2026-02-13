"""
Tests for ConflictService: conflict detection, scoring, and group construction.

Tests three conflict types (time overlap, distance, travel buffer),
five scoring dimensions, composite score calculation, and Union-Find grouping.
"""

import pytest
from datetime import date, time
from unittest.mock import MagicMock, patch, PropertyMock

from backend.src.services.conflict_service import ConflictService
from backend.src.schemas.conflict import (
    ConflictType,
    ConflictGroupStatus,
    EventScores,
    ScoringWeightsResponse,
    ConflictRulesResponse,
)


def _make_event(
    guid="evt_test_001",
    event_date=date(2026, 3, 15),
    start_time=time(14, 0),
    end_time=time(18, 0),
    is_all_day=False,
    attendance="planned",
    location=None,
    organizer=None,
    event_performers=None,
    travel_required=None,
    ticket_required=None,
    timeoff_required=None,
    ticket_status=None,
    timeoff_status=None,
    travel_status=None,
    is_deadline=False,
    deleted_at=None,
    title="Test Event",
    category=None,
    series=None,
    team_id=1,
):
    """Create a mock Event object for testing."""
    event = MagicMock()
    event.guid = guid
    event.event_date = event_date
    event.start_time = start_time
    event.end_time = end_time
    event.is_all_day = is_all_day
    event.attendance = attendance
    event.location = location
    event.organizer = organizer
    event.event_performers = event_performers or []
    event.travel_required = travel_required
    event.ticket_required = ticket_required
    event.timeoff_required = timeoff_required
    event.ticket_status = ticket_status
    event.timeoff_status = timeoff_status
    event.travel_status = travel_status
    event.is_deadline = is_deadline
    event.deleted_at = deleted_at
    event.effective_title = title
    event.title = title
    event.category = category
    event.series = series
    event.team_id = team_id
    return event


def _make_location(latitude=None, longitude=None, rating=None, guid="loc_test", name="Test Location", city=None, country=None):
    loc = MagicMock()
    loc.latitude = latitude
    loc.longitude = longitude
    loc.rating = rating
    loc.guid = guid
    loc.name = name
    loc.city = city
    loc.country = country
    return loc


def _make_organizer(rating=None, guid="org_test", name="Test Organizer"):
    org = MagicMock()
    org.rating = rating
    org.guid = guid
    org.name = name
    return org


def _make_performer(status="confirmed"):
    perf = MagicMock()
    perf.status = status
    return perf


DEFAULT_WEIGHTS = ScoringWeightsResponse(
    weight_venue_quality=20,
    weight_organizer_reputation=20,
    weight_performer_lineup=20,
    weight_logistics_ease=20,
    weight_readiness=20,
)


class TestScoring:
    """Tests for event quality scoring dimensions."""

    def test_venue_quality_with_rating(self):
        """Location rating 4 → score 80."""
        event = _make_event(location=_make_location(rating=4))
        score = ConflictService._score_venue_quality(event)
        assert score == 80.0

    def test_venue_quality_no_location(self):
        """No location → neutral default 50."""
        event = _make_event(location=None)
        score = ConflictService._score_venue_quality(event)
        assert score == 50.0

    def test_venue_quality_null_rating(self):
        """Location with null rating → neutral default 50."""
        event = _make_event(location=_make_location(rating=None))
        score = ConflictService._score_venue_quality(event)
        assert score == 50.0

    def test_organizer_reputation_with_rating(self):
        """Organizer rating 5 → score 100."""
        event = _make_event(organizer=_make_organizer(rating=5))
        score = ConflictService._score_organizer_reputation(event)
        assert score == 100.0

    def test_organizer_reputation_no_organizer(self):
        """No organizer → neutral default 50."""
        event = _make_event(organizer=None)
        score = ConflictService._score_organizer_reputation(event)
        assert score == 50.0

    def test_performer_lineup_full(self):
        """5 confirmed performers with ceiling 5 → 100."""
        performers = [_make_performer("confirmed") for _ in range(5)]
        event = _make_event(event_performers=performers)
        score = ConflictService._score_performer_lineup(event, performer_ceiling=5)
        assert score == 100.0

    def test_performer_lineup_partial(self):
        """2 confirmed + 1 announced with ceiling 5 → 40."""
        performers = [
            _make_performer("confirmed"),
            _make_performer("confirmed"),
            _make_performer("announced"),
        ]
        event = _make_event(event_performers=performers)
        score = ConflictService._score_performer_lineup(event, performer_ceiling=5)
        assert score == 40.0

    def test_performer_lineup_over_ceiling(self):
        """7 confirmed with ceiling 5 → capped at 100."""
        performers = [_make_performer("confirmed") for _ in range(7)]
        event = _make_event(event_performers=performers)
        score = ConflictService._score_performer_lineup(event, performer_ceiling=5)
        assert score == 100.0

    def test_performer_lineup_none(self):
        """No performers → 0."""
        event = _make_event(event_performers=[])
        score = ConflictService._score_performer_lineup(event, performer_ceiling=5)
        assert score == 0.0

    def test_logistics_ease_all_not_required(self):
        """All logistics not required → 100."""
        event = _make_event(travel_required=False, ticket_required=False, timeoff_required=False)
        score = ConflictService._score_logistics_ease(event)
        assert abs(score - 100.0) < 0.1

    def test_logistics_ease_all_required(self):
        """All logistics required → 0."""
        event = _make_event(travel_required=True, ticket_required=True, timeoff_required=True)
        score = ConflictService._score_logistics_ease(event)
        assert score == 0.0

    def test_logistics_ease_null_treated_as_not_required(self):
        """Null logistics fields treated as not required → 100."""
        event = _make_event(travel_required=None, ticket_required=None, timeoff_required=None)
        score = ConflictService._score_logistics_ease(event)
        assert abs(score - 100.0) < 0.1

    def test_readiness_all_resolved(self):
        """All required items resolved → 100."""
        event = _make_event(
            ticket_required=True, ticket_status="ready",
            timeoff_required=True, timeoff_status="approved",
            travel_required=True, travel_status="booked",
        )
        score = ConflictService._score_readiness(event)
        assert score == 100.0

    def test_readiness_none_resolved(self):
        """All required, none resolved → 0."""
        event = _make_event(
            ticket_required=True, ticket_status="not_purchased",
            timeoff_required=True, timeoff_status="planned",
            travel_required=True, travel_status="planned",
        )
        score = ConflictService._score_readiness(event)
        assert score == 0.0

    def test_readiness_nothing_required(self):
        """Nothing required → 100 (fully ready)."""
        event = _make_event(ticket_required=False, timeoff_required=False, travel_required=False)
        score = ConflictService._score_readiness(event)
        assert score == 100.0

    def test_readiness_partial(self):
        """1 of 2 required items resolved → 50."""
        event = _make_event(
            ticket_required=True, ticket_status="ready",
            travel_required=True, travel_status="planned",
            timeoff_required=False,
        )
        score = ConflictService._score_readiness(event)
        assert score == 50.0


class TestCompositeScore:
    """Tests for weighted composite score calculation."""

    def test_equal_weights(self):
        """Equal weights → simple average of dimensions."""
        event = _make_event(
            location=_make_location(rating=4),  # 80
            organizer=_make_organizer(rating=3),  # 60
            event_performers=[_make_performer("confirmed")],  # 20 (1/5)
            travel_required=False, ticket_required=False, timeoff_required=False,  # 100
        )  # Readiness: nothing required → 100

        service = ConflictService.__new__(ConflictService)
        scores = service.score_event(event, DEFAULT_WEIGHTS, performer_ceiling=5)

        # (80 + 60 + 20 + 100 + 100) / 5 = 72
        assert abs(scores.composite - 72.0) < 0.5

    def test_zero_weights_returns_50(self):
        """All zero weights → neutral composite of 50."""
        event = _make_event()
        zero_weights = ScoringWeightsResponse(
            weight_venue_quality=0, weight_organizer_reputation=0,
            weight_performer_lineup=0, weight_logistics_ease=0,
            weight_readiness=0,
        )

        service = ConflictService.__new__(ConflictService)
        scores = service.score_event(event, zero_weights, performer_ceiling=5)
        assert scores.composite == 50.0

    def test_single_weight(self):
        """Only venue weight → composite equals venue score."""
        event = _make_event(location=_make_location(rating=5))
        single_weight = ScoringWeightsResponse(
            weight_venue_quality=100, weight_organizer_reputation=0,
            weight_performer_lineup=0, weight_logistics_ease=0,
            weight_readiness=0,
        )

        service = ConflictService.__new__(ConflictService)
        scores = service.score_event(event, single_weight, performer_ceiling=5)
        assert scores.composite == 100.0


class TestTimeOverlap:
    """Tests for time overlap conflict detection."""

    def test_overlapping_times(self):
        """Two events with overlapping time windows → conflict."""
        a = _make_event(guid="evt_a", start_time=time(14, 0), end_time=time(18, 0))
        b = _make_event(guid="evt_b", start_time=time(16, 0), end_time=time(20, 0))
        assert ConflictService._times_overlap(a, b) is True

    def test_non_overlapping_times(self):
        """Two events with non-overlapping times → no conflict."""
        a = _make_event(guid="evt_a", start_time=time(9, 0), end_time=time(12, 0))
        b = _make_event(guid="evt_b", start_time=time(14, 0), end_time=time(18, 0))
        assert ConflictService._times_overlap(a, b) is False

    def test_all_day_always_conflicts(self):
        """All-day event conflicts with any same-day event."""
        a = _make_event(guid="evt_a", is_all_day=True)
        b = _make_event(guid="evt_b", start_time=time(14, 0), end_time=time(18, 0))
        assert ConflictService._times_overlap(a, b) is True

    def test_missing_times_conservative(self):
        """Missing times on same day → conflict (conservative approach)."""
        a = _make_event(guid="evt_a", start_time=None, end_time=None)
        b = _make_event(guid="evt_b", start_time=time(14, 0), end_time=time(18, 0))
        assert ConflictService._times_overlap(a, b) is True

    def test_adjacent_times_no_overlap(self):
        """Adjacent times (end == start) → no overlap."""
        a = _make_event(guid="evt_a", start_time=time(9, 0), end_time=time(12, 0))
        b = _make_event(guid="evt_b", start_time=time(12, 0), end_time=time(15, 0))
        assert ConflictService._times_overlap(a, b) is False


class TestDistanceConflict:
    """Tests for distance conflict detection."""

    def test_distant_events_conflict(self):
        """Events > threshold miles apart within window → conflict."""
        loc_nyc = _make_location(latitude=40.7128, longitude=-74.0060)
        loc_la = _make_location(latitude=34.0522, longitude=-118.2437)

        a = _make_event(guid="evt_a", event_date=date(2026, 3, 15), location=loc_nyc)
        b = _make_event(guid="evt_b", event_date=date(2026, 3, 15), location=loc_la)

        service = ConflictService.__new__(ConflictService)
        rules = ConflictRulesResponse(distance_threshold_miles=50, consecutive_window_days=1)
        edges = service._detect_distance_conflicts([a, b], rules)

        assert len(edges) == 1
        assert edges[0].conflict_type == ConflictType.DISTANCE

    def test_close_events_no_conflict(self):
        """Events within threshold miles → no conflict."""
        loc_a = _make_location(latitude=40.7128, longitude=-74.0060)
        loc_b = _make_location(latitude=40.7580, longitude=-73.9855)

        a = _make_event(guid="evt_a", event_date=date(2026, 3, 15), location=loc_a)
        b = _make_event(guid="evt_b", event_date=date(2026, 3, 15), location=loc_b)

        service = ConflictService.__new__(ConflictService)
        rules = ConflictRulesResponse(distance_threshold_miles=50, consecutive_window_days=1)
        edges = service._detect_distance_conflicts([a, b], rules)

        assert len(edges) == 0

    def test_missing_coordinates_ignored(self):
        """Events without coordinates → no distance conflict."""
        loc_none = _make_location(latitude=None, longitude=None)
        loc_nyc = _make_location(latitude=40.7128, longitude=-74.0060)

        a = _make_event(guid="evt_a", event_date=date(2026, 3, 15), location=loc_none)
        b = _make_event(guid="evt_b", event_date=date(2026, 3, 15), location=loc_nyc)

        service = ConflictService.__new__(ConflictService)
        rules = ConflictRulesResponse(distance_threshold_miles=50, consecutive_window_days=1)
        edges = service._detect_distance_conflicts([a, b], rules)

        assert len(edges) == 0

    def test_beyond_window_no_conflict(self):
        """Events more than window_days apart → no distance conflict."""
        loc_nyc = _make_location(latitude=40.7128, longitude=-74.0060)
        loc_la = _make_location(latitude=34.0522, longitude=-118.2437)

        a = _make_event(guid="evt_a", event_date=date(2026, 3, 15), location=loc_nyc)
        b = _make_event(guid="evt_b", event_date=date(2026, 3, 20), location=loc_la)

        service = ConflictService.__new__(ConflictService)
        rules = ConflictRulesResponse(distance_threshold_miles=50, consecutive_window_days=1)
        edges = service._detect_distance_conflicts([a, b], rules)

        assert len(edges) == 0


class TestTravelBuffer:
    """Tests for travel buffer violation detection."""

    def test_travel_events_within_buffer(self):
        """Two travel events too close in time → conflict."""
        loc_nyc = _make_location(latitude=40.7128, longitude=-74.0060)
        loc_la = _make_location(latitude=34.0522, longitude=-118.2437)

        a = _make_event(
            guid="evt_a", event_date=date(2026, 3, 15),
            location=loc_nyc, travel_required=True,
        )
        b = _make_event(
            guid="evt_b", event_date=date(2026, 3, 16),
            location=loc_la, travel_required=True,
        )

        service = ConflictService.__new__(ConflictService)
        rules = ConflictRulesResponse(travel_buffer_days=3, colocation_radius_miles=10)
        edges = service._detect_travel_buffer_violations([a, b], rules)

        assert len(edges) == 1
        assert edges[0].conflict_type == ConflictType.TRAVEL_BUFFER

    def test_colocated_travel_events_exempt(self):
        """Co-located travel events within buffer → no conflict."""
        loc_a = _make_location(latitude=40.7128, longitude=-74.0060)
        loc_b = _make_location(latitude=40.7200, longitude=-74.0000)  # ~0.5 miles

        a = _make_event(
            guid="evt_a", event_date=date(2026, 3, 15),
            location=loc_a, travel_required=True,
        )
        b = _make_event(
            guid="evt_b", event_date=date(2026, 3, 16),
            location=loc_b, travel_required=True,
        )

        service = ConflictService.__new__(ConflictService)
        rules = ConflictRulesResponse(travel_buffer_days=3, colocation_radius_miles=10)
        edges = service._detect_travel_buffer_violations([a, b], rules)

        assert len(edges) == 0

    def test_non_travel_events_ignored(self):
        """Non-travel events → no travel buffer conflict."""
        loc_nyc = _make_location(latitude=40.7128, longitude=-74.0060)
        loc_la = _make_location(latitude=34.0522, longitude=-118.2437)

        a = _make_event(
            guid="evt_a", event_date=date(2026, 3, 15),
            location=loc_nyc, travel_required=False,
        )
        b = _make_event(
            guid="evt_b", event_date=date(2026, 3, 16),
            location=loc_la, travel_required=False,
        )

        service = ConflictService.__new__(ConflictService)
        rules = ConflictRulesResponse(travel_buffer_days=3, colocation_radius_miles=10)
        edges = service._detect_travel_buffer_violations([a, b], rules)

        assert len(edges) == 0


class TestGroupConstruction:
    """Tests for Union-Find group construction and status derivation."""

    def test_transitive_closure(self):
        """A↔B and B↔C should produce one group with A, B, C."""
        from backend.src.schemas.conflict import ConflictEdge

        a = _make_event(guid="evt_a")
        b = _make_event(guid="evt_b")
        c = _make_event(guid="evt_c")

        edges = [
            ConflictEdge(
                event_a_guid="evt_a", event_b_guid="evt_b",
                conflict_type=ConflictType.TIME_OVERLAP, detail="test",
            ),
            ConflictEdge(
                event_a_guid="evt_b", event_b_guid="evt_c",
                conflict_type=ConflictType.TIME_OVERLAP, detail="test",
            ),
        ]

        service = ConflictService.__new__(ConflictService)
        groups = service._build_groups([a, b, c], edges, DEFAULT_WEIGHTS, 5)

        assert len(groups) == 1
        assert len(groups[0].events) == 3

    def test_separate_groups(self):
        """A↔B and C↔D → two separate groups."""
        from backend.src.schemas.conflict import ConflictEdge

        a = _make_event(guid="evt_a")
        b = _make_event(guid="evt_b")
        c = _make_event(guid="evt_c")
        d = _make_event(guid="evt_d")

        edges = [
            ConflictEdge(
                event_a_guid="evt_a", event_b_guid="evt_b",
                conflict_type=ConflictType.TIME_OVERLAP, detail="test",
            ),
            ConflictEdge(
                event_a_guid="evt_c", event_b_guid="evt_d",
                conflict_type=ConflictType.DISTANCE, detail="test",
            ),
        ]

        service = ConflictService.__new__(ConflictService)
        groups = service._build_groups([a, b, c, d], edges, DEFAULT_WEIGHTS, 5)

        assert len(groups) == 2

    def test_status_unresolved(self):
        """All events planned → unresolved."""
        from backend.src.schemas.conflict import ScoredEvent

        events = [
            MagicMock(attendance="planned"),
            MagicMock(attendance="planned"),
        ]
        status = ConflictService._derive_group_status(events)
        assert status == ConflictGroupStatus.UNRESOLVED

    def test_status_resolved(self):
        """At most 1 event planned → resolved."""
        events = [
            MagicMock(attendance="planned"),
            MagicMock(attendance="skipped"),
        ]
        status = ConflictService._derive_group_status(events)
        assert status == ConflictGroupStatus.RESOLVED

    def test_status_partially_resolved(self):
        """Some but not all events planned → partially resolved."""
        events = [
            MagicMock(attendance="planned"),
            MagicMock(attendance="planned"),
            MagicMock(attendance="skipped"),
        ]
        status = ConflictService._derive_group_status(events)
        assert status == ConflictGroupStatus.PARTIALLY_RESOLVED
