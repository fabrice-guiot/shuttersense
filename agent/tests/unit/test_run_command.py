"""
Unit tests for the run CLI command.

Tests online mode, offline mode, remote collection rejection,
tool validation, and error handling.

Issue #108 - Remove CLI Direct Usage
Task: T038
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cli.run import run
from src.cache import (
    COLLECTION_CACHE_TTL_DAYS,
    CachedCollection,
    CollectionCache,
    TeamConfigCache,
)
from src.config_resolver import ConfigResult


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
    with patch("cli.run.AgentConfig") as mock_cls:
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
    with patch("cli.run.AgentConfig") as mock_cls:
        config = MagicMock()
        config.is_registered = False
        mock_cls.return_value = config
        yield config


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
def remote_collection_cache():
    """Cache with an S3 collection."""
    now = datetime.now(timezone.utc)
    return CollectionCache(
        agent_guid="agt_test",
        synced_at=now,
        expires_at=now + timedelta(days=COLLECTION_CACHE_TTL_DAYS),
        collections=[
            CachedCollection(
                guid="col_s3bucket",
                name="S3 Bucket",
                type="S3",
                location="s3://bucket/prefix",
                connector_guid="con_test",
                is_accessible=True,
                supports_offline=False,
            ),
        ],
    )


@pytest.fixture
def mock_upload_success():
    """Mock successful upload response."""
    return {
        "job_guid": "job_01hgw2bbg0000000000000001",
        "result_guid": "res_01hgw2bbg0000000000000001",
        "collection_guid": "col_local123",
        "status": "uploaded",
    }


FAKE_INPUT_STATE_HASH = "a" * 64


def _make_team_config():
    """Create a minimal TeamConfigCache for tests."""
    now = datetime.now(timezone.utc)
    return TeamConfigCache(
        agent_guid="agt_test",
        fetched_at=now,
        expires_at=now + timedelta(hours=24),
        photo_extensions=[".dng", ".cr3"],
        metadata_extensions=[".xmp"],
        require_sidecar=[".cr3"],
        cameras={},
        processing_methods={},
        default_pipeline=None,
    )


@pytest.fixture(autouse=True)
def mock_team_config():
    """Mock resolve_team_config so tests don't need a server or cache file."""
    with patch("cli.run.resolve_team_config") as mock_resolve:
        mock_resolve.return_value = ConfigResult(
            config=_make_team_config(),
            source="cache",
            message="from cache (test)",
        )
        yield mock_resolve


@pytest.fixture
def mock_prepare_analysis():
    """Mock _prepare_analysis to return fake file_infos and hash."""
    with patch("cli.run._prepare_analysis", return_value=([], FAKE_INPUT_STATE_HASH)) as mock:
        yield mock


@pytest.fixture
def mock_fetch_previous_result_none():
    """Mock _fetch_previous_result to return None (no previous result)."""
    with patch("cli.run._fetch_previous_result", return_value=None) as mock:
        yield mock


# ============================================================================
# Registration Tests
# ============================================================================


class TestRunRegistration:
    """Tests for agent registration checks."""

    def test_unregistered_agent_fails(self, runner, mock_config_unregistered):
        result = runner.invoke(run, ["col_local123", "--tool", "photostats"])
        assert result.exit_code == 1
        assert "not registered" in result.output

    def test_config_load_failure(self, runner):
        with patch("cli.run.AgentConfig", side_effect=Exception("config broken")):
            result = runner.invoke(run, ["col_local123", "--tool", "photostats"])
        assert result.exit_code == 1
        assert "Failed to load agent config" in result.output


# ============================================================================
# Collection Lookup Tests
# ============================================================================


class TestCollectionLookup:
    """Tests for collection cache lookup."""

    def test_collection_not_in_cache(self, runner, mock_config):
        with patch("cli.run.col_cache") as mock_cache:
            mock_cache.load.return_value = None
            result = runner.invoke(run, ["col_unknown", "--tool", "photostats"])
        assert result.exit_code == 1
        assert "not found in local cache" in result.output

    def test_collection_found_in_cache(
        self, runner, mock_config, local_collection_cache,
        mock_upload_success, mock_prepare_analysis, mock_fetch_previous_result_none,
    ):
        with patch("cli.run.col_cache") as mock_cache, \
             patch("cli.run._execute_tool", return_value=({"total_files": 10, "results": {}}, None)), \
             patch("cli.run._upload_result_async", new_callable=AsyncMock, return_value=mock_upload_success):
            mock_cache.load.return_value = local_collection_cache
            result = runner.invoke(run, ["col_local123", "--tool", "photostats"])
        assert result.exit_code == 0
        assert "Local Photos" in result.output


