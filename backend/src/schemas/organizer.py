"""
Pydantic schemas for organizer API request/response validation.

Provides data validation and serialization for:
- Organizer creation requests
- Organizer update requests
- Organizer API responses

Design:
- GUIDs are exposed via guid property, never internal IDs
- Rating must be 1-5
- Category matching enforced at service layer
- ticket_required_default applied to new events by organizer

Issue #39 - Calendar Events feature (Phase 9)
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, field_serializer, HttpUrl


# ============================================================================
# Embedded Schemas
# ============================================================================


class CategorySummary(BaseModel):
    """
    Minimal category info embedded in organizer responses.
    """

    guid: str = Field(..., description="Category GUID (cat_xxx)")
    name: str = Field(..., description="Category name")
    icon: Optional[str] = Field(default=None, description="Lucide icon name")
    color: Optional[str] = Field(default=None, description="Hex color code")

    model_config = {"from_attributes": True}


# ============================================================================
# Organizer Request Schemas
# ============================================================================


class OrganizerCreate(BaseModel):
    """
    Schema for creating a new organizer.

    Required:
        name: Organizer display name
        category_guid: Category GUID for this organizer

    Optional:
        website: Organizer website URL
        rating: Organizer rating (1-5 stars)
        ticket_required_default: Pre-select ticket required for new events
        notes: Additional notes

    Example:
        >>> create = OrganizerCreate(
        ...     name="Live Nation",
        ...     category_guid="cat_01hgw2bbg0000000000000001",
        ...     website="https://livenation.com",
        ...     rating=4
        ... )
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Organizer display name",
    )
    category_guid: str = Field(
        ...,
        description="Category GUID for this organizer",
    )
    website: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Organizer website URL",
    )
    rating: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="Organizer rating (1-5 stars)",
    )
    ticket_required_default: bool = Field(
        default=False,
        description="Pre-select ticket required for new events by this organizer",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes",
    )

    @field_validator("name")
    @classmethod
    def validate_name_not_whitespace(cls, v: str) -> str:
        """Ensure name is not just whitespace."""
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()

    @field_validator("website")
    @classmethod
    def validate_website_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate website URL format if provided."""
        if v is not None:
            v = v.strip()
            if v:
                # Accept URLs with or without protocol
                if not v.startswith(('http://', 'https://')):
                    v = f'https://{v}'
            else:
                return None
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Live Nation",
                "category_guid": "cat_01hgw2bbg0000000000000001",
                "website": "https://livenation.com",
                "rating": 4,
                "ticket_required_default": True,
                "notes": "Major concert promoter",
            }
        }
    }


class OrganizerUpdate(BaseModel):
    """
    Schema for updating an existing organizer.

    All fields are optional - only provided fields will be updated.

    Fields:
        name: New organizer name
        category_guid: New category GUID
        website: New website URL (null to clear)
        rating: New rating (null to clear)
        ticket_required_default: New ticket default
        notes: New notes (null to clear)

    Example:
        >>> update = OrganizerUpdate(rating=5, notes="Great organizer")
    """

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Organizer display name",
    )
    category_guid: Optional[str] = Field(
        default=None,
        description="Category GUID for this organizer",
    )
    website: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Organizer website URL",
    )
    rating: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="Organizer rating (1-5 stars)",
    )
    ticket_required_default: Optional[bool] = Field(
        default=None,
        description="Pre-select ticket required for new events",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes",
    )

    @field_validator("name")
    @classmethod
    def validate_name_not_whitespace(cls, v: Optional[str]) -> Optional[str]:
        """Ensure name is not just whitespace."""
        if v is not None and not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip() if v else None

    @field_validator("website")
    @classmethod
    def validate_website_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate website URL format if provided.

        For update schema, empty string means 'clear', None means 'don't update'.
        """
        if v is not None:
            v = v.strip()
            if v:
                # Accept URLs with or without protocol
                if not v.startswith(('http://', 'https://')):
                    v = f'https://{v}'
            # Keep empty string - service interprets as 'clear'
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "rating": 5,
                "notes": "Great organizer, always well-organized events",
            }
        }
    }


# ============================================================================
# Organizer Response Schemas
# ============================================================================


class OrganizerResponse(BaseModel):
    """
    Schema for organizer API responses.

    Includes all organizer fields with GUID as identifier.

    Fields:
        guid: External identifier (org_xxx)
        name: Organizer display name
        website: Organizer website URL
        category: Embedded category info
        rating: Organizer rating (1-5 stars)
        ticket_required_default: Default ticket setting for events
        notes: Additional notes
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Example:
        >>> response = OrganizerResponse.model_validate(organizer_obj)
    """

    guid: str = Field(..., description="External identifier (org_xxx)")
    name: str
    website: Optional[str]
    category: CategorySummary
    rating: Optional[int]
    ticket_required_default: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    @classmethod
    def serialize_datetime_utc(cls, v: datetime) -> str:
        """Serialize datetime as ISO 8601 with explicit UTC timezone (Z suffix)."""
        return v.isoformat() + "Z" if v else None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "guid": "org_01hgw2bbg0000000000000001",
                "name": "Live Nation",
                "website": "https://livenation.com",
                "category": {
                    "guid": "cat_01hgw2bbg0000000000000001",
                    "name": "Concert",
                    "icon": "music",
                    "color": "#8B5CF6",
                },
                "rating": 4,
                "ticket_required_default": True,
                "notes": "Major concert promoter",
                "created_at": "2026-01-10T10:00:00Z",
                "updated_at": "2026-01-10T10:00:00Z",
            }
        },
    }


class OrganizerListResponse(BaseModel):
    """
    Schema for list of organizers response.

    Fields:
        items: List of organizers
        total: Total count

    Example:
        >>> response = OrganizerListResponse(items=[...], total=10)
    """

    items: List[OrganizerResponse]
    total: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [
                    {
                        "guid": "org_01hgw2bbg0000000000000001",
                        "name": "Live Nation",
                        "website": "https://livenation.com",
                        "category": {
                            "guid": "cat_01hgw2bbg0000000000000001",
                            "name": "Concert",
                            "icon": "music",
                            "color": "#8B5CF6",
                        },
                        "rating": 4,
                        "ticket_required_default": True,
                    }
                ],
                "total": 1,
            }
        }
    }


class OrganizerStatsResponse(BaseModel):
    """
    Schema for organizer statistics response.

    Fields:
        total_count: Total number of organizers
        with_rating_count: Number with ratings assigned
        avg_rating: Average rating across rated organizers

    Example:
        >>> stats = OrganizerStatsResponse(
        ...     total_count=15,
        ...     with_rating_count=12,
        ...     avg_rating=3.8
        ... )
    """

    total_count: int = Field(..., ge=0, description="Total number of organizers")
    with_rating_count: int = Field(..., ge=0, description="Number with ratings")
    avg_rating: Optional[float] = Field(
        default=None, ge=1, le=5, description="Average rating"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_count": 15,
                "with_rating_count": 12,
                "avg_rating": 3.8,
            }
        }
    }
