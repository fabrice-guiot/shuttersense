"""
Unit tests for Results API endpoints.

Tests result listing, retrieval, deletion, and report download endpoints.
"""

import pytest
import tempfile
from datetime import datetime

from backend.src.models import AnalysisResult, ResultStatus


@pytest.fixture
def sample_result(test_db_session, sample_collection):
    """Factory for creating sample AnalysisResult models in the database."""
    def _create(
        collection_id=None,
        tool="photostats",
        status=ResultStatus.COMPLETED,
        results=None,
        report_html=None,
        **kwargs
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            if collection_id is None:
                collection = sample_collection(
                    name=f"Test Collection {datetime.utcnow().timestamp()}",
                    type="local",
                    location=temp_dir
                )
                collection_id = collection.id

            result = AnalysisResult(
                collection_id=collection_id,
                tool=tool,
                status=status,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                duration_seconds=10.5,
                results_json=results or {"total_files": 100},
                report_html=report_html,
                files_scanned=100,
                issues_found=5,
                **kwargs
            )
            test_db_session.add(result)
            test_db_session.commit()
            test_db_session.refresh(result)
            return result
    return _create


class TestListResultsEndpoint:
    """Tests for GET /api/results endpoint."""

    def test_list_results_empty(self, test_client):
        """Test listing results when none exist."""
        response = test_client.get("/api/results")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] == 0

    def test_list_results_with_data(self, test_client, sample_result):
        """Test listing results with data."""
        sample_result()

        response = test_client.get("/api/results")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1

    def test_list_results_pagination(self, test_client, sample_result):
        """Test result pagination."""
        # Create multiple results
        for i in range(5):
            sample_result(tool=f"photostats")

        # Request with limit
        response = test_client.get("/api/results", params={"limit": 2})

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 2
        assert len(data["items"]) <= 2

    def test_list_results_filter_by_tool(self, test_client, sample_result):
        """Test filtering results by tool."""
        sample_result(tool="photostats")
        sample_result(tool="photo_pairing")

        response = test_client.get("/api/results", params={"tool": "photostats"})

        assert response.status_code == 200
        for item in response.json()["items"]:
            assert item["tool"] == "photostats"


class TestGetResultEndpoint:
    """Tests for GET /api/results/{guid} endpoint."""

    def test_get_result_success(self, test_client, sample_result):
        """Test getting result details."""
        result = sample_result()

        response = test_client.get(f"/api/results/{result.guid}")

        assert response.status_code == 200
        data = response.json()
        assert data["guid"] == result.guid
        assert data["tool"] == "photostats"
        assert "results" in data
        assert "id" not in data

    def test_get_result_not_found(self, test_client):
        """Test 404 for non-existent result."""
        response = test_client.get("/api/results/res_01hgw2bbg00000000000000000")

        assert response.status_code == 404


class TestDeleteResultEndpoint:
    """Tests for DELETE /api/results/{guid} endpoint."""

    def test_delete_result_success(self, test_client, sample_result):
        """Test deleting a result."""
        result = sample_result()

        response = test_client.delete(f"/api/results/{result.guid}")

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_guid"] == result.guid

        # Verify deletion
        get_response = test_client.get(f"/api/results/{result.guid}")
        assert get_response.status_code == 404

    def test_delete_result_not_found(self, test_client):
        """Test 404 when deleting non-existent result."""
        response = test_client.delete("/api/results/res_01hgw2bbg00000000000000000")

        assert response.status_code == 404


class TestDownloadReportEndpoint:
    """Tests for GET /api/results/{guid}/report endpoint."""

    def test_download_report_success(self, test_client, sample_result):
        """Test downloading HTML report."""
        result = sample_result(report_html="<html><body>Test Report</body></html>")

        response = test_client.get(f"/api/results/{result.guid}/report")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        assert "Test Report" in response.text

    def test_download_report_not_found(self, test_client, sample_result):
        """Test 404 for result without report."""
        result = sample_result(report_html=None)

        response = test_client.get(f"/api/results/{result.guid}/report")

        assert response.status_code == 404


class TestResultStatsEndpoint:
    """Tests for GET /api/results/stats endpoint."""

    def test_get_stats_empty(self, test_client):
        """Test stats with no results."""
        response = test_client.get("/api/results/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] == 0

    def test_get_stats_with_data(self, test_client, sample_result):
        """Test stats with results."""
        sample_result(status=ResultStatus.COMPLETED)
        sample_result(status=ResultStatus.FAILED)

        response = test_client.get("/api/results/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_results"] >= 2
        assert "by_tool" in data
