"""
Notification trigger tests for JobCoordinatorService.

Issue #114 - PWA with Push Notifications (Phase 13 — T056)
Tests that job lifecycle events trigger the correct notifications.
"""

from unittest.mock import patch, MagicMock

import pytest

from backend.src.models import JobStatus, ResultStatus


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_notification_service():
    """Create a mock NotificationService."""
    mock = MagicMock()
    mock.notify_job_failure.return_value = 1
    mock.notify_inflection_point.return_value = 1
    mock.notify_retry_warning.return_value = 1
    return mock


@pytest.fixture
def coordinator_service(test_db_session):
    """Create a JobCoordinatorService instance."""
    from backend.src.services.job_coordinator_service import JobCoordinatorService
    return JobCoordinatorService(db=test_db_session)


# ============================================================================
# Test: fail_job triggers notify_job_failure
# ============================================================================


class TestFailJobNotification:
    """Tests for fail_job() notification trigger (FR-023)."""

    @patch("backend.src.services.job_coordinator_service.NotificationService")
    @patch("backend.src.services.job_coordinator_service.get_settings")
    def test_fail_job_calls_notify_job_failure(
        self, mock_settings, mock_ns_class,
        coordinator_service, test_db_session, test_team, test_user,
        sample_collection,
    ):
        """fail_job() should call notify_job_failure on the notification service."""
        mock_settings.return_value = MagicMock(
            vapid_private_key="test", vapid_subject="mailto:test@example.com"
        )
        mock_ns_instance = MagicMock()
        mock_ns_class.return_value = mock_ns_instance

        # Create a collection and job
        collection = sample_collection()
        from backend.src.models.job import Job
        job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.RUNNING,
        )
        test_db_session.add(job)
        test_db_session.commit()

        # Create agent and assign job
        from backend.src.models import Agent, AgentStatus
        agent = Agent(
            team_id=test_team.id,
            name="Test Agent",
            status=AgentStatus.ONLINE,
        )
        test_db_session.add(agent)
        test_db_session.commit()
        job.agent_id = agent.id
        job.status = JobStatus.RUNNING
        test_db_session.commit()

        # Fail the job
        coordinator_service.fail_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            error_message="Test failure",
        )

        mock_ns_instance.notify_job_failure.assert_called_once()


# ============================================================================
# Test: complete_job triggers notify_inflection_point
# ============================================================================


class TestCompleteJobNotification:
    """Tests for complete_job() notification trigger (FR-026, FR-027)."""

    @patch("backend.src.services.job_coordinator_service.NotificationService")
    @patch("backend.src.services.job_coordinator_service.get_settings")
    def test_complete_job_calls_notify_inflection_point(
        self, mock_settings, mock_ns_class,
        coordinator_service, test_db_session, test_team,
        sample_collection,
    ):
        """complete_job() should call notify_inflection_point for new results."""
        mock_settings.return_value = MagicMock(
            vapid_private_key="test", vapid_subject="mailto:test@example.com"
        )
        mock_ns_instance = MagicMock()
        mock_ns_class.return_value = mock_ns_instance

        collection = sample_collection()
        from backend.src.models.job import Job
        job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.RUNNING,
        )
        test_db_session.add(job)
        test_db_session.commit()

        from backend.src.models import Agent, AgentStatus
        agent = Agent(
            team_id=test_team.id,
            name="Test Agent",
            status=AgentStatus.ONLINE,
        )
        test_db_session.add(agent)
        test_db_session.commit()
        job.agent_id = agent.id
        test_db_session.commit()

        # Complete the job with results
        coordinator_service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            files_scanned=100,
            issues_found=5,
            results_json={"summary": "test"},
            report_html="<html>test</html>",
        )

        # Inflection point notification should have been called
        mock_ns_instance.notify_inflection_point.assert_called_once()
