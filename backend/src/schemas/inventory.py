"""
Pydantic schemas for inventory import API request/response validation.

Provides data validation and serialization for:
- S3 and GCS inventory configuration
- FileInfo metadata structure
- InventoryFolder responses
- Delta summary tracking
- Collection creation from inventory

Issue #107: Cloud Storage Bucket Inventory Import
"""

from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Inventory Configuration Schemas
# ============================================================================

class S3InventoryConfig(BaseModel):
    """
    AWS S3 Inventory configuration.

    Required fields for locating S3 inventory reports:
    - destination_bucket: Bucket where inventory reports are stored
    - destination_prefix: Optional prefix path within destination bucket
    - source_bucket: Bucket being inventoried
    - config_name: AWS inventory configuration name

    The full inventory path is:
    s3://{destination_bucket}/{destination_prefix}/{source_bucket}/{config_name}/{timestamp}/manifest.json

    Example:
        >>> config = S3InventoryConfig(
        ...     destination_bucket="my-inventory-bucket",
        ...     destination_prefix="Inventories/PhotoArchive",
        ...     source_bucket="my-photo-bucket",
        ...     config_name="daily-inventory"
        ... )
    """
    provider: Literal["s3"] = Field(default="s3", description="Provider type (always 's3')")
    destination_bucket: str = Field(
        ...,
        min_length=3,
        max_length=63,
        description="Bucket where inventory reports are stored"
    )
    destination_prefix: str = Field(
        default="",
        max_length=1024,
        description="Optional prefix path within destination bucket (e.g., 'Inventories/PhotoArchive')"
    )
    source_bucket: str = Field(
        ...,
        min_length=3,
        max_length=63,
        description="Bucket being inventoried"
    )
    config_name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="AWS inventory configuration name"
    )
    format: Literal["CSV", "ORC", "Parquet"] = Field(
        default="CSV",
        description="Inventory file format"
    )

    @field_validator('destination_bucket', 'source_bucket')
    @classmethod
    def validate_bucket_name(cls, v: str) -> str:
        """Validate S3 bucket naming rules."""
        if not v.islower() and not v.replace('-', '').replace('.', '').isalnum():
            # Allow lowercase, numbers, hyphens, and dots
            pass  # S3 bucket names are more permissive
        if v.startswith('-') or v.endswith('-'):
            raise ValueError("Bucket name cannot start or end with hyphen")
        if '..' in v:
            raise ValueError("Bucket name cannot contain consecutive dots")
        return v

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "example": {
                "provider": "s3",
                "destination_bucket": "my-inventory-bucket",
                "destination_prefix": "Inventories/PhotoArchive",
                "source_bucket": "my-photo-bucket",
                "config_name": "daily-inventory",
                "format": "CSV"
            }
        }
    }


class GCSInventoryConfig(BaseModel):
    """
    Google Cloud Storage Insights configuration.

    Required fields for locating GCS inventory reports:
    - destination_bucket: Bucket where inventory reports are stored
    - report_config_name: GCS report configuration name

    Example:
        >>> config = GCSInventoryConfig(
        ...     destination_bucket="my-inventory-bucket",
        ...     report_config_name="photo-inventory"
        ... )
    """
    provider: Literal["gcs"] = Field(default="gcs", description="Provider type (always 'gcs')")
    destination_bucket: str = Field(
        ...,
        min_length=3,
        max_length=63,
        description="Bucket where inventory reports are stored"
    )
    report_config_name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="GCS report configuration name"
    )
    format: Literal["CSV", "Parquet"] = Field(
        default="CSV",
        description="Inventory file format"
    )

    @field_validator('destination_bucket')
    @classmethod
    def validate_bucket_name(cls, v: str) -> str:
        """Validate GCS bucket naming rules."""
        if v.startswith('-') or v.endswith('-'):
            raise ValueError("Bucket name cannot start or end with hyphen")
        return v

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "example": {
                "provider": "gcs",
                "destination_bucket": "my-inventory-bucket",
                "report_config_name": "photo-inventory",
                "format": "CSV"
            }
        }
    }


