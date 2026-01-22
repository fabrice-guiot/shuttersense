"""
Unit tests for ConfigService.

Tests CRUD operations, YAML import/export, conflict detection, and statistics.
"""

import pytest
import yaml
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from backend.src.models import Configuration, ConfigSource
from backend.src.models.team import Team
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError as ServiceValidationError


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def test_team(test_db_session):
    """Create a test team for tenant isolation."""
    team = Team(
        name="Test Team",
        slug="test-team",
        is_active=True
    )
    test_db_session.add(team)
    test_db_session.commit()
    test_db_session.refresh(team)
    return team


@pytest.fixture
def config_service(test_db_session):
    """Create a ConfigService instance for testing."""
    from backend.src.services.config_service import ConfigService
    return ConfigService(test_db_session)


@pytest.fixture
def sample_config(test_db_session, test_team):
    """Factory for creating sample Configuration models."""
    def _create(
        category="cameras",
        key="AB3D",
        value=None,
        description=None,
        source=ConfigSource.DATABASE,
        team_id=None
    ):
        if value is None:
            value = {"name": "Canon EOS R5", "serial_number": "12345"}
        # Use provided team_id or default to test_team
        actual_team_id = team_id if team_id is not None else test_team.id
        config = Configuration(
            category=category,
            key=key,
            value_json=value,
            description=description,
            source=source,
            team_id=actual_team_id
        )
        test_db_session.add(config)
        test_db_session.commit()
        test_db_session.refresh(config)
        return config
    return _create


# ============================================================================
# CRUD Tests (T139)
# ============================================================================

class TestConfigServiceCRUD:
    """Tests for CRUD operations."""

    def test_create_config(self, config_service, test_team):
        """Test creating a new configuration item."""
        result = config_service.create(
            category="cameras",
            key="AB3D",
            value={"name": "Canon EOS R5", "serial_number": "12345"},
            team_id=test_team.id,
            description="Primary camera"
        )

        assert result.id is not None
        assert result.category == "cameras"
        assert result.key == "AB3D"
        assert result.value["name"] == "Canon EOS R5"
        assert result.source == "database"

    def test_create_config_duplicate_key(self, config_service, sample_config, test_team):
        """Test error when creating duplicate category/key."""
        sample_config(category="cameras", key="AB3D")

        with pytest.raises(ConflictError) as exc_info:
            config_service.create(
                category="cameras",
                key="AB3D",
                value={"name": "Different Camera"},
                team_id=test_team.id
            )
        assert "already exists" in str(exc_info.value).lower()

    def test_create_config_same_key_different_category(self, config_service, sample_config, test_team):
        """Test same key in different categories is allowed."""
        sample_config(category="cameras", key="test_key")

        result = config_service.create(
            category="processing_methods",
            key="test_key",
            value="Test Method",
            team_id=test_team.id
        )

        assert result.id is not None
        assert result.category == "processing_methods"

    def test_get_config(self, config_service, sample_config, test_team):
        """Test getting a config by category and key."""
        sample_config(category="cameras", key="AB3D")

        result = config_service.get("cameras", "AB3D", team_id=test_team.id)

        assert result is not None
        assert result.category == "cameras"
        assert result.key == "AB3D"

    def test_get_config_not_found(self, config_service, test_team):
        """Test getting non-existent config."""
        result = config_service.get("cameras", "NONEXISTENT", team_id=test_team.id)

        assert result is None

    def test_get_by_id(self, config_service, sample_config, test_team):
        """Test getting config by ID."""
        config = sample_config(category="cameras", key="AB3D")

        result = config_service.get_by_id(config.id, team_id=test_team.id)

        assert result is not None
        assert result.id == config.id

    def test_get_by_id_not_found(self, config_service, test_team):
        """Test getting config by non-existent ID."""
        with pytest.raises(NotFoundError):
            config_service.get_by_id(99999, team_id=test_team.id)

    def test_list_configs(self, config_service, sample_config, test_team):
        """Test listing all configurations."""
        sample_config(category="cameras", key="AB3D")
        sample_config(category="cameras", key="CD5E")
        sample_config(category="extensions", key="photo_extensions", value=[".dng"])

        result = config_service.list(team_id=test_team.id)

        assert len(result) >= 3

    def test_list_configs_filter_by_category(self, config_service, sample_config, test_team):
        """Test listing configurations filtered by category."""
        sample_config(category="cameras", key="AB3D")
        sample_config(category="cameras", key="CD5E")
        sample_config(category="extensions", key="photo_extensions", value=[".dng"])

        result = config_service.list(team_id=test_team.id, category_filter="cameras")

        assert all(r.category == "cameras" for r in result)

    def test_update_config(self, config_service, sample_config, test_team):
        """Test updating a configuration."""
        config = sample_config(category="cameras", key="AB3D")

        result = config_service.update(
            category="cameras",
            key="AB3D",
            team_id=test_team.id,
            value={"name": "Updated Name", "serial_number": "99999"},
            description="Updated description"
        )

        assert result.value["name"] == "Updated Name"
        assert result.description == "Updated description"

    def test_update_config_not_found(self, config_service, test_team):
        """Test updating non-existent config."""
        with pytest.raises(NotFoundError):
            config_service.update(
                category="cameras",
                key="NONEXISTENT",
                team_id=test_team.id,
                value={"name": "New"}
            )

    def test_delete_config(self, config_service, sample_config, test_db_session, test_team):
        """Test deleting a configuration."""
        config = sample_config(category="cameras", key="AB3D")
        config_id = config.id

        result = config_service.delete("cameras", "AB3D", team_id=test_team.id)

        assert result == config_id

        # Verify deleted
        deleted = test_db_session.query(Configuration).filter(
            Configuration.id == config_id
        ).first()
        assert deleted is None

    def test_delete_config_not_found(self, config_service, test_team):
        """Test deleting non-existent config."""
        with pytest.raises(NotFoundError):
            config_service.delete("cameras", "NONEXISTENT", team_id=test_team.id)


