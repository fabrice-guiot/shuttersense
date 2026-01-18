"""
Team model for multi-tenancy support.

Teams represent tenancy boundaries - all data in the system belongs to
exactly one Team for complete data isolation between different organizations.

Design Rationale:
- Teams provide complete data isolation (all tenant-scoped entities have team_id FK)
- slug is auto-generated for URL-safe team identification
- is_active controls whether team members can log in
- settings_json allows team-level configuration (timezone, branding, etc.)
- Soft-delete only via is_active=false (no hard delete)
"""

import re
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin

if TYPE_CHECKING:
    from backend.src.models.user import User
    from backend.src.models.api_token import ApiToken
    from backend.src.models.agent import Agent


class Team(Base, GuidMixin):
    """
    Team model representing a tenancy boundary.

    All data in the system belongs to exactly one Team. Teams provide
    complete isolation between different organizations using the application.

    Attributes:
        id: Primary key (internal, never exposed)
        uuid: UUIDv7 for external identification (inherited from GuidMixin)
        guid: GUID string property (ten_xxx, inherited from GuidMixin)
        name: Team display name (unique)
        slug: URL-safe identifier (auto-generated from name)
        is_active: Whether team is active (controls member login)
        settings_json: Team-level settings as JSON
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Relationships:
        users: Users belonging to this team (one-to-many)
        api_tokens: API tokens scoped to this team (one-to-many)

    Constraints:
        - name must be unique
        - slug must be unique and URL-safe
        - Cannot hard-delete teams (use is_active=false)

    Indexes:
        - uuid (unique, for GUID lookups)
        - name (unique)
        - slug (unique)
        - is_active (for filtering)
    """

    __tablename__ = "teams"

    # GUID prefix for Team entities
    GUID_PREFIX = "ten"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Core fields
    name = Column(String(255), unique=True, nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)

    # State
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Settings (JSON-encoded)
    settings_json = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    users = relationship(
        "User",
        back_populates="team",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    api_tokens = relationship(
        "ApiToken",
        back_populates="team",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    agents = relationship(
        "Agent",
        back_populates="team",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    @staticmethod
    def generate_slug(name: str) -> str:
        """
        Generate a URL-safe slug from a team name.

        Args:
            name: Team display name

        Returns:
            URL-safe slug (lowercase, spaces→hyphens, special chars removed)

        Example:
            >>> Team.generate_slug("My Photo Team!")
            'my-photo-team'
        """
        if not name:
            return ""

        # Convert to lowercase
        slug = name.lower().strip()

        # Replace spaces and underscores with hyphens
        slug = re.sub(r'[\s_]+', '-', slug)

        # Remove any character that isn't alphanumeric or hyphen
        slug = re.sub(r'[^a-z0-9-]', '', slug)

        # Collapse multiple hyphens into one
        slug = re.sub(r'-+', '-', slug)

        # Remove leading/trailing hyphens
        slug = slug.strip('-')

        return slug

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Team("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"slug='{self.slug}', "
            f"active={self.is_active}"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return self.name
