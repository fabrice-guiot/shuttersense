"""
Unit tests for agent configuration module.

Tests configuration loading, saving, defaults, and validation.

Issue #90 - Distributed Agent Architecture (Phase 3)
Task: T035
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


class TestAgentConfig:
    """Tests for AgentConfig class."""

    def test_default_config_values(self, temp_config_dir):
        """Test that default configuration values are set correctly."""
        from agent.src.config import AgentConfig

        config = AgentConfig(config_dir=temp_config_dir)

        assert config.server_url == ""
        assert config.api_key == ""
        assert config.agent_guid == ""
        assert config.agent_name == ""
        assert config.heartbeat_interval_seconds == 30
        assert config.poll_interval_seconds == 5
        assert config.log_level == "INFO"

    def test_load_config_from_file(self, agent_config_file, agent_config):
        """Test loading configuration from a YAML file."""
        from agent.src.config import AgentConfig

        config = AgentConfig(config_path=agent_config_file)

        assert config.server_url == agent_config["server_url"]
        assert config.api_key == agent_config["api_key"]
        assert config.agent_name == agent_config["agent_name"]
        assert config.heartbeat_interval_seconds == agent_config["heartbeat_interval_seconds"]
        assert config.poll_interval_seconds == agent_config["poll_interval_seconds"]
        assert config.log_level == agent_config["log_level"]

    def test_save_config_to_file(self, temp_config_dir):
        """Test saving configuration to a YAML file."""
        from agent.src.config import AgentConfig

        config_path = temp_config_dir / "agent-config.yaml"
        config = AgentConfig(config_path=config_path)
        config.server_url = "http://example.com:8000"
        config.api_key = "agt_key_test123"
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        config.agent_name = "Test Agent"
        config.save()

        # Verify saved file
        with open(config_path) as f:
            saved = yaml.safe_load(f)

        assert saved["server_url"] == "http://example.com:8000"
        assert saved["api_key"] == "agt_key_test123"
        assert saved["agent_guid"] == "agt_01hgw2bbg0000000000000001"
        assert saved["agent_name"] == "Test Agent"

    def test_load_config_from_environment(self, temp_config_dir, monkeypatch):
        """Test that environment variables override file configuration."""
        from agent.src.config import AgentConfig

        monkeypatch.setenv("SHUTTERSENSE_SERVER_URL", "http://env-server:8000")
        monkeypatch.setenv("SHUTTERSENSE_API_KEY", "agt_key_from_env")
        monkeypatch.setenv("SHUTTERSENSE_LOG_LEVEL", "DEBUG")

        config = AgentConfig(config_dir=temp_config_dir)

        assert config.server_url == "http://env-server:8000"
        assert config.api_key == "agt_key_from_env"
        assert config.log_level == "DEBUG"

    def test_config_file_not_found_uses_defaults(self, temp_config_dir):
        """Test that missing config file uses default values."""
        from agent.src.config import AgentConfig

        nonexistent_path = temp_config_dir / "nonexistent.yaml"
        config = AgentConfig(config_path=nonexistent_path)

        # Should use defaults without raising error
        assert config.server_url == ""
        assert config.heartbeat_interval_seconds == 30

    def test_is_registered_property(self, temp_config_dir):
        """Test the is_registered property."""
        from agent.src.config import AgentConfig

        config = AgentConfig(config_dir=temp_config_dir)

        # Not registered without api_key and agent_guid
        assert config.is_registered is False

        # Still not registered with only api_key
        config.api_key = "agt_key_test123"
        assert config.is_registered is False

        # Registered with both
        config.agent_guid = "agt_01hgw2bbg0000000000000001"
        assert config.is_registered is True

    def test_is_configured_property(self, temp_config_dir):
        """Test the is_configured property."""
        from agent.src.config import AgentConfig

        config = AgentConfig(config_dir=temp_config_dir)

        # Not configured without server_url
        assert config.is_configured is False

        # Configured with server_url
        config.server_url = "http://localhost:8000"
        assert config.is_configured is True

    def test_default_config_dir(self, clean_environment, monkeypatch):
        """Test that default config directory is platform-appropriate."""
        from agent.src.config import get_default_config_dir

        # Should return a path in user's config directory
        config_dir = get_default_config_dir()
        assert isinstance(config_dir, Path)
        assert "shuttersense" in str(config_dir).lower()


class TestConfigValidation:
    """Tests for configuration validation."""

    def test_invalid_server_url_format(self, temp_config_dir):
        """Test validation of server URL format."""
        from agent.src.config import AgentConfig, ConfigValidationError

        config = AgentConfig(config_dir=temp_config_dir)
        config.server_url = "not-a-valid-url"

        with pytest.raises(ConfigValidationError) as exc_info:
            config.validate()

        assert "server_url" in str(exc_info.value).lower()

    def test_valid_server_url_formats(self, temp_config_dir):
        """Test that valid server URLs pass validation."""
        from agent.src.config import AgentConfig

        config = AgentConfig(config_dir=temp_config_dir)

        # Valid URLs should not raise
        for url in ["http://localhost:8000", "https://api.shuttersense.ai", "http://192.168.1.100:8080"]:
            config.server_url = url
            config.validate()  # Should not raise

    def test_invalid_heartbeat_interval(self, temp_config_dir):
        """Test validation of heartbeat interval."""
        from agent.src.config import AgentConfig, ConfigValidationError

        config = AgentConfig(config_dir=temp_config_dir)
        config.server_url = "http://localhost:8000"
        config.heartbeat_interval_seconds = 0

        with pytest.raises(ConfigValidationError) as exc_info:
            config.validate()

        assert "heartbeat" in str(exc_info.value).lower()

    def test_invalid_poll_interval(self, temp_config_dir):
        """Test validation of poll interval."""
        from agent.src.config import AgentConfig, ConfigValidationError

        config = AgentConfig(config_dir=temp_config_dir)
        config.server_url = "http://localhost:8000"
        config.poll_interval_seconds = -1

        with pytest.raises(ConfigValidationError) as exc_info:
            config.validate()

        assert "poll" in str(exc_info.value).lower()


class TestConfigPersistence:
    """Tests for configuration persistence."""

    def test_update_registration_info(self, temp_config_dir):
        """Test updating registration information and saving."""
        from agent.src.config import AgentConfig

        config_path = temp_config_dir / "agent-config.yaml"
        config = AgentConfig(config_path=config_path)
        config.server_url = "http://localhost:8000"

        # Simulate registration
        config.update_registration(
            agent_guid="agt_01hgw2bbg0000000000000001",
            api_key="agt_key_secret123",
            agent_name="My Agent"
        )

        # Reload and verify
        config2 = AgentConfig(config_path=config_path)
        assert config2.agent_guid == "agt_01hgw2bbg0000000000000001"
        assert config2.api_key == "agt_key_secret123"
        assert config2.agent_name == "My Agent"
        assert config2.is_registered is True

    def test_clear_registration(self, temp_config_dir):
        """Test clearing registration information."""
        from agent.src.config import AgentConfig

        config_path = temp_config_dir / "agent-config.yaml"
        config = AgentConfig(config_path=config_path)
        config.server_url = "http://localhost:8000"
        config.update_registration(
            agent_guid="agt_01hgw2bbg0000000000000001",
            api_key="agt_key_secret123",
            agent_name="My Agent"
        )

        # Clear registration
        config.clear_registration()
        config.save()

        # Reload and verify
        config2 = AgentConfig(config_path=config_path)
        assert config2.agent_guid == ""
        assert config2.api_key == ""
        assert config2.is_registered is False
