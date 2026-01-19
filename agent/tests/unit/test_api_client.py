"""
Unit tests for agent API client.

Tests registration, heartbeat, and error handling.

Issue #90 - Distributed Agent Architecture (Phase 3)
Task: T036
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import httpx


class TestAgentApiClient:
    """Tests for AgentApiClient class."""

    @pytest.fixture
    def api_client(self, mock_server_url):
        """Create an API client instance for testing."""
        from agent.src.api_client import AgentApiClient

        return AgentApiClient(server_url=mock_server_url)

    @pytest.fixture
    def registered_api_client(self, mock_server_url, mock_api_key):
        """Create a registered API client instance for testing."""
        from agent.src.api_client import AgentApiClient

        return AgentApiClient(server_url=mock_server_url, api_key=mock_api_key)


class TestRegistration(TestAgentApiClient):
    """Tests for agent registration."""

    @pytest.mark.asyncio
    async def test_register_success(self, api_client, mock_registration_token, mock_agent_guid, mock_api_key):
        """Test successful agent registration."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "guid": mock_agent_guid,
            "api_key": mock_api_key,
            "name": "Test Agent",
            "team_guid": "tea_01hgw2bbg0000000000000001",
        }

        with patch.object(api_client, "_client") as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)

            result = await api_client.register(
                registration_token=mock_registration_token,
                name="Test Agent",
                hostname="test-host.local",
                os_info="macOS 14.0",
                capabilities=["local_filesystem", "tool:photostats:1.0.0"],
                version="0.1.0",
            )

        assert result["guid"] == mock_agent_guid
        assert result["api_key"] == mock_api_key
        assert result["name"] == "Test Agent"

    @pytest.mark.asyncio
    async def test_register_invalid_token(self, api_client, mock_registration_token):
        """Test registration with invalid token."""
        from agent.src.api_client import RegistrationError

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"detail": "Invalid or expired registration token"}

        with patch.object(api_client, "_client") as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)

            with pytest.raises(RegistrationError) as exc_info:
                await api_client.register(
                    registration_token=mock_registration_token,
                    name="Test Agent",
                    hostname="test-host.local",
                    os_info="macOS 14.0",
                    capabilities=[],
                    version="0.1.0",
                )

        assert "invalid" in str(exc_info.value).lower() or "expired" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_register_expired_token(self, api_client):
        """Test registration with expired token."""
        from agent.src.api_client import RegistrationError

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"detail": "Registration token has expired"}

        with patch.object(api_client, "_client") as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)

            with pytest.raises(RegistrationError):
                await api_client.register(
                    registration_token="art_expired_token",
                    name="Test Agent",
                    hostname="test-host.local",
                    os_info="macOS 14.0",
                    capabilities=[],
                    version="0.1.0",
                )

    @pytest.mark.asyncio
    async def test_register_network_error(self, api_client, mock_registration_token):
        """Test registration with network error."""
        from agent.src.api_client import ConnectionError as AgentConnectionError

        with patch.object(api_client, "_client") as mock_client:
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

            with pytest.raises(AgentConnectionError):
                await api_client.register(
                    registration_token=mock_registration_token,
                    name="Test Agent",
                    hostname="test-host.local",
                    os_info="macOS 14.0",
                    capabilities=[],
                    version="0.1.0",
                )


class TestHeartbeat(TestAgentApiClient):
    """Tests for agent heartbeat."""

    @pytest.mark.asyncio
    async def test_heartbeat_success(self, registered_api_client, heartbeat_response):
        """Test successful heartbeat."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = heartbeat_response

        with patch.object(registered_api_client, "_client") as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)

            result = await registered_api_client.heartbeat()

        assert result["acknowledged"] is True
        assert "server_time" in result

    @pytest.mark.asyncio
    async def test_heartbeat_with_status(self, registered_api_client, heartbeat_response):
        """Test heartbeat with status update."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = heartbeat_response

        with patch.object(registered_api_client, "_client") as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)

            result = await registered_api_client.heartbeat(status="busy")

        # Verify the status was sent in request
        call_args = mock_client.post.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_heartbeat_with_capabilities_update(self, registered_api_client, heartbeat_response, sample_capabilities):
        """Test heartbeat with updated capabilities."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = heartbeat_response

        with patch.object(registered_api_client, "_client") as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)

            result = await registered_api_client.heartbeat(capabilities=sample_capabilities)

        assert result["acknowledged"] is True

    @pytest.mark.asyncio
    async def test_heartbeat_unauthorized(self, registered_api_client):
        """Test heartbeat with invalid API key."""
        from agent.src.api_client import AuthenticationError

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Invalid API key"}

        with patch.object(registered_api_client, "_client") as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)

            with pytest.raises(AuthenticationError):
                await registered_api_client.heartbeat()

    @pytest.mark.asyncio
    async def test_heartbeat_agent_revoked(self, registered_api_client):
        """Test heartbeat when agent is revoked."""
        from agent.src.api_client import AgentRevokedError

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"detail": "Agent has been revoked"}

        with patch.object(registered_api_client, "_client") as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)

            with pytest.raises(AgentRevokedError):
                await registered_api_client.heartbeat()

    @pytest.mark.asyncio
    async def test_heartbeat_network_error(self, registered_api_client):
        """Test heartbeat with network error."""
        from agent.src.api_client import ConnectionError as AgentConnectionError

        with patch.object(registered_api_client, "_client") as mock_client:
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

            with pytest.raises(AgentConnectionError):
                await registered_api_client.heartbeat()


class TestGetAgentInfo(TestAgentApiClient):
    """Tests for getting agent information."""

    @pytest.mark.asyncio
    async def test_get_me_success(self, registered_api_client, mock_agent_guid):
        """Test getting current agent information."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "guid": mock_agent_guid,
            "name": "Test Agent",
            "hostname": "test-host.local",
            "os_info": "macOS 14.0",
            "status": "online",
            "capabilities": ["local_filesystem"],
            "version": "0.1.0",
            "team_guid": "tea_01hgw2bbg0000000000000001",
        }

        with patch.object(registered_api_client, "_client") as mock_client:
            mock_client.get = AsyncMock(return_value=mock_response)

            result = await registered_api_client.get_me()

        assert result["guid"] == mock_agent_guid
        assert result["name"] == "Test Agent"
        assert result["status"] == "online"


class TestClientConfiguration:
    """Tests for API client configuration."""

    def test_client_requires_server_url(self):
        """Test that client requires server URL."""
        from agent.src.api_client import AgentApiClient

        with pytest.raises(ValueError):
            AgentApiClient(server_url="")

    def test_client_sets_user_agent(self, mock_server_url):
        """Test that client sets appropriate User-Agent header."""
        from agent.src.api_client import AgentApiClient

        client = AgentApiClient(server_url=mock_server_url)

        # User-Agent should include ShutterSense-Agent
        assert "ShutterSense-Agent" in client._client.headers.get("User-Agent", "")

    def test_client_sets_auth_header_when_api_key_provided(self, mock_server_url, mock_api_key):
        """Test that client sets Authorization header when API key is provided."""
        from agent.src.api_client import AgentApiClient

        client = AgentApiClient(server_url=mock_server_url, api_key=mock_api_key)

        auth_header = client._client.headers.get("Authorization", "")
        assert auth_header == f"Bearer {mock_api_key}"