# Union type for inventory config
InventoryConfigType = S3InventoryConfig | GCSInventoryConfig


# ============================================================================
# FileInfo Schema
# ============================================================================

class FileInfo(BaseModel):
    """
    File metadata from inventory or cloud API.

    Represents a single file's metadata as cached on Collection.

    Fields:
        key: Full object key/path (e.g., "2020/vacation/IMG_001.CR3")
        size: File size in bytes
        last_modified: ISO8601 timestamp of last modification
        etag: Object ETag (optional, for change detection)
        storage_class: Storage class (optional, e.g., "STANDARD", "GLACIER")

    Example:
        >>> info = FileInfo(
        ...     key="2020/vacation/IMG_001.CR3",
        ...     size=25000000,
        ...     last_modified="2022-11-25T13:30:49.000Z"
        ... )
    """
    key: str = Field(..., min_length=1, description="Full object key/path")
    size: int = Field(..., ge=0, description="File size in bytes")
    last_modified: str = Field(..., description="ISO8601 timestamp")
    etag: Optional[str] = Field(default=None, description="Object ETag")
    storage_class: Optional[str] = Field(default=None, description="Storage class")

    model_config = {
        "json_schema_extra": {
            "example": {
                "key": "2020/vacation/IMG_001.CR3",
                "size": 25000000,
                "last_modified": "2022-11-25T13:30:49.000Z",
                "etag": "371e1101d4248ef2609e269697bb0221-2",
                "storage_class": "STANDARD"
            }
        }
    }


# ============================================================================
# Delta Summary Schema
# ============================================================================

class DeltaSummary(BaseModel):
    """
    Summary of changes between inventory imports.

    Tracks counts of new, modified, and deleted files detected during
    inventory import Phase C (Delta Detection).

    Fields:
        new_count: Files in current inventory but not in previous
        modified_count: Files with changed ETag or size
        deleted_count: Files in previous inventory but not in current
        computed_at: ISO8601 timestamp when delta was computed

    Example:
        >>> delta = DeltaSummary(
        ...     new_count=15,
        ...     modified_count=3,
        ...     deleted_count=2,
        ...     computed_at="2026-01-25T10:30:00Z"
        ... )
    """
    new_count: int = Field(default=0, ge=0, description="Count of new files")
    modified_count: int = Field(default=0, ge=0, description="Count of modified files")
    deleted_count: int = Field(default=0, ge=0, description="Count of deleted files")
    computed_at: Optional[str] = Field(default=None, description="ISO8601 timestamp")

    @property
    def total_changes(self) -> int:
        """Total number of changes detected."""
        return self.new_count + self.modified_count + self.deleted_count

    @property
    def has_changes(self) -> bool:
        """Whether any changes were detected."""
        return self.total_changes > 0

    model_config = {
        "json_schema_extra": {
            "example": {
                "new_count": 15,
                "modified_count": 3,
                "deleted_count": 2,
                "computed_at": "2026-01-25T10:30:00Z"
            }
        }
    }


# ============================================================================
# Inventory Folder Schemas
# ============================================================================

class InventoryFolderResponse(BaseModel):
    """
    Response schema for inventory folder.

    Represents a discovered folder from inventory import.

    Fields:
        guid: External identifier (fld_xxx)
        path: Full folder path ending with "/"
        object_count: Number of objects in folder
        total_size_bytes: Sum of object sizes
        deepest_modified: Most recent modification in folder
        discovered_at: When folder was discovered
        collection_guid: GUID of mapped collection (if any)
        suggested_name: Suggested collection name from path

    Example:
        >>> folder = InventoryFolderResponse(
        ...     guid="fld_01hgw2bbg0000000000000001",
        ...     path="2020/Vacation/",
        ...     object_count=150,
        ...     total_size_bytes=3750000000
        ... )
    """
    guid: str = Field(..., description="External identifier (fld_xxx)")
    path: str = Field(..., description="Full folder path")
    object_count: int = Field(..., ge=0, description="Number of objects")
    total_size_bytes: int = Field(..., ge=0, description="Total size in bytes")
    deepest_modified: Optional[datetime] = Field(default=None, description="Most recent modification")
    discovered_at: datetime = Field(..., description="Discovery timestamp")
    collection_guid: Optional[str] = Field(default=None, description="Mapped collection GUID")
    suggested_name: Optional[str] = Field(default=None, description="Suggested collection name")

    @property
    def is_mapped(self) -> bool:
        """Whether folder is mapped to a collection."""
        return self.collection_guid is not None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "guid": "fld_01hgw2bbg0000000000000001",
                "path": "2020/Vacation/",
                "object_count": 150,
                "total_size_bytes": 3750000000,
                "deepest_modified": "2020-08-15T14:30:00Z",
                "discovered_at": "2026-01-25T10:00:00Z",
                "collection_guid": None,
                "suggested_name": "2020 - Vacation"
            }
        }
    }


