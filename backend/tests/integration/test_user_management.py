"""
Integration tests for user management functionality.

Tests for user pre-provisioning, global email uniqueness,
and pending user activation on OAuth login.

Part of Issue #73 - User Story 3: User Pre-Provisioning
"""

import pytest

from backend.src.models import Team, User, UserStatus
from backend.src.services.user_service import UserService
from backend.src.services.exceptions import ConflictError


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def user_service(test_db_session):
    """Create a UserService instance for testing."""
    return UserService(test_db_session)


@pytest.fixture
def team_a(test_db_session):
    """Create Team A for cross-team tests."""
    team = Team(
        name="Team Alpha",
        slug="team-alpha",
        is_active=True,
    )
    test_db_session.add(team)
    test_db_session.commit()
    test_db_session.refresh(team)
    return team


@pytest.fixture
def team_b(test_db_session):
    """Create Team B for cross-team tests."""
    team = Team(
        name="Team Beta",
        slug="team-beta",
        is_active=True,
    )
    test_db_session.add(team)
    test_db_session.commit()
    test_db_session.refresh(team)
    return team


# ============================================================================
# T074: Global Email Uniqueness Tests
# ============================================================================


class TestGlobalEmailUniqueness:
    """Tests for global email uniqueness across teams."""

    def test_email_unique_across_teams(self, user_service, team_a, team_b):
        """Test that email must be unique across all teams."""
        # Create user in Team A
        user_service.invite(
            team_id=team_a.id,
            email="shared@example.com",
        )

        # Attempt to create same email in Team B should fail
        with pytest.raises(ConflictError) as exc_info:
            user_service.invite(
                team_id=team_b.id,
                email="shared@example.com",
            )

        assert "already exists" in str(exc_info.value).lower()

    def test_email_unique_case_insensitive(self, user_service, team_a, team_b):
        """Test email uniqueness is case-insensitive across teams."""
        # Create user with lowercase email in Team A
        user_service.invite(
            team_id=team_a.id,
            email="test@example.com",
        )

        # Attempt with different case in Team B should fail
        with pytest.raises(ConflictError):
            user_service.invite(
                team_id=team_b.id,
                email="TEST@EXAMPLE.COM",
            )

    def test_different_emails_allowed_across_teams(self, user_service, team_a, team_b):
        """Test different emails can be created in different teams."""
        user_a = user_service.invite(
            team_id=team_a.id,
            email="user_a@example.com",
        )

        user_b = user_service.invite(
            team_id=team_b.id,
            email="user_b@example.com",
        )

        assert user_a.email == "user_a@example.com"
        assert user_b.email == "user_b@example.com"
        assert user_a.team_id == team_a.id
        assert user_b.team_id == team_b.id


# ============================================================================
# T075: Pending User Activation Tests
# ============================================================================


