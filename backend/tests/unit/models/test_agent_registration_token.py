"""
Unit tests for AgentRegistrationToken model.

Tests expiration, usage tracking, and validation.
"""

import pytest
from datetime import datetime, timedelta

from backend.src.models.agent_registration_token import (
    AgentRegistrationToken,
    DEFAULT_TOKEN_EXPIRATION_HOURS
)


class TestAgentRegistrationTokenModel:
    """Tests for AgentRegistrationToken model."""

    def test_guid_prefix(self):
        """Test that AgentRegistrationToken has correct GUID prefix."""
        assert AgentRegistrationToken.GUID_PREFIX == "art"

    def test_tablename(self):
        """Test that AgentRegistrationToken has correct table name."""
        assert AgentRegistrationToken.__tablename__ == "agent_registration_tokens"

    def test_default_is_used(self):
        """Test that is_used can be set to False."""
        token = AgentRegistrationToken(
            token_hash="a" * 64,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_used=False
        )
        assert token.is_used is False

    def test_default_expiration_hours_constant(self):
        """Test default expiration hours constant."""
        assert DEFAULT_TOKEN_EXPIRATION_HOURS == 24


class TestAgentRegistrationTokenExpiration:
    """Tests for token expiration."""

    def test_is_expired_false_when_future(self):
        """Test is_expired returns False when expires_at is in future."""
        token = AgentRegistrationToken(
            token_hash="a" * 64,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        assert token.is_expired is False

    def test_is_expired_true_when_past(self):
        """Test is_expired returns True when expires_at is in past."""
        token = AgentRegistrationToken(
            token_hash="a" * 64,
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        assert token.is_expired is True

    def test_time_until_expiration_returns_timedelta(self):
        """Test time_until_expiration returns positive timedelta when valid."""
        future_time = datetime.utcnow() + timedelta(hours=12)
        token = AgentRegistrationToken(
            token_hash="a" * 64,
            expires_at=future_time
        )
        remaining = token.time_until_expiration
        assert remaining is not None
        assert remaining.total_seconds() > 0

    def test_time_until_expiration_returns_none_when_expired(self):
        """Test time_until_expiration returns None when expired."""
        token = AgentRegistrationToken(
            token_hash="a" * 64,
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        assert token.time_until_expiration is None


class TestAgentRegistrationTokenValidity:
    """Tests for token validity checks."""

    def test_is_valid_true_when_unused_and_not_expired(self):
        """Test is_valid returns True when unused and not expired."""
        token = AgentRegistrationToken(
            token_hash="a" * 64,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_used=False
        )
        assert token.is_valid is True

    def test_is_valid_false_when_used(self):
        """Test is_valid returns False when already used."""
        token = AgentRegistrationToken(
            token_hash="a" * 64,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_used=True
        )
        assert token.is_valid is False

    def test_is_valid_false_when_expired(self):
        """Test is_valid returns False when expired."""
        token = AgentRegistrationToken(
            token_hash="a" * 64,
            expires_at=datetime.utcnow() - timedelta(hours=1),
            is_used=False
        )
        assert token.is_valid is False

    def test_is_valid_false_when_used_and_expired(self):
        """Test is_valid returns False when both used and expired."""
        token = AgentRegistrationToken(
            token_hash="a" * 64,
            expires_at=datetime.utcnow() - timedelta(hours=1),
            is_used=True
        )
        assert token.is_valid is False


class TestAgentRegistrationTokenUsage:
    """Tests for token usage tracking."""

    def test_mark_as_used(self):
        """Test mark_as_used sets is_used and used_by_agent_id."""
        token = AgentRegistrationToken(
            token_hash="a" * 64,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_used=False
        )

        token.mark_as_used(agent_id=42)

        assert token.is_used is True
        assert token.used_by_agent_id == 42

    def test_mark_as_used_changes_validity(self):
        """Test that marking as used changes is_valid."""
        token = AgentRegistrationToken(
            token_hash="a" * 64,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_used=False
        )
        assert token.is_valid is True

        token.mark_as_used(agent_id=42)

        assert token.is_valid is False


class TestAgentRegistrationTokenRepresentation:
    """Tests for token string representation."""

    def test_repr(self):
        """Test __repr__ output."""
        token = AgentRegistrationToken(
            token_hash="a" * 64,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_used=False
        )
        token.id = 1
        token.team_id = 1
        repr_str = repr(token)
        assert "AgentRegistrationToken" in repr_str
        assert "is_used=False" in repr_str

    def test_str_valid_token(self):
        """Test __str__ output for valid token."""
        token = AgentRegistrationToken(
            token_hash="a" * 64,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_used=False
        )
        str_str = str(token)
        assert "Registration Token" in str_str
        assert "valid" in str_str

    def test_str_used_token(self):
        """Test __str__ output for used token."""
        token = AgentRegistrationToken(
            token_hash="a" * 64,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_used=True
        )
        str_str = str(token)
        assert "used" in str_str

    def test_str_expired_token(self):
        """Test __str__ output for expired token."""
        token = AgentRegistrationToken(
            token_hash="a" * 64,
            expires_at=datetime.utcnow() - timedelta(hours=1),
            is_used=False
        )
        str_str = str(token)
        assert "expired" in str_str

    def test_str_with_name(self):
        """Test __str__ output includes name if set."""
        token = AgentRegistrationToken(
            token_hash="a" * 64,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_used=False,
            name="My Dev Machine"
        )
        str_str = str(token)
        assert "My Dev Machine" in str_str
