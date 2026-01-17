"""
Performer model for event participants/subjects.

Performers represent the subjects/participants scheduled to appear at events
(pilots, athletes, artists, etc.). They are associated with events through
the EventPerformer junction table.

Design Rationale:
- Category matching ensures events and performers are compatible
- Instagram and website links enable quick access to performer info
- Additional info field supports multiline notes
- Many-to-many relationship with events allows same performer at multiple events
"""

from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, DateTime, Text,
    ForeignKey
)
from sqlalchemy.orm import relationship

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin


class Performer(Base, GuidMixin):
    """
    Event performer model.

    Represents a performer/participant at events (pilot, athlete, artist, etc.)
    with social media links and notes.

    Attributes:
        id: Primary key (internal, never exposed)
        uuid: UUIDv7 for external identification (inherited from GuidMixin)
        guid: GUID string property (prf_xxx, inherited from GuidMixin)
        name: Performer name
        category_id: Foreign key to categories (must match event category)
        website: Website URL
        instagram_handle: Instagram username (without @)
        additional_info: Multiline notes
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Relationships:
        category: Parent category (many-to-one, RESTRICT on delete)
        event_performers: Junction records linking to events (one-to-many)

    Constraints:
        - category_id is required
        - website must be valid URL if provided
        - instagram_handle should not include @ symbol
        - category must be active
        - Cannot delete performer if linked to events (RESTRICT via junction)

    Indexes:
        - uuid (unique, for GUID lookups)
        - category_id (for filtering by category)
    """

    __tablename__ = "performers"

    # GUID prefix for Performer entities
    GUID_PREFIX = "prf"

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
    additional_info = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    category = relationship("Category", back_populates="performers")
    event_performers = relationship(
        "EventPerformer",
        back_populates="performer",
        lazy="dynamic",
        cascade="all, delete-orphan"
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
            f"<Performer("
            f"id={self.id}, "
            f"name='{self.name}'"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return self.name
