"""
Unit tests for AgentService.

Tests agent registration, heartbeat processing, token management,
and offline detection.
"""

import pytest
import hashlib
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from backend.src.services.agent_service import (
    AgentService,
    HEARTBEAT_TIMEOUT_SECONDS,
    API_KEY_PREFIX,
    API_KEY_LENGTH,
)
from backend.src.models.agent import Agent, AgentStatus
from backend.src.models.agent_registration_token import (
    AgentRegistrationToken,
    DEFAULT_TOKEN_EXPIRATION_HOURS,
)
from backend.src.models import User, UserStatus, UserType, Team
from backend.src.models.job import Job, JobStatus
from backend.src.services.exceptions import NotFoundError, ValidationError


class TestAgentServiceTokenGeneration:
    """Tests for registration token generation."""

    def test_create_registration_token(self, test_db_session, test_team, test_user):
        """Test creating a registration token."""
        service = AgentService(test_db_session)

        result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
            name="Test Token"
        )

        assert result.token is not None
        assert result.plaintext_token is not None
        assert result.plaintext_token.startswith("art_")
        assert result.token.name == "Test Token"
        assert result.token.team_id == test_team.id
        assert result.token.created_by_user_id == test_user.id
        assert result.token.is_used is False
        assert result.token.is_expired is False

    def test_create_registration_token_default_expiration(
        self, test_db_session, test_team, test_user
    ):
        """Test token has default expiration of 24 hours."""
        service = AgentService(test_db_session)

        result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )

        # Should expire in approximately 24 hours
        expected_expiry = datetime.utcnow() + timedelta(hours=DEFAULT_TOKEN_EXPIRATION_HOURS)
        assert abs((result.token.expires_at - expected_expiry).total_seconds()) < 60

    def test_create_registration_token_custom_expiration(
        self, test_db_session, test_team, test_user
    ):
        """Test token with custom expiration."""
        service = AgentService(test_db_session)

        result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
            expiration_hours=48
        )

        expected_expiry = datetime.utcnow() + timedelta(hours=48)
        assert abs((result.token.expires_at - expected_expiry).total_seconds()) < 60

    def test_validate_registration_token_valid(
        self, test_db_session, test_team, test_user
    ):
        """Test validating a valid registration token."""
        service = AgentService(test_db_session)

        # Create a token
        result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )

        # Validate it
        token = service.validate_registration_token(result.plaintext_token)

        assert token is not None
        assert token.id == result.token.id
        assert token.is_valid is True

    def test_validate_registration_token_invalid(self, test_db_session):
        """Test validating an invalid registration token."""
        service = AgentService(test_db_session)

        with pytest.raises(ValidationError, match="Invalid registration token"):
            service.validate_registration_token("art_invalid_token_12345")

    def test_validate_registration_token_expired(
        self, test_db_session, test_team, test_user
    ):
        """Test validating an expired registration token."""
        service = AgentService(test_db_session)

        # Create a token that's already expired
        result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
            expiration_hours=0  # Expires immediately
        )

        # Manually set expiration to past
        result.token.expires_at = datetime.utcnow() - timedelta(hours=1)
        test_db_session.commit()

        with pytest.raises(ValidationError, match="expired"):
            service.validate_registration_token(result.plaintext_token)

    def test_validate_registration_token_used(
        self, test_db_session, test_team, test_user
    ):
        """Test validating an already used registration token."""
        service = AgentService(test_db_session)

        # Create a token
        result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )

        # Mark as used (without setting agent_id to avoid FK constraint)
        result.token.is_used = True
        test_db_session.commit()

        with pytest.raises(ValidationError, match="already been used"):
            service.validate_registration_token(result.plaintext_token)


