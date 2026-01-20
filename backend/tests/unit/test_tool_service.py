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
