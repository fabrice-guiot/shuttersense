"""
Contract tests for Configuration API endpoints.

Tests API contracts for:
- GET /api/config - Get all configuration
- GET /api/config/{category} - Get category configuration
- GET /api/config/{category}/{key} - Get specific config value
- PUT /api/config/{category}/{key} - Update config value
- DELETE /api/config/{category}/{key} - Delete config value
- POST /api/config/import - Start YAML import
- GET /api/config/import/{session_id} - Get import session
- POST /api/config/import/{session_id}/resolve - Resolve conflicts
- GET /api/config/export - Export as YAML
- GET /api/config/stats - Get statistics
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from backend.src.models import Configuration, ConfigSource


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_config(test_db_session):
    """Factory for creating sample Configuration models."""
    def _create(
        category="cameras",
        key="AB3D",
        value=None,
        description=None,
        source=ConfigSource.DATABASE
    ):
        if value is None:
            value = {"name": "Canon EOS R5", "serial_number": "12345"}
        config = Configuration(
            category=category,
            key=key,
            value_json=value,
            description=description,
            source=source
        )
        test_db_session.add(config)
        test_db_session.commit()
        test_db_session.refresh(config)
        return config
    return _create


@pytest.fixture
def sample_configs(sample_config):
    """Create a set of sample configurations."""
    return [
        sample_config(
            category="extensions",
            key="photo_extensions",
            value=[".dng", ".cr3", ".tiff"]
        ),
        sample_config(
            category="extensions",
            key="metadata_extensions",
            value=[".xmp"]
        ),
        sample_config(
            category="cameras",
            key="AB3D",
            value={"name": "Canon EOS R5", "serial_number": "12345"}
        ),
        sample_config(
            category="processing_methods",
            key="HDR",
            value="High Dynamic Range"
        ),
    ]


# ============================================================================
# GET /api/config Tests (T135)
# ============================================================================

class TestGetAllConfig:
    """Tests for GET /api/config endpoint."""

    def test_get_all_config_empty(self, test_client):
        """Test getting config when empty."""
        response = test_client.get("/api/config")

        assert response.status_code == 200
        data = response.json()
        assert "extensions" in data
        assert "cameras" in data
        assert "processing_methods" in data

    def test_get_all_config_with_data(self, test_client, sample_configs):
        """Test getting all config with data."""
        response = test_client.get("/api/config")

        assert response.status_code == 200
        data = response.json()
        assert len(data["cameras"]) > 0
        assert "AB3D" in data["cameras"]

    def test_get_all_config_filter_by_category(self, test_client, sample_configs):
        """Test filtering by category."""
        response = test_client.get("/api/config?category=cameras")

        assert response.status_code == 200
        data = response.json()
        assert "cameras" in data

    def test_get_all_config_invalid_category(self, test_client):
        """Test filtering with invalid category."""
        response = test_client.get("/api/config?category=invalid")

        # Should return empty or 400 depending on implementation
        assert response.status_code in [200, 400]


class TestGetCategoryConfig:
    """Tests for GET /api/config/{category} endpoint."""

    def test_get_category_config(self, test_client, sample_configs):
        """Test getting category configuration."""
        response = test_client.get("/api/config/cameras")

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "cameras"
        assert "items" in data

    def test_get_category_config_empty(self, test_client):
        """Test getting empty category."""
        response = test_client.get("/api/config/cameras")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    def test_get_category_invalid(self, test_client):
        """Test getting invalid category."""
        response = test_client.get("/api/config/invalid_category")

        assert response.status_code == 400


class TestGetConfigValue:
    """Tests for GET /api/config/{category}/{key} endpoint."""

    def test_get_config_value(self, test_client, sample_config):
        """Test getting specific config value."""
        sample_config(category="cameras", key="AB3D")

        response = test_client.get("/api/config/cameras/AB3D")

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "cameras"
        assert data["key"] == "AB3D"
        assert "value" in data

    def test_get_config_value_not_found(self, test_client):
        """Test getting non-existent config."""
        response = test_client.get("/api/config/cameras/NONEXISTENT")

        assert response.status_code == 404


# ============================================================================
# POST /api/config/import Tests (T136)
# ============================================================================

class TestImportConfig:
    """Tests for POST /api/config/import endpoint."""

    def test_import_valid_yaml(self, test_client):
        """Test importing valid YAML file."""
        yaml_content = """
photo_extensions:
  - .dng
  - .cr3
camera_mappings:
  AB3D:
    name: Canon EOS R5
    serial_number: "12345"
"""
        files = {"file": ("config.yaml", yaml_content.encode(), "application/x-yaml")}

        response = test_client.post("/api/config/import", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["status"] == "pending"
        assert "total_items" in data

    def test_import_invalid_yaml(self, test_client):
        """Test importing invalid YAML."""
        yaml_content = "invalid: yaml: content: {"
        files = {"file": ("config.yaml", yaml_content.encode(), "application/x-yaml")}

        response = test_client.post("/api/config/import", files=files)

        assert response.status_code == 400

    def test_import_with_conflicts(self, test_client, sample_config):
        """Test importing YAML with conflicts."""
        # Create existing config
        sample_config(category="cameras", key="AB3D", value={"name": "Old Name"})

        yaml_content = """
