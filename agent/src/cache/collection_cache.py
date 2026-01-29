"""
Collection cache storage for local collection snapshots.

Provides save/load operations for CollectionCache objects,
stored as a single JSON file at {data_dir}/collection-cache.json.

The cache has a 7-day TTL. Expired caches still return data but
signal staleness via is_valid()/is_expired().

Issue #108 - Remove CLI Direct Usage
Task: T020
"""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from src.cache import COLLECTION_CACHE_TTL_DAYS, CachedCollection, CollectionCache
from src.config import get_cache_paths

logger = logging.getLogger(__name__)


def _get_cache_file() -> Path:
    """Get the collection cache file path, creating parent dir if needed."""
    cache_file = get_cache_paths()["collection_cache_file"]
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    return cache_file


def save(cache: CollectionCache) -> Path:
    """
    Save a collection cache to disk.

    Args:
        cache: CollectionCache to save

    Returns:
        Path to the saved cache file

    Raises:
        OSError: If the file cannot be written
    """
    cache_file = _get_cache_file()
    cache_file.write_text(cache.model_dump_json(indent=2), encoding="utf-8")
    logger.debug(
        "Saved collection cache with %d collections -> %s",
        len(cache.collections),
        cache_file,
    )
    return cache_file


def load() -> Optional[CollectionCache]:
    """
    Load the collection cache from disk.

    Returns None if no cache file exists or if it cannot be parsed.

    Returns:
        CollectionCache if found and parseable, None otherwise
    """
    cache_file = _get_cache_file()
    if not cache_file.exists():
        return None

    try:
        raw = cache_file.read_text(encoding="utf-8")
        return CollectionCache.model_validate_json(raw)
    except Exception as e:
        logger.warning("Failed to load collection cache: %s", e)
        return None


def load_valid() -> Optional[CollectionCache]:
    """
    Load the collection cache only if it is still valid (not expired).

    Returns:
        CollectionCache if found and not expired, None otherwise
    """
    cache = load()
    if cache is None:
        return None
    if cache.is_expired():
        logger.debug("Collection cache expired (synced at %s)", cache.synced_at)
        return None
    return cache


def delete() -> bool:
    """
    Delete the collection cache file.

    Returns:
        True if a file was deleted, False if no cache existed
    """
    cache_file = _get_cache_file()
    if cache_file.exists():
        cache_file.unlink()
        logger.debug("Deleted collection cache")
        return True
    return False


def make_cache(
    agent_guid: str,
    collections: list[CachedCollection],
) -> CollectionCache:
    """
    Create a new CollectionCache with computed timestamps.

    Args:
        agent_guid: GUID of the agent
        collections: List of CachedCollection items

    Returns:
        A fully populated CollectionCache
    """
    now = datetime.now(timezone.utc)
    return CollectionCache(
        agent_guid=agent_guid,
        synced_at=now,
        expires_at=now + timedelta(days=COLLECTION_CACHE_TTL_DAYS),
        collections=collections,
    )
