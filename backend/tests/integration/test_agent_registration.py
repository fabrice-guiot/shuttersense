"""
Integration tests for Agent Registration API.

Tests end-to-end flows for agent registration:
- POST /api/agent/v1/register (success, invalid token, expired token)

Issue #90 - Distributed Agent Architecture (Phase 3)
"""

import pytest
from datetime import datetime, timedelta

from backend.src.services.agent_service import AgentService
from backend.src.models.agent import AgentStatus


class TestAgentRegistration:
    """Integration tests for agent registration endpoint."""

    def test_register_agent_success(self, test_db_session, test_team, test_user, test_client):
        """Test successful agent registration with valid token."""
        # Create a registration token
        service = AgentService(test_db_session)
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
            name="Test Registration"
        )
        test_db_session.commit()

        response = test_client.post(
            "/api/agent/v1/register",
            json={
                "registration_token": token_result.plaintext_token,
                "name": "Test Agent",
                "hostname": "test-host.local",
                "os_info": "macOS 14.0",
                "capabilities": ["local_filesystem", "tool:photostats:1.0.0"],
                "version": "1.0.0"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["guid"].startswith("agt_")
        assert data["api_key"].startswith("agt_key_")
        assert data["name"] == "Test Agent"
        assert data["team_guid"] == test_team.guid

    def test_register_agent_invalid_token(self, test_client):
        """Test registration with invalid token."""
        response = test_client.post(
            "/api/agent/v1/register",
            json={
                "registration_token": "art_invalid_token_12345",
                "name": "Test Agent",
                "hostname": "test-host.local",
                "os_info": "macOS 14.0",
                "capabilities": [],
                "version": "1.0.0"
            }
        )

        assert response.status_code == 400
        assert "Invalid" in response.json()["detail"]

    def test_register_agent_expired_token(self, test_db_session, test_team, test_user, test_client):
        """Test registration with expired token."""
        # Create an expired token
        service = AgentService(test_db_session)
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
            expiration_hours=1
        )

        # Manually expire the token
        token_result.token.expires_at = datetime.utcnow() - timedelta(hours=1)
        test_db_session.commit()

        response = test_client.post(
            "/api/agent/v1/register",
            json={
                "registration_token": token_result.plaintext_token,
                "name": "Test Agent",
                "hostname": "test-host.local",
                "os_info": "macOS 14.0",
                "capabilities": [],
                "version": "1.0.0"
            }
        )

        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    def test_register_agent_used_token(self, test_db_session, test_team, test_user, test_client):
        """Test registration with already-used token."""
        # Create a token
        service = AgentService(test_db_session)
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        # First registration should succeed
        response1 = test_client.post(
            "/api/agent/v1/register",
            json={
                "registration_token": token_result.plaintext_token,
                "name": "Agent 1",
                "hostname": "host1.local",
                "os_info": "macOS 14.0",
                "capabilities": [],
                "version": "1.0.0"
            }
        )
        assert response1.status_code == 201

        # Second registration with same token should fail
        response2 = test_client.post(
            "/api/agent/v1/register",
            json={
                "registration_token": token_result.plaintext_token,
                "name": "Agent 2",
                "hostname": "host2.local",
                "os_info": "macOS 14.0",
                "capabilities": [],
                "version": "1.0.0"
            }
        )
        assert response2.status_code == 400
        assert "used" in response2.json()["detail"].lower()

    def test_register_agent_missing_required_fields(self, test_db_session, test_team, test_user, test_client):
        """Test registration with missing required fields."""
        service = AgentService(test_db_session)
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        # Missing name
        response = test_client.post(
            "/api/agent/v1/register",
            json={
                "registration_token": token_result.plaintext_token,
                "hostname": "test-host.local",
                "os_info": "macOS 14.0",
                "version": "1.0.0"
            }
        )
        assert response.status_code == 422  # Pydantic validation error
