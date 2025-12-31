"""
Job queue for sequential analysis execution.

This module provides an in-memory job queue for managing analysis tasks
(PhotoStats, Photo Pairing, Pipeline Validation) with position tracking
and cancellation support.

Based on research.md Task 4 decision: Use FastAPI BackgroundTasks with
in-memory job queue for sequential processing.
"""

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any


class JobStatus(Enum):
    """
    Status enum for analysis jobs.

    Represents the lifecycle states of an analysis job in the queue.

    States:
        QUEUED: Job is waiting in queue
        RUNNING: Job is currently executing
        COMPLETED: Job finished successfully
        FAILED: Job failed with error
        CANCELLED: Job was cancelled by user

    Task: T022 - JobStatus enum
    """
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AnalysisJob:
    """
    Metadata for an analysis job.

    Stores all information about a queued or running analysis task,
    including progress tracking, timestamps, and error information.

    Attributes:
        id: Unique job identifier (UUID)
        collection_id: ID of the collection being analyzed
        tool: Analysis tool name ('photostats', 'photo_pairing', 'pipeline_validation')
        pipeline_id: Optional pipeline ID for Pipeline Validation tool
        status: Current job status (JobStatus enum)
        created_at: Timestamp when job was created
        started_at: Timestamp when job started execution (None if not started)
        completed_at: Timestamp when job completed (None if not finished)
        progress: Progress metadata dict (e.g., {files_scanned: 100, stage: "scanning"})
        error_message: Error message if job failed (None if successful)
        result_id: ID of the analysis result in database (None until completed)

    Task: T023 - AnalysisJob dataclass
    """
    id: str
    collection_id: int
    tool: str
    pipeline_id: Optional[int]
    status: JobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    result_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert job to dictionary for API responses.

        Returns:
            dict: Job data with serialized timestamps
        """
        return {
            'id': self.id,
            'collection_id': self.collection_id,
            'tool': self.tool,
            'pipeline_id': self.pipeline_id,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'progress': self.progress,
            'error_message': self.error_message,
            'result_id': self.result_id
        }


class JobQueue:
    """
    In-memory job queue for analysis tasks.

    Manages sequential execution of analysis jobs with position tracking,
    cancellation support, and job metadata storage. Jobs are processed
    one at a time (FIFO order) to avoid resource contention and maintain
    simplicity (research.md Task 4).

    Thread Safety:
        All operations are protected by a threading.Lock to ensure safe
        concurrent access from multiple FastAPI request handlers.

    Features:
        - FIFO job queue with position tracking
        - Job cancellation (queued jobs only, not running)
        - Progress tracking via job.progress dict
        - Job history retention (completed/failed jobs)
        - Single worker pattern (one job at a time)

    Tasks implemented:
        - T024: JobQueue class with position tracking
        - T025: enqueue(), dequeue(), cancel(), get_position() methods

    Usage:
        # Initialize queue (singleton in FastAPI app state)
        queue = JobQueue()

        # Create and enqueue job
        job = AnalysisJob(
            id=str(uuid.uuid4()),
            collection_id=1,
            tool="photostats",
            pipeline_id=None,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )
        position = queue.enqueue(job)

        # Get job position
        position = queue.get_position(job.id)

        # Dequeue next job for processing
        next_job = queue.dequeue()

        # Cancel queued job
        queue.cancel(job.id)
    """

    def __init__(self):
        """
        Initialize the job queue.

        Task: T024 - JobQueue initialization with thread safety
        """
        self._jobs: Dict[str, AnalysisJob] = {}  # All jobs (queued + running + completed)
        self._queue: List[str] = []  # Job IDs in FIFO order
        self._lock = threading.Lock()
        self._current_job: Optional[str] = None  # Currently running job ID

    def enqueue(self, job: AnalysisJob) -> int:
        """
        Add job to queue and return position.

        Args:
            job: AnalysisJob to enqueue

        Returns:
            int: Position in queue (1-indexed, 1 = next to run)

        Thread Safety:
            Protected by lock for safe concurrent access

        Example:
            >>> queue = JobQueue()
            >>> job = AnalysisJob(
            ...     id=str(uuid.uuid4()),
            ...     collection_id=1,
            ...     tool="photostats",
            ...     pipeline_id=None,
            ...     status=JobStatus.QUEUED,
            ...     created_at=datetime.utcnow()
            ... )
            >>> position = queue.enqueue(job)
            >>> print(f"Job queued at position {position}")
            Job queued at position 1

        Task: T025 - enqueue() method implementation
        """
        with self._lock:
            self._jobs[job.id] = job
            self._queue.append(job.id)
            return len(self._queue)  # Position in queue (1-indexed)

    def dequeue(self) -> Optional[AnalysisJob]:
        """
        Get next job from queue for processing.

        Removes the first job from the queue and marks it as the current
        running job. Returns None if queue is empty.

        Returns:
            AnalysisJob: Next job to process
            None: If queue is empty

        Thread Safety:
            Protected by lock for safe concurrent access

        Example:
            >>> job = queue.dequeue()
            >>> if job:
            ...     job.status = JobStatus.RUNNING
            ...     job.started_at = datetime.utcnow()
            ...     # Execute analysis tool...

        Task: T025 - dequeue() method implementation
        """
        with self._lock:
            if not self._queue:
                return None

            job_id = self._queue.pop(0)
            job = self._jobs[job_id]
            self._current_job = job_id
            return job

    def get_position(self, job_id: str) -> Optional[int]:
        """
        Get job position in queue.

        Args:
            job_id: Job ID to check

        Returns:
            int: Position in queue (1-indexed, 1 = next to run)
            None: If job is not in queue (running, completed, or not found)

        Thread Safety:
            Protected by lock for safe concurrent access

        Example:
            >>> position = queue.get_position(job_id)
            >>> if position:
            ...     estimated_minutes = (position - 1) * 5
            ...     print(f"Position: {position}. Estimated start: {estimated_minutes} min")

        Task: T025 - get_position() method implementation
        """
        with self._lock:
            try:
                return self._queue.index(job_id) + 1  # 1-indexed position
            except ValueError:
                return None  # Not in queue (running, completed, or doesn't exist)

    def cancel(self, job_id: str):
        """
        Cancel a queued job.

        Removes the job from the queue and marks it as CANCELLED.
        Cannot cancel running jobs (research.md Task 4: too complex for v1).

        Args:
            job_id: Job ID to cancel

        Raises:
            ValueError: If job is currently running or not found

        Thread Safety:
            Protected by lock for safe concurrent access

        Example:
            >>> try:
            ...     queue.cancel(job_id)
            ...     print("Job cancelled successfully")
            ... except ValueError as e:
            ...     print(f"Cannot cancel: {e}")

        Task: T025 - cancel() method implementation
        """
        with self._lock:
            if job_id in self._queue:
                # Remove from queue
                self._queue.remove(job_id)
                # Mark as cancelled
                self._jobs[job_id].status = JobStatus.CANCELLED
                self._jobs[job_id].completed_at = datetime.utcnow()
            elif self._current_job == job_id:
                raise ValueError("Cannot cancel running job")
            else:
                raise ValueError("Job not found or already completed")

    def get_job(self, job_id: str) -> Optional[AnalysisJob]:
        """
        Get job by ID.

        Args:
            job_id: Job ID to retrieve

        Returns:
            AnalysisJob: Job metadata
            None: If job not found

        Thread Safety:
            Protected by lock for safe concurrent access
        """
        with self._lock:
            return self._jobs.get(job_id)

    def find_active_job(self, collection_id: int, tool: str) -> Optional[AnalysisJob]:
        """
        Find active job for a collection and tool.

        Checks if there's already a queued or running job for the same
        collection and tool. Prevents duplicate analysis requests.

        Args:
            collection_id: Collection ID
            tool: Tool name ('photostats', 'photo_pairing', 'pipeline_validation')

        Returns:
            AnalysisJob: Active job if found
            None: If no active job for this collection/tool

        Thread Safety:
            Protected by lock for safe concurrent access

        Example:
            >>> existing = queue.find_active_job(collection_id=1, tool="photostats")
            >>> if existing:
            ...     return {"message": "Analysis already in progress", "job_id": existing.id}
        """
        with self._lock:
            for job in self._jobs.values():
                if (job.collection_id == collection_id and
                    job.tool == tool and
                    job.status in (JobStatus.QUEUED, JobStatus.RUNNING)):
                    return job
            return None

    def get_queue_status(self) -> Dict[str, Any]:
        """
        Get queue status for monitoring.

        Returns:
            dict: Queue statistics

        Example:
            >>> status = queue.get_queue_status()
            >>> print(status)
            {
                'queued_count': 3,
                'running_count': 1,
                'completed_count': 10,
                'failed_count': 2,
                'current_job_id': 'abc123...'
            }
        """
        with self._lock:
            status_counts = {
                'queued_count': 0,
                'running_count': 0,
                'completed_count': 0,
                'failed_count': 0,
                'cancelled_count': 0
            }

            for job in self._jobs.values():
                if job.status == JobStatus.QUEUED:
                    status_counts['queued_count'] += 1
                elif job.status == JobStatus.RUNNING:
                    status_counts['running_count'] += 1
                elif job.status == JobStatus.COMPLETED:
                    status_counts['completed_count'] += 1
                elif job.status == JobStatus.FAILED:
                    status_counts['failed_count'] += 1
                elif job.status == JobStatus.CANCELLED:
                    status_counts['cancelled_count'] += 1

            status_counts['current_job_id'] = self._current_job
            return status_counts

    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """
        Remove completed/failed jobs older than max_age_hours.

        Prevents unbounded memory growth by removing old job history.
        Only removes jobs in terminal states (COMPLETED, FAILED, CANCELLED).

        Args:
            max_age_hours: Maximum age in hours for job retention

        Returns:
            int: Number of jobs removed

        Thread Safety:
            Protected by lock for safe concurrent access

        Example:
            >>> # Remove jobs older than 24 hours
            >>> removed = queue.cleanup_old_jobs(max_age_hours=24)
            >>> print(f"Removed {removed} old jobs")
        """
        with self._lock:
            cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
            removed_count = 0

            for job_id, job in list(self._jobs.items()):
                # Only remove terminal state jobs
                if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                    if job.completed_at and job.completed_at < cutoff:
                        del self._jobs[job_id]
                        removed_count += 1

            return removed_count


# Singleton instance for dependency injection in FastAPI
_job_queue_instance: Optional[JobQueue] = None


def get_job_queue() -> JobQueue:
    """
    Get or create the singleton JobQueue instance.

    This function is used as a FastAPI dependency for routes that need
    to access the job queue.

    Returns:
        JobQueue: Singleton instance

    Usage in FastAPI:
        from fastapi import Depends
        from backend.src.utils.job_queue import get_job_queue

        @app.post("/tools/photostats")
        async def run_photostats(
            collection_id: int,
            queue: JobQueue = Depends(get_job_queue)
        ):
            # Check for existing job
            existing = queue.find_active_job(collection_id, "photostats")
            if existing:
                return {"job_id": existing.id, "position": queue.get_position(existing.id)}

            # Create new job
            job = AnalysisJob(...)
            position = queue.enqueue(job)
            return {"job_id": job.id, "position": position}
    """
    global _job_queue_instance

    if _job_queue_instance is None:
        _job_queue_instance = JobQueue()

    return _job_queue_instance


def init_job_queue() -> JobQueue:
    """
    Initialize the job queue singleton.

    This should be called during application startup to ensure the queue
    is ready before handling requests.

    Returns:
        JobQueue: Initialized singleton instance
    """
    global _job_queue_instance
    _job_queue_instance = JobQueue()
    return _job_queue_instance


def create_job_id() -> str:
    """
    Generate a unique job ID.

    Returns:
        str: UUID4 string

    Example:
        >>> job_id = create_job_id()
        >>> print(job_id)
        '550e8400-e29b-41d4-a716-446655440000'
    """
    return str(uuid.uuid4())
