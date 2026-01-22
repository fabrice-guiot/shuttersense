"""
Integration tests for job execution flow.

Tests the end-to-end flow of:
- Claiming jobs from the server
- Executing jobs with tools
- Reporting progress
- Completing/failing jobs with signed results

Issue #90 - Distributed Agent Architecture (Phase 5)
Task: T096
"""

import asyncio
import tempfile
import os
from pathlib import Path
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from base64 import b64encode
import secrets

from src.polling_loop import JobPollingLoop
from src.job_executor import JobExecutor
from src.progress_reporter import ProgressReporter
from src.result_signer import ResultSigner
from src.config_loader import ApiConfigLoader


class TestJobExecutionEndToEnd:
    """Integration tests for full job execution cycle."""

    @pytest.mark.asyncio
    async def test_claim_execute_complete_flow(self, mock_api_client, sample_job_claim_response):
        """Test complete flow: claim -> execute -> complete."""
        # Setup mock responses
        mock_api_client.claim_job = AsyncMock(return_value=sample_job_claim_response)
        mock_api_client.get_job_config = AsyncMock(return_value={
            "config": {
                "photo_extensions": [".dng", ".jpg"],
                "metadata_extensions": [".xmp"],
                "camera_mappings": {},
                "processing_methods": {},
                "require_sidecar": [],
            },
            "collection_path": sample_job_claim_response.get("collection_path"),
        })

        # Create executor
        executor = JobExecutor(mock_api_client)

        # Mock the actual tool execution to avoid running real analysis
        with patch.object(executor, '_execute_tool', new_callable=AsyncMock) as mock_tool:
            mock_tool.return_value = MagicMock(
                success=True,
                results={"total_files": 100, "issues_found": 5},
                report_html="<html>Test Report</html>",
                files_scanned=100,
                issues_found=5,
                error_message=None,
            )

            # Execute the job
            await executor.execute(sample_job_claim_response)

        # Verify complete_job was called with signed results
        mock_api_client.complete_job.assert_called_once()
        call_kwargs = mock_api_client.complete_job.call_args.kwargs

        assert call_kwargs["job_guid"] == sample_job_claim_response["guid"]
        assert call_kwargs["results"]["total_files"] == 100
        assert call_kwargs["files_scanned"] == 100
        assert call_kwargs["issues_found"] == 5
        assert "signature" in call_kwargs
        assert len(call_kwargs["signature"]) == 64  # SHA-256 hex

    @pytest.mark.asyncio
    async def test_claim_execute_fail_flow(self, mock_api_client, sample_job_claim_response):
        """Test flow when job execution fails: claim -> execute -> fail."""
        mock_api_client.claim_job = AsyncMock(return_value=sample_job_claim_response)
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

        with patch.object(executor, '_execute_tool', new_callable=AsyncMock) as mock_tool:
            mock_tool.return_value = MagicMock(
                success=False,
                results={},
                report_html=None,
                files_scanned=0,
                issues_found=0,
                error_message="Collection path not accessible",
            )

            with pytest.raises(Exception, match="Collection path not accessible"):
                await executor.execute(sample_job_claim_response)

        # Verify fail_job was called
        mock_api_client.fail_job.assert_called_once()
        call_kwargs = mock_api_client.fail_job.call_args.kwargs

        assert call_kwargs["job_guid"] == sample_job_claim_response["guid"]
        assert "Collection path not accessible" in call_kwargs["error_message"]
        assert "signature" in call_kwargs


