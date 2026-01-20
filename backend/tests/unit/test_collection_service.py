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
        self, test_db_session, test_file_cache, test_connector_service, test_team
    ):
        """Should create local collection and test directory accessibility"""
        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        with tempfile.TemporaryDirectory() as temp_dir:
            collection = service.create_collection(
                name="Local Photos",
                type=CollectionType.LOCAL,
                location=temp_dir,
                team_id=test_team.id,
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
        self, test_db_session, test_file_cache, test_connector_service, test_team
    ):
        """Should mark local collection as inaccessible if directory doesn't exist"""
        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        collection = service.create_collection(
            name="Invalid Path",
            type=CollectionType.LOCAL,
            location="/nonexistent/path/to/photos",
            team_id=test_team.id,
            state=CollectionState.LIVE
        )

        assert collection.is_accessible is False
        # Path is rejected either because it's not under authorized root, or not found
        assert any(msg in collection.last_error.lower() for msg in [
            "not found or not readable",
            "not under an authorized root",
        ])

    def test_create_remote_collection_with_connector(
        self, test_db_session, test_file_cache, test_connector_service, sample_connector, test_team
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
            team_id=test_team.id,
            connector_id=connector.id,
            state=CollectionState.LIVE
        )

        assert collection.id is not None
        assert collection.type == CollectionType.S3
        assert collection.connector_id == connector.id
        assert collection.is_accessible is True
        test_connector_service.test_connector.assert_called_once_with(connector.id)

    def test_create_remote_collection_requires_connector(
        self, test_db_session, test_file_cache, test_connector_service, test_team
    ):
        """Should raise ValueError if remote collection missing connector_id"""
        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        with pytest.raises(ValueError) as exc_info:
            service.create_collection(
                name="S3 Photos",
                type=CollectionType.S3,
                location="my-bucket/photos",
                team_id=test_team.id
                # Missing connector_id
            )

        assert "Connector ID required" in str(exc_info.value)

    def test_create_local_collection_rejects_connector(
        self, test_db_session, test_file_cache, test_connector_service, sample_connector, test_team
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
                    team_id=test_team.id,
                    connector_id=connector.id  # Should not be provided for LOCAL
                )

        assert "should not be provided for LOCAL" in str(exc_info.value)

    def test_create_collection_with_metadata(
        self, test_db_session, test_file_cache, test_connector_service, test_team
    ):
        """Should create collection with metadata"""
        service = CollectionService(test_db_session, test_file_cache, test_connector_service)
        metadata = {"project": "Vacation 2024", "photographer": "John Doe"}

        with tempfile.TemporaryDirectory() as temp_dir:
            collection = service.create_collection(
                name="Vacation Photos",
                type=CollectionType.LOCAL,
                location=temp_dir,
                team_id=test_team.id,
                metadata=metadata
            )

            assert collection.metadata_json == json.dumps(metadata)

    def test_create_collection_duplicate_name(
        self, test_db_session, test_file_cache, test_connector_service, test_team
    ):
        """Should raise ValueError if collection name already exists"""
        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        with tempfile.TemporaryDirectory() as temp_dir:
            service.create_collection("Duplicate", CollectionType.LOCAL, temp_dir, team_id=test_team.id)

            with pytest.raises(ValueError) as exc_info:
                service.create_collection("Duplicate", CollectionType.LOCAL, temp_dir, team_id=test_team.id)

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
        self, test_db_session, test_file_cache, test_connector_service, sample_collection, test_team
    ):
        """Should list all collections sorted by created_at DESC (newest first)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create collections at different times
            coll1 = sample_collection(name="First", type="local", location=temp_dir)
            coll2 = sample_collection(name="Second", type="local", location=temp_dir)
            coll3 = sample_collection(name="Third", type="local", location=temp_dir)

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)
        collections = service.list_collections(team_id=test_team.id)

        assert len(collections) == 3
        # Should be newest first
        assert collections[0].id == coll3.id
        assert collections[1].id == coll2.id
        assert collections[2].id == coll1.id

    def test_list_collections_filter_by_state(
        self, test_db_session, test_file_cache, test_connector_service, sample_collection, test_team
    ):
        """Should filter collections by state"""
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_collection(name="Live 1", type="local", location=temp_dir, state="live")
            sample_collection(name="Live 2", type="local", location=temp_dir, state="live")
            sample_collection(name="Closed", type="local", location=temp_dir, state="closed")

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)
        collections = service.list_collections(team_id=test_team.id, state_filter=CollectionState.LIVE)

        assert len(collections) == 2
        assert all(c.state == CollectionState.LIVE for c in collections)

    def test_list_collections_filter_by_type(
        self, test_db_session, test_file_cache, test_connector_service,
        sample_collection, sample_connector, test_team
    ):
        """Should filter collections by type"""
        connector = sample_connector(name="Test", type="s3")
        with tempfile.TemporaryDirectory() as temp_dir:
            sample_collection(name="Local 1", type="local", location=temp_dir)
            sample_collection(name="Local 2", type="local", location=temp_dir)
            sample_collection(name="S3", type="s3", connector_id=connector.id, location="bucket")

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)
        collections = service.list_collections(team_id=test_team.id, type_filter=CollectionType.LOCAL)

        assert len(collections) == 2
        assert all(c.type == CollectionType.LOCAL for c in collections)

    def test_list_collections_accessible_only(
        self, test_db_session, test_file_cache, test_connector_service, sample_collection, test_team
    ):
        """Should filter collections by accessibility"""
        with tempfile.TemporaryDirectory() as temp_dir:
            accessible = sample_collection(name="Accessible", type="local", location=temp_dir, is_accessible=True)
            inaccessible = sample_collection(
                name="Inaccessible", type="local", location="/invalid", is_accessible=False
            )

        service = CollectionService(test_db_session, test_file_cache, test_connector_service)
        collections = service.list_collections(team_id=test_team.id, accessible_only=True)

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


# ============================================================================
# Collection Agent Binding Tests (Phase 6 - T103)
# ============================================================================

class TestCollectionAgentBinding:
    """Tests for collection agent binding validation.

    Issue #90 - Distributed Agent Architecture (Phase 6)
    Task T103: Unit tests for collection binding validation

    Requirements:
    - LOCAL collections SHOULD have a bound agent for job execution
    - Bound agent validation: agent must exist and belong to same team
    - Collection model properties for binding state
    """

    @pytest.fixture
    def create_agent(self, test_db_session, test_team, test_user):
        """Factory fixture to create test agents."""
        from backend.src.services.agent_service import AgentService
        from backend.src.models.agent import AgentStatus

        def _create_agent(name="Test Agent", status=AgentStatus.ONLINE):
            service = AgentService(test_db_session)

            # Create token
            token_result = service.create_registration_token(
                team_id=test_team.id,
                created_by_user_id=test_user.id,
            )
            test_db_session.commit()

            # Register agent
            result = service.register_agent(
                plaintext_token=token_result.plaintext_token,
                name=name,
                hostname="test.local",
                os_info="Linux",
                capabilities=["local_filesystem"],
                version="1.0.0"
            )
            test_db_session.commit()

            # Set agent status
            if status == AgentStatus.ONLINE:
                service.process_heartbeat(result.agent, status=AgentStatus.ONLINE)
                test_db_session.commit()

            return result.agent

        return _create_agent

    def test_collection_model_requires_bound_agent_property(
        self, test_db_session, sample_collection
    ):
        """Test Collection model requires_bound_agent property for LOCAL type."""
        with tempfile.TemporaryDirectory() as temp_dir:
            local_collection = sample_collection(
                name="Local Collection",
                type="local",
                location=temp_dir
            )

        assert local_collection.type == CollectionType.LOCAL
        assert local_collection.requires_bound_agent is True
        assert local_collection.has_bound_agent is False

    def test_collection_model_requires_bound_agent_remote(
        self, test_db_session, sample_collection, sample_connector
    ):
        """Test Collection model requires_bound_agent is False for remote types."""
        connector = sample_connector(name="S3 Test", type="s3")
        remote_collection = sample_collection(
            name="S3 Collection",
            type="s3",
            location="bucket/path",
            connector_id=connector.id
        )

        assert remote_collection.type == CollectionType.S3
        assert remote_collection.requires_bound_agent is False

    def test_collection_model_has_bound_agent_property(
        self, test_db_session, sample_collection, create_agent
    ):
        """Test Collection model has_bound_agent property when agent is bound."""
        agent = create_agent(name="Bound Agent")

        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(
                name="Bound Collection",
                type="local",
                location=temp_dir
            )
            # Manually bind the agent (service will do this in Phase 6)
            collection.bound_agent_id = agent.id
            test_db_session.commit()
            test_db_session.refresh(collection)

        assert collection.has_bound_agent is True
        assert collection.bound_agent_id == agent.id
        assert collection.bound_agent is not None
        assert collection.bound_agent.name == "Bound Agent"

    def test_local_collection_can_have_bound_agent(
        self, test_db_session, test_file_cache, test_connector_service, test_team, create_agent
    ):
        """Test that LOCAL collections can be created with bound_agent_id."""
        agent = create_agent(name="Local Agent")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create collection with bound agent directly via model
            collection = Collection(
                name="Local with Agent",
                type=CollectionType.LOCAL,
                location=temp_dir,
                team_id=test_team.id,
                state=CollectionState.LIVE,
                bound_agent_id=agent.id,
                is_accessible=True,
            )
            test_db_session.add(collection)
            test_db_session.commit()
            test_db_session.refresh(collection)

        assert collection.bound_agent_id == agent.id
        assert collection.bound_agent.name == "Local Agent"
        assert collection.requires_bound_agent is True
        assert collection.has_bound_agent is True

    def test_remote_collection_cannot_have_bound_agent(
        self, test_db_session, sample_connector, test_team
    ):
        """Test that remote collections don't use bound agents (they use connectors)."""
        connector = sample_connector(name="S3 Test", type="s3")

        # Remote collections use connectors, not bound agents
        collection = Collection(
            name="S3 Collection",
            type=CollectionType.S3,
            location="bucket/path",
            team_id=test_team.id,
            state=CollectionState.LIVE,
            connector_id=connector.id,
            bound_agent_id=None,  # Remote collections don't have bound agents
            is_accessible=True,
        )
        test_db_session.add(collection)
        test_db_session.commit()
        test_db_session.refresh(collection)

        assert collection.connector_id == connector.id
        assert collection.bound_agent_id is None
        assert collection.requires_bound_agent is False
        assert collection.has_bound_agent is False

    def test_bound_agent_relationship_eager_loaded(
        self, test_db_session, test_team, create_agent
    ):
        """Test that bound_agent relationship is eagerly loaded."""
        agent = create_agent(name="Eager Agent")

        with tempfile.TemporaryDirectory() as temp_dir:
            collection = Collection(
                name="Eager Load Test",
                type=CollectionType.LOCAL,
                location=temp_dir,
                team_id=test_team.id,
                state=CollectionState.LIVE,
                bound_agent_id=agent.id,
                is_accessible=True,
            )
            test_db_session.add(collection)
            test_db_session.commit()

        # Query fresh collection
        fresh_collection = test_db_session.query(Collection).filter(
            Collection.id == collection.id
        ).first()

        # bound_agent should be eagerly loaded (lazy="joined" in model)
        # Access without additional query
        assert fresh_collection.bound_agent is not None
        assert fresh_collection.bound_agent.name == "Eager Agent"

    def test_collection_with_nonexistent_agent_raises_integrity_error(
        self, test_db_session, test_team
    ):
        """Test that binding to nonexistent agent raises integrity error."""
        from sqlalchemy.exc import IntegrityError

        with tempfile.TemporaryDirectory() as temp_dir:
            collection = Collection(
                name="Invalid Agent Binding",
                type=CollectionType.LOCAL,
                location=temp_dir,
                team_id=test_team.id,
                state=CollectionState.LIVE,
                bound_agent_id=99999,  # Nonexistent agent
                is_accessible=True,
            )
            test_db_session.add(collection)

            with pytest.raises(IntegrityError):
                test_db_session.commit()