class InventoryFolderListResponse(BaseModel):
    """
    Paginated list of inventory folders.

    Fields:
        folders: List of folder responses
        total_count: Total number of folders matching query
        has_more: Whether more folders exist beyond this page
    """
    folders: List[InventoryFolderResponse] = Field(..., description="List of folders")
    total_count: int = Field(..., ge=0, description="Total count")
    has_more: bool = Field(..., description="More results available")

    model_config = {
        "json_schema_extra": {
            "example": {
                "folders": [
                    {
                        "guid": "fld_01hgw2bbg0000000000000001",
                        "path": "2020/Vacation/",
                        "object_count": 150,
                        "total_size_bytes": 3750000000
                    }
                ],
                "total_count": 1,
                "has_more": False
            }
        }
    }


# ============================================================================
# Inventory Status Schema
# ============================================================================

class InventoryJobSummary(BaseModel):
    """Summary of current inventory import job."""
    guid: str = Field(..., description="Job GUID (job_xxx)")
    status: str = Field(..., description="Job status")
    phase: Optional[str] = Field(default=None, description="Current pipeline phase")
    progress_percentage: int = Field(default=0, ge=0, le=100, description="Progress percentage")

    model_config = {
        "json_schema_extra": {
            "example": {
                "guid": "job_01hgw2bbg0000000000000001",
                "status": "running",
                "phase": "folder_extraction",
                "progress_percentage": 45
            }
        }
    }


class InventoryStatusResponse(BaseModel):
    """
    Inventory status for a connector.

    Provides current state of inventory configuration and import.
    """
    validation_status: Optional[str] = Field(default=None, description="Validation status")
    validation_error: Optional[str] = Field(default=None, description="Validation error message")
    last_import_at: Optional[datetime] = Field(default=None, description="Last import timestamp")
    next_scheduled_at: Optional[datetime] = Field(default=None, description="Next scheduled import")
    folder_count: int = Field(default=0, ge=0, description="Total discovered folders")
    mapped_folder_count: int = Field(default=0, ge=0, description="Folders mapped to collections")
    current_job: Optional[InventoryJobSummary] = Field(default=None, description="Current running job")

    model_config = {
        "json_schema_extra": {
            "example": {
                "validation_status": "validated",
                "validation_error": None,
                "last_import_at": "2026-01-24T10:00:00Z",
                "next_scheduled_at": "2026-01-25T00:00:00Z",
                "folder_count": 42,
                "mapped_folder_count": 15,
                "current_job": None
            }
        }
    }


# ============================================================================
# Inventory Configuration Request/Response
# ============================================================================

class InventoryConfigRequest(BaseModel):
    """
    Request to configure inventory on a connector.

    Accepts either S3 or GCS configuration based on provider field.
    """
    config: S3InventoryConfig | GCSInventoryConfig = Field(
        ..., description="Inventory configuration"
    )
    schedule: Literal["manual", "daily", "weekly"] = Field(
        default="manual", description="Import schedule"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "config": {
                    "provider": "s3",
                    "destination_bucket": "my-inventory-bucket",
                    "source_bucket": "my-photo-bucket",
                    "config_name": "daily-inventory",
                    "format": "CSV"
                },
                "schedule": "weekly"
            }
        }
    }


