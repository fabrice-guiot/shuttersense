"""
Unit tests for CollectionService business logic.

Tests collection CRUD operations with accessibility testing, file listing caching,
connector integration, and deletion validation.
"""

import pytest
import json
import os
import tempfile
from unittest.mock import MagicMock, patch
from freezegun import freeze_time

from backend.src.services.collection_service import CollectionService
from backend.src.services.connector_service import ConnectorService
from backend.src.models import Collection, CollectionType, CollectionState, ConnectorType
from backend.src.utils.cache import FileListingCache


class TestCollectionServiceCreate:
    """Tests for CollectionService.create_collection() - T104m"""

    def test_create_local_collection_with_accessibility_test(
        self, test_db_session, test_file_cache, test_connector_service
    ):
        """Should create local collection and test directory accessibility"""
        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        with tempfile.TemporaryDirectory() as temp_dir:
            collection = service.create_collection(
                name="Local Photos",
                type=CollectionType.LOCAL,
                location=temp_dir,
                state=CollectionState.LIVE
            )

            assert collection.id is not None
            assert collection.name == "Local Photos"
            assert collection.type == CollectionType.LOCAL
            assert collection.location == temp_dir
            assert collection.is_accessible is True
            assert collection.last_error is None
            assert collection.connector_id is None

    def test_create_local_collection_inaccessible_directory(
        self, test_db_session, test_file_cache, test_connector_service
    ):
        """Should mark local collection as inaccessible if directory doesn't exist"""
        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        collection = service.create_collection(
            name="Invalid Path",
            type=CollectionType.LOCAL,
            location="/nonexistent/path/to/photos",
            state=CollectionState.LIVE
        )

        assert collection.is_accessible is False
        # Path is rejected either because it's not under authorized root, or not found
        assert any(msg in collection.last_error.lower() for msg in [
            "not found or not readable",
            "not under an authorized root",
        ])

    def test_create_remote_collection_with_connector(
        self, test_db_session, test_file_cache, test_connector_service, sample_connector
    ):
        """Should create remote collection and test connector accessibility"""
        connector = sample_connector(name="S3 Connector", type="s3")

        # Mock connector test
        test_connector_service.test_connector = MagicMock(return_value=(True, "Connected"))

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        collection = service.create_collection(
            name="S3 Photos",
            type=CollectionType.S3,
            location="my-bucket/photos",
            connector_id=connector.id,
            state=CollectionState.LIVE
        )

        assert collection.id is not None
        assert collection.type == CollectionType.S3
        assert collection.connector_id == connector.id
        assert collection.is_accessible is True
        test_connector_service.test_connector.assert_called_once_with(connector.id)

    def test_create_remote_collection_requires_connector(
        self, test_db_session, test_file_cache, test_connector_service
    ):
        """Should raise ValueError if remote collection missing connector_id"""
        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        with pytest.raises(ValueError) as exc_info:
            service.create_collection(
                name="S3 Photos",
                type=CollectionType.S3,
                location="my-bucket/photos"
                # Missing connector_id
            )

        assert "Connector ID required" in str(exc_info.value)

    def test_create_local_collection_rejects_connector(
        self, test_db_session, test_file_cache, test_connector_service, sample_connector
    ):
        """Should raise ValueError if local collection has connector_id"""
        connector = sample_connector(name="Test", type="s3")
        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError) as exc_info:
                service.create_collection(
                    name="Local Photos",
                    type=CollectionType.LOCAL,
                    location=temp_dir,
                    connector_id=connector.id  # Should not be provided for LOCAL
                )

        assert "should not be provided for LOCAL" in str(exc_info.value)

    def test_create_collection_with_metadata(
        self, test_db_session, test_file_cache, test_connector_service
    ):
        """Should create collection with metadata"""
        service = CollectionService(test_db_session, test_file_cache, test_connector_service)
        metadata = {"project": "Vacation 2024", "photographer": "John Doe"}

        with tempfile.TemporaryDirectory() as temp_dir:
            collection = service.create_collection(
                name="Vacation Photos",
                type=CollectionType.LOCAL,
                location=temp_dir,
                metadata=metadata
            )

            assert collection.metadata_json == json.dumps(metadata)

    def test_create_collection_duplicate_name(
        self, test_db_session, test_file_cache, test_connector_service
    ):
        """Should raise ValueError if collection name already exists"""
        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        with tempfile.TemporaryDirectory() as temp_dir:
            service.create_collection("Duplicate", CollectionType.LOCAL, temp_dir)

            with pytest.raises(ValueError) as exc_info:
                service.create_collection("Duplicate", CollectionType.LOCAL, temp_dir)

        assert "already exists" in str(exc_info.value)


