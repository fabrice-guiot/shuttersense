"""
Unit tests for UserService.

Tests CRUD operations for users with validation, team association,
and OAuth profile syncing.
Part of Issue #73 - Teams/Tenants and User Management.
"""

import pytest
from datetime import datetime

from backend.src.models import Team, User, UserStatus
from backend.src.services.user_service import UserService
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def user_service(test_db_session):
    """Create a UserService instance for testing."""
    return UserService(test_db_session)


@pytest.fixture
def sample_team(test_db_session):
    """Create a sample team for user tests."""
    team = Team(
        name="Test Team",
        slug="test-team",
        is_active=True,
    )
    test_db_session.add(team)
    test_db_session.commit()
    test_db_session.refresh(team)
    return team


@pytest.fixture
def sample_user(test_db_session, sample_team):
    """Factory for creating sample User models."""

    def _create(
        email="user@example.com",
        team_id=None,
        first_name=None,
        last_name=None,
        display_name=None,
        is_active=True,
        status=UserStatus.PENDING,
    ):
        if team_id is None:
            team_id = sample_team.id

        user = User(
            team_id=team_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            display_name=display_name,
            is_active=is_active,
            status=status,
        )
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)
        return user

    return _create


# ============================================================================
# Create Tests (T019)
# ============================================================================


class TestUserServiceCreate:
    """Tests for user creation."""

    def test_create_user(self, user_service, sample_team):
        """Test creating a new user."""
        result = user_service.create(
            team_id=sample_team.id,
            email="admin@example.com",
            first_name="John",
            last_name="Doe",
        )

        assert result.id is not None
        assert result.uuid is not None
        assert result.email == "admin@example.com"
        assert result.first_name == "John"
        assert result.last_name == "Doe"
        assert result.team_id == sample_team.id
        assert result.status == UserStatus.PENDING
        assert result.is_active is True
        assert result.guid.startswith("usr_")

    def test_create_user_minimal(self, user_service, sample_team):
        """Test creating user with minimal fields."""
        result = user_service.create(
            team_id=sample_team.id,
            email="minimal@example.com",
        )

        assert result.email == "minimal@example.com"
        assert result.first_name is None
        assert result.last_name is None
        assert result.display_name is None

    def test_create_user_email_normalized(self, user_service, sample_team):
        """Test email is normalized (lowercase, trimmed)."""
        result = user_service.create(
            team_id=sample_team.id,
            email="  UPPER@EXAMPLE.COM  ",
        )

        assert result.email == "upper@example.com"

    def test_create_user_duplicate_email(self, user_service, sample_team, sample_user):
        """Test error when creating duplicate email."""
        sample_user(email="existing@example.com")

        with pytest.raises(ConflictError) as exc_info:
            user_service.create(
                team_id=sample_team.id,
                email="existing@example.com",
            )

        assert "already exists" in str(exc_info.value).lower()

    def test_create_user_duplicate_email_case_insensitive(
        self, user_service, sample_team, sample_user
    ):
        """Test duplicate detection is case-insensitive."""
        sample_user(email="test@example.com")

        with pytest.raises(ConflictError):
            user_service.create(
                team_id=sample_team.id,
                email="TEST@EXAMPLE.COM",
            )

    def test_create_user_invalid_email(self, user_service, sample_team):
        """Test error on invalid email format."""
        invalid_emails = [
            "notanemail",
            "@nodomain",
            "no@domain",
            "",
            "   ",
        ]

        for email in invalid_emails:
            with pytest.raises(ValidationError) as exc_info:
                user_service.create(team_id=sample_team.id, email=email)

            assert "email" in str(exc_info.value).lower()

    def test_create_user_invalid_team(self, user_service):
        """Test error when team doesn't exist."""
        with pytest.raises(NotFoundError):
            user_service.create(
                team_id=99999,
                email="test@example.com",
            )

    def test_create_user_with_display_name(self, user_service, sample_team):
        """Test creating user with display name."""
        result = user_service.create(
            team_id=sample_team.id,
            email="test@example.com",
            display_name="Johnny D",
        )

        assert result.display_name == "Johnny D"

    def test_create_user_with_status(self, user_service, sample_team):
        """Test creating user with specific status."""
        result = user_service.create(
            team_id=sample_team.id,
            email="test@example.com",
            status=UserStatus.ACTIVE,
        )

        assert result.status == UserStatus.ACTIVE

    def test_create_user_inactive(self, user_service, sample_team):
        """Test creating inactive user."""
        result = user_service.create(
            team_id=sample_team.id,
            email="test@example.com",
            is_active=False,
        )

        assert result.is_active is False