# ============================================================================
# Conflict Detection Tests (T140)
# ============================================================================

class TestConfigServiceConflictDetection:
    """Tests for conflict detection during import."""

    def test_detect_no_conflicts(self, config_service, test_team):
        """Test no conflicts when importing new items."""
        yaml_data = {
            "photo_extensions": [".dng", ".cr3"],
            "camera_mappings": {
                "AB3D": {"name": "Canon EOS R5"}
            }
        }

        conflicts = config_service.detect_conflicts(yaml_data, team_id=test_team.id)

        assert len(conflicts) == 0

    def test_detect_conflicts(self, config_service, sample_config, test_team):
        """Test detecting conflicts with existing data."""
        sample_config(category="cameras", key="AB3D", value={"name": "Old Name"})

        yaml_data = {
            "camera_mappings": {
                "AB3D": {"name": "New Name"}
            }
        }

        conflicts = config_service.detect_conflicts(yaml_data, team_id=test_team.id)

        assert len(conflicts) == 1
        assert conflicts[0]["category"] == "cameras"
        assert conflicts[0]["key"] == "AB3D"
        assert conflicts[0]["database_value"]["name"] == "Old Name"
        assert conflicts[0]["yaml_value"]["name"] == "New Name"

    def test_detect_conflicts_same_value(self, config_service, sample_config, test_team):
        """Test no conflict when values are equal."""
        sample_config(
            category="cameras",
            key="AB3D",
            value={"name": "Same Name", "serial_number": "12345"}
        )

        yaml_data = {
            "camera_mappings": {
                "AB3D": {"name": "Same Name", "serial_number": "12345"}
            }
        }

        conflicts = config_service.detect_conflicts(yaml_data, team_id=test_team.id)

        # Same value should not create a conflict
        assert len(conflicts) == 0


