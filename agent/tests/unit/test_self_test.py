"""
Unit tests for self-test CLI command.

Tests the agent self-test diagnostic command covering:
- All checks pass scenario
- Server connectivity failure scenarios
- Invalid API key / revoked agent scenarios
- Inaccessible authorized root scenarios
- Warning vs failure exit codes

Issue #108 - Remove CLI Direct Usage (Phase 8)
Task: T055
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from click.testing import CliRunner

import httpx


class TestSelfTestAllPass:
    """Tests for the self-test command when all checks pass."""

    @pytest.fixture
    def cli_runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_config(self, tmp_path):
        config = MagicMock()
        config.server_url = "http://localhost:8000"
        config.api_key = "TEST_API_KEY"
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        config.authorized_roots = [str(tmp_path)]
        return config

    def test_all_checks_pass(self, cli_runner, mock_config):
        """All checks pass with valid config, reachable server, and accessible roots."""
        from cli.main import cli

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = mock_config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response
            mock_async_run.return_value = {"server_time": "2024-01-01T00:00:00"}

            result = cli_runner.invoke(cli, ["self-test"])

        assert result.exit_code == 0
        assert "all checks passed" in result.output
        assert "Agent Self-Test" in result.output

    def test_output_format_sections(self, cli_runner, mock_config):
        """Output contains all expected sections."""
        from cli.main import cli

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = mock_config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response
            mock_async_run.return_value = {"server_time": "2024-01-01T00:00:00"}

            result = cli_runner.invoke(cli, ["self-test"])

        assert "Server Connection:" in result.output
        assert "Agent Registration:" in result.output
        assert "Tools:" in result.output
        assert "Authorized Roots:" in result.output
        assert "Self-test complete:" in result.output

    def test_shows_server_url(self, cli_runner, mock_config):
        """Output displays the configured server URL."""
        from cli.main import cli

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = mock_config
            mock_detect.return_value = ["local_filesystem"]
            mock_httpx_get.return_value = mock_response
            mock_async_run.return_value = {}

            result = cli_runner.invoke(cli, ["self-test"])

        assert "http://localhost:8000" in result.output

    def test_shows_agent_guid(self, cli_runner, mock_config):
        """Output displays the agent GUID."""
        from cli.main import cli

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = mock_config
            mock_detect.return_value = ["local_filesystem"]
            mock_httpx_get.return_value = mock_response
            mock_async_run.return_value = {}

            result = cli_runner.invoke(cli, ["self-test"])

        assert "agt_01hgw2bbg0000000000000001" in result.output


class TestServerConnectivity:
    """Tests for server connectivity check failures."""

    @pytest.fixture
    def cli_runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_config(self, tmp_path):
        config = MagicMock()
        config.server_url = "http://localhost:8000"
        config.api_key = "TEST_API_KEY"
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        config.authorized_roots = [str(tmp_path)]
        return config

    def test_server_connection_refused(self, cli_runner, mock_config):
        """Exit code 2 when server connection is refused."""
        from cli.main import cli

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = mock_config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.side_effect = httpx.ConnectError("Connection refused")
            mock_async_run.return_value = {}

            result = cli_runner.invoke(cli, ["self-test"])

        assert result.exit_code == 2
        assert "Connection refused" in result.output

    def test_server_timeout(self, cli_runner, mock_config):
        """Exit code 2 when server connection times out."""
        from cli.main import cli

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = mock_config
            mock_detect.return_value = ["local_filesystem"]
            mock_httpx_get.side_effect = httpx.TimeoutException("timed out")
            mock_async_run.return_value = {}

            result = cli_runner.invoke(cli, ["self-test"])

        assert result.exit_code == 2
        assert "timed out" in result.output

    def test_no_server_url_configured(self, cli_runner):
        """Exit code 2 when no server URL is configured."""
        from cli.main import cli

        config = MagicMock()
        config.server_url = ""
        config.api_key = ""
        config.agent_guid = ""
        config.authorized_roots = []

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect:

            mock_config_class.return_value = config
            mock_detect.return_value = ["local_filesystem"]

            result = cli_runner.invoke(cli, ["self-test"])

        assert result.exit_code == 2
        assert "not configured" in result.output

    def test_server_non_200_response(self, cli_runner, mock_config):
        """Warns when server returns non-200 status."""
        from cli.main import cli

        mock_response = MagicMock()
        mock_response.status_code = 503

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = mock_config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response
            mock_async_run.return_value = {}

            result = cli_runner.invoke(cli, ["self-test"])

        # Non-200 is a warning, not failure; exit depends on other checks too
        assert "status 503" in result.output


class TestRegistration:
    """Tests for agent registration check."""

    @pytest.fixture
    def cli_runner(self):
        return CliRunner()

    def test_not_registered(self, cli_runner, tmp_path):
        """Exit code 2 when agent is not registered."""
        from cli.main import cli
        from src.api_client import AuthenticationError

        config = MagicMock()
        config.server_url = "http://localhost:8000"
        config.api_key = ""
        config.agent_guid = ""
        config.authorized_roots = [str(tmp_path)]

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get:

            mock_config_class.return_value = config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response

            result = cli_runner.invoke(cli, ["self-test"])

        assert result.exit_code == 2
        assert "not registered" in result.output

    def test_invalid_api_key(self, cli_runner, tmp_path):
        """Exit code 2 when API key is invalid."""
        from cli.main import cli
        from src.api_client import AuthenticationError

        config = MagicMock()
        config.server_url = "http://localhost:8000"
        config.api_key = "agt_key_invalid"
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        config.authorized_roots = [str(tmp_path)]

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response
            mock_async_run.side_effect = AuthenticationError("Invalid API key")

            result = cli_runner.invoke(cli, ["self-test"])

        assert result.exit_code == 2
        assert "Invalid API key" in result.output

    def test_agent_revoked(self, cli_runner, tmp_path):
        """Exit code 2 when agent has been revoked."""
        from cli.main import cli
        from src.api_client import AgentRevokedError

        config = MagicMock()
        config.server_url = "http://localhost:8000"
        config.api_key = "agt_key_revoked"
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        config.authorized_roots = [str(tmp_path)]

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response
            mock_async_run.side_effect = AgentRevokedError("Agent has been revoked")

            result = cli_runner.invoke(cli, ["self-test"])

        assert result.exit_code == 2
        assert "revoked" in result.output

    def test_server_unreachable_during_heartbeat(self, cli_runner, tmp_path):
        """Warns when server is unreachable during heartbeat (not a failure)."""
        from cli.main import cli
        from src.api_client import ConnectionError as AgentConnectionError

        config = MagicMock()
        config.server_url = "http://localhost:8000"
        config.api_key = "agt_key_test"
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        config.authorized_roots = [str(tmp_path)]

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response
            mock_async_run.side_effect = AgentConnectionError("Connection failed")

            result = cli_runner.invoke(cli, ["self-test"])

        # Connection error during heartbeat is a warning (server was reachable for health)
        assert "cannot verify" in result.output.lower()


class TestToolAvailability:
    """Tests for tool availability checks."""

    @pytest.fixture
    def cli_runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_config(self, tmp_path):
        config = MagicMock()
        config.server_url = "http://localhost:8000"
        config.api_key = "TEST_API_KEY"
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        config.authorized_roots = [str(tmp_path)]
        return config

    def test_all_tools_available(self, cli_runner, mock_config):
        """All tools show OK when detected."""
        from cli.main import cli

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = mock_config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response
            mock_async_run.return_value = {}

            result = cli_runner.invoke(cli, ["self-test"])

        assert result.exit_code == 0
        assert "photostats" in result.output
        assert "photo_pairing" in result.output
        assert "pipeline_validation" in result.output

    def test_missing_tool_warns(self, cli_runner, mock_config):
        """Missing tool shows WARN and results in exit code 1."""
        from cli.main import cli

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = mock_config
            # Only photostats available, others missing
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response
            mock_async_run.return_value = {}

            result = cli_runner.invoke(cli, ["self-test"])

        assert result.exit_code == 1
        assert "not found" in result.output
        assert "warning" in result.output.lower()

    def test_no_tools_available(self, cli_runner, mock_config):
        """All tools missing shows warnings."""
        from cli.main import cli

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = mock_config
            mock_detect.return_value = ["local_filesystem"]
            mock_httpx_get.return_value = mock_response
            mock_async_run.return_value = {}

            result = cli_runner.invoke(cli, ["self-test"])

        assert result.exit_code == 1
        assert "3 warning" in result.output


class TestAuthorizedRoots:
    """Tests for authorized root accessibility checks."""

    @pytest.fixture
    def cli_runner(self):
        return CliRunner()

    def test_accessible_root(self, cli_runner, tmp_path):
        """Accessible root shows OK."""
        from cli.main import cli

        config = MagicMock()
        config.server_url = "http://localhost:8000"
        config.api_key = "agt_key_test"
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        config.authorized_roots = [str(tmp_path)]

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response
            mock_async_run.return_value = {}

            result = cli_runner.invoke(cli, ["self-test"])

        assert result.exit_code == 0
        assert "readable" in result.output

    def test_nonexistent_root_warns(self, cli_runner, tmp_path):
        """Non-existent root shows WARN."""
        from cli.main import cli

        config = MagicMock()
        config.server_url = "http://localhost:8000"
        config.api_key = "agt_key_test"
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        config.authorized_roots = [str(tmp_path / "nonexistent")]

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response
            mock_async_run.return_value = {}

            result = cli_runner.invoke(cli, ["self-test"])

        assert result.exit_code == 1
        assert "not mounted" in result.output

    def test_no_roots_configured_warns(self, cli_runner):
        """No authorized roots configured shows WARN."""
        from cli.main import cli

        config = MagicMock()
        config.server_url = "http://localhost:8000"
        config.api_key = "agt_key_test"
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        config.authorized_roots = []

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response
            mock_async_run.return_value = {}

            result = cli_runner.invoke(cli, ["self-test"])

        assert result.exit_code == 1
        assert "none configured" in result.output

    def test_file_as_root_warns(self, cli_runner, tmp_path):
        """File path (not a directory) as root shows WARN."""
        from cli.main import cli

        # Create a file instead of a directory
        file_path = tmp_path / "not_a_dir.txt"
        file_path.write_text("test")

        config = MagicMock()
        config.server_url = "http://localhost:8000"
        config.api_key = "agt_key_test"
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        config.authorized_roots = [str(file_path)]

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response
            mock_async_run.return_value = {}

            result = cli_runner.invoke(cli, ["self-test"])

        assert result.exit_code == 1
        assert "not a directory" in result.output


class TestRemediation:
    """Tests for remediation suggestions in output."""

    @pytest.fixture
    def cli_runner(self):
        return CliRunner()

    def test_remediation_for_unregistered_agent(self, cli_runner, tmp_path):
        """Shows register suggestion when agent is not registered."""
        from cli.main import cli

        config = MagicMock()
        config.server_url = ""
        config.api_key = ""
        config.agent_guid = ""
        config.authorized_roots = [str(tmp_path)]

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect:

            mock_config_class.return_value = config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]

            result = cli_runner.invoke(cli, ["self-test"])

        assert result.exit_code == 2
        assert "Suggestions:" in result.output
        assert "register" in result.output.lower()

    def test_remediation_for_invalid_api_key(self, cli_runner, tmp_path):
        """Shows re-register suggestion when API key is invalid."""
        from cli.main import cli
        from src.api_client import AuthenticationError

        config = MagicMock()
        config.server_url = "http://localhost:8000"
        config.api_key = "agt_key_invalid"
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        config.authorized_roots = [str(tmp_path)]

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response
            mock_async_run.side_effect = AuthenticationError("Invalid API key")

            result = cli_runner.invoke(cli, ["self-test"])

        assert result.exit_code == 2
        assert "Suggestions:" in result.output
        assert "--force" in result.output

    def test_remediation_for_revoked_agent(self, cli_runner, tmp_path):
        """Shows admin contact suggestion when agent is revoked."""
        from cli.main import cli
        from src.api_client import AgentRevokedError

        config = MagicMock()
        config.server_url = "http://localhost:8000"
        config.api_key = "agt_key_revoked"
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        config.authorized_roots = [str(tmp_path)]

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response
            mock_async_run.side_effect = AgentRevokedError("Agent has been revoked")

            result = cli_runner.invoke(cli, ["self-test"])

        assert result.exit_code == 2
        assert "Suggestions:" in result.output
        assert "admin" in result.output.lower()

    def test_remediation_for_nonexistent_root(self, cli_runner, tmp_path):
        """Shows mount suggestion for non-existent root."""
        from cli.main import cli

        config = MagicMock()
        config.server_url = "http://localhost:8000"
        config.api_key = "agt_key_test"
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        nonexistent = str(tmp_path / "nonexistent_mount")
        config.authorized_roots = [nonexistent]

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response
            mock_async_run.return_value = {}

            result = cli_runner.invoke(cli, ["self-test"])

        assert "Suggestions:" in result.output
        assert "Mount or create" in result.output


class TestExitCodes:
    """Tests for correct exit code behavior."""

    @pytest.fixture
    def cli_runner(self):
        return CliRunner()

    def test_exit_0_all_pass(self, cli_runner, tmp_path):
        """Exit code 0 when all checks pass."""
        from cli.main import cli

        config = MagicMock()
        config.server_url = "http://localhost:8000"
        config.api_key = "agt_key_test"
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        config.authorized_roots = [str(tmp_path)]

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response
            mock_async_run.return_value = {}

            result = cli_runner.invoke(cli, ["self-test"])

        assert result.exit_code == 0

    def test_exit_1_warnings_only(self, cli_runner, tmp_path):
        """Exit code 1 when only warnings (no failures)."""
        from cli.main import cli

        config = MagicMock()
        config.server_url = "http://localhost:8000"
        config.api_key = "agt_key_test"
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        # Non-existent root triggers WARN, not FAIL
        config.authorized_roots = [str(tmp_path / "missing")]

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response
            mock_async_run.return_value = {}

            result = cli_runner.invoke(cli, ["self-test"])

        assert result.exit_code == 1

    def test_exit_2_failures(self, cli_runner, tmp_path):
        """Exit code 2 when failures are present."""
        from cli.main import cli
        from src.api_client import AuthenticationError

        config = MagicMock()
        config.server_url = "http://localhost:8000"
        config.api_key = "agt_key_invalid"
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        config.authorized_roots = [str(tmp_path)]

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response
            mock_async_run.side_effect = AuthenticationError("Invalid API key")

            result = cli_runner.invoke(cli, ["self-test"])

        assert result.exit_code == 2

    def test_exit_2_mixed_failures_and_warnings(self, cli_runner, tmp_path):
        """Exit code 2 when both failures and warnings exist."""
        from cli.main import cli
        from src.api_client import AuthenticationError

        config = MagicMock()
        config.server_url = "http://localhost:8000"
        config.api_key = "agt_key_invalid"
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        # Non-existent root = WARN; invalid API key = FAIL
        config.authorized_roots = [str(tmp_path / "missing")]

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = config
            mock_detect.return_value = ["local_filesystem"]
            mock_httpx_get.return_value = mock_response
            mock_async_run.side_effect = AuthenticationError("Invalid API key")

            result = cli_runner.invoke(cli, ["self-test"])

        assert result.exit_code == 2
        assert "failure" in result.output.lower()
        assert "warning" in result.output.lower()


class TestSummaryOutput:
    """Tests for summary line formatting."""

    @pytest.fixture
    def cli_runner(self):
        return CliRunner()

    def test_summary_all_pass(self, cli_runner, tmp_path):
        """Summary says 'all checks passed' when everything is OK."""
        from cli.main import cli

        config = MagicMock()
        config.server_url = "http://localhost:8000"
        config.api_key = "agt_key_test"
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        config.authorized_roots = [str(tmp_path)]

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response
            mock_async_run.return_value = {}

            result = cli_runner.invoke(cli, ["self-test"])

        assert "all checks passed" in result.output

    def test_summary_singular_warning(self, cli_runner, tmp_path):
        """Summary correctly uses singular 'warning'."""
        from cli.main import cli

        config = MagicMock()
        config.server_url = "http://localhost:8000"
        config.api_key = "agt_key_test"
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        config.authorized_roots = [str(tmp_path / "missing")]

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response
            mock_async_run.return_value = {}

            result = cli_runner.invoke(cli, ["self-test"])

        assert "1 warning" in result.output

    def test_summary_plural_warnings(self, cli_runner, tmp_path):
        """Summary correctly uses plural 'warnings'."""
        from cli.main import cli

        config = MagicMock()
        config.server_url = "http://localhost:8000"
        config.api_key = "agt_key_test"
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        config.authorized_roots = [
            str(tmp_path / "missing1"),
            str(tmp_path / "missing2"),
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("cli.self_test.AgentConfig") as mock_config_class, \
             patch("cli.self_test.detect_capabilities") as mock_detect, \
             patch("cli.self_test.httpx.get") as mock_httpx_get, \
             patch("cli.self_test.asyncio.run") as mock_async_run:

            mock_config_class.return_value = config
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
                "tool:pipeline_validation:1.0.0",
            ]
            mock_httpx_get.return_value = mock_response
            mock_async_run.return_value = {}

            result = cli_runner.invoke(cli, ["self-test"])

        assert "2 warnings" in result.output
