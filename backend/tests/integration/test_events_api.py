"""
Integration tests for Events API endpoints.

Tests end-to-end flows for event management:
- Listing events with date range filtering
- Getting event details by GUID
- Statistics endpoint
- Creating single events and series (Phase 5)
- Updating events with scope (Phase 5)
- Soft deleting events with scope (Phase 5)

Issue #39 - Calendar Events feature (Phases 4 & 5)
"""

import pytest
from datetime import date, time

from backend.src.models import Category, Event, EventSeries, Location, Organizer


class TestEventsAPI:
    """Integration tests for Events API endpoints."""

    @pytest.fixture
    def test_category(self, test_db_session):
        """Create a test category."""
        category = Category(
            name="Test Airshow",
            icon="plane",
            color="#3B82F6",
            is_active=True,
            display_order=0,
        )
        test_db_session.add(category)
        test_db_session.commit()
        test_db_session.refresh(category)
        return category

    @pytest.fixture
    def test_events(self, test_db_session, test_category):
        """Create test events."""
        events = []

        # Create standalone events
        for i in range(3):
            event = Event(
                title=f"Test Event {i + 1}",
                event_date=date(2026, 3, 10 + i),
                start_time=time(9, 0),
                end_time=time(17, 0),
                is_all_day=False,
                status="future",
                attendance="planned",
                category_id=test_category.id,
            )
            test_db_session.add(event)
            events.append(event)

        test_db_session.commit()
        for event in events:
            test_db_session.refresh(event)

        return events

    @pytest.fixture
    def test_series(self, test_db_session, test_category):
        """Create a test event series with events."""
        series = EventSeries(
            title="Multi-Day Airshow",
            category_id=test_category.id,
            total_events=3,
            ticket_required=True,
            travel_required=True,
            timeoff_required=False,
        )
        test_db_session.add(series)
        test_db_session.commit()
        test_db_session.refresh(series)

        events = []
        for i in range(3):
            event = Event(
                series_id=series.id,
                sequence_number=i + 1,
                event_date=date(2026, 7, 27 + i),
                start_time=time(8, 0),
                end_time=time(18, 0),
                is_all_day=False,
                status="future",
                attendance="planned",
            )
            test_db_session.add(event)
            events.append(event)

        test_db_session.commit()
        for event in events:
            test_db_session.refresh(event)

        return series, events

    def test_list_events_empty(self, test_client):
        """Test listing events when none exist."""
        response = test_client.get("/api/events")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_events(self, test_client, test_events):
        """Test listing all events."""
        response = test_client.get("/api/events")
        assert response.status_code == 200

        events = response.json()
        assert len(events) >= 3

        # Verify event structure
        event = events[0]
        assert "guid" in event
        assert event["guid"].startswith("evt_")
        assert "title" in event
        assert "event_date" in event
        assert "status" in event
        assert "attendance" in event
        assert "category" in event

    def test_list_events_with_date_range(self, test_client, test_events):
        """Test listing events with date range filter."""
        # Filter to specific dates
        response = test_client.get(
            "/api/events",
            params={
                "start_date": "2026-03-10",
                "end_date": "2026-03-11",
            },
        )
        assert response.status_code == 200

        events = response.json()
        # Should only get events within the date range
        for event in events:
            event_date = event["event_date"]
            assert "2026-03-10" <= event_date <= "2026-03-11"

    def test_list_events_with_category_filter(self, test_client, test_events, test_category):
        """Test listing events filtered by category."""
        response = test_client.get(
            "/api/events",
            params={"category_guid": test_category.guid},
        )
        assert response.status_code == 200

        events = response.json()
        assert len(events) >= 3

        # All events should have the test category
        for event in events:
            if event["category"]:
                assert event["category"]["guid"] == test_category.guid

    def test_list_events_with_status_filter(self, test_client, test_events):
        """Test listing events filtered by status."""
        response = test_client.get(
            "/api/events",
            params={"status": "future"},
        )
        assert response.status_code == 200

        events = response.json()
        for event in events:
            assert event["status"] == "future"

    def test_list_events_with_attendance_filter(self, test_client, test_events):
        """Test listing events filtered by attendance."""
        response = test_client.get(
            "/api/events",
            params={"attendance": "planned"},
        )
        assert response.status_code == 200

        events = response.json()
        for event in events:
            assert event["attendance"] == "planned"

    def test_list_events_ordered_by_date(self, test_client, test_events):
        """Test that events are returned ordered by date."""
        response = test_client.get("/api/events")
        assert response.status_code == 200

        events = response.json()
        if len(events) > 1:
            dates = [event["event_date"] for event in events]
            assert dates == sorted(dates)

    def test_get_event_by_guid(self, test_client, test_events):
        """Test getting event details by GUID."""
        event = test_events[0]

        response = test_client.get(f"/api/events/{event.guid}")
        assert response.status_code == 200

        data = response.json()
        assert data["guid"] == event.guid
        assert data["title"] == event.title
        assert data["event_date"] == str(event.event_date)
        assert data["status"] == event.status
        assert data["attendance"] == event.attendance

        # Detail response should include additional fields
        assert "description" in data
        assert "location" in data
        assert "organizer" in data
        assert "performers" in data
        assert "ticket_required" in data
        assert "travel_required" in data

    def test_get_event_not_found(self, test_client):
        """Test getting non-existent event."""
        response = test_client.get("/api/events/evt_00000000000000000000000001")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_event_invalid_guid(self, test_client):
        """Test getting event with invalid GUID format."""
        response = test_client.get("/api/events/invalid-guid")
        assert response.status_code == 404

    def test_list_series_events(self, test_client, test_series):
        """Test that series events are listed with series info."""
        series, events = test_series

        response = test_client.get("/api/events")
        assert response.status_code == 200

        result = response.json()

        # Find series events
        series_events = [e for e in result if e.get("series_guid")]
        assert len(series_events) >= 3

        for event in series_events:
            assert event["series_guid"] == series.guid
            assert event["sequence_number"] is not None
            assert event["series_total"] == 3
            # Series events should have title from series
            assert event["title"] == "Multi-Day Airshow"

    def test_get_series_event_details(self, test_client, test_series):
        """Test getting details for a series event."""
        series, events = test_series
        event = events[0]

        response = test_client.get(f"/api/events/{event.guid}")
        assert response.status_code == 200

        data = response.json()
        assert data["series_guid"] == series.guid
        assert data["sequence_number"] == 1
        assert data["series_total"] == 3
        assert data["title"] == "Multi-Day Airshow"

        # Should include series details
        assert "series" in data
        assert data["series"]["guid"] == series.guid
        assert data["series"]["title"] == "Multi-Day Airshow"
        assert data["series"]["total_events"] == 3

    def test_get_event_stats(self, test_client, test_events):
        """Test getting event statistics."""
        response = test_client.get("/api/events/stats")
        assert response.status_code == 200

        stats = response.json()
        assert "total_count" in stats
        assert "upcoming_count" in stats
        assert "this_month_count" in stats
        assert "attended_count" in stats

        # With test events, should have at least 3
        assert stats["total_count"] >= 3

    def test_get_event_stats_empty(self, test_client):
        """Test getting stats when no events exist."""
        response = test_client.get("/api/events/stats")
        assert response.status_code == 200

        stats = response.json()
        assert stats["total_count"] == 0
        assert stats["upcoming_count"] == 0
        assert stats["this_month_count"] == 0
        assert stats["attended_count"] == 0


