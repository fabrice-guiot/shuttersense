"""
Unit tests for NotificationService.

Issue #114 - PWA with Push Notifications (Phase 13 — T050)
Tests notification CRUD, push delivery, preference management,
orchestration flow, and subscription cleanup.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

from backend.src.models.notification import Notification
from backend.src.models.push_subscription import PushSubscription
from backend.src.models.user import User, UserStatus
from backend.src.models.team import Team
from backend.src.services.notification_service import (
    NotificationService,
    DEFAULT_PREFERENCES,
    PushGoneError,
    PushDeliveryError,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def notification_service(test_db_session):
    """Create a NotificationService with test VAPID config."""
    return NotificationService(
        db=test_db_session,
        vapid_private_key="test-private-key",
        vapid_claims={"sub": "mailto:test@example.com"},
    )


@pytest.fixture
def create_notification(test_db_session, test_team, test_user):
    """Factory for creating test notification records."""
    def _create(
        category="job_failure",
        title="Test Title",
        body="Test body",
        data=None,
        read_at=None,
        user=None,
    ):
        notification = Notification(
            team_id=test_team.id,
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
    """Factory for creating test push subscriptions."""
    _counter = [0]

    def _create(user=None, endpoint=None):
        _counter[0] += 1
        sub = PushSubscription(
            team_id=test_team.id,
            user_id=(user or test_user).id,
            endpoint=endpoint or f"https://push.example.com/sub/{_counter[0]}",
            p256dh_key="test-p256dh-key",
            auth_key="test-auth-key",
            device_name="Test Device",
        )
        test_db_session.add(sub)
        test_db_session.commit()
        test_db_session.refresh(sub)
        return sub
    return _create


@pytest.fixture
def enabled_user(test_db_session, test_user):
    """Set up a user with notifications enabled."""
    test_user.preferences_json = json.dumps({
        "notifications": {
            "enabled": True,
            "job_failures": True,
            "inflection_points": True,
            "agent_status": True,
            "deadline": True,
            "retry_warning": False,
            "deadline_days_before": 3,
            "timezone": "UTC",
            "retention_days": 30,
        }
    })
    test_db_session.commit()
    test_db_session.refresh(test_user)
    return test_user


# ============================================================================
# Test: create_notification
# ============================================================================


class TestCreateNotification:
    """Tests for NotificationService.create_notification."""

    def test_creates_notification_record(
        self, notification_service, test_team, test_user
    ):
        """Should create a notification in the database."""
        notification = notification_service.create_notification(
            team_id=test_team.id,
            user_id=test_user.id,
            category="job_failure",
            title="Test",
            body="Test body",
        )
        assert notification.id is not None
        assert notification.guid.startswith("ntf_")
        assert notification.team_id == test_team.id
        assert notification.user_id == test_user.id
        assert notification.category == "job_failure"
        assert notification.read_at is None

    def test_stores_data_json(
        self, notification_service, test_team, test_user
    ):
        """Should store JSONB data payload."""
        data = {"url": "/tools", "job_guid": "job_123"}
        notification = notification_service.create_notification(
            team_id=test_team.id,
            user_id=test_user.id,
            category="job_failure",
            title="Test",
            body="Body",
            data=data,
        )
        assert notification.data["url"] == "/tools"
        assert notification.data["job_guid"] == "job_123"

    def test_truncates_long_title(
        self, notification_service, test_team, test_user
    ):
        """Should truncate title to 200 characters."""
        long_title = "A" * 300
        notification = notification_service.create_notification(
            team_id=test_team.id,
            user_id=test_user.id,
            category="job_failure",
            title=long_title,
            body="Body",
        )
        assert len(notification.title) == 200

    def test_truncates_long_body(
        self, notification_service, test_team, test_user
    ):
        """Should truncate body to 500 characters."""
        long_body = "B" * 600
        notification = notification_service.create_notification(
            team_id=test_team.id,
            user_id=test_user.id,
            category="job_failure",
            title="Title",
            body=long_body,
        )
        assert len(notification.body) == 500


# ============================================================================
# Test: deliver_push
# ============================================================================


class TestDeliverPush:
    """Tests for NotificationService.deliver_push."""

    def test_returns_zero_with_no_subscriptions(
        self, notification_service, test_user, test_team
    ):
        """Should return 0 when user has no push subscriptions."""
        count = notification_service.deliver_push(
            user_id=test_user.id,
            team_id=test_team.id,
            payload={"title": "Test"},
        )
        assert count == 0

    @patch("backend.src.services.notification_service.NotificationService._send_push")
    def test_delivers_to_all_subscriptions(
        self, mock_send, notification_service, test_user, test_team,
        create_subscription,
    ):
        """Should deliver to all user subscriptions and return success count."""
        create_subscription()
        create_subscription()
        count = notification_service.deliver_push(
            user_id=test_user.id,
            team_id=test_team.id,
            payload={"title": "Test"},
        )
        assert count == 2
        assert mock_send.call_count == 2

    @patch("backend.src.services.notification_service.NotificationService._send_push")
    def test_removes_subscription_on_410_gone(
        self, mock_send, notification_service, test_user, test_team,
        create_subscription, test_db_session,
    ):
        """Should delete subscription when push returns 410 Gone."""
        sub = create_subscription()
        mock_send.side_effect = PushGoneError(sub.endpoint)

        count = notification_service.deliver_push(
            user_id=test_user.id,
            team_id=test_team.id,
            payload={"title": "Test"},
        )
        assert count == 0
        # Verify subscription was removed
        remaining = test_db_session.query(PushSubscription).filter(
            PushSubscription.id == sub.id
        ).first()
        assert remaining is None

    @patch("backend.src.services.notification_service.NotificationService._send_push")
    def test_continues_on_delivery_error(
        self, mock_send, notification_service, test_user, test_team,
        create_subscription,
    ):
        """Should continue delivering to other subscriptions on error."""
        create_subscription()
        create_subscription()
        mock_send.side_effect = [
            PushDeliveryError("timeout"),
            None,  # Second succeeds
        ]
        count = notification_service.deliver_push(
            user_id=test_user.id,
            team_id=test_team.id,
            payload={"title": "Test"},
        )
        assert count == 1


# ============================================================================
# Test: Preferences
# ============================================================================


class TestPreferences:
    """Tests for notification preference management."""

    def test_get_default_preferences(self, notification_service):
        """Should return all default preference values."""
        defaults = notification_service.get_default_preferences()
        assert defaults["enabled"] is False
        assert defaults["job_failures"] is True
        assert defaults["retry_warning"] is False
        assert defaults["deadline_days_before"] == 3
        assert defaults["timezone"] == "UTC"
        assert defaults["retention_days"] == 30

    def test_get_user_preferences_returns_defaults_for_new_user(
        self, notification_service, test_user
    ):
        """Should return defaults when user has no stored preferences."""
        prefs = notification_service.get_user_preferences(test_user)
        assert prefs == DEFAULT_PREFERENCES

    def test_get_user_preferences_merges_with_defaults(
        self, notification_service, test_db_session, test_user
    ):
        """Should merge stored preferences with defaults for missing keys."""
        test_user.preferences_json = json.dumps({
            "notifications": {"enabled": True, "job_failures": False}
        })
        test_db_session.commit()

        prefs = notification_service.get_user_preferences(test_user)
        assert prefs["enabled"] is True
        assert prefs["job_failures"] is False
        # Defaults should fill missing keys
        assert prefs["inflection_points"] is True
        assert prefs["deadline_days_before"] == 3

    def test_update_preferences_partial(
        self, notification_service, test_user
    ):
        """Should update only specified keys."""
        result = notification_service.update_preferences(
            test_user, {"enabled": True, "deadline_days_before": 7}
        )
        assert result["enabled"] is True
        assert result["deadline_days_before"] == 7
        # Other keys unchanged from defaults
        assert result["job_failures"] is True

    def test_update_preferences_ignores_unknown_keys(
        self, notification_service, test_user
    ):
        """Should ignore keys not in DEFAULT_PREFERENCES."""
        result = notification_service.update_preferences(
            test_user, {"unknown_key": "value", "enabled": True}
        )
        assert "unknown_key" not in result
        assert result["enabled"] is True


# ============================================================================
# Test: check_preference
# ============================================================================


class TestCheckPreference:
    """Tests for NotificationService.check_preference."""

    def test_returns_false_when_master_toggle_off(
        self, notification_service, test_user
    ):
        """Should return False when notifications are disabled."""
        assert notification_service.check_preference(test_user, "job_failure") is False

    def test_returns_true_when_enabled(
        self, notification_service, enabled_user
    ):
        """Should return True when master toggle and category are on."""
        assert notification_service.check_preference(enabled_user, "job_failure") is True

    def test_returns_false_for_disabled_category(
        self, notification_service, enabled_user
    ):
        """Should return False when category is explicitly disabled."""
        # retry_warning is disabled by default
        assert notification_service.check_preference(enabled_user, "retry_warning") is False

    def test_returns_false_for_unknown_category(
        self, notification_service, enabled_user
    ):
        """Should return False for unknown category names."""
        assert notification_service.check_preference(enabled_user, "nonexistent") is False


# ============================================================================
# Test: send_notification (orchestration)
# ============================================================================


class TestSendNotification:
    """Tests for send_notification orchestration flow."""

    @patch("backend.src.services.notification_service.NotificationService.deliver_push")
    def test_creates_record_and_delivers_push(
        self, mock_deliver, notification_service, enabled_user, test_team,
    ):
        """Should create notification record and deliver push when enabled."""
        mock_deliver.return_value = 1
        notification = notification_service.send_notification(
            user=enabled_user,
            team_id=test_team.id,
            category="job_failure",
            title="Test",
            body="Test body",
        )
        assert notification is not None
        assert notification.guid.startswith("ntf_")
        mock_deliver.assert_called_once()

    def test_returns_none_when_preference_disabled(
        self, notification_service, test_user, test_team,
    ):
        """Should return None when notifications are disabled."""
        notification = notification_service.send_notification(
            user=test_user,
            team_id=test_team.id,
            category="job_failure",
            title="Test",
            body="Test body",
        )
        assert notification is None

    @patch("backend.src.services.notification_service.NotificationService.deliver_push")
    def test_includes_notification_guid_in_push_payload(
        self, mock_deliver, notification_service, enabled_user, test_team,
    ):
        """Should include notification_guid in the push payload data."""
        mock_deliver.return_value = 1
        custom_payload = {
            "title": "Test",
            "body": "Body",
            "data": {"url": "/test"},
        }
        notification_service.send_notification(
            user=enabled_user,
            team_id=test_team.id,
            category="job_failure",
            title="Test",
            body="Body",
            push_payload=custom_payload,
        )
        # Verify notification_guid was added to payload data
        call_payload = mock_deliver.call_args[1]["payload"] if mock_deliver.call_args[1] else mock_deliver.call_args[0][2]
        assert "notification_guid" in call_payload.get("data", {})


# ============================================================================
# Test: Notification queries
# ============================================================================


class TestNotificationQueries:
    """Tests for list, count, and stats queries."""

    def test_list_notifications_returns_paginated(
        self, notification_service, test_user, test_team, create_notification,
    ):
        """Should return paginated list ordered by created_at desc."""
        for i in range(5):
            create_notification(title=f"Notification {i}")

        notifications, total = notification_service.list_notifications(
            user_id=test_user.id,
            team_id=test_team.id,
            limit=3,
            offset=0,
        )
        assert total == 5
        assert len(notifications) == 3

    def test_list_notifications_unread_only(
        self, notification_service, test_user, test_team, create_notification,
    ):
        """Should filter to unread notifications when unread_only=True."""
        create_notification(title="Unread")
        create_notification(title="Read", read_at=datetime.utcnow())

        notifications, total = notification_service.list_notifications(
            user_id=test_user.id,
            team_id=test_team.id,
            unread_only=True,
        )
        assert total == 1
        assert notifications[0].title == "Unread"

    def test_list_notifications_category_filter(
        self, notification_service, test_user, test_team, create_notification,
    ):
        """Should filter by notification category."""
        create_notification(category="job_failure")
        create_notification(category="deadline")

        notifications, total = notification_service.list_notifications(
            user_id=test_user.id,
            team_id=test_team.id,
            category="deadline",
        )
        assert total == 1
        assert notifications[0].category == "deadline"

    def test_get_unread_count(
        self, notification_service, test_user, test_team, create_notification,
    ):
        """Should return count of unread notifications."""
        create_notification()
        create_notification()
        create_notification(read_at=datetime.utcnow())

        count = notification_service.get_unread_count(
            user_id=test_user.id, team_id=test_team.id
        )
        assert count == 2

    def test_get_stats(
        self, notification_service, test_user, test_team, create_notification,
    ):
        """Should return total, unread, and this_week counts."""
        create_notification()
        create_notification(read_at=datetime.utcnow())

        stats = notification_service.get_stats(
            user_id=test_user.id, team_id=test_team.id
        )
        assert stats["total_count"] == 2
        assert stats["unread_count"] == 1
        assert stats["this_week_count"] == 2


# ============================================================================
# Test: mark_as_read
# ============================================================================


class TestMarkAsRead:
    """Tests for marking notifications as read."""

    def test_marks_unread_as_read(
        self, notification_service, test_team, create_notification,
    ):
        """Should set read_at timestamp on unread notification."""
        notification = create_notification()
        assert notification.read_at is None

        updated = notification_service.mark_as_read(
            guid=notification.guid, team_id=test_team.id
        )
        assert updated.read_at is not None

    def test_idempotent_on_already_read(
        self, notification_service, test_team, create_notification,
    ):
        """Should not change read_at if already read."""
        read_time = datetime.utcnow()
        notification = create_notification(read_at=read_time)

        updated = notification_service.mark_as_read(
            guid=notification.guid, team_id=test_team.id
        )
        assert updated.read_at == read_time

    def test_raises_not_found_for_invalid_guid(
        self, notification_service, test_team,
    ):
        """Should raise NotFoundError for invalid GUID."""
        from backend.src.services.exceptions import NotFoundError

        with pytest.raises(NotFoundError):
            notification_service.mark_as_read(
                guid="ntf_00000000000000000000000000", team_id=test_team.id
            )


# ============================================================================
# Test: cleanup_read_notifications
# ============================================================================


class TestCleanupReadNotifications:
    """Tests for read notification cleanup."""

    def test_deletes_expired_read_notifications(
        self, notification_service, test_user, test_team,
        test_db_session, create_notification,
    ):
        """Should delete read notifications older than retention period."""
        old_read = create_notification(
            read_at=datetime.utcnow() - timedelta(days=31)
        )
        recent_read = create_notification(
            read_at=datetime.utcnow() - timedelta(days=1)
        )
        unread = create_notification()

        count = notification_service.cleanup_read_notifications(
            user_id=test_user.id, team_id=test_team.id
        )
        assert count == 1
        # Verify only old read was deleted
        remaining = test_db_session.query(Notification).filter(
            Notification.user_id == test_user.id
        ).count()
        assert remaining == 2
