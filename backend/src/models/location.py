"""
Location model for event venues.

Locations represent physical venues where events take place. They include
geocoded coordinates for timezone resolution and default logistics settings.

Design Rationale:
- Geocoded coordinates enable automatic timezone detection
- Category matching ensures events and locations are compatible
- Default logistics (timeoff_required, travel_required) are applied to new events
- Rating (1-5) helps prioritize favorite venues
- is_known flag distinguishes saved locations from one-time entries
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, Index, Numeric
)
from sqlalchemy.orm import relationship

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin


class Location(Base, GuidMixin):
    """
    Event location model.

    Represents a physical venue for events with geocoding support,
    timezone information, and default logistics settings.

    Attributes:
        id: Primary key (internal, never exposed)
        uuid: UUIDv7 for external identification (inherited from GuidMixin)
        guid: GUID string property (loc_xxx, inherited from GuidMixin)
        name: Location display name
        address: Full street address
        city: City name
        state: State/province
        country: Country name
        postal_code: ZIP/postal code
        instagram_handle: Instagram username (without @)
        latitude: Geocoded latitude (Decimal 10,7)
        longitude: Geocoded longitude (Decimal 10,7)
        timezone: IANA timezone identifier (e.g., "America/New_York")
        category_id: Foreign key to categories (must match event category)
        rating: Location rating 1-5 (displayed as camera icons)
        timeoff_required_default: Pre-select time-off for new events
        travel_required_default: Pre-select travel for new events
        notes: Additional notes
        is_known: Whether this is a saved "known location"
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Relationships:
        category: Parent category (many-to-one, RESTRICT on delete)
        events: Events at this location (one-to-many, SET NULL on delete)
        event_series: Event series at this location (one-to-many, SET NULL on delete)

    Constraints:
        - category_id is required
        - If coordinates provided, both latitude and longitude required
        - rating must be 1-5 if provided
        - category must be active

    Indexes:
        - uuid (unique, for GUID lookups)
        - category_id (for filtering by category)
        - is_known, category_id (for known locations lookup)
    """

    __tablename__ = "locations"

    # GUID prefix for Location entities
    GUID_PREFIX = "loc"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Tenant isolation
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)

    # Foreign key to category
    category_id = Column(
        Integer,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # Core fields
    name = Column(String(255), nullable=False)
    address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    instagram_handle = Column(String(100), nullable=True)  # Without @

    # Geocoding fields
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)
    timezone = Column(String(64), nullable=True)  # IANA timezone

    # Rating and defaults
    rating = Column(Integer, nullable=True)  # 1-5
    timeoff_required_default = Column(Boolean, default=False, nullable=False)
    travel_required_default = Column(Boolean, default=False, nullable=False)

    # Additional info
    notes = Column(Text, nullable=True)
    is_known = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    category = relationship("Category", back_populates="locations")
    events = relationship(
        "Event",
        back_populates="location",
        lazy="dynamic"
    )
    event_series = relationship(
        "EventSeries",
        back_populates="location",
        lazy="dynamic"
    )

    # Table-level indexes
    __table_args__ = (
        Index(
            "idx_locations_known_category",
            "is_known",
            "category_id",
        ),
    )

    @property
    def has_coordinates(self) -> bool:
        """Check if location has geocoded coordinates."""
        return self.latitude is not None and self.longitude is not None

    @property
    def full_address(self) -> Optional[str]:
        """Get full formatted address."""
        parts = [
            self.address,
            self.city,
            self.state,
            self.postal_code,
            self.country
        ]
        filtered = [p for p in parts if p]
        return ", ".join(filtered) if filtered else None

    @property
    def instagram_url(self) -> str | None:
        """Get full Instagram profile URL."""
        if self.instagram_handle:
            return f"https://www.instagram.com/{self.instagram_handle}"
        return None

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Location("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"city='{self.city}'"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        if self.city:
            return f"{self.name} ({self.city})"
        return self.name
