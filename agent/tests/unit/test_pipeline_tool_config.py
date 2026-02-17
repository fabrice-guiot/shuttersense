"""
Unit tests for PipelineToolConfig extraction.

Tests extract_tool_config() with various Pipeline structures:
- Linear pipeline
- Branching pipeline
- Multi-file nodes
- Missing Capture node error
- Sidecar inference (optional vs non-optional metadata)
- Extension case-insensitivity
- Deterministic output
- Multiple Capture nodes (uses first)
- File node without extension (skipped)

Issue #217 - Pipeline-Driven Analysis Tools
Task: T013
"""

import pytest

from src.analysis.pipeline_tool_config import (
    METADATA_EXTENSIONS,
    PipelineToolConfig,
    extract_tool_config,
)


# ============================================================================
# Fixtures: Pipeline node/edge builders
# ============================================================================


def _capture_node(
    node_id: str = "capture_1",
    name: str = "Camera Capture",
    filename_regex: str = r"^([A-Z0-9]{4})(\d{4})",
    camera_id_group: str = "1",
    sample_filename: str = "AB3D0001.cr3",
):
    """Build a Capture node dict."""
    return {
        "id": node_id,
        "type": "capture",
        "name": name,
        "properties": {
            "name": name,
            "filename_regex": filename_regex,
            "camera_id_group": camera_id_group,
            "sample_filename": sample_filename,
        },
    }


def _file_node(
    node_id: str,
    extension: str,
    name: str = "",
    optional: bool = False,
):
    """Build a File node dict."""
    props = {"extension": extension}
    if optional:
        props["optional"] = True
    if name:
        props["name"] = name
    return {
        "id": node_id,
        "type": "file",
        "name": name or f"File ({extension})",
        "properties": props,
    }


def _process_node(
    node_id: str,
    name: str,
    method_ids: list[str],
):
    """Build a Process node dict."""
    return {
        "id": node_id,
        "type": "process",
        "name": name,
        "properties": {
            "name": name,
            "method_ids": method_ids,
        },
    }


def _edge(from_id: str, to_id: str):
    """Build an edge dict."""
    return {"from": from_id, "to": to_id}


# ============================================================================
# Test: METADATA_EXTENSIONS constant
# ============================================================================


class TestMetadataExtensions:
    """T001: METADATA_EXTENSIONS constant."""

    def test_contains_xmp(self):
        assert ".xmp" in METADATA_EXTENSIONS

    def test_is_frozenset(self):
        assert isinstance(METADATA_EXTENSIONS, frozenset)


# ============================================================================
# Test: PipelineToolConfig dataclass
# ============================================================================


class TestPipelineToolConfig:
    """T001: PipelineToolConfig dataclass."""

    def test_frozen_dataclass(self):
        config = PipelineToolConfig(
            filename_regex=r"^([A-Z]{4})(\d{4})",
            camera_id_group=1,
            photo_extensions=frozenset({".cr3"}),
            metadata_extensions=frozenset({".xmp"}),
            require_sidecar=frozenset({".cr3"}),
            processing_suffixes={"HDR": "HDR Merge"},
        )
        assert config.filename_regex == r"^([A-Z]{4})(\d{4})"
        assert config.camera_id_group == 1
        assert ".cr3" in config.photo_extensions
        assert ".xmp" in config.metadata_extensions
        assert ".cr3" in config.require_sidecar
        assert config.processing_suffixes["HDR"] == "HDR Merge"

    def test_immutable(self):
        config = PipelineToolConfig(
            filename_regex="test",
            camera_id_group=1,
            photo_extensions=frozenset(),
            metadata_extensions=frozenset(),
            require_sidecar=frozenset(),
        )
        with pytest.raises(AttributeError):
            config.filename_regex = "changed"

    def test_default_processing_suffixes(self):
        config = PipelineToolConfig(
            filename_regex="test",
            camera_id_group=1,
            photo_extensions=frozenset(),
            metadata_extensions=frozenset(),
            require_sidecar=frozenset(),
        )
        assert config.processing_suffixes == {}


# ============================================================================
# Test: extract_tool_config() — linear pipeline
# ============================================================================


