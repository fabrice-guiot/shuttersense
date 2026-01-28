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

    def test_irrelevant_keys_ignored(self, service, sample_config):
        """Should ignore irrelevant config keys (Issue #92).

        This ensures hash consistency between agent and backend.
        """
        # Add irrelevant keys that should be ignored
        config_with_extra = dict(sample_config)
        config_with_extra["some_other_setting"] = "value"
        config_with_extra["unrelated_config"] = {"nested": "data"}
        config_with_extra["retention_days"] = 30

        hash1 = service.compute_configuration_hash(sample_config)
        hash2 = service.compute_configuration_hash(config_with_extra)

        # Hashes should be identical - extra keys ignored
        assert hash1 == hash2

    def test_only_relevant_keys_affect_hash(self, service):
        """Should only hash relevant keys defined in RELEVANT_CONFIG_KEYS."""
        # Config with only relevant keys
        config_relevant = {
            "photo_extensions": [".dng"],
            "metadata_extensions": [".xmp"],
        }

        # Same config with extra irrelevant keys
        config_extra = {
            "photo_extensions": [".dng"],
            "metadata_extensions": [".xmp"],
            "unrelated_setting": "ignored",
            "another_setting": 123,
        }

        hash1 = service.compute_configuration_hash(config_relevant)
        hash2 = service.compute_configuration_hash(config_extra)

        assert hash1 == hash2

    def test_relevant_keys_list_matches_agent(self, service):
        """RELEVANT_CONFIG_KEYS should match agent's _extract_relevant_config."""
        # These are the keys that should be included (from agent/src/input_state.py)
        expected_keys = {
            "photo_extensions",
            "metadata_extensions",
            "require_sidecar",
            "cameras",
            "processing_methods",
            "pipeline",
        }

        assert set(service.RELEVANT_CONFIG_KEYS) == expected_keys


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


# ============================================================================
# Test: Cross-verification with agent
# ============================================================================

class TestAgentBackendConsistency:
    """Tests ensuring agent and backend produce identical hashes."""

    def test_config_hash_matches_agent_implementation(self, service):
        """Backend config hash should match agent's implementation.

        This is critical for NO_CHANGE detection to work properly.
        The agent computes hash during job execution, and the backend
        must produce the same hash for comparison.
        """
        # Test config with all relevant keys
        config = {
            "photo_extensions": [".dng", ".cr3"],
            "metadata_extensions": [".xmp"],
            "require_sidecar": [".cr3"],
            "cameras": {"AB3D": [{"name": "Canon R5"}]},
            "processing_methods": {"HDR": "High Dynamic Range"},
            "pipeline": {"stages": ["import", "edit"]},
        }

        hash1 = service.compute_configuration_hash(config)

        # Manually compute what the agent would produce
        # (sorted JSON of filtered keys)
        import json
        relevant = {k: config[k] for k in service.RELEVANT_CONFIG_KEYS if k in config}
        expected = json.dumps(relevant, sort_keys=True, separators=(",", ":"))
        import hashlib
        expected_hash = hashlib.sha256(expected.encode("utf-8")).hexdigest()

        assert hash1 == expected_hash

    def test_file_list_hash_matches_agent_implementation(self, service):
        """Backend file list hash should match agent's implementation.

        The agent computes this from filesystem scan, backend verifies
        the hash on NO_CHANGE detection.
        """
        files = [
            ("photos/IMG_001.dng", 25000000, 1704067200),
            ("photos/IMG_001.xmp", 4096, 1704067201),
        ]

        hash1 = service.compute_file_list_hash(files)

        # Manually compute what the agent would produce
        sorted_files = sorted(files, key=lambda f: f[0])
        lines = [f"{p}|{s}|{int(m)}" for p, s, m in sorted_files]
        content = "\n".join(lines)
        import hashlib
        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        assert hash1 == expected_hash

    def test_input_state_hash_matches_agent_implementation(self, service):
        """Backend input state hash should match agent's implementation."""
        file_hash = "a" * 64
        config_hash = "b" * 64
        tool = "photostats"

        hash1 = service.compute_input_state_hash(file_hash, config_hash, tool)

        # Manually compute what the agent would produce
        content = f"{tool}|{file_hash}|{config_hash}"
        import hashlib
        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        assert hash1 == expected_hash


# ============================================================================
# Test: Phase 7 - Server-Side No-Change Detection (Issue #107)
# ============================================================================