# ============================================================================
# Offline Mode Tests
# ============================================================================


class TestOfflineMode:
    """Tests for offline execution mode."""

    def test_offline_saves_result(
        self, runner, mock_config, local_collection_cache, mock_prepare_analysis,
    ):
        with patch("cli.run.col_cache") as mock_cache, \
             patch("cli.run._execute_tool", return_value=({"total_files": 10, "results": {}}, None)), \
             patch("cli.run.result_store") as mock_store:
            mock_cache.load.return_value = local_collection_cache
            mock_store.save.return_value = Path("/tmp/results/test-uuid.json")
            result = runner.invoke(run, ["col_local123", "--tool", "photostats", "--offline"])
        assert result.exit_code == 0
        assert "Result saved locally" in result.output
        mock_store.save.assert_called_once()

    def test_offline_rejects_remote_collection(self, runner, mock_config, remote_collection_cache):
        with patch("cli.run.col_cache") as mock_cache:
            mock_cache.load.return_value = remote_collection_cache
            result = runner.invoke(run, ["col_s3bucket", "--tool", "photostats", "--offline"])
        assert result.exit_code == 1
        assert "Offline mode only supports LOCAL" in result.output


# ============================================================================
# Online Mode Tests
# ============================================================================


class TestOnlineMode:
    """Tests for online execution mode."""

    def test_online_uploads_result(
        self, runner, mock_config, local_collection_cache,
        mock_upload_success, mock_prepare_analysis, mock_fetch_previous_result_none,
    ):
        with patch("cli.run.col_cache") as mock_cache, \
             patch("cli.run._execute_tool", return_value=({"total_files": 10, "results": {}}, None)), \
             patch("cli.run._upload_result_async", new_callable=AsyncMock, return_value=mock_upload_success):
            mock_cache.load.return_value = local_collection_cache
            result = runner.invoke(run, ["col_local123", "--tool", "photostats"])
        assert result.exit_code == 0
        assert "Result uploaded successfully" in result.output
        assert "job_01hgw2bbg0000000000000001" in result.output

    def test_online_connection_error(
        self, runner, mock_config, local_collection_cache,
        mock_prepare_analysis, mock_fetch_previous_result_none,
    ):
        from src.api_client import ConnectionError as AgentConnectionError

        with patch("cli.run.col_cache") as mock_cache, \
             patch("cli.run._execute_tool", return_value=({"total_files": 10, "results": {}}, None)), \
             patch("cli.run._upload_result_async", new_callable=AsyncMock,
                   side_effect=AgentConnectionError("Connection refused")):
            mock_cache.load.return_value = local_collection_cache
            result = runner.invoke(run, ["col_local123", "--tool", "photostats"])
        assert result.exit_code == 2
        assert "Connection failed" in result.output
        assert "--offline" in result.output  # Tip about offline mode

    def test_online_rejects_remote_collection(self, runner, mock_config, remote_collection_cache):
        with patch("cli.run.col_cache") as mock_cache:
            mock_cache.load.return_value = remote_collection_cache
            result = runner.invoke(run, ["col_s3bucket", "--tool", "photostats"])
        assert result.exit_code == 1
        assert "not yet supported via CLI" in result.output

    def test_online_no_change_detected(
        self, runner, mock_config, local_collection_cache, mock_prepare_analysis,
    ):
        """When previous result hash matches current, skip execution and record on server."""
        previous_result = {
            "guid": "res_previous123",
            "input_state_hash": FAKE_INPUT_STATE_HASH,
            "completed_at": "2026-01-20T10:00:00+00:00",
        }
        no_change_response = {
            "job_guid": "job_nochange001",
            "result_guid": "res_nochange001",
            "collection_guid": "col_local123",
            "status": "no_change",
        }
        with patch("cli.run.col_cache") as mock_cache, \
             patch("cli.run._fetch_previous_result", return_value=previous_result), \
             patch("cli.run._record_no_change", return_value=no_change_response) as mock_record, \
             patch("cli.run._execute_tool") as mock_execute:
            mock_cache.load.return_value = local_collection_cache
            result = runner.invoke(run, ["col_local123", "--tool", "photostats"])
        assert result.exit_code == 0
        assert "No changes detected" in result.output
        assert "res_nochange001" in result.output
        assert "res_previous123" in result.output
        mock_execute.assert_not_called()
        mock_record.assert_called_once_with(
            mock_config, "col_local123", "photostats",
            FAKE_INPUT_STATE_HASH, "res_previous123",
        )

    def test_online_no_change_recording_failure(
        self, runner, mock_config, local_collection_cache, mock_prepare_analysis,
    ):
        """When no-change recording fails, still exit 0 (detection succeeded)."""
        previous_result = {
            "guid": "res_previous123",
            "input_state_hash": FAKE_INPUT_STATE_HASH,
            "completed_at": "2026-01-20T10:00:00+00:00",
        }
        with patch("cli.run.col_cache") as mock_cache, \
             patch("cli.run._fetch_previous_result", return_value=previous_result), \
             patch("cli.run._record_no_change", return_value=None), \
             patch("cli.run._execute_tool") as mock_execute:
            mock_cache.load.return_value = local_collection_cache
            result = runner.invoke(run, ["col_local123", "--tool", "photostats"])
        assert result.exit_code == 0
        assert "No changes detected" in result.output
        assert "res_previous123" in result.output
        mock_execute.assert_not_called()

    def test_online_change_detected_runs_analysis(
        self, runner, mock_config, local_collection_cache, mock_upload_success,
        mock_prepare_analysis,
    ):
        """When previous result hash differs, run analysis normally."""
        previous_result = {
            "guid": "res_previous123",
            "input_state_hash": "b" * 64,  # Different from FAKE_INPUT_STATE_HASH
            "completed_at": "2026-01-20T10:00:00+00:00",
        }
        with patch("cli.run.col_cache") as mock_cache, \
             patch("cli.run._fetch_previous_result", return_value=previous_result), \
             patch("cli.run._execute_tool", return_value=({"total_files": 10, "results": {}}, None)), \
             patch("cli.run._upload_result_async", new_callable=AsyncMock, return_value=mock_upload_success):
            mock_cache.load.return_value = local_collection_cache
            result = runner.invoke(run, ["col_local123", "--tool", "photostats"])
        assert result.exit_code == 0
        assert "Result uploaded successfully" in result.output


