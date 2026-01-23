"""
Integration tests for NO_CHANGE job completion flow.

Issue #92: Storage Optimization for Analysis Results
Task T027d: Integration test for NO_CHANGE detection flow.

Tests the complete NO_CHANGE workflow:
1. Agent claims job with previous_result
2. Agent computes Input State hash
3. Hash matches previous result's hash
4. Agent calls /jobs/{guid}/no-change endpoint
5. Server creates NO_CHANGE result referencing source result
"""

import pytest
import secrets
import hashlib
import hmac
import json
from base64 import b64encode
from datetime import datetime

from backend.src.models.job import Job, JobStatus
from backend.src.models.agent import AgentStatus
from backend.src.models import AnalysisResult
from backend.src.models.analysis_result import ResultStatus


class TestNoChangeFlow:
    """Integration tests for the NO_CHANGE job completion flow."""

    def test_no_change_complete_success(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_running_job_with_previous_result,
    ):
        """Successfully complete a job with NO_CHANGE status."""
        job, signing_secret, previous_result = create_running_job_with_previous_result(
            test_team, test_agent
        )

        # The agent would compute this hash and find it matches previous_result
        input_state_hash = previous_result.input_state_hash

        # Compute valid signature for no-change completion
        signature = compute_no_change_signature(signing_secret, input_state_hash)

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/no-change",
            json={
                "input_state_hash": input_state_hash,
                "source_result_guid": previous_result.guid,
                "signature": signature,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["guid"] == job.guid
        assert data["status"] == "completed"

        # Verify job updated in DB
        test_db_session.refresh(job)
        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None
        assert job.result_id is not None

    def test_no_change_creates_result_with_reference(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_running_job_with_previous_result,
    ):
        """NO_CHANGE creates result referencing source result's report."""
        job, signing_secret, previous_result = create_running_job_with_previous_result(
            test_team, test_agent
        )

        input_state_hash = previous_result.input_state_hash
        signature = compute_no_change_signature(signing_secret, input_state_hash)

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/no-change",
            json={
                "input_state_hash": input_state_hash,
                "source_result_guid": previous_result.guid,
                "signature": signature,
            }
        )

        assert response.status_code == 200

        # Verify new result was created with NO_CHANGE status
        test_db_session.refresh(job)
        new_result = test_db_session.query(AnalysisResult).filter(
            AnalysisResult.id == job.result_id
        ).first()

        assert new_result is not None
        assert new_result.status == ResultStatus.NO_CHANGE
        assert new_result.input_state_hash == input_state_hash

        # Verify it references the source result's report (by GUID)
        assert new_result.download_report_from == previous_result.guid

        # Verify results_json is copied from source
        assert new_result.results_json == previous_result.results_json
        assert new_result.files_scanned == previous_result.files_scanned
        assert new_result.issues_found == previous_result.issues_found

        # Verify NO storage of duplicate report_html
        assert new_result.report_html is None

    def test_no_change_invalid_source_result(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_running_job,
    ):
        """Returns error when source result doesn't exist."""
        job, signing_secret = create_running_job(test_team, test_agent)

        input_state_hash = "a" * 64
        signature = compute_no_change_signature(signing_secret, input_state_hash)

        # Use a properly formatted GUID (26 chars after prefix) that doesn't exist
        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/no-change",
            json={
                "input_state_hash": input_state_hash,
                "source_result_guid": "res_01hgw2bbg0000000000000999",
                "signature": signature,
            }
        )

        # 422 for invalid format, 404 for not found - either is acceptable
        assert response.status_code in (404, 422), f"Expected 404 or 422, got {response.status_code}: {response.json()}"

    def test_no_change_hash_mismatch(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_running_job_with_previous_result,
    ):
        """Returns error when input_state_hash doesn't match source result."""
        job, signing_secret, previous_result = create_running_job_with_previous_result(
            test_team, test_agent
        )

        # Use a different hash than what's stored in previous_result
        wrong_hash = "b" * 64  # Previous result has "a" * 64
        signature = compute_no_change_signature(signing_secret, wrong_hash)

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/no-change",
            json={
                "input_state_hash": wrong_hash,
                "source_result_guid": previous_result.guid,
                "signature": signature,
            }
        )

        assert response.status_code == 400
        assert "hash" in response.json()["detail"].lower() or "match" in response.json()["detail"].lower()

    def test_no_change_wrong_agent(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_user,
        test_agent,
        create_agent,
        create_running_job_with_previous_result,
    ):
        """Cannot complete NO_CHANGE for job assigned to different agent."""
        other_agent = create_agent(test_team, test_user, name="Other Agent")

        # Create job assigned to other_agent (not test_agent)
        job, signing_secret, previous_result = create_running_job_with_previous_result(
            test_team, other_agent
        )

        input_state_hash = previous_result.input_state_hash
        signature = compute_no_change_signature(signing_secret, input_state_hash)

        # agent_client is authenticated as test_agent, not other_agent
        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/no-change",
            json={
                "input_state_hash": input_state_hash,
                "source_result_guid": previous_result.guid,
                "signature": signature,
            }
        )

        assert response.status_code == 400
        assert "not assigned" in response.json()["detail"].lower()

    def test_no_change_invalid_signature(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_running_job_with_previous_result,
    ):
        """Returns error when signature is invalid."""
        job, signing_secret, previous_result = create_running_job_with_previous_result(
            test_team, test_agent
        )

        input_state_hash = previous_result.input_state_hash

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/no-change",
            json={
                "input_state_hash": input_state_hash,
                "source_result_guid": previous_result.guid,
                "signature": "invalid_signature" + "0" * 48,  # 64 chars but invalid
            }
        )

        assert response.status_code == 400
        assert "signature" in response.json()["detail"].lower()

    def test_no_change_with_input_state_json(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_running_job_with_previous_result,
    ):
        """Successfully complete with optional input_state_json for debugging."""
        job, signing_secret, previous_result = create_running_job_with_previous_result(
            test_team, test_agent
        )

        input_state_hash = previous_result.input_state_hash
        signature = compute_no_change_signature(signing_secret, input_state_hash)

        input_state_json = json.dumps({
            "tool": "photostats",
            "file_count": 10,
            "files": [{"path": "test.dng", "size": 1000, "mtime": 1704067200}],
            "configuration": {"photo_extensions": [".dng"]}
        })

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/no-change",
            json={
                "input_state_hash": input_state_hash,
                "source_result_guid": previous_result.guid,
                "signature": signature,
                "input_state_json": input_state_json,
            }
        )

        assert response.status_code == 200

        # Result should be created successfully
        test_db_session.refresh(job)
        assert job.status == JobStatus.COMPLETED


