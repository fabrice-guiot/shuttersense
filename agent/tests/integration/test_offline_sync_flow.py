"""
Integration tests for offline-run-then-sync workflow.

Tests the end-to-end flow:
1. Run a tool offline → result saved locally
2. Sync offline results → result uploaded to server, local file cleaned up
3. Verify sync summary output

Issue #108 - Remove CLI Direct Usage (Phase 9)
Task: T057
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
    COLLECTION_CACHE_TTL_DAYS,
    CachedCollection,
    CollectionCache,
    OfflineResult,
)


# ============================================================================
# Fixtures
# ============================================================================


FAKE_INPUT_STATE_HASH = "a" * 64


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def local_collection_cache():
    """Cache with a LOCAL collection."""
    now = datetime.now(timezone.utc)
    return CollectionCache(
        agent_guid="agt_test",
        synced_at=now,
        expires_at=now + timedelta(days=COLLECTION_CACHE_TTL_DAYS),
        collections=[
            CachedCollection(
                guid="col_local123",
                name="Local Photos",
                type="LOCAL",
                location="/tmp/photos",
                bound_agent_guid="agt_test",
                is_accessible=True,
                supports_offline=True,
            ),
        ],
    )


@pytest.fixture
def sample_offline_result():
    """An OfflineResult as created by `run --offline`."""
    return OfflineResult(
        result_id="offline-uuid-001",
        collection_guid="col_local123",
        collection_name="Local Photos",
        tool="photostats",
        executed_at=datetime(2026, 1, 28, 10, 0, 0, tzinfo=timezone.utc),
        agent_guid="agt_test",
        agent_version="v1.0.0-test",
        analysis_data={"total_files": 10, "results": {}},
        input_state_hash=FAKE_INPUT_STATE_HASH,
    )


@pytest.fixture
def mock_upload_success():
    """Mock server response for result upload."""
    return {
        "job_guid": "job_01hgw2bbg0000000000000001",
        "result_guid": "res_01hgw2bbg0000000000000001",
        "collection_guid": "col_local123",
        "status": "uploaded",
    }


# ============================================================================
# Offline Run → Sync Flow
# ============================================================================


class TestOfflineSyncFlow:
    """Integration tests for the offline run → sync workflow."""

    def test_offline_run_then_sync_full_flow(
        self, runner, local_collection_cache, mock_upload_success,
    ):
        """Run offline creates a local result, then sync uploads it."""
        saved_results = []

        def mock_save(result):
            saved_results.append(result)
            return Path(f"/tmp/results/{result.result_id}.json")

        # Step 1: Run offline
        with patch("cli.run.AgentConfig") as mock_cfg_cls, \
             patch("cli.run.col_cache") as mock_cache, \
             patch("cli.run._prepare_analysis", return_value=([], FAKE_INPUT_STATE_HASH)), \
             patch("cli.run._execute_tool", return_value=({"total_files": 10, "results": {}}, None)), \
             patch("cli.run.result_store") as mock_store:

            config = MagicMock()
            config.is_registered = True
            config.agent_guid = "agt_test"
            config.server_url = "http://localhost:8000"
            config.api_key = "agt_key_test123"
            mock_cfg_cls.return_value = config

            mock_cache.load.return_value = local_collection_cache
            mock_store.save.side_effect = mock_save

            result = runner.invoke(
                cli,
                ["run", "col_local123", "--tool", "photostats", "--offline"],
            )

        assert result.exit_code == 0, f"offline run failed: {result.output}"
        assert "Result saved locally" in result.output
        assert len(saved_results) == 1

        offline_result = saved_results[0]

        # Step 2: Sync the result to the server
        with patch("cli.sync_results.AgentConfig") as mock_cfg_cls, \
             patch("cli.sync_results.result_store") as mock_store, \
             patch("cli.sync_results._upload_result_async",
                   new_callable=AsyncMock,
                   return_value=mock_upload_success):

            config = MagicMock()
            config.is_registered = True
            config.agent_guid = "agt_test"
            config.server_url = "http://localhost:8000"
            config.api_key = "agt_key_test123"
            mock_cfg_cls.return_value = config

            mock_store.list_pending.return_value = [offline_result]

            result = runner.invoke(cli, ["sync"])

        assert result.exit_code == 0, f"sync failed: {result.output}"
        assert "Sync complete!" in result.output
        assert "1 result(s) uploaded" in result.output
        mock_store.mark_synced.assert_called_once_with(offline_result.result_id)
        mock_store.delete.assert_called_once_with(offline_result.result_id)

    def test_sync_no_pending_results(self, runner):
        """Sync with no pending results prints message and exits cleanly."""
        with patch("cli.sync_results.AgentConfig") as mock_cfg_cls, \
             patch("cli.sync_results.result_store") as mock_store:

            config = MagicMock()
            config.is_registered = True
            config.agent_guid = "agt_test"
            config.server_url = "http://localhost:8000"
            config.api_key = "agt_key_test123"
            mock_cfg_cls.return_value = config

            mock_store.list_pending.return_value = []

            result = runner.invoke(cli, ["sync"])

        assert result.exit_code == 0
        assert "No pending results" in result.output

    def test_sync_dry_run_lists_without_uploading(
        self, runner, sample_offline_result,
    ):
        """Sync with --dry-run lists pending results without uploading."""
        with patch("cli.sync_results.AgentConfig") as mock_cfg_cls, \
             patch("cli.sync_results.result_store") as mock_store, \
             patch("cli.sync_results._upload_result_async",
                   new_callable=AsyncMock) as mock_upload:

            config = MagicMock()
            config.is_registered = True
            config.agent_guid = "agt_test"
            config.server_url = "http://localhost:8000"
            config.api_key = "agt_key_test123"
            mock_cfg_cls.return_value = config

            mock_store.list_pending.return_value = [sample_offline_result]

            result = runner.invoke(cli, ["sync", "--dry-run"])

        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "1 result(s) would be uploaded" in result.output
        mock_upload.assert_not_called()
        mock_store.mark_synced.assert_not_called()

    def test_sync_connection_failure_reports_error(
        self, runner, sample_offline_result,
    ):
        """Sync with server connection failure reports error and exits 2."""
        from src.api_client import ConnectionError as AgentConnectionError

        with patch("cli.sync_results.AgentConfig") as mock_cfg_cls, \
             patch("cli.sync_results.result_store") as mock_store, \
             patch("cli.sync_results._upload_result_async",
                   new_callable=AsyncMock,
                   side_effect=AgentConnectionError("Connection refused")):

            config = MagicMock()
            config.is_registered = True
            config.agent_guid = "agt_test"
            config.server_url = "http://localhost:8000"
            config.api_key = "agt_key_test123"
            mock_cfg_cls.return_value = config

            mock_store.list_pending.return_value = [sample_offline_result]

            result = runner.invoke(cli, ["sync"])

        assert result.exit_code == 2
        assert "connection failed" in result.output
        assert "Sync partially complete" in result.output
        mock_store.mark_synced.assert_not_called()
        mock_store.delete.assert_not_called()

    def test_sync_409_conflict_marks_as_synced(
        self, runner, sample_offline_result,
    ):
        """Sync with 409 Conflict (already uploaded) still marks as synced."""
        from src.api_client import ApiError

        with patch("cli.sync_results.AgentConfig") as mock_cfg_cls, \
             patch("cli.sync_results.result_store") as mock_store, \
             patch("cli.sync_results._upload_result_async",
                   new_callable=AsyncMock,
                   side_effect=ApiError("Duplicate", status_code=409)):

            config = MagicMock()
            config.is_registered = True
            config.agent_guid = "agt_test"
            config.server_url = "http://localhost:8000"
            config.api_key = "agt_key_test123"
            mock_cfg_cls.return_value = config

            mock_store.list_pending.return_value = [sample_offline_result]

            result = runner.invoke(cli, ["sync"])

        assert result.exit_code == 0
        assert "already uploaded" in result.output
        assert "Sync complete!" in result.output
        mock_store.mark_synced.assert_called_once_with(sample_offline_result.result_id)
        mock_store.delete.assert_called_once_with(sample_offline_result.result_id)

    def test_sync_unregistered_agent_fails(self, runner):
        """Sync with unregistered agent fails with exit code 1."""
        with patch("cli.sync_results.AgentConfig") as mock_cfg_cls:
            config = MagicMock()
            config.is_registered = False
            mock_cfg_cls.return_value = config

            result = runner.invoke(cli, ["sync"])

        assert result.exit_code == 1
        assert "not registered" in result.output
