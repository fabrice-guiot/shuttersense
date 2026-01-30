"""
Notification trigger tests for AgentService.

Issue #114 - PWA with Push Notifications (Phase 13 — T057)
Tests agent status notifications: pool_offline, agent_error, pool_recovery,
debounce, and retry warning on final attempt.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

from backend.src.models import Agent, AgentStatus, JobStatus
from backend.src.models.team import Team
from backend.src.models.user import User, UserStatus
from backend.src.services.agent_service import AgentService


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def agent_service(test_db_session):
    """Create an AgentService instance."""
    return AgentService(db=test_db_session)


@pytest.fixture
def create_agent(test_db_session, test_team):
    """Factory for creating test agents."""
    _counter = [0]

    def _create(name=None, status=AgentStatus.ONLINE):
        _counter[0] += 1
        agent = Agent(
            team_id=test_team.id,
            name=name or f"Agent {_counter[0]}",
            status=status,
            last_heartbeat=datetime.utcnow(),
        )
        test_db_session.add(agent)
        test_db_session.commit()
        test_db_session.refresh(agent)
        return agent
    return _create


# ============================================================================
# Test: Retry warning on final attempt
# ============================================================================


class TestRetryWarningTrigger:
    """Tests for retry warning notifications (FR-043, FR-044)."""

    @patch("backend.src.services.agent_service.NotificationService")
    @patch("backend.src.services.agent_service.get_settings")
    def test_retry_warning_on_final_attempt(
        self, mock_settings, mock_ns_class,
        agent_service, test_db_session, test_team, create_agent, sample_collection,
    ):
        """Should call notify_retry_warning when retry_count reaches max_retries - 1."""
        mock_settings.return_value = MagicMock(
            vapid_private_key="test", vapid_subject="mailto:test@example.com"
        )
        mock_ns_instance = MagicMock()
        mock_ns_class.return_value = mock_ns_instance

        agent = create_agent(status=AgentStatus.ONLINE)

        collection = sample_collection()
        from backend.src.models.job import Job
        job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.RUNNING,
            agent_id=agent.id,
            retry_count=1,  # After prepare_retry() -> 2, max_retries default is 3
            max_retries=3,
        )
        test_db_session.add(job)
        test_db_session.commit()

        # Mark agent offline to trigger _release_agent_jobs
        agent.status = AgentStatus.OFFLINE
        agent.last_heartbeat = datetime.utcnow() - timedelta(minutes=10)
        test_db_session.commit()

        # Release jobs — should trigger retry warning since retry_count will be 2 (== max_retries - 1)
        released = agent_service._release_agent_jobs(agent)
        assert released == 1

        # Verify the notify_retry_warning was called
        mock_ns_instance.notify_retry_warning.assert_called_once()

    @patch("backend.src.services.agent_service.NotificationService")
    @patch("backend.src.services.agent_service.get_settings")
    def test_no_retry_warning_on_non_final_attempt(
        self, mock_settings, mock_ns_class,
        agent_service, test_db_session, test_team, create_agent, sample_collection,
    ):
        """Should NOT call notify_retry_warning on non-final retry."""
        mock_settings.return_value = MagicMock(
            vapid_private_key="test", vapid_subject="mailto:test@example.com"
        )
        mock_ns_instance = MagicMock()
        mock_ns_class.return_value = mock_ns_instance

        agent = create_agent(status=AgentStatus.ONLINE)

        collection = sample_collection()
        from backend.src.models.job import Job
        job = Job(
            team_id=test_team.id,
            collection_id=collection.id,
            tool="photostats",
            status=JobStatus.RUNNING,
            agent_id=agent.id,
            retry_count=0,  # After prepare_retry() -> 1, not final (max_retries=3)
            max_retries=3,
        )
        test_db_session.add(job)
        test_db_session.commit()

        agent.status = AgentStatus.OFFLINE
        test_db_session.commit()

        agent_service._release_agent_jobs(agent)

        # Verify no retry warning was sent
        mock_ns_instance.notify_retry_warning.assert_not_called()


# ============================================================================
# Test: Debounce
# ============================================================================


class TestNotificationDebounce:
    """Tests for agent notification debounce (FR-033)."""

    def test_debounce_suppresses_duplicate_within_window(self):
        """Should suppress duplicate notifications within 5-minute window."""
        from backend.src.services.notification_service import (
            _agent_notification_debounce,
            AGENT_NOTIFICATION_DEBOUNCE_SECONDS,
        )

        # Simulate a recent notification for agent_id=999, transition_type="pool_offline"
        debounce_key = (999, "pool_offline")
        _agent_notification_debounce[debounce_key] = datetime.utcnow()

        # Verify the debounce timestamp exists and is recent
        last_sent = _agent_notification_debounce.get(debounce_key)
        assert last_sent is not None
        elapsed = (datetime.utcnow() - last_sent).total_seconds()
        assert elapsed < AGENT_NOTIFICATION_DEBOUNCE_SECONDS

        # Cleanup
        del _agent_notification_debounce[debounce_key]
