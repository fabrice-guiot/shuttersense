"""
Unit tests for InventoryService.

Tests configuration, validation, folder management, and status operations.

Issue #107: Cloud Storage Bucket Inventory Import
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from backend.src.services.inventory_service import (
    InventoryService,
    InventoryValidationStatus,
)
from backend.src.services.exceptions import NotFoundError, ValidationError
from backend.src.models import Connector, ConnectorType
from backend.src.models.connector import CredentialLocation
from backend.src.models.inventory_folder import InventoryFolder
from backend.src.models.job import Job, JobStatus
from backend.src.schemas.inventory import S3InventoryConfig, GCSInventoryConfig


class TestInventoryServiceSetConfig:
    """Tests for set_inventory_config method."""

    def test_set_s3_inventory_config(self, test_db_session, test_team, test_connector):
        """Test setting S3 inventory configuration on a connector."""
        service = InventoryService(test_db_session)
        config = S3InventoryConfig(
            destination_bucket="my-inventory-bucket",
            source_bucket="my-photo-bucket",
            config_name="daily-inventory"
        )

        result = service.set_inventory_config(
            connector_id=test_connector.id,
            config=config,
            schedule="weekly",
            team_id=test_team.id
        )

        assert result.inventory_config is not None
        assert result.inventory_config["provider"] == "s3"
        assert result.inventory_config["destination_bucket"] == "my-inventory-bucket"
        assert result.inventory_config["source_bucket"] == "my-photo-bucket"
        assert result.inventory_config["config_name"] == "daily-inventory"
        assert result.inventory_schedule == "weekly"
        assert result.inventory_validation_status == InventoryValidationStatus.PENDING

    def test_set_gcs_inventory_config(self, test_db_session, test_team):
        """Test setting GCS inventory configuration on a connector."""
        # Create a GCS connector
        connector = Connector(
            name="GCS Connector",
            type=ConnectorType.GCS,
            team_id=test_team.id,
            credential_location=CredentialLocation.SERVER,
            credentials="encrypted_creds"
        )
        test_db_session.add(connector)
        test_db_session.commit()

        service = InventoryService(test_db_session)
        config = GCSInventoryConfig(
            destination_bucket="gcs-inventory-bucket",
            report_config_name="photo-inventory"
        )

        result = service.set_inventory_config(
            connector_id=connector.id,
            config=config,
            schedule="daily",
            team_id=test_team.id
        )

        assert result.inventory_config is not None
        assert result.inventory_config["provider"] == "gcs"
        assert result.inventory_config["destination_bucket"] == "gcs-inventory-bucket"
        assert result.inventory_config["report_config_name"] == "photo-inventory"
        assert result.inventory_schedule == "daily"

    def test_set_config_on_smb_connector_raises_error(self, test_db_session, test_team):
        """Test that SMB connectors cannot have inventory config."""
        # Create an SMB connector
        connector = Connector(
            name="SMB Connector",
            type=ConnectorType.SMB,
            team_id=test_team.id,
            credential_location=CredentialLocation.SERVER,
            credentials="encrypted_creds"
        )
        test_db_session.add(connector)
        test_db_session.commit()

        service = InventoryService(test_db_session)
        config = S3InventoryConfig(
            destination_bucket="bucket",
            source_bucket="source",
            config_name="config"
        )

        with pytest.raises(ValidationError) as exc_info:
            service.set_inventory_config(
                connector_id=connector.id,
                config=config,
                team_id=test_team.id
            )
        assert "does not support inventory" in str(exc_info.value)

    def test_set_config_connector_type_mismatch_raises_error(self, test_db_session, test_team, test_connector):
        """Test that config provider must match connector type."""
        service = InventoryService(test_db_session)
        # test_connector is S3, try to set GCS config
        config = GCSInventoryConfig(
            destination_bucket="bucket",
            report_config_name="config"
        )

        with pytest.raises(ValidationError) as exc_info:
            service.set_inventory_config(
                connector_id=test_connector.id,
                config=config,
                team_id=test_team.id
            )
        assert "doesn't match" in str(exc_info.value)

    def test_set_config_nonexistent_connector_raises_error(self, test_db_session, test_team):
        """Test that non-existent connector raises NotFoundError."""
        service = InventoryService(test_db_session)
        config = S3InventoryConfig(
            destination_bucket="bucket",
            source_bucket="source",
            config_name="config"
        )

        with pytest.raises(NotFoundError):
            service.set_inventory_config(
                connector_id=99999,
                config=config,
                team_id=test_team.id
            )


class TestInventoryServiceClearConfig:
    """Tests for clear_inventory_config method."""

    def test_clear_inventory_config(self, test_db_session, test_team, test_connector):
        """Test clearing inventory configuration from a connector."""
        service = InventoryService(test_db_session)

        # First set a config
        config = S3InventoryConfig(
            destination_bucket="bucket",
            source_bucket="source",
            config_name="config"
        )
        service.set_inventory_config(
            connector_id=test_connector.id,
            config=config,
            schedule="daily",
            team_id=test_team.id
        )

        # Now clear it
        result = service.clear_inventory_config(
            connector_id=test_connector.id,
            team_id=test_team.id
        )

        assert result.inventory_config is None
        assert result.inventory_schedule == "manual"
        assert result.inventory_validation_status is None
        assert result.inventory_validation_error is None

    def test_clear_config_deletes_folders(self, test_db_session, test_team, test_connector):
        """Test that clearing config also deletes associated folders."""
        service = InventoryService(test_db_session)

        # Create some inventory folders
        folder1 = InventoryFolder(
            connector_id=test_connector.id,
            path="2020/",
            object_count=100,
            total_size_bytes=1000000
        )
        folder2 = InventoryFolder(
            connector_id=test_connector.id,
            path="2021/",
            object_count=200,
            total_size_bytes=2000000
        )
        test_db_session.add_all([folder1, folder2])
        test_db_session.commit()

        # Clear config
        service.clear_inventory_config(
            connector_id=test_connector.id,
            team_id=test_team.id
        )

        # Check folders are deleted
        remaining_folders = test_db_session.query(InventoryFolder).filter(
            InventoryFolder.connector_id == test_connector.id
        ).count()
        assert remaining_folders == 0


class TestInventoryServiceCreateValidationJob:
    """Tests for create_validation_job method."""

    def test_create_validation_job(self, test_db_session, test_team, test_connector):
        """Test creating a validation job for a connector."""
        service = InventoryService(test_db_session)

        # Set inventory config first
        config = S3InventoryConfig(
            destination_bucket="bucket",
            source_bucket="source",
            config_name="config"
        )
        service.set_inventory_config(
            connector_id=test_connector.id,
            config=config,
            team_id=test_team.id
        )

        # Create validation job
        # Note: The Job model defaults are not fully compatible with SQLite test DB
        # This test verifies the job object is created with correct attributes
        # Full integration tests should use PostgreSQL
        job = service.create_validation_job(
            connector_id=test_connector.id,
            team_id=test_team.id
        )

        assert job is not None
        assert job.tool == "inventory_validate"
        assert job.mode == "validation"
        assert job.status == JobStatus.PENDING
        assert job.priority == 5
        # Progress is stored as JSON string
        progress = job.progress
        assert progress is not None
        assert progress.get("connector_id") == test_connector.id

    def test_create_validation_job_without_config_raises_error(self, test_db_session, test_team, test_connector):
        """Test that validation job cannot be created without inventory config."""
        service = InventoryService(test_db_session)

        with pytest.raises(ValidationError) as exc_info:
            service.create_validation_job(
                connector_id=test_connector.id,
                team_id=test_team.id
            )
        assert "no inventory configuration" in str(exc_info.value)


class TestInventoryServiceUpdateValidationStatus:
    """Tests for update_validation_status method."""

    def test_update_validation_status_success(self, test_db_session, test_team, test_connector):
        """Test updating validation status to validated."""
        service = InventoryService(test_db_session)

        # Set initial config
        config = S3InventoryConfig(
            destination_bucket="bucket",
            source_bucket="source",
            config_name="config"
        )
        service.set_inventory_config(
            connector_id=test_connector.id,
            config=config,
            team_id=test_team.id
        )

        # Update to validated
        result = service.update_validation_status(
            connector_id=test_connector.id,
            success=True,
            team_id=test_team.id
        )

        assert result.inventory_validation_status == InventoryValidationStatus.VALIDATED
        assert result.inventory_validation_error is None

    def test_update_validation_status_failure(self, test_db_session, test_team, test_connector):
        """Test updating validation status to failed."""
        service = InventoryService(test_db_session)

        # Set initial config
        config = S3InventoryConfig(
            destination_bucket="bucket",
            source_bucket="source",
            config_name="config"
        )
        service.set_inventory_config(
            connector_id=test_connector.id,
            config=config,
            team_id=test_team.id
        )

        # Update to failed
        result = service.update_validation_status(
            connector_id=test_connector.id,
            success=False,
            error_message="Access denied to bucket",
            team_id=test_team.id
        )

        assert result.inventory_validation_status == InventoryValidationStatus.FAILED
        assert result.inventory_validation_error == "Access denied to bucket"


class TestInventoryServiceGetStatus:
    """Tests for get_inventory_status method."""

    def test_get_inventory_status(self, test_db_session, test_team, test_connector):
        """Test getting inventory status for a connector."""
        service = InventoryService(test_db_session)

        # Set config and validate
        config = S3InventoryConfig(
            destination_bucket="bucket",
            source_bucket="source",
            config_name="config"
        )
        service.set_inventory_config(
            connector_id=test_connector.id,
            config=config,
            team_id=test_team.id
        )
        service.update_validation_status(
            connector_id=test_connector.id,
            success=True,
            team_id=test_team.id
        )

        # Add some folders
        folder1 = InventoryFolder(
            connector_id=test_connector.id,
            path="2020/",
            object_count=100,
            total_size_bytes=1000000
        )
        folder2 = InventoryFolder(
            connector_id=test_connector.id,
            path="2021/",
            object_count=200,
            total_size_bytes=2000000,
            collection_guid="col_xxx"  # mapped
        )
        test_db_session.add_all([folder1, folder2])
        test_db_session.commit()

        # Get status
        status = service.get_inventory_status(
            connector_id=test_connector.id,
            team_id=test_team.id
        )

        assert status["validation_status"] == InventoryValidationStatus.VALIDATED
        assert status["folder_count"] == 2
        assert status["mapped_folder_count"] == 1
        assert status["validation_error"] is None


class TestInventoryServiceListFolders:
    """Tests for list_folders method."""

    def test_list_folders(self, test_db_session, test_team, test_connector):
        """Test listing folders for a connector."""
        service = InventoryService(test_db_session)

        # Add folders
        folders = [
            InventoryFolder(connector_id=test_connector.id, path="2020/", object_count=100, total_size_bytes=1000),
            InventoryFolder(connector_id=test_connector.id, path="2020/Vacation/", object_count=50, total_size_bytes=500),
            InventoryFolder(connector_id=test_connector.id, path="2021/", object_count=200, total_size_bytes=2000),
        ]
        test_db_session.add_all(folders)
        test_db_session.commit()

        result, total_count, has_more = service.list_folders(
            connector_id=test_connector.id,
            team_id=test_team.id
        )

        assert len(result) == 3
        assert total_count == 3
        assert not has_more

    def test_list_folders_with_path_prefix(self, test_db_session, test_team, test_connector):
        """Test listing folders with path prefix filter."""
        service = InventoryService(test_db_session)

        # Add folders
        folders = [
            InventoryFolder(connector_id=test_connector.id, path="2020/", object_count=100, total_size_bytes=1000),
            InventoryFolder(connector_id=test_connector.id, path="2020/Vacation/", object_count=50, total_size_bytes=500),
            InventoryFolder(connector_id=test_connector.id, path="2021/", object_count=200, total_size_bytes=2000),
        ]
        test_db_session.add_all(folders)
        test_db_session.commit()

        result, total_count, has_more = service.list_folders(
            connector_id=test_connector.id,
            path_prefix="2020/",
            team_id=test_team.id
        )

        assert len(result) == 2
        assert total_count == 2

    def test_list_folders_unmapped_only(self, test_db_session, test_team, test_connector):
        """Test listing only unmapped folders."""
        service = InventoryService(test_db_session)

        # Add folders (one mapped)
        folder1 = InventoryFolder(connector_id=test_connector.id, path="2020/", object_count=100, total_size_bytes=1000)
        folder2 = InventoryFolder(connector_id=test_connector.id, path="2021/", object_count=200, total_size_bytes=2000, collection_guid="col_xxx")
        test_db_session.add_all([folder1, folder2])
        test_db_session.commit()

        result, total_count, has_more = service.list_folders(
            connector_id=test_connector.id,
            unmapped_only=True,
            team_id=test_team.id
        )

        assert len(result) == 1
        assert result[0].path == "2020/"

    def test_list_folders_pagination(self, test_db_session, test_team, test_connector):
        """Test folder list pagination."""
        service = InventoryService(test_db_session)

        # Add multiple folders
        for i in range(10):
            folder = InventoryFolder(
                connector_id=test_connector.id,
                path=f"folder{i:02d}/",
                object_count=i * 10,
                total_size_bytes=i * 100
            )
            test_db_session.add(folder)
        test_db_session.commit()

        # Get first page
        result, total_count, has_more = service.list_folders(
            connector_id=test_connector.id,
            limit=5,
            offset=0,
            team_id=test_team.id
        )

        assert len(result) == 5
        assert total_count == 10
        assert has_more

        # Get second page
        result, total_count, has_more = service.list_folders(
            connector_id=test_connector.id,
            limit=5,
            offset=5,
            team_id=test_team.id
        )

        assert len(result) == 5
        assert not has_more


class TestInventoryServiceUpsertFolders:
    """Tests for upsert_folders method."""

    def test_upsert_new_folders(self, test_db_session, test_team, test_connector):
        """Test upserting new folders."""
        service = InventoryService(test_db_session)

        folders_data = [
            {"path": "2020/", "object_count": 100, "total_size_bytes": 1000000},
            {"path": "2021/", "object_count": 200, "total_size_bytes": 2000000},
        ]

        count = service.upsert_folders(
            connector_id=test_connector.id,
            folders_data=folders_data,
            team_id=test_team.id
        )

        assert count == 2

        # Verify folders were created
        folders = test_db_session.query(InventoryFolder).filter(
            InventoryFolder.connector_id == test_connector.id
        ).all()
        assert len(folders) == 2

    def test_upsert_updates_existing_folders(self, test_db_session, test_team, test_connector):
        """Test that upsert updates existing folders."""
        service = InventoryService(test_db_session)

        # Create initial folder
        folder = InventoryFolder(
            connector_id=test_connector.id,
            path="2020/",
            object_count=100,
            total_size_bytes=1000000
        )
        test_db_session.add(folder)
        test_db_session.commit()

        # Upsert with updated values
        folders_data = [
            {"path": "2020/", "object_count": 150, "total_size_bytes": 1500000},
        ]

        count = service.upsert_folders(
            connector_id=test_connector.id,
            folders_data=folders_data,
            team_id=test_team.id
        )

        assert count == 1

        # Verify folder was updated
        test_db_session.refresh(folder)
        assert folder.object_count == 150
        assert folder.total_size_bytes == 1500000


class TestInventoryServiceMapFolderToCollection:
    """Tests for map_folder_to_collection method."""

    def test_map_folder_to_collection(self, test_db_session, test_team, test_connector):
        """Test mapping a folder to a collection."""
        from backend.src.models import Collection, CollectionType, CollectionState
        from backend.src.services.guid import GuidService

        service = InventoryService(test_db_session)

        # Create a collection to map to
        collection_uuid = GuidService.generate_uuid()
        collection = Collection(
            uuid=collection_uuid,
            name="Test Collection",
            type=CollectionType.S3,
            state=CollectionState.LIVE,
            location="my-bucket/2020/Vacation/",
            team_id=test_team.id,
            connector_id=test_connector.id,
            is_accessible=True
        )
        test_db_session.add(collection)
        test_db_session.commit()

        # Create folder
        folder = InventoryFolder(
            connector_id=test_connector.id,
            path="2020/Vacation/",
            object_count=100,
            total_size_bytes=1000000
        )
        test_db_session.add(folder)
        test_db_session.commit()

        # Map to collection
        result = service.map_folder_to_collection(
            folder_id=folder.id,
            collection_guid=collection.guid,
            team_id=test_team.id
        )

        assert result.collection_guid == collection.guid
        assert result.is_mapped is True

    def test_map_nonexistent_folder_raises_error(self, test_db_session, test_team):
        """Test that mapping non-existent folder raises error."""
        service = InventoryService(test_db_session)

        with pytest.raises(NotFoundError):
            service.map_folder_to_collection(
                folder_id=99999,
                collection_guid="col_xxx",
                team_id=test_team.id
            )


# ============================================================================
# T058a: Unit tests for overlapping path validation
# ============================================================================

class TestPathsOverlap:
    """Tests for _paths_overlap private method (T058a).

    These tests verify the path overlap detection used in folder mapping
    validation to prevent ancestor/descendant collection paths.
    """

    def test_paths_overlap_ancestor_descendant(self, test_db_session):
        """Test that ancestor is detected as overlapping with descendant."""
        service = InventoryService(test_db_session)

        # Ancestor/descendant relationship
        assert service._paths_overlap("2020/", "2020/Events/") is True
        assert service._paths_overlap("2020/Events/", "2020/Events/Wedding/") is True
        assert service._paths_overlap("photos/", "photos/2020/summer/") is True

    def test_paths_overlap_descendant_ancestor(self, test_db_session):
        """Test that descendant is detected as overlapping with ancestor."""
        service = InventoryService(test_db_session)

        # Descendant/ancestor relationship (reversed order)
        assert service._paths_overlap("2020/Events/", "2020/") is True
        assert service._paths_overlap("2020/Events/Wedding/", "2020/Events/") is True

    def test_paths_overlap_no_relation(self, test_db_session):
        """Test that unrelated paths do not overlap."""
        service = InventoryService(test_db_session)

        # Sibling paths
        assert service._paths_overlap("2020/Events/", "2020/Photos/") is False
        assert service._paths_overlap("2020/", "2021/") is False

        # Different root paths
        assert service._paths_overlap("photos/2020/", "backups/2020/") is False

    def test_paths_overlap_same_path(self, test_db_session):
        """Test that same path overlaps with itself."""
        service = InventoryService(test_db_session)

        assert service._paths_overlap("2020/", "2020/") is True
        assert service._paths_overlap("photos/summer/", "photos/summer/") is True

    def test_paths_overlap_handles_missing_trailing_slash(self, test_db_session):
        """Test that paths without trailing slash are handled correctly."""
        service = InventoryService(test_db_session)

        # Without trailing slashes
        assert service._paths_overlap("2020", "2020/Events") is True
        assert service._paths_overlap("2020/Events", "2020") is True

        # Mixed trailing slashes
        assert service._paths_overlap("2020/", "2020/Events") is True
        assert service._paths_overlap("2020", "2020/Events/") is True

    def test_paths_overlap_partial_name_match_not_overlap(self, test_db_session):
        """Test that partial folder name matches are not considered overlaps."""
        service = InventoryService(test_db_session)

        # "photo" is not ancestor of "photos/"
        assert service._paths_overlap("photo/", "photos/") is False

        # "2020" is not ancestor of "2020-backup/"
        assert service._paths_overlap("2020/", "2020-backup/") is False

        # Similar prefixes that are not ancestors
        assert service._paths_overlap("events/", "events-archive/") is False


# ============================================================================
# T058b: Unit tests for state validation in validate_folder_mappings
# ============================================================================

class TestValidateFolderMappings:
    """Tests for validate_folder_mappings method (T058b).

    These tests verify the validation logic for folder-to-collection mappings,
    including checks for folder existence, already-mapped status, and path overlaps.
    """

    def test_validate_valid_mappings(self, test_db_session, test_team, test_connector):
        """Test validation passes for valid non-overlapping folders."""
        service = InventoryService(test_db_session)

        # Create folders
        folder1 = InventoryFolder(
            connector_id=test_connector.id,
            path="2020/Events/",
            object_count=100,
            total_size_bytes=1000000
        )
        folder2 = InventoryFolder(
            connector_id=test_connector.id,
            path="2021/Photos/",
            object_count=200,
            total_size_bytes=2000000
        )
        test_db_session.add_all([folder1, folder2])
        test_db_session.commit()

        valid_folders, errors = service.validate_folder_mappings(
            connector_id=test_connector.id,
            folder_guids=[folder1.guid, folder2.guid],
            team_id=test_team.id
        )

        assert len(valid_folders) == 2
        assert len(errors) == 0

    def test_validate_nonexistent_folder(self, test_db_session, test_team, test_connector):
        """Test validation fails for non-existent folder GUIDs."""
        service = InventoryService(test_db_session)

        valid_folders, errors = service.validate_folder_mappings(
            connector_id=test_connector.id,
            folder_guids=["fld_nonexistent12345678901"],
            team_id=test_team.id
        )

        assert len(valid_folders) == 0
        assert len(errors) == 1
        assert "not found" in errors[0][1].lower() or "invalid" in errors[0][1].lower()

    def test_validate_already_mapped_folder(self, test_db_session, test_team, test_connector):
        """Test validation fails for folders already mapped to collections."""
        service = InventoryService(test_db_session)

        # Create folder that's already mapped
        folder = InventoryFolder(
            connector_id=test_connector.id,
            path="2020/Events/",
            object_count=100,
            total_size_bytes=1000000,
            collection_guid="col_01hgw2bbg00000000000000001"
        )
        test_db_session.add(folder)
        test_db_session.commit()

        valid_folders, errors = service.validate_folder_mappings(
            connector_id=test_connector.id,
            folder_guids=[folder.guid],
            team_id=test_team.id
        )

        assert len(valid_folders) == 0
        assert len(errors) == 1
        assert "already mapped" in errors[0][1].lower()

    def test_validate_overlapping_paths_ancestor_descendant(self, test_db_session, test_team, test_connector):
        """Test validation fails for overlapping ancestor/descendant paths."""
        service = InventoryService(test_db_session)

        # Create folders with overlapping paths
        parent = InventoryFolder(
            connector_id=test_connector.id,
            path="2020/",
            object_count=100,
            total_size_bytes=1000000
        )
        child = InventoryFolder(
            connector_id=test_connector.id,
            path="2020/Events/",
            object_count=50,
            total_size_bytes=500000
        )
        test_db_session.add_all([parent, child])
        test_db_session.commit()

        valid_folders, errors = service.validate_folder_mappings(
            connector_id=test_connector.id,
            folder_guids=[parent.guid, child.guid],
            team_id=test_team.id
        )

        # One folder should be valid, one should have overlap error
        assert len(valid_folders) == 1
        assert len(errors) == 1
        assert "overlap" in errors[0][1].lower()

    def test_validate_folder_wrong_connector(self, test_db_session, test_team, test_connector):
        """Test validation fails for folder from different connector."""
        service = InventoryService(test_db_session)

        # Create another connector
        other_connector = Connector(
            name="Other Connector",
            type=ConnectorType.S3,
            team_id=test_team.id,
            credential_location=CredentialLocation.SERVER,
            credentials="encrypted_creds"
        )
        test_db_session.add(other_connector)
        test_db_session.commit()

        # Create folder on other connector
        folder = InventoryFolder(
            connector_id=other_connector.id,
            path="2020/",
            object_count=100,
            total_size_bytes=1000000
        )
        test_db_session.add(folder)
        test_db_session.commit()

        # Try to validate with original connector
        valid_folders, errors = service.validate_folder_mappings(
            connector_id=test_connector.id,
            folder_guids=[folder.guid],
            team_id=test_team.id
        )

        assert len(valid_folders) == 0
        assert len(errors) == 1
        assert "connector" in errors[0][1].lower()

    def test_validate_empty_folder_list(self, test_db_session, test_team, test_connector):
        """Test validation with empty folder list returns empty results."""
        service = InventoryService(test_db_session)

        valid_folders, errors = service.validate_folder_mappings(
            connector_id=test_connector.id,
            folder_guids=[],
            team_id=test_team.id
        )

        assert len(valid_folders) == 0
        assert len(errors) == 0

    def test_validate_sibling_paths_allowed(self, test_db_session, test_team, test_connector):
        """Test validation passes for sibling paths (non-overlapping)."""
        service = InventoryService(test_db_session)

        # Create sibling folders (same parent, different names)
        folder1 = InventoryFolder(
            connector_id=test_connector.id,
            path="2020/Events/",
            object_count=100,
            total_size_bytes=1000000
        )
        folder2 = InventoryFolder(
            connector_id=test_connector.id,
            path="2020/Photos/",
            object_count=200,
            total_size_bytes=2000000
        )
        folder3 = InventoryFolder(
            connector_id=test_connector.id,
            path="2020/Videos/",
            object_count=50,
            total_size_bytes=5000000
        )
        test_db_session.add_all([folder1, folder2, folder3])
        test_db_session.commit()

        valid_folders, errors = service.validate_folder_mappings(
            connector_id=test_connector.id,
            folder_guids=[folder1.guid, folder2.guid, folder3.guid],
            team_id=test_team.id
        )

        assert len(valid_folders) == 3
        assert len(errors) == 0


# =============================================================================
# T069a: Unit tests for FileInfo storage service
# =============================================================================

class TestFileInfoStorage:
    """Tests for FileInfo storage methods (T069a)."""

    def test_get_collections_for_connector(self, test_db_session, test_team, test_connector):
        """Test retrieving collections mapped to connector folders."""
        from backend.src.models import Collection, CollectionType, CollectionState
        from backend.src.services.guid import GuidService

        service = InventoryService(test_db_session)

        # Create a collection
        collection_uuid = GuidService.generate_uuid()
        collection_guid = GuidService.encode_uuid(collection_uuid, "col")
        collection = Collection(
            uuid=collection_uuid,
            name="Test Collection",
            type=CollectionType.S3,
            state=CollectionState.LIVE,
            location="my-bucket/2020/vacation/",
            team_id=test_team.id,
            connector_id=test_connector.id,
            is_accessible=True
        )
        test_db_session.add(collection)
        test_db_session.commit()

        # Create folder mapped to this collection
        folder = InventoryFolder(
            connector_id=test_connector.id,
            path="2020/vacation/",
            object_count=100,
            total_size_bytes=1000000,
            collection_guid=collection_guid
        )
        test_db_session.add(folder)
        test_db_session.commit()

        # Get collections for connector
        collections = service.get_collections_for_connector(
            connector_id=test_connector.id,
            team_id=test_team.id
        )

        assert len(collections) == 1
        assert collections[0]["collection_guid"] == collection_guid
        assert collections[0]["collection_id"] == collection.id
        assert collections[0]["folder_path"] == "2020/vacation/"

    def test_get_collections_for_connector_no_mappings(self, test_db_session, test_team, test_connector):
        """Test getting collections when no mappings exist."""
        service = InventoryService(test_db_session)

        # Create folder without mapping
        folder = InventoryFolder(
            connector_id=test_connector.id,
            path="2020/vacation/",
            object_count=100,
            total_size_bytes=1000000
        )
        test_db_session.add(folder)
        test_db_session.commit()

        collections = service.get_collections_for_connector(
            connector_id=test_connector.id,
            team_id=test_team.id
        )

        assert len(collections) == 0

    def test_store_file_info(self, test_db_session, test_team, test_connector):
        """Test storing FileInfo on a collection."""
        from backend.src.models import Collection, CollectionType, CollectionState

        service = InventoryService(test_db_session)

        # Create a collection
        collection = Collection(
            name="Test Collection",
            type=CollectionType.S3,
            state=CollectionState.LIVE,
            location="my-bucket/2020/vacation/",
            team_id=test_team.id,
            connector_id=test_connector.id,
            is_accessible=True
        )
        test_db_session.add(collection)
        test_db_session.commit()

        # Store FileInfo
        file_info = [
            {"key": "2020/vacation/IMG_001.CR3", "size": 25000000, "last_modified": "2020-07-15T10:30:00Z"},
            {"key": "2020/vacation/IMG_002.CR3", "size": 24000000, "last_modified": "2020-07-15T11:00:00Z"},
        ]

        result = service.store_file_info(
            collection_id=collection.id,
            file_info=file_info,
            team_id=test_team.id
        )

        assert result is True

        # Verify storage
        test_db_session.refresh(collection)
        assert collection.file_info is not None
        assert len(collection.file_info) == 2
        assert collection.file_info_source == "inventory"
        assert collection.file_info_updated_at is not None

    def test_store_file_info_updates_timestamp(self, test_db_session, test_team, test_connector):
        """Test that storing FileInfo updates the timestamp."""
        from backend.src.models import Collection, CollectionType, CollectionState
        from datetime import datetime, timedelta

        service = InventoryService(test_db_session)

        # Create collection with existing FileInfo
        old_time = datetime.utcnow() - timedelta(days=1)
        collection = Collection(
            name="Test Collection",
            type=CollectionType.S3,
            state=CollectionState.LIVE,
            location="my-bucket/2020/vacation/",
            team_id=test_team.id,
            connector_id=test_connector.id,
            is_accessible=True,
            file_info=[{"key": "old.jpg", "size": 1000, "last_modified": "2020-01-01T00:00:00Z"}],
            file_info_source="api",
            file_info_updated_at=old_time
        )
        test_db_session.add(collection)
        test_db_session.commit()

        # Store new FileInfo
        new_file_info = [
            {"key": "new.jpg", "size": 2000, "last_modified": "2020-07-15T10:30:00Z"},
        ]

        service.store_file_info(
            collection_id=collection.id,
            file_info=new_file_info,
            team_id=test_team.id
        )

        test_db_session.refresh(collection)
        assert collection.file_info_source == "inventory"
        assert collection.file_info_updated_at > old_time
        assert len(collection.file_info) == 1
        assert collection.file_info[0]["key"] == "new.jpg"

    def test_store_file_info_batch(self, test_db_session, test_team, test_connector):
        """Test batch storing FileInfo for multiple collections."""
        from backend.src.models import Collection, CollectionType, CollectionState
        from backend.src.models.inventory_folder import InventoryFolder
        from backend.src.services.guid import GuidService

        service = InventoryService(test_db_session)

        # Create collections
        collections = []
        for i in range(3):
            collection_uuid = GuidService.generate_uuid()
            collection = Collection(
                uuid=collection_uuid,
                name=f"Test Collection {i}",
                type=CollectionType.S3,
                state=CollectionState.LIVE,
                location=f"my-bucket/folder{i}/",
                team_id=test_team.id,
                connector_id=test_connector.id,
                is_accessible=True
            )
            test_db_session.add(collection)
            collections.append(collection)
        test_db_session.commit()

        # Create InventoryFolder mappings for each collection
        for i, collection in enumerate(collections):
            folder = InventoryFolder(
                connector_id=test_connector.id,
                path=f"folder{i}/",
                object_count=1,
                total_size_bytes=1000,
                collection_guid=collection.guid,
                is_mappable=False  # Already mapped
            )
            test_db_session.add(folder)
        test_db_session.commit()

        # Build batch data
        collections_data = [
            {
                "collection_guid": collections[0].guid,
                "file_info": [{"key": "f0/a.jpg", "size": 1000, "last_modified": "2020-01-01T00:00:00Z"}]
            },
            {
                "collection_guid": collections[1].guid,
                "file_info": [{"key": "f1/b.jpg", "size": 2000, "last_modified": "2020-01-01T00:00:00Z"}]
            },
            {
                "collection_guid": collections[2].guid,
                "file_info": [{"key": "f2/c.jpg", "size": 3000, "last_modified": "2020-01-01T00:00:00Z"}]
            },
        ]

        updated_count = service.store_file_info_batch(
            collections_data=collections_data,
            team_id=test_team.id,
            connector_id=test_connector.id
        )

        assert updated_count == 3

        # Verify all collections updated
        for i, coll in enumerate(collections):
            test_db_session.refresh(coll)
            assert coll.file_info is not None
            assert coll.file_info_source == "inventory"
            assert coll.file_info_updated_at is not None

    def test_store_file_info_batch_skips_invalid_guid(self, test_db_session, test_team, test_connector):
        """Test batch storage skips invalid collection GUIDs."""
        from backend.src.models import Collection, CollectionType, CollectionState
        from backend.src.models.inventory_folder import InventoryFolder
        from backend.src.services.guid import GuidService

        service = InventoryService(test_db_session)

        # Create one valid collection
        collection_uuid = GuidService.generate_uuid()
        collection = Collection(
            uuid=collection_uuid,
            name="Test Collection",
            type=CollectionType.S3,
            state=CollectionState.LIVE,
            location="my-bucket/folder/",
            team_id=test_team.id,
            connector_id=test_connector.id,
            is_accessible=True
        )
        test_db_session.add(collection)
        test_db_session.commit()

        # Create InventoryFolder mapping for the valid collection
        folder = InventoryFolder(
            connector_id=test_connector.id,
            path="folder/",
            object_count=1,
            total_size_bytes=1000,
            collection_guid=collection.guid,
            is_mappable=False  # Already mapped
        )
        test_db_session.add(folder)
        test_db_session.commit()

        # Build batch data with invalid GUID
        collections_data = [
            {
                "collection_guid": collection.guid,
                "file_info": [{"key": "a.jpg", "size": 1000, "last_modified": "2020-01-01T00:00:00Z"}]
            },
            {
                "collection_guid": "invalid_guid",  # Invalid
                "file_info": [{"key": "b.jpg", "size": 2000, "last_modified": "2020-01-01T00:00:00Z"}]
            },
            {
                "collection_guid": "col_nonexistent12345678901234",  # Valid format but doesn't exist
                "file_info": [{"key": "c.jpg", "size": 3000, "last_modified": "2020-01-01T00:00:00Z"}]
            },
        ]

        updated_count = service.store_file_info_batch(
            collections_data=collections_data,
            team_id=test_team.id,
            connector_id=test_connector.id
        )

        # Only 1 should be updated (the valid one)
        assert updated_count == 1

        test_db_session.refresh(collection)
        assert collection.file_info is not None

    def test_store_file_info_batch_requires_team_id(self, test_db_session, test_team, test_connector):
        """Test that store_file_info_batch raises ValueError when team_id is falsy."""
        service = InventoryService(test_db_session)

        collections_data = [
            {
                "collection_guid": "col_01hgw2bbg00000000000000001",
                "file_info": [{"key": "a.jpg", "size": 1000, "last_modified": "2020-01-01T00:00:00Z"}]
            },
        ]

        with pytest.raises(ValueError, match="team_id is required"):
            service.store_file_info_batch(
                collections_data=collections_data,
                team_id=0  # Falsy value
            )


# ============================================================================
# Scheduled Import Tests (Phase 6 - Issue #107)
# ============================================================================

class TestInventoryServiceScheduling:
    """Tests for scheduled inventory import functionality (Phase 6 - T077-T081)."""

    def test_calculate_next_scheduled_at_manual(self, test_db_session):
        """Test that manual schedule returns None."""
        service = InventoryService(test_db_session)
        result = service.calculate_next_scheduled_at("manual")
        assert result is None

    def test_calculate_next_scheduled_at_daily(self, test_db_session):
        """Test daily schedule returns next 00:00 UTC."""
        from datetime import timedelta

        service = InventoryService(test_db_session)
        reference = datetime(2026, 1, 25, 14, 30, 0)  # 2:30 PM

        result = service.calculate_next_scheduled_at("daily", reference)

        assert result is not None
        # Next day at 00:00
        expected = datetime(2026, 1, 26, 0, 0, 0)
        assert result == expected

    def test_calculate_next_scheduled_at_weekly(self, test_db_session):
        """Test weekly schedule returns same weekday next week at 00:00 UTC."""
        service = InventoryService(test_db_session)
        # Saturday, Jan 25, 2026
        reference = datetime(2026, 1, 25, 14, 30, 0)

        result = service.calculate_next_scheduled_at("weekly", reference)

        assert result is not None
        # Next Saturday (Feb 1, 2026) at 00:00
        expected = datetime(2026, 2, 1, 0, 0, 0)
        assert result == expected

    def test_set_config_schedule_change_to_manual_cancels_jobs(
        self, test_db_session, test_team, test_connector
    ):
        """Test that changing schedule to manual cancels scheduled jobs."""
        service = InventoryService(test_db_session)

        # Set inventory config with weekly schedule
        config = S3InventoryConfig(
            destination_bucket="bucket",
            source_bucket="source",
            config_name="config"
        )
        service.set_inventory_config(
            connector_id=test_connector.id,
            config=config,
            schedule="weekly",
            team_id=test_team.id
        )

        # Validate so we can create import jobs
        service.update_validation_status(
            connector_id=test_connector.id,
            team_id=test_team.id,
            success=True
        )

        # Create a scheduled import job
        scheduled_job = service.create_scheduled_import_job(
            connector_id=test_connector.id,
            team_id=test_team.id,
            scheduled_for=datetime(2026, 2, 1, 0, 0, 0)
        )

        # Verify job was created
        assert scheduled_job.status == JobStatus.SCHEDULED

        # Change schedule to manual
        service.set_inventory_config(
            connector_id=test_connector.id,
            config=config,
            schedule="manual",
            team_id=test_team.id
        )

        # Verify job was cancelled
        test_db_session.refresh(scheduled_job)
        assert scheduled_job.status == JobStatus.CANCELLED

    def test_clear_config_cancels_scheduled_jobs(
        self, test_db_session, test_team, test_connector
    ):
        """Test that clearing config cancels scheduled jobs."""
        service = InventoryService(test_db_session)

        # Set inventory config with weekly schedule
        config = S3InventoryConfig(
            destination_bucket="bucket",
            source_bucket="source",
            config_name="config"
        )
        service.set_inventory_config(
            connector_id=test_connector.id,
            config=config,
            schedule="weekly",
            team_id=test_team.id
        )

        # Validate so we can create import jobs
        service.update_validation_status(
            connector_id=test_connector.id,
            team_id=test_team.id,
            success=True
        )

        # Create a scheduled import job
        scheduled_job = service.create_scheduled_import_job(
            connector_id=test_connector.id,
            team_id=test_team.id,
            scheduled_for=datetime(2026, 2, 1, 0, 0, 0)
        )

        # Clear config
        service.clear_inventory_config(
            connector_id=test_connector.id,
            team_id=test_team.id
        )

        # Verify job was cancelled
        test_db_session.refresh(scheduled_job)
        assert scheduled_job.status == JobStatus.CANCELLED

    def test_on_import_completed_creates_scheduled_job(
        self, test_db_session, test_team, test_connector
    ):
        """Test that on_import_completed creates next scheduled job."""
        service = InventoryService(test_db_session)

        # Set inventory config with daily schedule
        config = S3InventoryConfig(
            destination_bucket="bucket",
            source_bucket="source",
            config_name="config"
        )
        service.set_inventory_config(
            connector_id=test_connector.id,
            config=config,
            schedule="daily",
            team_id=test_team.id
        )

        # Validate
        service.update_validation_status(
            connector_id=test_connector.id,
            team_id=test_team.id,
            success=True
        )

        # Simulate import completion
        next_job = service.on_import_completed(
            connector_id=test_connector.id,
            team_id=test_team.id
        )

        assert next_job is not None
        assert next_job.status == JobStatus.SCHEDULED
        assert next_job.tool == "inventory_import"
        assert next_job.scheduled_for is not None

    def test_on_import_completed_manual_schedule_no_job(
        self, test_db_session, test_team, test_connector
    ):
        """Test that on_import_completed with manual schedule creates no job."""
        service = InventoryService(test_db_session)

        # Set inventory config with manual schedule
        config = S3InventoryConfig(
            destination_bucket="bucket",
            source_bucket="source",
            config_name="config"
        )
        service.set_inventory_config(
            connector_id=test_connector.id,
            config=config,
            schedule="manual",
            team_id=test_team.id
        )

        # Validate
        service.update_validation_status(
            connector_id=test_connector.id,
            team_id=test_team.id,
            success=True
        )

        # Simulate import completion
        next_job = service.on_import_completed(
            connector_id=test_connector.id,
            team_id=test_team.id
        )

        assert next_job is None

    def test_get_next_scheduled_import_from_existing_job(
        self, test_db_session, test_team, test_connector
    ):
        """Test get_next_scheduled_import returns time from existing scheduled job."""
        service = InventoryService(test_db_session)

        # Set inventory config
        config = S3InventoryConfig(
            destination_bucket="bucket",
            source_bucket="source",
            config_name="config"
        )
        service.set_inventory_config(
            connector_id=test_connector.id,
            config=config,
            schedule="daily",
            team_id=test_team.id
        )

        # Validate
        service.update_validation_status(
            connector_id=test_connector.id,
            team_id=test_team.id,
            success=True
        )

        # Create a scheduled job
        scheduled_time = datetime(2026, 2, 1, 0, 0, 0)
        service.create_scheduled_import_job(
            connector_id=test_connector.id,
            team_id=test_team.id,
            scheduled_for=scheduled_time
        )

        # Get next scheduled import
        result = service.get_next_scheduled_import(
            connector_id=test_connector.id,
            team_id=test_team.id
        )

        assert result == scheduled_time

    def test_create_scheduled_import_job_replaces_existing(
        self, test_db_session, test_team, test_connector
    ):
        """Test that creating a new scheduled job cancels the old one."""
        service = InventoryService(test_db_session)

        # Set inventory config
        config = S3InventoryConfig(
            destination_bucket="bucket",
            source_bucket="source",
            config_name="config"
        )
        service.set_inventory_config(
            connector_id=test_connector.id,
            config=config,
            schedule="daily",
            team_id=test_team.id
        )

        # Validate
        service.update_validation_status(
            connector_id=test_connector.id,
            team_id=test_team.id,
            success=True
        )

        # Create first scheduled job
        first_job = service.create_scheduled_import_job(
            connector_id=test_connector.id,
            team_id=test_team.id,
            scheduled_for=datetime(2026, 2, 1, 0, 0, 0)
        )

        # Create second scheduled job (should cancel first)
        second_job = service.create_scheduled_import_job(
            connector_id=test_connector.id,
            team_id=test_team.id,
            scheduled_for=datetime(2026, 2, 2, 0, 0, 0)
        )

        # Verify first job was cancelled
        test_db_session.refresh(first_job)
        assert first_job.status == JobStatus.CANCELLED

        # Verify second job is scheduled
        assert second_job.status == JobStatus.SCHEDULED
