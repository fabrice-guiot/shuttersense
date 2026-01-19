"""
Integration tests for GET /api/agent/v1/pool-status endpoint.

Issue #90 - Distributed Agent Architecture (Phase 4)
Task: T054
"""

import pytest
from datetime import datetime

from backend.src.services.agent_service import AgentService
from backend.src.models.agent import AgentStatus


class TestPoolStatusAPI:
    """Integration tests for pool status endpoint."""

    def test_get_pool_status_empty(self, test_client, test_team):
        """Pool status returns offline for empty team."""
        response = test_client.get("/api/agent/v1/pool-status")
        assert response.status_code == 200

        data = response.json()
        assert data["online_count"] == 0
        assert data["offline_count"] == 0
        assert data["idle_count"] == 0
        assert data["running_jobs_count"] == 0
        assert data["status"] == "offline"

    def test_get_pool_status_with_online_agent(self, test_client, test_db_session, test_team, test_user):
        """Pool status shows idle when online agents exist."""
        service = AgentService(test_db_session)

        # Register an agent (starts OFFLINE, needs heartbeat)
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
            hostname="test.local",
            os_info="macOS 14.0",
            capabilities=["local_filesystem"],
            version="1.0.0"
        )
        test_db_session.commit()

        # Send heartbeat to bring agent online
        service.process_heartbeat(result.agent, status=AgentStatus.ONLINE)
        test_db_session.commit()

        response = test_client.get("/api/agent/v1/pool-status")
        assert response.status_code == 200

        data = response.json()
        assert data["online_count"] == 1
        assert data["offline_count"] == 0
        assert data["idle_count"] == 1
        assert data["running_jobs_count"] == 0
        assert data["status"] == "idle"

    def test_get_pool_status_with_offline_agent(self, test_client, test_db_session, test_team, test_user):
        """Pool status shows offline agents correctly."""
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
            os_info="Ubuntu 22.04",
            capabilities=["local_filesystem"],
            version="1.0.0"
        )
        test_db_session.commit()

        # Set agent to offline
        result.agent.status = AgentStatus.OFFLINE
        test_db_session.commit()

        response = test_client.get("/api/agent/v1/pool-status")
        assert response.status_code == 200

        data = response.json()
        assert data["online_count"] == 0
        assert data["offline_count"] == 1
        assert data["idle_count"] == 0
        assert data["status"] == "offline"

    def test_get_pool_status_response_schema(self, test_client, test_db_session, test_team, test_user):
        """Pool status response matches expected schema."""
        service = AgentService(test_db_session)

        # Register an agent
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        test_db_session.commit()

        service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
            hostname="test.local",
            os_info="Linux",
            capabilities=["local_filesystem"],
            version="1.0.0"
        )
        test_db_session.commit()

        response = test_client.get("/api/agent/v1/pool-status")
        assert response.status_code == 200

        data = response.json()

        # Verify all expected fields exist
        assert "online_count" in data
        assert "offline_count" in data
        assert "idle_count" in data
        assert "running_jobs_count" in data
        assert "status" in data

        # Verify field types
        assert isinstance(data["online_count"], int)
        assert isinstance(data["offline_count"], int)
        assert isinstance(data["idle_count"], int)
        assert isinstance(data["running_jobs_count"], int)
        assert data["status"] in ["offline", "idle", "running"]

    def test_get_pool_status_excludes_other_teams(
        self, test_client, test_db_session, test_team, test_user, other_team, other_team_user
    ):
        """Pool status only includes agents from user's team."""
        service = AgentService(test_db_session)

        # Register agent in other_team only
        token_result = service.create_registration_token(
            team_id=other_team.id,
            created_by_user_id=other_team_user.id,
        )
        test_db_session.commit()

        service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Other Team Agent",
            hostname="other.local",
            os_info="Linux",
            capabilities=["local_filesystem"],
            version="1.0.0"
        )
        test_db_session.commit()

        # Our team should show no agents
        response = test_client.get("/api/agent/v1/pool-status")
        assert response.status_code == 200

        data = response.json()
        assert data["online_count"] == 0
        assert data["status"] == "offline"
