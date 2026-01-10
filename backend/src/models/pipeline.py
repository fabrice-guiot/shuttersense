"""
Pipeline model for photo processing workflow definitions.

Stores pipeline configurations as graph structures (nodes and edges) in JSONB,
with validation status tracking and version control support.

Design Rationale:
- JSONB for nodes/edges: Flexible graph structure without separate join tables
- Active status: Multiple pipelines can be active (valid and ready for use)
- Default status: Only one pipeline can be default at a time (used by tools)
- Version tracking: Integer version incremented on each update
- Validation caching: is_valid and validation_errors cached to avoid re-validation
"""

from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Index, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin


class Pipeline(Base, GuidMixin):
    """
    Pipeline model for photo processing workflows.

    Represents a directed graph of processing nodes (capture, file, process,
    pairing, branching, termination) connected by edges.

    Attributes:
        id: Primary key
        uuid: UUIDv7 for external identification (inherited from GuidMixin)
        guid: GUID string property (pip_xxx, inherited from GuidMixin)
        name: Unique display name
        description: Purpose/usage description
        nodes_json: Node definitions array (JSONB)
        edges_json: Edge connections array (JSONB)
        version: Current version number (incremented on update)
        is_active: Whether this pipeline is active (valid and ready for use)
        is_default: Whether this is the default pipeline for tool execution
        is_valid: Whether structure validation passed
        validation_errors: Validation error messages (JSONB)
        created_at: Creation timestamp
        updated_at: Last modification timestamp
        history: Related history entries (one-to-many)
        analysis_results: Related analysis results (one-to-many)
        collections: Related collections with explicit pipeline assignment (one-to-many)

    Constraints:
        - name must be unique, 1-255 characters
        - nodes_json must contain at least one node
        - edges_json can be empty (single-node pipeline)
        - version must be >= 1
        - Multiple pipelines can be active (is_active=true)
        - Only one pipeline can be default (is_default=true, application-enforced)
        - Default pipeline must be active (is_default implies is_active)

    Indexes:
        - idx_pipelines_name: name
        - uuid (unique, for GUID lookups)
        - idx_pipelines_active: is_active WHERE is_active = true
        - idx_pipelines_default: is_default WHERE is_default = true

    Node Structure (nodes_json):
        [
            {"id": "capture_1", "type": "capture", "properties": {...}},
            {"id": "file_raw", "type": "file", "properties": {"extension": ".dng"}},
            ...
        ]

    Edge Structure (edges_json):
        [
            {"from": "capture_1", "to": "file_raw"},
            {"from": "file_raw", "to": "process_hdr"},
            ...
        ]
    """

    __tablename__ = "pipelines"

    # GUID prefix for Pipeline entities
    GUID_PREFIX = "pip"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Core fields
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Graph structure - JSONB for PostgreSQL, JSON fallback for SQLite testing
    nodes_json = Column(JSONB().with_variant(JSON(), "sqlite"), nullable=False, default=list)
    edges_json = Column(JSONB().with_variant(JSON(), "sqlite"), nullable=False, default=list)

    # Version control
    version = Column(Integer, nullable=False, default=1)

    # Status
    is_active = Column(Boolean, nullable=False, default=False, index=True)
    is_default = Column(Boolean, nullable=False, default=False, index=True)
    is_valid = Column(Boolean, nullable=False, default=False)
    validation_errors = Column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    history = relationship(
        "PipelineHistory",
        back_populates="pipeline",
        cascade="all, delete-orphan",
        order_by="desc(PipelineHistory.version)"
    )
    analysis_results = relationship(
        "AnalysisResult",
        back_populates="pipeline"
    )
    collections = relationship(
        "Collection",
        back_populates="pipeline"
    )

    # Indexes
    __table_args__ = (
        Index("idx_pipelines_name", "name"),
        Index("idx_pipelines_active", "is_active", postgresql_where=(is_active == True)),
        Index("idx_pipelines_default", "is_default", postgresql_where=(is_default == True)),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Pipeline("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"version={self.version}, "
            f"active={self.is_active}, "
            f"default={self.is_default}, "
            f"valid={self.is_valid}"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        status_parts = []
        if self.is_default:
            status_parts.append("default")
        elif self.is_active:
            status_parts.append("active")
        else:
            status_parts.append("inactive")
        status_parts.append("valid" if self.is_valid else "invalid")
        return f"{self.name} v{self.version} ({', '.join(status_parts)})"

    @property
    def node_count(self) -> int:
        """Get the number of nodes in the pipeline."""
        if self.nodes_json is None:
            return 0
        return len(self.nodes_json)

    @property
    def edge_count(self) -> int:
        """Get the number of edges in the pipeline."""
        if self.edges_json is None:
            return 0
        return len(self.edges_json)

    def get_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a node by its ID.

        Args:
            node_id: The node identifier

        Returns:
            Node dictionary or None if not found
        """
        if self.nodes_json is None:
            return None
        for node in self.nodes_json:
            if node.get("id") == node_id:
                return node
        return None

    def get_nodes_by_type(self, node_type: str) -> List[Dict[str, Any]]:
        """
        Get all nodes of a specific type.

        Args:
            node_type: The node type (capture, file, process, pairing, branching, termination)

        Returns:
            List of node dictionaries matching the type
        """
        if self.nodes_json is None:
            return []
        return [node for node in self.nodes_json if node.get("type") == node_type]

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the pipeline for API responses.

        Returns:
            Dictionary with pipeline summary
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "is_valid": self.is_valid,
            "node_count": self.node_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
