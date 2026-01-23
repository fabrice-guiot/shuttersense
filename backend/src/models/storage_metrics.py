"""
StorageMetrics model for tracking cumulative storage optimization statistics.

Stores team-level cumulative counters for reports generated, cleanup operations,
and estimated bytes freed. One row per team, created on first cleanup or job completion.

Design Rationale:
- Cumulative counters persist across cleanup runs for historical metrics
- BigInteger types handle large values (10K+ results, 100K+ files)
- Real-time byte counts computed from actual result data
- Team-scoped with unique constraint for one row per team
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, BigInteger, DateTime, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship

from backend.src.models import Base


class StorageMetrics(Base):
    """
    Storage metrics model for cumulative cleanup and generation statistics.

    Tracks team-level metrics for storage optimization effectiveness.
    Created on first job completion or cleanup run for a team.

    Attributes:
        id: Primary key
        team_id: Foreign key to Team (one row per team)
        total_reports_generated: Cumulative count of all job completions
        completed_jobs_purged: Cumulative completed jobs deleted by cleanup
        failed_jobs_purged: Cumulative failed jobs deleted by cleanup
        completed_results_purged_original: Original results purged (no_change_copy=false)
        completed_results_purged_copy: Copy results purged (no_change_copy=true)
        estimated_bytes_purged: Cumulative estimated bytes freed from DB
        updated_at: Last update timestamp

    Constraints:
        - Unique constraint on team_id (one metrics row per team)
        - All counter fields use BigInteger for large cumulative values
    """

    __tablename__ = "storage_metrics"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Team scope (one row per team)
    team_id = Column(
        Integer,
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Cumulative counters
    total_reports_generated = Column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Cumulative count of all job completions (COMPLETED, NO_CHANGE, FAILED)"
    )
    completed_jobs_purged = Column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Cumulative count of completed jobs deleted by cleanup"
    )
    failed_jobs_purged = Column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Cumulative count of failed jobs deleted by cleanup"
    )
    completed_results_purged_original = Column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Cumulative count of original results purged (no_change_copy=false)"
    )
    completed_results_purged_copy = Column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Cumulative count of copy results purged (no_change_copy=true)"
    )
    estimated_bytes_purged = Column(
        BigInteger,
        nullable=False,
        default=0,
        server_default="0",
        comment="Cumulative estimated bytes freed from DB (JSON + HTML sizes)"
    )

    # Timestamps
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    team = relationship("Team")

    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint("team_id", name="uq_storage_metrics_team"),
        Index("idx_storage_metrics_team", "team_id"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<StorageMetrics("
            f"team_id={self.team_id}, "
            f"total_reports_generated={self.total_reports_generated}, "
            f"estimated_bytes_purged={self.estimated_bytes_purged}"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"StorageMetrics for team {self.team_id}: {self.total_reports_generated} reports generated"
