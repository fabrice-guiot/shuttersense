"""
Unit tests for load balancing in job distribution.

Tests that when multiple agents can handle a job, the system prefers
the agent with the fewest recently completed jobs for even distribution.

Issue #90 - Distributed Agent Architecture (Phase 12)
Task: T177 - Unit tests for load balancing
"""

import pytest
from datetime import datetime, timedelta

from backend.src.services.job_coordinator_service import JobCoordinatorService
from backend.src.models.agent import AgentStatus
from backend.src.models.job import Job, JobStatus


class TestAgentLoadTracking:
    """Tests for tracking agent load (recent job count)."""

    def test_get_agent_recent_job_count_no_jobs(
        self, test_db_session, test_team, test_user, create_agent
    ):
        """Agent with no jobs returns count of 0."""
        agent = create_agent(test_team, test_user, name="Idle Agent")

        service = JobCoordinatorService(test_db_session)
        count = service.get_agent_recent_job_count(agent.id, test_team.id)

        assert count == 0

    def test_get_agent_recent_job_count_completed_jobs(
        self, test_db_session, test_team, test_user, create_agent, create_job
    ):
        """Agent with completed jobs returns correct count."""
        agent = create_agent(test_team, test_user, name="Busy Agent")

        # Create 3 completed jobs for this agent (completed in last hour)
        for i in range(3):
            job = create_job(
                test_team,
                tool="photostats",
                status=JobStatus.COMPLETED,
                agent=agent,
            )
            job.completed_at = datetime.utcnow() - timedelta(minutes=30)
        test_db_session.commit()

        service = JobCoordinatorService(test_db_session)
        count = service.get_agent_recent_job_count(agent.id, test_team.id)

        assert count == 3

    def test_get_agent_recent_job_count_excludes_old_jobs(
        self, test_db_session, test_team, test_user, create_agent, create_job
    ):
        """Jobs completed more than 1 hour ago are not counted."""
        agent = create_agent(test_team, test_user, name="Agent")

        # Create 2 recent jobs (within 1 hour)
        for i in range(2):
            job = create_job(
                test_team,
                tool="photostats",
                status=JobStatus.COMPLETED,
                agent=agent,
            )
            job.completed_at = datetime.utcnow() - timedelta(minutes=30)

        # Create 3 old jobs (more than 1 hour ago)
        for i in range(3):
            job = create_job(
                test_team,
                tool="photostats",
                status=JobStatus.COMPLETED,
                agent=agent,
            )
            job.completed_at = datetime.utcnow() - timedelta(hours=2)

        test_db_session.commit()

        service = JobCoordinatorService(test_db_session)
        count = service.get_agent_recent_job_count(agent.id, test_team.id)

        # Only 2 recent jobs should be counted
        assert count == 2

    def test_get_agent_recent_job_count_includes_running_jobs(
        self, test_db_session, test_team, test_user, create_agent, create_job
    ):
        """Running jobs count toward agent load."""
        agent = create_agent(test_team, test_user, name="Agent")

        # Create 2 running jobs
        for i in range(2):
            create_job(
                test_team,
                tool="photostats",
                status=JobStatus.RUNNING,
                agent=agent,
            )

        # Create 1 completed job
        job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.COMPLETED,
            agent=agent,
        )
        job.completed_at = datetime.utcnow() - timedelta(minutes=15)

        test_db_session.commit()

        service = JobCoordinatorService(test_db_session)
        count = service.get_agent_recent_job_count(agent.id, test_team.id)

        # 2 running + 1 completed = 3
        assert count == 3

    def test_get_agent_recent_job_count_excludes_failed_jobs(
        self, test_db_session, test_team, test_user, create_agent, create_job
    ):
        """Failed jobs are not counted toward load."""
        agent = create_agent(test_team, test_user, name="Agent")

        # Create 2 completed jobs
        for i in range(2):
            job = create_job(
                test_team,
                tool="photostats",
                status=JobStatus.COMPLETED,
                agent=agent,
            )
            job.completed_at = datetime.utcnow() - timedelta(minutes=15)

        # Create 3 failed jobs
        for i in range(3):
            job = create_job(
                test_team,
                tool="photostats",
                status=JobStatus.FAILED,
                agent=agent,
            )
            job.completed_at = datetime.utcnow() - timedelta(minutes=15)

        test_db_session.commit()

        service = JobCoordinatorService(test_db_session)
        count = service.get_agent_recent_job_count(agent.id, test_team.id)

        # Only 2 completed jobs, failed jobs not counted
        assert count == 2

    def test_get_agent_recent_job_count_tenant_isolation(
        self, test_db_session, test_team, test_user, other_team, other_team_user,
        create_agent, create_job
    ):
        """Agent job count is scoped to team."""
        # Create same agent name in both teams
        agent1 = create_agent(test_team, test_user, name="Agent")
        agent2 = create_agent(other_team, other_team_user, name="Agent")

        # Create jobs for agent1 in test_team
        for i in range(3):
            job = create_job(
                test_team,
                tool="photostats",
                status=JobStatus.COMPLETED,
                agent=agent1,
            )
            job.completed_at = datetime.utcnow() - timedelta(minutes=15)

        # Create jobs for agent2 in other_team
        for i in range(5):
            job = create_job(
                other_team,
                tool="photostats",
                status=JobStatus.COMPLETED,
                agent=agent2,
            )
            job.completed_at = datetime.utcnow() - timedelta(minutes=15)

        test_db_session.commit()

        service = JobCoordinatorService(test_db_session)

        # Count for agent1 in test_team should be 3
        count1 = service.get_agent_recent_job_count(agent1.id, test_team.id)
        assert count1 == 3

        # Count for agent2 in other_team should be 5
        count2 = service.get_agent_recent_job_count(agent2.id, other_team.id)
        assert count2 == 5


