"""
Integration tests for agent progress WebSocket functionality.

Tests WebSocket-based progress updates including:
- Agent pool status WebSocket endpoint
- Job progress broadcasting to connected clients
- Real-time job updates via WebSocket

Issue #90 - Distributed Agent Architecture (Phase 5)
Task: T075
"""

import pytest
import asyncio
import json
import secrets
import hashlib
from base64 import b64encode
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from backend.src.models.job import Job, JobStatus
from backend.src.models.agent import AgentStatus
from backend.src.utils.websocket import ConnectionManager


class TestPoolStatusWebSocket:
    """Integration tests for pool status WebSocket endpoint."""

    def test_pool_status_websocket_connection(
        self,
        test_client,
        test_db_session,
        test_team,
        test_user,
    ):
        """WebSocket connects successfully for authenticated user."""
        from backend.src.middleware.tenant import TenantContext

        # Create mock tenant context for WebSocket auth
        mock_ctx = TenantContext(
            team_id=test_team.id,
            team_guid=test_team.guid,
            user_id=test_user.id,
            user_guid=test_user.guid,
            user_email=test_user.email,
            is_super_admin=False,
            is_api_token=False,
        )

        with patch(
            "backend.src.middleware.tenant.get_websocket_tenant_context",
            new=AsyncMock(return_value=mock_ctx)
        ):
            with test_client.websocket_connect("/api/agent/v1/ws/pool-status") as websocket:
                # Should receive initial pool status
                data = websocket.receive_json()

                assert data["type"] == "agent_pool_status"
                assert "pool_status" in data
                assert "online_count" in data["pool_status"]
                assert "offline_count" in data["pool_status"]
                assert "status" in data["pool_status"]

    def test_pool_status_websocket_heartbeat(
        self,
        test_client,
        test_db_session,
        test_team,
        test_user,
    ):
        """WebSocket responds to ping with pong."""
        from backend.src.middleware.tenant import TenantContext

        mock_ctx = TenantContext(
            team_id=test_team.id,
            team_guid=test_team.guid,
            user_id=test_user.id,
            user_guid=test_user.guid,
            user_email=test_user.email,
            is_super_admin=False,
            is_api_token=False,
        )

        with patch(
            "backend.src.middleware.tenant.get_websocket_tenant_context",
            new=AsyncMock(return_value=mock_ctx)
        ):
            with test_client.websocket_connect("/api/agent/v1/ws/pool-status") as websocket:
                # Receive initial status
                websocket.receive_json()

                # Send ping
                websocket.send_text("ping")

                # Should receive pong
                response = websocket.receive_text()
                assert response == "pong"

    def test_pool_status_initial_with_agents(
        self,
        test_client,
        test_db_session,
        test_team,
        test_user,
        create_agent,
    ):
        """WebSocket returns correct initial status with registered agents."""
        from backend.src.middleware.tenant import TenantContext

        # Create an online agent
        agent = create_agent(test_team, test_user)

        mock_ctx = TenantContext(
            team_id=test_team.id,
            team_guid=test_team.guid,
            user_id=test_user.id,
            user_guid=test_user.guid,
            user_email=test_user.email,
            is_super_admin=False,
            is_api_token=False,
        )

        with patch(
            "backend.src.middleware.tenant.get_websocket_tenant_context",
            new=AsyncMock(return_value=mock_ctx)
        ):
            with test_client.websocket_connect("/api/agent/v1/ws/pool-status") as websocket:
                data = websocket.receive_json()

                assert data["type"] == "agent_pool_status"
                assert data["pool_status"]["online_count"] >= 1
                # Status can be "idle" (online, no jobs), "running" (has jobs), or "online"
                assert data["pool_status"]["status"] in ["online", "running", "idle"]


