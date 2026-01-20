"""
Agent model for distributed job execution workers.

Represents a worker process running on user-owned hardware that executes
analysis jobs. Each agent belongs to a team and has a dedicated SYSTEM user
for audit trail purposes.

Design Rationale:
- Agents run on user hardware and poll for jobs to execute
- Each agent gets a dedicated SYSTEM user for audit trail (created_by tracking)
- API key authentication using hashed keys (like API tokens)
- Capabilities are declared by the agent and used for job routing
- Status tracks online/offline/error/revoked states
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin

if TYPE_CHECKING:
    from backend.src.models.team import Team
    from backend.src.models.user import User
    from backend.src.models.collection import Collection


class AgentStatus(str, enum.Enum):
    """
    Agent status enumeration.

    Tracks the operational state of an agent:
    - ONLINE: Heartbeat received within 90 seconds
    - OFFLINE: No heartbeat for 90+ seconds
    - ERROR: Agent reported an error state
    - REVOKED: Agent revoked by administrator
    """
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    REVOKED = "revoked"


class Agent(Base, GuidMixin):
    """
    Agent model representing a distributed job execution worker.

    Agents are worker processes running on user-owned hardware that execute
    analysis jobs. They poll the server for available jobs, execute them
    locally, and report progress via WebSocket.

    Attributes:
        id: Primary key (internal, never exposed)
        uuid: UUIDv7 for external identification (inherited from GuidMixin)
        guid: GUID string property (agt_xxx, inherited from GuidMixin)
        team_id: Team this agent belongs to (FK to teams)
        system_user_id: Dedicated SYSTEM user for audit trail (FK to users)
        created_by_user_id: Human who registered the agent (FK to users)
        name: User-friendly agent name
        hostname: Machine hostname (auto-detected by agent)
        os_info: Operating system type/version
        status: Agent status (online/offline/error/revoked)
        error_message: Last error message if status=error
        last_heartbeat: Timestamp of last successful heartbeat
        capabilities_json: Declared capabilities as JSONB array
        connectors_json: Connector GUIDs with local credentials as JSONB array
        api_key_hash: SHA-256 hash of the agent's API key
        api_key_prefix: First 8 characters of API key for identification
        version: Agent software version
        binary_checksum: SHA-256 of agent binary (for attestation)
        revocation_reason: Reason if status=revoked
        revoked_at: Timestamp of revocation
        created_at: Registration timestamp
        updated_at: Last modification timestamp

    Relationships:
        team: Team this agent belongs to (many-to-one)
        system_user: Dedicated SYSTEM user for audit (one-to-one)
        created_by: Human who registered the agent (many-to-one)
        bound_collections: Collections bound to this agent (one-to-many)

    Constraints:
        - name must be 1-255 characters
        - api_key_hash must be unique
        - When status=REVOKED, revocation_reason is required
        - Cannot delete agent with bound collections

    Indexes:
        - uuid (unique, for GUID lookups)
        - team_id (for team-scoped queries)
        - status (for filtering by status)
        - api_key_hash (unique, for authentication)
        - api_key_prefix (for key identification)
    """

    __tablename__ = "agents"

    # GUID prefix for Agent entities
    GUID_PREFIX = "agt"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Team membership
    team_id = Column(
        Integer,
        ForeignKey("teams.id", name="fk_agents_team_id"),
        nullable=False,
        index=True
    )

    # User references
    system_user_id = Column(
        Integer,
        ForeignKey("users.id", name="fk_agents_system_user_id"),
        nullable=False
    )
    created_by_user_id = Column(
        Integer,
        ForeignKey("users.id", name="fk_agents_created_by_user_id"),
        nullable=False
    )

    # Identity
    name = Column(String(255), nullable=False)
    hostname = Column(String(255), nullable=True)
    os_info = Column(String(255), nullable=True)

    # Status
    status = Column(
        Enum(AgentStatus, name="agent_status", create_constraint=True),
        default=AgentStatus.OFFLINE,
        nullable=False,
        index=True
    )
    error_message = Column(Text, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)

    # Capabilities (JSONB array of capability strings)
    capabilities_json = Column(
        JSONB().with_variant(Text, "sqlite"),
        nullable=False,
        default=list
    )

    # Connectors with local credentials (JSONB array of connector GUIDs)
    connectors_json = Column(
        JSONB().with_variant(Text, "sqlite"),
        nullable=False,
        default=list
    )

    # Authorized local filesystem roots (JSONB array of path strings)
    authorized_roots_json = Column(
        JSONB().with_variant(Text, "sqlite"),
        nullable=False,
        default=list
    )

    # Authentication
    api_key_hash = Column(String(255), unique=True, nullable=False)
    api_key_prefix = Column(String(20), nullable=False, index=True)  # "agt_key_" + 8 random chars

    # Version and attestation
    version = Column(String(50), nullable=True)
    binary_checksum = Column(String(64), nullable=True)

    # Revocation
    revocation_reason = Column(Text, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

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
        back_populates="agents",
        lazy="joined"
    )
    system_user = relationship(
        "User",
        foreign_keys=[system_user_id],
        lazy="joined"
    )
    created_by = relationship(
        "User",
        foreign_keys=[created_by_user_id],
        lazy="joined"
    )
    bound_collections = relationship(
        "Collection",
        back_populates="bound_agent",
        lazy="dynamic"
    )

    # Table-level indexes
    __table_args__ = (
        Index("ix_agents_team_status", "team_id", "status"),
    )

    @property
    def capabilities(self) -> List[str]:
        """
        Get the agent's declared capabilities as a list.

        Returns:
            List of capability strings
        """
        if self.capabilities_json is None:
            return []
        if isinstance(self.capabilities_json, str):
            import json
            return json.loads(self.capabilities_json)
        return self.capabilities_json

    @capabilities.setter
    def capabilities(self, value: List[str]) -> None:
        """
        Set the agent's capabilities.

        Args:
            value: List of capability strings
        """
        # For SQLite compatibility, serialize to JSON string
        import json
        if isinstance(value, list):
            # Check if we're using SQLite (Text variant) - serialize to JSON string
            # PostgreSQL JSONB handles lists natively
            self.capabilities_json = json.dumps(value) if value else "[]"
        else:
            self.capabilities_json = value

    @property
    def connector_guids(self) -> List[str]:
        """
        Get the connector GUIDs with local credentials.

        Returns:
            List of connector GUID strings
        """
        if self.connectors_json is None:
            return []
        if isinstance(self.connectors_json, str):
            import json
            return json.loads(self.connectors_json)
        return self.connectors_json

    @connector_guids.setter
    def connector_guids(self, value: List[str]) -> None:
        """
        Set the connector GUIDs with local credentials.

        Args:
            value: List of connector GUID strings
        """
        # For SQLite compatibility, serialize to JSON string
        import json
        if isinstance(value, list):
            self.connectors_json = json.dumps(value) if value else "[]"
        else:
            self.connectors_json = value

    @property
    def authorized_roots(self) -> List[str]:
        """
        Get the authorized local filesystem roots.

        Returns:
            List of authorized root path strings
        """
        if self.authorized_roots_json is None:
            return []
        if isinstance(self.authorized_roots_json, str):
            import json
            return json.loads(self.authorized_roots_json)
        return self.authorized_roots_json

    @authorized_roots.setter
    def authorized_roots(self, value: List[str]) -> None:
        """
        Set the authorized local filesystem roots.

        Args:
            value: List of authorized root path strings
        """
        # For SQLite compatibility, serialize to JSON string
        import json
        if isinstance(value, list):
            self.authorized_roots_json = json.dumps(value) if value else "[]"
        else:
            self.authorized_roots_json = value

    def is_path_authorized(self, path: str) -> bool:
        """
        Check if a path is under one of the agent's authorized roots.

        The path is considered authorized if it starts with any of the
        authorized root paths.

        Args:
            path: Path to check

        Returns:
            True if the path is under an authorized root
        """
        from pathlib import Path as PathLib

        # Normalize and resolve the path
        try:
            normalized_path = PathLib(path).expanduser().resolve()
        except (OSError, ValueError):
            return False

        # Check against each authorized root
        for root in self.authorized_roots:
            try:
                normalized_root = PathLib(root).expanduser().resolve()
                # Check if path is the root or a subdirectory of the root
                if normalized_path == normalized_root:
                    return True
                try:
                    normalized_path.relative_to(normalized_root)
                    return True
                except ValueError:
                    # Path is not relative to this root
                    continue
            except (OSError, ValueError):
                continue

        return False

    @property
    def is_online(self) -> bool:
        """
        Check if the agent is currently online.

        Returns:
            True if status is ONLINE
        """
        return self.status == AgentStatus.ONLINE

    @property
    def is_revoked(self) -> bool:
        """
        Check if the agent has been revoked.

        Returns:
            True if status is REVOKED
        """
        return self.status == AgentStatus.REVOKED

    @property
    def can_execute_jobs(self) -> bool:
        """
        Check if the agent can execute jobs.

        An agent can execute jobs if it is online and not revoked.

        Returns:
            True if agent can execute jobs
        """
        return self.status == AgentStatus.ONLINE

    def has_capability(self, capability: str) -> bool:
        """
        Check if the agent has a specific capability.

        Args:
            capability: Capability string to check

        Returns:
            True if the agent has the capability
        """
        return capability in self.capabilities

    def has_all_capabilities(self, required: List[str]) -> bool:
        """
        Check if the agent has all required capabilities.

        Args:
            required: List of required capability strings

        Returns:
            True if the agent has all required capabilities
        """
        agent_caps = set(self.capabilities)
        return all(cap in agent_caps for cap in required)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Agent("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"status={self.status.value}, "
            f"team_id={self.team_id}"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.name} ({self.status.value})"