class TestIntermediateCopyCleanup:
    """Tests for intermediate NO_CHANGE copy cleanup (Issue #92 Phase 7)."""

    def test_intermediate_copy_deleted_when_new_no_change_created(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_running_job,
        create_completed_result,
    ):
        """When third NO_CHANGE is created, middle copy is deleted.

        Scenario: Original A -> Copy B -> Copy C
        After creating C, B should be deleted (A and C remain).
        """
        # Create original COMPLETED result (A)
        original_result = create_completed_result(
            test_team, tool="photostats", input_state_hash="a" * 64
        )

        # Create first NO_CHANGE copy (B) referencing A
        first_copy = AnalysisResult(
            team_id=test_team.id,
            tool="photostats",
            status=ResultStatus.NO_CHANGE,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=0.1,
            files_scanned=original_result.files_scanned,
            issues_found=original_result.issues_found,
            results_json=original_result.results_json,
            input_state_hash="a" * 64,
            no_change_copy=True,
            download_report_from=original_result.guid,
        )
        test_db_session.add(first_copy)
        test_db_session.commit()
        test_db_session.refresh(first_copy)
        first_copy_id = first_copy.id

        # Create running job for second NO_CHANGE
        job, signing_secret = create_running_job(test_team, test_agent, tool="photostats")

        input_state_hash = "a" * 64
        signature = compute_no_change_signature(signing_secret, input_state_hash)

        # Complete job with NO_CHANGE referencing original (creates C)
        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/no-change",
            json={
                "input_state_hash": input_state_hash,
                "source_result_guid": original_result.guid,
                "signature": signature,
            }
        )

        assert response.status_code == 200

        # Verify: original (A) should still exist
        assert test_db_session.query(AnalysisResult).filter(
            AnalysisResult.id == original_result.id
        ).first() is not None

        # Verify: first copy (B) should be DELETED
        assert test_db_session.query(AnalysisResult).filter(
            AnalysisResult.id == first_copy_id
        ).first() is None

        # Verify: new result (C) was created
        test_db_session.refresh(job)
        new_result = test_db_session.query(AnalysisResult).filter(
            AnalysisResult.id == job.result_id
        ).first()
        assert new_result is not None
        assert new_result.no_change_copy is True
        assert new_result.download_report_from == original_result.guid

    def test_multiple_intermediate_copies_all_deleted(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_running_job,
        create_completed_result,
    ):
        """When new NO_CHANGE is created, ALL intermediate copies are deleted.

        Scenario: Original A -> Copies B, C, D -> New Copy E
        After creating E, B, C, D should all be deleted.
        """
        # Create original COMPLETED result
        original_result = create_completed_result(
            test_team, tool="photostats", input_state_hash="a" * 64
        )

        # Create multiple NO_CHANGE copies
        copy_ids = []
        for i in range(3):
            copy = AnalysisResult(
                team_id=test_team.id,
                tool="photostats",
                status=ResultStatus.NO_CHANGE,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                duration_seconds=0.1,
                files_scanned=original_result.files_scanned,
                issues_found=original_result.issues_found,
                results_json=original_result.results_json,
                input_state_hash="a" * 64,
                no_change_copy=True,
                download_report_from=original_result.guid,
            )
            test_db_session.add(copy)
            test_db_session.commit()
            test_db_session.refresh(copy)
            copy_ids.append(copy.id)

        # Create running job
        job, signing_secret = create_running_job(test_team, test_agent, tool="photostats")

        input_state_hash = "a" * 64
        signature = compute_no_change_signature(signing_secret, input_state_hash)

        # Complete with NO_CHANGE
        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/no-change",
            json={
                "input_state_hash": input_state_hash,
                "source_result_guid": original_result.guid,
                "signature": signature,
            }
        )

        assert response.status_code == 200

        # All intermediate copies should be deleted
        for copy_id in copy_ids:
            assert test_db_session.query(AnalysisResult).filter(
                AnalysisResult.id == copy_id
            ).first() is None

        # Original should still exist
        assert test_db_session.query(AnalysisResult).filter(
            AnalysisResult.id == original_result.id
        ).first() is not None

    def test_copies_pointing_to_different_source_not_deleted(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_running_job,
        create_completed_result,
    ):
        """Copies pointing to different source result are NOT deleted."""
        # Create two original COMPLETED results
        original_a = create_completed_result(
            test_team, tool="photostats", input_state_hash="a" * 64
        )
        original_b = create_completed_result(
            test_team, tool="photostats", input_state_hash="b" * 64
        )

        # Create copy pointing to original_b
        copy_of_b = AnalysisResult(
            team_id=test_team.id,
            tool="photostats",
            status=ResultStatus.NO_CHANGE,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            duration_seconds=0.1,
            files_scanned=original_b.files_scanned,
            issues_found=original_b.issues_found,
            results_json=original_b.results_json,
            input_state_hash="b" * 64,
            no_change_copy=True,
            download_report_from=original_b.guid,
        )
        test_db_session.add(copy_of_b)
        test_db_session.commit()
        copy_of_b_id = copy_of_b.id

        # Create running job and complete with NO_CHANGE referencing original_a
        job, signing_secret = create_running_job(test_team, test_agent, tool="photostats")

        signature = compute_no_change_signature(signing_secret, "a" * 64)

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/no-change",
            json={
                "input_state_hash": "a" * 64,
                "source_result_guid": original_a.guid,
                "signature": signature,
            }
        )

        assert response.status_code == 200

        # Copy of B should NOT be deleted (different source)
        assert test_db_session.query(AnalysisResult).filter(
            AnalysisResult.id == copy_of_b_id
        ).first() is not None

    def test_storage_metrics_updated_on_copy_cleanup(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_running_job,
        create_completed_result,
    ):
        """StorageMetrics.completed_results_purged_copy is incremented."""
        from backend.src.models.storage_metrics import StorageMetrics

        # Create original COMPLETED result
        original_result = create_completed_result(
            test_team, tool="photostats", input_state_hash="a" * 64
        )

        # Create intermediate copies
        for _ in range(2):
            copy = AnalysisResult(
                team_id=test_team.id,
                tool="photostats",
                status=ResultStatus.NO_CHANGE,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                duration_seconds=0.1,
                files_scanned=original_result.files_scanned,
                issues_found=original_result.issues_found,
                results_json=original_result.results_json,
                input_state_hash="a" * 64,
                no_change_copy=True,
                download_report_from=original_result.guid,
            )
            test_db_session.add(copy)
        test_db_session.commit()

        # Get initial metrics (may not exist)
        initial_metrics = test_db_session.query(StorageMetrics).filter(
            StorageMetrics.team_id == test_team.id
        ).first()
        initial_purged = initial_metrics.completed_results_purged_copy if initial_metrics else 0

        # Create running job and complete with NO_CHANGE
        job, signing_secret = create_running_job(test_team, test_agent, tool="photostats")

        signature = compute_no_change_signature(signing_secret, "a" * 64)

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/no-change",
            json={
                "input_state_hash": "a" * 64,
                "source_result_guid": original_result.guid,
                "signature": signature,
            }
        )

        assert response.status_code == 200

        # Check metrics were updated
        test_db_session.expire_all()
        metrics = test_db_session.query(StorageMetrics).filter(
            StorageMetrics.team_id == test_team.id
        ).first()

        assert metrics is not None
        assert metrics.completed_results_purged_copy == initial_purged + 2


