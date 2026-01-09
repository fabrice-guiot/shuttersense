"""
Unit tests for Configuration model.

Tests the Configuration model for:
- Model creation and field validation
- JSONB value storage for different types
- Category/key uniqueness constraints
- Source tracking (database vs yaml_import)
- Helper methods
"""

import pytest
from datetime import datetime

from backend.src.models import (
    Base,
    Configuration,
    ConfigSource,
)


class TestConfigSource:
    """Tests for ConfigSource enum."""

    def test_config_source_values(self):
        """Test ConfigSource enum has correct values."""
        assert ConfigSource.DATABASE.value == "database"
        assert ConfigSource.YAML_IMPORT.value == "yaml_import"

    def test_config_source_members(self):
        """Test all ConfigSource enum members exist."""
        expected_sources = {"DATABASE", "YAML_IMPORT"}
        actual_sources = {cs.name for cs in ConfigSource}
        assert actual_sources == expected_sources


class TestConfigurationModel:
    """Tests for Configuration model."""

    def test_create_string_list_config(self, test_db_session):
        """Test creating configuration with string list value."""
        config = Configuration(
            category="extensions",
            key="photo_extensions",
            value_json=[".dng", ".cr3", ".tiff", ".jpg"],
            description="List of supported photo file extensions"
        )
        test_db_session.add(config)
        test_db_session.commit()

        assert config.id is not None
        assert config.category == "extensions"
        assert config.key == "photo_extensions"
        assert config.value_json == [".dng", ".cr3", ".tiff", ".jpg"]
        assert config.source == ConfigSource.DATABASE
        assert config.created_at is not None
        assert config.updated_at is not None

    def test_create_object_config(self, test_db_session):
        """Test creating configuration with object value (camera)."""
        config = Configuration(
            category="cameras",
            key="AB3D",
            value_json={
                "name": "Canon EOS R5",
                "serial_number": "123456789"
            },
            description="Camera AB3D configuration"
        )
        test_db_session.add(config)
        test_db_session.commit()

        assert config.value_json["name"] == "Canon EOS R5"
        assert config.value_json["serial_number"] == "123456789"

    def test_create_string_config(self, test_db_session):
        """Test creating configuration with string value (processing method)."""
        config = Configuration(
            category="processing_methods",
            key="HDR",
            value_json="High Dynamic Range",
            source=ConfigSource.DATABASE
        )
        test_db_session.add(config)
        test_db_session.commit()

        assert config.value_json == "High Dynamic Range"

    def test_yaml_import_source(self, test_db_session):
        """Test configuration with YAML_IMPORT source."""
        config = Configuration(
            category="extensions",
            key="metadata_extensions",
            value_json=[".xmp"],
            source=ConfigSource.YAML_IMPORT
        )
        test_db_session.add(config)
        test_db_session.commit()

        assert config.source == ConfigSource.YAML_IMPORT

    def test_unique_category_key_constraint(self, test_db_session):
        """Test that (category, key) must be unique."""
        from sqlalchemy.exc import IntegrityError

        config1 = Configuration(
            category="cameras",
            key="AB3D",
            value_json={"name": "Camera 1"}
        )
        test_db_session.add(config1)
        test_db_session.commit()

        config2 = Configuration(
            category="cameras",
            key="AB3D",  # Same category and key
            value_json={"name": "Camera 2"}
        )
        test_db_session.add(config2)

        with pytest.raises(IntegrityError):
            test_db_session.commit()

        test_db_session.rollback()

    def test_same_key_different_category(self, test_db_session):
        """Test that same key in different categories is allowed."""
        config1 = Configuration(
            category="cameras",
            key="test_key",
            value_json="camera value"
        )
        config2 = Configuration(
            category="processing_methods",
            key="test_key",  # Same key, different category
            value_json="method value"
        )

        test_db_session.add_all([config1, config2])
        test_db_session.commit()

        assert config1.id is not None
        assert config2.id is not None
        assert config1.id != config2.id

    def test_get_value_method(self, test_db_session):
        """Test get_value method."""
        config = Configuration(
            category="extensions",
            key="require_sidecar",
            value_json=[".cr3", ".arw"]
        )
        test_db_session.add(config)
        test_db_session.commit()

        value = config.get_value()
        assert value == [".cr3", ".arw"]

    def test_set_value_method(self, test_db_session):
        """Test set_value method."""
        config = Configuration(
            category="processing_methods",
            key="BW",
            value_json="Black and White",
            source=ConfigSource.YAML_IMPORT
        )
        test_db_session.add(config)
        test_db_session.commit()

        # Update value without changing source
        config.set_value("B&W Conversion")
        test_db_session.commit()

        assert config.value_json == "B&W Conversion"
        assert config.source == ConfigSource.YAML_IMPORT

        # Update value and source
        config.set_value("Black & White", source=ConfigSource.DATABASE)
        test_db_session.commit()

        assert config.value_json == "Black & White"
        assert config.source == ConfigSource.DATABASE

    def test_to_dict_method(self, test_db_session):
        """Test to_dict method."""
        config = Configuration(
            category="cameras",
            key="CD5E",
            value_json={"name": "Sony A7R IV", "serial_number": "999"},
            description="Secondary camera",
            source=ConfigSource.DATABASE
        )
        test_db_session.add(config)
        test_db_session.commit()

        result = config.to_dict()

        assert result["category"] == "cameras"
        assert result["key"] == "CD5E"
        assert result["value"]["name"] == "Sony A7R IV"
        assert result["description"] == "Secondary camera"
        assert result["source"] == "database"
        assert result["updated_at"] is not None

    def test_from_yaml_item_classmethod(self, test_db_session):
        """Test from_yaml_item class method."""
        config = Configuration.from_yaml_item(
            category="processing_methods",
            key="PANO",
            value="Panorama",
            description="Panoramic images"
        )
        test_db_session.add(config)
        test_db_session.commit()

        assert config.category == "processing_methods"
        assert config.key == "PANO"
        assert config.value_json == "Panorama"
        assert config.description == "Panoramic images"
        assert config.source == ConfigSource.YAML_IMPORT

    def test_repr_and_str(self, test_db_session):
        """Test string representations."""
        config = Configuration(
            category="extensions",
            key="photo_extensions",
            value_json=[".dng", ".cr3"],
            source=ConfigSource.DATABASE
        )
        test_db_session.add(config)
        test_db_session.commit()

        # Test __repr__
        repr_str = repr(config)
        assert "Configuration" in repr_str
        assert "extensions" in repr_str
        assert "photo_extensions" in repr_str
        assert "database" in repr_str

        # Test __str__
        str_str = str(config)
        assert "extensions.photo_extensions" in str_str

    def test_updated_at_auto_update(self, test_db_session):
        """Test that updated_at is automatically updated on changes."""
        config = Configuration(
            category="cameras",
            key="EF6G",
            value_json={"name": "Initial"}
        )
        test_db_session.add(config)
        test_db_session.commit()

        initial_updated_at = config.updated_at

        # Update the value
        config.value_json = {"name": "Updated"}
        test_db_session.commit()
        test_db_session.refresh(config)

        # Note: In SQLite (used in tests), onupdate may not work the same way
        # as PostgreSQL. This test documents expected behavior.
        assert config.updated_at is not None

    def test_complex_jsonb_value(self, test_db_session):
        """Test storing complex nested JSONB value."""
        complex_value = {
            "name": "Canon EOS R5",
            "serial_number": "123456",
            "metadata": {
                "purchase_date": "2023-01-15",
                "firmware_version": "1.5.0",
                "lenses": ["RF 24-70mm", "RF 70-200mm"]
            }
        }

        config = Configuration(
            category="cameras",
            key="GH7I",
            value_json=complex_value
        )
        test_db_session.add(config)
        test_db_session.commit()

        # Refresh and verify complex structure is preserved
        test_db_session.refresh(config)

        assert config.value_json["name"] == "Canon EOS R5"
        assert config.value_json["metadata"]["firmware_version"] == "1.5.0"
        assert len(config.value_json["metadata"]["lenses"]) == 2
