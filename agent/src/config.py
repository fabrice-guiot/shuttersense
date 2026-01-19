"""
Agent configuration module.

Manages agent configuration including server URL, API key storage,
and runtime settings. Configuration can be loaded from files or
environment variables.

Issue #90 - Distributed Agent Architecture (Phase 3)
Task: T039
"""

import os
import re
from pathlib import Path
from typing import Optional

import yaml
from platformdirs import user_config_dir


# ============================================================================
# Constants
# ============================================================================

APP_NAME = "shuttersense"
APP_AUTHOR = "ShutterSense"
CONFIG_FILENAME = "agent-config.yaml"

# Environment variable names
ENV_SERVER_URL = "SHUTTERSENSE_SERVER_URL"
ENV_API_KEY = "SHUTTERSENSE_API_KEY"
ENV_LOG_LEVEL = "SHUTTERSENSE_LOG_LEVEL"
ENV_CONFIG_PATH = "SHUTTERSENSE_CONFIG_PATH"

# Default values
DEFAULT_HEARTBEAT_INTERVAL = 30  # seconds
DEFAULT_POLL_INTERVAL = 5  # seconds
DEFAULT_LOG_LEVEL = "INFO"

# URL validation regex
URL_PATTERN = re.compile(
    r"^https?://"  # http:// or https://
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
    r"localhost|"  # localhost
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
    r"(?::\d+)?"  # optional port
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)


# ============================================================================
# Exceptions
# ============================================================================


class ConfigError(Exception):
    """Base exception for configuration errors."""

    pass


class ConfigValidationError(ConfigError):
    """Raised when configuration validation fails."""

    pass


# ============================================================================
# Helper Functions
# ============================================================================


def get_default_config_dir() -> Path:
    """
    Get the default configuration directory for the current platform.

    Returns:
        Path to the platform-appropriate config directory
    """
    return Path(user_config_dir(APP_NAME, APP_AUTHOR))


def get_default_config_path() -> Path:
    """
    Get the default configuration file path.

    Returns:
        Path to the default config file
    """
    return get_default_config_dir() / CONFIG_FILENAME


# ============================================================================
# AgentConfig Class
# ============================================================================


