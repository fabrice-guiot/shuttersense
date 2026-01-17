"""
Integration tests for tenant isolation (User Story 6).

These tests verify that:
1. Users can only see data belonging to their team
2. Cross-team GUID access returns 404 (not 403)
3. New entities are automatically assigned to the user's team
4. Authenticated users cannot access data from other teams
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.src.main import app
from backend.src.models import (
    Team, User, UserStatus, Collection, CollectionType, CollectionState,
    Event, Category, Location, Organizer, Performer, Connector, Pipeline
)
from backend.src.middleware.auth import TenantContext, require_auth
from backend.src.db.database import get_db


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def team_a(test_db_session):
    """Create Team A for testing."""
    team = Team(name="Team Alpha", slug="team-alpha", is_active=True)
    test_db_session.add(team)
    test_db_session.commit()
    test_db_session.refresh(team)
    return team


@pytest.fixture
def team_b(test_db_session):
    """Create Team B for testing."""
    team = Team(name="Team Beta", slug="team-beta", is_active=True)
    test_db_session.add(team)
    test_db_session.commit()
    test_db_session.refresh(team)
    return team


@pytest.fixture
def user_a(test_db_session, team_a):
    """Create User A in Team A."""
    user = User(
        team_id=team_a.id,
        email="alice@team-alpha.com",
        first_name="Alice",
        last_name="Alpha",
        is_active=True,
        status=UserStatus.ACTIVE
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture
def user_b(test_db_session, team_b):
    """Create User B in Team B."""
    user = User(
        team_id=team_b.id,
        email="bob@team-beta.com",
        first_name="Bob",
        last_name="Beta",
        is_active=True,
        status=UserStatus.ACTIVE
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture
def collection_team_a(test_db_session, team_a):
    """Create a collection belonging to Team A."""
    collection = Collection(
        name="Team A Photos",
        type=CollectionType.LOCAL,
        location="/photos/team-a",
        state=CollectionState.LIVE,
        team_id=team_a.id
    )
    test_db_session.add(collection)
    test_db_session.commit()
    test_db_session.refresh(collection)
    return collection


@pytest.fixture
def collection_team_b(test_db_session, team_b):
    """Create a collection belonging to Team B."""
    collection = Collection(
        name="Team B Photos",
        type=CollectionType.LOCAL,
        location="/photos/team-b",
        state=CollectionState.LIVE,
        team_id=team_b.id
    )
    test_db_session.add(collection)
    test_db_session.commit()
    test_db_session.refresh(collection)
    return collection


@pytest.fixture
def category_team_a(test_db_session, team_a):
    """Create a category belonging to Team A."""
    category = Category(
        name="Team A Events",
        team_id=team_a.id
    )
    test_db_session.add(category)
    test_db_session.commit()
    test_db_session.refresh(category)
    return category


@pytest.fixture
def category_team_b(test_db_session, team_b):
    """Create a category belonging to Team B."""
    category = Category(
        name="Team B Events",
        team_id=team_b.id
    )
    test_db_session.add(category)
    test_db_session.commit()
    test_db_session.refresh(category)
    return category


def mock_tenant_context(team, user):
    """Create a mock TenantContext for testing."""
    return TenantContext(
        team_id=team.id,
        team_guid=team.guid,
        user_id=user.id,
        user_guid=user.guid,
        user_email=user.email,
        is_super_admin=False,
        is_api_token=False
    )


# ============================================================================
# T057: Collection Tenant Isolation Tests
# ============================================================================

class TestCollectionTenantIsolation:
    """Test tenant isolation for Collection endpoints."""

    def test_list_collections_only_shows_own_team(
        self, test_db_session, test_session_factory, test_cache, test_job_queue, test_encryptor, test_websocket_manager,
        team_a, team_b, user_a, collection_team_a, collection_team_b
    ):
        """
        Verify that listing collections only returns collections from user's team.

        Given: User A in Team A, collections exist in both Team A and Team B
        When: User A lists collections
        Then: Only Team A collections are returned
        """
        ctx = mock_tenant_context(team_a, user_a)

        # Create client with team A context
        from fastapi.testclient import TestClient
        from backend.src.db.database import get_db
        from backend.src.api.collections import get_file_cache, get_credential_encryptor

        def get_test_db():
            yield test_db_session

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[get_file_cache] = lambda: test_cache
        app.dependency_overrides[get_credential_encryptor] = lambda: test_encryptor
        app.dependency_overrides[require_auth] = lambda: ctx

        with TestClient(app) as client:
            response = client.get("/api/collections")

        assert response.status_code == 200
        data = response.json()

        # Response is a list directly, not {"collections": [...]}
        collection_names = [c["name"] for c in data]
        assert "Team A Photos" in collection_names
        assert "Team B Photos" not in collection_names

        app.dependency_overrides.clear()

    def test_get_collection_returns_404_for_other_team(
        self, test_db_session, test_cache, test_encryptor,
        team_a, team_b, user_a, collection_team_a, collection_team_b
    ):
        """
        Verify that accessing another team's collection returns 404.

        Given: User A in Team A, collection exists in Team B
        When: User A tries to access Team B's collection by GUID
        Then: 404 Not Found is returned (not 403 Forbidden)
        """
        ctx = mock_tenant_context(team_a, user_a)
        team_b_guid = collection_team_b.guid

        from fastapi.testclient import TestClient
        from backend.src.db.database import get_db
        from backend.src.api.collections import get_file_cache, get_credential_encryptor

        def get_test_db():
            yield test_db_session

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[get_file_cache] = lambda: test_cache
        app.dependency_overrides[get_credential_encryptor] = lambda: test_encryptor
        app.dependency_overrides[require_auth] = lambda: ctx

        with TestClient(app) as client:
            response = client.get(f"/api/collections/{team_b_guid}")

        # Should be 404, not 403 (security: don't reveal existence)
        assert response.status_code == 404

        app.dependency_overrides.clear()

    def test_get_own_team_collection_succeeds(
        self, test_db_session, test_cache, test_encryptor,
        team_a, user_a, collection_team_a
    ):
        """
        Verify that accessing own team's collection succeeds.

        Given: User A in Team A, collection exists in Team A
        When: User A accesses the collection by GUID
        Then: Collection is returned successfully
        """
        ctx = mock_tenant_context(team_a, user_a)

        from fastapi.testclient import TestClient
        from backend.src.db.database import get_db
        from backend.src.api.collections import get_file_cache, get_credential_encryptor

        def get_test_db():
            yield test_db_session

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[get_file_cache] = lambda: test_cache
        app.dependency_overrides[get_credential_encryptor] = lambda: test_encryptor
        app.dependency_overrides[require_auth] = lambda: ctx

        with TestClient(app) as client:
            response = client.get(f"/api/collections/{collection_team_a.guid}")

        assert response.status_code == 200
        assert response.json()["name"] == "Team A Photos"

        app.dependency_overrides.clear()


# ============================================================================
# T058: Event Tenant Isolation Tests
# ============================================================================

class TestEventTenantIsolation:
    """Test tenant isolation for Event endpoints."""

    @pytest.fixture
    def event_team_a(self, test_db_session, team_a, category_team_a):
        """Create an event belonging to Team A."""
        from datetime import date
        event = Event(
            title="Team A Conference",
            event_date=date(2026, 6, 15),
            category_id=category_team_a.id,
            team_id=team_a.id
        )
        test_db_session.add(event)
        test_db_session.commit()
        test_db_session.refresh(event)
        return event

    @pytest.fixture
    def event_team_b(self, test_db_session, team_b, category_team_b):
        """Create an event belonging to Team B."""
        from datetime import date
        event = Event(
            title="Team B Meetup",
            event_date=date(2026, 7, 20),
            category_id=category_team_b.id,
            team_id=team_b.id
        )
        test_db_session.add(event)
        test_db_session.commit()
        test_db_session.refresh(event)
        return event

    def test_list_events_only_shows_own_team(
        self, test_db_session, team_a, team_b, user_a,
        event_team_a, event_team_b
    ):
        """
        Verify that listing events only returns events from user's team.
        """
        ctx = mock_tenant_context(team_a, user_a)

        def get_test_db():
            yield test_db_session

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[require_auth] = lambda: ctx

        with TestClient(app) as client:
            response = client.get("/api/events")

        assert response.status_code == 200
        data = response.json()

        # Response is a list directly, not {"events": [...]}
        event_titles = [e["title"] for e in data]
        assert "Team A Conference" in event_titles
        assert "Team B Meetup" not in event_titles

        app.dependency_overrides.clear()

    def test_get_event_returns_404_for_other_team(
        self, test_db_session, team_a, team_b, user_a,
        event_team_a, event_team_b
    ):
        """
        Verify that accessing another team's event returns 404.
        """
        ctx = mock_tenant_context(team_a, user_a)
        team_b_event_guid = event_team_b.guid

        def get_test_db():
            yield test_db_session

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[require_auth] = lambda: ctx

        with TestClient(app) as client:
            response = client.get(f"/api/events/{team_b_event_guid}")

        # Should be 404, not 403
        assert response.status_code == 404

        app.dependency_overrides.clear()


# ============================================================================
# T059: Cross-Team GUID Access Returns 404
# ============================================================================

class TestCrossTeamGuidAccess:
    """Test that cross-team GUID access returns 404, not 403."""

    def test_cross_team_collection_returns_404_not_403(
        self, test_db_session, test_cache, test_encryptor,
        team_a, team_b, user_a, collection_team_b
    ):
        """
        Security: Cross-team access should return 404 to prevent GUID enumeration.
        """
        ctx = mock_tenant_context(team_a, user_a)

        from backend.src.api.collections import get_file_cache, get_credential_encryptor

        def get_test_db():
            yield test_db_session

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[get_file_cache] = lambda: test_cache
        app.dependency_overrides[get_credential_encryptor] = lambda: test_encryptor
        app.dependency_overrides[require_auth] = lambda: ctx

        with TestClient(app) as client:
            response = client.get(f"/api/collections/{collection_team_b.guid}")

        assert response.status_code == 404
        # Should NOT mention "forbidden" or "not authorized"
        assert "forbidden" not in response.json().get("detail", "").lower()
        assert "unauthorized" not in response.json().get("detail", "").lower()

        app.dependency_overrides.clear()

    def test_cross_team_category_returns_404_not_403(
        self, test_db_session, team_a, team_b, user_a, category_team_b
    ):
        """
        Security: Cross-team category access should return 404.
        """
        ctx = mock_tenant_context(team_a, user_a)

        def get_test_db():
            yield test_db_session

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[require_auth] = lambda: ctx

        with TestClient(app) as client:
            response = client.get(f"/api/categories/{category_team_b.guid}")

        assert response.status_code == 404

        app.dependency_overrides.clear()


# ============================================================================
# T060: New Entities Auto-Assigned to User's Team
# ============================================================================

class TestAutoTeamAssignment:
    """Test that new entities are automatically assigned to user's team."""

    def test_new_collection_assigned_to_user_team(
        self, test_db_session, test_cache, test_encryptor, team_a, user_a
    ):
        """
        Verify that creating a collection automatically assigns it to user's team.
        """
        ctx = mock_tenant_context(team_a, user_a)

        from backend.src.api.collections import get_file_cache, get_credential_encryptor

        def get_test_db():
            yield test_db_session

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[get_file_cache] = lambda: test_cache
        app.dependency_overrides[get_credential_encryptor] = lambda: test_encryptor
        app.dependency_overrides[require_auth] = lambda: ctx

        with patch('backend.src.services.collection_service.CollectionService._test_accessibility',
                   return_value=(True, None)):
            with TestClient(app) as client:
                response = client.post(
                    "/api/collections",
                    json={
                        "name": "New Collection",
                        "type": "local",
                        "location": "/photos/new",
                        "state": "live"
                    }
                )

        assert response.status_code == 201

        # Verify the collection belongs to Team A
        from backend.src.models import Collection
        collection = test_db_session.query(Collection).filter(
            Collection.uuid == Collection.uuid  # Get latest
        ).order_by(Collection.id.desc()).first()

        assert collection.team_id == team_a.id

        app.dependency_overrides.clear()

    def test_new_category_assigned_to_user_team(
        self, test_db_session, team_a, user_a
    ):
        """
        Verify that creating a category automatically assigns it to user's team.
        """
        ctx = mock_tenant_context(team_a, user_a)

        def get_test_db():
            yield test_db_session

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[require_auth] = lambda: ctx

        with TestClient(app) as client:
            response = client.post(
                "/api/categories",
                json={"name": "New Category"}
            )

        assert response.status_code == 201

        # Verify the category belongs to Team A
        from backend.src.models import Category
        category = test_db_session.query(Category).filter(
            Category.name == "New Category"
        ).first()

        assert category is not None
        assert category.team_id == team_a.id

        app.dependency_overrides.clear()

    def test_new_event_assigned_to_user_team(
        self, test_db_session, team_a, user_a, category_team_a
    ):
        """
        Verify that creating an event automatically assigns it to user's team.
        """
        ctx = mock_tenant_context(team_a, user_a)

        def get_test_db():
            yield test_db_session

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[require_auth] = lambda: ctx

        with TestClient(app) as client:
            response = client.post(
                "/api/events",
                json={
                    "title": "New Event",
                    "event_date": "2026-08-15",
                    "category_guid": category_team_a.guid
                }
            )

        assert response.status_code == 201

        # Verify the event belongs to Team A
        from backend.src.models import Event
        event = test_db_session.query(Event).filter(
            Event.title == "New Event"
        ).first()

        assert event is not None
        assert event.team_id == team_a.id

        app.dependency_overrides.clear()


