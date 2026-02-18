"""
Unit tests for version cache module.

Tests caching of outdated status from heartbeat responses,
TTL expiration, and corrupt/missing cache handling.

Issue #243 - Agent CLI self-update command & outdated warnings
"""

import json
import time

import pytest

from src.version_cache import (
    CACHE_TTL_SECONDS,
    read_cached_version_state,
    write_version_cache,
)


class TestVersionCache:
    """Tests for version_cache read/write operations."""

    @pytest.fixture(autouse=True)
    def patch_cache_path(self, tmp_path, monkeypatch):
        """Route all cache operations to a temp directory."""
        cache_file = tmp_path / "version-state.json"
        monkeypatch.setattr(
            "src.version_cache._get_cache_path",
            lambda: cache_file,
        )
        self.cache_file = cache_file

    def test_read_returns_none_when_no_cache(self):
        """Returns None when cache file doesn't exist."""
        assert read_cached_version_state() is None

    def test_write_then_read(self):
        """Written cache can be read back."""
        write_version_cache(is_outdated=True, latest_version="v2.0.0")
        state = read_cached_version_state()

        assert state is not None
        assert state["is_outdated"] is True
        assert state["latest_version"] == "v2.0.0"
        assert "cached_at" in state

    def test_write_not_outdated(self):
        """Cache correctly stores is_outdated=False."""
        write_version_cache(is_outdated=False, latest_version=None)
        state = read_cached_version_state()

        assert state is not None
        assert state["is_outdated"] is False
        assert state["latest_version"] is None

    def test_expired_cache_returns_none(self):
        """Returns None when cache has expired past TTL."""
        write_version_cache(is_outdated=True, latest_version="v2.0.0")

        # Manually backdate the cached_at timestamp
        data = json.loads(self.cache_file.read_text())
        data["cached_at"] = time.time() - CACHE_TTL_SECONDS - 1
        self.cache_file.write_text(json.dumps(data))

        assert read_cached_version_state() is None

    def test_fresh_cache_not_expired(self):
        """Returns data when cache is within TTL."""
        write_version_cache(is_outdated=True, latest_version="v2.0.0")

        # Backdate to just within TTL
        data = json.loads(self.cache_file.read_text())
        data["cached_at"] = time.time() - CACHE_TTL_SECONDS + 60
        self.cache_file.write_text(json.dumps(data))

        state = read_cached_version_state()
        assert state is not None
        assert state["is_outdated"] is True

    def test_corrupt_json_returns_none(self):
        """Returns None when cache file contains invalid JSON."""
        self.cache_file.write_text("not valid json{{{")
        assert read_cached_version_state() is None

    def test_overwrite_cache(self):
        """Writing cache a second time overwrites the previous value."""
        write_version_cache(is_outdated=True, latest_version="v1.0.0")
        write_version_cache(is_outdated=False, latest_version="v2.0.0")

        state = read_cached_version_state()
        assert state["is_outdated"] is False
        assert state["latest_version"] == "v2.0.0"
