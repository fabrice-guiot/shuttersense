"""
Unit tests for agent metrics storage and retrieval.

Tests metrics storage in Agent model and heartbeat processing.
Part of Issue #90 - Distributed Agent Architecture (Phase 11).
Task: T164 - Unit tests for metrics storage
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch

from backend.src.services.agent_service import AgentService
from backend.src.models.agent import Agent, AgentStatus
from backend.src.api.agent.schemas import AgentMetrics, HeartbeatRequest


class TestAgentMetricsModel:
    """Tests for Agent model metrics property."""

    def test_metrics_property_when_none(self, test_db_session, test_team, test_user):
        """Test metrics property returns None when no metrics set."""
        service = AgentService(test_db_session)

        # Create an agent
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
        )

        # Verify metrics is None initially
        assert reg_result.agent.metrics is None
        assert reg_result.agent.metrics_json is None

    def test_metrics_property_setter_and_getter(self, test_db_session, test_team, test_user):
        """Test setting and getting metrics via property."""
        service = AgentService(test_db_session)

        # Create an agent
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
        )

        # Set metrics
        metrics_data = {
            "cpu_percent": 45.5,
            "memory_percent": 62.3,
            "disk_free_gb": 128.7
        }
        reg_result.agent.metrics = metrics_data
        test_db_session.commit()

        # Refresh and verify
        test_db_session.refresh(reg_result.agent)
        assert reg_result.agent.metrics is not None
        assert reg_result.agent.metrics["cpu_percent"] == 45.5
        assert reg_result.agent.metrics["memory_percent"] == 62.3
        assert reg_result.agent.metrics["disk_free_gb"] == 128.7

    def test_metrics_property_clears_with_none(self, test_db_session, test_team, test_user):
        """Test that setting metrics to None clears them."""
        service = AgentService(test_db_session)

        # Create an agent with metrics
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
        )

        # Set then clear metrics
        reg_result.agent.metrics = {"cpu_percent": 50.0}
        test_db_session.commit()

        reg_result.agent.metrics = None
        test_db_session.commit()

        test_db_session.refresh(reg_result.agent)
        assert reg_result.agent.metrics is None


class TestHeartbeatWithMetrics:
    """Tests for heartbeat processing with metrics."""

    def test_process_heartbeat_stores_metrics(self, test_db_session, test_team, test_user):
        """Test that heartbeat stores metrics in the agent."""
        service = AgentService(test_db_session)

        # Create an agent
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
        )

        # Process heartbeat with metrics
        metrics = {
            "cpu_percent": 35.2,
            "memory_percent": 55.8,
            "disk_free_gb": 200.0
        }
        service.process_heartbeat(
            agent=reg_result.agent,
            status=AgentStatus.ONLINE,
            metrics=metrics,
        )

        # Verify metrics are stored
        test_db_session.refresh(reg_result.agent)
        assert reg_result.agent.metrics is not None
        assert reg_result.agent.metrics["cpu_percent"] == 35.2
        assert reg_result.agent.metrics["memory_percent"] == 55.8
        assert reg_result.agent.metrics["disk_free_gb"] == 200.0
        # Should include timestamp
        assert "metrics_updated_at" in reg_result.agent.metrics

    def test_process_heartbeat_updates_metrics(self, test_db_session, test_team, test_user):
        """Test that subsequent heartbeats update metrics."""
        service = AgentService(test_db_session)

        # Create an agent
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
        )

        # First heartbeat
        service.process_heartbeat(
            agent=reg_result.agent,
            metrics={"cpu_percent": 20.0},
        )

        # Second heartbeat with different metrics
        service.process_heartbeat(
            agent=reg_result.agent,
            metrics={"cpu_percent": 80.0},
        )

        # Verify metrics are updated
        test_db_session.refresh(reg_result.agent)
        assert reg_result.agent.metrics["cpu_percent"] == 80.0

    def test_process_heartbeat_without_metrics_preserves_existing(
        self, test_db_session, test_team, test_user
    ):
        """Test that heartbeat without metrics preserves existing metrics."""
        service = AgentService(test_db_session)

        # Create an agent
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
        )

        # First heartbeat with metrics
        service.process_heartbeat(
            agent=reg_result.agent,
            metrics={"cpu_percent": 50.0},
        )

        # Second heartbeat without metrics
        service.process_heartbeat(
            agent=reg_result.agent,
            status=AgentStatus.ONLINE,
            metrics=None,  # Explicitly no metrics
        )

        # Verify original metrics are preserved
        test_db_session.refresh(reg_result.agent)
        assert reg_result.agent.metrics["cpu_percent"] == 50.0

    def test_process_heartbeat_with_partial_metrics(
        self, test_db_session, test_team, test_user
    ):
        """Test heartbeat with only some metrics fields."""
        service = AgentService(test_db_session)

        # Create an agent
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
        )

        # Heartbeat with only CPU metric
        service.process_heartbeat(
            agent=reg_result.agent,
            metrics={"cpu_percent": 75.5},
        )

        # Verify only CPU metric is stored
        test_db_session.refresh(reg_result.agent)
        assert reg_result.agent.metrics["cpu_percent"] == 75.5
        assert "memory_percent" not in reg_result.agent.metrics or reg_result.agent.metrics.get("memory_percent") is None


class TestAgentMetricsSchema:
    """Tests for AgentMetrics Pydantic schema."""

    def test_agent_metrics_validation_valid(self):
        """Test AgentMetrics accepts valid values."""
        metrics = AgentMetrics(
            cpu_percent=45.5,
            memory_percent=62.3,
            disk_free_gb=128.7
        )
        assert metrics.cpu_percent == 45.5
        assert metrics.memory_percent == 62.3
        assert metrics.disk_free_gb == 128.7

    def test_agent_metrics_validation_optional_fields(self):
        """Test AgentMetrics accepts partial data."""
        metrics = AgentMetrics(cpu_percent=50.0)
        assert metrics.cpu_percent == 50.0
        assert metrics.memory_percent is None
        assert metrics.disk_free_gb is None

    def test_agent_metrics_validation_rejects_negative_cpu(self):
        """Test AgentMetrics rejects negative CPU percent."""
        with pytest.raises(ValueError):
            AgentMetrics(cpu_percent=-5.0)

    def test_agent_metrics_validation_rejects_over_100_cpu(self):
        """Test AgentMetrics rejects CPU percent over 100."""
        with pytest.raises(ValueError):
            AgentMetrics(cpu_percent=150.0)

    def test_agent_metrics_validation_rejects_negative_memory(self):
        """Test AgentMetrics rejects negative memory percent."""
        with pytest.raises(ValueError):
            AgentMetrics(memory_percent=-10.0)

    def test_agent_metrics_validation_accepts_boundary_values(self):
        """Test AgentMetrics accepts boundary values."""
        metrics = AgentMetrics(
            cpu_percent=0.0,
            memory_percent=100.0,
            disk_free_gb=0.0
        )
        assert metrics.cpu_percent == 0.0
        assert metrics.memory_percent == 100.0
        assert metrics.disk_free_gb == 0.0


class TestHeartbeatRequestWithMetrics:
    """Tests for HeartbeatRequest schema with metrics."""

    def test_heartbeat_request_with_metrics(self):
        """Test HeartbeatRequest accepts metrics field."""
        request = HeartbeatRequest(
            status=AgentStatus.ONLINE,
            metrics=AgentMetrics(
                cpu_percent=45.0,
                memory_percent=60.0,
                disk_free_gb=100.0
            )
        )
        assert request.metrics is not None
        assert request.metrics.cpu_percent == 45.0

    def test_heartbeat_request_without_metrics(self):
        """Test HeartbeatRequest works without metrics."""
        request = HeartbeatRequest(status=AgentStatus.ONLINE)
        assert request.metrics is None

    def test_heartbeat_request_metrics_model_dump(self):
        """Test metrics can be dumped to dict for service."""
        request = HeartbeatRequest(
            status=AgentStatus.ONLINE,
            metrics=AgentMetrics(
                cpu_percent=25.0,
                memory_percent=50.0
            )
        )
        metrics_dict = request.metrics.model_dump(exclude_none=True)
        assert metrics_dict == {
            "cpu_percent": 25.0,
            "memory_percent": 50.0
        }
