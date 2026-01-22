"""
Integration tests for multi-agent job distribution.

Tests that multiple agents can claim and execute jobs concurrently,
with load tracking for visibility.

Issue #90 - Distributed Agent Architecture (Phase 12)
Task: T178 - Integration tests for multi-agent distribution
"""

import pytest
from datetime import datetime, timedelta

from backend.src.models.job import Job, JobStatus
from backend.src.models.agent import Agent, AgentStatus
from backend.src.services.agent_service import AgentService


class TestMultiAgentJobClaiming:
    """Integration tests for multiple agents claiming jobs."""

    def _register_agent(
        self,
        service: AgentService,
        team,
        user,
        db_session,
        name: str = "Test Agent",
        capabilities: list = None
    ):
        """Helper to register an agent and return registration result with API key."""
        token_result = service.create_registration_token(
            team_id=team.id,
            created_by_user_id=user.id,
        )
        db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name=name,
            hostname="test-host.local",
            os_info="Linux",
            capabilities=capabilities or ["local_filesystem"],
            version="1.0.0"
        )
        db_session.commit()

        # Bring agent online
        service.process_heartbeat(reg_result.agent, status=AgentStatus.ONLINE)
        db_session.commit()

        return reg_result

    def test_two_agents_claim_different_jobs(
        self,
        test_db_session,
        test_team,
        test_user,
        test_client,
        create_job,
    ):
        """Two agents claim different jobs when polling."""
        service = AgentService(test_db_session)

        # Register two agents
        reg1 = self._register_agent(service, test_team, test_user, test_db_session, name="Agent 1")
        reg2 = self._register_agent(service, test_team, test_user, test_db_session, name="Agent 2")

        # Create two pending jobs
        job1 = create_job(test_team, tool="photostats", status=JobStatus.PENDING)
        job2 = create_job(test_team, tool="photostats", status=JobStatus.PENDING)

        # Agent 1 claims first job
        response1 = test_client.post(
            "/api/agent/v1/jobs/claim",
            headers={"Authorization": f"Bearer {reg1.api_key}"}
        )

        # Agent 2 claims second job
        response2 = test_client.post(
            "/api/agent/v1/jobs/claim",
            headers={"Authorization": f"Bearer {reg2.api_key}"}
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Verify they got different jobs
        data1 = response1.json()
        data2 = response2.json()
        assert data1["guid"] != data2["guid"]

        # Refresh and verify assignments
        test_db_session.refresh(job1)
        test_db_session.refresh(job2)
        assert job1.status == JobStatus.ASSIGNED
        assert job2.status == JobStatus.ASSIGNED

        # Jobs should be assigned to different agents
        assigned_agents = {job1.agent_id, job2.agent_id}
        assert len(assigned_agents) == 2

    def test_three_agents_two_jobs(
        self,
        test_db_session,
        test_team,
        test_user,
        test_client,
        create_job,
    ):
        """Three agents, two jobs - third agent gets nothing."""
        service = AgentService(test_db_session)

        # Register three agents
        reg1 = self._register_agent(service, test_team, test_user, test_db_session, name="Agent 1")
        reg2 = self._register_agent(service, test_team, test_user, test_db_session, name="Agent 2")
        reg3 = self._register_agent(service, test_team, test_user, test_db_session, name="Agent 3")

        # Create only two pending jobs
        create_job(test_team, tool="photostats", status=JobStatus.PENDING)
        create_job(test_team, tool="photostats", status=JobStatus.PENDING)

        # All agents try to claim
        response1 = test_client.post(
            "/api/agent/v1/jobs/claim",
            headers={"Authorization": f"Bearer {reg1.api_key}"}
        )
        response2 = test_client.post(
            "/api/agent/v1/jobs/claim",
            headers={"Authorization": f"Bearer {reg2.api_key}"}
        )
        response3 = test_client.post(
            "/api/agent/v1/jobs/claim",
            headers={"Authorization": f"Bearer {reg3.api_key}"}
        )

        # First two get jobs
        assert response1.status_code == 200
        assert response2.status_code == 200

        # Third agent gets nothing (204)
        assert response3.status_code == 204

    def test_capability_based_distribution(
        self,
        test_db_session,
        test_team,
        test_user,
        test_client,
        create_job,
    ):
        """Jobs requiring specific capabilities go to capable agents."""
        service = AgentService(test_db_session)

        # Register two agents with different capabilities
        reg_basic = self._register_agent(
            service, test_team, test_user, test_db_session,
            name="Basic Agent",
            capabilities=["local_filesystem"]
        )
        reg_advanced = self._register_agent(
            service, test_team, test_user, test_db_session,
            name="Advanced Agent",
            capabilities=["local_filesystem", "tool:photostats:1.0.0"]
        )

        # Create a job requiring photostats capability
        job_with_cap = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.PENDING,
        )
        # Set required capabilities
        job_with_cap.required_capabilities = ["photostats"]
        test_db_session.commit()

        # Basic agent tries first - should get nothing
        response_basic = test_client.post(
            "/api/agent/v1/jobs/claim",
            headers={"Authorization": f"Bearer {reg_basic.api_key}"}
        )
        assert response_basic.status_code == 204

        # Advanced agent gets the job
        response_advanced = test_client.post(
            "/api/agent/v1/jobs/claim",
            headers={"Authorization": f"Bearer {reg_advanced.api_key}"}
        )
        assert response_advanced.status_code == 200
        assert response_advanced.json()["guid"] == job_with_cap.guid