class TestCollectionServiceGet:
    """Tests for CollectionService.get_collection() - T104m"""

    def test_get_collection_with_connector_details(
        self, test_db_session, test_file_cache, test_connector_service,
        sample_connector, sample_collection
    ):
        """Should get collection with connector relationship loaded"""
        connector = sample_connector(name="My Connector", type="s3")
        collection = sample_collection(
            name="Test Collection",
            type="s3",
            connector_id=connector.id,
            location="bucket/path"
        )

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)
        result = service.get_collection(collection.id)

        assert result is not None
        assert result.connector is not None
        assert result.connector.name == "My Connector"

    def test_get_collection_not_found(
        self, test_db_session, test_file_cache, test_connector_service
    ):
        """Should return None if collection doesn't exist"""
        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        result = service.get_collection(99999)

        assert result is None


class TestCollectionServiceList:
    """Tests for CollectionService.list_collections() - T104m"""

    def test_list_all_collections_sorted_by_created_at(
        self, test_db_session, test_file_cache, test_connector_service, sample_collection
    ):
        """Should list all collections sorted by created_at DESC (newest first)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create collections at different times
            coll1 = sample_collection(name="First", type="local", location=temp_dir)
            coll2 = sample_collection(name="Second", type="local", location=temp_dir)
            coll3 = sample_collection(name="Third", type="local", location=temp_dir)

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)
        collections = service.list_collections()

        assert len(collections) == 3
        # Should be newest first
        assert collections[0].id == coll3.id
        assert collections[1].id == coll2.id
        assert collections[2].id == coll1.id

    def test_list_collections_filter_by_state(
        self, test_db_session, test_file_cache, test_connector_service, sample_collection
    ):
        """Should filter collections by state"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_collection(name="Live 1", type="local", location=temp_dir, state="live")
            sample_collection(name="Live 2", type="local", location=temp_dir, state="live")
            sample_collection(name="Closed", type="local", location=temp_dir, state="closed")

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)
        collections = service.list_collections(state_filter=CollectionState.LIVE)

        assert len(collections) == 2
        assert all(c.state == CollectionState.LIVE for c in collections)

    def test_list_collections_filter_by_type(
        self, test_db_session, test_file_cache, test_connector_service,
        sample_collection, sample_connector
    ):
        """Should filter collections by type"""
        connector = sample_connector(name="Test", type="s3")
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_collection(name="Local 1", type="local", location=temp_dir)
            sample_collection(name="Local 2", type="local", location=temp_dir)
            sample_collection(name="S3", type="s3", connector_id=connector.id, location="bucket")

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)
        collections = service.list_collections(type_filter=CollectionType.LOCAL)

        assert len(collections) == 2
        assert all(c.type == CollectionType.LOCAL for c in collections)

    def test_list_collections_accessible_only(
        self, test_db_session, test_file_cache, test_connector_service, sample_collection
    ):
        """Should filter collections by accessibility"""
        with tempfile.TemporaryDirectory() as temp_dir:
            accessible = sample_collection(name="Accessible", type="local", location=temp_dir, is_accessible=True)
            inaccessible = sample_collection(
                name="Inaccessible", type="local", location="/invalid", is_accessible=False
            )

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)
        collections = service.list_collections(accessible_only=True)

        assert len(collections) == 1
        assert collections[0].id == accessible.id


class TestCollectionServiceUpdate:
    """Tests for CollectionService.update_collection() - T104m"""

    def test_update_collection_name(
        self, test_db_session, test_file_cache, test_connector_service, sample_collection
    ):
        """Should update collection name"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Old Name", type="local", location=temp_dir)

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)
        updated = service.update_collection(collection.id, name="New Name")

        assert updated.name == "New Name"

    def test_update_collection_state_invalidates_cache(
        self, test_db_session, test_file_cache, test_connector_service, sample_collection
    ):
        """Should invalidate cache when state changes (different TTL applies)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Test", type="local", location=temp_dir, state="live")

        # Pre-populate cache
        test_file_cache.set(collection.id, ['file1.jpg'], ttl_seconds=3600)
        assert test_file_cache.get(collection.id) is not None

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)
        service.update_collection(collection.id, state=CollectionState.CLOSED)

        # Cache should be invalidated
        assert test_file_cache.get(collection.id) is None

    def test_update_collection_same_state_no_cache_invalidation(
        self, test_db_session, test_file_cache, test_connector_service, sample_collection
    ):
        """Should NOT invalidate cache if state unchanged"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Test", type="local", location=temp_dir, state="live")

        # Pre-populate cache
        test_file_cache.set(collection.id, ['file1.jpg'], ttl_seconds=3600)

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)
        service.update_collection(collection.id, name="New Name")  # State unchanged

        # Cache should NOT be invalidated
        assert test_file_cache.get(collection.id) == ['file1.jpg']

    def test_update_collection_not_found(
        self, test_db_session, test_file_cache, test_connector_service
    ):
        """Should raise ValueError if collection doesn't exist"""
        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        with pytest.raises(ValueError) as exc_info:
            service.update_collection(99999, name="New Name")

        assert "not found" in str(exc_info.value)