class TestNoChangeSourceResultValidation:
    """Tests for source result validation in NO_CHANGE flow."""

    def test_source_result_can_reference_failed_result(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_running_job,
        create_failed_result,
    ):
        """NO_CHANGE can reference any result status (including FAILED).

        Note: The implementation doesn't enforce COMPLETED-only source results.
        This allows re-using the same hash comparison even if the previous
        execution failed (indicating the inputs are still the same).
        """
        job, signing_secret = create_running_job(test_team, test_agent)

        # Create a FAILED result
        failed_result = create_failed_result(test_team, tool=job.tool)

        input_state_hash = failed_result.input_state_hash
        signature = compute_no_change_signature(signing_secret, input_state_hash)

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/no-change",
            json={
                "input_state_hash": input_state_hash,
                "source_result_guid": failed_result.guid,
                "signature": signature,
            }
        )

        # Should succeed - we allow referencing any previous result
        assert response.status_code == 200

    def test_source_result_must_have_matching_tool(
        self,
        agent_client,
        test_db_session,
        test_team,
        test_agent,
        create_running_job,
        create_completed_result,
    ):
        """Source result must have the same tool as the job."""
        # Create job for photostats
        job, signing_secret = create_running_job(test_team, test_agent, tool="photostats")

        # Create result for different tool
        different_tool_result = create_completed_result(
            test_team,
            tool="photo_pairing",  # Different tool
            input_state_hash="a" * 64
        )

        signature = compute_no_change_signature(signing_secret, different_tool_result.input_state_hash)

        response = agent_client.post(
            f"/api/agent/v1/jobs/{job.guid}/no-change",
            json={
                "input_state_hash": different_tool_result.input_state_hash,
                "source_result_guid": different_tool_result.guid,
                "signature": signature,
            }
        )

        assert response.status_code == 400


