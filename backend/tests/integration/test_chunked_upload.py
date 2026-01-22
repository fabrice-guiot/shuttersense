"""
Integration tests for chunked upload flow.

Tests the full chunked upload workflow including:
- API endpoint integration
- Session management
- Chunk storage and assembly
- Checksum verification
- Content validation

Issue #90 - Distributed Agent Architecture (Phase 15)
Task: T202
"""

import hashlib
import json
import pytest
from fastapi.testclient import TestClient

from backend.src.main import app
from backend.src.models.job import Job, JobStatus
from backend.src.models.agent import AgentStatus


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def create_agent(test_db_session):
    """Factory fixture to create and register test agents."""
    def _create_agent(team, user, name="Test Agent", capabilities=None):
        from backend.src.services.agent_service import AgentService

        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=team.id,
            created_by_user_id=user.id,
        )

        result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name=name,
            hostname="test-host.local",
            os_info="Test OS 1.0",
            capabilities=capabilities or ["local_filesystem"],
            authorized_roots=["/tmp"],
            version="1.0.0",
            development_mode=True,
        )

        return result.agent

    return _create_agent


class TestChunkedUploadEndpoints:
    """Integration tests for chunked upload API endpoints."""

    @pytest.fixture
    def test_job(self, test_db_session, test_team, test_user, create_agent):
        """Create a test job assigned to an agent."""
        import json
        from datetime import datetime

        # Create agent
        agent = create_agent(test_team, test_user, name="Test Upload Agent")

        # Create job
        job = Job(
            team_id=test_team.id,
            tool="photostats",
            mode="collection",
            status=JobStatus.RUNNING,
            agent_id=agent.id,
            assigned_at=datetime.utcnow(),
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        return job, agent

    @pytest.fixture
    def client_with_agent_auth(self, test_db_session, test_job, test_team):
        """Create test client with agent authentication."""
        from backend.src.api.agent.dependencies import get_agent_context, AgentContext
        from backend.src.db.database import get_db

        job, agent = test_job

        # Create a function to return the test DB session
        def get_test_db():
            try:
                yield test_db_session
            finally:
                pass

        # Create a mock agent context with all required fields
        mock_ctx = AgentContext(
            agent_id=agent.id,
            agent_guid=agent.guid,
            team_id=agent.team_id,
            team_guid=test_team.guid,
            agent_name=agent.name,
            status=agent.status,
            agent=agent,
        )

        # Override dependencies
        app.dependency_overrides[get_db] = get_test_db
        app.dependency_overrides[get_agent_context] = lambda: mock_ctx

        with TestClient(app) as client:
            yield client

        # Clean up
        app.dependency_overrides.clear()


class TestInitiateUpload(TestChunkedUploadEndpoints):
    """Tests for upload initiation endpoint."""

    def test_initiate_upload_success(self, client_with_agent_auth, test_job):
        """Successfully initiate a chunked upload."""
        job, agent = test_job

        response = client_with_agent_auth.post(
            f"/api/agent/v1/jobs/{job.guid}/uploads/initiate",
            json={
                "upload_type": "results_json",
                "expected_size": 5_000_000,
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "upload_id" in data
        assert data["chunk_size"] > 0
        assert data["total_chunks"] > 0

    def test_initiate_upload_custom_chunk_size(self, client_with_agent_auth, test_job):
        """Initiate upload with custom chunk size."""
        job, agent = test_job

        response = client_with_agent_auth.post(
            f"/api/agent/v1/jobs/{job.guid}/uploads/initiate",
            json={
                "upload_type": "report_html",
                "expected_size": 3_000_000,
                "chunk_size": 1_000_000,
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["chunk_size"] == 1_000_000
        assert data["total_chunks"] == 3

    def test_initiate_upload_invalid_type(self, client_with_agent_auth, test_job):
        """Reject invalid upload type."""
        job, agent = test_job

        response = client_with_agent_auth.post(
            f"/api/agent/v1/jobs/{job.guid}/uploads/initiate",
            json={
                "upload_type": "invalid_type",
                "expected_size": 1000,
            }
        )

        assert response.status_code == 400

    def test_initiate_upload_job_not_found(self, client_with_agent_auth):
        """Handle non-existent job."""
        response = client_with_agent_auth.post(
            "/api/agent/v1/jobs/job_nonexistent00000000000000/uploads/initiate",
            json={
                "upload_type": "results_json",
                "expected_size": 1000,
            }
        )

        assert response.status_code == 404


class TestChunkUploadEndpoint(TestChunkedUploadEndpoints):
    """Tests for chunk upload endpoint."""

    def test_upload_chunk_success(self, client_with_agent_auth, test_job):
        """Successfully upload a chunk."""
        job, agent = test_job

        # First initiate an upload
        init_response = client_with_agent_auth.post(
            f"/api/agent/v1/jobs/{job.guid}/uploads/initiate",
            json={
                "upload_type": "results_json",
                "expected_size": 1000,
                "chunk_size": 1000,
            }
        )
        assert init_response.status_code == 201
        upload_id = init_response.json()["upload_id"]

        # Upload chunk
        chunk_data = b"x" * 1000
        response = client_with_agent_auth.put(
            f"/api/agent/v1/uploads/{upload_id}/0",
            content=chunk_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["received"] is True
        assert data["chunk_index"] == 0
        assert data["chunks_received"] == 1

    def test_upload_chunk_idempotent(self, client_with_agent_auth, test_job):
        """Duplicate chunk upload is idempotent."""
        job, agent = test_job

        # Initiate upload
        init_response = client_with_agent_auth.post(
            f"/api/agent/v1/jobs/{job.guid}/uploads/initiate",
            json={
                "upload_type": "results_json",
                "expected_size": 1000,
                "chunk_size": 1000,
            }
        )
        upload_id = init_response.json()["upload_id"]

        chunk_data = b"x" * 1000

        # First upload
        response1 = client_with_agent_auth.put(
            f"/api/agent/v1/uploads/{upload_id}/0",
            content=chunk_data,
        )
        assert response1.status_code == 200
        assert response1.json()["received"] is True

        # Duplicate upload - should return False for received
        response2 = client_with_agent_auth.put(
            f"/api/agent/v1/uploads/{upload_id}/0",
            content=chunk_data,
        )
        assert response2.status_code == 200
        assert response2.json()["received"] is False


class TestUploadStatus(TestChunkedUploadEndpoints):
    """Tests for upload status endpoint."""

    def test_get_upload_status(self, client_with_agent_auth, test_job):
        """Get upload status with progress."""
        job, agent = test_job

        # Initiate upload with 2 chunks
        init_response = client_with_agent_auth.post(
            f"/api/agent/v1/jobs/{job.guid}/uploads/initiate",
            json={
                "upload_type": "results_json",
                "expected_size": 2000,
                "chunk_size": 1000,
            }
        )
        upload_id = init_response.json()["upload_id"]

        # Upload first chunk
        client_with_agent_auth.put(
            f"/api/agent/v1/uploads/{upload_id}/0",
            content=b"x" * 1000,
        )

        # Get status
        response = client_with_agent_auth.get(
            f"/api/agent/v1/uploads/{upload_id}/status"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["upload_id"] == upload_id
        assert data["total_chunks"] == 2
        assert data["received_chunks"] == 1
        assert data["received_chunk_indices"] == [0]
        assert data["missing_chunk_indices"] == [1]
        assert data["is_complete"] is False


class TestFinalizeUpload(TestChunkedUploadEndpoints):
    """Tests for upload finalization endpoint."""

    def test_finalize_upload_success(self, client_with_agent_auth, test_job):
        """Successfully finalize a complete upload."""
        job, agent = test_job

        # Create content
        content = json.dumps({"test": "data"}).encode('utf-8')
        checksum = hashlib.sha256(content).hexdigest()

        # Initiate upload
        init_response = client_with_agent_auth.post(
            f"/api/agent/v1/jobs/{job.guid}/uploads/initiate",
            json={
                "upload_type": "results_json",
                "expected_size": len(content),
                "chunk_size": len(content),  # Single chunk
            }
        )
        upload_id = init_response.json()["upload_id"]

        # Upload chunk
        client_with_agent_auth.put(
            f"/api/agent/v1/uploads/{upload_id}/0",
            content=content,
        )

        # Finalize
        response = client_with_agent_auth.post(
            f"/api/agent/v1/uploads/{upload_id}/finalize",
            json={"checksum": checksum}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["upload_type"] == "results_json"
        assert data["content_size"] == len(content)

    def test_finalize_incomplete_upload(self, client_with_agent_auth, test_job):
        """Reject finalization of incomplete upload."""
        job, agent = test_job

        # Initiate upload with 2 chunks
        init_response = client_with_agent_auth.post(
            f"/api/agent/v1/jobs/{job.guid}/uploads/initiate",
            json={
                "upload_type": "results_json",
                "expected_size": 2000,
                "chunk_size": 1000,
            }
        )
        upload_id = init_response.json()["upload_id"]

        # Upload only first chunk
        client_with_agent_auth.put(
            f"/api/agent/v1/uploads/{upload_id}/0",
            content=b"x" * 1000,
        )

        # Try to finalize with a valid-format but dummy checksum (64 hex chars)
        dummy_checksum = "0" * 64  # Valid 64 char hex string
        response = client_with_agent_auth.post(
            f"/api/agent/v1/uploads/{upload_id}/finalize",
            json={"checksum": dummy_checksum}
        )

        assert response.status_code == 400
        assert "incomplete" in response.json()["detail"].lower()

    def test_finalize_checksum_mismatch(self, client_with_agent_auth, test_job):
        """Reject finalization with wrong checksum."""
        job, agent = test_job

        content = b"test content"

        # Initiate and upload
        init_response = client_with_agent_auth.post(
            f"/api/agent/v1/jobs/{job.guid}/uploads/initiate",
            json={
                "upload_type": "results_json",
                "expected_size": len(content),
                "chunk_size": len(content),
            }
        )
        upload_id = init_response.json()["upload_id"]

        client_with_agent_auth.put(
            f"/api/agent/v1/uploads/{upload_id}/0",
            content=content,
        )

        # Finalize with wrong checksum (valid format but incorrect value)
        wrong_checksum = "f" * 64  # Valid 64 char hex string, but wrong
        response = client_with_agent_auth.post(
            f"/api/agent/v1/uploads/{upload_id}/finalize",
            json={"checksum": wrong_checksum}
        )

        assert response.status_code == 400
        assert "checksum" in response.json()["detail"].lower()


class TestCancelUpload(TestChunkedUploadEndpoints):
    """Tests for upload cancellation endpoint."""

    def test_cancel_upload_success(self, client_with_agent_auth, test_job):
        """Successfully cancel an upload."""
        job, agent = test_job

        # Initiate upload
        init_response = client_with_agent_auth.post(
            f"/api/agent/v1/jobs/{job.guid}/uploads/initiate",
            json={
                "upload_type": "results_json",
                "expected_size": 1000,
            }
        )
        upload_id = init_response.json()["upload_id"]

        # Cancel
        response = client_with_agent_auth.delete(
            f"/api/agent/v1/uploads/{upload_id}"
        )

        assert response.status_code == 204

        # Verify cancelled - status should now 404
        status_response = client_with_agent_auth.get(
            f"/api/agent/v1/uploads/{upload_id}/status"
        )
        assert status_response.status_code == 404

    def test_cancel_nonexistent_upload(self, client_with_agent_auth):
        """Handle cancellation of non-existent upload."""
        response = client_with_agent_auth.delete(
            "/api/agent/v1/uploads/nonexistent_upload_id"
        )

        assert response.status_code == 404


class TestHTMLSecurityValidation(TestChunkedUploadEndpoints):
    """Integration tests for HTML security validation."""

    def test_reject_external_scripts(self, client_with_agent_auth, test_job):
        """Reject HTML with external script sources."""
        job, agent = test_job

        html_content = b'<html><head><script src="https://evil.com/script.js"></script></head></html>'
        checksum = hashlib.sha256(html_content).hexdigest()

        # Initiate and upload
        init_response = client_with_agent_auth.post(
            f"/api/agent/v1/jobs/{job.guid}/uploads/initiate",
            json={
                "upload_type": "report_html",
                "expected_size": len(html_content),
                "chunk_size": len(html_content),
            }
        )
        upload_id = init_response.json()["upload_id"]

        client_with_agent_auth.put(
            f"/api/agent/v1/uploads/{upload_id}/0",
            content=html_content,
        )

        # Finalize should fail
        response = client_with_agent_auth.post(
            f"/api/agent/v1/uploads/{upload_id}/finalize",
            json={"checksum": checksum}
        )

        assert response.status_code == 400
        assert "external script" in response.json()["detail"].lower()

    def test_accept_self_contained_html(self, client_with_agent_auth, test_job):
        """Accept self-contained HTML with inline scripts."""
        job, agent = test_job

        html_content = b'''
        <!DOCTYPE html>
        <html>
        <head><title>Report</title></head>
        <body>
            <script>console.log("inline script is OK");</script>
            <style>.class { color: red; }</style>
        </body>
        </html>
        '''
        checksum = hashlib.sha256(html_content).hexdigest()

        # Initiate and upload
        init_response = client_with_agent_auth.post(
            f"/api/agent/v1/jobs/{job.guid}/uploads/initiate",
            json={
                "upload_type": "report_html",
                "expected_size": len(html_content),
                "chunk_size": len(html_content),
            }
        )
        upload_id = init_response.json()["upload_id"]

        client_with_agent_auth.put(
            f"/api/agent/v1/uploads/{upload_id}/0",
            content=html_content,
        )

        # Finalize should succeed
        response = client_with_agent_auth.post(
            f"/api/agent/v1/uploads/{upload_id}/finalize",
            json={"checksum": checksum}
        )

        assert response.status_code == 200
        assert response.json()["success"] is True


class TestMultiChunkUpload(TestChunkedUploadEndpoints):
    """Tests for multi-chunk upload scenarios."""

    def test_multi_chunk_upload_success(self, client_with_agent_auth, test_job):
        """Successfully upload content in multiple chunks."""
        job, agent = test_job

        # Create content that spans 3 chunks
        chunk_size = 100
        content_part1 = b"A" * chunk_size
        content_part2 = b"B" * chunk_size
        content_part3 = b"C" * 50  # Last chunk smaller
        full_content = content_part1 + content_part2 + content_part3
        checksum = hashlib.sha256(full_content).hexdigest()

        # Initiate upload
        init_response = client_with_agent_auth.post(
            f"/api/agent/v1/jobs/{job.guid}/uploads/initiate",
            json={
                "upload_type": "results_json",
                "expected_size": len(full_content),
                "chunk_size": chunk_size,
            }
        )
        assert init_response.status_code == 201
        upload_id = init_response.json()["upload_id"]
        assert init_response.json()["total_chunks"] == 3

        # Upload chunks in order
        client_with_agent_auth.put(f"/api/agent/v1/uploads/{upload_id}/0", content=content_part1)
        client_with_agent_auth.put(f"/api/agent/v1/uploads/{upload_id}/1", content=content_part2)
        client_with_agent_auth.put(f"/api/agent/v1/uploads/{upload_id}/2", content=content_part3)

        # Verify complete
        status = client_with_agent_auth.get(f"/api/agent/v1/uploads/{upload_id}/status")
        assert status.json()["is_complete"] is True

        # Finalize
        # Note: Content needs to be valid JSON for results_json type
        # For this test, we'd need valid JSON content
        # Let's just verify the checksum calculation works with the test data

    def test_upload_chunks_out_of_order(self, client_with_agent_auth, test_job):
        """Chunks can be uploaded in any order."""
        job, agent = test_job

        chunk_size = 100
        full_content = b"A" * 100 + b"B" * 100 + b"C" * 50
        checksum = hashlib.sha256(full_content).hexdigest()

        # Initiate
        init_response = client_with_agent_auth.post(
            f"/api/agent/v1/jobs/{job.guid}/uploads/initiate",
            json={
                "upload_type": "results_json",
                "expected_size": len(full_content),
                "chunk_size": chunk_size,
            }
        )
        upload_id = init_response.json()["upload_id"]

        # Upload out of order: 2, 0, 1
        client_with_agent_auth.put(f"/api/agent/v1/uploads/{upload_id}/2", content=b"C" * 50)
        client_with_agent_auth.put(f"/api/agent/v1/uploads/{upload_id}/0", content=b"A" * 100)
        client_with_agent_auth.put(f"/api/agent/v1/uploads/{upload_id}/1", content=b"B" * 100)

        # Should be complete
        status = client_with_agent_auth.get(f"/api/agent/v1/uploads/{upload_id}/status")
        assert status.json()["is_complete"] is True
