"""
Integration tests for Agent Admin API.

Tests end-to-end flows for agent administration:
- GET /api/agent/v1 (list agents)
- GET /api/agent/v1/{guid} (get agent details)
- PATCH /api/agent/v1/{guid} (rename agent)
- DELETE /api/agent/v1/{guid} (revoke agent)
- POST /api/agent/v1/tokens (create registration token)
- GET /api/agent/v1/tokens (list tokens)
- DELETE /api/agent/v1/tokens/{guid} (revoke token)
- GET /api/agent/v1/pool-status (get pool status)

Issue #90 - Distributed Agent Architecture (Phase 3)
"""

from datetime import datetime
from fastapi.testclient import TestClient

from backend.src.main import app
from backend.src.services.agent_service import AgentService
from backend.src.models.agent import AgentStatus


class TestAgentListEndpoint:
    """Integration tests for GET /api/agent/v1 endpoint."""

    def test_list_agents_empty(self, test_client):
        """Test listing agents when none exist."""
        response = test_client.get("/api/agent/v1")

        assert response.status_code == 200
        data = response.json()
        assert data["agents"] == []
        assert data["total_count"] == 0

    def test_list_agents_with_agents(self, test_db_session, test_team, test_user, test_client):
        """Test listing agents when some exist."""
        service = AgentService(test_db_session)

        # Register two agents
        for i in range(2):
            token_result = service.create_registration_token(
                team_id=test_team.id,
                created_by_user_id=test_user.id,
            )
            test_db_session.commit()

            service.register_agent(
                plaintext_token=token_result.plaintext_token,
                name=f"Test Agent {i+1}",
                hostname=f"host{i+1}.local",
                os_info="macOS 14.0",
                capabilities=["local_filesystem"],
                version="1.0.0"
            )
            test_db_session.commit()

        response = test_client.get("/api/agent/v1")

        assert response.status_code == 200
        data = response.json()
        assert len(data["agents"]) == 2
        assert data["total_count"] == 2
        # Check both agents are returned (order may vary)
        names = [a["name"] for a in data["agents"]]
        assert "Test Agent 1" in names
        assert "Test Agent 2" in names

    def test_list_agents_filters_by_status(self, test_db_session, test_team, test_user, test_client):
        """Test filtering agents by status."""
        service = AgentService(test_db_session)

        # Register an agent
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
            hostname="host.local",
            os_info="macOS 14.0",
            capabilities=["local_filesystem"],
            version="1.0.0"
        )
        test_db_session.commit()

        # Filter by online status (agent should be online after registration)
        response = test_client.get("/api/agent/v1?status=online")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1

    def test_list_agents_requires_auth(self):
        """Test that listing agents requires authentication."""
        with TestClient(app) as client:
            response = client.get("/api/agent/v1")

        assert response.status_code == 401


class TestAgentGetEndpoint:
    """Integration tests for GET /api/agent/v1/{guid} endpoint."""

    def test_get_agent_success(self, test_db_session, test_team, test_user, test_client):
        """Test getting agent details."""
        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
            hostname="host.local",
            os_info="macOS 14.0",
            capabilities=["local_filesystem", "tool:photostats:1.0.0"],
            version="1.0.0"
        )
        test_db_session.commit()

        response = test_client.get(f"/api/agent/v1/{reg_result.agent.guid}")

        assert response.status_code == 200
        data = response.json()
        assert data["guid"] == reg_result.agent.guid
        assert data["name"] == "Test Agent"
        assert data["hostname"] == "host.local"
        assert "local_filesystem" in data["capabilities"]

    def test_get_agent_not_found(self, test_client):
        """Test getting non-existent agent."""
        response = test_client.get("/api/agent/v1/agt_nonexistent12345678901")

        assert response.status_code == 404

    def test_get_agent_wrong_team(self, test_db_session, test_team, test_user, other_team_client):
        """Test that agents are team-scoped."""
        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
            hostname="host.local",
            os_info="macOS 14.0",
            capabilities=[],
            version="1.0.0"
        )
        test_db_session.commit()

        # Try to access from different team (should return 404)
        response = other_team_client.get(f"/api/agent/v1/{reg_result.agent.guid}")

        assert response.status_code == 404


