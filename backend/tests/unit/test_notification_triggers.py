"""
Notification trigger tests for JobCoordinatorService.

Issue #114 - PWA with Push Notifications (Phase 13 — T056)
Tests that job lifecycle events trigger the correct notifications.
"""

from unittest.mock import patch, MagicMock

import pytest

from backend.src.models import JobStatus, AgentStatus, ResultStatus


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

    @patch("backend.src.services.notification_service.NotificationService")
    @patch("backend.src.config.settings.get_settings")
    def test_fail_job_calls_notify_job_failure(
        self, mock_settings, mock_ns_class,
        coordinator_service, test_db_session, test_team, test_user,
        create_agent, sample_collection,
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

        # Use conftest create_agent (handles system_user_id)
        agent = create_agent(status=AgentStatus.ONLINE)
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

    @patch("backend.src.services.notification_service.NotificationService")
    @patch("backend.src.config.settings.get_settings")
    def test_complete_job_calls_notify_inflection_point(
        self, mock_settings, mock_ns_class,
        coordinator_service, test_db_session, test_team,
        create_agent, sample_collection,
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

        # Use conftest create_agent (handles system_user_id)
        agent = create_agent(status=AgentStatus.ONLINE)
        job.agent_id = agent.id
        test_db_session.commit()

        # Complete the job with results
        from backend.src.services.job_coordinator_service import JobCompletionData
        completion_data = JobCompletionData(
            results={"summary": "test"},
            report_html="<html>test</html>",
            files_scanned=100,
            issues_found=5,
        )
        coordinator_service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        # Inflection point notification should have been called
        mock_ns_instance.notify_inflection_point.assert_called_once()


# ============================================================================
# Test: inventory_import no-change skips notification (Issue #219)
# ============================================================================


class TestInventoryImportNoChangeNotification:
    """Tests for inventory_import no_changes flag suppressing notifications."""

    @patch("backend.src.services.notification_service.NotificationService")
    @patch("backend.src.config.settings.get_settings")
    def test_complete_job_skips_notification_for_inventory_no_changes(
        self, mock_settings, mock_ns_class,
        coordinator_service, test_db_session, test_team,
        create_agent, sample_collection,
    ):
        """complete_job() should skip notify_inflection_point when
        inventory_import reports no_changes=True (Issue #219)."""
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
            tool="inventory_import",
            status=JobStatus.RUNNING,
        )
        test_db_session.add(job)
        test_db_session.commit()

        agent = create_agent(status=AgentStatus.ONLINE)
        job.agent_id = agent.id
        test_db_session.commit()

        from backend.src.services.job_coordinator_service import JobCompletionData
        completion_data = JobCompletionData(
            results={
                "success": True,
                "folders_count": 5,
                "total_files": 100,
                "total_size": 500000,
                "collections_with_file_info": 3,
                "collections_with_deltas": 3,
                "no_changes": True,
            },
            files_scanned=100,
            issues_found=0,
        )
        coordinator_service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        # Notification should NOT have been called
        mock_ns_instance.notify_inflection_point.assert_not_called()

        # Result should have NO_CHANGE status
        from backend.src.models.analysis_result import AnalysisResult
        result = test_db_session.query(AnalysisResult).filter(
            AnalysisResult.team_id == test_team.id,
            AnalysisResult.tool == "inventory_import",
        ).first()
        assert result is not None
        assert result.status == ResultStatus.NO_CHANGE

    @patch("backend.src.services.notification_service.NotificationService")
    @patch("backend.src.config.settings.get_settings")
    def test_complete_job_sends_notification_for_inventory_with_changes(
        self, mock_settings, mock_ns_class,
        coordinator_service, test_db_session, test_team,
        create_agent, sample_collection,
    ):
        """complete_job() should call notify_inflection_point when
        inventory_import reports no_changes=False (Issue #219)."""
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
            tool="inventory_import",
            status=JobStatus.RUNNING,
        )
        test_db_session.add(job)
        test_db_session.commit()

        agent = create_agent(status=AgentStatus.ONLINE)
        job.agent_id = agent.id
        test_db_session.commit()

        from backend.src.services.job_coordinator_service import JobCompletionData
        completion_data = JobCompletionData(
            results={
                "success": True,
                "folders_count": 5,
                "total_files": 120,
                "total_size": 600000,
                "collections_with_file_info": 3,
                "collections_with_deltas": 3,
                "no_changes": False,
            },
            files_scanned=120,
            issues_found=0,
        )
        coordinator_service.complete_job(
            job_guid=job.guid,
            agent_id=agent.id,
            team_id=test_team.id,
            completion_data=completion_data,
        )

        # Notification SHOULD have been called
        mock_ns_instance.notify_inflection_point.assert_called_once()

        # Result should have COMPLETED status (not NO_CHANGE)
        from backend.src.models.analysis_result import AnalysisResult
        result = test_db_session.query(AnalysisResult).filter(
            AnalysisResult.team_id == test_team.id,
            AnalysisResult.tool == "inventory_import",
        ).first()
        assert result is not None
        assert result.status == ResultStatus.COMPLETED
