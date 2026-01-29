"""
Offline result storage for analysis results pending upload.

Provides save/load/list_pending/mark_synced/delete operations for
OfflineResult objects, stored as JSON files at {data_dir}/results/{result_id}.json.

Results have no TTL — they persist until explicitly synced and deleted.

Issue #108 - Remove CLI Direct Usage
Task: T030
"""

import logging
from pathlib import Path
from typing import List, Optional

from src.cache import OfflineResult
from src.config import get_cache_paths

logger = logging.getLogger(__name__)


def _get_results_dir() -> Path:
    """Get the results directory, creating it if needed."""
    results_dir = get_cache_paths()["results_dir"]
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


def _result_file(result_id: str) -> Path:
    """Get the path for a specific result file."""
    return _get_results_dir() / f"{result_id}.json"


def save(result: OfflineResult) -> Path:
    """
    Save an offline result to disk.

    Args:
        result: OfflineResult to save

    Returns:
        Path to the saved result file

    Raises:
        OSError: If the file cannot be written
    """
    result_file = _result_file(result.result_id)
    result_file.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    logger.debug(
        "Saved offline result %s (tool=%s, collection=%s) -> %s",
        result.result_id,
        result.tool,
        result.collection_guid,
        result_file,
    )
    return result_file


def load(result_id: str) -> Optional[OfflineResult]:
    """
    Load an offline result from disk.

    Args:
        result_id: UUID of the result to load

    Returns:
        OfflineResult if found and parseable, None otherwise
    """
    result_file = _result_file(result_id)
    if not result_file.exists():
        return None

    try:
        raw = result_file.read_text(encoding="utf-8")
        return OfflineResult.model_validate_json(raw)
    except Exception as e:
        logger.warning("Failed to load offline result %s: %s", result_id, e)
        return None


def list_all() -> List[OfflineResult]:
    """
    List all offline results (both pending and synced).

    Returns:
        List of all OfflineResult objects found on disk
    """
    results_dir = _get_results_dir()
    results = []
    for result_file in sorted(results_dir.glob("*.json")):
        try:
            raw = result_file.read_text(encoding="utf-8")
            result = OfflineResult.model_validate_json(raw)
            results.append(result)
        except Exception as e:
            logger.warning("Skipping corrupted result file %s: %s", result_file, e)
    return results


def list_pending() -> List[OfflineResult]:
    """
    List all offline results that have not been synced.

    Returns:
        List of OfflineResult objects where synced=False
    """
    return [r for r in list_all() if not r.synced]


def mark_synced(result_id: str) -> bool:
    """
    Mark an offline result as synced (uploaded to server).

    Loads the result, sets synced=True, and saves it back.

    Args:
        result_id: UUID of the result to mark

    Returns:
        True if the result was found and updated, False otherwise
    """
    result = load(result_id)
    if result is None:
        return False

    result.synced = True
    save(result)
    logger.debug("Marked result %s as synced", result_id)
    return True


def delete(result_id: str) -> bool:
    """
    Delete an offline result file.

    Args:
        result_id: UUID of the result to delete

    Returns:
        True if a file was deleted, False if no file existed
    """
    result_file = _result_file(result_id)
    if result_file.exists():
        result_file.unlink()
        logger.debug("Deleted offline result %s", result_id)
        return True
    return False


def cleanup_synced() -> int:
    """
    Delete all synced result files.

    Returns:
        Number of files deleted
    """
    removed = 0
    for result in list_all():
        if result.synced:
            if delete(result.result_id):
                removed += 1
    return removed
