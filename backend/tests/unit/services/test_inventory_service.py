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
        service = InventoryService(test_db_session)

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
            collection_guid="col_01hgw2bbg0000000000000001",
            team_id=test_team.id
        )

        assert result.collection_guid == "col_01hgw2bbg0000000000000001"
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
            collection_guid="col_01hgw2bbg0000000000000001"
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
