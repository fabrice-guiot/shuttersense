"""
Unit tests for the test CLI command.

Tests path validation, check-only mode, tool filter, output flag,
and error messages.

Issue #108 - Remove CLI Direct Usage
Task: T012
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from cli.test import test
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
    """Sample FileInfo list for testing."""
    return [
        FileInfo(path="photo1.dng", size=10000),
        FileInfo(path="photo2.dng", size=15000),
        FileInfo(path="photo3.cr3", size=20000),
        FileInfo(path="photo1.xmp", size=500),
        FileInfo(path="readme.txt", size=100),
    ]


@pytest.fixture
def mock_adapter(sample_files):
    """Mock LocalAdapter that returns sample files."""
    with patch("cli.test.LocalAdapter") as mock_cls:
        adapter = MagicMock()
        adapter.list_files_with_metadata.return_value = sample_files
        mock_cls.return_value = adapter
        yield adapter


@pytest.fixture
def mock_save():
    """Mock the cache save function."""
    with patch("cli.test.save") as mock:
        yield mock


@pytest.fixture
def mock_config():
    """Mock AgentConfig."""
    with patch("cli.test.AgentConfig") as mock_cls:
        config = MagicMock()
        config.agent_guid = "agt_test"
        mock_cls.return_value = config
        yield config


# ============================================================================
# Accessibility Tests
# ============================================================================


class TestAccessibility:
    """Tests for path accessibility checking."""

    def test_accessible_path(self, runner, mock_adapter, mock_save, mock_config):
        result = runner.invoke(test, ["/tmp/photos", "--check-only"])
        assert result.exit_code == 0
        assert "OK" in result.output
        assert "readable" in result.output
        assert "5 files found" in result.output

    def test_nonexistent_path(self, runner, mock_save, mock_config):
        with patch("cli.test.LocalAdapter") as mock_cls:
            adapter = MagicMock()
            adapter.list_files_with_metadata.side_effect = FileNotFoundError(
                "Path does not exist"
            )
            mock_cls.return_value = adapter
            result = runner.invoke(test, ["/nonexistent/path"])
        assert result.exit_code == 1
        assert "FAIL" in result.output
        assert "does not exist" in result.output

    def test_permission_denied(self, runner, mock_save, mock_config):
        with patch("cli.test.LocalAdapter") as mock_cls:
            adapter = MagicMock()
            adapter.list_files_with_metadata.side_effect = PermissionError(
                "Permission denied"
            )
            mock_cls.return_value = adapter
            result = runner.invoke(test, ["/protected/path"])
        assert result.exit_code == 1
        assert "FAIL" in result.output
        assert "Permission denied" in result.output


# ============================================================================
# Check-Only Mode Tests
# ============================================================================


class TestCheckOnlyMode:
    """Tests for --check-only flag."""

    def test_check_only_skips_analysis(self, runner, mock_adapter, mock_save, mock_config):
        result = runner.invoke(test, ["/tmp/photos", "--check-only"])
        assert result.exit_code == 0
        assert "Running" not in result.output
        assert "Test Summary:" in result.output

    def test_check_only_shows_file_counts(self, runner, mock_adapter, mock_save, mock_config):
        result = runner.invoke(test, ["/tmp/photos", "--check-only"])
        assert result.exit_code == 0
        assert "photos" in result.output
        assert "sidecars" in result.output

    def test_check_only_caches_result(self, runner, mock_adapter, mock_save, mock_config):
        runner.invoke(test, ["/tmp/photos", "--check-only"])
        mock_save.assert_called_once()


# ============================================================================
# Tool Filter Tests
# ============================================================================


class TestToolFilter:
    """Tests for --tool option."""

    def test_single_tool_photostats(self, runner, mock_adapter, mock_save, mock_config):
        with patch("cli.test._run_photostats", return_value={"stats": {}, "pairing": {}}) as mock_run:
            result = runner.invoke(test, ["/tmp/photos", "--tool", "photostats"])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        assert "Running photostats" in result.output
        # Should NOT run other tools
        assert "Running photo_pairing" not in result.output

    def test_single_tool_photo_pairing(self, runner, mock_adapter, mock_save, mock_config):
        with patch("cli.test._run_photo_pairing", return_value={"imagegroups": {}, "invalid_files": []}) as mock_run:
            result = runner.invoke(test, ["/tmp/photos", "--tool", "photo_pairing"])
        assert result.exit_code == 0
        mock_run.assert_called_once()

    def test_invalid_tool_rejected(self, runner):
        result = runner.invoke(test, ["/tmp/photos", "--tool", "invalid_tool"])
        assert result.exit_code != 0
        assert "Invalid value" in result.output or "invalid_tool" in result.output

    def test_all_tools_default(self, runner, mock_adapter, mock_save, mock_config):
        with patch("cli.test._run_photostats", return_value={"stats": {}, "pairing": {}}), \
             patch("cli.test._run_photo_pairing", return_value={"imagegroups": {}, "invalid_files": []}), \
             patch("cli.test._run_pipeline_validation", return_value={"status_counts": {}}):
            result = runner.invoke(test, ["/tmp/photos"])
        assert result.exit_code == 0
        assert "Running photo_pairing" in result.output
        assert "Running photostats" in result.output
        assert "Running pipeline_validation" in result.output


# ============================================================================
# Output Flag Tests
# ============================================================================


class TestOutputFlag:
    """Tests for --output option."""

    def test_output_flag_accepted(self, runner, mock_adapter, mock_save, mock_config):
        with patch("cli.test._run_photostats", return_value={"stats": {}, "pairing": {}}), \
             patch("cli.test._run_photo_pairing", return_value={"imagegroups": {}, "invalid_files": []}), \
             patch("cli.test._run_pipeline_validation", return_value={"status_counts": {}}):
            result = runner.invoke(test, ["/tmp/photos", "--output", "report.html"])
        assert result.exit_code == 0
        assert "report.html" in result.output


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Tests for analysis error handling."""

    def test_tool_failure_continues_others(self, runner, mock_adapter, mock_save, mock_config):
        """If one tool fails, others should still run."""
        with patch("cli.test._run_photostats", side_effect=Exception("photostats broke")), \
             patch("cli.test._run_photo_pairing", return_value={"imagegroups": {}, "invalid_files": []}), \
             patch("cli.test._run_pipeline_validation", return_value={"status_counts": {}}):
            result = runner.invoke(test, ["/tmp/photos"])
        # Should still have run other tools
        assert "Running photo_pairing" in result.output
        assert "photostats broke" in result.output
        # Exit code 2 for analysis failure
        assert result.exit_code == 2

    def test_tool_failure_single_tool(self, runner, mock_adapter, mock_save, mock_config):
        with patch("cli.test._run_photostats", side_effect=Exception("analysis error")):
            result = runner.invoke(test, ["/tmp/photos", "--tool", "photostats"])
        assert result.exit_code == 2
        assert "FAIL" in result.output


