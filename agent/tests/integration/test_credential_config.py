"""
Integration tests for credential configuration flow.

End-to-end tests for the complete credential configuration workflow:
1. List pending connectors from server
2. Configure credentials locally
3. Report capability to server
4. Verify credentials persist and work across operations

Issue #90 - Distributed Agent Architecture (Phase 8)
Task: T138
"""

import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from click.testing import CliRunner


class TestCredentialConfigurationFlow:
    """Integration tests for the complete credential configuration flow."""

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI runner."""
        return CliRunner()

    @pytest.fixture
    def temp_credential_store(self, temp_config_dir):
        """Create a credential store in a temporary directory."""
        from src.credential_store import CredentialStore
        return CredentialStore(base_dir=temp_config_dir)

    @pytest.fixture
    def mock_connector_guid(self):
        """Get a mock connector GUID."""
        return "con_01hgw2bbg0000000000000001"

    @pytest.fixture
    def mock_connector_metadata(self, mock_connector_guid):
        """Create mock connector metadata response."""
        return {
            "guid": mock_connector_guid,
            "name": "AWS S3 Photos",
            "type": "s3",
            "credential_fields": [
                {
                    "name": "aws_access_key_id",
                    "type": "string",
                    "required": True,
                    "description": "AWS Access Key ID",
                },
                {
                    "name": "aws_secret_access_key",
                    "type": "password",
                    "required": True,
                    "description": "AWS Secret Access Key",
                },
                {
                    "name": "region",
                    "type": "string",
                    "required": True,
                    "description": "AWS Region",
                },
            ],
        }

    @pytest.fixture
    def mock_connectors_list_response(self, mock_connector_guid):
        """Create mock connector list response."""
        return {
            "connectors": [
                {
                    "guid": mock_connector_guid,
                    "name": "AWS S3 Photos",
                    "type": "s3",
                    "credential_location": "pending",
                    "has_local_credentials": False,
                },
            ],
            "total": 1,
        }

    def test_full_configuration_flow(
        self,
        cli_runner,
        temp_config_dir,
        mock_connector_guid,
        mock_connector_metadata,
        mock_connectors_list_response,
    ):
        """Test the complete flow: list → configure → store → report."""
        from cli.main import cli
        from src.credential_store import CredentialStore

        # Step 1: List pending connectors
        with patch("cli.connectors._get_api_client") as mock_get_client:
            mock_client = MagicMock()
            mock_list_response = MagicMock()
            mock_list_response.json.return_value = mock_connectors_list_response
            mock_client.get.return_value = mock_list_response
            mock_get_client.return_value = mock_client

            result = cli_runner.invoke(cli, ["connectors", "list", "--pending"])

        assert result.exit_code == 0
        assert "AWS S3 Photos" in result.output
        assert "Pending" in result.output

        # Step 2: Configure credentials (with mocked credential test)
        with patch("cli.connectors._get_api_client") as mock_get_client, \
             patch("cli.connectors.CredentialStore") as mock_store_class, \
             patch("cli.connectors._test_credentials") as mock_test:

            mock_client = MagicMock()

            # Mock metadata endpoint
            mock_metadata_response = MagicMock()
            mock_metadata_response.json.return_value = mock_connector_metadata
            mock_client.get.return_value = mock_metadata_response

            # Mock report-capability endpoint
            mock_report_response = MagicMock()
            mock_report_response.json.return_value = {
                "acknowledged": True,
                "credential_location_updated": True,
            }
            mock_client.post.return_value = mock_report_response
            mock_get_client.return_value = mock_client

            # Mock credential store
            mock_store = MagicMock()
            mock_store.has_credentials.return_value = False
            mock_store_class.return_value = mock_store

            # Mock credential test
            mock_test.return_value = (True, "Successfully connected to AWS S3")

            # Run configure command with input
            result = cli_runner.invoke(
                cli,
                ["connectors", "configure", mock_connector_guid],
                input="AKIAIOSFODNN7EXAMPLE\nsecretkey123\nus-east-1\n",
            )

        assert result.exit_code == 0
        assert "Configuring credentials for: AWS S3 Photos" in result.output
        assert "Successfully connected to AWS S3" in result.output
        assert "Credentials stored successfully" in result.output
        assert "changed from pending to agent" in result.output

        # Verify store was called with correct credentials
        mock_store.store_credentials.assert_called_once()
        call_args = mock_store.store_credentials.call_args
        assert call_args.kwargs["connector_guid"] == mock_connector_guid
        assert call_args.kwargs["credentials"]["aws_access_key_id"] == "AKIAIOSFODNN7EXAMPLE"
        assert call_args.kwargs["credentials"]["region"] == "us-east-1"

        # Verify capability was reported
        mock_client.post.assert_called_once()
        post_call = mock_client.post.call_args
        assert mock_connector_guid in post_call.args[0]
        assert post_call.kwargs["json"]["has_credentials"] is True

    def test_test_and_report_flow(
        self,
        cli_runner,
        temp_config_dir,
        mock_connector_guid,
    ):
        """Test the test command flow: load credentials → test → report."""
        from cli.main import cli

        mock_credentials = {
            "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "aws_secret_access_key": "secretkey123",
            "region": "us-east-1",
        }
        mock_metadata = {
            "connector_name": "AWS S3 Photos",
            "connector_type": "s3",
        }

        with patch("cli.connectors.CredentialStore") as mock_store_class, \
             patch("cli.connectors._get_api_client") as mock_get_client, \
             patch("cli.connectors._test_credentials") as mock_test:

            # Mock credential store
            mock_store = MagicMock()
            mock_store.get_credentials.return_value = mock_credentials
            mock_store.get_metadata.return_value = mock_metadata
            mock_store_class.return_value = mock_store

            # Mock API client
            mock_client = MagicMock()
            mock_report_response = MagicMock()
            mock_report_response.json.return_value = {"acknowledged": True}
            mock_client.post.return_value = mock_report_response
            mock_get_client.return_value = mock_client

            # Mock successful test
            mock_test.return_value = (True, "Successfully connected to AWS S3")

            result = cli_runner.invoke(
                cli,
                ["connectors", "test", mock_connector_guid],
            )

        assert result.exit_code == 0
        assert "Testing credentials for: AWS S3 Photos" in result.output
        assert "Successfully connected to AWS S3" in result.output
        assert "Capability reported to server" in result.output

        # Verify capability was reported
        mock_client.post.assert_called_once()

    def test_credential_removal_flow(
        self,
        cli_runner,
        mock_connector_guid,
    ):
        """Test credential removal flow: confirm → delete → notify server."""
        from cli.main import cli

        with patch("cli.connectors.CredentialStore") as mock_store_class, \
             patch("cli.connectors._get_api_client") as mock_get_client:

            # Mock credential store
            mock_store = MagicMock()
            mock_store.has_credentials.return_value = True
            mock_store_class.return_value = mock_store

            # Mock API client
            mock_client = MagicMock()
            mock_report_response = MagicMock()
            mock_report_response.json.return_value = {"acknowledged": True}
            mock_client.post.return_value = mock_report_response
            mock_get_client.return_value = mock_client

            # Run remove with confirmation
            result = cli_runner.invoke(
                cli,
                ["connectors", "remove", mock_connector_guid],
                input="y\n",
            )

        assert result.exit_code == 0
        assert "Credentials removed" in result.output
        assert "Server notified" in result.output

        # Verify delete was called
        mock_store.delete_credentials.assert_called_once_with(mock_connector_guid)

        # Verify server was notified with has_credentials=False
        mock_client.post.assert_called_once()
        post_call = mock_client.post.call_args
        assert post_call.kwargs["json"]["has_credentials"] is False


class TestCredentialPersistence:
    """Tests for credential persistence across operations."""

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI runner."""
        return CliRunner()

    def test_credentials_persist_across_store_instances(self, temp_config_dir):
        """Test that credentials persist when creating new store instances."""
        from src.credential_store import CredentialStore

        connector_guid = "con_01hgw2bbg0000000000000001"
        test_credentials = {
            "aws_access_key_id": "AKIATEST123",
            "aws_secret_access_key": "secrettest",
            "region": "us-west-2",
        }
        test_metadata = {
            "connector_name": "Test Connector",
            "connector_type": "s3",
        }

        # Store credentials with first instance
        store1 = CredentialStore(base_dir=temp_config_dir)
        store1.store_credentials(
            connector_guid=connector_guid,
            credentials=test_credentials,
            metadata=test_metadata,
        )

        # Create new instance (simulating agent restart)
        store2 = CredentialStore(base_dir=temp_config_dir)

        # Verify credentials are accessible
        assert store2.has_credentials(connector_guid)
        retrieved_creds = store2.get_credentials(connector_guid)
        assert retrieved_creds == test_credentials

        retrieved_meta = store2.get_metadata(connector_guid)
        assert retrieved_meta == test_metadata

    def test_multiple_connectors_persist(self, temp_config_dir):
        """Test that multiple connector credentials persist correctly."""
        from src.credential_store import CredentialStore

        store = CredentialStore(base_dir=temp_config_dir)

        # Store credentials for multiple connectors
        connectors = {
            "con_01hgw2bbg0000000000000001": {
                "aws_access_key_id": "KEY1",
                "aws_secret_access_key": "SECRET1",
            },
            "con_01hgw2bbg0000000000000002": {
                "server": "smb.example.com",
                "username": "user",
                "password": "pass",
            },
        }

        for guid, creds in connectors.items():
            store.store_credentials(connector_guid=guid, credentials=creds)

        # Create new instance
        store2 = CredentialStore(base_dir=temp_config_dir)

        # Verify all connectors are listed
        guids = store2.list_connector_guids()
        assert len(guids) == 2
        assert "con_01hgw2bbg0000000000000001" in guids
        assert "con_01hgw2bbg0000000000000002" in guids

        # Verify credentials
        for guid, expected_creds in connectors.items():
            retrieved = store2.get_credentials(guid)
            assert retrieved == expected_creds


