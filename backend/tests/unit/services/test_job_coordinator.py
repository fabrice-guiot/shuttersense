"""
Unit tests for JobCoordinatorService.

Tests job claiming, completion, progress updates, and result signing.

Issue #90 - Distributed Agent Architecture (Phase 5)
Tasks: T069, T070, T077, T079, T080
"""

import pytest
from datetime import datetime, timedelta
from base64 import b64decode

from backend.src.services.job_coordinator_service import (
    JobCoordinatorService,
    JobCompletionData,
)
from backend.src.models.agent import AgentStatus
from backend.src.models.job import Job, JobStatus
from backend.src.models.collection import Collection, CollectionType, CollectionState
from backend.src.services.exceptions import NotFoundError, ValidationError


class TestJobClaiming:
    """Tests for job claiming functionality."""

    def test_claim_job_no_jobs_available(self, test_db_session, test_team, test_user):
        """Claim returns None when no jobs are available."""
        service = JobCoordinatorService(test_db_session)

        result = service.claim_job(
            agent_id=1,
            team_id=test_team.id,
            agent_capabilities=["local_filesystem"],
        )

        assert result is None

    def test_claim_job_success(self, test_db_session, test_team, test_user, create_agent, create_job):
        """Successfully claim an available job."""
        agent = create_agent(test_team, test_user)
        job = create_job(test_team, tool="photostats", status=JobStatus.PENDING)

        service = JobCoordinatorService(test_db_session)

        result = service.claim_job(
            agent_id=agent.id,
            team_id=test_team.id,
            agent_capabilities=["local_filesystem"],
        )

        assert result is not None
        assert result.job.guid == job.guid
        assert result.job.status == JobStatus.ASSIGNED
        assert result.job.agent_id == agent.id
        assert result.signing_secret is not None
        assert len(b64decode(result.signing_secret)) == 32  # 256-bit secret

    def test_claim_job_bound_agent(self, test_db_session, test_team, test_user, create_agent, create_collection, create_job):
        """Bound jobs are only claimable by the bound agent."""
        agent1 = create_agent(test_team, test_user, name="Agent 1")
        agent2 = create_agent(test_team, test_user, name="Agent 2")

        # Create a LOCAL collection bound to agent1
        collection = create_collection(test_team, bound_agent=agent1)

        # Create a job bound to the collection's agent
        job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.PENDING,
            collection=collection,
            bound_agent=agent1,
        )

        service = JobCoordinatorService(test_db_session)

        # Agent 2 should not be able to claim the bound job
        result2 = service.claim_job(
            agent_id=agent2.id,
            team_id=test_team.id,
            agent_capabilities=["local_filesystem"],
        )
        assert result2 is None

        # Agent 1 should be able to claim it
        result1 = service.claim_job(
            agent_id=agent1.id,
            team_id=test_team.id,
            agent_capabilities=["local_filesystem"],
        )
        assert result1 is not None
        assert result1.job.guid == job.guid

    def test_claim_job_priority_ordering(self, test_db_session, test_team, test_user, create_agent, create_job):
        """Jobs are claimed in priority order (highest first)."""
        agent = create_agent(test_team, test_user)

        # Create jobs with different priorities
        low_priority = create_job(test_team, tool="photostats", priority=0)
        high_priority = create_job(test_team, tool="photostats", priority=10)
        medium_priority = create_job(test_team, tool="photostats", priority=5)

        service = JobCoordinatorService(test_db_session)

        # Should claim highest priority first
        result1 = service.claim_job(agent_id=agent.id, team_id=test_team.id)
        assert result1.job.guid == high_priority.guid

        result2 = service.claim_job(agent_id=agent.id, team_id=test_team.id)
        assert result2.job.guid == medium_priority.guid

        result3 = service.claim_job(agent_id=agent.id, team_id=test_team.id)
        assert result3.job.guid == low_priority.guid

    def test_claim_job_scheduled_not_due(self, test_db_session, test_team, test_user, create_agent, create_job):
        """Scheduled jobs are not claimable before their scheduled time."""
        agent = create_agent(test_team, test_user)

        # Create a scheduled job for the future
        future_job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.SCHEDULED,
            scheduled_for=datetime.utcnow() + timedelta(hours=1),
        )

        service = JobCoordinatorService(test_db_session)

        result = service.claim_job(agent_id=agent.id, team_id=test_team.id)
        assert result is None

    def test_claim_job_scheduled_due(self, test_db_session, test_team, test_user, create_agent, create_job):
        """Scheduled jobs are claimable after their scheduled time."""
        agent = create_agent(test_team, test_user)

        # Create a scheduled job for the past
        past_job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.SCHEDULED,
            scheduled_for=datetime.utcnow() - timedelta(minutes=5),
        )

        service = JobCoordinatorService(test_db_session)

        result = service.claim_job(agent_id=agent.id, team_id=test_team.id)
        assert result is not None
        assert result.job.guid == past_job.guid

    def test_claim_job_tenant_isolation(self, test_db_session, test_team, test_user, other_team, other_team_user, create_agent, create_job):
        """Jobs are isolated by team."""
        agent = create_agent(test_team, test_user)

        # Create job in other team
        other_job = create_job(other_team, tool="photostats", status=JobStatus.PENDING)

        service = JobCoordinatorService(test_db_session)

        # Agent should not see job from other team
        result = service.claim_job(agent_id=agent.id, team_id=test_team.id)
        assert result is None