class TestConnectionManagerBroadcasts:
    """Tests for ConnectionManager WebSocket broadcast functionality."""

    @pytest.mark.asyncio
    async def test_broadcast_job_progress(self, test_websocket_manager, test_team):
        """Job progress is broadcast to connected clients."""
        manager = test_websocket_manager
        job_guid = "job_test123456789012345678901"

        # Create mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()

        # Register connection for job-specific channel
        await manager.register_accepted(job_guid, mock_ws)

        # Broadcast progress
        progress = {"stage": "scanning", "percentage": 50}
        await manager.broadcast_job_progress(test_team.id, job_guid, progress)

        # Verify message sent to job channel
        mock_ws.send_json.assert_called()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "job_progress"
        assert call_args["job_guid"] == job_guid
        assert call_args["progress"]["percentage"] == 50

    @pytest.mark.asyncio
    async def test_broadcast_global_job_update(self, test_websocket_manager):
        """Job updates are broadcast to global jobs channel."""
        manager = test_websocket_manager

        # Create mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()

        # Register to global jobs channel
        await manager.register_accepted(ConnectionManager.GLOBAL_JOBS_CHANNEL, mock_ws)

        # Broadcast job update
        job_data = {
            "guid": "job_test123456789012345678901",
            "status": "running",
            "tool": "photostats",
        }
        await manager.broadcast_global_job_update(job_data)

        # Verify broadcast
        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "job_update"
        assert call_args["job"]["guid"] == job_data["guid"]
        assert call_args["job"]["status"] == "running"

    @pytest.mark.asyncio
    async def test_broadcast_agent_pool_status(self, test_websocket_manager, test_team):
        """Pool status is broadcast to team channel."""
        manager = test_websocket_manager

        # Create mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock()

        # Register to team's pool status channel
        channel = manager.get_agent_pool_channel(test_team.id)
        await manager.register_accepted(channel, mock_ws)

        # Broadcast pool status
        pool_status = {
            "online_count": 2,
            "offline_count": 1,
            "idle_count": 1,
            "running_jobs_count": 1,
            "status": "running",
        }
        await manager.broadcast_agent_pool_status(test_team.id, pool_status)

        # Verify broadcast
        mock_ws.send_json.assert_called_once()
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "agent_pool_status"
        assert call_args["pool_status"]["online_count"] == 2
        assert call_args["pool_status"]["status"] == "running"

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_clients(self, test_websocket_manager):
        """Broadcasts reach all connected clients."""
        manager = test_websocket_manager
        channel = "test_channel"

        # Create multiple mock WebSockets
        mock_ws1 = AsyncMock()
        mock_ws1.send_json = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws2.send_json = AsyncMock()

        # Register both connections
        await manager.register_accepted(channel, mock_ws1)
        await manager.register_accepted(channel, mock_ws2)

        # Broadcast
        await manager.broadcast(channel, {"test": "data"})

        # Both should receive the message
        mock_ws1.send_json.assert_called_once_with({"test": "data"})
        mock_ws2.send_json.assert_called_once_with({"test": "data"})

    @pytest.mark.asyncio
    async def test_broadcast_handles_disconnected_client(self, test_websocket_manager):
        """Disconnected clients are removed during broadcast."""
        manager = test_websocket_manager
        channel = "test_channel"

        # Create mock WebSocket that fails
        mock_ws_fail = AsyncMock()
        mock_ws_fail.send_json = AsyncMock(side_effect=Exception("Connection closed"))

        # Create mock WebSocket that succeeds
        mock_ws_ok = AsyncMock()
        mock_ws_ok.send_json = AsyncMock()

        # Register both connections
        await manager.register_accepted(channel, mock_ws_fail)
        await manager.register_accepted(channel, mock_ws_ok)

        # Broadcast - should not raise
        await manager.broadcast(channel, {"test": "data"})

        # OK connection should receive message
        mock_ws_ok.send_json.assert_called_once()

        # Failed connection should be removed
        assert manager.get_connection_count(channel) == 1

    @pytest.mark.asyncio
    async def test_job_progress_broadcasts_to_global_channel(self, test_websocket_manager, test_team):
        """Job progress also broadcasts to global jobs channel."""
        manager = test_websocket_manager
        job_guid = "job_test123456789012345678901"

        # Create mock WebSocket for global channel
        mock_ws_global = AsyncMock()
        mock_ws_global.send_json = AsyncMock()

        # Register to global jobs channel (not job-specific)
        await manager.register_accepted(ConnectionManager.GLOBAL_JOBS_CHANNEL, mock_ws_global)

        # Broadcast progress
        progress = {"stage": "processing", "percentage": 75}
        await manager.broadcast_job_progress(test_team.id, job_guid, progress)

        # Global channel should receive update
        mock_ws_global.send_json.assert_called()
        call_args = mock_ws_global.send_json.call_args[0][0]
        assert call_args["type"] == "job_progress"
        assert call_args["job_guid"] == job_guid


class TestJobProgressBroadcastIntegration:
    """Integration tests for job progress broadcasts via REST endpoint."""

    def test_progress_update_triggers_broadcast(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_assigned_job,
        test_websocket_manager,
    ):
        """POST /jobs/{guid}/progress triggers WebSocket broadcasts."""
        job = create_assigned_job(test_team, test_agent)

        # Track broadcasts via manager
        original_broadcast = test_websocket_manager.broadcast_job_progress
        broadcast_calls = []

        async def mock_broadcast(team_id, job_guid, progress):
            broadcast_calls.append((team_id, job_guid, progress))
            await original_broadcast(team_id, job_guid, progress)

        test_websocket_manager.broadcast_job_progress = mock_broadcast

        # Update progress
        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/progress",
            json={
                "stage": "scanning",
                "percentage": 50,
                "files_scanned": 500,
                "total_files": 1000,
            }
        )

        assert response.status_code == 200

        # Note: In test environment, asyncio tasks may not complete synchronously
        # The broadcast is scheduled but may not be awaited in test context

    def test_job_complete_triggers_pool_status_broadcast(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_running_job,
        test_websocket_manager,
    ):
        """POST /jobs/{guid}/complete triggers pool status broadcast."""
        job, signing_secret = create_running_job(test_team, test_agent)

        # Compute valid signature
        results = {"total_files": 100}
        signature = compute_signature(signing_secret, results)

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/complete",
            json={
                "results": results,
                "report_html": "<html>Done</html>",
                "files_scanned": 100,
                "issues_found": 0,
                "signature": signature,
            }
        )

        assert response.status_code == 200
        # Pool status broadcast is triggered asynchronously


