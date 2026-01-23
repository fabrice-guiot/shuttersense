"""
Unit tests for Analytics API endpoints.

Tests storage metrics endpoint for Issue #92.
"""

import pytest
from datetime import datetime, timezone

from backend.src.models import AnalysisResult, ResultStatus, StorageMetrics


@pytest.fixture
def sample_result_with_report(test_db_session, sample_collection, test_team):
    """Factory for creating sample AnalysisResult models with reports."""
    def _create(
        tool="photostats",
        status=ResultStatus.COMPLETED,
        report_html="<html><body>Test Report</body></html>",
        no_change_copy=False,
        download_report_from=None,
        results_json=None,
        **kwargs
    ):
        collection = sample_collection(
            name=f"Test Collection {datetime.now(timezone.utc).timestamp()}",
            type="local",
            location="/tmp/test"
        )

        # If no_change_copy=True and no download_report_from is provided,
        # we need to create a source result first (due to CHECK constraint)
        effective_download_report_from = download_report_from
        effective_report_html = report_html
        if no_change_copy and not download_report_from:
            # Create a source result to reference
            source = AnalysisResult(
                collection_id=collection.id,
                tool=tool,
                status=ResultStatus.COMPLETED,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                duration_seconds=10.5,
                results_json=results_json or {"total_files": 100, "issues": []},
                report_html="<html><body>Source Report</body></html>",
                files_scanned=100,
                issues_found=5,
                team_id=test_team.id,
                no_change_copy=False,
            )
            test_db_session.add(source)
            test_db_session.flush()
            effective_download_report_from = source.guid
            effective_report_html = None  # NO_CHANGE results must have NULL report_html

        result = AnalysisResult(
            collection_id=collection.id,
            tool=tool,
            status=status,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            duration_seconds=10.5,
            results_json=results_json or {"total_files": 100, "issues": []},
            report_html=effective_report_html if no_change_copy else report_html,
            files_scanned=100,
            issues_found=5,
            team_id=test_team.id,
            no_change_copy=no_change_copy,
            download_report_from=effective_download_report_from,
            **kwargs
        )
        test_db_session.add(result)
        test_db_session.commit()
        test_db_session.refresh(result)
        return result
    return _create


@pytest.fixture
def sample_storage_metrics(test_db_session, test_team):
    """Factory for creating sample StorageMetrics."""
    def _create(**kwargs):
        metrics = StorageMetrics(
            team_id=test_team.id,
            total_reports_generated=kwargs.get("total_reports_generated", 100),
            completed_jobs_purged=kwargs.get("completed_jobs_purged", 10),
            failed_jobs_purged=kwargs.get("failed_jobs_purged", 5),
            completed_results_purged_original=kwargs.get("completed_results_purged_original", 8),
            completed_results_purged_copy=kwargs.get("completed_results_purged_copy", 15),
            estimated_bytes_purged=kwargs.get("estimated_bytes_purged", 1024000)
        )
        test_db_session.add(metrics)
        test_db_session.commit()
        test_db_session.refresh(metrics)
        return metrics
    return _create


# ============================================================================
# GET /api/analytics/storage Tests (Issue #92 - US7)
# ============================================================================

