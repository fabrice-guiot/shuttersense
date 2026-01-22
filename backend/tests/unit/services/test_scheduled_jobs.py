"""
Unit tests for scheduled job creation (auto-refresh scheduling).

Tests the automatic creation of SCHEDULED jobs when analysis jobs complete,
based on collection TTL configuration from team settings.

Phase 13: User Story 11 - Automatic Collection Refresh Scheduling
Tasks: T182
"""

import json
import pytest
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from backend.src.models.agent import AgentStatus
from backend.src.models.job import Job, JobStatus
from backend.src.models.collection import Collection, CollectionType, CollectionState
from backend.src.services.job_coordinator_service import (
    JobCoordinatorService,
    JobCompletionData,
)


# ============================================================================
# Fixtures (copied from test_job_coordinator.py for isolation)
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

    return _create_agent


@pytest.fixture
def create_collection(test_db_session):
    """Factory fixture to create test collections."""
    def _create_collection(team, bound_agent=None, state=CollectionState.LIVE):
        # Create a temp directory for the collection
        temp_dir = tempfile.mkdtemp()

        collection = Collection(
            team_id=team.id,
            name="Test Collection",
            location=temp_dir,
            type=CollectionType.LOCAL,
            state=state,
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


# ============================================================================
# Test Classes
# ============================================================================


class TestScheduledJobCreation:
    """Tests for automatic scheduled job creation on job completion."""

    def test_creates_scheduled_job_on_completion_with_ttl(
        self, test_db_session, test_team, test_user, create_agent, create_collection, create_job
    ):
        """When a job completes and collection has TTL, a SCHEDULED job is created."""
        agent = create_agent(test_team, test_user)
        collection = create_collection(test_team, bound_agent=agent)

        # Create a running job
        job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.ASSIGNED,
            collection=collection,
            bound_agent=agent,
        )
        job.agent_id = agent.id
        job.assigned_at = datetime.utcnow()
        test_db_session.commit()

        # Mock the config service to return TTL
        mock_config_service = MagicMock()
        mock_config_service.get_collection_ttl.return_value = {
            'live': 3600,  # 1 hour
            'closed': 86400,
            'archived': 604800,
        }

        # Complete the job with TTL scheduling enabled
        service = JobCoordinatorService(test_db_session, config_service=mock_config_service)

        completion_data = JobCompletionData(
            results={"files_scanned": 100, "issues_found": 5, "total_files": 100},
            files_scanned=100,
            issues_found=5,
        )

        completed_job = service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        # Verify original job completed
        assert completed_job.status == JobStatus.COMPLETED

        # Verify scheduled job was created
        scheduled_job = test_db_session.query(Job).filter(
            Job.collection_id == collection.id,
            Job.tool == "photostats",
            Job.status == JobStatus.SCHEDULED,
        ).first()

        assert scheduled_job is not None
        assert scheduled_job.parent_job_id == job.id
        assert scheduled_job.scheduled_for is not None
        # Should be scheduled ~1 hour from now (with small tolerance)
        expected_time = datetime.utcnow() + timedelta(seconds=3600)
        assert abs((scheduled_job.scheduled_for - expected_time).total_seconds()) < 5

    def test_no_scheduled_job_without_ttl(
        self, test_db_session, test_team, test_user, create_agent, create_collection, create_job
    ):
        """When collection has no TTL (0), no SCHEDULED job is created."""
        agent = create_agent(test_team, test_user)
        collection = create_collection(test_team, bound_agent=agent)

        job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.ASSIGNED,
            collection=collection,
        )
        job.agent_id = agent.id
        job.assigned_at = datetime.utcnow()
        test_db_session.commit()

        # Mock config service to return 0 TTL (disabled)
        mock_config_service = MagicMock()
        mock_config_service.get_collection_ttl.return_value = {
            'live': 0,  # Disabled
            'closed': 0,
            'archived': 0,
        }

        service = JobCoordinatorService(test_db_session, config_service=mock_config_service)

        completion_data = JobCompletionData(
            results={"files_scanned": 100, "total_files": 100},
            files_scanned=100,
        )

        service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        # Verify no scheduled job was created
        scheduled_job = test_db_session.query(Job).filter(
            Job.collection_id == collection.id,
            Job.status == JobStatus.SCHEDULED,
        ).first()

        assert scheduled_job is None

    def test_no_scheduled_job_for_collection_test(
        self, test_db_session, test_team, test_user, create_agent, create_collection, create_job
    ):
        """Collection_test jobs should not create scheduled follow-up jobs."""
        agent = create_agent(test_team, test_user)
        collection = create_collection(test_team, bound_agent=agent)

        # Create a collection_test job
        job = create_job(
            test_team,
            tool="collection_test",
            status=JobStatus.ASSIGNED,
            collection=collection,
            bound_agent=agent,
        )
        job.agent_id = agent.id
        job.assigned_at = datetime.utcnow()
        test_db_session.commit()

        # Mock config service with TTL
        mock_config_service = MagicMock()
        mock_config_service.get_collection_ttl.return_value = {
            'live': 3600,
            'closed': 86400,
            'archived': 604800,
        }

        service = JobCoordinatorService(test_db_session, config_service=mock_config_service)

        completion_data = JobCompletionData(
            results={"success": True, "message": "Path accessible"},
        )

        service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        # Verify no scheduled job was created for collection_test
        scheduled_job = test_db_session.query(Job).filter(
            Job.collection_id == collection.id,
            Job.status == JobStatus.SCHEDULED,
        ).first()

        assert scheduled_job is None

    def test_scheduled_job_uses_correct_state_ttl(
        self, test_db_session, test_team, test_user, create_agent, create_collection, create_job
    ):
        """Scheduled job uses TTL for collection's current state."""
        agent = create_agent(test_team, test_user)

        # Create ARCHIVED collection (longest TTL)
        collection = create_collection(
            test_team,
            bound_agent=agent,
            state=CollectionState.ARCHIVED,
        )

        job = create_job(
            test_team,
            tool="photo_pairing",
            status=JobStatus.ASSIGNED,
            collection=collection,
        )
        job.agent_id = agent.id
        job.assigned_at = datetime.utcnow()
        test_db_session.commit()

        # Mock config service with different TTLs per state
        mock_config_service = MagicMock()
        mock_config_service.get_collection_ttl.return_value = {
            'live': 3600,      # 1 hour
            'closed': 86400,   # 24 hours
            'archived': 604800,  # 7 days
        }

        service = JobCoordinatorService(test_db_session, config_service=mock_config_service)

        completion_data = JobCompletionData(
            results={"groups": 50, "image_count": 100},
            files_scanned=100,
        )

        service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        # Verify scheduled job uses archived TTL (7 days)
        scheduled_job = test_db_session.query(Job).filter(
            Job.collection_id == collection.id,
            Job.status == JobStatus.SCHEDULED,
        ).first()

        assert scheduled_job is not None
        expected_time = datetime.utcnow() + timedelta(seconds=604800)
        assert abs((scheduled_job.scheduled_for - expected_time).total_seconds()) < 5