# ============================================================================
# Get Tests
# ============================================================================


class TestUserServiceGet:
    """Tests for user retrieval."""

    def test_get_by_guid(self, user_service, sample_user):
        """Test getting user by GUID."""
        user = sample_user(email="test@example.com")

        result = user_service.get_by_guid(user.guid)

        assert result.id == user.id
        assert result.email == "test@example.com"

    def test_get_by_guid_not_found(self, user_service):
        """Test error when GUID not found."""
        with pytest.raises(NotFoundError):
            user_service.get_by_guid("usr_00000000000000000000000000")

    def test_get_by_guid_invalid_format(self, user_service):
        """Test error on invalid GUID format."""
        with pytest.raises(NotFoundError):
            user_service.get_by_guid("invalid_guid")

    def test_get_by_guid_wrong_prefix(self, user_service):
        """Test error when GUID has wrong prefix."""
        with pytest.raises(NotFoundError):
            user_service.get_by_guid("ten_00000000000000000000000000")

    def test_get_by_id(self, user_service, sample_user):
        """Test getting user by internal ID."""
        user = sample_user(email="test@example.com")

        result = user_service.get_by_id(user.id)

        assert result.id == user.id

    def test_get_by_id_not_found(self, user_service):
        """Test error when ID not found."""
        with pytest.raises(NotFoundError):
            user_service.get_by_id(99999)

    def test_get_by_email(self, user_service, sample_user):
        """Test getting user by email."""
        user = sample_user(email="findme@example.com")

        result = user_service.get_by_email("findme@example.com")

        assert result.id == user.id

    def test_get_by_email_case_insensitive(self, user_service, sample_user):
        """Test get_by_email is case-insensitive."""
        user = sample_user(email="test@example.com")

        result = user_service.get_by_email("TEST@EXAMPLE.COM")

        assert result.id == user.id

    def test_get_by_email_not_found(self, user_service):
        """Test None returned when email not found."""
        result = user_service.get_by_email("nonexistent@example.com")

        assert result is None

    def test_get_by_oauth_subject(self, user_service, sample_user, test_db_session):
        """Test getting user by OAuth subject."""
        user = sample_user(email="oauth@example.com")
        user.oauth_subject = "google-12345"
        test_db_session.commit()

        result = user_service.get_by_oauth_subject("google-12345")

        assert result.id == user.id

    def test_get_by_oauth_subject_not_found(self, user_service):
        """Test None returned when OAuth subject not found."""
        result = user_service.get_by_oauth_subject("nonexistent")

        assert result is None


# ============================================================================
# List Tests
# ============================================================================


class TestUserServiceList:
    """Tests for user listing."""

    def test_list_by_team(self, user_service, sample_team, sample_user):
        """Test listing users in a team."""
        sample_user(email="user1@example.com")
        sample_user(email="user2@example.com")
        sample_user(email="user3@example.com")

        result = user_service.list_by_team(sample_team.id)

        assert len(result) == 3

    def test_list_by_team_active_only(self, user_service, sample_team, sample_user):
        """Test listing only active users."""
        sample_user(email="active1@example.com", is_active=True)
        sample_user(email="active2@example.com", is_active=True)
        sample_user(email="inactive@example.com", is_active=False)

        result = user_service.list_by_team(sample_team.id, active_only=True)

        assert len(result) == 2
        assert all(u.is_active for u in result)

    def test_list_by_team_status_filter(self, user_service, sample_team, sample_user):
        """Test filtering by status."""
        sample_user(email="pending@example.com", status=UserStatus.PENDING)
        sample_user(email="active@example.com", status=UserStatus.ACTIVE)

        result = user_service.list_by_team(
            sample_team.id, status_filter=UserStatus.PENDING
        )

        assert len(result) == 1
        assert result[0].email == "pending@example.com"

    def test_list_by_team_ordered_by_email(self, user_service, sample_team, sample_user):
        """Test list is ordered by email."""
        sample_user(email="zebra@example.com")
        sample_user(email="apple@example.com")

        result = user_service.list_by_team(sample_team.id)

        emails = [u.email for u in result]
        assert emails == ["apple@example.com", "zebra@example.com"]


# ============================================================================
# Update Tests
# ============================================================================


