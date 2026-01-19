"""
Unit tests for DictConfigLoader.

Issue #90 - Distributed Agent Architecture (Phase 5)
Task: T095
"""

import pytest

from src.config_loader import DictConfigLoader


class TestDictConfigLoader:
    """Tests for DictConfigLoader."""

    def test_photo_extensions(self):
        """Returns photo extensions from config."""
        config = {"photo_extensions": [".dng", ".cr3"]}
        loader = DictConfigLoader(config)

        assert loader.photo_extensions == [".dng", ".cr3"]

    def test_photo_extensions_default(self):
        """Returns empty list when not configured."""
        config = {}
        loader = DictConfigLoader(config)

        assert loader.photo_extensions == []

    def test_metadata_extensions(self):
        """Returns metadata extensions from config."""
        config = {"metadata_extensions": [".xmp"]}
        loader = DictConfigLoader(config)

        assert loader.metadata_extensions == [".xmp"]

    def test_metadata_extensions_default(self):
        """Returns empty list when not configured."""
        config = {}
        loader = DictConfigLoader(config)

        assert loader.metadata_extensions == []

    def test_camera_mappings(self):
        """Returns camera mappings from config."""
        config = {
            "camera_mappings": {
                "AB3D": [{"name": "Canon EOS R5", "serial_number": "12345"}]
            }
        }
        loader = DictConfigLoader(config)

        assert loader.camera_mappings == {
            "AB3D": [{"name": "Canon EOS R5", "serial_number": "12345"}]
        }

    def test_camera_mappings_default(self):
        """Returns empty dict when not configured."""
        config = {}
        loader = DictConfigLoader(config)

        assert loader.camera_mappings == {}

    def test_processing_methods(self):
        """Returns processing methods from config."""
        config = {
            "processing_methods": {
                "HDR": "High Dynamic Range",
                "BW": "Black and White"
            }
        }
        loader = DictConfigLoader(config)

        assert loader.processing_methods == {
            "HDR": "High Dynamic Range",
            "BW": "Black and White"
        }

    def test_processing_methods_default(self):
        """Returns empty dict when not configured."""
        config = {}
        loader = DictConfigLoader(config)

        assert loader.processing_methods == {}

    def test_require_sidecar(self):
        """Returns require sidecar from config."""
        config = {"require_sidecar": [".cr3"]}
        loader = DictConfigLoader(config)

        assert loader.require_sidecar == [".cr3"]

    def test_require_sidecar_default(self):
        """Returns empty list when not configured."""
        config = {}
        loader = DictConfigLoader(config)

        assert loader.require_sidecar == []

    def test_full_config(self):
        """Works with full configuration."""
        config = {
            "photo_extensions": [".dng", ".cr3", ".tiff"],
            "metadata_extensions": [".xmp"],
            "camera_mappings": {"AB3D": [{"name": "Canon EOS R5"}]},
            "processing_methods": {"HDR": "High Dynamic Range"},
            "require_sidecar": [".cr3"]
        }
        loader = DictConfigLoader(config)

        assert loader.photo_extensions == [".dng", ".cr3", ".tiff"]
        assert loader.metadata_extensions == [".xmp"]
        assert len(loader.camera_mappings) == 1
        assert len(loader.processing_methods) == 1
        assert loader.require_sidecar == [".cr3"]
