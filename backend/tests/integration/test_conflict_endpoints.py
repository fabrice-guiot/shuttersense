"""
Integration tests for conflict detection and scoring API endpoints.

Tests end-to-end flows for:
- GET /events/conflicts (date range conflict detection)
- POST /events/conflicts/resolve (batch attendance updates)
- GET /events/{guid}/score (single event quality scoring)

Issue #182 - Calendar Conflict Visualization & Event Picker
"""

import pytest
from datetime import date, time

from collections import defaultdict

from backend.src.models import Category, Configuration, ConfigSource, Event, EventSeries, Location, Organizer


class TestConflictDetection:
    """Integration tests for GET /events/conflicts."""

    @pytest.fixture
    def category(self, test_db_session, test_team):
        """Create a test category for conflict detection tests.

        Args:
            test_db_session: SQLAlchemy test database session.
            test_team: Test team instance providing team_id.

        Returns:
            Category: A persisted Category instance with id and team_id set.
        """
        cat = Category(
            name="Conflict Test Category",
            icon="calendar",
            color="#FF0000",
            is_active=True,
            display_order=0,
            team_id=test_team.id,
        )
        test_db_session.add(cat)
        test_db_session.commit()
        test_db_session.refresh(cat)
        return cat

    @pytest.fixture
    def locations(self, test_db_session, test_team, category):
        """Two distant locations (NYC & LA)."""
        nyc = Location(
            name="NYC Venue",
            city="New York",
            country="US",
            latitude=40.7128,
            longitude=-74.0060,
            category_id=category.id,
            team_id=test_team.id,
        )
        la = Location(
            name="LA Venue",
            city="Los Angeles",
            country="US",
            latitude=34.0522,
            longitude=-118.2437,
            category_id=category.id,
            team_id=test_team.id,
        )
        test_db_session.add_all([nyc, la])
        test_db_session.commit()
        test_db_session.refresh(nyc)
        test_db_session.refresh(la)
        return nyc, la

    @pytest.fixture
    def overlapping_events(self, test_db_session, test_team, category):
        """Two events on the same day with overlapping times."""
        e1 = Event(
            title="Morning Event",
            event_date=date(2026, 6, 15),
            start_time=time(9, 0),
            end_time=time(12, 0),
            is_all_day=False,
            status="future",
            attendance="planned",
            category_id=category.id,
            team_id=test_team.id,
        )
        e2 = Event(
            title="Overlapping Event",
            event_date=date(2026, 6, 15),
            start_time=time(11, 0),
            end_time=time(14, 0),
            is_all_day=False,
            status="future",
            attendance="planned",
            category_id=category.id,
            team_id=test_team.id,
        )
        test_db_session.add_all([e1, e2])
        test_db_session.commit()
        test_db_session.refresh(e1)
        test_db_session.refresh(e2)
        return e1, e2

    @pytest.fixture
    def distant_events(self, test_db_session, test_team, category, locations):
        """Two events on consecutive days at distant locations."""
        nyc, la = locations
        e1 = Event(
            title="NYC Event",
            event_date=date(2026, 6, 20),
            start_time=time(10, 0),
            end_time=time(16, 0),
            is_all_day=False,
            status="future",
            attendance="planned",
            category_id=category.id,
            location_id=nyc.id,
            team_id=test_team.id,
        )
        e2 = Event(
            title="LA Event",
            event_date=date(2026, 6, 21),
            start_time=time(10, 0),
            end_time=time(16, 0),
            is_all_day=False,
            status="future",
            attendance="planned",
            category_id=category.id,
            location_id=la.id,
            team_id=test_team.id,
        )
        test_db_session.add_all([e1, e2])
        test_db_session.commit()
        test_db_session.refresh(e1)
        test_db_session.refresh(e2)
        return e1, e2

    def test_no_events_returns_empty(self, test_client):
        """Empty date range → no conflict groups."""
        response = test_client.get(
            "/api/events/conflicts",
            params={"start_date": "2026-01-01", "end_date": "2026-01-31"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["conflict_groups"] == []
        assert data["summary"]["total_groups"] == 0

    def test_no_conflicts_returns_empty(self, test_client, test_db_session, test_team, category):
        """Non-overlapping events → no conflict groups."""
        e1 = Event(
            title="Event A",
            event_date=date(2026, 6, 10),
            start_time=time(9, 0),
            end_time=time(10, 0),
            is_all_day=False,
            status="future",
            attendance="planned",
            category_id=category.id,
            team_id=test_team.id,
        )
        e2 = Event(
            title="Event B",
            event_date=date(2026, 6, 10),
            start_time=time(11, 0),
            end_time=time(12, 0),
            is_all_day=False,
            status="future",
            attendance="planned",
            category_id=category.id,
            team_id=test_team.id,
        )
        test_db_session.add_all([e1, e2])
        test_db_session.commit()

        response = test_client.get(
            "/api/events/conflicts",
            params={"start_date": "2026-06-01", "end_date": "2026-06-30"},
        )
        assert response.status_code == 200
        assert response.json()["conflict_groups"] == []

    def test_time_overlap_detected(self, test_client, _overlapping_events):
        """Two overlapping same-day events → one conflict group."""
        response = test_client.get(
            "/api/events/conflicts",
            params={"start_date": "2026-06-01", "end_date": "2026-06-30"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total_groups"] == 1

        group = data["conflict_groups"][0]
        assert len(group["events"]) == 2
        assert len(group["edges"]) >= 1
        assert group["edges"][0]["conflict_type"] == "time_overlap"
        assert group["status"] == "unresolved"

    def test_distance_conflict_detected(self, test_client, _distant_events):
        """Distant consecutive-day events → distance conflict."""
        response = test_client.get(
            "/api/events/conflicts",
            params={"start_date": "2026-06-01", "end_date": "2026-06-30"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total_groups"] >= 1

        # Find the distance edge
        all_edges = []
        for g in data["conflict_groups"]:
            all_edges.extend(g["edges"])
        distance_edges = [e for e in all_edges if e["conflict_type"] == "distance"]
        assert len(distance_edges) >= 1

    def test_scored_events_in_group(self, test_client, _overlapping_events):
        """Events in conflict groups include quality scores."""
        response = test_client.get(
            "/api/events/conflicts",
            params={"start_date": "2026-06-01", "end_date": "2026-06-30"},
        )
        assert response.status_code == 200
        group = response.json()["conflict_groups"][0]

        for event in group["events"]:
            scores = event["scores"]
            assert "venue_quality" in scores
            assert "organizer_reputation" in scores
            assert "performer_lineup" in scores
            assert "logistics_ease" in scores
            assert "readiness" in scores
            assert "composite" in scores
            assert 0 <= scores["composite"] <= 100

    def test_invalid_date_range(self, test_client):
        """end_date < start_date → 422."""
        response = test_client.get(
            "/api/events/conflicts",
            params={"start_date": "2026-06-30", "end_date": "2026-06-01"},
        )
        assert response.status_code == 422

    def test_missing_dates(self, test_client):
        """Missing required query params → 422."""
        response = test_client.get("/api/events/conflicts")
        assert response.status_code == 422

    def test_response_summary_structure(self, test_client, _overlapping_events):
        """Summary includes all required counts."""
        response = test_client.get(
            "/api/events/conflicts",
            params={"start_date": "2026-06-01", "end_date": "2026-06-30"},
        )
        summary = response.json()["summary"]
        assert "total_groups" in summary
        assert "unresolved" in summary
        assert "partially_resolved" in summary
        assert "resolved" in summary


class TestConflictResolve:
    """Integration tests for POST /events/conflicts/resolve."""

    @pytest.fixture
    def conflict_events(self, test_db_session, test_team):
        """Two overlapping events to resolve."""
        cat = Category(
            name="Resolve Test Category",
            icon="check",
            color="#00FF00",
            is_active=True,
            display_order=0,
            team_id=test_team.id,
        )
        test_db_session.add(cat)
        test_db_session.flush()

        e1 = Event(
            title="Keep This Event",
            event_date=date(2026, 8, 1),
            start_time=time(10, 0),
            end_time=time(15, 0),
            is_all_day=False,
            status="future",
            attendance="planned",
            category_id=cat.id,
            team_id=test_team.id,
        )
        e2 = Event(
            title="Skip This Event",
            event_date=date(2026, 8, 1),
            start_time=time(12, 0),
            end_time=time(17, 0),
            is_all_day=False,
            status="future",
            attendance="planned",
            category_id=cat.id,
            team_id=test_team.id,
        )
        test_db_session.add_all([e1, e2])
        test_db_session.commit()
        test_db_session.refresh(e1)
        test_db_session.refresh(e2)
        return e1, e2

    def test_resolve_updates_attendance(self, test_client, conflict_events):
        """Resolving sets attendance on specified events."""
        e1, e2 = conflict_events
        response = test_client.post("/api/events/conflicts/resolve", json={
            "group_id": "cg_1",
            "decisions": [
                {"event_guid": e1.guid, "attendance": "planned"},
                {"event_guid": e2.guid, "attendance": "skipped"},
            ],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["updated_count"] == 1  # Only e2 changed

    def test_resolve_nonexistent_event(self, test_client):
        """Resolving with a bad GUID → 404."""
        response = test_client.post("/api/events/conflicts/resolve", json={
            "group_id": "cg_1",
            "decisions": [
                {"event_guid": "evt_does_not_exist", "attendance": "skipped"},
            ],
        })
        assert response.status_code == 404

    def test_resolve_empty_decisions(self, test_client):
        """Empty decisions list → 422 (min_length=1)."""
        response = test_client.post("/api/events/conflicts/resolve", json={
            "group_id": "cg_1",
            "decisions": [],
        })
        assert response.status_code == 422

    def test_resolve_makes_group_resolved(self, test_client, conflict_events):
        """After resolving, conflict group status should update."""
        e1, e2 = conflict_events

        # Resolve: keep e1, skip e2
        test_client.post("/api/events/conflicts/resolve", json={
            "group_id": "cg_1",
            "decisions": [
                {"event_guid": e1.guid, "attendance": "planned"},
                {"event_guid": e2.guid, "attendance": "skipped"},
            ],
        })

        # Re-detect: group should now be resolved (only 1 active event)
        response = test_client.get(
            "/api/events/conflicts",
            params={"start_date": "2026-08-01", "end_date": "2026-08-31"},
        )
        data = response.json()
        # Assert that we have conflict groups (the fixture creates overlapping events)
        assert data["conflict_groups"], "Expected at least one conflict group after resolution"
        group = data["conflict_groups"][0]
        assert group["status"] == "resolved"


class TestEventScore:
    """Integration tests for GET /events/{guid}/score."""

    @pytest.fixture
    def scored_event(self, test_db_session, test_team):
        """An event with location and organizer for scoring."""
        cat = Category(
            name="Score Test Category",
            icon="star",
            color="#FFD700",
            is_active=True,
            display_order=0,
            team_id=test_team.id,
        )
        test_db_session.add(cat)
        test_db_session.flush()

        loc = Location(
            name="Great Venue",
            city="Austin",
            country="US",
            rating=4,
            category_id=cat.id,
            team_id=test_team.id,
        )
        org = Organizer(
            name="Top Organizer",
            rating=5,
            category_id=cat.id,
            team_id=test_team.id,
        )
        test_db_session.add_all([loc, org])
        test_db_session.flush()

        event = Event(
            title="Scored Event",
            event_date=date(2026, 9, 15),
            start_time=time(10, 0),
            end_time=time(18, 0),
            is_all_day=False,
            status="future",
            attendance="planned",
            category_id=cat.id,
            location_id=loc.id,
            organizer_id=org.id,
            travel_required=False,
            ticket_required=False,
            timeoff_required=False,
            team_id=test_team.id,
        )
        test_db_session.add(event)
        test_db_session.commit()
        test_db_session.refresh(event)
        return event

    def test_get_event_score(self, test_client, scored_event):
        """Returns scores for a valid event."""
        response = test_client.get(f"/api/events/{scored_event.guid}/score")
        assert response.status_code == 200

        data = response.json()
        assert data["guid"] == scored_event.guid
        assert data["title"] == "Scored Event"
        assert data["event_date"] == "2026-09-15"

        scores = data["scores"]
        assert scores["venue_quality"] == 80.0  # rating 4 * 20
        assert scores["organizer_reputation"] == 100.0  # rating 5 * 20
        assert scores["logistics_ease"] == 100.0  # nothing required → 100
        assert scores["readiness"] == 100.0  # nothing required → 100
        assert 0 <= scores["composite"] <= 100

    def test_score_not_found(self, test_client):
        """Non-existent event GUID → 404."""
        response = test_client.get("/api/events/evt_does_not_exist/score")
        assert response.status_code == 404

    def test_score_includes_all_dimensions(self, test_client, scored_event):
        """Response includes all five scoring dimensions."""
        response = test_client.get(f"/api/events/{scored_event.guid}/score")
        scores = response.json()["scores"]
        expected_keys = {
            "venue_quality",
            "organizer_reputation",
            "performer_lineup",
            "logistics_ease",
            "readiness",
            "composite",
        }
        assert set(scores.keys()) == expected_keys


class TestFiveEventProductionScenario:
    """Test the exact 5-event production scenario from Issue #193.

    Setup:
    - 2 series, 2 locations (NYC, LA — ~2,451 mi apart)
    - Series 1: 3 events (Thu/Fri/Sat) at NYC, travel_required=True
    - Series 2: 2 events (Sat/Sun) at LA, travel_required=True
    - Config: travel_buffer_days=3, consecutive_window_days=0

    Expected conflict counts per day:
    - Thu: 1 edge (E1/S1 ↔ E1/S2 travel buffer)
    - Fri: 2 edges (E2/S1 ↔ E1/S2, E2/S1 ↔ E2/S2 travel buffer)
    - Sat: 5 edges (time overlap + distance + 3 travel buffers)
    - Sun: 2 edges (E2/S2 ↔ E2/S1, E2/S2 ↔ E3/S1 travel buffer)

    One conflict group with all 5 events.
    Skipping Series 2 (2 events) resolves all conflicts.
    """

    @pytest.fixture
    def category(self, test_db_session, test_team):
        cat = Category(
            name="Production Test Category",
            icon="calendar",
            color="#FF0000",
            is_active=True,
            display_order=0,
            team_id=test_team.id,
        )
        test_db_session.add(cat)
        test_db_session.commit()
        test_db_session.refresh(cat)
        return cat

    @pytest.fixture
    def setup(self, test_db_session, test_team, category, test_user):
        """Create 2 series, 2 locations, 5 events, and override config."""
        # Series
        series1 = EventSeries(
            title="Series 1",
            category_id=category.id,
            team_id=test_team.id,
            total_events=3,
        )
        series2 = EventSeries(
            title="Series 2",
            category_id=category.id,
            team_id=test_team.id,
            total_events=2,
        )
        test_db_session.add_all([series1, series2])
        test_db_session.flush()

        # Locations
        nyc = Location(
            name="NYC Venue", city="New York", country="US",
            latitude=40.7128, longitude=-74.0060,
            category_id=category.id, team_id=test_team.id,
        )
        la = Location(
            name="LA Venue", city="Los Angeles", country="US",
            latitude=34.0522, longitude=-118.2437,
            category_id=category.id, team_id=test_team.id,
        )
        test_db_session.add_all([nyc, la])
        test_db_session.flush()

        # Events — all same time (all-day) so same-day events always overlap
        events = []
        for title, evt_date, series, location in [
            ("E1/S1", date(2026, 6, 4), series1, nyc),   # Thursday
            ("E2/S1", date(2026, 6, 5), series1, nyc),   # Friday
            ("E3/S1", date(2026, 6, 6), series1, nyc),   # Saturday
            ("E1/S2", date(2026, 6, 6), series2, la),    # Saturday (same day as E3/S1)
            ("E2/S2", date(2026, 6, 7), series2, la),    # Sunday
        ]:
            e = Event(
                title=title,
                event_date=evt_date,
                start_time=time(10, 0),
                end_time=time(18, 0),
                is_all_day=False,
                status="future",
                attendance="planned",
                travel_required=True,
                category_id=category.id,
                series_id=series.id,
                location_id=location.id,
                team_id=test_team.id,
            )
            events.append(e)
        test_db_session.add_all(events)
        test_db_session.flush()

        # Override conflict rules: consecutive_window_days=0, travel_buffer_days=3
        for key, val in [
            ("consecutive_window_days", 0),
            ("travel_buffer_days", 3),
        ]:
            existing = test_db_session.query(Configuration).filter(
                Configuration.category == "conflict_rules",
                Configuration.key == key,
                Configuration.team_id == test_team.id,
            ).first()
            if existing:
                existing.value_json = {"value": val}
            else:
                test_db_session.add(Configuration(
                    category="conflict_rules",
                    key=key,
                    value_json={"value": val},
                    source=ConfigSource.DATABASE,
                    team_id=test_team.id,
                ))
        test_db_session.commit()

        for e in events:
            test_db_session.refresh(e)

        return {
            "events": events,
            "nyc": nyc,
            "la": la,
            "series1": series1,
            "series2": series2,
        }

    def _count_edges_by_date(self, group):
        """Count conflict edges per day for a conflict group."""
        event_dates = {e["guid"]: e["event_date"] for e in group["events"]}
        edges_by_day = defaultdict(list)
        for edge in group["edges"]:
            date_a = event_dates.get(edge["event_a_guid"])
            date_b = event_dates.get(edge["event_b_guid"])
            for d in {date_a, date_b}:
                if d:
                    edges_by_day[d].append(edge)
        return edges_by_day

    def test_conflict_counts_per_day(self, test_client, setup):
        """Verify exact edge counts per day match the production scenario."""
        response = test_client.get(
            "/api/events/conflicts",
            params={"start_date": "2026-06-04", "end_date": "2026-06-07"},
        )
        assert response.status_code == 200
        data = response.json()

        # One conflict group with all 5 events
        assert data["summary"]["total_groups"] == 1
        group = data["conflict_groups"][0]
        assert len(group["events"]) == 5

        edges_by_day = self._count_edges_by_date(group)

        # Thu (Jun 4): 1 edge — E1/S1 ↔ E1/S2 travel buffer
        assert len(edges_by_day["2026-06-04"]) == 1
        # Fri (Jun 5): 2 edges — E2/S1 ↔ E1/S2, E2/S1 ↔ E2/S2
        assert len(edges_by_day["2026-06-05"]) == 2
        # Sat (Jun 6): 6 edges — time overlap + distance + 4 travel buffers
        assert len(edges_by_day["2026-06-06"]) == 6
        # Sun (Jun 7): 2 edges — E2/S2 ↔ E2/S1, E2/S2 ↔ E3/S1
        assert len(edges_by_day["2026-06-07"]) == 2

    def test_saturday_conflict_types(self, test_client, setup):
        """Saturday (peak day) should have time_overlap, distance, and travel_buffer."""
        response = test_client.get(
            "/api/events/conflicts",
            params={"start_date": "2026-06-04", "end_date": "2026-06-07"},
        )
        group = response.json()["conflict_groups"][0]
        edges_by_day = self._count_edges_by_date(group)

        sat_edges = edges_by_day["2026-06-06"]
        conflict_types = {e["conflict_type"] for e in sat_edges}
        assert "time_overlap" in conflict_types
        assert "distance" in conflict_types
        assert "travel_buffer" in conflict_types

    def test_skip_series2_resolves_all(self, test_client, setup):
        """Skipping both Series 2 events resolves all conflicts."""
        events = setup["events"]
        e1_s2 = events[3]  # E1/S2
        e2_s2 = events[4]  # E2/S2

        # Skip Series 2 events
        response = test_client.post("/api/events/conflicts/resolve", json={
            "group_id": "cg_1",
            "decisions": [
                {"event_guid": e1_s2.guid, "attendance": "skipped"},
                {"event_guid": e2_s2.guid, "attendance": "skipped"},
            ],
        })
        assert response.status_code == 200
        assert response.json()["updated_count"] == 2

        # Re-detect: group should be resolved
        response = test_client.get(
            "/api/events/conflicts",
            params={"start_date": "2026-06-04", "end_date": "2026-06-07"},
        )
        data = response.json()
        assert data["summary"]["total_groups"] == 1
        assert data["summary"]["resolved"] == 1
        assert data["summary"]["unresolved"] == 0
        assert data["conflict_groups"][0]["status"] == "resolved"

    def test_skip_one_event_partially_resolves(self, test_client, setup):
        """Skipping only one Series 2 event should partially resolve."""
        events = setup["events"]
        e1_s2 = events[3]  # E1/S2

        # Skip only E1/S2
        response = test_client.post("/api/events/conflicts/resolve", json={
            "group_id": "cg_1",
            "decisions": [
                {"event_guid": e1_s2.guid, "attendance": "skipped"},
            ],
        })
        assert response.status_code == 200

        # Re-detect: group should be partially_resolved
        # (E3/S1 ↔ E2/S2 travel buffer still unresolved)
        response = test_client.get(
            "/api/events/conflicts",
            params={"start_date": "2026-06-04", "end_date": "2026-06-07"},
        )
        data = response.json()
        group = data["conflict_groups"][0]
        assert group["status"] == "partially_resolved"

    def test_restore_skipped_event_returns_to_unresolved(self, test_client, setup):
        """Restoring a skipped event should return the group to unresolved."""
        events = setup["events"]
        e1_s2 = events[3]
        e2_s2 = events[4]

        # Skip both Series 2 events (resolves)
        test_client.post("/api/events/conflicts/resolve", json={
            "group_id": "cg_1",
            "decisions": [
                {"event_guid": e1_s2.guid, "attendance": "skipped"},
                {"event_guid": e2_s2.guid, "attendance": "skipped"},
            ],
        })

        # Restore E1/S2 (un-resolves)
        test_client.post("/api/events/conflicts/resolve", json={
            "group_id": "cg_1",
            "decisions": [
                {"event_guid": e1_s2.guid, "attendance": "planned"},
            ],
        })

        # Re-detect: group should not be resolved
        response = test_client.get(
            "/api/events/conflicts",
            params={"start_date": "2026-06-04", "end_date": "2026-06-07"},
        )
        data = response.json()
        group = data["conflict_groups"][0]
        assert group["status"] in ("unresolved", "partially_resolved")
