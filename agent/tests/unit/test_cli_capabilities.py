"""
Unit tests for capabilities CLI command.

Tests the capabilities display command.

Issue #90 - Distributed Agent Architecture (Phase 8)
Task: T137
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from click.testing import CliRunner


class TestCapabilitiesCommand:
    """Tests for the capabilities CLI command."""

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_config(self):
        """Create a mock AgentConfig."""
        config = MagicMock()
        config.authorized_roots = ["/photos", "/archive"]
        return config

    @pytest.fixture
    def mock_credential_store(self):
        """Create a mock CredentialStore."""
        store = MagicMock()
        store.list_connector_guids.return_value = [
            "con_01hgw2bbg0000000000000001",
            "con_01hgw2bbg0000000000000002",
        ]
        return store

    def test_capabilities_shows_builtin_and_connectors(self, cli_runner, mock_config, mock_credential_store):
        """Test capabilities command shows all capabilities."""
        from cli.main import cli

        with patch("cli.capabilities.AgentConfig") as mock_config_class, \
             patch("cli.capabilities.CredentialStore") as mock_store_class, \
             patch("cli.capabilities.detect_capabilities") as mock_detect:

            mock_config_class.return_value = mock_config
            mock_store_class.return_value = mock_credential_store
            mock_detect.return_value = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                "tool:photo_pairing:1.0.0",
            ]

            result = cli_runner.invoke(cli, ["capabilities"])

        assert result.exit_code == 0
        assert "local_filesystem" in result.output
        assert "photostats" in result.output
        assert "photo_pairing" in result.output
        assert "con_01hgw2bbg0000000000000001" in result.output
        assert "con_01hgw2bbg0000000000000002" in result.output

    def test_capabilities_json_output(self, cli_runner, mock_config, mock_credential_store):
        """Test capabilities command JSON output."""
        from cli.main import cli

        with patch("cli.capabilities.AgentConfig") as mock_config_class, \
             patch("cli.capabilities.CredentialStore") as mock_store_class, \
             patch("cli.capabilities.detect_capabilities") as mock_detect:

            mock_config_class.return_value = mock_config
            mock_store_class.return_value = mock_credential_store
            mock_detect.return_value = ["local_filesystem", "tool:photostats:1.0.0"]

            result = cli_runner.invoke(cli, ["capabilities", "--json"])

        assert result.exit_code == 0

        # Parse JSON output
        data = json.loads(result.output)
        assert "capabilities" in data
        assert "builtin" in data
        assert "connectors" in data
        assert "total" in data

        assert "local_filesystem" in data["builtin"]
        assert "con_01hgw2bbg0000000000000001" in data["connectors"]

    def test_capabilities_no_connectors(self, cli_runner, mock_config):
        """Test capabilities when no connectors are configured."""
        from cli.main import cli

        mock_store = MagicMock()
        mock_store.list_connector_guids.return_value = []

        with patch("cli.capabilities.AgentConfig") as mock_config_class, \
             patch("cli.capabilities.CredentialStore") as mock_store_class, \
             patch("cli.capabilities.detect_capabilities") as mock_detect:

            mock_config_class.return_value = mock_config
            mock_store_class.return_value = mock_store
            mock_detect.return_value = ["local_filesystem"]

            result = cli_runner.invoke(cli, ["capabilities"])

        assert result.exit_code == 0
        assert "(none configured)" in result.output

    def test_capabilities_shows_authorized_roots(self, cli_runner, mock_config, mock_credential_store):
        """Test capabilities shows authorized roots."""
        from cli.main import cli

        with patch("cli.capabilities.AgentConfig") as mock_config_class, \
             patch("cli.capabilities.CredentialStore") as mock_store_class, \
             patch("cli.capabilities.detect_capabilities") as mock_detect:

            mock_config_class.return_value = mock_config
            mock_store_class.return_value = mock_credential_store
            mock_detect.return_value = ["local_filesystem"]

            result = cli_runner.invoke(cli, ["capabilities"])

        assert result.exit_code == 0
        assert "Authorized Local Roots" in result.output
        assert "/photos" in result.output
        assert "/archive" in result.output

    def test_capabilities_shows_tool_versions(self, cli_runner, mock_config, mock_credential_store):
        """Test capabilities shows tool versions properly formatted."""
        from cli.main import cli

        with patch("cli.capabilities.AgentConfig") as mock_config_class, \
             patch("cli.capabilities.CredentialStore") as mock_store_class, \
             patch("cli.capabilities.detect_capabilities") as mock_detect:

            mock_config_class.return_value = mock_config
            mock_store_class.return_value = mock_credential_store
            mock_detect.return_value = [
                "tool:photostats:2.1.0",
                "tool:pipeline_validation:1.5.0",
            ]

            result = cli_runner.invoke(cli, ["capabilities"])

        assert result.exit_code == 0
        assert "photostats" in result.output
        assert "2.1.0" in result.output
        assert "pipeline_validation" in result.output
        assert "1.5.0" in result.output