class TestLoadBalancedJobClaiming:
    """Tests for load-balanced job claiming."""

    def test_claim_prefers_least_busy_agent(
        self, test_db_session, test_team, test_user, create_agent, create_job
    ):
        """When multiple agents can handle a job, prefer the least busy one."""
        # Create two agents with different workloads
        busy_agent = create_agent(test_team, test_user, name="Busy Agent")
        idle_agent = create_agent(test_team, test_user, name="Idle Agent")

        # Give busy_agent 5 recent completed jobs
        for i in range(5):
            job = create_job(
                test_team,
                tool="photostats",
                status=JobStatus.COMPLETED,
                agent=busy_agent,
            )
            job.completed_at = datetime.utcnow() - timedelta(minutes=15)

        # Give idle_agent 1 recent completed job
        job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.COMPLETED,
            agent=idle_agent,
        )
        job.completed_at = datetime.utcnow() - timedelta(minutes=15)

        test_db_session.commit()

        # Create a new pending job that either agent could handle
        pending_job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.PENDING,
        )

        service = JobCoordinatorService(test_db_session)

        # The idle agent should claim the job (has fewer recent jobs)
        result = service.claim_job(
            agent_id=idle_agent.id,
            team_id=test_team.id,
            agent_capabilities=["local_filesystem"],
        )

        assert result is not None
        assert result.job.guid == pending_job.guid
        assert result.job.agent_id == idle_agent.id

    def test_claim_still_works_with_busy_agent(
        self, test_db_session, test_team, test_user, create_agent, create_job
    ):
        """Busy agent can still claim jobs when no other option."""
        busy_agent = create_agent(test_team, test_user, name="Busy Agent")

        # Give busy_agent 10 recent completed jobs
        for i in range(10):
            job = create_job(
                test_team,
                tool="photostats",
                status=JobStatus.COMPLETED,
                agent=busy_agent,
            )
            job.completed_at = datetime.utcnow() - timedelta(minutes=15)

        test_db_session.commit()

        # Create a new pending job
        pending_job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.PENDING,
        )

        service = JobCoordinatorService(test_db_session)

        # Busy agent should still be able to claim (no alternatives)
        result = service.claim_job(
            agent_id=busy_agent.id,
            team_id=test_team.id,
            agent_capabilities=["local_filesystem"],
        )

        assert result is not None
        assert result.job.guid == pending_job.guid

    def test_bound_job_ignores_load_balancing(
        self, test_db_session, test_team, test_user, create_agent, create_collection, create_job
    ):
        """Bound jobs are claimed by the bound agent regardless of load."""
        busy_agent = create_agent(test_team, test_user, name="Busy Agent")
        idle_agent = create_agent(test_team, test_user, name="Idle Agent")

        # Give busy_agent many recent jobs
        for i in range(10):
            job = create_job(
                test_team,
                tool="photostats",
                status=JobStatus.COMPLETED,
                agent=busy_agent,
            )
            job.completed_at = datetime.utcnow() - timedelta(minutes=15)

        test_db_session.commit()

        # Create a LOCAL collection bound to busy_agent
        collection = create_collection(test_team, bound_agent=busy_agent)

        # Create a job bound to this collection (and thus to busy_agent)
        bound_job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.PENDING,
            collection=collection,
            bound_agent=busy_agent,
        )

        service = JobCoordinatorService(test_db_session)

        # Idle agent cannot claim the bound job
        result_idle = service.claim_job(
            agent_id=idle_agent.id,
            team_id=test_team.id,
            agent_capabilities=["local_filesystem"],
        )
        assert result_idle is None

        # Busy agent can claim it despite high load
        result_busy = service.claim_job(
            agent_id=busy_agent.id,
            team_id=test_team.id,
            agent_capabilities=["local_filesystem"],
        )
        assert result_busy is not None
        assert result_busy.job.guid == bound_job.guid

    def test_claim_with_equal_load_uses_fifo(
        self, test_db_session, test_team, test_user, create_agent, create_job
    ):
        """When agents have equal load, use standard FIFO ordering."""
        agent1 = create_agent(test_team, test_user, name="Agent 1")
        agent2 = create_agent(test_team, test_user, name="Agent 2")

        # Both agents have 2 recent jobs
        for agent in [agent1, agent2]:
            for i in range(2):
                job = create_job(
                    test_team,
                    tool="photostats",
                    status=JobStatus.COMPLETED,
                    agent=agent,
                )
                job.completed_at = datetime.utcnow() - timedelta(minutes=15)

        test_db_session.commit()

        # Create pending jobs
        job1 = create_job(test_team, tool="photostats", status=JobStatus.PENDING, priority=5)
        job2 = create_job(test_team, tool="photostats", status=JobStatus.PENDING, priority=5)

        service = JobCoordinatorService(test_db_session)

        # Both agents should be able to claim jobs (equal load)
        result1 = service.claim_job(
            agent_id=agent1.id,
            team_id=test_team.id,
            agent_capabilities=["local_filesystem"],
        )
        result2 = service.claim_job(
            agent_id=agent2.id,
            team_id=test_team.id,
            agent_capabilities=["local_filesystem"],
        )

        assert result1 is not None
        assert result2 is not None
        # Jobs should be different
        assert result1.job.guid != result2.job.guid