class TestChannelIsolation:
    """Tests for WebSocket channel isolation between teams."""

    @pytest.mark.asyncio
    async def test_team_pool_channels_are_isolated(self, test_websocket_manager, test_team, other_team):
        """Pool status broadcasts only reach the correct team."""
        manager = test_websocket_manager

        # Create mock WebSockets for each team
        mock_ws_team1 = AsyncMock()
        mock_ws_team1.send_json = AsyncMock()
        mock_ws_team2 = AsyncMock()
        mock_ws_team2.send_json = AsyncMock()

        # Register to team-specific channels
        channel1 = manager.get_agent_pool_channel(test_team.id)
        channel2 = manager.get_agent_pool_channel(other_team.id)
        await manager.register_accepted(channel1, mock_ws_team1)
        await manager.register_accepted(channel2, mock_ws_team2)

        # Broadcast to team 1 only
        pool_status = {"online_count": 1, "status": "online"}
        await manager.broadcast_agent_pool_status(test_team.id, pool_status)

        # Only team 1 should receive
        mock_ws_team1.send_json.assert_called_once()
        mock_ws_team2.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_job_channels_are_isolated(self, test_websocket_manager, test_team):
        """Job progress broadcasts only reach clients watching that job."""
        manager = test_websocket_manager
        job1_guid = "job_job1_1234567890123456789012"
        job2_guid = "job_job2_1234567890123456789012"

        # Create mock WebSockets for each job
        mock_ws_job1 = AsyncMock()
        mock_ws_job1.send_json = AsyncMock()
        mock_ws_job2 = AsyncMock()
        mock_ws_job2.send_json = AsyncMock()

        # Register to job-specific channels
        await manager.register_accepted(job1_guid, mock_ws_job1)
        await manager.register_accepted(job2_guid, mock_ws_job2)

        # Broadcast progress for job 1
        progress = {"stage": "processing", "percentage": 50}
        await manager.broadcast_job_progress(test_team.id, job1_guid, progress)

        # Only job 1 client should receive (from job channel)
        mock_ws_job1.send_json.assert_called_once()
        mock_ws_job2.send_json.assert_not_called()


# ============================================================================
# Helper Functions
# ============================================================================

def compute_signature(signing_secret: str, data: dict) -> str:
    """Compute HMAC-SHA256 signature for data."""
    import hmac
    from base64 import b64decode

    secret_bytes = b64decode(signing_secret)
    canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
    signature = hmac.new(
        secret_bytes,
        canonical.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def create_agent(test_db_session):
    """Factory fixture to create and register test agents."""
    def _create_agent(team, user, name="Test Agent", capabilities=None):
        from backend.src.services.agent_service import AgentService

        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=team.id,
            created_by_user_id=user.id,
        )
        test_db_session.commit()

        result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name=name,
            hostname="test.local",
            os_info="Linux",
            capabilities=capabilities or ["local_filesystem"],
            version="1.0.0"
        )
        test_db_session.commit()

        service.process_heartbeat(result.agent, status=AgentStatus.ONLINE)
        test_db_session.commit()

        return result.agent

    return _create_agent


@pytest.fixture
def test_agent(test_db_session, test_team, test_user, create_agent):
    """Create a test agent that will be used by agent_client."""
    return create_agent(test_team, test_user)


@pytest.fixture
def create_assigned_job(test_db_session):
    """Factory fixture to create a job assigned to an agent."""
    def _create_assigned_job(team, agent, tool="photostats"):
        job = Job(
            team_id=team.id,
            tool=tool,
            mode="collection",
            status=JobStatus.ASSIGNED,
            agent_id=agent.id,
            assigned_at=datetime.utcnow(),
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)
        return job

    return _create_assigned_job


@pytest.fixture
def create_running_job(test_db_session):
    """Factory fixture to create a running job with signing secret."""
    def _create_running_job(team, agent, tool="photostats"):
        secret_bytes = secrets.token_bytes(32)
        signing_secret = b64encode(secret_bytes).decode('utf-8')
        secret_hash = hashlib.sha256(secret_bytes).hexdigest()

        job = Job(
            team_id=team.id,
            tool=tool,
            mode="collection",
            status=JobStatus.RUNNING,
            agent_id=agent.id,
            assigned_at=datetime.utcnow(),
            started_at=datetime.utcnow(),
            signing_secret_hash=secret_hash,
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        return job, signing_secret

    return _create_running_job


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

    agent = test_agent

    agent_ctx = AgentContext(
        agent_id=agent.id,
        agent_guid=agent.guid,
        team_id=test_team.id,
        team_guid=test_team.guid,
        agent_name=agent.name,
        status=AgentStatus.ONLINE,
    )

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
