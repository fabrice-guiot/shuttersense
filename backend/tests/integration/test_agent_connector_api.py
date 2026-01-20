"""
Integration tests for Agent Connector API endpoints.

Tests end-to-end flows for agent connector operations:
- GET /api/agent/v1/connectors (list connectors for credential configuration)
- GET /api/agent/v1/connectors/{guid}/metadata (get connector metadata)
- POST /api/agent/v1/connectors/{guid}/report-capability (report credential capability)

Issue #90 - Distributed Agent Architecture (Phase 8)
Task: T131
"""

import json
import pytest

from backend.src.services.agent_service import AgentService
from backend.src.models.agent import Agent, AgentStatus
from backend.src.models.connector import Connector, ConnectorType, CredentialLocation


class TestAgentConnectorListEndpoint:
    """Integration tests for GET /api/agent/v1/connectors."""

    def _create_connector(
        self,
        db_session,
        test_encryptor,
        team,
        name,
        connector_type=ConnectorType.S3,
        credential_location=CredentialLocation.SERVER,
        credentials=None,
    ):
        """Helper to create a connector with specific credential_location."""
        if credentials is None and credential_location == CredentialLocation.SERVER:
            credentials = {
                "aws_access_key_id": "AKIATEST",
                "aws_secret_access_key": "secretkey"
            }

        encrypted_creds = None
        if credentials:
            creds_json = json.dumps(credentials)
            encrypted_creds = test_encryptor.encrypt(creds_json)

        connector = Connector(
            name=name,
            type=connector_type,
            credential_location=credential_location,
            credentials=encrypted_creds,
            is_active=True,
            team_id=team.id,
        )
        db_session.add(connector)
        db_session.commit()
        db_session.refresh(connector)
        return connector

    def test_list_connectors_filters_server_credentials(
        self, test_db_session, test_team, test_encryptor, agent_client
    ):
        """Server-side credential connectors are filtered out."""
        # Create connectors with different credential locations
        server_conn = self._create_connector(
            test_db_session, test_encryptor, test_team,
            name="Server Connector",
            credential_location=CredentialLocation.SERVER
        )
        pending_conn = self._create_connector(
            test_db_session, test_encryptor, test_team,
            name="Pending Connector",
            credential_location=CredentialLocation.PENDING,
            credentials=None
        )
        agent_conn = self._create_connector(
            test_db_session, test_encryptor, test_team,
            name="Agent Connector",
            credential_location=CredentialLocation.AGENT,
            credentials=None
        )

        response = agent_client.get("/api/agent/v1/connectors")

        assert response.status_code == 200
        data = response.json()

        # Should include PENDING and AGENT, but not SERVER
        guids = [c["guid"] for c in data["connectors"]]
        assert server_conn.guid not in guids
        assert pending_conn.guid in guids
        assert agent_conn.guid in guids
        assert data["total"] == 2

    def test_list_connectors_pending_only_filter(
        self, test_db_session, test_team, test_encryptor, agent_client
    ):
        """pending_only=true returns only PENDING connectors."""
        pending_conn = self._create_connector(
            test_db_session, test_encryptor, test_team,
            name="Pending Connector",
            credential_location=CredentialLocation.PENDING,
            credentials=None
        )
        agent_conn = self._create_connector(
            test_db_session, test_encryptor, test_team,
            name="Agent Connector",
            credential_location=CredentialLocation.AGENT,
            credentials=None
        )

        response = agent_client.get("/api/agent/v1/connectors?pending_only=true")

        assert response.status_code == 200
        data = response.json()

        guids = [c["guid"] for c in data["connectors"]]
        assert pending_conn.guid in guids
        assert agent_conn.guid not in guids
        assert data["total"] == 1

    def test_list_connectors_shows_has_local_credentials(
        self, test_db_session, test_team, test_encryptor, agent_client_with_capabilities
    ):
        """Response shows has_local_credentials based on agent capabilities."""
        agent_conn = self._create_connector(
            test_db_session, test_encryptor, test_team,
            name="Agent Connector",
            credential_location=CredentialLocation.AGENT,
            credentials=None
        )

        # Use agent_client_with_capabilities that has the connector capability
        client = agent_client_with_capabilities([f"connector:{agent_conn.guid}"])

        response = client.get("/api/agent/v1/connectors")

        assert response.status_code == 200
        data = response.json()

        connector_data = next(c for c in data["connectors"] if c["guid"] == agent_conn.guid)
        assert connector_data["has_local_credentials"] is True

    def test_list_connectors_no_auth(self, test_client):
        """List connectors without authentication returns 401."""
        response = test_client.get("/api/agent/v1/connectors")
        assert response.status_code == 401

    def test_list_connectors_tenant_isolation(
        self, test_db_session, test_team, test_encryptor, agent_client
    ):
        """Connectors from other teams are not visible."""
        from backend.src.models import Team

        # Create connector in another team
        other_team = Team(name="Other Team", slug="other-team", is_active=True)
        test_db_session.add(other_team)
        test_db_session.commit()

        other_connector = self._create_connector(
            test_db_session, test_encryptor, other_team,
            name="Other Team Connector",
            credential_location=CredentialLocation.PENDING,
            credentials=None
        )

        # Create connector in agent's team
        own_connector = self._create_connector(
            test_db_session, test_encryptor, test_team,
            name="Own Connector",
            credential_location=CredentialLocation.PENDING,
            credentials=None
        )

        response = agent_client.get("/api/agent/v1/connectors")

        assert response.status_code == 200
        data = response.json()

        guids = [c["guid"] for c in data["connectors"]]
        assert own_connector.guid in guids
        assert other_connector.guid not in guids