class InventoryImportTriggerResponse(BaseModel):
    """Response when triggering inventory import."""
    job_guid: str = Field(..., description="Created job GUID")
    message: str = Field(..., description="Status message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_guid": "job_01hgw2bbg0000000000000001",
                "message": "Inventory import job created"
            }
        }
    }


class InventoryValidationResponse(BaseModel):
    """
    Response from inventory configuration validation.

    For server-side credentials, validation happens synchronously.
    For agent-side credentials, a validation job is created.
    """
    success: bool = Field(..., description="Whether validation succeeded")
    message: str = Field(..., description="Validation result message")
    validation_status: str = Field(..., description="New validation status")
    job_guid: Optional[str] = Field(
        default=None,
        description="Job GUID if validation requires agent (agent credentials)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Found 3 inventory manifest(s)",
                "validation_status": "validated",
                "job_guid": None
            }
        }
    }


# ============================================================================
# Collection Creation from Inventory
# ============================================================================

class FolderToCollectionMapping(BaseModel):
    """
    Mapping request for creating a collection from a folder.

    Fields:
        folder_guid: GUID of the inventory folder
        name: Name for the new collection
        state: Collection state (live, archived, closed)
        pipeline_guid: Optional pipeline to assign
    """
    folder_guid: str = Field(..., description="Folder GUID (fld_xxx)")
    name: str = Field(..., min_length=1, max_length=255, description="Collection name")
    state: Literal["live", "archived", "closed"] = Field(..., description="Collection state")
    pipeline_guid: Optional[str] = Field(default=None, description="Pipeline GUID (pip_xxx)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "folder_guid": "fld_01hgw2bbg0000000000000001",
                "name": "2020 - Vacation",
                "state": "archived",
                "pipeline_guid": None
            }
        }
    }


class CreateCollectionsFromInventoryRequest(BaseModel):
    """
    Request to create multiple collections from inventory folders.

    Fields:
        connector_guid: Connector GUID for the collections
        folders: List of folder-to-collection mappings
    """
    connector_guid: str = Field(..., description="Connector GUID (con_xxx)")
    folders: List[FolderToCollectionMapping] = Field(
        ..., min_length=1, description="Folder mappings"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "connector_guid": "con_01hgw2bbg0000000000000001",
                "folders": [
                    {
                        "folder_guid": "fld_01hgw2bbg0000000000000001",
                        "name": "2020 - Vacation",
                        "state": "archived"
                    },
                    {
                        "folder_guid": "fld_01hgw2bbg0000000000000002",
                        "name": "2021 - Wedding",
                        "state": "closed"
                    }
                ]
            }
        }
    }


class CollectionCreatedSummary(BaseModel):
    """Summary of a successfully created collection."""
    collection_guid: str = Field(..., description="Created collection GUID")
    folder_guid: str = Field(..., description="Source folder GUID")
    name: str = Field(..., description="Collection name")


class CollectionCreationError(BaseModel):
    """Error for a failed collection creation."""
    folder_guid: str = Field(..., description="Source folder GUID")
    error: str = Field(..., description="Error message")


class CreateCollectionsFromInventoryResponse(BaseModel):
    """
    Response from batch collection creation.

    Fields:
        created: Successfully created collections
        errors: Failed creation attempts
    """
    created: List[CollectionCreatedSummary] = Field(
        default_factory=list, description="Created collections"
    )
    errors: List[CollectionCreationError] = Field(
        default_factory=list, description="Creation errors"
    )

    @property
    def success_count(self) -> int:
        """Number of successfully created collections."""
        return len(self.created)

    @property
    def error_count(self) -> int:
        """Number of failed creation attempts."""
        return len(self.errors)

    model_config = {
        "json_schema_extra": {
            "example": {
                "created": [
                    {
                        "collection_guid": "col_01hgw2bbg0000000000000001",
                        "folder_guid": "fld_01hgw2bbg0000000000000001",
                        "name": "2020 - Vacation"
                    }
                ],
                "errors": [
                    {
                        "folder_guid": "fld_01hgw2bbg0000000000000099",
                        "error": "Folder already mapped to a collection"
                    }
                ]
            }
        }
    }
