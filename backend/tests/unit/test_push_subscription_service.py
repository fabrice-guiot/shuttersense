"""
Unit tests for PushSubscriptionService.

Issue #114 - PWA with Push Notifications (Phase 13 — T051)
Tests subscription create (upsert), remove, list, cleanup, and invalidation.
"""

from datetime import datetime, timedelta

import pytest

from backend.src.models.push_subscription import PushSubscription
from backend.src.services.push_subscription_service import PushSubscriptionService
from backend.src.services.exceptions import NotFoundError


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def push_service(test_db_session):
    """Create a PushSubscriptionService instance."""
    return PushSubscriptionService(db=test_db_session)


# ============================================================================
# Test: create_subscription
# ============================================================================


class TestCreateSubscription:
    """Tests for PushSubscriptionService.create_subscription."""

    def test_creates_new_subscription(
        self, push_service, test_team, test_user
    ):
        """Should create a new subscription record."""
        sub = push_service.create_subscription(
            team_id=test_team.id,
            user_id=test_user.id,
            endpoint="https://push.example.com/sub/1",
            p256dh_key="test-p256dh",
            auth_key="test-auth",
            device_name="Chrome Desktop",
        )
        assert sub.id is not None
        assert sub.guid.startswith("sub_")
        assert sub.endpoint == "https://push.example.com/sub/1"
        assert sub.device_name == "Chrome Desktop"

    def test_upserts_existing_endpoint_same_user(
        self, push_service, test_team, test_user
    ):
        """Should update keys when endpoint exists for same user."""
        endpoint = "https://push.example.com/sub/1"
        push_service.create_subscription(
            team_id=test_team.id,
            user_id=test_user.id,
            endpoint=endpoint,
            p256dh_key="old-key",
            auth_key="old-auth",
        )
        updated = push_service.create_subscription(
            team_id=test_team.id,
            user_id=test_user.id,
            endpoint=endpoint,
            p256dh_key="new-key",
            auth_key="new-auth",
        )
        assert updated.p256dh_key == "new-key"
        assert updated.auth_key == "new-auth"

    def test_transfers_endpoint_to_new_user(
        self, push_service, test_team, test_user, test_db_session
    ):
        """Should transfer subscription to new user when endpoint changes owner."""
        from backend.src.models.user import User, UserStatus

        other_user = User(
            team_id=test_team.id,
            email="other@example.com",
            display_name="Other User",
            status=UserStatus.ACTIVE,
        )
        test_db_session.add(other_user)
        test_db_session.commit()

        endpoint = "https://push.example.com/shared"
        push_service.create_subscription(
            team_id=test_team.id,
            user_id=test_user.id,
            endpoint=endpoint,
            p256dh_key="key1",
            auth_key="auth1",
        )
        transferred = push_service.create_subscription(
            team_id=test_team.id,
            user_id=other_user.id,
            endpoint=endpoint,
            p256dh_key="key2",
            auth_key="auth2",
        )
        assert transferred.user_id == other_user.id


# ============================================================================
# Test: remove_subscription
# ============================================================================


class TestRemoveSubscription:
    """Tests for PushSubscriptionService.remove_subscription."""

    def test_removes_existing_subscription(
        self, push_service, test_team, test_user
    ):
        """Should remove the subscription matching endpoint + user."""
        endpoint = "https://push.example.com/sub/1"
        push_service.create_subscription(
            team_id=test_team.id,
            user_id=test_user.id,
            endpoint=endpoint,
            p256dh_key="key",
            auth_key="auth",
        )
        result = push_service.remove_subscription(
            user_id=test_user.id,
            team_id=test_team.id,
            endpoint=endpoint,
        )
        assert result is True

    def test_raises_not_found_for_unknown_endpoint(
        self, push_service, test_team, test_user
    ):
        """Should raise NotFoundError when endpoint doesn't exist."""
        with pytest.raises(NotFoundError):
            push_service.remove_subscription(
                user_id=test_user.id,
                team_id=test_team.id,
                endpoint="https://nonexistent.com",
            )


# ============================================================================
# Test: list_subscriptions
# ============================================================================


