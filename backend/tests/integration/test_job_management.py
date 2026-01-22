"""
Integration tests for job management endpoints.

Tests:
- GET /api/tools/jobs - Job listing with pagination and filters
- POST /api/tools/jobs/{job_id}/cancel - Job cancellation
- POST /api/tools/jobs/{job_id}/retry - Job retry

Issue #90 - Distributed Agent Architecture (Phase 10)
Task: T153
"""

import json
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from backend.src.models.job import Job, JobStatus
from backend.src.main import app


class TestJobListPagination:
    """Integration tests for GET /api/tools/jobs with pagination."""

    def test_list_jobs_default_pagination(
        self,
        test_client,
        test_db_session,
        test_team,
        sample_collection,
    ):
        """Test listing jobs with default pagination (limit=50, offset=0)."""
        # Create test collection
        collection = sample_collection()

        # Create 5 test jobs
        for i in range(5):
            job = Job(
                team_id=test_team.id,
                collection_id=collection.id,
                tool="photostats",
                status=JobStatus.PENDING,
                required_capabilities_json=json.dumps([]),
            )
            test_db_session.add(job)
        test_db_session.commit()

        response = test_client.get("/api/tools/jobs")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["total"] == 5
        assert data["limit"] == 50
        assert data["offset"] == 0
        assert len(data["items"]) == 5

    def test_list_jobs_with_limit(
        self,
        test_client,
        test_db_session,
        test_team,
        sample_collection,
    ):
        """Test listing jobs with custom limit."""
        collection = sample_collection()

        # Create 10 test jobs
        for i in range(10):
            job = Job(
                team_id=test_team.id,
                collection_id=collection.id,
                tool="photostats",
                status=JobStatus.PENDING,
                required_capabilities_json=json.dumps([]),
            )
            test_db_session.add(job)
        test_db_session.commit()

        response = test_client.get("/api/tools/jobs", params={"limit": 3})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert data["limit"] == 3
        assert len(data["items"]) == 3

    def test_list_jobs_with_offset(
        self,
        test_client,
        test_db_session,
        test_team,
        sample_collection,
    ):
        """Test listing jobs with offset for pagination."""
        collection = sample_collection()

        # Create 5 test jobs
        for i in range(5):
            job = Job(
                team_id=test_team.id,
                collection_id=collection.id,
                tool="photostats",
                status=JobStatus.PENDING,
                required_capabilities_json=json.dumps([]),
            )
            test_db_session.add(job)
        test_db_session.commit()

        response = test_client.get("/api/tools/jobs", params={"limit": 2, "offset": 2})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert data["offset"] == 2
        assert len(data["items"]) == 2

    def test_list_jobs_empty_page(
        self,
        test_client,
        test_db_session,
        test_team,
        sample_collection,
    ):
        """Test listing jobs with offset beyond available items returns empty."""
        collection = sample_collection()

        # Create 3 test jobs
        for i in range(3):
            job = Job(
                team_id=test_team.id,
                collection_id=collection.id,
                tool="photostats",
                status=JobStatus.PENDING,
                required_capabilities_json=json.dumps([]),
            )
            test_db_session.add(job)
        test_db_session.commit()

        response = test_client.get("/api/tools/jobs", params={"offset": 10})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["items"]) == 0


class TestJobListFilters:
    """Integration tests for GET /api/tools/jobs with status filters."""

    def test_list_jobs_filter_by_single_status(
        self,
        test_client,
        test_db_session,
        test_team,
        sample_collection,
    ):
        """Test filtering jobs by a single status."""
        collection = sample_collection()

        # Create jobs with different statuses
        pending_job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.PENDING,
            required_capabilities_json=json.dumps([]),
        )
        completed_job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.COMPLETED,
            completed_at=datetime.utcnow(),
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add_all([pending_job, completed_job])
        test_db_session.commit()

        response = test_client.get("/api/tools/jobs", params={"status": "completed"})

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["status"] == "completed"

    def test_list_jobs_filter_by_multiple_statuses(
        self,
        test_client,
        test_db_session,
        test_team,
        sample_collection,
    ):
        """Test filtering jobs by multiple statuses (e.g., queued+running for Active tab)."""
        collection = sample_collection()

        # Create jobs with different statuses
        pending_job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.PENDING,
            required_capabilities_json=json.dumps([]),
        )
        running_job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.RUNNING,
            started_at=datetime.utcnow(),
            required_capabilities_json=json.dumps([]),
        )
        completed_job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.COMPLETED,
            completed_at=datetime.utcnow(),
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add_all([pending_job, running_job, completed_job])
        test_db_session.commit()

        # Filter by both queued and running (Active tab scenario)
        response = test_client.get(
            "/api/tools/jobs",
            params={"status": ["queued", "running"]}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        statuses = {item["status"] for item in data["items"]}
        assert statuses == {"queued", "running"}


class TestJobCancel:
    """Integration tests for POST /api/tools/jobs/{job_id}/cancel."""

    def test_cancel_pending_job(
        self,
        test_client,
        test_db_session,
        test_team,
        sample_collection,
    ):
        """Test cancelling a pending job."""
        collection = sample_collection()

        job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.PENDING,
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        response = test_client.post(f"/api/tools/jobs/{job.guid}/cancel")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

        # Verify in DB
        test_db_session.refresh(job)
        assert job.status == JobStatus.CANCELLED

    def test_cancel_completed_job_fails(
        self,
        test_client,
        test_db_session,
        test_team,
        sample_collection,
    ):
        """Test that cancelling a completed job returns 400."""
        collection = sample_collection()

        job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.COMPLETED,
            completed_at=datetime.utcnow(),
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        response = test_client.post(f"/api/tools/jobs/{job.guid}/cancel")

        assert response.status_code == 400
        assert "Cannot cancel" in response.json()["detail"]

    def test_cancel_nonexistent_job(
        self,
        test_client,
    ):
        """Test cancelling a non-existent job returns 404."""
        response = test_client.post("/api/tools/jobs/job_01hgw2bbg0000000000000999/cancel")

        assert response.status_code == 404


class TestJobRetry:
    """Integration tests for POST /api/tools/jobs/{job_id}/retry."""

    def test_retry_failed_job(
        self,
        test_client,
        test_db_session,
        test_team,
        sample_collection,
    ):
        """Test retrying a failed job creates a new pending job."""
        collection = sample_collection()

        failed_job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.FAILED,
            completed_at=datetime.utcnow(),
            error_message="Test error",
            retry_count=0,
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(failed_job)
        test_db_session.commit()
        test_db_session.refresh(failed_job)

        response = test_client.post(f"/api/tools/jobs/{failed_job.guid}/retry")

        assert response.status_code == 201  # Created
        data = response.json()
        assert data["status"] == "queued"  # PENDING maps to queued
        assert data["id"] != failed_job.guid  # New job created

    def test_retry_completed_job_fails(
        self,
        test_client,
        test_db_session,
        test_team,
        sample_collection,
    ):
        """Test that retrying a completed job returns 400."""
        collection = sample_collection()

        job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.COMPLETED,
            completed_at=datetime.utcnow(),
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        response = test_client.post(f"/api/tools/jobs/{job.guid}/retry")

        assert response.status_code == 400
        assert "Cannot retry" in response.json()["detail"]

    def test_retry_nonexistent_job(
        self,
        test_client,
    ):
        """Test retrying a non-existent job returns 404."""
        response = test_client.post("/api/tools/jobs/job_01hgw2bbg0000000000000999/retry")

        assert response.status_code == 404
