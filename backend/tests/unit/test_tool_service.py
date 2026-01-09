"""
Unit tests for ToolService.

Tests job management, tool execution, and queue operations.
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock

from sqlalchemy.orm import Session

from backend.src.models import Collection, Pipeline, CollectionType, CollectionState
from backend.src.schemas.tools import ToolType, JobStatus
from backend.src.services.tool_service import ToolService
from backend.src.services.exceptions import ConflictError
from backend.src.utils.job_queue import JobQueue, AnalysisJob, JobStatus as QueueJobStatus


class TestToolServiceJobManagement:
    """Tests for job creation and management."""

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
        pipeline.name = "Test Pipeline"
        pipeline.nodes_json = [{"id": "capture", "type": "capture", "properties": {"sample_filename": "AB3D0001", "filename_regex": "([A-Z0-9]{4})([0-9]{4})", "camera_id_group": "1"}}]
        pipeline.edges_json = []
        return pipeline

    def test_run_tool_creates_job(self, mock_db, mock_collection, job_queue):
        """Test that run_tool creates a new job."""
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
        assert job.collection_id == 1
        assert job.tool == ToolType.PHOTOSTATS
        assert job.status == JobStatus.QUEUED

    def test_run_tool_validates_collection(self, mock_db, job_queue):
        """Test that run_tool validates collection exists."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        service = ToolService(db=mock_db, job_queue=job_queue)
        with pytest.raises(ValueError, match="Collection 999 not found"):
            service.run_tool(collection_id=999, tool=ToolType.PHOTOSTATS)

    def test_run_tool_validates_default_pipeline_for_validation(self, mock_db, mock_collection, job_queue):
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

    def test_run_tool_prevents_duplicate(self, mock_db, mock_collection, job_queue):
        """Test that duplicate tool execution is prevented."""
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

    def test_get_job_returns_job(self, mock_db, mock_collection, job_queue):
        """Test getting job by ID."""
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
        service = ToolService(db=mock_db, job_queue=job_queue)
        result = service.get_job(uuid4())
        assert result is None

    def test_list_jobs_returns_all(self, mock_db, mock_collection, job_queue):
        """Test listing all jobs."""
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
        service.run_tool(collection_id=1, tool=ToolType.PHOTOSTATS)

        jobs = service.list_jobs()
        assert len(jobs) == 1

    def test_list_jobs_filters_by_status(self, mock_db, mock_collection, job_queue):
        """Test filtering jobs by status."""
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
        service.run_tool(collection_id=1, tool=ToolType.PHOTOSTATS)

        queued = service.list_jobs(status=JobStatus.QUEUED)
        running = service.list_jobs(status=JobStatus.RUNNING)

        assert len(queued) == 1
        assert len(running) == 0

    def test_cancel_job_cancels_queued(self, mock_db, mock_collection, job_queue):
        """Test cancelling a queued job."""
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
        result = service.cancel_job(uuid4())
        assert result is None


class TestToolServiceQueueStatus:
    """Tests for queue status."""

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
        collection.name = "Test"
        collection.location = "/test"
        return collection

    def test_get_queue_status(self, mock_db, mock_collection, job_queue):
        """Test getting queue status."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_collection

        service = ToolService(db=mock_db, job_queue=job_queue)
        service.run_tool(collection_id=1, tool=ToolType.PHOTOSTATS)

        status = service.get_queue_status()

        assert status["queued_count"] == 1
        assert status["running_count"] == 0
        assert status["completed_count"] == 0

    def test_queue_status_empty(self, mock_db, job_queue):
        """Test queue status with no jobs."""
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
        job = AnalysisJob(
            id=job_id,
            collection_id=1,
            tool="photostats",
            pipeline_id=None,
            status=QueueJobStatus.QUEUED,
            created_at=datetime.utcnow(),
        )

        response = JobAdapter.to_response(job, position=1)

        assert str(response.id) == job_id
        assert response.collection_id == 1
        assert response.tool == ToolType.PHOTOSTATS
        assert response.status == JobStatus.QUEUED
        assert response.position == 1