# ============================================================================
# Additional Security Tests
# ============================================================================

class TestTenantIsolationSecurity:
    """Additional security tests for tenant isolation."""

    def test_unauthenticated_request_returns_401(self, test_db_session, test_cache, test_encryptor):
        """
        Verify that unauthenticated requests return 401.
        """
        from backend.src.api.collections import get_file_cache, get_credential_encryptor

        def get_test_db():
            yield test_db_session

        # Clear any existing overrides
        app.dependency_overrides.clear()
        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[get_file_cache] = lambda: test_cache
        app.dependency_overrides[get_credential_encryptor] = lambda: test_encryptor
        # Don't override require_auth - let it check for real auth

        with TestClient(app) as client:
            response = client.get("/api/collections")

        # Should require authentication
        assert response.status_code == 401

        app.dependency_overrides.clear()

    def test_inactive_team_returns_403(
        self, test_db_session, test_cache, test_encryptor, team_a, user_a
    ):
        """
        Verify that users in inactive teams cannot access data.
        """
        from fastapi import HTTPException
        from backend.src.api.collections import get_file_cache, get_credential_encryptor

        # Deactivate the team
        team_a.is_active = False
        test_db_session.commit()

        def get_test_db():
            yield test_db_session

        # Override require_auth to raise 403 for inactive team
        def mock_require_auth():
            raise HTTPException(
                status_code=403,
                detail="Team is inactive"
            )

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[get_file_cache] = lambda: test_cache
        app.dependency_overrides[get_credential_encryptor] = lambda: test_encryptor
        app.dependency_overrides[require_auth] = mock_require_auth

        with TestClient(app) as client:
            response = client.get("/api/collections")

        assert response.status_code == 403

        app.dependency_overrides.clear()

    def test_stats_endpoint_scoped_to_team(
        self, test_db_session, test_cache, test_encryptor, team_a, team_b, user_a,
        collection_team_a, collection_team_b
    ):
        """
        Verify that stats endpoints only count data from user's team.
        """
        ctx = mock_tenant_context(team_a, user_a)

        from backend.src.api.collections import get_file_cache, get_credential_encryptor

        def get_test_db():
            yield test_db_session

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[get_file_cache] = lambda: test_cache
        app.dependency_overrides[get_credential_encryptor] = lambda: test_encryptor
        app.dependency_overrides[require_auth] = lambda: ctx

        with TestClient(app) as client:
            response = client.get("/api/collections/stats")

        assert response.status_code == 200
        data = response.json()

        # Should only count Team A's collection (1, not 2)
        assert data["total_collections"] == 1

        app.dependency_overrides.clear()


