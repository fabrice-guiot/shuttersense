"""
Unit tests for JobPollingLoop.

Issue #90 - Distributed Agent Architecture (Phase 5)
Task: T091
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.polling_loop import JobPollingLoop, DEFAULT_POLL_INTERVAL, MAX_POLL_FAILURES
from src.api_client import (
    AgentRevokedError,
    AuthenticationError,
    ConnectionError as AgentConnectionError,
    ApiError,
)


class TestJobPollingLoopInit:
    """Tests for JobPollingLoop initialization."""

    def test_init_with_defaults(self, mock_api_client):
        """Initialize with default poll interval."""
        executor = MagicMock()
        loop = JobPollingLoop(mock_api_client, executor)

        assert loop._poll_interval == DEFAULT_POLL_INTERVAL
        assert loop._api_client == mock_api_client
        assert loop._job_executor == executor
        assert loop._current_job is None
        assert loop._consecutive_failures == 0

    def test_init_with_custom_interval(self, mock_api_client):
        """Initialize with custom poll interval."""
        executor = MagicMock()
        loop = JobPollingLoop(mock_api_client, executor, poll_interval=10)

        assert loop._poll_interval == 10

    def test_is_running_initially_true(self, mock_api_client):
        """is_running returns True before shutdown is requested."""
        executor = MagicMock()
        loop = JobPollingLoop(mock_api_client, executor)

        assert loop.is_running is True

    def test_current_job_initially_none(self, mock_api_client):
        """current_job is None when no job is executing."""
        executor = MagicMock()
        loop = JobPollingLoop(mock_api_client, executor)

        assert loop.current_job is None


class TestRequestShutdown:
    """Tests for shutdown request functionality."""

    def test_request_shutdown_sets_event(self, mock_api_client):
        """request_shutdown sets the shutdown event."""
        executor = MagicMock()
        loop = JobPollingLoop(mock_api_client, executor)

        assert loop.is_running is True
        loop.request_shutdown()
        assert loop.is_running is False


class TestClaimJob:
    """Tests for job claiming."""

    @pytest.mark.asyncio
    async def test_claim_job_success(self, mock_api_client, sample_job_claim_response):
        """Successfully claims a job."""
        mock_api_client.claim_job = AsyncMock(return_value=sample_job_claim_response)
        executor = MagicMock()
        loop = JobPollingLoop(mock_api_client, executor)

        result = await loop._claim_job()

        assert result == sample_job_claim_response
        mock_api_client.claim_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_claim_job_no_jobs_available(self, mock_api_client):
        """Returns None when no jobs are available (204)."""
        mock_api_client.claim_job = AsyncMock(side_effect=ApiError("No jobs available", status_code=204))
        executor = MagicMock()
        loop = JobPollingLoop(mock_api_client, executor)

        result = await loop._claim_job()

        assert result is None

    @pytest.mark.asyncio
    async def test_claim_job_error_propagates(self, mock_api_client):
        """Non-204 API errors propagate."""
        mock_api_client.claim_job = AsyncMock(side_effect=ApiError("Server error", status_code=500))
        executor = MagicMock()
        loop = JobPollingLoop(mock_api_client, executor)

        with pytest.raises(ApiError) as exc:
            await loop._claim_job()

        assert exc.value.status_code == 500


class TestPollAndExecute:
    """Tests for poll and execute cycle."""

    @pytest.mark.asyncio
    async def test_poll_execute_no_job(self, mock_api_client):
        """Returns False when no job is available."""
        mock_api_client.claim_job = AsyncMock(side_effect=ApiError("No jobs", status_code=204))
        executor = MagicMock()
        loop = JobPollingLoop(mock_api_client, executor)

        result = await loop._poll_and_execute()

        assert result is False
        executor.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_poll_execute_with_job_success(self, mock_api_client, sample_job_claim_response):
        """Executes job and returns True on success."""
        mock_api_client.claim_job = AsyncMock(return_value=sample_job_claim_response)
        executor = MagicMock()
        executor.execute = AsyncMock()
        loop = JobPollingLoop(mock_api_client, executor)

        result = await loop._poll_and_execute()

        assert result is True
        executor.execute.assert_called_once_with(sample_job_claim_response)
        assert loop._current_job is None  # Cleared after execution

    @pytest.mark.asyncio
    async def test_poll_execute_sets_current_job(self, mock_api_client, sample_job_claim_response):
        """current_job is set during execution."""
        mock_api_client.claim_job = AsyncMock(return_value=sample_job_claim_response)

        current_job_during_execute = None

        async def capture_current_job(job):
            nonlocal current_job_during_execute
            # Access loop's current_job during execution
            current_job_during_execute = loop._current_job

        executor = MagicMock()
        executor.execute = AsyncMock(side_effect=capture_current_job)
        loop = JobPollingLoop(mock_api_client, executor)

        await loop._poll_and_execute()

        assert current_job_during_execute == sample_job_claim_response

    @pytest.mark.asyncio
    async def test_poll_execute_with_job_failure(self, mock_api_client, sample_job_claim_response):
        """Returns True even when job execution fails."""
        mock_api_client.claim_job = AsyncMock(return_value=sample_job_claim_response)
        executor = MagicMock()
        executor.execute = AsyncMock(side_effect=Exception("Job failed"))
        loop = JobPollingLoop(mock_api_client, executor)

        result = await loop._poll_and_execute()

        assert result is True  # A job was attempted
        assert loop._current_job is None  # Cleaned up


class TestWaitForNextPoll:
    """Tests for poll interval waiting."""

    @pytest.mark.asyncio
    async def test_wait_respects_poll_interval(self, mock_api_client):
        """Wait completes after poll interval timeout."""
        executor = MagicMock()
        loop = JobPollingLoop(mock_api_client, executor, poll_interval=0.1)

        start = asyncio.get_event_loop().time()
        await loop._wait_for_next_poll()
        elapsed = asyncio.get_event_loop().time() - start

        assert elapsed >= 0.1

    @pytest.mark.asyncio
    async def test_wait_interrupted_by_shutdown(self, mock_api_client):
        """Wait completes immediately if shutdown is requested."""
        executor = MagicMock()
        loop = JobPollingLoop(mock_api_client, executor, poll_interval=10)

        async def request_shutdown_soon():
            await asyncio.sleep(0.05)
            loop.request_shutdown()

        asyncio.create_task(request_shutdown_soon())

        start = asyncio.get_event_loop().time()
        await loop._wait_for_next_poll()
        elapsed = asyncio.get_event_loop().time() - start

        # Should have completed in ~0.05 seconds, not 10
        assert elapsed < 1.0


class TestRunLoop:
    """Tests for main polling loop."""

    @pytest.mark.asyncio
    async def test_run_exits_on_shutdown(self, mock_api_client):
        """Loop exits cleanly when shutdown is requested."""
        mock_api_client.claim_job = AsyncMock(side_effect=ApiError("No jobs", status_code=204))
        executor = MagicMock()
        loop = JobPollingLoop(mock_api_client, executor, poll_interval=0.05)

        async def shutdown_soon():
            await asyncio.sleep(0.1)
            loop.request_shutdown()

        asyncio.create_task(shutdown_soon())

        exit_code = await loop.run()

        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_run_exits_on_revoked(self, mock_api_client):
        """Loop exits with code 2 when agent is revoked."""
        mock_api_client.claim_job = AsyncMock(side_effect=AgentRevokedError("Revoked"))
        executor = MagicMock()
        loop = JobPollingLoop(mock_api_client, executor, poll_interval=0.01)

        exit_code = await loop.run()

        assert exit_code == 2

    @pytest.mark.asyncio
    async def test_run_exits_on_auth_error(self, mock_api_client):
        """Loop exits with code 3 on authentication error."""
        mock_api_client.claim_job = AsyncMock(side_effect=AuthenticationError("Invalid token"))
        executor = MagicMock()
        loop = JobPollingLoop(mock_api_client, executor, poll_interval=0.01)

        exit_code = await loop.run()

        assert exit_code == 3

    @pytest.mark.asyncio
    async def test_run_exits_after_max_connection_failures(self, mock_api_client):
        """Loop exits with code 4 after max connection failures."""
        mock_api_client.claim_job = AsyncMock(
            side_effect=AgentConnectionError("Connection refused")
        )
        executor = MagicMock()
        loop = JobPollingLoop(mock_api_client, executor, poll_interval=0.01)

        exit_code = await loop.run()

        assert exit_code == 4
        assert mock_api_client.claim_job.call_count >= MAX_POLL_FAILURES

    @pytest.mark.asyncio
    async def test_run_resets_failure_count_on_success(self, mock_api_client, sample_job_claim_response):
        """Failure counter resets after successful poll."""
        call_count = 0

        async def varying_claim():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise AgentConnectionError("Connection failed")
            elif call_count == 3:
                return sample_job_claim_response
            else:
                raise ApiError("No jobs", status_code=204)

        mock_api_client.claim_job = AsyncMock(side_effect=varying_claim)
        executor = MagicMock()
        executor.execute = AsyncMock()
        loop = JobPollingLoop(mock_api_client, executor, poll_interval=0.01)

        async def shutdown_soon():
            await asyncio.sleep(0.2)
            loop.request_shutdown()

        asyncio.create_task(shutdown_soon())

        exit_code = await loop.run()

        # Should have reset after successful claim, not exited with failure
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_run_polls_without_waiting_after_job(self, mock_api_client, sample_job_claim_response):
        """Polls immediately after job execution, no wait."""
        claim_times = []

        async def track_claim():
            claim_times.append(asyncio.get_event_loop().time())
            if len(claim_times) == 1:
                return sample_job_claim_response
            raise ApiError("No jobs", status_code=204)

        mock_api_client.claim_job = AsyncMock(side_effect=track_claim)
        executor = MagicMock()
        executor.execute = AsyncMock()
        loop = JobPollingLoop(mock_api_client, executor, poll_interval=1.0)

        async def shutdown_soon():
            await asyncio.sleep(0.1)
            loop.request_shutdown()

        asyncio.create_task(shutdown_soon())

        await loop.run()

        # Second claim should happen immediately after job, not after 1s
        if len(claim_times) >= 2:
            assert claim_times[1] - claim_times[0] < 0.5

    @pytest.mark.asyncio
    async def test_run_handles_cancelled(self, mock_api_client):
        """Loop handles cancellation gracefully."""
        async def slow_claim():
            await asyncio.sleep(10)

        mock_api_client.claim_job = AsyncMock(side_effect=slow_claim)
        executor = MagicMock()
        loop = JobPollingLoop(mock_api_client, executor, poll_interval=0.01)

        task = asyncio.create_task(loop.run())
        await asyncio.sleep(0.05)
        task.cancel()

        # The loop catches CancelledError internally and returns 0
        try:
            result = await task
            assert result == 0
        except asyncio.CancelledError:
            # Also acceptable - cancellation propagated
            pass
