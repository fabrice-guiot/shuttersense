"""
Unit tests for job queue for sequential analysis execution.

Tests the JobQueue and AnalysisJob for:
- Job enqueueing and dequeueing
- Position tracking
- Job cancellation
- Status management
- Thread safety
- Finding active jobs
- Queue cleanup

Task: T104c - Unit tests for job_queue module
"""

import threading
import uuid
from datetime import datetime, timedelta
import pytest
from freezegun import freeze_time

from backend.src.utils.job_queue import (
    JobStatus,
    AnalysisJob,
    JobQueue,
    get_job_queue,
    init_job_queue,
    create_job_id
)


class TestJobStatus:
    """Tests for JobStatus enum."""

    def test_job_status_values(self):
        """Test JobStatus enum has correct values."""
        assert JobStatus.QUEUED.value == "queued"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELLED.value == "cancelled"

    def test_job_status_enum_members(self):
        """Test all JobStatus enum members exist."""
        expected_statuses = {"QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"}
        actual_statuses = {status.name for status in JobStatus}
        assert actual_statuses == expected_statuses


class TestAnalysisJob:
    """Tests for AnalysisJob dataclass."""

    def test_create_analysis_job(self):
        """Test creating an AnalysisJob instance."""
        job_id = str(uuid.uuid4())
        created_at = datetime.utcnow()

        job = AnalysisJob(
            id=job_id,
            collection_id=1,
            tool="photostats",
            pipeline_id=None,
            status=JobStatus.QUEUED,
            created_at=created_at
        )

        assert job.id == job_id
        assert job.collection_id == 1
        assert job.tool == "photostats"
        assert job.pipeline_id is None
        assert job.status == JobStatus.QUEUED
        assert job.created_at == created_at
        assert job.started_at is None
        assert job.completed_at is None
        assert job.progress == {}
        assert job.error_message is None
        assert job.result_id is None

    def test_create_job_with_pipeline_id(self):
        """Test creating an AnalysisJob with pipeline_id for pipeline validation."""
        job = AnalysisJob(
            id=str(uuid.uuid4()),
            collection_id=1,
            tool="pipeline_validation",
            pipeline_id=5,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )

        assert job.tool == "pipeline_validation"
        assert job.pipeline_id == 5

    def test_job_to_dict(self):
        """Test converting job to dictionary."""
        job_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        started_at = datetime.utcnow()
        completed_at = datetime.utcnow()

        job = AnalysisJob(
            id=job_id,
            collection_id=1,
            tool="photostats",
            pipeline_id=None,
            status=JobStatus.COMPLETED,
            created_at=created_at,
            started_at=started_at,
            completed_at=completed_at,
            progress={'files_scanned': 100, 'stage': 'complete'},
            error_message=None,
            result_id=42
        )

        job_dict = job.to_dict()

        assert job_dict['id'] == job_id
        assert job_dict['collection_id'] == 1
        assert job_dict['tool'] == "photostats"
        assert job_dict['pipeline_id'] is None
        assert job_dict['status'] == "completed"
        assert job_dict['created_at'] == created_at.isoformat()
        assert job_dict['started_at'] == started_at.isoformat()
        assert job_dict['completed_at'] == completed_at.isoformat()
        assert job_dict['progress'] == {'files_scanned': 100, 'stage': 'complete'}
        assert job_dict['error_message'] is None
        assert job_dict['result_id'] == 42

    def test_job_to_dict_with_none_timestamps(self):
        """Test to_dict handles None timestamps correctly."""
        job = AnalysisJob(
            id=str(uuid.uuid4()),
            collection_id=1,
            tool="photostats",
            pipeline_id=None,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )

        job_dict = job.to_dict()

        assert job_dict['started_at'] is None
        assert job_dict['completed_at'] is None

    def test_job_with_error_message(self):
        """Test job with error message for failed status."""
        job = AnalysisJob(
            id=str(uuid.uuid4()),
            collection_id=1,
            tool="photostats",
            pipeline_id=None,
            status=JobStatus.FAILED,
            created_at=datetime.utcnow(),
            error_message="Connection timeout"
        )

        assert job.status == JobStatus.FAILED
        assert job.error_message == "Connection timeout"