# ============================================================================
# Helper Functions
# ============================================================================

def compute_no_change_signature(signing_secret: str, input_state_hash: str) -> str:
    """Compute HMAC-SHA256 signature for NO_CHANGE completion."""
    from base64 import b64decode

    secret_bytes = b64decode(signing_secret)
    data = {"hash": input_state_hash}
    canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
    signature = hmac.new(
        secret_bytes,
        canonical.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature


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
        test_db_session.commit()

        result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name=name,
            hostname="test.local",
            os_info="Linux",
            capabilities=capabilities or ["local_filesystem"],
            version="1.0.0"
        )
        test_db_session.commit()

        service.process_heartbeat(result.agent, status=AgentStatus.ONLINE)
        test_db_session.commit()

        return result.agent

    return _create_agent


@pytest.fixture
def test_agent(test_db_session, test_team, test_user, create_agent):
    """Create a test agent that will be used by agent_client."""
    return create_agent(test_team, test_user)


@pytest.fixture
def create_running_job(test_db_session):
    """Factory fixture to create a running job with signing secret."""
    def _create_running_job(team, agent, tool="photostats"):
        # Generate signing secret
        secret_bytes = secrets.token_bytes(32)
        signing_secret = b64encode(secret_bytes).decode('utf-8')
        secret_hash = hashlib.sha256(secret_bytes).hexdigest()

        job = Job(
            team_id=team.id,
            tool=tool,
            mode="collection",
            status=JobStatus.RUNNING,
            agent_id=agent.id,
            assigned_at=datetime.utcnow(),
            started_at=datetime.utcnow(),
            signing_secret_hash=secret_hash,
            required_capabilities_json=json.dumps([]),
        )
        test_db_session.add(job)
        test_db_session.commit()
        test_db_session.refresh(job)

        return job, signing_secret

    return _create_running_job


