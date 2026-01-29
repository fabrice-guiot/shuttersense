"""
Unit tests for the collection CLI commands.

Tests collection subcommands: create, list, sync, test.
Covers cache lookup, auto-test, name prompt, skip-test flag, analyze flag,
server errors, success output, online/offline modes, type filters, and
collection accessibility testing.

Issue #108 - Remove CLI Direct Usage
Tasks: T018, T029
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cli.collection import collection
from src.cache import (
    TEST_CACHE_TTL_HOURS,
    COLLECTION_CACHE_TTL_DAYS,
    CachedCollection,
    CollectionCache,
    TestCacheEntry,
)
from src.cache.test_cache import _hash_path


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_config():
    """Mock AgentConfig that is registered."""
    with patch("cli.collection.AgentConfig") as mock_cls:
        config = MagicMock()
        config.is_registered = True
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        config.server_url = "http://localhost:8000"
        config.api_key = "agt_key_test123"
        mock_cls.return_value = config
        yield config


@pytest.fixture
def mock_config_unregistered():
    """Mock AgentConfig that is NOT registered."""
    with patch("cli.collection.AgentConfig") as mock_cls:
        config = MagicMock()
        config.is_registered = False
        mock_cls.return_value = config
        yield config


@pytest.fixture
def valid_cache_entry():
    """A valid (non-expired) test cache entry."""
    now = datetime.now(timezone.utc)
    return TestCacheEntry(
        path="/tmp/photos",
        path_hash=_hash_path("/tmp/photos"),
        tested_at=now,
        expires_at=now + timedelta(hours=TEST_CACHE_TTL_HOURS),
        accessible=True,
        file_count=100,
        photo_count=80,
        sidecar_count=15,
        tools_tested=["photostats"],
        issues_found=None,
        agent_id="agt_01hgw2bbg0000000000000001",
        agent_version="v1.0.0",
    )


@pytest.fixture
def inaccessible_cache_entry():
    """A cache entry where path was not accessible."""
    now = datetime.now(timezone.utc)
    return TestCacheEntry(
        path="/tmp/photos",
        path_hash=_hash_path("/tmp/photos"),
        tested_at=now,
        expires_at=now + timedelta(hours=TEST_CACHE_TTL_HOURS),
        accessible=False,
        file_count=0,
        photo_count=0,
        sidecar_count=0,
        tools_tested=[],
        issues_found=None,
        agent_id="agt_01hgw2bbg0000000000000001",
        agent_version="v1.0.0",
    )


@pytest.fixture
def mock_api_success():
    """Mock successful API response for collection creation."""
    return {
        "guid": "col_01hgw2bbg0000000000000001",
        "name": "Test Photos",
        "type": "LOCAL",
        "location": "/tmp/photos",
        "bound_agent_guid": "agt_01hgw2bbg0000000000000001",
        "web_url": "/collections/col_01hgw2bbg0000000000000001",
        "created_at": "2026-01-28T12:00:00.000Z",
    }


# ============================================================================
# Agent Registration Tests
# ============================================================================


class TestAgentRegistration:
    """Tests for agent registration checks."""

    def test_unregistered_agent_fails(self, runner, mock_config_unregistered):
        result = runner.invoke(collection, ["create", "/tmp/photos", "--name", "Test"])
        assert result.exit_code == 1
        assert "not registered" in result.output

    def test_config_load_failure(self, runner):
        with patch("cli.collection.AgentConfig", side_effect=Exception("config broken")):
            result = runner.invoke(collection, ["create", "/tmp/photos", "--name", "Test"])
        assert result.exit_code == 1
        assert "Failed to load agent config" in result.output


# ============================================================================
# Cache Lookup Tests
# ============================================================================


class TestCacheLookup:
    """Tests for test cache integration."""

    def test_uses_valid_cache(self, runner, mock_config, valid_cache_entry, mock_api_success):
        with patch("cli.collection.load_valid", return_value=valid_cache_entry), \
             patch("cli.collection._create_collection_async", new_callable=AsyncMock, return_value=mock_api_success):
            result = runner.invoke(collection, ["create", "/tmp/photos", "--name", "Test Photos"])
        assert result.exit_code == 0
        assert "Using cached test result" in result.output
        assert "100" in result.output  # file count

    def test_inaccessible_cache_fails(self, runner, mock_config, inaccessible_cache_entry):
        with patch("cli.collection.load_valid", return_value=inaccessible_cache_entry):
            result = runner.invoke(collection, ["create", "/tmp/photos", "--name", "Test"])
        assert result.exit_code == 1
        assert "not accessible" in result.output


# ============================================================================
# Auto-Test Tests
# ============================================================================


class TestAutoTest:
    """Tests for automatic test when no cache exists."""

    def test_auto_test_on_cache_miss(self, runner, mock_config, valid_cache_entry, mock_api_success):
        """When no cache exists and --skip-test not set, test runs automatically."""
        call_count = [0]

        def mock_load_valid(path):
            call_count[0] += 1
            # First call returns None (cache miss), second returns valid entry (after test)
            if call_count[0] == 1:
                return None
            return valid_cache_entry

        with patch("cli.collection.load_valid", side_effect=mock_load_valid), \
             patch("cli.test.LocalAdapter") as mock_adapter_cls, \
             patch("cli.test.save"), \
             patch("cli.test.AgentConfig") as mock_test_config, \
             patch("cli.collection._create_collection_async", new_callable=AsyncMock, return_value=mock_api_success):
            adapter = MagicMock()
            adapter.list_files_with_metadata.return_value = []
            mock_adapter_cls.return_value = adapter
            test_cfg = MagicMock()
            test_cfg.agent_guid = "agt_01hgw2bbg0000000000000001"
            mock_test_config.return_value = test_cfg

            result = runner.invoke(collection, ["create", "/tmp/photos", "--name", "Test Photos"])
        assert "Running test automatically" in result.output

    def test_skip_test_flag(self, runner, mock_config, mock_api_success):
        """--skip-test skips test validation."""
        with patch("cli.collection.load_valid", return_value=None), \
             patch("cli.collection._create_collection_async", new_callable=AsyncMock, return_value=mock_api_success):
            result = runner.invoke(collection, ["create", "/tmp/photos", "--name", "Test", "--skip-test"])
        assert result.exit_code == 0
        assert "Skipping test" in result.output
        assert "created successfully" in result.output


# ============================================================================
# Name Prompt Tests
# ============================================================================


class TestNamePrompt:
    """Tests for collection name handling."""

    def test_name_from_option(self, runner, mock_config, valid_cache_entry, mock_api_success):
        with patch("cli.collection.load_valid", return_value=valid_cache_entry), \
             patch("cli.collection._create_collection_async", new_callable=AsyncMock, return_value=mock_api_success):
            result = runner.invoke(collection, ["create", "/tmp/photos", "--name", "My Collection"])
        assert result.exit_code == 0
        assert "created successfully" in result.output

    def test_name_from_prompt(self, runner, mock_config, valid_cache_entry, mock_api_success):
        """When --name not provided, prompts with folder name as default."""
        with patch("cli.collection.load_valid", return_value=valid_cache_entry), \
             patch("cli.collection._create_collection_async", new_callable=AsyncMock, return_value=mock_api_success):
            result = runner.invoke(collection, ["create", "/tmp/photos"], input="My Photos\n")
        assert result.exit_code == 0
        assert "Collection name" in result.output  # prompt shown


# ============================================================================
# Server Error Tests
# ============================================================================


class TestServerErrors:
    """Tests for server error handling."""

    def test_connection_error(self, runner, mock_config, valid_cache_entry):
        from src.api_client import ConnectionError as AgentConnectionError

        with patch("cli.collection.load_valid", return_value=valid_cache_entry), \
             patch("cli.collection._create_collection_async", new_callable=AsyncMock,
                   side_effect=AgentConnectionError("Connection refused")):
            result = runner.invoke(collection, ["create", "/tmp/photos", "--name", "Test"])
        assert result.exit_code == 2
        assert "Connection failed" in result.output

    def test_auth_error(self, runner, mock_config, valid_cache_entry):
        from src.api_client import AuthenticationError

        with patch("cli.collection.load_valid", return_value=valid_cache_entry), \
             patch("cli.collection._create_collection_async", new_callable=AsyncMock,
                   side_effect=AuthenticationError("Invalid API key", status_code=401)):
            result = runner.invoke(collection, ["create", "/tmp/photos", "--name", "Test"])
        assert result.exit_code == 2
        assert "Authentication failed" in result.output

    def test_conflict_error_exit_code_3(self, runner, mock_config, valid_cache_entry):
        from src.api_client import ApiError

        with patch("cli.collection.load_valid", return_value=valid_cache_entry), \
             patch("cli.collection._create_collection_async", new_callable=AsyncMock,
                   side_effect=ApiError("Collection with name 'Test' already exists", status_code=409)):
            result = runner.invoke(collection, ["create", "/tmp/photos", "--name", "Test"])
        assert result.exit_code == 3
        assert "already exists" in result.output

    def test_validation_error(self, runner, mock_config, valid_cache_entry):
        from src.api_client import ApiError

        with patch("cli.collection.load_valid", return_value=valid_cache_entry), \
             patch("cli.collection._create_collection_async", new_callable=AsyncMock,
                   side_effect=ApiError("Path not authorized", status_code=400)):
            result = runner.invoke(collection, ["create", "/tmp/photos", "--name", "Test"])
        assert result.exit_code == 2
        assert "Path not authorized" in result.output


# ============================================================================
# Success Output Tests
# ============================================================================


class TestSuccessOutput:
    """Tests for successful collection creation output."""

    def test_displays_guid_and_url(self, runner, mock_config, valid_cache_entry, mock_api_success):
        with patch("cli.collection.load_valid", return_value=valid_cache_entry), \
             patch("cli.collection._create_collection_async", new_callable=AsyncMock, return_value=mock_api_success):
            result = runner.invoke(collection, ["create", "/tmp/photos", "--name", "Test Photos"])
        assert result.exit_code == 0
        assert "col_01hgw2bbg0000000000000001" in result.output
        assert "/collections/col_01hgw2bbg0000000000000001" in result.output
        assert "created successfully" in result.output

    def test_displays_collection_details(self, runner, mock_config, valid_cache_entry, mock_api_success):
        with patch("cli.collection.load_valid", return_value=valid_cache_entry), \
             patch("cli.collection._create_collection_async", new_callable=AsyncMock, return_value=mock_api_success):
            result = runner.invoke(collection, ["create", "/tmp/photos", "--name", "Test Photos"])
        assert "GUID:" in result.output
        assert "Name:" in result.output
        assert "Type:" in result.output
        assert "Location:" in result.output
        assert "Web URL:" in result.output

    def test_analyze_flag_accepted(self, runner, mock_config, valid_cache_entry, mock_api_success):
        """The --analyze flag is accepted without error."""
        with patch("cli.collection.load_valid", return_value=valid_cache_entry), \
             patch("cli.collection._create_collection_async", new_callable=AsyncMock, return_value=mock_api_success):
            result = runner.invoke(
                collection, ["create", "/tmp/photos", "--name", "Test", "--analyze"]
            )
        assert result.exit_code == 0
        assert "Collection created successfully" in result.output

    def test_next_steps_shown(self, runner, mock_config, valid_cache_entry, mock_api_success):
        """After creation, next steps with run commands are displayed."""
        with patch("cli.collection.load_valid", return_value=valid_cache_entry), \
             patch("cli.collection._create_collection_async", new_callable=AsyncMock, return_value=mock_api_success):
            result = runner.invoke(
                collection, ["create", "/tmp/photos", "--name", "Test"]
            )
        assert result.exit_code == 0
        assert "Next steps:" in result.output
        assert "shuttersense-agent run" in result.output
        assert "--tool photostats" in result.output


# ============================================================================
# Test Results Passed to API Tests
# ============================================================================


class TestTestResultsPassthrough:
    """Tests that test results are correctly passed to the API."""

    def test_test_results_included_when_cache_exists(
        self, runner, mock_config, valid_cache_entry, mock_api_success
    ):
        with patch("cli.collection.load_valid", return_value=valid_cache_entry), \
             patch("cli.collection._create_collection_async", new_callable=AsyncMock, return_value=mock_api_success) as mock_create:
            result = runner.invoke(collection, ["create", "/tmp/photos", "--name", "Test"])
        assert result.exit_code == 0
        # Verify test_results was passed
        call_args = mock_create.call_args
        assert call_args.kwargs["test_results"] is not None
        assert call_args.kwargs["test_results"]["file_count"] == 100

    def test_no_test_results_with_skip_test(self, runner, mock_config, mock_api_success):
        with patch("cli.collection.load_valid", return_value=None), \
             patch("cli.collection._create_collection_async", new_callable=AsyncMock, return_value=mock_api_success) as mock_create:
            result = runner.invoke(
                collection, ["create", "/tmp/photos", "--name", "Test", "--skip-test"]
            )
        assert result.exit_code == 0
        call_args = mock_create.call_args
        assert call_args.kwargs["test_results"] is None


# ============================================================================
# Shared Fixtures for list/sync/test subcommands (T029)
# ============================================================================


@pytest.fixture
def mock_list_response():
    """Mock successful API response for collection listing."""
    return {
        "collections": [
            {
                "guid": "col_01hgw2bbg0000000000000001",
                "name": "Vacation 2024",
                "type": "LOCAL",
                "location": "/photos/2024",
                "bound_agent_guid": "agt_01hgw2bbg0000000000000001",
                "connector_guid": None,
                "connector_name": None,
                "is_accessible": True,
                "last_analysis_at": None,
                "supports_offline": True,
            },
            {
                "guid": "col_01hgw2bbg0000000000000002",
                "name": "Wedding Photos",
                "type": "LOCAL",
                "location": "/photos/wedding",
                "bound_agent_guid": "agt_01hgw2bbg0000000000000001",
                "connector_guid": None,
                "connector_name": None,
                "is_accessible": False,
                "last_analysis_at": None,
                "supports_offline": True,
            },
        ],
        "total_count": 2,
    }


@pytest.fixture
def sample_collection_cache():
    """A valid collection cache with two entries."""
    now = datetime.now(timezone.utc)
    return CollectionCache(
        agent_guid="agt_01hgw2bbg0000000000000001",
        synced_at=now,
        expires_at=now + timedelta(days=COLLECTION_CACHE_TTL_DAYS),
        collections=[
            CachedCollection(
                guid="col_01hgw2bbg0000000000000001",
                name="Vacation 2024",
                type="LOCAL",
                location="/photos/2024",
                bound_agent_guid="agt_01hgw2bbg0000000000000001",
                is_accessible=True,
                supports_offline=True,
            ),
            CachedCollection(
                guid="col_01hgw2bbg0000000000000002",
                name="Wedding Photos",
                type="LOCAL",
                location="/photos/wedding",
                bound_agent_guid="agt_01hgw2bbg0000000000000001",
                is_accessible=False,
                supports_offline=True,
            ),
        ],
    )


@pytest.fixture
def expired_collection_cache():
    """An expired collection cache."""
    past = datetime(2020, 1, 1, tzinfo=timezone.utc)
    return CollectionCache(
        agent_guid="agt_01hgw2bbg0000000000000001",
        synced_at=past,
        expires_at=past + timedelta(days=COLLECTION_CACHE_TTL_DAYS),
        collections=[
            CachedCollection(
                guid="col_01hgw2bbg0000000000000001",
                name="Old Photos",
                type="LOCAL",
                location="/photos/old",
                bound_agent_guid="agt_01hgw2bbg0000000000000001",
                is_accessible=True,
                supports_offline=True,
            ),
        ],
    )


# ============================================================================
# List Command Tests (T029)
# ============================================================================


class TestListCommand:
    """Tests for collection list subcommand."""

    def test_list_online_success(self, runner, mock_config, mock_list_response):
        """Online mode fetches from server and displays collections."""
        with patch("cli.collection._list_collections_async", new_callable=AsyncMock, return_value=mock_list_response), \
             patch("cli.collection.col_cache"):
            result = runner.invoke(collection, ["list"])
        assert result.exit_code == 0
        assert "2 collection(s)" in result.output
        assert "col_01hgw2bbg0000000000000001" in result.output
        assert "Vacation 2024" in result.output

    def test_list_offline_with_cache(self, runner, mock_config, sample_collection_cache):
        """Offline mode displays cached data."""
        with patch("cli.collection.col_cache") as mock_cache:
            mock_cache.load.return_value = sample_collection_cache
            result = runner.invoke(collection, ["list", "--offline"])
        assert result.exit_code == 0
        assert "Cached data from:" in result.output
        assert "2 collection(s)" in result.output

    def test_list_offline_no_cache(self, runner, mock_config):
        """Offline mode with no cache shows error."""
        with patch("cli.collection.col_cache") as mock_cache:
            mock_cache.load.return_value = None
            result = runner.invoke(collection, ["list", "--offline"])
        assert result.exit_code == 1
        assert "No cached collection data" in result.output

    def test_list_offline_expired_cache_warns(self, runner, mock_config, expired_collection_cache):
        """Offline mode with expired cache shows warning."""
        with patch("cli.collection.col_cache") as mock_cache:
            mock_cache.load.return_value = expired_collection_cache
            result = runner.invoke(collection, ["list", "--offline"])
        assert result.exit_code == 0
        assert "Warning:" in result.output or "expired" in result.output.lower()

    def test_list_type_filter(self, runner, mock_config, mock_list_response):
        """Type filter is passed to API."""
        with patch("cli.collection._list_collections_async", new_callable=AsyncMock, return_value=mock_list_response) as mock_fn, \
             patch("cli.collection.col_cache"):
            result = runner.invoke(collection, ["list", "--type", "LOCAL"])
        assert result.exit_code == 0
        call_args = mock_fn.call_args
        assert call_args.kwargs["type_filter"] == "LOCAL"

    def test_list_connection_error(self, runner, mock_config):
        """Connection error produces exit code 2."""
        from src.api_client import ConnectionError as AgentConnectionError

        with patch("cli.collection._list_collections_async", new_callable=AsyncMock,
                   side_effect=AgentConnectionError("Connection refused")):
            result = runner.invoke(collection, ["list"])
        assert result.exit_code == 2
        assert "Connection failed" in result.output

    def test_list_unregistered_agent(self, runner, mock_config_unregistered):
        """Unregistered agent fails for list."""
        result = runner.invoke(collection, ["list"])
        assert result.exit_code == 1
        assert "not registered" in result.output

    def test_list_empty_collections(self, runner, mock_config):
        """Empty collection list shows appropriate message."""
        with patch("cli.collection._list_collections_async", new_callable=AsyncMock,
                   return_value={"collections": [], "total_count": 0}), \
             patch("cli.collection.col_cache"):
            result = runner.invoke(collection, ["list"])
        assert result.exit_code == 0
        assert "No collections found" in result.output


# ============================================================================
# Sync Command Tests (T029)
# ============================================================================


class TestSyncCommand:
    """Tests for collection sync subcommand."""

    def test_sync_success(self, runner, mock_config, mock_list_response):
        """Sync fetches collections and saves cache."""
        with patch("cli.collection._list_collections_async", new_callable=AsyncMock, return_value=mock_list_response), \
             patch("cli.collection.col_cache") as mock_cache:
            mock_cache.make_cache.return_value = MagicMock(
                synced_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )
            mock_cache.save.return_value = Path("/tmp/collection-cache.json")
            result = runner.invoke(collection, ["sync"])
        assert result.exit_code == 0
        assert "Sync complete!" in result.output
        assert "Collections: 2" in result.output
        mock_cache.save.assert_called_once()

    def test_sync_connection_error(self, runner, mock_config):
        """Connection error during sync produces exit code 2."""
        from src.api_client import ConnectionError as AgentConnectionError

        with patch("cli.collection._list_collections_async", new_callable=AsyncMock,
                   side_effect=AgentConnectionError("Connection refused")):
            result = runner.invoke(collection, ["sync"])
        assert result.exit_code == 2
        assert "Connection failed" in result.output

    def test_sync_auth_error(self, runner, mock_config):
        """Auth error during sync produces exit code 2."""
        from src.api_client import AuthenticationError

        with patch("cli.collection._list_collections_async", new_callable=AsyncMock,
                   side_effect=AuthenticationError("Invalid API key", status_code=401)):
            result = runner.invoke(collection, ["sync"])
        assert result.exit_code == 2
        assert "Authentication failed" in result.output

    def test_sync_unregistered_agent(self, runner, mock_config_unregistered):
        """Unregistered agent fails for sync."""
        result = runner.invoke(collection, ["sync"])
        assert result.exit_code == 1
        assert "not registered" in result.output


# ============================================================================
# Test Command Tests (T029)
# ============================================================================


class TestTestCommand:
    """Tests for collection test subcommand."""

    def test_test_accessible_path(self, runner, mock_config, sample_collection_cache, tmp_path):
        """Test reports accessible path to server."""
        # Create a temp directory with files
        test_dir = tmp_path / "photos"
        test_dir.mkdir()
        (test_dir / "file1.jpg").write_text("x")
        (test_dir / "file2.cr3").write_text("x")

        # Patch the cache to return collection with test_dir as location
        cache = CollectionCache(
            agent_guid="agt_01hgw2bbg0000000000000001",
            synced_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            collections=[
                CachedCollection(
                    guid="col_01hgw2bbg0000000000000001",
                    name="Test Collection",
                    type="LOCAL",
                    location=str(test_dir),
                    bound_agent_guid="agt_01hgw2bbg0000000000000001",
                    is_accessible=True,
                    supports_offline=True,
                ),
            ],
        )

        mock_test_response = {
            "guid": "col_01hgw2bbg0000000000000001",
            "is_accessible": True,
            "updated_at": "2026-01-28T12:00:00.000Z",
        }

        with patch("cli.collection.col_cache") as mock_cache, \
             patch("cli.collection._test_collection_async", new_callable=AsyncMock, return_value=mock_test_response):
            mock_cache.load.return_value = cache
            result = runner.invoke(collection, ["test", "col_01hgw2bbg0000000000000001"])
        assert result.exit_code == 0
        assert "Accessible:" in result.output
        assert "yes" in result.output
        assert "Server updated" in result.output

    def test_test_inaccessible_path(self, runner, mock_config):
        """Test reports inaccessible path to server."""
        cache = CollectionCache(
            agent_guid="agt_01hgw2bbg0000000000000001",
            synced_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            collections=[
                CachedCollection(
                    guid="col_01hgw2bbg0000000000000002",
                    name="Missing Collection",
                    type="LOCAL",
                    location="/nonexistent/path/to/photos",
                    bound_agent_guid="agt_01hgw2bbg0000000000000001",
                    is_accessible=True,
                    supports_offline=True,
                ),
            ],
        )

        mock_test_response = {
            "guid": "col_01hgw2bbg0000000000000002",
            "is_accessible": False,
            "updated_at": "2026-01-28T12:00:00.000Z",
        }

        with patch("cli.collection.col_cache") as mock_cache, \
             patch("cli.collection._test_collection_async", new_callable=AsyncMock, return_value=mock_test_response):
            mock_cache.load.return_value = cache
            result = runner.invoke(collection, ["test", "col_01hgw2bbg0000000000000002"])
        assert result.exit_code == 0
        assert "no" in result.output
        assert "does not exist" in result.output

    def test_test_guid_not_in_cache(self, runner, mock_config, sample_collection_cache):
        """Unknown GUID shows error."""
        with patch("cli.collection.col_cache") as mock_cache:
            mock_cache.load.return_value = sample_collection_cache
            result = runner.invoke(collection, ["test", "col_01hgw2bbg0000000000000099"])
        assert result.exit_code == 1
        assert "not found in local cache" in result.output

    def test_test_no_cache(self, runner, mock_config):
        """No cache shows error."""
        with patch("cli.collection.col_cache") as mock_cache:
            mock_cache.load.return_value = None
            result = runner.invoke(collection, ["test", "col_01hgw2bbg0000000000000001"])
        assert result.exit_code == 1
        assert "not found in local cache" in result.output

    def test_test_remote_collection_rejected(self, runner, mock_config):
        """Remote (non-LOCAL) collections cannot be tested."""
        cache = CollectionCache(
            agent_guid="agt_01hgw2bbg0000000000000001",
            synced_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            collections=[
                CachedCollection(
                    guid="col_01hgw2bbg0000000000000003",
                    name="S3 Bucket",
                    type="S3",
                    location="s3://bucket/prefix",
                    connector_guid="con_01hgw2bbg0000000000000001",
                    is_accessible=True,
                    supports_offline=False,
                ),
            ],
        )

        with patch("cli.collection.col_cache") as mock_cache:
            mock_cache.load.return_value = cache
            result = runner.invoke(collection, ["test", "col_01hgw2bbg0000000000000003"])
        assert result.exit_code == 1
        assert "Only LOCAL collections" in result.output

    def test_test_connection_error(self, runner, mock_config, tmp_path):
        """Connection error during test report."""
        from src.api_client import ConnectionError as AgentConnectionError

        test_dir = tmp_path / "photos"
        test_dir.mkdir()

        cache = CollectionCache(
            agent_guid="agt_01hgw2bbg0000000000000001",
            synced_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            collections=[
                CachedCollection(
                    guid="col_01hgw2bbg0000000000000001",
                    name="Test Collection",
                    type="LOCAL",
                    location=str(test_dir),
                    bound_agent_guid="agt_01hgw2bbg0000000000000001",
                    is_accessible=True,
                    supports_offline=True,
                ),
            ],
        )

        with patch("cli.collection.col_cache") as mock_cache, \
             patch("cli.collection._test_collection_async", new_callable=AsyncMock,
                   side_effect=AgentConnectionError("Connection refused")):
            mock_cache.load.return_value = cache
            result = runner.invoke(collection, ["test", "col_01hgw2bbg0000000000000001"])
        assert result.exit_code == 2
        assert "Connection failed" in result.output

    def test_test_unregistered_agent(self, runner, mock_config_unregistered):
        """Unregistered agent fails for test."""
        result = runner.invoke(collection, ["test", "col_01hgw2bbg0000000000000001"])
        assert result.exit_code == 1
        assert "not registered" in result.output