class TestJobQueueBasics:
    """Tests for basic JobQueue operations."""

    def test_init_empty_queue(self):
        """Test initializing an empty job queue."""
        queue = JobQueue()

        status = queue.get_queue_status()
        assert status['queued_count'] == 0
        assert status['running_count'] == 0
        assert status['completed_count'] == 0
        assert status['current_job_id'] is None

    def test_enqueue_single_job(self):
        """Test enqueueing a single job."""
        queue = JobQueue()
        job = AnalysisJob(
            id=str(uuid.uuid4()),
            collection_id=1,
            tool="photostats",
            pipeline_id=None,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )

        position = queue.enqueue(job)

        assert position == 1
        assert queue.get_queue_status()['queued_count'] == 1

    def test_enqueue_multiple_jobs(self):
        """Test enqueueing multiple jobs returns correct positions."""
        queue = JobQueue()

        job1 = AnalysisJob(
            id=str(uuid.uuid4()),
            collection_id=1,
            tool="photostats",
            pipeline_id=None,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )
        job2 = AnalysisJob(
            id=str(uuid.uuid4()),
            collection_id=2,
            tool="photo_pairing",
            pipeline_id=None,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )
        job3 = AnalysisJob(
            id=str(uuid.uuid4()),
            collection_id=3,
            tool="pipeline_validation",
            pipeline_id=1,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )

        pos1 = queue.enqueue(job1)
        pos2 = queue.enqueue(job2)
        pos3 = queue.enqueue(job3)

        assert pos1 == 1
        assert pos2 == 2
        assert pos3 == 3
        assert queue.get_queue_status()['queued_count'] == 3

    def test_dequeue_from_empty_queue(self):
        """Test dequeueing from empty queue returns None."""
        queue = JobQueue()

        job = queue.dequeue()

        assert job is None

    def test_dequeue_fifo_order(self):
        """Test dequeueing jobs in FIFO order."""
        queue = JobQueue()

        job1 = AnalysisJob(
            id="job1",
            collection_id=1,
            tool="photostats",
            pipeline_id=None,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )
        job2 = AnalysisJob(
            id="job2",
            collection_id=2,
            tool="photo_pairing",
            pipeline_id=None,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )

        queue.enqueue(job1)
        queue.enqueue(job2)

        dequeued1 = queue.dequeue()
        dequeued2 = queue.dequeue()

        assert dequeued1.id == "job1"
        assert dequeued2.id == "job2"

    def test_dequeue_sets_current_job(self):
        """Test dequeueing sets the current job."""
        queue = JobQueue()
        job = AnalysisJob(
            id="job1",
            collection_id=1,
            tool="photostats",
            pipeline_id=None,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )

        queue.enqueue(job)
        dequeued = queue.dequeue()
        # Caller is responsible for updating status
        dequeued.status = JobStatus.RUNNING

        status = queue.get_queue_status()
        assert status['current_job_id'] == "job1"
        assert status['queued_count'] == 0
        assert status['running_count'] == 1


class TestJobPosition:
    """Tests for job position tracking."""

    def test_get_position_first_in_queue(self):
        """Test getting position for first job in queue."""
        queue = JobQueue()
        job = AnalysisJob(
            id="job1",
            collection_id=1,
            tool="photostats",
            pipeline_id=None,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )

        queue.enqueue(job)
        position = queue.get_position("job1")

        assert position == 1

    def test_get_position_multiple_jobs(self):
        """Test getting positions for multiple jobs."""
        queue = JobQueue()

        job1 = AnalysisJob(id="job1", collection_id=1, tool="photostats", pipeline_id=None, status=JobStatus.QUEUED, created_at=datetime.utcnow())
        job2 = AnalysisJob(id="job2", collection_id=2, tool="photostats", pipeline_id=None, status=JobStatus.QUEUED, created_at=datetime.utcnow())
        job3 = AnalysisJob(id="job3", collection_id=3, tool="photostats", pipeline_id=None, status=JobStatus.QUEUED, created_at=datetime.utcnow())

        queue.enqueue(job1)
        queue.enqueue(job2)
        queue.enqueue(job3)

        assert queue.get_position("job1") == 1
        assert queue.get_position("job2") == 2
        assert queue.get_position("job3") == 3

    def test_get_position_after_dequeue(self):
        """Test positions update after dequeueing."""
        queue = JobQueue()

        job1 = AnalysisJob(id="job1", collection_id=1, tool="photostats", pipeline_id=None, status=JobStatus.QUEUED, created_at=datetime.utcnow())
        job2 = AnalysisJob(id="job2", collection_id=2, tool="photostats", pipeline_id=None, status=JobStatus.QUEUED, created_at=datetime.utcnow())
        job3 = AnalysisJob(id="job3", collection_id=3, tool="photostats", pipeline_id=None, status=JobStatus.QUEUED, created_at=datetime.utcnow())

        queue.enqueue(job1)
        queue.enqueue(job2)
        queue.enqueue(job3)

        queue.dequeue()  # Remove job1

        # Positions should shift
        assert queue.get_position("job1") is None  # No longer in queue
        assert queue.get_position("job2") == 1
        assert queue.get_position("job3") == 2

    def test_get_position_not_in_queue(self):
        """Test getting position for non-existent job returns None."""
        queue = JobQueue()

        position = queue.get_position("nonexistent")

        assert position is None


