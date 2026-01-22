"""
Unit tests for agent pool status service.

Issue #90 - Distributed Agent Architecture (Phase 4)
Task: T053
"""

import pytest
from datetime import datetime

from backend.src.services.agent_service import AgentService
from backend.src.models.agent import Agent, AgentStatus
from backend.src.models.job import Job, JobStatus


class TestAgentPoolStatus:
    """Tests for get_pool_status method."""

    def test_pool_status_empty_team(self, test_db_session, test_team):
        """Pool status returns offline for team with no agents."""
        service = AgentService(test_db_session)
        status = service.get_pool_status(test_team.id)

        assert status["online_count"] == 0
        assert status["offline_count"] == 0
        assert status["idle_count"] == 0
        assert status["running_jobs_count"] == 0
        assert status["status"] == "offline"

    def test_pool_status_with_online_agent(self, test_db_session, test_team, test_user):
        """Pool status shows idle when online agents have no jobs."""
        service = AgentService(test_db_session)

        # Register an agent (starts as OFFLINE, needs heartbeat to go online)
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
            hostname="test.local",
            os_info="Linux",
            capabilities=["local_filesystem"],
            version="1.0.0"
        )
        test_db_session.commit()

        # Send heartbeat to bring agent online
        service.process_heartbeat(result.agent, status=AgentStatus.ONLINE)
        test_db_session.commit()

        status = service.get_pool_status(test_team.id)

        assert status["online_count"] == 1
        assert status["offline_count"] == 0
        assert status["idle_count"] == 1
        assert status["running_jobs_count"] == 0
        assert status["status"] == "idle"

    def test_pool_status_with_multiple_online_agents(self, test_db_session, test_team, test_user):
        """Pool status correctly counts multiple online agents."""
        service = AgentService(test_db_session)

        # Register multiple agents and bring them online
        agents = []
        for i in range(3):
            token_result = service.create_registration_token(
                team_id=test_team.id,
                created_by_user_id=test_user.id,
            )
            test_db_session.commit()

            result = service.register_agent(
                plaintext_token=token_result.plaintext_token,
                name=f"Agent {i+1}",
                hostname=f"host{i+1}.local",
                os_info="Linux",
                capabilities=["local_filesystem"],
                version="1.0.0"
            )
            agents.append(result.agent)
            test_db_session.commit()

        # Send heartbeats to bring all agents online
        for agent in agents:
            service.process_heartbeat(agent, status=AgentStatus.ONLINE)
        test_db_session.commit()

        status = service.get_pool_status(test_team.id)

        assert status["online_count"] == 3
        assert status["offline_count"] == 0
        assert status["idle_count"] == 3
        assert status["status"] == "idle"

    def test_pool_status_tenant_isolation(self, test_db_session, test_team, test_user, other_team, other_team_user):
        """Pool status only counts agents from the specified team."""
        service = AgentService(test_db_session)

        # Register agent in test_team
        token1 = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()
        result1 = service.register_agent(
            plaintext_token=token1.plaintext_token,
            name="Our Agent",
            hostname="our.local",
            os_info="Linux",
            capabilities=["local_filesystem"],
            version="1.0.0"
        )
        test_db_session.commit()

        # Register agent in other_team
        token2 = service.create_registration_token(
            team_id=other_team.id,
            created_by_user_id=other_team_user.id,
        )
        test_db_session.commit()
        result2 = service.register_agent(
            plaintext_token=token2.plaintext_token,
            name="Their Agent",
            hostname="their.local",
            os_info="Linux",
            capabilities=["local_filesystem"],
            version="1.0.0"
        )
        test_db_session.commit()

        # Bring both agents online via heartbeat
        service.process_heartbeat(result1.agent, status=AgentStatus.ONLINE)
        service.process_heartbeat(result2.agent, status=AgentStatus.ONLINE)
        test_db_session.commit()

        # Our team should only see our agent
        our_status = service.get_pool_status(test_team.id)
        assert our_status["online_count"] == 1

        # Other team should only see their agent
        their_status = service.get_pool_status(other_team.id)
        assert their_status["online_count"] == 1

    def test_pool_status_with_offline_agent(self, test_db_session, test_team, test_user):
        """Pool status shows offline when agent goes offline."""
        service = AgentService(test_db_session)

        # Register an agent
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
            hostname="test.local",
            os_info="Linux",
            capabilities=["local_filesystem"],
            version="1.0.0"
        )
        test_db_session.commit()

        # Set agent to offline
        result.agent.status = AgentStatus.OFFLINE
        test_db_session.commit()

        status = service.get_pool_status(test_team.id)

        assert status["online_count"] == 0
        assert status["offline_count"] == 1
        assert status["idle_count"] == 0
        assert status["status"] == "offline"

    def test_pool_status_with_revoked_agent(self, test_db_session, test_team, test_user):
        """Pool status excludes revoked agents from counts."""
        service = AgentService(test_db_session)

        # Register an agent
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
            hostname="test.local",
            os_info="Linux",
            capabilities=["local_filesystem"],
            version="1.0.0"
        )
        test_db_session.commit()

        # Revoke the agent
        service.revoke_agent(result.agent, "Testing")
        test_db_session.commit()

        status = service.get_pool_status(test_team.id)

        # Revoked agents should not be counted
        assert status["online_count"] == 0
        assert status["offline_count"] == 0
        assert status["status"] == "offline"
