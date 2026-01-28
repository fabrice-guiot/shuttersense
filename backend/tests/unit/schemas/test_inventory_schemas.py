"""
Unit tests for inventory Pydantic schemas.

Tests validation rules for S3InventoryConfig, GCSInventoryConfig, FileInfo, and more.

Issue #107: Cloud Storage Bucket Inventory Import
"""

import pytest
from pydantic import ValidationError

from backend.src.schemas.inventory import (
    S3InventoryConfig,
    GCSInventoryConfig,
    FileInfo,
    DeltaSummary,
    InventoryFolderResponse,
    InventoryFolderListResponse,
    FolderToCollectionMapping,
    CreateCollectionsFromInventoryRequest,
    InventoryConfigRequest,
)


class TestS3InventoryConfig:
    """Tests for S3InventoryConfig schema."""

    def test_valid_s3_config(self):
        """Test valid S3 inventory configuration."""
        config = S3InventoryConfig(
            destination_bucket="my-inventory-bucket",
            source_bucket="my-photo-bucket",
            config_name="daily-inventory"
        )
        assert config.provider == "s3"
        assert config.destination_bucket == "my-inventory-bucket"
        assert config.source_bucket == "my-photo-bucket"
        assert config.config_name == "daily-inventory"
        assert config.format == "CSV"  # default

    def test_s3_config_with_format(self):
        """Test S3 config with explicit format."""
        config = S3InventoryConfig(
            destination_bucket="bucket",
            source_bucket="source",
            config_name="config",
            format="Parquet"
        )
        assert config.format == "Parquet"

    def test_s3_config_requires_destination_bucket(self):
        """Test that destination_bucket is required."""
        with pytest.raises(ValidationError) as exc_info:
            S3InventoryConfig(
                source_bucket="source",
                config_name="config"
            )
        assert "destination_bucket" in str(exc_info.value)

    def test_s3_config_requires_source_bucket(self):
        """Test that source_bucket is required."""
        with pytest.raises(ValidationError) as exc_info:
            S3InventoryConfig(
                destination_bucket="dest",
                config_name="config"
            )
        assert "source_bucket" in str(exc_info.value)

    def test_s3_config_requires_config_name(self):
        """Test that config_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            S3InventoryConfig(
                destination_bucket="dest",
                source_bucket="source"
            )
        assert "config_name" in str(exc_info.value)

    def test_s3_config_bucket_min_length(self):
        """Test bucket name minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            S3InventoryConfig(
                destination_bucket="ab",  # too short
                source_bucket="source-bucket",
                config_name="config"
            )
        assert "destination_bucket" in str(exc_info.value)

    def test_s3_config_bucket_max_length(self):
        """Test bucket name maximum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            S3InventoryConfig(
                destination_bucket="a" * 64,  # too long
                source_bucket="source-bucket",
                config_name="config"
            )
        assert "destination_bucket" in str(exc_info.value)

    def test_s3_config_invalid_bucket_hyphen_start(self):
        """Test bucket name cannot start with hyphen."""
        with pytest.raises(ValidationError) as exc_info:
            S3InventoryConfig(
                destination_bucket="-invalid-bucket",
                source_bucket="source-bucket",
                config_name="config"
            )
        assert "hyphen" in str(exc_info.value).lower()

    def test_s3_config_invalid_bucket_hyphen_end(self):
        """Test bucket name cannot end with hyphen."""
        with pytest.raises(ValidationError) as exc_info:
            S3InventoryConfig(
                destination_bucket="invalid-bucket-",
                source_bucket="source-bucket",
                config_name="config"
            )
        assert "hyphen" in str(exc_info.value).lower()

    def test_s3_config_forbids_extra_fields(self):
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            S3InventoryConfig(
                destination_bucket="bucket",
                source_bucket="source",
                config_name="config",
                extra_field="not allowed"
            )
        assert "extra" in str(exc_info.value).lower()


class TestGCSInventoryConfig:
    """Tests for GCSInventoryConfig schema."""

    def test_valid_gcs_config(self):
        """Test valid GCS inventory configuration."""
        config = GCSInventoryConfig(
            destination_bucket="my-inventory-bucket",
            report_config_name="photo-inventory"
        )
        assert config.provider == "gcs"
        assert config.destination_bucket == "my-inventory-bucket"
        assert config.report_config_name == "photo-inventory"
        assert config.format == "CSV"  # default

    def test_gcs_config_with_parquet_format(self):
        """Test GCS config with Parquet format."""
        config = GCSInventoryConfig(
            destination_bucket="bucket",
            report_config_name="config",
            format="Parquet"
        )
        assert config.format == "Parquet"

    def test_gcs_config_requires_destination_bucket(self):
        """Test that destination_bucket is required."""
        with pytest.raises(ValidationError) as exc_info:
            GCSInventoryConfig(report_config_name="config")
        assert "destination_bucket" in str(exc_info.value)

    def test_gcs_config_requires_report_config_name(self):
        """Test that report_config_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            GCSInventoryConfig(destination_bucket="bucket")
        assert "report_config_name" in str(exc_info.value)

    def test_gcs_config_forbids_extra_fields(self):
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            GCSInventoryConfig(
                destination_bucket="bucket",
                report_config_name="config",
                source_bucket="should not exist"  # GCS doesn't have this
            )
        assert "extra" in str(exc_info.value).lower()


