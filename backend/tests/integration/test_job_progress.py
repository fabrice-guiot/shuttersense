"""
Integration tests for POST /api/agent/v1/jobs/{guid}/progress endpoint.

Tests job progress updates via the agent API including:
- Successful progress update
- Status transition from ASSIGNED to RUNNING
- Progress data storage
- Error handling

Issue #90 - Distributed Agent Architecture (Phase 5)
Task: T074
"""

import pytest
import secrets
import hashlib
import json
from base64 import b64encode
from datetime import datetime

from backend.src.models.job import Job, JobStatus
from backend.src.models.agent import AgentStatus


class TestJobProgressEndpoint:
    """Integration tests for POST /api/agent/v1/jobs/{guid}/progress."""

    def test_update_progress_success(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_assigned_job,
    ):
        """Successfully update job progress."""
        job = create_assigned_job(test_team, test_agent)

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/progress",
            json={
                "stage": "scanning",
                "percentage": 50,
                "files_scanned": 500,
                "total_files": 1000,
                "message": "Scanning files...",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["guid"] == job.guid
        assert data["status"] == "running"  # Should transition to RUNNING

        # Verify progress stored in DB
        test_db_session.refresh(job)
        assert job.progress is not None
        assert job.progress["stage"] == "scanning"
        assert job.progress["percentage"] == 50
        assert job.progress["files_scanned"] == 500

    def test_progress_transitions_assigned_to_running(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_assigned_job,
    ):
        """First progress update transitions job from ASSIGNED to RUNNING."""
        job = create_assigned_job(test_team, test_agent)

        # Verify initial status
        assert job.status == JobStatus.ASSIGNED

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/progress",
            json={
                "stage": "starting",
                "percentage": 0,
            }
        )

        assert response.status_code == 200

        # Verify status transitioned
        test_db_session.refresh(job)
        assert job.status == JobStatus.RUNNING
        assert job.started_at is not None

    def test_progress_update_running_job(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_running_job,
    ):
        """Progress updates work on already RUNNING jobs."""
        job, _ = create_running_job(test_team, test_agent)

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/progress",
            json={
                "stage": "processing",
                "percentage": 75,
                "files_scanned": 750,
                "total_files": 1000,
            }
        )

        assert response.status_code == 200

        test_db_session.refresh(job)
        assert job.progress["percentage"] == 75
        assert job.status == JobStatus.RUNNING

    def test_progress_minimal_data(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_assigned_job,
    ):
        """Progress update with minimal required data."""
        job = create_assigned_job(test_team, test_agent)

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/progress",
            json={
                "stage": "initializing",
            }
        )

        assert response.status_code == 200

        test_db_session.refresh(job)
        assert job.progress["stage"] == "initializing"

    def test_progress_job_not_found(
        self,
        agent_client,
        test_db_session,
        test_team,
    ):
        """Returns 404 for non-existent job."""
        # agent_client fixture creates the agent

        response = agent_client.post(
            "/api/agent/v1/jobs/job_nonexistent123456789012345/progress",
            json={
                "stage": "scanning",
            }
        )

        assert response.status_code == 404

    def test_progress_wrong_agent(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_user,
        test_agent,
        create_agent,
        create_assigned_job,
    ):
        """Cannot update progress for job assigned to different agent."""
        # agent_client is authenticated as test_agent
        other_agent = create_agent(test_team, test_user, name="Other Agent")

        # Job assigned to other_agent (not test_agent)
        job = create_assigned_job(test_team, other_agent)

        # agent_client is authenticated as agent1
        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/progress",
            json={
                "stage": "scanning",
            }
        )

        assert response.status_code == 400
        assert "not assigned" in response.json()["detail"].lower()

    def test_progress_updates_overwrite(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_assigned_job,
    ):
        """Multiple progress updates overwrite previous progress."""
        job = create_assigned_job(test_team, test_agent)

        # First update
        agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/progress",
            json={
                "stage": "scanning",
                "percentage": 25,
            }
        )

        # Second update
        agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/progress",
            json={
                "stage": "processing",
                "percentage": 50,
            }
        )

        test_db_session.refresh(job)
        assert job.progress["stage"] == "processing"
        assert job.progress["percentage"] == 50


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
def create_running_job(test_db_session):
    """Factory fixture to create a running job with signing secret."""
    def _create_running_job(team, agent, tool="photostats"):
        secret_bytes = secrets.token_bytes(32)
        signing_secret = b64encode(secret_bytes).decode('utf-8')
        secret_hash = hashlib.sha256(secret_bytes).hexdigest()

        job = Job(
            team_id=team.id,
            tool=tool,
            mode="collection",
            status=JobStatus.RUNNING,
            agent_id=agent.id,
            assigned_at=datetime.utcnow(),
            started_at=datetime.utcnow(),
            signing_secret_hash=secret_hash,
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        return job, signing_secret

    return _create_running_job


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