class TestJobProgress:
    """Tests for job progress updates."""

    def test_update_progress_success(self, test_db_session, test_team, test_user, create_agent, create_job):
        """Successfully update job progress."""
        agent = create_agent(test_team, test_user)
        job = create_job(test_team, tool="photostats", status=JobStatus.ASSIGNED, agent=agent)

        service = JobCoordinatorService(test_db_session)

        progress = {
            "stage": "scanning",
            "percentage": 50,
            "files_scanned": 1000,
            "total_files": 2000,
        }

        updated_job = service.update_progress(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            progress=progress,
        )

        assert updated_job.progress == progress
        assert updated_job.status == JobStatus.RUNNING  # Auto-transition from ASSIGNED

    def test_update_progress_wrong_agent(self, test_db_session, test_team, test_user, create_agent, create_job):
        """Cannot update progress for job assigned to different agent."""
        agent1 = create_agent(test_team, test_user, name="Agent 1")
        agent2 = create_agent(test_team, test_user, name="Agent 2")
        job = create_job(test_team, tool="photostats", status=JobStatus.ASSIGNED, agent=agent1)

        service = JobCoordinatorService(test_db_session)

        with pytest.raises(ValidationError):
            service.update_progress(
                job_guid=job.guid,
                agent_id=agent2.id,
                team_id=test_team.id,
                progress={"stage": "scanning"},
            )

    def test_update_progress_job_not_found(self, test_db_session, test_team, test_user, create_agent):
        """Cannot update progress for non-existent job."""
        agent = create_agent(test_team, test_user)
        service = JobCoordinatorService(test_db_session)

        with pytest.raises(NotFoundError):
            service.update_progress(
                job_guid="job_nonexistent123456789012345",
                agent_id=agent.id,
                team_id=test_team.id,
                progress={"stage": "scanning"},
            )


class TestJobCompletion:
    """Tests for job completion."""

    def test_complete_job_success(self, test_db_session, test_team, test_user, create_agent, create_job):
        """Successfully complete a job."""
        agent = create_agent(test_team, test_user)
        job = create_job(test_team, tool="photostats", status=JobStatus.RUNNING, agent=agent)

        # Set signing secret hash
        job.signing_secret_hash = "dummy_hash"
        test_db_session.commit()

        service = JobCoordinatorService(test_db_session)

        completion_data = JobCompletionData(
            results={"total_files": 1000, "issues_found": 5},
            report_html="<html>Report</html>",
            files_scanned=1000,
            issues_found=5,
            signature="a" * 64,  # Dummy signature (64 hex chars)
        )

        completed_job = service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        assert completed_job.status == JobStatus.COMPLETED
        assert completed_job.result_id is not None
        assert completed_job.completed_at is not None

    def test_complete_job_creates_result(self, test_db_session, test_team, test_user, create_agent, create_job):
        """Completing a job creates an AnalysisResult record."""
        agent = create_agent(test_team, test_user)
        job = create_job(test_team, tool="photostats", status=JobStatus.RUNNING, agent=agent)
        job.signing_secret_hash = "dummy_hash"
        test_db_session.commit()

        service = JobCoordinatorService(test_db_session)

        completion_data = JobCompletionData(
            results={"total_files": 1000},
            report_html="<html>Report</html>",
            files_scanned=1000,
            issues_found=5,
            signature="a" * 64,
        )

        service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        # Check AnalysisResult was created
        from backend.src.models import AnalysisResult

        result = test_db_session.query(AnalysisResult).filter(
            AnalysisResult.id == job.result_id
        ).first()

        assert result is not None
        assert result.tool == "photostats"
        assert result.files_scanned == 1000
        assert result.issues_found == 5
        assert result.report_html == "<html>Report</html>"