class TestAgentRenameEndpoint:
    """Integration tests for PATCH /api/agent/v1/{guid} endpoint."""

    def test_rename_agent_success(self, test_db_session, test_team, test_user, test_client):
        """Test renaming an agent."""
        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Original Name",
            hostname="host.local",
            os_info="macOS 14.0",
            capabilities=[],
            version="1.0.0"
        )
        test_db_session.commit()

        response = test_client.patch(
            f"/api/agent/v1/{reg_result.agent.guid}",
            json={"name": "New Name"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Name"

        # Verify in database
        test_db_session.refresh(reg_result.agent)
        assert reg_result.agent.name == "New Name"

    def test_rename_agent_not_found(self, test_client):
        """Test renaming non-existent agent."""
        response = test_client.patch(
            "/api/agent/v1/agt_nonexistent12345678901",
            json={"name": "New Name"}
        )

        assert response.status_code == 404


class TestAgentRevokeEndpoint:
    """Integration tests for DELETE /api/agent/v1/{guid} endpoint."""

    def test_revoke_agent_success(self, test_db_session, test_team, test_user, test_client):
        """Test revoking an agent."""
        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
            hostname="host.local",
            os_info="macOS 14.0",
            capabilities=[],
            version="1.0.0"
        )
        test_db_session.commit()

        response = test_client.delete(
            f"/api/agent/v1/{reg_result.agent.guid}",
            params={"reason": "Testing revocation"}
        )

        assert response.status_code == 204

        # Verify in database
        test_db_session.refresh(reg_result.agent)
        assert reg_result.agent.status == AgentStatus.REVOKED
        assert reg_result.agent.revocation_reason == "Testing revocation"

    def test_revoke_agent_not_found(self, test_client):
        """Test revoking non-existent agent."""
        response = test_client.delete(
            "/api/agent/v1/agt_nonexistent12345678901"
        )

        assert response.status_code == 404


class TestTokenCreateEndpoint:
    """Integration tests for POST /api/agent/v1/tokens endpoint."""

    def test_create_token_success(self, test_client):
        """Test creating a registration token."""
        response = test_client.post(
            "/api/agent/v1/tokens",
            json={"name": "My Dev Machine"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["token"].startswith("art_")
        assert data["name"] == "My Dev Machine"
        assert "expires_at" in data

    def test_create_token_with_custom_expiration(self, test_client):
        """Test creating a token with custom expiration."""
        response = test_client.post(
            "/api/agent/v1/tokens",
            json={"name": "Short-lived Token", "expires_in_hours": 2}
        )

        assert response.status_code == 201
        data = response.json()
        # Verify expiration is roughly 2 hours from now
        # Parse expires_at and strip timezone info for comparison with utcnow()
        expires_at_str = data["expires_at"].replace("Z", "")
        if "+" in expires_at_str:
            expires_at_str = expires_at_str.split("+")[0]
        expires_at = datetime.fromisoformat(expires_at_str)
        now = datetime.utcnow()
        diff = expires_at - now
        assert 1.9 * 3600 < diff.total_seconds() < 2.1 * 3600

    def test_create_token_requires_auth(self):
        """Test that creating tokens requires authentication."""
        with TestClient(app) as client:
            response = client.post(
                "/api/agent/v1/tokens",
                json={"name": "Test Token"}
            )

        assert response.status_code == 401


class TestTokenListEndpoint:
    """Integration tests for GET /api/agent/v1/tokens endpoint."""

    def test_list_tokens_empty(self, test_client):
        """Test listing tokens when none exist."""
        response = test_client.get("/api/agent/v1/tokens")

        assert response.status_code == 200
        data = response.json()
        assert data["tokens"] == []
        assert data["total_count"] == 0

    def test_list_tokens_with_tokens(self, test_db_session, test_team, test_user, test_client):
        """Test listing tokens when some exist."""
        service = AgentService(test_db_session)

        # Create two tokens
        for i in range(2):
            service.create_registration_token(
                team_id=test_team.id,
                created_by_user_id=test_user.id,
                name=f"Token {i+1}"
            )
            test_db_session.commit()

        response = test_client.get("/api/agent/v1/tokens")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tokens"]) == 2
        assert data["total_count"] == 2


class TestTokenDeleteEndpoint:
    """Integration tests for DELETE /api/agent/v1/tokens/{guid} endpoint."""

    def test_delete_token_success(self, test_db_session, test_team, test_user, test_client):
        """Test deleting a registration token."""
        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
            name="Test Token"
        )
        test_db_session.commit()

        response = test_client.delete(
            f"/api/agent/v1/tokens/{token_result.token.guid}"
        )

        assert response.status_code == 204

    def test_delete_token_not_found(self, test_client):
        """Test deleting non-existent token."""
        response = test_client.delete(
            "/api/agent/v1/tokens/art_nonexistent12345678901"
        )

        assert response.status_code == 404


class TestPoolStatusEndpoint:
    """Integration tests for GET /api/agent/v1/pool-status endpoint."""

    def test_pool_status_empty(self, test_client):
        """Test pool status when no agents exist."""
        response = test_client.get("/api/agent/v1/pool-status")

        assert response.status_code == 200
        data = response.json()
        assert data["online_count"] == 0
        assert data["offline_count"] == 0
        assert data["idle_count"] == 0
        assert data["status"] == "offline"

    def test_pool_status_with_agents(self, test_db_session, test_team, test_user, test_client):
        """Test pool status with agents."""
        service = AgentService(test_db_session)

        # Register an agent
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
            hostname="host.local",
            os_info="macOS 14.0",
            capabilities=["local_filesystem"],
            version="1.0.0"
        )
        test_db_session.commit()

        # Send heartbeat to bring agent online (agents start OFFLINE)
        service.process_heartbeat(reg_result.agent, status=AgentStatus.ONLINE)
        test_db_session.commit()

        response = test_client.get("/api/agent/v1/pool-status")

        assert response.status_code == 200
        data = response.json()
        assert data["online_count"] == 1
        assert data["offline_count"] == 0
        assert data["idle_count"] == 1
        assert data["status"] in ["idle", "running"]

    def test_pool_status_requires_auth(self):
        """Test that pool status requires authentication."""
        with TestClient(app) as client:
            response = client.get("/api/agent/v1/pool-status")

        assert response.status_code == 401
