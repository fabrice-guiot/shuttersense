"""
Unit tests for ProgressReporter.

Issue #90 - Distributed Agent Architecture (Phase 5)
Task: T093
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from src.progress_reporter import ProgressReporter, MIN_REPORT_INTERVAL


class TestProgressReporterInit:
    """Tests for ProgressReporter initialization."""

    def test_init_stores_params(self, mock_api_client):
        """API client and job GUID are stored."""
        reporter = ProgressReporter(mock_api_client, "job_test123")

        assert reporter._api_client == mock_api_client
        assert reporter._job_guid == "job_test123"
        assert reporter._last_report_time == 0
        assert reporter._pending_report is None
        assert reporter._closed is False


class TestReport:
    """Tests for progress reporting."""

    @pytest.mark.asyncio
    async def test_report_sends_to_api(self, mock_api_client):
        """Report sends progress to API."""
        reporter = ProgressReporter(mock_api_client, "job_test123")

        await reporter.report(
            stage="scanning",
            percentage=50,
            files_scanned=500,
            total_files=1000,
            message="Scanning files...",
        )

        mock_api_client.update_job_progress.assert_called_once()
        call_kwargs = mock_api_client.update_job_progress.call_args.kwargs
        assert call_kwargs["job_guid"] == "job_test123"
        assert call_kwargs["stage"] == "scanning"
        assert call_kwargs["percentage"] == 50

    @pytest.mark.asyncio
    async def test_report_omits_none_values(self, mock_api_client):
        """Report omits None values."""
        reporter = ProgressReporter(mock_api_client, "job_test123")

        await reporter.report(
            stage="starting",
        )

        call_kwargs = mock_api_client.update_job_progress.call_args.kwargs
        assert "percentage" not in call_kwargs
        assert "files_scanned" not in call_kwargs
        assert "total_files" not in call_kwargs

    @pytest.mark.asyncio
    async def test_report_closed_does_nothing(self, mock_api_client):
        """Report does nothing when closed."""
        reporter = ProgressReporter(mock_api_client, "job_test123")
        reporter._closed = True

        await reporter.report(stage="scanning")

        mock_api_client.update_job_progress.assert_not_called()


class TestRateLimiting:
    """Tests for rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_first_report_sends_immediately(self, mock_api_client):
        """First report is sent immediately."""
        reporter = ProgressReporter(mock_api_client, "job_test123")

        start = time.monotonic()
        await reporter.report(stage="starting")
        elapsed = time.monotonic() - start

        # Should complete quickly (no delay)
        assert elapsed < 0.1
        mock_api_client.update_job_progress.assert_called_once()

    @pytest.mark.asyncio
    async def test_rapid_reports_are_rate_limited(self, mock_api_client):
        """Rapid reports are queued and rate-limited."""
        reporter = ProgressReporter(mock_api_client, "job_test123")

        # First report
        await reporter.report(stage="starting", percentage=0)

        # Reset mock to track subsequent calls
        mock_api_client.update_job_progress.reset_mock()

        # Immediate second report should be queued
        await reporter.report(stage="scanning", percentage=10)

        # The queued report should be scheduled for later
        assert reporter._pending_report is not None
        assert reporter._pending_report["stage"] == "scanning"

    @pytest.mark.asyncio
    async def test_queued_report_sends_after_delay(self, mock_api_client):
        """Queued reports are sent after rate limit delay."""
        reporter = ProgressReporter(mock_api_client, "job_test123")

        # First report
        await reporter.report(stage="starting")
        mock_api_client.update_job_progress.reset_mock()

        # Queued report
        await reporter.report(stage="scanning")

        # Wait for delayed send
        await asyncio.sleep(MIN_REPORT_INTERVAL + 0.1)

        # Queued report should have been sent
        mock_api_client.update_job_progress.assert_called()
        assert reporter._pending_report is None

    @pytest.mark.asyncio
    async def test_latest_report_replaces_queued(self, mock_api_client):
        """Latest report replaces any queued report."""
        reporter = ProgressReporter(mock_api_client, "job_test123")

        # First report
        await reporter.report(stage="starting")
        mock_api_client.update_job_progress.reset_mock()

        # Multiple rapid reports
        await reporter.report(stage="scanning", percentage=10)
        await reporter.report(stage="scanning", percentage=20)
        await reporter.report(stage="scanning", percentage=30)

        # Only the latest should be pending
        assert reporter._pending_report["percentage"] == 30

    @pytest.mark.asyncio
    async def test_respects_min_interval_between_sends(self, mock_api_client):
        """Reports after min interval are sent immediately."""
        reporter = ProgressReporter(mock_api_client, "job_test123")

        # First report
        await reporter.report(stage="starting")

        # Wait longer than min interval
        await asyncio.sleep(MIN_REPORT_INTERVAL + 0.1)

        mock_api_client.update_job_progress.reset_mock()

        # Second report should be immediate
        await reporter.report(stage="scanning")

        mock_api_client.update_job_progress.assert_called_once()
        # No pending report
        assert reporter._pending_report is None


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_api_error_does_not_raise(self, mock_api_client):
        """API errors during report don't raise exceptions."""
        mock_api_client.update_job_progress = AsyncMock(
            side_effect=Exception("API error")
        )
        reporter = ProgressReporter(mock_api_client, "job_test123")

        # Should not raise
        await reporter.report(stage="scanning")

        # Verify attempt was made
        mock_api_client.update_job_progress.assert_called_once()