# ============================================================================
# Import Session Tests (T141)
# ============================================================================

class TestConfigServiceImportSession:
    """Tests for import session management."""

    def test_start_import_session(self, config_service, test_team):
        """Test starting an import session."""
        yaml_content = """
photo_extensions:
  - .dng
  - .cr3
camera_mappings:
  AB3D:
    name: Canon EOS R5
"""
        result = config_service.start_import(yaml_content, team_id=test_team.id, filename="config.yaml")

        assert result["session_id"] is not None
        assert result["status"] == "pending"
        assert result["file_name"] == "config.yaml"
        assert "expires_at" in result

    def test_start_import_invalid_yaml(self, config_service, test_team):
        """Test error when importing invalid YAML."""
        yaml_content = "invalid: yaml: content: {"

        with pytest.raises(ServiceValidationError) as exc_info:
            config_service.start_import(yaml_content, team_id=test_team.id)
        assert "yaml" in str(exc_info.value).lower()

    def test_get_import_session(self, config_service, test_team):
        """Test getting import session by ID."""
        yaml_content = """
photo_extensions:
  - .dng
"""
        session = config_service.start_import(yaml_content, team_id=test_team.id)
        session_id = session["session_id"]

        result = config_service.get_import_session(session_id)

        assert result is not None
        assert result["session_id"] == session_id

    def test_get_import_session_not_found(self, config_service):
        """Test getting non-existent session."""
        with pytest.raises(NotFoundError):
            config_service.get_import_session("nonexistent-session-id")

    def test_apply_import(self, config_service, test_db_session, test_team):
        """Test applying import without conflicts."""
        yaml_content = """
photo_extensions:
  - .dng
  - .cr3
camera_mappings:
  AB3D:
    name: Canon EOS R5
    serial_number: "12345"
processing_methods:
  HDR: High Dynamic Range
"""
        session = config_service.start_import(yaml_content, team_id=test_team.id)
        session_id = session["session_id"]

        result = config_service.apply_import(session_id, [])

        assert result["success"] is True
        assert result["items_imported"] > 0

        # Verify items were created
        camera = config_service.get("cameras", "AB3D", team_id=test_team.id)
        assert camera is not None
        assert camera.value["name"] == "Canon EOS R5"

    def test_apply_import_with_resolutions(self, config_service, sample_config, test_team):
        """Test applying import with conflict resolutions."""
        sample_config(category="cameras", key="AB3D", value={"name": "Old Name"})

        yaml_content = """
camera_mappings:
  AB3D:
    name: New Name
"""
        session = config_service.start_import(yaml_content, team_id=test_team.id)
        session_id = session["session_id"]

        # Resolve to use YAML value
        resolutions = [{"category": "cameras", "key": "AB3D", "use_yaml": True}]
        result = config_service.apply_import(session_id, resolutions)

        assert result["success"] is True

        # Verify YAML value was applied
        camera = config_service.get("cameras", "AB3D", team_id=test_team.id)
        assert camera.value["name"] == "New Name"

    def test_cancel_import(self, config_service, test_team):
        """Test canceling an import session."""
        yaml_content = """
photo_extensions:
  - .dng
"""
        session = config_service.start_import(yaml_content, team_id=test_team.id)
        session_id = session["session_id"]

        config_service.cancel_import(session_id)

        with pytest.raises(NotFoundError):
            config_service.get_import_session(session_id)


# ============================================================================
# YAML Export Tests (T142)
# ============================================================================

