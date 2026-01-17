"""
Tests for TokenService - API token generation and validation.

Phase 10: User Story 7 - API Token Authentication

Tests cover:
- T117: TokenService.generate_token() creates tokens with system users
- T118: TokenService.validate_token() validates JWT and returns context
- T119: TokenService.revoke_token() revokes tokens properly
- T120: Token lifecycle (expiration handling)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from backend.src.models import User, UserStatus, UserType, Team


class TestUserTypeModel:
    """Tests for UserType enum and related model properties."""

    def test_user_type_human_default(self, test_db_session, test_team):
        """New users default to HUMAN type."""
        user = User(
            team_id=test_team.id,
            email='newuser@example.com',
            status=UserStatus.ACTIVE,
        )
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        assert user.user_type == UserType.HUMAN
        assert user.is_human_user is True
        assert user.is_system_user is False

    def test_user_type_system_explicit(self, test_db_session, test_team):
        """System users can be created explicitly."""
        user = User(
            team_id=test_team.id,
            email='system-token@system.local',
            status=UserStatus.ACTIVE,
            user_type=UserType.SYSTEM,
        )
        test_db_session.add(user)
        test_db_session.commit()
        test_db_session.refresh(user)

        assert user.user_type == UserType.SYSTEM
        assert user.is_system_user is True
        assert user.is_human_user is False

    def test_system_user_cannot_login(self, test_system_user):
        """System users cannot log in via OAuth (can_login is False)."""
        assert test_system_user.user_type == UserType.SYSTEM
        assert test_system_user.can_login is False

    def test_human_user_can_login(self, test_user):
        """Human users can log in via OAuth."""
        assert test_user.user_type == UserType.HUMAN
        assert test_user.can_login is True

    def test_inactive_human_cannot_login(self, test_db_session, test_team):
        """Inactive human users cannot login."""
        user = User(
            team_id=test_team.id,
            email='inactive@example.com',
            status=UserStatus.ACTIVE,
            user_type=UserType.HUMAN,
            is_active=False,
        )
        test_db_session.add(user)
        test_db_session.commit()

        assert user.can_login is False

    def test_deactivated_human_cannot_login(self, test_db_session, test_team):
        """Deactivated human users cannot login."""
        user = User(
            team_id=test_team.id,
            email='deactivated@example.com',
            status=UserStatus.DEACTIVATED,
            user_type=UserType.HUMAN,
        )
        test_db_session.add(user)
        test_db_session.commit()

        assert user.can_login is False


class TestUserServiceSystemUserFiltering:
    """Tests for filtering system users from user lists."""

    def test_list_by_team_excludes_system_users_by_default(
        self, test_db_session, test_team, test_user, test_system_user
    ):
        """list_by_team excludes system users by default."""
        from backend.src.services.user_service import UserService

        service = UserService(test_db_session)
        users = service.list_by_team(test_team.id)

        # Should only return human user
        assert len(users) == 1
        assert users[0].id == test_user.id
        assert users[0].user_type == UserType.HUMAN

    def test_list_by_team_includes_system_users_when_requested(
        self, test_db_session, test_team, test_user, test_system_user
    ):
        """list_by_team includes system users when explicitly requested."""
        from backend.src.services.user_service import UserService

        service = UserService(test_db_session)
        users = service.list_by_team(test_team.id, include_system_users=True)

        # Should return both users
        assert len(users) == 2
        user_types = {u.user_type for u in users}
        assert UserType.HUMAN in user_types
        assert UserType.SYSTEM in user_types

    def test_count_by_team_excludes_system_users_by_default(
        self, test_db_session, test_team, test_user, test_system_user
    ):
        """count_by_team excludes system users by default."""
        from backend.src.services.user_service import UserService

        service = UserService(test_db_session)
        count = service.count_by_team(test_team.id)

        # Should only count human user
        assert count == 1

    def test_count_by_team_includes_system_users_when_requested(
        self, test_db_session, test_team, test_user, test_system_user
    ):
        """count_by_team includes system users when explicitly requested."""
        from backend.src.services.user_service import UserService

        service = UserService(test_db_session)
        count = service.count_by_team(test_team.id, include_system_users=True)

        # Should count both users
        assert count == 2


class TestAuthServiceSystemUserBlock:
    """Tests for blocking system users from OAuth login (T122)."""

    def test_system_user_oauth_login_blocked(self, test_db_session, test_system_user):
        """System user attempting OAuth login gets blocked."""
        from backend.src.services.auth_service import AuthService

        service = AuthService(test_db_session)

        result = service._validate_and_authenticate(
            email=test_system_user.email,
            provider='google',
            oauth_subject='google-sub-123',
            user_info={'email': test_system_user.email, 'name': 'System User'},
        )

        assert result.success is False
        assert result.error_code == 'system_user_login_blocked'
        assert 'cannot be used for interactive login' in result.error

    def test_human_user_oauth_login_allowed(self, test_db_session, test_user):
        """Human user OAuth login proceeds normally."""
        from backend.src.services.auth_service import AuthService

        service = AuthService(test_db_session)

        result = service._validate_and_authenticate(
            email=test_user.email,
            provider='google',
            oauth_subject='google-sub-456',
            user_info={'email': test_user.email, 'name': 'Test User'},
        )

        assert result.success is True
        assert result.user is not None
        assert result.user.id == test_user.id


class TestTokenServiceGenerate:
    """Tests for TokenService.generate_token (T117)."""

    JWT_SECRET = "test-secret-key-for-tokens"

    def test_generate_token_creates_system_user(self, test_db_session, test_team, test_user):
        """TokenService.generate_token creates a system user for the token."""
        from backend.src.services.token_service import TokenService

        service = TokenService(test_db_session, self.JWT_SECRET)
        jwt_token, api_token = service.generate_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
            name="Test Token",
        )

        # Verify system user was created
        assert api_token.system_user is not None
        assert api_token.system_user.user_type == UserType.SYSTEM
        assert api_token.system_user.team_id == test_team.id
        assert "API Token: Test Token" in api_token.system_user.display_name

    def test_generate_token_returns_jwt(self, test_db_session, test_team, test_user):
        """TokenService.generate_token returns a JWT token string."""
        from backend.src.services.token_service import TokenService

        service = TokenService(test_db_session, self.JWT_SECRET)
        jwt_token, api_token = service.generate_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
            name="Test Token",
        )

        # JWT tokens have 3 parts separated by dots
        assert jwt_token is not None
        assert jwt_token.count('.') == 2

        # Token prefix should be stored
        assert api_token.token_prefix == jwt_token[:8]

    def test_generate_token_stores_hash(self, test_db_session, test_team, test_user):
        """TokenService.generate_token stores token hash for revocation lookup."""
        from backend.src.services.token_service import TokenService
        import hashlib

        service = TokenService(test_db_session, self.JWT_SECRET)
        jwt_token, api_token = service.generate_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
            name="Test Token",
        )

        expected_hash = hashlib.sha256(jwt_token.encode()).hexdigest()
        assert api_token.token_hash == expected_hash

    def test_generate_token_tracks_creator(self, test_db_session, test_team, test_user):
        """TokenService.generate_token tracks which user created the token."""
        from backend.src.services.token_service import TokenService

        service = TokenService(test_db_session, self.JWT_SECRET)
        jwt_token, api_token = service.generate_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
            name="Test Token",
        )

        assert api_token.created_by_user_id == test_user.id
        assert api_token.created_by.id == test_user.id

    def test_generate_token_validates_name(self, test_db_session, test_team, test_user):
        """TokenService.generate_token validates token name."""
        from backend.src.services.token_service import TokenService
        from backend.src.services.exceptions import ValidationError

        service = TokenService(test_db_session, self.JWT_SECRET)

        with pytest.raises(ValidationError) as exc:
            service.generate_token(
                team_id=test_team.id,
                created_by_user_id=test_user.id,
                name="",
            )
        assert "cannot be empty" in str(exc.value)


class TestTokenServiceValidate:
    """Tests for TokenService.validate_token (T118)."""

    JWT_SECRET = "test-secret-key-for-tokens"

    def test_validate_token_returns_context(self, test_db_session, test_team, test_user):
        """TokenService.validate_token returns TenantContext with is_api_token=True."""
        from backend.src.services.token_service import TokenService

        service = TokenService(test_db_session, self.JWT_SECRET)
        jwt_token, api_token = service.generate_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
            name="Test Token",
        )

        ctx = service.validate_token(jwt_token)

        assert ctx is not None
        assert ctx.is_api_token is True
        assert ctx.is_super_admin is False  # API tokens NEVER have super admin
        assert ctx.team_id == test_team.id
        assert ctx.user_id == api_token.system_user_id

    def test_validate_token_invalid_jwt_fails(self, test_db_session):
        """TokenService.validate_token rejects invalid JWT."""
        from backend.src.services.token_service import TokenService

        service = TokenService(test_db_session, self.JWT_SECRET)
        ctx = service.validate_token("invalid.jwt.token")

        assert ctx is None

    def test_validate_token_wrong_secret_fails(self, test_db_session, test_team, test_user):
        """TokenService.validate_token rejects tokens signed with wrong secret."""
        from backend.src.services.token_service import TokenService

        # Generate with one secret
        service1 = TokenService(test_db_session, "secret-1")
        jwt_token, _ = service1.generate_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
            name="Test Token",
        )

        # Validate with different secret
        service2 = TokenService(test_db_session, "secret-2")
        ctx = service2.validate_token(jwt_token)

        assert ctx is None


class TestTokenServiceExpiration:
    """Tests for token expiration handling (T120)."""

    JWT_SECRET = "test-secret-key-for-tokens"

    def test_validate_token_expired_fails(self, test_db_session, test_team, test_user):
        """TokenService.validate_token rejects expired tokens."""
        from backend.src.services.token_service import TokenService
        from datetime import datetime, timedelta

        service = TokenService(test_db_session, self.JWT_SECRET)
        jwt_token, api_token = service.generate_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
            name="Test Token",
            expires_in_days=1,
        )

        # Manually expire the token
        api_token.expires_at = datetime.utcnow() - timedelta(hours=1)
        test_db_session.commit()

        ctx = service.validate_token(jwt_token)
        assert ctx is None


class TestTokenServiceRevoke:
    """Tests for TokenService.revoke_token (T119)."""

    JWT_SECRET = "test-secret-key-for-tokens"

    def test_revoke_token_deactivates(self, test_db_session, test_team, test_user):
        """TokenService.revoke_token deactivates the token and system user."""
        from backend.src.services.token_service import TokenService

        service = TokenService(test_db_session, self.JWT_SECRET)
        jwt_token, api_token = service.generate_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
            name="Test Token",
        )

        # Verify token is active
        assert api_token.is_active is True
        assert api_token.system_user.is_active is True

        # Revoke
        service.revoke_token(api_token.guid)

        # Refresh and verify deactivated
        test_db_session.refresh(api_token)
        assert api_token.is_active is False
        assert api_token.system_user.is_active is False
        assert api_token.system_user.status == UserStatus.DEACTIVATED

    def test_validate_token_revoked_fails(self, test_db_session, test_team, test_user):
        """TokenService.validate_token rejects revoked tokens."""
        from backend.src.services.token_service import TokenService

        service = TokenService(test_db_session, self.JWT_SECRET)
        jwt_token, api_token = service.generate_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
            name="Test Token",
        )

        # Verify token works before revocation
        ctx = service.validate_token(jwt_token)
        assert ctx is not None

        # Revoke
        service.revoke_token(api_token.guid)

        # Verify token no longer works
        ctx = service.validate_token(jwt_token)
        assert ctx is None

    def test_revoke_token_not_found(self, test_db_session):
        """TokenService.revoke_token raises NotFoundError for unknown token."""
        from backend.src.services.token_service import TokenService
        from backend.src.services.exceptions import NotFoundError

        service = TokenService(test_db_session, self.JWT_SECRET)

        with pytest.raises(NotFoundError):
            service.revoke_token("tok_00000000000000000000000001")
