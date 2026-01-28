"""
Unit tests for the sync CLI command.

Tests dry-run mode, upload, cleanup, partial failure, and resume.

Issue #108 - Remove CLI Direct Usage
Task: T039
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cli.sync_results import sync
from src.cache import OfflineResult


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
    with patch("cli.sync_results.AgentConfig") as mock_cls:
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
    with patch("cli.sync_results.AgentConfig") as mock_cls:
        config = MagicMock()
        config.is_registered = False
        mock_cls.return_value = config
        yield config


@pytest.fixture
def sample_pending_results():
    """Two pending offline results."""
    return [
        OfflineResult(
            result_id="uuid-001",
            collection_guid="col_01hgw2bbg0000000000000001",
            collection_name="Vacation 2024",
            tool="photostats",
            executed_at=datetime.now(timezone.utc),
            agent_guid="agt_test",
            agent_version="v1.0.0",
            analysis_data={"total_files": 100, "results": {}},
        ),
        OfflineResult(
            result_id="uuid-002",
            collection_guid="col_01hgw2bbg0000000000000002",
            collection_name="Wedding Photos",
            tool="photo_pairing",
            executed_at=datetime.now(timezone.utc),
            agent_guid="agt_test",
            agent_version="v1.0.0",
            analysis_data={"image_count": 50, "results": {}},
        ),
    ]


# ============================================================================
# Registration Tests
# ============================================================================


class TestSyncRegistration:
    """Tests for agent registration checks."""

    def test_unregistered_agent_fails(self, runner, mock_config_unregistered):
        result = runner.invoke(sync, [])
        assert result.exit_code == 1
        assert "not registered" in result.output

    def test_config_load_failure(self, runner):
        with patch("cli.sync_results.AgentConfig", side_effect=Exception("config broken")):
            result = runner.invoke(sync, [])
        assert result.exit_code == 1
        assert "Failed to load agent config" in result.output


# ============================================================================
# No Pending Results
# ============================================================================


class TestNoPending:
    """Tests when no results are pending."""

    def test_no_pending_results(self, runner, mock_config):
        with patch("cli.sync_results.result_store") as mock_store:
            mock_store.list_pending.return_value = []
            result = runner.invoke(sync, [])
        assert result.exit_code == 0
        assert "No pending results" in result.output


# ============================================================================
# Dry Run Tests
# ============================================================================


class TestDryRun:
    """Tests for --dry-run mode."""

    def test_dry_run_lists_pending(self, runner, mock_config, sample_pending_results):
        with patch("cli.sync_results.result_store") as mock_store:
            mock_store.list_pending.return_value = sample_pending_results
            result = runner.invoke(sync, ["--dry-run"])
        assert result.exit_code == 0
        assert "2 pending result(s)" in result.output
        assert "photostats" in result.output
        assert "photo_pairing" in result.output
        assert "Vacation 2024" in result.output
        assert "Wedding Photos" in result.output
        assert "Dry run" in result.output

    def test_dry_run_does_not_upload(self, runner, mock_config, sample_pending_results):
        with patch("cli.sync_results.result_store") as mock_store, \
             patch("cli.sync_results._upload_result_async") as mock_upload:
            mock_store.list_pending.return_value = sample_pending_results
            result = runner.invoke(sync, ["--dry-run"])
        mock_upload.assert_not_called()


# ============================================================================
# Upload Tests
# ============================================================================


class TestUpload:
    """Tests for result upload."""

    def test_upload_all_success(self, runner, mock_config, sample_pending_results):
        with patch("cli.sync_results.result_store") as mock_store, \
             patch("cli.sync_results._upload_result_async", new_callable=AsyncMock, return_value={"status": "uploaded"}):
            mock_store.list_pending.return_value = sample_pending_results
            mock_store.mark_synced.return_value = True
            mock_store.delete.return_value = True
            result = runner.invoke(sync, [])
        assert result.exit_code == 0
        assert "Sync complete!" in result.output
        assert "2 result(s) uploaded" in result.output
        assert mock_store.mark_synced.call_count == 2
        assert mock_store.delete.call_count == 2

    def test_upload_handles_already_uploaded(self, runner, mock_config, sample_pending_results):
        from src.api_client import ApiError

        with patch("cli.sync_results.result_store") as mock_store, \
             patch("cli.sync_results._upload_result_async", new_callable=AsyncMock,
                   side_effect=ApiError("Already uploaded", status_code=409)):
            mock_store.list_pending.return_value = [sample_pending_results[0]]
            mock_store.mark_synced.return_value = True
            mock_store.delete.return_value = True
            result = runner.invoke(sync, [])
        assert result.exit_code == 0
        assert "already uploaded" in result.output
        mock_store.mark_synced.assert_called_once()
        mock_store.delete.assert_called_once()


# ============================================================================
# Partial Failure Tests
# ============================================================================


class TestPartialFailure:
    """Tests for partial failure and resume."""

    def test_partial_failure(self, runner, mock_config, sample_pending_results):
        from src.api_client import ConnectionError as AgentConnectionError

        call_count = [0]

        async def mock_upload(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"status": "uploaded"}
            raise AgentConnectionError("Connection lost")

        with patch("cli.sync_results.result_store") as mock_store, \
             patch("cli.sync_results._upload_result_async", new_callable=AsyncMock, side_effect=mock_upload):
            mock_store.list_pending.return_value = sample_pending_results
            mock_store.mark_synced.return_value = True
            mock_store.delete.return_value = True
            result = runner.invoke(sync, [])
        assert result.exit_code == 2
        assert "partially complete" in result.output
        assert "1 uploaded" in result.output
        assert "1 failed" in result.output

    def test_all_failures(self, runner, mock_config, sample_pending_results):
        from src.api_client import ConnectionError as AgentConnectionError

        with patch("cli.sync_results.result_store") as mock_store, \
             patch("cli.sync_results._upload_result_async", new_callable=AsyncMock,
                   side_effect=AgentConnectionError("Connection refused")):
            mock_store.list_pending.return_value = sample_pending_results
            result = runner.invoke(sync, [])
        assert result.exit_code == 2
        assert "0 uploaded" in result.output
        assert "2 failed" in result.output

    def test_auth_failure(self, runner, mock_config, sample_pending_results):
        from src.api_client import AuthenticationError

        with patch("cli.sync_results.result_store") as mock_store, \
             patch("cli.sync_results._upload_result_async", new_callable=AsyncMock,
                   side_effect=AuthenticationError("Invalid key", status_code=401)):
            mock_store.list_pending.return_value = [sample_pending_results[0]]
            result = runner.invoke(sync, [])
        assert result.exit_code == 2
        assert "auth failed" in result.output