class TestJobCancellation:
    """Tests for job cancellation."""

    def test_cancel_queued_job(self):
        """Test cancelling a queued job."""
        queue = JobQueue()
        job = AnalysisJob(
            id="job1",
            collection_id=1,
            tool="photostats",
            pipeline_id=None,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )

        queue.enqueue(job)
        queue.cancel("job1")

        # Job should be removed from queue
        assert queue.get_position("job1") is None
        assert queue.get_queue_status()['queued_count'] == 0
        assert queue.get_queue_status()['cancelled_count'] == 1

        # Job should be marked as cancelled
        cancelled_job = queue.get_job("job1")
        assert cancelled_job.status == JobStatus.CANCELLED
        assert cancelled_job.completed_at is not None

    def test_cancel_running_job_raises_error(self):
        """Test cancelling a running job raises ValueError."""
        queue = JobQueue()
        job = AnalysisJob(
            id="job1",
            collection_id=1,
            tool="photostats",
            pipeline_id=None,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )

        queue.enqueue(job)
        queue.dequeue()  # Job is now running

        with pytest.raises(ValueError) as exc_info:
            queue.cancel("job1")

        assert "Cannot cancel running job" in str(exc_info.value)

    def test_cancel_nonexistent_job_raises_error(self):
        """Test cancelling non-existent job raises ValueError."""
        queue = JobQueue()

        with pytest.raises(ValueError) as exc_info:
            queue.cancel("nonexistent")

        assert "Job not found or already completed" in str(exc_info.value)

    def test_cancel_middle_job_updates_positions(self):
        """Test cancelling a job in the middle updates positions."""
        queue = JobQueue()

        job1 = AnalysisJob(id="job1", collection_id=1, tool="photostats", pipeline_id=None, status=JobStatus.QUEUED, created_at=datetime.utcnow())
        job2 = AnalysisJob(id="job2", collection_id=2, tool="photostats", pipeline_id=None, status=JobStatus.QUEUED, created_at=datetime.utcnow())
        job3 = AnalysisJob(id="job3", collection_id=3, tool="photostats", pipeline_id=None, status=JobStatus.QUEUED, created_at=datetime.utcnow())

        queue.enqueue(job1)
        queue.enqueue(job2)
        queue.enqueue(job3)

        queue.cancel("job2")

        # Positions should update
        assert queue.get_position("job1") == 1
        assert queue.get_position("job2") is None
        assert queue.get_position("job3") == 2


class TestGetJob:
    """Tests for retrieving jobs by ID."""

    def test_get_job_exists(self):
        """Test getting a job by ID."""
        queue = JobQueue()
        job = AnalysisJob(
            id="job1",
            collection_id=1,
            tool="photostats",
            pipeline_id=None,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )

        queue.enqueue(job)
        retrieved = queue.get_job("job1")

        assert retrieved is not None
        assert retrieved.id == "job1"
        assert retrieved.collection_id == 1

    def test_get_job_not_exists(self):
        """Test getting non-existent job returns None."""
        queue = JobQueue()

        retrieved = queue.get_job("nonexistent")

        assert retrieved is None