class TestParseISO8601ToTimestamp:
    """Tests for InputStateService._parse_iso8601_to_timestamp."""

    def test_parses_z_suffix(self, service):
        """Should parse ISO8601 with Z suffix."""
        result = service._parse_iso8601_to_timestamp("2022-11-25T13:30:49Z")
        assert result is not None
        # 2022-11-25 13:30:49 UTC
        assert abs(result - 1669383049) < 1

    def test_parses_milliseconds_z_suffix(self, service):
        """Should parse ISO8601 with milliseconds and Z suffix."""
        result = service._parse_iso8601_to_timestamp("2022-11-25T13:30:49.000Z")
        assert result is not None
        assert abs(result - 1669383049) < 1

    def test_parses_timezone_offset(self, service):
        """Should parse ISO8601 with timezone offset."""
        result = service._parse_iso8601_to_timestamp("2022-11-25T13:30:49+00:00")
        assert result is not None
        assert abs(result - 1669383049) < 1

    def test_returns_none_for_empty_string(self, service):
        """Should return None for empty string."""
        assert service._parse_iso8601_to_timestamp("") is None

    def test_returns_none_for_invalid_format(self, service):
        """Should return None for invalid format."""
        assert service._parse_iso8601_to_timestamp("not-a-date") is None
        assert service._parse_iso8601_to_timestamp("2022/11/25") is None


