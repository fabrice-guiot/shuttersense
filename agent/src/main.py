"""
Agent main loop.

Implements the agent polling loop with heartbeat and job execution.

Issue #90 - Distributed Agent Architecture (Phase 3)
Task: T043
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from src import __version__
from src.config import AgentConfig
from src.capabilities import detect_capabilities
from src.credential_store import CredentialStore
from src.api_client import (
    AgentApiClient,
    AgentRevokedError,
    AuthenticationError,
    ConnectionError as AgentConnectionError,
)
from src.polling_loop import JobPollingLoop
from src.job_executor import JobExecutor


def get_all_capabilities() -> list[str]:
    """
    Get all agent capabilities including connector credentials.

    Returns:
        List of capability strings
    """
    # Get built-in capabilities (tools, local_filesystem)
    capabilities = detect_capabilities()

    # Add connector capabilities from credential store
    try:
        store = CredentialStore()
        connector_guids = store.list_connector_guids()
        for guid in connector_guids:
            capabilities.append(f"connector:{guid}")
    except Exception:
        # Credential store not initialized or error - skip connector capabilities
        pass

    return capabilities


# ============================================================================
# Logging Setup
# ============================================================================


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Setup logging for the agent.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger
    """
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("shuttersense.agent")


# ============================================================================
# Agent Runner
# ============================================================================


