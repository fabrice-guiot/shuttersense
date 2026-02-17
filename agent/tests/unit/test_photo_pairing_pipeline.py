"""
Unit tests for Photo_Pairing Pipeline integration.

Tests regex-based filename parsing, processing suffix resolution,
and fallback to FilenameParser when no regex is provided.

Issue #217 - Pipeline-Driven Analysis Tools
Task: T025
"""

import pytest

from src.analysis.photo_pairing_analyzer import build_imagegroups, calculate_analytics
from src.analysis.pipeline_tool_config import PipelineToolConfig
from src.remote.base import FileInfo


# ============================================================================
# Helpers
# ============================================================================


def _fi(name: str, path: str = None) -> FileInfo:
    """Create a FileInfo for testing."""
    return FileInfo(path=path or f"/photos/{name}", size=1000)


# ============================================================================
# Test: Custom regex patterns (FR-009)
# ============================================================================


class TestRegexBasedParsing:
    """T022/T025: build_imagegroups() with Pipeline regex."""

    def test_custom_regex_img_pattern(self):
        """Capture node regex ^(IMG)_([0-9]{4}) with camera_id_group=1."""
        files = [
            _fi("IMG_0001.cr3"),
            _fi("IMG_0001-HDR.cr3"),
            _fi("IMG_0002.cr3"),
        ]
        result = build_imagegroups(
            files,
            filename_regex=r"^(IMG)_(\d{4})",
            camera_id_group=1,
        )

        groups = result["imagegroups"]
        assert len(groups) == 2
        assert groups[0]["camera_id"] == "IMG"
        assert groups[0]["counter"] == "0001"
        assert groups[1]["counter"] == "0002"

    def test_camera_id_group_2(self):
        """camera_id_group=2 uses second capture group as camera ID."""
        files = [
            _fi("0001_SONY.cr3"),
        ]
        result = build_imagegroups(
            files,
            filename_regex=r"^(\d{4})_([A-Z]+)",
            camera_id_group=2,
        )

        groups = result["imagegroups"]
        assert len(groups) == 1
        assert groups[0]["camera_id"] == "SONY"
        assert groups[0]["counter"] == "0001"

    def test_standard_pattern_with_regex(self):
        """Standard AB3D0001 pattern works via regex too."""
        files = [
            _fi("AB3D0001.cr3"),
            _fi("AB3D0001-HDR.cr3"),
            _fi("AB3D0002.cr3"),
        ]
        result = build_imagegroups(
            files,
            filename_regex=r"^([A-Z0-9]{4})(\d{4})",
            camera_id_group=1,
        )

        groups = result["imagegroups"]
        assert len(groups) == 2
        assert groups[0]["camera_id"] == "AB3D"
        assert groups[0]["counter"] == "0001"

    def test_regex_with_processing_suffix(self):
        """Processing suffixes after regex match are extracted."""
        files = [
            _fi("IMG_0001.cr3"),
            _fi("IMG_0001-HDR.cr3"),
            _fi("IMG_0001-BW.cr3"),
        ]
        result = build_imagegroups(
            files,
            filename_regex=r"^(IMG)_(\d{4})",
            camera_id_group=1,
        )

        groups = result["imagegroups"]
        assert len(groups) == 1

        sep = groups[0]["separate_images"][""]
        assert "HDR" in sep["properties"]
        assert "BW" in sep["properties"]

    def test_invalid_regex_falls_back(self):
        """Invalid regex falls back to FilenameParser."""
        files = [
            _fi("AB3D0001.cr3"),
        ]
        result = build_imagegroups(
            files,
            filename_regex="[invalid",  # broken regex
            camera_id_group=1,
        )

        # Should fall back to FilenameParser and still parse
        groups = result["imagegroups"]
        assert len(groups) == 1
        assert groups[0]["camera_id"] == "AB3D"

    def test_regex_no_match_is_invalid(self):
        """Files not matching the regex go to invalid_files."""
        files = [
            _fi("RANDOM_NAME.cr3"),
        ]
        result = build_imagegroups(
            files,
            filename_regex=r"^(IMG)_(\d{4})",
            camera_id_group=1,
        )

        assert len(result["imagegroups"]) == 0
        assert len(result["invalid_files"]) == 1


# ============================================================================
# Test: All-numeric suffix detection unchanged (FR-012)
# ============================================================================


class TestNumericSuffixDetection:
    """FR-012: All-numeric suffixes remain hardcoded as separate_image."""

    def test_numeric_suffix_is_separate_image(self):
        """Suffix -2 is a separate image, not a processing method."""
        files = [
            _fi("IMG_0001.cr3"),
            _fi("IMG_0001-2.cr3"),
            _fi("IMG_0001-3.cr3"),
        ]
        result = build_imagegroups(
            files,
            filename_regex=r"^(IMG)_(\d{4})",
            camera_id_group=1,
        )

        groups = result["imagegroups"]
        assert len(groups) == 1
        sep_images = groups[0]["separate_images"]
        assert "" in sep_images  # base image
        assert "2" in sep_images
        assert "3" in sep_images

    def test_numeric_suffix_with_legacy_parser(self):
        """Numeric suffix detection works with FilenameParser too."""
        files = [
            _fi("AB3D0001.cr3"),
            _fi("AB3D0001-2.cr3"),
        ]
        result = build_imagegroups(files)  # No regex -> FilenameParser

        groups = result["imagegroups"]
        assert len(groups) == 1
        assert "2" in groups[0]["separate_images"]