class TestJobFailure:
    """Tests for job failure handling."""

    def test_fail_job_success(self, test_db_session, test_team, test_user, create_agent, create_job):
        """Successfully mark a job as failed."""
        agent = create_agent(test_team, test_user)
        job = create_job(test_team, tool="photostats", status=JobStatus.RUNNING, agent=agent)

        service = JobCoordinatorService(test_db_session)

        failed_job = service.fail_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            error_message="Test error",
        )

        assert failed_job.status == JobStatus.FAILED
        assert failed_job.error_message == "Test error"

    def test_fail_job_wrong_agent(self, test_db_session, test_team, test_user, create_agent, create_job):
        """Cannot fail job assigned to different agent."""
        agent1 = create_agent(test_team, test_user, name="Agent 1")
        agent2 = create_agent(test_team, test_user, name="Agent 2")
        job = create_job(test_team, tool="photostats", status=JobStatus.RUNNING, agent=agent1)

        service = JobCoordinatorService(test_db_session)

        with pytest.raises(ValidationError):
            service.fail_job(
                job_guid=job.guid,
                agent_id=agent2.id,
                team_id=test_team.id,
                error_message="Test error",
            )


class TestSigningSecret:
    """Tests for signing secret generation and verification."""

    def test_signing_secret_generation(self, test_db_session, test_team, test_user, create_agent, create_job):
        """Signing secret is generated on job claim."""
        agent = create_agent(test_team, test_user)
        job = create_job(test_team, tool="photostats", status=JobStatus.PENDING)

        service = JobCoordinatorService(test_db_session)

        result = service.claim_job(agent_id=agent.id, team_id=test_team.id)

        # Signing secret should be base64-encoded 32 bytes
        secret_bytes = b64decode(result.signing_secret)
        assert len(secret_bytes) == 32

        # Hash should be stored in job
        assert result.job.signing_secret_hash is not None
        assert len(result.job.signing_secret_hash) == 64  # SHA-256 hex

    def test_compute_signature(self, test_db_session, test_team):
        """Compute signature produces valid HMAC-SHA256."""
        service = JobCoordinatorService(test_db_session)

        # Generate a secret
        import secrets
        from base64 import b64encode

        secret_bytes = secrets.token_bytes(32)
        secret_b64 = b64encode(secret_bytes).decode('utf-8')

        results = {"total_files": 100, "issues_found": 5}
        signature = service.compute_signature(secret_b64, results)

        # Signature should be 64 hex characters
        assert len(signature) == 64
        assert all(c in '0123456789abcdef' for c in signature)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def create_agent(test_db_session):
    """Factory fixture to create test agents."""
    created_agents = []

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

        created_agents.append(result.agent)
        return result.agent

    yield _create_agent


@pytest.fixture
def create_collection(test_db_session):
    """Factory fixture to create test collections."""
    def _create_collection(team, bound_agent=None):
        import tempfile

        # Create a temp directory for the collection
        temp_dir = tempfile.mkdtemp()

        collection = Collection(
            team_id=team.id,
            name="Test Collection",
            location=temp_dir,
            type=CollectionType.LOCAL,
            state=CollectionState.LIVE,
            connector_id=None,  # LOCAL collections don't need connectors
            bound_agent_id=bound_agent.id if bound_agent else None,
        )
        test_db_session.add(collection)
        test_db_session.commit()
        test_db_session.refresh(collection)

        return collection

    return _create_collection


