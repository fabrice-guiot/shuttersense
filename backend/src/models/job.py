"""
Job model for persistent job queue with agent routing.

Represents a unit of work for tool execution. Jobs are queued in PostgreSQL
and claimed by agents for execution. Supports agent binding, capability-based
routing, and auto-refresh scheduling.

Design Rationale:
- Persistent queue replaces in-memory job queue for reliability
- Agent routing via bound_agent_id (LOCAL collections) or capabilities (remote)
- Progress stored in JSONB for flexible structure
- Retry mechanism with max_retries for fault tolerance
- Parent job reference for auto-refresh chains
"""

import enum
import json
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin

if TYPE_CHECKING:
    from backend.src.models.team import Team
    from backend.src.models.collection import Collection
    from backend.src.models.pipeline import Pipeline
    from backend.src.models.agent import Agent
    from backend.src.models.analysis_result import AnalysisResult


class JobStatus(str, enum.Enum):
    """
    Job status enumeration.

    Represents the lifecycle states of a job:
    - SCHEDULED: Waiting for scheduled_for time (auto-refresh)
    - PENDING: Ready to be claimed by an agent
    - ASSIGNED: Claimed by agent, not yet started
    - RUNNING: Agent actively executing
    - COMPLETED: Successfully finished
    - FAILED: Execution failed (may retry)
    - CANCELLED: Cancelled by user or system
    """
    SCHEDULED = "scheduled"
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(Base, GuidMixin):
    """
    Job model representing a unit of work for tool execution.

    Jobs are queued in PostgreSQL and claimed by agents using
    FOR UPDATE SKIP LOCKED for atomic claiming.

    Attributes:
        id: Primary key (internal, never exposed)
        uuid: UUIDv7 for external identification (inherited from GuidMixin)
        guid: GUID string property (job_xxx, inherited from GuidMixin)
        team_id: Team this job belongs to (FK to teams)
        collection_id: Collection being analyzed (FK, nullable for display_graph)
        pipeline_id: Pipeline used (FK, nullable)
        pipeline_version: Pipeline version at execution time
        tool: Analysis tool (photostats, photo_pairing, pipeline_validation)
        mode: Execution mode (e.g., 'collection', 'display_graph')
        status: Job status (scheduled/pending/assigned/running/completed/failed/cancelled)
        priority: Job priority (higher = more urgent, default 0)
        bound_agent_id: Required agent for LOCAL collections (FK to agents)
        required_capabilities_json: Capabilities needed for unbound jobs
        agent_id: Currently assigned/executing agent (FK to agents)
        assigned_at: When job was assigned to agent
        started_at: When job execution began
        completed_at: When job finished
        progress_json: Current progress data (stage, percentage, files)
        error_message: Error message if failed
        retry_count: Number of retry attempts
        max_retries: Maximum retries allowed (default 3)
        scheduled_for: Earliest execution time (NULL = immediate)
        parent_job_id: Previous job in refresh chain (self-ref FK)
        signing_secret_hash: For HMAC result verification
        result_id: Associated analysis result (FK to analysis_results)
        created_at: Creation timestamp
        updated_at: Last modification timestamp

    Relationships:
        team: Team this job belongs to (many-to-one)
        collection: Collection being analyzed (many-to-one)
        pipeline: Pipeline used (many-to-one)
        bound_agent: Agent bound to this job (many-to-one)
        agent: Currently executing agent (many-to-one)
        parent_job: Previous job in refresh chain (self-referential)
        child_jobs: Jobs created from this job (refresh chain)
        result: Analysis result (one-to-one)

    Indexes:
        - uuid (unique, for GUID lookups)
        - team_id (for team-scoped queries)
        - status (for filtering by status)
        - (team_id, status, scheduled_for, priority) for job claiming
        - Partial unique on (collection_id, tool) WHERE status='scheduled'
    """

    __tablename__ = "jobs"

    # GUID prefix for Job entities
    GUID_PREFIX = "job"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Team membership
    team_id = Column(
        Integer,
        ForeignKey("teams.id", name="fk_jobs_team_id"),
        nullable=False,
        index=True
    )

    # Collection and pipeline references
    collection_id = Column(
        Integer,
        ForeignKey("collections.id", name="fk_jobs_collection_id", ondelete="CASCADE"),
        nullable=True,  # Nullable for display_graph mode
        index=True
    )
    pipeline_id = Column(
        Integer,
        ForeignKey("pipelines.id", name="fk_jobs_pipeline_id", ondelete="SET NULL"),
        nullable=True
    )
    pipeline_version = Column(Integer, nullable=True)

    # Tool and mode
    tool = Column(String(50), nullable=False)
    mode = Column(String(50), nullable=True)

    # Status and priority
    # Use native_enum=False to store as string (matches migration's String(20) column)
    status = Column(
        Enum(JobStatus, native_enum=False),
        default=JobStatus.PENDING,
        nullable=False,
        index=True
    )
    priority = Column(Integer, default=0, nullable=False)

    # Agent binding and routing
    bound_agent_id = Column(
        Integer,
        ForeignKey("agents.id", name="fk_jobs_bound_agent_id"),
        nullable=True,
        index=True
    )
    required_capabilities_json = Column(
        JSONB().with_variant(Text, "sqlite"),
        nullable=False,
        default=list
    )

    # Currently executing agent
    agent_id = Column(
        Integer,
        ForeignKey("agents.id", name="fk_jobs_agent_id"),
        nullable=True,
        index=True
    )

    # Execution timing
    assigned_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Progress tracking
    progress_json = Column(
        JSONB().with_variant(Text, "sqlite"),
        nullable=True
    )

    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)

    # Scheduling
    scheduled_for = Column(DateTime, nullable=True, index=True)

    # Refresh chain
    parent_job_id = Column(
        Integer,
        ForeignKey("jobs.id", name="fk_jobs_parent_job_id"),
        nullable=True
    )

    # Result attestation
    signing_secret_hash = Column(String(64), nullable=True)

    # Analysis result reference
    result_id = Column(
        Integer,
        ForeignKey("analysis_results.id", name="fk_jobs_result_id", ondelete="SET NULL"),
        nullable=True
    )

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
        lazy="joined"
    )
    collection = relationship(
        "Collection",
        back_populates="jobs",
        lazy="joined"
    )
    pipeline = relationship(
        "Pipeline",
        lazy="joined"
    )
    bound_agent = relationship(
        "Agent",
        foreign_keys=[bound_agent_id],
        lazy="joined"
    )
    agent = relationship(
        "Agent",
        foreign_keys=[agent_id],
        lazy="joined"
    )
    parent_job = relationship(
        "Job",
        remote_side=[id],
        foreign_keys=[parent_job_id],
        backref="child_jobs",
        lazy="joined"
    )
    result = relationship(
        "AnalysisResult",
        lazy="joined"
    )

    # Table-level indexes
    __table_args__ = (
        Index("ix_jobs_claimable", "team_id", "status", "scheduled_for", "priority"),
    )

    @property
    def required_capabilities(self) -> List[str]:
        """
        Get the required capabilities as a list.

        Returns:
            List of required capability strings
        """
        if self.required_capabilities_json is None:
            return []
        if isinstance(self.required_capabilities_json, str):
            import json
            return json.loads(self.required_capabilities_json)
        return self.required_capabilities_json

    @required_capabilities.setter
    def required_capabilities(self, value: List[str]) -> None:
        """
        Set the required capabilities.

        Args:
            value: List of required capability strings
        """
        # Serialize for SQLite compatibility (uses Text variant)
        if value is None:
            self.required_capabilities_json = None
        else:
            self.required_capabilities_json = json.dumps(value)

    @property
    def progress(self) -> Optional[Dict[str, Any]]:
        """
        Get the progress data as a dictionary.

        Returns:
            Progress dictionary or None
        """
        if self.progress_json is None:
            return None
        if isinstance(self.progress_json, str):
            import json
            return json.loads(self.progress_json)
        return self.progress_json

    @progress.setter
    def progress(self, value: Optional[Dict[str, Any]]) -> None:
        """
        Set the progress data.

        Args:
            value: Progress dictionary or None
        """
        # Serialize for SQLite compatibility (uses Text variant)
        if value is None:
            self.progress_json = None
        else:
            self.progress_json = json.dumps(value)

    @property
    def is_claimable(self) -> bool:
        """
        Check if the job can be claimed by an agent.

        A job is claimable if:
        - Status is PENDING, or
        - Status is SCHEDULED and scheduled_for <= now

        Returns:
            True if job can be claimed
        """
        if self.status == JobStatus.PENDING:
            return True
        if self.status == JobStatus.SCHEDULED:
            if self.scheduled_for is None:
                return True
            return datetime.utcnow() >= self.scheduled_for
        return False

    @property
    def is_terminal(self) -> bool:
        """
        Check if the job is in a terminal state.

        Terminal states are COMPLETED, FAILED, or CANCELLED.

        Returns:
            True if job is in terminal state
        """
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)

    @property
    def can_retry(self) -> bool:
        """
        Check if the job can be retried.

        A job can be retried if it's failed and retry_count < max_retries.

        Returns:
            True if job can be retried
        """
        return self.status == JobStatus.FAILED and self.retry_count < self.max_retries

    def assign_to_agent(self, agent_id: int) -> None:
        """
        Assign the job to an agent.

        Args:
            agent_id: Internal ID of the agent
        """
        self.agent_id = agent_id
        self.status = JobStatus.ASSIGNED
        self.assigned_at = datetime.utcnow()

    def start_execution(self) -> None:
        """Mark the job as started."""
        self.status = JobStatus.RUNNING
        self.started_at = datetime.utcnow()

    def complete(self, result_id: Optional[int] = None) -> None:
        """
        Mark the job as completed.

        Args:
            result_id: Optional analysis result ID
        """
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if result_id is not None:
            self.result_id = result_id

    def fail(self, error_message: str) -> None:
        """
        Mark the job as failed.

        Args:
            error_message: Error message describing the failure
        """
        self.status = JobStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message

    def cancel(self) -> None:
        """Mark the job as cancelled."""
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.utcnow()

    def release(self) -> None:
        """
        Release the job back to pending state.

        Used when an agent goes offline or fails to complete the job.
        """
        self.agent_id = None
        self.assigned_at = None
        self.started_at = None
        self.status = JobStatus.PENDING
        self.progress_json = None

    def prepare_retry(self) -> None:
        """
        Prepare the job for retry.

        Increments retry_count and releases the job.
        """
        self.retry_count += 1
        self.release()

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Job("
            f"id={self.id}, "
            f"tool='{self.tool}', "
            f"status={self.status.value}, "
            f"team_id={self.team_id}"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"Job {self.guid} ({self.tool}, {self.status.value})"