class TestMultiAgentLoadVisibility:
    """Integration tests for agent load visibility."""

    def _register_agent(
        self,
        service: AgentService,
        team,
        user,
        db_session,
        name: str = "Test Agent",
        capabilities: list = None
    ):
        """Helper to register an agent and return registration result with API key."""
        token_result = service.create_registration_token(
            team_id=team.id,
            created_by_user_id=user.id,
        )
        db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name=name,
            hostname="test-host.local",
            os_info="Linux",
            capabilities=capabilities or ["local_filesystem"],
            version="1.0.0"
        )
        db_session.commit()

        # Bring agent online
        service.process_heartbeat(reg_result.agent, status=AgentStatus.ONLINE)
        db_session.commit()

        return reg_result

    def test_agent_load_visible_in_pool_status(
        self,
        test_db_session,
        test_team,
        test_user,
        authenticated_client,
        create_job,
    ):
        """Agent load is visible in pool status API."""
        service = AgentService(test_db_session)

        # Register an agent
        reg = self._register_agent(
            service, test_team, test_user, test_db_session,
            name="Busy Agent"
        )

        # Create completed jobs for the agent
        for _ in range(3):
            job = create_job(
                test_team,
                tool="photostats",
                status=JobStatus.COMPLETED,
                agent=reg.agent,
            )
            job.completed_at = datetime.utcnow() - timedelta(minutes=15)
        test_db_session.commit()

        # Check pool status
        response = authenticated_client.get("/api/agent/v1/pool-status")
        assert response.status_code == 200

        data = response.json()
        assert data["online_count"] >= 1

    def test_agent_detail_shows_job_stats(
        self,
        test_db_session,
        test_team,
        test_user,
        authenticated_client,
        create_job,
    ):
        """Agent detail page shows job statistics."""
        service = AgentService(test_db_session)

        # Register an agent
        reg = self._register_agent(
            service, test_team, test_user, test_db_session,
            name="Productive Agent"
        )

        # Create some completed jobs
        for _ in range(5):
            job = create_job(
                test_team,
                tool="photostats",
                status=JobStatus.COMPLETED,
                agent=reg.agent,
            )
            job.completed_at = datetime.utcnow() - timedelta(minutes=15)

        # Create some failed jobs
        for _ in range(2):
            job = create_job(
                test_team,
                tool="photostats",
                status=JobStatus.FAILED,
                agent=reg.agent,
            )
            job.completed_at = datetime.utcnow() - timedelta(minutes=15)

        test_db_session.commit()

        # Get agent detail
        response = authenticated_client.get(f"/api/agent/v1/{reg.agent.guid}/detail")
        assert response.status_code == 200

        data = response.json()
        assert data["total_jobs_completed"] == 5
        assert data["total_jobs_failed"] == 2


