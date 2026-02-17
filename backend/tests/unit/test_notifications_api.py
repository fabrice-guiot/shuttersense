"""
Integration tests for notification API endpoints.

Issue #114 - PWA with Push Notifications (Phase 13 — T052)
Tests all notification endpoints: subscribe, unsubscribe, status, preferences,
list, unread-count, mark-as-read, deadline-check, and vapid-key.
"""

import json
from datetime import datetime

import pytest

from backend.src.models.notification import Notification
from backend.src.models.push_subscription import PushSubscription
from backend.src.models.user import User, UserStatus
from backend.src.models.team import Team


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def create_notification(test_db_session, test_team, test_user):
    """Factory for creating test notifications."""
    def _create(
        category="job_failure",
        title="Test Notification",
        body="Test body",
        data=None,
        read_at=None,
        user=None,
        team=None,
    ):
        notification = Notification(
            team_id=(team or test_team).id,
            user_id=(user or test_user).id,
            category=category,
            title=title,
            body=body,
            data=data,
            read_at=read_at,
        )
        test_db_session.add(notification)
        test_db_session.commit()
        test_db_session.refresh(notification)
        return notification
    return _create


@pytest.fixture
def create_subscription(test_db_session, test_team, test_user):
    """Factory for creating push subscriptions."""
    _counter = [0]

    def _create(endpoint=None, user=None, team=None):
        _counter[0] += 1
        sub = PushSubscription(
            team_id=(team or test_team).id,
            user_id=(user or test_user).id,
            endpoint=endpoint or f"https://push.example.com/{_counter[0]}",
            p256dh_key="test-p256dh-key",
            auth_key="test-auth-key",
            device_name="Test Device",
        )
        test_db_session.add(sub)
        test_db_session.commit()
        test_db_session.refresh(sub)
        return sub
    return _create


# ============================================================================
# Test: POST /subscribe
# ============================================================================