class AgentRunner:
    """
    Main agent loop runner.

    Manages the heartbeat loop and job polling. Handles graceful shutdown
    on SIGINT/SIGTERM.

    Attributes:
        config: Agent configuration
        api_client: API client for server communication
        logger: Logger instance
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize the agent runner.

        Args:
            config: Agent configuration
        """
        self.config = config
        self.logger = setup_logging(config.log_level)
        self._shutdown_event = asyncio.Event()
        self._api_client: Optional[AgentApiClient] = None
        self._polling_loop: Optional[JobPollingLoop] = None

    async def run(self) -> int:
        """
        Run the main agent loop.

        Returns:
            Exit code (0 for success, non-zero for error)
        """
        # Setup signal handlers in the async context for immediate response
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self.request_shutdown)

        # Validate configuration
        if not self.config.is_registered:
            self.logger.error("Agent is not registered. Run 'shuttersense-agent register' first.")
            return 1

        if not self.config.is_configured:
            self.logger.error("Agent is not configured with a server URL.")
            return 1

        self.logger.info(f"Starting ShutterSense Agent v{__version__}")
        self.logger.info(f"Agent GUID: {self.config.agent_guid}")
        self.logger.info(f"Server: {self.config.server_url}")
        self.logger.info(f"Heartbeat interval: {self.config.heartbeat_interval_seconds}s")

        # Create API client
        self._api_client = AgentApiClient(
            server_url=self.config.server_url,
            api_key=self.config.api_key,
        )

        try:
            # Run the main loop
            return await self._main_loop()
        except asyncio.CancelledError:
            self.logger.info("Agent shutdown requested")
            return 0
        except AgentRevokedError:
            self.logger.error("Agent has been revoked by administrator")
            return 2
        except AuthenticationError as e:
            self.logger.error(f"Authentication failed: {e}")
            return 3
        finally:
            if self._api_client:
                # Notify server of graceful disconnect
                try:
                    self.logger.info("Notifying server of disconnect...")
                    await self._api_client.disconnect()
                    self.logger.info("Disconnected from server")
                except Exception as e:
                    self.logger.warning(f"Failed to notify server of disconnect: {e}")
                await self._api_client.close()

    async def _main_loop(self) -> int:
        """
        Main heartbeat and polling loop.

        Runs the heartbeat loop and job polling loop concurrently.

        Returns:
            Exit code
        """
        # Detect capabilities on startup (in case tools were added/upgraded or connectors configured)
        self.logger.info("Detecting agent capabilities...")
        capabilities = get_all_capabilities()
        self.logger.info(f"Detected capabilities: {capabilities}")

        # Send initial heartbeat with capabilities, version, and authorized roots to set agent status to ONLINE
        # This ensures the agent can claim jobs immediately and has up-to-date capabilities/version/roots
        authorized_roots = self.config.authorized_roots
        self.logger.info(f"Sending initial heartbeat (version: {__version__}, roots: {len(authorized_roots)})...")
        try:
            await self._api_client.heartbeat(
                capabilities=capabilities,
                version=__version__,
                authorized_roots=authorized_roots,
            )
            self.logger.info("Initial heartbeat acknowledged, agent is now ONLINE")
        except AgentRevokedError:
            raise  # Re-raise to be handled by caller
        except AuthenticationError:
            raise  # Re-raise to be handled by caller
        except Exception as e:
            self.logger.warning(f"Initial heartbeat failed: {e}, continuing anyway...")

        # Create job executor and polling loop
        job_executor = JobExecutor(self._api_client)
        self._polling_loop = JobPollingLoop(
            api_client=self._api_client,
            job_executor=job_executor,
            poll_interval=5,  # Poll every 5 seconds when idle
        )

        # Start heartbeat and polling loops concurrently
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        polling_task = asyncio.create_task(self._polling_loop.run())

        try:
            # Wait for either task to complete (or shutdown)
            done, pending = await asyncio.wait(
                [heartbeat_task, polling_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Check if any task failed
            for task in done:
                exc = task.exception()
                if exc:
                    raise exc
                result = task.result()
                if result != 0:
                    return result

        finally:
            # Signal shutdown to both loops
            self._shutdown_event.set()
            self._polling_loop.request_shutdown()

            # Cancel pending tasks
            for task in [heartbeat_task, polling_task]:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

        self.logger.info("Agent stopped")
        return 0

    async def _heartbeat_loop(self) -> int:
        """
        Heartbeat loop for maintaining server connection.

        Returns:
            Exit code
        """
        consecutive_failures = 0
        max_failures = 5
        heartbeat_count = 0

        while not self._shutdown_event.is_set():
            try:
                # Refresh capabilities periodically (every 10 heartbeats, ~5 minutes)
                # This catches new connector credentials configured while agent is running
                capabilities = None
                if heartbeat_count % 10 == 0:
                    capabilities = get_all_capabilities()
                    self.logger.debug(f"Refreshed capabilities: {len(capabilities)} total")

                # Send heartbeat with authorized roots and capabilities (if refreshed)
                response = await self._api_client.heartbeat(
                    authorized_roots=self.config.authorized_roots,
                    capabilities=capabilities,
                )
                self.logger.debug(f"Heartbeat acknowledged, server time: {response.get('server_time')}")
                heartbeat_count += 1

                # Reset failure counter on success
                consecutive_failures = 0

                # Process any pending commands
                pending_commands = response.get("pending_commands", [])
                for cmd in pending_commands:
                    await self._process_command(cmd)

            except AgentConnectionError as e:
                consecutive_failures += 1
                self.logger.warning(f"Connection error: {e} (attempt {consecutive_failures}/{max_failures})")

                if consecutive_failures >= max_failures:
                    self.logger.error("Too many consecutive connection failures, exiting")
                    return 4

            except AgentRevokedError:
                raise  # Re-raise to be handled by caller

            except AuthenticationError:
                raise  # Re-raise to be handled by caller

            except Exception as e:
                consecutive_failures += 1
                self.logger.error(f"Unexpected error in heartbeat: {e}")

                if consecutive_failures >= max_failures:
                    self.logger.error("Too many consecutive errors, exiting")
                    return 5

            # Wait for next heartbeat interval or shutdown
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self.config.heartbeat_interval_seconds,
                )
                # Shutdown was requested
                break
            except asyncio.TimeoutError:
                # Normal timeout, continue loop
                pass

        return 0

    def request_shutdown(self) -> None:
        """Request graceful shutdown of the agent."""
        self._shutdown_event.set()

    async def _process_command(self, command: str) -> None:
        """
        Process a pending command from the server.

        Commands are strings like:
        - "cancel_job:{job_guid}" - Cancel the specified job

        Args:
            command: Command string to process
        """
        self.logger.info(f"Processing command: {command}")

        if command.startswith("cancel_job:"):
            job_guid = command.split(":", 1)[1]
            await self._handle_cancel_job(job_guid)
        else:
            self.logger.warning(f"Unknown command: {command}")

    async def _handle_cancel_job(self, job_guid: str) -> None:
        """
        Handle a cancel_job command.

        If the specified job is currently being executed, request its cancellation.
        If the job is not the current job, log and ignore (the job may have
        already completed or never been claimed by this agent).

        Args:
            job_guid: GUID of the job to cancel
        """
        if not hasattr(self, '_polling_loop') or self._polling_loop is None:
            self.logger.warning(f"Cannot cancel job {job_guid}: polling loop not initialized")
            return

        current_job = self._polling_loop.current_job
        if current_job and current_job.get("guid") == job_guid:
            self.logger.info(f"Requesting cancellation of current job: {job_guid}")
            self._polling_loop.request_job_cancellation()
        else:
            self.logger.debug(
                f"Ignoring cancel for job {job_guid}: not the current job "
                f"(current: {current_job.get('guid') if current_job else 'none'})"
            )


# ============================================================================
# Main Entry Point
# ============================================================================


def run_agent() -> int:
    """
    Run the agent.

    This is the main entry point for the agent daemon.

    Returns:
        Exit code
    """
    # Load configuration
    config = AgentConfig()

    # Create runner
    runner = AgentRunner(config)

    # Run the agent (signal handlers are setup inside the async context)
    return asyncio.run(runner.run())


if __name__ == "__main__":
    sys.exit(run_agent())
