"""
Integration tests for config API endpoints.

Tests job configuration retrieval via the agent API including:
- Successful config retrieval for assigned jobs
- Team-specific configuration loading
- Access control (only assigned agent can get config)
- Collection and pipeline info inclusion

Issue #90 - Distributed Agent Architecture (Phase 5)
Task: T076
"""

import pytest
import json
from datetime import datetime

from backend.src.models.job import Job, JobStatus
from backend.src.models.agent import AgentStatus
from backend.src.models import Configuration


class TestJobConfigEndpoint:
    """Integration tests for GET /api/agent/v1/jobs/{guid}/config."""

    def test_get_job_config_success(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_assigned_job,
    ):
        """Successfully retrieve config for an assigned job."""
        job = create_assigned_job(test_team, test_agent)

        response = agent_client.get(f"/api/agent/v1/jobs/{job.guid}/config")

        assert response.status_code == 200
        data = response.json()
        assert data["job_guid"] == job.guid
        assert "config" in data
        assert "photo_extensions" in data["config"]
        assert "metadata_extensions" in data["config"]
        assert "camera_mappings" in data["config"]
        assert "processing_methods" in data["config"]
        assert "require_sidecar" in data["config"]

    def test_get_job_config_default_extensions(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_assigned_job,
    ):
        """Returns default extensions when not configured."""
        job = create_assigned_job(test_team, test_agent)

        response = agent_client.get(f"/api/agent/v1/jobs/{job.guid}/config")

        assert response.status_code == 200
        data = response.json()

        # Should have default photo extensions
        assert ".dng" in data["config"]["photo_extensions"]
        assert ".jpg" in data["config"]["photo_extensions"]

        # Should have default metadata extensions
        assert ".xmp" in data["config"]["metadata_extensions"]

    def test_get_job_config_with_custom_extensions(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_assigned_job,
    ):
        """Returns custom extensions from database configuration."""
        # Create custom configuration
        config = Configuration(
            team_id=test_team.id,
            category="extensions",
            key="photo_extensions",
            value_json=[".raw", ".arw", ".orf"]
        )
        test_db_session.add(config)
        test_db_session.commit()

        job = create_assigned_job(test_team, test_agent)

        response = agent_client.get(f"/api/agent/v1/jobs/{job.guid}/config")

        assert response.status_code == 200
        data = response.json()

        # Should return custom extensions
        assert data["config"]["photo_extensions"] == [".raw", ".arw", ".orf"]

    def test_get_job_config_with_collection(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        sample_collection,
    ):
        """Config response includes collection path."""
        collection = sample_collection(location="/photos/vacation")

        job = Job(
            team_id=test_team.id,
            tool="photostats",
            mode="collection",
            status=JobStatus.ASSIGNED,
            agent_id=test_agent.id,
            collection_id=collection.id,
            assigned_at=datetime.utcnow(),
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        response = agent_client.get(f"/api/agent/v1/jobs/{job.guid}/config")

        assert response.status_code == 200
        data = response.json()
        assert data["collection_path"] == "/photos/vacation"

    def test_get_job_config_with_pipeline(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        sample_pipeline,
    ):
        """Config response includes pipeline data."""
        pipeline = sample_pipeline()

        job = Job(
            team_id=test_team.id,
            tool="pipeline_validation",
            mode="collection",
            status=JobStatus.ASSIGNED,
            agent_id=test_agent.id,
            pipeline_id=pipeline.id,
            pipeline_version=pipeline.version,
            assigned_at=datetime.utcnow(),
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        response = agent_client.get(f"/api/agent/v1/jobs/{job.guid}/config")

        assert response.status_code == 200
        data = response.json()
        assert data["pipeline_guid"] == pipeline.guid
        assert data["pipeline"] is not None
        assert data["pipeline"]["name"] == pipeline.name
        assert "nodes" in data["pipeline"]
        assert "edges" in data["pipeline"]

    def test_get_job_config_not_found(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
    ):
        """Returns 404 for non-existent job."""
        # test_agent is already created by agent_client fixture

        response = agent_client.get(
            "/api/agent/v1/jobs/job_nonexistent123456789012345/config"
        )

        assert response.status_code == 404

    def test_get_job_config_wrong_agent(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_user,
        test_agent,
        create_agent,
    ):
        """Returns 403 for job assigned to different agent."""
        # agent_client is authenticated as test_agent
        other_agent = create_agent(test_team, test_user, name="Other Agent")

        # Create job assigned to other_agent (not test_agent)
        job = Job(
            team_id=test_team.id,
            tool="photostats",
            mode="collection",
            status=JobStatus.ASSIGNED,
            agent_id=other_agent.id,
            assigned_at=datetime.utcnow(),
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        # agent_client is authenticated as test_agent, should be forbidden
        response = agent_client.get(f"/api/agent/v1/jobs/{job.guid}/config")

        assert response.status_code == 403
        assert "not assigned" in response.json()["detail"].lower()

    def test_get_job_config_invalid_guid(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
    ):
        """Returns 404 for invalid job GUID format."""
        # test_agent is already created by agent_client fixture

        response = agent_client.get("/api/agent/v1/jobs/invalid_guid/config")

        assert response.status_code == 404

    def test_get_job_config_camera_mappings(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_assigned_job,
    ):
        """Config includes camera mappings from database."""
        # Create camera mapping configuration
        config = Configuration(
            team_id=test_team.id,
            category="cameras",
            key="AB3D",
            value_json={"name": "Canon EOS R5", "serial_number": "12345"}
        )
        test_db_session.add(config)
        test_db_session.commit()

        job = create_assigned_job(test_team, test_agent)

        response = agent_client.get(f"/api/agent/v1/jobs/{job.guid}/config")

        assert response.status_code == 200
        data = response.json()
        assert "AB3D" in data["config"]["camera_mappings"]
        assert data["config"]["camera_mappings"]["AB3D"][0]["name"] == "Canon EOS R5"

    def test_get_job_config_processing_methods(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_assigned_job,
    ):
        """Config includes processing methods from database."""
        # Create processing method configuration
        config = Configuration(
            team_id=test_team.id,
            category="processing_methods",
            key="HDR",
            value_json="High Dynamic Range"
        )
        test_db_session.add(config)
        test_db_session.commit()

        job = create_assigned_job(test_team, test_agent)

        response = agent_client.get(f"/api/agent/v1/jobs/{job.guid}/config")

        assert response.status_code == 200
        data = response.json()
        assert "HDR" in data["config"]["processing_methods"]
        assert data["config"]["processing_methods"]["HDR"] == "High Dynamic Range"


class TestConfigTenantIsolation:
    """Tests for config tenant isolation."""

    def test_config_is_team_scoped(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        other_team,
        create_assigned_job,
    ):
        """Config only returns data for the agent's team."""
        # Create config for test_team - use unique keys to avoid constraint violation
        config1 = Configuration(
            team_id=test_team.id,
            category="cameras",
            key="TEAM1",
            value_json={"name": "Team 1 Camera", "serial_number": "111"}
        )
        # Create config for other_team - use different key
        config2 = Configuration(
            team_id=other_team.id,
            category="cameras",
            key="TEAM2",
            value_json={"name": "Team 2 Camera", "serial_number": "222"}
        )
        test_db_session.add_all([config1, config2])
        test_db_session.commit()

        job = create_assigned_job(test_team, test_agent)

        response = agent_client.get(f"/api/agent/v1/jobs/{job.guid}/config")

        assert response.status_code == 200
        data = response.json()

        # Should see test_team's camera mapping
        assert "TEAM1" in data["config"]["camera_mappings"]
        # Should NOT see other_team's camera mapping
        assert "TEAM2" not in data["config"]["camera_mappings"]


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def create_agent(test_db_session):
    """Factory fixture to create and register test agents."""
    def _create_agent(team, user, name="Test Agent", capabilities=None):
        from backend.src.services.agent_service import AgentService

        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=team.id,
            created_by_user_id=user.id,
        )
        test_db_session.commit()

        result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name=name,
            hostname="test.local",
            os_info="Linux",
            capabilities=capabilities or ["local_filesystem"],
            version="1.0.0"
        )
        test_db_session.commit()

        service.process_heartbeat(result.agent, status=AgentStatus.ONLINE)
        test_db_session.commit()

        return result.agent

    return _create_agent


@pytest.fixture
def test_agent(test_db_session, test_team, test_user, create_agent):
    """Create a test agent that will be used by agent_client."""
    return create_agent(test_team, test_user)


@pytest.fixture
def create_assigned_job(test_db_session):
    """Factory fixture to create a job assigned to an agent."""
    def _create_assigned_job(team, agent, tool="photostats"):
        job = Job(
            team_id=team.id,
            tool=tool,
            mode="collection",
            status=JobStatus.ASSIGNED,
            agent_id=agent.id,
            assigned_at=datetime.utcnow(),
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)
        return job

    return _create_assigned_job


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