class TestScheduledJobUniqueness:
    """Tests for unique scheduled job constraint per (collection, tool)."""

    def test_no_duplicate_scheduled_job(
        self, test_db_session, test_team, test_user, create_agent, create_collection, create_job
    ):
        """Completing a job doesn't create duplicate if SCHEDULED job exists."""
        agent = create_agent(test_team, test_user)
        collection = create_collection(test_team, bound_agent=agent)

        # Create an existing scheduled job
        existing_scheduled = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.SCHEDULED,
            scheduled_for=datetime.utcnow() + timedelta(hours=2),
            required_capabilities_json=json.dumps([]),  # SQLite needs JSON string
        )
        test_db_session.add(existing_scheduled)

        # Create a completing job
        job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.ASSIGNED,
            collection=collection,
        )
        job.agent_id = agent.id
        job.assigned_at = datetime.utcnow()
        test_db_session.commit()

        mock_config_service = MagicMock()
        mock_config_service.get_collection_ttl.return_value = {'live': 3600}

        service = JobCoordinatorService(test_db_session, config_service=mock_config_service)

        completion_data = JobCompletionData(
            results={"files_scanned": 100, "total_files": 100},
            files_scanned=100,
        )

        service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        # Verify only one scheduled job exists
        scheduled_count = test_db_session.query(Job).filter(
            Job.collection_id == collection.id,
            Job.tool == "photostats",
            Job.status == JobStatus.SCHEDULED,
        ).count()

        assert scheduled_count == 1

    def test_different_tools_can_have_scheduled_jobs(
        self, test_db_session, test_team, test_user, create_agent, create_collection, create_job
    ):
        """Different tools on same collection can each have scheduled jobs."""
        agent = create_agent(test_team, test_user)
        collection = create_collection(test_team, bound_agent=agent)

        # Create scheduled job for photostats
        photostats_scheduled = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.SCHEDULED,
            scheduled_for=datetime.utcnow() + timedelta(hours=1),
            required_capabilities_json=json.dumps([]),  # SQLite needs JSON string
        )
        test_db_session.add(photostats_scheduled)

        # Create completing job for photo_pairing
        job = create_job(
            test_team,
            tool="photo_pairing",
            status=JobStatus.ASSIGNED,
            collection=collection,
        )
        job.agent_id = agent.id
        job.assigned_at = datetime.utcnow()
        test_db_session.commit()

        mock_config_service = MagicMock()
        mock_config_service.get_collection_ttl.return_value = {'live': 3600}

        service = JobCoordinatorService(test_db_session, config_service=mock_config_service)

        completion_data = JobCompletionData(
            results={"groups": 50, "image_count": 100},
            files_scanned=100,
        )

        service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        # Verify both tools have scheduled jobs
        photostats_count = test_db_session.query(Job).filter(
            Job.collection_id == collection.id,
            Job.tool == "photostats",
            Job.status == JobStatus.SCHEDULED,
        ).count()

        photo_pairing_count = test_db_session.query(Job).filter(
            Job.collection_id == collection.id,
            Job.tool == "photo_pairing",
            Job.status == JobStatus.SCHEDULED,
        ).count()

        assert photostats_count == 1
        assert photo_pairing_count == 1


