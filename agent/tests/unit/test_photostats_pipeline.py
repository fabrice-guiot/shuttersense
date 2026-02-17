"""
Unit tests for PhotoStats Pipeline integration.

Verifies that PhotoStats produces identical results when using
Pipeline-derived extensions vs Config-based extensions, and
that it falls back gracefully when no Pipeline is available.

Issue #217 - Pipeline-Driven Analysis Tools
Task: T021
"""

import pytest
from unittest.mock import MagicMock, patch

from src.analysis.pipeline_tool_config import PipelineToolConfig, extract_tool_config
from src.remote.base import FileInfo


# ============================================================================
# Fixtures
# ============================================================================


def _make_file_info(name: str, size: int = 1000, path: str = None) -> FileInfo:
    """Create a FileInfo with the given filename."""
    return FileInfo(
        path=path or f"/photos/{name}",
        size=size,
    )


def _make_team_config(**overrides):
    """Create a minimal TeamConfigCache-like mock."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    defaults = {
        "agent_guid": "agt_test",
        "fetched_at": now,
        "expires_at": now + timedelta(hours=24),
        "photo_extensions": [".cr3", ".dng"],
        "metadata_extensions": [".xmp"],
        "require_sidecar": [".cr3"],
        "cameras": {},
        "processing_methods": {},
        "default_pipeline": None,
    }
    defaults.update(overrides)

    from src.cache import TeamConfigCache

    return TeamConfigCache(**defaults)


def _make_pipeline_tool_config(**overrides):
    """Create a PipelineToolConfig with defaults."""
    defaults = {
        "filename_regex": r"^([A-Z0-9]{4})(\d{4})",
        "camera_id_group": 1,
        "photo_extensions": frozenset({".cr3", ".dng"}),
        "metadata_extensions": frozenset({".xmp"}),
        "require_sidecar": frozenset({".cr3"}),
        "processing_suffixes": {},
    }
    defaults.update(overrides)
    return PipelineToolConfig(**defaults)


# ============================================================================
# Test fixtures: file lists
# ============================================================================


@pytest.fixture
def photo_files():
    """Standard set of photo files for testing."""
    return [
        _make_file_info("AB3D0001.cr3", 5000),
        _make_file_info("AB3D0001.xmp", 500),
        _make_file_info("AB3D0002.cr3", 5000),
        _make_file_info("AB3D0002.dng", 6000),
        _make_file_info("AB3D0002.xmp", 500),
        _make_file_info("AB3D0003.cr3", 5000),
        # Orphan: no sidecar for AB3D0003
    ]


# ============================================================================
# Test: Pipeline-derived extensions produce same results as Config
# ============================================================================


class TestPhotostatsWithPipeline:
    """US1: PhotoStats with Pipeline-derived extensions."""

    def test_pipeline_extensions_match_config(self, photo_files):
        """Pipeline-derived and Config-based extensions produce identical results
        when the extension sets are the same."""
        from cli.run import _execute_tool

        team_config = _make_team_config()
        pipeline_config = _make_pipeline_tool_config()

        # Run with Config
        result_config, _ = _execute_tool(
            "photostats", photo_files, "/photos", team_config
        )

        # Run with Pipeline
        result_pipeline, _ = _execute_tool(
            "photostats", photo_files, "/photos", team_config,
            pipeline_tool_config=pipeline_config,
        )

        # Same results
        assert result_config["total_files"] == result_pipeline["total_files"]
        assert result_config["file_counts"] == result_pipeline["file_counts"]
        assert result_config["orphaned_images"] == result_pipeline["orphaned_images"]
        assert result_config["orphaned_xmp"] == result_pipeline["orphaned_xmp"]

    def test_pipeline_with_different_extensions(self, photo_files):
        """Pipeline-derived extensions can differ from Config."""
        from cli.run import _execute_tool

        # Config has .cr3 and .dng
        team_config = _make_team_config()

        # Pipeline only recognizes .cr3 (not .dng)
        pipeline_config = _make_pipeline_tool_config(
            photo_extensions=frozenset({".cr3"}),
        )

        result_config, _ = _execute_tool(
            "photostats", photo_files, "/photos", team_config
        )
        result_pipeline, _ = _execute_tool(
            "photostats", photo_files, "/photos", team_config,
            pipeline_tool_config=pipeline_config,
        )

        # Config sees .dng files; Pipeline doesn't
        assert result_config["file_counts"].get(".dng", 0) == 1
        assert result_pipeline["file_counts"].get(".dng", 0) == 0

    def test_pipeline_sidecar_requirement(self, photo_files):
        """Pipeline-derived sidecar requirements are used for orphan detection."""
        from cli.run import _execute_tool

        team_config = _make_team_config(require_sidecar=[])

        # Config says no sidecar required -> no orphans
        result_no_sidecar, _ = _execute_tool(
            "photostats", photo_files, "/photos", team_config
        )

        # Pipeline says .cr3 requires sidecar
        pipeline_config = _make_pipeline_tool_config(
            require_sidecar=frozenset({".cr3"}),
        )
        result_with_sidecar, _ = _execute_tool(
            "photostats", photo_files, "/photos", team_config,
            pipeline_tool_config=pipeline_config,
        )

        # With sidecar requirement, AB3D0003.cr3 is orphaned (no .xmp)
        assert len(result_no_sidecar["orphaned_images"]) == 0
        assert len(result_with_sidecar["orphaned_images"]) > 0


# ============================================================================
# Test: Fallback when no Pipeline
# ============================================================================


class TestPhotostatsConfigFallback:
    """US1: Fallback to Config when no Pipeline."""

    def test_no_pipeline_uses_config(self, photo_files):
        """When pipeline_tool_config is None, Config extensions are used."""
        from cli.run import _execute_tool

        team_config = _make_team_config()

        result, html = _execute_tool(
            "photostats", photo_files, "/photos", team_config,
            pipeline_tool_config=None,
        )

        # Should still produce valid results
        assert result["total_files"] == len(photo_files)
        assert html is not None


# ============================================================================
# Test: Invalid Pipeline fallback (FR-014)
# ============================================================================


class TestPhotostatsInvalidPipelineFallback:
    """FR-014: Invalid Pipeline logs warning and falls back to Config."""

    def test_invalid_pipeline_falls_back_to_config(self):
        """_resolve_pipeline_config returns None for invalid pipeline."""
        from cli.run import _resolve_pipeline_config
        from src.cache import CachedPipeline

        # Pipeline with no Capture node -> invalid
        team_config = _make_team_config(
            default_pipeline=CachedPipeline(
                guid="pip_test",
                name="Invalid Pipeline",
                version=1,
                nodes=[
                    {"id": "file_1", "type": "file", "properties": {"extension": ".cr3"}},
                ],
                edges=[],
            )
        )

        result = _resolve_pipeline_config(team_config)
        assert result is None

    def test_valid_pipeline_returns_config(self):
        """_resolve_pipeline_config returns PipelineToolConfig for valid pipeline."""
        from cli.run import _resolve_pipeline_config
        from src.cache import CachedPipeline

        team_config = _make_team_config(
            default_pipeline=CachedPipeline(
                guid="pip_test",
                name="Valid Pipeline",
                version=1,
                nodes=[
                    {
                        "id": "capture_1",
                        "type": "capture",
                        "properties": {
                            "filename_regex": r"^([A-Z0-9]{4})(\d{4})",
                            "camera_id_group": "1",
                            "sample_filename": "AB3D0001.cr3",
                        },
                    },
                    {
                        "id": "file_cr3",
                        "type": "file",
                        "properties": {"extension": ".cr3"},
                    },
                ],
                edges=[{"from": "capture_1", "to": "file_cr3"}],
            )
        )

        result = _resolve_pipeline_config(team_config)
        assert result is not None
        assert ".cr3" in result.photo_extensions

    def test_no_default_pipeline_returns_none(self):
        """_resolve_pipeline_config returns None when no default pipeline."""
        from cli.run import _resolve_pipeline_config

        team_config = _make_team_config(default_pipeline=None)
        result = _resolve_pipeline_config(team_config)
        assert result is None
