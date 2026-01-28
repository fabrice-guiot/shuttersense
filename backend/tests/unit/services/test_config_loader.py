"""
Unit tests for ConfigLoader protocol and implementations.

Tests the ConfigLoader protocol interface and concrete implementations:
- DictConfigLoader (dict-based)
- DatabaseConfigLoader (database-backed)

Issue #90 - Distributed Agent Architecture (Phase 5)
Task: T071
"""

import pytest
from typing import List, Dict, Any

from backend.src.services.config_loader import (
    ConfigLoader,
    BaseConfigLoader,
    DictConfigLoader,
    DatabaseConfigLoader,
)


class TestConfigLoaderProtocol:
    """Tests for ConfigLoader protocol compliance."""

    def test_dict_config_loader_is_config_loader(self):
        """DictConfigLoader implements ConfigLoader protocol."""
        loader = DictConfigLoader({})
        assert isinstance(loader, ConfigLoader)

    def test_database_config_loader_is_config_loader(self, test_db_session, test_team):
        """DatabaseConfigLoader implements ConfigLoader protocol."""
        loader = DatabaseConfigLoader(test_team.id, test_db_session)
        assert isinstance(loader, ConfigLoader)

    def test_protocol_has_required_properties(self):
        """ConfigLoader protocol defines all required properties."""
        # Verify protocol has the expected attributes
        assert hasattr(ConfigLoader, 'photo_extensions')
        assert hasattr(ConfigLoader, 'metadata_extensions')
        assert hasattr(ConfigLoader, 'camera_mappings')
        assert hasattr(ConfigLoader, 'processing_methods')
        assert hasattr(ConfigLoader, 'require_sidecar')


class TestDictConfigLoader:
    """Tests for DictConfigLoader implementation."""

    def test_photo_extensions(self):
        """Returns photo extensions from config dict."""
        config = {"photo_extensions": [".dng", ".cr3", ".nef"]}
        loader = DictConfigLoader(config)

        assert loader.photo_extensions == [".dng", ".cr3", ".nef"]

    def test_photo_extensions_default_empty(self):
        """Returns empty list when photo_extensions not in config."""
        loader = DictConfigLoader({})
        assert loader.photo_extensions == []

    def test_metadata_extensions(self):
        """Returns metadata extensions from config dict."""
        config = {"metadata_extensions": [".xmp", ".xml"]}
        loader = DictConfigLoader(config)

        assert loader.metadata_extensions == [".xmp", ".xml"]

    def test_metadata_extensions_default_empty(self):
        """Returns empty list when metadata_extensions not in config."""
        loader = DictConfigLoader({})
        assert loader.metadata_extensions == []

    def test_camera_mappings(self):
        """Returns camera mappings from config dict."""
        config = {
            "camera_mappings": {
                "AB3D": [{"name": "Canon EOS R5", "serial_number": "12345"}],
                "XY9Z": [{"name": "Sony A7R IV"}]
            }
        }
        loader = DictConfigLoader(config)

        assert len(loader.camera_mappings) == 2
        assert "AB3D" in loader.camera_mappings
        assert loader.camera_mappings["AB3D"][0]["name"] == "Canon EOS R5"

    def test_camera_mappings_default_empty(self):
        """Returns empty dict when camera_mappings not in config."""
        loader = DictConfigLoader({})
        assert loader.camera_mappings == {}

    def test_processing_methods(self):
        """Returns processing methods from config dict."""
        config = {
            "processing_methods": {
                "HDR": "High Dynamic Range",
                "BW": "Black and White",
                "PANO": "Panorama"
            }
        }
        loader = DictConfigLoader(config)

        assert len(loader.processing_methods) == 3
        assert loader.processing_methods["HDR"] == "High Dynamic Range"

    def test_processing_methods_default_empty(self):
        """Returns empty dict when processing_methods not in config."""
        loader = DictConfigLoader({})
        assert loader.processing_methods == {}

    def test_require_sidecar(self):
        """Returns require_sidecar from config dict."""
        config = {"require_sidecar": [".cr3", ".nef"]}
        loader = DictConfigLoader(config)

        assert loader.require_sidecar == [".cr3", ".nef"]

    def test_require_sidecar_default_empty(self):
        """Returns empty list when require_sidecar not in config."""
        loader = DictConfigLoader({})
        assert loader.require_sidecar == []

    def test_full_config(self):
        """All properties work together with full config."""
        config = {
            "photo_extensions": [".dng", ".cr3"],
            "metadata_extensions": [".xmp"],
            "camera_mappings": {"AB3D": [{"name": "Canon"}]},
            "processing_methods": {"HDR": "High Dynamic Range"},
            "require_sidecar": [".cr3"]
        }
        loader = DictConfigLoader(config)

        assert loader.photo_extensions == [".dng", ".cr3"]
        assert loader.metadata_extensions == [".xmp"]
        assert len(loader.camera_mappings) == 1
        assert len(loader.processing_methods) == 1
        assert loader.require_sidecar == [".cr3"]