class TestExtractToolConfigLinear:
    """T002: Linear pipeline extraction."""

    def test_basic_linear_pipeline(self):
        """Capture -> .cr3 File + .xmp File."""
        nodes = [
            _capture_node(),
            _file_node("file_cr3", ".cr3"),
            _file_node("file_xmp", ".xmp"),
        ]
        edges = [
            _edge("capture_1", "file_cr3"),
            _edge("capture_1", "file_xmp"),
        ]

        config = extract_tool_config(nodes, edges)

        assert config.filename_regex == r"^([A-Z0-9]{4})(\d{4})"
        assert config.camera_id_group == 1
        assert config.photo_extensions == frozenset({".cr3"})
        assert config.metadata_extensions == frozenset({".xmp"})
        # Both non-optional under same parent -> sidecar required
        assert config.require_sidecar == frozenset({".cr3"})

    def test_camera_id_group_2(self):
        """Capture node with camera_id_group=2."""
        nodes = [
            _capture_node(camera_id_group="2"),
            _file_node("file_cr3", ".cr3"),
        ]
        edges = [_edge("capture_1", "file_cr3")]

        config = extract_tool_config(nodes, edges)
        assert config.camera_id_group == 2

    def test_custom_regex(self):
        """Capture node with custom filename_regex."""
        nodes = [
            _capture_node(filename_regex=r"^(IMG)_(\d{4})"),
            _file_node("file_cr3", ".cr3"),
        ]
        edges = [_edge("capture_1", "file_cr3")]

        config = extract_tool_config(nodes, edges)
        assert config.filename_regex == r"^(IMG)_(\d{4})"


# ============================================================================
# Test: extract_tool_config() — branching pipeline
# ============================================================================


class TestExtractToolConfigBranching:
    """T002: Branching pipeline extraction."""

    def test_branching_with_process_nodes(self):
        """Capture -> Process(HDR) -> .dng File; Capture -> Process(BW) -> .tiff File."""
        nodes = [
            _capture_node(),
            _process_node("proc_hdr", "HDR Merge", ["HDR"]),
            _process_node("proc_bw", "Black & White", ["BW"]),
            _file_node("file_dng", ".dng"),
            _file_node("file_tiff", ".tiff"),
        ]
        edges = [
            _edge("capture_1", "proc_hdr"),
            _edge("capture_1", "proc_bw"),
            _edge("proc_hdr", "file_dng"),
            _edge("proc_bw", "file_tiff"),
        ]

        config = extract_tool_config(nodes, edges)

        assert config.photo_extensions == frozenset({".dng", ".tiff"})
        assert config.metadata_extensions == frozenset()
        assert config.processing_suffixes == {"BW": "Black & White", "HDR": "HDR Merge"}


# ============================================================================
# Test: extract_tool_config() — multi-file
# ============================================================================


class TestExtractToolConfigMultiFile:
    """T002: Multi-file pipeline extraction."""

    def test_multiple_image_extensions(self):
        """Pipeline with .cr3, .dng, .heif, and .xmp file nodes."""
        nodes = [
            _capture_node(),
            _file_node("file_cr3", ".cr3"),
            _file_node("file_dng", ".dng"),
            _file_node("file_heif", ".heif"),
            _file_node("file_xmp", ".xmp"),
        ]
        edges = [
            _edge("capture_1", "file_cr3"),
            _edge("capture_1", "file_dng"),
            _edge("capture_1", "file_heif"),
            _edge("capture_1", "file_xmp"),
        ]

        config = extract_tool_config(nodes, edges)

        assert config.photo_extensions == frozenset({".cr3", ".dng", ".heif"})
        assert config.metadata_extensions == frozenset({".xmp"})
        # .heif is image (not in METADATA_EXTENSIONS), FR-002
        assert ".heif" in config.photo_extensions


# ============================================================================
# Test: extract_tool_config() — error cases
# ============================================================================


class TestExtractToolConfigErrors:
    """T002: Error handling."""

    def test_no_capture_node_raises_error(self):
        """Pipeline without Capture node raises ValueError (FR-007)."""
        nodes = [
            _file_node("file_cr3", ".cr3"),
        ]
        edges = []

        with pytest.raises(ValueError, match="no Capture node"):
            extract_tool_config(nodes, edges)

    def test_missing_filename_regex_raises_error(self):
        """Capture node without filename_regex raises ValueError."""
        nodes = [
            {
                "id": "capture_1",
                "type": "capture",
                "name": "Camera",
                "properties": {
                    "name": "Camera",
                    "sample_filename": "AB3D0001.cr3",
                    # No filename_regex!
                },
            },
            _file_node("file_cr3", ".cr3"),
        ]
        edges = [_edge("capture_1", "file_cr3")]

        with pytest.raises(ValueError, match="missing required.*filename_regex"):
            extract_tool_config(nodes, edges)

    def test_empty_pipeline_raises_error(self):
        """Empty pipeline raises ValueError."""
        with pytest.raises(ValueError, match="no Capture node"):
            extract_tool_config([], [])

    def test_no_file_nodes_raises_error(self):
        """Pipeline with Capture but no File nodes raises ValueError (FR-014)."""
        nodes = [_capture_node()]
        edges = []

        with pytest.raises(ValueError, match="no File nodes"):
            extract_tool_config(nodes, edges)

    def test_camera_id_group_out_of_range_defaults_to_1(self):
        """camera_id_group outside {1, 2} defaults to 1."""
        nodes = [
            _capture_node(camera_id_group="5"),
            _file_node("file_cr3", ".cr3"),
        ]
        edges = [_edge("capture_1", "file_cr3")]

        config = extract_tool_config(nodes, edges)
        assert config.camera_id_group == 1


