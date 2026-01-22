"""
Unit tests for job cancellation service.

Tests cancel_job and retry_job methods in ToolService including:
- Cancelling PENDING jobs (direct cancellation)
- Cancelling RUNNING jobs (via pending_commands mechanism)
- Cannot cancel COMPLETED/FAILED jobs
- Retry creates new job from failed job
"""

import json
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from backend.src.services.tool_service import ToolService
from backend.src.models.job import Job, JobStatus as DBJobStatus
from backend.src.models import Pipeline
from backend.src.schemas.tools import JobStatus, ToolType
from backend.src.utils.job_queue import JobQueue


class TestCancelPendingJob:
    """Tests for cancelling PENDING/SCHEDULED jobs."""

    def test_cancel_pending_job_success(self, test_db_session, test_team, test_collection):
        """Test cancelling a PENDING job directly updates status."""
        # Create a pending job with proper JSON for JSONB fields
        job = Job(
            team_id=test_team.id,
            collection_id=test_collection.id,
            tool="photostats",
            status=DBJobStatus.PENDING,
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        service = ToolService(db=test_db_session, job_queue=JobQueue())
        result = service.cancel_job(job.guid, team_id=test_team.id)

        assert result is not None
        assert result.status == JobStatus.CANCELLED
        assert result.id == job.guid

        # Verify DB was updated
        test_db_session.refresh(job)
        assert job.status == DBJobStatus.CANCELLED
        assert job.completed_at is not None

    def test_cancel_scheduled_job_success(self, test_db_session, test_team, test_collection):
        """Test cancelling a SCHEDULED job directly updates status."""
        job = Job(
            team_id=test_team.id,
            collection_id=test_collection.id,
            tool="photostats",
            status=DBJobStatus.SCHEDULED,
            scheduled_for=datetime.utcnow() + timedelta(hours=1),
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        service = ToolService(db=test_db_session, job_queue=JobQueue())
        result = service.cancel_job(job.guid, team_id=test_team.id)

        assert result is not None
        assert result.status == JobStatus.CANCELLED

    def test_cancel_already_cancelled_returns_job(self, test_db_session, test_team, test_collection):
        """Test cancelling an already cancelled job returns the job."""
        job = Job(
            team_id=test_team.id,
            collection_id=test_collection.id,
            tool="photostats",
            status=DBJobStatus.CANCELLED,
            completed_at=datetime.utcnow(),
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        service = ToolService(db=test_db_session, job_queue=JobQueue())
        result = service.cancel_job(job.guid, team_id=test_team.id)

        assert result is not None
        assert result.status == JobStatus.CANCELLED


class TestCancelRunningJob:
    """Tests for cancelling RUNNING/ASSIGNED jobs with agent notification."""

    @pytest.mark.skip(reason="Agent creation requires PostgreSQL for JSONB columns")
    def test_cancel_running_job_queues_command(self, test_db_session, test_team, test_collection, test_agent):
        """Test cancelling a RUNNING job queues cancel command to agent."""
        # Create a running job assigned to agent
        job = Job(
            team_id=test_team.id,
            collection_id=test_collection.id,
            tool="photostats",
            status=DBJobStatus.RUNNING,
            agent_id=test_agent.id,
            started_at=datetime.utcnow(),
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        service = ToolService(db=test_db_session, job_queue=JobQueue())

        with patch('backend.src.services.tool_service.AgentService') as MockAgentService:
            mock_agent_service = Mock()
            MockAgentService.return_value = mock_agent_service

            result = service.cancel_job(job.guid, team_id=test_team.id)

            assert result is not None
            assert result.status == JobStatus.CANCELLED

            # Verify cancel command was queued to agent
            mock_agent_service.queue_command.assert_called_once_with(
                test_agent.id,
                f"cancel_job:{job.guid}"
            )

    @pytest.mark.skip(reason="Agent creation requires PostgreSQL for JSONB columns")
    def test_cancel_assigned_job_queues_command(self, test_db_session, test_team, test_collection, test_agent):
        """Test cancelling an ASSIGNED job queues cancel command to agent."""
        job = Job(
            team_id=test_team.id,
            collection_id=test_collection.id,
            tool="photostats",
            status=DBJobStatus.ASSIGNED,
            agent_id=test_agent.id,
            assigned_at=datetime.utcnow(),
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        service = ToolService(db=test_db_session, job_queue=JobQueue())

        with patch('backend.src.services.tool_service.AgentService') as MockAgentService:
            mock_agent_service = Mock()
            MockAgentService.return_value = mock_agent_service

            result = service.cancel_job(job.guid, team_id=test_team.id)

            assert result is not None
            assert result.status == JobStatus.CANCELLED
            mock_agent_service.queue_command.assert_called_once()

    def test_cancel_running_job_without_agent(self, test_db_session, test_team, test_collection):
        """Test cancelling a RUNNING job without agent_id doesn't fail."""
        job = Job(
            team_id=test_team.id,
            collection_id=test_collection.id,
            tool="photostats",
            status=DBJobStatus.RUNNING,
            agent_id=None,  # No agent assigned
            started_at=datetime.utcnow(),
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        service = ToolService(db=test_db_session, job_queue=JobQueue())
        result = service.cancel_job(job.guid, team_id=test_team.id)

        assert result is not None
        assert result.status == JobStatus.CANCELLED


class TestCannotCancelTerminalJobs:
    """Tests that completed/failed jobs cannot be cancelled."""

    def test_cannot_cancel_completed_job(self, test_db_session, test_team, test_collection):
        """Test cancelling a COMPLETED job raises ValueError."""
        job = Job(
            team_id=test_team.id,
            collection_id=test_collection.id,
            tool="photostats",
            status=DBJobStatus.COMPLETED,
            completed_at=datetime.utcnow(),
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        service = ToolService(db=test_db_session, job_queue=JobQueue())

        with pytest.raises(ValueError) as exc_info:
            service.cancel_job(job.guid, team_id=test_team.id)

        assert "Cannot cancel job in completed state" in str(exc_info.value)

    def test_cannot_cancel_failed_job(self, test_db_session, test_team, test_collection):
        """Test cancelling a FAILED job raises ValueError."""
        job = Job(
            team_id=test_team.id,
            collection_id=test_collection.id,
            tool="photostats",
            status=DBJobStatus.FAILED,
            completed_at=datetime.utcnow(),
            error_message="Test error",
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        service = ToolService(db=test_db_session, job_queue=JobQueue())

        with pytest.raises(ValueError) as exc_info:
            service.cancel_job(job.guid, team_id=test_team.id)

        assert "Cannot cancel job in failed state" in str(exc_info.value)


class TestCancelJobNotFound:
    """Tests for cancelling non-existent jobs."""

    def test_cancel_nonexistent_job_returns_none(self, test_db_session):
        """Test cancelling a non-existent job returns None."""
        service = ToolService(db=test_db_session, job_queue=JobQueue())
        result = service.cancel_job("job_01hgw2bbg0000000000000999")

        assert result is None

    def test_cancel_invalid_guid_returns_none(self, test_db_session):
        """Test cancelling with invalid GUID format returns None."""
        service = ToolService(db=test_db_session, job_queue=JobQueue())
        result = service.cancel_job("invalid-guid")

        assert result is None

    def test_cancel_job_wrong_team_returns_none(self, test_db_session, test_team, test_collection):
        """Test cancelling job with wrong team_id returns None."""
        job = Job(
            team_id=test_team.id,
            collection_id=test_collection.id,
            tool="photostats",
            status=DBJobStatus.PENDING,
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        service = ToolService(db=test_db_session, job_queue=JobQueue())
        # Try to cancel with wrong team_id
        result = service.cancel_job(job.guid, team_id=99999)

        assert result is None


class TestRetryJob:
    """Tests for retry_job method."""

    def test_retry_failed_job_creates_new_job(self, test_db_session, test_team, test_collection):
        """Test retrying a failed job creates a new PENDING job."""
        # Create a failed job
        original_job = Job(
            team_id=test_team.id,
            collection_id=test_collection.id,
            tool="photostats",
            status=DBJobStatus.FAILED,
            completed_at=datetime.utcnow(),
            error_message="Original error",
            retry_count=0,
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(original_job)
        test_db_session.commit()
        test_db_session.refresh(original_job)

        service = ToolService(db=test_db_session, job_queue=JobQueue())
        result = service.retry_job(original_job.guid, team_id=test_team.id)

        assert result is not None
        assert result.status == JobStatus.QUEUED  # PENDING maps to QUEUED
        assert result.id != original_job.guid  # New job created
        assert result.collection_guid == original_job.collection.guid

        # Verify new job in DB - need to parse GUID to UUID for query
        new_job_uuid = Job.parse_guid(result.id)
        new_job = test_db_session.query(Job).filter(Job.uuid == new_job_uuid).first()
        assert new_job is not None
        assert new_job.retry_count == 1
        assert new_job.parent_job_id == original_job.id

    @pytest.mark.skip(reason="Pipeline creation requires additional fixtures")
    def test_retry_preserves_job_parameters(self, test_db_session, test_team, test_collection, test_pipeline):
        """Test retry preserves tool, mode, pipeline from original job."""
        original_job = Job(
            team_id=test_team.id,
            collection_id=test_collection.id,
            pipeline_id=test_pipeline.id,
            pipeline_version=test_pipeline.version,
            tool="pipeline_validation",
            mode="collection",
            status=DBJobStatus.FAILED,
            completed_at=datetime.utcnow(),
            error_message="Validation failed",
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(original_job)
        test_db_session.commit()
        test_db_session.refresh(original_job)

        service = ToolService(db=test_db_session, job_queue=JobQueue())
        result = service.retry_job(original_job.guid, team_id=test_team.id)

        assert result is not None
        assert result.tool == ToolType.PIPELINE_VALIDATION
        assert result.pipeline_guid == test_pipeline.guid

    def test_cannot_retry_non_failed_job(self, test_db_session, test_team, test_collection):
        """Test retrying a non-failed job raises ValueError."""
        job = Job(
            team_id=test_team.id,
            collection_id=test_collection.id,
            tool="photostats",
            status=DBJobStatus.COMPLETED,
            completed_at=datetime.utcnow(),
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        service = ToolService(db=test_db_session, job_queue=JobQueue())

        with pytest.raises(ValueError) as exc_info:
            service.retry_job(job.guid, team_id=test_team.id)

        assert "Cannot retry job in completed status" in str(exc_info.value)

    def test_retry_nonexistent_job_returns_none(self, test_db_session):
        """Test retrying a non-existent job returns None."""
        service = ToolService(db=test_db_session, job_queue=JobQueue())
        result = service.retry_job("job_01hgw2bbg0000000000000999")

        assert result is None

    def test_retry_increments_retry_count(self, test_db_session, test_team, test_collection):
        """Test retry increments retry_count from original job."""
        original_job = Job(
            team_id=test_team.id,
            collection_id=test_collection.id,
            tool="photostats",
            status=DBJobStatus.FAILED,
            completed_at=datetime.utcnow(),
            error_message="Error",
            retry_count=2,  # Already retried twice
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(original_job)
        test_db_session.commit()
        test_db_session.refresh(original_job)

        service = ToolService(db=test_db_session, job_queue=JobQueue())
        result = service.retry_job(original_job.guid, team_id=test_team.id)

        # Verify new job in DB has incremented retry_count
        new_job_uuid = Job.parse_guid(result.id)
        new_job = test_db_session.query(Job).filter(Job.uuid == new_job_uuid).first()
        assert new_job is not None
        assert new_job.retry_count == 3


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def test_connector(sample_connector):
    """Create a test connector using the sample_connector factory."""
    return sample_connector(connector_type='s3')


@pytest.fixture
def test_collection(sample_collection, test_connector):
    """Create a test collection using the sample_collection factory."""
    return sample_collection(connector_id=test_connector.id)


@pytest.fixture
def test_agent(test_db_session, test_team, test_user):
    """Create a test agent using the AgentService for proper JSONB handling."""
    from backend.src.services.agent_service import AgentService

    service = AgentService(test_db_session)

    # Create registration token
    token_result = service.create_registration_token(
        team_id=test_team.id,
        created_by_user_id=test_user.id,
    )
    test_db_session.commit()

    # Register agent
    result = service.register_agent(
        plaintext_token=token_result.plaintext_token,
        name="Test Agent",
        hostname="test.local",
        os_info="Linux",
        capabilities=["local_filesystem"],
        version="1.0.0",
    )
    test_db_session.commit()
    test_db_session.refresh(result.agent)
    return result.agent


@pytest.fixture
def test_pipeline(test_db_session, test_team):
    """Create a test pipeline."""
    pipeline = Pipeline(
        team_id=test_team.id,
        name="Test Pipeline",
        description="Test pipeline for testing",
        stages=[{"name": "stage1", "extensions": [".jpg"]}],
        is_active=True,
        is_valid=True,
        is_default=True,
        version=1,
    )
    test_db_session.add(pipeline)
    test_db_session.commit()
    test_db_session.refresh(pipeline)
    return pipeline