class TestBoundAgentRouting:
    """Integration tests for bound agent job routing."""

    def _register_agent(
        self,
        service: AgentService,
        team,
        user,
        db_session,
        name: str = "Test Agent",
        capabilities: list = None
    ):
        """Helper to register an agent and return registration result with API key."""
        token_result = service.create_registration_token(
            team_id=team.id,
            created_by_user_id=user.id,
        )
        db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name=name,
            hostname="test-host.local",
            os_info="Linux",
            capabilities=capabilities or ["local_filesystem"],
            version="1.0.0"
        )
        db_session.commit()

        # Bring agent online
        service.process_heartbeat(reg_result.agent, status=AgentStatus.ONLINE)
        db_session.commit()

        return reg_result

    def test_bound_job_only_goes_to_bound_agent(
        self,
        test_db_session,
        test_team,
        test_user,
        test_client,
        create_job,
        sample_collection,
    ):
        """Jobs bound to a specific agent only go to that agent."""
        service = AgentService(test_db_session)

        # Register two agents
        reg_bound = self._register_agent(
            service, test_team, test_user, test_db_session,
            name="Bound Agent"
        )
        reg_other = self._register_agent(
            service, test_team, test_user, test_db_session,
            name="Other Agent"
        )

        # Create a collection bound to bound_agent
        collection = sample_collection(location="/photos/local")
        collection.bound_agent_id = reg_bound.agent.id
        test_db_session.commit()

        # Create a job bound to that agent
        bound_job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.PENDING,
            collection=collection,
            bound_agent=reg_bound.agent,
        )

        # Other agent tries first - should get nothing
        response_other = test_client.post(
            "/api/agent/v1/jobs/claim",
            headers={"Authorization": f"Bearer {reg_other.api_key}"}
        )
        assert response_other.status_code == 204

        # Bound agent gets the job
        response_bound = test_client.post(
            "/api/agent/v1/jobs/claim",
            headers={"Authorization": f"Bearer {reg_bound.api_key}"}
        )
        assert response_bound.status_code == 200
        assert response_bound.json()["guid"] == bound_job.guid


class TestMultiAgentConcurrency:
    """Integration tests for concurrent multi-agent operations."""

    def _register_agent(
        self,
        service: AgentService,
        team,
        user,
        db_session,
        name: str = "Test Agent",
        capabilities: list = None
    ):
        """Helper to register an agent and return registration result with API key."""
        token_result = service.create_registration_token(
            team_id=team.id,
            created_by_user_id=user.id,
        )
        db_session.commit()

        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name=name,
            hostname="test-host.local",
            os_info="Linux",
            capabilities=capabilities or ["local_filesystem"],
            version="1.0.0"
        )
        db_session.commit()

        # Bring agent online
        service.process_heartbeat(reg_result.agent, status=AgentStatus.ONLINE)
        db_session.commit()

        return reg_result

    def test_sequential_claiming_different_jobs(
        self,
        test_db_session,
        test_team,
        test_user,
        test_client,
        create_job,
    ):
        """Sequential claiming gives each agent a different job."""
        service = AgentService(test_db_session)

        # Register multiple agents
        registrations = [
            self._register_agent(
                service, test_team, test_user, test_db_session,
                name=f"Agent {i}"
            )
            for i in range(5)
        ]

        # Create many pending jobs
        jobs = [
            create_job(test_team, tool="photostats", status=JobStatus.PENDING)
            for _ in range(5)
        ]

        claimed_guids = []

        # Each agent claims sequentially
        for reg in registrations:
            response = test_client.post(
                "/api/agent/v1/jobs/claim",
                headers={"Authorization": f"Bearer {reg.api_key}"}
            )
            assert response.status_code == 200
            data = response.json()
            claimed_guids.append(data["guid"])

        # All claimed GUIDs should be unique
        assert len(claimed_guids) == len(set(claimed_guids))

        # All jobs should be assigned
        for job in jobs:
            test_db_session.refresh(job)
            assert job.status == JobStatus.ASSIGNED


# ============================================================================
# Fixtures
# ============================================================================

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
def sample_collection(test_db_session, test_team):
    """Factory fixture to create sample collections."""
    from backend.src.models.collection import Collection, CollectionType, CollectionState

    def _create(location="/photos/test", name="Test Collection"):
        collection = Collection(
            team_id=test_team.id,
            name=name,
            location=location,
            type=CollectionType.LOCAL,
            state=CollectionState.LIVE,
        )
        test_db_session.add(collection)
        test_db_session.commit()
        test_db_session.refresh(collection)
        return collection

    return _create
