"""
Unit tests for Results API endpoints.

Tests result listing, retrieval, deletion, and report download endpoints.
"""

import pytest
import tempfile
from datetime import datetime

from backend.src.models import AnalysisResult, ResultStatus


@pytest.fixture
def sample_result(test_db_session, sample_collection, test_team):
    """Factory for creating sample AnalysisResult models in the database."""
    def _create(
        collection_id=None,
        tool="photostats",
        status=ResultStatus.COMPLETED,
        results=None,
        report_html=None,
        team_id=None,
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
                team_id=team_id if team_id is not None else test_team.id,
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


# ============================================================================
# NO_CHANGE Report Download Tests (Issue #92 - US3)
# ============================================================================

class TestNoChangeReportDownload:
    """Tests for report download from NO_CHANGE results (Issue #92)."""

    def test_download_report_from_no_change_result(self, test_client, sample_result):
        """
        Test downloading report from NO_CHANGE result.

        When a NO_CHANGE result has download_report_from set, the report
        should be served from the referenced source result.
        """
        # Create source result with report
        source = sample_result(
            report_html="<html><body>Original Report</body></html>",
            input_state_hash="abc123"
        )

        # Create NO_CHANGE result referencing source
        no_change = sample_result(
            status=ResultStatus.NO_CHANGE,
            report_html=None,  # NO_CHANGE results don't have their own report
            no_change_copy=True,
            download_report_from=source.guid,
            input_state_hash="abc123"
        )

        response = test_client.get(f"/api/results/{no_change.guid}/report")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        assert "Original Report" in response.text

    def test_download_report_from_no_change_deleted_source(self, test_client, sample_result, test_db_session):
        """
        Test 404 when NO_CHANGE result's source has been deleted.

        When the referenced source result no longer exists, the report
        download should return 404.
        """
        # Create source result with report
        source = sample_result(
            report_html="<html><body>Original Report</body></html>",
            input_state_hash="abc123"
        )
        source_guid = source.guid

        # Create NO_CHANGE result referencing source
        no_change = sample_result(
            status=ResultStatus.NO_CHANGE,
            report_html=None,
            no_change_copy=True,
            download_report_from=source_guid,
            input_state_hash="abc123"
        )

        # Delete the source result
        test_db_session.delete(source)
        test_db_session.commit()

        response = test_client.get(f"/api/results/{no_change.guid}/report")

        assert response.status_code == 404

    def test_download_report_no_change_without_reference(self, test_client, sample_result):
        """
        Test 404 for NO_CHANGE result without download_report_from reference.

        Legacy NO_CHANGE results might not have the reference set.
        """
        no_change = sample_result(
            status=ResultStatus.NO_CHANGE,
            report_html=None,
            no_change_copy=True,
            download_report_from=None  # No reference
        )

        response = test_client.get(f"/api/results/{no_change.guid}/report")

        assert response.status_code == 404

    def test_result_detail_shows_source_result_exists_true(self, test_client, sample_result):
        """
        Test that result detail includes source_result_exists=true when source exists.
        """
        source = sample_result(
            report_html="<html>Report</html>",
            input_state_hash="abc123"
        )

        no_change = sample_result(
            status=ResultStatus.NO_CHANGE,
            no_change_copy=True,
            download_report_from=source.guid,
            input_state_hash="abc123"
        )

        response = test_client.get(f"/api/results/{no_change.guid}")

        assert response.status_code == 200
        data = response.json()
        assert data["no_change_copy"] == True
        assert data["download_report_from"] == source.guid
        # source_result_exists should be computed
        assert "source_result_exists" in data
        assert data["source_result_exists"] == True

    def test_result_detail_shows_source_result_exists_false(self, test_client, sample_result, test_db_session):
        """
        Test that result detail includes source_result_exists=false when source deleted.
        """
        source = sample_result(
            report_html="<html>Report</html>",
            input_state_hash="abc123"
        )
        source_guid = source.guid

        no_change = sample_result(
            status=ResultStatus.NO_CHANGE,
            no_change_copy=True,
            download_report_from=source_guid,
            input_state_hash="abc123"
        )

        # Delete the source
        test_db_session.delete(source)
        test_db_session.commit()

        response = test_client.get(f"/api/results/{no_change.guid}")

        assert response.status_code == 200
        data = response.json()
        assert data["no_change_copy"] == True
        assert data["source_result_exists"] == False


# ============================================================================
# Results List Filter Tests (Issue #92 - T049)
# ============================================================================

class TestResultsListNoChangeCopyFilter:
    """Tests for no_change_copy filter parameter on GET /api/results (Issue #92)."""

    def test_filter_no_change_copy_true(self, test_client, sample_result):
        """Test filtering to show only NO_CHANGE copies."""
        # Create original result
        original = sample_result(
            report_html="<html>Report</html>",
            no_change_copy=False
        )

        # Create NO_CHANGE copy
        copy = sample_result(
            status=ResultStatus.NO_CHANGE,
            no_change_copy=True,
            download_report_from=original.guid
        )

        response = test_client.get("/api/results", params={"no_change_copy": "true"})

        assert response.status_code == 200
        data = response.json()
        # Should only return copies
        for item in data["items"]:
            assert item["no_change_copy"] == True

    def test_filter_no_change_copy_false(self, test_client, sample_result):
        """Test filtering to show only original results (not copies)."""
        # Create original result
        original = sample_result(
            report_html="<html>Report</html>",
            no_change_copy=False
        )

        # Create NO_CHANGE copy
        sample_result(
            status=ResultStatus.NO_CHANGE,
            no_change_copy=True,
            download_report_from=original.guid
        )

        response = test_client.get("/api/results", params={"no_change_copy": "false"})

        assert response.status_code == 200
        data = response.json()
        # Should only return originals
        for item in data["items"]:
            assert item["no_change_copy"] == False

    def test_filter_no_change_combined_with_tool(self, test_client, sample_result):
        """Test combining no_change_copy filter with tool filter."""
        # Create original photostats result
        original_ps = sample_result(
            tool="photostats",
            report_html="<html>Report</html>",
            no_change_copy=False
        )

        # Create NO_CHANGE copy for photostats
        sample_result(
            tool="photostats",
            status=ResultStatus.NO_CHANGE,
            no_change_copy=True,
            download_report_from=original_ps.guid
        )

        # Create original photo_pairing result
        sample_result(
            tool="photo_pairing",
            report_html="<html>Report</html>",
            no_change_copy=False
        )

        response = test_client.get(
            "/api/results",
            params={"no_change_copy": "false", "tool": "photostats"}
        )

        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["no_change_copy"] == False
            assert item["tool"] == "photostats"

    def test_no_filter_returns_all(self, test_client, sample_result):
        """Test that without filter, both originals and copies are returned."""
        original = sample_result(
            report_html="<html>Report</html>",
            no_change_copy=False
        )

        sample_result(
            status=ResultStatus.NO_CHANGE,
            no_change_copy=True,
            download_report_from=original.guid
        )

        response = test_client.get("/api/results")

        assert response.status_code == 200
        data = response.json()
        # Should return both
        assert data["total"] >= 2

        has_original = any(not item["no_change_copy"] for item in data["items"])
        has_copy = any(item["no_change_copy"] for item in data["items"])
        assert has_original
        assert has_copy


# ============================================================================
# Result Response Fields Tests (Issue #92 - Schema validation)
# ============================================================================

class TestResultResponseFields:
    """Tests for result response schema fields (Issue #92)."""

    def test_result_has_input_state_hash_field(self, test_client, sample_result):
        """Test that result response includes input_state_hash field."""
        result = sample_result(input_state_hash="test_hash_123")

        response = test_client.get(f"/api/results/{result.guid}")

        assert response.status_code == 200
        data = response.json()
        assert "input_state_hash" in data
        assert data["input_state_hash"] == "test_hash_123"

    def test_result_has_no_change_copy_field(self, test_client, sample_result):
        """Test that result response includes no_change_copy field."""
        result = sample_result(no_change_copy=False)

        response = test_client.get(f"/api/results/{result.guid}")

        assert response.status_code == 200
        data = response.json()
        assert "no_change_copy" in data
        assert data["no_change_copy"] == False

    def test_result_has_download_report_from_field(self, test_client, sample_result):
        """Test that result response includes download_report_from field."""
        source = sample_result(report_html="<html>Report</html>")

        result = sample_result(
            status=ResultStatus.NO_CHANGE,
            no_change_copy=True,
            download_report_from=source.guid
        )

        response = test_client.get(f"/api/results/{result.guid}")

        assert response.status_code == 200
        data = response.json()
        assert "download_report_from" in data
        assert data["download_report_from"] == source.guid

    def test_result_list_items_have_no_change_copy_field(self, test_client, sample_result):
        """Test that result list items include no_change_copy field."""
        sample_result(no_change_copy=False)

        response = test_client.get("/api/results")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
        for item in data["items"]:
            assert "no_change_copy" in item