class TestComputeInventoryFileHash:
    """Tests for InputStateService.compute_inventory_file_hash."""

    @pytest.fixture
    def sample_file_info(self):
        """Sample inventory FileInfo for testing."""
        return [
            {"key": "2020/IMG_001.dng", "size": 25000000, "last_modified": "2022-11-25T13:30:49.000Z"},
            {"key": "2020/IMG_001.xmp", "size": 4096, "last_modified": "2022-11-25T13:30:50.000Z"},
            {"key": "2020/subfolder/IMG_002.dng", "size": 26000000, "last_modified": "2022-11-26T13:30:49.000Z"},
        ]

    def test_produces_64_char_hex_hash(self, service, sample_file_info):
        """Should produce a 64-character hex string (SHA-256)."""
        hash_value = service.compute_inventory_file_hash(sample_file_info)

        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_deterministic_for_same_input(self, service, sample_file_info):
        """Should produce the same hash for the same input."""
        hash1 = service.compute_inventory_file_hash(sample_file_info)
        hash2 = service.compute_inventory_file_hash(sample_file_info)

        assert hash1 == hash2

    def test_order_independent(self, service, sample_file_info):
        """Should produce the same hash regardless of input order."""
        reversed_info = list(reversed(sample_file_info))

        hash_original = service.compute_inventory_file_hash(sample_file_info)
        hash_reversed = service.compute_inventory_file_hash(reversed_info)

        assert hash_original == hash_reversed

    def test_different_files_produce_different_hash(self, service, sample_file_info):
        """Should produce different hash when files differ."""
        different_info = [
            {"key": "2020/IMG_999.dng", "size": 25000000, "last_modified": "2022-11-25T13:30:49.000Z"},
        ]

        hash1 = service.compute_inventory_file_hash(sample_file_info)
        hash2 = service.compute_inventory_file_hash(different_info)

        assert hash1 != hash2

    def test_size_change_produces_different_hash(self, service, sample_file_info):
        """Should detect when file size changes."""
        modified_info = [
            {"key": "2020/IMG_001.dng", "size": 25000001, "last_modified": "2022-11-25T13:30:49.000Z"},
            {"key": "2020/IMG_001.xmp", "size": 4096, "last_modified": "2022-11-25T13:30:50.000Z"},
            {"key": "2020/subfolder/IMG_002.dng", "size": 26000000, "last_modified": "2022-11-26T13:30:49.000Z"},
        ]

        hash1 = service.compute_inventory_file_hash(sample_file_info)
        hash2 = service.compute_inventory_file_hash(modified_info)

        assert hash1 != hash2

    def test_mtime_change_produces_different_hash(self, service, sample_file_info):
        """Should detect when file last_modified changes."""
        modified_info = [
            {"key": "2020/IMG_001.dng", "size": 25000000, "last_modified": "2022-11-25T14:30:49.000Z"},  # Changed
            {"key": "2020/IMG_001.xmp", "size": 4096, "last_modified": "2022-11-25T13:30:50.000Z"},
            {"key": "2020/subfolder/IMG_002.dng", "size": 26000000, "last_modified": "2022-11-26T13:30:49.000Z"},
        ]

        hash1 = service.compute_inventory_file_hash(sample_file_info)
        hash2 = service.compute_inventory_file_hash(modified_info)

        assert hash1 != hash2

    def test_empty_file_info(self, service):
        """Should handle empty file info list."""
        hash_value = service.compute_inventory_file_hash([])

        assert len(hash_value) == 64

    def test_skips_entries_with_invalid_timestamps(self, service):
        """Should skip entries with invalid/missing timestamps."""
        file_info = [
            {"key": "2020/IMG_001.dng", "size": 25000000, "last_modified": "2022-11-25T13:30:49.000Z"},
            {"key": "2020/IMG_002.dng", "size": 25000000, "last_modified": "invalid-date"},
            {"key": "2020/IMG_003.dng", "size": 25000000, "last_modified": ""},
        ]

        # Should not raise, should skip invalid entries
        hash_value = service.compute_inventory_file_hash(file_info)
        assert len(hash_value) == 64

        # Should match hash of only the valid entry
        valid_only = [
            {"key": "2020/IMG_001.dng", "size": 25000000, "last_modified": "2022-11-25T13:30:49.000Z"},
        ]
        hash_valid = service.compute_inventory_file_hash(valid_only)
        assert hash_value == hash_valid

    def test_matches_file_list_hash_format(self, service):
        """Should produce same hash as compute_file_list_hash for equivalent data."""
        # Inventory FileInfo
        file_info = [
            {"key": "photos/IMG_001.dng", "size": 25000000, "last_modified": "2022-11-25T13:30:49Z"},
        ]

        # Equivalent tuple format (path, size, mtime)
        # 2022-11-25T13:30:49Z = 1669383049
        files_tuples = [
            ("photos/IMG_001.dng", 25000000, 1669383049.0),
        ]

        hash_inventory = service.compute_inventory_file_hash(file_info)
        hash_tuples = service.compute_file_list_hash(files_tuples)

        assert hash_inventory == hash_tuples

    def test_url_encoded_paths_are_decoded(self, service):
        """Should URL-decode paths to match agent-side behavior.

        S3/GCS inventory keys are URL-encoded (e.g., spaces become %20).
        The agent URL-decodes these before hashing, so we must too.
        """
        # URL-encoded FileInfo (as stored in S3/GCS inventory)
        encoded_file_info = [
            {"key": "2025/Spring%20Training/IMG_001.dng", "size": 25000000, "last_modified": "2022-11-25T13:30:49Z"},
            {"key": "2025/Event%20%26%20Session/IMG_002.dng", "size": 26000000, "last_modified": "2022-11-25T13:30:50Z"},
        ]

        # Equivalent with decoded paths (what agent uses)
        decoded_file_info = [
            {"key": "2025/Spring Training/IMG_001.dng", "size": 25000000, "last_modified": "2022-11-25T13:30:49Z"},
            {"key": "2025/Event & Session/IMG_002.dng", "size": 26000000, "last_modified": "2022-11-25T13:30:50Z"},
        ]

        # Both should produce the same hash (decoded internally)
        hash_encoded = service.compute_inventory_file_hash(encoded_file_info)
        hash_decoded = service.compute_inventory_file_hash(decoded_file_info)

        assert hash_encoded == hash_decoded

        # Verify against direct file_list_hash with decoded paths
        files_tuples = [
            ("2025/Spring Training/IMG_001.dng", 25000000, 1669383049.0),
            ("2025/Event & Session/IMG_002.dng", 26000000, 1669383050.0),
        ]
        hash_tuples = service.compute_file_list_hash(files_tuples)

        assert hash_encoded == hash_tuples


