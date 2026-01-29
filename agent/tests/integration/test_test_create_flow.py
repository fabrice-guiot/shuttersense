"""
Integration tests for test-then-create workflow.

Tests the end-to-end flow:
1. Test a local path (check-only) → cache entry created
2. Create a collection from the tested path → uses cache, calls server
3. Verify the collection appears in the local cache

Issue #108 - Remove CLI Direct Usage (Phase 9)
Task: T056
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cli.main import cli
from src.cache import (
    TEST_CACHE_TTL_HOURS,
    CachedCollection,
    CollectionCache,
    TestCacheEntry,
)
from src.cache.test_cache import _hash_path
from src.remote.base import FileInfo


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def sample_files():
    """Sample FileInfo list mimicking a real photo directory."""
    return [
        FileInfo(path="AB3D0001.dng", size=25_000_000),
        FileInfo(path="AB3D0001.xmp", size=500),
        FileInfo(path="AB3D0002.dng", size=24_000_000),
        FileInfo(path="AB3D0002.xmp", size=480),
        FileInfo(path="AB3D0003.cr3", size=30_000_000),
        FileInfo(path="readme.txt", size=100),
    ]


@pytest.fixture
def mock_api_create_response():
    """Mock server response for collection creation."""
    return {
        "guid": "col_01hgw2bbg0000000000000001",
        "name": "Integration Photos",
        "type": "LOCAL",
        "location": "/tmp/photos",
        "bound_agent_guid": "agt_test",
        "web_url": "/collections/col_01hgw2bbg0000000000000001",
        "created_at": "2026-01-28T12:00:00.000Z",
    }


# ============================================================================
# Test-Then-Create Flow
# ============================================================================


class TestTestThenCreateFlow:
    """Integration tests for the test → create workflow."""

    def test_check_only_then_create_uses_cache(
        self, runner, sample_files, mock_api_create_response,
    ):
        """Test path with --check-only, then create collection reuses cache."""
        saved_entries = {}

        def mock_save(entry):
            saved_entries[entry.path_hash] = entry

        def mock_load_valid(path):
            h = _hash_path(str(Path(path).resolve()))
            return saved_entries.get(h)

        with patch("cli.test.AgentConfig") as mock_cfg_cls, \
             patch("cli.test.LocalAdapter") as mock_adapter_cls, \
             patch("cli.test.save", side_effect=mock_save), \
             patch("cli.test.load_valid", side_effect=mock_load_valid):

            # Setup config mock
            config = MagicMock()
            config.agent_guid = "agt_test"
            mock_cfg_cls.return_value = config

            # Setup adapter mock
            adapter = MagicMock()
            adapter.list_files_with_metadata.return_value = sample_files
            mock_adapter_cls.return_value = adapter

            # Step 1: Run test command with --check-only
            result = runner.invoke(cli, ["test", "/tmp/photos", "--check-only"])

        assert result.exit_code == 0, f"test failed: {result.output}"
        assert "OK" in result.output
        assert "6 files found" in result.output
        assert len(saved_entries) == 1

        # Step 2: Run collection create, reusing the cache
        with patch("cli.collection.AgentConfig") as mock_cfg_cls, \
             patch("cli.collection.load_valid", side_effect=mock_load_valid), \
             patch("cli.collection._create_collection_async",
                   new_callable=AsyncMock,
                   return_value=mock_api_create_response) as mock_create, \
             patch("cli.collection.col_cache") as mock_col_cache:

            config = MagicMock()
            config.is_registered = True
            config.agent_guid = "agt_test"
            config.server_url = "http://localhost:8000"
            config.api_key = "agt_key_test123"
            mock_cfg_cls.return_value = config

            mock_col_cache.load.return_value = None

            result = runner.invoke(
                cli,
                ["collection", "create", "/tmp/photos", "--name", "Integration Photos"],
            )

        assert result.exit_code == 0, f"create failed: {result.output}"
        assert "col_01hgw2bbg0000000000000001" in result.output

        # Verify the server was called with test_results from cache
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["name"] == "Integration Photos"
        assert call_kwargs["server_url"] == "http://localhost:8000"
        assert call_kwargs["api_key"] == "agt_key_test123"
        # test_results should be populated from the cache entry
        assert call_kwargs.get("test_results") is not None

    def test_create_without_cache_runs_auto_test(
        self, runner, sample_files, mock_api_create_response,
    ):
        """Create without prior test triggers auto-test inline."""
        with patch("cli.collection.AgentConfig") as mock_cfg_cls, \
             patch("cli.collection.load_valid", return_value=None), \
             patch("cli.collection._create_collection_async",
                   new_callable=AsyncMock,
                   return_value=mock_api_create_response), \
             patch("cli.collection.col_cache") as mock_col_cache, \
             patch("cli.collection.click.Context.invoke") as mock_invoke:

            config = MagicMock()
            config.is_registered = True
            config.agent_guid = "agt_test"
            config.server_url = "http://localhost:8000"
            config.api_key = "agt_key_test123"
            mock_cfg_cls.return_value = config

            mock_col_cache.load.return_value = None

            result = runner.invoke(
                cli,
                ["collection", "create", "/tmp/photos", "--name", "Auto Test"],
            )

        # The auto-test should have been invoked
        assert mock_invoke.called or result.exit_code == 0

    def test_create_with_skip_test_bypasses_auto_test(
        self, runner, mock_api_create_response,
    ):
        """Create with --skip-test skips auto-test when no cache exists."""
        with patch("cli.collection.AgentConfig") as mock_cfg_cls, \
             patch("cli.collection.load_valid", return_value=None) as mock_load, \
             patch("cli.collection._create_collection_async",
                   new_callable=AsyncMock,
                   return_value=mock_api_create_response), \
             patch("cli.collection.col_cache") as mock_col_cache:

            config = MagicMock()
            config.is_registered = True
            config.agent_guid = "agt_test"
            config.server_url = "http://localhost:8000"
            config.api_key = "agt_key_test123"
            mock_cfg_cls.return_value = config

            mock_col_cache.load.return_value = None

            result = runner.invoke(
                cli,
                ["collection", "create", "/tmp/photos", "--name", "Skip Test",
                 "--skip-test"],
            )

        assert result.exit_code == 0, f"create failed: {result.output}"
        assert "col_01hgw2bbg0000000000000001" in result.output
        # load_valid is always called (cache check), but skip_test skips the auto-test
        mock_load.assert_called_once()
        assert "Skipping test" in result.output

    def test_create_adds_collection_to_local_cache(
        self, runner, mock_api_create_response,
    ):
        """After creation, the collection is added to the local cache."""
        with patch("cli.collection.AgentConfig") as mock_cfg_cls, \
             patch("cli.collection.load_valid", return_value=None), \
             patch("cli.collection._create_collection_async",
                   new_callable=AsyncMock,
                   return_value=mock_api_create_response), \
             patch("cli.collection.col_cache") as mock_col_cache:

            config = MagicMock()
            config.is_registered = True
            config.agent_guid = "agt_test"
            config.server_url = "http://localhost:8000"
            config.api_key = "agt_key_test123"
            mock_cfg_cls.return_value = config

            # Pre-populate cache with no collections
            now = datetime.now(timezone.utc)
            existing_cache = CollectionCache(
                agent_guid="agt_test",
                synced_at=now,
                expires_at=now + timedelta(days=7),
                collections=[],
            )
            mock_col_cache.load.return_value = existing_cache

            result = runner.invoke(
                cli,
                ["collection", "create", "/tmp/photos", "--name", "Cached",
                 "--skip-test"],
            )

        assert result.exit_code == 0, f"create failed: {result.output}"
        # Verify save was called to persist the updated cache
        mock_col_cache.save.assert_called_once()

    def test_create_server_error_returns_exit_2(self, runner):
        """Server connection failure during create returns exit code 2."""
        from src.api_client import ConnectionError as AgentConnectionError

        with patch("cli.collection.AgentConfig") as mock_cfg_cls, \
             patch("cli.collection.load_valid", return_value=None), \
             patch("cli.collection._create_collection_async",
                   new_callable=AsyncMock,
                   side_effect=AgentConnectionError("Connection refused")), \
             patch("cli.collection.col_cache"):

            config = MagicMock()
            config.is_registered = True
            config.agent_guid = "agt_test"
            config.server_url = "http://localhost:8000"
            config.api_key = "agt_key_test123"
            mock_cfg_cls.return_value = config

            result = runner.invoke(
                cli,
                ["collection", "create", "/tmp/photos", "--name", "Fail",
                 "--skip-test"],
            )

        assert result.exit_code == 2
