"""
AnalysisResult model for storing tool execution results.

Stores execution history and results for all analysis tools (PhotoStats,
Photo Pairing, Pipeline Validation). Results include structured JSONB data
and optional pre-rendered HTML reports for historical access.

Design Rationale:
- JSONB storage: Flexible schema for tool-specific results
- HTML report storage: Pre-rendered for immediate download without re-generation
- Collection cascade: Results deleted when collection is deleted
- Pipeline SET NULL: Results preserved even if pipeline is deleted
"""

from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, Enum, ForeignKey, Index, JSON
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from backend.src.models import Base, ResultStatus
from backend.src.models.mixins import GuidMixin


class AnalysisResult(Base, GuidMixin):
    """
    Analysis result model.

    Stores the results of tool executions (PhotoStats, Photo Pairing,
    Pipeline Validation) with structured JSONB data and optional HTML reports.

    Attributes:
        id: Primary key
        uuid: UUIDv7 for external identification (inherited from GuidMixin)
        guid: GUID string property (res_xxx, inherited from GuidMixin)
        collection_id: Foreign key to Collection (CASCADE on delete, nullable for display-graph mode)
        tool: Tool name ('photostats', 'photo_pairing', 'pipeline_validation')
        pipeline_id: Foreign key to Pipeline (SET NULL on delete)
        pipeline_version: Pipeline version used at execution time (nullable)
        status: Result status (COMPLETED, FAILED, CANCELLED)
        started_at: Execution start timestamp
        completed_at: Execution end timestamp
        duration_seconds: Execution duration
        results_json: Tool-specific structured results (JSONB)
        report_html: Pre-rendered HTML report for download
        error_message: Error details if failed
        files_scanned: Number of files processed
        issues_found: Number of issues detected
        created_at: Record creation timestamp
        collection: Related collection (many-to-one, nullable)
        pipeline: Related pipeline (many-to-one, nullable)

    Constraints:
        - collection_id optional (NULL for pipeline-only display-graph mode)
        - tool must be one of: 'photostats', 'photo_pairing', 'pipeline_validation'
        - PhotoStats/PhotoPairing require collection_id
        - Pipeline Validation display-graph mode: collection_id NULL, pipeline_id required
        - completed_at must be >= started_at
        - duration_seconds must be >= 0
        - results_json must be valid JSON

    Indexes:
        - uuid (unique, for GUID lookups)
        - idx_results_collection: collection_id
        - idx_results_tool: tool
        - idx_results_created: created_at DESC
        - idx_results_collection_tool_date: (collection_id, tool, created_at DESC)
    """

    __tablename__ = "analysis_results"

    # GUID prefix for AnalysisResult entities
    GUID_PREFIX = "res"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    collection_id = Column(
        Integer,
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=True,  # Nullable for pipeline-only validation (display-graph mode)
        index=True
    )
    pipeline_id = Column(
        Integer,
        ForeignKey("pipelines.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    pipeline_version = Column(Integer, nullable=True)

    # Core fields
    tool = Column(String(50), nullable=False, index=True)
    status = Column(
        Enum(ResultStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # Timing
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=False)
    duration_seconds = Column(Float, nullable=False)

    # Results - JSONB for PostgreSQL, JSON fallback for SQLite testing
    results_json = Column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    report_html = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    # Metrics
    files_scanned = Column(Integer, nullable=True)
    issues_found = Column(Integer, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    collection = relationship("Collection", back_populates="analysis_results")
    pipeline = relationship("Pipeline", back_populates="analysis_results")

    # Indexes
    __table_args__ = (
        Index("idx_results_collection", "collection_id"),
        Index("idx_results_tool", "tool"),
        Index("idx_results_created", "created_at"),
        Index("idx_results_collection_tool_date", "collection_id", "tool", "created_at"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<AnalysisResult("
            f"id={self.id}, "
            f"collection_id={self.collection_id}, "
            f"tool='{self.tool}', "
            f"status={self.status.value if self.status else None}"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"Result #{self.id}: {self.tool} on collection {self.collection_id} ({self.status.value if self.status else 'unknown'})"

    @property
    def has_report(self) -> bool:
        """Check if HTML report is available."""
        return self.report_html is not None and len(self.report_html) > 0

    def get_result_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the result for API responses.

        Returns:
            Dictionary with key result metrics
        """
        return {
            "id": self.id,
            "collection_id": self.collection_id,
            "tool": self.tool,
            "status": self.status.value if self.status else None,
            "duration_seconds": self.duration_seconds,
            "files_scanned": self.files_scanned,
            "issues_found": self.issues_found,
            "has_report": self.has_report,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
