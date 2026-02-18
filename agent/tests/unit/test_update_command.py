"""
Unit tests for the update CLI command.

Tests the agent self-update command covering:
- Windows not-supported message
- Agent not registered error
- Already up to date scenario
- No active release scenario
- Platform not found scenario
- Outdated warning banner on CLI commands
- Download and replace flow (mocked)

Issue #243 - Agent CLI self-update command & outdated warnings
"""

import json

import pytest
from unittest.mock import MagicMock, patch
from click.testing import CliRunner


class TestUpdateCommandWindows:
    """Tests for the update command on Windows."""

    @pytest.fixture
    def cli_runner(self):
        return CliRunner()

    def test_windows_prints_manual_instructions(self, cli_runner):
        """On Windows, prints manual instructions and exits cleanly."""
        from cli.main import cli

        with patch("cli.update.platform") as mock_platform, \
             patch("cli.main.read_cached_version_state", return_value=None):
            mock_platform.system.return_value = "Windows"

            result = cli_runner.invoke(cli, ["update"])

        assert result.exit_code == 0
        assert "not supported on Windows" in result.output
        assert "manually" in result.output.lower()


class TestUpdateCommandNotRegistered:
    """Tests for update command when agent is not registered."""

    @pytest.fixture
    def cli_runner(self):
        return CliRunner()

    def test_not_registered_shows_error(self, cli_runner):
        """Shows error when agent is not registered."""
        from cli.main import cli

        mock_config = MagicMock()
        mock_config.is_registered = False
        mock_config.is_configured = True

        with patch("cli.update.platform") as mock_platform, \
             patch("cli.update.AgentConfig", return_value=mock_config), \
             patch("cli.main.read_cached_version_state", return_value=None):
            mock_platform.system.return_value = "Linux"

            result = cli_runner.invoke(cli, ["update"])

        assert result.exit_code == 1
        assert "not registered" in result.output

    def test_not_configured_shows_error(self, cli_runner):
        """Shows error when agent has no server URL."""
        from cli.main import cli

        mock_config = MagicMock()
        mock_config.is_registered = True
        mock_config.is_configured = False

        with patch("cli.update.platform") as mock_platform, \
             patch("cli.update.AgentConfig", return_value=mock_config), \
             patch("cli.main.read_cached_version_state", return_value=None):
            mock_platform.system.return_value = "Linux"

            result = cli_runner.invoke(cli, ["update"])

        assert result.exit_code == 1
        assert "server URL" in result.output


class TestUpdateCommandVersionCheck:
    """Tests for version checking in the update command."""

    @pytest.fixture
    def cli_runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.is_registered = True
        config.is_configured = True
        config.server_url = "http://localhost:8000"
        config.api_key = "TEST_KEY"
        return config

    def test_no_active_release(self, cli_runner, mock_config):
        """Handles no active release on server."""
        from cli.main import cli

        mock_client = MagicMock()
        mock_client.get_active_release.return_value = None

        with patch("cli.update.platform") as mock_platform, \
             patch("cli.update.AgentConfig", return_value=mock_config), \
             patch("cli.update.AgentApiClient", return_value=mock_client), \
             patch("cli.update.get_platform_identifier", return_value="linux-amd64"), \
             patch("cli.update.__version__", "v1.0.0"), \
             patch("cli.main.read_cached_version_state", return_value=None):
            mock_platform.system.return_value = "Linux"

            result = cli_runner.invoke(cli, ["update"])

        assert result.exit_code == 0
        assert "No active release" in result.output

    def test_already_up_to_date(self, cli_runner, mock_config):
        """Exits cleanly when already on latest version."""
        from cli.main import cli

        mock_client = MagicMock()
        mock_client.get_active_release.return_value = {
            "guid": "rel_01",
            "version": "v1.0.0",
            "artifacts": [
                {"platform": "linux-amd64", "checksum": "sha256:abc", "signed_url": "/dl"}
            ],
        }

        with patch("cli.update.platform") as mock_platform, \
             patch("cli.update.AgentConfig", return_value=mock_config), \
             patch("cli.update.AgentApiClient", return_value=mock_client), \
             patch("cli.update.get_platform_identifier", return_value="linux-amd64"), \
             patch("cli.update.__version__", "v1.0.0"), \
             patch("cli.update._get_current_binary_path", return_value=None), \
             patch("cli.main.read_cached_version_state", return_value=None):
            mock_platform.system.return_value = "Linux"

            result = cli_runner.invoke(cli, ["update"])

        assert result.exit_code == 0
        assert "Already up to date" in result.output

    def test_platform_not_found(self, cli_runner, mock_config):
        """Shows error when no artifact for current platform."""
        from cli.main import cli

        mock_client = MagicMock()
        mock_client.get_active_release.return_value = {
            "guid": "rel_01",
            "version": "v2.0.0",
            "artifacts": [
                {"platform": "darwin-arm64", "checksum": "sha256:abc", "signed_url": "/dl"}
            ],
        }

        with patch("cli.update.platform") as mock_platform, \
             patch("cli.update.AgentConfig", return_value=mock_config), \
             patch("cli.update.AgentApiClient", return_value=mock_client), \
             patch("cli.update.get_platform_identifier", return_value="linux-amd64"), \
             patch("cli.update.__version__", "v1.0.0"), \
             patch("cli.main.read_cached_version_state", return_value=None):
            mock_platform.system.return_value = "Linux"

            result = cli_runner.invoke(cli, ["update"])

        assert result.exit_code == 1
        assert "No binary available" in result.output
        assert "darwin-arm64" in result.output

    def test_script_mode_not_supported(self, cli_runner, mock_config):
        """Shows note when running as Python script (not frozen binary)."""
        from cli.main import cli

        mock_client = MagicMock()
        mock_client.get_active_release.return_value = {
            "guid": "rel_01",
            "version": "v2.0.0",
            "artifacts": [
                {"platform": "linux-amd64", "checksum": "sha256:abc", "signed_url": "/dl"}
            ],
        }

        with patch("cli.update.platform") as mock_platform, \
             patch("cli.update.AgentConfig", return_value=mock_config), \
             patch("cli.update.AgentApiClient", return_value=mock_client), \
             patch("cli.update.get_platform_identifier", return_value="linux-amd64"), \
             patch("cli.update.__version__", "v1.0.0"), \
             patch("cli.update._get_current_binary_path", return_value=None), \
             patch("cli.main.read_cached_version_state", return_value=None):
            mock_platform.system.return_value = "Linux"

            result = cli_runner.invoke(cli, ["update"])

        assert result.exit_code == 1
        assert "Python script" in result.output


