"""
Unit tests for agent input_state module.

Issue #92: Storage Optimization for Analysis Results
Tests Input State computation for no-change detection.
"""

import json
import tempfile
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.input_state import (
    InputStateComputer,
    check_no_change,
    get_input_state_computer,
)
from src.remote.base import FileInfo


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def computer():
    """Create an InputStateComputer instance."""
    return InputStateComputer()


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "photo_extensions": [".dng", ".cr3"],
        "metadata_extensions": [".xmp"],
        "require_sidecar": [".cr3"],
        "camera_mappings": {"AB3D": [{"name": "Canon R5"}]},
        "processing_methods": {"HDR": "High Dynamic Range"},
        # These should be ignored
        "unrelated_key": "should be ignored",
    }


@pytest.fixture
def temp_collection(tmp_path):
    """Create a temporary collection directory with files."""
    # Create some test files
    (tmp_path / "IMG_001.dng").write_bytes(b"x" * 1000)
    (tmp_path / "IMG_001.xmp").write_bytes(b"y" * 100)
    (tmp_path / "subfolder").mkdir()
    (tmp_path / "subfolder" / "IMG_002.dng").write_bytes(b"z" * 2000)
    return tmp_path


# ============================================================================
# Test: compute_file_list_hash_from_path
# ============================================================================

class TestComputeFileListHashFromPath:
    """Tests for local file scanning."""

    def test_produces_64_char_hash(self, computer, temp_collection):
        """Should produce a 64-character hex hash."""
        hash_value, count = computer.compute_file_list_hash_from_path(str(temp_collection))

        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_returns_file_count(self, computer, temp_collection):
        """Should return correct file count."""
        hash_value, count = computer.compute_file_list_hash_from_path(str(temp_collection))

        assert count == 3  # IMG_001.dng, IMG_001.xmp, subfolder/IMG_002.dng

    def test_deterministic(self, computer, temp_collection):
        """Should produce the same hash for same input."""
        hash1, _ = computer.compute_file_list_hash_from_path(str(temp_collection))
        hash2, _ = computer.compute_file_list_hash_from_path(str(temp_collection))

        assert hash1 == hash2

    def test_filters_by_extension(self, computer, temp_collection):
        """Should filter files by extension when specified."""
        hash_all, count_all = computer.compute_file_list_hash_from_path(str(temp_collection))
        hash_dng, count_dng = computer.compute_file_list_hash_from_path(
            str(temp_collection), extensions=[".dng"]
        )

        assert count_dng == 2  # Only .dng files
        assert count_all == 3
        assert hash_all != hash_dng

    def test_empty_directory(self, computer, tmp_path):
        """Should handle empty directory."""
        hash_value, count = computer.compute_file_list_hash_from_path(str(tmp_path))

        assert count == 0
        assert len(hash_value) == 64


# ============================================================================
# Test: compute_file_list_hash_from_file_info
# ============================================================================

class TestComputeFileListHashFromFileInfo:
    """Tests for FileInfo-based hash computation."""

    def test_produces_64_char_hash(self, computer):
        """Should produce a 64-character hex hash."""
        file_infos = [
            FileInfo(path="IMG_001.dng", size=1000, last_modified="2024-01-01T00:00:00Z"),
            FileInfo(path="IMG_001.xmp", size=100, last_modified="2024-01-01T00:00:01Z"),
        ]

        hash_value, count = computer.compute_file_list_hash_from_file_info(file_infos)

        assert len(hash_value) == 64
        assert count == 2

    def test_deterministic(self, computer):
        """Should produce the same hash for same input."""
        file_infos = [
            FileInfo(path="IMG_001.dng", size=1000, last_modified="2024-01-01T00:00:00Z"),
        ]

        hash1, _ = computer.compute_file_list_hash_from_file_info(file_infos)
        hash2, _ = computer.compute_file_list_hash_from_file_info(file_infos)

        assert hash1 == hash2

    def test_order_independent(self, computer):
        """Should produce the same hash regardless of input order."""
        file_infos1 = [
            FileInfo(path="a.dng", size=100, last_modified="2024-01-01T00:00:00Z"),
            FileInfo(path="b.dng", size=200, last_modified="2024-01-01T00:00:01Z"),
        ]
        file_infos2 = [
            FileInfo(path="b.dng", size=200, last_modified="2024-01-01T00:00:01Z"),
            FileInfo(path="a.dng", size=100, last_modified="2024-01-01T00:00:00Z"),
        ]

        hash1, _ = computer.compute_file_list_hash_from_file_info(file_infos1)
        hash2, _ = computer.compute_file_list_hash_from_file_info(file_infos2)

        assert hash1 == hash2

    def test_handles_none_last_modified(self, computer):
        """Should handle missing last_modified."""
        file_infos = [
            FileInfo(path="IMG_001.dng", size=1000, last_modified=None),
        ]

        hash_value, count = computer.compute_file_list_hash_from_file_info(file_infos)

        assert len(hash_value) == 64
        assert count == 1