class TestPollingLoopIntegration:
    """Integration tests for polling loop with executor."""

    @pytest.mark.asyncio
    async def test_polling_loop_claims_and_executes_job(self, mock_api_client, sample_job_claim_response):
        """Polling loop claims job and passes it to executor."""
        claim_count = 0

        async def claim_once():
            nonlocal claim_count
            claim_count += 1
            if claim_count == 1:
                return sample_job_claim_response
            from src.api_client import ApiError
            raise ApiError(204, "No jobs")

        mock_api_client.claim_job = AsyncMock(side_effect=claim_once)
        mock_api_client.get_job_config = AsyncMock(return_value={
            "config": {
                "photo_extensions": [".dng"],
                "metadata_extensions": [".xmp"],
                "camera_mappings": {},
                "processing_methods": {},
                "require_sidecar": [],
            },
        })

        # Create executor with mocked tool execution
        executor = JobExecutor(mock_api_client)
        job_executed = asyncio.Event()

        original_execute = executor.execute

        async def track_execute(job):
            # Mock the tool execution part
            with patch.object(executor, '_execute_tool', new_callable=AsyncMock) as mock_tool:
                mock_tool.return_value = MagicMock(
                    success=True,
                    results={"total_files": 10},
                    report_html="<html></html>",
                    files_scanned=10,
                    issues_found=0,
                    error_message=None,
                )
                await original_execute(job)
            job_executed.set()

        executor.execute = track_execute

        # Create polling loop
        loop = JobPollingLoop(mock_api_client, executor, poll_interval=0.05)

        # Run loop with timeout
        async def run_with_timeout():
            task = asyncio.create_task(loop.run())
            try:
                await asyncio.wait_for(job_executed.wait(), timeout=2.0)
                loop.request_shutdown()
                await task
            except asyncio.TimeoutError:
                loop.request_shutdown()
                await task
                pytest.fail("Job was not executed in time")

        await run_with_timeout()

        # Verify job was processed
        mock_api_client.complete_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_polling_loop_handles_no_jobs(self, mock_api_client):
        """Polling loop handles no jobs available gracefully."""
        from src.api_client import ApiError

        mock_api_client.claim_job = AsyncMock(side_effect=ApiError(204, "No jobs"))

        executor = MagicMock()
        loop = JobPollingLoop(mock_api_client, executor, poll_interval=0.05)

        # Run for a short time
        async def shutdown_soon():
            await asyncio.sleep(0.15)
            loop.request_shutdown()

        asyncio.create_task(shutdown_soon())
        exit_code = await loop.run()

        assert exit_code == 0
        # Executor should not have been called
        executor.execute.assert_not_called()


class TestProgressReportingIntegration:
    """Integration tests for progress reporting during execution."""

    @pytest.mark.asyncio
    async def test_progress_reported_during_execution(self, mock_api_client, sample_job_claim_response):
        """Progress updates are reported during job execution."""
        mock_api_client.get_job_config = AsyncMock(return_value={
            "config": {
                "photo_extensions": [".dng"],
                "metadata_extensions": [".xmp"],
                "camera_mappings": {},
                "processing_methods": {},
                "require_sidecar": [],
            },
        })

        progress_reports = []
        original_update = mock_api_client.update_job_progress

        async def capture_progress(*args, **kwargs):
            progress_reports.append(kwargs)
            return {"status": "ok"}

        mock_api_client.update_job_progress = AsyncMock(side_effect=capture_progress)

        executor = JobExecutor(mock_api_client)

        with patch.object(executor, '_execute_tool', new_callable=AsyncMock) as mock_tool:
            async def tool_with_progress(job, config):
                # Simulate tool reporting progress
                executor._sync_progress_callback(stage="scanning", percentage=25)
                await asyncio.sleep(0.1)
                executor._sync_progress_callback(stage="scanning", percentage=50)
                await asyncio.sleep(0.1)
                executor._sync_progress_callback(stage="processing", percentage=75)
                await asyncio.sleep(0.1)

                return MagicMock(
                    success=True,
                    results={"total_files": 100},
                    report_html="<html></html>",
                    files_scanned=100,
                    issues_found=0,
                    error_message=None,
                )

            mock_tool.side_effect = tool_with_progress
            await executor.execute(sample_job_claim_response)

        # Should have multiple progress reports
        assert len(progress_reports) >= 2  # At least starting + one from tool
        assert any(p.get("stage") == "starting" for p in progress_reports)


