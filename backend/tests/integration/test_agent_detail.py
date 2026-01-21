"""
Integration tests for Agent Detail API.

Tests end-to-end flows for agent detail and job history:
- GET /api/agent/v1/{guid}/detail (get agent detail view)
- GET /api/agent/v1/{guid}/jobs (get agent job history)

Issue #90 - Distributed Agent Architecture (Phase 11)
Tasks: T165 - Integration tests for agent detail endpoint
"""

import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from backend.src.main import app
from backend.src.services.agent_service import AgentService
from backend.src.models.agent import AgentStatus
from backend.src.models.job import Job, JobStatus
from backend.src.models.collection import Collection, CollectionType, CollectionState


class TestAgentDetailEndpoint:
    """Integration tests for GET /api/agent/v1/{guid}/detail endpoint."""

    def test_get_agent_detail_basic(self, test_db_session, test_team, test_user, test_client):
        """Test getting basic agent detail."""
        service = AgentService(test_db_session)

        # Create an agent
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Detail Test Agent",
            hostname="detail-host.local",
            os_info="macOS 14.0",
            capabilities=["local_filesystem"],
            version="1.0.0"
        )
        test_db_session.commit()

        response = test_client.get(f"/api/agent/v1/{reg_result.agent.guid}/detail")

        assert response.status_code == 200
        data = response.json()
        assert data["guid"] == reg_result.agent.guid
        assert data["name"] == "Detail Test Agent"
        assert data["hostname"] == "detail-host.local"
        assert data["bound_collections_count"] == 0
        assert data["total_jobs_completed"] == 0
        assert data["total_jobs_failed"] == 0
        assert data["recent_jobs"] == []

    def test_get_agent_detail_with_metrics(self, test_db_session, test_team, test_user, test_client):
        """Test agent detail includes metrics when available."""
        service = AgentService(test_db_session)

        # Create an agent
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Metrics Test Agent",
            hostname="metrics-host.local",
            os_info="macOS 14.0",
        )

        # Add metrics via heartbeat
        service.process_heartbeat(
            agent=reg_result.agent,
            status=AgentStatus.ONLINE,
            metrics={
                "cpu_percent": 45.5,
                "memory_percent": 62.3,
                "disk_free_gb": 128.7
            }
        )
        test_db_session.commit()

        response = test_client.get(f"/api/agent/v1/{reg_result.agent.guid}/detail")

        if response.status_code != 200:
            print(f"Response: {response.json()}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
        data = response.json()
        assert data["metrics"] is not None
        assert data["metrics"]["cpu_percent"] == 45.5
        assert data["metrics"]["memory_percent"] == 62.3
        assert data["metrics"]["disk_free_gb"] == 128.7

    def test_get_agent_detail_with_job_stats(
        self, test_db_session, test_team, test_user, test_client
    ):
        """Test agent detail includes job statistics."""
        import tempfile
        service = AgentService(test_db_session)

        # Create an agent
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Job Stats Agent",
        )
        test_db_session.commit()

        # Create completed and failed jobs
        for i in range(5):
            job = Job(
                team_id=test_team.id,
                tool="photostats",
                status=JobStatus.COMPLETED,
                agent_id=reg_result.agent.id,
                required_capabilities_json="[]",
            )
            test_db_session.add(job)

        for i in range(2):
            job = Job(
                team_id=test_team.id,
                tool="photopairing",
                status=JobStatus.FAILED,
                agent_id=reg_result.agent.id,
                error_message="Test failure",
                required_capabilities_json="[]",
            )
            test_db_session.add(job)
        test_db_session.commit()

        response = test_client.get(f"/api/agent/v1/{reg_result.agent.guid}/detail")

        assert response.status_code == 200
        data = response.json()
        assert data["total_jobs_completed"] == 5
        assert data["total_jobs_failed"] == 2

    def test_get_agent_detail_with_bound_collections(
        self, test_db_session, test_team, test_user, test_client
    ):
        """Test agent detail includes bound collections count."""
        import tempfile
        service = AgentService(test_db_session)

        # Create an agent
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Collection Agent",
        )
        test_db_session.commit()

        # Create bound collections
        with tempfile.TemporaryDirectory() as temp_dir:
            for i in range(3):
                collection = Collection(
                    name=f"Bound Collection {i+1}",
                    type=CollectionType.LOCAL,
                    location=f"{temp_dir}/collection{i}",
                    team_id=test_team.id,
                    state=CollectionState.LIVE,
                    bound_agent_id=reg_result.agent.id,
                )
                test_db_session.add(collection)
            test_db_session.commit()

            response = test_client.get(f"/api/agent/v1/{reg_result.agent.guid}/detail")

        assert response.status_code == 200
        data = response.json()
        assert data["bound_collections_count"] == 3

    def test_get_agent_detail_with_recent_jobs(
        self, test_db_session, test_team, test_user, test_client
    ):
        """Test agent detail includes recent job history."""
        import tempfile
        service = AgentService(test_db_session)

        # Create an agent
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Recent Jobs Agent",
        )
        test_db_session.commit()

        # Create 15 jobs (more than the 10 limit)
        for i in range(15):
            job = Job(
                team_id=test_team.id,
                tool="photostats",
                status=JobStatus.COMPLETED,
                agent_id=reg_result.agent.id,
                required_capabilities_json="[]",
            )
            test_db_session.add(job)
        test_db_session.commit()

        response = test_client.get(f"/api/agent/v1/{reg_result.agent.guid}/detail")

        assert response.status_code == 200
        data = response.json()
        # Should only return last 10 jobs
        assert len(data["recent_jobs"]) == 10

    def test_get_agent_detail_not_found(self, test_client):
        """Test getting detail for non-existent agent."""
        response = test_client.get("/api/agent/v1/agt_nonexistent12345678/detail")

        assert response.status_code == 404
        assert response.json()["detail"] == "Agent not found"

    def test_get_agent_detail_requires_auth(self):
        """Test that getting agent detail requires authentication."""
        with TestClient(app) as client:
            response = client.get("/api/agent/v1/agt_test12345678901234/detail")

        assert response.status_code == 401