class TestLoadBalancingWithCapabilities:
    """Tests for load balancing with capability requirements."""

    def test_load_balancing_respects_capabilities(
        self, test_db_session, test_team, test_user, create_agent, create_job
    ):
        """Load balancing only considers agents with required capabilities."""
        # Idle agent without required capability
        idle_agent = create_agent(
            test_team, test_user,
            name="Idle Agent",
            capabilities=["local_filesystem"]  # Missing photostats capability
        )

        # Busy agent with required capability
        busy_agent = create_agent(
            test_team, test_user,
            name="Busy Agent",
            capabilities=["local_filesystem", "tool:photostats:1.0.0"]
        )

        # Give busy_agent 10 recent jobs
        for i in range(10):
            job = create_job(
                test_team,
                tool="photostats",
                status=JobStatus.COMPLETED,
                agent=busy_agent,
            )
            job.completed_at = datetime.utcnow() - timedelta(minutes=15)

        test_db_session.commit()

        # Create job requiring photostats capability
        pending_job = create_job(
            test_team,
            tool="photostats",
            status=JobStatus.PENDING,
        )
        pending_job.required_capabilities = ["photostats"]
        test_db_session.commit()

        service = JobCoordinatorService(test_db_session)

        # Idle agent cannot claim (lacks capability)
        result_idle = service.claim_job(
            agent_id=idle_agent.id,
            team_id=test_team.id,
            agent_capabilities=["local_filesystem"],
        )
        assert result_idle is None

        # Busy agent can claim despite high load (only option)
        result_busy = service.claim_job(
            agent_id=busy_agent.id,
            team_id=test_team.id,
            agent_capabilities=["local_filesystem", "tool:photostats:1.0.0"],
        )
        assert result_busy is not None
        assert result_busy.job.guid == pending_job.guid


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
    from backend.src.models.collection import Collection, CollectionType, CollectionState

    def _create_collection(team, bound_agent=None):
        import tempfile

        temp_dir = tempfile.mkdtemp()

        collection = Collection(
            team_id=team.id,
            name="Test Collection",
            location=temp_dir,
            type=CollectionType.LOCAL,
            state=CollectionState.LIVE,
            connector_id=None,
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
            required_capabilities_json=json.dumps([]),
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