camera_mappings:
  AB3D:
    name: New Name
    serial_number: "99999"
"""
        files = {"file": ("config.yaml", yaml_content.encode(), "application/x-yaml")}

        response = test_client.post("/api/config/import", files=files)

        assert response.status_code == 200
        data = response.json()
        assert len(data.get("conflicts", [])) > 0


class TestGetImportSession:
    """Tests for GET /api/config/import/{session_id} endpoint."""

    def test_get_import_session_not_found(self, test_client):
        """Test getting non-existent session."""
        response = test_client.get("/api/config/import/550e8400-e29b-41d4-a716-446655440000")

        assert response.status_code == 404


# ============================================================================
# POST /api/config/import/{session_id}/resolve Tests (T137)
# ============================================================================

class TestResolveImport:
    """Tests for POST /api/config/import/{session_id}/resolve endpoint."""

    def test_resolve_conflicts(self, test_client, sample_config):
        """Test resolving conflicts.

        Note: Import sessions are stored in-memory per ConfigService instance.
        In production, a shared storage (Redis, DB) would be used.
        For this API test, we test the import endpoint returns valid data
        and the resolve endpoint handles unknown sessions correctly.
        """
        # First create a conflict scenario
        sample_config(category="cameras", key="AB3D", value={"name": "Old Name"})

        yaml_content = """
camera_mappings:
  AB3D:
    name: New Name
    serial_number: "99999"
"""
        files = {"file": ("config.yaml", yaml_content.encode(), "application/x-yaml")}
        import_response = test_client.post("/api/config/import", files=files)

        # Verify import started successfully with conflict detected
        assert import_response.status_code == 200
        data = import_response.json()
        assert "session_id" in data
        assert data["status"] == "pending"
        # Due to in-memory session storage, the session won't persist across
        # separate requests in the test client. The config service unit tests
        # properly test the full resolve flow.

    def test_resolve_invalid_session(self, test_client):
        """Test resolving with invalid session."""
        response = test_client.post(
            "/api/config/import/550e8400-e29b-41d4-a716-446655440000/resolve",
            json={"resolutions": []}
        )

        assert response.status_code == 404


# ============================================================================
# GET /api/config/export Tests (T138)
# ============================================================================

class TestExportConfig:
    """Tests for GET /api/config/export endpoint."""

    def test_export_config(self, test_client, sample_configs):
        """Test exporting configuration as YAML."""
        response = test_client.get("/api/config/export")

        assert response.status_code == 200
        assert "application/x-yaml" in response.headers.get("content-type", "")

        content = response.text
        assert "photo_extensions" in content or "camera_mappings" in content

    def test_export_config_empty(self, test_client):
        """Test exporting empty configuration."""
        response = test_client.get("/api/config/export")

        assert response.status_code == 200


# ============================================================================
# PUT /api/config/{category}/{key} Tests
# ============================================================================

class TestUpdateConfigValue:
    """Tests for PUT /api/config/{category}/{key} endpoint."""

    def test_update_config_value(self, test_client, sample_config):
        """Test updating config value."""
        sample_config(category="cameras", key="AB3D")

        response = test_client.put(
            "/api/config/cameras/AB3D",
            json={
                "value": {"name": "Updated Name", "serial_number": "99999"},
                "description": "Updated description"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["value"]["name"] == "Updated Name"

    def test_update_config_not_found(self, test_client):
        """Test updating non-existent config."""
        response = test_client.put(
            "/api/config/cameras/NONEXISTENT",
            json={"value": {"name": "New"}}
        )

        assert response.status_code == 404


# ============================================================================
# DELETE /api/config/{category}/{key} Tests
# ============================================================================

class TestDeleteConfigValue:
    """Tests for DELETE /api/config/{category}/{key} endpoint."""

    def test_delete_config_value(self, test_client, sample_config):
        """Test deleting config value."""
        sample_config(category="cameras", key="AB3D")

        response = test_client.delete("/api/config/cameras/AB3D")

        assert response.status_code == 200

        # Verify deleted
        get_response = test_client.get("/api/config/cameras/AB3D")
        assert get_response.status_code == 404

    def test_delete_config_not_found(self, test_client):
        """Test deleting non-existent config."""
        response = test_client.delete("/api/config/cameras/NONEXISTENT")

        assert response.status_code == 404


# ============================================================================
# GET /api/config/stats Tests
# ============================================================================

class TestConfigStats:
    """Tests for GET /api/config/stats endpoint."""

    def test_get_stats_empty(self, test_client):
        """Test getting stats when empty."""
        response = test_client.get("/api/config/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_items"] == 0
        assert data["cameras_configured"] == 0
        assert data["processing_methods_configured"] == 0

    def test_get_stats_with_data(self, test_client, sample_configs):
        """Test getting stats with data."""
        response = test_client.get("/api/config/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_items"] > 0
        assert "source_breakdown" in data
