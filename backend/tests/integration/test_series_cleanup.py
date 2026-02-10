"""
Test series cleanup when deleting events.

Issue: Deleting events from a series did not properly handle cleanup:
- Deleting next-to-last event should convert remaining event to standalone
- Deleting last event should clean up deadline entries
- Single event deletion should update series total

Fix: soft_delete now always updates series total and handles cleanup logic.
"""
import pytest
from datetime import date

from backend.src.models import Category


class TestSeriesCleanup:
    """Test series cleanup when deleting events."""

    @pytest.fixture
    def test_category(self, test_db_session, test_team):
        """Create a test category."""
        category = Category(
            name="Test Cleanup Category",
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

    def test_delete_single_event_updates_series_total(self, test_client, test_category):
        """Deleting a single event from a series should update total_events."""
        # Create a series with 3 events
        response = test_client.post(
            "/api/events/series",
            json={
                "title": "Three Day Series",
                "category_guid": test_category.guid,
                "event_dates": ["2026-08-10", "2026-08-11", "2026-08-12"],
            },
        )
        assert response.status_code == 201
        events = response.json()
        assert len(events) == 3

        # All events should show series_total=3
        for event in events:
            assert event["series_total"] == 3

        # Delete the first event (single scope)
        delete_resp = test_client.delete(
            f"/api/events/{events[0]['guid']}",
            params={"scope": "single"},
        )
        assert delete_resp.status_code == 200

        # Remaining events should now show series_total=2
        detail = test_client.get(f"/api/events/{events[1]['guid']}")
        assert detail.status_code == 200
        assert detail.json()["series_total"] == 2

    def test_delete_next_to_last_converts_to_standalone(self, test_client, test_category):
        """Deleting next-to-last event should convert remaining event to standalone."""
        # Create a series with 2 events
        response = test_client.post(
            "/api/events/series",
            json={
                "title": "Two Day Series",
                "category_guid": test_category.guid,
                "event_dates": ["2026-09-10", "2026-09-11"],
                "ticket_required": True,  # Set logistics on series
            },
        )
        assert response.status_code == 201
        events = response.json()
        assert len(events) == 2

        # Both events should be part of series
        for event in events:
            assert event["series_guid"] is not None
            assert event["series_total"] == 2

        # Remember the second event GUID
        remaining_event_guid = events[1]["guid"]

        # Delete the first event
        delete_resp = test_client.delete(
            f"/api/events/{events[0]['guid']}",
            params={"scope": "single"},
        )
        assert delete_resp.status_code == 200

        # The remaining event should now be standalone
        detail = test_client.get(f"/api/events/{remaining_event_guid}")
        assert detail.status_code == 200
        data = detail.json()

        # Should no longer be part of a series
        assert data["series_guid"] is None, "Event should be converted to standalone"
        assert data["sequence_number"] is None, "Sequence number should be cleared"
        assert data["series_total"] is None, "Series total should be None for standalone"

        # Should have inherited logistics from series
        assert data["ticket_required"] is True, "Should retain ticket_required from series"

        # Title should be copied from series
        assert data["title"] == "Two Day Series"

    def test_delete_last_event_cleans_up_deadline(self, test_client, test_category):
        """Deleting all events should soft-delete the deadline entry."""
        # Create a series with 2 events and a deadline
        response = test_client.post(
            "/api/events/series",
            json={
                "title": "Series With Deadline",
                "category_guid": test_category.guid,
                "event_dates": ["2026-10-10", "2026-10-11"],
                "deadline_date": "2026-10-20",
            },
        )
        assert response.status_code == 201
        events = response.json()

        # Should have 3 events (2 regular + 1 deadline)
        assert len(events) == 3
        deadline_events = [e for e in events if e.get("is_deadline")]
        regular_events = [e for e in events if not e.get("is_deadline")]
        assert len(deadline_events) == 1
        assert len(regular_events) == 2

        deadline_guid = deadline_events[0]["guid"]

        # Delete both regular events (scope=all on one of them)
        delete_resp = test_client.delete(
            f"/api/events/{regular_events[0]['guid']}",
            params={"scope": "all"},
        )
        assert delete_resp.status_code == 200

        # The deadline entry should also be soft-deleted
        deadline_detail = test_client.get(f"/api/events/{deadline_guid}")
        # Should be 404 because it's soft-deleted and include_deleted defaults to false
        assert deadline_detail.status_code == 404

        # Can still find it with include_deleted=true
        deadline_detail_with_deleted = test_client.get(
            f"/api/events/{deadline_guid}",
            params={"include_deleted": True},
        )
        assert deadline_detail_with_deleted.status_code == 200
        assert deadline_detail_with_deleted.json()["deleted_at"] is not None

    def test_delete_from_series_excludes_deadline_from_count(
        self, test_client, test_category
    ):
        """Verify deadline entry is not counted when updating series total."""
        # Create a series with 2 events and a deadline
        response = test_client.post(
            "/api/events/series",
            json={
                "title": "Series Count Test",
                "category_guid": test_category.guid,
                "event_dates": ["2026-11-10", "2026-11-11"],
                "deadline_date": "2026-11-20",
            },
        )
        assert response.status_code == 201
        events = response.json()

        regular_events = [e for e in events if not e.get("is_deadline")]
        assert len(regular_events) == 2

        # series_total should be 2 (not 3)
        assert regular_events[0]["series_total"] == 2

        # Delete one regular event
        delete_resp = test_client.delete(
            f"/api/events/{regular_events[0]['guid']}",
            params={"scope": "single"},
        )
        assert delete_resp.status_code == 200

        # The remaining event should now be standalone (series_total was 2, now 1)
        detail = test_client.get(f"/api/events/{regular_events[1]['guid']}")
        data = detail.json()

        # Should be converted to standalone
        assert data["series_guid"] is None
        assert data["series_total"] is None

    def test_convert_to_standalone_preserves_event_overrides(
        self, test_client, test_category, test_db_session, test_team
    ):
        """When converting to standalone, event-level overrides should be preserved."""
        # Create series via API
        response = test_client.post(
            "/api/events/series",
            json={
                "title": "Override Test Series",
                "category_guid": test_category.guid,
                "event_dates": ["2026-12-10", "2026-12-11"],
                "ticket_required": True,  # Series default
            },
        )
        assert response.status_code == 201
        events = response.json()

        # Set explicit override on second event
        update_resp = test_client.patch(
            f"/api/events/{events[1]['guid']}",
            json={"ticket_required": False},  # Override series default
        )
        assert update_resp.status_code == 200

        # Delete first event, converting second to standalone
        delete_resp = test_client.delete(
            f"/api/events/{events[0]['guid']}",
            params={"scope": "single"},
        )
        assert delete_resp.status_code == 200

        # The remaining event (now standalone) should keep its override
        detail = test_client.get(f"/api/events/{events[1]['guid']}")
        data = detail.json()

        assert data["series_guid"] is None, "Should be standalone"
        assert data["ticket_required"] is False, "Should keep event-level override"

    def test_convert_to_standalone_creates_deadline_entry(self, test_client, test_category):
        """When converting to standalone, a deadline entry should be created if deadline exists."""
        # Create a series with 2 events and a deadline
        response = test_client.post(
            "/api/events/series",
            json={
                "title": "Series With Deadline",
                "category_guid": test_category.guid,
                "event_dates": ["2026-12-15", "2026-12-16"],
                "deadline_date": "2026-12-25",
            },
        )
        assert response.status_code == 201
        events = response.json()

        # Should have 3 events (2 regular + 1 deadline)
        regular_events = [e for e in events if not e.get("is_deadline")]
        series_deadline = [e for e in events if e.get("is_deadline")]
        assert len(regular_events) == 2
        assert len(series_deadline) == 1

        remaining_event_guid = regular_events[1]["guid"]
        series_deadline_guid = series_deadline[0]["guid"]

        # Delete the first event
        delete_resp = test_client.delete(
            f"/api/events/{regular_events[0]['guid']}",
            params={"scope": "single"},
        )
        assert delete_resp.status_code == 200

        # The remaining event should be standalone
        detail = test_client.get(f"/api/events/{remaining_event_guid}")
        assert detail.status_code == 200
        data = detail.json()
        assert data["series_guid"] is None, "Event should be standalone"
        assert data["deadline_date"] == "2026-12-25", "Deadline date should be preserved"

        # The series deadline entry should be soft-deleted
        series_deadline_detail = test_client.get(f"/api/events/{series_deadline_guid}")
        assert series_deadline_detail.status_code == 404, "Series deadline should be deleted"

        # A new standalone deadline entry should exist for the remaining event
        # Find it by listing events for that date
        list_resp = test_client.get(
            "/api/events",
            params={"start_date": "2026-12-25", "end_date": "2026-12-25"},
        )
        assert list_resp.status_code == 200
        deadline_events = [e for e in list_resp.json() if e.get("is_deadline")]
        assert len(deadline_events) == 1, "A standalone deadline entry should exist"

        # The standalone deadline should be linked to the remaining event
        standalone_deadline = deadline_events[0]
        assert standalone_deadline["title"] == "Series With Deadline - Deadline"
