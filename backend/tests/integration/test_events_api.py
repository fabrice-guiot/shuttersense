"""
Integration tests for Events API endpoints.

Tests end-to-end flows for event management:
- Listing events with date range filtering
- Getting event details by GUID
- Statistics endpoint
- Creating single events and series (Phase 5)
- Updating events with scope (Phase 5)
- Soft deleting events with scope (Phase 5)
- Deadline entry management (Issue #68)

Issue #39 - Calendar Events feature (Phases 4 & 5)
Issue #68 - Make Event Deadline appear in the Calendar view
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

    def test_create_event_with_organizer_ticket_default(
        self, test_client, test_db_session, test_category
    ):
        """Test that organizer's ticket_required_default is applied to new events."""
        # Create an organizer with ticket_required_default=True
        organizer = Organizer(
            name="Ticket Required Organizer",
            category_id=test_category.id,
            ticket_required_default=True,
        )
        test_db_session.add(organizer)
        test_db_session.commit()
        test_db_session.refresh(organizer)

        # Create event without explicitly setting ticket_required
        response = test_client.post(
            "/api/events",
            json={
                "title": "Event with Organizer Default",
                "category_guid": test_category.guid,
                "event_date": "2026-05-15",
                "organizer_guid": organizer.guid,
                # ticket_required is NOT explicitly set
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Verify ticket_required was applied from organizer default
        detail_response = test_client.get(f"/api/events/{data['guid']}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["ticket_required"] is True

    def test_create_event_with_location_logistics_defaults(
        self, test_client, test_db_session, test_category
    ):
        """Test that location's travel/timeoff defaults are applied to new events."""
        # Create a location with logistics defaults
        location = Location(
            name="Remote Venue",
            city="Remote City",
            country="USA",
            category_id=test_category.id,
            is_known=True,
            timeoff_required_default=True,
            travel_required_default=True,
        )
        test_db_session.add(location)
        test_db_session.commit()
        test_db_session.refresh(location)

        # Create event without explicitly setting logistics
        response = test_client.post(
            "/api/events",
            json={
                "title": "Event at Remote Venue",
                "category_guid": test_category.guid,
                "event_date": "2026-05-20",
                "location_guid": location.guid,
                # timeoff_required and travel_required are NOT explicitly set
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Verify logistics were applied from location defaults
        detail_response = test_client.get(f"/api/events/{data['guid']}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["timeoff_required"] is True
        assert detail["travel_required"] is True

    def test_create_event_explicit_overrides_defaults(
        self, test_client, test_db_session, test_category
    ):
        """Test that explicit False overrides organizer/location defaults."""
        # Create organizer with default=True
        organizer = Organizer(
            name="Ticket Default Organizer",
            category_id=test_category.id,
            ticket_required_default=True,
        )
        test_db_session.add(organizer)

        # Create location with defaults=True
        location = Location(
            name="Default Location",
            city="Default City",
            country="USA",
            category_id=test_category.id,
            is_known=True,
            travel_required_default=True,
        )
        test_db_session.add(location)
        test_db_session.commit()
        test_db_session.refresh(organizer)
        test_db_session.refresh(location)

        # Create event with explicit False values
        response = test_client.post(
            "/api/events",
            json={
                "title": "Event with Explicit Overrides",
                "category_guid": test_category.guid,
                "event_date": "2026-05-25",
                "organizer_guid": organizer.guid,
                "location_guid": location.guid,
                "ticket_required": False,  # Explicit override
                "travel_required": False,  # Explicit override
            },
        )

        assert response.status_code == 201
        data = response.json()

        # Verify explicit values were respected (not overridden by defaults)
        detail_response = test_client.get(f"/api/events/{data['guid']}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["ticket_required"] is False
        assert detail["travel_required"] is False


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


# =============================================================================
# Issue #68: Deadline Entry Tests
# =============================================================================


class TestEventsDeadline:
    """Tests for deadline entry functionality (Issue #68).

    Deadline entries are special Event records with is_deadline=True that
    appear in the calendar to represent series/event deadlines.
    """

    @pytest.fixture
    def deadline_category(self, test_db_session):
        """Create a test category for deadline tests."""
        category = Category(
            name="Deadline Test Category",
            icon="clock",
            color="#FF0000",
            is_active=True,
            display_order=0,
        )
        test_db_session.add(category)
        test_db_session.commit()
        test_db_session.refresh(category)
        return category

    @pytest.fixture
    def deadline_organizer(self, test_db_session, deadline_category):
        """Create a test organizer for deadline tests."""
        organizer = Organizer(
            name="Deadline Test Organizer",
            category_id=deadline_category.id,
        )
        test_db_session.add(organizer)
        test_db_session.commit()
        test_db_session.refresh(organizer)
        return organizer

    @pytest.fixture
    def deadline_location(self, test_db_session, deadline_category):
        """Create a test location for deadline tests."""
        location = Location(
            name="Deadline Test Location",
            city="Test City",
            country="USA",
            category_id=deadline_category.id,
            is_known=True,
        )
        test_db_session.add(location)
        test_db_session.commit()
        test_db_session.refresh(location)
        return location

    # -------------------------------------------------------------------------
    # T011: Test deadline entry creation when deadline_date is set
    # -------------------------------------------------------------------------

    def test_create_series_with_deadline_creates_deadline_entry(
        self, test_client, deadline_category
    ):
        """Test that creating a series with deadline creates a deadline entry."""
        response = test_client.post(
            "/api/events/series",
            json={
                "title": "Series With Deadline",
                "category_guid": deadline_category.guid,
                "event_dates": ["2026-09-01", "2026-09-02", "2026-09-03"],
                "deadline_date": "2026-09-15",
                "deadline_time": "17:00:00",
            },
        )

        assert response.status_code == 201
        events = response.json()

        # Should have 4 events: 3 series events + 1 deadline entry
        assert len(events) == 4

        # Find the deadline entry
        deadline_entries = [e for e in events if e.get("is_deadline") is True]
        assert len(deadline_entries) == 1

        deadline = deadline_entries[0]
        assert deadline["title"] == "Series With Deadline - Deadline"
        assert deadline["event_date"] == "2026-09-15"
        assert deadline["start_time"] == "17:00:00"
        assert deadline["is_deadline"] is True

    # -------------------------------------------------------------------------
    # T012: Test deadline entry update when deadline changes
    # -------------------------------------------------------------------------

    def test_update_series_deadline_updates_deadline_entry(
        self, test_client, deadline_category
    ):
        """Test that updating series deadline updates the deadline entry."""
        # Create series with deadline
        create_response = test_client.post(
            "/api/events/series",
            json={
                "title": "Series to Update Deadline",
                "category_guid": deadline_category.guid,
                "event_dates": ["2026-10-01", "2026-10-02"],
                "deadline_date": "2026-10-15",
                "deadline_time": "12:00:00",
            },
        )
        assert create_response.status_code == 201
        events = create_response.json()

        # Get series GUID from first event
        series_guid = events[0]["series_guid"]

        # Update deadline via series endpoint
        update_response = test_client.patch(
            f"/api/events/series/{series_guid}",
            json={
                "deadline_date": "2026-10-20",
                "deadline_time": "18:00:00",
            },
        )
        assert update_response.status_code == 200

        # List events and verify deadline entry updated
        list_response = test_client.get(
            "/api/events",
            params={
                "start_date": "2026-10-01",
                "end_date": "2026-10-31",
            },
        )
        assert list_response.status_code == 200
        updated_events = list_response.json()

        deadline_entries = [e for e in updated_events if e.get("is_deadline") is True]
        assert len(deadline_entries) == 1

        deadline = deadline_entries[0]
        assert deadline["event_date"] == "2026-10-20"
        assert deadline["start_time"] == "18:00:00"

    # -------------------------------------------------------------------------
    # T013: Test deadline entry deletion when deadline is cleared
    # -------------------------------------------------------------------------

    def test_clear_series_deadline_deletes_deadline_entry(
        self, test_client, deadline_category
    ):
        """Test that clearing deadline removes the deadline entry."""
        # Create series with deadline
        create_response = test_client.post(
            "/api/events/series",
            json={
                "title": "Series to Clear Deadline",
                "category_guid": deadline_category.guid,
                "event_dates": ["2026-11-01", "2026-11-02"],
                "deadline_date": "2026-11-15",
            },
        )
        assert create_response.status_code == 201
        events = create_response.json()

        # Verify deadline entry exists
        deadline_entries = [e for e in events if e.get("is_deadline") is True]
        assert len(deadline_entries) == 1

        # Get series GUID
        series_guid = events[0]["series_guid"]

        # Clear deadline via series endpoint
        update_response = test_client.patch(
            f"/api/events/series/{series_guid}",
            json={"deadline_date": None},
        )
        assert update_response.status_code == 200

        # Verify deadline entry is deleted
        list_response = test_client.get(
            "/api/events",
            params={
                "start_date": "2026-11-01",
                "end_date": "2026-11-30",
            },
        )
        assert list_response.status_code == 200
        updated_events = list_response.json()

        # Should only have 2 regular events, no deadline entry
        deadline_entries = [e for e in updated_events if e.get("is_deadline") is True]
        assert len(deadline_entries) == 0
        assert len(updated_events) == 2

    # -------------------------------------------------------------------------
    # T014: Test deadline entry has correct fields
    # -------------------------------------------------------------------------

    def test_deadline_entry_has_correct_fields(
        self, test_client, deadline_category, deadline_organizer, deadline_location
    ):
        """Test that deadline entry has correct fields (no location, has organizer)."""
        # Create series with deadline, location, and organizer
        create_response = test_client.post(
            "/api/events/series",
            json={
                "title": "Series With Full Details",
                "category_guid": deadline_category.guid,
                "event_dates": ["2026-12-01", "2026-12-02"],
                "deadline_date": "2026-12-15",
                "deadline_time": "23:59:00",
                "location_guid": deadline_location.guid,
                "organizer_guid": deadline_organizer.guid,
            },
        )
        assert create_response.status_code == 201
        events = create_response.json()

        # Find deadline entry
        deadline_entries = [e for e in events if e.get("is_deadline") is True]
        assert len(deadline_entries) == 1
        deadline = deadline_entries[0]

        # Get full details
        detail_response = test_client.get(f"/api/events/{deadline['guid']}")
        assert detail_response.status_code == 200
        detail = detail_response.json()

        # Verify correct fields
        assert detail["is_deadline"] is True
        assert detail["title"] == "Series With Full Details - Deadline"
        assert detail["event_date"] == "2026-12-15"
        assert detail["start_time"] == "23:59:00"
        assert detail["category"]["guid"] == deadline_category.guid

        # Deadline should have organizer but NO location
        assert detail["organizer"] is not None
        assert detail["organizer"]["guid"] == deadline_organizer.guid
        assert detail["location"] is None  # Deadline entries don't have location

    # -------------------------------------------------------------------------
    # T015: Test standalone event deadline entry
    # -------------------------------------------------------------------------

    def test_standalone_event_deadline_creates_entry(
        self, test_client, deadline_category
    ):
        """Test that setting deadline on standalone event creates deadline entry."""
        # Create standalone event without deadline
        create_response = test_client.post(
            "/api/events",
            json={
                "title": "Standalone Event",
                "category_guid": deadline_category.guid,
                "event_date": "2027-01-15",
            },
        )
        assert create_response.status_code == 201
        event = create_response.json()
        event_guid = event["guid"]

        # Update to add deadline
        update_response = test_client.patch(
            f"/api/events/{event_guid}",
            json={
                "deadline_date": "2027-01-30",
                "deadline_time": "18:00:00",
            },
        )
        assert update_response.status_code == 200

        # List events and find deadline entry
        list_response = test_client.get(
            "/api/events",
            params={
                "start_date": "2027-01-01",
                "end_date": "2027-01-31",
            },
        )
        assert list_response.status_code == 200
        events = list_response.json()

        # Should have 2 events: standalone + deadline entry
        assert len(events) == 2

        deadline_entries = [e for e in events if e.get("is_deadline") is True]
        assert len(deadline_entries) == 1

        deadline = deadline_entries[0]
        assert deadline["title"] == "Standalone Event - Deadline"
        assert deadline["event_date"] == "2027-01-30"
        assert deadline["start_time"] == "18:00:00"

    def test_standalone_event_deadline_clear_deletes_entry(
        self, test_client, deadline_category
    ):
        """Test that clearing deadline on standalone event deletes deadline entry."""
        # Create standalone event with deadline
        create_response = test_client.post(
            "/api/events",
            json={
                "title": "Standalone With Deadline",
                "category_guid": deadline_category.guid,
                "event_date": "2027-02-15",
                "deadline_date": "2027-02-28",
                "deadline_time": "12:00:00",
            },
        )
        assert create_response.status_code == 201
        event = create_response.json()
        event_guid = event["guid"]

        # Verify deadline entry exists
        list_response = test_client.get(
            "/api/events",
            params={
                "start_date": "2027-02-01",
                "end_date": "2027-02-28",
            },
        )
        events = list_response.json()
        assert len(events) == 2  # Event + deadline entry

        # Clear deadline
        update_response = test_client.patch(
            f"/api/events/{event_guid}",
            json={"deadline_date": None},
        )
        assert update_response.status_code == 200

        # Verify deadline entry deleted
        list_response = test_client.get(
            "/api/events",
            params={
                "start_date": "2027-02-01",
                "end_date": "2027-02-28",
            },
        )
        events = list_response.json()
        assert len(events) == 1  # Only original event
        assert events[0]["is_deadline"] is False

    # -------------------------------------------------------------------------
    # T016: Test deadline_time syncs across all events in series
    # -------------------------------------------------------------------------

    def test_deadline_time_syncs_across_series_events(
        self, test_client, deadline_category
    ):
        """Test that deadline_time syncs to all events in series."""
        # Create series with deadline
        create_response = test_client.post(
            "/api/events/series",
            json={
                "title": "Series for Time Sync",
                "category_guid": deadline_category.guid,
                "event_dates": ["2027-03-01", "2027-03-02", "2027-03-03"],
                "deadline_date": "2027-03-15",
                "deadline_time": "14:00:00",
            },
        )
        assert create_response.status_code == 201
        events = create_response.json()

        # All regular events should have deadline_time synced
        regular_events = [e for e in events if e.get("is_deadline") is not True]
        assert len(regular_events) == 3

        for event in regular_events:
            detail_response = test_client.get(f"/api/events/{event['guid']}")
            detail = detail_response.json()
            assert detail["deadline_date"] == "2027-03-15"
            assert detail["deadline_time"] == "14:00:00"

    def test_update_deadline_time_syncs_across_series(
        self, test_client, deadline_category
    ):
        """Test that updating deadline_time via event syncs across series."""
        # Create series with deadline
        create_response = test_client.post(
            "/api/events/series",
            json={
                "title": "Series for Time Update",
                "category_guid": deadline_category.guid,
                "event_dates": ["2027-04-01", "2027-04-02"],
                "deadline_date": "2027-04-15",
                "deadline_time": "09:00:00",
            },
        )
        assert create_response.status_code == 201
        events = create_response.json()

        # Get first regular event
        regular_events = [e for e in events if e.get("is_deadline") is not True]
        first_event = regular_events[0]

        # Update deadline_time via first event
        update_response = test_client.patch(
            f"/api/events/{first_event['guid']}",
            json={"deadline_time": "21:00:00"},
        )
        assert update_response.status_code == 200

        # Verify all events have updated deadline_time
        for event in regular_events:
            detail_response = test_client.get(f"/api/events/{event['guid']}")
            detail = detail_response.json()
            assert detail["deadline_time"] == "21:00:00"

        # Verify deadline entry also updated
        deadline_events = [e for e in events if e.get("is_deadline") is True]
        if deadline_events:
            deadline_detail = test_client.get(f"/api/events/{deadline_events[0]['guid']}")
            assert deadline_detail.json()["start_time"] == "21:00:00"

    # -------------------------------------------------------------------------
    # T017: Test deadline entry excluded from series sequence numbering
    # -------------------------------------------------------------------------

    def test_deadline_entry_has_no_sequence_number(
        self, test_client, deadline_category
    ):
        """Test that deadline entry has sequence_number=None."""
        # Create series with deadline
        create_response = test_client.post(
            "/api/events/series",
            json={
                "title": "Series for Sequence Test",
                "category_guid": deadline_category.guid,
                "event_dates": ["2027-05-01", "2027-05-02", "2027-05-03"],
                "deadline_date": "2027-05-15",
            },
        )
        assert create_response.status_code == 201
        events = create_response.json()

        # Find deadline entry
        deadline_entries = [e for e in events if e.get("is_deadline") is True]
        assert len(deadline_entries) == 1

        deadline = deadline_entries[0]
        assert deadline["sequence_number"] is None

        # Regular events should have sequence numbers 1, 2, 3
        regular_events = [e for e in events if e.get("is_deadline") is not True]
        sequence_numbers = sorted([e["sequence_number"] for e in regular_events])
        assert sequence_numbers == [1, 2, 3]

    def test_deadline_entry_not_counted_in_series_total(
        self, test_client, deadline_category
    ):
        """Test that deadline entry is not counted in series_total."""
        # Create series with 3 events + deadline
        create_response = test_client.post(
            "/api/events/series",
            json={
                "title": "Series Total Test",
                "category_guid": deadline_category.guid,
                "event_dates": ["2027-06-01", "2027-06-02", "2027-06-03"],
                "deadline_date": "2027-06-15",
            },
        )
        assert create_response.status_code == 201
        events = create_response.json()

        # Should have 4 events total (3 regular + 1 deadline)
        assert len(events) == 4

        # But series_total should be 3 (excludes deadline)
        regular_events = [e for e in events if e.get("is_deadline") is not True]
        for event in regular_events:
            assert event["series_total"] == 3

    # -------------------------------------------------------------------------
    # T030: Test PATCH rejection on deadline entry (Phase 4 - Protection)
    # -------------------------------------------------------------------------

    def test_patch_deadline_entry_returns_403(
        self, test_client, deadline_category
    ):
        """Test that PATCH on deadline entry returns 403 Forbidden."""
        # Create series with deadline
        create_response = test_client.post(
            "/api/events/series",
            json={
                "title": "Protected Deadline Series",
                "category_guid": deadline_category.guid,
                "event_dates": ["2027-07-01", "2027-07-02"],
                "deadline_date": "2027-07-15",
            },
        )
        assert create_response.status_code == 201
        events = create_response.json()

        # Find deadline entry
        deadline_entries = [e for e in events if e.get("is_deadline") is True]
        assert len(deadline_entries) == 1
        deadline_guid = deadline_entries[0]["guid"]
        series_guid = deadline_entries[0]["series_guid"]

        # Try to PATCH the deadline entry
        update_response = test_client.patch(
            f"/api/events/{deadline_guid}",
            json={"title": "Modified Deadline"},
        )

        # Should return 403 Forbidden
        assert update_response.status_code == 403
        detail = update_response.json()["detail"]
        assert "Cannot modify deadline entry" in detail["message"]
        assert detail["series_guid"] == series_guid

    def test_patch_standalone_deadline_entry_returns_403(
        self, test_client, deadline_category
    ):
        """Test that PATCH on standalone event deadline entry returns 403."""
        # Create standalone event with deadline
        create_response = test_client.post(
            "/api/events",
            json={
                "title": "Standalone with Protected Deadline",
                "category_guid": deadline_category.guid,
                "event_date": "2027-08-01",
                "deadline_date": "2027-08-15",
            },
        )
        assert create_response.status_code == 201
        event = create_response.json()
        parent_event_guid = event["guid"]

        # Find deadline entry
        list_response = test_client.get(
            "/api/events",
            params={
                "start_date": "2027-08-01",
                "end_date": "2027-08-31",
            },
        )
        events = list_response.json()
        deadline_entries = [e for e in events if e.get("is_deadline") is True]
        assert len(deadline_entries) == 1
        deadline_guid = deadline_entries[0]["guid"]

        # Try to PATCH the deadline entry
        update_response = test_client.patch(
            f"/api/events/{deadline_guid}",
            json={"title": "Modified Standalone Deadline"},
        )

        # Should return 403 Forbidden
        assert update_response.status_code == 403
        detail = update_response.json()["detail"]
        assert "Cannot modify deadline entry" in detail["message"]
        assert detail["parent_event_guid"] == parent_event_guid

    # -------------------------------------------------------------------------
    # T031: Test DELETE rejection on deadline entry (Phase 4 - Protection)
    # -------------------------------------------------------------------------

    def test_delete_deadline_entry_returns_403(
        self, test_client, deadline_category
    ):
        """Test that DELETE on deadline entry returns 403 Forbidden."""
        # Create series with deadline
        create_response = test_client.post(
            "/api/events/series",
            json={
                "title": "Delete Protected Series",
                "category_guid": deadline_category.guid,
                "event_dates": ["2027-09-01", "2027-09-02"],
                "deadline_date": "2027-09-15",
            },
        )
        assert create_response.status_code == 201
        events = create_response.json()

        # Find deadline entry
        deadline_entries = [e for e in events if e.get("is_deadline") is True]
        assert len(deadline_entries) == 1
        deadline_guid = deadline_entries[0]["guid"]
        series_guid = deadline_entries[0]["series_guid"]

        # Try to DELETE the deadline entry
        delete_response = test_client.delete(f"/api/events/{deadline_guid}")

        # Should return 403 Forbidden
        assert delete_response.status_code == 403
        detail = delete_response.json()["detail"]
        assert "Cannot modify deadline entry" in detail["message"]
        assert detail["series_guid"] == series_guid

    def test_delete_standalone_deadline_entry_returns_403(
        self, test_client, deadline_category
    ):
        """Test that DELETE on standalone event deadline entry returns 403."""
        # Create standalone event with deadline
        create_response = test_client.post(
            "/api/events",
            json={
                "title": "Standalone Delete Protected",
                "category_guid": deadline_category.guid,
                "event_date": "2027-10-01",
                "deadline_date": "2027-10-15",
            },
        )
        assert create_response.status_code == 201
        event = create_response.json()
        parent_event_guid = event["guid"]

        # Find deadline entry
        list_response = test_client.get(
            "/api/events",
            params={
                "start_date": "2027-10-01",
                "end_date": "2027-10-31",
            },
        )
        events = list_response.json()
        deadline_entries = [e for e in events if e.get("is_deadline") is True]
        assert len(deadline_entries) == 1
        deadline_guid = deadline_entries[0]["guid"]

        # Try to DELETE the deadline entry
        delete_response = test_client.delete(f"/api/events/{deadline_guid}")

        # Should return 403 Forbidden
        assert delete_response.status_code == 403
        detail = delete_response.json()["detail"]
        assert "Cannot modify deadline entry" in detail["message"]
        assert detail["parent_event_guid"] == parent_event_guid

    # -------------------------------------------------------------------------
    # T039: Test GET /api/events includes deadline entries (Phase 5 - Visibility)
    # -------------------------------------------------------------------------

    def test_list_events_includes_deadlines_by_default(
        self, test_client, deadline_category
    ):
        """Test that GET /api/events includes deadline entries by default."""
        # Create series with deadline
        create_response = test_client.post(
            "/api/events/series",
            json={
                "title": "Visibility Test Series",
                "category_guid": deadline_category.guid,
                "event_dates": ["2027-11-01", "2027-11-02"],
                "deadline_date": "2027-11-15",
            },
        )
        assert create_response.status_code == 201

        # List events without specifying include_deadlines (should default to true)
        list_response = test_client.get(
            "/api/events",
            params={
                "start_date": "2027-11-01",
                "end_date": "2027-11-30",
            },
        )
        assert list_response.status_code == 200
        events = list_response.json()

        # Should include deadline entry
        deadline_entries = [e for e in events if e.get("is_deadline") is True]
        assert len(deadline_entries) == 1

        # Should also include regular events
        regular_events = [e for e in events if e.get("is_deadline") is not True]
        assert len(regular_events) == 2

    def test_list_events_exclude_deadlines_parameter(
        self, test_client, deadline_category
    ):
        """Test that include_deadlines=false excludes deadline entries."""
        # Create series with deadline
        create_response = test_client.post(
            "/api/events/series",
            json={
                "title": "Exclude Deadlines Test",
                "category_guid": deadline_category.guid,
                "event_dates": ["2027-12-01", "2027-12-02"],
                "deadline_date": "2027-12-15",
            },
        )
        assert create_response.status_code == 201

        # List events with include_deadlines=false
        list_response = test_client.get(
            "/api/events",
            params={
                "start_date": "2027-12-01",
                "end_date": "2027-12-31",
                "include_deadlines": False,
            },
        )
        assert list_response.status_code == 200
        events = list_response.json()

        # Should NOT include deadline entries
        deadline_entries = [e for e in events if e.get("is_deadline") is True]
        assert len(deadline_entries) == 0

        # Should still include regular events
        assert len(events) == 2
        for event in events:
            assert event["is_deadline"] is False

    def test_list_events_include_deadlines_true(
        self, test_client, deadline_category
    ):
        """Test that include_deadlines=true explicitly includes deadline entries."""
        # Create series with deadline
        create_response = test_client.post(
            "/api/events/series",
            json={
                "title": "Include Deadlines True Test",
                "category_guid": deadline_category.guid,
                "event_dates": ["2028-01-01", "2028-01-02"],
                "deadline_date": "2028-01-15",
            },
        )
        assert create_response.status_code == 201

        # List events with include_deadlines=true
        list_response = test_client.get(
            "/api/events",
            params={
                "start_date": "2028-01-01",
                "end_date": "2028-01-31",
                "include_deadlines": True,
            },
        )
        assert list_response.status_code == 200
        events = list_response.json()

        # Should include deadline entry
        deadline_entries = [e for e in events if e.get("is_deadline") is True]
        assert len(deadline_entries) == 1

        # Total should be 3 (2 regular + 1 deadline)
        assert len(events) == 3

    # -------------------------------------------------------------------------
    # T040: Test GET /api/events/{guid} on deadline entry shows series reference
    # -------------------------------------------------------------------------

    def test_get_deadline_entry_shows_series_reference(
        self, test_client, deadline_category
    ):
        """Test that GET /api/events/{guid} on deadline entry shows series_guid."""
        # Create series with deadline
        create_response = test_client.post(
            "/api/events/series",
            json={
                "title": "Series Reference Test",
                "category_guid": deadline_category.guid,
                "event_dates": ["2028-02-01", "2028-02-02"],
                "deadline_date": "2028-02-15",
            },
        )
        assert create_response.status_code == 201
        events = create_response.json()

        # Get series GUID from first regular event
        regular_events = [e for e in events if e.get("is_deadline") is not True]
        series_guid = regular_events[0]["series_guid"]

        # Find deadline entry
        deadline_entries = [e for e in events if e.get("is_deadline") is True]
        assert len(deadline_entries) == 1
        deadline_guid = deadline_entries[0]["guid"]

        # Get deadline entry details
        detail_response = test_client.get(f"/api/events/{deadline_guid}")
        assert detail_response.status_code == 200
        detail = detail_response.json()

        # Verify series reference is present
        assert detail["is_deadline"] is True
        assert detail["series_guid"] == series_guid
        assert detail["title"] == "Series Reference Test - Deadline"

    def test_get_standalone_deadline_entry_shows_no_series(
        self, test_client, deadline_category
    ):
        """Test that GET on standalone deadline entry has no series_guid."""
        # Create standalone event with deadline
        create_response = test_client.post(
            "/api/events",
            json={
                "title": "Standalone Series Ref Test",
                "category_guid": deadline_category.guid,
                "event_date": "2028-03-01",
                "deadline_date": "2028-03-15",
            },
        )
        assert create_response.status_code == 201

        # Find deadline entry
        list_response = test_client.get(
            "/api/events",
            params={
                "start_date": "2028-03-01",
                "end_date": "2028-03-31",
            },
        )
        events = list_response.json()
        deadline_entries = [e for e in events if e.get("is_deadline") is True]
        assert len(deadline_entries) == 1
        deadline_guid = deadline_entries[0]["guid"]

        # Get deadline entry details
        detail_response = test_client.get(f"/api/events/{deadline_guid}")
        assert detail_response.status_code == 200
        detail = detail_response.json()

        # Verify no series reference (standalone event deadline)
        assert detail["is_deadline"] is True
        assert detail["series_guid"] is None
        assert detail["title"] == "Standalone Series Ref Test - Deadline"
