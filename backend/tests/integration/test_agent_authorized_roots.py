"""
Integration tests for Agent Authorized Roots.

Tests end-to-end flows for agent authorized roots:
- Registration with authorized roots
- Heartbeat updates for authorized roots
- Roots returned in agent responses

Issue #90 - Distributed Agent Architecture (Phase 6b)
"""

import pytest
from backend.src.services.agent_service import AgentService


class TestAgentAuthorizedRoots:
    """Integration tests for agent authorized roots feature."""

    def _create_registration_token(self, service, test_team, test_user, db_session):
        """Helper to create a registration token."""
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        db_session.commit()
        return token_result

    def test_register_agent_with_authorized_roots(
        self, test_db_session, test_team, test_user, test_client
    ):
        """Test agent registration includes authorized_roots."""
        service = AgentService(test_db_session)
        token_result = self._create_registration_token(
            service, test_team, test_user, test_db_session
        )

        authorized_roots = ["/photos", "/backup", "/external"]

        response = test_client.post(
            "/api/agent/v1/register",
            json={
                "registration_token": token_result.plaintext_token,
                "name": "Test Agent with Roots",
                "hostname": "test-host.local",
                "os_info": "macOS 14.0",
                "capabilities": ["local_filesystem"],
                "authorized_roots": authorized_roots,
                "version": "1.0.0",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["guid"].startswith("agt_")
        assert data["authorized_roots"] == authorized_roots

    def test_register_agent_without_authorized_roots(
        self, test_db_session, test_team, test_user, test_client
    ):
        """Test agent registration with empty authorized_roots."""
        service = AgentService(test_db_session)
        token_result = self._create_registration_token(
            service, test_team, test_user, test_db_session
        )

        response = test_client.post(
            "/api/agent/v1/register",
            json={
                "registration_token": token_result.plaintext_token,
                "name": "Test Agent No Roots",
                "hostname": "test-host.local",
                "os_info": "macOS 14.0",
                "capabilities": ["local_filesystem"],
                "authorized_roots": [],
                "version": "1.0.0",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["authorized_roots"] == []

    def test_authorized_roots_stored_in_database(
        self, test_db_session, test_team, test_user, test_client
    ):
        """Test that authorized_roots are persisted in database."""
        service = AgentService(test_db_session)
        token_result = self._create_registration_token(
            service, test_team, test_user, test_db_session
        )

        authorized_roots = ["/photos/vacation", "/photos/work"]

        response = test_client.post(
            "/api/agent/v1/register",
            json={
                "registration_token": token_result.plaintext_token,
                "name": "Persistence Test Agent",
                "hostname": "test-host.local",
                "os_info": "macOS 14.0",
                "capabilities": ["local_filesystem"],
                "authorized_roots": authorized_roots,
                "version": "1.0.0",
            },
        )

        assert response.status_code == 201

        # Verify via service
        agent_guid = response.json()["guid"]
        agent = service.get_agent_by_guid(agent_guid, team_id=test_team.id)
        assert agent is not None
        assert agent.authorized_roots == authorized_roots

    def test_heartbeat_updates_authorized_roots(
        self, test_db_session, test_team, test_user, test_client
    ):
        """Test heartbeat can update authorized_roots."""
        service = AgentService(test_db_session)
        token_result = self._create_registration_token(
            service, test_team, test_user, test_db_session
        )

        # Register with initial roots
        initial_roots = ["/photos"]
        reg_response = test_client.post(
            "/api/agent/v1/register",
            json={
                "registration_token": token_result.plaintext_token,
                "name": "Heartbeat Test Agent",
                "hostname": "test-host.local",
                "os_info": "macOS 14.0",
                "capabilities": ["local_filesystem"],
                "authorized_roots": initial_roots,
                "version": "1.0.0",
            },
        )
        assert reg_response.status_code == 201
        api_key = reg_response.json()["api_key"]
        agent_guid = reg_response.json()["guid"]

        # Update roots via heartbeat
        updated_roots = ["/photos", "/backup", "/external/drives"]
        hb_response = test_client.post(
            "/api/agent/v1/heartbeat",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "status": "online",
                "authorized_roots": updated_roots,
            },
        )

        assert hb_response.status_code == 200

        # Verify roots were updated
        test_db_session.expire_all()
        agent = service.get_agent_by_guid(agent_guid, team_id=test_team.id)
        assert agent is not None
        assert agent.authorized_roots == updated_roots

    def test_heartbeat_without_roots_preserves_existing(
        self, test_db_session, test_team, test_user, test_client
    ):
        """Test heartbeat without authorized_roots preserves existing roots."""
        service = AgentService(test_db_session)
        token_result = self._create_registration_token(
            service, test_team, test_user, test_db_session
        )

        # Register with roots
        initial_roots = ["/photos", "/backup"]
        reg_response = test_client.post(
            "/api/agent/v1/register",
            json={
                "registration_token": token_result.plaintext_token,
                "name": "Preserve Roots Agent",
                "hostname": "test-host.local",
                "os_info": "macOS 14.0",
                "capabilities": ["local_filesystem"],
                "authorized_roots": initial_roots,
                "version": "1.0.0",
            },
        )
        assert reg_response.status_code == 201
        api_key = reg_response.json()["api_key"]
        agent_guid = reg_response.json()["guid"]

        # Heartbeat without roots
        hb_response = test_client.post(
            "/api/agent/v1/heartbeat",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"status": "online"},
        )

        assert hb_response.status_code == 200

        # Verify roots were preserved
        test_db_session.expire_all()
        agent = service.get_agent_by_guid(agent_guid, team_id=test_team.id)
        assert agent is not None
        assert agent.authorized_roots == initial_roots

    def test_is_path_authorized_via_agent_model(
        self, test_db_session, test_team, test_user, test_client
    ):
        """Test is_path_authorized method on Agent model."""
        service = AgentService(test_db_session)
        token_result = self._create_registration_token(
            service, test_team, test_user, test_db_session
        )

        authorized_roots = ["/photos", "/backup"]
        reg_response = test_client.post(
            "/api/agent/v1/register",
            json={
                "registration_token": token_result.plaintext_token,
                "name": "Path Auth Test Agent",
                "hostname": "test-host.local",
                "os_info": "macOS 14.0",
                "capabilities": ["local_filesystem"],
                "authorized_roots": authorized_roots,
                "version": "1.0.0",
            },
        )
        assert reg_response.status_code == 201
        agent_guid = reg_response.json()["guid"]

        agent = service.get_agent_by_guid(agent_guid, team_id=test_team.id)
        assert agent is not None

        # Test authorized paths
        assert agent.is_path_authorized("/photos") is True
        assert agent.is_path_authorized("/photos/vacation") is True
        assert agent.is_path_authorized("/backup") is True
        assert agent.is_path_authorized("/backup/archives/2024") is True

        # Test unauthorized paths
        assert agent.is_path_authorized("/documents") is False
        assert agent.is_path_authorized("/photos2") is False


class TestAgentAdminWithRoots:
    """Integration tests for agent admin endpoints returning roots."""

    def _register_agent_with_roots(
        self, service, test_team, test_user, db_session, roots, name="Test Agent"
    ):
        """Helper to register an agent with authorized roots."""
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name=name,
            hostname="test-host.local",
            os_info="macOS 14.0",
            capabilities=["local_filesystem"],
            authorized_roots=roots,
            version="1.0.0",
        )
        db_session.commit()
        return reg_result

    def test_list_agents_includes_authorized_roots(
        self, test_db_session, test_team, test_user, test_client
    ):
        """Test GET /api/admin/agents returns authorized_roots."""
        service = AgentService(test_db_session)

        # Register agents with different roots
        self._register_agent_with_roots(
            service,
            test_team,
            test_user,
            test_db_session,
            ["/photos"],
            name="Agent 1",
        )
        self._register_agent_with_roots(
            service,
            test_team,
            test_user,
            test_db_session,
            ["/backup", "/external"],
            name="Agent 2",
        )

        response = test_client.get("/api/agent/v1")
        assert response.status_code == 200

        data = response.json()
        agents = data["agents"]
        assert len(agents) >= 2

        # Find our agents and verify roots
        agent1 = next((a for a in agents if a["name"] == "Agent 1"), None)
        agent2 = next((a for a in agents if a["name"] == "Agent 2"), None)

        assert agent1 is not None
        assert agent1["authorized_roots"] == ["/photos"]

        assert agent2 is not None
        assert set(agent2["authorized_roots"]) == {"/backup", "/external"}

    def test_get_agent_includes_authorized_roots(
        self, test_db_session, test_team, test_user, test_client
    ):
        """Test GET /api/admin/agents/{guid} returns authorized_roots."""
        service = AgentService(test_db_session)

        roots = ["/photos/vacation", "/photos/work", "/backup"]
        reg_result = self._register_agent_with_roots(
            service,
            test_team,
            test_user,
            test_db_session,
            roots,
            name="Detail Test Agent",
        )

        response = test_client.get(f"/api/agent/v1/{reg_result.agent.guid}")
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Detail Test Agent"
        assert data["authorized_roots"] == roots
