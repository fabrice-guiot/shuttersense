"""
Pydantic schemas for category API request/response validation.

Provides data validation and serialization for:
- Category creation requests
- Category update requests
- Category API responses
- Category statistics

Design:
- Strict validation for color format (hex)
- Validates icon names are non-empty strings
- GUIDs are exposed via guid property, never internal IDs
"""

import re
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, field_serializer

from backend.src.schemas.audit import AuditInfo


# ============================================================================
# Category Request Schemas
# ============================================================================


class CategoryCreate(BaseModel):
    """
    Schema for creating a new category.

    Required:
        name: Category name (unique, case-insensitive)

    Optional:
        icon: Lucide icon name (e.g., "plane", "bird")
        color: Hex color code (e.g., "#3B82F6")
        is_active: Whether category is active (default: True)
        display_order: Sort order in UI (auto-assigned if not provided)

    Example:
        >>> create = CategoryCreate(
        ...     name="Airshow",
        ...     icon="plane",
        ...     color="#3B82F6"
        ... )
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Category name (unique)",
    )
    icon: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Lucide icon name",
    )
    color: Optional[str] = Field(
        default=None,
        max_length=7,
        description="Hex color code (e.g., #3B82F6)",
    )
    is_active: bool = Field(
        default=True,
        description="Whether category is active",
    )
    display_order: Optional[int] = Field(
        default=None,
        ge=0,
        description="Sort order in UI (auto-assigned if not provided)",
    )

    @field_validator("color")
    @classmethod
    def validate_color_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate hex color format."""
        if v is None or v == "":
            return v
        if not re.match(r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$", v):
            raise ValueError("Color must be hex format like #RGB or #RRGGBB")
        return v

    @field_validator("icon")
    @classmethod
    def validate_icon_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """Ensure icon is not empty string."""
        if v is not None and v.strip() == "":
            return None
        return v

    @field_validator("name")
    @classmethod
    def validate_name_not_whitespace(cls, v: str) -> str:
        """Ensure name is not just whitespace."""
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Airshow",
                "icon": "plane",
                "color": "#3B82F6",
                "is_active": True,
            }
        }
    }


class CategoryUpdate(BaseModel):
    """
    Schema for updating an existing category.

    All fields are optional - only provided fields will be updated.

    Fields:
        name: New category name
        icon: New icon name (null to clear)
        color: New color code (null to clear)
        is_active: New active status

    Example:
        >>> update = CategoryUpdate(name="Aviation Events", color="#1E40AF")
    """

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Category name",
    )
    icon: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Lucide icon name (null to clear)",
    )
    color: Optional[str] = Field(
        default=None,
        max_length=7,
        description="Hex color code (null to clear)",
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Whether category is active",
    )

    @field_validator("color")
    @classmethod
    def validate_color_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate hex color format."""
        if v is None or v == "":
            return v
        if not re.match(r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$", v):
            raise ValueError("Color must be hex format like #RGB or #RRGGBB")
        return v

    @field_validator("name")
    @classmethod
    def validate_name_not_whitespace(cls, v: Optional[str]) -> Optional[str]:
        """Ensure name is not just whitespace."""
        if v is not None and not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip() if v else None

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Aviation Events",
                "color": "#1E40AF",
            }
        }
    }


class CategoryReorderRequest(BaseModel):
    """
    Schema for reordering categories.

    Fields:
        ordered_guids: List of category GUIDs in desired order

    Example:
        >>> reorder = CategoryReorderRequest(
        ...     ordered_guids=["cat_xxx1", "cat_xxx2", "cat_xxx3"]
        ... )
    """

    ordered_guids: List[str] = Field(
        ...,
        min_length=1,
        description="List of category GUIDs in desired display order",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "ordered_guids": [
                    "cat_01hgw2bbg0000000000000001",
                    "cat_01hgw2bbg0000000000000002",
                    "cat_01hgw2bbg0000000000000003",
                ]
            }
        }
    }


# ============================================================================
# Category Response Schemas
# ============================================================================


class CategoryResponse(BaseModel):
    """
    Schema for category API responses.

    Includes all category fields with GUID as identifier.

    Fields:
        guid: External identifier (cat_xxx)
        name: Category name
        icon: Lucide icon name
        color: Hex color code
        is_active: Whether category is active
        display_order: Sort order in UI
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Example:
        >>> response = CategoryResponse.model_validate(category_obj)
    """

    guid: str = Field(..., description="External identifier (cat_xxx)")
    name: str
    icon: Optional[str]
    color: Optional[str]
    is_active: bool
    display_order: int
    created_at: datetime
    updated_at: datetime
    audit: Optional[AuditInfo] = None

    @field_serializer("created_at", "updated_at")
    @classmethod
    def serialize_datetime_utc(cls, v: datetime) -> str:
        """Serialize datetime as ISO 8601 with explicit UTC timezone (Z suffix)."""
        return v.isoformat() + "Z" if v else None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "guid": "cat_01hgw2bbg0000000000000001",
                "name": "Airshow",
                "icon": "plane",
                "color": "#3B82F6",
                "is_active": True,
                "display_order": 0,
                "created_at": "2026-01-10T10:00:00Z",
                "updated_at": "2026-01-10T10:00:00Z",
            }
        },
    }


class CategoryListResponse(BaseModel):
    """
    Schema for list of categories response.

    Fields:
        items: List of categories
        total: Total count

    Example:
        >>> response = CategoryListResponse(items=[...], total=7)
    """

    items: List[CategoryResponse]
    total: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [
                    {
                        "guid": "cat_01hgw2bbg0000000000000001",
                        "name": "Airshow",
                        "icon": "plane",
                        "color": "#3B82F6",
                        "is_active": True,
                        "display_order": 0,
                        "created_at": "2026-01-10T10:00:00Z",
                        "updated_at": "2026-01-10T10:00:00Z",
                    }
                ],
                "total": 1,
            }
        }
    }


class CategoryStatsResponse(BaseModel):
    """
    Schema for category statistics response.

    Fields:
        total_count: Total number of categories
        active_count: Number of active categories
        inactive_count: Number of inactive categories

    Example:
        >>> stats = CategoryStatsResponse(total_count=7, active_count=6, inactive_count=1)
    """

    total_count: int = Field(..., ge=0, description="Total number of categories")
    active_count: int = Field(..., ge=0, description="Number of active categories")
    inactive_count: int = Field(..., ge=0, description="Number of inactive categories")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_count": 7,
                "active_count": 6,
                "inactive_count": 1,
            }
        }
    }
