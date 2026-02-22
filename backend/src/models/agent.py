"""
Agent model for distributed job execution workers.

Represents a worker process running on user-owned hardware that executes
analysis jobs. Each agent belongs to a team and has a dedicated SYSTEM user
for audit trail purposes.

Design Rationale:
- Agents run on user hardware and poll for jobs to execute
- Each agent gets a dedicated SYSTEM user for audit trail (created_by tracking)
- API key authentication using hashed keys (like API tokens)
- Volatile runtime state (status, heartbeat, metrics, capabilities) is stored
  in the separate AgentRuntime table so that onupdate on updated_at only fires
  for meaningful identity/config changes, not routine heartbeats.
"""

import enum
import json
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin

if TYPE_CHECKING:
    from backend.src.models.team import Team
    from backend.src.models.user import User
    from backend.src.models.collection import Collection
    from backend.src.models.agent_runtime import AgentRuntime


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

    Identity and configuration data lives on this table (audit-tracked).
    Volatile runtime state (status, heartbeat, metrics, capabilities) lives
    on the related AgentRuntime record.

    Proxy properties on this model delegate to self.runtime for backward
    compatibility so that existing code using agent.status, agent.capabilities,
    etc. continues to work unchanged.
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

    # Connectors with local credentials (JSONB array of connector GUIDs)
    connectors_json = Column(
        JSONB().with_variant(Text, "sqlite"),
        nullable=False,
        default="[]"
    )

    # Authentication
    api_key_hash = Column(String(255), unique=True, nullable=False)
    api_key_prefix = Column(String(20), nullable=False, index=True)

    # Version and attestation
    version = Column(String(50), nullable=True)
    binary_checksum = Column(String(64), nullable=True)
    platform = Column(String(50), nullable=True)
    is_outdated = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=True, nullable=False)

    # Revocation
    revocation_reason = Column(Text, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    # Audit: who last updated this agent
    updated_by_user_id = Column(
        Integer,
        ForeignKey("users.id", name="fk_agents_updated_by_user_id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Timestamps — onupdate restored; volatile fields now live on AgentRuntime
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # ── Relationships ──

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
    updated_by_user = relationship(
        "User",
        foreign_keys=[updated_by_user_id],
        lazy="select"
    )
    bound_collections = relationship(
        "Collection",
        back_populates="bound_agent",
        lazy="dynamic"
    )
    runtime = relationship(
        "AgentRuntime",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="joined",
    )

    @property
    def audit(self):
        """Computed audit info dict for API serialization."""
        from backend.src.schemas.audit import build_audit_info
        return build_audit_info(self, created_by_attr="created_by")

    # ── Proxy properties delegating to AgentRuntime ──

    @property
    def status(self) -> "AgentStatus":
        """Current agent status (delegated to runtime)."""
        if self.runtime is not None:
            return self.runtime.status
        return AgentStatus.OFFLINE

    @status.setter
    def status(self, value: "AgentStatus") -> None:
        if self.runtime is not None:
            self.runtime.status = value

    @property
    def error_message(self) -> Optional[str]:
        if self.runtime is not None:
            return self.runtime.error_message
        return None

    @error_message.setter
    def error_message(self, value: Optional[str]) -> None:
        if self.runtime is not None:
            self.runtime.error_message = value

    @property
    def last_heartbeat(self) -> Optional[datetime]:
        if self.runtime is not None:
            return self.runtime.last_heartbeat
        return None

    @last_heartbeat.setter
    def last_heartbeat(self, value: Optional[datetime]) -> None:
        if self.runtime is not None:
            self.runtime.last_heartbeat = value

    @property
    def capabilities_json(self) -> Any:
        if self.runtime is not None:
            return self.runtime.capabilities_json
        return "[]"

    @capabilities_json.setter
    def capabilities_json(self, value: Any) -> None:
        if self.runtime is not None:
            self.runtime.capabilities_json = value

    @property
    def capabilities(self) -> List[str]:
        """Get the agent's declared capabilities as a list."""
        if self.runtime is not None:
            return self.runtime.capabilities
        return []

    @capabilities.setter
    def capabilities(self, value: List[str]) -> None:
        if self.runtime is not None:
            self.runtime.capabilities = value

    @property
    def authorized_roots_json(self) -> Any:
        if self.runtime is not None:
            return self.runtime.authorized_roots_json
        return "[]"

    @authorized_roots_json.setter
    def authorized_roots_json(self, value: Any) -> None:
        if self.runtime is not None:
            self.runtime.authorized_roots_json = value

    @property
    def authorized_roots(self) -> List[str]:
        """Get the authorized local filesystem roots."""
        if self.runtime is not None:
            return self.runtime.authorized_roots
        return []

    @authorized_roots.setter
    def authorized_roots(self, value: List[str]) -> None:
        if self.runtime is not None:
            self.runtime.authorized_roots = value

    @property
    def pending_commands_json(self) -> Any:
        if self.runtime is not None:
            return self.runtime.pending_commands_json
        return "[]"

    @pending_commands_json.setter
    def pending_commands_json(self, value: Any) -> None:
        if self.runtime is not None:
            self.runtime.pending_commands_json = value

    @property
    def pending_commands(self) -> List[str]:
        """Get the pending commands for this agent."""
        if self.runtime is not None:
            return self.runtime.pending_commands
        return []

    @pending_commands.setter
    def pending_commands(self, value: List[str]) -> None:
        if self.runtime is not None:
            self.runtime.pending_commands = value

    @property
    def metrics_json(self) -> Any:
        if self.runtime is not None:
            return self.runtime.metrics_json
        return None

    @metrics_json.setter
    def metrics_json(self, value: Any) -> None:
        if self.runtime is not None:
            self.runtime.metrics_json = value

    @property
    def metrics(self) -> Optional[Dict[str, Any]]:
        """Get the agent's system resource metrics."""
        if self.runtime is not None:
            return self.runtime.metrics
        return None

    @metrics.setter
    def metrics(self, value: Optional[Dict[str, Any]]) -> None:
        if self.runtime is not None:
            self.runtime.metrics = value

    # ── Connector GUIDs (stays on agents table) ──

    @property
    def connector_guids(self) -> List[str]:
        """Get the connector GUIDs with local credentials."""
        if self.connectors_json is None:
            return []
        if isinstance(self.connectors_json, str):
            return json.loads(self.connectors_json)
        return self.connectors_json

    @connector_guids.setter
    def connector_guids(self, value: List[str]) -> None:
        if isinstance(value, list):
            self.connectors_json = json.dumps(value) if value else "[]"
        else:
            self.connectors_json = value

    # ── Delegated helpers ──

    def is_path_authorized(self, path: str) -> bool:
        """Check if a path is under one of the agent's authorized roots."""
        if self.runtime is not None:
            return self.runtime.is_path_authorized(path)
        return False

    @property
    def is_online(self) -> bool:
        """Check if the agent is currently online."""
        return self.status == AgentStatus.ONLINE

    @property
    def is_revoked(self) -> bool:
        """Check if the agent has been revoked."""
        return self.revoked_at is not None

    @property
    def can_execute_jobs(self) -> bool:
        """Check if the agent can execute jobs (online and verified)."""
        return self.status == AgentStatus.ONLINE and self.is_verified

    def has_capability(self, capability: str) -> bool:
        """Check if the agent has a specific capability."""
        return capability in self.capabilities

    def has_all_capabilities(self, required: List[str]) -> bool:
        """Check if the agent has all required capabilities."""
        agent_caps = set(self.capabilities)
        return all(cap in agent_caps for cap in required)

    def __repr__(self) -> str:
        """String representation for debugging."""
        status_val = self.status.value if self.runtime else "no_runtime"
        return (
            f"<Agent("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"status={status_val}, "
            f"team_id={self.team_id}"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        status_val = self.status.value if self.runtime else "no_runtime"
        return f"{self.name} ({status_val})"
