"""
Unit tests for file listing cache.

Tests the FileListingCache and CachedFileListing for:
- Caching file listings with TTL
- Cache hit/miss/expiry behavior
- Manual invalidation
- Thread safety
- Collection state-aware TTL
- Cache statistics

Task: T104b - Unit tests for cache module
"""

import time
import threading
from datetime import datetime, timedelta
import pytest
from freezegun import freeze_time

from backend.src.utils.cache import (
    CachedFileListing,
    FileListingCache,
    COLLECTION_STATE_TTL,
    get_ttl_for_state,
    get_file_listing_cache,
    init_file_listing_cache
)


class TestCachedFileListing:
    """Tests for CachedFileListing dataclass."""

    def test_create_cached_listing(self):
        """Test creating a CachedFileListing instance."""
        files = ['photo1.dng', 'photo2.dng', 'photo3.dng']
        cached_at = datetime.utcnow()
        ttl_seconds = 3600

        cached = CachedFileListing(
            files=files,
            cached_at=cached_at,
            ttl_seconds=ttl_seconds
        )

        assert cached.files == files
        assert cached.cached_at == cached_at
        assert cached.ttl_seconds == ttl_seconds

    def test_is_expired_not_expired(self):
        """Test is_expired returns False for non-expired cache."""
        cached = CachedFileListing(
            files=['photo1.dng'],
            cached_at=datetime.utcnow(),
            ttl_seconds=3600
        )

        assert not cached.is_expired()

    @freeze_time("2025-01-01 12:00:00")
    def test_is_expired_after_ttl(self):
        """Test is_expired returns True after TTL has passed."""
        # Create cache entry at noon
        cached = CachedFileListing(
            files=['photo1.dng'],
            cached_at=datetime.utcnow(),
            ttl_seconds=3600  # 1 hour
        )

        # Immediately after creation - not expired
        assert not cached.is_expired()

        # Move time forward by 1 hour + 1 second
        with freeze_time("2025-01-01 13:00:01"):
            assert cached.is_expired()

    def test_time_until_expiry_positive(self):
        """Test time_until_expiry returns positive timedelta for valid cache."""
        cached = CachedFileListing(
            files=['photo1.dng'],
            cached_at=datetime.utcnow(),
            ttl_seconds=3600
        )

        time_until = cached.time_until_expiry()

        # Should be approximately 3600 seconds (allow small variance for test execution time)
        assert 3595 < time_until.total_seconds() <= 3600

    @freeze_time("2025-01-01 12:00:00")
    def test_time_until_expiry_negative(self):
        """Test time_until_expiry returns negative timedelta for expired cache."""
        # Create cache entry at noon with 1 hour TTL
        cached = CachedFileListing(
            files=['photo1.dng'],
            cached_at=datetime.utcnow(),
            ttl_seconds=3600
        )

        # Move time forward by 2 hours
        with freeze_time("2025-01-01 14:00:00"):
            time_until = cached.time_until_expiry()
            # Should be -3600 seconds (1 hour past expiry)
            assert time_until.total_seconds() == -3600


class TestFileListingCacheBasics:
    """Tests for basic FileListingCache operations."""

    def test_init_empty_cache(self):
        """Test initializing an empty cache."""
        cache = FileListingCache()

        assert cache.get_stats() == {'entries': 0, 'total_files': 0}

    def test_set_and_get_cache_hit(self):
        """Test setting and getting a cached file listing."""
        cache = FileListingCache()
        collection_id = 1
        files = ['photo1.dng', 'photo2.dng', 'photo3.dng']

        cache.set(collection_id=collection_id, files=files, ttl_seconds=3600)
        cached_files = cache.get(collection_id=collection_id)

        assert cached_files == files

    def test_get_cache_miss(self):
        """Test getting a non-existent cache entry returns None."""
        cache = FileListingCache()

        cached_files = cache.get(collection_id=999)

        assert cached_files is None

    def test_set_overwrites_existing_entry(self):
        """Test setting a cache entry twice overwrites the first entry."""
        cache = FileListingCache()
        collection_id = 1

        # Set initial files
        cache.set(collection_id=collection_id, files=['photo1.dng'], ttl_seconds=3600)

        # Overwrite with new files
        new_files = ['photo2.dng', 'photo3.dng']
        cache.set(collection_id=collection_id, files=new_files, ttl_seconds=3600)

        cached_files = cache.get(collection_id=collection_id)
        assert cached_files == new_files

    def test_multiple_collections_cached(self):
        """Test caching multiple collections independently."""
        cache = FileListingCache()

        cache.set(collection_id=1, files=['collection1_file1.dng'], ttl_seconds=3600)
        cache.set(collection_id=2, files=['collection2_file1.dng', 'collection2_file2.dng'], ttl_seconds=3600)
        cache.set(collection_id=3, files=['collection3_file1.dng'], ttl_seconds=3600)

        assert cache.get(collection_id=1) == ['collection1_file1.dng']
        assert cache.get(collection_id=2) == ['collection2_file1.dng', 'collection2_file2.dng']
        assert cache.get(collection_id=3) == ['collection3_file1.dng']