# ============================================================================
# Test: compute_configuration_hash
# ============================================================================

class TestComputeConfigurationHash:
    """Tests for configuration hash computation."""

    def test_produces_64_char_hash(self, computer, sample_config):
        """Should produce a 64-character hex hash."""
        hash_value = computer.compute_configuration_hash(sample_config)

        assert len(hash_value) == 64

    def test_deterministic(self, computer, sample_config):
        """Should produce the same hash for same input."""
        hash1 = computer.compute_configuration_hash(sample_config)
        hash2 = computer.compute_configuration_hash(sample_config)

        assert hash1 == hash2

    def test_extracts_relevant_keys_only(self, computer):
        """Should only include analysis-relevant keys in hash."""
        config1 = {
            "photo_extensions": [".dng"],
            "irrelevant_key": "value1",
        }
        config2 = {
            "photo_extensions": [".dng"],
            "irrelevant_key": "different_value",
        }

        hash1 = computer.compute_configuration_hash(config1)
        hash2 = computer.compute_configuration_hash(config2)

        # Irrelevant keys should not affect hash
        assert hash1 == hash2

    def test_relevant_key_change_produces_different_hash(self, computer):
        """Should detect changes to relevant configuration keys."""
        config1 = {"photo_extensions": [".dng"]}
        config2 = {"photo_extensions": [".dng", ".cr3"]}

        hash1 = computer.compute_configuration_hash(config1)
        hash2 = computer.compute_configuration_hash(config2)

        assert hash1 != hash2


# ============================================================================
# Test: compute_input_state_hash
# ============================================================================

class TestComputeInputStateHash:
    """Tests for combined Input State hash."""

    def test_produces_64_char_hash(self, computer):
        """Should produce a 64-character hex hash."""
        hash_value = computer.compute_input_state_hash(
            file_list_hash="a" * 64,
            configuration_hash="b" * 64,
            tool="photostats"
        )

        assert len(hash_value) == 64

    def test_includes_tool_name(self, computer):
        """Should produce different hash for different tools."""
        hash1 = computer.compute_input_state_hash(
            file_list_hash="a" * 64,
            configuration_hash="b" * 64,
            tool="photostats"
        )
        hash2 = computer.compute_input_state_hash(
            file_list_hash="a" * 64,
            configuration_hash="b" * 64,
            tool="photo_pairing"
        )

        assert hash1 != hash2


# ============================================================================
# Test: check_no_change
# ============================================================================

class TestCheckNoChange:
    """Tests for no-change detection helper."""

    def test_returns_false_when_no_previous_result(self):
        """Should return False when previous_result is None."""
        assert check_no_change(None, "abc123") is False

    def test_returns_false_when_no_previous_hash(self):
        """Should return False when previous_result has no hash."""
        previous = {"guid": "res_123", "input_state_hash": None}
        assert check_no_change(previous, "abc123") is False

    def test_returns_true_when_hashes_match(self):
        """Should return True when hashes match."""
        current_hash = "a" * 64
        previous = {"guid": "res_123", "input_state_hash": current_hash}

        assert check_no_change(previous, current_hash) is True

    def test_returns_false_when_hashes_differ(self):
        """Should return False when hashes differ."""
        previous = {"guid": "res_123", "input_state_hash": "a" * 64}

        assert check_no_change(previous, "b" * 64) is False


# ============================================================================
# Test: Module singleton
# ============================================================================

class TestModuleSingleton:
    """Tests for the module-level singleton."""

    def test_get_input_state_computer_returns_singleton(self):
        """Should return the same instance on multiple calls."""
        computer1 = get_input_state_computer()
        computer2 = get_input_state_computer()

        assert computer1 is computer2

    def test_get_input_state_computer_returns_instance(self):
        """Should return an InputStateComputer instance."""
        computer = get_input_state_computer()

        assert isinstance(computer, InputStateComputer)
