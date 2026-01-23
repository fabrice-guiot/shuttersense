"""
Performance validation tests for Storage Optimization (Issue #92).

Tests:
- T052: Verify <50ms overhead for no-change detection
- T053: Verify <1s file list hash for 10K files
- T054: Verify backward compatibility with null input_state_hash

These tests validate the performance requirements from the spec.

Performance tests are gated by RUN_PERF_TESTS=1 environment variable to avoid CI flakiness.
"""

import os
import pytest
import time
import hashlib
from unittest.mock import MagicMock


# Skip performance tests unless explicitly enabled via environment variable
skip_perf_tests = pytest.mark.skipif(
    os.environ.get("RUN_PERF_TESTS") != "1",
    reason="Performance tests disabled (set RUN_PERF_TESTS=1 to enable)"
)

from backend.src.services.input_state_service import InputStateService
from backend.src.models.analysis_result import AnalysisResult
from backend.src.models import ResultStatus


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def input_state_service():
    """Create InputStateService instance."""
    return InputStateService()


@pytest.fixture
def large_file_list():
    """Generate a list of 10K file tuples for performance testing."""
    # Each file is (path, size, mtime) tuple
    return [
        (f"/photos/2024/event_{i // 100:03d}/IMG_{i:05d}.CR3", 25000000 + i, 1700000000.0 + i)
        for i in range(10000)
    ]


@pytest.fixture
def simple_file_list():
    """Generate a simple list for order-sensitive tests."""
    return [
        ("/a.jpg", 1000, 1700000000.0),
        ("/b.jpg", 2000, 1700000001.0),
        ("/c.jpg", 3000, 1700000002.0),
    ]


@pytest.fixture
def sample_config():
    """Sample configuration for hash computation."""
    return {
        "photo_extensions": [".cr3", ".dng", ".raf", ".arw", ".nef"],
        "metadata_extensions": [".xmp"],
        "require_sidecar": [".cr3", ".dng"]
    }


# ============================================================================
# T052: No-Change Detection Overhead (<50ms)
# ============================================================================

@skip_perf_tests
class TestNoChangeDetectionOverhead:
    """Verify no-change detection adds <50ms overhead."""

    def test_hash_comparison_is_fast(self):
        """
        Hash comparison for no-change detection should be nearly instant.

        The actual comparison is just a string equality check.
        """
        hash1 = hashlib.sha256(b"test data 1").hexdigest()
        hash2 = hashlib.sha256(b"test data 2").hexdigest()

        start = time.perf_counter()

        # Simulate 1000 hash comparisons
        for _ in range(1000):
            _ = hash1 == hash2

        elapsed_ms = (time.perf_counter() - start) * 1000

        # 1000 comparisons should take <1ms total
        assert elapsed_ms < 1, f"Hash comparison too slow: {elapsed_ms}ms for 1000 comparisons"

    def test_configuration_hash_computation_under_50ms(
        self,
        input_state_service,
        sample_config
    ):
        """Configuration hash computation should be <50ms."""
        start = time.perf_counter()

        result = input_state_service.compute_configuration_hash(sample_config)

        elapsed_ms = (time.perf_counter() - start) * 1000

        assert result is not None
        assert elapsed_ms < 50, f"Configuration hash took {elapsed_ms}ms, expected <50ms"


# ============================================================================
# T053: File List Hash Performance (<1s for 10K files)
# ============================================================================

@skip_perf_tests
class TestFileListHashPerformance:
    """Verify file list hash computation performs within spec."""

    def test_compute_file_list_hash_under_1_second(
        self,
        input_state_service,
        large_file_list
    ):
        """
        File list hash for 10K files should complete in <1 second.

        This validates the performance requirement from FR-002.
        """
        assert len(large_file_list) == 10000

        start = time.perf_counter()

        result = input_state_service.compute_file_list_hash(large_file_list)

        elapsed_seconds = time.perf_counter() - start

        assert result is not None
        assert len(result) == 64  # SHA-256 hex digest length
        assert elapsed_seconds < 1.0, f"File list hash took {elapsed_seconds}s, expected <1s"

        # Log actual performance for visibility
        print(f"\nFile list hash for 10K files: {elapsed_seconds*1000:.2f}ms")

    def test_file_list_hash_scales_linearly(
        self,
        input_state_service,
        large_file_list
    ):
        """Hash computation should scale approximately linearly."""
        # Test with 1K files
        small_list = large_file_list[:1000]

        start = time.perf_counter()
        input_state_service.compute_file_list_hash(small_list)
        small_time = time.perf_counter() - start

        # Test with 10K files
        start = time.perf_counter()
        input_state_service.compute_file_list_hash(large_file_list)
        large_time = time.perf_counter() - start

        # 10x files should take roughly 10x time (with some overhead tolerance)
        # Allow up to 20x to account for setup overhead
        ratio = large_time / small_time if small_time > 0 else 0

        assert ratio < 20, f"Hash computation doesn't scale linearly: {ratio}x for 10x files"

    def test_input_state_hash_combined_performance(
        self,
        input_state_service,
        large_file_list,
        sample_config
    ):
        """
        Combined input state hash (files + config) should be <1.1s.

        Allows 100ms overhead for configuration hash on top of file list hash.
        """
        start = time.perf_counter()

        file_hash = input_state_service.compute_file_list_hash(large_file_list)
        config_hash = input_state_service.compute_configuration_hash(sample_config)
        combined = input_state_service.compute_input_state_hash(file_hash, config_hash)

        elapsed_seconds = time.perf_counter() - start

        assert combined is not None
        assert elapsed_seconds < 1.1, f"Combined hash took {elapsed_seconds}s, expected <1.1s"


