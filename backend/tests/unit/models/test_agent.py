"""
Unit tests for Agent model.

Tests GUID generation, AgentStatus enum, capabilities, and validation.
"""

import pytest
from datetime import datetime, timedelta

from backend.src.models.agent import Agent, AgentStatus
from backend.src.models.agent_runtime import AgentRuntime


def _make_agent(status=None, **kwargs):
    """Helper to create an Agent with an attached AgentRuntime."""
    agent = Agent(
        name=kwargs.pop("name", "Test Agent"),
        api_key_hash=kwargs.pop("api_key_hash", "a" * 64),
        api_key_prefix=kwargs.pop("api_key_prefix", "agt_key_"),
        **kwargs,
    )
    runtime = AgentRuntime(
        status=status if status is not None else AgentStatus.OFFLINE,
    )
    agent.runtime = runtime
    return agent


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
        agent = _make_agent(status=AgentStatus.OFFLINE)
        assert agent.status == AgentStatus.OFFLINE

    def test_default_capabilities(self):
        """Test that default capabilities is empty list."""
        agent = _make_agent()
        # Default runtime has empty capabilities
        assert agent.capabilities == []


class TestAgentCapabilities:
    """Tests for Agent capabilities property."""

    def test_capabilities_getter_with_list(self):
        """Test capabilities getter when capabilities_json is a list."""
        agent = _make_agent()
        agent.runtime.capabilities_json = ["local_filesystem", "tool:photostats:1.0.0"]
        assert agent.capabilities == ["local_filesystem", "tool:photostats:1.0.0"]

    def test_capabilities_getter_with_none(self):
        """Test capabilities getter when capabilities_json is None."""
        agent = _make_agent()
        agent.runtime.capabilities_json = None
        assert agent.capabilities == []

    def test_capabilities_setter(self):
        """Test capabilities setter stores value correctly."""
        agent = _make_agent()
        agent.capabilities = ["local_filesystem"]
        # Verify via getter (internal storage format varies by DB type)
        assert agent.capabilities == ["local_filesystem"]

    def test_has_capability_true(self):
        """Test has_capability returns True for existing capability."""
        agent = _make_agent()
        agent.runtime.capabilities_json = ["local_filesystem", "tool:photostats:1.0.0"]
        assert agent.has_capability("local_filesystem") is True
        assert agent.has_capability("tool:photostats:1.0.0") is True

    def test_has_capability_false(self):
        """Test has_capability returns False for missing capability."""
        agent = _make_agent()
        agent.runtime.capabilities_json = ["local_filesystem"]
        assert agent.has_capability("tool:photostats:1.0.0") is False

    def test_has_all_capabilities_true(self):
        """Test has_all_capabilities returns True when all present."""
        agent = _make_agent()
        agent.runtime.capabilities_json = ["local_filesystem", "tool:photostats:1.0.0", "tool:photo_pairing:1.0.0"]
        assert agent.has_all_capabilities(["local_filesystem", "tool:photostats:1.0.0"]) is True

    def test_has_all_capabilities_false(self):
        """Test has_all_capabilities returns False when some missing."""
        agent = _make_agent()
        agent.runtime.capabilities_json = ["local_filesystem"]
        assert agent.has_all_capabilities(["local_filesystem", "tool:photostats:1.0.0"]) is False


class TestAgentStatusProperties:
    """Tests for Agent status-related properties."""

    def test_is_online_true(self):
        """Test is_online returns True when status is ONLINE."""
        agent = _make_agent(status=AgentStatus.ONLINE)
        assert agent.is_online is True

    def test_is_online_false(self):
        """Test is_online returns False when status is not ONLINE."""
        agent = _make_agent(status=AgentStatus.OFFLINE)
        assert agent.is_online is False

    def test_is_revoked_true(self):
        """Test is_revoked returns True when revoked_at is set."""
        agent = _make_agent(status=AgentStatus.REVOKED, revoked_at=datetime.utcnow())
        assert agent.is_revoked is True

    def test_is_revoked_false(self):
        """Test is_revoked returns False when revoked_at is not set."""
        agent = _make_agent(status=AgentStatus.ONLINE)
        assert agent.is_revoked is False

    def test_can_execute_jobs_when_online(self):
        """Test can_execute_jobs returns True when ONLINE and verified."""
        agent = _make_agent(status=AgentStatus.ONLINE, is_verified=True)
        assert agent.can_execute_jobs is True

    def test_can_execute_jobs_when_offline(self):
        """Test can_execute_jobs returns False when OFFLINE."""
        agent = _make_agent(status=AgentStatus.OFFLINE)
        assert agent.can_execute_jobs is False

    def test_can_execute_jobs_when_revoked(self):
        """Test can_execute_jobs returns False when REVOKED."""
        agent = _make_agent(status=AgentStatus.REVOKED)
        assert agent.can_execute_jobs is False


