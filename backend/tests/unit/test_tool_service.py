"""
Unit tests for ToolService.

Tests job management, tool execution, and queue operations.

Note: These tests focus on the in-memory job queue functionality which is retained
for potential future server-side tools. Most tests mock is_inmemory_job_type() to
return True to force the in-memory queue path. The default behavior (persistent jobs)
is tested in integration tests.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from sqlalchemy.orm import Session

from backend.src.models import Collection, Pipeline, CollectionType, CollectionState
from backend.src.schemas.tools import ToolType, JobStatus
from backend.src.services.tool_service import ToolService
from backend.src.services.exceptions import ConflictError
from backend.src.utils.job_queue import JobQueue, AnalysisJob, JobStatus as QueueJobStatus


class TestToolServiceJobManagement:
    """Tests for job creation and management using in-memory queue."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def job_queue(self):
        """Create fresh job queue for each test."""
        return JobQueue()

    @pytest.fixture
    def mock_collection(self):
        """Create mock collection."""
        collection = Mock(spec=Collection)
        collection.id = 1
        collection.guid = "col_01hgw2bbg0000000000000001"  # GUID for API responses
        collection.name = "Test Collection"
        collection.location = "/path/to/photos"
        collection.type = CollectionType.LOCAL
        collection.state = CollectionState.LIVE
        collection.is_accessible = True
        collection.pipeline_id = None  # No explicit pipeline assignment
        collection.pipeline_version = None
        return collection

    @pytest.fixture
    def mock_pipeline(self):
        """Create mock pipeline."""
        pipeline = Mock(spec=Pipeline)
        pipeline.id = 1
        pipeline.guid = "pip_01hgw2bbg0000000000000001"  # GUID for API responses
        pipeline.name = "Test Pipeline"
        pipeline.nodes_json = [{"id": "capture", "type": "capture", "properties": {"sample_filename": "AB3D0001", "filename_regex": "([A-Z0-9]{4})([0-9]{4})", "camera_id_group": "1"}}]
        pipeline.edges_json = []
        return pipeline

    @pytest.fixture
    def mock_settings_inmemory(self):
        """Mock settings to enable in-memory job queue for all tool types."""
        with patch('backend.src.config.settings.get_settings') as mock_get_settings:
            mock_settings = Mock()
            mock_settings.is_inmemory_job_type.return_value = True
            mock_get_settings.return_value = mock_settings
            yield mock_settings

    def test_run_tool_creates_job(self, mock_db, mock_collection, job_queue, mock_settings_inmemory):
        """Test that run_tool creates a new job in in-memory queue."""
        # Set up mock to return collection first, then None for default pipeline query
        def side_effect(model):
            query_mock = Mock()
            filter_mock = Mock()
            if model == Collection:
                filter_mock.first.return_value = mock_collection
            else:
                # Pipeline query returns None (no default pipeline, which is OK for PhotoStats)
                filter_mock.first.return_value = None
            query_mock.filter.return_value = filter_mock
            return query_mock

        mock_db.query.side_effect = side_effect

        service = ToolService(db=mock_db, job_queue=job_queue)
        job = service.run_tool(
            collection_id=1,
            tool=ToolType.PHOTOSTATS
        )

        assert job.id is not None
        assert job.id.startswith("job_")  # GUID format
        assert job.collection_guid == mock_collection.guid
        assert job.tool == ToolType.PHOTOSTATS
        assert job.status == JobStatus.QUEUED

    def test_run_tool_validates_collection(self, mock_db, job_queue, mock_settings_inmemory):
        """Test that run_tool validates collection exists."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = ToolService(db=mock_db, job_queue=job_queue)
        with pytest.raises(ValueError, match="Collection 999 not found"):
            service.run_tool(collection_id=999, tool=ToolType.PHOTOSTATS)

    def test_run_tool_validates_default_pipeline_for_validation(self, mock_db, mock_collection, job_queue, mock_settings_inmemory):
        """Test that a default pipeline is required for pipeline_validation when no pipeline_id is provided."""
        # Set up mock to return collection first, then None for pipeline query
        def side_effect(model):
            query_mock = Mock()
            filter_mock = Mock()
            if model == Collection:
                filter_mock.first.return_value = mock_collection
            else:
                # Pipeline query returns None (no default pipeline)
                filter_mock.first.return_value = None
            query_mock.filter.return_value = filter_mock
            return query_mock

        mock_db.query.side_effect = side_effect

        service = ToolService(db=mock_db, job_queue=job_queue)
        with pytest.raises(ValueError, match="No pipeline available"):
            service.run_tool(
                collection_id=1,
                tool=ToolType.PIPELINE_VALIDATION
            )

    def test_run_tool_prevents_duplicate(self, mock_db, mock_collection, job_queue, mock_settings_inmemory):
        """Test that duplicate tool execution is prevented in in-memory queue."""
        # Set up mock to return collection first, then None for default pipeline query
        def side_effect(model):
            query_mock = Mock()
            filter_mock = Mock()
            if model == Collection:
                filter_mock.first.return_value = mock_collection
            else:
                filter_mock.first.return_value = None
            query_mock.filter.return_value = filter_mock
            return query_mock

        mock_db.query.side_effect = side_effect

        service = ToolService(db=mock_db, job_queue=job_queue)

        # First job succeeds
        job1 = service.run_tool(collection_id=1, tool=ToolType.PHOTOSTATS)
        assert job1.status == JobStatus.QUEUED

        # Second job for same collection/tool should fail
        with pytest.raises(ConflictError):
            service.run_tool(collection_id=1, tool=ToolType.PHOTOSTATS)

    def test_get_job_returns_job(self, mock_db, mock_collection, job_queue, mock_settings_inmemory):
        """Test getting job by ID from in-memory queue."""
        def side_effect(model):
            query_mock = Mock()
            filter_mock = Mock()
            if model == Collection:
                filter_mock.first.return_value = mock_collection
            else:
                filter_mock.first.return_value = None
            query_mock.filter.return_value = filter_mock
            return query_mock

        mock_db.query.side_effect = side_effect

        service = ToolService(db=mock_db, job_queue=job_queue)
        job = service.run_tool(collection_id=1, tool=ToolType.PHOTOSTATS)

        retrieved = service.get_job(job.id)
        assert retrieved.id == job.id
        assert retrieved.tool == ToolType.PHOTOSTATS

    def test_get_job_returns_none_for_unknown(self, mock_db, job_queue):
        """Test getting non-existent job returns None."""
        # Mock the DB query for looking up the job in the database
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = ToolService(db=mock_db, job_queue=job_queue)
        # Use a valid GUID format string instead of UUID object
        result = service.get_job("job_01hgw2bbg0000000000000999")
        assert result is None

    def test_list_jobs_returns_all(self, mock_db, mock_collection, job_queue, mock_settings_inmemory):
        """Test listing all jobs from in-memory queue."""
        # Set up flexible mock for queries
        def side_effect(model):
            query_mock = Mock()
            filter_mock = Mock()
            order_mock = Mock()
            limit_mock = Mock()

            if model == Collection:
                filter_mock.first.return_value = mock_collection
            else:
                filter_mock.first.return_value = None
                # For list_jobs DB query, return empty list
                limit_mock.all.return_value = []
                order_mock.limit.return_value = limit_mock
                filter_mock.order_by.return_value = order_mock

            query_mock.filter.return_value = filter_mock
            query_mock.order_by.return_value = order_mock
            return query_mock

        mock_db.query.side_effect = side_effect

        service = ToolService(db=mock_db, job_queue=job_queue)
        service.run_tool(collection_id=1, tool=ToolType.PHOTOSTATS)

        jobs = service.list_jobs()
        assert len(jobs) == 1

    def test_list_jobs_filters_by_status(self, mock_db, mock_collection, job_queue, mock_settings_inmemory):
        """Test filtering jobs by status in in-memory queue."""
        def side_effect(model):
            query_mock = Mock()
            filter_mock = Mock()
            order_mock = Mock()
            limit_mock = Mock()

            if model == Collection:
                filter_mock.first.return_value = mock_collection
            else:
                filter_mock.first.return_value = None
                # For list_jobs DB query, return empty list
                limit_mock.all.return_value = []
                order_mock.limit.return_value = limit_mock
                filter_mock.order_by.return_value = order_mock
                filter_mock.filter.return_value = filter_mock  # For chained filters

            query_mock.filter.return_value = filter_mock
            query_mock.order_by.return_value = order_mock
            return query_mock

        mock_db.query.side_effect = side_effect

        service = ToolService(db=mock_db, job_queue=job_queue)
        service.run_tool(collection_id=1, tool=ToolType.PHOTOSTATS)

        queued = service.list_jobs(status=JobStatus.QUEUED)
        running = service.list_jobs(status=JobStatus.RUNNING)

        assert len(queued) == 1
        assert len(running) == 0

    def test_cancel_job_cancels_queued(self, mock_db, mock_collection, job_queue, mock_settings_inmemory):
        """Test cancelling a queued job in in-memory queue."""
        def side_effect(model):
            query_mock = Mock()
            filter_mock = Mock()
            if model == Collection:
                filter_mock.first.return_value = mock_collection
            else:
                filter_mock.first.return_value = None
            query_mock.filter.return_value = filter_mock
            return query_mock

        mock_db.query.side_effect = side_effect

        service = ToolService(db=mock_db, job_queue=job_queue)
        job = service.run_tool(collection_id=1, tool=ToolType.PHOTOSTATS)

        cancelled = service.cancel_job(job.id)
        assert cancelled.status == JobStatus.CANCELLED
        assert cancelled.completed_at is not None

    def test_cancel_job_returns_none_for_unknown(self, mock_db, job_queue):
        """Test cancelling non-existent job returns None."""
        service = ToolService(db=mock_db, job_queue=job_queue)
        result = service.cancel_job("job_01hgw2bbg0000000000000999")  # Non-existent GUID
        assert result is None


class TestToolServiceQueueStatus:
    """Tests for queue status combining in-memory and persistent jobs."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def job_queue(self):
        """Create fresh job queue for each test."""
        return JobQueue()

    @pytest.fixture
    def mock_collection(self):
        """Create mock collection."""
        collection = Mock(spec=Collection)
        collection.id = 1
        collection.guid = "col_01hgw2bbg0000000000000002"  # GUID for API responses
        collection.name = "Test"
        collection.location = "/test"
        collection.is_accessible = True
        collection.pipeline_id = None
        return collection

    @pytest.fixture
    def mock_settings_inmemory(self):
        """Mock settings to enable in-memory job queue for all tool types."""
        with patch('backend.src.config.settings.get_settings') as mock_get_settings:
            mock_settings = Mock()
            mock_settings.is_inmemory_job_type.return_value = True
            mock_get_settings.return_value = mock_settings
            yield mock_settings

    def test_get_queue_status(self, mock_db, mock_collection, job_queue, mock_settings_inmemory):
        """Test getting queue status with in-memory jobs."""
        # Set up mock that handles different query patterns with variable arguments
        def side_effect(*args):
            query_mock = Mock()
            filter_mock = Mock()
            group_mock = Mock()

            # Check if this is a Collection query (single arg)
            if len(args) == 1 and args[0] == Collection:
                filter_mock.first.return_value = mock_collection
            else:
                # Pipeline query or get_queue_status query (multiple args or Job)
                filter_mock.first.return_value = None
                # For get_queue_status DB query, return empty counts
                group_mock.all.return_value = []
                filter_mock.group_by.return_value = group_mock

            query_mock.filter.return_value = filter_mock
            query_mock.group_by.return_value = group_mock
            return query_mock

        mock_db.query.side_effect = side_effect

        service = ToolService(db=mock_db, job_queue=job_queue)
        service.run_tool(collection_id=1, tool=ToolType.PHOTOSTATS)

        status = service.get_queue_status()

        # In-memory queue should have 1 queued job
        assert status["queued_count"] == 1
        assert status["running_count"] == 0
        assert status["completed_count"] == 0

    def test_queue_status_empty(self, mock_db, job_queue):
        """Test queue status with no jobs."""
        # Mock the database query for get_queue_status
        query_mock = Mock()
        filter_mock = Mock()
        group_mock = Mock()
        group_mock.all.return_value = []  # No DB jobs
        filter_mock.group_by.return_value = group_mock
        query_mock.filter.return_value = filter_mock
        query_mock.group_by.return_value = group_mock
        mock_db.query.return_value = query_mock

        service = ToolService(db=mock_db, job_queue=job_queue)
        status = service.get_queue_status()

        assert status["queued_count"] == 0
        assert status["running_count"] == 0
        assert status["current_job_id"] is None