class TestConfigServiceExport:
    """Tests for YAML export."""

    def test_export_to_yaml(self, config_service, sample_config, test_team):
        """Test exporting config to YAML."""
        sample_config(
            category="extensions",
            key="photo_extensions",
            value=[".dng", ".cr3"]
        )
        sample_config(
            category="cameras",
            key="AB3D",
            value={"name": "Canon EOS R5", "serial_number": "12345"}
        )
        sample_config(
            category="processing_methods",
            key="HDR",
            value="High Dynamic Range"
        )

        result = config_service.export_to_yaml(team_id=test_team.id)

        # Parse the YAML to verify structure
        parsed = yaml.safe_load(result)

        assert "photo_extensions" in parsed or "extensions" in parsed
        assert "camera_mappings" in parsed or "cameras" in parsed
        assert "processing_methods" in parsed

    def test_export_empty_to_yaml(self, config_service, test_team):
        """Test exporting empty config."""
        result = config_service.export_to_yaml(team_id=test_team.id)

        # Should return valid YAML even if empty
        assert result is not None
        parsed = yaml.safe_load(result)
        assert isinstance(parsed, dict)


# ============================================================================
# Statistics Tests
# ============================================================================

class TestConfigServiceStats:
    """Tests for statistics."""

    def test_get_stats_empty(self, config_service, test_team):
        """Test stats with no configuration."""
        result = config_service.get_stats(team_id=test_team.id)

        assert result.total_items == 0
        assert result.cameras_configured == 0
        assert result.processing_methods_configured == 0
        assert result.last_import is None

    def test_get_stats_with_data(self, config_service, sample_config, test_team):
        """Test stats with configuration data."""
        sample_config(category="cameras", key="AB3D")
        sample_config(category="cameras", key="CD5E")
        sample_config(
            category="processing_methods",
            key="HDR",
            value="High Dynamic Range"
        )
        sample_config(
            category="extensions",
            key="photo_extensions",
            value=[".dng"],
            source=ConfigSource.YAML_IMPORT
        )

        result = config_service.get_stats(team_id=test_team.id)

        assert result.total_items >= 4
        assert result.cameras_configured == 2
        assert result.processing_methods_configured == 1
        assert "database" in result.source_breakdown
        assert "yaml_import" in result.source_breakdown


# ============================================================================
# Get All Config Tests
# ============================================================================

class TestConfigServiceGetAll:
    """Tests for getting all configuration."""

    def test_get_all_config(self, config_service, sample_config, test_team):
        """Test getting all configuration organized by category."""
        sample_config(
            category="extensions",
            key="photo_extensions",
            value=[".dng", ".cr3"]
        )
        sample_config(
            category="cameras",
            key="AB3D",
            value={"name": "Canon EOS R5"}
        )
        sample_config(
            category="processing_methods",
            key="HDR",
            value="High Dynamic Range"
        )

        result = config_service.get_all(team_id=test_team.id)

        assert "extensions" in result
        assert "cameras" in result
        assert "processing_methods" in result
        assert "photo_extensions" in result["extensions"]
        assert "AB3D" in result["cameras"]
        assert "HDR" in result["processing_methods"]

    def test_get_all_config_empty(self, config_service, test_team):
        """Test getting all config when empty."""
        result = config_service.get_all(team_id=test_team.id)

        assert result == {
            "extensions": {},
            "cameras": {},
            "processing_methods": {},
            "event_statuses": {},
            "collection_ttl": {}
        }


# ============================================================================
# Category Validation Tests
# ============================================================================

class TestConfigServiceCategoryValidation:
    """Tests for category validation."""

    def test_valid_categories(self, config_service, test_team):
        """Test that valid categories are accepted."""
        valid_categories = ["extensions", "cameras", "processing_methods", "event_statuses"]

        for category in valid_categories:
            result = config_service.create(
                category=category,
                key=f"test_{category}",
                value="test value",
                team_id=test_team.id
            )
            assert result.category == category

    def test_invalid_category(self, config_service, test_team):
        """Test that invalid category raises error."""
        with pytest.raises(ServiceValidationError) as exc_info:
            config_service.create(
                category="invalid_category",
                key="test",
                value="test",
                team_id=test_team.id
            )
        assert "category" in str(exc_info.value).lower()
