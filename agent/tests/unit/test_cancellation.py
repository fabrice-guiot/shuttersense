"""
Unit tests for agent cancellation handling.

Tests command parsing, cancel current job, and cancel non-current job scenarios.

Issue #90 - Distributed Agent Architecture (Phase 10)
Task: T158
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.polling_loop import JobPollingLoop
from src.job_executor import JobExecutor, JobCancelledException
from src.main import AgentRunner


class TestCommandParsing:
    """Tests for pending command parsing in AgentRunner."""

    @pytest.mark.asyncio
    async def test_parse_cancel_job_command(self):
        """Test parsing cancel_job:{guid} command."""
        runner = object.__new__(AgentRunner)
        runner.logger = MagicMock()
        runner._handle_cancel_job = AsyncMock()

        command = "cancel_job:job_01hgw2bbg0000000000000001"
        await AgentRunner._process_command(runner, command)

        runner._handle_cancel_job.assert_called_once_with("job_01hgw2bbg0000000000000001")

    @pytest.mark.asyncio
    async def test_parse_unknown_command(self):
        """Test that unknown commands log a warning."""
        runner = object.__new__(AgentRunner)
        runner.logger = MagicMock()
        runner._handle_cancel_job = AsyncMock()

        command = "unknown_command:data"
        await AgentRunner._process_command(runner, command)

        # Should log a warning, not call _handle_cancel_job
        runner._handle_cancel_job.assert_not_called()
        runner.logger.warning.assert_called_once()
        assert "Unknown command" in runner.logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_parse_cancel_job_with_colon_in_guid(self):
        """Test parsing cancel_job command when guid contains colons (edge case)."""
        runner = object.__new__(AgentRunner)
        runner.logger = MagicMock()
        runner._handle_cancel_job = AsyncMock()

        # This tests the split(":", 1) behavior
        command = "cancel_job:job_01hgw2bbg:extra:parts"
        await AgentRunner._process_command(runner, command)

        # Should extract everything after the first colon
        runner._handle_cancel_job.assert_called_once_with("job_01hgw2bbg:extra:parts")


class TestCancelCurrentJob:
    """Tests for cancelling the currently executing job."""

    @pytest.mark.asyncio
    async def test_cancel_current_job_calls_polling_loop(self):
        """Test that cancelling current job calls polling_loop.request_job_cancellation()."""
        runner = object.__new__(AgentRunner)
        runner.logger = MagicMock()

        # Mock polling loop with current job
        mock_polling_loop = MagicMock()
        mock_polling_loop.current_job = {"guid": "job_01hgw2bbg0000000000000001"}
        mock_polling_loop.request_job_cancellation = MagicMock()
        runner._polling_loop = mock_polling_loop

        job_guid = "job_01hgw2bbg0000000000000001"
        await AgentRunner._handle_cancel_job(runner, job_guid)

        mock_polling_loop.request_job_cancellation.assert_called_once()
        runner.logger.info.assert_called()

    @pytest.mark.asyncio
    async def test_cancel_current_job_logs_info(self):
        """Test that cancellation of current job logs at info level."""
        runner = object.__new__(AgentRunner)
        runner.logger = MagicMock()

        mock_polling_loop = MagicMock()
        mock_polling_loop.current_job = {"guid": "job_test123"}
        mock_polling_loop.request_job_cancellation = MagicMock()
        runner._polling_loop = mock_polling_loop

        await AgentRunner._handle_cancel_job(runner, "job_test123")

        # Verify info log was called with the job guid
        info_calls = [str(call) for call in runner.logger.info.call_args_list]
        assert any("job_test123" in call for call in info_calls)


class TestCancelNonCurrentJob:
    """Tests for ignoring cancel commands for non-current jobs."""

    @pytest.mark.asyncio
    async def test_cancel_non_current_job_ignored(self):
        """Test that cancelling a non-current job is ignored."""
        runner = object.__new__(AgentRunner)
        runner.logger = MagicMock()

        # Mock polling loop with different current job
        mock_polling_loop = MagicMock()
        mock_polling_loop.current_job = {"guid": "job_other_job_running"}
        mock_polling_loop.request_job_cancellation = MagicMock()
        runner._polling_loop = mock_polling_loop

        # Try to cancel a different job
        await AgentRunner._handle_cancel_job(runner, "job_01hgw2bbg0000000000000001")

        # Should NOT call request_job_cancellation
        mock_polling_loop.request_job_cancellation.assert_not_called()
        # Should log at debug level
        runner.logger.debug.assert_called()

    @pytest.mark.asyncio
    async def test_cancel_when_no_job_running(self):
        """Test that cancel command when no job is running is ignored."""
        runner = object.__new__(AgentRunner)
        runner.logger = MagicMock()

        # Mock polling loop with no current job
        mock_polling_loop = MagicMock()
        mock_polling_loop.current_job = None
        mock_polling_loop.request_job_cancellation = MagicMock()
        runner._polling_loop = mock_polling_loop

        await AgentRunner._handle_cancel_job(runner, "job_01hgw2bbg0000000000000001")

        # Should NOT call request_job_cancellation
        mock_polling_loop.request_job_cancellation.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_without_polling_loop(self):
        """Test that cancel command without polling loop logs warning."""
        runner = object.__new__(AgentRunner)
        runner.logger = MagicMock()
        # No _polling_loop attribute

        await AgentRunner._handle_cancel_job(runner, "job_01hgw2bbg0000000000000001")

        # Should log a warning
        runner.logger.warning.assert_called()
        assert "polling loop not initialized" in runner.logger.warning.call_args[0][0]


class TestPollingLoopCancellation:
    """Tests for JobPollingLoop cancellation methods."""

    def test_request_job_cancellation_with_current_job(self, mock_api_client):
        """Test request_job_cancellation sets flag and notifies executor."""
        executor = MagicMock()
        executor.request_cancellation = MagicMock()
        loop = JobPollingLoop(mock_api_client, executor)

        # Simulate a current job
        loop._current_job = {"guid": "job_test123"}

        loop.request_job_cancellation()

        assert loop._cancellation_requested is True
        executor.request_cancellation.assert_called_once()

    def test_request_job_cancellation_without_current_job(self, mock_api_client):
        """Test request_job_cancellation with no current job does nothing."""
        executor = MagicMock()
        executor.request_cancellation = MagicMock()
        loop = JobPollingLoop(mock_api_client, executor)

        # No current job
        loop._current_job = None

        loop.request_job_cancellation()

        # Flag should NOT be set when no job
        assert loop._cancellation_requested is False
        executor.request_cancellation.assert_not_called()

    def test_clear_cancellation_resets_flag(self, mock_api_client):
        """Test clear_cancellation resets the flag."""
        executor = MagicMock()
        loop = JobPollingLoop(mock_api_client, executor)

        loop._cancellation_requested = True
        loop.clear_cancellation()

        assert loop._cancellation_requested is False

    @pytest.mark.asyncio
    async def test_poll_and_execute_clears_cancellation_on_completion(
        self, mock_api_client, sample_job_claim_response
    ):
        """Test cancellation flag is cleared after job execution."""
        mock_api_client.claim_job = AsyncMock(return_value=sample_job_claim_response)

        executor = MagicMock()
        executor.execute = AsyncMock()
        loop = JobPollingLoop(mock_api_client, executor)

        # Set cancellation before job
        loop._cancellation_requested = True

        await loop._poll_and_execute()

        # Should be cleared after job completes
        assert loop._cancellation_requested is False


class TestJobExecutorCancellation:
    """Tests for JobExecutor cancellation methods."""

    def test_request_cancellation_sets_flag(self, mock_api_client):
        """Test request_cancellation sets the flag."""
        executor = JobExecutor(mock_api_client)

        assert executor._cancel_requested is False
        executor.request_cancellation()
        assert executor._cancel_requested is True

    def test_is_cancellation_requested_returns_flag(self, mock_api_client):
        """Test is_cancellation_requested returns the flag value."""
        executor = JobExecutor(mock_api_client)

        assert executor.is_cancellation_requested() is False
        executor._cancel_requested = True
        assert executor.is_cancellation_requested() is True

    def test_check_cancellation_raises_when_requested(self, mock_api_client):
        """Test _check_cancellation raises JobCancelledException when flag is set."""
        executor = JobExecutor(mock_api_client)
        executor._cancel_requested = True
        executor._current_job_guid = "job_test123"

        with pytest.raises(JobCancelledException) as exc_info:
            executor._check_cancellation()

        assert "job_test123" in str(exc_info.value)
        assert "cancelled" in str(exc_info.value).lower()

    def test_check_cancellation_does_nothing_when_not_requested(self, mock_api_client):
        """Test _check_cancellation does nothing when flag is not set."""
        executor = JobExecutor(mock_api_client)
        executor._cancel_requested = False

        # Should not raise
        executor._check_cancellation()

    @pytest.mark.asyncio
    async def test_execute_resets_cancellation_flag(
        self, mock_api_client, sample_job_claim_response
    ):
        """Test execute resets cancellation flag at start of new job."""
        mock_api_client.get_job_config = AsyncMock(return_value={
            "config": {
                "photo_extensions": [".dng"],
                "metadata_extensions": [".xmp"],
                "camera_mappings": {},
                "processing_methods": {},
                "require_sidecar": [],
            },
        })

        executor = JobExecutor(mock_api_client)
        executor._cancel_requested = True  # Set from previous job

        with patch.object(executor, '_execute_tool', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = MagicMock(
                success=True,
                results={"total_files": 0},
                files_scanned=0,
                issues_found=0,
                report_html=None,
            )

            await executor.execute(sample_job_claim_response)

        # Flag should have been reset
        assert executor._cancel_requested is False


class TestJobCancelledException:
    """Tests for JobCancelledException."""

    def test_exception_message(self):
        """Test JobCancelledException has proper message."""
        exc = JobCancelledException("Job job_test123 was cancelled")

        assert "job_test123" in str(exc)
        assert "cancelled" in str(exc).lower()

    def test_exception_is_caught_properly(self):
        """Test that JobCancelledException can be caught separately."""
        def raise_exception():
            raise JobCancelledException("Test")

        # Should be catchable as JobCancelledException
        try:
            raise_exception()
        except JobCancelledException as e:
            assert "Test" in str(e)

        # Should also be catchable as Exception
        try:
            raise_exception()
        except Exception as e:
            assert isinstance(e, JobCancelledException)
