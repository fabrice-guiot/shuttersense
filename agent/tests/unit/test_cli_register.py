"""
Unit tests for register CLI command.

Tests argument parsing, success flow, and error handling.

Issue #90 - Distributed Agent Architecture (Phase 3)
Task: T037
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner


class TestRegisterCommand:
    """Tests for the register CLI command."""

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_config(self, temp_config_dir):
        """Create a mock AgentConfig."""
        config = MagicMock()
        config.server_url = ""
        config.api_key = ""
        config.agent_guid = ""
        config.is_registered = False
        config.config_path = temp_config_dir / "agent-config.yaml"
        return config

    def test_register_with_all_arguments(self, cli_runner, temp_config_dir, mock_registration_token, mock_agent_guid, mock_api_key):
        """Test register command with all required arguments."""
        from cli.main import cli

        with patch("cli.register.AgentConfig") as mock_config_class, \
             patch("cli.register.AgentApiClient") as mock_client_class, \
             patch("cli.register.get_system_info") as mock_sys_info, \
             patch("cli.register.detect_capabilities") as mock_capabilities:

            # Setup mocks
            mock_config = MagicMock()
            mock_config.is_registered = False
            mock_config.server_url = ""
            mock_config_class.return_value = mock_config

            mock_client = MagicMock()
            mock_client.register = AsyncMock(return_value={
                "guid": mock_agent_guid,
                "api_key": mock_api_key,
                "name": "Test Agent",
                "team_guid": "tea_01hgw2bbg0000000000000001",
            })
            mock_client_class.return_value = mock_client

            mock_sys_info.return_value = ("test-host.local", "macOS 14.0")
            mock_capabilities.return_value = ["local_filesystem"]

            result = cli_runner.invoke(cli, [
                "register",
                "--server", "http://localhost:8000",
                "--token", mock_registration_token,
                "--name", "Test Agent",
            ])

        assert result.exit_code == 0
        assert "success" in result.output.lower() or "registered" in result.output.lower()

    def test_register_requires_server_argument(self, cli_runner, mock_registration_token):
        """Test that register command requires --server argument."""
        from cli.main import cli

        result = cli_runner.invoke(cli, [
            "register",
            "--token", mock_registration_token,
            "--name", "Test Agent",
        ])

        assert result.exit_code != 0
        assert "server" in result.output.lower() or "required" in result.output.lower()

    def test_register_requires_token_argument(self, cli_runner):
        """Test that register command requires --token argument."""
        from cli.main import cli

        result = cli_runner.invoke(cli, [
            "register",
            "--server", "http://localhost:8000",
            "--name", "Test Agent",
        ])

        assert result.exit_code != 0
        assert "token" in result.output.lower() or "required" in result.output.lower()

    def test_register_uses_hostname_as_default_name(self, cli_runner, temp_config_dir, mock_registration_token, mock_agent_guid, mock_api_key):
        """Test that register uses hostname as default agent name."""
        from cli.main import cli

        with patch("cli.register.AgentConfig") as mock_config_class, \
             patch("cli.register.AgentApiClient") as mock_client_class, \
             patch("cli.register.get_system_info") as mock_sys_info, \
             patch("cli.register.detect_capabilities") as mock_capabilities:

            mock_config = MagicMock()
            mock_config.is_registered = False
            mock_config.server_url = ""
            mock_config_class.return_value = mock_config

            mock_client = MagicMock()
            mock_client.register = AsyncMock(return_value={
                "guid": mock_agent_guid,
                "api_key": mock_api_key,
                "name": "test-host.local",
                "team_guid": "tea_01hgw2bbg0000000000000001",
            })
            mock_client_class.return_value = mock_client

            mock_sys_info.return_value = ("test-host.local", "macOS 14.0")
            mock_capabilities.return_value = ["local_filesystem"]

            result = cli_runner.invoke(cli, [
                "register",
                "--server", "http://localhost:8000",
                "--token", mock_registration_token,
                # No --name provided, should use hostname
            ])

        assert result.exit_code == 0

    def test_register_already_registered_warns(self, cli_runner, mock_registration_token):
        """Test that register warns if agent is already registered."""
        from cli.main import cli

        with patch("cli.register.AgentConfig") as mock_config_class:
            mock_config = MagicMock()
            mock_config.is_registered = True
            mock_config.agent_guid = "agt_01hgw2bbg0000000000000001"
            mock_config.server_url = "http://localhost:8000"
            mock_config_class.return_value = mock_config

            result = cli_runner.invoke(cli, [
                "register",
                "--server", "http://localhost:8000",
                "--token", mock_registration_token,
            ])

        # Should either warn and exit or prompt for confirmation
        assert "already registered" in result.output.lower() or result.exit_code != 0

    def test_register_force_reregisters(self, cli_runner, temp_config_dir, mock_registration_token, mock_agent_guid, mock_api_key):
        """Test that --force flag allows re-registration."""
        from cli.main import cli

        with patch("cli.register.AgentConfig") as mock_config_class, \
             patch("cli.register.AgentApiClient") as mock_client_class, \
             patch("cli.register.get_system_info") as mock_sys_info, \
             patch("cli.register.detect_capabilities") as mock_capabilities:

            mock_config = MagicMock()
            mock_config.is_registered = True
            mock_config.agent_guid = "agt_old_agent_guid"
            mock_config.server_url = "http://localhost:8000"
            mock_config_class.return_value = mock_config

            mock_client = MagicMock()
            mock_client.register = AsyncMock(return_value={
                "guid": mock_agent_guid,
                "api_key": mock_api_key,
                "name": "Test Agent",
                "team_guid": "tea_01hgw2bbg0000000000000001",
            })
            mock_client_class.return_value = mock_client

            mock_sys_info.return_value = ("test-host.local", "macOS 14.0")
            mock_capabilities.return_value = ["local_filesystem"]

            result = cli_runner.invoke(cli, [
                "register",
                "--server", "http://localhost:8000",
                "--token", mock_registration_token,
                "--name", "Test Agent",
                "--force",
            ])

        assert result.exit_code == 0

    def test_register_invalid_token_error(self, cli_runner, temp_config_dir):
        """Test register command with invalid token shows error."""
        from cli.main import cli
        from src.api_client import RegistrationError

        with patch("cli.register.AgentConfig") as mock_config_class, \
             patch("cli.register.AgentApiClient") as mock_client_class, \
             patch("cli.register.get_system_info") as mock_sys_info, \
             patch("cli.register.detect_capabilities") as mock_capabilities:

            mock_config = MagicMock()
            mock_config.is_registered = False
            mock_config.server_url = ""
            mock_config_class.return_value = mock_config

            # Mock the async context manager properly
            mock_client = MagicMock()
            mock_client.register = AsyncMock(side_effect=RegistrationError("Invalid or expired token"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            mock_sys_info.return_value = ("test-host.local", "macOS 14.0")
            mock_capabilities.return_value = ["local_filesystem"]

            result = cli_runner.invoke(cli, [
                "register",
                "--server", "http://localhost:8000",
                "--token", "art_invalid_token",
                "--name", "Test Agent",
            ])

        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "error" in result.output.lower()

    def test_register_connection_error(self, cli_runner, temp_config_dir, mock_registration_token):
        """Test register command with connection error shows error."""
        from cli.main import cli
        from src.api_client import ConnectionError as AgentConnectionError

        with patch("cli.register.AgentConfig") as mock_config_class, \
             patch("cli.register.AgentApiClient") as mock_client_class, \
             patch("cli.register.get_system_info") as mock_sys_info, \
             patch("cli.register.detect_capabilities") as mock_capabilities:

            mock_config = MagicMock()
            mock_config.is_registered = False
            mock_config.server_url = ""
            mock_config_class.return_value = mock_config

            # Mock the async context manager properly
            mock_client = MagicMock()
            mock_client.register = AsyncMock(side_effect=AgentConnectionError("Connection refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            mock_sys_info.return_value = ("test-host.local", "macOS 14.0")
            mock_capabilities.return_value = ["local_filesystem"]

            result = cli_runner.invoke(cli, [
                "register",
                "--server", "http://localhost:8000",
                "--token", mock_registration_token,
                "--name", "Test Agent",
            ])

        assert result.exit_code != 0
        assert "connection" in result.output.lower() or "error" in result.output.lower()


class TestRegisterCommandOutput:
    """Tests for register command output formatting."""

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI runner."""
        return CliRunner()

    def test_register_shows_agent_guid_on_success(self, cli_runner, temp_config_dir, mock_registration_token, mock_agent_guid, mock_api_key):
        """Test that successful registration shows the agent GUID."""
        from cli.main import cli

        with patch("cli.register.AgentConfig") as mock_config_class, \
             patch("cli.register.AgentApiClient") as mock_client_class, \
             patch("cli.register.get_system_info") as mock_sys_info, \
             patch("cli.register.detect_capabilities") as mock_capabilities:

            mock_config = MagicMock()
            mock_config.is_registered = False
            mock_config.server_url = ""
            mock_config.config_path = temp_config_dir / "agent-config.yaml"
            mock_config_class.return_value = mock_config

            # Mock the async context manager properly
            mock_client = MagicMock()
            mock_client.register = AsyncMock(return_value={
                "guid": mock_agent_guid,
                "api_key": mock_api_key,
                "name": "Test Agent",
                "team_guid": "tea_01hgw2bbg0000000000000001",
            })
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            mock_sys_info.return_value = ("test-host.local", "macOS 14.0")
            mock_capabilities.return_value = ["local_filesystem"]

            result = cli_runner.invoke(cli, [
                "register",
                "--server", "http://localhost:8000",
                "--token", mock_registration_token,
                "--name", "Test Agent",
            ])

        assert mock_agent_guid in result.output or "agt_" in result.output

    def test_register_saves_config_on_success(self, cli_runner, temp_config_dir, mock_registration_token, mock_agent_guid, mock_api_key):
        """Test that successful registration saves the configuration."""
        from cli.main import cli

        with patch("cli.register.AgentConfig") as mock_config_class, \
             patch("cli.register.AgentApiClient") as mock_client_class, \
             patch("cli.register.get_system_info") as mock_sys_info, \
             patch("cli.register.detect_capabilities") as mock_capabilities:

            mock_config = MagicMock()
            mock_config.is_registered = False
            mock_config.server_url = ""
            mock_config_class.return_value = mock_config

            mock_client = MagicMock()
            mock_client.register = AsyncMock(return_value={
                "guid": mock_agent_guid,
                "api_key": mock_api_key,
                "name": "Test Agent",
                "team_guid": "tea_01hgw2bbg0000000000000001",
            })
            mock_client_class.return_value = mock_client

            mock_sys_info.return_value = ("test-host.local", "macOS 14.0")
            mock_capabilities.return_value = ["local_filesystem"]

            cli_runner.invoke(cli, [
                "register",
                "--server", "http://localhost:8000",
                "--token", mock_registration_token,
                "--name", "Test Agent",
            ])

        # Verify update_registration was called
        mock_config.update_registration.assert_called_once()
