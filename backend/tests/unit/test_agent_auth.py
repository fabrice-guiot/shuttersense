"""
Unit tests for agent authentication dependency.

Tests API key validation and AgentContext creation.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException

from backend.src.api.agent.dependencies import (
    AgentContext,
    get_agent_context,
    get_optional_agent_context,
    require_online_agent,
)
from backend.src.models.agent import Agent, AgentStatus
from backend.src.services.agent_service import AgentService


class TestAgentContext:
    """Tests for AgentContext dataclass."""

    def test_agent_context_creation(self):
        """Test creating a valid AgentContext."""
        ctx = AgentContext(
            agent_id=1,
            agent_guid="agt_test123",
            team_id=1,
            team_guid="tea_test123",
            agent_name="Test Agent",
            status=AgentStatus.ONLINE,
        )

        assert ctx.agent_id == 1
        assert ctx.agent_guid == "agt_test123"
        assert ctx.team_id == 1
        assert ctx.team_guid == "tea_test123"
        assert ctx.agent_name == "Test Agent"
        assert ctx.status == AgentStatus.ONLINE

    def test_agent_context_requires_agent_id(self):
        """Test that AgentContext requires agent_id."""
        with pytest.raises(ValueError, match="agent_id and agent_guid are required"):
            AgentContext(
                agent_id=None,
                agent_guid="agt_test123",
                team_id=1,
                team_guid="tea_test123",
                agent_name="Test Agent",
                status=AgentStatus.ONLINE,
            )

    def test_agent_context_requires_team_id(self):
        """Test that AgentContext requires team_id."""
        with pytest.raises(ValueError, match="team_id and team_guid are required"):
            AgentContext(
                agent_id=1,
                agent_guid="agt_test123",
                team_id=None,
                team_guid="tea_test123",
                agent_name="Test Agent",
                status=AgentStatus.ONLINE,
            )


class TestGetAgentContext:
    """Tests for get_agent_context dependency."""

    @pytest.mark.asyncio
    async def test_get_agent_context_no_auth_header(self, test_db_session):
        """Test that missing Authorization header raises 401."""
        request = Mock()
        request.headers.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_agent_context(request, test_db_session)

        assert exc_info.value.status_code == 401
        assert "Authorization header required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_agent_context_invalid_auth_format(self, test_db_session):
        """Test that invalid Authorization format raises 401."""
        request = Mock()
        request.headers.get.return_value = "InvalidFormat token123"

        with pytest.raises(HTTPException) as exc_info:
            await get_agent_context(request, test_db_session)

        assert exc_info.value.status_code == 401
        assert "Invalid Authorization header format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_agent_context_invalid_api_key_format(self, test_db_session):
        """Test that invalid API key format raises 401."""
        request = Mock()
        request.headers.get.return_value = "Bearer invalid_key_format"

        with pytest.raises(HTTPException) as exc_info:
            await get_agent_context(request, test_db_session)

        assert exc_info.value.status_code == 401
        assert "Invalid API key format" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_agent_context_api_key_not_found(self, test_db_session):
        """Test that non-existent API key raises 401."""
        request = Mock()
        request.headers.get.return_value = "Bearer agt_key_nonexistent123"

        with pytest.raises(HTTPException) as exc_info:
            await get_agent_context(request, test_db_session)

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_agent_context_revoked_agent(
        self, test_db_session, test_team, test_user
    ):
        """Test that revoked agent raises 403."""
        # Create and register an agent
        service = AgentService(test_db_session)
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
        )

        # Revoke the agent
        service.revoke_agent(reg_result.agent, "Testing")

        request = Mock()
        request.headers.get.return_value = f"Bearer {reg_result.api_key}"

        with pytest.raises(HTTPException) as exc_info:
            await get_agent_context(request, test_db_session)

        assert exc_info.value.status_code == 403
        assert "revoked" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_agent_context_valid_api_key(
        self, test_db_session, test_team, test_user
    ):
        """Test successful agent authentication."""
        # Create and register an agent
        service = AgentService(test_db_session)
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
        )

        request = Mock()
        request.headers.get.return_value = f"Bearer {reg_result.api_key}"

        ctx = await get_agent_context(request, test_db_session)

        assert ctx.agent_id == reg_result.agent.id
        assert ctx.agent_guid == reg_result.agent.guid
        assert ctx.team_id == test_team.id
        assert ctx.agent_name == "Test Agent"
        assert ctx.status == AgentStatus.OFFLINE  # Starts offline until first heartbeat


class TestGetOptionalAgentContext:
    """Tests for get_optional_agent_context dependency."""

    @pytest.mark.asyncio
    async def test_optional_returns_none_on_failure(self, test_db_session):
        """Test that optional context returns None on auth failure."""
        request = Mock()
        request.headers.get.return_value = None

        ctx = await get_optional_agent_context(request, test_db_session)

        assert ctx is None

    @pytest.mark.asyncio
    async def test_optional_returns_context_on_success(
        self, test_db_session, test_team, test_user
    ):
        """Test that optional context returns AgentContext on success."""
        # Create and register an agent
        service = AgentService(test_db_session)
        token_result = service.create_registration_token(
            team_id=test_team.id,
            created_by_user_id=test_user.id,
        )
        reg_result = service.register_agent(
            plaintext_token=token_result.plaintext_token,
            name="Test Agent",
        )

        request = Mock()
        request.headers.get.return_value = f"Bearer {reg_result.api_key}"

        ctx = await get_optional_agent_context(request, test_db_session)

        assert ctx is not None
        assert ctx.agent_id == reg_result.agent.id


class TestRequireOnlineAgent:
    """Tests for require_online_agent dependency."""

    def test_require_online_allows_online_agent(self):
        """Test that online agents pass the check."""
        ctx = AgentContext(
            agent_id=1,
            agent_guid="agt_test123",
            team_id=1,
            team_guid="tea_test123",
            agent_name="Test Agent",
            status=AgentStatus.ONLINE,
        )

        result = require_online_agent(ctx)

        assert result == ctx

    def test_require_online_rejects_offline_agent(self):
        """Test that offline agents are rejected."""
        ctx = AgentContext(
            agent_id=1,
            agent_guid="agt_test123",
            team_id=1,
            team_guid="tea_test123",
            agent_name="Test Agent",
            status=AgentStatus.OFFLINE,
        )

        with pytest.raises(HTTPException) as exc_info:
            require_online_agent(ctx)

        assert exc_info.value.status_code == 403
        assert "must be online" in exc_info.value.detail.lower()

    def test_require_online_rejects_error_agent(self):
        """Test that agents in ERROR status are rejected."""
        ctx = AgentContext(
            agent_id=1,
            agent_guid="agt_test123",
            team_id=1,
            team_guid="tea_test123",
            agent_name="Test Agent",
            status=AgentStatus.ERROR,
        )

        with pytest.raises(HTTPException) as exc_info:
            require_online_agent(ctx)

        assert exc_info.value.status_code == 403
