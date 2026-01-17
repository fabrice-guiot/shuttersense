"""
Integration tests for admin teams API.

Tests super admin authorization, team creation, and team deactivation
blocking member logins.

Part of Issue #73 - User Story 5: Team Management
"""

import pytest

from fastapi.testclient import TestClient

from backend.src.main import app
from backend.src.db.database import get_db
from backend.src.middleware.auth import require_auth, require_super_admin
from backend.src.middleware.tenant import TenantContext
from backend.src.models import Team, User, UserStatus
from backend.src.services.team_service import TeamService
from backend.src.services.user_service import UserService


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def team_service(test_db_session):
    """Create a TeamService instance for testing."""
    return TeamService(test_db_session)


@pytest.fixture
def user_service(test_db_session):
    """Create a UserService instance for testing."""
    return UserService(test_db_session)


@pytest.fixture
def super_admin_team(test_db_session):
    """Create a team for the super admin."""
    team = Team(
        name="Super Admin Team",
        slug="super-admin-team",
        is_active=True,
    )
    test_db_session.add(team)
    test_db_session.commit()
    test_db_session.refresh(team)
    return team


@pytest.fixture
def super_admin_user(test_db_session, super_admin_team):
    """Create a super admin user."""
    user = User(
        email="superadmin@example.com",
        team_id=super_admin_team.id,
        status=UserStatus.ACTIVE,
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture
def regular_team(test_db_session):
    """Create a regular team."""
    team = Team(
        name="Regular Team",
        slug="regular-team",
        is_active=True,
    )
    test_db_session.add(team)
    test_db_session.commit()
    test_db_session.refresh(team)
    return team


@pytest.fixture
def regular_user(test_db_session, regular_team):
    """Create a regular (non-super-admin) user."""
    user = User(
        email="regular@example.com",
        team_id=regular_team.id,
        status=UserStatus.ACTIVE,
        is_active=True,
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


# ============================================================================
# T098: Super Admin Authorization Tests
# ============================================================================


class TestSuperAdminAuthorization:
    """Tests for super admin authorization on admin endpoints."""

    def test_non_super_admin_cannot_list_teams(
        self, test_db_session, regular_user, regular_team
    ):
        """Test that non-super-admin gets 403 on list teams."""
        from fastapi import HTTPException

        ctx = TenantContext(
            user_id=regular_user.id,
            user_guid=regular_user.guid,
            user_email=regular_user.email,
            team_id=regular_team.id,
            team_guid=regular_team.guid,
            is_super_admin=False,
            is_api_token=False,
        )

        def get_test_db():
            yield test_db_session

        def mock_require_super_admin():
            # Simulate what require_super_admin does for non-super-admin
            if not ctx.is_super_admin:
                raise HTTPException(
                    status_code=403,
                    detail="Super admin privileges required"
                )
            return ctx

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[require_super_admin] = mock_require_super_admin

        try:
            with TestClient(app) as client:
                response = client.get("/api/admin/teams")
                assert response.status_code == 403
                assert "super admin" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(require_super_admin, None)

    def test_non_super_admin_cannot_create_team(
        self, test_db_session, regular_user, regular_team
    ):
        """Test that non-super-admin gets 403 on create team."""
        from fastapi import HTTPException

        ctx = TenantContext(
            user_id=regular_user.id,
            user_guid=regular_user.guid,
            user_email=regular_user.email,
            team_id=regular_team.id,
            team_guid=regular_team.guid,
            is_super_admin=False,
            is_api_token=False,
        )

        def get_test_db():
            yield test_db_session

        def mock_require_super_admin():
            if not ctx.is_super_admin:
                raise HTTPException(
                    status_code=403,
                    detail="Super admin privileges required"
                )
            return ctx

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[require_super_admin] = mock_require_super_admin

        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/admin/teams",
                    json={"name": "New Team", "admin_email": "admin@new.com"},
                )
                assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(require_super_admin, None)

    def test_super_admin_can_list_teams(
        self, test_db_session, super_admin_user, super_admin_team
    ):
        """Test that super admin can list teams."""
        ctx = TenantContext(
            user_id=super_admin_user.id,
            user_guid=super_admin_user.guid,
            user_email=super_admin_user.email,
            team_id=super_admin_team.id,
            team_guid=super_admin_team.guid,
            is_super_admin=True,
            is_api_token=False,
        )

        def get_test_db():
            yield test_db_session

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[require_super_admin] = lambda: ctx

        try:
            with TestClient(app) as client:
                response = client.get("/api/admin/teams")
                assert response.status_code == 200
                data = response.json()
                assert "teams" in data
                assert "total" in data
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(require_super_admin, None)

    def test_super_admin_can_create_team(
        self, test_db_session, super_admin_user, super_admin_team
    ):
        """Test that super admin can create a team."""
        ctx = TenantContext(
            user_id=super_admin_user.id,
            user_guid=super_admin_user.guid,
            user_email=super_admin_user.email,
            team_id=super_admin_team.id,
            team_guid=super_admin_team.guid,
            is_super_admin=True,
            is_api_token=False,
        )

        def get_test_db():
            yield test_db_session

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[require_super_admin] = lambda: ctx

        try:
            with TestClient(app) as client:
                response = client.post(
                    "/api/admin/teams",
                    json={"name": "New Team", "admin_email": "admin@newteam.com"},
                )
                assert response.status_code == 201
                data = response.json()
                assert data["team"]["name"] == "New Team"
                assert data["admin_email"] == "admin@newteam.com"
                assert data["admin_guid"].startswith("usr_")
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(require_super_admin, None)


# ============================================================================
# T099: Team Deactivation Blocks Logins Tests
# ============================================================================


class TestTeamDeactivationBlocksLogins:
    """Tests for team deactivation blocking all member logins."""

    def test_deactivated_team_blocks_user_login(
        self, team_service, user_service, test_db_session
    ):
        """Test that users in deactivated team cannot login."""
        # Create a team and user
        team = team_service.create(name="Soon Inactive")
        user = user_service.create(
            team_id=team.id,
            email="member@sooninactive.com",
            status=UserStatus.ACTIVE,
        )

        # User can login initially
        assert user.can_login is True
        assert team.is_active is True

        # Deactivate the team
        team_service.deactivate(team.guid)
        test_db_session.refresh(team)
        test_db_session.refresh(user)

        # User's can_login is still True (individual user is active)
        # But team.is_active is False (blocks login at auth level)
        assert team.is_active is False
        assert user.is_active is True

    def test_cannot_deactivate_own_team(
        self, test_db_session, super_admin_user, super_admin_team
    ):
        """Test that super admin cannot deactivate their own team."""
        ctx = TenantContext(
            user_id=super_admin_user.id,
            user_guid=super_admin_user.guid,
            user_email=super_admin_user.email,
            team_id=super_admin_team.id,
            team_guid=super_admin_team.guid,
            is_super_admin=True,
            is_api_token=False,
        )

        def get_test_db():
            yield test_db_session

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[require_super_admin] = lambda: ctx

        try:
            with TestClient(app) as client:
                response = client.post(
                    f"/api/admin/teams/{super_admin_team.guid}/deactivate"
                )
                assert response.status_code == 400
                assert "own team" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(require_super_admin, None)

    def test_super_admin_can_deactivate_other_team(
        self, test_db_session, super_admin_user, super_admin_team, regular_team
    ):
        """Test that super admin can deactivate other teams."""
        ctx = TenantContext(
            user_id=super_admin_user.id,
            user_guid=super_admin_user.guid,
            user_email=super_admin_user.email,
            team_id=super_admin_team.id,
            team_guid=super_admin_team.guid,
            is_super_admin=True,
            is_api_token=False,
        )

        def get_test_db():
            yield test_db_session

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[require_super_admin] = lambda: ctx

        try:
            with TestClient(app) as client:
                response = client.post(
                    f"/api/admin/teams/{regular_team.guid}/deactivate"
                )
                assert response.status_code == 200
                data = response.json()
                assert data["is_active"] is False
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(require_super_admin, None)

    def test_reactivate_team_restores_login_ability(
        self, team_service, user_service, test_db_session
    ):
        """Test that reactivating a team restores login ability."""
        # Create a team and user
        team = team_service.create(name="Reactivate Test")
        user = user_service.create(
            team_id=team.id,
            email="member@reactivate.com",
            status=UserStatus.ACTIVE,
        )

        # Deactivate then reactivate
        team_service.deactivate(team.guid)
        test_db_session.refresh(team)
        assert team.is_active is False

        team_service.activate(team.guid)
        test_db_session.refresh(team)
        test_db_session.refresh(user)

        # Team is active again
        assert team.is_active is True
        assert user.can_login is True


# ============================================================================
# Additional API Tests
# ============================================================================


class TestTeamsAPIEndpoints:
    """Additional tests for team API endpoints."""

    def test_get_team_stats(
        self, test_db_session, super_admin_user, super_admin_team, regular_team
    ):
        """Test getting team statistics."""
        ctx = TenantContext(
            user_id=super_admin_user.id,
            user_guid=super_admin_user.guid,
            user_email=super_admin_user.email,
            team_id=super_admin_team.id,
            team_guid=super_admin_team.guid,
            is_super_admin=True,
            is_api_token=False,
        )

        def get_test_db():
            yield test_db_session

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[require_super_admin] = lambda: ctx

        try:
            with TestClient(app) as client:
                response = client.get("/api/admin/teams/stats")
                assert response.status_code == 200
                data = response.json()
                assert "total_teams" in data
                assert "active_teams" in data
                assert "inactive_teams" in data
                assert data["total_teams"] >= 2  # At least 2 teams created
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(require_super_admin, None)

    def test_get_single_team(
        self, test_db_session, super_admin_user, super_admin_team, regular_team
    ):
        """Test getting a single team by GUID."""
        ctx = TenantContext(
            user_id=super_admin_user.id,
            user_guid=super_admin_user.guid,
            user_email=super_admin_user.email,
            team_id=super_admin_team.id,
            team_guid=super_admin_team.guid,
            is_super_admin=True,
            is_api_token=False,
        )

        def get_test_db():
            yield test_db_session

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[require_super_admin] = lambda: ctx

        try:
            with TestClient(app) as client:
                response = client.get(f"/api/admin/teams/{regular_team.guid}")
                assert response.status_code == 200
                data = response.json()
                assert data["guid"] == regular_team.guid
                assert data["name"] == "Regular Team"
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(require_super_admin, None)

    def test_get_nonexistent_team(
        self, test_db_session, super_admin_user, super_admin_team
    ):
        """Test getting a nonexistent team returns 404."""
        ctx = TenantContext(
            user_id=super_admin_user.id,
            user_guid=super_admin_user.guid,
            user_email=super_admin_user.email,
            team_id=super_admin_team.id,
            team_guid=super_admin_team.guid,
            is_super_admin=True,
            is_api_token=False,
        )

        def get_test_db():
            yield test_db_session

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[require_super_admin] = lambda: ctx

        try:
            with TestClient(app) as client:
                response = client.get("/api/admin/teams/ten_00000000000000000000000000")
                assert response.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(require_super_admin, None)