# ============================================================================
# Tool Validation Tests
# ============================================================================


class TestToolValidation:
    """Tests for tool option validation."""

    def test_invalid_tool_rejected(self, runner, mock_config):
        result = runner.invoke(run, ["col_local123", "--tool", "invalid_tool"])
        assert result.exit_code != 0
        assert "Invalid value" in result.output or "invalid choice" in result.output.lower()

    def test_tool_is_required(self, runner, mock_config):
        result = runner.invoke(run, ["col_local123"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()


# ============================================================================
# Execution Error Tests
# ============================================================================


class TestExecutionErrors:
    """Tests for analysis execution errors."""

    def test_path_not_found(self, runner, mock_config, local_collection_cache):
        with patch("cli.run.col_cache") as mock_cache, \
             patch("cli.run._prepare_analysis", side_effect=FileNotFoundError("Path does not exist")):
            mock_cache.load.return_value = local_collection_cache
            result = runner.invoke(run, ["col_local123", "--tool", "photostats"])
        assert result.exit_code == 1
        assert "Path does not exist" in result.output

    def test_analysis_failure(
        self, runner, mock_config, local_collection_cache,
        mock_prepare_analysis, mock_fetch_previous_result_none,
    ):
        with patch("cli.run.col_cache") as mock_cache, \
             patch("cli.run._execute_tool", side_effect=RuntimeError("Tool crashed")):
            mock_cache.load.return_value = local_collection_cache
            result = runner.invoke(run, ["col_local123", "--tool", "photostats"])
        assert result.exit_code == 1
        assert "Analysis failed" in result.output


# ============================================================================
# Output Tests
# ============================================================================


class TestOutputOption:
    """Tests for --output option."""

    def test_output_saves_report(
        self, runner, mock_config, local_collection_cache, tmp_path,
        mock_upload_success, mock_prepare_analysis, mock_fetch_previous_result_none,
    ):
        report_path = str(tmp_path / "report.html")
        report_html = "<html><body>Report</body></html>"

        with patch("cli.run.col_cache") as mock_cache, \
             patch("cli.run._execute_tool", return_value=({"total_files": 10, "results": {}}, report_html)), \
             patch("cli.run._upload_result_async", new_callable=AsyncMock, return_value=mock_upload_success):
            mock_cache.load.return_value = local_collection_cache
            result = runner.invoke(run, ["col_local123", "--tool", "photostats", "--output", report_path])
        assert result.exit_code == 0
        assert Path(report_path).exists()
        assert "Report saved" in result.output