class TestAgentConnectorMetadataEndpoint:
    """Integration tests for GET /api/agent/v1/connectors/{guid}/metadata."""

    def _create_connector(
        self,
        db_session,
        test_encryptor,
        team,
        name,
        connector_type=ConnectorType.S3,
        credential_location=CredentialLocation.PENDING,
    ):
        """Helper to create a connector."""
        connector = Connector(
            name=name,
            type=connector_type,
            credential_location=credential_location,
            credentials=None,
            is_active=True,
            team_id=team.id,
        )
        db_session.add(connector)
        db_session.commit()
        db_session.refresh(connector)
        return connector

    def test_get_metadata_success(
        self, test_db_session, test_team, test_encryptor, agent_client
    ):
        """Get metadata for a PENDING connector."""
        connector = self._create_connector(
            test_db_session, test_encryptor, test_team,
            name="S3 Connector",
            connector_type=ConnectorType.S3,
            credential_location=CredentialLocation.PENDING
        )

        response = agent_client.get(
            f"/api/agent/v1/connectors/{connector.guid}/metadata"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["guid"] == connector.guid
        assert data["name"] == "S3 Connector"
        assert data["type"] == "s3"
        assert data["credential_location"] == "pending"
        assert "credential_fields" in data
        # S3 should have specific fields
        field_names = [f["name"] for f in data["credential_fields"]]
        assert "aws_access_key_id" in field_names
        assert "aws_secret_access_key" in field_names

    def test_get_metadata_gcs_fields(
        self, test_db_session, test_team, test_encryptor, agent_client
    ):
        """Get metadata for GCS connector returns GCS credential fields."""
        connector = self._create_connector(
            test_db_session, test_encryptor, test_team,
            name="GCS Connector",
            connector_type=ConnectorType.GCS,
            credential_location=CredentialLocation.PENDING
        )

        response = agent_client.get(
            f"/api/agent/v1/connectors/{connector.guid}/metadata"
        )

        assert response.status_code == 200
        data = response.json()

        field_names = [f["name"] for f in data["credential_fields"]]
        assert "service_account_json" in field_names

    def test_get_metadata_smb_fields(
        self, test_db_session, test_team, test_encryptor, agent_client
    ):
        """Get metadata for SMB connector returns SMB credential fields."""
        connector = self._create_connector(
            test_db_session, test_encryptor, test_team,
            name="SMB Connector",
            connector_type=ConnectorType.SMB,
            credential_location=CredentialLocation.PENDING
        )

        response = agent_client.get(
            f"/api/agent/v1/connectors/{connector.guid}/metadata"
        )

        assert response.status_code == 200
        data = response.json()

        field_names = [f["name"] for f in data["credential_fields"]]
        assert "username" in field_names
        assert "password" in field_names

    def test_get_metadata_server_connector_rejected(
        self, test_db_session, test_team, test_encryptor, agent_client
    ):
        """Cannot get metadata for server-side credential connector."""
        # Create connector with server credentials
        encrypted_creds = test_encryptor.encrypt(json.dumps({
            "aws_access_key_id": "AKIATEST",
            "aws_secret_access_key": "secret"
        }))

        connector = Connector(
            name="Server Connector",
            type=ConnectorType.S3,
            credential_location=CredentialLocation.SERVER,
            credentials=encrypted_creds,
            is_active=True,
            team_id=test_team.id,
        )
        test_db_session.add(connector)
        test_db_session.commit()
        test_db_session.refresh(connector)

        response = agent_client.get(
            f"/api/agent/v1/connectors/{connector.guid}/metadata"
        )

        assert response.status_code == 400
        assert "server-side" in response.json()["detail"].lower()

    def test_get_metadata_not_found(self, agent_client):
        """Get metadata for non-existent connector returns 404."""
        response = agent_client.get(
            "/api/agent/v1/connectors/con_01hgw2bbg00000000000000000/metadata"
        )

        assert response.status_code == 404


class TestAgentConnectorReportCapabilityEndpoint:
    """Integration tests for POST /api/agent/v1/connectors/{guid}/report-capability."""

    def _create_connector(
        self,
        db_session,
        test_encryptor,
        team,
        name,
        connector_type=ConnectorType.S3,
        credential_location=CredentialLocation.PENDING,
    ):
        """Helper to create a connector."""
        connector = Connector(
            name=name,
            type=connector_type,
            credential_location=credential_location,
            credentials=None,
            is_active=True,
            team_id=team.id,
        )
        db_session.add(connector)
        db_session.commit()
        db_session.refresh(connector)
        return connector

    def test_report_capability_adds_capability(
        self, test_db_session, test_team, test_encryptor, agent_client, test_agent
    ):
        """Reporting capability adds connector:{guid} to agent capabilities."""
        connector = self._create_connector(
            test_db_session, test_encryptor, test_team,
            name="Agent Connector",
            credential_location=CredentialLocation.AGENT
        )

        response = agent_client.post(
            f"/api/agent/v1/connectors/{connector.guid}/report-capability",
            json={"has_credentials": True}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["acknowledged"] is True

        # Verify agent capabilities updated
        test_db_session.refresh(test_agent)
        assert f"connector:{connector.guid}" in test_agent.capabilities

    def test_report_capability_removes_capability(
        self, test_db_session, test_team, test_encryptor, test_agent, agent_client_with_capabilities
    ):
        """Reporting has_credentials=false removes connector capability."""
        connector = self._create_connector(
            test_db_session, test_encryptor, test_team,
            name="Agent Connector",
            credential_location=CredentialLocation.AGENT
        )

        # Use agent client WITH connector capability
        client = agent_client_with_capabilities([f"connector:{connector.guid}"])

        # Verify initial capability
        test_db_session.refresh(test_agent)
        assert f"connector:{connector.guid}" in test_agent.capabilities

        response = client.post(
            f"/api/agent/v1/connectors/{connector.guid}/report-capability",
            json={"has_credentials": False}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["acknowledged"] is True

        # Verify capability removed
        test_db_session.refresh(test_agent)
        assert f"connector:{connector.guid}" not in test_agent.capabilities

    def test_report_capability_flips_pending_to_agent(
        self, test_db_session, test_team, test_encryptor, agent_client
    ):
        """Reporting capability on PENDING connector flips to AGENT."""
        connector = self._create_connector(
            test_db_session, test_encryptor, test_team,
            name="Pending Connector",
            credential_location=CredentialLocation.PENDING
        )

        assert connector.credential_location == CredentialLocation.PENDING

        response = agent_client.post(
            f"/api/agent/v1/connectors/{connector.guid}/report-capability",
            json={"has_credentials": True}
        )

        assert response.status_code == 200

        # Verify connector credential_location flipped
        test_db_session.refresh(connector)
        assert connector.credential_location == CredentialLocation.AGENT

    def test_report_capability_server_connector_rejected(
        self, test_db_session, test_team, test_encryptor, agent_client
    ):
        """Cannot report capability for server-side connector."""
        # Create server-side connector
        encrypted_creds = test_encryptor.encrypt(json.dumps({
            "aws_access_key_id": "AKIATEST",
            "aws_secret_access_key": "secret"
        }))

        connector = Connector(
            name="Server Connector",
            type=ConnectorType.S3,
            credential_location=CredentialLocation.SERVER,
            credentials=encrypted_creds,
            is_active=True,
            team_id=test_team.id,
        )
        test_db_session.add(connector)
        test_db_session.commit()
        test_db_session.refresh(connector)

        response = agent_client.post(
            f"/api/agent/v1/connectors/{connector.guid}/report-capability",
            json={"has_credentials": True}
        )

        assert response.status_code == 400
        assert "server-side" in response.json()["detail"].lower()

    def test_report_capability_not_found(self, agent_client):
        """Report capability for non-existent connector returns 404."""
        response = agent_client.post(
            "/api/agent/v1/connectors/con_01hgw2bbg00000000000000000/report-capability",
            json={"has_credentials": True}
        )

        assert response.status_code == 404

    def test_report_capability_no_auth(self, test_client):
        """Report capability without authentication returns 401."""
        response = test_client.post(
            "/api/agent/v1/connectors/con_01hgw2bbg00000000000000000/report-capability",
            json={"has_credentials": True}
        )
        assert response.status_code == 401


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def create_agent(test_db_session):
    """Factory fixture to create test agents."""
    def _create_agent(team, user, name="Test Agent", capabilities=None):
        from backend.src.services.agent_service import AgentService

        service = AgentService(test_db_session)

        # Create token
        token_result = service.create_registration_token(
            team_id=team.id,
            created_by_user_id=user.id,
        )
        test_db_session.commit()

        # Register agent
        result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name=name,
            hostname="test.local",
            os_info="Linux",
            capabilities=capabilities or ["local_filesystem"],
            version="1.0.0"
        )
        test_db_session.commit()

        # Bring agent online
        service.process_heartbeat(result.agent, status=AgentStatus.ONLINE)
        test_db_session.commit()

        return result.agent

    return _create_agent


@pytest.fixture
def test_agent(test_db_session, test_team, test_user, create_agent):
    """Create a test agent that will be used by agent_client."""
    return create_agent(test_team, test_user)


@pytest.fixture
def agent_client(
    test_db_session,
    test_session_factory,
    test_team,
    test_user,
    test_websocket_manager,
    test_agent,
):
    """Create a test client authenticated as an online agent."""
    from fastapi.testclient import TestClient
    from backend.src.main import app
    from backend.src.api.agent.dependencies import AgentContext

    agent = test_agent

    agent_ctx = AgentContext(
        agent_id=agent.id,
        agent_guid=agent.guid,
        team_id=test_team.id,
        team_guid=test_team.guid,
        agent_name=agent.name,
        status=AgentStatus.ONLINE,
        agent=agent,
    )

    def get_test_db():
        try:
            yield test_db_session
        finally:
            pass

    def get_test_agent_context():
        return agent_ctx

    def get_test_online_agent():
        return agent_ctx

    def get_test_websocket_manager():
        return test_websocket_manager

    from backend.src.db.database import get_db
    from backend.src.api.agent.dependencies import get_agent_context, require_online_agent
    from backend.src.utils.websocket import get_connection_manager

    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_agent_context] = get_test_agent_context
    app.dependency_overrides[require_online_agent] = get_test_online_agent
    app.dependency_overrides[get_connection_manager] = get_test_websocket_manager

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def agent_client_with_capabilities(
    test_db_session,
    test_session_factory,
    test_team,
    test_user,
    test_websocket_manager,
    test_agent,
):
    """Factory to create a test client with specific agent capabilities."""
    from fastapi.testclient import TestClient
    from backend.src.main import app
    from backend.src.api.agent.dependencies import AgentContext

    def _create_client(additional_capabilities):
        agent = test_agent

        # Update agent capabilities
        existing_caps = agent.capabilities or []
        agent.capabilities = list(set(existing_caps + additional_capabilities))
        test_db_session.commit()
        test_db_session.refresh(agent)

        agent_ctx = AgentContext(
            agent_id=agent.id,
            agent_guid=agent.guid,
            team_id=test_team.id,
            team_guid=test_team.guid,
            agent_name=agent.name,
            status=AgentStatus.ONLINE,
            agent=agent,
        )

        def get_test_db():
            try:
                yield test_db_session
            finally:
                pass

        def get_test_agent_context():
            return agent_ctx

        def get_test_online_agent():
            return agent_ctx

        def get_test_websocket_manager():
            return test_websocket_manager

        from backend.src.db.database import get_db
        from backend.src.api.agent.dependencies import get_agent_context, require_online_agent
        from backend.src.utils.websocket import get_connection_manager

        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[get_agent_context] = get_test_agent_context
        app.dependency_overrides[require_online_agent] = get_test_online_agent
        app.dependency_overrides[get_connection_manager] = get_test_websocket_manager

        client = TestClient(app)
        return client

    yield _create_client

    app.dependency_overrides.clear()