# ============================================================================
# Test: Fallback to FilenameParser (FR-013)
# ============================================================================


class TestFallbackToFilenameParser:
    """FR-013: No regex -> FilenameParser fallback."""

    def test_no_regex_uses_filename_parser(self):
        """When filename_regex is None, FilenameParser is used."""
        files = [
            _fi("AB3D0001.cr3"),
            _fi("AB3D0001-HDR.cr3"),
            _fi("AB3D0002.cr3"),
        ]
        result = build_imagegroups(files)  # No regex

        groups = result["imagegroups"]
        assert len(groups) == 2
        assert groups[0]["camera_id"] == "AB3D"

    def test_no_regex_invalid_files(self):
        """FilenameParser rejects non-conforming filenames."""
        files = [
            _fi("not_valid.cr3"),
        ]
        result = build_imagegroups(files)  # No regex

        assert len(result["imagegroups"]) == 0
        assert len(result["invalid_files"]) == 1


# ============================================================================
# Test: Processing suffix resolution from Pipeline (FR-010)
# ============================================================================


class TestProcessingSuffixResolution:
    """FR-010: Processing method names from Pipeline Process nodes."""

    def test_pipeline_processing_suffixes(self):
        """calculate_analytics uses processing_suffixes from Pipeline."""
        imagegroups = [
            {
                "group_id": "AB3D0001",
                "camera_id": "AB3D",
                "counter": "0001",
                "separate_images": {
                    "": {
                        "files": ["/photos/AB3D0001.cr3", "/photos/AB3D0001-HDR.cr3"],
                        "properties": ["HDR"],
                    }
                },
            },
        ]

        # Pipeline processing_suffixes: HDR -> "HDR Merge"
        config = {"processing_methods": {"HDR": "HDR Merge"}}
        analytics = calculate_analytics(imagegroups, config)

        assert "HDR Merge" in analytics["method_usage"]
        assert analytics["method_usage"]["HDR Merge"] == 1

    def test_no_pipeline_raw_method_ids(self):
        """Without Pipeline processing_suffixes, raw method IDs are used."""
        imagegroups = [
            {
                "group_id": "AB3D0001",
                "camera_id": "AB3D",
                "counter": "0001",
                "separate_images": {
                    "": {
                        "files": ["/photos/AB3D0001-HDR.cr3"],
                        "properties": ["HDR"],
                    }
                },
            },
        ]

        analytics = calculate_analytics(imagegroups, {})
        assert "HDR" in analytics["method_usage"]


# ============================================================================
# Test: Pipeline-derived photo_extensions for file filtering (FR-011)
# ============================================================================


class TestPipelinePhotoExtensions:
    """FR-011: Photo_Pairing uses Pipeline-derived extensions for filtering."""

    def test_photo_extensions_filter(self):
        """Only files matching Pipeline photo_extensions are processed."""
        from cli.run import _execute_tool
        from datetime import datetime, timedelta, timezone
        from src.cache import TeamConfigCache

        now = datetime.now(timezone.utc)
        team_config = TeamConfigCache(
            agent_guid="agt_test",
            fetched_at=now,
            expires_at=now + timedelta(hours=24),
            photo_extensions=[".cr3", ".dng", ".tiff"],
            metadata_extensions=[".xmp"],
            require_sidecar=[],
        )

        # Pipeline only recognizes .cr3
        pipeline_config = PipelineToolConfig(
            filename_regex=r"^([A-Z0-9]{4})(\d{4})",
            camera_id_group=1,
            photo_extensions=frozenset({".cr3"}),
            metadata_extensions=frozenset({".xmp"}),
            require_sidecar=frozenset(),
            processing_suffixes={},
        )

        files = [
            FileInfo(path="/photos/AB3D0001.cr3", size=5000),
            FileInfo(path="/photos/AB3D0002.dng", size=6000),
            FileInfo(path="/photos/AB3D0003.tiff", size=7000),
        ]

        # With Pipeline: only .cr3 files processed
        result_pipeline, _ = _execute_tool(
            "photo_pairing", files, "/photos", team_config,
            pipeline_tool_config=pipeline_config,
        )
        assert result_pipeline["photo_files"] == 1

        # With Config: .cr3, .dng, .tiff all processed
        result_config, _ = _execute_tool(
            "photo_pairing", files, "/photos", team_config,
        )
        assert result_config["photo_files"] == 3