class AgentConfig:
    """
    Agent configuration manager.

    Handles loading, saving, and validating agent configuration.
    Configuration sources (in priority order):
    1. Environment variables
    2. Configuration file
    3. Default values

    Attributes:
        server_url: ShutterSense server URL
        api_key: Agent API key for authentication
        agent_guid: Agent's unique identifier
        agent_name: Human-readable agent name
        heartbeat_interval_seconds: Interval for heartbeat messages
        poll_interval_seconds: Interval for job polling
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        config_dir: Optional[Path] = None,
    ):
        """
        Initialize agent configuration.

        Args:
            config_path: Explicit path to config file (takes precedence)
            config_dir: Directory containing config file
        """
        # Determine config path
        if config_path:
            self._config_path = Path(config_path)
            self._config_dir = self._config_path.parent
        elif config_dir:
            self._config_dir = Path(config_dir)
            self._config_path = self._config_dir / CONFIG_FILENAME
        else:
            env_path = os.environ.get(ENV_CONFIG_PATH)
            if env_path:
                self._config_path = Path(env_path)
                self._config_dir = self._config_path.parent
            else:
                self._config_dir = get_default_config_dir()
                self._config_path = self._config_dir / CONFIG_FILENAME

        # Initialize with defaults
        self._server_url: str = ""
        self._api_key: str = ""
        self._agent_guid: str = ""
        self._agent_name: str = ""
        self._heartbeat_interval_seconds: int = DEFAULT_HEARTBEAT_INTERVAL
        self._poll_interval_seconds: int = DEFAULT_POLL_INTERVAL
        self._log_level: str = DEFAULT_LOG_LEVEL

        # Load configuration
        self._load()

    @property
    def config_path(self) -> Path:
        """Get the configuration file path."""
        return self._config_path

    @property
    def config_dir(self) -> Path:
        """Get the configuration directory."""
        return self._config_dir

    # -------------------------------------------------------------------------
    # Configuration Properties
    # -------------------------------------------------------------------------

    @property
    def server_url(self) -> str:
        """Get the server URL."""
        return os.environ.get(ENV_SERVER_URL, self._server_url)

    @server_url.setter
    def server_url(self, value: str) -> None:
        """Set the server URL."""
        self._server_url = value

    @property
    def api_key(self) -> str:
        """Get the API key."""
        return os.environ.get(ENV_API_KEY, self._api_key)

    @api_key.setter
    def api_key(self, value: str) -> None:
        """Set the API key."""
        self._api_key = value

    @property
    def agent_guid(self) -> str:
        """Get the agent GUID."""
        return self._agent_guid

    @agent_guid.setter
    def agent_guid(self, value: str) -> None:
        """Set the agent GUID."""
        self._agent_guid = value

    @property
    def agent_name(self) -> str:
        """Get the agent name."""
        return self._agent_name

    @agent_name.setter
    def agent_name(self, value: str) -> None:
        """Set the agent name."""
        self._agent_name = value

    @property
    def heartbeat_interval_seconds(self) -> int:
        """Get the heartbeat interval in seconds."""
        return self._heartbeat_interval_seconds

    @heartbeat_interval_seconds.setter
    def heartbeat_interval_seconds(self, value: int) -> None:
        """Set the heartbeat interval in seconds."""
        self._heartbeat_interval_seconds = value

    @property
    def poll_interval_seconds(self) -> int:
        """Get the poll interval in seconds."""
        return self._poll_interval_seconds

    @poll_interval_seconds.setter
    def poll_interval_seconds(self, value: int) -> None:
        """Set the poll interval in seconds."""
        self._poll_interval_seconds = value

    @property
    def log_level(self) -> str:
        """Get the log level."""
        return os.environ.get(ENV_LOG_LEVEL, self._log_level)

    @log_level.setter
    def log_level(self, value: str) -> None:
        """Set the log level."""
        self._log_level = value

    # -------------------------------------------------------------------------
    # Computed Properties
    # -------------------------------------------------------------------------

    @property
    def is_registered(self) -> bool:
        """Check if the agent is registered with a server."""
        return bool(self.api_key and self.agent_guid)

    @property
    def is_configured(self) -> bool:
        """Check if the agent is configured with a server URL."""
        return bool(self.server_url)

    # -------------------------------------------------------------------------
    # Configuration Management
    # -------------------------------------------------------------------------

    def _load(self) -> None:
        """Load configuration from file."""
        if not self._config_path.exists():
            return

        try:
            with open(self._config_path) as f:
                data = yaml.safe_load(f) or {}

            self._server_url = data.get("server_url", "")
            self._api_key = data.get("api_key", "")
            self._agent_guid = data.get("agent_guid", "")
            self._agent_name = data.get("agent_name", "")
            self._heartbeat_interval_seconds = data.get(
                "heartbeat_interval_seconds", DEFAULT_HEARTBEAT_INTERVAL
            )
            self._poll_interval_seconds = data.get(
                "poll_interval_seconds", DEFAULT_POLL_INTERVAL
            )
            self._log_level = data.get("log_level", DEFAULT_LOG_LEVEL)

        except yaml.YAMLError as e:
            raise ConfigError(f"Failed to parse config file: {e}")

    def save(self) -> None:
        """Save configuration to file."""
        # Ensure directory exists
        self._config_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "server_url": self._server_url,
            "api_key": self._api_key,
            "agent_guid": self._agent_guid,
            "agent_name": self._agent_name,
            "heartbeat_interval_seconds": self._heartbeat_interval_seconds,
            "poll_interval_seconds": self._poll_interval_seconds,
            "log_level": self._log_level,
        }

        with open(self._config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def validate(self) -> None:
        """
        Validate the current configuration.

        Raises:
            ConfigValidationError: If configuration is invalid
        """
        # Validate server_url if set
        if self.server_url and not URL_PATTERN.match(self.server_url):
            raise ConfigValidationError(
                f"Invalid server_url format: {self.server_url}"
            )

        # Validate heartbeat interval
        if self.heartbeat_interval_seconds <= 0:
            raise ConfigValidationError(
                f"heartbeat_interval_seconds must be positive, got: {self.heartbeat_interval_seconds}"
            )

        # Validate poll interval
        if self.poll_interval_seconds < 0:
            raise ConfigValidationError(
                f"poll_interval_seconds must be non-negative, got: {self.poll_interval_seconds}"
            )

    def update_registration(
        self,
        agent_guid: str,
        api_key: str,
        agent_name: str,
    ) -> None:
        """
        Update configuration with registration information.

        Automatically saves the configuration after updating.

        Args:
            agent_guid: The registered agent's GUID
            api_key: The API key for authentication
            agent_name: The agent's display name
        """
        self._agent_guid = agent_guid
        self._api_key = api_key
        self._agent_name = agent_name
        self.save()

    def clear_registration(self) -> None:
        """
        Clear registration information.

        Does not automatically save - call save() explicitly.
        """
        self._agent_guid = ""
        self._api_key = ""
