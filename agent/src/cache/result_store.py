"""
Offline result storage for analysis results pending upload.

Provides save/load/list_pending/mark_synced/delete operations for
OfflineResult objects, stored as encrypted files at
{data_dir}/results/{result_id}.json.

Results are encrypted at rest using Fernet symmetric encryption.
The encryption key is shared with the credential store
(~/.shuttersense-agent/master.key) and auto-generated on first use.

Results have no TTL — they persist until explicitly synced and deleted.

Issue #108 - Remove CLI Direct Usage
Task: T030
"""

import logging
import os
from pathlib import Path
from typing import List, Optional

from cryptography.fernet import Fernet

from src.cache import OfflineResult
from src.config import get_cache_paths

logger = logging.getLogger(__name__)

# Master key lives alongside the credential store
_AGENT_DIR = Path.home() / ".shuttersense-agent"
_MASTER_KEY_FILE = _AGENT_DIR / "master.key"
_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """Get or create the Fernet cipher, reusing the credential store's master key."""
    global _fernet
    if _fernet is not None:
        return _fernet

    _AGENT_DIR.mkdir(parents=True, exist_ok=True)

    if _MASTER_KEY_FILE.exists():
        key = _MASTER_KEY_FILE.read_bytes()
    else:
        key = Fernet.generate_key()
        _MASTER_KEY_FILE.write_bytes(key)
        try:
            os.chmod(_MASTER_KEY_FILE, 0o600)
        except OSError:
            pass

    try:
        os.chmod(_AGENT_DIR, 0o700)
    except OSError:
        pass

    _fernet = Fernet(key)
    return _fernet


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
    Save an offline result to disk (encrypted).

    Args:
        result: OfflineResult to save

    Returns:
        Path to the saved result file

    Raises:
        OSError: If the file cannot be written
    """
    fernet = _get_fernet()
    result_file = _result_file(result.result_id)
    encrypted = fernet.encrypt(result.model_dump_json(indent=2).encode("utf-8"))
    result_file.write_bytes(encrypted)
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
    Load an offline result from disk (decrypting).

    Args:
        result_id: UUID of the result to load

    Returns:
        OfflineResult if found and parseable, None otherwise
    """
    result_file = _result_file(result_id)
    if not result_file.exists():
        return None

    try:
        encrypted = result_file.read_bytes()
        fernet = _get_fernet()
        raw = fernet.decrypt(encrypted).decode("utf-8")
        return OfflineResult.model_validate_json(raw)
    except Exception as e:
        # Try reading as plaintext for backwards compatibility with
        # results saved before encryption was added.
        try:
            raw = result_file.read_text(encoding="utf-8")
            return OfflineResult.model_validate_json(raw)
        except Exception:
            pass
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
        result_id = result_file.stem
        loaded = load(result_id)
        if loaded:
            results.append(loaded)
        else:
            logger.warning("Skipping unreadable result file %s", result_file)
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