class TestAgentServiceRegistration:
    """Tests for agent registration."""

    def test_register_agent_success(self, test_db_session, test_team, test_user):
        """Test successful agent registration."""
        service = AgentService(test_db_session)

        # Create a registration token
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )

        # Register agent
        result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
            hostname="test-host.local",
            os_info="macOS 14.0",
            capabilities=["local_filesystem", "tool:photostats:1.0.0"],
            version="1.0.0"
        )

        assert result.agent is not None
        assert result.api_key is not None
        assert result.api_key.startswith(API_KEY_PREFIX)
        assert result.agent.name == "Test Agent"
        assert result.agent.hostname == "test-host.local"
        assert result.agent.os_info == "macOS 14.0"
        assert result.agent.status == AgentStatus.OFFLINE  # Starts offline until first heartbeat
        assert result.agent.last_heartbeat is None  # No heartbeat yet
        assert "local_filesystem" in result.agent.capabilities
        assert result.agent.team_id == test_team.id

    def test_register_agent_creates_system_user(
        self, test_db_session, test_team, test_user
    ):
        """Test that agent registration creates a SYSTEM user."""
        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )

        result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
        )

        # Verify system user was created
        assert result.agent.system_user_id is not None

        system_user = test_db_session.query(User).filter(
            User.id == result.agent.system_user_id
        ).first()

        assert system_user is not None
        assert system_user.user_type == UserType.SYSTEM
        assert "@system.shuttersense.local" in system_user.email

    def test_register_agent_marks_token_used(
        self, test_db_session, test_team, test_user
    ):
        """Test that registration marks the token as used."""
        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )

        result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
        )

        # Refresh token from database
        test_db_session.refresh(token_result.token)

        assert token_result.token.is_used is True
        assert token_result.token.used_by_agent_id == result.agent.id

    def test_register_agent_invalid_token(self, test_db_session):
        """Test registration with invalid token."""
        service = AgentService(test_db_session)

        with pytest.raises(ValidationError, match="Invalid registration token"):
            service.register_agent(
                plaintext_token="art_invalid_token",
                name="Test Agent",
            )

    def test_register_agent_token_cannot_be_reused(
        self, test_db_session, test_team, test_user
    ):
        """Test that a token cannot be used twice."""
        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )

        # First registration succeeds
        service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Agent 1",
        )

        # Second registration fails
        with pytest.raises(ValidationError, match="already been used"):
            service.register_agent(
                plaintext_token=token_result.plaintext_token,
                name="Agent 2",
            )


class TestAgentServiceHeartbeat:
    """Tests for agent heartbeat processing."""

    def test_process_heartbeat_updates_timestamp(
        self, test_db_session, test_team, test_user
    ):
        """Test that heartbeat updates last_heartbeat timestamp."""
        service = AgentService(test_db_session)

        # Create and register an agent
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
        )

        # Agent starts with no heartbeat
        assert reg_result.agent.last_heartbeat is None

        # Process first heartbeat
        service.process_heartbeat(reg_result.agent)
        first_heartbeat = reg_result.agent.last_heartbeat

        assert first_heartbeat is not None

        # Wait a tiny bit to ensure timestamp changes
        import time
        time.sleep(0.01)

        # Process second heartbeat
        service.process_heartbeat(reg_result.agent)

        assert reg_result.agent.last_heartbeat > first_heartbeat

    def test_process_heartbeat_updates_status(
        self, test_db_session, test_team, test_user
    ):
        """Test that heartbeat can update agent status."""
        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
        )

        # Process heartbeat with ERROR status
        service.process_heartbeat(
            reg_result.agent,
            status=AgentStatus.ERROR,
            error_message="Test error"
        )

        assert reg_result.agent.status == AgentStatus.ERROR
        assert reg_result.agent.error_message == "Test error"

    def test_process_heartbeat_updates_capabilities(
        self, test_db_session, test_team, test_user
    ):
        """Test that heartbeat can update capabilities."""
        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
            capabilities=["local_filesystem"],
        )

        # Update capabilities via heartbeat
        new_capabilities = ["local_filesystem", "tool:photostats:1.0.0"]
        service.process_heartbeat(
            reg_result.agent,
            capabilities=new_capabilities
        )

        assert reg_result.agent.capabilities == new_capabilities


class TestAgentServiceOfflineDetection:
    """Tests for offline agent detection."""

    def test_check_offline_agents_marks_stale_agents(
        self, test_db_session, test_team, test_user
    ):
        """Test that stale agents are marked offline."""
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

        # Bring agent online via heartbeat, then make it stale
        service.process_heartbeat(reg_result.agent, status=AgentStatus.ONLINE)
        reg_result.agent.last_heartbeat = (
            datetime.utcnow() - timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS + 10)
        )
        test_db_session.commit()

        # Check for offline agents
        offline_agents = service.check_offline_agents(test_team.id)

        assert len(offline_agents) == 1
        assert offline_agents[0].id == reg_result.agent.id
        assert offline_agents[0].status == AgentStatus.OFFLINE

    def test_check_offline_agents_ignores_recent_heartbeats(
        self, test_db_session, test_team, test_user
    ):
        """Test that agents with recent heartbeats are not marked offline."""
        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
        )

        # Bring agent online via heartbeat with recent timestamp
        service.process_heartbeat(reg_result.agent, status=AgentStatus.ONLINE)
        reg_result.agent.last_heartbeat = datetime.utcnow()
        test_db_session.commit()

        offline_agents = service.check_offline_agents(test_team.id)

        assert len(offline_agents) == 0
        assert reg_result.agent.status == AgentStatus.ONLINE


