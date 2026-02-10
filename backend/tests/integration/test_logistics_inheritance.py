"""
Test to verify series event logistics inheritance.

Issue: Logistics fields (ticket_required, timeoff_required, travel_required) were not
properly inherited from series when viewing/editing series events.

Fix: build_event_detail_response now preserves the inherited values from
build_event_response instead of overwriting them with raw NULL values.
"""
import pytest
from datetime import date

from backend.src.models import Category, Event, EventSeries


class TestSeriesLogisticsInheritance:
    """Test series event logistics inheritance after fix."""

    @pytest.fixture
    def test_category(self, test_db_session, test_team):
        """Create a test category."""
        category = Category(
            name="Test Logistics Category",
            icon="plane",
            color="#3B82F6",
            is_active=True,
            display_order=0,
            team_id=test_team.id,
        )
        test_db_session.add(category)
        test_db_session.commit()
        test_db_session.refresh(category)
        return category

    def test_series_event_logistics_inheritance(self, test_client, test_category):
        """
        Verify that:
        1. Series events inherit logistics from series (not NULL)
        2. Event detail response shows inherited values
        3. After editing, event stores explicit value
        """
        # Create a series with ticket_required=True
        response = test_client.post(
            "/api/events/series",
            json={
                "title": "Test Series",
                "category_guid": test_category.guid,
                "event_dates": ["2026-09-10", "2026-09-11"],
                "ticket_required": True,
                "timeoff_required": True,
                "travel_required": False,
            },
        )
        assert response.status_code == 201
        events = response.json()

        # Get the first event's GUID
        event_guid = events[0]["guid"]

        # Fetch event detail - should show inherited values
        detail = test_client.get(f"/api/events/{event_guid}")
        assert detail.status_code == 200
        data = detail.json()

        # Verify inherited values are shown (not NULL)
        assert data["ticket_required"] is True, "ticket_required should be inherited from series"
        assert data["timeoff_required"] is True, "timeoff_required should be inherited from series"
        assert data["travel_required"] is False, "travel_required should be inherited from series"

        # Now update the event with explicit values
        update_resp = test_client.patch(
            f"/api/events/{event_guid}",
            json={
                "ticket_required": False,  # Override inherited value
            },
        )
        assert update_resp.status_code == 200

        # Verify update persisted
        detail2 = test_client.get(f"/api/events/{event_guid}")
        data2 = detail2.json()
        assert data2["ticket_required"] is False, "ticket_required should be updated to False"
        # Other fields still inherit
        assert data2["timeoff_required"] is True

    def test_standalone_event_logistics_not_affected(self, test_client, test_category):
        """Verify standalone events still work correctly (no regression)."""
        # Create standalone event with explicit logistics
        response = test_client.post(
            "/api/events",
            json={
                "title": "Standalone Event",
                "category_guid": test_category.guid,
                "event_date": "2026-10-15",
                "ticket_required": True,
                "timeoff_required": False,
            },
        )
        assert response.status_code == 201
        event_guid = response.json()["guid"]

        # Verify detail shows correct values
        detail = test_client.get(f"/api/events/{event_guid}")
        data = detail.json()
        assert data["ticket_required"] is True
        assert data["timeoff_required"] is False

        # Update and verify
        update_resp = test_client.patch(
            f"/api/events/{event_guid}",
            json={"ticket_required": False},
        )
        assert update_resp.status_code == 200

        detail2 = test_client.get(f"/api/events/{event_guid}")
        assert detail2.json()["ticket_required"] is False

    def test_series_with_fixture_events_inherit_logistics(
        self, test_client, test_db_session, test_category, test_team
    ):
        """
        Test with manually created series/events (like existing fixtures).
        This verifies the inheritance works even when events are created
        directly in DB without the API.
        """
        # Create series with logistics values
        series = EventSeries(
            title="Fixture Series",
            category_id=test_category.id,
            total_events=2,
            ticket_required=True,
            travel_required=True,
            timeoff_required=False,
            team_id=test_team.id,
        )
        test_db_session.add(series)
        test_db_session.commit()
        test_db_session.refresh(series)

        # Create events with NULL logistics (inheritance pattern)
        events = []
        for i in range(2):
            event = Event(
                series_id=series.id,
                sequence_number=i + 1,
                event_date=date(2026, 11, 15 + i),
                status="future",
                attendance="planned",
                team_id=test_team.id,
                # Logistics explicitly NULL (inherit from series)
                ticket_required=None,
                timeoff_required=None,
                travel_required=None,
            )
            test_db_session.add(event)
            events.append(event)

        test_db_session.commit()
        for event in events:
            test_db_session.refresh(event)

        # Verify detail response shows inherited values
        detail = test_client.get(f"/api/events/{events[0].guid}")
        data = detail.json()

        # These should be inherited from series, not NULL
        assert data["ticket_required"] is True, "Should inherit ticket_required=True from series"
        assert data["travel_required"] is True, "Should inherit travel_required=True from series"
        assert data["timeoff_required"] is False, "Should inherit timeoff_required=False from series"

    def test_series_logistics_status_and_dates_transmitted(self, test_client, test_category):
        """
        Verify that logistics status and date fields from series creation
        are properly transmitted to individual events.
        """
        # Create a series with logistics status and dates
        response = test_client.post(
            "/api/events/series",
            json={
                "title": "Status Date Test Series",
                "category_guid": test_category.guid,
                "event_dates": ["2026-12-20", "2026-12-21"],
                "ticket_required": True,
                "ticket_status": "purchased",
                "ticket_purchase_date": "2026-10-15",
                "timeoff_required": True,
                "timeoff_status": "approved",
                "timeoff_booking_date": "2026-09-01",
                "travel_required": True,
                "travel_status": "booked",
                "travel_booking_date": "2026-11-01",
            },
        )
        assert response.status_code == 201
        events = response.json()
        assert len(events) == 2

        # Check first event has all the status/date fields
        event_guid = events[0]["guid"]
        detail = test_client.get(f"/api/events/{event_guid}")
        assert detail.status_code == 200
        data = detail.json()

        # Verify logistics requirements are inherited from series
        assert data["ticket_required"] is True
        assert data["timeoff_required"] is True
        assert data["travel_required"] is True

        # Verify logistics status fields are transmitted
        assert data["ticket_status"] == "purchased", "ticket_status should be transmitted from series"
        assert data["timeoff_status"] == "approved", "timeoff_status should be transmitted from series"
        assert data["travel_status"] == "booked", "travel_status should be transmitted from series"

        # Verify logistics date fields are transmitted
        assert data["ticket_purchase_date"] == "2026-10-15", "ticket_purchase_date should be transmitted from series"
        assert data["timeoff_booking_date"] == "2026-09-01", "timeoff_booking_date should be transmitted from series"
        assert data["travel_booking_date"] == "2026-11-01", "travel_booking_date should be transmitted from series"