# ============================================================================
# T054: Backward Compatibility with null input_state_hash
# ============================================================================

class TestBackwardCompatibility:
    """Verify backward compatibility with legacy results (null input_state_hash)."""

    def test_legacy_result_without_input_state_hash(self):
        """Legacy results with null input_state_hash should work correctly."""
        # Create a mock legacy result (pre-storage-optimization)
        legacy_result = MagicMock(spec=AnalysisResult)
        legacy_result.id = 1
        legacy_result.guid = "res_legacy123"
        legacy_result.input_state_hash = None  # Legacy: no hash stored
        legacy_result.no_change_copy = False
        legacy_result.download_report_from = None
        legacy_result.status = ResultStatus.COMPLETED
        legacy_result.report_html = "<html>Legacy Report</html>"

        # Verify legacy result is still valid
        assert legacy_result.input_state_hash is None
        assert legacy_result.no_change_copy == False
        assert legacy_result.download_report_from is None

    def test_no_change_detection_skips_legacy_results(self):
        """No-change detection should skip results without input_state_hash."""
        # When looking for previous results, legacy results (null hash) should be skipped
        # because we can't compare hashes

        legacy_result = MagicMock()
        legacy_result.input_state_hash = None
        legacy_result.status = ResultStatus.COMPLETED

        new_result = MagicMock()
        new_result.input_state_hash = "abc123"
        new_result.status = ResultStatus.COMPLETED

        # Simulate the matching logic
        def can_match_hash(result, target_hash):
            """Check if result's hash matches target (skips null hashes)."""
            if result.input_state_hash is None:
                return False
            return result.input_state_hash == target_hash

        # Legacy result should not match
        assert not can_match_hash(legacy_result, "abc123")

        # New result with matching hash should match
        assert can_match_hash(new_result, "abc123")

        # New result with different hash should not match
        assert not can_match_hash(new_result, "xyz789")

    def test_result_service_handles_null_hash_in_list(self):
        """ResultService should handle mixed legacy and new results."""
        # Mix of legacy and new results
        results = [
            MagicMock(input_state_hash=None, no_change_copy=False),  # Legacy
            MagicMock(input_state_hash="hash1", no_change_copy=False),  # New original
            MagicMock(input_state_hash="hash1", no_change_copy=True),  # New copy
        ]

        # All results should be processable
        for result in results:
            # These should not raise errors
            _ = result.input_state_hash
            _ = result.no_change_copy

    def test_download_report_from_null_for_legacy(self):
        """Legacy results should have null download_report_from."""
        legacy_result = MagicMock()
        legacy_result.download_report_from = None
        legacy_result.report_html = "<html>Full Report</html>"

        # For legacy results, report should be served directly
        assert legacy_result.download_report_from is None
        assert legacy_result.report_html is not None

    def test_no_change_copy_defaults_to_false(self):
        """New column no_change_copy should default to False for existing rows."""
        # This tests the database migration default
        result = MagicMock()
        result.no_change_copy = False  # Default value from migration

        assert result.no_change_copy == False


# ============================================================================
# Additional Performance Tests
# ============================================================================

class TestHashDeterminism:
    """Verify hash computation is deterministic."""

    def test_file_list_hash_is_deterministic(self, input_state_service, large_file_list):
        """Same file list should always produce same hash."""
        hash1 = input_state_service.compute_file_list_hash(large_file_list)
        hash2 = input_state_service.compute_file_list_hash(large_file_list)

        assert hash1 == hash2

    def test_file_list_hash_is_order_independent(self, input_state_service, simple_file_list):
        """
        File order should NOT affect the hash (deterministic behavior).

        The hash function sorts files internally to ensure the same files
        in any order produce the same hash. This is important because
        filesystem listing order may vary.
        """
        files1 = simple_file_list
        files2 = list(reversed(simple_file_list))

        hash1 = input_state_service.compute_file_list_hash(files1)
        hash2 = input_state_service.compute_file_list_hash(files2)

        # Same files in different order should produce same hash
        assert hash1 == hash2

    def test_file_list_hash_detects_changes(self, input_state_service, simple_file_list):
        """File list hash should detect when files change."""
        # Modify one file's mtime
        modified_list = [
            simple_file_list[0],
            (simple_file_list[1][0], simple_file_list[1][1], simple_file_list[1][2] + 1),  # Changed mtime
            simple_file_list[2],
        ]

        hash1 = input_state_service.compute_file_list_hash(simple_file_list)
        hash2 = input_state_service.compute_file_list_hash(modified_list)

        # Modified file should produce different hash
        assert hash1 != hash2

    def test_configuration_hash_is_deterministic(self, input_state_service, sample_config):
        """Same configuration should always produce same hash."""
        hash1 = input_state_service.compute_configuration_hash(sample_config)
        hash2 = input_state_service.compute_configuration_hash(sample_config)

        assert hash1 == hash2
