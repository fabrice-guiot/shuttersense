"""
Pydantic schemas for location API request/response validation.

Provides data validation and serialization for:
- Location creation requests
- Location update requests
- Location API responses
- Geocoding requests/responses

Design:
- GUIDs are exposed via guid property, never internal IDs
- Latitude/longitude validated for valid coordinate ranges
- Rating must be 1-5
- Category matching enforced at service layer
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, field_serializer


# ============================================================================
# Embedded Schemas
# ============================================================================


class CategorySummary(BaseModel):
    """
    Minimal category info embedded in location responses.
    """

    guid: str = Field(..., description="Category GUID (cat_xxx)")
    name: str = Field(..., description="Category name")
    icon: Optional[str] = Field(default=None, description="Lucide icon name")
    color: Optional[str] = Field(default=None, description="Hex color code")

    model_config = {"from_attributes": True}


# ============================================================================
# Geocoding Schemas
# ============================================================================


class GeocodeRequest(BaseModel):
    """
    Schema for geocoding an address.

    Fields:
        address: Full address string to geocode

    Example:
        >>> request = GeocodeRequest(address="1600 Pennsylvania Avenue, Washington, DC")
    """

    address: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Full address to geocode",
    )

    @field_validator("address")
    @classmethod
    def validate_address_not_whitespace(cls, v: str) -> str:
        """Ensure address is not just whitespace."""
        if not v.strip():
            raise ValueError("Address cannot be empty or whitespace")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "address": "1600 Pennsylvania Avenue, Washington, DC, USA"
            }
        }
    }


class GeocodeResponse(BaseModel):
    """
    Schema for geocoding result.

    Fields:
        address: Formatted address
        city: City name
        state: State/province
        country: Country name
        postal_code: ZIP/postal code
        latitude: Geocoded latitude
        longitude: Geocoded longitude
        timezone: IANA timezone identifier

    Example:
        >>> response = GeocodeResponse(
        ...     address="1600 Pennsylvania Avenue NW",
        ...     city="Washington",
        ...     state="District of Columbia",
        ...     country="United States",
        ...     latitude=38.8977,
        ...     longitude=-77.0365,
        ...     timezone="America/New_York"
        ... )
    """

    address: Optional[str] = Field(default=None, description="Formatted address")
    city: Optional[str] = Field(default=None, description="City name")
    state: Optional[str] = Field(default=None, description="State/province")
    country: Optional[str] = Field(default=None, description="Country name")
    postal_code: Optional[str] = Field(default=None, description="ZIP/postal code")
    latitude: Decimal = Field(..., description="Geocoded latitude")
    longitude: Decimal = Field(..., description="Geocoded longitude")
    timezone: Optional[str] = Field(default=None, description="IANA timezone identifier")

    model_config = {
        "json_schema_extra": {
            "example": {
                "address": "1600 Pennsylvania Avenue NW",
                "city": "Washington",
                "state": "District of Columbia",
                "country": "United States",
                "postal_code": "20500",
                "latitude": 38.8977,
                "longitude": -77.0365,
                "timezone": "America/New_York",
            }
        }
    }


# ============================================================================
# Location Request Schemas
# ============================================================================


class LocationCreate(BaseModel):
    """
    Schema for creating a new location.

    Required:
        name: Location display name
        category_guid: Category GUID for this location

    Optional:
        address: Full street address
        city: City name
        state: State/province
        country: Country name
        postal_code: ZIP/postal code
        latitude: Geocoded latitude (-90 to 90)
        longitude: Geocoded longitude (-180 to 180)
        timezone: IANA timezone identifier
        rating: Location rating (1-5)
        timeoff_required_default: Default time-off setting for events
        travel_required_default: Default travel setting for events
        notes: Additional notes
        is_known: Whether this is a saved "known location"

    Example:
        >>> create = LocationCreate(
        ...     name="Madison Square Garden",
        ...     category_guid="cat_01hgw2bbg0000000000000001",
        ...     city="New York",
        ...     country="United States",
        ...     rating=5
        ... )
    """

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Location display name",
    )
    category_guid: str = Field(
        ...,
        description="Category GUID for this location",
    )
    address: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Full street address",
    )
    city: Optional[str] = Field(
        default=None,
        max_length=100,
        description="City name",
    )
    state: Optional[str] = Field(
        default=None,
        max_length=100,
        description="State/province",
    )
    country: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Country name",
    )
    postal_code: Optional[str] = Field(
        default=None,
        max_length=20,
        description="ZIP/postal code",
    )
    latitude: Optional[Decimal] = Field(
        default=None,
        ge=-90,
        le=90,
        description="Geocoded latitude (-90 to 90)",
    )
    longitude: Optional[Decimal] = Field(
        default=None,
        ge=-180,
        le=180,
        description="Geocoded longitude (-180 to 180)",
    )
    timezone: Optional[str] = Field(
        default=None,
        max_length=64,
        description="IANA timezone identifier",
    )
    rating: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="Location rating (1-5)",
    )
    timeoff_required_default: bool = Field(
        default=False,
        description="Default time-off setting for events at this location",
    )
    travel_required_default: bool = Field(
        default=False,
        description="Default travel setting for events at this location",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes",
    )
    is_known: bool = Field(
        default=True,
        description="Whether this is a saved 'known location'",
    )

    @field_validator("name")
    @classmethod
    def validate_name_not_whitespace(cls, v: str) -> str:
        """Ensure name is not just whitespace."""
        if not v.strip():
            raise ValueError("Name cannot be empty or whitespace")
        return v.strip()

    @field_validator("latitude", "longitude")
    @classmethod
    def validate_coordinates_together(cls, v, info):
        """Note: Cross-field validation done at service layer."""
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Madison Square Garden",
                "category_guid": "cat_01hgw2bbg0000000000000001",
                "address": "4 Pennsylvania Plaza",
                "city": "New York",
                "state": "New York",
                "country": "United States",
                "postal_code": "10001",
                "latitude": 40.7505,
                "longitude": -73.9934,
                "timezone": "America/New_York",
                "rating": 5,
                "timeoff_required_default": False,
                "travel_required_default": True,
                "is_known": True,
            }
        }
    }


class LocationUpdate(BaseModel):
    """
    Schema for updating an existing location.

    All fields are optional - only provided fields will be updated.

    Fields:
        name: New location name
        category_guid: New category GUID
        address: New street address
        city: New city
        state: New state
        country: New country
        postal_code: New postal code
        latitude: New latitude (null to clear)
        longitude: New longitude (null to clear)
        timezone: New timezone (null to clear)
        rating: New rating (null to clear)
        timeoff_required_default: New time-off default
        travel_required_default: New travel default
        notes: New notes (null to clear)
        is_known: Update known status

    Example:
        >>> update = LocationUpdate(rating=4, notes="Great venue")
    """

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Location display name",
    )
    category_guid: Optional[str] = Field(
        default=None,
        description="Category GUID for this location",
    )
    address: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Full street address",
    )
    city: Optional[str] = Field(
        default=None,
        max_length=100,
        description="City name",
    )
    state: Optional[str] = Field(
        default=None,
        max_length=100,
        description="State/province",
    )
    country: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Country name",
    )
    postal_code: Optional[str] = Field(
        default=None,
        max_length=20,
        description="ZIP/postal code",
    )
    latitude: Optional[Decimal] = Field(
        default=None,
        ge=-90,
        le=90,
        description="Geocoded latitude",
    )
    longitude: Optional[Decimal] = Field(
        default=None,
        ge=-180,
        le=180,
        description="Geocoded longitude",
    )
    timezone: Optional[str] = Field(
        default=None,
        max_length=64,
        description="IANA timezone identifier",
    )
    rating: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="Location rating (1-5)",
    )
    timeoff_required_default: Optional[bool] = Field(
        default=None,
        description="Default time-off setting for events",
    )
    travel_required_default: Optional[bool] = Field(
        default=None,
        description="Default travel setting for events",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes",
    )
    is_known: Optional[bool] = Field(
        default=None,
        description="Whether this is a saved 'known location'",
    )

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
                "rating": 4,
                "notes": "Great venue, easy parking",
            }
        }
    }


# ============================================================================
# Location Response Schemas
# ============================================================================


class LocationResponse(BaseModel):
    """
    Schema for location API responses.

    Includes all location fields with GUID as identifier.

    Fields:
        guid: External identifier (loc_xxx)
        name: Location display name
        address: Full street address
        city: City name
        state: State/province
        country: Country name
        postal_code: ZIP/postal code
        latitude: Geocoded latitude
        longitude: Geocoded longitude
        timezone: IANA timezone identifier
        category: Embedded category info
        rating: Location rating (1-5)
        timeoff_required_default: Default time-off setting
        travel_required_default: Default travel setting
        notes: Additional notes
        is_known: Whether this is a saved location
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Example:
        >>> response = LocationResponse.model_validate(location_obj)
    """

    guid: str = Field(..., description="External identifier (loc_xxx)")
    name: str
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]
    postal_code: Optional[str]
    latitude: Optional[Decimal]
    longitude: Optional[Decimal]
    timezone: Optional[str]
    category: CategorySummary
    rating: Optional[int]
    timeoff_required_default: bool
    travel_required_default: bool
    notes: Optional[str]
    is_known: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    @classmethod
    def serialize_datetime_utc(cls, v: datetime) -> str:
        """Serialize datetime as ISO 8601 with explicit UTC timezone (Z suffix)."""
        return v.isoformat() + "Z" if v else None

    @field_serializer("latitude", "longitude")
    @classmethod
    def serialize_decimal(cls, v: Optional[Decimal]) -> Optional[float]:
        """Serialize Decimal as float for JSON."""
        return float(v) if v is not None else None

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "guid": "loc_01hgw2bbg0000000000000001",
                "name": "Madison Square Garden",
                "address": "4 Pennsylvania Plaza",
                "city": "New York",
                "state": "New York",
                "country": "United States",
                "postal_code": "10001",
                "latitude": 40.7505,
                "longitude": -73.9934,
                "timezone": "America/New_York",
                "category": {
                    "guid": "cat_01hgw2bbg0000000000000001",
                    "name": "Concert",
                    "icon": "music",
                    "color": "#8B5CF6",
                },
                "rating": 5,
                "timeoff_required_default": False,
                "travel_required_default": True,
                "notes": "Great venue for concerts",
                "is_known": True,
                "created_at": "2026-01-10T10:00:00Z",
                "updated_at": "2026-01-10T10:00:00Z",
            }
        },
    }


class LocationListResponse(BaseModel):
    """
    Schema for list of locations response.

    Fields:
        items: List of locations
        total: Total count

    Example:
        >>> response = LocationListResponse(items=[...], total=10)
    """

    items: List[LocationResponse]
    total: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [
                    {
                        "guid": "loc_01hgw2bbg0000000000000001",
                        "name": "Madison Square Garden",
                        "city": "New York",
                        "country": "United States",
                        "timezone": "America/New_York",
                        "category": {
                            "guid": "cat_01hgw2bbg0000000000000001",
                            "name": "Concert",
                            "icon": "music",
                            "color": "#8B5CF6",
                        },
                        "rating": 5,
                        "is_known": True,
                    }
                ],
                "total": 1,
            }
        }
    }


class LocationStatsResponse(BaseModel):
    """
    Schema for location statistics response.

    Fields:
        total_count: Total number of locations
        known_count: Number of saved "known" locations
        with_coordinates_count: Number with geocoded coordinates

    Example:
        >>> stats = LocationStatsResponse(
        ...     total_count=25,
        ...     known_count=20,
        ...     with_coordinates_count=18
        ... )
    """

    total_count: int = Field(..., ge=0, description="Total number of locations")
    known_count: int = Field(..., ge=0, description="Number of known locations")
    with_coordinates_count: int = Field(
        ..., ge=0, description="Number with geocoded coordinates"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_count": 25,
                "known_count": 20,
                "with_coordinates_count": 18,
            }
        }
    }
