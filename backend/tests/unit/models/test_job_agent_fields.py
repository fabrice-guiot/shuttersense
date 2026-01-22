"""
Unit tests for Job model agent routing fields.

Tests new fields, status transitions, and job lifecycle methods.
"""

import pytest
from datetime import datetime, timedelta

from backend.src.models.job import Job, JobStatus


class TestJobStatus:
    """Tests for JobStatus enum."""

    def test_all_status_values(self):
        """Test that all expected status values exist."""
        assert JobStatus.SCHEDULED.value == "scheduled"
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.ASSIGNED.value == "assigned"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELLED.value == "cancelled"

    def test_status_is_string_enum(self):
        """Test that JobStatus is a string enum."""
        assert isinstance(JobStatus.PENDING.value, str)


class TestJobModel:
    """Tests for Job model."""

    def test_guid_prefix(self):
        """Test that Job has correct GUID prefix."""
        assert Job.GUID_PREFIX == "job"

    def test_tablename(self):
        """Test that Job has correct table name."""
        assert Job.__tablename__ == "jobs"

    def test_default_status(self):
        """Test that default status is PENDING when explicitly set."""
        job = Job(tool="photostats", status=JobStatus.PENDING)
        assert job.status == JobStatus.PENDING

    def test_default_priority(self):
        """Test that priority can be set to 0."""
        job = Job(tool="photostats", priority=0)
        assert job.priority == 0

    def test_default_retry_count(self):
        """Test that retry_count can be set to 0."""
        job = Job(tool="photostats", retry_count=0)
        assert job.retry_count == 0

    def test_default_max_retries(self):
        """Test that max_retries can be set to 3."""
        job = Job(tool="photostats", max_retries=3)
        assert job.max_retries == 3


class TestJobRequiredCapabilities:
    """Tests for Job required_capabilities property."""

    def test_required_capabilities_getter_with_list(self):
        """Test required_capabilities getter when json is a list."""
        job = Job(tool="photostats")
        job.required_capabilities_json = ["tool:photostats:1.0.0", "local_filesystem"]
        assert job.required_capabilities == ["tool:photostats:1.0.0", "local_filesystem"]

    def test_required_capabilities_getter_with_none(self):
        """Test required_capabilities getter when json is None."""
        job = Job(tool="photostats")
        job.required_capabilities_json = None
        assert job.required_capabilities == []

    def test_required_capabilities_setter(self):
        """Test required_capabilities setter."""
        job = Job(tool="photostats")
        job.required_capabilities = ["tool:photostats:1.0.0"]
        # Use property getter to verify - agnostic to internal JSON serialization
        assert job.required_capabilities == ["tool:photostats:1.0.0"]


class TestJobProgress:
    """Tests for Job progress property."""

    def test_progress_getter_with_dict(self):
        """Test progress getter when json is a dict."""
        job = Job(tool="photostats")
        job.progress_json = {"stage": "scanning", "percentage": 45}
        assert job.progress == {"stage": "scanning", "percentage": 45}

    def test_progress_getter_with_none(self):
        """Test progress getter when json is None."""
        job = Job(tool="photostats")
        job.progress_json = None
        assert job.progress is None

    def test_progress_setter(self):
        """Test progress setter."""
        job = Job(tool="photostats")
        job.progress = {"stage": "analyzing", "percentage": 75}
        # Use property getter to verify - agnostic to internal JSON serialization
        assert job.progress == {"stage": "analyzing", "percentage": 75}

    def test_progress_setter_with_none(self):
        """Test progress setter with None."""
        job = Job(tool="photostats")
        job.progress_json = {"stage": "scanning"}
        job.progress = None
        assert job.progress_json is None


class TestJobClaimability:
    """Tests for is_claimable property."""

    def test_is_claimable_when_pending(self):
        """Test is_claimable returns True when status is PENDING."""
        job = Job(tool="photostats", status=JobStatus.PENDING)
        assert job.is_claimable is True

    def test_is_claimable_when_scheduled_and_due(self):
        """Test is_claimable returns True when SCHEDULED and due."""
        job = Job(
            tool="photostats",
            status=JobStatus.SCHEDULED,
            scheduled_for=datetime.utcnow() - timedelta(minutes=5)
        )
        assert job.is_claimable is True

    def test_is_claimable_when_scheduled_and_not_due(self):
        """Test is_claimable returns False when SCHEDULED and not due."""
        job = Job(
            tool="photostats",
            status=JobStatus.SCHEDULED,
            scheduled_for=datetime.utcnow() + timedelta(hours=1)
        )
        assert job.is_claimable is False

    def test_is_claimable_when_running(self):
        """Test is_claimable returns False when RUNNING."""
        job = Job(tool="photostats", status=JobStatus.RUNNING)
        assert job.is_claimable is False

    def test_is_claimable_when_completed(self):
        """Test is_claimable returns False when COMPLETED."""
        job = Job(tool="photostats", status=JobStatus.COMPLETED)
        assert job.is_claimable is False


