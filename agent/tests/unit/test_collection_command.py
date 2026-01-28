"""
Unit tests for the collection CLI commands.

Tests collection create subcommand: cache lookup, auto-test, name prompt,
skip-test flag, analyze flag, server errors, and success output.

Issue #108 - Remove CLI Direct Usage
Task: T018
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cli.collection import collection
from src.cache import TEST_CACHE_TTL_HOURS, TestCacheEntry
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
        config.agent_guid = "agt_test"
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
        agent_id="agt_test",
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
        agent_id="agt_test",
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
        "bound_agent_guid": "agt_test",
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
            test_cfg.agent_guid = "agt_test"
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

    def test_analyze_flag_acknowledged(self, runner, mock_config, valid_cache_entry, mock_api_success):
        with patch("cli.collection.load_valid", return_value=valid_cache_entry), \
             patch("cli.collection._create_collection_async", new_callable=AsyncMock, return_value=mock_api_success):
            result = runner.invoke(
                collection, ["create", "/tmp/photos", "--name", "Test", "--analyze"]
            )
        assert result.exit_code == 0
        assert "--analyze" in result.output


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