class TestConfigLoadingIntegration:
    """Integration tests for config loading during execution."""

    @pytest.mark.asyncio
    async def test_config_loaded_before_execution(self, mock_api_client, sample_job_claim_response):
        """Configuration is loaded before tool execution."""
        config_loaded = asyncio.Event()
        expected_config = {
            "photo_extensions": [".dng", ".cr3"],
            "metadata_extensions": [".xmp"],
            "camera_mappings": {"AB3D": [{"name": "Canon", "serial_number": "123"}]},
            "processing_methods": {"HDR": "High Dynamic Range"},
            "require_sidecar": [".cr3"],
        }

        async def mock_get_config(job_guid):
            config_loaded.set()
            return {"config": expected_config}

        mock_api_client.get_job_config = AsyncMock(side_effect=mock_get_config)

        executor = JobExecutor(mock_api_client)
        received_config = None

        with patch.object(executor, '_execute_tool', new_callable=AsyncMock) as mock_tool:
            async def capture_config(job, config):
                nonlocal received_config
                received_config = config
                return MagicMock(
                    success=True,
                    results={"total_files": 0},
                    report_html=None,
                    files_scanned=0,
                    issues_found=0,
                    error_message=None,
                )

            mock_tool.side_effect = capture_config
            await executor.execute(sample_job_claim_response)

        assert config_loaded.is_set()
        assert received_config == expected_config


class TestResultSigningIntegration:
    """Integration tests for result signing."""

    @pytest.mark.asyncio
    async def test_results_are_signed(self, mock_api_client, sample_job_claim_response):
        """Results are signed with job's signing secret."""
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
        result_data = {"total_files": 100, "issues_found": 5}

        with patch.object(executor, '_execute_tool', new_callable=AsyncMock) as mock_tool:
            mock_tool.return_value = MagicMock(
                success=True,
                results=result_data,
                report_html="<html></html>",
                files_scanned=100,
                issues_found=5,
                error_message=None,
            )

            await executor.execute(sample_job_claim_response)

        # Verify signature was computed
        call_kwargs = mock_api_client.complete_job.call_args.kwargs
        signature = call_kwargs["signature"]

        # Verify signature is valid
        signer = ResultSigner(sample_job_claim_response["signing_secret"])
        assert signer.verify(result_data, signature)

    @pytest.mark.asyncio
    async def test_failure_error_is_signed(self, mock_api_client, sample_job_claim_response):
        """Error messages are signed when job fails."""
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
        error_message = "Analysis failed: path not found"

        with patch.object(executor, '_execute_tool', new_callable=AsyncMock) as mock_tool:
            mock_tool.return_value = MagicMock(
                success=False,
                results={},
                error_message=error_message,
            )

            with pytest.raises(Exception):
                await executor.execute(sample_job_claim_response)

        # Verify signature was computed for failure
        call_kwargs = mock_api_client.fail_job.call_args.kwargs
        signature = call_kwargs["signature"]

        # Verify signature is valid for error data
        signer = ResultSigner(sample_job_claim_response["signing_secret"])
        assert signer.verify({"error": error_message}, signature)


class TestErrorRecovery:
    """Integration tests for error recovery scenarios."""

    @pytest.mark.asyncio
    async def test_config_load_error_fails_job(self, mock_api_client, sample_job_claim_response):
        """Job fails if config cannot be loaded."""
        mock_api_client.get_job_config = AsyncMock(
            side_effect=Exception("Config service unavailable")
        )

        executor = JobExecutor(mock_api_client)

        with pytest.raises(Exception, match="Config service unavailable"):
            await executor.execute(sample_job_claim_response)

        # Job should be failed
        mock_api_client.fail_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_api_error_does_not_crash(self, mock_api_client, sample_job_claim_response):
        """API error when completing job doesn't crash executor."""
        mock_api_client.get_job_config = AsyncMock(return_value={
            "config": {
                "photo_extensions": [".dng"],
                "metadata_extensions": [".xmp"],
                "camera_mappings": {},
                "processing_methods": {},
                "require_sidecar": [],
            },
        })
        mock_api_client.complete_job = AsyncMock(
            side_effect=Exception("Server error")
        )

        executor = JobExecutor(mock_api_client)

        with patch.object(executor, '_execute_tool', new_callable=AsyncMock) as mock_tool:
            mock_tool.return_value = MagicMock(
                success=True,
                results={"total_files": 0},
                report_html=None,
                files_scanned=0,
                issues_found=0,
                error_message=None,
            )

            # Should raise the complete_job exception
            with pytest.raises(Exception, match="Server error"):
                await executor.execute(sample_job_claim_response)