class TestFindActiveJob:
    """Tests for finding active jobs."""

    def test_find_active_queued_job(self):
        """Test finding a queued job for collection and tool."""
        queue = JobQueue()
        job = AnalysisJob(
            id="job1",
            collection_id=1,
            tool="photostats",
            pipeline_id=None,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )

        queue.enqueue(job)
        found = queue.find_active_job(collection_id=1, tool="photostats")

        assert found is not None
        assert found.id == "job1"

    def test_find_active_running_job(self):
        """Test finding a running job for collection and tool."""
        queue = JobQueue()
        job = AnalysisJob(
            id="job1",
            collection_id=1,
            tool="photostats",
            pipeline_id=None,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )

        queue.enqueue(job)
        dequeued = queue.dequeue()
        dequeued.status = JobStatus.RUNNING

        found = queue.find_active_job(collection_id=1, tool="photostats")

        assert found is not None
        assert found.id == "job1"
        assert found.status == JobStatus.RUNNING

    def test_find_active_job_different_tool(self):
        """Test finding active job for different tool returns None."""
        queue = JobQueue()
        job = AnalysisJob(
            id="job1",
            collection_id=1,
            tool="photostats",
            pipeline_id=None,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )

        queue.enqueue(job)
        found = queue.find_active_job(collection_id=1, tool="photo_pairing")

        assert found is None

    def test_find_active_job_different_collection(self):
        """Test finding active job for different collection returns None."""
        queue = JobQueue()
        job = AnalysisJob(
            id="job1",
            collection_id=1,
            tool="photostats",
            pipeline_id=None,
            status=JobStatus.QUEUED,
            created_at=datetime.utcnow()
        )

        queue.enqueue(job)
        found = queue.find_active_job(collection_id=2, tool="photostats")

        assert found is None

    def test_find_active_job_completed_not_found(self):
        """Test completed jobs are not considered active."""
        queue = JobQueue()
        job = AnalysisJob(
            id="job1",
            collection_id=1,
            tool="photostats",
            pipeline_id=None,
            status=JobStatus.COMPLETED,
            created_at=datetime.utcnow()
        )

        queue.enqueue(job)
        found = queue.find_active_job(collection_id=1, tool="photostats")

        # Should not find completed jobs
        assert found is None


class TestQueueStatus:
    """Tests for queue status monitoring."""

    def test_queue_status_empty(self):
        """Test queue status for empty queue."""
        queue = JobQueue()

        status = queue.get_queue_status()

        assert status['queued_count'] == 0
        assert status['running_count'] == 0
        assert status['completed_count'] == 0
        assert status['failed_count'] == 0
        assert status['cancelled_count'] == 0
        assert status['current_job_id'] is None

    def test_queue_status_with_jobs(self):
        """Test queue status with various job states."""
        queue = JobQueue()

        # Queued jobs
        job1 = AnalysisJob(id="job1", collection_id=1, tool="photostats", pipeline_id=None, status=JobStatus.QUEUED, created_at=datetime.utcnow())
        job2 = AnalysisJob(id="job2", collection_id=2, tool="photostats", pipeline_id=None, status=JobStatus.QUEUED, created_at=datetime.utcnow())

        queue.enqueue(job1)
        queue.enqueue(job2)

        # Dequeue one (running)
        running_job = queue.dequeue()
        running_job.status = JobStatus.RUNNING

        # Completed job
        completed_job = AnalysisJob(id="job3", collection_id=3, tool="photostats", pipeline_id=None, status=JobStatus.COMPLETED, created_at=datetime.utcnow())
        queue.enqueue(completed_job)

        # Failed job
        failed_job = AnalysisJob(id="job4", collection_id=4, tool="photostats", pipeline_id=None, status=JobStatus.FAILED, created_at=datetime.utcnow())
        queue.enqueue(failed_job)

        status = queue.get_queue_status()

        assert status['queued_count'] == 1  # job2
        assert status['running_count'] == 1  # job1
        assert status['completed_count'] == 1  # job3
        assert status['failed_count'] == 1  # job4
        assert status['current_job_id'] == "job1"


