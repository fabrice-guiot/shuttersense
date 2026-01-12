"""
Pydantic schemas for performer API request/response validation.

Provides data validation and serialization for:
- Performer creation requests
- Performer update requests
- Performer API responses
- EventPerformer (junction) schemas

Design:
- GUIDs are exposed via guid property, never internal IDs
- Category matching enforced at service layer
- Instagram handle stored without @ symbol
- EventPerformer uses performer_guid, not internal IDs

Issue #39 - Calendar Events feature (Phase 11)
"""

from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator, field_serializer


# ============================================================================
# Embedded Schemas
# ============================================================================


class CategorySummary(BaseModel):
    """
    Minimal category info embedded in performer responses.
    """

    guid: str = Field(..., description="Category GUID (cat_xxx)")
    name: str = Field(..., description="Category name")
    icon: Optional[str] = Field(default=None, description="Lucide icon name")
    color: Optional[str] = Field(default=None, description="Hex color code")

    model_config = {"from_attributes": True}


# ============================================================================
# Performer Request Schemas
# ============================================================================


class PerformerCreate(BaseModel):
    """
    Schema for creating a new performer.

    Required:
        name: Performer display name
        category_guid: Category GUID for this performer

    Optional:
        website: Performer website URL
        instagram_handle: Instagram username (without @)
        additional_info: Additional notes/bio

    Example:
        >>> create = PerformerCreate(
        ...     name="Blue Angels",
        ...     category_guid="cat_01hgw2bbg0000000000000001",
        ...     instagram_handle="usaborngirl"
        ... )
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Performer display name",
    )
    category_guid: str = Field(
        ...,
        description="Category GUID for this performer",
    )
    website: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Performer website URL",
    )
    instagram_handle: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Instagram username (without @)",
    )
    additional_info: Optional[str] = Field(
        default=None,
        description="Additional notes or bio",
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

    @field_validator("instagram_handle")
    @classmethod
    def validate_instagram_handle(cls, v: Optional[str]) -> Optional[str]:
        """Strip @ from instagram handle if present."""
        if v is not None:
            v = v.strip()
            if v:
                # Remove @ if present
                if v.startswith('@'):
                    v = v[1:]
                # Validate format (alphanumeric, underscores, periods)
                if not all(c.isalnum() or c in '._' for c in v):
                    raise ValueError("Instagram handle can only contain letters, numbers, underscores, and periods")
            else:
                return None
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Blue Angels",
                "category_guid": "cat_01hgw2bbg0000000000000001",
                "website": "https://www.blueangels.navy.mil",
                "instagram_handle": "usaborngirl",
                "additional_info": "U.S. Navy flight demonstration squadron",
            }
        }
    }


class PerformerUpdate(BaseModel):
    """
    Schema for updating an existing performer.

    All fields are optional - only provided fields will be updated.

    Fields:
        name: New performer name
        category_guid: New category GUID
        website: New website URL (empty string to clear)
        instagram_handle: New Instagram handle (empty string to clear)
        additional_info: New notes (empty string to clear)

    Example:
        >>> update = PerformerUpdate(instagram_handle="newhandle")
    """

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Performer display name",
    )
    category_guid: Optional[str] = Field(
        default=None,
        description="Category GUID for this performer",
    )
    website: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Performer website URL",
    )
    instagram_handle: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Instagram username (without @)",
    )
    additional_info: Optional[str] = Field(
        default=None,
        description="Additional notes or bio",
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

    @field_validator("instagram_handle")
    @classmethod
    def validate_instagram_handle(cls, v: Optional[str]) -> Optional[str]:
        """Strip @ from instagram handle if present.

        For update schema, empty string means 'clear', None means 'don't update'.
        """
        if v is not None:
            v = v.strip()
            if v:
                # Remove @ if present
                if v.startswith('@'):
                    v = v[1:]
                # Validate format
                if not all(c.isalnum() or c in '._' for c in v):
                    raise ValueError("Instagram handle can only contain letters, numbers, underscores, and periods")
            # Keep empty string - service interprets as 'clear'
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "instagram_handle": "newhandle",
                "additional_info": "Updated bio information",
            }
        }
    }


# ============================================================================
# Performer Response Schemas
# ============================================================================


class PerformerResponse(BaseModel):
    """
    Schema for performer API responses.

    Includes all performer fields with GUID as identifier.

    Fields:
        guid: External identifier (prf_xxx)
        name: Performer display name
        website: Performer website URL
        instagram_handle: Instagram username (without @)
        instagram_url: Full Instagram profile URL (computed)
        category: Embedded category info
        additional_info: Additional notes
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Example:
        >>> response = PerformerResponse.model_validate(performer_obj)
    """

    guid: str = Field(..., description="External identifier (prf_xxx)")
    name: str
    website: Optional[str]
    instagram_handle: Optional[str]
    instagram_url: Optional[str] = Field(
        default=None,
        description="Full Instagram profile URL"
    )
    category: CategorySummary
    additional_info: Optional[str]
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
                "guid": "prf_01hgw2bbg0000000000000001",
                "name": "Blue Angels",
                "website": "https://www.blueangels.navy.mil",
                "instagram_handle": "usaborngirl",
                "instagram_url": "https://www.instagram.com/usaborngirl",
                "category": {
                    "guid": "cat_01hgw2bbg0000000000000001",
                    "name": "Airshow",
                    "icon": "plane",
                    "color": "#3B82F6",
                },
                "additional_info": "U.S. Navy flight demonstration squadron",
                "created_at": "2026-01-10T10:00:00Z",
                "updated_at": "2026-01-10T10:00:00Z",
            }
        },
    }


class PerformerListResponse(BaseModel):
    """
    Schema for list of performers response.

    Fields:
        items: List of performers
        total: Total count

    Example:
        >>> response = PerformerListResponse(items=[...], total=10)
    """

    items: List[PerformerResponse]
    total: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [
                    {
                        "guid": "prf_01hgw2bbg0000000000000001",
                        "name": "Blue Angels",
                        "website": "https://www.blueangels.navy.mil",
                        "instagram_handle": "usaborngirl",
                        "instagram_url": "https://www.instagram.com/usaborngirl",
                        "category": {
                            "guid": "cat_01hgw2bbg0000000000000001",
                            "name": "Airshow",
                            "icon": "plane",
                            "color": "#3B82F6",
                        },
                    }
                ],
                "total": 1,
            }
        }
    }


class PerformerStatsResponse(BaseModel):
    """
    Schema for performer statistics response.

    Fields:
        total_count: Total number of performers
        with_instagram_count: Number with Instagram handle
        with_website_count: Number with website

    Example:
        >>> stats = PerformerStatsResponse(
        ...     total_count=25,
        ...     with_instagram_count=18,
        ...     with_website_count=15
        ... )
    """

    total_count: int = Field(..., ge=0, description="Total number of performers")
    with_instagram_count: int = Field(..., ge=0, description="Number with Instagram")
    with_website_count: int = Field(..., ge=0, description="Number with website")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_count": 25,
                "with_instagram_count": 18,
                "with_website_count": 15,
            }
        }
    }


# ============================================================================
# EventPerformer Schemas (for event-performer associations)
# ============================================================================


PerformerStatusType = Literal["announced", "confirmed", "cancelled"]


class EventPerformerCreate(BaseModel):
    """
    Schema for adding a performer to an event.

    Required:
        performer_guid: GUID of performer to add

    Optional:
        status: Performer status (default: announced)

    Example:
        >>> add = EventPerformerCreate(
        ...     performer_guid="prf_01hgw2bbg0000000000000001",
        ...     status="announced"
        ... )
    """

    performer_guid: str = Field(..., description="Performer GUID to add")
    status: PerformerStatusType = Field(
        default="announced",
        description="Performer status at event"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "performer_guid": "prf_01hgw2bbg0000000000000001",
                "status": "announced",
            }
        }
    }


class EventPerformerUpdate(BaseModel):
    """
    Schema for updating a performer's status at an event.

    Fields:
        status: New performer status

    Example:
        >>> update = EventPerformerUpdate(status="cancelled")
    """

    status: PerformerStatusType = Field(..., description="New performer status")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "cancelled",
            }
        }
    }


class EventPerformerResponse(BaseModel):
    """
    Schema for event-performer association in API responses.

    Fields:
        performer: Performer details
        status: Performer status at this event
        added_at: When performer was added to event

    Example:
        >>> response = EventPerformerResponse.model_validate(event_performer_obj)
    """

    performer: PerformerResponse
    status: PerformerStatusType
    added_at: datetime

    @field_serializer("added_at")
    @classmethod
    def serialize_datetime_utc(cls, v: datetime) -> str:
        """Serialize datetime as ISO 8601 with explicit UTC timezone."""
        return v.isoformat() + "Z" if v else None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "performer": {
                    "guid": "prf_01hgw2bbg0000000000000001",
                    "name": "Blue Angels",
                    "website": "https://www.blueangels.navy.mil",
                    "instagram_handle": "usaborngirl",
                    "instagram_url": "https://www.instagram.com/usaborngirl",
                    "category": {
                        "guid": "cat_01hgw2bbg0000000000000001",
                        "name": "Airshow",
                        "icon": "plane",
                        "color": "#3B82F6",
                    },
                },
                "status": "confirmed",
                "added_at": "2026-01-10T10:00:00Z",
            }
        },
    }


class EventPerformersListResponse(BaseModel):
    """
    Schema for list of performers at an event.

    Fields:
        items: List of event-performer associations
        total: Total count

    Example:
        >>> response = EventPerformersListResponse(items=[...], total=5)
    """

    items: List[EventPerformerResponse]
    total: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [
                    {
                        "performer": {
                            "guid": "prf_01hgw2bbg0000000000000001",
                            "name": "Blue Angels",
                        },
                        "status": "confirmed",
                        "added_at": "2026-01-10T10:00:00Z",
                    }
                ],
                "total": 1,
            }
        }
    }


# ============================================================================
# Performer Summary (for embedding in other responses)
# ============================================================================


class PerformerSummary(BaseModel):
    """
    Minimal performer info for embedding in event responses.
    """

    guid: str = Field(..., description="Performer GUID (prf_xxx)")
    name: str = Field(..., description="Performer name")
    instagram_handle: Optional[str] = Field(default=None)
    status: PerformerStatusType = Field(..., description="Status at this event")

    model_config = {"from_attributes": True}