class TestClose:
    """Tests for closing the reporter."""

    @pytest.mark.asyncio
    async def test_close_sets_closed_flag(self, mock_api_client):
        """Close sets the closed flag."""
        reporter = ProgressReporter(mock_api_client, "job_test123")

        await reporter.close()

        assert reporter._closed is True

    @pytest.mark.asyncio
    async def test_close_sends_pending_report(self, mock_api_client):
        """Close sends any pending report."""
        reporter = ProgressReporter(mock_api_client, "job_test123")

        # Create a pending report
        await reporter.report(stage="starting")
        mock_api_client.update_job_progress.reset_mock()

        await reporter.report(stage="scanning", percentage=50)

        # Close should send the pending report
        await reporter.close()

        # Pending report should have been sent
        mock_api_client.update_job_progress.assert_called()
        assert reporter._pending_report is None

    @pytest.mark.asyncio
    async def test_close_cancels_scheduled_task(self, mock_api_client):
        """Close cancels any scheduled send task."""
        reporter = ProgressReporter(mock_api_client, "job_test123")

        # Create a pending report (which schedules a task)
        await reporter.report(stage="starting")
        await reporter.report(stage="scanning")

        assert reporter._report_task is not None

        # Close should cancel the task
        await reporter.close()

        # Task should be done (cancelled)
        assert reporter._report_task.done()

    @pytest.mark.asyncio
    async def test_close_handles_error_in_final_send(self, mock_api_client):
        """Close handles errors when sending final report."""
        reporter = ProgressReporter(mock_api_client, "job_test123")

        # Create a pending report
        await reporter.report(stage="starting")
        await reporter.report(stage="scanning")

        # Make API fail
        mock_api_client.update_job_progress = AsyncMock(
            side_effect=Exception("API error")
        )

        # Close should not raise
        await reporter.close()

        assert reporter._closed is True
        assert reporter._pending_report is None


class TestProgressDataBuilding:
    """Tests for progress data structure building."""

    @pytest.mark.asyncio
    async def test_includes_all_fields(self, mock_api_client):
        """All provided fields are included in progress data."""
        reporter = ProgressReporter(mock_api_client, "job_test123")

        await reporter.report(
            stage="processing",
            percentage=75,
            files_scanned=750,
            total_files=1000,
            current_file="IMG_1234.dng",
            message="Processing files...",
        )

        call_kwargs = mock_api_client.update_job_progress.call_args.kwargs
        assert call_kwargs["stage"] == "processing"
        assert call_kwargs["percentage"] == 75
        assert call_kwargs["files_scanned"] == 750
        assert call_kwargs["total_files"] == 1000
        assert call_kwargs["current_file"] == "IMG_1234.dng"
        assert call_kwargs["message"] == "Processing files..."

    @pytest.mark.asyncio
    async def test_minimal_report(self, mock_api_client):
        """Minimal report with just stage."""
        reporter = ProgressReporter(mock_api_client, "job_test123")

        await reporter.report(stage="done")

        call_kwargs = mock_api_client.update_job_progress.call_args.kwargs
        assert call_kwargs["stage"] == "done"
        assert len([k for k in call_kwargs if k != "job_guid" and k != "stage"]) == 0