# ============================================================================
# Summary Output Tests
# ============================================================================


class TestSummaryOutput:
    """Tests for the test summary display."""

    def test_summary_shows_ready_yes(self, runner, mock_adapter, mock_save, mock_config):
        with patch("cli.test._run_photostats", return_value={"stats": {}, "pairing": {}}), \
             patch("cli.test._run_photo_pairing", return_value={"imagegroups": {}, "invalid_files": []}), \
             patch("cli.test._run_pipeline_validation", return_value={"status_counts": {}}):
            result = runner.invoke(test, ["/tmp/photos"])
        assert "Ready to create Collection:" in result.output
        assert "Yes" in result.output

    def test_summary_shows_issues(self, runner, mock_adapter, mock_save, mock_config):
        with patch("cli.test._run_photostats", return_value={
            "stats": {},
            "pairing": {"orphaned_images": ["a.cr3", "b.cr3"], "orphaned_xmp": []},
        }), \
             patch("cli.test._run_photo_pairing", return_value={"imagegroups": {}, "invalid_files": []}), \
             patch("cli.test._run_pipeline_validation", return_value={"status_counts": {}}):
            result = runner.invoke(test, ["/tmp/photos"])
        assert "Issues:" in result.output
        assert "2" in result.output

    def test_check_only_summary(self, runner, mock_adapter, mock_save, mock_config):
        result = runner.invoke(test, ["/tmp/photos", "--check-only"])
        assert "Test Summary:" in result.output
        assert "Files:" in result.output
        assert "Issues: None" in result.output