class TestCollectionServiceDelete:
    """Tests for CollectionService.delete_collection() - T104n"""

    def test_delete_collection_success_no_dependencies(
        self, test_db_session, test_file_cache, test_connector_service, sample_collection
    ):
        """Should successfully delete collection when no dependencies exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="To Delete", type="local", location=temp_dir)
            collection_id = collection.id

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)
        service.delete_collection(collection_id)

        # Collection should be deleted
        deleted = test_db_session.query(Collection).filter(Collection.id == collection_id).first()
        assert deleted is None

    def test_delete_collection_checks_analysis_results(
        self, test_db_session, test_file_cache, test_connector_service, sample_collection
    ):
        """Should check for analysis results before deletion"""
        # Note: This is a placeholder test since AnalysisResult model doesn't exist yet
        # The service currently has result_count = 0 hardcoded (TODO)
        # This test validates the check structure is in place

        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Test", type="local", location=temp_dir)

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        # Should succeed because placeholder result_count = 0
        service.delete_collection(collection.id)

        # TODO: When AnalysisResult model exists, update this test to:
        # 1. Create analysis results for collection
        # 2. Verify ValueError is raised
        # 3. Test that force=True allows deletion

    def test_delete_collection_checks_active_jobs(
        self, test_db_session, test_file_cache, test_connector_service, sample_collection
    ):
        """Should check for active jobs before deletion"""
        # Note: This is a placeholder test since job counting doesn't exist yet
        # The service currently has job_count = 0 hardcoded (TODO)
        # This test validates the check structure is in place

        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Test", type="local", location=temp_dir)

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        # Should succeed because placeholder job_count = 0
        service.delete_collection(collection.id)

        # TODO: When job counting is implemented, update this test to:
        # 1. Create active jobs for collection
        # 2. Verify ValueError is raised
        # 3. Test that force=True allows deletion

    def test_delete_collection_force_flag_behavior(
        self, test_db_session, test_file_cache, test_connector_service, sample_collection
    ):
        """Should respect force flag for deletion with dependencies"""
        # Note: Placeholder test for force flag structure
        # When dependencies are implemented, this will test cascade deletion

        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Test", type="local", location=temp_dir)

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        # Should succeed with force=True
        service.delete_collection(collection.id, force=True)

        # TODO: When dependencies exist, verify cascade deletion happens

    def test_delete_collection_invalidates_cache(
        self, test_db_session, test_file_cache, test_connector_service, sample_collection
    ):
        """Should invalidate cache when collection is deleted"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Test", type="local", location=temp_dir)

        # Pre-populate cache
        test_file_cache.set(collection.id, ['file1.jpg'], ttl_seconds=3600)
        assert test_file_cache.get(collection.id) is not None

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)
        service.delete_collection(collection.id)

        # Cache should be invalidated
        assert test_file_cache.get(collection.id) is None

    def test_delete_collection_not_found(
        self, test_db_session, test_file_cache, test_connector_service
    ):
        """Should raise ValueError if collection doesn't exist"""
        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        with pytest.raises(ValueError) as exc_info:
            service.delete_collection(99999)

        assert "not found" in str(exc_info.value)


