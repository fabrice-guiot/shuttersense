"""
Integration tests for Agent Heartbeat API.

Tests end-to-end flows for agent heartbeat:
- POST /api/agent/v1/heartbeat (status update, capability refresh)

Issue #90 - Distributed Agent Architecture (Phase 3)
"""

from datetime import datetime
from fastapi.testclient import TestClient

from backend.src.main import app
from backend.src.services.agent_service import AgentService
from backend.src.models.agent import AgentStatus


class TestAgentHeartbeat:
    """Integration tests for agent heartbeat endpoint."""

    def _register_agent(self, service, test_team, test_user, db_session):
        """Helper to register an agent and return the API key."""
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
            hostname="test-host.local",
            os_info="macOS 14.0",
            capabilities=["local_filesystem"],
            version="1.0.0"
        )
        db_session.commit()
        return reg_result

    def test_heartbeat_success(self, test_db_session, test_team, test_user, test_client):
        """Test successful heartbeat with valid API key."""
        service = AgentService(test_db_session)
        reg_result = self._register_agent(service, test_team, test_user, test_db_session)

        response = test_client.post(
            "/api/agent/v1/heartbeat",
            headers={"Authorization": f"Bearer {reg_result.api_key}"},
            json={
                "status": "online"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["acknowledged"] is True
        assert "server_time" in data

    def test_heartbeat_updates_status(self, test_db_session, test_team, test_user, test_client):
        """Test that heartbeat updates agent status."""
        service = AgentService(test_db_session)
        reg_result = self._register_agent(service, test_team, test_user, test_db_session)

        response = test_client.post(
            "/api/agent/v1/heartbeat",
            headers={"Authorization": f"Bearer {reg_result.api_key}"},
            json={
                "status": "error",
                "error_message": "Test error message"
            }
        )

        assert response.status_code == 200

        # Verify status was updated
        test_db_session.refresh(reg_result.agent)
        assert reg_result.agent.status == AgentStatus.ERROR
        assert reg_result.agent.error_message == "Test error message"

    def test_heartbeat_updates_capabilities(self, test_db_session, test_team, test_user, test_client):
        """Test that heartbeat can update capabilities."""
        service = AgentService(test_db_session)
        reg_result = self._register_agent(service, test_team, test_user, test_db_session)

        new_capabilities = ["local_filesystem", "tool:photostats:1.0.0", "tool:photo_pairing:1.0.0"]

        response = test_client.post(
            "/api/agent/v1/heartbeat",
            headers={"Authorization": f"Bearer {reg_result.api_key}"},
            json={
                "status": "online",
                "capabilities": new_capabilities
            }
        )

        assert response.status_code == 200

        # Verify capabilities were updated
        test_db_session.refresh(reg_result.agent)
        assert set(reg_result.agent.capabilities) == set(new_capabilities)

    def test_heartbeat_no_auth(self, test_client):
        """Test heartbeat without authentication."""
        response = test_client.post(
            "/api/agent/v1/heartbeat",
            json={"status": "online"}
        )

        assert response.status_code == 401

    def test_heartbeat_invalid_api_key(self, test_client):
        """Test heartbeat with invalid API key."""
        response = test_client.post(
            "/api/agent/v1/heartbeat",
            headers={"Authorization": "Bearer agt_key_invalid_key"},
            json={"status": "online"}
        )

        assert response.status_code == 401

    def test_heartbeat_revoked_agent(self, test_db_session, test_team, test_user, test_client):
        """Test heartbeat from revoked agent."""
        service = AgentService(test_db_session)
        reg_result = self._register_agent(service, test_team, test_user, test_db_session)

        # Revoke the agent
        service.revoke_agent(reg_result.agent, "Testing revocation")
        test_db_session.commit()

        response = test_client.post(
            "/api/agent/v1/heartbeat",
            headers={"Authorization": f"Bearer {reg_result.api_key}"},
            json={"status": "online"}
        )

        assert response.status_code == 403
        assert "revoked" in response.json()["detail"].lower()

    def test_heartbeat_with_job_progress(self, test_db_session, test_team, test_user, test_client):
        """Test heartbeat with current job progress."""
        service = AgentService(test_db_session)
        reg_result = self._register_agent(service, test_team, test_user, test_db_session)

        response = test_client.post(
            "/api/agent/v1/heartbeat",
            headers={"Authorization": f"Bearer {reg_result.api_key}"},
            json={
                "status": "online",
                "current_job_guid": "job_test123",
                "current_job_progress": {
                    "stage": "scanning",
                    "percentage": 45,
                    "files_scanned": 1234
                }
            }
        )

        assert response.status_code == 200
