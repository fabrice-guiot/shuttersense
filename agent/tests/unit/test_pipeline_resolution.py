"""
Unit tests for Pipeline resolution per Collection.

Tests _resolve_pipeline_config() and input_state_hash integration:
- Team default pipeline resolution
- Config fallback when no pipeline
- Invalid pipeline warning + fallback
- Offline with cached pipeline
- input_state_hash includes pipeline data

Issue #217 - Pipeline-Driven Analysis Tools
Task: T046
"""

import hashlib
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from cli.run import _resolve_pipeline_config, _prepare_analysis
from src.cache import CachedPipeline, TeamConfigCache
from src.analysis.pipeline_tool_config import PipelineToolConfig


# ============================================================================
# Fixtures
# ============================================================================


def _make_team_config(**overrides) -> TeamConfigCache:
    """Create a minimal TeamConfigCache."""
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
    return TeamConfigCache(**defaults)


def _valid_pipeline_nodes():
    """Return valid pipeline nodes with Capture and File nodes."""
    return [
        {
            "id": "capture_1",
            "type": "capture",
            "properties": {
                "name": "Camera Capture",
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
        {
            "id": "file_xmp",
            "type": "file",
            "properties": {"extension": ".xmp"},
        },
    ]


def _valid_pipeline_edges():
    """Return edges for valid pipeline."""
    return [
        {"from": "capture_1", "to": "file_cr3"},
        {"from": "capture_1", "to": "file_xmp"},
    ]


def _invalid_pipeline_nodes():
    """Return invalid pipeline nodes (no Capture node)."""
    return [
        {
            "id": "file_cr3",
            "type": "file",
            "properties": {"extension": ".cr3"},
        },
    ]


# ============================================================================
# Test: Team default pipeline resolution
# ============================================================================


class TestTeamDefaultPipelineResolution:
    """T043: Resolve team default pipeline."""

    def test_resolves_team_default_pipeline(self):
        """When team has a default pipeline, extract tool config from it."""
        team_config = _make_team_config(
            default_pipeline=CachedPipeline(
                guid="pip_test",
                name="Default Pipeline",
                version=1,
                nodes=_valid_pipeline_nodes(),
                edges=_valid_pipeline_edges(),
            )
        )

        result = _resolve_pipeline_config(team_config)

        assert result is not None
        assert ".cr3" in result.photo_extensions
        assert ".xmp" in result.metadata_extensions
        assert result.filename_regex == r"^([A-Z0-9]{4})(\d{4})"

    def test_pipeline_with_process_nodes(self):
        """Pipeline with Process nodes extracts processing_suffixes."""
        nodes = _valid_pipeline_nodes() + [
            {
                "id": "proc_hdr",
                "type": "process",
                "name": "HDR Merge",
                "properties": {
                    "name": "HDR Merge",
                    "method_ids": ["HDR"],
                },
            },
        ]
        edges = _valid_pipeline_edges() + [
            {"from": "capture_1", "to": "proc_hdr"},
        ]

        team_config = _make_team_config(
            default_pipeline=CachedPipeline(
                guid="pip_test",
                name="Pipeline with HDR",
                version=1,
                nodes=nodes,
                edges=edges,
            )
        )

        result = _resolve_pipeline_config(team_config)
        assert result is not None
        assert result.processing_suffixes.get("HDR") == "HDR Merge"


# ============================================================================
# Test: Config fallback when no pipeline
# ============================================================================


class TestConfigFallback:
    """T043: Fallback to Config when no Pipeline available."""

    def test_no_default_pipeline_returns_none(self):
        """When team has no default pipeline, return None for Config fallback."""
        team_config = _make_team_config(default_pipeline=None)

        result = _resolve_pipeline_config(team_config)
        assert result is None


# ============================================================================
# Test: Invalid pipeline warning + fallback (FR-014)
# ============================================================================


class TestInvalidPipelineFallback:
    """FR-014: Invalid pipeline falls back to Config with warning."""

    def test_missing_capture_node_returns_none(self):
        """Pipeline without Capture node returns None."""
        team_config = _make_team_config(
            default_pipeline=CachedPipeline(
                guid="pip_invalid",
                name="Invalid Pipeline",
                version=1,
                nodes=_invalid_pipeline_nodes(),
                edges=[],
            )
        )

        result = _resolve_pipeline_config(team_config)
        assert result is None

    def test_missing_filename_regex_returns_none(self):
        """Pipeline with Capture node but no filename_regex returns None."""
        nodes = [
            {
                "id": "capture_1",
                "type": "capture",
                "properties": {
                    "name": "Camera",
                    "sample_filename": "AB3D0001.cr3",
                    # No filename_regex!
                },
            },
            {"id": "file_cr3", "type": "file", "properties": {"extension": ".cr3"}},
        ]

        team_config = _make_team_config(
            default_pipeline=CachedPipeline(
                guid="pip_invalid",
                name="Pipeline Without Regex",
                version=1,
                nodes=nodes,
                edges=[{"from": "capture_1", "to": "file_cr3"}],
            )
        )

        result = _resolve_pipeline_config(team_config)
        assert result is None


# ============================================================================
# Test: Offline with cached pipeline
# ============================================================================


class TestOfflineCachedPipeline:
    """T045: Offline mode uses cached pipeline from TeamConfigCache."""

    def test_cached_pipeline_resolves_config(self):
        """TeamConfigCache.default_pipeline provides cached pipeline data."""
        # This simulates offline mode: team_config was loaded from cache
        team_config = _make_team_config(
            default_pipeline=CachedPipeline(
                guid="pip_cached",
                name="Cached Pipeline",
                version=2,
                nodes=_valid_pipeline_nodes(),
                edges=_valid_pipeline_edges(),
            )
        )

        result = _resolve_pipeline_config(team_config)
        assert result is not None
        assert ".cr3" in result.photo_extensions

    def test_expired_cache_still_resolves(self):
        """Even with expired cache, pipeline resolution works."""
        past = datetime.now(timezone.utc) - timedelta(hours=48)
        team_config = TeamConfigCache(
            agent_guid="agt_test",
            fetched_at=past,
            expires_at=past + timedelta(hours=24),  # expired
            photo_extensions=[".cr3"],
            metadata_extensions=[".xmp"],
            require_sidecar=[],
            default_pipeline=CachedPipeline(
                guid="pip_old",
                name="Old Pipeline",
                version=1,
                nodes=_valid_pipeline_nodes(),
                edges=_valid_pipeline_edges(),
            ),
        )

        result = _resolve_pipeline_config(team_config)
        assert result is not None


# ============================================================================
# Test: input_state_hash includes pipeline data (T044)
# ============================================================================


class TestInputStateHashWithPipeline:
    """T044: Hash changes when pipeline changes."""

    def test_hash_differs_with_and_without_pipeline(self, tmp_path):
        """input_state_hash is different with vs without PipelineToolConfig."""
        # Create a temp directory with a file
        test_file = tmp_path / "AB3D0001.cr3"
        test_file.write_bytes(b"test content")

        team_config = _make_team_config()

        pipeline_config = PipelineToolConfig(
            filename_regex=r"^([A-Z0-9]{4})(\d{4})",
            camera_id_group=1,
            photo_extensions=frozenset({".cr3"}),
            metadata_extensions=frozenset({".xmp"}),
            require_sidecar=frozenset(),
            processing_suffixes={},
        )

        # Hash without pipeline
        _, hash_without = _prepare_analysis(
            str(tmp_path), "photostats", team_config
        )

        # Hash with pipeline
        _, hash_with = _prepare_analysis(
            str(tmp_path), "photostats", team_config,
            pipeline_tool_config=pipeline_config,
        )

        assert hash_without != hash_with

    def test_same_pipeline_same_hash(self, tmp_path):
        """Same PipelineToolConfig produces same hash."""
        test_file = tmp_path / "AB3D0001.cr3"
        test_file.write_bytes(b"test content")

        team_config = _make_team_config()

        pipeline_config = PipelineToolConfig(
            filename_regex=r"^([A-Z0-9]{4})(\d{4})",
            camera_id_group=1,
            photo_extensions=frozenset({".cr3"}),
            metadata_extensions=frozenset({".xmp"}),
            require_sidecar=frozenset(),
            processing_suffixes={},
        )

        _, hash1 = _prepare_analysis(
            str(tmp_path), "photostats", team_config,
            pipeline_tool_config=pipeline_config,
        )
        _, hash2 = _prepare_analysis(
            str(tmp_path), "photostats", team_config,
            pipeline_tool_config=pipeline_config,
        )

        assert hash1 == hash2

    def test_different_pipeline_different_hash(self, tmp_path):
        """Different PipelineToolConfig produces different hash."""
        test_file = tmp_path / "AB3D0001.cr3"
        test_file.write_bytes(b"test content")

        team_config = _make_team_config()

        pipeline_config_1 = PipelineToolConfig(
            filename_regex=r"^([A-Z0-9]{4})(\d{4})",
            camera_id_group=1,
            photo_extensions=frozenset({".cr3"}),
            metadata_extensions=frozenset({".xmp"}),
            require_sidecar=frozenset(),
            processing_suffixes={},
        )

        pipeline_config_2 = PipelineToolConfig(
            filename_regex=r"^(IMG)_(\d{4})",  # Different regex
            camera_id_group=1,
            photo_extensions=frozenset({".cr3"}),
            metadata_extensions=frozenset({".xmp"}),
            require_sidecar=frozenset(),
            processing_suffixes={},
        )

        _, hash1 = _prepare_analysis(
            str(tmp_path), "photostats", team_config,
            pipeline_tool_config=pipeline_config_1,
        )
        _, hash2 = _prepare_analysis(
            str(tmp_path), "photostats", team_config,
            pipeline_tool_config=pipeline_config_2,
        )

        assert hash1 != hash2
