"""
Pydantic schemas for configuration API request/response validation.

Provides data validation and serialization for:
- Configuration CRUD operations
- YAML import with conflict detection
- Conflict resolution
- Statistics for KPIs

Design:
- Uses JSONB for flexible value storage
- Supports multiple value types (arrays, objects, strings)
- Session-based import with conflict resolution
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field


class ConfigCategory(str, Enum):
    """Valid configuration categories."""
    EXTENSIONS = "extensions"
    CAMERAS = "cameras"
    PROCESSING_METHODS = "processing_methods"


class ConfigSourceType(str, Enum):
    """Source of configuration value."""
    DATABASE = "database"
    YAML_IMPORT = "yaml_import"


class ImportSessionStatus(str, Enum):
    """Status of an import session."""
    PENDING = "pending"
    RESOLVED = "resolved"
    APPLIED = "applied"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ConflictResolution(str, Enum):
    """How a conflict was resolved."""
    USE_DATABASE = "use_database"
    USE_YAML = "use_yaml"


# ============================================================================
# Request Schemas
# ============================================================================

class ConfigItemCreate(BaseModel):
    """
    Request to create a configuration item.

    Note: category and key are provided as path parameters, not in the body.
    """
    value: Any = Field(
        ...,
        description="Configuration value (array, object, or string)"
    )
    description: Optional[str] = Field(
        None,
        description="Human-readable description"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "value": {"name": "Canon EOS R5", "serial_number": "12345"},
                "description": "Primary camera"
            }
        }
    }


class ConfigItemUpdate(BaseModel):
    """
    Request to update a configuration item.
    """
    value: Optional[Any] = Field(
        None,
        description="New configuration value"
    )
    description: Optional[str] = Field(
        None,
        description="Updated description"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "value": {"name": "Canon EOS R5", "serial_number": "12345-updated"},
                "description": "Primary camera (updated)"
            }
        }
    }


class ConflictResolutionItem(BaseModel):
    """
    Resolution for a single conflict.
    """
    category: str = Field(..., description="Configuration category")
    key: str = Field(..., description="Configuration key")
    use_yaml: bool = Field(..., description="True to use YAML value, False to keep database")


class ConflictResolutionRequest(BaseModel):
    """
    Request to resolve conflicts and apply import.
    """
    resolutions: List[ConflictResolutionItem] = Field(
        ...,
        description="List of conflict resolutions"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "resolutions": [
                    {"category": "cameras", "key": "AB3D", "use_yaml": True},
                    {"category": "extensions", "key": "photo_extensions", "use_yaml": False}
                ]
            }
        }
    }


# ============================================================================
# Response Schemas
# ============================================================================

class ConfigItemResponse(BaseModel):
    """
    Configuration item details.
    """
    id: int = Field(..., description="Configuration item ID")
    category: str = Field(..., description="Configuration category")
    key: str = Field(..., description="Configuration key")
    value: Any = Field(..., description="Configuration value")
    description: Optional[str] = Field(None, description="Description")
    source: str = Field(..., description="Source: 'database' or 'yaml_import'")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "category": "cameras",
                "key": "AB3D",
                "value": {"name": "Canon EOS R5", "serial_number": "12345"},
                "description": "Primary camera",
                "source": "database",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T14:45:00Z"
            }
        }
    }


class CategoryConfigResponse(BaseModel):
    """
    Configuration items for a specific category.
    """
    category: str = Field(..., description="Category name")
    items: List[ConfigItemResponse] = Field(..., description="Items in this category")

    model_config = {
        "json_schema_extra": {
            "example": {
                "category": "cameras",
                "items": []
            }
        }
    }


class ConfigurationResponse(BaseModel):
    """
    All configuration organized by category.
    """
    extensions: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extension configuration"
    )
    cameras: Dict[str, Any] = Field(
        default_factory=dict,
        description="Camera mappings"
    )
    processing_methods: Dict[str, str] = Field(
        default_factory=dict,
        description="Processing method descriptions"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "extensions": {
                    "photo_extensions": [".dng", ".cr3"],
                    "metadata_extensions": [".xmp"],
                    "require_sidecar": [".cr3"]
                },
                "cameras": {
                    "AB3D": {"name": "Canon EOS R5", "serial_number": "12345"}
                },
                "processing_methods": {
                    "HDR": "High Dynamic Range",
                    "BW": "Black and White"
                }
            }
        }
    }


class ConfigConflict(BaseModel):
    """
    A conflict between database and YAML values.
    """
    category: str = Field(..., description="Configuration category")
    key: str = Field(..., description="Configuration key")
    database_value: Any = Field(..., description="Current database value")
    yaml_value: Any = Field(..., description="Value from YAML file")
    resolved: bool = Field(False, description="Whether conflict is resolved")
    resolution: Optional[str] = Field(
        None,
        description="Resolution choice: 'use_database' or 'use_yaml'"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "category": "cameras",
                "key": "AB3D",
                "database_value": {"name": "Canon EOS R5", "serial_number": "12345"},
                "yaml_value": {"name": "Canon EOS R5", "serial_number": "67890"},
                "resolved": False,
                "resolution": None
            }
        }
    }


class ImportSessionResponse(BaseModel):
    """
    Import session details with conflicts.
    """
    session_id: str = Field(..., description="Session GUID (imp_xxx format)")
    status: str = Field(..., description="Session status")
    expires_at: datetime = Field(..., description="Session expiration time")
    file_name: Optional[str] = Field(None, description="Original filename")
    total_items: int = Field(..., description="Total items in YAML")
    new_items: int = Field(..., description="New items (no conflict)")
    conflicts: List[ConfigConflict] = Field(
        default_factory=list,
        description="Items with conflicts"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "imp_01hgw2bbg0000000000000001",
                "status": "pending",
                "expires_at": "2024-01-15T11:30:00Z",
                "file_name": "config.yaml",
                "total_items": 15,
                "new_items": 12,
                "conflicts": []
            }
        }
    }


class ImportResultResponse(BaseModel):
    """
    Result of applying an import.
    """
    success: bool = Field(..., description="Whether import succeeded")
    items_imported: int = Field(..., description="Number of items imported")
    items_skipped: int = Field(..., description="Number of items skipped")
    message: str = Field(..., description="Result message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "items_imported": 15,
                "items_skipped": 2,
                "message": "Import completed successfully"
            }
        }
    }


class ConfigStatsResponse(BaseModel):
    """
    Configuration statistics for KPIs.
    """
    total_items: int = Field(0, ge=0, description="Total configuration items")
    cameras_configured: int = Field(0, ge=0, description="Number of camera mappings")
    processing_methods_configured: int = Field(
        0, ge=0,
        description="Number of processing methods"
    )
    last_import: Optional[datetime] = Field(
        None,
        description="Last YAML import timestamp"
    )
    source_breakdown: Dict[str, int] = Field(
        default_factory=dict,
        description="Count by source type"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_items": 42,
                "cameras_configured": 5,
                "processing_methods_configured": 8,
                "last_import": "2024-01-15T10:30:00Z",
                "source_breakdown": {
                    "database": 30,
                    "yaml_import": 12
                }
            }
        }
    }


class DeleteResponse(BaseModel):
    """
    Response after deleting a configuration item.
    """
    message: str = Field(..., description="Confirmation message")
    deleted_id: int = Field(..., description="ID of deleted item")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Configuration deleted successfully",
                "deleted_id": 1
            }
        }
    }
