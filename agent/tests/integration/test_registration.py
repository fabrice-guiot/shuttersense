"""
Integration tests for agent registration flow.

End-to-end tests with mock server for the complete registration process.

Issue #90 - Distributed Agent Architecture (Phase 3)
Task: T038
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner


class TestRegistrationFlow:
    """Integration tests for the complete registration flow."""

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI runner for integration tests."""
        return CliRunner()

    @pytest.mark.asyncio
    async def test_full_registration_flow(
        self,
        temp_config_dir,
        mock_server_url,
        mock_registration_token,
        mock_agent_guid,
        mock_api_key,
        sample_capabilities,
    ):
        """Test the complete registration flow from start to finish."""
        from agent.src.config import AgentConfig
        from agent.src.api_client import AgentApiClient

        # Create a fresh config
        config = AgentConfig(config_dir=temp_config_dir)
        assert config.is_registered is False

        # Mock the API client response
        with patch.object(AgentApiClient, "register", new_callable=AsyncMock) as mock_register:
            mock_register.return_value = {
                "guid": mock_agent_guid,
                "api_key": mock_api_key,
                "name": "Integration Test Agent",
                "team_guid": "tea_01hgw2bbg0000000000000001",
            }

            # Create API client and register
            client = AgentApiClient(server_url=mock_server_url)
            result = await client.register(
                registration_token=mock_registration_token,
                name="Integration Test Agent",
                hostname="test-host.local",
                os_info="macOS 14.0",
                capabilities=sample_capabilities,
                version="0.1.0",
            )

        # Verify registration result
        assert result["guid"] == mock_agent_guid
        assert result["api_key"] == mock_api_key

        # Update config with registration info
        config.update_registration(
            agent_guid=result["guid"],
            api_key=result["api_key"],
            agent_name=result["name"],
        )
        config.server_url = mock_server_url

        # Verify config is now registered
        assert config.is_registered is True
        assert config.agent_guid == mock_agent_guid
        assert config.api_key == mock_api_key

    def test_cli_registration_flow(
        self,
        cli_runner,
        temp_config_dir,
        mock_server_url,
        mock_registration_token,
        mock_agent_guid,
        mock_api_key,
    ):
        """Test registration via CLI end-to-end."""
        from agent.cli.main import cli

        with patch("agent.cli.register.AgentConfig") as mock_config_class, \
             patch("agent.cli.register.AgentApiClient") as mock_client_class, \
             patch("agent.cli.register.get_system_info") as mock_sys_info, \
             patch("agent.cli.register.detect_capabilities") as mock_capabilities:

            # Setup config mock
            mock_config = MagicMock()
            mock_config.is_registered = False
            mock_config.server_url = ""
            mock_config.config_dir = temp_config_dir
            mock_config_class.return_value = mock_config

            # Setup API client mock with async context manager
            mock_client = MagicMock()
            mock_client.register = AsyncMock(return_value={
                "guid": mock_agent_guid,
                "api_key": mock_api_key,
                "name": "CLI Test Agent",
                "team_guid": "tea_01hgw2bbg0000000000000001",
            })
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            # Setup system info mock
            mock_sys_info.return_value = ("cli-test-host.local", "macOS 14.0")
            mock_capabilities.return_value = ["local_filesystem", "tool:photostats:1.0.0"]

            # Run the register command
            result = cli_runner.invoke(cli, [
                "register",
                "--server", mock_server_url,
                "--token", mock_registration_token,
                "--name", "CLI Test Agent",
            ])

        # Verify success
        assert result.exit_code == 0

        # Verify API client was called correctly
        mock_client.register.assert_called_once()
        call_kwargs = mock_client.register.call_args.kwargs
        assert call_kwargs["registration_token"] == mock_registration_token
        assert call_kwargs["name"] == "CLI Test Agent"
        assert "local_filesystem" in call_kwargs["capabilities"]

        # Verify config was updated
        mock_config.update_registration.assert_called_once_with(
            agent_guid=mock_agent_guid,
            api_key=mock_api_key,
            agent_name="CLI Test Agent",
        )

    def test_registration_persists_across_restarts(
        self,
        cli_runner,
        temp_config_dir,
        mock_server_url,
        mock_registration_token,
        mock_agent_guid,
        mock_api_key,
    ):
        """Test that registration information persists after agent restart."""
        from agent.src.config import AgentConfig

        # First registration
        config1 = AgentConfig(config_dir=temp_config_dir)
        config1.server_url = mock_server_url
        config1.update_registration(
            agent_guid=mock_agent_guid,
            api_key=mock_api_key,
            agent_name="Persistent Agent",
        )

        # Simulate restart by creating new config instance
        config2 = AgentConfig(config_dir=temp_config_dir)

        # Verify registration persisted
        assert config2.is_registered is True
        assert config2.agent_guid == mock_agent_guid
        assert config2.api_key == mock_api_key
        assert config2.agent_name == "Persistent Agent"
        assert config2.server_url == mock_server_url