class TestGetStorageMetrics:
    """Tests for GET /api/analytics/storage endpoint."""

    def test_get_storage_metrics_empty(self, test_client):
        """Test getting storage metrics when no data exists."""
        response = test_client.get("/api/analytics/storage")

        assert response.status_code == 200
        data = response.json()

        # All cumulative counters should be 0
        assert data["total_reports_generated"] == 0
        assert data["completed_jobs_purged"] == 0
        assert data["failed_jobs_purged"] == 0
        assert data["completed_results_purged_original"] == 0
        assert data["completed_results_purged_copy"] == 0
        assert data["estimated_bytes_purged"] == 0

        # Real-time counts should be 0
        assert data["total_results_retained"] == 0
        assert data["original_results_retained"] == 0
        assert data["copy_results_retained"] == 0

    def test_get_storage_metrics_with_cumulative_data(self, test_client, sample_storage_metrics):
        """Test that cumulative metrics are returned from StorageMetrics table."""
        sample_storage_metrics(
            total_reports_generated=150,
            completed_jobs_purged=25,
            failed_jobs_purged=10,
            completed_results_purged_original=20,
            completed_results_purged_copy=30,
            estimated_bytes_purged=5242880
        )

        response = test_client.get("/api/analytics/storage")

        assert response.status_code == 200
        data = response.json()

        assert data["total_reports_generated"] == 150
        assert data["completed_jobs_purged"] == 25
        assert data["failed_jobs_purged"] == 10
        assert data["completed_results_purged_original"] == 20
        assert data["completed_results_purged_copy"] == 30
        assert data["estimated_bytes_purged"] == 5242880

    def test_get_storage_metrics_with_results(self, test_client, sample_result_with_report):
        """Test that real-time metrics are computed from current results."""
        # Create 2 original results
        original1 = sample_result_with_report(no_change_copy=False)
        sample_result_with_report(no_change_copy=False)
        # Create 1 copy referencing the first original (avoids auto-creating a source)
        sample_result_with_report(
            status=ResultStatus.NO_CHANGE,
            no_change_copy=True,
            download_report_from=original1.guid,
            report_html=None
        )

        response = test_client.get("/api/analytics/storage")

        assert response.status_code == 200
        data = response.json()

        assert data["total_results_retained"] == 3
        assert data["original_results_retained"] == 2
        assert data["copy_results_retained"] == 1

    def test_get_storage_metrics_deduplication_ratio(self, test_client, sample_result_with_report):
        """Test that deduplication ratio is calculated correctly."""
        # Create 1 original and 2 copies (66.67% deduplication)
        original = sample_result_with_report(no_change_copy=False)
        sample_result_with_report(
            status=ResultStatus.NO_CHANGE,
            no_change_copy=True,
            download_report_from=original.guid,
            report_html=None
        )
        sample_result_with_report(
            status=ResultStatus.NO_CHANGE,
            no_change_copy=True,
            download_report_from=original.guid,
            report_html=None
        )

        response = test_client.get("/api/analytics/storage")

        assert response.status_code == 200
        data = response.json()

        # 2 copies out of 3 total = 66.67%
        assert data["deduplication_ratio"] == pytest.approx(66.67, rel=0.01)

    def test_get_storage_metrics_response_schema(self, test_client):
        """Test that response includes all required fields."""
        response = test_client.get("/api/analytics/storage")

        assert response.status_code == 200
        data = response.json()

        # Cumulative counters
        assert "total_reports_generated" in data
        assert "completed_jobs_purged" in data
        assert "failed_jobs_purged" in data
        assert "completed_results_purged_original" in data
        assert "completed_results_purged_copy" in data
        assert "estimated_bytes_purged" in data

        # Real-time statistics
        assert "total_results_retained" in data
        assert "original_results_retained" in data
        assert "copy_results_retained" in data
        assert "preserved_results_count" in data
        assert "reports_retained_json_bytes" in data
        assert "reports_retained_html_bytes" in data

        # Derived metrics
        assert "deduplication_ratio" in data
        assert "storage_savings_bytes" in data

    def test_get_storage_metrics_bytes_computation(self, test_client, sample_result_with_report):
        """Test that retained bytes are computed from result data."""
        # Create a result with known HTML size
        html_report = "<html><body>Test Report Content</body></html>"
        sample_result_with_report(
            report_html=html_report,
            results_json={"data": "test value"}
        )

        response = test_client.get("/api/analytics/storage")

        assert response.status_code == 200
        data = response.json()

        # Should have non-zero bytes for HTML
        assert data["reports_retained_html_bytes"] > 0
        # Should have non-zero bytes for JSON
        assert data["reports_retained_json_bytes"] > 0

    def test_get_storage_metrics_storage_savings(self, test_client, sample_result_with_report):
        """Test that storage savings are calculated based on copies."""
        # Create original with HTML
        html_report = "<html><body>" + "X" * 1000 + "</body></html>"
        original = sample_result_with_report(
            no_change_copy=False,
            report_html=html_report
        )

        # Create copy (which doesn't store HTML)
        sample_result_with_report(
            status=ResultStatus.NO_CHANGE,
            no_change_copy=True,
            download_report_from=original.guid,
            report_html=None
        )

        response = test_client.get("/api/analytics/storage")

        assert response.status_code == 200
        data = response.json()

        # Storage savings should be positive (copy would have stored same HTML)
        assert data["storage_savings_bytes"] >= 0
