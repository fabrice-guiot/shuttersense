"""
Integration tests for scheduled job functionality.

Tests:
- Scheduled job creation on job completion (with TTL)
- Queue status scheduled_count field
- Job list filtering by scheduled status
- Scheduled job cancellation on manual run

Issue #90 - Distributed Agent Architecture (Phase 13)
Task: T183
"""

import json
import pytest
import secrets
import hashlib
import hmac
from base64 import b64encode, b64decode
from datetime import datetime, timedelta

from backend.src.models.job import Job, JobStatus
from backend.src.models.collection import Collection, CollectionType, CollectionState
from backend.src.models.agent import Agent, AgentStatus


class TestScheduledJobCreationOnCompletion:
    """Integration tests for scheduled job creation when job completes."""

    def test_completion_creates_scheduled_job_when_ttl_configured(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_user,
        test_agent,
        create_collection_with_ttl,
    ):
        """Completing a job creates a scheduled follow-up job when team TTL is configured."""
        # Team has default TTL of 3600s for LIVE state (from seed data)
        collection = create_collection_with_ttl(test_team, test_agent, state=CollectionState.LIVE)

        # Create running job for this collection
        job, signing_secret = create_running_job_for_collection(
            test_db_session, test_team, test_agent, collection
        )

        # Complete the job
        results = {"total_files": 100, "issues_found": 0}
        signature = compute_signature(signing_secret, results)

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/complete",
            json={
                "results": results,
                "report_html": "<html>Test</html>",
                "files_scanned": 100,
                "issues_found": 0,
                "signature": signature,
            }
        )

        assert response.status_code == 200

        # Verify scheduled job was created
        scheduled_job = test_db_session.query(Job).filter(
            Job.collection_id == collection.id,
            Job.status == JobStatus.SCHEDULED,
            Job.tool == "photostats",
        ).first()

        assert scheduled_job is not None
        assert scheduled_job.parent_job_id == job.id
        assert scheduled_job.scheduled_for is not None

        # Should be scheduled ~1 hour from now (default TTL for LIVE state)
        expected_time = datetime.utcnow() + timedelta(seconds=3600)
        assert abs((scheduled_job.scheduled_for - expected_time).total_seconds()) < 60

    def test_completion_no_scheduled_job_when_ttl_is_zero(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_collection_with_ttl,
        set_team_ttl_config,
    ):
        """Completing a job does NOT create scheduled job when team TTL is 0."""
        # Set team's LIVE TTL to 0 (disabled)
        set_team_ttl_config(test_team, 'live', 0)

        collection = create_collection_with_ttl(test_team, test_agent, state=CollectionState.LIVE)

        # Create running job for this collection
        job, signing_secret = create_running_job_for_collection(
            test_db_session, test_team, test_agent, collection
        )

        # Complete the job
        results = {"total_files": 50, "issues_found": 0}
        signature = compute_signature(signing_secret, results)

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/complete",
            json={
                "results": results,
                "report_html": "<html>Test</html>",
                "files_scanned": 50,
                "issues_found": 0,
                "signature": signature,
            }
        )

        assert response.status_code == 200

        # Verify no scheduled job was created
        scheduled_job = test_db_session.query(Job).filter(
            Job.collection_id == collection.id,
            Job.status == JobStatus.SCHEDULED,
        ).first()

        assert scheduled_job is None