class TestCanComputeServerSideHash:
    """Tests for InputStateService.can_compute_server_side_hash."""

    def test_returns_false_for_none_collection(self, service):
        """Should return False when collection is None."""
        assert service.can_compute_server_side_hash(None) is False

    def test_returns_false_for_empty_file_info(self, service):
        """Should return False when file_info is empty."""
        from unittest.mock import MagicMock

        collection = MagicMock()
        collection.file_info = None

        assert service.can_compute_server_side_hash(collection) is False

        collection.file_info = []
        assert service.can_compute_server_side_hash(collection) is False

    def test_returns_false_for_api_source(self, service):
        """Should return False when file_info_source is 'api'."""
        from unittest.mock import MagicMock

        collection = MagicMock()
        collection.file_info = [{"key": "test.dng", "size": 100}]
        collection.file_info_source = "api"

        assert service.can_compute_server_side_hash(collection) is False

    def test_returns_false_for_null_source(self, service):
        """Should return False when file_info_source is None."""
        from unittest.mock import MagicMock

        collection = MagicMock()
        collection.file_info = [{"key": "test.dng", "size": 100}]
        collection.file_info_source = None

        assert service.can_compute_server_side_hash(collection) is False

    def test_returns_true_for_inventory_source(self, service):
        """Should return True when file_info_source is 'inventory'."""
        from unittest.mock import MagicMock

        collection = MagicMock()
        collection.file_info = [{"key": "test.dng", "size": 100}]
        collection.file_info_source = "inventory"

        assert service.can_compute_server_side_hash(collection) is True


class TestComputeCollectionInputStateHash:
    """Tests for InputStateService.compute_collection_input_state_hash."""

    @pytest.fixture
    def inventory_collection(self):
        """Create a mock collection with inventory file info."""
        from unittest.mock import MagicMock

        collection = MagicMock()
        collection.file_info = [
            {"key": "2020/IMG_001.dng", "size": 25000000, "last_modified": "2022-11-25T13:30:49.000Z"},
            {"key": "2020/IMG_001.xmp", "size": 4096, "last_modified": "2022-11-25T13:30:50.000Z"},
        ]
        collection.file_info_source = "inventory"
        return collection

    @pytest.fixture
    def api_collection(self):
        """Create a mock collection with API-sourced file info."""
        from unittest.mock import MagicMock

        collection = MagicMock()
        collection.file_info = [
            {"key": "2020/IMG_001.dng", "size": 25000000, "last_modified": "2022-11-25T13:30:49.000Z"},
        ]
        collection.file_info_source = "api"
        return collection

    def test_returns_none_for_api_source(self, service, api_collection, sample_config):
        """Should return None when collection uses API source."""
        result = service.compute_collection_input_state_hash(
            api_collection, sample_config, "photostats"
        )
        assert result is None

    def test_returns_hash_for_inventory_source(self, service, inventory_collection, sample_config):
        """Should return hash when collection uses inventory source."""
        result = service.compute_collection_input_state_hash(
            inventory_collection, sample_config, "photostats"
        )

        assert result is not None
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic_for_same_input(self, service, inventory_collection, sample_config):
        """Should produce the same hash for the same input."""
        hash1 = service.compute_collection_input_state_hash(
            inventory_collection, sample_config, "photostats"
        )
        hash2 = service.compute_collection_input_state_hash(
            inventory_collection, sample_config, "photostats"
        )

        assert hash1 == hash2

    def test_different_tool_produces_different_hash(self, service, inventory_collection, sample_config):
        """Should produce different hash for different tools."""
        hash1 = service.compute_collection_input_state_hash(
            inventory_collection, sample_config, "photostats"
        )
        hash2 = service.compute_collection_input_state_hash(
            inventory_collection, sample_config, "photo_pairing"
        )

        assert hash1 != hash2

    def test_different_config_produces_different_hash(self, service, inventory_collection, sample_config):
        """Should produce different hash for different config."""
        modified_config = dict(sample_config)
        modified_config["photo_extensions"] = [".dng"]

        hash1 = service.compute_collection_input_state_hash(
            inventory_collection, sample_config, "photostats"
        )
        hash2 = service.compute_collection_input_state_hash(
            inventory_collection, modified_config, "photostats"
        )

        assert hash1 != hash2

    def test_different_files_produce_different_hash(self, service, sample_config):
        """Should produce different hash when file info differs."""
        from unittest.mock import MagicMock

        collection1 = MagicMock()
        collection1.file_info = [
            {"key": "2020/IMG_001.dng", "size": 25000000, "last_modified": "2022-11-25T13:30:49.000Z"},
        ]
        collection1.file_info_source = "inventory"

        collection2 = MagicMock()
        collection2.file_info = [
            {"key": "2020/IMG_002.dng", "size": 25000000, "last_modified": "2022-11-25T13:30:49.000Z"},
        ]
        collection2.file_info_source = "inventory"

        hash1 = service.compute_collection_input_state_hash(
            collection1, sample_config, "photostats"
        )
        hash2 = service.compute_collection_input_state_hash(
            collection2, sample_config, "photostats"
        )

        assert hash1 != hash2
