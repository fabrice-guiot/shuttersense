"""
Progress reporter for job execution.

Reports job progress to the server via REST API with rate limiting
to prevent overwhelming the server.

Issue #90 - Distributed Agent Architecture (Phase 5)
Tasks: T093, T099
"""

import asyncio
import logging
import time
from typing import Optional

from src.api_client import AgentApiClient


logger = logging.getLogger("shuttersense.agent.progress")

# Rate limiting configuration
MIN_REPORT_INTERVAL = 0.5  # Minimum seconds between progress reports (2/second max)


class ProgressReporter:
    """
    Progress reporter for job execution.

    Reports progress updates to the server via REST API. Implements rate
    limiting to prevent overwhelming the server with updates.

    Attributes:
        api_client: API client for server communication
        job_guid: GUID of the job being executed
    """

    def __init__(
        self,
        api_client: AgentApiClient,
        job_guid: str,
    ):
        """
        Initialize the progress reporter.

        Args:
            api_client: API client for server communication
            job_guid: GUID of the job being executed
        """
        self._api_client = api_client
        self._job_guid = job_guid
        self._last_report_time: float = 0
        self._pending_report: Optional[dict] = None
        self._report_task: Optional[asyncio.Task] = None
        self._closed = False

    async def report(
        self,
        stage: str,
        percentage: Optional[int] = None,
        files_scanned: Optional[int] = None,
        total_files: Optional[int] = None,
        current_file: Optional[str] = None,
        message: Optional[str] = None,
    ) -> None:
        """
        Report job progress to the server.

        Implements rate limiting - if called too frequently, the latest
        progress will be queued and sent after the minimum interval.

        Args:
            stage: Current execution stage
            percentage: Progress percentage (0-100)
            files_scanned: Number of files scanned
            total_files: Total files to scan
            current_file: Currently processing file
            message: Progress message
        """
        if self._closed:
            return

        # Build progress data
        progress = {"stage": stage}
        if percentage is not None:
            progress["percentage"] = percentage
        if files_scanned is not None:
            progress["files_scanned"] = files_scanned
        if total_files is not None:
            progress["total_files"] = total_files
        if current_file is not None:
            progress["current_file"] = current_file
        if message is not None:
            progress["message"] = message

        # Check rate limiting
        now = time.monotonic()
        time_since_last = now - self._last_report_time

        if time_since_last >= MIN_REPORT_INTERVAL:
            # Enough time has passed, send immediately
            await self._send_report(progress)
        else:
            # Queue the report for later
            self._pending_report = progress

            # Schedule a delayed send if not already scheduled
            if self._report_task is None or self._report_task.done():
                delay = MIN_REPORT_INTERVAL - time_since_last
                self._report_task = asyncio.create_task(
                    self._delayed_send(delay)
                )

    async def _send_report(self, progress: dict) -> None:
        """
        Send a progress report to the server.

        Args:
            progress: Progress data to send
        """
        try:
            await self._api_client.update_job_progress(
                job_guid=self._job_guid,
                **progress
            )
            self._last_report_time = time.monotonic()

            logger.debug(
                f"Progress reported for job {self._job_guid}: {progress}"
            )

        except Exception as e:
            logger.warning(f"Failed to report progress: {e}")
            # Don't raise - progress reporting is best-effort

    async def _delayed_send(self, delay: float) -> None:
        """
        Send a pending progress report after a delay.

        Args:
            delay: Seconds to wait before sending
        """
        await asyncio.sleep(delay)

        if self._pending_report and not self._closed:
            progress = self._pending_report
            self._pending_report = None
            await self._send_report(progress)

    async def close(self) -> None:
        """
        Close the progress reporter.

        Sends any pending progress report before closing.
        """
        self._closed = True

        # Cancel any scheduled report
        if self._report_task and not self._report_task.done():
            self._report_task.cancel()
            try:
                await self._report_task
            except asyncio.CancelledError:
                pass

        # Send final pending report if any
        if self._pending_report:
            try:
                await self._send_report(self._pending_report)
            except Exception:
                pass  # Best effort
            self._pending_report = None
