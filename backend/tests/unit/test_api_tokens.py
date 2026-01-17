"""
Tests for API token endpoints.

Phase 10: User Story 7 - API Token Authentication
Tasks T124-T129
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.src.main import app
from backend.src.models import User, UserStatus, Team
from backend.src.middleware.tenant import TenantContext, get_tenant_context
from backend.src.db.database import get_db


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


class TestTokenApiCreate:
    """Tests for POST /api/tokens (T124)."""

    def test_create_token_success(self, test_db_session, test_team, test_user):
        """Successfully create a new API token."""
        ctx = mock_tenant_context(test_team, test_user)

        def get_test_db():
            yield test_db_session

        # Set JWT_SECRET_KEY for tests
        with patch.dict('os.environ', {'JWT_SECRET_KEY': 'test-secret-key-at-least-32-chars'}):
            app.dependency_overrides[get_db] = get_test_db
            app.dependency_overrides[get_tenant_context] = lambda: ctx

            with TestClient(app) as client:
                response = client.post(
                    "/api/tokens",
                    json={
                        "name": "CI/CD Token",
                        "expires_in_days": 30
                    }
                )

            assert response.status_code == 201
            data = response.json()

            assert data["name"] == "CI/CD Token"
            assert "token" in data  # The actual JWT
            assert "guid" in data
            assert data["guid"].startswith("tok_")
            assert "token_prefix" in data
            assert data["token_prefix"] == data["token"][:8]

            app.dependency_overrides.clear()

    def test_create_token_validates_name(self, test_db_session, test_team, test_user):
        """Token name is validated."""
        ctx = mock_tenant_context(test_team, test_user)

        def get_test_db():
            yield test_db_session

        with patch.dict('os.environ', {'JWT_SECRET_KEY': 'test-secret-key-at-least-32-chars'}):
            app.dependency_overrides[get_db] = get_test_db
            app.dependency_overrides[get_tenant_context] = lambda: ctx

            with TestClient(app) as client:
                # Empty name
                response = client.post(
                    "/api/tokens",
                    json={"name": ""}
                )

            # Pydantic validation should reject empty name
            assert response.status_code == 422

            app.dependency_overrides.clear()

    def test_create_token_requires_session_auth(self, test_db_session, test_team, test_user):
        """API tokens cannot create new tokens."""
        # Context with is_api_token=True
        ctx = TenantContext(
            team_id=test_team.id,
            team_guid=test_team.guid,
            user_id=test_user.id,
            user_guid=test_user.guid,
            user_email=test_user.email,
            is_super_admin=False,
            is_api_token=True  # This is an API token auth
        )

        def get_test_db():
            yield test_db_session

        with patch.dict('os.environ', {'JWT_SECRET_KEY': 'test-secret-key-at-least-32-chars'}):
            app.dependency_overrides[get_db] = get_test_db
            app.dependency_overrides[get_tenant_context] = lambda: ctx

            with TestClient(app) as client:
                response = client.post(
                    "/api/tokens",
                    json={"name": "Test Token"}
                )

            assert response.status_code == 403
            assert "API tokens cannot create" in response.json()["detail"]

            app.dependency_overrides.clear()


class TestTokenApiList:
    """Tests for GET /api/tokens (T125)."""

    def test_list_tokens_empty(self, test_db_session, test_team, test_user):
        """List tokens returns empty list when user has no tokens."""
        ctx = mock_tenant_context(test_team, test_user)

        def get_test_db():
            yield test_db_session

        with patch.dict('os.environ', {'JWT_SECRET_KEY': 'test-secret-key-at-least-32-chars'}):
            app.dependency_overrides[get_db] = get_test_db
            app.dependency_overrides[get_tenant_context] = lambda: ctx

            with TestClient(app) as client:
                response = client.get("/api/tokens")

            assert response.status_code == 200
            assert response.json() == []

            app.dependency_overrides.clear()

    def test_list_tokens_returns_user_tokens(self, test_db_session, test_team, test_user):
        """List tokens returns only tokens created by the user."""
        ctx = mock_tenant_context(test_team, test_user)

        def get_test_db():
            yield test_db_session

        with patch.dict('os.environ', {'JWT_SECRET_KEY': 'test-secret-key-at-least-32-chars'}):
            app.dependency_overrides[get_db] = get_test_db
            app.dependency_overrides[get_tenant_context] = lambda: ctx

            with TestClient(app) as client:
                # First create a token
                create_response = client.post(
                    "/api/tokens",
                    json={"name": "Test Token"}
                )
                assert create_response.status_code == 201

                # Then list tokens
                response = client.get("/api/tokens")

            assert response.status_code == 200
            tokens = response.json()
            assert len(tokens) == 1
            assert tokens[0]["name"] == "Test Token"
            # Token value should NOT be in list response
            assert "token" not in tokens[0]

            app.dependency_overrides.clear()


class TestTokenApiGet:
    """Tests for GET /api/tokens/{guid} (T126)."""

    def test_get_token_success(self, test_db_session, test_team, test_user):
        """Get token details by GUID."""
        ctx = mock_tenant_context(test_team, test_user)

        def get_test_db():
            yield test_db_session

        with patch.dict('os.environ', {'JWT_SECRET_KEY': 'test-secret-key-at-least-32-chars'}):
            app.dependency_overrides[get_db] = get_test_db
            app.dependency_overrides[get_tenant_context] = lambda: ctx

            with TestClient(app) as client:
                # Create a token first
                create_response = client.post(
                    "/api/tokens",
                    json={"name": "Test Token"}
                )
                created = create_response.json()
                guid = created["guid"]

                # Get the token
                response = client.get(f"/api/tokens/{guid}")

            assert response.status_code == 200
            data = response.json()
            assert data["guid"] == guid
            assert data["name"] == "Test Token"
            # Token value should NOT be returned
            assert "token" not in data

            app.dependency_overrides.clear()

    def test_get_token_not_found(self, test_db_session, test_team, test_user):
        """Get nonexistent token returns 404."""
        ctx = mock_tenant_context(test_team, test_user)

        def get_test_db():
            yield test_db_session

        with patch.dict('os.environ', {'JWT_SECRET_KEY': 'test-secret-key-at-least-32-chars'}):
            app.dependency_overrides[get_db] = get_test_db
            app.dependency_overrides[get_tenant_context] = lambda: ctx

            with TestClient(app) as client:
                response = client.get("/api/tokens/tok_00000000000000000000000001")

            assert response.status_code == 404

            app.dependency_overrides.clear()


class TestTokenApiRevoke:
    """Tests for DELETE /api/tokens/{guid} (T127)."""

    def test_revoke_token_success(self, test_db_session, test_team, test_user):
        """Revoke a token successfully."""
        ctx = mock_tenant_context(test_team, test_user)

        def get_test_db():
            yield test_db_session

        with patch.dict('os.environ', {'JWT_SECRET_KEY': 'test-secret-key-at-least-32-chars'}):
            app.dependency_overrides[get_db] = get_test_db
            app.dependency_overrides[get_tenant_context] = lambda: ctx

            with TestClient(app) as client:
                # Create a token first
                create_response = client.post(
                    "/api/tokens",
                    json={"name": "Test Token"}
                )
                guid = create_response.json()["guid"]

                # Revoke the token
                response = client.delete(f"/api/tokens/{guid}")

            assert response.status_code == 204

            # Verify token is revoked by trying to get it
            with TestClient(app) as client:
                get_response = client.get(f"/api/tokens/{guid}")
                # Should still be visible but inactive
                assert get_response.status_code == 200
                assert get_response.json()["is_active"] is False

            app.dependency_overrides.clear()

    def test_revoke_token_not_found(self, test_db_session, test_team, test_user):
        """Revoke nonexistent token returns 404."""
        ctx = mock_tenant_context(test_team, test_user)

        def get_test_db():
            yield test_db_session

        with patch.dict('os.environ', {'JWT_SECRET_KEY': 'test-secret-key-at-least-32-chars'}):
            app.dependency_overrides[get_db] = get_test_db
            app.dependency_overrides[get_tenant_context] = lambda: ctx

            with TestClient(app) as client:
                response = client.delete("/api/tokens/tok_00000000000000000000000001")

            assert response.status_code == 404

            app.dependency_overrides.clear()