class TestQueueStatusScheduledCount:
    """Integration tests for queue status scheduled_count field."""

    def test_queue_status_includes_scheduled_count(
        self,
        test_client,
        test_db_session,
        test_team,
        sample_collection,
    ):
        """Queue status response includes scheduled_count field."""
        collection = sample_collection()

        # Create scheduled jobs
        for _ in range(3):
            job = Job(
                team_id=test_team.id,
                collection_id=collection.id,
                tool="photostats",
                status=JobStatus.SCHEDULED,
                scheduled_for=datetime.utcnow() + timedelta(hours=1),
                required_capabilities_json=json.dumps([]),
            )
            test_db_session.add(job)

        # Create pending jobs
        for _ in range(2):
            job = Job(
                team_id=test_team.id,
                collection_id=collection.id,
                tool="photostats",
                status=JobStatus.PENDING,
                required_capabilities_json=json.dumps([]),
            )
            test_db_session.add(job)

        test_db_session.commit()

        response = test_client.get("/api/tools/queue/status")

        assert response.status_code == 200
        data = response.json()
        assert "scheduled_count" in data
        assert data["scheduled_count"] == 3
        assert data["queued_count"] == 2  # Only PENDING, not SCHEDULED

    def test_queue_status_scheduled_count_zero_when_none(
        self,
        test_client,
        test_db_session,
    ):
        """Queue status returns scheduled_count=0 when no scheduled jobs."""
        response = test_client.get("/api/tools/queue/status")

        assert response.status_code == 200
        data = response.json()
        assert data["scheduled_count"] == 0


class TestJobListScheduledFilter:
    """Integration tests for job list filtering by scheduled status."""

    def test_list_jobs_filter_by_scheduled_status(
        self,
        test_client,
        test_db_session,
        test_team,
        sample_collection,
    ):
        """Can filter jobs by scheduled status."""
        collection = sample_collection()

        # Create jobs with different statuses
        scheduled_job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.SCHEDULED,
            scheduled_for=datetime.utcnow() + timedelta(hours=2),
            required_capabilities_json=json.dumps([]),
        )
        pending_job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.PENDING,
            required_capabilities_json=json.dumps([]),
        )
        completed_job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.COMPLETED,
            completed_at=datetime.utcnow(),
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add_all([scheduled_job, pending_job, completed_job])
        test_db_session.commit()

        # Filter by scheduled status AND collection to avoid picking up jobs from other tests
        response = test_client.get(
            "/api/tools/jobs",
            params={"status": "scheduled", "collection_guid": collection.guid}
        )

        assert response.status_code == 200
        data = response.json()

        # Should have exactly 1 scheduled job for this collection
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "scheduled"

    def test_scheduled_job_includes_scheduled_for_timestamp(
        self,
        test_client,
        test_db_session,
        test_team,
        sample_collection,
    ):
        """Scheduled job response includes scheduled_for timestamp."""
        collection = sample_collection()

        scheduled_time = datetime.utcnow() + timedelta(hours=4)
        job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.SCHEDULED,
            scheduled_for=scheduled_time,
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        response = test_client.get(f"/api/tools/jobs/{job.guid}")

        assert response.status_code == 200
        data = response.json()
        assert data["scheduled_for"] is not None
        # Parse and verify it's approximately correct
        returned_time = datetime.fromisoformat(data["scheduled_for"].replace("Z", "+00:00"))
        assert abs((returned_time.replace(tzinfo=None) - scheduled_time).total_seconds()) < 2


class TestScheduledJobCancellation:
    """Integration tests for scheduled job cancellation on manual run."""

    def test_manual_run_cancels_existing_scheduled_job(
        self,
        test_client,
        test_db_session,
        test_team,
        sample_collection,
    ):
        """Running a tool manually cancels the scheduled job for same collection/tool."""
        collection = sample_collection()

        # Create existing scheduled job
        scheduled_job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.SCHEDULED,
            scheduled_for=datetime.utcnow() + timedelta(hours=1),
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(scheduled_job)
        test_db_session.commit()
        test_db_session.refresh(scheduled_job)

        # Run tool manually
        response = test_client.post(
            "/api/tools/run",
            json={
                "tool": "photostats",
                "collection_guid": collection.guid,
            }
        )

        assert response.status_code == 202

        # Verify scheduled job was cancelled
        test_db_session.refresh(scheduled_job)
        assert scheduled_job.status == JobStatus.CANCELLED

    def test_manual_run_different_tool_does_not_cancel_scheduled(
        self,
        test_client,
        test_db_session,
        test_team,
        sample_collection,
    ):
        """Running a different tool does NOT cancel scheduled job for other tool."""
        collection = sample_collection()

        # Create scheduled job for photostats
        scheduled_job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.SCHEDULED,
            scheduled_for=datetime.utcnow() + timedelta(hours=1),
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(scheduled_job)
        test_db_session.commit()
        test_db_session.refresh(scheduled_job)

        # Run different tool manually
        response = test_client.post(
            "/api/tools/run",
            json={
                "tool": "photo_pairing",
                "collection_guid": collection.guid,
            }
        )

        assert response.status_code == 202

        # Verify scheduled job was NOT cancelled
        test_db_session.refresh(scheduled_job)
        assert scheduled_job.status == JobStatus.SCHEDULED