class TestCacheExpiry:
    """Tests for cache expiry behavior."""

    @freeze_time("2025-01-01 12:00:00")
    def test_get_expired_entry_returns_none(self):
        """Test that getting an expired entry returns None and removes it."""
        cache = FileListingCache()
        collection_id = 1

        # Set cache at noon with 1 hour TTL
        cache.set(collection_id=collection_id, files=['photo1.dng'], ttl_seconds=3600)

        # Verify it's cached
        assert cache.get(collection_id=collection_id) == ['photo1.dng']
        assert cache.get_stats()['entries'] == 1

        # Move time forward past expiry
        with freeze_time("2025-01-01 13:00:01"):
            cached_files = cache.get(collection_id=collection_id)

            # Should return None
            assert cached_files is None

            # Entry should be removed from cache
            assert cache.get_stats()['entries'] == 0

    @freeze_time("2025-01-01 12:00:00")
    def test_different_ttl_per_collection(self):
        """Test that different collections can have different TTLs."""
        cache = FileListingCache()

        # Collection 1: 1 hour TTL (Live)
        cache.set(collection_id=1, files=['live_photo.dng'], ttl_seconds=3600)

        # Collection 2: 24 hours TTL (Closed)
        cache.set(collection_id=2, files=['closed_photo.dng'], ttl_seconds=86400)

        # After 2 hours, collection 1 expired but collection 2 still valid
        with freeze_time("2025-01-01 14:00:00"):
            assert cache.get(collection_id=1) is None  # Expired
            assert cache.get(collection_id=2) == ['closed_photo.dng']  # Still valid


class TestCacheInvalidation:
    """Tests for manual cache invalidation."""

    def test_invalidate_existing_entry(self):
        """Test invalidating a cached entry."""
        cache = FileListingCache()
        collection_id = 1

        cache.set(collection_id=collection_id, files=['photo1.dng'], ttl_seconds=3600)
        assert cache.get(collection_id=collection_id) is not None

        cache.invalidate(collection_id=collection_id)

        assert cache.get(collection_id=collection_id) is None
        assert cache.get_stats()['entries'] == 0

    def test_invalidate_non_existent_entry(self):
        """Test invalidating a non-existent entry doesn't raise error."""
        cache = FileListingCache()

        # Should not raise error
        cache.invalidate(collection_id=999)

        assert cache.get_stats()['entries'] == 0

    def test_clear_all_entries(self):
        """Test clearing entire cache."""
        cache = FileListingCache()

        # Add multiple entries
        cache.set(collection_id=1, files=['photo1.dng'], ttl_seconds=3600)
        cache.set(collection_id=2, files=['photo2.dng'], ttl_seconds=3600)
        cache.set(collection_id=3, files=['photo3.dng'], ttl_seconds=3600)

        assert cache.get_stats()['entries'] == 3

        cache.clear()

        assert cache.get_stats()['entries'] == 0
        assert cache.get(collection_id=1) is None
        assert cache.get(collection_id=2) is None
        assert cache.get(collection_id=3) is None