@pytest.fixture
def create_completed_result(test_db_session):
    """Factory fixture to create a completed AnalysisResult."""
    def _create_completed_result(team, tool="photostats", input_state_hash=None):
        now = datetime.utcnow()
        result = AnalysisResult(
            team_id=team.id,
            tool=tool,
            status=ResultStatus.COMPLETED,
            started_at=now,
            completed_at=now,
            duration_seconds=1.5,
            files_scanned=100,
            issues_found=5,
            results_json={"total_files": 100, "issues": 5},
            report_html="<html><body>Test Report</body></html>",
            input_state_hash=input_state_hash or ("a" * 64),
        )
        test_db_session.add(result)
        test_db_session.commit()
        test_db_session.refresh(result)
        return result

    return _create_completed_result


@pytest.fixture
def create_failed_result(test_db_session):
    """Factory fixture to create a failed AnalysisResult."""
    def _create_failed_result(team, tool="photostats"):
        now = datetime.utcnow()
        result = AnalysisResult(
            team_id=team.id,
            tool=tool,
            status=ResultStatus.FAILED,
            started_at=now,
            completed_at=now,
            duration_seconds=0.0,
            results_json={},  # Required field
            files_scanned=0,
            issues_found=0,
            error_message="Test failure",
            input_state_hash="a" * 64,
        )
        test_db_session.add(result)
        test_db_session.commit()
        test_db_session.refresh(result)
        return result

    return _create_failed_result


@pytest.fixture
def create_running_job_with_previous_result(
    test_db_session,
    create_running_job,
    create_completed_result,
):
    """Factory to create a running job with a previous completed result."""
    def _create(team, agent, tool="photostats"):
        # First create a completed result (the "previous" result)
        previous_result = create_completed_result(team, tool=tool)

        # Then create a running job
        job, signing_secret = create_running_job(team, agent, tool=tool)

        return job, signing_secret, previous_result

    return _create


@pytest.fixture
def agent_client(
    test_db_session,
    test_session_factory,
    test_team,
    test_user,
    test_websocket_manager,
    test_agent,
):
    """Create a test client authenticated as an online agent."""
    from fastapi.testclient import TestClient
    from backend.src.main import app
    from backend.src.api.agent.dependencies import AgentContext

    agent = test_agent

    agent_ctx = AgentContext(
        agent_id=agent.id,
        agent_guid=agent.guid,
        team_id=test_team.id,
        team_guid=test_team.guid,
        agent_name=agent.name,
        status=AgentStatus.ONLINE,
    )

    def get_test_db():
        try:
            yield test_db_session
        finally:
            pass

    def get_test_agent_context():
        return agent_ctx

    def get_test_online_agent():
        return agent_ctx

    def get_test_websocket_manager():
        return test_websocket_manager

    from backend.src.db.database import get_db
    from backend.src.api.agent.dependencies import get_agent_context, require_online_agent
    from backend.src.utils.websocket import get_connection_manager

    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_agent_context] = get_test_agent_context
    app.dependency_overrides[require_online_agent] = get_test_online_agent
    app.dependency_overrides[get_connection_manager] = get_test_websocket_manager

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