class TestSubscribeEndpoint:
    """Tests for POST /api/notifications/subscribe."""

    def test_creates_subscription(self, test_client):
        """Should create a push subscription and return 201."""
        response = test_client.post(
            "/api/notifications/subscribe",
            json={
                "endpoint": "https://push.example.com/new",
                "p256dh_key": "test-key-p256dh",
                "auth_key": "test-key-auth",
                "device_name": "Chrome",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["guid"].startswith("sub_")
        assert data["device_name"] == "Chrome"

    def test_rejects_missing_fields(self, test_client):
        """Should return 422 for missing required fields."""
        response = test_client.post(
            "/api/notifications/subscribe",
            json={"endpoint": "https://push.example.com/new"},
        )
        assert response.status_code == 422


# ============================================================================
# Test: DELETE /subscribe
# ============================================================================


class TestUnsubscribeEndpoint:
    """Tests for DELETE /api/notifications/subscribe."""

    def test_removes_subscription(self, test_client, create_subscription):
        """Should remove subscription and return 204."""
        sub = create_subscription(endpoint="https://push.example.com/remove")
        response = test_client.request(
            "DELETE",
            "/api/notifications/subscribe",
            json={"endpoint": "https://push.example.com/remove"},
        )
        assert response.status_code == 204

    def test_returns_404_for_unknown_endpoint(self, test_client):
        """Should return 404 when endpoint doesn't exist."""
        response = test_client.request(
            "DELETE",
            "/api/notifications/subscribe",
            json={"endpoint": "https://nonexistent.com"},
        )
        assert response.status_code == 404


# ============================================================================
# Test: DELETE /subscribe/{guid}
# ============================================================================


class TestUnsubscribeByGuidEndpoint:
    """Tests for DELETE /api/notifications/subscribe/{guid}."""

    def test_removes_subscription_by_guid(self, test_client, create_subscription):
        """Should remove subscription and return 204."""
        sub = create_subscription()
        response = test_client.delete(
            f"/api/notifications/subscribe/{sub.guid}"
        )
        assert response.status_code == 204

    def test_returns_404_for_unknown_guid(self, test_client):
        """Should return 404 when GUID doesn't match any subscription."""
        response = test_client.delete(
            "/api/notifications/subscribe/sub_00000000000000000000000000"
        )
        assert response.status_code == 404

    def test_returns_404_for_invalid_guid(self, test_client):
        """Should return 404 for malformed GUID."""
        response = test_client.delete(
            "/api/notifications/subscribe/not-a-guid"
        )
        assert response.status_code == 404


# ============================================================================
# Test: GET /status
# ============================================================================


class TestStatusEndpoint:
    """Tests for GET /api/notifications/status."""

    def test_returns_status(self, test_client):
        """Should return notification enabled status and subscriptions."""
        response = test_client.get("/api/notifications/status")
        assert response.status_code == 200
        data = response.json()
        assert "notifications_enabled" in data
        assert "subscriptions" in data


# ============================================================================
# Test: GET /preferences
# ============================================================================


class TestGetPreferencesEndpoint:
    """Tests for GET /api/notifications/preferences."""

    def test_returns_preferences(self, test_client):
        """Should return notification preferences with all fields."""
        response = test_client.get("/api/notifications/preferences")
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "job_failures" in data
        assert "deadline_days_before" in data
        assert "timezone" in data
        assert "retention_days" in data


# ============================================================================
# Test: PUT /preferences
# ============================================================================


class TestUpdatePreferencesEndpoint:
    """Tests for PUT /api/notifications/preferences."""

    def test_updates_preferences(self, test_client):
        """Should update and return updated preferences."""
        response = test_client.put(
            "/api/notifications/preferences",
            json={"enabled": True, "deadline_days_before": 7},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["deadline_days_before"] == 7

    def test_rejects_invalid_timezone(self, test_client):
        """Should return 400 for invalid timezone."""
        response = test_client.put(
            "/api/notifications/preferences",
            json={"timezone": "Invalid/Timezone"},
        )
        assert response.status_code == 400


# ============================================================================
# Test: GET /notifications (list)
# ============================================================================


class TestListNotificationsEndpoint:
    """Tests for GET /api/notifications."""

    def test_returns_paginated_list(self, test_client, create_notification):
        """Should return paginated notification list."""
        for i in range(3):
            create_notification(title=f"Notification {i}")

        response = test_client.get(
            "/api/notifications", params={"limit": 2, "offset": 0}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3

    def test_filters_by_category(self, test_client, create_notification):
        """Should filter by category parameter."""
        create_notification(category="job_failure")
        create_notification(category="deadline")

        response = test_client.get(
            "/api/notifications", params={"category": "deadline"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["category"] == "deadline"

    def test_unread_only_filter(self, test_client, create_notification):
        """Should filter to unread notifications."""
        create_notification()
        create_notification(read_at=datetime.utcnow())

        response = test_client.get(
            "/api/notifications", params={"unread_only": True}
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1


# ============================================================================
# Test: GET /unread-count
# ============================================================================


class TestUnreadCountEndpoint:
    """Tests for GET /api/notifications/unread-count."""

    def test_returns_unread_count(self, test_client, create_notification):
        """Should return the count of unread notifications."""
        create_notification()
        create_notification()
        create_notification(read_at=datetime.utcnow())

        response = test_client.get("/api/notifications/unread-count")
        assert response.status_code == 200
        assert response.json()["unread_count"] == 2


# ============================================================================
# Test: POST /{guid}/read
# ============================================================================


class TestMarkAsReadEndpoint:
    """Tests for POST /api/notifications/{guid}/read."""

    def test_marks_notification_as_read(self, test_client, create_notification):
        """Should mark notification as read and return updated record."""
        notification = create_notification()
        response = test_client.post(
            f"/api/notifications/{notification.guid}/read"
        )
        assert response.status_code == 200
        assert response.json()["read_at"] is not None

    def test_returns_404_for_invalid_guid(self, test_client):
        """Should return 404 for non-existent notification."""
        response = test_client.post(
            "/api/notifications/ntf_00000000000000000000000000/read"
        )
        assert response.status_code == 404


# ============================================================================
# Test: POST /mark-all-read
# ============================================================================


class TestMarkAllReadEndpoint:
    """Tests for POST /api/notifications/mark-all-read."""

    def test_marks_all_unread(self, test_client, create_notification):
        """Should mark all unread notifications and return updated_count."""
        create_notification(title="N1")
        create_notification(title="N2")
        create_notification(title="N3", read_at=datetime.utcnow())

        response = test_client.post("/api/notifications/mark-all-read")
        assert response.status_code == 200
        data = response.json()
        assert data["updated_count"] == 2

    def test_returns_zero_when_all_read(self, test_client, create_notification):
        """Should return 0 when no unread notifications exist."""
        create_notification(title="Read", read_at=datetime.utcnow())

        response = test_client.post("/api/notifications/mark-all-read")
        assert response.status_code == 200
        assert response.json()["updated_count"] == 0

    def test_returns_zero_when_no_notifications(self, test_client):
        """Should return 0 when user has no notifications."""
        response = test_client.post("/api/notifications/mark-all-read")
        assert response.status_code == 200
        assert response.json()["updated_count"] == 0


# ============================================================================
# Test: POST /deadline-check
# ============================================================================


class TestDeadlineCheckEndpoint:
    """Tests for POST /api/notifications/deadline-check."""

    def test_returns_sent_count(self, test_client):
        """Should return sent_count (0 when no events)."""
        response = test_client.post("/api/notifications/deadline-check")
        assert response.status_code == 200
        data = response.json()
        assert "sent_count" in data
        assert data["sent_count"] == 0


# ============================================================================
# Test: GET /vapid-key
# ============================================================================


class TestVapidKeyEndpoint:
    """Tests for GET /api/notifications/vapid-key."""

    def test_returns_vapid_key_or_503(self, test_client):
        """Should return VAPID key if configured, or 503 if not."""
        response = test_client.get("/api/notifications/vapid-key")
        # Accept either 200 (configured) or 503 (not configured in test env)
        assert response.status_code in (200, 503)


# ============================================================================
# Test: Multi-tenant isolation
# ============================================================================


class TestMultiTenantIsolation:
    """Tests for cross-team notification isolation."""

    def test_cross_team_notification_returns_404(
        self, test_client, test_db_session, create_notification
    ):
        """Cross-team notification GUID should return 404, not 403."""
        # Create notification for a different team
        other_team = Team(name="Other Team", slug="other-team-iso", is_active=True)
        test_db_session.add(other_team)
        test_db_session.commit()

        other_user = User(
            team_id=other_team.id,
            email="other@iso.com",
            display_name="Other",
            status=UserStatus.ACTIVE,
        )
        test_db_session.add(other_user)
        test_db_session.commit()

        other_notification = create_notification(
            user=other_user, team=other_team
        )

        # Try to mark it as read from the test_client (different team)
        response = test_client.post(
            f"/api/notifications/{other_notification.guid}/read"
        )
        assert response.status_code == 404
