"""
Unit tests for Tools API endpoints.

Tests tool execution, job management, and queue status endpoints.
"""

import pytest
import tempfile
from uuid import uuid4
from datetime import datetime


class TestRunToolEndpoint:
    """Tests for POST /api/tools/run endpoint."""

    def test_run_tool_photostats_success(self, test_client, sample_collection):
        """Test successful PhotoStats tool execution request."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(
                name="Test Collection",
                type="local",
                location=temp_dir
            )

            response = test_client.post(
                "/api/tools/run",
                json={"collection_id": collection.id, "tool": "photostats"}
            )

            assert response.status_code == 202
            data = response.json()
            assert data["collection_id"] == collection.id
            assert data["tool"] == "photostats"
            assert data["status"] == "queued"
            assert "id" in data

    def test_run_tool_invalid_collection(self, test_client):
        """Test error for non-existent collection."""
        response = test_client.post(
            "/api/tools/run",
            json={"collection_id": 99999, "tool": "photostats"}
        )

        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    def test_run_tool_invalid_tool_type(self, test_client):
        """Test error for invalid tool type."""
        response = test_client.post(
            "/api/tools/run",
            json={"collection_id": 1, "tool": "invalid_tool"}
        )

        assert response.status_code == 422

    def test_run_tool_pipeline_validation_requires_pipeline(self, test_client, sample_collection):
        """Test that pipeline_validation requires pipeline_id."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(
                name="Test Collection",
                type="local",
                location=temp_dir
            )

            response = test_client.post(
                "/api/tools/run",
                json={"collection_id": collection.id, "tool": "pipeline_validation"}
            )

            assert response.status_code == 400
            assert "pipeline_id required" in response.json()["detail"]


class TestListJobsEndpoint:
    """Tests for GET /api/tools/jobs endpoint."""

    def test_list_jobs_empty(self, test_client):
        """Test listing jobs when none exist."""
        response = test_client.get("/api/tools/jobs")

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_jobs_filter_by_status(self, test_client):
        """Test filtering jobs by status."""
        response = test_client.get("/api/tools/jobs", params={"status": "completed"})

        assert response.status_code == 200
        # All returned jobs should have the filtered status
        for job in response.json():
            assert job["status"] == "completed"


class TestGetJobEndpoint:
    """Tests for GET /api/tools/jobs/{job_id} endpoint."""

    def test_get_job_not_found(self, test_client):
        """Test 404 for non-existent job."""
        fake_uuid = str(uuid4())
        response = test_client.get(f"/api/tools/jobs/{fake_uuid}")

        assert response.status_code == 404


class TestCancelJobEndpoint:
    """Tests for POST /api/tools/jobs/{job_id}/cancel endpoint."""

    def test_cancel_nonexistent_job(self, test_client):
        """Test 404 for cancelling non-existent job."""
        fake_uuid = str(uuid4())
        response = test_client.post(f"/api/tools/jobs/{fake_uuid}/cancel")

        assert response.status_code == 404


class TestQueueStatusEndpoint:
    """Tests for GET /api/tools/queue/status endpoint."""

    def test_get_queue_status(self, test_client):
        """Test getting queue status."""
        response = test_client.get("/api/tools/queue/status")

        assert response.status_code == 200
        data = response.json()
        assert "queued_count" in data
        assert "running_count" in data
        assert "completed_count" in data
        assert "failed_count" in data
        assert "cancelled_count" in data


class TestRunAllToolsEndpoint:
    """Tests for POST /api/tools/run-all/{collection_id} endpoint."""

    def test_run_all_tools_success(self, test_client, sample_collection):
        """Test successful run-all tools request queues both tools."""
        with tempfile.TemporaryDirectory() as temp_dir:
            collection = sample_collection(
                name="Test Collection",
                type="local",
                location=temp_dir
            )

            response = test_client.post(f"/api/tools/run-all/{collection.id}")

            assert response.status_code == 202
            data = response.json()
            assert len(data["jobs"]) == 2
            assert data["skipped"] == []
            assert "2 analysis jobs queued" in data["message"]

            # Verify both tools are queued
            tools = [job["tool"] for job in data["jobs"]]
            assert "photostats" in tools
            assert "photo_pairing" in tools

    def test_run_all_tools_inaccessible_collection(self, test_client, sample_collection, test_db_session):
        """Test run-all on inaccessible collection returns 422."""
        # Create collection with non-existent path and mark it as inaccessible
        collection = sample_collection(
            name="Inaccessible",
            type="local",
            location="/nonexistent/path/to/photos"
        )
        # Update the collection to be inaccessible
        collection.is_accessible = False
        test_db_session.commit()

        response = test_client.post(f"/api/tools/run-all/{collection.id}")

        assert response.status_code == 422
        data = response.json()
        assert "Cannot run tools" in data["detail"]["message"]
        assert data["detail"]["collection_id"] == collection.id

    def test_run_all_tools_nonexistent_collection(self, test_client):
        """Test run-all on non-existent collection returns 400."""
        response = test_client.post("/api/tools/run-all/99999")

        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()