# ============================================================================
# Test: Sidecar inference (T003)
# ============================================================================


class TestSidecarInference:
    """T003: _infer_sidecar_requirements() behavior."""

    def test_non_optional_metadata_creates_sidecar(self):
        """Non-optional .xmp sibling to non-optional .cr3 -> sidecar required."""
        nodes = [
            _capture_node(),
            _file_node("file_cr3", ".cr3"),
            _file_node("file_xmp", ".xmp"),
        ]
        edges = [
            _edge("capture_1", "file_cr3"),
            _edge("capture_1", "file_xmp"),
        ]

        config = extract_tool_config(nodes, edges)
        assert ".cr3" in config.require_sidecar

    def test_optional_metadata_no_sidecar(self):
        """Optional .xmp sibling does NOT create sidecar requirement (FR-004)."""
        nodes = [
            _capture_node(),
            _file_node("file_cr3", ".cr3"),
            _file_node("file_xmp", ".xmp", optional=True),
        ]
        edges = [
            _edge("capture_1", "file_cr3"),
            _edge("capture_1", "file_xmp"),
        ]

        config = extract_tool_config(nodes, edges)
        assert config.require_sidecar == frozenset()

    def test_no_metadata_no_sidecar(self):
        """No metadata File nodes -> no sidecar requirement."""
        nodes = [
            _capture_node(),
            _file_node("file_cr3", ".cr3"),
            _file_node("file_dng", ".dng"),
        ]
        edges = [
            _edge("capture_1", "file_cr3"),
            _edge("capture_1", "file_dng"),
        ]

        config = extract_tool_config(nodes, edges)
        assert config.require_sidecar == frozenset()

    def test_sidecar_from_process_parent(self):
        """Process node as parent with both image and metadata children."""
        nodes = [
            _capture_node(),
            _process_node("proc_1", "Develop", ["Dev"]),
            _file_node("file_dng", ".dng"),
            _file_node("file_xmp", ".xmp"),
        ]
        edges = [
            _edge("capture_1", "proc_1"),
            _edge("proc_1", "file_dng"),
            _edge("proc_1", "file_xmp"),
        ]

        config = extract_tool_config(nodes, edges)
        assert ".dng" in config.require_sidecar

    def test_multiple_image_exts_under_same_parent(self):
        """Multiple image extensions under same parent with non-optional metadata."""
        nodes = [
            _capture_node(),
            _file_node("file_cr3", ".cr3"),
            _file_node("file_dng", ".dng"),
            _file_node("file_xmp", ".xmp"),
        ]
        edges = [
            _edge("capture_1", "file_cr3"),
            _edge("capture_1", "file_dng"),
            _edge("capture_1", "file_xmp"),
        ]

        config = extract_tool_config(nodes, edges)
        assert ".cr3" in config.require_sidecar
        assert ".dng" in config.require_sidecar


# ============================================================================
# Test: Extension case-insensitivity (FR-024)
# ============================================================================


class TestExtensionCaseInsensitivity:
    """FR-024: Extensions normalized to lowercase."""

    def test_uppercase_extensions_normalized(self):
        """Uppercase .CR3 and .XMP are normalized to lowercase."""
        nodes = [
            _capture_node(),
            _file_node("file_cr3", ".CR3"),
            _file_node("file_xmp", ".XMP"),
        ]
        edges = [
            _edge("capture_1", "file_cr3"),
            _edge("capture_1", "file_xmp"),
        ]

        config = extract_tool_config(nodes, edges)
        assert ".cr3" in config.photo_extensions
        assert ".xmp" in config.metadata_extensions

    def test_mixed_case_extensions(self):
        """Mixed case like .Dng is normalized to .dng."""
        nodes = [
            _capture_node(),
            _file_node("file_dng", ".Dng"),
        ]
        edges = [_edge("capture_1", "file_dng")]

        config = extract_tool_config(nodes, edges)
        assert ".dng" in config.photo_extensions


# ============================================================================
# Test: Deterministic output (FR-034)
# ============================================================================


