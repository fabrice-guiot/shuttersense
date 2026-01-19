"""
Job polling loop for agent.

Implements the main job polling loop that:
- Polls the server for available jobs at regular intervals
- Claims and executes jobs
- Reports progress and results back to the server
- Handles errors and retries gracefully

Issue #90 - Distributed Agent Architecture (Phase 5)
Tasks: T091, T097
"""

import asyncio
import logging
from typing import Optional, Dict, Any

from src.api_client import (
    AgentApiClient,
    AgentRevokedError,
    AuthenticationError,
    ConnectionError as AgentConnectionError,
    ApiError,
)


logger = logging.getLogger("shuttersense.agent.polling")

# Configuration
DEFAULT_POLL_INTERVAL = 5  # seconds between job polls when idle
MAX_POLL_FAILURES = 5  # Max consecutive failures before giving up


class JobPollingLoop:
    """
    Job polling loop for claiming and executing jobs.

    Polls the server for available jobs, claims them, executes them using
    the job executor, and reports results back to the server.

    Attributes:
        api_client: API client for server communication
        job_executor: Job executor instance
        poll_interval: Seconds between job polls
        shutdown_event: Event to signal shutdown
    """

    def __init__(
        self,
        api_client: AgentApiClient,
        job_executor: "JobExecutor",
        poll_interval: int = DEFAULT_POLL_INTERVAL,
    ):
        """
        Initialize the polling loop.

        Args:
            api_client: API client for server communication
            job_executor: Job executor for running tools
            poll_interval: Seconds between job polls
        """
        self._api_client = api_client
        self._job_executor = job_executor
        self._poll_interval = poll_interval
        self._shutdown_event = asyncio.Event()
        self._current_job: Optional[Dict[str, Any]] = None
        self._consecutive_failures = 0

    async def run(self) -> int:
        """
        Run the job polling loop.

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        logger.info(f"Starting job polling loop (interval: {self._poll_interval}s)")

        try:
            while not self._shutdown_event.is_set():
                try:
                    # Try to claim and execute a job
                    job_executed = await self._poll_and_execute()

                    # Reset failure counter on success
                    self._consecutive_failures = 0

                    # If no job was executed, wait before polling again
                    if not job_executed:
                        await self._wait_for_next_poll()

                except AgentConnectionError as e:
                    self._consecutive_failures += 1
                    logger.warning(
                        f"Connection error during poll: {e} "
                        f"(attempt {self._consecutive_failures}/{MAX_POLL_FAILURES})"
                    )

                    if self._consecutive_failures >= MAX_POLL_FAILURES:
                        logger.error("Too many consecutive connection failures")
                        return 4

                    # Wait before retrying
                    await self._wait_for_next_poll()

                except AgentRevokedError:
                    logger.error("Agent has been revoked")
                    return 2

                except AuthenticationError as e:
                    logger.error(f"Authentication error: {e}")
                    return 3

                except Exception as e:
                    self._consecutive_failures += 1
                    logger.error(
                        f"Unexpected error in polling loop: {e}",
                        exc_info=True
                    )

                    if self._consecutive_failures >= MAX_POLL_FAILURES:
                        logger.error("Too many consecutive errors")
                        return 5

                    await self._wait_for_next_poll()

        except asyncio.CancelledError:
            logger.info("Polling loop cancelled")
            return 0

        logger.info("Polling loop stopped")
        return 0

    async def _poll_and_execute(self) -> bool:
        """
        Poll for a job and execute it if available.

        Returns:
            True if a job was executed, False if no job available
        """
        # Try to claim a job
        job = await self._claim_job()
        if not job:
            return False

        self._current_job = job
        logger.info(f"Claimed job {job['guid']} ({job['tool']})")

        try:
            # Execute the job
            await self._job_executor.execute(job)

            logger.info(f"Job {job['guid']} completed successfully")
            return True

        except Exception as e:
            # Job execution failed - the executor should have reported the failure
            logger.error(f"Job {job['guid']} failed: {e}")
            return True  # Still return True since a job was attempted

        finally:
            self._current_job = None

    async def _claim_job(self) -> Optional[Dict[str, Any]]:
        """
        Try to claim a job from the server.

        Returns:
            Job data if a job was claimed, None otherwise
        """
        try:
            result = await self._api_client.claim_job()
            return result
        except ApiError as e:
            if e.status_code == 204:
                # No jobs available - this is normal
                return None
            raise

    async def _wait_for_next_poll(self) -> None:
        """Wait for the next poll interval or shutdown signal."""
        try:
            await asyncio.wait_for(
                self._shutdown_event.wait(),
                timeout=self._poll_interval,
            )
        except asyncio.TimeoutError:
            # Normal timeout, continue polling
            pass

    def request_shutdown(self) -> None:
        """Request graceful shutdown of the polling loop."""
        self._shutdown_event.set()

    @property
    def current_job(self) -> Optional[Dict[str, Any]]:
        """Get the currently executing job, if any."""
        return self._current_job

    @property
    def is_running(self) -> bool:
        """Check if the polling loop is running."""
        return not self._shutdown_event.is_set()