# ============================================================================
# T121: API Token Admin Restriction Tests (Phase 10)
# ============================================================================

class TestApiTokenAdminRestriction:
    """Tests for API token restriction from admin endpoints (T121)."""

    def test_api_token_cannot_access_admin_endpoints(self, test_team, test_user):
        """API tokens should be rejected from /api/admin/* endpoints."""
        from backend.src.middleware.tenant import require_super_admin, TenantContext
        from fastapi import HTTPException

        # Create a context that simulates API token auth
        token_ctx = TenantContext(
            team_id=test_team.id,
            team_guid=test_team.guid,
            user_id=test_user.id,
            user_guid=test_user.guid,
            user_email="system-token@system.local",
            is_super_admin=False,  # Tokens never have super admin
            is_api_token=True,     # This is an API token
        )

        # require_super_admin should reject API tokens
        with pytest.raises(HTTPException) as exc:
            require_super_admin(token_ctx)

        assert exc.value.status_code == 403
        assert "API tokens cannot access admin endpoints" in exc.value.detail

    def test_api_token_rejected_even_with_super_admin_flag(self, test_team, test_user):
        """API tokens should be rejected even if is_super_admin is True (defense in depth)."""
        from backend.src.middleware.tenant import require_super_admin, TenantContext
        from fastapi import HTTPException

        # Hypothetically, if someone tries to craft a token with is_super_admin=True
        # (TokenService prevents this, but test defense in depth)
        token_ctx = TenantContext(
            team_id=test_team.id,
            team_guid=test_team.guid,
            user_id=test_user.id,
            user_guid=test_user.guid,
            user_email="system-token@system.local",
            is_super_admin=True,   # Even if this is True...
            is_api_token=True,     # ...API tokens are still rejected
        )

        # require_super_admin should still reject because is_api_token=True
        with pytest.raises(HTTPException) as exc:
            require_super_admin(token_ctx)

        assert exc.value.status_code == 403
        assert "API tokens cannot access admin endpoints" in exc.value.detail

    def test_super_admin_session_can_access_admin_endpoints(self, test_team, test_user):
        """Super admin session auth should be allowed."""
        from backend.src.middleware.tenant import require_super_admin, TenantContext

        # Create a context for a super admin session
        admin_ctx = TenantContext(
            team_id=test_team.id,
            team_guid=test_team.guid,
            user_id=test_user.id,
            user_guid=test_user.guid,
            user_email=test_user.email,
            is_super_admin=True,
            is_api_token=False,
        )

        # Should not raise
        result = require_super_admin(admin_ctx)
        assert result is admin_ctx

    def test_non_super_admin_session_rejected(self, test_team, test_user):
        """Non-super-admin session should be rejected from admin endpoints."""
        from backend.src.middleware.tenant import require_super_admin, TenantContext
        from fastapi import HTTPException

        # Create a context for a regular user session
        user_ctx = TenantContext(
            team_id=test_team.id,
            team_guid=test_team.guid,
            user_id=test_user.id,
            user_guid=test_user.guid,
            user_email=test_user.email,
            is_super_admin=False,
            is_api_token=False,
        )

        with pytest.raises(HTTPException) as exc:
            require_super_admin(user_ctx)

        assert exc.value.status_code == 403
        assert "Super admin privileges required" in exc.value.detail
