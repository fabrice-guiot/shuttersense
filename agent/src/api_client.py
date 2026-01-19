"""
Agent API client for server communication.

Provides HTTP client for registration, heartbeat, and other server
communication. Handles authentication, error handling, and retries.

Issue #90 - Distributed Agent Architecture (Phase 3)
Task: T040
"""

from typing import Any, Optional

import httpx

from src import __version__


# ============================================================================
# Constants
# ============================================================================

API_VERSION = "v1"
API_BASE_PATH = f"/api/agent/{API_VERSION}"
DEFAULT_TIMEOUT = 30.0  # seconds
USER_AGENT = f"ShutterSense-Agent/{__version__}"


# ============================================================================
# Exceptions
# ============================================================================


class ApiError(Exception):
    """Base exception for API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class ConnectionError(ApiError):
    """Raised when connection to server fails."""

    pass


class RegistrationError(ApiError):
    """Raised when agent registration fails."""

    pass


class AuthenticationError(ApiError):
    """Raised when authentication fails (invalid API key)."""

    pass


class AgentRevokedError(ApiError):
    """Raised when agent has been revoked."""

    pass


# ============================================================================
# AgentApiClient Class
# ============================================================================


class AgentApiClient:
    """
    HTTP client for ShutterSense agent API.

    Handles all communication between the agent and the ShutterSense server,
    including registration, heartbeat, and job operations.

    Attributes:
        server_url: Base URL of the ShutterSense server
        api_key: Optional API key for authenticated requests
    """

    def __init__(
        self,
        server_url: str,
        api_key: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        """
        Initialize the API client.

        Args:
            server_url: Base URL of the ShutterSense server
            api_key: Optional API key for authenticated requests
            timeout: Request timeout in seconds

        Raises:
            ValueError: If server_url is empty
        """
        if not server_url:
            raise ValueError("server_url is required")

        self._server_url = server_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

        # Build headers
        headers = {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Create HTTP client
        self._client = httpx.AsyncClient(
            base_url=self._server_url,
            headers=headers,
            timeout=timeout,
        )

    @property
    def server_url(self) -> str:
        """Get the server URL."""
        return self._server_url

    # -------------------------------------------------------------------------
    # Registration
    # -------------------------------------------------------------------------

    async def register(
        self,
        registration_token: str,
        name: str,
        hostname: str,
        os_info: str,
        capabilities: list[str],
        version: str,
        binary_checksum: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Register a new agent with the server.

        Args:
            registration_token: One-time registration token from admin
            name: Agent display name
            hostname: Machine hostname
            os_info: Operating system information
            capabilities: List of agent capabilities
            version: Agent software version
            binary_checksum: Optional SHA-256 checksum of agent binary

        Returns:
            Registration response containing agent GUID and API key

        Raises:
            RegistrationError: If registration fails
            ConnectionError: If connection to server fails
        """
        payload = {
            "registration_token": registration_token,
            "name": name,
            "hostname": hostname,
            "os_info": os_info,
            "capabilities": capabilities,
            "version": version,
        }
        if binary_checksum:
            payload["binary_checksum"] = binary_checksum

        try:
            response = await self._client.post(
                f"{API_BASE_PATH}/register",
                json=payload,
            )
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect to server: {e}")
        except httpx.TimeoutException as e:
            raise ConnectionError(f"Connection timed out: {e}")

        if response.status_code == 201:
            return response.json()
        elif response.status_code == 400:
            detail = response.json().get("detail", "Registration failed")
            raise RegistrationError(detail, status_code=400)
        elif response.status_code == 404:
            raise RegistrationError("Invalid registration token", status_code=404)
        else:
            raise RegistrationError(
                f"Registration failed with status {response.status_code}",
                status_code=response.status_code,
            )

    # -------------------------------------------------------------------------
    # Heartbeat
    # -------------------------------------------------------------------------

    async def heartbeat(
        self,
        status: str = "online",
        capabilities: Optional[list[str]] = None,
        version: Optional[str] = None,
        current_job_guid: Optional[str] = None,
        current_job_progress: Optional[dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Send heartbeat to the server.

        Args:
            status: Current agent status (online, busy, error)
            capabilities: Updated capabilities list (if changed)
            version: Updated version (if changed)
            current_job_guid: GUID of job currently being executed
            current_job_progress: Progress info for current job
            error_message: Error message if status is error

        Returns:
            Heartbeat response with server time and pending commands

        Raises:
            AuthenticationError: If API key is invalid
            AgentRevokedError: If agent has been revoked
            ConnectionError: If connection to server fails
        """
        payload: dict[str, Any] = {"status": status}

        if capabilities is not None:
            payload["capabilities"] = capabilities
        if version is not None:
            payload["version"] = version
        if current_job_guid:
            payload["current_job_guid"] = current_job_guid
        if current_job_progress:
            payload["current_job_progress"] = current_job_progress
        if error_message:
            payload["error_message"] = error_message

        try:
            response = await self._client.post(
                f"{API_BASE_PATH}/heartbeat",
                json=payload,
            )
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect to server: {e}")
        except httpx.TimeoutException as e:
            raise ConnectionError(f"Connection timed out: {e}")

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise AuthenticationError("Invalid API key", status_code=401)
        elif response.status_code == 403:
            raise AgentRevokedError("Agent has been revoked", status_code=403)
        elif response.status_code == 404:
            raise AuthenticationError("Agent not found", status_code=404)
        else:
            raise ApiError(
                f"Heartbeat failed with status {response.status_code}",
                status_code=response.status_code,
            )

    # -------------------------------------------------------------------------
    # Agent Info
    # -------------------------------------------------------------------------

    async def get_me(self) -> dict[str, Any]:
        """
        Get current agent information.

        Returns:
            Agent information including status, capabilities, etc.

        Raises:
            AuthenticationError: If API key is invalid
            ConnectionError: If connection to server fails
        """
        try:
            response = await self._client.get(f"{API_BASE_PATH}/me")
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect to server: {e}")
        except httpx.TimeoutException as e:
            raise ConnectionError(f"Connection timed out: {e}")

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise AuthenticationError("Invalid API key", status_code=401)
        elif response.status_code == 404:
            raise AuthenticationError("Agent not found", status_code=404)
        else:
            raise ApiError(
                f"Get agent info failed with status {response.status_code}",
                status_code=response.status_code,
            )

    # -------------------------------------------------------------------------
    # Disconnect
    # -------------------------------------------------------------------------

    async def disconnect(self) -> None:
        """
        Notify the server that the agent is disconnecting.

        Called during graceful shutdown to immediately mark the agent as
        offline on the server side.

        Raises:
            AuthenticationError: If API key is invalid
            ConnectionError: If connection to server fails
        """
        try:
            response = await self._client.post(f"{API_BASE_PATH}/disconnect")
        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect to server: {e}")
        except httpx.TimeoutException as e:
            raise ConnectionError(f"Connection timed out: {e}")

        if response.status_code == 204:
            return
        elif response.status_code == 401:
            raise AuthenticationError("Invalid API key", status_code=401)
        elif response.status_code == 404:
            raise AuthenticationError("Agent not found", status_code=404)
        else:
            raise ApiError(
                f"Disconnect failed with status {response.status_code}",
                status_code=response.status_code,
            )

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> "AgentApiClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
