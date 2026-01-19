"""
Pytest configuration and fixtures for ShutterSense Agent tests.

This module provides shared fixtures for testing agent functionality,
including mock servers, temporary configuration files, and test data.
"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml


# ============================================================================
# Configuration Fixtures
# ============================================================================


@pytest.fixture
def temp_config_dir() -> Generator[Path, None, None]:
    """
    Create a temporary directory for agent configuration files.

    Yields:
        Path to temporary configuration directory
    """
    with tempfile.TemporaryDirectory(prefix="shuttersense_agent_test_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def agent_config(temp_config_dir: Path) -> dict:
    """
    Create a sample agent configuration.

    Returns:
        Dictionary with agent configuration
    """
    config = {
        "server_url": "http://localhost:8000",
        "agent_name": "Test Agent",
        "api_key": "agt_key_test_1234567890abcdef",
        "poll_interval_seconds": 5,
        "heartbeat_interval_seconds": 30,
        "log_level": "DEBUG",
    }
    return config


@pytest.fixture
def agent_config_file(temp_config_dir: Path, agent_config: dict) -> Path:
    """
    Create a temporary agent configuration file.

    Args:
        temp_config_dir: Temporary directory for config files
        agent_config: Agent configuration dictionary

    Returns:
        Path to the configuration file
    """
    config_path = temp_config_dir / "agent-config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(agent_config, f)
    return config_path


# ============================================================================
# Mock Server Fixtures
# ============================================================================


@pytest.fixture
def mock_server_url() -> str:
    """
    Get the mock server URL for testing.

    Returns:
        Mock server URL string
    """
    return "http://localhost:8000"


@pytest.fixture
def mock_registration_token() -> str:
    """
    Get a mock registration token for testing.

    Returns:
        Registration token string (art_ prefix)
    """
    return "art_test_registration_token_1234567890"


@pytest.fixture
def mock_api_key() -> str:
    """
    Get a mock API key for testing.

    Returns:
        API key string (agt_key_ prefix)
    """
    return "agt_key_test_1234567890abcdef1234567890abcdef"


@pytest.fixture
def mock_agent_guid() -> str:
    """
    Get a mock agent GUID for testing.

    Returns:
        Agent GUID string (agt_ prefix)
    """
    return "agt_01hgw2bbg0000000000000001"


# ============================================================================
# Job Fixtures
# ============================================================================


@pytest.fixture
def sample_job() -> dict:
    """
    Create a sample job for testing.

    Returns:
        Dictionary representing a job
    """
    return {
        "guid": "job_01hgw2bbg0000000000000001",
        "collection_guid": "col_01hgw2bbg0000000000000001",
        "tool": "photostats",
        "status": "assigned",
        "collection": {
            "guid": "col_01hgw2bbg0000000000000001",
            "name": "Test Collection",
            "type": "local",
            "location": "/path/to/photos",
        },
        "parameters": {},
        "websocket_url": "ws://localhost:8000/ws/agent/jobs/job_01hgw2bbg0000000000000001/progress",
    }


@pytest.fixture
def sample_job_progress() -> dict:
    """
    Create sample job progress data for testing.

    Returns:
        Dictionary representing job progress
    """
    return {
        "stage": "scanning",
        "percentage": 45,
        "files_scanned": 1234,
        "total_files": 2741,
        "current_file": "IMG_1234.jpg",
        "message": "Scanning files...",
    }


# ============================================================================
# Mock HTTP Client Fixtures
# ============================================================================


@pytest.fixture
def mock_http_client() -> MagicMock:
    """
    Create a mock HTTP client for testing API calls.

    Returns:
        Mock httpx.AsyncClient
    """
    client = MagicMock()
    client.post = AsyncMock()
    client.get = AsyncMock()
    client.patch = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.fixture
def mock_websocket() -> MagicMock:
    """
    Create a mock WebSocket connection for testing progress streaming.

    Returns:
        Mock websockets connection
    """
    ws = MagicMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock()
    ws.close = AsyncMock()
    ws.__aenter__ = AsyncMock(return_value=ws)
    ws.__aexit__ = AsyncMock()
    return ws


# ============================================================================
# Registration Response Fixtures
# ============================================================================


@pytest.fixture
def registration_success_response(mock_agent_guid: str, mock_api_key: str) -> dict:
    """
    Create a successful registration response.

    Args:
        mock_agent_guid: Agent GUID
        mock_api_key: API key

    Returns:
        Dictionary representing registration response
    """
    return {
        "agent_guid": mock_agent_guid,
        "api_key": mock_api_key,
        "server_url": "http://localhost:8000",
        "websocket_url": "ws://localhost:8000/ws/agent",
    }


@pytest.fixture
def heartbeat_response() -> dict:
    """
    Create a heartbeat response.

    Returns:
        Dictionary representing heartbeat response
    """
    return {
        "acknowledged": True,
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# Environment Fixtures
# ============================================================================


@pytest.fixture
def clean_environment(monkeypatch) -> None:
    """
    Clean environment variables that might affect tests.

    Removes ShutterSense-related environment variables to ensure
    test isolation.
    """
    env_vars_to_remove = [
        "SHUTTERSENSE_SERVER_URL",
        "SHUTTERSENSE_API_KEY",
        "SHUTTERSENSE_LOG_LEVEL",
        "SHUTTERSENSE_CONFIG_PATH",
    ]
    for var in env_vars_to_remove:
        monkeypatch.delenv(var, raising=False)


# ============================================================================
# Capability Fixtures
# ============================================================================


@pytest.fixture
def sample_capabilities() -> list[str]:
    """
    Create sample agent capabilities for testing.

    Returns:
        List of capability strings
    """
    return [
        "local_filesystem",
        "tool:photostats:1.0.0",
        "tool:photo_pairing:1.0.0",
        "tool:pipeline_validation:1.0.0",
    ]


@pytest.fixture
def sample_capabilities_with_connector() -> list[str]:
    """
    Create sample agent capabilities including a connector.

    Returns:
        List of capability strings including connector capability
    """
    return [
        "local_filesystem",
        "tool:photostats:1.0.0",
        "tool:photo_pairing:1.0.0",
        "tool:pipeline_validation:1.0.0",
        "connector:con_01hgw2bbg0000000000000001",
    ]


# ============================================================================
# Job Claim Response Fixtures (Phase 5)
# ============================================================================


@pytest.fixture
def sample_job_claim_response():
    """Sample job claim response data."""
    return {
        "guid": "job_01hgw2bbg0000000000000001",
        "tool": "photostats",
        "mode": "collection",
        "collection_guid": "col_01hgw2bbg0000000000000001",
        "collection_path": "/tmp/test",
        "pipeline_guid": None,
        "signing_secret": "dGVzdC1zZWNyZXQtMzItYnl0ZXMtaGVyZSEh",  # base64 encoded
        "priority": 0,
        "retry_count": 0,
        "max_retries": 3,
    }


@pytest.fixture
def sample_config():
    """Sample configuration data."""
    return {
        "photo_extensions": [".dng", ".cr3", ".tiff"],
        "metadata_extensions": [".xmp"],
        "camera_mappings": {
            "AB3D": [{"name": "Canon EOS R5", "serial_number": "12345"}]
        },
        "processing_methods": {
            "HDR": "High Dynamic Range",
            "BW": "Black and White"
        },
        "require_sidecar": [".cr3"]
    }


@pytest.fixture
def mock_api_client():
    """Create a mock API client for job operations."""
    client = MagicMock()
    client.claim_job = AsyncMock(return_value=None)
    client.update_job_progress = AsyncMock(return_value={"status": "ok"})
    client.complete_job = AsyncMock(return_value={"status": "ok"})
    client.fail_job = AsyncMock(return_value={"status": "ok"})
    client.get_job_config = AsyncMock(return_value={
        "config": {
            "photo_extensions": [".dng", ".cr3"],
            "metadata_extensions": [".xmp"],
            "camera_mappings": {},
            "processing_methods": {},
            "require_sidecar": [".cr3"],
        },
        "collection_path": "/tmp/test",
        "pipeline_guid": None,
    })
    client.heartbeat = AsyncMock(return_value={"server_time": "2024-01-01T00:00:00"})
    client.disconnect = AsyncMock()
    client.close = AsyncMock()
    return client
