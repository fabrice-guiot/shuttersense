"""
AgentRegistrationToken model for one-time agent registration.

Represents a single-use token that allows an agent to register with
the ShutterSense server. Tokens expire after 24 hours by default.

Design Rationale:
- Single-use tokens prevent replay attacks
- Expiration limits exposure window
- Token hash stored (not plaintext) for security
- Links to the agent that used it for audit trail
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin

if TYPE_CHECKING:
    from backend.src.models.team import Team
    from backend.src.models.user import User
    from backend.src.models.agent import Agent


# Default token expiration: 24 hours
DEFAULT_TOKEN_EXPIRATION_HOURS = 24


class AgentRegistrationToken(Base, GuidMixin):
    """
    AgentRegistrationToken model for one-time agent registration.

    Registration tokens are single-use tokens that allow agents to register
    with a ShutterSense server. They expire after 24 hours by default.

    Attributes:
        id: Primary key (internal, never exposed)
        uuid: UUIDv7 for external identification (inherited from GuidMixin)
        guid: GUID string property (art_xxx, inherited from GuidMixin)
        team_id: Team this token registers for (FK to teams)
        created_by_user_id: User who created the token (FK to users)
        token_hash: SHA-256 hash of the token
        name: Optional description for the token
        is_used: Whether the token has been used
        used_by_agent_id: Agent that used this token (FK to agents)
        expires_at: Token expiration timestamp
        created_at: Creation timestamp

    Relationships:
        team: Team this token registers for (many-to-one)
        created_by: User who created the token (many-to-one)
        used_by_agent: Agent that used this token (one-to-one, nullable)

    Constraints:
        - token_hash must be unique
        - Token can only be used once (is_used=false required)
        - Token must not be expired (expires_at > NOW())

    Indexes:
        - uuid (unique, for GUID lookups)
        - token_hash (unique, for token validation)
        - (team_id, expires_at, is_used) for finding valid tokens
    """

    __tablename__ = "agent_registration_tokens"

    # GUID prefix for AgentRegistrationToken entities
    GUID_PREFIX = "art"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Team membership
    team_id = Column(
        Integer,
        ForeignKey("teams.id", name="fk_art_team_id"),
        nullable=False,
        index=True
    )

    # Creator
    created_by_user_id = Column(
        Integer,
        ForeignKey("users.id", name="fk_art_created_by_user_id"),
        nullable=False
    )

    # Token (hashed)
    token_hash = Column(String(255), unique=True, nullable=False)

    # Optional name/description
    name = Column(String(100), nullable=True)

    # Usage tracking
    is_used = Column(Boolean, default=False, nullable=False)
    used_by_agent_id = Column(
        Integer,
        ForeignKey("agents.id", name="fk_art_used_by_agent_id"),
        nullable=True
    )

    # Expiration
    expires_at = Column(DateTime, nullable=False)

    # Audit: who last updated this token
    updated_by_user_id = Column(
        Integer,
        ForeignKey("users.id", name="fk_art_updated_by_user_id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    team = relationship(
        "Team",
        lazy="joined"
    )
    created_by = relationship(
        "User",
        foreign_keys=[created_by_user_id],
        lazy="joined"
    )
    updated_by_user = relationship(
        "User",
        foreign_keys=[updated_by_user_id],
        lazy="select"
    )
    used_by_agent = relationship(
        "Agent",
        foreign_keys=[used_by_agent_id],
        lazy="joined"
    )

    # Table-level indexes
    __table_args__ = (
        Index("ix_art_team_expires_used", "team_id", "expires_at", "is_used"),
    )

    @property
    def is_expired(self) -> bool:
        """
        Check if the token has expired.

        Returns:
            True if the token has expired
        """
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """
        Check if the token is valid for registration.

        A token is valid if it hasn't been used and hasn't expired.

        Returns:
            True if the token can be used for registration
        """
        return not self.is_used and not self.is_expired

    @property
    def time_until_expiration(self) -> Optional[timedelta]:
        """
        Get the time remaining until token expiration.

        Returns:
            timedelta until expiration, or None if already expired
        """
        if self.is_expired:
            return None
        return self.expires_at - datetime.utcnow()

    def mark_as_used(self, agent_id: int) -> None:
        """
        Mark the token as used by an agent.

        Args:
            agent_id: Internal ID of the agent that used this token
        """
        self.is_used = True
        self.used_by_agent_id = agent_id

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<AgentRegistrationToken("
            f"id={self.id}, "
            f"team_id={self.team_id}, "
            f"is_used={self.is_used}, "
            f"expired={self.is_expired}"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        status = "used" if self.is_used else ("expired" if self.is_expired else "valid")
        name_part = f" ({self.name})" if self.name else ""
        return f"Registration Token{name_part} [{status}]"
