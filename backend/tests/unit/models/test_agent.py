"""
Unit tests for Agent model.

Tests GUID generation, AgentStatus enum, capabilities, and validation.
"""

import pytest
from datetime import datetime, timedelta

from backend.src.models.agent import Agent, AgentStatus


class TestAgentStatus:
    """Tests for AgentStatus enum."""

    def test_status_values(self):
        """Test that all expected status values exist."""
        assert AgentStatus.ONLINE.value == "online"
        assert AgentStatus.OFFLINE.value == "offline"
        assert AgentStatus.ERROR.value == "error"
        assert AgentStatus.REVOKED.value == "revoked"

    def test_status_is_string_enum(self):
        """Test that AgentStatus is a string enum."""
        assert isinstance(AgentStatus.ONLINE.value, str)
        assert str(AgentStatus.ONLINE) == "AgentStatus.ONLINE"


class TestAgentModel:
    """Tests for Agent model."""

    def test_guid_prefix(self):
        """Test that Agent has correct GUID prefix."""
        assert Agent.GUID_PREFIX == "agt"

    def test_tablename(self):
        """Test that Agent has correct table name."""
        assert Agent.__tablename__ == "agents"

    def test_default_status(self):
        """Test that status OFFLINE can be set."""
        agent = Agent(
            name="Test Agent",
            api_key_hash="a" * 64,
            api_key_prefix="agt_key_",
            status=AgentStatus.OFFLINE
        )
        assert agent.status == AgentStatus.OFFLINE

    def test_default_capabilities(self):
        """Test that default capabilities is empty list."""
        agent = Agent(
            name="Test Agent",
            api_key_hash="a" * 64,
            api_key_prefix="agt_key_"
        )
        # Default from Column definition
        assert agent.capabilities_json == [] or agent.capabilities_json is None


class TestAgentCapabilities:
    """Tests for Agent capabilities property."""

    def test_capabilities_getter_with_list(self):
        """Test capabilities getter when capabilities_json is a list."""
        agent = Agent(
            name="Test Agent",
            api_key_hash="a" * 64,
            api_key_prefix="agt_key_"
        )
        agent.capabilities_json = ["local_filesystem", "tool:photostats:1.0.0"]
        assert agent.capabilities == ["local_filesystem", "tool:photostats:1.0.0"]

    def test_capabilities_getter_with_none(self):
        """Test capabilities getter when capabilities_json is None."""
        agent = Agent(
            name="Test Agent",
            api_key_hash="a" * 64,
            api_key_prefix="agt_key_"
        )
        agent.capabilities_json = None
        assert agent.capabilities == []

    def test_capabilities_setter(self):
        """Test capabilities setter."""
        agent = Agent(
            name="Test Agent",
            api_key_hash="a" * 64,
            api_key_prefix="agt_key_"
        )
        agent.capabilities = ["local_filesystem"]
        assert agent.capabilities_json == ["local_filesystem"]

    def test_has_capability_true(self):
        """Test has_capability returns True for existing capability."""
        agent = Agent(
            name="Test Agent",
            api_key_hash="a" * 64,
            api_key_prefix="agt_key_"
        )
        agent.capabilities_json = ["local_filesystem", "tool:photostats:1.0.0"]
        assert agent.has_capability("local_filesystem") is True
        assert agent.has_capability("tool:photostats:1.0.0") is True

    def test_has_capability_false(self):
        """Test has_capability returns False for missing capability."""
        agent = Agent(
            name="Test Agent",
            api_key_hash="a" * 64,
            api_key_prefix="agt_key_"
        )
        agent.capabilities_json = ["local_filesystem"]
        assert agent.has_capability("tool:photostats:1.0.0") is False

    def test_has_all_capabilities_true(self):
        """Test has_all_capabilities returns True when all present."""
        agent = Agent(
            name="Test Agent",
            api_key_hash="a" * 64,
            api_key_prefix="agt_key_"
        )
        agent.capabilities_json = ["local_filesystem", "tool:photostats:1.0.0", "tool:photo_pairing:1.0.0"]
        assert agent.has_all_capabilities(["local_filesystem", "tool:photostats:1.0.0"]) is True

    def test_has_all_capabilities_false(self):
        """Test has_all_capabilities returns False when some missing."""
        agent = Agent(
            name="Test Agent",
            api_key_hash="a" * 64,
            api_key_prefix="agt_key_"
        )
        agent.capabilities_json = ["local_filesystem"]
        assert agent.has_all_capabilities(["local_filesystem", "tool:photostats:1.0.0"]) is False


class TestAgentStatusProperties:
    """Tests for Agent status-related properties."""

    def test_is_online_true(self):
        """Test is_online returns True when status is ONLINE."""
        agent = Agent(
            name="Test Agent",
            api_key_hash="a" * 64,
            api_key_prefix="agt_key_",
            status=AgentStatus.ONLINE
        )
        assert agent.is_online is True

    def test_is_online_false(self):
        """Test is_online returns False when status is not ONLINE."""
        agent = Agent(
            name="Test Agent",
            api_key_hash="a" * 64,
            api_key_prefix="agt_key_",
            status=AgentStatus.OFFLINE
        )
        assert agent.is_online is False

    def test_is_revoked_true(self):
        """Test is_revoked returns True when status is REVOKED."""
        agent = Agent(
            name="Test Agent",
            api_key_hash="a" * 64,
            api_key_prefix="agt_key_",
            status=AgentStatus.REVOKED
        )
        assert agent.is_revoked is True

    def test_is_revoked_false(self):
        """Test is_revoked returns False when status is not REVOKED."""
        agent = Agent(
            name="Test Agent",
            api_key_hash="a" * 64,
            api_key_prefix="agt_key_",
            status=AgentStatus.ONLINE
        )
        assert agent.is_revoked is False

    def test_can_execute_jobs_when_online(self):
        """Test can_execute_jobs returns True when ONLINE."""
        agent = Agent(
            name="Test Agent",
            api_key_hash="a" * 64,
            api_key_prefix="agt_key_",
            status=AgentStatus.ONLINE
        )
        assert agent.can_execute_jobs is True

    def test_can_execute_jobs_when_offline(self):
        """Test can_execute_jobs returns False when OFFLINE."""
        agent = Agent(
            name="Test Agent",
            api_key_hash="a" * 64,
            api_key_prefix="agt_key_",
            status=AgentStatus.OFFLINE
        )
        assert agent.can_execute_jobs is False

    def test_can_execute_jobs_when_revoked(self):
        """Test can_execute_jobs returns False when REVOKED."""
        agent = Agent(
            name="Test Agent",
            api_key_hash="a" * 64,
            api_key_prefix="agt_key_",
            status=AgentStatus.REVOKED
        )
        assert agent.can_execute_jobs is False


class TestAgentRepresentation:
    """Tests for Agent string representation."""

    def test_repr(self):
        """Test __repr__ output."""
        agent = Agent(
            name="Test Agent",
            api_key_hash="a" * 64,
            api_key_prefix="agt_key_",
            status=AgentStatus.ONLINE
        )
        agent.id = 1
        agent.team_id = 1
        repr_str = repr(agent)
        assert "Agent" in repr_str
        assert "Test Agent" in repr_str
        assert "online" in repr_str

    def test_str(self):
        """Test __str__ output."""
        agent = Agent(
            name="Test Agent",
            api_key_hash="a" * 64,
            api_key_prefix="agt_key_",
            status=AgentStatus.ONLINE
        )
        str_str = str(agent)
        assert "Test Agent" in str_str
        assert "online" in str_str