class TestAgentJobHistoryEndpoint:
    """Integration tests for GET /api/agent/v1/{guid}/jobs endpoint."""

    def test_get_agent_jobs_empty(self, test_db_session, test_team, test_user, test_client):
        """Test getting job history when no jobs exist."""
        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="No Jobs Agent",
        )
        test_db_session.commit()

        response = test_client.get(f"/api/agent/v1/{reg_result.agent.guid}/jobs")

        assert response.status_code == 200
        data = response.json()
        assert data["jobs"] == []
        assert data["total_count"] == 0
        assert data["offset"] == 0
        assert data["limit"] == 20

    def test_get_agent_jobs_with_jobs(self, test_db_session, test_team, test_user, test_client):
        """Test getting job history with jobs."""
        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Jobs Agent",
        )
        test_db_session.commit()

        # Create some jobs
        for i in range(5):
            job = Job(
                team_id=test_team.id,
                tool="photostats" if i % 2 == 0 else "photopairing",
                status=JobStatus.COMPLETED if i < 3 else JobStatus.FAILED,
                agent_id=reg_result.agent.id,
                error_message="Test error" if i >= 3 else None,
                required_capabilities_json="[]",
            )
            test_db_session.add(job)
        test_db_session.commit()

        response = test_client.get(f"/api/agent/v1/{reg_result.agent.guid}/jobs")

        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 5
        assert data["total_count"] == 5

        # Check job structure
        job_data = data["jobs"][0]
        assert "guid" in job_data
        assert "tool" in job_data
        assert "status" in job_data

    def test_get_agent_jobs_pagination(self, test_db_session, test_team, test_user, test_client):
        """Test job history pagination."""
        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Pagination Agent",
        )
        test_db_session.commit()

        # Create 30 jobs
        for i in range(30):
            job = Job(
                team_id=test_team.id,
                tool="photostats",
                status=JobStatus.COMPLETED,
                agent_id=reg_result.agent.id,
                required_capabilities_json="[]",
            )
            test_db_session.add(job)
        test_db_session.commit()

        # Get first page
        response = test_client.get(f"/api/agent/v1/{reg_result.agent.guid}/jobs?offset=0&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 10
        assert data["total_count"] == 30
        assert data["offset"] == 0
        assert data["limit"] == 10

        # Get second page
        response = test_client.get(f"/api/agent/v1/{reg_result.agent.guid}/jobs?offset=10&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 10
        assert data["total_count"] == 30
        assert data["offset"] == 10

    def test_get_agent_jobs_limit_capped(self, test_db_session, test_team, test_user, test_client):
        """Test that job history limit is capped at 100."""
        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Limit Cap Agent",
        )
        test_db_session.commit()

        response = test_client.get(f"/api/agent/v1/{reg_result.agent.guid}/jobs?limit=500")

        assert response.status_code == 200
        data = response.json()
        # Limit should be capped to 100
        assert data["limit"] == 100

    def test_get_agent_jobs_not_found(self, test_client):
        """Test getting jobs for non-existent agent."""
        response = test_client.get("/api/agent/v1/agt_nonexistent12345678/jobs")

        assert response.status_code == 404
        assert response.json()["detail"] == "Agent not found"

    def test_get_agent_jobs_requires_auth(self):
        """Test that getting agent jobs requires authentication."""
        with TestClient(app) as client:
            response = client.get("/api/agent/v1/agt_test12345678901234/jobs")

        assert response.status_code == 401


class TestAgentMetricsInHeartbeat:
    """Integration tests for metrics in heartbeat endpoint."""

    def test_heartbeat_with_metrics(self, test_db_session, test_team, test_user, test_client):
        """Test that heartbeat stores metrics correctly."""
        service = AgentService(test_db_session)

        # Create and register an agent
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Heartbeat Metrics Agent",
        )
        test_db_session.commit()

        # Send heartbeat with metrics (using agent API key with Bearer auth)
        agent_client = TestClient(app)
        agent_client.headers["Authorization"] = f"Bearer {reg_result.api_key}"

        response = agent_client.post(
            "/api/agent/v1/heartbeat",
            json={
                "status": "online",
                "metrics": {
                    "cpu_percent": 35.5,
                    "memory_percent": 72.1,
                    "disk_free_gb": 256.0
                }
            }
        )

        assert response.status_code == 200

        # Verify metrics were stored
        test_db_session.refresh(reg_result.agent)
        assert reg_result.agent.metrics is not None
        assert reg_result.agent.metrics["cpu_percent"] == 35.5
        assert reg_result.agent.metrics["memory_percent"] == 72.1
        assert reg_result.agent.metrics["disk_free_gb"] == 256.0
        assert "metrics_updated_at" in reg_result.agent.metrics

    def test_heartbeat_metrics_in_get_response(
        self, test_db_session, test_team, test_user, test_client
    ):
        """Test that metrics are included in GET agent response."""
        service = AgentService(test_db_session)

        # Create an agent with metrics
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Response Metrics Agent",
        )

        service.process_heartbeat(
            agent=reg_result.agent,
            status=AgentStatus.ONLINE,
            metrics={"cpu_percent": 50.0, "memory_percent": 60.0}
        )
        test_db_session.commit()

        # GET the agent
        response = test_client.get(f"/api/agent/v1/{reg_result.agent.guid}")

        assert response.status_code == 200
        data = response.json()
        assert data["metrics"] is not None
        assert data["metrics"]["cpu_percent"] == 50.0
        assert data["metrics"]["memory_percent"] == 60.0
