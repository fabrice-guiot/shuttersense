"""
Unit tests for AuthService.

Tests authentication business logic including user validation,
session management, and OAuth profile handling.
Part of Issue #73 - Teams/Tenants and User Management.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from backend.src.models import Team, User, UserStatus
from backend.src.services.auth_service import AuthService, AuthResult, AuthenticationError


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def auth_service(test_db_session):
    """Create an AuthService instance for testing."""
    return AuthService(test_db_session)


@pytest.fixture
def sample_team(test_db_session):
    """Create a sample team."""
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
    """Factory for creating sample users."""

    def _create(
        email="user@example.com",
        team_id=None,
        is_active=True,
        status=UserStatus.PENDING,
    ):
        if team_id is None:
            team_id = sample_team.id

        user = User(
            team_id=team_id,
            email=email,
            is_active=is_active,
            status=status,
        )
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)
        return user

    return _create


@pytest.fixture
def mock_request():
    """Create a mock Starlette request with session."""
    request = Mock()
    request.session = {}
    # Simulate session middleware being installed
    request.scope = {"session": request.session}
    return request


# ============================================================================
# Provider Tests
# ============================================================================


class TestAuthServiceProviders:
    """Tests for OAuth provider configuration."""

    def test_get_available_providers_none_configured(self, auth_service, monkeypatch):
        """Test when no providers are configured."""
        # Mock settings to have no providers
        mock_settings = Mock()
        mock_settings.google_enabled = False
        mock_settings.microsoft_enabled = False
        monkeypatch.setattr(auth_service, "settings", mock_settings)

        providers = auth_service.get_available_providers()

        assert providers == []

    def test_get_available_providers_google_only(self, auth_service, monkeypatch):
        """Test when only Google is configured."""
        mock_settings = Mock()
        mock_settings.google_enabled = True
        mock_settings.microsoft_enabled = False
        monkeypatch.setattr(auth_service, "settings", mock_settings)

        providers = auth_service.get_available_providers()

        assert len(providers) == 1
        assert providers[0]["name"] == "google"

    def test_get_available_providers_both(self, auth_service, monkeypatch):
        """Test when both providers are configured."""
        mock_settings = Mock()
        mock_settings.google_enabled = True
        mock_settings.microsoft_enabled = True
        monkeypatch.setattr(auth_service, "settings", mock_settings)

        providers = auth_service.get_available_providers()

        assert len(providers) == 2
        names = [p["name"] for p in providers]
        assert "google" in names
        assert "microsoft" in names


# ============================================================================
# User Validation Tests
# ============================================================================


class TestAuthServiceValidation:
    """Tests for user validation logic."""

    def test_validate_user_not_found(self, auth_service):
        """Test validation fails for unknown email."""
        result = auth_service._validate_and_authenticate(
            email="unknown@example.com",
            provider="google",
            oauth_subject="google-123",
            user_info={},
        )

        assert result.success is False
        assert result.error_code == "user_not_found"

    def test_validate_user_inactive(self, auth_service, sample_user):
        """Test validation fails for inactive user."""
        user = sample_user(email="inactive@example.com", is_active=False)

        result = auth_service._validate_and_authenticate(
            email="inactive@example.com",
            provider="google",
            oauth_subject="google-123",
            user_info={},
        )

        assert result.success is False
        assert result.error_code == "user_inactive"

    def test_validate_user_deactivated(self, auth_service, sample_user):
        """Test validation fails for deactivated user."""
        user = sample_user(
            email="deactivated@example.com",
            is_active=True,
            status=UserStatus.DEACTIVATED,
        )

        result = auth_service._validate_and_authenticate(
            email="deactivated@example.com",
            provider="google",
            oauth_subject="google-123",
            user_info={},
        )

        assert result.success is False
        assert result.error_code == "user_deactivated"

    def test_validate_team_inactive(self, auth_service, test_db_session, sample_user):
        """Test validation fails for user in inactive team."""
        user = sample_user(email="teamless@example.com")

        # Deactivate the team
        user.team.is_active = False
        test_db_session.commit()

        result = auth_service._validate_and_authenticate(
            email="teamless@example.com",
            provider="google",
            oauth_subject="google-123",
            user_info={},
        )

        assert result.success is False
        assert result.error_code == "team_inactive"

    def test_validate_success(self, auth_service, sample_user):
        """Test successful validation."""
        user = sample_user(
            email="valid@example.com",
            is_active=True,
            status=UserStatus.ACTIVE,
        )

        result = auth_service._validate_and_authenticate(
            email="valid@example.com",
            provider="google",
            oauth_subject="google-123",
            user_info={"name": "Test User", "picture": "https://example.com/pic.jpg"},
        )

        assert result.success is True
        assert result.user is not None
        assert result.user.email == "valid@example.com"

    def test_validate_updates_oauth_profile(self, auth_service, sample_user, test_db_session):
        """Test that validation updates OAuth profile data."""
        user = sample_user(email="oauth@example.com", status=UserStatus.PENDING)

        result = auth_service._validate_and_authenticate(
            email="oauth@example.com",
            provider="microsoft",
            oauth_subject="ms-456",
            user_info={"name": "OAuth User", "picture": "https://example.com/avatar.jpg"},
        )

        assert result.success is True

        # Refresh to get updated data
        test_db_session.refresh(result.user)
        assert result.user.oauth_provider == "microsoft"
        assert result.user.oauth_subject == "ms-456"
        assert result.user.display_name == "OAuth User"
        assert result.user.picture_url == "https://example.com/avatar.jpg"

    def test_validate_activates_pending_user(self, auth_service, sample_user, test_db_session):
        """Test that first login activates pending user."""
        user = sample_user(email="pending@example.com", status=UserStatus.PENDING)

        result = auth_service._validate_and_authenticate(
            email="pending@example.com",
            provider="google",
            oauth_subject="google-789",
            user_info={},
        )

        assert result.success is True

        test_db_session.refresh(result.user)
        assert result.user.status == UserStatus.ACTIVE


# ============================================================================
# Session Tests
# ============================================================================


class TestAuthServiceSession:
    """Tests for session management."""

    def test_create_session(self, auth_service, sample_user, mock_request):
        """Test creating a session."""
        user = sample_user(email="session@example.com")

        auth_service.create_session(mock_request, user)

        assert mock_request.session["user_guid"] == user.guid
        assert mock_request.session["team_guid"] == user.team.guid
        assert mock_request.session["email"] == user.email
        assert "authenticated_at" in mock_request.session
        # Numeric IDs should NOT be in session (M4 security fix)
        assert "user_id" not in mock_request.session
        assert "team_id" not in mock_request.session

    def test_clear_session(self, auth_service, mock_request):
        """Test clearing a session."""
        mock_request.session["user_id"] = 1
        mock_request.session["email"] = "test@example.com"

        auth_service.clear_session(mock_request)

        assert mock_request.session == {}

    def test_is_authenticated_true(self, auth_service, mock_request):
        """Test is_authenticated when session exists."""
        mock_request.session["user_guid"] = "usr_01hgw2bbg0000000000000001"

        assert auth_service.is_authenticated(mock_request) is True

    def test_is_authenticated_false(self, auth_service, mock_request):
        """Test is_authenticated when no session."""
        assert auth_service.is_authenticated(mock_request) is False

    def test_get_session_user(self, auth_service, sample_user, mock_request):
        """Test getting user from session."""
        user = sample_user(email="getuser@example.com")
        mock_request.session["user_guid"] = user.guid

        result = auth_service.get_session_user(mock_request)

        assert result is not None
        assert result.id == user.id

    def test_get_session_user_not_found(self, auth_service, mock_request):
        """Test getting user when GUID not in database."""
        mock_request.session["user_guid"] = "usr_00000000000000000000000000"

        result = auth_service.get_session_user(mock_request)

        assert result is None
        # Session should be cleared
        assert mock_request.session == {}

    def test_get_current_user_info(self, auth_service, mock_request):
        """Test getting current user info from session."""
        mock_request.session = {
            "user_guid": "usr_123",
            "team_guid": "ten_456",
            "email": "info@example.com",
            "is_super_admin": False,
        }

        result = auth_service.get_current_user_info(mock_request)

        assert result is not None
        assert result["email"] == "info@example.com"
        assert result["user_guid"] == "usr_123"

    def test_get_current_user_info_not_authenticated(self, auth_service, mock_request):
        """Test getting user info when not authenticated."""
        result = auth_service.get_current_user_info(mock_request)

        assert result is None