class TestCollectionServiceGetFiles:
    """Tests for CollectionService.get_collection_files() - T104o"""

    def test_get_collection_files_cache_hit(
        self, test_db_session, test_file_cache, test_connector_service, sample_collection
    ):
        """Should return cached files on cache hit"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Test", type="local", location=temp_dir, is_accessible=True)

        # Pre-populate cache
        cached_files = ['photo1.dng', 'photo2.cr3']
        test_file_cache.set(collection.id, cached_files, ttl_seconds=3600)

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)
        files = service.get_collection_files(collection.id, use_cache=True)

        assert files == cached_files

    def test_get_collection_files_cache_miss_fetches_and_caches(
        self, test_db_session, test_file_cache, test_connector_service, sample_collection
    ):
        """Should fetch files and cache them on cache miss"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some files
            open(os.path.join(temp_dir, 'photo1.dng'), 'a').close()
            open(os.path.join(temp_dir, 'photo2.cr3'), 'a').close()

            collection = sample_collection(name="Test", type="local", location=temp_dir, is_accessible=True)

            service = CollectionService(test_db_session, test_file_cache, test_connector_service)

            # Cache should be empty
            assert test_file_cache.get(collection.id) is None

            files = service.get_collection_files(collection.id, use_cache=True)

            # Should fetch files
            assert 'photo1.dng' in files
            assert 'photo2.cr3' in files

            # Should cache files
            cached = test_file_cache.get(collection.id)
            assert cached is not None
            assert set(cached) == set(files)

    def test_get_collection_files_force_refresh(
        self, test_db_session, test_file_cache, test_connector_service, sample_collection
    ):
        """Should skip cache when use_cache=False"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create new files
            open(os.path.join(temp_dir, 'new_photo.dng'), 'a').close()

            collection = sample_collection(name="Test", type="local", location=temp_dir, is_accessible=True)

            # Pre-populate cache with old data
            test_file_cache.set(collection.id, ['old_photo.jpg'], ttl_seconds=3600)

            service = CollectionService(test_db_session, test_file_cache, test_connector_service)
            files = service.get_collection_files(collection.id, use_cache=False)

            # Should fetch fresh files, not cached
            assert 'new_photo.dng' in files
            assert 'old_photo.jpg' not in files

    @freeze_time("2025-01-01 12:00:00")
    def test_get_collection_files_ttl_expiry(
        self, test_db_session, test_file_cache, test_connector_service, sample_collection
    ):
        """Should fetch fresh files when cache has expired"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(name="Test", type="local", location=temp_dir, is_accessible=True)

        # Cache files with short TTL
        test_file_cache.set(collection.id, ['cached_photo.jpg'], ttl_seconds=3600)

        # Move time forward past TTL
        with freeze_time("2025-01-01 13:00:01"):
            service = CollectionService(test_db_session, test_file_cache, test_connector_service)

            # Cache should be expired, return None
            assert test_file_cache.get(collection.id) is None

            # Should fetch fresh files
            files = service.get_collection_files(collection.id, use_cache=True)
            # Files will be whatever is in temp_dir at this point

    def test_get_collection_files_state_based_ttl_live(
        self, test_db_session, test_file_cache, test_connector_service, sample_collection
    ):
        """Should use state-based TTL (Live = 3600s) when caching"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(
                name="Live Collection",
                type="local",
                location=temp_dir,
                state="live",
                is_accessible=True
            )

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        # Mock the cache set to capture TTL
        original_set = test_file_cache.set
        captured_ttl = None

        def capture_ttl(collection_id, files, ttl_seconds):
            nonlocal captured_ttl
            captured_ttl = ttl_seconds
            return original_set(collection_id, files, ttl_seconds)

        test_file_cache.set = capture_ttl

        service.get_collection_files(collection.id, use_cache=False)

        # Should use Live TTL (3600s)
        assert captured_ttl == 3600

    def test_get_collection_files_state_based_ttl_closed(
        self, test_db_session, test_file_cache, test_connector_service, sample_collection
    ):
        """Should use state-based TTL (Closed = 86400s) when caching"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(
                name="Closed Collection",
                type="local",
                location=temp_dir,
                state="closed",
                is_accessible=True
            )

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        # Mock the cache set to capture TTL
        original_set = test_file_cache.set
        captured_ttl = None

        def capture_ttl(collection_id, files, ttl_seconds):
            nonlocal captured_ttl
            captured_ttl = ttl_seconds
            return original_set(collection_id, files, ttl_seconds)

        test_file_cache.set = capture_ttl

        service.get_collection_files(collection.id, use_cache=False)

        # Should use Closed TTL (86400s = 24 hours)
        assert captured_ttl == 86400

    def test_get_collection_files_custom_ttl_override(
        self, test_db_session, test_file_cache, test_connector_service, sample_collection
    ):
        """Should use custom cache_ttl if provided"""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(
                name="Custom TTL",
                type="local",
                location=temp_dir,
                state="live",
                cache_ttl=7200,  # Custom override
                is_accessible=True
            )

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        # Mock the cache set to capture TTL
        original_set = test_file_cache.set
        captured_ttl = None

        def capture_ttl(collection_id, files, ttl_seconds):
            nonlocal captured_ttl
            captured_ttl = ttl_seconds
            return original_set(collection_id, files, ttl_seconds)

        test_file_cache.set = capture_ttl

        service.get_collection_files(collection.id, use_cache=False)

        # Should use custom TTL
        assert captured_ttl == 7200

    def test_get_collection_files_not_accessible_raises_error(
        self, test_db_session, test_file_cache, test_connector_service, sample_collection
    ):
        """Should raise ValueError if collection is not accessible"""
        collection = sample_collection(
            name="Inaccessible",
            type="local",
            location="/invalid/path",
            is_accessible=False,
            last_error="Directory not found"
        )

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        with pytest.raises(ValueError) as exc_info:
            service.get_collection_files(collection.id)

        assert "not accessible" in str(exc_info.value)
        assert "Directory not found" in str(exc_info.value)

    def test_get_collection_files_not_found(
        self, test_db_session, test_file_cache, test_connector_service
    ):
        """Should raise ValueError if collection doesn't exist"""
        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        with pytest.raises(ValueError) as exc_info:
            service.get_collection_files(99999)

        assert "not found" in str(exc_info.value)