class TestPendingUserActivation:
    """Tests for pending user activation on first OAuth login."""

    def test_pending_user_activated_on_oauth_login(self, user_service, team_a):
        """Test that pending user is activated on first OAuth login."""
        # Create pending user
        user = user_service.invite(
            team_id=team_a.id,
            email="pending@example.com",
        )
        assert user.status == UserStatus.PENDING

        # Simulate OAuth login
        updated = user_service.update_oauth_profile(
            user=user,
            provider="google",
            oauth_subject="google-12345",
            display_name="Test User",
            picture_url="https://example.com/photo.jpg",
        )

        assert updated.status == UserStatus.ACTIVE
        assert updated.oauth_provider == "google"
        assert updated.oauth_subject == "google-12345"
        assert updated.last_login_at is not None

    def test_active_user_stays_active_on_oauth_login(self, user_service, team_a, test_db_session):
        """Test that active user stays active on subsequent OAuth login."""
        # Create user and manually set to active
        user = user_service.invite(
            team_id=team_a.id,
            email="active@example.com",
        )
        user.status = UserStatus.ACTIVE
        test_db_session.commit()
        test_db_session.refresh(user)

        # Simulate OAuth login
        updated = user_service.update_oauth_profile(
            user=user,
            provider="google",
            oauth_subject="google-67890",
        )

        assert updated.status == UserStatus.ACTIVE

    def test_oauth_profile_data_synced(self, user_service, team_a):
        """Test OAuth profile data is synced on login."""
        user = user_service.invite(
            team_id=team_a.id,
            email="sync@example.com",
        )

        updated = user_service.update_oauth_profile(
            user=user,
            provider="microsoft",
            oauth_subject="ms-user-id",
            display_name="Microsoft User",
            picture_url="https://graph.microsoft.com/photo.jpg",
        )

        assert updated.display_name == "Microsoft User"
        assert updated.picture_url == "https://graph.microsoft.com/photo.jpg"
        assert updated.oauth_provider == "microsoft"

    def test_oauth_login_updates_last_login_timestamp(self, user_service, team_a):
        """Test OAuth login updates last_login_at timestamp."""
        user = user_service.invite(
            team_id=team_a.id,
            email="timestamp@example.com",
        )
        assert user.last_login_at is None

        updated = user_service.update_oauth_profile(
            user=user,
            provider="google",
            oauth_subject="google-timestamp",
        )

        assert updated.last_login_at is not None


# ============================================================================
# User Invite Flow Integration Tests
# ============================================================================


class TestUserInviteFlow:
    """Integration tests for complete user invite flow."""

    def test_complete_invite_and_activation_flow(self, user_service, team_a):
        """Test complete flow: invite → pending → OAuth login → active."""
        # Step 1: Admin invites user
        invited = user_service.invite(
            team_id=team_a.id,
            email="newuser@example.com",
        )
        assert invited.status == UserStatus.PENDING
        assert invited.last_login_at is None

        # Step 2: User logs in via OAuth
        activated = user_service.update_oauth_profile(
            user=invited,
            provider="google",
            oauth_subject="google-newuser",
            display_name="New User",
            picture_url="https://example.com/avatar.jpg",
        )
        assert activated.status == UserStatus.ACTIVE
        assert activated.last_login_at is not None
        assert activated.display_name == "New User"

    def test_deactivated_user_cannot_login(self, user_service, team_a, test_db_session):
        """Test that deactivated user's can_login is False."""
        user = user_service.invite(
            team_id=team_a.id,
            email="deactivate@example.com",
        )

        # Activate user first
        user.status = UserStatus.ACTIVE
        test_db_session.commit()
        test_db_session.refresh(user)
        assert user.can_login is True

        # Deactivate user
        deactivated = user_service.deactivate(user.guid)
        assert deactivated.can_login is False
        assert deactivated.status == UserStatus.DEACTIVATED

    def test_list_team_users_ordered(self, user_service, team_a):
        """Test listing team users returns ordered results."""
        user_service.invite(team_id=team_a.id, email="zebra@example.com")
        user_service.invite(team_id=team_a.id, email="apple@example.com")
        user_service.invite(team_id=team_a.id, email="mango@example.com")

        users = user_service.list_by_team(team_a.id)

        emails = [u.email for u in users]
        assert emails == ["apple@example.com", "mango@example.com", "zebra@example.com"]

    def test_filter_users_by_status(self, user_service, team_a, test_db_session):
        """Test filtering users by status."""
        pending = user_service.invite(team_id=team_a.id, email="pending@example.com")

        active = user_service.invite(team_id=team_a.id, email="active@example.com")
        active.status = UserStatus.ACTIVE
        test_db_session.commit()

        # Filter pending only
        pending_users = user_service.list_by_team(
            team_a.id, status_filter=UserStatus.PENDING
        )
        assert len(pending_users) == 1
        assert pending_users[0].email == "pending@example.com"

        # Filter active only
        active_users = user_service.list_by_team(
            team_a.id, status_filter=UserStatus.ACTIVE
        )
        assert len(active_users) == 1
        assert active_users[0].email == "active@example.com"