class TestDeterministicOutput:
    """FR-034: Same pipeline always produces same config."""

    def test_deterministic_extensions(self):
        """Extensions are sorted for deterministic frozenset output."""
        nodes = [
            _capture_node(),
            _file_node("file_tiff", ".tiff"),
            _file_node("file_cr3", ".cr3"),
            _file_node("file_dng", ".dng"),
        ]
        edges = [
            _edge("capture_1", "file_tiff"),
            _edge("capture_1", "file_cr3"),
            _edge("capture_1", "file_dng"),
        ]

        config1 = extract_tool_config(nodes, edges)
        config2 = extract_tool_config(nodes, edges)

        assert config1.photo_extensions == config2.photo_extensions
        assert config1 == config2

    def test_deterministic_processing_suffixes(self):
        """Processing suffixes dict is sorted by key."""
        nodes = [
            _capture_node(),
            _file_node("file_cr3", ".cr3"),
            _process_node("proc_bw", "Black & White", ["BW"]),
            _process_node("proc_hdr", "HDR Merge", ["HDR"]),
        ]
        edges = [
            _edge("capture_1", "proc_bw"),
            _edge("capture_1", "proc_hdr"),
            _edge("proc_bw", "file_cr3"),
        ]

        config = extract_tool_config(nodes, edges)

        keys = list(config.processing_suffixes.keys())
        assert keys == sorted(keys)


# ============================================================================
# Test: Multiple Capture nodes (uses first)
# ============================================================================


class TestMultipleCaptureNodes:
    """Edge case: Multiple Capture nodes uses the first one found."""

    def test_uses_first_capture_node(self):
        """When multiple Capture nodes exist, the first one's regex is used."""
        nodes = [
            _capture_node(
                node_id="capture_1",
                filename_regex=r"^([A-Z]{4})(\d{4})",
                camera_id_group="1",
            ),
            _capture_node(
                node_id="capture_2",
                filename_regex=r"^(IMG)_(\d{4})",
                camera_id_group="2",
            ),
            _file_node("file_cr3", ".cr3"),
        ]
        edges = [
            _edge("capture_1", "file_cr3"),
        ]

        config = extract_tool_config(nodes, edges)
        # Should use first capture node's regex
        assert config.filename_regex == r"^([A-Z]{4})(\d{4})"
        assert config.camera_id_group == 1


# ============================================================================
# Test: File node without extension (skipped)
# ============================================================================


class TestFileNodeWithoutExtension:
    """Edge case: File node without extension property is skipped."""

    def test_file_node_no_extension_skipped(self):
        """File node missing extension property is not included."""
        nodes = [
            _capture_node(),
            _file_node("file_cr3", ".cr3"),
            {
                "id": "file_noext",
                "type": "file",
                "name": "Unknown",
                "properties": {},
            },
        ]
        edges = [
            _edge("capture_1", "file_cr3"),
            _edge("capture_1", "file_noext"),
        ]

        config = extract_tool_config(nodes, edges)
        assert config.photo_extensions == frozenset({".cr3"})


# ============================================================================
# Test: Optional File nodes included in extensions (FR-033)
# ============================================================================


class TestOptionalFileExtensions:
    """FR-033: Optional File nodes still included in extension sets."""

    def test_optional_file_in_extensions(self):
        """Optional .xmp File node is still in metadata_extensions."""
        nodes = [
            _capture_node(),
            _file_node("file_cr3", ".cr3"),
            _file_node("file_xmp", ".xmp", optional=True),
        ]
        edges = [
            _edge("capture_1", "file_cr3"),
            _edge("capture_1", "file_xmp"),
        ]

        config = extract_tool_config(nodes, edges)
        # FR-033: optional still included in extension sets
        assert ".xmp" in config.metadata_extensions
        # But NOT in require_sidecar (FR-004)
        assert config.require_sidecar == frozenset()


# ============================================================================
# Test: No Process nodes (empty processing_suffixes)
# ============================================================================


class TestNoProcessNodes:
    """Edge case: Pipeline without Process nodes."""

    def test_empty_processing_suffixes(self):
        """No Process nodes -> empty processing_suffixes map."""
        nodes = [
            _capture_node(),
            _file_node("file_cr3", ".cr3"),
        ]
        edges = [_edge("capture_1", "file_cr3")]

        config = extract_tool_config(nodes, edges)
        assert config.processing_suffixes == {}


# ============================================================================
# Test: Edge format aliases (source/target)
# ============================================================================


class TestEdgeFormatAliases:
    """Edge format with source/target aliases works."""

    def test_source_target_edges(self):
        """Edges using source/target keys instead of from/to."""
        nodes = [
            _capture_node(),
            _file_node("file_cr3", ".cr3"),
            _file_node("file_xmp", ".xmp"),
        ]
        edges = [
            {"source": "capture_1", "target": "file_cr3"},
            {"source": "capture_1", "target": "file_xmp"},
        ]

        config = extract_tool_config(nodes, edges)
        assert ".cr3" in config.photo_extensions
        assert ".xmp" in config.metadata_extensions
        assert ".cr3" in config.require_sidecar