class TestEventsSoftDelete:
    """Tests for soft-deleted events."""

    @pytest.fixture
    def deleted_event(self, test_db_session):
        """Create a soft-deleted event."""
        category = Category(
            name="Deleted Test Category",
            is_active=True,
            display_order=0,
        )
        test_db_session.add(category)
        test_db_session.commit()

        from datetime import datetime

        event = Event(
            title="Deleted Event",
            event_date=date(2026, 5, 15),
            status="cancelled",
            attendance="skipped",
            category_id=category.id,
            deleted_at=datetime.utcnow(),
        )
        test_db_session.add(event)
        test_db_session.commit()
        test_db_session.refresh(event)
        return event

    def test_list_events_excludes_deleted(self, test_client, deleted_event):
        """Test that soft-deleted events are excluded by default."""
        response = test_client.get("/api/events")
        assert response.status_code == 200

        events = response.json()
        guids = [e["guid"] for e in events]
        assert deleted_event.guid not in guids

    def test_list_events_includes_deleted(self, test_client, deleted_event):
        """Test that soft-deleted events can be included."""
        response = test_client.get(
            "/api/events",
            params={"include_deleted": True},
        )
        assert response.status_code == 200

        events = response.json()
        guids = [e["guid"] for e in events]
        assert deleted_event.guid in guids

    def test_get_deleted_event_excluded(self, test_client, deleted_event):
        """Test that soft-deleted event returns 404 by default."""
        response = test_client.get(f"/api/events/{deleted_event.guid}")
        assert response.status_code == 404

    def test_get_deleted_event_included(self, test_client, deleted_event):
        """Test that soft-deleted event can be retrieved."""
        response = test_client.get(
            f"/api/events/{deleted_event.guid}",
            params={"include_deleted": True},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["guid"] == deleted_event.guid
        assert data["deleted_at"] is not None


# =============================================================================
# Phase 5: Create/Update/Delete Tests
# =============================================================================


class TestEventsCreate:
    """Tests for creating events (Phase 5)."""

    @pytest.fixture
    def test_category(self, test_db_session):
        """Create a test category for event creation."""
        category = Category(
            name="Create Test Category",
            icon="star",
            color="#FF5733",
            is_active=True,
            display_order=0,
        )
        test_db_session.add(category)
        test_db_session.commit()
        test_db_session.refresh(category)
        return category

    def test_create_single_event(self, test_client, test_category):
        """Test creating a single standalone event."""
        response = test_client.post(
            "/api/events",
            json={
                "title": "New Test Event",
                "category_guid": test_category.guid,
                "event_date": "2026-04-15",
                "start_time": "10:00:00",
                "end_time": "16:00:00",
                "description": "Test description",
                "status": "future",
                "attendance": "planned",
            },
        )

        assert response.status_code == 201

        data = response.json()
        assert data["guid"].startswith("evt_")
        assert data["title"] == "New Test Event"
        assert data["event_date"] == "2026-04-15"
        assert data["start_time"] == "10:00:00"
        assert data["end_time"] == "16:00:00"
        assert data["description"] == "Test description"
        assert data["status"] == "future"
        assert data["attendance"] == "planned"
        assert data["category"]["guid"] == test_category.guid

    def test_create_event_minimal(self, test_client, test_category):
        """Test creating an event with minimal required fields."""
        response = test_client.post(
            "/api/events",
            json={
                "title": "Minimal Event",
                "category_guid": test_category.guid,
                "event_date": "2026-05-01",
            },
        )

        assert response.status_code == 201

        data = response.json()
        assert data["title"] == "Minimal Event"
        assert data["event_date"] == "2026-05-01"
        # Defaults applied
        assert data["status"] == "future"
        assert data["attendance"] == "planned"
        assert data["is_all_day"] is False

    def test_create_event_all_day(self, test_client, test_category):
        """Test creating an all-day event."""
        response = test_client.post(
            "/api/events",
            json={
                "title": "All Day Event",
                "category_guid": test_category.guid,
                "event_date": "2026-06-01",
                "is_all_day": True,
            },
        )

        assert response.status_code == 201

        data = response.json()
        assert data["is_all_day"] is True
        assert data["start_time"] is None
        assert data["end_time"] is None

    def test_create_event_missing_title(self, test_client, test_category):
        """Test creating event without required title fails."""
        response = test_client.post(
            "/api/events",
            json={
                "category_guid": test_category.guid,
                "event_date": "2026-04-15",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_create_event_invalid_category(self, test_client):
        """Test creating event with invalid category fails."""
        response = test_client.post(
            "/api/events",
            json={
                "title": "Invalid Category Event",
                "category_guid": "cat_00000000000000000000000000",
                "event_date": "2026-04-15",
            },
        )

        assert response.status_code == 400
        assert "Category not found" in response.json()["detail"]

    def test_create_event_series(self, test_client, test_category):
        """Test creating a multi-day event series."""
        response = test_client.post(
            "/api/events/series",
            json={
                "title": "Multi-Day Conference",
                "category_guid": test_category.guid,
                "event_dates": ["2026-08-10", "2026-08-11", "2026-08-12"],
                "start_time": "09:00:00",
                "end_time": "17:00:00",
                "ticket_required": True,
            },
        )

        assert response.status_code == 201

        events = response.json()
        assert len(events) == 3

        # Verify series info
        for i, event in enumerate(events):
            assert event["title"] == "Multi-Day Conference"
            assert event["series_guid"] is not None
            assert event["sequence_number"] == i + 1
            assert event["series_total"] == 3

        # Events should be ordered by date
        dates = [e["event_date"] for e in events]
        assert dates == ["2026-08-10", "2026-08-11", "2026-08-12"]

    def test_create_series_too_few_dates(self, test_client, test_category):
        """Test creating series with less than 2 dates fails."""
        response = test_client.post(
            "/api/events/series",
            json={
                "title": "Single Day Event",
                "category_guid": test_category.guid,
                "event_dates": ["2026-08-10"],
            },
        )

        assert response.status_code == 422  # Validation error


class TestEventsUpdate:
    """Tests for updating events (Phase 5)."""

    @pytest.fixture
    def update_category(self, test_db_session):
        """Create a test category."""
        category = Category(
            name="Update Test Category",
            icon="edit",
            color="#00FF00",
            is_active=True,
            display_order=0,
        )
        test_db_session.add(category)
        test_db_session.commit()
        test_db_session.refresh(category)
        return category

    @pytest.fixture
    def update_event(self, test_db_session, update_category):
        """Create an event for update testing."""
        event = Event(
            title="Event to Update",
            event_date=date(2026, 9, 15),
            start_time=time(10, 0),
            end_time=time(18, 0),
            status="future",
            attendance="planned",
            category_id=update_category.id,
        )
        test_db_session.add(event)
        test_db_session.commit()
        test_db_session.refresh(event)
        return event

    @pytest.fixture
    def update_series(self, test_db_session, update_category):
        """Create a series for update testing."""
        series = EventSeries(
            title="Series to Update",
            category_id=update_category.id,
            total_events=3,
        )
        test_db_session.add(series)
        test_db_session.commit()
        test_db_session.refresh(series)

        events = []
        for i in range(3):
            event = Event(
                series_id=series.id,
                sequence_number=i + 1,
                event_date=date(2026, 10, 10 + i),
                start_time=time(9, 0),
                end_time=time(17, 0),
                status="future",
                attendance="planned",
            )
            test_db_session.add(event)
            events.append(event)

        test_db_session.commit()
        for event in events:
            test_db_session.refresh(event)

        return series, events

    def test_update_event_single_field(self, test_client, update_event):
        """Test updating a single field on an event."""
        response = test_client.patch(
            f"/api/events/{update_event.guid}",
            json={"attendance": "attended"},
        )

        assert response.status_code == 200

        data = response.json()
        assert data["attendance"] == "attended"
        # Other fields unchanged
        assert data["title"] == "Event to Update"
        assert data["status"] == "future"

    def test_update_event_multiple_fields(self, test_client, update_event):
        """Test updating multiple fields at once."""
        response = test_client.patch(
            f"/api/events/{update_event.guid}",
            json={
                "title": "Updated Event Title",
                "status": "confirmed",
                "attendance": "planned",
                "description": "Added description",
            },
        )

        assert response.status_code == 200

        data = response.json()
        assert data["title"] == "Updated Event Title"
        assert data["status"] == "confirmed"
        assert data["description"] == "Added description"

    def test_update_event_not_found(self, test_client):
        """Test updating non-existent event fails."""
        response = test_client.patch(
            "/api/events/evt_00000000000000000000000000",
            json={"title": "New Title"},
        )

        assert response.status_code == 404

    def test_update_series_event_single_scope(self, test_client, update_series):
        """Test updating a series event with single scope."""
        series, events = update_series
        first_event = events[0]

        response = test_client.patch(
            f"/api/events/{first_event.guid}",
            json={
                "attendance": "attended",
                "scope": "single",
            },
        )

        assert response.status_code == 200

        data = response.json()
        assert data["attendance"] == "attended"

        # Check other events are not updated
        response2 = test_client.get(f"/api/events/{events[1].guid}")
        assert response2.json()["attendance"] == "planned"

    def test_update_series_event_all_scope(self, test_client, update_series):
        """Test updating all events in a series."""
        series, events = update_series
        first_event = events[0]

        response = test_client.patch(
            f"/api/events/{first_event.guid}",
            json={
                "status": "confirmed",
                "scope": "all",
            },
        )

        assert response.status_code == 200

        # Verify all events in series updated
        for event in events:
            response = test_client.get(f"/api/events/{event.guid}")
            assert response.json()["status"] == "confirmed"

    def test_update_series_location_syncs_to_all_events(
        self, test_client, test_db_session, update_category, update_series
    ):
        """Test that updating location on a series event syncs to ALL events.

        Location is a series-level property and should always sync across
        all events, regardless of scope.
        """
        series, events = update_series

        # Create a location
        location = Location(
            name="Test Venue",
            city="Test City",
            country="USA",
            category_id=update_category.id,
            is_known=True,
        )
        test_db_session.add(location)
        test_db_session.commit()
        test_db_session.refresh(location)

        # Update location on middle event with scope="single"
        # Expectation: location syncs to ALL events despite single scope
        middle_event = events[1]
        response = test_client.patch(
            f"/api/events/{middle_event.guid}",
            json={
                "location_guid": location.guid,
                "scope": "single",  # Single scope, but location should sync to all
            },
        )

        assert response.status_code == 200

        # Verify ALL events in series have the location
        for event in events:
            response = test_client.get(f"/api/events/{event.guid}")
            data = response.json()
            assert data["location"] is not None, f"Event {event.guid} missing location"
            assert data["location"]["guid"] == location.guid
            assert data["location"]["name"] == "Test Venue"

    def test_update_series_location_clear_syncs_to_all_events(
        self, test_client, test_db_session, update_category
    ):
        """Test that clearing location on a series event syncs to ALL events."""
        # Create a location
        location = Location(
            name="Location to Clear",
            city="Clear City",
            country="USA",
            category_id=update_category.id,
            is_known=True,
        )
        test_db_session.add(location)
        test_db_session.commit()
        test_db_session.refresh(location)

        # Create series with location set
        series = EventSeries(
            title="Series with Location",
            category_id=update_category.id,
            location_id=location.id,
            total_events=3,
        )
        test_db_session.add(series)
        test_db_session.commit()
        test_db_session.refresh(series)

        events = []
        for i in range(3):
            event = Event(
                series_id=series.id,
                sequence_number=i + 1,
                event_date=date(2026, 11, 10 + i),
                location_id=location.id,  # All start with location
                status="future",
                attendance="planned",
            )
            test_db_session.add(event)
            events.append(event)

        test_db_session.commit()
        for event in events:
            test_db_session.refresh(event)

        # Clear location on first event with scope="single"
        first_event = events[0]
        response = test_client.patch(
            f"/api/events/{first_event.guid}",
            json={
                "location_guid": None,  # Clear location
                "scope": "single",
            },
        )

        assert response.status_code == 200

        # Verify ALL events have location cleared
        for event in events:
            response = test_client.get(f"/api/events/{event.guid}")
            data = response.json()
            assert data["location"] is None, f"Event {event.guid} location not cleared"

    def test_update_series_organizer_syncs_to_all_events(
        self, test_client, test_db_session, update_category, update_series
    ):
        """Test that updating organizer on a series event syncs to ALL events.

        Organizer is a series-level property and should always sync across
        all events, regardless of scope.
        """
        series, events = update_series

        # Create an organizer for the category
        organizer = Organizer(
            name="Test Organizer",
            category_id=update_category.id,
            ticket_required_default=True,
        )
        test_db_session.add(organizer)
        test_db_session.commit()
        test_db_session.refresh(organizer)

        # Update organizer on middle event with scope="single"
        # Expectation: organizer syncs to ALL events despite single scope
        middle_event = events[1]
        response = test_client.patch(
            f"/api/events/{middle_event.guid}",
            json={
                "organizer_guid": organizer.guid,
                "scope": "single",  # Single scope, but organizer should sync to all
            },
        )

        assert response.status_code == 200

        # Verify ALL events in series have the organizer
        for event in events:
            response = test_client.get(f"/api/events/{event.guid}")
            data = response.json()
            assert data["organizer"] is not None, f"Event {event.guid} missing organizer"
            assert data["organizer"]["guid"] == organizer.guid
            assert data["organizer"]["name"] == "Test Organizer"

    def test_update_series_organizer_clear_syncs_to_all_events(
        self, test_client, test_db_session, update_category
    ):
        """Test that clearing organizer on a series event syncs to ALL events."""
        # Create an organizer
        organizer = Organizer(
            name="Organizer to Clear",
            category_id=update_category.id,
            ticket_required_default=False,
        )
        test_db_session.add(organizer)
        test_db_session.commit()
        test_db_session.refresh(organizer)

        # Create series with organizer set
        series = EventSeries(
            title="Series with Organizer",
            category_id=update_category.id,
            organizer_id=organizer.id,
            total_events=3,
        )
        test_db_session.add(series)
        test_db_session.commit()
        test_db_session.refresh(series)

        events = []
        for i in range(3):
            event = Event(
                series_id=series.id,
                sequence_number=i + 1,
                event_date=date(2026, 11, 20 + i),
                organizer_id=organizer.id,  # All start with organizer
                status="future",
                attendance="planned",
            )
            test_db_session.add(event)
            events.append(event)

        test_db_session.commit()
        for event in events:
            test_db_session.refresh(event)

        # Clear organizer on first event with scope="single"
        first_event = events[0]
        response = test_client.patch(
            f"/api/events/{first_event.guid}",
            json={
                "organizer_guid": None,  # Clear organizer
                "scope": "single",
            },
        )

        assert response.status_code == 200

        # Verify ALL events have organizer cleared
        for event in events:
            response = test_client.get(f"/api/events/{event.guid}")
            data = response.json()
            assert data["organizer"] is None, f"Event {event.guid} organizer not cleared"


class TestEventsDelete:
    """Tests for deleting events (Phase 5)."""

    @pytest.fixture
    def delete_category(self, test_db_session):
        """Create a test category."""
        category = Category(
            name="Delete Test Category",
            is_active=True,
            display_order=0,
        )
        test_db_session.add(category)
        test_db_session.commit()
        test_db_session.refresh(category)
        return category

    @pytest.fixture
    def delete_event(self, test_db_session, delete_category):
        """Create an event for delete testing."""
        event = Event(
            title="Event to Delete",
            event_date=date(2026, 11, 15),
            status="future",
            attendance="planned",
            category_id=delete_category.id,
        )
        test_db_session.add(event)
        test_db_session.commit()
        test_db_session.refresh(event)
        return event

    @pytest.fixture
    def delete_series(self, test_db_session, delete_category):
        """Create a series for delete testing."""
        series = EventSeries(
            title="Series to Delete",
            category_id=delete_category.id,
            total_events=3,
        )
        test_db_session.add(series)
        test_db_session.commit()
        test_db_session.refresh(series)

        events = []
        for i in range(3):
            event = Event(
                series_id=series.id,
                sequence_number=i + 1,
                event_date=date(2026, 12, 10 + i),
                status="future",
                attendance="planned",
            )
            test_db_session.add(event)
            events.append(event)

        test_db_session.commit()
        for event in events:
            test_db_session.refresh(event)

        return series, events

    def test_delete_single_event(self, test_client, delete_event):
        """Test soft deleting a single event."""
        response = test_client.delete(f"/api/events/{delete_event.guid}")

        assert response.status_code == 200

        data = response.json()
        assert data["deleted_at"] is not None

        # Event should not appear in list
        list_response = test_client.get("/api/events")
        guids = [e["guid"] for e in list_response.json()]
        assert delete_event.guid not in guids

    def test_delete_event_not_found(self, test_client):
        """Test deleting non-existent event fails."""
        response = test_client.delete("/api/events/evt_00000000000000000000000000")
        assert response.status_code == 404

    def test_delete_series_event_single_scope(self, test_client, delete_series):
        """Test deleting single event from series."""
        series, events = delete_series
        first_event = events[0]

        response = test_client.delete(
            f"/api/events/{first_event.guid}",
            params={"scope": "single"},
        )

        assert response.status_code == 200

        # First event deleted
        get_response = test_client.get(f"/api/events/{first_event.guid}")
        assert get_response.status_code == 404

        # Other events still exist
        for event in events[1:]:
            get_response = test_client.get(f"/api/events/{event.guid}")
            assert get_response.status_code == 200

    def test_delete_series_event_all_scope(self, test_client, delete_series):
        """Test deleting all events in series."""
        series, events = delete_series
        first_event = events[0]

        response = test_client.delete(
            f"/api/events/{first_event.guid}",
            params={"scope": "all"},
        )

        assert response.status_code == 200

        # All events should be deleted
        for event in events:
            get_response = test_client.get(f"/api/events/{event.guid}")
            assert get_response.status_code == 404

    def test_restore_deleted_event(self, test_client, delete_event):
        """Test restoring a soft-deleted event."""
        # First delete
        delete_response = test_client.delete(f"/api/events/{delete_event.guid}")
        assert delete_response.status_code == 200

        # Then restore
        restore_response = test_client.post(f"/api/events/{delete_event.guid}/restore")
        assert restore_response.status_code == 200

        data = restore_response.json()
        assert data["deleted_at"] is None

        # Event should appear in list again
        list_response = test_client.get("/api/events")
        guids = [e["guid"] for e in list_response.json()]
        assert delete_event.guid in guids
