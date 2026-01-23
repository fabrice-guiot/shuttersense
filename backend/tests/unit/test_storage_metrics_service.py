"""
Unit tests for StorageMetricsService.

Tests for storage metrics tracking and querying functionality.
Part of Issue #92: Storage Optimization for Analysis Results (Phase 9).
Task: T064
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from backend.src.services.storage_metrics_service import (
    StorageMetricsService,
    StorageMetricsResponse
)
from backend.src.models.storage_metrics import StorageMetrics
from backend.src.models.analysis_result import AnalysisResult
from backend.src.models import ResultStatus


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock()
    return db


@pytest.fixture
def mock_retention_service():
    """Create a mock retention service."""
    with patch('backend.src.services.storage_metrics_service.RetentionService') as mock:
        service = MagicMock()
        settings = MagicMock()
        settings.preserve_per_collection = 3  # Set as attribute directly, not as MagicMock
        service.get_settings.return_value = settings
        service.get_settings_by_team_id.return_value = settings  # Also mock get_settings_by_team_id
        mock.return_value = service
        yield mock


@pytest.fixture
def service(mock_db):
    """Create a StorageMetricsService instance."""
    return StorageMetricsService(mock_db)


@pytest.fixture
def sample_metrics():
    """Create sample StorageMetrics object."""
    metrics = MagicMock(spec=StorageMetrics)
    metrics.team_id = 1
    metrics.total_reports_generated = 100
    metrics.completed_jobs_purged = 20
    metrics.failed_jobs_purged = 5
    metrics.completed_results_purged_original = 15
    metrics.completed_results_purged_copy = 30
    metrics.estimated_bytes_purged = 1000000
    metrics.updated_at = datetime.now(timezone.utc)
    return metrics


# ============================================================================
# Test: _get_or_create_metrics
# ============================================================================

class TestGetOrCreateMetrics:
    """Tests for _get_or_create_metrics method."""

    def test_returns_existing_metrics(self, service, mock_db, sample_metrics):
        """Should return existing metrics if found."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_metrics

        result = service._get_or_create_metrics(team_id=1)

        assert result == sample_metrics
        mock_db.add.assert_not_called()

    def test_creates_new_metrics_if_not_found(self, service, mock_db):
        """Should create new metrics if none exist for team."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = service._get_or_create_metrics(team_id=1)

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        # Check the created object
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.team_id == 1
        assert added_obj.total_reports_generated == 0


# ============================================================================
# Test: increment_on_completion
# ============================================================================

class TestIncrementOnCompletion:
    """Tests for increment_on_completion method."""

    def test_increments_total_reports_generated(self, service, mock_db, sample_metrics):
        """Should increment total_reports_generated counter."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_metrics
        original_count = sample_metrics.total_reports_generated

        service.increment_on_completion(team_id=1)

        assert sample_metrics.total_reports_generated == original_count + 1

    def test_updates_timestamp(self, service, mock_db, sample_metrics):
        """Should update the updated_at timestamp."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_metrics
        old_timestamp = sample_metrics.updated_at

        service.increment_on_completion(team_id=1)

        assert sample_metrics.updated_at != old_timestamp


# ============================================================================
# Test: increment_on_cleanup
# ============================================================================

class TestIncrementOnCleanup:
    """Tests for increment_on_cleanup method."""

    def test_increments_all_counters(self, service, mock_db, sample_metrics):
        """Should increment all provided counters."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_metrics

        original_completed = sample_metrics.completed_jobs_purged
        original_failed = sample_metrics.failed_jobs_purged
        original_results = sample_metrics.completed_results_purged_original
        original_copy = sample_metrics.completed_results_purged_copy
        original_bytes = sample_metrics.estimated_bytes_purged

        service.increment_on_cleanup(
            team_id=1,
            completed_jobs_deleted=5,
            failed_jobs_deleted=2,
            original_results_deleted=3,
            copy_results_deleted=7,
            bytes_freed=50000
        )

        assert sample_metrics.completed_jobs_purged == original_completed + 5
        assert sample_metrics.failed_jobs_purged == original_failed + 2
        assert sample_metrics.completed_results_purged_original == original_results + 3
        assert sample_metrics.completed_results_purged_copy == original_copy + 7
        assert sample_metrics.estimated_bytes_purged == original_bytes + 50000

    def test_handles_partial_updates(self, service, mock_db, sample_metrics):
        """Should handle partial updates (only some counters provided)."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_metrics

        original_completed = sample_metrics.completed_jobs_purged
        original_failed = sample_metrics.failed_jobs_purged

        service.increment_on_cleanup(
            team_id=1,
            completed_jobs_deleted=3
        )

        assert sample_metrics.completed_jobs_purged == original_completed + 3
        assert sample_metrics.failed_jobs_purged == original_failed  # Unchanged


# ============================================================================
# Test: _count_retained_results
# ============================================================================

class TestCountRetainedResults:
    """Tests for _count_retained_results method."""

    def test_counts_all_result_types(self, service, mock_db):
        """Should count total, original, and copy results."""
        # Set up mock to return different counts for different queries
        query_mock = MagicMock()
        mock_db.query.return_value = query_mock
        filter_mock = MagicMock()
        query_mock.filter.return_value = filter_mock

        # Return counts in order: total, original, copy
        filter_mock.scalar.side_effect = [100, 60, 40]

        total, original, copy = service._count_retained_results(team_id=1)

        assert total == 100
        assert original == 60
        assert copy == 40


# ============================================================================
# Test: _compute_retained_bytes
# ============================================================================

class TestComputeRetainedBytes:
    """Tests for _compute_retained_bytes method."""

    def test_computes_json_and_html_bytes(self, service, mock_db):
        """Should compute bytes for JSON and HTML columns."""
        # Create mock results
        mock_result1 = MagicMock()
        mock_result1.results_json = {"key": "value"}
        mock_result1.report_html = "<html>Report 1</html>"

        mock_result2 = MagicMock()
        mock_result2.results_json = {"data": [1, 2, 3]}
        mock_result2.report_html = "<html>Report 2 with more content</html>"

        mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_result1,
            mock_result2
        ]

        json_bytes, html_bytes = service._compute_retained_bytes(team_id=1)

        assert json_bytes > 0
        assert html_bytes > 0

    def test_handles_null_values(self, service, mock_db):
        """Should handle results with null JSON or HTML."""
        mock_result = MagicMock()
        mock_result.results_json = None
        mock_result.report_html = None

        mock_db.query.return_value.filter.return_value.all.return_value = [mock_result]

        json_bytes, html_bytes = service._compute_retained_bytes(team_id=1)

        assert json_bytes == 0
        assert html_bytes == 0


# ============================================================================
# Test: get_metrics
# ============================================================================

class TestGetMetrics:
    """Tests for get_metrics method."""

    def test_returns_storage_metrics_response(
        self,
        service,
        mock_db,
        sample_metrics,
        mock_retention_service
    ):
        """Should return a StorageMetricsResponse with all metrics."""
        # Set up cumulative metrics
        mock_db.query.return_value.filter.return_value.first.return_value = sample_metrics

        # Set up real-time queries - need to handle multiple query() calls
        query_results = [
            sample_metrics,  # _get_or_create_metrics
            100,  # total count
            60,   # original count
            40,   # copy count
            [],   # distinct pairs for preserved
            [],   # retained bytes results
        ]

        def side_effect_query(model):
            mock = MagicMock()
            mock.filter.return_value = mock
            mock.distinct.return_value = mock

            if hasattr(model, '__name__') and model.__name__ == 'StorageMetrics':
                mock.first.return_value = sample_metrics
            elif hasattr(model, '__name__') and model.__name__ == 'AnalysisResult':
                mock.all.return_value = []

            return mock

        mock_db.query.side_effect = None
        mock_db.query.return_value.filter.return_value.first.return_value = sample_metrics
        mock_db.query.return_value.filter.return_value.scalar.return_value = 50
        mock_db.query.return_value.filter.return_value.distinct.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.all.return_value = []

        result = service.get_metrics(team_id=1)

        assert isinstance(result, StorageMetricsResponse)
        assert result.total_reports_generated == sample_metrics.total_reports_generated
        assert result.completed_jobs_purged == sample_metrics.completed_jobs_purged

    def test_calculates_deduplication_ratio(
        self,
        service,
        mock_db,
        sample_metrics,
        mock_retention_service
    ):
        """Should calculate deduplication ratio correctly."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_metrics
        mock_db.query.return_value.filter.return_value.scalar.return_value = 50
        mock_db.query.return_value.filter.return_value.distinct.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.all.return_value = []

        result = service.get_metrics(team_id=1)

        # Dedup ratio should be calculated from copy / total
        assert isinstance(result.deduplication_ratio, float)
        assert 0 <= result.deduplication_ratio <= 100


# ============================================================================
# Test: StorageMetricsResponse
# ============================================================================

class TestStorageMetricsResponse:
    """Tests for StorageMetricsResponse dataclass."""

    def test_response_has_all_fields(self):
        """Should have all required fields."""
        response = StorageMetricsResponse(
            total_reports_generated=100,
            completed_jobs_purged=20,
            failed_jobs_purged=5,
            completed_results_purged_original=15,
            completed_results_purged_copy=30,
            estimated_bytes_purged=1000000,
            total_results_retained=200,
            original_results_retained=120,
            copy_results_retained=80,
            preserved_results_count=50,
            reports_retained_json_bytes=500000,
            reports_retained_html_bytes=2000000,
            deduplication_ratio=40.0,
            storage_savings_bytes=800000
        )

        assert response.total_reports_generated == 100
        assert response.completed_jobs_purged == 20
        assert response.deduplication_ratio == 40.0
        assert response.storage_savings_bytes == 800000