class TestAgentAuthorizedRoots:
    """Tests for Agent authorized_roots property and is_path_authorized method.

    Issue #90 - Distributed Agent Architecture (Phase 6b)
    Task: T133
    """

    def test_authorized_roots_getter_with_list(self):
        """Test authorized_roots getter when authorized_roots_json is a list."""
        agent = _make_agent()
        agent.runtime.authorized_roots_json = ["/photos", "/backup"]
        assert agent.authorized_roots == ["/photos", "/backup"]

    def test_authorized_roots_getter_with_none(self):
        """Test authorized_roots getter when authorized_roots_json is None."""
        agent = _make_agent()
        agent.runtime.authorized_roots_json = None
        assert agent.authorized_roots == []

    def test_authorized_roots_setter(self):
        """Test authorized_roots setter stores value correctly."""
        agent = _make_agent()
        agent.authorized_roots = ["/photos", "/backup"]
        assert agent.authorized_roots == ["/photos", "/backup"]

    def test_authorized_roots_setter_empty_list(self):
        """Test authorized_roots setter with empty list."""
        agent = _make_agent()
        agent.authorized_roots = []
        assert agent.authorized_roots == []

    def test_is_path_authorized_exact_match(self):
        """Test is_path_authorized returns True for exact root match."""
        agent = _make_agent()
        agent.authorized_roots = ["/photos", "/backup"]
        assert agent.is_path_authorized("/photos") is True
        assert agent.is_path_authorized("/backup") is True

    def test_is_path_authorized_subdirectory(self):
        """Test is_path_authorized returns True for subdirectories of root."""
        agent = _make_agent()
        agent.authorized_roots = ["/photos"]
        assert agent.is_path_authorized("/photos/vacation") is True
        assert agent.is_path_authorized("/photos/vacation/2024") is True

    def test_is_path_authorized_not_under_root(self):
        """Test is_path_authorized returns False for paths not under any root."""
        agent = _make_agent()
        agent.authorized_roots = ["/photos"]
        assert agent.is_path_authorized("/documents") is False
        assert agent.is_path_authorized("/photos2") is False

    def test_is_path_authorized_empty_roots(self):
        """Test is_path_authorized returns False when no roots configured."""
        agent = _make_agent()
        agent.authorized_roots = []
        assert agent.is_path_authorized("/photos") is False

    def test_is_path_authorized_multiple_roots(self):
        """Test is_path_authorized with multiple authorized roots."""
        agent = _make_agent()
        agent.authorized_roots = ["/photos", "/backup", "/external"]
        assert agent.is_path_authorized("/photos/vacation") is True
        assert agent.is_path_authorized("/backup/archives") is True
        assert agent.is_path_authorized("/external/raw") is True
        assert agent.is_path_authorized("/documents") is False


class TestAgentRepresentation:
    """Tests for Agent string representation."""

    def test_repr(self):
        """Test __repr__ output."""
        agent = _make_agent(status=AgentStatus.ONLINE)
        agent.id = 1
        agent.team_id = 1
        repr_str = repr(agent)
        assert "Agent" in repr_str
        assert "Test Agent" in repr_str
        assert "online" in repr_str

    def test_str(self):
        """Test __str__ output."""
        agent = _make_agent(status=AgentStatus.ONLINE)
        str_str = str(agent)
        assert "Test Agent" in str_str
        assert "online" in str_str
