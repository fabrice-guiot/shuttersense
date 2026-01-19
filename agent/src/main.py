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
from src.api_client import (
    AgentApiClient,
    AgentRevokedError,
    AuthenticationError,
    ConnectionError as AgentConnectionError,
)


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

        Returns:
            Exit code
        """
        consecutive_failures = 0
        max_failures = 5

        while not self._shutdown_event.is_set():
            try:
                # Send heartbeat
                response = await self._api_client.heartbeat()
                self.logger.debug(f"Heartbeat acknowledged, server time: {response.get('server_time')}")

                # Reset failure counter on success
                consecutive_failures = 0

                # Process any pending commands
                pending_commands = response.get("pending_commands", [])
                if pending_commands:
                    self.logger.info(f"Received {len(pending_commands)} pending commands")
                    # TODO: Process commands (Phase 4)

            except AgentConnectionError as e:
                consecutive_failures += 1
                self.logger.warning(f"Connection error: {e} (attempt {consecutive_failures}/{max_failures})")

                if consecutive_failures >= max_failures:
                    self.logger.error("Too many consecutive connection failures, exiting")
                    return 4

            except AgentRevokedError:
                raise  # Re-raise to be handled by run()

            except AuthenticationError:
                raise  # Re-raise to be handled by run()

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

        self.logger.info("Agent stopped")
        return 0

    def request_shutdown(self) -> None:
        """Request graceful shutdown of the agent."""
        self._shutdown_event.set()


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
