"""
Organizer model for event hosts/organizers.

Organizers represent the entities that host or organize events.
They include default ticket settings and ratings for prioritization.

Design Rationale:
- Category matching ensures events and organizers are compatible
- Default ticket_required setting is applied to new events
- Rating (1-5) helps prioritize favorite organizers
- Website allows linking to organizer's official page
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, Index
)
from sqlalchemy.orm import relationship

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin


class Organizer(Base, GuidMixin):
    """
    Event organizer model.

    Represents an event organizer/host with default ticket settings
    and rating for prioritization.

    Attributes:
        id: Primary key (internal, never exposed)
        uuid: UUIDv7 for external identification (inherited from GuidMixin)
        guid: GUID string property (org_xxx, inherited from GuidMixin)
        name: Organizer name
        website: Website URL
        instagram_handle: Instagram username (without @)
        category_id: Foreign key to categories (must match event category)
        rating: Organizer rating 1-5 (displayed as stars)
        ticket_required_default: Pre-select ticket required for new events
        notes: Additional notes
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Relationships:
        category: Parent category (many-to-one, RESTRICT on delete)
        events: Events by this organizer (one-to-many, SET NULL on delete)
        event_series: Event series by this organizer (one-to-many, SET NULL on delete)

    Constraints:
        - category_id is required
        - rating must be 1-5 if provided
        - website must be valid URL if provided
        - category must be active

    Indexes:
        - uuid (unique, for GUID lookups)
        - category_id (for filtering by category)
    """

    __tablename__ = "organizers"

    # GUID prefix for Organizer entities
    GUID_PREFIX = "org"

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
    website = Column(String(500), nullable=True)
    instagram_handle = Column(String(100), nullable=True)  # Without @

    # Rating and defaults
    rating = Column(Integer, nullable=True)  # 1-5
    ticket_required_default = Column(Boolean, default=False, nullable=False)

    # Additional info
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    category = relationship("Category", back_populates="organizers")
    events = relationship(
        "Event",
        back_populates="organizer",
        lazy="dynamic"
    )
    event_series = relationship(
        "EventSeries",
        back_populates="organizer",
        lazy="dynamic"
    )

    @property
    def instagram_url(self) -> str | None:
        """Get full Instagram profile URL."""
        if self.instagram_handle:
            return f"https://www.instagram.com/{self.instagram_handle}"
        return None

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Organizer("
            f"id={self.id}, "
            f"name='{self.name}'"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return self.name
