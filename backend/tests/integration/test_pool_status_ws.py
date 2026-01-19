"""
Integration tests for WebSocket pool status broadcast.

Issue #90 - Distributed Agent Architecture (Phase 4)
Task: T055
"""

import pytest
from unittest.mock import AsyncMock

from backend.src.services.agent_service import AgentService
from backend.src.utils.websocket import ConnectionManager, get_connection_manager


class TestPoolStatusWebSocket:
    """Tests for pool status WebSocket functionality."""

    def test_get_agent_pool_channel(self):
        """Agent pool channel is team-scoped."""
        manager = ConnectionManager()

        channel1 = manager.get_agent_pool_channel(1)
        channel2 = manager.get_agent_pool_channel(2)

        assert channel1 != channel2
        assert "1" in channel1
        assert "2" in channel2
        assert channel1.startswith(manager.AGENT_POOL_CHANNEL_PREFIX)

    @pytest.mark.asyncio
    async def test_broadcast_agent_pool_status_no_listeners(self):
        """Broadcast works with no connected clients."""
        manager = ConnectionManager()

        # Should not raise even with no listeners
        await manager.broadcast_agent_pool_status(1, {
            "online_count": 2,
            "offline_count": 1,
            "idle_count": 1,
            "running_jobs_count": 1,
            "status": "running"
        })

    @pytest.mark.asyncio
    async def test_broadcast_agent_pool_status_with_listeners(self):
        """Broadcast sends to connected clients."""
        manager = ConnectionManager()
        team_id = 42
        channel = manager.get_agent_pool_channel(team_id)

        # Create mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()

        # Register connection
        await manager.connect(channel, mock_ws)

        # Broadcast status
        pool_status = {
            "online_count": 3,
            "offline_count": 0,
            "idle_count": 2,
            "running_jobs_count": 1,
            "status": "running"
        }
        await manager.broadcast_agent_pool_status(team_id, pool_status)

        # Verify message was sent
        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "agent_pool_status"
        assert call_args["pool_status"] == pool_status

        # Cleanup
        manager.disconnect(channel, mock_ws)

    @pytest.mark.asyncio
    async def test_broadcast_only_to_team_channel(self):
        """Broadcast only reaches the correct team's clients."""
        manager = ConnectionManager()

        # Create mock WebSockets for two teams
        team1_ws = AsyncMock()
        team1_ws.send_json = AsyncMock()
        team2_ws = AsyncMock()
        team2_ws.send_json = AsyncMock()

        # Register connections
        channel1 = manager.get_agent_pool_channel(1)
        channel2 = manager.get_agent_pool_channel(2)
        await manager.connect(channel1, team1_ws)
        await manager.connect(channel2, team2_ws)

        # Broadcast to team 1 only
        await manager.broadcast_agent_pool_status(1, {
            "online_count": 1,
            "status": "idle"
        })

        # Team 1 should receive, team 2 should not
        team1_ws.send_json.assert_called_once()
        team2_ws.send_json.assert_not_called()

        # Cleanup
        manager.disconnect(channel1, team1_ws)
        manager.disconnect(channel2, team2_ws)


class TestPoolStatusServiceIntegration:
    """Tests for pool status service with broadcasts."""

    def test_pool_status_calculation(self, test_db_session, test_team, test_user):
        """Verify pool status is calculated correctly."""
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

        status = service.get_pool_status(test_team.id)

        assert status["online_count"] == 1
        assert status["status"] == "idle"

    def test_connection_manager_singleton(self):
        """Connection manager is a singleton."""
        manager1 = get_connection_manager()
        manager2 = get_connection_manager()

        assert manager1 is manager2
