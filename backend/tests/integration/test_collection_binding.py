"""
Integration tests for LOCAL collection creation with agent binding.

Issue #90 - Distributed Agent Architecture (Phase 6)
Task T104: Integration tests for LOCAL collection creation with bound agents

Tests:
- Creating LOCAL collections with bound agents via API
- Bound agent validation (must exist, belong to same team)
- Collection response includes bound agent details
- Agent binding restrictions for remote collections
"""

import pytest
import tempfile
from fastapi.testclient import TestClient

from backend.src.models.agent import AgentStatus


class TestLocalCollectionWithBoundAgent:
    """Integration tests for LOCAL collections with agent binding."""

    def test_create_local_collection_with_bound_agent(
        self, authenticated_client, create_agent
    ):
        """Test creating a LOCAL collection with a bound agent."""
        agent = create_agent(name="Local Agent")

        with tempfile.TemporaryDirectory() as temp_dir:
            response = authenticated_client.post(
                "/api/collections",
                json={
                    "name": "Local with Agent",
                    "type": "local",
                    "location": temp_dir,
                    "state": "live",
                    "bound_agent_guid": agent.guid,
                }
            )

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "Local with Agent"
            assert data["type"] == "local"
            assert data["bound_agent"] is not None
            assert data["bound_agent"]["guid"] == agent.guid
            assert data["bound_agent"]["name"] == "Local Agent"
            assert data["bound_agent"]["status"] in ["online", "offline"]

    def test_create_local_collection_without_bound_agent(
        self, authenticated_client
    ):
        """Test that LOCAL collections can be created without a bound agent."""
        with tempfile.TemporaryDirectory() as temp_dir:
            response = authenticated_client.post(
                "/api/collections",
                json={
                    "name": "Local without Agent",
                    "type": "local",
                    "location": temp_dir,
                    "state": "live",
                }
            )

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "Local without Agent"
            assert data["type"] == "local"
            assert data["bound_agent"] is None

    def test_create_remote_collection_rejects_bound_agent(
        self, authenticated_client, sample_connector
    ):
        """Test that remote collections cannot have a bound agent."""
        connector = sample_connector(name="S3 Test", type="s3")

        # Try to create S3 collection with bound_agent_guid
        response = authenticated_client.post(
            "/api/collections",
            json={
                "name": "S3 with Agent",
                "type": "s3",
                "location": "bucket/path",
                "connector_guid": connector.guid,
                "bound_agent_guid": "agt_01hgw2bbg0000000000000999",  # Doesn't matter, should fail validation
            }
        )

        assert response.status_code == 422
        # Pydantic validation error for remote collection with bound_agent_guid
        assert "bound_agent_guid is only valid for LOCAL" in str(response.json())

    def test_create_local_collection_with_nonexistent_agent(
        self, authenticated_client
    ):
        """Test that creating a collection with a nonexistent agent fails."""
        # Use a valid-format GUID (Crockford Base32) that doesn't exist
        # This is a valid format: 26 chars of Crockford Base32 after prefix
        nonexistent_guid = "agt_00000000000000000000000000"

        with tempfile.TemporaryDirectory() as temp_dir:
            response = authenticated_client.post(
                "/api/collections",
                json={
                    "name": "Bad Agent Collection",
                    "type": "local",
                    "location": temp_dir,
                    "state": "live",
                    "bound_agent_guid": nonexistent_guid,
                }
            )

            assert response.status_code == 400
            assert "Agent not found" in response.json()["detail"]

    def test_create_local_collection_with_invalid_agent_guid_format(
        self, authenticated_client
    ):
        """Test that an invalid agent GUID format is rejected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            response = authenticated_client.post(
                "/api/collections",
                json={
                    "name": "Invalid GUID Collection",
                    "type": "local",
                    "location": temp_dir,
                    "state": "live",
                    "bound_agent_guid": "invalid_guid_format",
                }
            )

            assert response.status_code == 400
            assert "Invalid identifier" in response.json()["detail"] or "GUID" in response.json()["detail"]

    def test_get_collection_includes_bound_agent(
        self, authenticated_client, create_agent
    ):
        """Test that GET collection includes bound agent details."""
        agent = create_agent(name="Get Test Agent")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create collection
            create_response = authenticated_client.post(
                "/api/collections",
                json={
                    "name": "Get Test Collection",
                    "type": "local",
                    "location": temp_dir,
                    "state": "live",
                    "bound_agent_guid": agent.guid,
                }
            )
            assert create_response.status_code == 201
            collection_guid = create_response.json()["guid"]

            # Get collection
            get_response = authenticated_client.get(f"/api/collections/{collection_guid}")
            assert get_response.status_code == 200
            data = get_response.json()
            assert data["bound_agent"] is not None
            assert data["bound_agent"]["guid"] == agent.guid
            assert data["bound_agent"]["name"] == "Get Test Agent"

    def test_list_collections_includes_bound_agent(
        self, authenticated_client, create_agent
    ):
        """Test that listing collections includes bound agent details."""
        agent = create_agent(name="List Test Agent")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create collection
            authenticated_client.post(
                "/api/collections",
                json={
                    "name": "List Test Collection",
                    "type": "local",
                    "location": temp_dir,
                    "state": "live",
                    "bound_agent_guid": agent.guid,
                }
            )

            # List collections
            response = authenticated_client.get("/api/collections")
            assert response.status_code == 200
            data = response.json()

            # Find our collection
            our_collection = next(
                (c for c in data if c["name"] == "List Test Collection"),
                None
            )
            assert our_collection is not None
            assert our_collection["bound_agent"] is not None
            assert our_collection["bound_agent"]["guid"] == agent.guid

    def test_update_local_collection_bind_agent(
        self, authenticated_client, create_agent
    ):
        """Test updating a LOCAL collection to bind an agent."""
        agent = create_agent(name="Update Bind Agent")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create collection without bound agent
            create_response = authenticated_client.post(
                "/api/collections",
                json={
                    "name": "Update Bind Collection",
                    "type": "local",
                    "location": temp_dir,
                    "state": "live",
                }
            )
            assert create_response.status_code == 201
            collection_guid = create_response.json()["guid"]
            assert create_response.json()["bound_agent"] is None

            # Update to bind agent
            update_response = authenticated_client.put(
                f"/api/collections/{collection_guid}",
                json={
                    "bound_agent_guid": agent.guid,
                }
            )
            assert update_response.status_code == 200
            data = update_response.json()
            assert data["bound_agent"] is not None
            assert data["bound_agent"]["guid"] == agent.guid
            assert data["bound_agent"]["name"] == "Update Bind Agent"

    def test_update_local_collection_unbind_agent(
        self, authenticated_client, create_agent
    ):
        """Test updating a LOCAL collection to unbind an agent."""
        agent = create_agent(name="Update Unbind Agent")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create collection with bound agent
            create_response = authenticated_client.post(
                "/api/collections",
                json={
                    "name": "Update Unbind Collection",
                    "type": "local",
                    "location": temp_dir,
                    "state": "live",
                    "bound_agent_guid": agent.guid,
                }
            )
            assert create_response.status_code == 201
            collection_guid = create_response.json()["guid"]
            assert create_response.json()["bound_agent"] is not None

            # Update to unbind agent (set to null)
            update_response = authenticated_client.put(
                f"/api/collections/{collection_guid}",
                json={
                    "bound_agent_guid": None,
                }
            )
            assert update_response.status_code == 200
            data = update_response.json()
            assert data["bound_agent"] is None

    def test_update_local_collection_change_bound_agent(
        self, authenticated_client, create_agent
    ):
        """Test updating a LOCAL collection to change the bound agent."""
        agent1 = create_agent(name="Agent One")
        agent2 = create_agent(name="Agent Two")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create collection with agent1
            create_response = authenticated_client.post(
                "/api/collections",
                json={
                    "name": "Change Bound Agent Collection",
                    "type": "local",
                    "location": temp_dir,
                    "state": "live",
                    "bound_agent_guid": agent1.guid,
                }
            )
            assert create_response.status_code == 201
            collection_guid = create_response.json()["guid"]
            assert create_response.json()["bound_agent"]["guid"] == agent1.guid

            # Update to change to agent2
            update_response = authenticated_client.put(
                f"/api/collections/{collection_guid}",
                json={
                    "bound_agent_guid": agent2.guid,
                }
            )
            assert update_response.status_code == 200
            data = update_response.json()
            assert data["bound_agent"] is not None
            assert data["bound_agent"]["guid"] == agent2.guid
            assert data["bound_agent"]["name"] == "Agent Two"

    def test_update_local_collection_with_nonexistent_agent(
        self, authenticated_client
    ):
        """Test that updating with a nonexistent agent fails."""
        nonexistent_guid = "agt_00000000000000000000000000"

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create collection
            create_response = authenticated_client.post(
                "/api/collections",
                json={
                    "name": "Nonexistent Agent Update Collection",
                    "type": "local",
                    "location": temp_dir,
                    "state": "live",
                }
            )
            assert create_response.status_code == 201
            collection_guid = create_response.json()["guid"]

            # Try to update with nonexistent agent
            update_response = authenticated_client.put(
                f"/api/collections/{collection_guid}",
                json={
                    "bound_agent_guid": nonexistent_guid,
                }
            )
            assert update_response.status_code == 400
            assert "Agent not found" in update_response.json()["detail"]


class TestAgentBindingCrossTeam:
    """Tests for cross-team agent binding restrictions."""

    def test_cannot_bind_agent_from_other_team(
        self, authenticated_client, other_team, other_team_user, test_db_session
    ):
        """Test that agents from other teams cannot be bound to collections."""
        from backend.src.services.agent_service import AgentService

        # Create an agent in the OTHER team
        agent_service = AgentService(test_db_session)
        token_result = agent_service.create_registration_token(
            team_id=other_team.id,
            created_by_user_id=other_team_user.id,
        )
        test_db_session.commit()

        reg_result = agent_service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Other Team Agent",
        )
        test_db_session.commit()
        other_agent = reg_result.agent

        # Try to create a collection in the authenticated user's team
        # bound to the other team's agent
        with tempfile.TemporaryDirectory() as temp_dir:
            response = authenticated_client.post(
                "/api/collections",
                json={
                    "name": "Cross Team Collection",
                    "type": "local",
                    "location": temp_dir,
                    "state": "live",
                    "bound_agent_guid": other_agent.guid,
                }
            )

            # Should fail - agent belongs to different team
            assert response.status_code == 400
            assert "same team" in response.json()["detail"].lower()


class TestBoundJobRouting:
    """Integration tests for bound job routing (T105).

    Verifies end-to-end flow:
    - Jobs created for bound collections have bound_agent_id set
    - Bound jobs are routed to the correct agent
    - Other agents cannot claim bound jobs
    """

    def test_job_created_for_bound_collection_has_bound_agent_id(
        self, authenticated_client, test_db_session, create_agent
    ):
        """Test that jobs created for bound collections have bound_agent_id."""
        from backend.src.models.job import Job

        agent = create_agent(name="Bound Agent for Job")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create collection with bound agent
            response = authenticated_client.post(
                "/api/collections",
                json={
                    "name": "Collection for Job Test",
                    "type": "local",
                    "location": temp_dir,
                    "state": "live",
                    "bound_agent_guid": agent.guid,
                }
            )
            assert response.status_code == 201
            collection_guid = response.json()["guid"]

            # Run a tool on the collection
            tool_response = authenticated_client.post(
                "/api/tools/run",
                json={
                    "collection_guid": collection_guid,
                    "tool": "photostats",
                }
            )
            # 202 Accepted is the expected status for job creation
            assert tool_response.status_code == 202
            job_data = tool_response.json()
            job_guid = job_data["id"]

            # Verify job has bound_agent_id set
            from backend.src.services.guid import GuidService
            job_uuid = GuidService.parse_identifier(job_guid, "job")
            job = test_db_session.query(Job).filter(Job.uuid == job_uuid).first()
            assert job is not None
            assert job.bound_agent_id == agent.id

    def test_bound_job_routed_to_bound_agent(
        self, test_db_session, test_team, test_user, create_agent
    ):
        """Test that bound jobs are routed to the bound agent only."""
        from backend.src.services.job_coordinator_service import JobCoordinatorService
        from backend.src.models.job import Job, JobStatus

        # Create two agents
        agent1 = create_agent(name="Agent 1")
        agent2 = create_agent(name="Agent 2")

        # Create job bound to agent1
        job = Job(
            team_id=test_team.id,
            tool="photostats",
            status=JobStatus.PENDING,
            bound_agent_id=agent1.id,
            required_capabilities=[],
        )
        test_db_session.add(job)
        test_db_session.commit()

        coordinator = JobCoordinatorService(test_db_session)

        # Agent1 should be able to claim the job
        result = coordinator.claim_job(agent1.id, test_team.id, ["photostats"])
        assert result is not None
        assert result.job.id == job.id

    def test_bound_job_not_claimable_by_other_agents(
        self, test_db_session, test_team, test_user, create_agent
    ):
        """Test that bound jobs cannot be claimed by other agents."""
        from backend.src.services.job_coordinator_service import JobCoordinatorService
        from backend.src.models.job import Job, JobStatus

        # Create two agents
        agent1 = create_agent(name="Agent 1")
        agent2 = create_agent(name="Agent 2")

        # Create job bound to agent1
        job = Job(
            team_id=test_team.id,
            tool="photostats",
            status=JobStatus.PENDING,
            bound_agent_id=agent1.id,
            required_capabilities=[],
        )
        test_db_session.add(job)
        test_db_session.commit()

        coordinator = JobCoordinatorService(test_db_session)

        # Agent2 should NOT be able to claim the job (returns None)
        result = coordinator.claim_job(agent2.id, test_team.id, ["photostats"])
        assert result is None

    def test_unbound_job_claimable_by_any_agent(
        self, test_db_session, test_team, test_user, create_agent
    ):
        """Test that unbound jobs can be claimed by any agent."""
        from backend.src.services.job_coordinator_service import JobCoordinatorService
        from backend.src.models.job import Job, JobStatus

        agent = create_agent(name="Any Agent")

        # Create unbound job (no bound_agent_id)
        job = Job(
            team_id=test_team.id,
            tool="photostats",
            status=JobStatus.PENDING,
            bound_agent_id=None,
            required_capabilities=["photostats"],
        )
        test_db_session.add(job)
        test_db_session.commit()

        coordinator = JobCoordinatorService(test_db_session)

        # Agent should be able to claim unbound job
        result = coordinator.claim_job(agent.id, test_team.id, ["photostats"])
        assert result is not None
        assert result.job.id == job.id

    def test_bound_job_prioritized_over_unbound(
        self, test_db_session, test_team, test_user, create_agent
    ):
        """Test that bound jobs are prioritized over unbound jobs for an agent."""
        from backend.src.services.job_coordinator_service import JobCoordinatorService
        from backend.src.models.job import Job, JobStatus

        agent = create_agent(name="Priority Agent")

        # Create unbound job first (older)
        unbound_job = Job(
            team_id=test_team.id,
            tool="photostats",
            status=JobStatus.PENDING,
            bound_agent_id=None,
            required_capabilities=["photostats"],
        )
        test_db_session.add(unbound_job)
        test_db_session.commit()

        # Create bound job after (newer, but should be prioritized)
        bound_job = Job(
            team_id=test_team.id,
            tool="photostats",
            status=JobStatus.PENDING,
            bound_agent_id=agent.id,
            required_capabilities=["photostats"],
        )
        test_db_session.add(bound_job)
        test_db_session.commit()

        coordinator = JobCoordinatorService(test_db_session)

        # Agent should claim bound job first, even though unbound is older
        result = coordinator.claim_job(agent.id, test_team.id, ["photostats"])
        assert result is not None
        assert result.job.id == bound_job.id


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def create_agent(test_db_session, test_team, test_user):
    """Factory fixture to create and register test agents."""
    from backend.src.services.agent_service import AgentService

    def _create_agent(name="Test Agent", status=AgentStatus.ONLINE):
        service = AgentService(test_db_session)

        # Create token
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        # Register agent
        result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name=name,
            hostname="test.local",
            os_info="Linux",
            capabilities=["local_filesystem", "photostats"],
            version="1.0.0"
        )
        test_db_session.commit()

        # Set agent status
        if status == AgentStatus.ONLINE:
            service.process_heartbeat(result.agent, status=AgentStatus.ONLINE)
            test_db_session.commit()

        return result.agent

    return _create_agent