class TestCleanupOldJobs:
    """Tests for cleaning up old jobs."""

    @freeze_time("2025-01-01 12:00:00")
    def test_cleanup_old_completed_jobs(self):
        """Test cleanup removes old completed jobs."""
        queue = JobQueue()

        # Create old completed job (25 hours ago)
        with freeze_time("2024-12-31 11:00:00"):
            old_job = AnalysisJob(
                id="old_job",
                collection_id=1,
                tool="photostats",
                pipeline_id=None,
                status=JobStatus.COMPLETED,
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            queue.enqueue(old_job)

        # Create recent completed job (12 hours ago)
        with freeze_time("2025-01-01 00:00:00"):
            recent_job = AnalysisJob(
                id="recent_job",
                collection_id=2,
                tool="photostats",
                pipeline_id=None,
                status=JobStatus.COMPLETED,
                created_at=datetime.utcnow(),
                completed_at=datetime.utcnow()
            )
            queue.enqueue(recent_job)

        # Cleanup jobs older than 24 hours
        removed = queue.cleanup_old_jobs(max_age_hours=24)

        assert removed == 1
        assert queue.get_job("old_job") is None
        assert queue.get_job("recent_job") is not None

    @freeze_time("2025-01-01 12:00:00")
    def test_cleanup_preserves_active_jobs(self):
        """Test cleanup doesn't remove queued or running jobs."""
        queue = JobQueue()

        # Create old queued job
        with freeze_time("2024-12-31 11:00:00"):
            queued_job = AnalysisJob(
                id="queued_job",
                collection_id=1,
                tool="photostats",
                pipeline_id=None,
                status=JobStatus.QUEUED,
                created_at=datetime.utcnow()
            )
            queue.enqueue(queued_job)

        # Create old running job
        with freeze_time("2024-12-31 11:00:00"):
            running_job = AnalysisJob(
                id="running_job",
                collection_id=2,
                tool="photostats",
                pipeline_id=None,
                status=JobStatus.RUNNING,
                created_at=datetime.utcnow(),
                started_at=datetime.utcnow()
            )
            queue.enqueue(running_job)

        # Cleanup
        removed = queue.cleanup_old_jobs(max_age_hours=24)

        # Should not remove active jobs
        assert removed == 0
        assert queue.get_job("queued_job") is not None
        assert queue.get_job("running_job") is not None


class TestThreadSafety:
    """Tests for thread-safe concurrent access."""

    def test_concurrent_enqueue(self):
        """Test concurrent enqueueing is thread-safe."""
        queue = JobQueue()
        num_threads = 10
        jobs_per_thread = 10

        def worker(thread_id):
            for i in range(jobs_per_thread):
                job = AnalysisJob(
                    id=f"thread{thread_id}_job{i}",
                    collection_id=thread_id,
                    tool="photostats",
                    pipeline_id=None,
                    status=JobStatus.QUEUED,
                    created_at=datetime.utcnow()
                )
                queue.enqueue(job)

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should have all jobs
        status = queue.get_queue_status()
        assert status['queued_count'] == num_threads * jobs_per_thread

    def test_concurrent_dequeue(self):
        """Test concurrent dequeueing is thread-safe."""
        queue = JobQueue()

        # Enqueue jobs
        for i in range(100):
            job = AnalysisJob(
                id=f"job{i}",
                collection_id=i,
                tool="photostats",
                pipeline_id=None,
                status=JobStatus.QUEUED,
                created_at=datetime.utcnow()
            )
            queue.enqueue(job)

        dequeued_jobs = []
        lock = threading.Lock()

        def worker():
            for _ in range(10):
                job = queue.dequeue()
                if job:
                    with lock:
                        dequeued_jobs.append(job.id)

        threads = []
        for _ in range(10):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Should have dequeued all 100 jobs
        assert len(dequeued_jobs) == 100
        # All job IDs should be unique (no duplicates)
        assert len(set(dequeued_jobs)) == 100


class TestSingletonPattern:
    """Tests for singleton job queue instance."""

    def test_get_job_queue_returns_instance(self):
        """Test get_job_queue returns a JobQueue."""
        queue = get_job_queue()

        assert isinstance(queue, JobQueue)

    def test_get_job_queue_returns_same_instance(self):
        """Test get_job_queue returns the same singleton instance."""
        queue1 = get_job_queue()
        queue2 = get_job_queue()

        assert queue1 is queue2

    def test_init_job_queue_creates_instance(self):
        """Test init_job_queue creates and returns instance."""
        queue = init_job_queue()

        assert isinstance(queue, JobQueue)


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_create_job_id_returns_uuid(self):
        """Test create_job_id returns a valid UUID string."""
        job_id = create_job_id()

        # Should be a string
        assert isinstance(job_id, str)

        # Should be a valid UUID4
        uuid_obj = uuid.UUID(job_id)
        assert uuid_obj.version == 4

    def test_create_job_id_unique(self):
        """Test create_job_id generates unique IDs."""
        ids = [create_job_id() for _ in range(100)]

        # All IDs should be unique
        assert len(set(ids)) == 100
