"""
Unit tests for the collection cache module.

Tests save/load/load_valid/delete/make_cache operations for CollectionCache.

Issue #108 - Remove CLI Direct Usage
Task: T028
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cache import COLLECTION_CACHE_TTL_DAYS, CachedCollection, CollectionCache
from src.cache.collection_cache import (
    delete,
    load,
    load_valid,
    make_cache,
    save,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_collection() -> CachedCollection:
    """A sample LOCAL collection."""
    return CachedCollection(
        guid="col_01hgw2bbg0000000000000001",
        name="Vacation 2024",
        type="LOCAL",
        location="/photos/2024",
        bound_agent_guid="agt_01hgw2bbg0000000000000001",
        connector_guid=None,
        connector_name=None,
        is_accessible=True,
        last_analysis_at=None,
        supports_offline=True,
    )


@pytest.fixture
def sample_cache(sample_collection) -> CollectionCache:
    """A valid, non-expired collection cache."""
    now = datetime.now(timezone.utc)
    return CollectionCache(
        agent_guid="agt_01hgw2bbg0000000000000001",
        synced_at=now,
        expires_at=now + timedelta(days=COLLECTION_CACHE_TTL_DAYS),
        collections=[sample_collection],
    )


@pytest.fixture
def expired_cache(sample_collection) -> CollectionCache:
    """An expired collection cache."""
    past = datetime(2020, 1, 1, tzinfo=timezone.utc)
    return CollectionCache(
        agent_guid="agt_01hgw2bbg0000000000000001",
        synced_at=past,
        expires_at=past + timedelta(days=COLLECTION_CACHE_TTL_DAYS),
        collections=[sample_collection],
    )


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    """Redirect cache to a temporary directory."""
    cache_file = tmp_path / "collection-cache.json"

    def mock_get_cache_paths():
        return {
            "data_dir": tmp_path,
            "test_cache_dir": tmp_path / "test-cache",
            "collection_cache_file": cache_file,
            "results_dir": tmp_path / "results",
        }

    monkeypatch.setattr("src.cache.collection_cache.get_cache_paths", mock_get_cache_paths)
    return tmp_path


# ============================================================================
# Save/Load Tests
# ============================================================================


class TestSaveLoad:
    """Tests for save and load operations."""

    def test_save_creates_file(self, cache_dir, sample_cache):
        path = save(sample_cache)
        assert path.exists()
        assert path.name == "collection-cache.json"

    def test_save_load_roundtrip(self, cache_dir, sample_cache):
        save(sample_cache)
        loaded = load()
        assert loaded is not None
        assert loaded.agent_guid == sample_cache.agent_guid
        assert len(loaded.collections) == 1
        assert loaded.collections[0].guid == "col_01hgw2bbg0000000000000001"
        assert loaded.collections[0].name == "Vacation 2024"
        assert loaded.collections[0].type == "LOCAL"

    def test_load_nonexistent_returns_none(self, cache_dir):
        result = load()
        assert result is None

    def test_load_corrupted_file_returns_none(self, cache_dir):
        """Corrupted JSON should return None, not raise."""
        cache_file = cache_dir / "collection-cache.json"
        cache_file.write_text("not valid json {{{")
        result = load()
        assert result is None

    def test_save_overwrites_existing(self, cache_dir, sample_cache, sample_collection):
        save(sample_cache)
        # Create a new cache with two collections
        second = CachedCollection(
            guid="col_01hgw2bbg0000000000000002",
            name="Wedding 2024",
            type="LOCAL",
            location="/photos/wedding",
            bound_agent_guid="agt_01hgw2bbg0000000000000001",
            is_accessible=True,
            supports_offline=True,
        )
        now = datetime.now(timezone.utc)
        new_cache = CollectionCache(
            agent_guid="agt_01hgw2bbg0000000000000001",
            synced_at=now,
            expires_at=now + timedelta(days=COLLECTION_CACHE_TTL_DAYS),
            collections=[sample_collection, second],
        )
        save(new_cache)
        loaded = load()
        assert loaded is not None
        assert len(loaded.collections) == 2

    def test_saved_json_is_valid(self, cache_dir, sample_cache):
        """Verify the saved file is valid JSON."""
        path = save(sample_cache)
        data = json.loads(path.read_text())
        assert data["agent_guid"] == sample_cache.agent_guid
        assert len(data["collections"]) == 1


# ============================================================================
# Load Valid Tests (TTL checking)
# ============================================================================


class TestLoadValid:
    """Tests for load_valid (TTL-aware loading)."""

    def test_valid_cache_returned(self, cache_dir, sample_cache):
        save(sample_cache)
        result = load_valid()
        assert result is not None
        assert result.agent_guid == sample_cache.agent_guid

    def test_expired_cache_returns_none(self, cache_dir, expired_cache):
        save(expired_cache)
        result = load_valid()
        assert result is None

    def test_nonexistent_returns_none(self, cache_dir):
        result = load_valid()
        assert result is None


# ============================================================================
# Delete Tests
# ============================================================================


class TestDelete:
    """Tests for delete operation."""

    def test_delete_existing(self, cache_dir, sample_cache):
        save(sample_cache)
        assert delete() is True
        assert load() is None

    def test_delete_nonexistent(self, cache_dir):
        assert delete() is False


# ============================================================================
# Make Cache Tests
# ============================================================================


class TestMakeCache:
    """Tests for the make_cache convenience factory."""

    def test_creates_valid_cache(self, sample_collection):
        cache = make_cache(
            agent_guid="agt_test",
            collections=[sample_collection],
        )
        assert cache.agent_guid == "agt_test"
        assert len(cache.collections) == 1
        assert cache.is_valid()

    def test_expires_at_auto_computed(self, sample_collection):
        cache = make_cache(
            agent_guid="agt_test",
            collections=[sample_collection],
        )
        expected_delta = timedelta(days=COLLECTION_CACHE_TTL_DAYS)
        actual_delta = cache.expires_at - cache.synced_at
        assert abs((actual_delta - expected_delta).total_seconds()) < 1

    def test_empty_collections(self):
        cache = make_cache(
            agent_guid="agt_test",
            collections=[],
        )
        assert len(cache.collections) == 0
        assert cache.is_valid()


# ============================================================================
# Is Valid / Is Expired Tests
# ============================================================================


class TestCacheValidity:
    """Tests for is_valid and is_expired methods."""

    def test_fresh_cache_is_valid(self, sample_cache):
        assert sample_cache.is_valid() is True
        assert sample_cache.is_expired() is False

    def test_expired_cache_is_invalid(self, expired_cache):
        assert expired_cache.is_valid() is False
        assert expired_cache.is_expired() is True