class TestListSubscriptions:
    """Tests for PushSubscriptionService.list_subscriptions."""

    def test_lists_user_subscriptions(
        self, push_service, test_team, test_user
    ):
        """Should return all subscriptions for a user."""
        push_service.create_subscription(
            team_id=test_team.id, user_id=test_user.id,
            endpoint="https://push.example.com/1",
            p256dh_key="k1", auth_key="a1",
        )
        push_service.create_subscription(
            team_id=test_team.id, user_id=test_user.id,
            endpoint="https://push.example.com/2",
            p256dh_key="k2", auth_key="a2",
        )
        subs = push_service.list_subscriptions(
            user_id=test_user.id, team_id=test_team.id
        )
        assert len(subs) == 2

    def test_empty_for_user_without_subscriptions(
        self, push_service, test_team, test_user
    ):
        """Should return empty list when user has no subscriptions."""
        subs = push_service.list_subscriptions(
            user_id=test_user.id, team_id=test_team.id
        )
        assert subs == []

    def test_team_isolation(
        self, push_service, test_db_session, test_team, test_user
    ):
        """Should only return subscriptions for the specified team."""
        from backend.src.models.team import Team
        from backend.src.models.user import User, UserStatus

        other_team = Team(name="Other Team", slug="other-team", is_active=True)
        test_db_session.add(other_team)
        test_db_session.commit()

        other_user = User(
            team_id=other_team.id,
            email="other@team.com",
            display_name="Other",
            status=UserStatus.ACTIVE,
        )
        test_db_session.add(other_user)
        test_db_session.commit()

        push_service.create_subscription(
            team_id=test_team.id, user_id=test_user.id,
            endpoint="https://push.example.com/team1",
            p256dh_key="k1", auth_key="a1",
        )
        push_service.create_subscription(
            team_id=other_team.id, user_id=other_user.id,
            endpoint="https://push.example.com/team2",
            p256dh_key="k2", auth_key="a2",
        )

        subs = push_service.list_subscriptions(
            user_id=test_user.id, team_id=test_team.id
        )
        assert len(subs) == 1
        assert subs[0].team_id == test_team.id


# ============================================================================
# Test: cleanup_expired
# ============================================================================


class TestCleanupExpired:
    """Tests for PushSubscriptionService.cleanup_expired."""

    def test_removes_expired_subscriptions(
        self, push_service, test_db_session, test_team, test_user
    ):
        """Should remove subscriptions past their expiration date."""
        expired_sub = PushSubscription(
            team_id=test_team.id,
            user_id=test_user.id,
            endpoint="https://push.example.com/expired",
            p256dh_key="k", auth_key="a",
            expires_at=datetime.utcnow() - timedelta(hours=1),
        )
        test_db_session.add(expired_sub)
        test_db_session.commit()

        count = push_service.cleanup_expired()
        assert count == 1

    def test_does_not_remove_active_subscriptions(
        self, push_service, test_team, test_user
    ):
        """Should not remove subscriptions that haven't expired."""
        push_service.create_subscription(
            team_id=test_team.id, user_id=test_user.id,
            endpoint="https://push.example.com/active",
            p256dh_key="k", auth_key="a",
        )
        count = push_service.cleanup_expired()
        assert count == 0


# ============================================================================
# Test: remove_invalid
# ============================================================================


class TestRemoveInvalid:
    """Tests for PushSubscriptionService.remove_invalid."""

    def test_removes_subscription_by_endpoint(
        self, push_service, test_team, test_user, test_db_session
    ):
        """Should remove subscription matching the 410 Gone endpoint."""
        endpoint = "https://push.example.com/gone"
        push_service.create_subscription(
            team_id=test_team.id, user_id=test_user.id,
            endpoint=endpoint, p256dh_key="k", auth_key="a",
        )
        push_service.remove_invalid(endpoint)

        remaining = test_db_session.query(PushSubscription).filter(
            PushSubscription.endpoint == endpoint
        ).first()
        assert remaining is None

    def test_no_error_for_nonexistent_endpoint(self, push_service):
        """Should not raise when endpoint doesn't exist."""
        push_service.remove_invalid("https://nonexistent.com")
