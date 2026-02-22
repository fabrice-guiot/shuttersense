"""
AgentRuntime model for volatile agent state.

Stores runtime/heartbeat data that changes frequently (status, metrics,
last_heartbeat, capabilities, etc.) separately from the Agent identity
table so that SQLAlchemy's onupdate mechanism on agents.updated_at only
fires for meaningful identity/config changes — not routine heartbeats.

One-to-one relationship with Agent (CASCADE delete).
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from backend.src.models import Base
from backend.src.models.agent import AgentStatus


class AgentRuntime(Base):
    """
    Volatile runtime state for an agent.

    This table is updated on every heartbeat (~30s) and is intentionally
    separated from the agents table so that audit-trail timestamps
    (updated_at with onupdate) are not affected by routine heartbeats.

    Attributes:
        id: Primary key
        agent_id: FK to agents.id (unique, 1:1)
        status: Current operational status (online/offline/error/revoked)
        error_message: Last error message if status=error
        last_heartbeat: Timestamp of last successful heartbeat
        capabilities_json: Declared capabilities as JSONB array
        authorized_roots_json: Authorized local filesystem roots as JSONB array
        pending_commands_json: Commands queued for the agent
        metrics_json: System resource metrics reported by agent
    """

    __tablename__ = "agent_runtime"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # One-to-one FK to agents
    agent_id = Column(
        Integer,
        ForeignKey("agents.id", name="fk_agent_runtime_agent_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Status — values_callable ensures SQLAlchemy uses .value (lowercase)
    # to match the native PostgreSQL enum, not .name (uppercase default)
    status = Column(
        Enum(
            AgentStatus,
            name="agent_status",
            create_constraint=False,
            values_callable=lambda e: [x.value for x in e],
        ),
        default=AgentStatus.OFFLINE,
        nullable=False,
    )
    error_message = Column(Text, nullable=True)
    last_heartbeat = Column(DateTime, nullable=True)

    # Capabilities (JSONB array of capability strings)
    capabilities_json = Column(
        JSONB().with_variant(Text, "sqlite"),
        nullable=False,
        default="[]",
    )

    # Authorized local filesystem roots (JSONB array of path strings)
    authorized_roots_json = Column(
        JSONB().with_variant(Text, "sqlite"),
        nullable=False,
        default="[]",
    )

    # Pending commands to be sent to agent on next heartbeat
    pending_commands_json = Column(
        JSONB().with_variant(Text, "sqlite"),
        nullable=False,
        default="[]",
    )

    # System resource metrics reported by agent
    metrics_json = Column(
        JSONB().with_variant(Text, "sqlite"),
        nullable=True,
        default=None,
    )

    # Table-level indexes
    __table_args__ = (
        Index("ix_agent_runtime_status", "status"),
    )

    # ── JSON property accessors ──

    @property
    def capabilities(self) -> List[str]:
        """Get the agent's declared capabilities as a list."""
        if self.capabilities_json is None:
            return []
        if isinstance(self.capabilities_json, str):
            return json.loads(self.capabilities_json)
        return self.capabilities_json

    @capabilities.setter
    def capabilities(self, value: List[str]) -> None:
        """Set the agent's capabilities."""
        if isinstance(value, list):
            self.capabilities_json = json.dumps(value) if value else "[]"
        else:
            self.capabilities_json = value

    @property
    def authorized_roots(self) -> List[str]:
        """Get the authorized local filesystem roots."""
        if self.authorized_roots_json is None:
            return []
        if isinstance(self.authorized_roots_json, str):
            return json.loads(self.authorized_roots_json)
        return self.authorized_roots_json

    @authorized_roots.setter
    def authorized_roots(self, value: List[str]) -> None:
        """Set the authorized local filesystem roots."""
        if isinstance(value, list):
            self.authorized_roots_json = json.dumps(value) if value else "[]"
        else:
            self.authorized_roots_json = value

    @property
    def pending_commands(self) -> List[str]:
        """Get the pending commands for this agent."""
        if self.pending_commands_json is None:
            return []
        if isinstance(self.pending_commands_json, str):
            return json.loads(self.pending_commands_json)
        return self.pending_commands_json

    @pending_commands.setter
    def pending_commands(self, value: List[str]) -> None:
        """Set the pending commands for this agent."""
        if isinstance(value, list):
            self.pending_commands_json = json.dumps(value) if value else "[]"
        else:
            self.pending_commands_json = value

    @property
    def metrics(self) -> Optional[Dict[str, Any]]:
        """Get the agent's system resource metrics."""
        if self.metrics_json is None:
            return None
        if isinstance(self.metrics_json, str):
            return json.loads(self.metrics_json)
        return self.metrics_json

    @metrics.setter
    def metrics(self, value: Optional[Dict[str, Any]]) -> None:
        """Set the agent's system resource metrics."""
        if value is None:
            self.metrics_json = None
        elif isinstance(value, dict):
            self.metrics_json = json.dumps(value)
        else:
            self.metrics_json = value

    def is_path_authorized(self, path: str) -> bool:
        """
        Check if a path is under one of the agent's authorized roots.

        Args:
            path: Path to check

        Returns:
            True if the path is under an authorized root
        """
        from pathlib import Path as PathLib

        try:
            normalized_path = PathLib(path).expanduser().resolve()
        except (OSError, ValueError):
            return False

        for root in self.authorized_roots:
            try:
                normalized_root = PathLib(root).expanduser().resolve()
                if normalized_path == normalized_root:
                    return True
                try:
                    normalized_path.relative_to(normalized_root)
                    return True
                except ValueError:
                    continue
            except (OSError, ValueError):
                continue

        return False

    def __repr__(self) -> str:
        return f"<AgentRuntime(agent_id={self.agent_id}, status={self.status.value if self.status else None})>"