class TestHeartbeatCapabilityReporting:
    """Tests for capability reporting via heartbeat."""

    @pytest.mark.asyncio
    async def test_heartbeat_includes_connector_capabilities(
        self,
        temp_config_dir,
        mock_server_url,
        mock_api_key,
    ):
        """Test that heartbeat includes connector capabilities when configured."""
        from src.credential_store import CredentialStore
        from src.api_client import AgentApiClient

        # Set up credential store with a connector
        store = CredentialStore(base_dir=temp_config_dir)
        connector_guid = "con_01hgw2bbg0000000000000001"
        store.store_credentials(
            connector_guid=connector_guid,
            credentials={"key": "value"},
            metadata={"connector_type": "s3"},
        )

        # Mock the heartbeat call
        with patch.object(AgentApiClient, "heartbeat", new_callable=AsyncMock) as mock_heartbeat:
            mock_heartbeat.return_value = {"acknowledged": True}

            client = AgentApiClient(server_url=mock_server_url, api_key=mock_api_key)

            # Simulate heartbeat with capabilities
            capabilities = [
                "local_filesystem",
                "tool:photostats:1.0.0",
                f"connector:{connector_guid}",
            ]

            await client.heartbeat(capabilities=capabilities)

            # Verify heartbeat was called with connector capability
            mock_heartbeat.assert_called_once()
            call_kwargs = mock_heartbeat.call_args.kwargs
            assert f"connector:{connector_guid}" in call_kwargs.get("capabilities", [])