# ============================================================================
# Collection Path Validation Against Agent Roots (Phase 6b - T134)
# ============================================================================

class TestCollectionPathValidation:
    """Tests for collection path validation against agent authorized roots.

    Issue #90 - Distributed Agent Architecture (Phase 6b)
    Task T134: Unit tests for path validation in collection service

    Requirements:
    - LOCAL collections MUST have bound_agent_id
    - Path must be under one of the agent's authorized roots
    """

    @pytest.fixture
    def create_agent_with_roots(self, test_db_session, test_team, test_user):
        """Factory fixture to create test agents with authorized roots."""
        from backend.src.services.agent_service import AgentService
        from backend.src.models.agent import AgentStatus
        import json

        def _create_agent(name="Test Agent", authorized_roots=None, status=AgentStatus.ONLINE):
            service = AgentService(test_db_session)

            # Create token
            token_result = service.create_registration_token(
                team_id=test_team.id,
                created_by_user_id=test_user.id,
            )
            test_db_session.commit()

            # Register agent with authorized roots
            result = service.register_agent(
                plaintext_token=token_result.plaintext_token,
                name=name,
                hostname="test.local",
                os_info="Linux",
                capabilities=["local_filesystem"],
                authorized_roots=authorized_roots or [],
                version="1.0.0"
            )
            test_db_session.commit()

            # Set agent status
            if status == AgentStatus.ONLINE:
                service.process_heartbeat(result.agent, status=AgentStatus.ONLINE)
                test_db_session.commit()

            return result.agent

        return _create_agent

    def test_local_collection_requires_bound_agent(
        self, test_db_session, test_file_cache, test_connector_service, test_team
    ):
        """Test that LOCAL collections require bound_agent_id."""
        service = CollectionService(test_db_session, test_file_cache, test_connector_service)

        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError) as exc_info:
                service.create_collection(
                    name="Local Without Agent",
                    type=CollectionType.LOCAL,
                    location=temp_dir,
                    team_id=test_team.id,
                    # Missing bound_agent_id
                )

            assert "bound_agent_id is required for LOCAL collections" in str(exc_info.value)

    def test_local_collection_path_validation_success(
        self, test_db_session, test_file_cache, test_connector_service, test_team, create_agent_with_roots
    ):
        """Test that path under authorized root is accepted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create agent with temp_dir as authorized root
            agent = create_agent_with_roots(
                name="Photo Agent",
                authorized_roots=[temp_dir]
            )

            service = CollectionService(test_db_session, test_file_cache, test_connector_service)

            # Create collection with path under authorized root
            subdir = os.path.join(temp_dir, "photos")
            os.makedirs(subdir)

            collection = service.create_collection(
                name="Valid Path Collection",
                type=CollectionType.LOCAL,
                location=subdir,
                team_id=test_team.id,
                bound_agent_id=agent.id,
            )

            assert collection.id is not None
            assert collection.bound_agent_id == agent.id

    def test_local_collection_path_validation_failure(
        self, test_db_session, test_file_cache, test_connector_service, test_team, create_agent_with_roots
    ):
        """Test that path not under authorized root is rejected."""
        with tempfile.TemporaryDirectory() as authorized_dir:
            with tempfile.TemporaryDirectory() as unauthorized_dir:
                # Create agent with authorized_dir as root, but try to use unauthorized_dir
                agent = create_agent_with_roots(
                    name="Photo Agent",
                    authorized_roots=[authorized_dir]
                )

                service = CollectionService(test_db_session, test_file_cache, test_connector_service)

                with pytest.raises(ValueError) as exc_info:
                    service.create_collection(
                        name="Invalid Path Collection",
                        type=CollectionType.LOCAL,
                        location=unauthorized_dir,
                        team_id=test_team.id,
                        bound_agent_id=agent.id,
                    )

                assert "not under any of the agent's authorized roots" in str(exc_info.value)

    def test_local_collection_path_validation_no_roots_configured(
        self, test_db_session, test_file_cache, test_connector_service, test_team, create_agent_with_roots
    ):
        """Test that collection creation fails when agent has no authorized roots."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create agent with no authorized roots
            agent = create_agent_with_roots(
                name="No Roots Agent",
                authorized_roots=[]
            )

            service = CollectionService(test_db_session, test_file_cache, test_connector_service)

            with pytest.raises(ValueError) as exc_info:
                service.create_collection(
                    name="No Roots Collection",
                    type=CollectionType.LOCAL,
                    location=temp_dir,
                    team_id=test_team.id,
                    bound_agent_id=agent.id,
                )

            assert "not under any of the agent's authorized roots" in str(exc_info.value)
            assert "none configured" in str(exc_info.value)

    def test_update_collection_validates_new_path(
        self, test_db_session, test_file_cache, test_connector_service, test_team, create_agent_with_roots
    ):
        """Test that updating location validates against agent's authorized roots."""
        with tempfile.TemporaryDirectory() as authorized_dir:
            with tempfile.TemporaryDirectory() as unauthorized_dir:
                # Create agent and collection with valid path
                agent = create_agent_with_roots(
                    name="Photo Agent",
                    authorized_roots=[authorized_dir]
                )

                service = CollectionService(test_db_session, test_file_cache, test_connector_service)

                collection = service.create_collection(
                    name="Original Collection",
                    type=CollectionType.LOCAL,
                    location=authorized_dir,
                    team_id=test_team.id,
                    bound_agent_id=agent.id,
                )

                # Try to update location to unauthorized path
                with pytest.raises(ValueError) as exc_info:
                    service.update_collection(
                        collection.id,
                        location=unauthorized_dir
                    )

                assert "not under any of the agent's authorized roots" in str(exc_info.value)