class TestJobTerminalState:
    """Tests for is_terminal property."""

    def test_is_terminal_when_completed(self):
        """Test is_terminal returns True when COMPLETED."""
        job = Job(tool="photostats", status=JobStatus.COMPLETED)
        assert job.is_terminal is True

    def test_is_terminal_when_failed(self):
        """Test is_terminal returns True when FAILED."""
        job = Job(tool="photostats", status=JobStatus.FAILED)
        assert job.is_terminal is True

    def test_is_terminal_when_cancelled(self):
        """Test is_terminal returns True when CANCELLED."""
        job = Job(tool="photostats", status=JobStatus.CANCELLED)
        assert job.is_terminal is True

    def test_is_terminal_when_running(self):
        """Test is_terminal returns False when RUNNING."""
        job = Job(tool="photostats", status=JobStatus.RUNNING)
        assert job.is_terminal is False

    def test_is_terminal_when_pending(self):
        """Test is_terminal returns False when PENDING."""
        job = Job(tool="photostats", status=JobStatus.PENDING)
        assert job.is_terminal is False


class TestJobRetry:
    """Tests for retry functionality."""

    def test_can_retry_when_failed_with_retries_left(self):
        """Test can_retry returns True when failed with retries remaining."""
        job = Job(
            tool="photostats",
            status=JobStatus.FAILED,
            retry_count=1,
            max_retries=3
        )
        assert job.can_retry is True

    def test_can_retry_false_when_max_retries_reached(self):
        """Test can_retry returns False when max retries reached."""
        job = Job(
            tool="photostats",
            status=JobStatus.FAILED,
            retry_count=3,
            max_retries=3
        )
        assert job.can_retry is False

    def test_can_retry_false_when_not_failed(self):
        """Test can_retry returns False when not in FAILED status."""
        job = Job(
            tool="photostats",
            status=JobStatus.RUNNING,
            retry_count=0,
            max_retries=3
        )
        assert job.can_retry is False


class TestJobLifecycleMethods:
    """Tests for job lifecycle methods."""

    def test_assign_to_agent(self):
        """Test assign_to_agent sets agent_id and status."""
        job = Job(tool="photostats", status=JobStatus.PENDING)
        job.assign_to_agent(agent_id=42)

        assert job.agent_id == 42
        assert job.status == JobStatus.ASSIGNED
        assert job.assigned_at is not None

    def test_start_execution(self):
        """Test start_execution sets status and started_at."""
        job = Job(tool="photostats", status=JobStatus.ASSIGNED)
        job.start_execution()

        assert job.status == JobStatus.RUNNING
        assert job.started_at is not None

    def test_complete_without_result(self):
        """Test complete sets status and completed_at."""
        job = Job(tool="photostats", status=JobStatus.RUNNING)
        job.complete()

        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None
        assert job.result_id is None

    def test_complete_with_result(self):
        """Test complete sets result_id when provided."""
        job = Job(tool="photostats", status=JobStatus.RUNNING)
        job.complete(result_id=123)

        assert job.status == JobStatus.COMPLETED
        assert job.result_id == 123

    def test_fail(self):
        """Test fail sets status, completed_at, and error_message."""
        job = Job(tool="photostats", status=JobStatus.RUNNING)
        job.fail("Something went wrong")

        assert job.status == JobStatus.FAILED
        assert job.completed_at is not None
        assert job.error_message == "Something went wrong"

    def test_cancel(self):
        """Test cancel sets status and completed_at."""
        job = Job(tool="photostats", status=JobStatus.RUNNING)
        job.cancel()

        assert job.status == JobStatus.CANCELLED
        assert job.completed_at is not None

    def test_release(self):
        """Test release resets job to pending state."""
        job = Job(
            tool="photostats",
            status=JobStatus.RUNNING,
            agent_id=42,
            assigned_at=datetime.utcnow(),
            started_at=datetime.utcnow(),
            progress_json={"stage": "scanning"}
        )
        job.release()

        assert job.status == JobStatus.PENDING
        assert job.agent_id is None
        assert job.assigned_at is None
        assert job.started_at is None
        assert job.progress_json is None

    def test_prepare_retry(self):
        """Test prepare_retry increments retry_count and releases."""
        job = Job(
            tool="photostats",
            status=JobStatus.FAILED,
            agent_id=42,
            retry_count=1
        )
        job.prepare_retry()

        assert job.retry_count == 2
        assert job.status == JobStatus.PENDING
        assert job.agent_id is None


class TestJobRepresentation:
    """Tests for Job string representation."""

    def test_repr(self):
        """Test __repr__ output."""
        job = Job(tool="photostats", status=JobStatus.RUNNING)
        job.id = 1
        job.team_id = 1
        repr_str = repr(job)
        assert "Job" in repr_str
        assert "photostats" in repr_str
        assert "running" in repr_str

    def test_str(self):
        """Test __str__ output."""
        job = Job(tool="photostats", status=JobStatus.RUNNING)
        job.id = 1
        str_str = str(job)
        assert "photostats" in str_str
        assert "running" in str_str
