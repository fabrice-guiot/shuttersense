"""
ApiToken model for programmatic API access.

API tokens are JWT-based credentials for automation and integrations.
The full token is only shown once at creation time; the hash is stored
for validation and revocation.

Design Rationale:
- JWT tokens for stateless validation
- token_hash stored for revocation lookup (can't recompute JWT hash)
- token_prefix (first 8 chars) allows users to identify tokens in UI
- team_id denormalized from user for efficient team-scoped queries
- scopes_json prepared for future granular permissions (v1: ["*"] only)
- Soft revocation via is_active=false (maintains audit trail)
"""

import json
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin

if TYPE_CHECKING:
    from backend.src.models.team import Team
    from backend.src.models.user import User


class ApiToken(Base, GuidMixin):
    """
    API token model for programmatic API access.

    Tokens are JWT-based credentials for automation. The full token is only
    shown once at creation; the hash is stored for validation and revocation.

    Attributes:
        id: Primary key (internal, never exposed)
        uuid: UUIDv7 for external identification (inherited from GuidMixin)
        guid: GUID string property (tok_xxx, inherited from GuidMixin)
        user_id: Token owner (FK to users)
        team_id: Team scope (denormalized from user for query efficiency)
        name: User-provided token name/description
        token_hash: SHA-256 hash of the full JWT (for validation)
        token_prefix: First 8 characters of token (for UI identification)
        scopes_json: Allowed API scopes as JSON array
        expires_at: Token expiration timestamp
        last_used_at: Last API call using this token
        is_active: Token active status (for revocation)
        created_at: Creation timestamp

    Relationships:
        user: User who owns this token (many-to-one)
        team: Team this token is scoped to (many-to-one)

    Constraints:
        - token_hash must be unique
        - user_id and team_id are required
        - expires_at must be in the future at creation

    Indexes:
        - uuid (unique, for GUID lookups)
        - token_hash (unique, for validation lookup)
        - user_id (for user's token list)
        - team_id (for team-scoped queries)
        - expires_at (for expiration cleanup)
        - is_active (for filtering active tokens)
    """

    __tablename__ = "api_tokens"

    # GUID prefix for ApiToken entities
    GUID_PREFIX = "tok"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Ownership
    user_id = Column(
        Integer,
        ForeignKey("users.id", name="fk_api_tokens_user_id"),
        nullable=False,
        index=True
    )
    team_id = Column(
        Integer,
        ForeignKey("teams.id", name="fk_api_tokens_team_id"),
        nullable=False,
        index=True
    )

    # Token metadata
    name = Column(String(100), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    token_prefix = Column(String(10), nullable=False)

    # Scopes (JSON array)
    scopes_json = Column(Text, nullable=False, default='["*"]')

    # Lifecycle
    expires_at = Column(DateTime, nullable=False, index=True)
    last_used_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship(
        "User",
        back_populates="api_tokens",
        lazy="joined"
    )
    team = relationship(
        "Team",
        back_populates="api_tokens",
        lazy="joined"
    )

    @property
    def scopes(self) -> List[str]:
        """
        Get the list of allowed scopes.

        Returns:
            List of scope strings (e.g., ["*"] for full access)
        """
        if not self.scopes_json:
            return ["*"]
        try:
            return json.loads(self.scopes_json)
        except (json.JSONDecodeError, TypeError):
            return ["*"]

    @scopes.setter
    def scopes(self, value: List[str]) -> None:
        """
        Set the list of allowed scopes.

        Args:
            value: List of scope strings
        """
        self.scopes_json = json.dumps(value)

    @property
    def is_expired(self) -> bool:
        """
        Check if the token has expired.

        Returns:
            True if current time is past expires_at
        """
        return datetime.utcnow() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """
        Check if the token is valid for use.

        A token is valid if:
        - It is active (not revoked)
        - It has not expired

        Returns:
            True if the token can be used for authentication
        """
        return self.is_active and not self.is_expired

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<ApiToken("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"prefix='{self.token_prefix}...', "
            f"active={self.is_active}, "
            f"expired={self.is_expired}"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        status = "active" if self.is_valid else ("expired" if self.is_expired else "revoked")
        return f"{self.name} ({self.token_prefix}...) [{status}]"