class TestDatabaseConfigLoader:
    """Tests for DatabaseConfigLoader implementation."""

    def test_default_photo_extensions(self, test_db_session, test_team):
        """Returns default photo extensions when not configured."""
        loader = DatabaseConfigLoader(test_team.id, test_db_session)

        extensions = loader.photo_extensions
        assert ".dng" in extensions
        assert ".cr3" in extensions
        assert ".jpg" in extensions

    def test_default_metadata_extensions(self, test_db_session, test_team):
        """Returns default metadata extensions when not configured."""
        loader = DatabaseConfigLoader(test_team.id, test_db_session)

        extensions = loader.metadata_extensions
        assert ".xmp" in extensions

    def test_default_require_sidecar(self, test_db_session, test_team):
        """Returns default require_sidecar when not configured."""
        loader = DatabaseConfigLoader(test_team.id, test_db_session)

        extensions = loader.require_sidecar
        assert ".cr3" in extensions

    def test_empty_camera_mappings_default(self, test_db_session, test_team):
        """Returns empty camera mappings when not configured."""
        loader = DatabaseConfigLoader(test_team.id, test_db_session)

        assert loader.camera_mappings == {}

    def test_empty_processing_methods_default(self, test_db_session, test_team):
        """Returns empty processing methods when not configured."""
        loader = DatabaseConfigLoader(test_team.id, test_db_session)

        assert loader.processing_methods == {}

    def test_loads_photo_extensions_from_db(self, test_db_session, test_team):
        """Loads photo extensions from Configuration table."""
        from backend.src.models import Configuration

        # Insert config into database
        config = Configuration(
            team_id=test_team.id,
            category="extensions",
            key="photo_extensions",
            value_json=[".raw", ".arw"]
        )
        test_db_session.add(config)
        test_db_session.commit()

        loader = DatabaseConfigLoader(test_team.id, test_db_session)

        assert loader.photo_extensions == [".raw", ".arw"]

    def test_loads_metadata_extensions_from_db(self, test_db_session, test_team):
        """Loads metadata extensions from Configuration table."""
        from backend.src.models import Configuration

        config = Configuration(
            team_id=test_team.id,
            category="extensions",
            key="metadata_extensions",
            value_json=[".xmp", ".xml"]
        )
        test_db_session.add(config)
        test_db_session.commit()

        loader = DatabaseConfigLoader(test_team.id, test_db_session)

        assert loader.metadata_extensions == [".xmp", ".xml"]

    def test_loads_camera_mappings_from_db(self, test_db_session, test_team):
        """Loads camera mappings from Configuration table."""
        from backend.src.models import Configuration

        config = Configuration(
            team_id=test_team.id,
            category="cameras",
            key="AB3D",
            value_json={"name": "Canon EOS R5", "serial_number": "12345"}
        )
        test_db_session.add(config)
        test_db_session.commit()

        loader = DatabaseConfigLoader(test_team.id, test_db_session)

        assert "AB3D" in loader.camera_mappings
        # Value is wrapped in list
        assert loader.camera_mappings["AB3D"][0]["name"] == "Canon EOS R5"

    def test_loads_processing_methods_from_db(self, test_db_session, test_team):
        """Loads processing methods from Configuration table."""
        from backend.src.models import Configuration

        config = Configuration(
            team_id=test_team.id,
            category="processing_methods",
            key="HDR",
            value_json="High Dynamic Range"
        )
        test_db_session.add(config)
        test_db_session.commit()

        loader = DatabaseConfigLoader(test_team.id, test_db_session)

        assert loader.processing_methods["HDR"] == "High Dynamic Range"

    def test_caches_config(self, test_db_session, test_team):
        """Config is cached after first load."""
        from backend.src.models import Configuration

        config = Configuration(
            team_id=test_team.id,
            category="extensions",
            key="photo_extensions",
            value_json=[".dng"]
        )
        test_db_session.add(config)
        test_db_session.commit()

        loader = DatabaseConfigLoader(test_team.id, test_db_session)

        # First access loads from DB
        _ = loader.photo_extensions
        assert loader._config_cache is not None

        # Modify DB directly
        config.value_json = [".cr3"]
        test_db_session.commit()

        # Should still return cached value
        assert loader.photo_extensions == [".dng"]

    def test_tenant_isolation(self, test_db_session, test_team, other_team):
        """Config for one team doesn't affect another team's loader."""
        from backend.src.models import Configuration

        # Insert config for test_team only
        config1 = Configuration(
            team_id=test_team.id,
            category="cameras",
            key="TEST1",
            value_json={"name": "Canon EOS R5", "serial_number": "team1"}
        )
        test_db_session.add(config1)
        test_db_session.commit()

        loader1 = DatabaseConfigLoader(test_team.id, test_db_session)
        loader2 = DatabaseConfigLoader(other_team.id, test_db_session)

        # test_team should see the camera mapping
        assert "TEST1" in loader1.camera_mappings

        # other_team should NOT see test_team's camera mapping
        # (should be empty since no config was added for other_team)
        assert "TEST1" not in loader2.camera_mappings