class TestRegistrationErrors:
    """Integration tests for registration error scenarios."""

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI runner."""
        return CliRunner()

    def test_registration_with_server_down(
        self,
        cli_runner,
        temp_config_dir,
        mock_registration_token,
    ):
        """Test registration when server is unreachable."""
        from agent.cli.main import cli
        from agent.src.api_client import ConnectionError as AgentConnectionError

        with patch("agent.cli.register.AgentConfig") as mock_config_class, \
             patch("agent.cli.register.AgentApiClient") as mock_client_class, \
             patch("agent.cli.register.get_system_info") as mock_sys_info, \
             patch("agent.cli.register.detect_capabilities") as mock_capabilities:

            mock_config = MagicMock()
            mock_config.is_registered = False
            mock_config.server_url = ""
            mock_config_class.return_value = mock_config

            # Mock the async context manager properly
            mock_client = MagicMock()
            mock_client.register = AsyncMock(
                side_effect=AgentConnectionError("Connection refused")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            mock_sys_info.return_value = ("test-host.local", "macOS 14.0")
            mock_capabilities.return_value = ["local_filesystem"]

            result = cli_runner.invoke(cli, [
                "register",
                "--server", "http://unreachable-server:8000",
                "--token", mock_registration_token,
                "--name", "Test Agent",
            ])

        assert result.exit_code != 0
        assert "connection" in result.output.lower() or "error" in result.output.lower()

    def test_registration_with_invalid_token(
        self,
        cli_runner,
        temp_config_dir,
    ):
        """Test registration with an invalid token."""
        from agent.cli.main import cli
        from agent.src.api_client import RegistrationError

        with patch("agent.cli.register.AgentConfig") as mock_config_class, \
             patch("agent.cli.register.AgentApiClient") as mock_client_class, \
             patch("agent.cli.register.get_system_info") as mock_sys_info, \
             patch("agent.cli.register.detect_capabilities") as mock_capabilities:

            mock_config = MagicMock()
            mock_config.is_registered = False
            mock_config.server_url = ""
            mock_config_class.return_value = mock_config

            # Mock the async context manager properly
            mock_client = MagicMock()
            mock_client.register = AsyncMock(
                side_effect=RegistrationError("Invalid registration token")
            )
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            mock_sys_info.return_value = ("test-host.local", "macOS 14.0")
            mock_capabilities.return_value = ["local_filesystem"]

            result = cli_runner.invoke(cli, [
                "register",
                "--server", "http://localhost:8000",
                "--token", "art_invalid_token_12345",
                "--name", "Test Agent",
            ])

        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "token" in result.output.lower()


class TestPostRegistration:
    """Integration tests for post-registration functionality."""

    @pytest.mark.asyncio
    async def test_heartbeat_after_registration(
        self,
        temp_config_dir,
        mock_server_url,
        mock_agent_guid,
        mock_api_key,
        heartbeat_response,
    ):
        """Test that heartbeat works after registration."""
        from agent.src.config import AgentConfig
        from agent.src.api_client import AgentApiClient

        # Setup registered config
        config = AgentConfig(config_dir=temp_config_dir)
        config.server_url = mock_server_url
        config.update_registration(
            agent_guid=mock_agent_guid,
            api_key=mock_api_key,
            agent_name="Heartbeat Test Agent",
        )

        # Create authenticated API client
        with patch.object(AgentApiClient, "heartbeat", new_callable=AsyncMock) as mock_heartbeat:
            mock_heartbeat.return_value = heartbeat_response

            client = AgentApiClient(server_url=config.server_url, api_key=config.api_key)
            result = await client.heartbeat()

        assert result["acknowledged"] is True

    @pytest.mark.asyncio
    async def test_get_agent_info_after_registration(
        self,
        temp_config_dir,
        mock_server_url,
        mock_agent_guid,
        mock_api_key,
    ):
        """Test getting agent info after registration."""
        from agent.src.config import AgentConfig
        from agent.src.api_client import AgentApiClient

        # Setup registered config
        config = AgentConfig(config_dir=temp_config_dir)
        config.server_url = mock_server_url
        config.update_registration(
            agent_guid=mock_agent_guid,
            api_key=mock_api_key,
            agent_name="Info Test Agent",
        )

        # Create authenticated API client
        with patch.object(AgentApiClient, "get_me", new_callable=AsyncMock) as mock_get_me:
            mock_get_me.return_value = {
                "guid": mock_agent_guid,
                "name": "Info Test Agent",
                "status": "online",
                "hostname": "test-host.local",
                "os_info": "macOS 14.0",
                "capabilities": ["local_filesystem"],
                "version": "0.1.0",
            }

            client = AgentApiClient(server_url=config.server_url, api_key=config.api_key)
            result = await client.get_me()

        assert result["guid"] == mock_agent_guid
        assert result["name"] == "Info Test Agent"
        assert result["status"] == "online"