class TestUserServiceUpdate:
    """Tests for user updates."""

    def test_update_name(self, user_service, sample_user):
        """Test updating user name."""
        user = sample_user(email="test@example.com")

        result = user_service.update(
            user.guid,
            first_name="Jane",
            last_name="Smith",
        )

        assert result.first_name == "Jane"
        assert result.last_name == "Smith"

    def test_update_display_name(self, user_service, sample_user):
        """Test updating display name."""
        user = sample_user(email="test@example.com")

        result = user_service.update(user.guid, display_name="JD")

        assert result.display_name == "JD"

    def test_update_is_active(self, user_service, sample_user):
        """Test updating active status."""
        user = sample_user(email="test@example.com", is_active=True)

        result = user_service.update(user.guid, is_active=False)

        assert result.is_active is False

    def test_update_status(self, user_service, sample_user):
        """Test updating user status."""
        user = sample_user(email="test@example.com", status=UserStatus.PENDING)

        result = user_service.update(user.guid, status=UserStatus.ACTIVE)

        assert result.status == UserStatus.ACTIVE

    def test_update_not_found(self, user_service):
        """Test error when updating nonexistent user."""
        with pytest.raises(NotFoundError):
            user_service.update("usr_00000000000000000000000000", first_name="New")

    def test_update_clear_field(self, user_service, sample_user):
        """Test clearing optional field."""
        user = sample_user(email="test@example.com", first_name="John")

        result = user_service.update(user.guid, first_name="")

        assert result.first_name is None


# ============================================================================
# OAuth Profile Tests
# ============================================================================


class TestUserServiceOAuthProfile:
    """Tests for OAuth profile syncing."""

    def test_update_oauth_profile(self, user_service, sample_user):
        """Test updating OAuth profile data."""
        user = sample_user(email="oauth@example.com")

        result = user_service.update_oauth_profile(
            user=user,
            provider="google",
            oauth_subject="google-12345",
            display_name="OAuth User",
            picture_url="https://example.com/photo.jpg",
        )

        assert result.oauth_provider == "google"
        assert result.oauth_subject == "google-12345"
        assert result.display_name == "OAuth User"
        assert result.picture_url == "https://example.com/photo.jpg"
        assert result.last_login_at is not None

    def test_update_oauth_profile_activates_pending(self, user_service, sample_user):
        """Test OAuth login activates pending user."""
        user = sample_user(email="pending@example.com", status=UserStatus.PENDING)

        result = user_service.update_oauth_profile(
            user=user,
            provider="microsoft",
            oauth_subject="ms-12345",
        )

        assert result.status == UserStatus.ACTIVE

    def test_update_oauth_profile_preserves_active(self, user_service, sample_user):
        """Test OAuth login preserves active status."""
        user = sample_user(email="active@example.com", status=UserStatus.ACTIVE)

        result = user_service.update_oauth_profile(
            user=user,
            provider="google",
            oauth_subject="google-12345",
        )

        assert result.status == UserStatus.ACTIVE


# ============================================================================
# Helper Methods Tests
# ============================================================================


class TestUserServiceHelpers:
    """Tests for helper methods."""

    def test_deactivate(self, user_service, sample_user):
        """Test deactivating a user."""
        user = sample_user(email="active@example.com", is_active=True)

        result = user_service.deactivate(user.guid)

        assert result.is_active is False
        assert result.status == UserStatus.DEACTIVATED

    def test_activate_never_logged_in(self, user_service, sample_user):
        """Test activating user who never logged in."""
        user = sample_user(
            email="pending@example.com",
            is_active=False,
            status=UserStatus.DEACTIVATED,
        )

        result = user_service.activate(user.guid)

        assert result.is_active is True
        assert result.status == UserStatus.PENDING

    def test_activate_previously_active(self, user_service, sample_user, test_db_session):
        """Test activating user who previously logged in."""
        user = sample_user(
            email="returning@example.com",
            is_active=False,
            status=UserStatus.DEACTIVATED,
        )
        user.last_login_at = datetime.utcnow()
        test_db_session.commit()

        result = user_service.activate(user.guid)

        assert result.is_active is True
        assert result.status == UserStatus.ACTIVE

    def test_count_by_team(self, user_service, sample_team, sample_user):
        """Test counting users in a team."""
        sample_user(email="user1@example.com")
        sample_user(email="user2@example.com")

        result = user_service.count_by_team(sample_team.id)

        assert result == 2


# ============================================================================
# User Properties Tests
# ============================================================================


# ============================================================================
# Invite Tests (T073)
# ============================================================================


