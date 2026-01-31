"""
Unit tests for the offline result store module.

Tests save/load/list_pending/mark_synced/delete operations for OfflineResult.

Issue #108 - Remove CLI Direct Usage
Task: T037
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cache import OfflineResult
from src.cache.result_store import (
    cleanup_synced,
    delete,
    list_all,
    list_pending,
    load,
    mark_synced,
    save,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_result() -> OfflineResult:
    """Create a sample offline result."""
    return OfflineResult(
        result_id="550e8400-e29b-41d4-a716-446655440001",
        collection_guid="col_01hgw2bbg0000000000000001",
        collection_name="Vacation 2024",
        tool="photostats",
        executed_at=datetime.now(timezone.utc),
        agent_guid="agt_test",
        agent_version="v1.0.0",
        analysis_data={
            "total_files": 5000,
            "orphaned_images": [],
            "results": {"total_files": 5000},
        },
    )


@pytest.fixture
def synced_result() -> OfflineResult:
    """Create a synced offline result."""
    return OfflineResult(
        result_id="550e8400-e29b-41d4-a716-446655440002",
        collection_guid="col_01hgw2bbg0000000000000001",
        collection_name="Vacation 2024",
        tool="photo_pairing",
        executed_at=datetime.now(timezone.utc),
        agent_guid="agt_test",
        agent_version="v1.0.0",
        analysis_data={"image_count": 100, "results": {"image_count": 100}},
        synced=True,
    )


@pytest.fixture
def results_dir(tmp_path, monkeypatch):
    """Redirect results to a temporary directory."""
    r_dir = tmp_path / "results"
    r_dir.mkdir()

    def mock_get_cache_paths():
        return {
            "data_dir": tmp_path,
            "test_cache_dir": tmp_path / "test-cache",
            "collection_cache_file": tmp_path / "collection-cache.json",
            "results_dir": r_dir,
        }

    monkeypatch.setattr("src.cache.result_store.get_cache_paths", mock_get_cache_paths)
    return r_dir


# ============================================================================
# Save/Load Tests
# ============================================================================


class TestSaveLoad:
    """Tests for save and load operations."""

    def test_save_creates_file(self, results_dir, sample_result):
        path = save(sample_result)
        assert path.exists()
        assert path.suffix == ".json"
        assert sample_result.result_id in path.name

    def test_save_load_roundtrip(self, results_dir, sample_result):
        save(sample_result)
        loaded = load(sample_result.result_id)
        assert loaded is not None
        assert loaded.result_id == sample_result.result_id
        assert loaded.collection_guid == sample_result.collection_guid
        assert loaded.tool == sample_result.tool
        assert loaded.synced is False

    def test_load_nonexistent_returns_none(self, results_dir):
        result = load("nonexistent-uuid")
        assert result is None

    def test_load_corrupted_file_returns_none(self, results_dir):
        """Corrupted JSON should return None."""
        bad_file = results_dir / "bad-uuid.json"
        bad_file.write_text("not valid json {{{")
        result = load("bad-uuid")
        assert result is None

    def test_saved_file_is_encrypted(self, results_dir, sample_result):
        """Saved file should not be readable as plaintext JSON."""
        path = save(sample_result)
        raw = path.read_bytes()
        # Encrypted Fernet tokens start with 'gAAAAA' (base64 prefix)
        # and are NOT valid JSON
        with pytest.raises(json.JSONDecodeError):
            json.loads(raw)

    def test_roundtrip_preserves_fields(self, results_dir, sample_result):
        save(sample_result)
        loaded = load(sample_result.result_id)
        assert loaded is not None
        assert loaded.result_id == sample_result.result_id
        assert loaded.tool == "photostats"
        assert loaded.synced is False


# ============================================================================
# List Tests
# ============================================================================


class TestListOperations:
    """Tests for list_all and list_pending."""

    def test_list_all_empty(self, results_dir):
        assert list_all() == []

    def test_list_all_returns_all(self, results_dir, sample_result, synced_result):
        save(sample_result)
        save(synced_result)
        all_results = list_all()
        assert len(all_results) == 2

    def test_list_pending_excludes_synced(self, results_dir, sample_result, synced_result):
        save(sample_result)
        save(synced_result)
        pending = list_pending()
        assert len(pending) == 1
        assert pending[0].result_id == sample_result.result_id

    def test_list_pending_empty_when_all_synced(self, results_dir, synced_result):
        save(synced_result)
        pending = list_pending()
        assert len(pending) == 0

    def test_list_skips_corrupted(self, results_dir, sample_result):
        save(sample_result)
        bad_file = results_dir / "bad-uuid.json"
        bad_file.write_text("not valid json")
        all_results = list_all()
        assert len(all_results) == 1  # Only the valid one


# ============================================================================
# Mark Synced Tests
# ============================================================================


class TestMarkSynced:
    """Tests for mark_synced operation."""

    def test_mark_synced_updates_flag(self, results_dir, sample_result):
        save(sample_result)
        assert mark_synced(sample_result.result_id) is True
        loaded = load(sample_result.result_id)
        assert loaded is not None
        assert loaded.synced is True

    def test_mark_synced_nonexistent_returns_false(self, results_dir):
        assert mark_synced("nonexistent-uuid") is False

    def test_mark_synced_removes_from_pending(self, results_dir, sample_result):
        save(sample_result)
        assert len(list_pending()) == 1
        mark_synced(sample_result.result_id)
        assert len(list_pending()) == 0


# ============================================================================
# Delete Tests
# ============================================================================


class TestDelete:
    """Tests for delete operation."""

    def test_delete_existing(self, results_dir, sample_result):
        save(sample_result)
        assert delete(sample_result.result_id) is True
        assert load(sample_result.result_id) is None

    def test_delete_nonexistent(self, results_dir):
        assert delete("nonexistent-uuid") is False


# ============================================================================
# Cleanup Tests
# ============================================================================


class TestCleanupSynced:
    """Tests for cleanup_synced operation."""

    def test_cleanup_removes_synced(self, results_dir, synced_result):
        save(synced_result)
        removed = cleanup_synced()
        assert removed == 1
        assert load(synced_result.result_id) is None

    def test_cleanup_keeps_pending(self, results_dir, sample_result):
        save(sample_result)
        removed = cleanup_synced()
        assert removed == 0
        assert load(sample_result.result_id) is not None

    def test_cleanup_mixed(self, results_dir, sample_result, synced_result):
        save(sample_result)
        save(synced_result)
        removed = cleanup_synced()
        assert removed == 1
        assert load(sample_result.result_id) is not None
        assert load(synced_result.result_id) is None
