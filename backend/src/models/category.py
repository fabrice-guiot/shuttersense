"""
Category model for event categorization.

Categories provide classification for events (Airshow, Wedding, Wildlife, etc.)
and enforce grouping consistency between Events and their related entities.

Design Rationale:
- Categories are foundational - Events, Locations, Organizers, and Performers all
  reference a category to ensure consistent grouping
- Soft enable/disable via is_active flag allows hiding categories without deletion
- display_order enables user-defined sorting in UI dropdowns
- color and icon are optional for visual customization
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Index, ForeignKey
from sqlalchemy.orm import relationship

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin, AuditMixin


class Category(Base, GuidMixin, AuditMixin):
    """
    Event category model.

    Represents a category for classifying events and related entities.
    Categories enforce consistency - a Location in "Airshow" category can only
    be assigned to events in the same category.

    Attributes:
        id: Primary key (internal, never exposed)
        uuid: UUIDv7 for external identification (inherited from GuidMixin)
        guid: GUID string property (cat_xxx, inherited from GuidMixin)
        name: Category name (unique, case-insensitive)
        color: Hex color code (e.g., "#FF5733") for UI display
        icon: Lucide icon name (e.g., "plane", "camera") for UI display
        is_active: Whether category is available for selection
        display_order: Sort order in UI dropdowns and lists
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Relationships:
        events: Events in this category (one-to-many)
        locations: Locations in this category (one-to-many)
        organizers: Organizers in this category (one-to-many)
        performers: Performers in this category (one-to-many)
        event_series: Event series in this category (one-to-many)

    Constraints:
        - name must be unique
        - color must be valid hex format if provided (#RRGGBB)
        - Cannot delete category with associated entities (RESTRICT)

    Indexes:
        - uuid (unique, for GUID lookups)
        - name (unique)
        - is_active, display_order (for filtered sorted lists)
    """

    __tablename__ = "categories"

    # GUID prefix for Category entities
    GUID_PREFIX = "cat"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Tenant isolation
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)

    # Core fields
    name = Column(String(100), unique=True, nullable=False, index=True)
    color = Column(String(7), nullable=True)  # Hex color: #RRGGBB
    icon = Column(String(50), nullable=True)  # Lucide icon name

    # State and ordering
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships (defined with back_populates for bidirectional access)
    events = relationship(
        "Event",
        back_populates="category",
        lazy="dynamic"
    )
    locations = relationship(
        "Location",
        back_populates="category",
        lazy="dynamic"
    )
    organizers = relationship(
        "Organizer",
        back_populates="category",
        lazy="dynamic"
    )
    performers = relationship(
        "Performer",
        back_populates="category",
        lazy="dynamic"
    )
    event_series = relationship(
        "EventSeries",
        back_populates="category",
        lazy="dynamic"
    )

    # Table-level indexes
    __table_args__ = (
        Index(
            "idx_categories_active_order",
            "is_active",
            "display_order",
        ),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Category("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"active={self.is_active}"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return self.name
