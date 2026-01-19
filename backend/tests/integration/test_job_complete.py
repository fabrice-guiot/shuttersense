"""
Integration tests for POST /api/agent/v1/jobs/{guid}/complete endpoint.

Tests job completion via the agent API including:
- Successful completion with results
- AnalysisResult creation
- HMAC signature verification
- Error handling for wrong agent, wrong status, etc.

Issue #90 - Distributed Agent Architecture (Phase 5)
Task: T073
"""

import pytest
import secrets
import hashlib
import hmac
import json
from base64 import b64encode
from datetime import datetime

from backend.src.models.job import Job, JobStatus
from backend.src.models.agent import AgentStatus
from backend.src.models import AnalysisResult


class TestJobCompleteEndpoint:
    """Integration tests for POST /api/agent/v1/jobs/{guid}/complete."""

    def test_complete_job_success(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_running_job,
    ):
        """Successfully complete a running job."""
        job, signing_secret = create_running_job(test_team, test_agent)

        # Compute valid signature
        results = {"total_files": 1000, "issues_found": 5}
        signature = compute_signature(signing_secret, results)

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/complete",
            json={
                "results": results,
                "report_html": "<html><body>Test Report</body></html>",
                "files_scanned": 1000,
                "issues_found": 5,
                "signature": signature,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["guid"] == job.guid
        assert data["status"] == "completed"

        # Verify job updated in DB
        test_db_session.refresh(job)
        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None
        assert job.result_id is not None

    def test_complete_job_creates_analysis_result(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_running_job,
    ):
        """Completing a job creates an AnalysisResult record."""
        job, signing_secret = create_running_job(test_team, test_agent)

        results = {"total_files": 500, "issues_found": 10}
        signature = compute_signature(signing_secret, results)

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/complete",
            json={
                "results": results,
                "report_html": "<html>Report</html>",
                "files_scanned": 500,
                "issues_found": 10,
                "signature": signature,
            }
        )

        assert response.status_code == 200

        # Verify AnalysisResult was created
        test_db_session.refresh(job)
        result = test_db_session.query(AnalysisResult).filter(
            AnalysisResult.id == job.result_id
        ).first()

        assert result is not None
        assert result.tool == job.tool
        assert result.files_scanned == 500
        assert result.issues_found == 10
        assert result.report_html == "<html>Report</html>"
        assert result.results_json == results

    def test_complete_job_not_found(
        self,
        agent_client,
        test_db_session,
        test_team,
    ):
        """Returns 404 for non-existent job."""
        # agent_client fixture creates the agent

        response = agent_client.post(
            "/api/agent/v1/jobs/job_nonexistent123456789012345/complete",
            json={
                "results": {},
                "report_html": "",
                "files_scanned": 0,
                "issues_found": 0,
                "signature": "a" * 64,
            }
        )

        assert response.status_code == 404

    def test_complete_job_wrong_agent(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_user,
        test_agent,
        create_agent,
        create_running_job,
    ):
        """Cannot complete job assigned to different agent."""
        # agent_client is authenticated as test_agent
        other_agent = create_agent(test_team, test_user, name="Other Agent")

        # Create job assigned to other_agent (not test_agent)
        job, signing_secret = create_running_job(test_team, other_agent)

        results = {"total_files": 100}
        signature = compute_signature(signing_secret, results)

        # agent_client is authenticated as agent1
        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/complete",
            json={
                "results": results,
                "report_html": "",
                "files_scanned": 100,
                "issues_found": 0,
                "signature": signature,
            }
        )

        assert response.status_code == 400
        assert "not assigned" in response.json()["detail"].lower()

    def test_complete_job_wrong_status(
        self,
        agent_client,
        test_db_session,
        test_team,
        create_job,
    ):
        """Cannot complete job that is not RUNNING or ASSIGNED."""
        # agent_client fixture creates the agent

        # Create PENDING job (not claimed yet)
        job = create_job(test_team, status=JobStatus.PENDING)

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/complete",
            json={
                "results": {},
                "report_html": "",
                "files_scanned": 0,
                "issues_found": 0,
                "signature": "a" * 64,
            }
        )

        assert response.status_code == 400


class TestJobFailEndpoint:
    """Integration tests for POST /api/agent/v1/jobs/{guid}/fail."""

    def test_fail_job_success(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_running_job,
    ):
        """Successfully mark a running job as failed."""
        job, signing_secret = create_running_job(test_team, test_agent)

        error_data = {"error": "Test error message"}
        signature = compute_signature(signing_secret, error_data)

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/fail",
            json={
                "error_message": "Test error message",
                "signature": signature,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["guid"] == job.guid
        assert data["status"] == "failed"
        assert data["error_message"] == "Test error message"

        # Verify job updated in DB
        test_db_session.refresh(job)
        assert job.status == JobStatus.FAILED
        assert job.error_message == "Test error message"

    def test_fail_job_creates_failed_result(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_running_job,
    ):
        """Failing a job creates an AnalysisResult with FAILED status."""
        job, signing_secret = create_running_job(test_team, test_agent)

        error_data = {"error": "Database connection failed"}
        signature = compute_signature(signing_secret, error_data)

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/fail",
            json={
                "error_message": "Database connection failed",
                "signature": signature,
            }
        )

        assert response.status_code == 200

        # Verify AnalysisResult was created with FAILED status
        test_db_session.refresh(job)
        result = test_db_session.query(AnalysisResult).filter(
            AnalysisResult.id == job.result_id
        ).first()

        assert result is not None
        assert result.status.value.lower() == "failed"
        assert result.error_message == "Database connection failed"

    def test_fail_job_wrong_agent(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_user,
        test_agent,
        create_agent,
        create_running_job,
    ):
        """Cannot fail job assigned to different agent."""
        # agent_client is authenticated as test_agent
        other_agent = create_agent(test_team, test_user, name="Other Agent")

        job, signing_secret = create_running_job(test_team, other_agent)

        error_data = {"error": "Test error"}
        signature = compute_signature(signing_secret, error_data)

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/fail",
            json={
                "error_message": "Test error",
                "signature": signature,
            }
        )

        assert response.status_code == 400


# ============================================================================
# Helper Functions
# ============================================================================

def compute_signature(signing_secret: str, data: dict) -> str:
    """Compute HMAC-SHA256 signature for data."""
    from base64 import b64decode

    secret_bytes = b64decode(signing_secret)
    canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
    signature = hmac.new(
        secret_bytes,
        canonical.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature


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
def create_job(test_db_session):
    """Factory fixture to create test jobs."""
    def _create_job(
        team,
        tool="photostats",
        status=JobStatus.PENDING,
        agent=None,
    ):
        job = Job(
            team_id=team.id,
            tool=tool,
            mode="collection",
            status=status,
            agent_id=agent.id if agent else None,
            assigned_at=datetime.utcnow() if agent else None,
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)
        return job

    return _create_job


@pytest.fixture
def create_running_job(test_db_session):
    """Factory fixture to create a running job with signing secret."""
    def _create_running_job(team, agent, tool="photostats"):
        # Generate signing secret
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