@pytest.fixture
def create_job(test_db_session):
    """Factory fixture to create test jobs."""
    import json

    def _create_job(
        team,
        tool="photostats",
        status=JobStatus.PENDING,
        priority=0,
        agent=None,
        collection=None,
        bound_agent=None,
        scheduled_for=None,
    ):
        job = Job(
            team_id=team.id,
            tool=tool,
            mode="collection",
            status=status,
            priority=priority,
            agent_id=agent.id if agent else None,
            assigned_at=datetime.utcnow() if agent else None,
            collection_id=collection.id if collection else None,
            bound_agent_id=bound_agent.id if bound_agent else None,
            scheduled_for=scheduled_for,
            required_capabilities_json=json.dumps([]),  # SQLite needs JSON string
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)
        return job

    return _create_job


@pytest.fixture
def other_team(test_db_session):
    """Create a second team for isolation tests."""
    from backend.src.models import Team

    team = Team(
        name='Other Team',
        slug='other-team',
        is_active=True,
    )
    test_db_session.add(team)
    test_db_session.commit()
    test_db_session.refresh(team)
    return team


@pytest.fixture
def other_team_user(test_db_session, other_team):
    """Create a user in the other team."""
    from backend.src.models import User, UserStatus

    user = User(
        team_id=other_team.id,
        email='other@example.com',
        display_name='Other User',
        status=UserStatus.ACTIVE,
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


# ============================================================================
# Collection Stats Update Tests (Phase 8)
# ============================================================================

class TestCollectionStatsUpdate:
    """Tests for collection stats update on job completion.

    When PhotoStats or Photo Pairing jobs complete, collection statistics
    should be automatically updated from the tool results.

    Issue #90 - Distributed Agent Architecture (Phase 8)
    """

    def test_photostats_updates_file_count_and_storage_bytes(
        self, test_db_session, test_team, test_user, create_agent, create_collection, create_job
    ):
        """PhotoStats results update collection's file_count and storage_bytes."""
        agent = create_agent(test_team, test_user)
        collection = create_collection(test_team)
        job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.RUNNING,
            agent=agent,
            collection=collection,
        )
        job.signing_secret_hash = "dummy_hash"
        test_db_session.commit()

        service = JobCoordinatorService(test_db_session)

        completion_data = JobCompletionData(
            results={
                "total_files": 1500,
                "total_size": 2500000000,  # 2.5 GB
                "orphaned_files": 10,
            },
            files_scanned=1500,
            issues_found=10,
            signature="a" * 64,
        )

        service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        # Refresh collection to get updated values
        test_db_session.refresh(collection)

        assert collection.file_count == 1500
        assert collection.storage_bytes == 2500000000

    def test_photo_pairing_updates_image_count(
        self, test_db_session, test_team, test_user, create_agent, create_collection, create_job
    ):
        """Photo Pairing results update collection's image_count."""
        agent = create_agent(test_team, test_user)
        collection = create_collection(test_team)
        job = create_job(
            test_team,
            tool="photo_pairing",
            status=JobStatus.RUNNING,
            agent=agent,
            collection=collection,
        )
        job.signing_secret_hash = "dummy_hash"
        test_db_session.commit()

        service = JobCoordinatorService(test_db_session)

        completion_data = JobCompletionData(
            results={
                "image_count": 850,
                "camera_groups": 3,
                "pairing_issues": 5,
            },
            files_scanned=1000,
            issues_found=5,
            signature="a" * 64,
        )

        service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        test_db_session.refresh(collection)

        assert collection.image_count == 850

    def test_stats_update_ignores_other_tools(
        self, test_db_session, test_team, test_user, create_agent, create_collection, create_job
    ):
        """Tools other than photostats/photo_pairing don't update collection stats."""
        agent = create_agent(test_team, test_user)
        collection = create_collection(test_team)

        # Set initial values
        collection.file_count = 100
        collection.storage_bytes = 1000000
        collection.image_count = 50
        test_db_session.commit()

        job = create_job(
            test_team,
            tool="pipeline_validation",
            status=JobStatus.RUNNING,
            agent=agent,
            collection=collection,
        )
        job.signing_secret_hash = "dummy_hash"
        test_db_session.commit()

        service = JobCoordinatorService(test_db_session)

        completion_data = JobCompletionData(
            results={
                "total_files": 9999,  # Should be ignored
                "total_size": 9999999,  # Should be ignored
                "image_count": 9999,  # Should be ignored
                "validation_passed": True,
            },
            files_scanned=100,
            issues_found=0,
            signature="a" * 64,
        )

        service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        test_db_session.refresh(collection)

        # Values should be unchanged
        assert collection.file_count == 100
        assert collection.storage_bytes == 1000000
        assert collection.image_count == 50

    def test_stats_update_handles_missing_fields(
        self, test_db_session, test_team, test_user, create_agent, create_collection, create_job
    ):
        """Stats update gracefully handles missing fields in results."""
        agent = create_agent(test_team, test_user)
        collection = create_collection(test_team)

        # Set initial values
        collection.file_count = 100
        collection.storage_bytes = 1000000
        test_db_session.commit()

        job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.RUNNING,
            agent=agent,
            collection=collection,
        )
        job.signing_secret_hash = "dummy_hash"
        test_db_session.commit()

        service = JobCoordinatorService(test_db_session)

        # Results only contain total_files, not total_size
        completion_data = JobCompletionData(
            results={
                "total_files": 200,
                # total_size is missing
            },
            files_scanned=200,
            issues_found=0,
            signature="a" * 64,
        )

        service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        test_db_session.refresh(collection)

        # file_count updated, storage_bytes unchanged
        assert collection.file_count == 200
        assert collection.storage_bytes == 1000000

    def test_stats_update_no_collection_skipped(
        self, test_db_session, test_team, test_user, create_agent, create_job
    ):
        """Stats update is skipped for jobs without collection_id."""
        agent = create_agent(test_team, test_user)

        # Job without collection
        job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.RUNNING,
            agent=agent,
            collection=None,  # No collection
        )
        job.signing_secret_hash = "dummy_hash"
        test_db_session.commit()

        service = JobCoordinatorService(test_db_session)

        completion_data = JobCompletionData(
            results={"total_files": 1000, "total_size": 5000000},
            files_scanned=1000,
            issues_found=0,
            signature="a" * 64,
        )

        # Should complete without error
        completed_job = service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        assert completed_job.status == JobStatus.COMPLETED


