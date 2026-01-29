"""
Team config cache storage for tool configuration.

Provides save/load operations for TeamConfigCache objects,
stored as a single JSON file at {data_dir}/team-config-cache.json.

The cache has a 24-hour TTL. Expired caches still return data but
signal staleness via is_valid()/is_expired().

Issue #108 - Remove CLI Direct Usage (Config Caching)
"""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.cache import TEAM_CONFIG_CACHE_TTL_HOURS, CachedPipeline, TeamConfigCache
from src.config import get_cache_paths

logger = logging.getLogger(__name__)


def _get_cache_file() -> Path:
    """Get the team config cache file path, creating parent dir if needed."""
    cache_file = get_cache_paths()["team_config_cache_file"]
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    return cache_file


def save(cache: TeamConfigCache) -> Path:
    """
    Save a team config cache to disk.

    Args:
        cache: TeamConfigCache to save

    Returns:
        Path to the saved cache file

    Raises:
        OSError: If the file cannot be written
    """
    cache_file = _get_cache_file()
    cache_file.write_text(cache.model_dump_json(indent=2), encoding="utf-8")
    logger.debug("Saved team config cache -> %s", cache_file)
    return cache_file


def load() -> Optional[TeamConfigCache]:
    """
    Load the team config cache from disk.

    Returns None if no cache file exists or if it cannot be parsed.

    Returns:
        TeamConfigCache if found and parseable, None otherwise
    """
    cache_file = _get_cache_file()
    if not cache_file.exists():
        return None

    try:
        raw = cache_file.read_text(encoding="utf-8")
        return TeamConfigCache.model_validate_json(raw)
    except Exception as e:
        logger.warning("Failed to load team config cache: %s", e)
        return None


def load_valid() -> Optional[TeamConfigCache]:
    """
    Load the team config cache only if it is still valid (not expired).

    Returns:
        TeamConfigCache if found and not expired, None otherwise
    """
    cache = load()
    if cache is None:
        return None
    if cache.is_expired():
        logger.debug("Team config cache expired (fetched at %s)", cache.fetched_at)
        return None
    return cache


def delete() -> bool:
    """
    Delete the team config cache file.

    Returns:
        True if a file was deleted, False if no cache existed
    """
    cache_file = _get_cache_file()
    if cache_file.exists():
        cache_file.unlink()
        logger.debug("Deleted team config cache")
        return True
    return False


def make_cache(
    agent_guid: str,
    server_response: Dict[str, Any],
) -> TeamConfigCache:
    """
    Create a new TeamConfigCache from a server API response.

    Args:
        agent_guid: GUID of the agent
        server_response: Response dict from GET /api/agent/v1/config

    Returns:
        A fully populated TeamConfigCache
    """
    now = datetime.now(timezone.utc)
    config = server_response["config"]

    pipeline_data = server_response.get("default_pipeline")
    cached_pipeline = None
    if pipeline_data:
        cached_pipeline = CachedPipeline(
            guid=pipeline_data["guid"],
            name=pipeline_data["name"],
            version=pipeline_data["version"],
            nodes=pipeline_data["nodes"],
            edges=pipeline_data["edges"],
        )

    return TeamConfigCache(
        agent_guid=agent_guid,
        fetched_at=now,
        expires_at=now + timedelta(hours=TEAM_CONFIG_CACHE_TTL_HOURS),
        photo_extensions=config["photo_extensions"],
        metadata_extensions=config["metadata_extensions"],
        cameras=config.get("cameras", {}),
        processing_methods=config.get("processing_methods", {}),
        require_sidecar=config["require_sidecar"],
        default_pipeline=cached_pipeline,
    )
