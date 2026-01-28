"""
Integration tests for POST /api/agent/v1/jobs/claim endpoint.

Tests job claiming via the agent API including:
- Successful job claiming
- No jobs available (204)
- Capability matching
- Bound agent routing
- Tenant isolation
- Server-side auto-completion loop (Phase 7)

Issue #90 - Distributed Agent Architecture (Phase 5)
Task: T072

Issue #107 - Bucket Inventory Import (Phase 7)
Task: T138
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from backend.src.models.job import Job, JobStatus
from backend.src.models.agent import Agent, AgentStatus


class TestJobClaimEndpoint:
    """Integration tests for POST /api/agent/v1/jobs/claim."""

    def test_claim_job_success(
        self,
        agent_client,
        test_db_session,
        test_team,
        create_job,
    ):
        """Successfully claim an available job."""
        # Note: agent_client fixture creates and authenticates as an agent
        job = create_job(test_team, tool="photostats", status=JobStatus.PENDING)

        response = agent_client.post("/api/agent/v1/jobs/claim")

        assert response.status_code == 200
        data = response.json()
        assert data["guid"] == job.guid
        assert data["tool"] == "photostats"
        assert "signing_secret" in data
        assert len(data["signing_secret"]) > 0

        # Verify job was updated in DB
        test_db_session.refresh(job)
        assert job.status == JobStatus.ASSIGNED
        assert job.agent_id is not None  # Job assigned to the authenticated agent

    def test_claim_job_no_jobs_available(
        self,
        agent_client,
        test_db_session,
        test_team,
    ):
        """Returns 204 when no jobs are available."""
        # agent_client fixture already creates the agent

        response = agent_client.post("/api/agent/v1/jobs/claim")

        assert response.status_code == 204
        assert response.content == b""

    def test_claim_job_returns_collection_info(
        self,
        agent_client,
        test_db_session,
        test_team,
        create_job,
        sample_collection,
    ):
        """Job claim response includes collection info."""
        # agent_client fixture creates the agent
        collection = sample_collection(location="/photos/vacation")
        job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.PENDING,
            collection=collection,
        )

        response = agent_client.post("/api/agent/v1/jobs/claim")

        assert response.status_code == 200
        data = response.json()
        assert data["collection_guid"] == collection.guid
        assert data["collection_path"] == "/photos/vacation"

    def test_claim_job_bound_agent_only(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_user,
        test_agent,
        create_agent,
        create_job,
    ):
        """Bound jobs are only claimable by the bound agent."""
        # agent_client is authenticated as test_agent
        other_agent = create_agent(test_team, test_user, name="Other Agent")

        # Create job bound to other_agent (not the authenticated test_agent)
        create_job(
            test_team,
            tool="photostats",
            status=JobStatus.PENDING,
            bound_agent=other_agent,
        )

        # agent_client is authenticated as test_agent, should not get bound job
        response = agent_client.post("/api/agent/v1/jobs/claim")

        # Should return 204 because the only job is bound to a different agent
        assert response.status_code == 204

    def test_claim_job_priority_order(
        self,
        agent_client,
        test_db_session,
        test_team,
        create_job,
    ):
        """Jobs are claimed in priority order (highest first)."""
        # agent_client fixture creates the agent

        # Create jobs with different priorities
        create_job(test_team, tool="photostats", priority=0)  # low priority
        high_job = create_job(test_team, tool="photostats", priority=10)

        response = agent_client.post("/api/agent/v1/jobs/claim")

        assert response.status_code == 200
        data = response.json()
        # Should claim high priority job first
        assert data["guid"] == high_job.guid

    def test_claim_job_scheduled_not_due(
        self,
        agent_client,
        test_db_session,
        test_team,
        create_job,
    ):
        """Scheduled jobs are not claimable before their time."""
        # agent_client fixture creates the agent

        # Create job scheduled for future
        create_job(
            test_team,
            tool="photostats",
            status=JobStatus.SCHEDULED,
            scheduled_for=datetime.utcnow() + timedelta(hours=1),
        )

        response = agent_client.post("/api/agent/v1/jobs/claim")

        assert response.status_code == 204

    def test_claim_job_scheduled_due(
        self,
        agent_client,
        test_db_session,
        test_team,
        create_job,
    ):
        """Scheduled jobs are claimable after their scheduled time."""
        # agent_client fixture creates the agent

        # Create job scheduled for past
        job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.SCHEDULED,
            scheduled_for=datetime.utcnow() - timedelta(minutes=5),
        )

        response = agent_client.post("/api/agent/v1/jobs/claim")

        assert response.status_code == 200
        data = response.json()
        assert data["guid"] == job.guid

    def test_claim_job_requires_online_agent(
        self,
        offline_agent_client,
        test_db_session,
        test_team,
        create_job,
    ):
        """Agent must be online to claim jobs."""
        create_job(test_team, tool="photostats", status=JobStatus.PENDING)

        response = offline_agent_client.post("/api/agent/v1/jobs/claim")

        assert response.status_code == 403
        assert "must be online" in response.json()["detail"].lower()

    # =========================================================================
    # Phase 7: Server-Side Auto-Completion Loop (Issue #107, T138)
    # =========================================================================

    def test_claim_job_returns_next_after_auto_completion(
        self,
        agent_client,
        test_db_session,
        test_team,
        create_job,
        create_inventory_collection,
        create_previous_result,
    ):
        """Auto-completed job is skipped and next available job is returned.

        When the endpoint auto-completes a job via server-side no-change
        detection, it loops and returns the next claimable job to the agent.

        Issue #107 - Phase 7 (Server-Side No-Change Detection)
        Task: T138 [US7]
        """
        from backend.src.services.input_state_service import get_input_state_service
        from backend.src.services.config_loader import DatabaseConfigLoader

        # Create inventory collection with file info
        file_info = [
            {"key": "2020/IMG_001.dng", "size": 25000000, "last_modified": "2022-11-25T13:30:49.000Z"},
            {"key": "2020/IMG_001.xmp", "size": 4096, "last_modified": "2022-11-25T13:30:50.000Z"},
        ]
        inventory_collection = create_inventory_collection(
            test_team, file_info=file_info
        )

        # Build config dict matching what server-side hash computation uses
        # (same structure as _get_tool_config in JobCoordinatorService)
        loader = DatabaseConfigLoader(team_id=test_team.id, db=test_db_session)
        config = {
            "photo_extensions": loader.photo_extensions,
            "metadata_extensions": loader.metadata_extensions,
            "camera_mappings": loader.camera_mappings,
            "processing_methods": loader.processing_methods,
            "require_sidecar": loader.require_sidecar,
        }

        # Compute hash matching current state using same config as server
        input_state_service = get_input_state_service()
        current_hash = input_state_service.compute_collection_input_state_hash(
            inventory_collection, config, "photostats"
        )

        # Create previous result with matching hash → triggers auto-completion
        create_previous_result(
            test_team, inventory_collection, "photostats",
            input_state_hash=current_hash
        )

        # Job 1: Inventory collection → will be auto-completed (created first = claimed first)
        auto_job = create_job(
            test_team, tool="photostats", collection=inventory_collection
        )

        # Job 2: Normal job (no inventory collection) → should be returned to agent
        normal_job = create_job(test_team, tool="photostats")

        response = agent_client.post("/api/agent/v1/jobs/claim")

        assert response.status_code == 200
        data = response.json()
        # Should receive the normal job (auto-completed job was skipped)
        assert data["guid"] == normal_job.guid

        # Verify the first job was auto-completed by the server
        test_db_session.refresh(auto_job)
        assert auto_job.status == JobStatus.COMPLETED

        # Verify the second job was assigned to the agent
        test_db_session.refresh(normal_job)
        assert normal_job.status == JobStatus.ASSIGNED

    def test_claim_job_204_when_all_auto_completed(
        self,
        agent_client,
        test_db_session,
        test_team,
        create_job,
        create_inventory_collection,
        create_previous_result,
    ):
        """Returns 204 when all claimable jobs are auto-completed server-side.

        When every available job triggers server-side no-change detection and
        no more jobs remain, the endpoint returns 204 No Content.

        Issue #107 - Phase 7 (Server-Side No-Change Detection)
        Task: T138 [US7]
        """
        from backend.src.services.input_state_service import get_input_state_service
        from backend.src.services.config_loader import DatabaseConfigLoader

        file_info = [
            {"key": "2020/IMG_001.dng", "size": 25000000, "last_modified": "2022-11-25T13:30:49.000Z"},
        ]
        collection = create_inventory_collection(test_team, file_info=file_info)

        # Build config dict matching what server-side hash computation uses
        loader = DatabaseConfigLoader(team_id=test_team.id, db=test_db_session)
        config = {
            "photo_extensions": loader.photo_extensions,
            "metadata_extensions": loader.metadata_extensions,
            "camera_mappings": loader.camera_mappings,
            "processing_methods": loader.processing_methods,
            "require_sidecar": loader.require_sidecar,
        }

        input_state_service = get_input_state_service()
        current_hash = input_state_service.compute_collection_input_state_hash(
            collection, config, "photostats"
        )

        create_previous_result(
            test_team, collection, "photostats",
            input_state_hash=current_hash
        )

        # Only inventory job → auto-completed, nothing left
        auto_job = create_job(
            test_team, tool="photostats", collection=collection
        )

        response = agent_client.post("/api/agent/v1/jobs/claim")

        assert response.status_code == 204
        assert response.content == b""

        # Verify the job was auto-completed
        test_db_session.refresh(auto_job)
        assert auto_job.status == JobStatus.COMPLETED


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def create_agent(test_db_session):
    """Factory fixture to create and register test agents."""
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
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)
        return job

    return _create_job


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

    # Use the test_agent created by the fixture
    agent = test_agent

    # Create agent context
    agent_ctx = AgentContext(
        agent_id=agent.id,
        agent_guid=agent.guid,
        team_id=test_team.id,
        team_guid=test_team.guid,
        agent_name=agent.name,
        status=AgentStatus.ONLINE,
    )

    # Override dependencies
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
def offline_agent_client(
    test_db_session,
    test_session_factory,
    test_team,
    test_user,
    test_websocket_manager,
):
    """Create a test client authenticated as an offline agent."""
    from fastapi.testclient import TestClient
    from fastapi import HTTPException
    from backend.src.main import app
    from backend.src.api.agent.dependencies import AgentContext

    # Create agent context (offline)
    agent_ctx = AgentContext(
        agent_id=1,
        agent_guid="agt_test123456789012345678901",
        team_id=test_team.id,
        team_guid=test_team.guid,
        agent_name="Offline Agent",
        status=AgentStatus.OFFLINE,
    )

    def get_test_db():
        try:
            yield test_db_session
        finally:
            pass

    def get_test_agent_context():
        return agent_ctx

    def get_test_online_agent():
        raise HTTPException(status_code=403, detail="Agent must be online to perform this action")

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


# ============================================================================
# Phase 7: Server-Side Auto-Completion Fixtures (Issue #107, T138)
# ============================================================================

@pytest.fixture
def create_inventory_collection(test_db_session):
    """Factory fixture to create collections with inventory file info."""
    from backend.src.models.collection import Collection, CollectionType, CollectionState

    def _create(team, file_info=None, bound_agent=None):
        collection = Collection(
            team_id=team.id,
            name="Inventory Collection",
            location="/photos/inventory",
            type=CollectionType.LOCAL,
            state=CollectionState.LIVE,
            file_info=file_info or [
                {"key": "2020/IMG_001.dng", "size": 25000000, "last_modified": "2022-11-25T13:30:49.000Z"},
                {"key": "2020/IMG_001.xmp", "size": 4096, "last_modified": "2022-11-25T13:30:50.000Z"},
            ],
            file_info_source="inventory",
            bound_agent_id=bound_agent.id if bound_agent else None,
        )
        test_db_session.add(collection)
        test_db_session.commit()
        test_db_session.refresh(collection)
        return collection

    return _create


@pytest.fixture
def create_previous_result(test_db_session):
    """Factory fixture to create a previous AnalysisResult with input_state_hash."""
    from backend.src.models.analysis_result import AnalysisResult
    from backend.src.models import ResultStatus

    def _create(team, collection, tool, input_state_hash):
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