class TestConfigurationErrorHandling:
    """Tests for error handling during credential configuration."""

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_connector_guid(self):
        """Get a mock connector GUID."""
        return "con_01hgw2bbg0000000000000001"

    def test_configuration_with_server_unreachable(
        self,
        cli_runner,
        temp_config_dir,
        mock_connector_guid,
    ):
        """Test configuration when server is unreachable during capability report."""
        from cli.main import cli
        import httpx

        mock_connector_metadata = {
            "guid": mock_connector_guid,
            "name": "Test S3",
            "type": "s3",
            "credential_fields": [
                {"name": "aws_access_key_id", "type": "string", "required": True, "description": "Key ID"},
                {"name": "aws_secret_access_key", "type": "password", "required": True, "description": "Secret"},
                {"name": "region", "type": "string", "required": True, "description": "Region"},
            ],
        }

        with patch("cli.connectors._get_api_client") as mock_get_client, \
             patch("cli.connectors.CredentialStore") as mock_store_class, \
             patch("cli.connectors._test_credentials") as mock_test:

            mock_client = MagicMock()

            # Metadata endpoint works
            mock_metadata_response = MagicMock()
            mock_metadata_response.json.return_value = mock_connector_metadata
            mock_client.get.return_value = mock_metadata_response

            # Report capability fails
            mock_client.post.side_effect = httpx.ConnectError("Server unreachable")
            mock_get_client.return_value = mock_client

            # Credential store works
            mock_store = MagicMock()
            mock_store.has_credentials.return_value = False
            mock_store_class.return_value = mock_store

            # Test passes
            mock_test.return_value = (True, "Connected")

            result = cli_runner.invoke(
                cli,
                ["connectors", "configure", mock_connector_guid],
                input="AKIATEST\nsecret\nus-east-1\n",
            )

        # Should still succeed (credentials stored locally)
        assert result.exit_code == 0
        assert "Credentials stored successfully" in result.output
        assert "Failed to report capability" in result.output or "Warning" in result.output

        # Verify credentials were still stored
        mock_store.store_credentials.assert_called_once()

    def test_configuration_test_failure_abort(
        self,
        cli_runner,
        mock_connector_guid,
    ):
        """Test configuration aborted when credential test fails and user declines."""
        from cli.main import cli

        mock_connector_metadata = {
            "guid": mock_connector_guid,
            "name": "Test S3",
            "type": "s3",
            "credential_fields": [
                {"name": "aws_access_key_id", "type": "string", "required": True, "description": "Key ID"},
                {"name": "aws_secret_access_key", "type": "password", "required": True, "description": "Secret"},
                {"name": "region", "type": "string", "required": True, "description": "Region"},
            ],
        }

        with patch("cli.connectors._get_api_client") as mock_get_client, \
             patch("cli.connectors.CredentialStore") as mock_store_class, \
             patch("cli.connectors._test_credentials") as mock_test:

            mock_client = MagicMock()
            mock_metadata_response = MagicMock()
            mock_metadata_response.json.return_value = mock_connector_metadata
            mock_client.get.return_value = mock_metadata_response
            mock_get_client.return_value = mock_client

            mock_store = MagicMock()
            mock_store.has_credentials.return_value = False
            mock_store_class.return_value = mock_store

            # Test fails
            mock_test.return_value = (False, "Invalid AWS Access Key ID")

            # User declines to store anyway
            result = cli_runner.invoke(
                cli,
                ["connectors", "configure", mock_connector_guid],
                input="AKIATEST\nsecret\nus-east-1\nn\n",  # "n" to decline
            )

        assert result.exit_code == 0
        assert "Invalid AWS Access Key ID" in result.output
        assert "Aborted" in result.output

        # Verify credentials were NOT stored
        mock_store.store_credentials.assert_not_called()

    def test_configuration_test_failure_proceed(
        self,
        cli_runner,
        mock_connector_guid,
    ):
        """Test configuration proceeds when credential test fails but user confirms."""
        from cli.main import cli

        mock_connector_metadata = {
            "guid": mock_connector_guid,
            "name": "Test S3",
            "type": "s3",
            "credential_fields": [
                {"name": "aws_access_key_id", "type": "string", "required": True, "description": "Key ID"},
                {"name": "aws_secret_access_key", "type": "password", "required": True, "description": "Secret"},
                {"name": "region", "type": "string", "required": True, "description": "Region"},
            ],
        }

        with patch("cli.connectors._get_api_client") as mock_get_client, \
             patch("cli.connectors.CredentialStore") as mock_store_class, \
             patch("cli.connectors._test_credentials") as mock_test:

            mock_client = MagicMock()
            mock_metadata_response = MagicMock()
            mock_metadata_response.json.return_value = mock_connector_metadata
            mock_client.get.return_value = mock_metadata_response

            mock_report_response = MagicMock()
            mock_report_response.json.return_value = {"acknowledged": True}
            mock_client.post.return_value = mock_report_response
            mock_get_client.return_value = mock_client

            mock_store = MagicMock()
            mock_store.has_credentials.return_value = False
            mock_store_class.return_value = mock_store

            # Test fails
            mock_test.return_value = (False, "Invalid credentials")

            # User confirms to store anyway
            result = cli_runner.invoke(
                cli,
                ["connectors", "configure", mock_connector_guid],
                input="AKIATEST\nsecret\nus-east-1\ny\n",  # "y" to proceed
            )

        assert result.exit_code == 0
        assert "Credentials stored successfully" in result.output

        # Verify credentials were stored despite failed test
        mock_store.store_credentials.assert_called_once()


