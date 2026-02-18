"""
Version cache for outdated agent detection.

Caches `latest_version` and `is_outdated` from heartbeat responses
in a local state file using platformdirs. Cache expires after 1 hour.

Issue #243 - Agent CLI self-update command & outdated warnings
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional

from src.config import get_default_data_dir

logger = logging.getLogger(__name__)

# Cache file name within the agent data directory
CACHE_FILENAME = "version-state.json"

# Cache entries expire after 1 hour (3600 seconds)
CACHE_TTL_SECONDS = 3600


def _get_cache_path() -> Path:
    """Get path to the version state cache file."""
    return get_default_data_dir() / CACHE_FILENAME


def read_cached_version_state() -> Optional[dict]:
    """
    Read cached version state from local file.

    Returns:
        Dict with 'is_outdated', 'latest_version', 'cached_at' if cache
        is valid and not expired, or None if cache is missing/expired/corrupt.
    """
    cache_path = _get_cache_path()

    if not cache_path.exists():
        return None

    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.debug(f"Failed to read version cache: {e}")
        return None

    # Check expiry
    cached_at = data.get("cached_at", 0)
    if time.time() - cached_at > CACHE_TTL_SECONDS:
        logger.debug("Version cache expired")
        return None

    return data


def write_version_cache(is_outdated: bool, latest_version: Optional[str]) -> None:
    """
    Write version state to local cache file.

    Args:
        is_outdated: Whether the server considers this agent outdated.
        latest_version: Latest available version string, or None.
    """
    cache_path = _get_cache_path()

    data = {
        "is_outdated": is_outdated,
        "latest_version": latest_version,
        "cached_at": time.time(),
    }

    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data), encoding="utf-8")
    except OSError as e:
        logger.debug(f"Failed to write version cache: {e}")
