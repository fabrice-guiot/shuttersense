"""
Unit tests for InputStateService.

Issue #92: Storage Optimization for Analysis Results
Tests Input State hash computation for determinism and correctness.
"""

import pytest
import json

from backend.src.services.input_state_service import (
    InputStateService,
    get_input_state_service,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def service():
    """Create an InputStateService instance."""
    return InputStateService()


@pytest.fixture
def sample_files():
    """Sample file list for testing."""
    return [
        ("photos/IMG_001.dng", 25000000, 1704067200),
        ("photos/IMG_001.xmp", 4096, 1704067201),
        ("photos/subfolder/IMG_002.dng", 26000000, 1704153600),
        ("photos/subfolder/IMG_002.xmp", 4500, 1704153601),
    ]


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "photo_extensions": [".dng", ".cr3", ".tiff"],
        "metadata_extensions": [".xmp"],
        "require_sidecar": [".cr3"],
        "cameras": {
            "AB3D": [{"name": "Canon EOS R5", "serial_number": "12345"}]
        },
        "processing_methods": {
            "HDR": "High Dynamic Range",
            "BW": "Black and White"
        }
    }


# ============================================================================
# Test: compute_file_list_hash
# ============================================================================

class TestComputeFileListHash:
    """Tests for InputStateService.compute_file_list_hash."""

    def test_produces_64_char_hex_hash(self, service, sample_files):
        """Should produce a 64-character hex string (SHA-256)."""
        hash_value = service.compute_file_list_hash(sample_files)

        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_deterministic_for_same_input(self, service, sample_files):
        """Should produce the same hash for the same input."""
        hash1 = service.compute_file_list_hash(sample_files)
        hash2 = service.compute_file_list_hash(sample_files)

        assert hash1 == hash2

    def test_order_independent(self, service, sample_files):
        """Should produce the same hash regardless of input order."""
        # Reverse the order
        reversed_files = list(reversed(sample_files))

        hash_original = service.compute_file_list_hash(sample_files)
        hash_reversed = service.compute_file_list_hash(reversed_files)

        assert hash_original == hash_reversed

    def test_different_files_produce_different_hash(self, service, sample_files):
        """Should produce different hash when files differ."""
        different_files = [
            ("photos/IMG_001.dng", 25000000, 1704067200),
            ("photos/IMG_003.xmp", 4096, 1704067201),  # Different file
        ]

        hash1 = service.compute_file_list_hash(sample_files)
        hash2 = service.compute_file_list_hash(different_files)

        assert hash1 != hash2

    def test_size_change_produces_different_hash(self, service, sample_files):
        """Should detect when file size changes."""
        modified_files = [
            ("photos/IMG_001.dng", 25000001, 1704067200),  # Size changed
            ("photos/IMG_001.xmp", 4096, 1704067201),
            ("photos/subfolder/IMG_002.dng", 26000000, 1704153600),
            ("photos/subfolder/IMG_002.xmp", 4500, 1704153601),
        ]

        hash1 = service.compute_file_list_hash(sample_files)
        hash2 = service.compute_file_list_hash(modified_files)

        assert hash1 != hash2

    def test_mtime_change_produces_different_hash(self, service, sample_files):
        """Should detect when file mtime changes."""
        modified_files = [
            ("photos/IMG_001.dng", 25000000, 1704067201),  # mtime changed
            ("photos/IMG_001.xmp", 4096, 1704067201),
            ("photos/subfolder/IMG_002.dng", 26000000, 1704153600),
            ("photos/subfolder/IMG_002.xmp", 4500, 1704153601),
        ]

        hash1 = service.compute_file_list_hash(sample_files)
        hash2 = service.compute_file_list_hash(modified_files)

        assert hash1 != hash2

    def test_empty_file_list(self, service):
        """Should handle empty file list."""
        hash_value = service.compute_file_list_hash([])

        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_float_mtime_truncated_to_int(self, service):
        """Should truncate float mtime to int for consistency."""
        files_float = [("a.txt", 100, 1704067200.123)]
        files_int = [("a.txt", 100, 1704067200)]

        hash1 = service.compute_file_list_hash(files_float)
        hash2 = service.compute_file_list_hash(files_int)

        assert hash1 == hash2


# ============================================================================
# Test: compute_configuration_hash
# ============================================================================

