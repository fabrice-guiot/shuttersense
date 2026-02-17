"""
Pipeline tool configuration extraction.

Extracts tool-relevant configuration from Pipeline node/edge definitions
into a unified PipelineToolConfig dataclass usable by PhotoStats and
Photo_Pairing analysis tools.

Issue #217 - Pipeline-Driven Analysis Tools
Tasks: T001, T002, T003
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set

from src.analysis.pipeline_config_builder import build_pipeline_config

logger = logging.getLogger(__name__)

# Recognized metadata file extensions (FR-002, FR-003)
METADATA_EXTENSIONS: FrozenSet[str] = frozenset({".xmp"})


@dataclass(frozen=True)
class PipelineToolConfig:
    """
    Tool-relevant configuration extracted from a Pipeline definition.

    Not a persistent entity. Created at analysis time from Pipeline
    nodes_json + edges_json via extract_tool_config().

    Attributes:
        filename_regex: Regex pattern for filename parsing (2 capture groups)
        camera_id_group: Which capture group is the camera ID (1 or 2)
        photo_extensions: Image file extensions (lowercase, e.g. {".cr3", ".dng"})
        metadata_extensions: Metadata file extensions (lowercase, e.g. {".xmp"})
        require_sidecar: Image extensions that require a metadata sidecar
        processing_suffixes: method_id -> human-readable display name
    """

    filename_regex: str
    camera_id_group: int
    photo_extensions: FrozenSet[str]
    metadata_extensions: FrozenSet[str]
    require_sidecar: FrozenSet[str]
    processing_suffixes: Dict[str, str] = field(default_factory=dict)


def extract_tool_config(
    nodes_json: List[Dict[str, Any]],
    edges_json: List[Dict[str, Any]],
) -> PipelineToolConfig:
    """
    Extract tool configuration from Pipeline node/edge definitions.

    Uses build_pipeline_config() to parse nodes, then extracts:
    - filename_regex and camera_id_group from the first Capture node
    - photo/metadata extensions from File nodes (by exclusion against METADATA_EXTENSIONS)
    - require_sidecar inferred from sibling File nodes under common parents
    - processing_suffixes from Process node method_ids -> names

    Args:
        nodes_json: Pipeline node definitions from server/cache
        edges_json: Pipeline edge definitions from server/cache

    Returns:
        PipelineToolConfig with all extracted configuration

    Raises:
        ValueError: If the Pipeline has no Capture node (FR-007)
    """
    pipeline_config = build_pipeline_config(nodes_json, edges_json)

    # --- Capture node: filename_regex and camera_id_group (FR-006, FR-007) ---
    if not pipeline_config.capture_nodes:
        raise ValueError(
            "Pipeline has no Capture node. "
            "A Capture node with filename_regex is required for tool configuration."
        )

    capture_node = pipeline_config.capture_nodes[0]
    # Read properties from raw nodes_json (not available on CaptureNode dataclass)
    capture_props = _get_node_properties(nodes_json, capture_node.id)

    filename_regex = capture_props.get("filename_regex", "")
    if not filename_regex:
        raise ValueError(
            f"Capture node '{capture_node.id}' is missing required "
            f"'filename_regex' property."
        )

    camera_id_group_raw = capture_props.get("camera_id_group", "1")
    try:
        camera_id_group = int(camera_id_group_raw)
    except (ValueError, TypeError):
        camera_id_group = 1
    if camera_id_group not in (1, 2):
        camera_id_group = 1

    # --- File nodes: photo and metadata extensions (FR-002, FR-003, FR-024) ---
    if not pipeline_config.file_nodes:
        raise ValueError(
            "Pipeline has no File nodes. "
            "Cannot derive photo/metadata extensions for tool configuration."
        )
    photo_extensions: Set[str] = set()
    metadata_extensions: Set[str] = set()

    for file_node in pipeline_config.file_nodes:
        ext = file_node.extension
        if not ext:
            # Skip File nodes without extension property
            continue
        ext_lower = ext.lower()
        if not ext_lower.startswith("."):
            ext_lower = "." + ext_lower

        if ext_lower in METADATA_EXTENSIONS:
            metadata_extensions.add(ext_lower)
        else:
            photo_extensions.add(ext_lower)

    # --- Sidecar inference (FR-004) ---
    require_sidecar = _infer_sidecar_requirements(
        nodes_json, edges_json, photo_extensions, metadata_extensions
    )

    # --- Processing suffixes (FR-005) ---
    processing_suffixes: Dict[str, str] = {}
    for process_node in pipeline_config.process_nodes:
        for method_id in process_node.method_ids:
            processing_suffixes[method_id] = process_node.name

    return PipelineToolConfig(
        filename_regex=filename_regex,
        camera_id_group=camera_id_group,
        photo_extensions=frozenset(sorted(photo_extensions)),
        metadata_extensions=frozenset(sorted(metadata_extensions)),
        require_sidecar=frozenset(sorted(require_sidecar)),
        processing_suffixes=dict(sorted(processing_suffixes.items())),
    )


def _get_node_properties(
    nodes_json: List[Dict[str, Any]],
    node_id: str,
) -> Dict[str, Any]:
    """Get properties dict for a node by ID from raw nodes_json."""
    for node in nodes_json:
        if node.get("id") == node_id:
            return node.get("properties", {})
    return {}


def _infer_sidecar_requirements(
    nodes_json: List[Dict[str, Any]],
    edges_json: List[Dict[str, Any]],
    photo_extensions: Set[str],
    metadata_extensions: Set[str],
) -> Set[str]:
    """
    Infer which image extensions require a metadata sidecar.

    A sidecar requirement is inferred when a parent node has edges to both:
    - A non-optional image File node
    - A non-optional metadata File node

    Optional File nodes (properties.optional = true) do NOT create
    sidecar requirements (FR-004).

    Args:
        nodes_json: Raw pipeline node definitions
        edges_json: Raw pipeline edge definitions
        photo_extensions: Already-categorized image extensions
        metadata_extensions: Already-categorized metadata extensions

    Returns:
        Set of image extensions that require sidecars
    """
    if not metadata_extensions:
        return set()

    # Build parent -> children map from edges
    parent_children: Dict[str, List[str]] = {}
    for edge in edges_json:
        from_id = edge.get("from") or edge.get("source")
        to_id = edge.get("to") or edge.get("target")
        if from_id and to_id:
            parent_children.setdefault(from_id, []).append(to_id)

    # Build node lookup for quick access
    node_lookup: Dict[str, Dict[str, Any]] = {}
    for node in nodes_json:
        node_id = node.get("id")
        if node_id:
            node_lookup[node_id] = node

    require_sidecar: Set[str] = set()

    # For each parent node, check if it has both non-optional image
    # and non-optional metadata File children
    for parent_id, children_ids in parent_children.items():
        non_optional_image_exts: Set[str] = set()
        has_non_optional_metadata = False

        for child_id in children_ids:
            child_node = node_lookup.get(child_id)
            if not child_node:
                continue

            node_type = child_node.get("type", "").lower()
            if node_type != "file":
                continue

            props = child_node.get("properties", {})
            ext = props.get("extension", "")
            if not ext:
                continue

            ext_lower = ext.lower()
            if not ext_lower.startswith("."):
                ext_lower = "." + ext_lower

            is_optional = props.get("optional", False)
            if is_optional:
                continue

            if ext_lower in metadata_extensions:
                has_non_optional_metadata = True
            elif ext_lower in photo_extensions:
                non_optional_image_exts.add(ext_lower)

        if has_non_optional_metadata and non_optional_image_exts:
            require_sidecar.update(non_optional_image_exts)

    return require_sidecar