# ============================================================================
# Collection Test Job Handling Tests (Phase 8)
# ============================================================================

class TestCollectionTestJobHandling:
    """Tests for collection_test job completion handling.

    collection_test jobs update collection accessibility status
    and create an AnalysisResult record for tracking purposes.

    Issue #90 - Distributed Agent Architecture (Phase 8)
    """

    def test_collection_test_updates_accessibility_on_success(
        self, test_db_session, test_team, test_user, create_agent, create_collection, create_job
    ):
        """Successful collection_test marks collection as accessible."""
        agent = create_agent(test_team, test_user)
        collection = create_collection(test_team)

        # Start as inaccessible
        collection.is_accessible = False
        collection.last_error = "Previous error"
        test_db_session.commit()

        job = create_job(
            test_team,
            tool="collection_test",
            status=JobStatus.RUNNING,
            agent=agent,
            collection=collection,
        )
        job.signing_secret_hash = "dummy_hash"
        test_db_session.commit()

        service = JobCoordinatorService(test_db_session)

        completion_data = JobCompletionData(
            results={
                "success": True,
                "message": "Directory accessible",
            },
            signature="a" * 64,
        )

        service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        test_db_session.refresh(collection)

        assert collection.is_accessible is True
        assert collection.last_error is None

    def test_collection_test_updates_error_on_failure(
        self, test_db_session, test_team, test_user, create_agent, create_collection, create_job
    ):
        """Failed collection_test marks collection as inaccessible with error."""
        agent = create_agent(test_team, test_user)
        collection = create_collection(test_team)

        # Start as accessible
        collection.is_accessible = True
        collection.last_error = None
        test_db_session.commit()

        job = create_job(
            test_team,
            tool="collection_test",
            status=JobStatus.RUNNING,
            agent=agent,
            collection=collection,
        )
        job.signing_secret_hash = "dummy_hash"
        test_db_session.commit()

        service = JobCoordinatorService(test_db_session)

        completion_data = JobCompletionData(
            results={
                "success": False,
                "error": "Permission denied: /path/to/collection",
                "message": "Cannot access directory",
            },
            signature="a" * 64,
        )

        service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        test_db_session.refresh(collection)

        assert collection.is_accessible is False
        assert collection.last_error == "Permission denied: /path/to/collection"

    def test_collection_test_creates_analysis_result(
        self, test_db_session, test_team, test_user, create_agent, create_collection, create_job
    ):
        """collection_test jobs create AnalysisResult records for tracking purposes."""
        from backend.src.models import AnalysisResult

        agent = create_agent(test_team, test_user)
        collection = create_collection(test_team)

        # Count existing results
        initial_count = test_db_session.query(AnalysisResult).count()

        job = create_job(
            test_team,
            tool="collection_test",
            status=JobStatus.RUNNING,
            agent=agent,
            collection=collection,
        )
        job.signing_secret_hash = "dummy_hash"
        test_db_session.commit()

        service = JobCoordinatorService(test_db_session)

        completion_data = JobCompletionData(
            results={"success": True, "message": "OK"},
            signature="a" * 64,
        )

        completed_job = service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        # Job completed with result_id
        assert completed_job.status == JobStatus.COMPLETED
        assert completed_job.result_id is not None

        # An AnalysisResult is created for collection_test jobs
        final_count = test_db_session.query(AnalysisResult).count()
        assert final_count == initial_count + 1

        # Verify result properties
        result = test_db_session.query(AnalysisResult).filter(
            AnalysisResult.id == completed_job.result_id
        ).first()
        assert result is not None
        assert result.tool == "collection_test"

    def test_collection_test_clears_progress(
        self, test_db_session, test_team, test_user, create_agent, create_collection, create_job
    ):
        """collection_test job completion clears progress field."""
        agent = create_agent(test_team, test_user)
        collection = create_collection(test_team)

        job = create_job(
            test_team,
            tool="collection_test",
            status=JobStatus.RUNNING,
            agent=agent,
            collection=collection,
        )
        job.signing_secret_hash = "dummy_hash"
        job.progress = {"stage": "testing", "percentage": 50}
        test_db_session.commit()

        service = JobCoordinatorService(test_db_session)

        completion_data = JobCompletionData(
            results={"success": True},
            signature="a" * 64,
        )

        completed_job = service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        assert completed_job.progress is None

    def test_collection_test_missing_collection_logged(
        self, test_db_session, test_team, test_user, create_agent, create_job
    ):
        """collection_test with missing collection completes without error."""
        agent = create_agent(test_team, test_user)

        # Job without collection
        job = create_job(
            test_team,
            tool="collection_test",
            status=JobStatus.RUNNING,
            agent=agent,
            collection=None,
        )
        job.signing_secret_hash = "dummy_hash"
        test_db_session.commit()

        service = JobCoordinatorService(test_db_session)

        completion_data = JobCompletionData(
            results={"success": True},
            signature="a" * 64,
        )

        # Should complete without error (warning logged)
        completed_job = service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        assert completed_job.status == JobStatus.COMPLETED