# ============================================================================
# T086: Cannot Deactivate Self Tests
# ============================================================================


class TestCannotDeactivateSelf:
    """Tests for preventing users from deactivating themselves."""

    def test_cannot_deactivate_self_via_api(self, user_service, team_a, test_db_session):
        """Test that a user cannot deactivate themselves via API endpoint.

        This tests the business rule enforced at the API layer that prevents
        users from locking themselves out by deactivating their own account.
        """
        from fastapi.testclient import TestClient
        from backend.src.main import app
        from backend.src.middleware.auth import require_auth
        from backend.src.middleware.tenant import TenantContext
        from backend.src.db.database import get_db

        # Create and activate a test user
        user = user_service.invite(
            team_id=team_a.id,
            email="selfdeactivate@example.com",
        )
        user.status = UserStatus.ACTIVE
        test_db_session.commit()
        test_db_session.refresh(user)

        # Override require_auth to authenticate as this user
        ctx = TenantContext(
            user_id=user.id,
            user_guid=user.guid,
            user_email=user.email,
            team_id=team_a.id,
            team_guid=team_a.guid,
            is_super_admin=False,
            is_api_token=False,
        )

        def get_test_db():
            yield test_db_session

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[require_auth] = lambda: ctx

        try:
            with TestClient(app) as client:
                # Attempt to deactivate self should return 400
                response = client.post(f"/api/users/{user.guid}/deactivate")
                assert response.status_code == 400
                assert "cannot deactivate yourself" in response.json()["detail"].lower()
        finally:
            # Clean up override
            app.dependency_overrides.pop(require_auth, None)
            app.dependency_overrides.pop(get_db, None)

    def test_can_deactivate_other_user(self, user_service, team_a, test_db_session):
        """Test that a user CAN deactivate another user in their team."""
        # Create the acting user (admin)
        admin = user_service.invite(
            team_id=team_a.id,
            email="admin@example.com",
        )
        admin.status = UserStatus.ACTIVE
        test_db_session.commit()

        # Create the target user
        target = user_service.invite(
            team_id=team_a.id,
            email="target@example.com",
        )
        target.status = UserStatus.ACTIVE
        test_db_session.commit()
        test_db_session.refresh(target)

        # Admin deactivates target - should succeed
        deactivated = user_service.deactivate(target.guid)
        assert deactivated.status == UserStatus.DEACTIVATED

    def test_reactivate_restores_previous_status(self, user_service, team_a, test_db_session):
        """Test that reactivating a user restores appropriate status."""
        # Create user who was active (has logged in)
        user = user_service.invite(
            team_id=team_a.id,
            email="reactivate@example.com",
        )
        # Simulate they logged in (set last_login_at)
        from datetime import datetime, timezone
        user.status = UserStatus.ACTIVE
        user.last_login_at = datetime.now(timezone.utc)
        test_db_session.commit()
        test_db_session.refresh(user)

        # Deactivate
        user_service.deactivate(user.guid)
        test_db_session.refresh(user)
        assert user.status == UserStatus.DEACTIVATED

        # Reactivate - should go back to ACTIVE since they previously logged in
        reactivated = user_service.activate(user.guid)
        assert reactivated.status == UserStatus.ACTIVE

    def test_reactivate_pending_user_stays_pending(self, user_service, team_a, test_db_session):
        """Test that reactivating a never-logged-in user returns to PENDING."""
        # Create pending user (never logged in)
        user = user_service.invite(
            team_id=team_a.id,
            email="pendinguser@example.com",
        )
        assert user.status == UserStatus.PENDING
        assert user.last_login_at is None

        # Deactivate the pending user
        user_service.deactivate(user.guid)
        test_db_session.refresh(user)
        assert user.status == UserStatus.DEACTIVATED

        # Reactivate - should go back to PENDING since never logged in
        reactivated = user_service.activate(user.guid)
        assert reactivated.status == UserStatus.PENDING
