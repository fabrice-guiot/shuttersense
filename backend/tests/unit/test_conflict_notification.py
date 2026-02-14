"""
Unit tests for conflict notification delivery.

Issue #182 - Calendar Conflict Visualization & Event Picker (Phase 9, T040)
Tests that notify_conflict_detected sends notifications to team members
and that EventService._notify_new_conflicts triggers on create/update.
"""

import json
from unittest.mock import patch, MagicMock

import pytest

from backend.src.services.notification_service import (
    NotificationService,
    DEFAULT_PREFERENCES,
    CATEGORY_PREFERENCE_KEYS,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def notification_service(test_db_session):
    """Create a NotificationService with test VAPID config.

    Args:
        test_db_session: SQLAlchemy test database session.

    Returns:
        NotificationService: Configured with test VAPID private key and claims.
    """
    return NotificationService(
        db=test_db_session,
        vapid_private_key="test-private-key",
        vapid_claims={"sub": "mailto:test@example.com"},
    )


@pytest.fixture
def enabled_user(test_db_session, test_user):
    """Set up a user with conflict notifications enabled.

    Args:
        test_db_session: SQLAlchemy test database session.
        test_user: Test user instance to enable notifications on.

    Returns:
        User: The test_user with conflict notifications enabled
            (preferences_json updated and committed).
    """
    test_user.preferences_json = json.dumps({
        "notifications": {
            **DEFAULT_PREFERENCES,
            "enabled": True,
            "conflict": True,
        }
    })
    test_db_session.commit()
    return test_user


# ============================================================================
# Test: conflict category registration
# ============================================================================


class TestConflictCategoryRegistration:
    """Tests that conflict category is properly registered."""

    def test_conflict_in_default_preferences(self):
        """conflict preference exists in DEFAULT_PREFERENCES."""
        assert "conflict" in DEFAULT_PREFERENCES
        assert DEFAULT_PREFERENCES["conflict"] is True

    def test_conflict_in_category_preference_keys(self):
        """conflict maps to preference key in CATEGORY_PREFERENCE_KEYS."""
        assert "conflict" in CATEGORY_PREFERENCE_KEYS
        assert CATEGORY_PREFERENCE_KEYS["conflict"] == "conflict"


# ============================================================================
# Test: notify_conflict_detected
# ============================================================================


class TestNotifyConflictDetected:
    """Tests for notify_conflict_detected() method."""

    @patch("backend.src.services.notification_service.NotificationService.deliver_push")
    def test_sends_notification_to_enabled_user(
        self, mock_deliver, notification_service, enabled_user, test_team,
    ):
        """Should send notification when user has conflict preference enabled."""
        mock_deliver.return_value = 1

        sent = notification_service.notify_conflict_detected(
            team_id=test_team.id,
            event_a_title="Airshow 2026",
            event_b_title="Music Festival",
            event_a_guid="evt_aaa",
            event_b_guid="evt_bbb",
            conflict_type="time_overlap",
            event_a_date="2026-06-15",
            event_b_date="2026-06-15",
        )

        assert sent == 1
        mock_deliver.assert_called_once()

    def test_suppressed_when_preference_disabled(
        self, notification_service, test_user, test_team,
    ):
        """Should not send when user has notifications disabled (default)."""
        # test_user has default prefs (enabled=False)
        sent = notification_service.notify_conflict_detected(
            team_id=test_team.id,
            event_a_title="Event A",
            event_b_title="Event B",
            event_a_guid="evt_aaa",
            event_b_guid="evt_bbb",
            conflict_type="distance",
            event_a_date="2026-07-01",
            event_b_date="2026-07-02",
        )

        assert sent == 0

    @patch("backend.src.services.notification_service.NotificationService.deliver_push")
    def test_notification_content(
        self, mock_deliver, notification_service, enabled_user, test_team,
        test_db_session,
    ):
        """Should include conflict type and event titles in notification body."""
        mock_deliver.return_value = 1

        notification_service.notify_conflict_detected(
            team_id=test_team.id,
            event_a_title="Oshkosh Airshow",
            event_b_title="Chicago Blues Fest",
            event_a_guid="evt_aaa",
            event_b_guid="evt_bbb",
            conflict_type="travel_buffer",
            event_a_date="2026-08-01",
            event_b_date="2026-08-01",
        )

        # Find the notification that was created
        from backend.src.models.notification import Notification

        notif = (
            test_db_session.query(Notification)
            .filter(Notification.category == "conflict")
            .order_by(Notification.id.desc())
            .first()
        )
        assert notif is not None
        assert notif.title == "New scheduling conflict detected"
        assert "Oshkosh Airshow" in notif.body
        assert "Chicago Blues Fest" in notif.body
        assert "travel buffer" in notif.body


# ============================================================================
# Test: EventService conflict notification trigger
# ============================================================================


class TestEventServiceConflictTrigger:
    """Tests that EventService._notify_new_conflicts fires after create/update."""

    @patch("backend.src.services.event_service.EventService._notify_new_conflicts")
    def test_create_triggers_conflict_check(
        self, mock_notify, test_db_session, test_team, test_user,
    ):
        """create() should call _notify_new_conflicts after commit."""
        from backend.src.services.event_service import EventService
        from backend.src.models import Category

        event_service = EventService(db=test_db_session)

        # Create a category for the event
        category = test_db_session.query(Category).filter(
            Category.team_id == test_team.id
        ).first()

        if not category:
            category = Category(
                team_id=test_team.id,
                name="Test Category",
                created_by_user_id=test_user.id,
                updated_by_user_id=test_user.id,
            )
            test_db_session.add(category)
            test_db_session.commit()

        from datetime import date

        event_service.create(
            team_id=test_team.id,
            title="Test Event",
            category_guid=category.guid,
            event_date=date(2026, 6, 15),
            user_id=test_user.id,
        )

        mock_notify.assert_called_once()
        call_args = mock_notify.call_args
        assert call_args[0][0] == test_team.id  # team_id
        assert call_args[0][1] == date(2026, 6, 15)  # event_date

    @patch("backend.src.services.conflict_service.ConflictService")
    def test_notify_does_not_block_on_error(
        self, mock_conflict_service_class, test_db_session, test_team, test_user,
    ):
        """_notify_new_conflicts errors should not prevent event creation."""
        from backend.src.services.event_service import EventService
        from backend.src.models import Category

        # Mock ConflictService.detect_conflicts to raise inside _notify_new_conflicts
        mock_conflict_service = MagicMock()
        mock_conflict_service.detect_conflicts.side_effect = Exception("Detection failed")
        mock_conflict_service_class.return_value = mock_conflict_service

        event_service = EventService(db=test_db_session)

        category = test_db_session.query(Category).filter(
            Category.team_id == test_team.id
        ).first()

        if not category:
            category = Category(
                team_id=test_team.id,
                name="Test Category",
                created_by_user_id=test_user.id,
                updated_by_user_id=test_user.id,
            )
            test_db_session.add(category)
            test_db_session.commit()

        from datetime import date

        # Should NOT raise - the try/except in _notify_new_conflicts should suppress
        event = event_service.create(
            team_id=test_team.id,
            title="Test Event 2",
            category_guid=category.guid,
            event_date=date(2026, 6, 20),
            user_id=test_user.id,
        )

        # Event should be created successfully despite the conflict detection error
        assert event is not None
        assert event.title == "Test Event 2"

        # Verify the conflict service was called (notification hook triggered)
        mock_conflict_service.detect_conflicts.assert_called_once()