class TestScheduledJobCancelEndpoint:
    """Integration tests for cancelling scheduled jobs via cancel endpoint."""

    def test_cancel_scheduled_job(
        self,
        test_client,
        test_db_session,
        test_team,
        sample_collection,
    ):
        """Can cancel a scheduled job via cancel endpoint."""
        collection = sample_collection()

        job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.SCHEDULED,
            scheduled_for=datetime.utcnow() + timedelta(hours=1),
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        response = test_client.post(f"/api/tools/jobs/{job.guid}/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

        # Verify in DB
        test_db_session.refresh(job)
        assert job.status == JobStatus.CANCELLED


# ============================================================================
# Helper Functions
# ============================================================================

def compute_signature(signing_secret: str, data: dict) -> str:
    """Compute HMAC-SHA256 signature for data."""
    secret_bytes = b64decode(signing_secret)
    canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
    signature = hmac.new(
        secret_bytes,
        canonical.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature


def create_running_job_for_collection(db_session, team, agent, collection):
    """Create a running job for a collection with signing secret."""
    secret_bytes = secrets.token_bytes(32)
    signing_secret = b64encode(secret_bytes).decode('utf-8')
    secret_hash = hashlib.sha256(secret_bytes).hexdigest()

    job = Job(
        team_id=team.id,
        collection_id=collection.id,
        tool="photostats",
        mode="collection",
        status=JobStatus.RUNNING,
        agent_id=agent.id,
        assigned_at=datetime.utcnow(),
        started_at=datetime.utcnow(),
        signing_secret_hash=secret_hash,
        required_capabilities_json=json.dumps(["local_filesystem"]),
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    return job, signing_secret


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def create_collection_with_ttl(test_db_session):
    """Factory fixture to create collections with specific state."""
    import tempfile

    def _create_collection(team, agent, state=CollectionState.LIVE):
        temp_dir = tempfile.mkdtemp()

        collection = Collection(
            team_id=team.id,
            name="TTL Test Collection",
            location=temp_dir,
            type=CollectionType.LOCAL,
            state=state,
            bound_agent_id=agent.id,
        )
        test_db_session.add(collection)
        test_db_session.commit()
        test_db_session.refresh(collection)

        return collection

    return _create_collection


@pytest.fixture
def set_team_ttl_config(test_db_session):
    """Factory fixture to set team TTL configuration."""
    def _set_config(team, state_key: str, ttl_value: int):
        from backend.src.models.configuration import Configuration

        # Update or create the TTL config
        config = test_db_session.query(Configuration).filter(
            Configuration.team_id == team.id,
            Configuration.category == 'collection_ttl',
            Configuration.key == state_key,
        ).first()

        if config:
            config.value_json = {'value': ttl_value, 'label': f'{state_key} ({ttl_value}s)'}
        else:
            config = Configuration(
                team_id=team.id,
                category='collection_ttl',
                key=state_key,
                value_json={'value': ttl_value, 'label': f'{state_key} ({ttl_value}s)'},
            )
            test_db_session.add(config)

        test_db_session.commit()

    return _set_config


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