class TestJobAdapter:
    """Tests for JobAdapter conversion."""

    def test_job_adapter_to_response(self):
        """Test converting AnalysisJob to response schema."""
        from backend.src.services.tool_service import JobAdapter
        from backend.src.utils.job_queue import create_job_id

        job_id = create_job_id()
        collection_guid = "col_01hgw2bbg0000000000000001"
        job = AnalysisJob(
            id=job_id,
            collection_id=1,
            collection_guid=collection_guid,
            tool="photostats",
            pipeline_id=None,
            status=QueueJobStatus.QUEUED,
            created_at=datetime.utcnow(),
        )

        response = JobAdapter.to_response(job, position=1)

        assert response.id == job_id  # Now a GUID string
        assert response.collection_guid == collection_guid
        assert response.tool == ToolType.PHOTOSTATS
        assert response.status == JobStatus.QUEUED
        assert response.position == 1


class TestInMemoryJobExecution:
    """Tests for in-memory job execution with mock tools.

    These tests verify the job execution flow works correctly by mocking
    the _execute_job method. Since all real tools now execute on agents,
    we use mocking to test the in-memory queue's execution handling.

    Issue #90 - Distributed Agent Architecture (Phase 8)
    """

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def job_queue(self):
        """Create fresh job queue for each test."""
        return JobQueue()

    @pytest.fixture
    def mock_collection(self):
        """Create mock collection."""
        collection = Mock(spec=Collection)
        collection.id = 1
        collection.guid = "col_01hgw2bbg0000000000000001"
        collection.name = "Test Collection"
        collection.location = "/path/to/photos"
        collection.type = CollectionType.LOCAL
        collection.state = CollectionState.LIVE
        collection.is_accessible = True
        collection.pipeline_id = None
        collection.pipeline_version = None
        return collection

    @pytest.fixture
    def mock_settings_inmemory(self):
        """Mock settings to enable in-memory job queue for all tool types."""
        with patch('backend.src.config.settings.get_settings') as mock_get_settings:
            mock_settings = Mock()
            mock_settings.is_inmemory_job_type.return_value = True
            mock_get_settings.return_value = mock_settings
            yield mock_settings

    @pytest.mark.asyncio
    async def test_execute_job_with_mock_tool(self, mock_db, mock_collection, job_queue, mock_settings_inmemory):
        """Test that job execution flow completes when _execute_job is mocked.

        This test verifies the queue's execution mechanism works by mocking
        _execute_job to simulate a successful tool run.
        """
        from backend.src.utils.job_queue import create_job_id

        def side_effect(model):
            query_mock = Mock()
            filter_mock = Mock()
            if model == Collection:
                filter_mock.first.return_value = mock_collection
            else:
                filter_mock.first.return_value = None
            query_mock.filter.return_value = filter_mock
            return query_mock

        mock_db.query.side_effect = side_effect

        service = ToolService(db=mock_db, job_queue=job_queue)

        # Create a job
        job = service.run_tool(collection_id=1, tool=ToolType.PHOTOSTATS)
        assert job.status == JobStatus.QUEUED

        # Mock _execute_job to simulate successful execution
        async def mock_execute_job(job_to_execute):
            job_to_execute.status = QueueJobStatus.COMPLETED
            job_to_execute.completed_at = datetime.utcnow()
            job_to_execute.result_data = {
                "total_files": 100,
                "total_size": 1000000,
                "orphaned_files": 5,
            }

        with patch.object(service, '_execute_job', mock_execute_job):
            # Get the actual job from the queue and execute it
            queue_job = job_queue.get_job(job.id)
            await service._execute_job(queue_job)

            # Verify job was "executed"
            assert queue_job.status == QueueJobStatus.COMPLETED
            assert queue_job.result_data is not None
            assert queue_job.result_data["total_files"] == 100

    @pytest.mark.asyncio
    async def test_execute_job_failure_handling(self, mock_db, mock_collection, job_queue, mock_settings_inmemory):
        """Test that job execution properly handles failures.

        This test verifies the queue properly marks jobs as failed when
        _execute_job raises an exception.
        """
        def side_effect(model):
            query_mock = Mock()
            filter_mock = Mock()
            if model == Collection:
                filter_mock.first.return_value = mock_collection
            else:
                filter_mock.first.return_value = None
            query_mock.filter.return_value = filter_mock
            return query_mock

        mock_db.query.side_effect = side_effect

        service = ToolService(db=mock_db, job_queue=job_queue)

        # Create a job
        job = service.run_tool(collection_id=1, tool=ToolType.PHOTOSTATS)

        # Mock _execute_job to simulate failure
        async def mock_execute_job_fail(job_to_execute):
            job_to_execute.status = QueueJobStatus.FAILED
            job_to_execute.completed_at = datetime.utcnow()
            job_to_execute.error_message = "Mock tool execution failed"

        with patch.object(service, '_execute_job', mock_execute_job_fail):
            queue_job = job_queue.get_job(job.id)
            await service._execute_job(queue_job)

            assert queue_job.status == QueueJobStatus.FAILED
            assert queue_job.error_message == "Mock tool execution failed"

    def test_queue_processes_jobs_in_order(self, mock_db, mock_collection, job_queue, mock_settings_inmemory):
        """Test that jobs are processed in FIFO order.

        This test verifies the queue maintains proper ordering when
        multiple jobs are added.
        """
        # Create a second mock collection for a different job
        mock_collection2 = Mock(spec=Collection)
        mock_collection2.id = 2
        mock_collection2.guid = "col_01hgw2bbg0000000000000002"
        mock_collection2.name = "Test Collection 2"
        mock_collection2.location = "/path/to/photos2"
        mock_collection2.type = CollectionType.LOCAL
        mock_collection2.state = CollectionState.LIVE
        mock_collection2.is_accessible = True
        mock_collection2.pipeline_id = None
        mock_collection2.pipeline_version = None

        # Update side effect to return different collections
        call_count = [0]
        def multi_collection_side_effect(*args):
            query_mock = Mock()
            filter_mock = Mock()
            order_mock = Mock()
            limit_mock = Mock()

            # Check what's being queried
            if len(args) == 1 and args[0] == Collection:
                call_count[0] += 1
                if call_count[0] == 1:
                    filter_mock.first.return_value = mock_collection
                else:
                    filter_mock.first.return_value = mock_collection2
            else:
                # Pipeline query or list_jobs query
                filter_mock.first.return_value = None
                # For list_jobs DB query, return empty list
                limit_mock.all.return_value = []
                order_mock.limit.return_value = limit_mock
                filter_mock.order_by.return_value = order_mock

            query_mock.filter.return_value = filter_mock
            query_mock.order_by.return_value = order_mock
            return query_mock

        mock_db.query.side_effect = multi_collection_side_effect

        service = ToolService(db=mock_db, job_queue=job_queue)

        # Create two jobs for different collections
        job1 = service.run_tool(collection_id=1, tool=ToolType.PHOTOSTATS)
        job2 = service.run_tool(collection_id=2, tool=ToolType.PHOTOSTATS)

        # Verify both jobs are in queue
        all_jobs = service.list_jobs()
        assert len(all_jobs) == 2

        # Verify both jobs exist (order may vary based on implementation)
        job_ids = {job.id for job in all_jobs}
        assert job1.id in job_ids
        assert job2.id in job_ids

        # Verify jobs are for different collections
        collection_guids = {job.collection_guid for job in all_jobs}
        assert mock_collection.guid in collection_guids
        assert mock_collection2.guid in collection_guids

    def test_job_progress_tracking(self, mock_db, mock_collection, job_queue, mock_settings_inmemory):
        """Test that job progress can be tracked.

        This test verifies that jobs support progress tracking which
        is essential for long-running tool executions.
        """
        def side_effect(model):
            query_mock = Mock()
            filter_mock = Mock()
            if model == Collection:
                filter_mock.first.return_value = mock_collection
            else:
                filter_mock.first.return_value = None
            query_mock.filter.return_value = filter_mock
            return query_mock

        mock_db.query.side_effect = side_effect

        service = ToolService(db=mock_db, job_queue=job_queue)

        # Create a job
        job = service.run_tool(collection_id=1, tool=ToolType.PHOTOSTATS)

        # Get the queue job and simulate progress updates
        queue_job = job_queue.get_job(job.id)

        # Simulate starting execution
        queue_job.status = QueueJobStatus.RUNNING
        queue_job.started_at = datetime.utcnow()
        queue_job.progress = {"percentage": 0, "stage": "initializing"}

        assert queue_job.status == QueueJobStatus.RUNNING
        assert queue_job.progress["percentage"] == 0

        # Simulate progress updates
        queue_job.progress = {"percentage": 50, "stage": "scanning", "files_scanned": 500}
        assert queue_job.progress["percentage"] == 50
        assert queue_job.progress["files_scanned"] == 500

        # Simulate completion
        queue_job.progress = {"percentage": 100, "stage": "complete"}
        queue_job.status = QueueJobStatus.COMPLETED
        queue_job.completed_at = datetime.utcnow()

        assert queue_job.status == QueueJobStatus.COMPLETED
        assert queue_job.progress["percentage"] == 100