class TestComputeConfigurationHash:
    """Tests for InputStateService.compute_configuration_hash."""

    def test_produces_64_char_hex_hash(self, service, sample_config):
        """Should produce a 64-character hex string (SHA-256)."""
        hash_value = service.compute_configuration_hash(sample_config)

        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_deterministic_for_same_input(self, service, sample_config):
        """Should produce the same hash for the same input."""
        hash1 = service.compute_configuration_hash(sample_config)
        hash2 = service.compute_configuration_hash(sample_config)

        assert hash1 == hash2

    def test_key_order_independent(self, service):
        """Should produce the same hash regardless of key order."""
        config1 = {"a": 1, "b": 2, "c": 3}
        config2 = {"c": 3, "a": 1, "b": 2}

        hash1 = service.compute_configuration_hash(config1)
        hash2 = service.compute_configuration_hash(config2)

        assert hash1 == hash2

    def test_different_config_produces_different_hash(self, service, sample_config):
        """Should produce different hash when config differs."""
        different_config = dict(sample_config)
        different_config["photo_extensions"] = [".dng"]  # Different

        hash1 = service.compute_configuration_hash(sample_config)
        hash2 = service.compute_configuration_hash(different_config)

        assert hash1 != hash2

    def test_empty_config(self, service):
        """Should handle empty configuration."""
        hash_value = service.compute_configuration_hash({})

        assert len(hash_value) == 64


# ============================================================================
# Test: compute_input_state_hash
# ============================================================================

class TestComputeInputStateHash:
    """Tests for InputStateService.compute_input_state_hash."""

    def test_produces_64_char_hex_hash(self, service):
        """Should produce a 64-character hex string (SHA-256)."""
        file_hash = "a" * 64
        config_hash = "b" * 64

        hash_value = service.compute_input_state_hash(file_hash, config_hash)

        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_deterministic_for_same_input(self, service):
        """Should produce the same hash for the same input."""
        file_hash = "a" * 64
        config_hash = "b" * 64

        hash1 = service.compute_input_state_hash(file_hash, config_hash)
        hash2 = service.compute_input_state_hash(file_hash, config_hash)

        assert hash1 == hash2

    def test_includes_tool_in_hash(self, service):
        """Should produce different hash for different tools."""
        file_hash = "a" * 64
        config_hash = "b" * 64

        hash1 = service.compute_input_state_hash(file_hash, config_hash, tool="photostats")
        hash2 = service.compute_input_state_hash(file_hash, config_hash, tool="photo_pairing")

        assert hash1 != hash2

    def test_without_tool_produces_valid_hash(self, service):
        """Should work without tool parameter."""
        file_hash = "a" * 64
        config_hash = "b" * 64

        hash_value = service.compute_input_state_hash(file_hash, config_hash)

        assert len(hash_value) == 64


# ============================================================================
# Test: compute_input_state_json
# ============================================================================

class TestComputeInputStateJson:
    """Tests for InputStateService.compute_input_state_json."""

    def test_produces_valid_json(self, service, sample_files, sample_config):
        """Should produce valid JSON output."""
        json_str = service.compute_input_state_json(sample_files, sample_config, "photostats")

        # Should be valid JSON
        parsed = json.loads(json_str)

        assert isinstance(parsed, dict)
        assert parsed["tool"] == "photostats"
        assert parsed["file_count"] == 4
        assert "files" in parsed
        assert "configuration" in parsed

    def test_files_sorted_by_path(self, service, sample_files, sample_config):
        """Should sort files by path in JSON output."""
        json_str = service.compute_input_state_json(sample_files, sample_config, "photostats")
        parsed = json.loads(json_str)

        paths = [f["path"] for f in parsed["files"]]
        assert paths == sorted(paths)


# ============================================================================
# Test: Module singleton
# ============================================================================

class TestModuleSingleton:
    """Tests for the module-level singleton."""

    def test_get_input_state_service_returns_singleton(self):
        """Should return the same instance on multiple calls."""
        service1 = get_input_state_service()
        service2 = get_input_state_service()

        assert service1 is service2

    def test_get_input_state_service_returns_instance(self):
        """Should return an InputStateService instance."""
        service = get_input_state_service()

        assert isinstance(service, InputStateService)