class TestCacheStatistics:
    """Tests for cache statistics and monitoring."""

    def test_get_stats_empty_cache(self):
        """Test statistics for empty cache."""
        cache = FileListingCache()

        stats = cache.get_stats()

        assert stats == {'entries': 0, 'total_files': 0}

    def test_get_stats_with_entries(self):
        """Test statistics with cached entries."""
        cache = FileListingCache()

        cache.set(collection_id=1, files=['photo1.dng', 'photo2.dng'], ttl_seconds=3600)
        cache.set(collection_id=2, files=['photo3.dng', 'photo4.dng', 'photo5.dng'], ttl_seconds=3600)

        stats = cache.get_stats()

        assert stats['entries'] == 2
        assert stats['total_files'] == 5

    def test_get_entry_info_exists(self):
        """Test getting detailed info about a cache entry."""
        cache = FileListingCache()

        with freeze_time("2025-01-01 12:00:00"):
            files = ['photo1.dng', 'photo2.dng', 'photo3.dng']
            cache.set(collection_id=1, files=files, ttl_seconds=3600)

            info = cache.get_entry_info(collection_id=1)

            assert info is not None
            assert info['file_count'] == 3
            assert info['cached_at'] == '2025-01-01T12:00:00'
            assert info['ttl_seconds'] == 3600
            assert 3595 < info['expires_in_seconds'] <= 3600
            assert info['is_expired'] is False

    def test_get_entry_info_not_exists(self):
        """Test getting info for non-existent entry returns None."""
        cache = FileListingCache()

        info = cache.get_entry_info(collection_id=999)

        assert info is None

    @freeze_time("2025-01-01 12:00:00")
    def test_get_entry_info_expired(self):
        """Test entry info shows expired status correctly."""
        cache = FileListingCache()

        cache.set(collection_id=1, files=['photo1.dng'], ttl_seconds=3600)

        # Move time forward past expiry
        with freeze_time("2025-01-01 13:00:01"):
            info = cache.get_entry_info(collection_id=1)

            assert info is not None
            assert info['is_expired'] is True
            assert info['expires_in_seconds'] < 0