class TestFileInfo:
    """Tests for FileInfo schema."""

    def test_valid_file_info(self):
        """Test valid FileInfo."""
        info = FileInfo(
            key="2020/vacation/photo.jpg",
            size=25000000,
            last_modified="2020-08-15T14:30:00Z"
        )
        assert info.key == "2020/vacation/photo.jpg"
        assert info.size == 25000000
        assert info.last_modified == "2020-08-15T14:30:00Z"
        assert info.etag is None
        assert info.storage_class is None

    def test_file_info_with_optional_fields(self):
        """Test FileInfo with all optional fields."""
        info = FileInfo(
            key="photo.jpg",
            size=1000,
            last_modified="2020-01-01T00:00:00Z",
            etag="abc123",
            storage_class="STANDARD"
        )
        assert info.etag == "abc123"
        assert info.storage_class == "STANDARD"

    def test_file_info_requires_key(self):
        """Test that key is required."""
        with pytest.raises(ValidationError) as exc_info:
            FileInfo(size=1000, last_modified="2020-01-01T00:00:00Z")
        assert "key" in str(exc_info.value)

    def test_file_info_requires_size(self):
        """Test that size is required."""
        with pytest.raises(ValidationError) as exc_info:
            FileInfo(key="photo.jpg", last_modified="2020-01-01T00:00:00Z")
        assert "size" in str(exc_info.value)

    def test_file_info_size_must_be_non_negative(self):
        """Test that size cannot be negative."""
        with pytest.raises(ValidationError) as exc_info:
            FileInfo(key="photo.jpg", size=-1, last_modified="2020-01-01T00:00:00Z")
        assert "size" in str(exc_info.value)

    def test_file_info_key_min_length(self):
        """Test that key must have minimum length."""
        with pytest.raises(ValidationError) as exc_info:
            FileInfo(key="", size=1000, last_modified="2020-01-01T00:00:00Z")
        assert "key" in str(exc_info.value)


class TestDeltaSummary:
    """Tests for DeltaSummary schema."""

    def test_valid_delta_summary(self):
        """Test valid DeltaSummary."""
        delta = DeltaSummary(
            new_count=10,
            modified_count=5,
            deleted_count=2,
            computed_at="2026-01-25T10:00:00Z"
        )
        assert delta.new_count == 10
        assert delta.modified_count == 5
        assert delta.deleted_count == 2
        assert delta.computed_at == "2026-01-25T10:00:00Z"

    def test_delta_summary_defaults(self):
        """Test DeltaSummary with defaults."""
        delta = DeltaSummary()
        assert delta.new_count == 0
        assert delta.modified_count == 0
        assert delta.deleted_count == 0
        assert delta.computed_at is None

    def test_delta_summary_total_changes(self):
        """Test total_changes property."""
        delta = DeltaSummary(new_count=10, modified_count=5, deleted_count=2)
        assert delta.total_changes == 17

    def test_delta_summary_has_changes_true(self):
        """Test has_changes returns True when there are changes."""
        delta = DeltaSummary(new_count=1)
        assert delta.has_changes is True

    def test_delta_summary_has_changes_false(self):
        """Test has_changes returns False when no changes."""
        delta = DeltaSummary()
        assert delta.has_changes is False

    def test_delta_summary_counts_non_negative(self):
        """Test that counts cannot be negative."""
        with pytest.raises(ValidationError):
            DeltaSummary(new_count=-1)


