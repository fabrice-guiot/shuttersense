"""
Test cache storage for local path test results.

Provides save/load/cleanup operations for TestCacheEntry objects,
stored as JSON files at {data_dir}/test-cache/{path_hash}.json.

Each entry has a 24-hour TTL. Expired entries are cleaned up on access.

Issue #108 - Remove CLI Direct Usage
Task: T008
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from src.cache import TEST_CACHE_TTL_HOURS, TestCacheEntry
from src.config import get_cache_paths

logger = logging.getLogger(__name__)


def _normalize_path(path: str) -> str:
    """Normalize a path for consistent hashing."""
    return str(Path(path).resolve())


def _hash_path(path: str) -> str:
    """Generate a SHA-256 hash of a normalized path."""
    normalized = _normalize_path(path)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _get_cache_dir() -> Path:
    """Get the test cache directory, creating it if needed."""
    cache_dir = get_cache_paths()["test_cache_dir"]
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _cache_file_for(path: str) -> Path:
    """Get the cache file path for a given directory path."""
    return _get_cache_dir() / f"{_hash_path(path)}.json"


def save(entry: TestCacheEntry) -> Path:
    """
    Save a test cache entry to disk.

    Args:
        entry: TestCacheEntry to save

    Returns:
        Path to the saved cache file

    Raises:
        OSError: If the file cannot be written
    """
    cache_file = _cache_file_for(entry.path)
    cache_file.write_text(entry.model_dump_json(indent=2), encoding="utf-8")
    logger.debug("Saved test cache entry for %s -> %s", entry.path, cache_file)
    return cache_file


def load(path: str) -> Optional[TestCacheEntry]:
    """
    Load a test cache entry for the given path.

    Returns None if no cache entry exists or if it cannot be parsed.

    Args:
        path: Absolute path that was tested

    Returns:
        TestCacheEntry if found and parseable, None otherwise
    """
    cache_file = _cache_file_for(path)
    if not cache_file.exists():
        return None

    try:
        raw = cache_file.read_text(encoding="utf-8")
        return TestCacheEntry.model_validate_json(raw)
    except Exception as e:
        logger.warning("Failed to load test cache for %s: %s", path, e)
        return None


def load_valid(path: str) -> Optional[TestCacheEntry]:
    """
    Load a test cache entry only if it is still valid (not expired).

    Args:
        path: Absolute path that was tested

    Returns:
        TestCacheEntry if found and not expired, None otherwise
    """
    entry = load(path)
    if entry is None:
        return None
    if not entry.is_valid():
        logger.debug("Test cache expired for %s, deleting", path)
        try:
            delete(path)
        except OSError:
            logger.debug("Failed to delete expired cache for %s", path)
        return None
    return entry


def delete(path: str) -> bool:
    """
    Delete the cache entry for a given path.

    Args:
        path: Absolute path whose cache entry to delete

    Returns:
        True if a file was deleted, False if no cache existed
    """
    cache_file = _cache_file_for(path)
    if cache_file.exists():
        cache_file.unlink()
        logger.debug("Deleted test cache for %s", path)
        return True
    return False


def cleanup() -> int:
    """
    Remove all expired test cache entries.

    Returns:
        Number of expired entries removed
    """
    cache_dir = _get_cache_dir()
    removed = 0

    for cache_file in cache_dir.glob("*.json"):
        try:
            raw = cache_file.read_text(encoding="utf-8")
            entry = TestCacheEntry.model_validate_json(raw)
            if not entry.is_valid():
                cache_file.unlink()
                removed += 1
                logger.debug("Cleaned up expired cache: %s", cache_file.name)
        except Exception as e:
            # Remove corrupted cache files
            logger.warning("Removing unparseable cache file %s: %s", cache_file.name, e)
            cache_file.unlink()
            removed += 1

    if removed:
        logger.info("Cleaned up %d expired test cache entries", removed)
    return removed


def make_entry(
    path: str,
    accessible: bool,
    file_count: int,
    photo_count: int,
    sidecar_count: int,
    tools_tested: list[str],
    agent_id: str,
    agent_version: str,
    issues_found: Optional[dict] = None,
) -> TestCacheEntry:
    """
    Create a new TestCacheEntry with computed fields.

    Convenience factory that fills in tested_at, expires_at, and path_hash
    automatically.

    Args:
        path: Absolute path that was tested
        accessible: Whether the path was accessible
        file_count: Total files found
        photo_count: Files matching photo extensions
        sidecar_count: Files matching metadata extensions
        tools_tested: List of tool names that were run
        agent_id: Agent GUID
        agent_version: Agent version string
        issues_found: Optional dict of issues per tool

    Returns:
        A fully populated TestCacheEntry
    """
    now = datetime.now(timezone.utc)
    return TestCacheEntry(
        path=_normalize_path(path),
        path_hash=_hash_path(path),
        tested_at=now,
        expires_at=now + timedelta(hours=TEST_CACHE_TTL_HOURS),
        accessible=accessible,
        file_count=file_count,
        photo_count=photo_count,
        sidecar_count=sidecar_count,
        tools_tested=tools_tested,
        issues_found=issues_found,
        agent_id=agent_id,
        agent_version=agent_version,
    )