class TestScheduledJobCancellation:
    """Tests for scheduled job cancellation on manual refresh."""

    def test_manual_job_cancels_scheduled(
        self, test_db_session, test_team, test_user, create_collection
    ):
        """Creating a manual job cancels existing scheduled job for same tool."""
        from backend.src.services.tool_service import ToolService
        from backend.src.schemas.tools import ToolType

        collection = create_collection(test_team)

        # Create existing scheduled job
        scheduled_job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.SCHEDULED,
            scheduled_for=datetime.utcnow() + timedelta(hours=1),
            required_capabilities_json=json.dumps([]),  # SQLite needs JSON string
        )
        test_db_session.add(scheduled_job)
        test_db_session.commit()

        # Create new manual job via ToolService
        service = ToolService(test_db_session)
        new_job = service.run_tool(
            tool=ToolType.PHOTOSTATS,
            collection_id=collection.id,
        )

        # Verify scheduled job was cancelled
        test_db_session.refresh(scheduled_job)
        assert scheduled_job.status == JobStatus.CANCELLED

        # Verify new job is pending (queued)
        assert new_job.status.value == "queued"

    def test_manual_job_only_cancels_same_tool_scheduled(
        self, test_db_session, test_team, test_user, create_collection
    ):
        """Manual job only cancels scheduled job for the same tool."""
        from backend.src.services.tool_service import ToolService
        from backend.src.schemas.tools import ToolType

        collection = create_collection(test_team)

        # Create scheduled job for photo_pairing
        scheduled_job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photo_pairing",
            status=JobStatus.SCHEDULED,
            scheduled_for=datetime.utcnow() + timedelta(hours=1),
            required_capabilities_json=json.dumps([]),  # SQLite needs JSON string
        )
        test_db_session.add(scheduled_job)
        test_db_session.commit()

        # Create manual job for photostats (different tool)
        service = ToolService(test_db_session)
        service.run_tool(
            tool=ToolType.PHOTOSTATS,
            collection_id=collection.id,
        )

        # Verify photo_pairing scheduled job is NOT cancelled
        test_db_session.refresh(scheduled_job)
        assert scheduled_job.status == JobStatus.SCHEDULED


class TestScheduledJobInheritance:
    """Tests for scheduled job inheritance from parent job."""

    def test_scheduled_job_inherits_binding(
        self, test_db_session, test_team, test_user, create_agent, create_collection, create_job
    ):
        """Scheduled job inherits bound_agent_id from parent job's collection."""
        agent = create_agent(test_team, test_user)

        # Collection bound to agent
        collection = create_collection(test_team, bound_agent=agent)

        job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.ASSIGNED,
            collection=collection,
            bound_agent=agent,
        )
        job.agent_id = agent.id
        job.assigned_at = datetime.utcnow()
        test_db_session.commit()

        mock_config_service = MagicMock()
        mock_config_service.get_collection_ttl.return_value = {'live': 3600}

        service = JobCoordinatorService(test_db_session, config_service=mock_config_service)

        completion_data = JobCompletionData(
            results={"files_scanned": 100, "total_files": 100},
            files_scanned=100,
        )

        service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        # Verify scheduled job has same bound_agent_id
        scheduled_job = test_db_session.query(Job).filter(
            Job.collection_id == collection.id,
            Job.status == JobStatus.SCHEDULED,
        ).first()

        assert scheduled_job is not None
        assert scheduled_job.bound_agent_id == agent.id

    def test_scheduled_job_inherits_capabilities(
        self, test_db_session, test_team, test_user, create_agent, create_collection, create_job
    ):
        """Scheduled job inherits required_capabilities from parent job."""
        agent = create_agent(test_team, test_user)
        collection = create_collection(test_team, bound_agent=agent)

        job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.ASSIGNED,
            collection=collection,
        )
        job.agent_id = agent.id
        job.assigned_at = datetime.utcnow()
        job.required_capabilities = ["photostats", "local_filesystem"]
        test_db_session.commit()

        mock_config_service = MagicMock()
        mock_config_service.get_collection_ttl.return_value = {'live': 3600}

        service = JobCoordinatorService(test_db_session, config_service=mock_config_service)

        completion_data = JobCompletionData(
            results={"files_scanned": 100, "total_files": 100},
            files_scanned=100,
        )

        service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        # Verify scheduled job has same capabilities
        scheduled_job = test_db_session.query(Job).filter(
            Job.collection_id == collection.id,
            Job.status == JobStatus.SCHEDULED,
        ).first()

        assert scheduled_job is not None
        assert scheduled_job.required_capabilities == ["photostats", "local_filesystem"]