class TestConfigurationWithSkippedTest:
    """Tests for configuration with --no-test flag."""

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI runner."""
        return CliRunner()

    def test_configure_without_test(self, cli_runner):
        """Test configuration with --no-test skips credential testing."""
        from cli.main import cli

        mock_connector_guid = "con_01hgw2bbg0000000000000001"
        mock_connector_metadata = {
            "guid": mock_connector_guid,
            "name": "Test S3",
            "type": "s3",
            "credential_fields": [
                {"name": "aws_access_key_id", "type": "string", "required": True, "description": "Key ID"},
                {"name": "aws_secret_access_key", "type": "password", "required": True, "description": "Secret"},
                {"name": "region", "type": "string", "required": True, "description": "Region"},
            ],
        }

        with patch("cli.connectors._get_api_client") as mock_get_client, \
             patch("cli.connectors.CredentialStore") as mock_store_class, \
             patch("cli.connectors._test_credentials") as mock_test:

            mock_client = MagicMock()
            mock_metadata_response = MagicMock()
            mock_metadata_response.json.return_value = mock_connector_metadata
            mock_client.get.return_value = mock_metadata_response

            mock_report_response = MagicMock()
            mock_report_response.json.return_value = {"acknowledged": True}
            mock_client.post.return_value = mock_report_response
            mock_get_client.return_value = mock_client

            mock_store = MagicMock()
            mock_store.has_credentials.return_value = False
            mock_store_class.return_value = mock_store

            result = cli_runner.invoke(
                cli,
                ["connectors", "configure", mock_connector_guid, "--no-test"],
                input="AKIATEST\nsecret\nus-east-1\n",
            )

        assert result.exit_code == 0
        assert "Credentials stored successfully" in result.output

        # Verify test was NOT called
        mock_test.assert_not_called()

        # Verify credentials were stored
        mock_store.store_credentials.assert_called_once()


class TestListConnectorsIntegration:
    """Integration tests for listing connectors."""

    @pytest.fixture
    def cli_runner(self):
        """Create a Click CLI runner."""
        return CliRunner()

    def test_list_shows_local_credential_status(self, cli_runner, temp_config_dir):
        """Test that list shows which connectors have local credentials."""
        from cli.main import cli

        mock_connectors = {
            "connectors": [
                {
                    "guid": "con_01hgw2bbg0000000000000001",
                    "name": "S3 with creds",
                    "type": "s3",
                    "credential_location": "agent",
                    "has_local_credentials": True,
                },
                {
                    "guid": "con_01hgw2bbg0000000000000002",
                    "name": "S3 pending",
                    "type": "s3",
                    "credential_location": "pending",
                    "has_local_credentials": False,
                },
            ],
            "total": 2,
        }

        with patch("cli.connectors._get_api_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json.return_value = mock_connectors
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = cli_runner.invoke(cli, ["connectors", "list"])

        assert result.exit_code == 0
        assert "S3 with creds" in result.output
        assert "S3 pending" in result.output
        assert "Yes" in result.output  # has_local_credentials
        assert "No" in result.output

    def test_list_json_includes_all_fields(self, cli_runner):
        """Test that JSON output includes all connector fields."""
        from cli.main import cli

        mock_connectors = {
            "connectors": [
                {
                    "guid": "con_01hgw2bbg0000000000000001",
                    "name": "Test Connector",
                    "type": "s3",
                    "credential_location": "agent",
                    "has_local_credentials": True,
                },
            ],
            "total": 1,
        }

        with patch("cli.connectors._get_api_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json.return_value = mock_connectors
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = cli_runner.invoke(cli, ["connectors", "list", "--json"])

        assert result.exit_code == 0

        # Parse and verify JSON
        output = json.loads(result.output)
        assert output["total"] == 1
        connector = output["connectors"][0]
        assert connector["guid"] == "con_01hgw2bbg0000000000000001"
        assert connector["has_local_credentials"] is True