class TestFolderToCollectionMapping:
    """Tests for FolderToCollectionMapping schema."""

    def test_valid_mapping(self):
        """Test valid folder-to-collection mapping."""
        mapping = FolderToCollectionMapping(
            folder_guid="fld_01hgw2bbg0000000000000001",
            name="2020 - Vacation",
            state="archived"
        )
        assert mapping.folder_guid == "fld_01hgw2bbg0000000000000001"
        assert mapping.name == "2020 - Vacation"
        assert mapping.state == "archived"
        assert mapping.pipeline_guid is None

    def test_mapping_with_pipeline(self):
        """Test mapping with pipeline assignment."""
        mapping = FolderToCollectionMapping(
            folder_guid="fld_xxx",
            name="Test",
            state="live",
            pipeline_guid="pip_01hgw2bbg0000000000000001"
        )
        assert mapping.pipeline_guid == "pip_01hgw2bbg0000000000000001"

    def test_mapping_requires_folder_guid(self):
        """Test that folder_guid is required."""
        with pytest.raises(ValidationError) as exc_info:
            FolderToCollectionMapping(name="Test", state="live")
        assert "folder_guid" in str(exc_info.value)

    def test_mapping_requires_name(self):
        """Test that name is required."""
        with pytest.raises(ValidationError) as exc_info:
            FolderToCollectionMapping(folder_guid="fld_xxx", state="live")
        assert "name" in str(exc_info.value)

    def test_mapping_requires_state(self):
        """Test that state is required."""
        with pytest.raises(ValidationError) as exc_info:
            FolderToCollectionMapping(folder_guid="fld_xxx", name="Test")
        assert "state" in str(exc_info.value)

    def test_mapping_state_must_be_valid(self):
        """Test that state must be live, archived, or closed."""
        with pytest.raises(ValidationError) as exc_info:
            FolderToCollectionMapping(
                folder_guid="fld_xxx",
                name="Test",
                state="invalid"
            )
        assert "state" in str(exc_info.value)

    def test_mapping_name_max_length(self):
        """Test that name has maximum length."""
        with pytest.raises(ValidationError) as exc_info:
            FolderToCollectionMapping(
                folder_guid="fld_xxx",
                name="a" * 256,  # too long
                state="live"
            )
        assert "name" in str(exc_info.value)


class TestCreateCollectionsFromInventoryRequest:
    """Tests for CreateCollectionsFromInventoryRequest schema."""

    def test_valid_request(self):
        """Test valid collection creation request."""
        request = CreateCollectionsFromInventoryRequest(
            connector_guid="con_01hgw2bbg0000000000000001",
            folders=[
                FolderToCollectionMapping(
                    folder_guid="fld_01hgw2bbg0000000000000001",
                    name="Test Collection",
                    state="live"
                )
            ]
        )
        assert request.connector_guid == "con_01hgw2bbg0000000000000001"
        assert len(request.folders) == 1

    def test_request_requires_connector_guid(self):
        """Test that connector_guid is required."""
        with pytest.raises(ValidationError) as exc_info:
            CreateCollectionsFromInventoryRequest(
                folders=[
                    FolderToCollectionMapping(
                        folder_guid="fld_xxx",
                        name="Test",
                        state="live"
                    )
                ]
            )
        assert "connector_guid" in str(exc_info.value)

    def test_request_requires_at_least_one_folder(self):
        """Test that at least one folder is required."""
        with pytest.raises(ValidationError) as exc_info:
            CreateCollectionsFromInventoryRequest(
                connector_guid="con_xxx",
                folders=[]
            )
        assert "folders" in str(exc_info.value)

    def test_request_with_multiple_folders(self):
        """Test request with multiple folder mappings."""
        request = CreateCollectionsFromInventoryRequest(
            connector_guid="con_xxx",
            folders=[
                FolderToCollectionMapping(folder_guid="fld_1", name="Collection 1", state="live"),
                FolderToCollectionMapping(folder_guid="fld_2", name="Collection 2", state="archived"),
                FolderToCollectionMapping(folder_guid="fld_3", name="Collection 3", state="closed"),
            ]
        )
        assert len(request.folders) == 3


class TestInventoryConfigRequest:
    """Tests for InventoryConfigRequest schema."""

    def test_valid_s3_request(self):
        """Test valid inventory config request with S3."""
        request = InventoryConfigRequest(
            config=S3InventoryConfig(
                destination_bucket="bucket",
                source_bucket="source",
                config_name="config"
            ),
            schedule="weekly"
        )
        assert request.config.provider == "s3"
        assert request.schedule == "weekly"

    def test_valid_gcs_request(self):
        """Test valid inventory config request with GCS."""
        request = InventoryConfigRequest(
            config=GCSInventoryConfig(
                destination_bucket="bucket",
                report_config_name="config"
            ),
            schedule="daily"
        )
        assert request.config.provider == "gcs"
        assert request.schedule == "daily"

    def test_request_default_schedule(self):
        """Test that schedule defaults to manual."""
        request = InventoryConfigRequest(
            config=S3InventoryConfig(
                destination_bucket="bucket",
                source_bucket="source",
                config_name="config"
            )
        )
        assert request.schedule == "manual"

    def test_request_invalid_schedule(self):
        """Test that invalid schedule is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            InventoryConfigRequest(
                config=S3InventoryConfig(
                    destination_bucket="bucket",
                    source_bucket="source",
                    config_name="config"
                ),
                schedule="hourly"  # not valid
            )
        assert "schedule" in str(exc_info.value)
