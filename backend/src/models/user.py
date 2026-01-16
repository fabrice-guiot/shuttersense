"""
User model for authenticated user management.

Users represent people who can access the system. Users are pre-provisioned
by team administrators before they can log in via OAuth.

Design Rationale:
- Pre-provisioned model: admins invite users by email before OAuth login
- Email is globally unique across ALL teams (prevents confusion)
- status tracks lifecycle (pending→active, active→deactivated)
- is_active is the functional toggle for login capability
- OAuth profile data (name, picture) synced on each login
- oauth_subject stores immutable OAuth sub claim for identity verification
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin

if TYPE_CHECKING:
    from backend.src.models.team import Team
    from backend.src.models.api_token import ApiToken


class UserStatus(enum.Enum):
    """
    User account lifecycle status.

    State transitions:
    - pending → active (first OAuth login)
    - active → deactivated (admin disables)
    - deactivated → active (admin re-enables)
    """
    PENDING = "pending"          # Invited, never logged in
    ACTIVE = "active"            # Logged in at least once
    DEACTIVATED = "deactivated"  # Admin disabled


class User(Base, GuidMixin):
    """
    User model representing an authenticated person.

    Users are pre-provisioned by team administrators (invite-before-login model).
    Each user belongs to exactly one team and authenticates via OAuth (Google/Microsoft).

    Attributes:
        id: Primary key (internal, never exposed)
        uuid: UUIDv7 for external identification (inherited from GuidMixin)
        guid: GUID string property (usr_xxx, inherited from GuidMixin)
        team_id: Team membership (FK to teams)
        email: Login email (globally unique across ALL teams)
        first_name: User's first name (from invite or OAuth)
        last_name: User's last name (from invite or OAuth)
        display_name: Display name (OAuth sync or manual)
        picture_url: Profile picture URL (from OAuth)
        is_active: Account active status (controls login)
        status: Account lifecycle status (pending/active/deactivated)
        last_login_at: Last successful login timestamp
        oauth_provider: Last used OAuth provider (google, microsoft)
        oauth_subject: OAuth sub claim for identity verification
        preferences_json: User preferences as JSON
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Relationships:
        team: Team this user belongs to (many-to-one)
        api_tokens: API tokens created by this user (one-to-many)

    Constraints:
        - email must be globally unique across all teams
        - team_id is required (every user belongs to a team)

    Indexes:
        - uuid (unique, for GUID lookups)
        - email (unique, global)
        - team_id (for team-scoped queries)
        - status (for filtering by status)
        - is_active (for filtering active users)
        - oauth_subject (for OAuth identity lookup)
    """

    __tablename__ = "users"

    # GUID prefix for User entities
    GUID_PREFIX = "usr"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Team membership
    team_id = Column(
        Integer,
        ForeignKey("teams.id", name="fk_users_team_id"),
        nullable=False,
        index=True
    )

    # Identity
    email = Column(String(255), unique=True, nullable=False, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    display_name = Column(String(255), nullable=True)
    picture_url = Column(Text, nullable=True)  # Text for base64 data URLs

    # State
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    status = Column(
        Enum(UserStatus, name="user_status", create_constraint=True),
        default=UserStatus.PENDING,
        nullable=False,
        index=True
    )

    # OAuth tracking
    last_login_at = Column(DateTime, nullable=True)
    oauth_provider = Column(String(50), nullable=True)
    oauth_subject = Column(String(255), nullable=True, index=True)

    # Preferences (JSON-encoded)
    preferences_json = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    team = relationship(
        "Team",
        back_populates="users",
        lazy="joined"
    )
    api_tokens = relationship(
        "ApiToken",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> Optional[str]:
        """
        Get the user's full name.

        Returns:
            Combined first and last name, or display_name if names not set,
            or None if no name information available.
        """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        elif self.display_name:
            return self.display_name
        return None

    @property
    def can_login(self) -> bool:
        """
        Check if the user can log in.

        A user can log in if:
        - Their account is active (is_active=True)
        - Their status is not DEACTIVATED
        - Their team is active

        Note: Team active status should be checked separately via the team relationship.
        """
        return self.is_active and self.status != UserStatus.DEACTIVATED

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<User("
            f"id={self.id}, "
            f"email='{self.email}', "
            f"status={self.status.value}, "
            f"active={self.is_active}"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return self.full_name or self.email