class TestAgentServiceApiKeyValidation:
    """Tests for API key validation."""

    def test_get_agent_by_api_key_valid(
        self, test_db_session, test_team, test_user
    ):
        """Test retrieving agent by valid API key."""
        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
        )

        # Get agent by API key
        agent = service.get_agent_by_api_key(reg_result.api_key)

        assert agent is not None
        assert agent.id == reg_result.agent.id

    def test_get_agent_by_api_key_invalid(self, test_db_session):
        """Test retrieving agent with invalid API key."""
        service = AgentService(test_db_session)

        agent = service.get_agent_by_api_key("agt_key_invalid")

        assert agent is None


class TestAgentServiceManagement:
    """Tests for agent management operations."""

    def test_list_agents(self, test_db_session, test_team, test_user):
        """Test listing agents for a team."""
        service = AgentService(test_db_session)

        # Create two agents
        for i in range(2):
            token_result = service.create_registration_token(
                team_id=test_team.id,
                created_by_user_id=test_user.id,
            )
            service.register_agent(
                plaintext_token=token_result.plaintext_token,
                name=f"Agent {i+1}",
            )

        agents = service.list_agents(test_team.id)

        assert len(agents) == 2

    def test_list_agents_excludes_revoked_by_default(
        self, test_db_session, test_team, test_user
    ):
        """Test that revoked agents are excluded by default."""
        service = AgentService(test_db_session)

        # Create two agents
        token_result1 = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result1 = service.register_agent(
            plaintext_token=token_result1.plaintext_token,
            name="Agent 1",
        )

        token_result2 = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        service.register_agent(
            plaintext_token=token_result2.plaintext_token,
            name="Agent 2",
        )

        # Revoke first agent
        service.revoke_agent(reg_result1.agent, "Testing")

        agents = service.list_agents(test_team.id, include_revoked=False)

        assert len(agents) == 1
        assert agents[0].name == "Agent 2"

    def test_revoke_agent(self, test_db_session, test_team, test_user):
        """Test revoking an agent."""
        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
        )

        service.revoke_agent(reg_result.agent, "Security concern")

        assert reg_result.agent.status == AgentStatus.REVOKED
        assert reg_result.agent.revocation_reason == "Security concern"
        assert reg_result.agent.revoked_at is not None

    def test_rename_agent(self, test_db_session, test_team, test_user):
        """Test renaming an agent."""
        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Original Name",
        )

        service.rename_agent(reg_result.agent, "New Name")

        assert reg_result.agent.name == "New Name"

    def test_get_agent_by_guid(self, test_db_session, test_team, test_user):
        """Test retrieving agent by GUID."""
        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
        )

        agent = service.get_agent_by_guid(reg_result.agent.guid, test_team.id)

        assert agent is not None
        assert agent.id == reg_result.agent.id

    def test_get_agent_by_guid_wrong_team(
        self, test_db_session, test_team, test_user
    ):
        """Test that agents from other teams are not accessible (returns 404)."""
        from backend.src.services.exceptions import NotFoundError

        service = AgentService(test_db_session)

        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
        )

        # Try to get with wrong team_id - should raise NotFoundError (prevents info leak)
        with pytest.raises(NotFoundError):
            service.get_agent_by_guid(reg_result.agent.guid, test_team.id + 999)


class TestAgentServicePoolStatus:
    """Tests for agent pool status."""

    def test_get_pool_status_empty(self, test_db_session, test_team):
        """Test pool status with no agents."""
        service = AgentService(test_db_session)

        status = service.get_pool_status(test_team.id)

        assert status["online_count"] == 0
        assert status["offline_count"] == 0
        assert status["idle_count"] == 0
        assert status["running_jobs_count"] == 0
        assert status["status"] == "offline"

    def test_get_pool_status_with_online_agents(
        self, test_db_session, test_team, test_user
    ):
        """Test pool status with online agents."""
        service = AgentService(test_db_session)

        # Create and register an agent
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
        )

        # Bring agent online via heartbeat
        service.process_heartbeat(reg_result.agent, status=AgentStatus.ONLINE)

        status = service.get_pool_status(test_team.id)

        assert status["online_count"] == 1
        assert status["idle_count"] == 1  # No running jobs
        assert status["status"] == "idle"

    def test_get_pool_status_with_running_jobs(
        self, test_db_session, test_team, test_user
    ):
        """Test pool status with running jobs."""
        service = AgentService(test_db_session)

        # Create and register an agent
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
        )

        # Bring agent online via heartbeat
        service.process_heartbeat(reg_result.agent, status=AgentStatus.ONLINE)

        # Create a running job assigned to this agent
        job = Job(
            team_id=test_team.id,
            tool="photostats",
            status=JobStatus.RUNNING,
            agent_id=reg_result.agent.id,
            required_capabilities_json="[]",  # SQLite needs serialized JSON
        )
        test_db_session.add(job)
        test_db_session.commit()

        status = service.get_pool_status(test_team.id)

        assert status["online_count"] == 1
        assert status["running_jobs_count"] == 1
        assert status["idle_count"] == 0  # Agent is running a job
        assert status["status"] == "running"
