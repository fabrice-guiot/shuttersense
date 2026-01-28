"""
Unit tests for the test cache module.

Tests save/load/is_valid/cleanup operations for TestCacheEntry objects.

Issue #108 - Remove CLI Direct Usage
Task: T011
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cache import TEST_CACHE_TTL_HOURS, TestCacheEntry
from src.cache.test_cache import (
    _hash_path,
    _normalize_path,
    cleanup,
    delete,
    load,
    load_valid,
    make_entry,
    save,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_entry() -> TestCacheEntry:
    """Create a valid, non-expired test cache entry."""
    now = datetime.now(timezone.utc)
    return TestCacheEntry(
        path="/tmp/test-photos",
        path_hash=_hash_path("/tmp/test-photos"),
        tested_at=now,
        expires_at=now + timedelta(hours=TEST_CACHE_TTL_HOURS),
        accessible=True,
        file_count=100,
        photo_count=80,
        sidecar_count=15,
        tools_tested=["photostats"],
        issues_found=None,
        agent_id="agt_test",
        agent_version="v1.0.0",
    )


@pytest.fixture
def expired_entry() -> TestCacheEntry:
    """Create an expired test cache entry."""
    past = datetime(2020, 1, 1, tzinfo=timezone.utc)
    return TestCacheEntry(
        path="/tmp/old-photos",
        path_hash=_hash_path("/tmp/old-photos"),
        tested_at=past,
        expires_at=past + timedelta(hours=TEST_CACHE_TTL_HOURS),
        accessible=True,
        file_count=50,
        photo_count=40,
        sidecar_count=5,
        tools_tested=[],
        agent_id="agt_test",
        agent_version="v1.0.0",
    )


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    """Redirect cache to a temporary directory."""
    cache_dir = tmp_path / "test-cache"
    cache_dir.mkdir()

    def mock_get_cache_paths():
        return {
            "data_dir": tmp_path,
            "test_cache_dir": cache_dir,
            "collection_cache_file": tmp_path / "collection-cache.json",
            "results_dir": tmp_path / "results",
        }

    monkeypatch.setattr("src.cache.test_cache.get_cache_paths", mock_get_cache_paths)
    return cache_dir


# ============================================================================
# Helper Function Tests
# ============================================================================


class TestNormalizePath:
    """Tests for _normalize_path."""

    def test_already_absolute(self):
        result = _normalize_path("/tmp/photos")
        assert result.startswith("/")

    def test_trailing_slash_removed(self):
        result = _normalize_path("/tmp/photos/")
        assert not result.endswith("/") or result == "/"

    def test_consistent_hashing(self):
        """Same logical path should produce same hash."""
        assert _hash_path("/tmp/photos") == _hash_path("/tmp/photos")

    def test_different_paths_different_hashes(self):
        assert _hash_path("/tmp/photos") != _hash_path("/tmp/other")


# ============================================================================
# Save/Load Tests
# ============================================================================


class TestSaveLoad:
    """Tests for save and load operations."""

    def test_save_creates_file(self, cache_dir, sample_entry):
        path = save(sample_entry)
        assert path.exists()
        assert path.suffix == ".json"

    def test_save_load_roundtrip(self, cache_dir, sample_entry):
        save(sample_entry)
        loaded = load(sample_entry.path)
        assert loaded is not None
        assert loaded.path == sample_entry.path
        assert loaded.file_count == sample_entry.file_count
        assert loaded.photo_count == sample_entry.photo_count
        assert loaded.sidecar_count == sample_entry.sidecar_count
        assert loaded.accessible == sample_entry.accessible
        assert loaded.tools_tested == sample_entry.tools_tested

    def test_load_nonexistent_returns_none(self, cache_dir):
        result = load("/nonexistent/path")
        assert result is None

    def test_load_corrupted_file_returns_none(self, cache_dir):
        """Corrupted JSON should return None, not raise."""
        hash_val = _hash_path("/tmp/corrupted")
        cache_file = cache_dir / f"{hash_val}.json"
        cache_file.write_text("not valid json {{{")
        result = load("/tmp/corrupted")
        assert result is None

    def test_save_overwrites_existing(self, cache_dir, sample_entry):
        save(sample_entry)
        # Modify and save again
        modified = sample_entry.model_copy(update={"file_count": 999})
        save(modified)
        loaded = load(sample_entry.path)
        assert loaded is not None
        assert loaded.file_count == 999

    def test_saved_json_is_valid(self, cache_dir, sample_entry):
        """Verify the saved file is valid JSON."""
        path = save(sample_entry)
        data = json.loads(path.read_text())
        assert data["path"] == sample_entry.path
        assert data["file_count"] == sample_entry.file_count


# ============================================================================
# Load Valid Tests (TTL checking)
# ============================================================================


class TestLoadValid:
    """Tests for load_valid (TTL-aware loading)."""

    def test_valid_entry_returned(self, cache_dir, sample_entry):
        save(sample_entry)
        result = load_valid(sample_entry.path)
        assert result is not None
        assert result.path == sample_entry.path

    def test_expired_entry_returns_none(self, cache_dir, expired_entry):
        save(expired_entry)
        result = load_valid(expired_entry.path)
        assert result is None

    def test_nonexistent_returns_none(self, cache_dir):
        result = load_valid("/nonexistent/path")
        assert result is None


# ============================================================================
# Delete Tests
# ============================================================================


class TestDelete:
    """Tests for delete operation."""

    def test_delete_existing(self, cache_dir, sample_entry):
        save(sample_entry)
        assert delete(sample_entry.path) is True
        assert load(sample_entry.path) is None

    def test_delete_nonexistent(self, cache_dir):
        assert delete("/nonexistent/path") is False


# ============================================================================
# Cleanup Tests
# ============================================================================


class TestCleanup:
    """Tests for cleanup of expired entries."""

    def test_cleanup_removes_expired(self, cache_dir, expired_entry):
        save(expired_entry)
        removed = cleanup()
        assert removed == 1
        assert load(expired_entry.path) is None

    def test_cleanup_keeps_valid(self, cache_dir, sample_entry):
        save(sample_entry)
        removed = cleanup()
        assert removed == 0
        assert load(sample_entry.path) is not None

    def test_cleanup_mixed(self, cache_dir, sample_entry, expired_entry):
        save(sample_entry)
        save(expired_entry)
        removed = cleanup()
        assert removed == 1
        assert load(sample_entry.path) is not None
        assert load(expired_entry.path) is None

    def test_cleanup_removes_corrupted(self, cache_dir):
        """Corrupted files should be removed during cleanup."""
        bad_file = cache_dir / "bad_hash.json"
        bad_file.write_text("not valid json")
        removed = cleanup()
        assert removed == 1
        assert not bad_file.exists()

    def test_cleanup_empty_dir(self, cache_dir):
        removed = cleanup()
        assert removed == 0


# ============================================================================
# Make Entry Tests
# ============================================================================


class TestMakeEntry:
    """Tests for the make_entry convenience factory."""

    def test_creates_valid_entry(self):
        entry = make_entry(
            path="/tmp/photos",
            accessible=True,
            file_count=100,
            photo_count=80,
            sidecar_count=15,
            tools_tested=["photostats"],
            agent_id="agt_test",
            agent_version="v1.0.0",
        )
        assert entry.path == _normalize_path("/tmp/photos")
        assert entry.path_hash == _hash_path("/tmp/photos")
        assert entry.accessible is True
        assert entry.file_count == 100
        assert entry.is_valid()

    def test_expires_at_auto_computed(self):
        entry = make_entry(
            path="/tmp/photos",
            accessible=True,
            file_count=0,
            photo_count=0,
            sidecar_count=0,
            tools_tested=[],
            agent_id="agt_test",
            agent_version="v1.0.0",
        )
        expected_delta = timedelta(hours=TEST_CACHE_TTL_HOURS)
        actual_delta = entry.expires_at - entry.tested_at
        assert abs((actual_delta - expected_delta).total_seconds()) < 1

    def test_with_issues(self):
        entry = make_entry(
            path="/tmp/photos",
            accessible=True,
            file_count=100,
            photo_count=80,
            sidecar_count=15,
            tools_tested=["photostats"],
            agent_id="agt_test",
            agent_version="v1.0.0",
            issues_found={"photostats": {"orphaned": 3}},
        )
        assert entry.issues_found == {"photostats": {"orphaned": 3}}
