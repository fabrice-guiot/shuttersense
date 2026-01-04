"""
PipelineHistory model for tracking pipeline version changes.

Stores snapshots of pipeline configurations for audit trail and rollback support.
Each update to a pipeline creates a new history entry with the previous state.

Design Rationale:
- Immutable snapshots: History entries are never modified after creation
- Full state capture: nodes_json and edges_json stored for complete restoration
- Change tracking: change_summary and changed_by for audit purposes
- Cascade delete: History deleted when parent pipeline is deleted
"""

from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from backend.src.models import Base


class PipelineHistory(Base):
    """
    Pipeline history model for version tracking.

    Stores snapshots of pipeline state at each version for audit trail
    and potential rollback functionality.

    Attributes:
        id: Primary key
        pipeline_id: Foreign key to Pipeline (CASCADE on delete)
        version: Version number this snapshot represents
        nodes_json: Node definitions at this version (JSONB)
        edges_json: Edge connections at this version (JSONB)
        change_summary: Description of changes made
        changed_by: User/system that made the change
        created_at: When this version was created
        pipeline: Related pipeline (many-to-one)

    Constraints:
        - pipeline_id required and must reference existing pipeline
        - version must be >= 1
        - (pipeline_id, version) must be unique

    Indexes:
        - idx_pipeline_history_pipeline: pipeline_id
        - idx_pipeline_history_version: (pipeline_id, version) DESC
    """

    __tablename__ = "pipeline_history"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key
    pipeline_id = Column(
        Integer,
        ForeignKey("pipelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Version info
    version = Column(Integer, nullable=False)

    # Snapshot of pipeline state - JSONB for PostgreSQL, JSON fallback for SQLite testing
    nodes_json = Column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    edges_json = Column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)

    # Change tracking
    change_summary = Column(String(500), nullable=True)
    changed_by = Column(String(255), nullable=True)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    pipeline = relationship("Pipeline", back_populates="history")

    # Indexes and constraints
    __table_args__ = (
        Index("idx_pipeline_history_pipeline", "pipeline_id"),
        Index("idx_pipeline_history_version", "pipeline_id", "version"),
        # Unique constraint on (pipeline_id, version)
        Index(
            "uq_pipeline_history_pipeline_version",
            "pipeline_id",
            "version",
            unique=True
        ),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<PipelineHistory("
            f"id={self.id}, "
            f"pipeline_id={self.pipeline_id}, "
            f"version={self.version}"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        summary = self.change_summary[:50] + "..." if self.change_summary and len(self.change_summary) > 50 else self.change_summary
        return f"Pipeline {self.pipeline_id} v{self.version}: {summary or 'No summary'}"

    @property
    def node_count(self) -> int:
        """Get the number of nodes in this snapshot."""
        if self.nodes_json is None:
            return 0
        return len(self.nodes_json)

    @property
    def edge_count(self) -> int:
        """Get the number of edges in this snapshot."""
        if self.edges_json is None:
            return 0
        return len(self.edges_json)

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of this history entry for API responses.

        Returns:
            Dictionary with history entry summary
        """
        return {
            "id": self.id,
            "version": self.version,
            "change_summary": self.change_summary,
            "changed_by": self.changed_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