class TestThreadSafety:
    """Tests for thread-safe concurrent access."""

    def test_concurrent_set_and_get(self):
        """Test concurrent set and get operations are thread-safe."""
        cache = FileListingCache()
        num_threads = 10
        num_operations = 100

        def worker(thread_id):
            for i in range(num_operations):
                collection_id = thread_id
                files = [f'thread{thread_id}_file{i}.dng']
                cache.set(collection_id=collection_id, files=files, ttl_seconds=3600)
                cached_files = cache.get(collection_id=collection_id)
                # Should always get back what we just set
                assert cached_files is not None

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should have one entry per thread
        assert cache.get_stats()['entries'] == num_threads

    def test_concurrent_invalidate(self):
        """Test concurrent invalidation is thread-safe."""
        cache = FileListingCache()

        # Pre-populate cache
        for i in range(100):
            cache.set(collection_id=i, files=[f'file{i}.dng'], ttl_seconds=3600)

        def worker(collection_ids):
            for cid in collection_ids:
                cache.invalidate(collection_id=cid)

        # Split collection IDs across threads
        num_threads = 10
        ids_per_thread = 10
        threads = []

        for i in range(num_threads):
            start_id = i * ids_per_thread
            end_id = start_id + ids_per_thread
            ids = list(range(start_id, end_id))
            t = threading.Thread(target=worker, args=(ids,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All entries should be invalidated
        assert cache.get_stats()['entries'] == 0


class TestCollectionStateTTL:
    """Tests for collection state-aware TTL."""

    def test_collection_state_ttl_constants(self):
        """Test TTL constants for different collection states."""
        assert COLLECTION_STATE_TTL['Live'] == 3600        # 1 hour
        assert COLLECTION_STATE_TTL['Closed'] == 86400     # 24 hours
        assert COLLECTION_STATE_TTL['Archived'] == 604800  # 7 days

    def test_get_ttl_for_state_live(self):
        """Test getting TTL for Live collection."""
        ttl = get_ttl_for_state('Live')
        assert ttl == 3600

    def test_get_ttl_for_state_closed(self):
        """Test getting TTL for Closed collection."""
        ttl = get_ttl_for_state('Closed')
        assert ttl == 86400

    def test_get_ttl_for_state_archived(self):
        """Test getting TTL for Archived collection."""
        ttl = get_ttl_for_state('Archived')
        assert ttl == 604800

    def test_get_ttl_for_state_unknown(self):
        """Test getting TTL for unknown state defaults to Live."""
        ttl = get_ttl_for_state('Unknown')
        assert ttl == 3600  # Defaults to Live

    def test_get_ttl_for_state_custom_override(self):
        """Test custom TTL overrides state-based TTL."""
        custom_ttl = 7200  # 2 hours
        ttl = get_ttl_for_state('Live', custom_ttl=custom_ttl)
        assert ttl == custom_ttl

    def test_get_ttl_for_state_custom_none(self):
        """Test custom TTL of None uses state-based TTL."""
        ttl = get_ttl_for_state('Closed', custom_ttl=None)
        assert ttl == 86400


class TestSingletonPattern:
    """Tests for singleton cache instance."""

    def test_get_file_listing_cache_returns_instance(self):
        """Test get_file_listing_cache returns a FileListingCache."""
        cache = get_file_listing_cache()

        assert isinstance(cache, FileListingCache)

    def test_get_file_listing_cache_returns_same_instance(self):
        """Test get_file_listing_cache returns the same singleton instance."""
        cache1 = get_file_listing_cache()
        cache2 = get_file_listing_cache()

        assert cache1 is cache2

    def test_init_file_listing_cache_creates_instance(self):
        """Test init_file_listing_cache creates and returns instance."""
        cache = init_file_listing_cache()

        assert isinstance(cache, FileListingCache)

    def test_singleton_preserves_data_across_calls(self):
        """Test singleton preserves cached data across multiple get calls."""
        cache1 = get_file_listing_cache()
        cache1.set(collection_id=1, files=['photo1.dng'], ttl_seconds=3600)

        cache2 = get_file_listing_cache()
        cached_files = cache2.get(collection_id=1)

        assert cached_files == ['photo1.dng']


class TestCacheLargeDatasets:
    """Tests for caching large file listings."""

    def test_cache_large_file_list(self):
        """Test caching a large file listing (10,000+ files)."""
        cache = FileListingCache()
        collection_id = 1

        # Generate large file list
        large_file_list = [f'photo{i:05d}.dng' for i in range(10000)]

        cache.set(collection_id=collection_id, files=large_file_list, ttl_seconds=3600)
        cached_files = cache.get(collection_id=collection_id)

        assert len(cached_files) == 10000
        assert cached_files == large_file_list

    def test_cache_stats_with_large_datasets(self):
        """Test statistics calculation with large datasets."""
        cache = FileListingCache()

        # Cache 5 collections with 10,000 files each
        for i in range(5):
            files = [f'collection{i}_photo{j:05d}.dng' for j in range(10000)]
            cache.set(collection_id=i, files=files, ttl_seconds=3600)

        stats = cache.get_stats()

        assert stats['entries'] == 5
        assert stats['total_files'] == 50000


class TestCacheEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_cache_empty_file_list(self):
        """Test caching an empty file list."""
        cache = FileListingCache()

        cache.set(collection_id=1, files=[], ttl_seconds=3600)
        cached_files = cache.get(collection_id=1)

        assert cached_files == []

    def test_cache_zero_ttl(self):
        """Test caching with zero TTL expires immediately."""
        cache = FileListingCache()

        with freeze_time("2025-01-01 12:00:00"):
            cache.set(collection_id=1, files=['photo1.dng'], ttl_seconds=0)

            # Even at the exact same time, TTL of 0 means expired
            with freeze_time("2025-01-01 12:00:00.000001"):
                cached_files = cache.get(collection_id=1)
                # Should be expired and return None
                assert cached_files is None

    def test_cache_very_long_ttl(self):
        """Test caching with very long TTL (years)."""
        cache = FileListingCache()

        # Set TTL to 1 year
        ttl_one_year = 365 * 24 * 3600
        cache.set(collection_id=1, files=['photo1.dng'], ttl_seconds=ttl_one_year)

        cached_files = cache.get(collection_id=1)
        assert cached_files == ['photo1.dng']

        info = cache.get_entry_info(collection_id=1)
        assert info['ttl_seconds'] == ttl_one_year
        assert info['expires_in_seconds'] > 365 * 24 * 3600 - 10  # Allow small variance

    def test_cache_collection_id_zero(self):
        """Test caching with collection_id of 0."""
        cache = FileListingCache()

        cache.set(collection_id=0, files=['photo1.dng'], ttl_seconds=3600)
        cached_files = cache.get(collection_id=0)

        assert cached_files == ['photo1.dng']

    def test_cache_negative_collection_id(self):
        """Test caching with negative collection_id."""
        cache = FileListingCache()

        cache.set(collection_id=-1, files=['photo1.dng'], ttl_seconds=3600)
        cached_files = cache.get(collection_id=-1)

        assert cached_files == ['photo1.dng']