class TestOutdatedWarningBanner:
    """Tests for the outdated warning banner shown on every CLI command."""

    @pytest.fixture
    def cli_runner(self):
        return CliRunner()

    def test_banner_shown_when_outdated(self, cli_runner):
        """Warning banner is displayed when cache says agent is outdated."""
        from cli.main import cli

        cache_state = {
            "is_outdated": True,
            "latest_version": "v2.0.0",
            "cached_at": 9999999999,  # far future
        }

        # Use the 'update' subcommand on "Windows" to trigger the group
        # callback (--help doesn't invoke it).
        with patch("cli.main.read_cached_version_state", return_value=cache_state), \
             patch("cli.update.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = cli_runner.invoke(cli, ["update"])

        assert "WARNING" in result.output
        assert "outdated" in result.output
        assert "v2.0.0" in result.output
        assert "shuttersense-agent update" in result.output

    def test_no_banner_when_not_outdated(self, cli_runner):
        """No warning banner when cache says agent is current."""
        from cli.main import cli

        cache_state = {
            "is_outdated": False,
            "latest_version": "v1.0.0",
            "cached_at": 9999999999,
        }

        with patch("cli.main.read_cached_version_state", return_value=cache_state), \
             patch("cli.update.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = cli_runner.invoke(cli, ["update"])

        assert "WARNING" not in result.output
        assert "outdated" not in result.output

    def test_no_banner_when_no_cache(self, cli_runner):
        """No warning banner when no cached version state exists."""
        from cli.main import cli

        with patch("cli.main.read_cached_version_state", return_value=None), \
             patch("cli.update.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = cli_runner.invoke(cli, ["update"])

        assert "WARNING" not in result.output

    def test_banner_with_unknown_version(self, cli_runner):
        """Warning banner shows 'unknown' when latest_version is None."""
        from cli.main import cli

        cache_state = {
            "is_outdated": True,
            "latest_version": None,
            "cached_at": 9999999999,
        }

        with patch("cli.main.read_cached_version_state", return_value=cache_state), \
             patch("cli.update.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            result = cli_runner.invoke(cli, ["update"])

        assert "WARNING" in result.output
        assert "unknown" in result.output


class TestUpdateForceFlag:
    """Tests for the --force flag on the update command."""

    @pytest.fixture
    def cli_runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_config(self):
        config = MagicMock()
        config.is_registered = True
        config.is_configured = True
        config.server_url = "http://localhost:8000"
        config.api_key = "TEST_KEY"
        return config

    def test_force_bypasses_version_check(self, cli_runner, mock_config):
        """--force proceeds even when already on latest version (but still
        requires frozen binary so will exit at that check)."""
        from cli.main import cli

        mock_client = MagicMock()
        mock_client.get_active_release.return_value = {
            "guid": "rel_01",
            "version": "v1.0.0",
            "artifacts": [
                {"platform": "linux-amd64", "checksum": "sha256:abc", "signed_url": "/dl"}
            ],
        }

        with patch("cli.update.platform") as mock_platform, \
             patch("cli.update.AgentConfig", return_value=mock_config), \
             patch("cli.update.AgentApiClient", return_value=mock_client), \
             patch("cli.update.get_platform_identifier", return_value="linux-amd64"), \
             patch("cli.update.__version__", "v1.0.0"), \
             patch("cli.update._get_current_binary_path", return_value=None), \
             patch("cli.main.read_cached_version_state", return_value=None):
            mock_platform.system.return_value = "Linux"

            result = cli_runner.invoke(cli, ["update", "--force"])

        # Should NOT say "Already up to date" since force was used
        assert "Already up to date" not in result.output
        # Will still fail because not a frozen binary
        assert "Python script" in result.output