# ============================================================================
# Phase 7: Server-Side No-Change Detection Tests (Issue #107)
# ============================================================================

class TestServerSideNoChangeDetection:
    """Tests for server-side no-change detection for inventory-sourced collections.

    When a collection has file_info from bucket inventory (file_info_source='inventory'),
    the server can compute Input State hash and compare with previous result to skip
    redundant job execution.

    Issue #107 - Bucket Inventory Import (Phase 7)
    """

    @pytest.fixture
    def create_inventory_collection(self, test_db_session):
        """Factory fixture to create collections with inventory file info."""
        def _create(team, bound_agent=None, file_info=None):
            import tempfile

            temp_dir = tempfile.mkdtemp()

            collection = Collection(
                team_id=team.id,
                name="Inventory Collection",
                location=temp_dir,
                type=CollectionType.LOCAL,
                state=CollectionState.LIVE,
                connector_id=None,
                bound_agent_id=bound_agent.id if bound_agent else None,
                file_info=file_info or [
                    {"key": "2020/IMG_001.dng", "size": 25000000, "last_modified": "2022-11-25T13:30:49.000Z"},
                    {"key": "2020/IMG_001.xmp", "size": 4096, "last_modified": "2022-11-25T13:30:50.000Z"},
                ],
                file_info_source="inventory",
            )
            test_db_session.add(collection)
            test_db_session.commit()
            test_db_session.refresh(collection)

            return collection

        return _create

    @pytest.fixture
    def create_previous_result(self, test_db_session):
        """Factory fixture to create a previous AnalysisResult with input_state_hash."""
        def _create(team, collection, tool, input_state_hash):
            from backend.src.models import AnalysisResult, ResultStatus

            result = AnalysisResult(
                team_id=team.id,
                collection_id=collection.id,
                tool=tool,
                status=ResultStatus.COMPLETED,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                duration_seconds=1.0,
                files_scanned=2,
                issues_found=0,
                results_json={"total_files": 2},
                report_html="<html>Previous Report</html>",
                input_state_hash=input_state_hash,
            )
            test_db_session.add(result)
            test_db_session.commit()
            test_db_session.refresh(result)

            return result

        return _create

    def test_no_server_detection_for_api_source(
        self, test_db_session, test_team, test_user, create_agent, create_job, create_collection
    ):
        """Server-side detection is skipped for API-sourced file info."""
        agent = create_agent(test_team, test_user)
        collection = create_collection(test_team, bound_agent=agent)

        # Set file_info from API (not inventory)
        collection.file_info = [
            {"key": "2020/IMG_001.dng", "size": 25000000, "last_modified": "2022-11-25T13:30:49.000Z"},
        ]
        collection.file_info_source = "api"  # Not inventory
        test_db_session.commit()

        job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.PENDING,
            collection=collection,
            bound_agent=agent,
        )

        service = JobCoordinatorService(test_db_session)

        result = service.claim_job(
            agent_id=agent.id,
            team_id=test_team.id,
            agent_capabilities=["local_filesystem"],
        )

        # Job claimed normally, not auto-completed
        assert result is not None
        assert result.server_completed is False
        assert result.job.status == JobStatus.ASSIGNED

    def test_no_server_detection_without_previous_result(
        self, test_db_session, test_team, test_user, create_agent, create_job, create_inventory_collection
    ):
        """Server-side detection is skipped when there's no previous result."""
        agent = create_agent(test_team, test_user)
        collection = create_inventory_collection(test_team, bound_agent=agent)

        job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.PENDING,
            collection=collection,
            bound_agent=agent,
        )

        service = JobCoordinatorService(test_db_session)

        result = service.claim_job(
            agent_id=agent.id,
            team_id=test_team.id,
            agent_capabilities=["local_filesystem"],
        )

        # Job claimed normally (no previous result to compare)
        assert result is not None
        assert result.server_completed is False
        assert result.job.status == JobStatus.ASSIGNED

    def test_server_detection_when_no_change(
        self, test_db_session, test_team, test_user, create_agent, create_job,
        create_inventory_collection, create_previous_result
    ):
        """Server detects no-change and auto-completes the job."""
        from backend.src.services.input_state_service import get_input_state_service
        from backend.src.services.config_loader import DatabaseConfigLoader

        agent = create_agent(test_team, test_user)

        # Create collection with inventory file info
        file_info = [
            {"key": "2020/IMG_001.dng", "size": 25000000, "last_modified": "2022-11-25T13:30:49.000Z"},
            {"key": "2020/IMG_001.xmp", "size": 4096, "last_modified": "2022-11-25T13:30:50.000Z"},
        ]
        collection = create_inventory_collection(test_team, bound_agent=agent, file_info=file_info)

        # Build config dict matching what server-side hash computation uses
        loader = DatabaseConfigLoader(team_id=test_team.id, db=test_db_session)
        config = {
            "photo_extensions": loader.photo_extensions,
            "metadata_extensions": loader.metadata_extensions,
            "camera_mappings": loader.camera_mappings,
            "processing_methods": loader.processing_methods,
            "require_sidecar": loader.require_sidecar,
        }

        # Compute the input state hash that matches the current state
        input_state_service = get_input_state_service()
        current_hash = input_state_service.compute_collection_input_state_hash(
            collection, config, "photostats"
        )

        # Create a previous result with the same hash
        create_previous_result(
            test_team, collection, "photostats", input_state_hash=current_hash
        )

        job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.PENDING,
            collection=collection,
            bound_agent=agent,
        )

        service = JobCoordinatorService(test_db_session)

        result = service.claim_job(
            agent_id=agent.id,
            team_id=test_team.id,
            agent_capabilities=["local_filesystem"],
        )

        # Job auto-completed by server
        assert result is not None
        assert result.server_completed is True
        assert result.job.status == JobStatus.COMPLETED

    def test_server_detection_when_files_changed(
        self, test_db_session, test_team, test_user, create_agent, create_job,
        create_inventory_collection, create_previous_result
    ):
        """Server detects change and returns job for agent execution."""
        agent = create_agent(test_team, test_user)

        # Create collection with new file info
        new_file_info = [
            {"key": "2020/IMG_001.dng", "size": 25000000, "last_modified": "2022-11-25T13:30:49.000Z"},
            {"key": "2020/IMG_001.xmp", "size": 4096, "last_modified": "2022-11-25T13:30:50.000Z"},
            {"key": "2020/IMG_002.dng", "size": 26000000, "last_modified": "2023-01-01T10:00:00.000Z"},  # New file
        ]
        collection = create_inventory_collection(test_team, bound_agent=agent, file_info=new_file_info)

        # Create a previous result with an old hash (different file list)
        create_previous_result(
            test_team, collection, "photostats", input_state_hash="old_hash_12345"
        )

        job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.PENDING,
            collection=collection,
            bound_agent=agent,
        )

        service = JobCoordinatorService(test_db_session)

        result = service.claim_job(
            agent_id=agent.id,
            team_id=test_team.id,
            agent_capabilities=["local_filesystem"],
        )

        # Job returned for agent execution (files changed)
        assert result is not None
        assert result.server_completed is False
        assert result.job.status == JobStatus.ASSIGNED

    def test_server_detection_preserves_previous_result_link(
        self, test_db_session, test_team, test_user, create_agent, create_job,
        create_inventory_collection, create_previous_result
    ):
        """Server-side auto-complete links to the previous result."""
        from backend.src.services.input_state_service import get_input_state_service
        from backend.src.services.config_loader import DatabaseConfigLoader
        from backend.src.models import AnalysisResult

        agent = create_agent(test_team, test_user)

        file_info = [
            {"key": "2020/IMG_001.dng", "size": 25000000, "last_modified": "2022-11-25T13:30:49.000Z"},
        ]
        collection = create_inventory_collection(test_team, bound_agent=agent, file_info=file_info)

        # Build config dict matching what server-side hash computation uses
        loader = DatabaseConfigLoader(team_id=test_team.id, db=test_db_session)
        config = {
            "photo_extensions": loader.photo_extensions,
            "metadata_extensions": loader.metadata_extensions,
            "camera_mappings": loader.camera_mappings,
            "processing_methods": loader.processing_methods,
            "require_sidecar": loader.require_sidecar,
        }

        # Compute matching hash
        input_state_service = get_input_state_service()
        current_hash = input_state_service.compute_collection_input_state_hash(
            collection, config, "photostats"
        )

        # Create previous result
        previous_result = create_previous_result(
            test_team, collection, "photostats", input_state_hash=current_hash
        )

        job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.PENDING,
            collection=collection,
            bound_agent=agent,
        )

        service = JobCoordinatorService(test_db_session)

        result = service.claim_job(
            agent_id=agent.id,
            team_id=test_team.id,
            agent_capabilities=["local_filesystem"],
        )

        # Job auto-completed
        assert result.server_completed is True

        # A new result was created that references previous or copies data
        test_db_session.refresh(result.job)
        assert result.job.result_id is not None

        # Get the new result
        new_result = test_db_session.query(AnalysisResult).filter(
            AnalysisResult.id == result.job.result_id
        ).first()
        assert new_result is not None
        # Results JSON should indicate server-side no-change
        assert new_result.results_json.get("_server_side_no_change") is True