class TestUserServiceInvite:
    """Tests for user invitation (pre-provisioning)."""

    def test_invite_creates_pending_user(self, user_service, sample_team):
        """Test invite creates a pending user."""
        result = user_service.invite(
            team_id=sample_team.id,
            email="invited@example.com",
        )

        assert result.email == "invited@example.com"
        assert result.status == UserStatus.PENDING
        assert result.is_active is True
        assert result.team_id == sample_team.id
        assert result.guid.startswith("usr_")

    def test_invite_validates_email_format(self, user_service, sample_team):
        """Test invite validates email format."""
        invalid_emails = ["notanemail", "no@domain", "", "   @.com"]

        for email in invalid_emails:
            with pytest.raises(ValidationError) as exc_info:
                user_service.invite(team_id=sample_team.id, email=email)
            assert "email" in str(exc_info.value).lower()

    def test_invite_normalizes_email(self, user_service, sample_team):
        """Test invite normalizes email (lowercase, trimmed)."""
        result = user_service.invite(
            team_id=sample_team.id,
            email="  INVITE@EXAMPLE.COM  ",
        )

        assert result.email == "invite@example.com"

    def test_invite_rejects_duplicate_email(self, user_service, sample_team, sample_user):
        """Test invite rejects duplicate email."""
        sample_user(email="existing@example.com")

        with pytest.raises(ConflictError) as exc_info:
            user_service.invite(
                team_id=sample_team.id,
                email="existing@example.com",
            )
        assert "already exists" in str(exc_info.value).lower()

    def test_invite_rejects_invalid_team(self, user_service):
        """Test invite rejects nonexistent team."""
        with pytest.raises(NotFoundError):
            user_service.invite(team_id=99999, email="test@example.com")


# ============================================================================
# Delete Pending Tests (T073)
# ============================================================================


class TestUserServiceDeletePending:
    """Tests for deleting pending users."""

    def test_delete_pending_success(self, user_service, sample_user, test_db_session):
        """Test successfully deleting a pending user."""
        user = sample_user(email="pending@example.com", status=UserStatus.PENDING)
        guid = user.guid

        user_service.delete_pending(guid)

        # Verify user is deleted
        with pytest.raises(NotFoundError):
            user_service.get_by_guid(guid)

    def test_delete_pending_rejects_active_user(self, user_service, sample_user):
        """Test cannot delete an active user."""
        user = sample_user(email="active@example.com", status=UserStatus.ACTIVE)

        with pytest.raises(ValidationError) as exc_info:
            user_service.delete_pending(user.guid)
        assert "pending" in str(exc_info.value).lower()

    def test_delete_pending_rejects_deactivated_user(self, user_service, sample_user):
        """Test cannot delete a deactivated user."""
        user = sample_user(email="deactivated@example.com", status=UserStatus.DEACTIVATED)

        with pytest.raises(ValidationError) as exc_info:
            user_service.delete_pending(user.guid)
        assert "pending" in str(exc_info.value).lower()

    def test_delete_pending_not_found(self, user_service):
        """Test error when user not found."""
        with pytest.raises(NotFoundError):
            user_service.delete_pending("usr_00000000000000000000000000")


class TestUserProperties:
    """Tests for User model properties."""

    def test_full_name_both(self, sample_user):
        """Test full_name with first and last name."""
        user = sample_user(
            email="test@example.com",
            first_name="John",
            last_name="Doe",
        )

        assert user.full_name == "John Doe"

    def test_full_name_first_only(self, sample_user):
        """Test full_name with only first name."""
        user = sample_user(
            email="test@example.com",
            first_name="John",
        )

        assert user.full_name == "John"

    def test_full_name_last_only(self, sample_user):
        """Test full_name with only last name."""
        user = sample_user(
            email="test@example.com",
            last_name="Doe",
        )

        assert user.full_name == "Doe"

    def test_full_name_display_fallback(self, sample_user):
        """Test full_name falls back to display_name."""
        user = sample_user(
            email="test@example.com",
            display_name="JD",
        )

        assert user.full_name == "JD"

    def test_full_name_none(self, sample_user):
        """Test full_name is None when no name info."""
        user = sample_user(email="test@example.com")

        assert user.full_name is None

    def test_can_login_active(self, sample_user):
        """Test can_login for active user."""
        user = sample_user(
            email="test@example.com",
            is_active=True,
            status=UserStatus.ACTIVE,
        )

        assert user.can_login is True

    def test_can_login_inactive(self, sample_user):
        """Test can_login for inactive user."""
        user = sample_user(
            email="test@example.com",
            is_active=False,
        )

        assert user.can_login is False

    def test_can_login_deactivated(self, sample_user):
        """Test can_login for deactivated user."""
        user = sample_user(
            email="test@example.com",
            is_active=True,
            status=UserStatus.DEACTIVATED,
        )

        assert user.can_login is False
