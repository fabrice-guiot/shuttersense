"""
Unit tests for connectors CLI commands.

Tests connector listing, credential display, and removal.

Issue #90 - Distributed Agent Architecture (Phase 8)
Task: T136
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from click.testing import CliRunner


class TestConnectorsListCommand:
    """Tests for the connectors list CLI command."""

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_api_client(self):
        """Create a mock API client."""
        client = MagicMock()
        return client

    def test_list_shows_connectors(self, cli_runner, mock_api_client):
        """Test list command shows connectors in table format."""
        from cli.main import cli

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "connectors": [
                {
                    "guid": "con_01hgw2bbg0000000000000001",
                    "name": "AWS Production",
                    "type": "s3",
                    "credential_location": "pending",
                    "has_local_credentials": False,
                },
                {
                    "guid": "con_01hgw2bbg0000000000000002",
                    "name": "NAS Share",
                    "type": "smb",
                    "credential_location": "agent",
                    "has_local_credentials": True,
                },
            ],
            "total": 2,
        }
        mock_api_client.get.return_value = mock_response

        with patch("cli.connectors._get_api_client") as mock_get_client:
            mock_get_client.return_value = mock_api_client

            result = cli_runner.invoke(cli, ["connectors", "list"])

        assert result.exit_code == 0
        assert "AWS Production" in result.output
        assert "NAS Share" in result.output
        assert "S3" in result.output
        assert "SMB" in result.output
        assert "Pending" in result.output
        assert "Agent" in result.output
        assert "Total: 2" in result.output

    def test_list_pending_only(self, cli_runner, mock_api_client):
        """Test list command with --pending flag."""
        from cli.main import cli

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "connectors": [
                {
                    "guid": "con_01hgw2bbg0000000000000001",
                    "name": "AWS Production",
                    "type": "s3",
                    "credential_location": "pending",
                    "has_local_credentials": False,
                },
            ],
            "total": 1,
        }
        mock_api_client.get.return_value = mock_response

        with patch("cli.connectors._get_api_client") as mock_get_client:
            mock_get_client.return_value = mock_api_client

            result = cli_runner.invoke(cli, ["connectors", "list", "--pending"])

        assert result.exit_code == 0
        # Verify the API was called with pending_only=true
        mock_api_client.get.assert_called_once_with("/connectors?pending_only=true")

    def test_list_json_output(self, cli_runner, mock_api_client):
        """Test list command with --json flag."""
        from cli.main import cli

        expected_data = {
            "connectors": [
                {
                    "guid": "con_01hgw2bbg0000000000000001",
                    "name": "AWS Production",
                    "type": "s3",
                    "credential_location": "pending",
                    "has_local_credentials": False,
                },
            ],
            "total": 1,
        }
        mock_response = MagicMock()
        mock_response.json.return_value = expected_data
        mock_api_client.get.return_value = mock_response

        with patch("cli.connectors._get_api_client") as mock_get_client:
            mock_get_client.return_value = mock_api_client

            result = cli_runner.invoke(cli, ["connectors", "list", "--json"])

        assert result.exit_code == 0
        output_data = json.loads(result.output)
        assert output_data == expected_data

    def test_list_not_registered(self, cli_runner):
        """Test list command when agent is not registered."""
        from cli.main import cli

        with patch("cli.connectors._get_api_client") as mock_get_client:
            mock_get_client.return_value = None

            result = cli_runner.invoke(cli, ["connectors", "list"])

        assert result.exit_code == 1
        assert "not registered" in result.output.lower()

    def test_list_no_connectors(self, cli_runner, mock_api_client):
        """Test list command when no connectors are available."""
        from cli.main import cli

        mock_response = MagicMock()
        mock_response.json.return_value = {"connectors": [], "total": 0}
        mock_api_client.get.return_value = mock_response

        with patch("cli.connectors._get_api_client") as mock_get_client:
            mock_get_client.return_value = mock_api_client

            result = cli_runner.invoke(cli, ["connectors", "list"])

        assert result.exit_code == 0
        assert "no connectors" in result.output.lower()


class TestConnectorsShowCommand:
    """Tests for the connectors show CLI command."""

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_credential_store(self):
        """Create a mock CredentialStore."""
        store = MagicMock()
        return store

    def test_show_displays_masked_credentials(self, cli_runner, mock_credential_store):
        """Test show command displays credentials with sensitive values masked."""
        from cli.main import cli

        mock_credential_store.get_credentials.return_value = {
            "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "region": "us-east-1",
        }

        with patch("cli.connectors.CredentialStore") as mock_store_class:
            mock_store_class.return_value = mock_credential_store

            result = cli_runner.invoke(cli, [
                "connectors", "show", "con_01hgw2bbg0000000000000001"
            ])

        assert result.exit_code == 0
        # Access key should be partially masked
        assert "AKIA" in result.output
        assert "****" in result.output
        # Region should be visible
        assert "us-east-1" in result.output

    def test_show_no_credentials(self, cli_runner, mock_credential_store):
        """Test show command when no credentials are found."""
        from cli.main import cli

        mock_credential_store.get_credentials.return_value = None

        with patch("cli.connectors.CredentialStore") as mock_store_class:
            mock_store_class.return_value = mock_credential_store

            result = cli_runner.invoke(cli, [
                "connectors", "show", "con_01hgw2bbg0000000000000001"
            ])

        assert result.exit_code == 0
        assert "no credentials found" in result.output.lower()


class TestConnectorsRemoveCommand:
    """Tests for the connectors remove CLI command."""

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_credential_store(self):
        """Create a mock CredentialStore."""
        store = MagicMock()
        store.has_credentials.return_value = True
        return store

    @pytest.fixture
    def mock_api_client(self):
        """Create a mock API client."""
        client = MagicMock()
        return client

    def test_remove_with_confirmation(self, cli_runner, mock_credential_store, mock_api_client):
        """Test remove command with user confirmation."""
        from cli.main import cli

        mock_response = MagicMock()
        mock_response.json.return_value = {"acknowledged": True}
        mock_api_client.post.return_value = mock_response

        with patch("cli.connectors.CredentialStore") as mock_store_class, \
             patch("cli.connectors._get_api_client") as mock_get_client:
            mock_store_class.return_value = mock_credential_store
            mock_get_client.return_value = mock_api_client

            result = cli_runner.invoke(
                cli,
                ["connectors", "remove", "con_01hgw2bbg0000000000000001"],
                input="y\n"
            )

        assert result.exit_code == 0
        mock_credential_store.delete_credentials.assert_called_once()
        # Verify server was notified
        mock_api_client.post.assert_called_once()

    def test_remove_with_force(self, cli_runner, mock_credential_store, mock_api_client):
        """Test remove command with --force flag."""
        from cli.main import cli

        mock_response = MagicMock()
        mock_response.json.return_value = {"acknowledged": True}
        mock_api_client.post.return_value = mock_response

        with patch("cli.connectors.CredentialStore") as mock_store_class, \
             patch("cli.connectors._get_api_client") as mock_get_client:
            mock_store_class.return_value = mock_credential_store
            mock_get_client.return_value = mock_api_client

            result = cli_runner.invoke(
                cli,
                ["connectors", "remove", "con_01hgw2bbg0000000000000001", "--force"]
            )

        assert result.exit_code == 0
        mock_credential_store.delete_credentials.assert_called_once()

    def test_remove_no_credentials(self, cli_runner, mock_credential_store):
        """Test remove command when no credentials exist."""
        from cli.main import cli

        mock_credential_store.has_credentials.return_value = False

        with patch("cli.connectors.CredentialStore") as mock_store_class:
            mock_store_class.return_value = mock_credential_store

            result = cli_runner.invoke(
                cli,
                ["connectors", "remove", "con_01hgw2bbg0000000000000001", "--force"]
            )

        assert result.exit_code == 0
        assert "no credentials found" in result.output.lower()
        mock_credential_store.delete_credentials.assert_not_called()

    def test_remove_aborted(self, cli_runner, mock_credential_store):
        """Test remove command aborted by user."""
        from cli.main import cli

        with patch("cli.connectors.CredentialStore") as mock_store_class:
            mock_store_class.return_value = mock_credential_store

            result = cli_runner.invoke(
                cli,
                ["connectors", "remove", "con_01hgw2bbg0000000000000001"],
                input="n\n"
            )

        assert result.exit_code == 0
        assert "aborted" in result.output.lower()
        mock_credential_store.delete_credentials.assert_not_called()


class TestConnectorsTestCommand:
    """Tests for the connectors test CLI command."""

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_credential_store(self):
        """Create a mock CredentialStore."""
        store = MagicMock()
        store.get_credentials.return_value = {
            "aws_access_key_id": "AKIATEST",
            "aws_secret_access_key": "secret",
        }
        store.get_metadata.return_value = {
            "connector_name": "Test S3",
            "connector_type": "s3",
        }
        return store

    @pytest.fixture
    def mock_api_client(self):
        """Create a mock API client."""
        client = MagicMock()
        return client

    def test_test_success_and_report(self, cli_runner, mock_credential_store, mock_api_client):
        """Test test command with successful connection and reporting."""
        from cli.main import cli

        mock_response = MagicMock()
        mock_response.json.return_value = {"acknowledged": True}
        mock_api_client.post.return_value = mock_response

        with patch("cli.connectors.CredentialStore") as mock_store_class, \
             patch("cli.connectors._get_api_client") as mock_get_client, \
             patch("cli.connectors._test_credentials") as mock_test:
            mock_store_class.return_value = mock_credential_store
            mock_get_client.return_value = mock_api_client
            mock_test.return_value = (True, "Successfully connected to AWS S3")

            result = cli_runner.invoke(
                cli,
                ["connectors", "test", "con_01hgw2bbg0000000000000001"]
            )

        assert result.exit_code == 0
        assert "successfully" in result.output.lower()
        mock_api_client.post.assert_called_once()

    def test_test_no_report(self, cli_runner, mock_credential_store):
        """Test test command with --no-report flag."""
        from cli.main import cli

        with patch("cli.connectors.CredentialStore") as mock_store_class, \
             patch("cli.connectors._test_credentials") as mock_test:
            mock_store_class.return_value = mock_credential_store
            mock_test.return_value = (True, "Successfully connected to AWS S3")

            result = cli_runner.invoke(
                cli,
                ["connectors", "test", "con_01hgw2bbg0000000000000001", "--no-report"]
            )

        assert result.exit_code == 0
        assert "successfully" in result.output.lower()

    def test_test_failure(self, cli_runner, mock_credential_store):
        """Test test command with connection failure."""
        from cli.main import cli

        with patch("cli.connectors.CredentialStore") as mock_store_class, \
             patch("cli.connectors._test_credentials") as mock_test:
            mock_store_class.return_value = mock_credential_store
            mock_test.return_value = (False, "Invalid AWS Access Key ID")

            result = cli_runner.invoke(
                cli,
                ["connectors", "test", "con_01hgw2bbg0000000000000001"]
            )

        assert result.exit_code == 1
        assert "invalid" in result.output.lower()

    def test_test_no_credentials(self, cli_runner, mock_credential_store):
        """Test test command when no credentials exist."""
        from cli.main import cli

        mock_credential_store.get_credentials.return_value = None

        with patch("cli.connectors.CredentialStore") as mock_store_class:
            mock_store_class.return_value = mock_credential_store

            result = cli_runner.invoke(
                cli,
                ["connectors", "test", "con_01hgw2bbg0000000000000001"]
            )

        assert result.exit_code == 1
        assert "no credentials found" in result.output.lower()
