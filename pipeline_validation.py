#!/usr/bin/env python3
"""
Photo Processing Pipeline Validation Tool

Validates photo collections against user-defined processing workflows (pipelines)
defined as directed graphs of nodes. Integrates with Photo Pairing Tool to obtain
file groupings, traverses pipeline paths, and classifies images as CONSISTENT,
CONSISTENT-WITH-WARNING, PARTIAL, or INCONSISTENT.

Core Value: Automated validation of 10,000+ image groups in under 60 seconds
(with caching), enabling photographers to identify incomplete processing workflows
and assess archival readiness without manual file inspection.

Usage:
    python3 pipeline_validation.py <folder_path>
    python3 pipeline_validation.py <folder_path> --config <config_path>
    python3 pipeline_validation.py <folder_path> --force-regenerate
    python3 pipeline_validation.py --help

Author: photo-admin project
License: AGPL-3.0
Version: 1.0.0
"""

import argparse
import sys
import signal
import yaml
import json
import hashlib
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from enum import Enum

# Import shared configuration manager
from utils.config_manager import PhotoAdminConfig

# Tool version (semantic versioning)
TOOL_VERSION = "1.0.0"

# Maximum loop iterations per node to prevent infinite path enumeration
# Applied to all node types except Capture and Termination nodes
MAX_ITERATIONS = 5


# =============================================================================
# Data Structures - Pipeline Configuration
# =============================================================================

@dataclass
class NodeBase:
    """Base class for all pipeline nodes."""
    id: str
    type: str
    name: str
    output: List[str]


@dataclass
class CaptureNode(NodeBase):
    """
    Capture Node - Starting point of pipeline.

    Represents the camera capture event that produces initial files.
    Must have at least one output (typically raw files).
    """
    type: str = field(default="Capture", init=False)


@dataclass
class FileNode(NodeBase):
    """
    File Node - Represents an expected file in the workflow.

    Attributes:
        extension: File extension including leading dot (e.g., ".CR3", ".DNG", ".XMP")
    """
    extension: str
    type: str = field(default="File", init=False)


@dataclass
class ProcessNode(NodeBase):
    """
    Process Node - Editing/conversion step that adds suffixes to filenames.

    Attributes:
        method_ids: List of processing method IDs that add suffixes.
                   Empty string means no suffix added (selection only).
                   Examples: [""], ["DxO_DeepPRIME_XD2s"], ["Edit"]
    """
    method_ids: List[str]
    type: str = field(default="Process", init=False)


@dataclass
class PairingNode(NodeBase):
    """
    Pairing Node - Multi-image merge operation (HDR, Panorama, Focus Stack).

    Attributes:
        pairing_type: Human-readable pairing operation type
        input_count: Expected number of input images
    """
    pairing_type: str
    input_count: int
    type: str = field(default="Pairing", init=False)


@dataclass
class BranchingNode(NodeBase):
    """
    Branching Node - Conditional path selection.

    Validation explores ALL branches (not just one path).

    Attributes:
        condition_description: Human-readable explanation of branching condition
    """
    condition_description: str
    type: str = field(default="Branching", init=False)


@dataclass
class TerminationNode(NodeBase):
    """
    Termination Node - End of pipeline (archival ready state).

    Represents a valid archival state. Images matching a path to this
    termination are considered archival ready for this termination type.

    Attributes:
        termination_type: Type of archival state (e.g., "Black Box Archive")
    """
    termination_type: str
    type: str = field(default="Termination", init=False)


# Type alias for any pipeline node
PipelineNode = Union[CaptureNode, FileNode, ProcessNode, PairingNode, BranchingNode, TerminationNode]


@dataclass
class PipelineConfig:
    """
    Complete pipeline configuration containing all nodes.

    Attributes:
        nodes: List of all pipeline nodes
        nodes_by_id: Dictionary mapping node IDs to node objects (populated after init)
    """
    nodes: List[PipelineNode]
    nodes_by_id: Dict[str, PipelineNode] = field(default_factory=dict, init=False)

    def __post_init__(self):
        """Build node ID lookup dictionary after initialization."""
        self.nodes_by_id = {node.id: node for node in self.nodes}


# =============================================================================
# Data Structures - Validation Results
# =============================================================================

class ValidationStatus(Enum):
    """
    Validation status classification for image completeness.

    Values:
        CONSISTENT: All expected files present, no extra files
        CONSISTENT_WITH_WARNING: All expected files present, but extra files exist
        PARTIAL: Some expected files missing (incomplete workflow)
        INCONSISTENT: No matching pipeline paths (wrong files or completely wrong)
    """
    CONSISTENT = "CONSISTENT"
    CONSISTENT_WITH_WARNING = "CONSISTENT-WITH-WARNING"
    PARTIAL = "PARTIAL"
    INCONSISTENT = "INCONSISTENT"


@dataclass
class SpecificImage:
    """
    Represents a single image within an ImageGroup.

    Flattened from ImageGroup's separate_images structure.

    Attributes:
        unique_id: Unique identifier (base_filename: camera_id + counter + suffix)
        group_id: Parent ImageGroup ID (camera_id + counter)
        camera_id: 4-character camera identifier
        counter: 4-digit counter string
        suffix: Separate image suffix ("" for primary, "2", "HDR", etc.)
        actual_files: List of actual files found for this specific image
    """
    unique_id: str
    group_id: str
    camera_id: str
    counter: str
    suffix: str
    actual_files: List[str]


@dataclass
class TerminationMatchResult:
    """
    Validation result for one termination node path.

    Attributes:
        termination_id: Termination node ID
        termination_type: Human-readable termination type
        status: Validation status for this termination
        completion_percentage: Percentage of expected files present (0-100)
        expected_files: List of all expected files for this termination
        actual_files: List of actual files present
        missing_files: List of missing expected files
        extra_files: List of extra files not in pipeline
        truncated: Whether path was truncated due to loop limit
        truncation_note: Explanation of truncation (None if not truncated)
    """
    termination_id: str
    termination_type: str
    status: ValidationStatus
    completion_percentage: float
    expected_files: List[str]
    actual_files: List[str]
    missing_files: List[str]
    extra_files: List[str]
    truncated: bool
    truncation_note: Optional[str] = None


@dataclass
class ValidationResult:
    """
    Complete validation result for one SpecificImage.

    Attributes:
        unique_id: Specific image unique identifier (base_filename)
        group_id: Parent ImageGroup ID
        camera_id: Camera identifier
        counter: Counter string
        suffix: Separate image suffix
        actual_files: Actual files found
        termination_matches: List of validation results per termination node
        overall_status: Worst status across all terminations
        archival_ready_for: List of termination types that are archival ready
    """
    unique_id: str
    group_id: str
    camera_id: str
    counter: str
    suffix: str
    actual_files: List[str]
    termination_matches: List[TerminationMatchResult]
    overall_status: ValidationStatus
    archival_ready_for: List[str]


# =============================================================================
# Pipeline Configuration Loading
# =============================================================================

def parse_node_from_yaml(node_dict: Dict[str, Any]) -> PipelineNode:
    """
    Parse a pipeline node from YAML dictionary.

    Args:
        node_dict: Dictionary containing node configuration from YAML

    Returns:
        Appropriate node object based on 'type' field

    Raises:
        ValueError: If node type is invalid or required fields are missing
    """
    node_type = node_dict.get('type')
    node_id = node_dict.get('id')
    name = node_dict.get('name')
    output = node_dict.get('output', [])

    if not all([node_type, node_id, name]):
        raise ValueError(f"Missing required fields (id, type, name) in node: {node_dict}")

    # Dispatch based on node type
    if node_type == 'Capture':
        return CaptureNode(
            id=node_id,
            name=name,
            output=output
        )
    elif node_type == 'File':
        extension = node_dict.get('extension')
        if not extension:
            raise ValueError(f"File node '{node_id}' missing required 'extension' field")
        return FileNode(
            id=node_id,
            name=name,
            output=output,
            extension=extension
        )
    elif node_type == 'Process':
        method_ids = node_dict.get('method_ids')
        if method_ids is None:
            raise ValueError(f"Process node '{node_id}' missing required 'method_ids' field")
        return ProcessNode(
            id=node_id,
            name=name,
            output=output,
            method_ids=method_ids
        )
    elif node_type == 'Pairing':
        pairing_type = node_dict.get('pairing_type')
        input_count = node_dict.get('input_count')
        if not pairing_type or input_count is None:
            raise ValueError(f"Pairing node '{node_id}' missing required fields (pairing_type, input_count)")
        return PairingNode(
            id=node_id,
            name=name,
            output=output,
            pairing_type=pairing_type,
            input_count=input_count
        )
    elif node_type == 'Branching':
        condition_description = node_dict.get('condition_description')
        if not condition_description:
            raise ValueError(f"Branching node '{node_id}' missing required 'condition_description' field")
        return BranchingNode(
            id=node_id,
            name=name,
            output=output,
            condition_description=condition_description
        )
    elif node_type == 'Termination':
        termination_type = node_dict.get('termination_type')
        if not termination_type:
            raise ValueError(f"Termination node '{node_id}' missing required 'termination_type' field")
        return TerminationNode(
            id=node_id,
            name=name,
            output=output,
            termination_type=termination_type
        )
    else:
        raise ValueError(f"Unknown node type: {node_type} (node: {node_id})")


def load_pipeline_config(config: PhotoAdminConfig, pipeline_name: str = 'default', verbose: bool = False) -> PipelineConfig:
    """
    Load pipeline configuration using PhotoAdminConfig.

    Per project constitution: All config interaction must go through PhotoAdminConfig.

    Args:
        config: PhotoAdminConfig instance
        pipeline_name: Name of the pipeline to load (default: 'default')
                      Supports versioned pipelines (e.g., 'default', 'v2', 'experimental')
        verbose: If True, print detailed loading information

    Returns:
        PipelineConfig object with all parsed nodes

    Raises:
        ValueError: If pipeline structure is invalid or nodes cannot be parsed
    """
    # Get pipeline configuration from PhotoAdminConfig (handles all YAML access)
    pipeline_config = config.get_pipeline_config(pipeline_name, verbose=verbose)

    # Extract nodes list from the pipeline
    nodes_list = pipeline_config.get('nodes', [])

    # Parse each node into typed node objects
    nodes = []
    for i, node_dict in enumerate(nodes_list):
        try:
            node = parse_node_from_yaml(node_dict)
            nodes.append(node)
            if verbose:
                print(f"    Parsed node {i}: {node.id} ({node.type})")
        except ValueError as e:
            raise ValueError(f"Error parsing node at index {i} in pipeline '{pipeline_name}': {e}")

    # Create and return PipelineConfig
    if verbose:
        print(f"  Successfully loaded pipeline with {len(nodes)} nodes")

    return PipelineConfig(nodes=nodes)


def validate_pipeline_structure(pipeline: PipelineConfig, config) -> List[str]:
    """
    Validate pipeline structure for consistency and correctness.

    Performs the following validation checks:
    1. Exactly one Capture node exists
    2. At least one Termination node exists
    3. All output references point to existing nodes
    4. No orphaned nodes (all reachable from Capture)
    5. No duplicate node IDs (already enforced by PipelineConfig)
    6. File extensions match photo_extensions or metadata_extensions
    7. Processing method_ids exist in processing_methods config

    Args:
        pipeline: PipelineConfig to validate
        config: PhotoAdminConfig with photo_extensions, metadata_extensions, processing_methods

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check 1: Exactly one Capture node
    capture_nodes = [n for n in pipeline.nodes if isinstance(n, CaptureNode)]
    if len(capture_nodes) == 0:
        errors.append("Pipeline must have exactly one Capture node (found 0)")
    elif len(capture_nodes) > 1:
        capture_ids = [n.id for n in capture_nodes]
        errors.append(f"Pipeline must have exactly one Capture node (found {len(capture_nodes)}: {capture_ids})")

    # Check 2: At least one Termination node
    termination_nodes = [n for n in pipeline.nodes if isinstance(n, TerminationNode)]
    if len(termination_nodes) == 0:
        errors.append("Pipeline must have at least one Termination node")

    # Check 3: All output references point to existing nodes
    for node in pipeline.nodes:
        for output_id in node.output:
            if output_id not in pipeline.nodes_by_id:
                errors.append(f"Node '{node.id}' references non-existent output node '{output_id}'")

    # Check 4: No orphaned nodes (all reachable from Capture)
    if capture_nodes:
        capture_node = capture_nodes[0]
        reachable = set()
        visited = set()

        def dfs(node_id: str):
            """Depth-first search to find all reachable nodes."""
            if node_id in visited:
                return
            visited.add(node_id)
            reachable.add(node_id)

            if node_id in pipeline.nodes_by_id:
                node = pipeline.nodes_by_id[node_id]
                for output_id in node.output:
                    dfs(output_id)

        # Start DFS from Capture node
        dfs(capture_node.id)

        # Find orphaned nodes
        all_node_ids = set(pipeline.nodes_by_id.keys())
        orphaned = all_node_ids - reachable
        if orphaned:
            errors.append(f"Pipeline has orphaned nodes (unreachable from Capture): {sorted(orphaned)}")

    # Check 6: File extensions validation
    valid_photo_extensions = [ext.lower() for ext in config.photo_extensions]
    valid_metadata_extensions = [ext.lower() for ext in config.metadata_extensions]
    valid_extensions = valid_photo_extensions + valid_metadata_extensions

    for node in pipeline.nodes:
        if isinstance(node, FileNode):
            ext_lower = node.extension.lower()
            if ext_lower not in valid_extensions:
                # Convert sets to sorted list for display
                all_valid_extensions = sorted(config.photo_extensions | config.metadata_extensions)
                errors.append(
                    f"File node '{node.id}' has invalid extension '{node.extension}'. "
                    f"Must be one of: {', '.join(all_valid_extensions)}"
                )

    # Check 7: Processing method_ids validation
    valid_method_ids = set(config.processing_methods.keys())
    # Empty string is always valid (means no suffix)
    valid_method_ids.add('')

    for node in pipeline.nodes:
        if isinstance(node, ProcessNode):
            for method_id in node.method_ids:
                if method_id not in valid_method_ids:
                    available = [k for k in sorted(valid_method_ids) if k != '']
                    errors.append(
                        f"Process node '{node.id}' references undefined processing method '{method_id}'. "
                        f"Available methods: {', '.join(available) if available else '(none defined)'}"
                    )

    return errors


# =============================================================================
# Photo Pairing Tool Integration
# =============================================================================

def load_or_generate_imagegroups(folder_path: Path, force_regenerate: bool = False) -> List[Dict[str, Any]]:
    """
    Load ImageGroups from Photo Pairing cache or generate if missing.

    This function integrates with the Photo Pairing Tool by either:
    1. Loading existing .photo_pairing_imagegroups cache file
    2. Running Photo Pairing Tool to generate ImageGroups (if cache missing)

    Args:
        folder_path: Path to folder containing photos
        force_regenerate: If True, ignore cache and regenerate from scratch

    Returns:
        List of ImageGroup dictionaries from Photo Pairing Tool

    Raises:
        FileNotFoundError: If cache doesn't exist and can't generate
        ValueError: If cache is invalid or corrupted
    """
    import photo_pairing

    cache_file = folder_path / '.photo_pairing_imagegroups'

    # If force_regenerate, run Photo Pairing Tool
    if force_regenerate or not cache_file.exists():
        print(f"Running Photo Pairing Tool to generate ImageGroups...")

        # Use photo_pairing module directly
        # Note: This assumes photo_pairing can be imported as a module
        try:
            # Get all files in folder
            all_files = list(folder_path.iterdir())
            file_names = [f.name for f in all_files if f.is_file()]

            # Build ImageGroups using photo_pairing module
            imagegroups, invalid_files = photo_pairing.build_imagegroups(file_names, folder_path)

            return imagegroups
        except Exception as e:
            raise ValueError(f"Failed to generate ImageGroups: {e}")

    # Load from cache
    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)

        imagegroups = cache_data.get('imagegroups')
        if not imagegroups:
            raise ValueError("Cache file missing 'imagegroups' field")

        return imagegroups
    except (json.JSONDecodeError, KeyError) as e:
        raise ValueError(f"Invalid Photo Pairing cache file: {e}")


def flatten_imagegroups_to_specific_images(imagegroups: List[Dict[str, Any]]) -> List[SpecificImage]:
    """
    Flatten ImageGroups to individual SpecificImage objects.

    Each ImageGroup contains multiple separate_images (suffix-based).
    This function converts each separate_image into a SpecificImage object
    for independent validation.

    Args:
        imagegroups: List of ImageGroup dictionaries from Photo Pairing Tool

    Returns:
        List of SpecificImage objects (one per separate_image)

    Example:
        ImageGroup {
            'group_id': 'AB3D0001',
            'separate_images': {
                '': {'files': ['AB3D0001.CR3', 'AB3D0001.XMP']},
                '2': {'files': ['AB3D0001-2.CR3']},
                'HDR': {'files': ['AB3D0001-HDR.DNG']}
            }
        }

        Flattens to 3 SpecificImages:
        - unique_id='AB3D0001', suffix=''
        - unique_id='AB3D0001-2', suffix='2'
        - unique_id='AB3D0001-HDR', suffix='HDR'
    """
    specific_images = []

    for group in imagegroups:
        group_id = group['group_id']
        camera_id = group['camera_id']
        counter = group['counter']
        separate_images = group.get('separate_images', {})

        for suffix, image_data in separate_images.items():
            # Build unique_id (base_filename)
            if suffix:
                unique_id = f"{camera_id}{counter}-{suffix}"
            else:
                unique_id = f"{camera_id}{counter}"

            # Get actual files
            actual_files = sorted(image_data.get('files', []))

            # Create SpecificImage
            specific_image = SpecificImage(
                unique_id=unique_id,
                group_id=group_id,
                camera_id=camera_id,
                counter=counter,
                suffix=suffix,
                actual_files=actual_files
            )
            specific_images.append(specific_image)

    return specific_images


# =============================================================================
# Core Validation Engine - Path Enumeration and File Validation
# =============================================================================

@dataclass
class PathState:
    """
    State tracking for DFS traversal through pipeline graph.

    Used to track iteration counts per node (except Capture/Termination) to prevent infinite loops.

    Attributes:
        node_iterations: Dictionary mapping node IDs to iteration count (all nodes except Capture/Termination)
        current_suffix: Accumulated suffix from all Process nodes traversed
    """
    node_iterations: Dict[str, int] = field(default_factory=dict)
    current_suffix: str = ""


def enumerate_all_paths(pipeline: PipelineConfig) -> List[List[Dict[str, Any]]]:
    """
    Enumerate all possible paths from Capture to Termination nodes using DFS.

    This function traverses the pipeline graph depth-first, exploring all branches
    and handling loops with truncation after MAX_ITERATIONS per node (except Capture
    and Termination nodes, which appear exactly once per path by design).

    Args:
        pipeline: PipelineConfig object with all nodes

    Returns:
        List of paths, where each path is a list of node dictionaries containing:
        - node_id: Node identifier
        - node_type: Type of node (Capture, File, Process, etc.)
        - extension: File extension (for File nodes)
        - method_ids: Processing methods (for Process nodes)
        - truncated: Whether this path was truncated due to loop limit
        - iteration_count: Number of times node was visited (all nodes except Capture/Termination)

    Example path:
        [
            {'node_id': 'capture', 'node_type': 'Capture'},
            {'node_id': 'raw_image', 'node_type': 'File', 'extension': '.CR3'},
            {'node_id': 'process', 'node_type': 'Process', 'method_ids': ['Edit'], 'iteration_count': 1},
            {'node_id': 'termination', 'node_type': 'Termination', 'truncated': False}
        ]
    """
    # Find Capture node
    capture_nodes = [n for n in pipeline.nodes if isinstance(n, CaptureNode)]
    if not capture_nodes:
        return []

    capture_node = capture_nodes[0]
    all_paths = []

    def dfs(node_id: str, current_path: List[Dict[str, Any]], state: PathState):
        """Depth-first search to enumerate all paths."""
        if node_id not in pipeline.nodes_by_id:
            return

        node = pipeline.nodes_by_id[node_id]

        # Build node info for path
        node_info = {
            'node_id': node.id,
            'node_type': node.type
        }

        # Add type-specific fields
        if isinstance(node, FileNode):
            node_info['extension'] = node.extension
        elif isinstance(node, ProcessNode):
            # Store method_ids temporarily (will be replaced with single method per path)
            node_info['method_ids'] = node.method_ids
        elif isinstance(node, TerminationNode):
            node_info['termination_type'] = node.termination_type
            node_info['truncated'] = False
        elif isinstance(node, BranchingNode):
            node_info['condition_description'] = node.condition_description
        elif isinstance(node, PairingNode):
            node_info['pairing_type'] = node.pairing_type
            node_info['input_count'] = node.input_count

        # Track iteration count for all nodes except Capture and Termination
        if not isinstance(node, (CaptureNode, TerminationNode)):
            iteration_count = state.node_iterations.get(node.id, 0) + 1
            node_info['iteration_count'] = iteration_count

        # Add node to current path
        current_path.append(node_info)

        # If this is a Termination node, save the complete path
        if isinstance(node, TerminationNode):
            all_paths.append(current_path.copy())
            current_path.pop()
            return

        # Check loop limit for all nodes except Capture and Termination
        if not isinstance(node, (CaptureNode, TerminationNode)):
            iteration_count = state.node_iterations.get(node.id, 0) + 1

            if iteration_count > MAX_ITERATIONS:
                # Truncate this path - mark termination as truncated
                truncated_termination = {
                    'node_id': f'truncated_from_{node.id}',
                    'node_type': 'Termination',
                    'termination_type': 'TRUNCATED',
                    'truncated': True,
                    'truncation_note': f'Path truncated after {MAX_ITERATIONS} iterations of {node.id}'
                }
                current_path.append(truncated_termination)
                all_paths.append(current_path.copy())
                current_path.pop()  # Remove truncation marker
                current_path.pop()  # Remove current node
                return

            # Update iteration count for this node
            new_state = PathState(
                node_iterations=state.node_iterations.copy(),
                current_suffix=state.current_suffix
            )
            new_state.node_iterations[node.id] = iteration_count
        else:
            new_state = state

        # PROCESS NODE WITH MULTIPLE METHOD_IDS: Create parallel paths (like branching)
        if isinstance(node, ProcessNode) and len(node.method_ids) > 1:
            # Remove the node we just added (we'll add it again with single method per iteration)
            current_path.pop()

            # Each method_id creates a separate path (user chooses one at runtime)
            for method_id in node.method_ids:
                # Create a new node_info with only this single method_id
                method_node_info = node_info.copy()
                method_node_info['method_ids'] = [method_id]
                current_path.append(method_node_info)

                # Explore all output nodes with this method choice
                for output_id in node.output:
                    dfs(output_id, current_path, new_state)

                # Backtrack this method's node
                current_path.pop()
        else:
            # Single method_id (or no method_ids) - explore outputs normally
            for output_id in node.output:
                dfs(output_id, current_path, new_state)

            # Backtrack
            current_path.pop()

    # Start DFS from Capture node
    initial_state = PathState()
    dfs(capture_node.id, [], initial_state)

    return all_paths


# =============================================================================
# Pairing-Aware Path Enumeration (Handles Pairing Nodes)
# =============================================================================

def find_pairing_nodes_in_topological_order(pipeline: PipelineConfig) -> List[PairingNode]:
    """
    Find all pairing nodes and return them in topological order (upstream first).

    Uses depth-first traversal from Capture node to determine order.

    Args:
        pipeline: PipelineConfig object

    Returns:
        List of PairingNode objects in topological order

    Raises:
        ValueError: If pairing nodes form a cycle (not supported)
    """
    pairing_nodes = [n for n in pipeline.nodes if isinstance(n, PairingNode)]

    if not pairing_nodes:
        return []

    # Build depth map via BFS from capture node
    from collections import deque

    capture_nodes = [n for n in pipeline.nodes if isinstance(n, CaptureNode)]
    if not capture_nodes:
        return pairing_nodes  # Shouldn't happen in valid pipeline

    # Use dynamic programming to find longest path to each node
    # This ensures correct topological ordering when nodes can be reached via multiple paths
    node_depth = {capture_nodes[0].id: 0}

    # Build reverse adjacency list (which nodes point to each node)
    predecessors = {}
    for node in pipeline.nodes:
        for output_id in node.output:
            if output_id not in predecessors:
                predecessors[output_id] = []
            predecessors[output_id].append(node.id)

    # Repeatedly relax edges until no changes (Bellman-Ford for longest path)
    changed = True
    iterations = 0
    max_iterations = len(pipeline.nodes) * 2  # Prevent infinite loops

    while changed and iterations < max_iterations:
        changed = False
        iterations += 1

        for node in pipeline.nodes:
            # Skip if this node has no predecessors (except capture)
            if node.id not in predecessors and not isinstance(node, CaptureNode):
                continue

            # Calculate longest path to this node
            if isinstance(node, CaptureNode):
                max_pred_depth = -1
            else:
                max_pred_depth = -1
                for pred_id in predecessors.get(node.id, []):
                    if pred_id in node_depth:
                        max_pred_depth = max(max_pred_depth, node_depth[pred_id])

            new_depth = max_pred_depth + 1

            # Update if we found a longer path
            if node.id not in node_depth or node_depth[node.id] < new_depth:
                node_depth[node.id] = new_depth
                changed = True

    # Sort pairing nodes by depth (topological order)
    pairing_with_depth = [(n, node_depth.get(n.id, float('inf'))) for n in pairing_nodes]
    pairing_with_depth.sort(key=lambda x: x[1])

    return [n for n, _ in pairing_with_depth]


def validate_pairing_node_inputs(pairing_node: PairingNode, pipeline: PipelineConfig) -> tuple:
    """
    Validate that a pairing node has exactly 2 input nodes.

    Args:
        pairing_node: The pairing node to validate
        pipeline: PipelineConfig object

    Returns:
        Tuple of (input1_id, input2_id) - the two nodes that output to this pairing node

    Raises:
        ValueError: If pairing node doesn't have exactly 2 inputs
    """
    # Find all nodes that output to this pairing node
    input_nodes = []
    for node in pipeline.nodes:
        if pairing_node.id in node.output:
            input_nodes.append(node.id)

    if len(input_nodes) != 2:
        raise ValueError(
            f"Pairing node '{pairing_node.id}' must have exactly 2 input nodes, "
            f"but has {len(input_nodes)}: {input_nodes}"
        )

    return (input_nodes[0], input_nodes[1])


def merge_two_paths(
    path1: List[Dict[str, Any]],
    path2: List[Dict[str, Any]],
    pairing_node: PairingNode,
    state1: PathState,
    state2: PathState
) -> tuple:
    """
    Merge two paths that meet at a pairing node.

    Creates a merged path by combining nodes from both branches.
    Since both paths start from capture and may share common ancestors,
    we keep path1 as the base and only append the unique branch nodes from path2.

    Args:
        path1: First path (list of node dicts)
        path2: Second path (list of node dicts)
        pairing_node: The pairing node where paths merge
        state1: PathState from first path
        state2: PathState from second path

    Returns:
        Tuple of (merged_path, merged_state) ready to continue DFS
    """
    # Start with path1 as base
    merged_path = path1.copy()

    # Find unique nodes in path2 (nodes not already in path1)
    path1_node_ids = {n['node_id'] for n in path1}
    for node in path2:
        if node['node_id'] not in path1_node_ids:
            merged_path.append(node)

    # Add pairing node info
    pairing_info = {
        'node_id': pairing_node.id,
        'node_type': 'Pairing',
        'pairing_type': pairing_node.pairing_type,
        'input_count': pairing_node.input_count,
        'iteration_count': 1  # First time visiting this pairing node
    }
    merged_path.append(pairing_info)

    # Merge iteration counts - take maximum per node
    merged_iterations = state1.node_iterations.copy()
    for node_id, count in state2.node_iterations.items():
        if node_id in merged_iterations:
            merged_iterations[node_id] = max(merged_iterations[node_id], count)
        else:
            merged_iterations[node_id] = count

    # Mark pairing node as visited once
    merged_iterations[pairing_node.id] = 1

    # Merged state
    merged_state = PathState(
        node_iterations=merged_iterations,
        current_suffix=state1.current_suffix  # Use first path's suffix (arbitrary choice)
    )

    return (merged_path, merged_state)


def enumerate_paths_with_pairing(pipeline: PipelineConfig) -> List[List[Dict[str, Any]]]:
    """
    Enumerate all paths through pipeline, handling Pairing nodes correctly.

    Pairing nodes combine paths from two upstream branches. This function:
    1. Identifies pairing nodes in topological order
    2. For each pairing node:
       - Enumerates paths from current frontier to the pairing node
       - Groups paths by which input edge they arrived on (2 groups)
       - Creates all combinations (Cartesian product)
       - Merges each pair: depth=max, files=union, iterations=max
    3. Continues from merged paths to next pairing node or terminations

    Restrictions:
    - Pairing nodes must have exactly 2 inputs (validated)
    - Pairing nodes cannot be in loops (MAX_ITERATIONS=1 enforced)
    - If same pairing node encountered again, path is TRUNCATED

    Args:
        pipeline: PipelineConfig object with all nodes

    Returns:
        List of paths (same format as enumerate_all_paths)

    Raises:
        ValueError: If pairing node doesn't have exactly 2 inputs
    """
    # Find all pairing nodes in topological order
    pairing_nodes = find_pairing_nodes_in_topological_order(pipeline)

    # If no pairing nodes, use simpler algorithm
    if not pairing_nodes:
        return enumerate_all_paths(pipeline)

    # Validate all pairing nodes have exactly 2 inputs
    pairing_inputs = {}
    for pairing_node in pairing_nodes:
        input1, input2 = validate_pairing_node_inputs(pairing_node, pipeline)
        pairing_inputs[pairing_node.id] = (input1, input2)

    # Find Capture node
    capture_nodes = [n for n in pipeline.nodes if isinstance(n, CaptureNode)]
    if not capture_nodes:
        return []

    capture_node = capture_nodes[0]

    # Initialize frontier with capture node
    initial_path = []
    initial_state = PathState()
    current_frontier = [(initial_path, initial_state, capture_node.id)]

    # NEW: Collect paths that terminate before reaching later pairing nodes
    all_completed_paths = []

    # Process each pairing node in topological order
    for pairing_node in pairing_nodes:
        input1_id, input2_id = pairing_inputs[pairing_node.id]

        # Enumerate paths from frontier to this pairing node
        paths_to_pairing = []

        for seed_path, seed_state, start_node_id in current_frontier:
            # DFS from start_node to pairing_node (treating pairing as termination)
            # Returns: (incomplete_paths, completed_paths)
            incomplete, completed = dfs_to_target_node(
                start_node_id=start_node_id,
                target_node_id=pairing_node.id,
                current_path=seed_path.copy(),
                state=seed_state,
                pipeline=pipeline
            )
            paths_to_pairing.extend(incomplete)
            all_completed_paths.extend(completed)  # NEW: Save early terminations

        # Group paths by which input they arrived on
        branch1_paths = []
        branch2_paths = []

        for path, state, arrived_from in paths_to_pairing:
            if arrived_from == input1_id:
                branch1_paths.append((path, state))
            elif arrived_from == input2_id:
                branch2_paths.append((path, state))
            # Ignore paths that didn't arrive via expected inputs

        # Create all combinations (Cartesian product)
        merged_paths = []
        for path1, state1 in branch1_paths:
            for path2, state2 in branch2_paths:
                merged_path, merged_state = merge_two_paths(
                    path1, path2, pairing_node, state1, state2
                )
                # Continue from pairing node's OUTPUTS, not the pairing node itself
                for output_id in pairing_node.output:
                    merged_paths.append((merged_path, merged_state, output_id))

        # Update frontier for next pairing node (or final terminations)
        current_frontier = merged_paths

    # Final enumeration: frontier to terminations
    final_paths = []
    for seed_path, seed_state, start_node_id in current_frontier:
        # Continue DFS to termination nodes
        paths = dfs_to_termination_nodes(
            start_node_id=start_node_id,
            current_path=seed_path.copy(),
            state=seed_state,
            pipeline=pipeline
        )
        final_paths.extend(paths)

    # Return all paths: early terminations + final paths
    return all_completed_paths + final_paths


def dfs_to_target_node(
    start_node_id: str,
    target_node_id: str,
    current_path: List[Dict[str, Any]],
    state: PathState,
    pipeline: PipelineConfig
) -> tuple:
    """
    DFS from start node to target node (treating target as temporary termination).

    Returns:
        Tuple of (incomplete_paths, completed_paths):
        - incomplete_paths: List of (path, state, arrived_from_node_id) that reached target
        - completed_paths: List of complete paths that reached termination nodes before target
    """
    incomplete_paths = []  # Paths that reached the target pairing node
    completed_paths = []   # Paths that reached termination nodes early

    def dfs(node_id: str, path: List[Dict[str, Any]], current_state: PathState, came_from: str):
        if node_id not in pipeline.nodes_by_id:
            return

        node = pipeline.nodes_by_id[node_id]

        # If we reached target pairing node, save as incomplete path
        if node_id == target_node_id:
            incomplete_paths.append((path.copy(), current_state, came_from))
            return

        # NEW: If we reached a termination node, save as completed path
        if isinstance(node, TerminationNode):
            # This is a complete path that terminated before reaching target
            node_info = {
                'node_id': node.id,
                'node_type': 'Termination',
                'termination_type': node.termination_type
            }
            path.append(node_info)
            completed_paths.append(path.copy())
            path.pop()
            return

        # Build node info
        node_info = {
            'node_id': node.id,
            'node_type': node.type
        }

        # Add type-specific fields
        if isinstance(node, FileNode):
            node_info['extension'] = node.extension
        elif isinstance(node, ProcessNode):
            node_info['method_ids'] = node.method_ids
        elif isinstance(node, BranchingNode):
            node_info['condition_description'] = node.condition_description
        elif isinstance(node, PairingNode):
            # If we encounter a pairing node that's NOT our target, truncate
            # (pairing nodes can only be visited once - no loops allowed)
            if node_id != target_node_id:
                truncated_termination = {
                    'node_id': f'truncated_at_pairing_{node_id}',
                    'node_type': 'Termination',
                    'termination_type': 'TRUNCATED',
                    'truncated': True,
                    'truncation_note': f'Pairing node {node_id} encountered multiple times (loops not allowed)'
                }
                path.append(truncated_termination)
                completed_paths.append(path.copy())  # Truncated paths are "complete"
                path.pop()
                return

        # Track iteration count for non-Capture/Termination nodes
        if not isinstance(node, (CaptureNode, TerminationNode)):
            iteration_count = current_state.node_iterations.get(node.id, 0) + 1
            node_info['iteration_count'] = iteration_count

        # Add node to path
        path.append(node_info)

        # Check loop limit for non-Capture/Termination nodes
        if not isinstance(node, (CaptureNode, TerminationNode)):
            iteration_count = current_state.node_iterations.get(node.id, 0) + 1

            if iteration_count > MAX_ITERATIONS:
                truncated_termination = {
                    'node_id': f'truncated_from_{node.id}',
                    'node_type': 'Termination',
                    'termination_type': 'TRUNCATED',
                    'truncated': True,
                    'truncation_note': f'Path truncated after {MAX_ITERATIONS} iterations of {node.id}'
                }
                path.append(truncated_termination)
                completed_paths.append(path.copy())  # Truncated paths are "complete"
                path.pop()
                path.pop()
                return

            # Update state
            new_state = PathState(
                node_iterations=current_state.node_iterations.copy(),
                current_suffix=current_state.current_suffix
            )
            new_state.node_iterations[node.id] = iteration_count
        else:
            new_state = current_state

        # PROCESS NODE WITH MULTIPLE METHOD_IDS: Create parallel paths (like branching)
        if isinstance(node, ProcessNode) and len(node.method_ids) > 1:
            # Remove the node we just added (we'll add it again with single method per iteration)
            path.pop()

            # Each method_id creates a separate path (user chooses one at runtime)
            for method_id in node.method_ids:
                # Create a new node_info with only this single method_id
                method_node_info = node_info.copy()
                method_node_info['method_ids'] = [method_id]
                path.append(method_node_info)

                # Explore all output nodes with this method choice
                for output_id in node.output:
                    dfs(output_id, path, new_state, node_id)

                # Backtrack this method's node
                path.pop()
        else:
            # Single method_id (or no method_ids) - explore outputs normally
            for output_id in node.output:
                dfs(output_id, path, new_state, node_id)

            # Backtrack
            path.pop()

    # Start DFS from start_node
    dfs(start_node_id, current_path, state, start_node_id)

    return (incomplete_paths, completed_paths)


def dfs_to_termination_nodes(
    start_node_id: str,
    current_path: List[Dict[str, Any]],
    state: PathState,
    pipeline: PipelineConfig
) -> List[List[Dict[str, Any]]]:
    """
    DFS from start node to any termination node.

    Similar to enumerate_all_paths but starts from arbitrary node (not Capture).
    """
    all_paths = []

    def dfs(node_id: str, path: List[Dict[str, Any]], current_state: PathState):
        if node_id not in pipeline.nodes_by_id:
            return

        node = pipeline.nodes_by_id[node_id]

        # Build node info
        node_info = {
            'node_id': node.id,
            'node_type': node.type
        }

        # Add type-specific fields
        if isinstance(node, FileNode):
            node_info['extension'] = node.extension
        elif isinstance(node, ProcessNode):
            node_info['method_ids'] = node.method_ids
        elif isinstance(node, TerminationNode):
            node_info['termination_type'] = node.termination_type
            node_info['truncated'] = False
        elif isinstance(node, BranchingNode):
            node_info['condition_description'] = node.condition_description
        elif isinstance(node, PairingNode):
            # Pairing node encountered again - truncate (no loops)
            truncated_termination = {
                'node_id': f'truncated_at_pairing_{node_id}',
                'node_type': 'Termination',
                'termination_type': 'TRUNCATED',
                'truncated': True,
                'truncation_note': f'Pairing node {node_id} encountered multiple times (loops not allowed)'
            }
            path.append(truncated_termination)
            all_paths.append(path.copy())
            path.pop()
            return

        # Track iteration count for non-Capture/Termination nodes
        if not isinstance(node, (CaptureNode, TerminationNode)):
            iteration_count = current_state.node_iterations.get(node.id, 0) + 1
            node_info['iteration_count'] = iteration_count

        # Add node to path
        path.append(node_info)

        # If termination, save path
        if isinstance(node, TerminationNode):
            all_paths.append(path.copy())
            path.pop()
            return

        # Check loop limit
        if not isinstance(node, (CaptureNode, TerminationNode)):
            iteration_count = current_state.node_iterations.get(node.id, 0) + 1

            if iteration_count > MAX_ITERATIONS:
                truncated_termination = {
                    'node_id': f'truncated_from_{node.id}',
                    'node_type': 'Termination',
                    'termination_type': 'TRUNCATED',
                    'truncated': True,
                    'truncation_note': f'Path truncated after {MAX_ITERATIONS} iterations of {node.id}'
                }
                path.append(truncated_termination)
                all_paths.append(path.copy())
                path.pop()
                path.pop()
                return

            # Update state
            new_state = PathState(
                node_iterations=current_state.node_iterations.copy(),
                current_suffix=current_state.current_suffix
            )
            new_state.node_iterations[node.id] = iteration_count
        else:
            new_state = current_state

        # PROCESS NODE WITH MULTIPLE METHOD_IDS: Create parallel paths (like branching)
        if isinstance(node, ProcessNode) and len(node.method_ids) > 1:
            # Remove the node we just added (we'll add it again with single method per iteration)
            path.pop()

            # Each method_id creates a separate path (user chooses one at runtime)
            for method_id in node.method_ids:
                # Create a new node_info with only this single method_id
                method_node_info = node_info.copy()
                method_node_info['method_ids'] = [method_id]
                path.append(method_node_info)

                # Explore all output nodes with this method choice
                for output_id in node.output:
                    dfs(output_id, path, new_state)

                # Backtrack this method's node
                path.pop()
        else:
            # Single method_id (or no method_ids) - explore outputs normally
            for output_id in node.output:
                dfs(output_id, path, new_state)

            # Backtrack
            path.pop()

    # Start DFS from start_node
    dfs(start_node_id, current_path, state)

    return all_paths


def generate_expected_files(path: List[Dict[str, Any]], base_filename: str) -> List[str]:
    """
    Generate list of expected files for a specific image following a pipeline path.

    This function walks through a pipeline path and builds filenames with appropriate
    suffixes from Process nodes. Duplicate filenames are removed, keeping only the
    last occurrence of each unique filename.

    Args:
        path: List of node dictionaries from enumerate_all_paths()
        base_filename: Base filename (e.g., "AB3D0001" or "AB3D0001-2")

    Returns:
        List of expected filenames (deduplicated, preserving order of last occurrence)

    Example:
        path = [
            {'node_type': 'Capture'},
            {'node_type': 'File', 'extension': '.CR3'},
            {'node_type': 'Process', 'method_ids': ['DxO_DeepPRIME_XD2s']},
            {'node_type': 'File', 'extension': '.DNG'},
            {'node_type': 'Termination'}
        ]
        base_filename = 'AB3D0001'

        Returns: ['AB3D0001.CR3', 'AB3D0001-DxO_DeepPRIME_XD2s.DNG']
    """
    # Track filenames with their last position in path
    # Key: filename, Value: (position, filename)
    file_positions = {}
    current_suffix = ""
    position = 0

    for node in path:
        node_type = node.get('node_type')

        if node_type == 'File':
            # Generate filename with accumulated suffix
            extension = node.get('extension', '')
            if current_suffix:
                filename = f"{base_filename}{current_suffix}{extension}"
            else:
                filename = f"{base_filename}{extension}"

            # Track position of this filename (overwrites if duplicate)
            file_positions[filename] = (position, filename)
            position += 1

        elif node_type == 'Process':
            # Add processing method suffixes
            method_ids = node.get('method_ids', [])
            for method_id in method_ids:
                if method_id:  # Empty string means no suffix
                    current_suffix += f"-{method_id}"

    # Sort by position to maintain order, extract filenames
    expected_files = [filename for (pos, filename) in sorted(file_positions.values())]

    return expected_files


def generate_sample_base_filename(config: PhotoAdminConfig) -> str:
    """
    Generate a sample base filename for graph visualization debugging.

    Uses the first camera ID from camera_mappings in config and a random
    counter between 0001 and 9999.

    Args:
        config: PhotoAdminConfig object

    Returns:
        Sample base filename (e.g., "AB3D0742")

    Example:
        If config has camera_mappings = {'AB3D': [...], 'XY12': [...]},
        returns something like "AB3D0742"
    """
    import random

    # Get first camera ID from config
    camera_mappings = config.camera_mappings
    if camera_mappings:
        first_camera_id = list(camera_mappings.keys())[0]
    else:
        # Fallback to a default camera ID if none configured
        first_camera_id = "XXXX"

    # Generate random counter between 1 and 9999
    counter = random.randint(1, 9999)
    counter_str = f"{counter:04d}"  # Pad to 4 digits

    return f"{first_camera_id}{counter_str}"


def classify_validation_status(actual_files: set, expected_files: set) -> ValidationStatus:
    """
    Classify validation status by comparing actual vs expected files.

    Classification rules:
    - CONSISTENT: All expected files present, no extra files
    - CONSISTENT_WITH_WARNING: All expected files present, but extra files exist
    - PARTIAL: Some (but not all) expected files present
    - INCONSISTENT: No expected files present (completely wrong)

    Args:
        actual_files: Set of actual filenames found
        expected_files: Set of expected filenames from pipeline

    Returns:
        ValidationStatus enum value
    """
    missing_files = expected_files - actual_files
    extra_files = actual_files - expected_files

    # INCONSISTENT: No expected files present at all
    if not actual_files or len(actual_files & expected_files) == 0:
        return ValidationStatus.INCONSISTENT

    # PARTIAL: Some expected files missing
    if missing_files:
        return ValidationStatus.PARTIAL

    # CONSISTENT-WITH-WARNING: All expected files present, but extra files exist
    if extra_files:
        return ValidationStatus.CONSISTENT_WITH_WARNING

    # CONSISTENT: Perfect match
    return ValidationStatus.CONSISTENT


def validate_specific_image(
    specific_image: SpecificImage,
    pipeline: PipelineConfig
) -> ValidationResult:
    """
    Validate a single SpecificImage against all pipeline paths.

    This function:
    1. Enumerates all paths from Capture to Termination
    2. For each path, generates expected files
    3. Compares actual files vs expected files
    4. Classifies status for each termination
    5. Returns aggregated ValidationResult

    Args:
        specific_image: SpecificImage object with actual files
        pipeline: PipelineConfig with all nodes

    Returns:
        ValidationResult with termination_matches and overall_status
    """
    # Enumerate all paths through pipeline (pairing-aware)
    all_paths = enumerate_paths_with_pairing(pipeline)

    # Group paths by termination node
    paths_by_termination = {}
    for path in all_paths:
        if path:
            # Last node should be termination
            term_node = path[-1]
            term_id = term_node.get('node_id')
            if term_id not in paths_by_termination:
                paths_by_termination[term_id] = []
            paths_by_termination[term_id].append(path)

    # Validate against each termination
    termination_matches = []
    actual_files_set = set(specific_image.actual_files)

    for term_id, paths in paths_by_termination.items():
        # NEW APPROACH: Evaluate each path independently and find the BEST match
        # An image group is CONSISTENT if AT LEAST ONE path produces the same files

        path_evaluations = []

        for path in paths:
            expected_files = generate_expected_files(path, specific_image.unique_id)
            expected_files_set = set(expected_files)

            # Classify status for this specific path
            path_status = classify_validation_status(actual_files_set, expected_files_set)

            # Calculate metrics for this path
            missing = expected_files_set - actual_files_set
            extra = actual_files_set - expected_files_set

            if expected_files_set:
                found_expected = actual_files_set & expected_files_set
                completion = (len(found_expected) / len(expected_files_set)) * 100
            else:
                completion = 0.0

            # Check if this path was truncated
            path_truncated = any(node.get('truncated', False) for node in path)
            truncation_note = None
            if path_truncated:
                for node in path:
                    if node.get('truncation_note'):
                        truncation_note = node['truncation_note']
                        break

            path_evaluations.append({
                'path': path,
                'status': path_status,
                'expected_files': expected_files_set,
                'missing_files': missing,
                'extra_files': extra,
                'completion_percentage': completion,
                'truncated': path_truncated,
                'truncation_note': truncation_note,
                'path_depth': len([n for n in path if n.get('node_type') not in ('Capture', 'Termination')])
            })

        # Find the BEST status (CONSISTENT > CONSISTENT_WITH_WARNING > PARTIAL > INCONSISTENT)
        status_priority = {
            ValidationStatus.CONSISTENT: 1,
            ValidationStatus.CONSISTENT_WITH_WARNING: 2,
            ValidationStatus.PARTIAL: 3,
            ValidationStatus.INCONSISTENT: 4
        }

        best_eval = min(path_evaluations, key=lambda e: (
            status_priority[e['status']],  # Best status first
            len(e['missing_files']),        # Fewest missing files second
            e['path_depth']                 # Shortest path third
        ))

        # Use the best match for reporting
        status = best_eval['status']
        completion_percentage = best_eval['completion_percentage']
        missing_files = sorted(list(best_eval['missing_files']))
        extra_files = sorted(list(best_eval['extra_files']))
        truncated = best_eval['truncated']
        truncation_note = best_eval['truncation_note']
        all_expected_files = best_eval['expected_files']

        # Get termination type
        term_node = paths[0][-1] if paths else {}
        termination_type = term_node.get('termination_type', term_id)

        # Create TerminationMatchResult
        term_match = TerminationMatchResult(
            termination_id=term_id,
            termination_type=termination_type,
            status=status,
            completion_percentage=completion_percentage,
            expected_files=sorted(list(all_expected_files)),
            actual_files=specific_image.actual_files,
            missing_files=missing_files,
            extra_files=extra_files,
            truncated=truncated,
            truncation_note=truncation_note
        )
        termination_matches.append(term_match)

    # Determine overall status (worst status across all terminations)
    status_priority = {
        ValidationStatus.INCONSISTENT: 4,
        ValidationStatus.PARTIAL: 3,
        ValidationStatus.CONSISTENT_WITH_WARNING: 2,
        ValidationStatus.CONSISTENT: 1
    }

    if termination_matches:
        overall_status = max(
            termination_matches,
            key=lambda tm: status_priority[tm.status]
        ).status
    else:
        overall_status = ValidationStatus.INCONSISTENT

    # Determine archival readiness
    archival_ready_for = [
        tm.termination_type
        for tm in termination_matches
        if tm.status in (ValidationStatus.CONSISTENT, ValidationStatus.CONSISTENT_WITH_WARNING)
    ]

    # Create ValidationResult
    return ValidationResult(
        unique_id=specific_image.unique_id,
        group_id=specific_image.group_id,
        camera_id=specific_image.camera_id,
        counter=specific_image.counter,
        suffix=specific_image.suffix,
        actual_files=specific_image.actual_files,
        termination_matches=termination_matches,
        overall_status=overall_status,
        archival_ready_for=archival_ready_for
    )


def validate_all_images(
    specific_images: List[SpecificImage],
    pipeline: PipelineConfig,
    show_progress: bool = True
) -> List[ValidationResult]:
    """
    Validate all SpecificImages against pipeline.

    Args:
        specific_images: List of SpecificImage objects to validate
        pipeline: PipelineConfig with all nodes
        show_progress: Whether to display progress indicators

    Returns:
        List of ValidationResult objects
    """
    validation_results = []
    total = len(specific_images)

    for i, specific_image in enumerate(specific_images, 1):
        if show_progress and total > 10:
            # Show progress for large collections
            if i % 100 == 0 or i == total:
                print(f"  Validating images: {i}/{total} ({(i/total)*100:.1f}%)", end='\r')

        result = validate_specific_image(specific_image, pipeline)
        validation_results.append(result)

    if show_progress and total > 10:
        print()  # New line after progress

    return validation_results


def setup_signal_handlers():
    """
    Setup graceful CTRL+C (SIGINT) handling.

    Per constitution v1.1.0: Tools MUST handle CTRL+C gracefully with
    user-friendly messages and exit code 130.
    """
    def signal_handler(sig, frame):
        print("\n\n⚠ Operation interrupted by user (CTRL+C)")
        print("Exiting gracefully...")
        sys.exit(130)  # Standard exit code for SIGINT

    signal.signal(signal.SIGINT, signal_handler)


def parse_arguments():
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        prog='pipeline_validation',
        description='Photo Processing Pipeline Validation Tool',
        epilog="""
Examples:
  # Validate photo collection against pipeline
  python3 pipeline_validation.py /Users/photographer/Photos/2025-01-15

  # Use custom configuration file
  python3 pipeline_validation.py /path/to/photos --config /path/to/custom-config.yaml

  # Force regeneration (ignore all caches)
  python3 pipeline_validation.py /path/to/photos --force-regenerate

  # Show cache status without running validation
  python3 pipeline_validation.py /path/to/photos --cache-status

Workflow:
  1. Run Photo Pairing Tool first: python3 photo_pairing.py <folder>
  2. Define pipeline in config/config.yaml (processing_pipelines section)
  3. Run pipeline validation: python3 pipeline_validation.py <folder>
  4. Review HTML report: pipeline_validation_report_YYYY-MM-DD_HH-MM-SS.html

For more information, see docs/pipeline-validation.md
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Positional argument: folder path
    parser.add_argument(
        'folder_path',
        nargs='?',
        type=Path,
        help='Path to folder containing photos to validate'
    )

    # Optional arguments
    parser.add_argument(
        '--config',
        type=Path,
        help='Path to custom configuration file (default: config/config.yaml)'
    )

    parser.add_argument(
        '--force-regenerate',
        action='store_true',
        help='Ignore all cache files and regenerate from scratch'
    )

    parser.add_argument(
        '--cache-status',
        action='store_true',
        help='Show cache status without running validation'
    )

    parser.add_argument(
        '--clear-cache',
        action='store_true',
        help='Delete cache files and regenerate'
    )

    parser.add_argument(
        '--output-format',
        choices=['html', 'json'],
        default='html',
        help='Output format for validation results (default: html)'
    )

    parser.add_argument(
        '--validate-config',
        action='store_true',
        help='Validate pipeline configuration syntax and structure without analyzing the images in the folder'
    )

    parser.add_argument(
        '--display-graph',
        action='store_true',
        help='Display pipeline graph visualization with sample filenames in HTML report. ' \
             'When used with --validate-config, generates report without requiring a folder argument.'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print detailed information about configuration loading and validation'
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {TOOL_VERSION}'
    )

    args = parser.parse_args()

    # Validate arguments
    # folder_path is optional when using --cache-status, --validate-config, or --display-graph with --validate-config
    standalone_modes = args.cache_status or args.validate_config or (args.display_graph and args.validate_config)
    if not standalone_modes and args.folder_path is None:
        parser.error('folder_path is required unless using --cache-status, --validate-config, or --display-graph with --validate-config')

    if args.folder_path and not args.folder_path.exists():
        parser.error(f"Folder does not exist: {args.folder_path}")

    if args.folder_path and not args.folder_path.is_dir():
        parser.error(f"Path is not a directory: {args.folder_path}")

    return args


def validate_prerequisites(args):
    """
    Validate that prerequisites are met before running validation.

    Args:
        args: Parsed command-line arguments

    Returns:
        bool: True if prerequisites met, False otherwise
    """
    # Check if Photo Pairing cache exists
    if args.folder_path:
        cache_file = args.folder_path / '.photo_pairing_imagegroups'
        if not cache_file.exists() and not args.force_regenerate:
            print("⚠ Error: Photo Pairing cache not found")
            print(f"  Expected: {cache_file}")
            print()
            print("Photo Pairing Tool must be run first to generate ImageGroups.")
            print()
            print("Run this command first:")
            print(f"  python3 photo_pairing.py {args.folder_path}")
            print()
            return False

    return True


# =============================================================================
# Cache Management Functions (Phase 6 - User Story 4)
# =============================================================================

def calculate_pipeline_config_hash(config_path: Path) -> str:
    """
    Calculate SHA256 hash of pipeline configuration structure.

    Uses JSON serialization with sorted keys to ensure hash is deterministic
    and insensitive to YAML formatting changes (whitespace, comments).

    Args:
        config_path: Path to config.yaml file

    Returns:
        str: SHA256 hash (64-character hexdigest)
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # Extract only the processing_pipelines section for hashing
    # This ensures that changes to other config sections (photo_extensions,
    # camera_mappings, etc.) don't invalidate pipeline validation cache
    pipeline_section = config.get('processing_pipelines', {})

    # Serialize to JSON with sorted keys for deterministic hashing
    config_str = json.dumps(pipeline_section, sort_keys=True, default=str)

    return hashlib.sha256(config_str.encode()).hexdigest()


def get_folder_content_hash(folder_path: Path) -> str:
    """
    Get folder content hash from Photo Pairing cache.

    Reuses the file_list_hash calculated by Photo Pairing Tool to avoid
    redundant folder scanning. This hash changes when files are added,
    removed, or modified in the folder.

    Args:
        folder_path: Path to analyzed folder

    Returns:
        str: SHA256 hash of file list from Photo Pairing cache

    Raises:
        FileNotFoundError: If Photo Pairing cache doesn't exist
        KeyError: If cache is malformed (missing expected fields)
    """
    cache_path = folder_path / '.photo_pairing_imagegroups'

    if not cache_path.exists():
        raise FileNotFoundError(
            f"Photo Pairing cache not found. Run Photo Pairing Tool first.\n"
            f"Expected cache file: {cache_path}"
        )

    with open(cache_path, 'r', encoding='utf-8') as f:
        cache_data = json.load(f)

    try:
        return cache_data['metadata']['file_list_hash']
    except KeyError as e:
        raise KeyError(
            f"Photo Pairing cache is malformed (missing {e}). "
            "Re-run Photo Pairing Tool to regenerate cache."
        ) from e


def calculate_validation_results_hash(validation_results: list) -> str:
    """
    Calculate SHA256 hash of validation results structure.

    Used to detect manual edits to pipeline validation cache file.
    If user manually modifies validation_results in the JSON cache,
    the hash mismatch will trigger cache invalidation.

    Args:
        validation_results: List of ValidationResult dictionaries

    Returns:
        str: SHA256 hash (64-character hexdigest)
    """
    # Serialize to JSON with sorted keys for deterministic hashing
    data_str = json.dumps(validation_results, sort_keys=True, default=str)
    return hashlib.sha256(data_str.encode()).hexdigest()


def save_pipeline_cache(
    folder_path: Path,
    validation_results: list,
    pipeline_config_hash: str,
    folder_content_hash: str
) -> bool:
    """
    Save pipeline validation results to .pipeline_validation_cache.json file.

    Cache structure follows Photo Pairing Tool's pattern with metadata
    including all hashes for invalidation detection.

    Args:
        folder_path: Path to analyzed folder
        validation_results: List of ValidationResult dictionaries
        pipeline_config_hash: Hash of pipeline configuration
        folder_content_hash: Hash of folder file list (from Photo Pairing)

    Returns:
        bool: True if cache was saved successfully, False otherwise
    """
    try:
        cache_path = folder_path / '.pipeline_validation_cache.json'

        # Calculate validation results hash for manual edit detection
        validation_results_hash = calculate_validation_results_hash(validation_results)

        # Calculate statistics
        total_groups = len(validation_results)
        consistent_groups = sum(
            1 for r in validation_results
            if r.get('status') == 'CONSISTENT'
        )
        partial_groups = sum(
            1 for r in validation_results
            if r.get('status') == 'PARTIAL'
        )
        inconsistent_groups = sum(
            1 for r in validation_results
            if r.get('status') == 'INCONSISTENT'
        )
        warning_groups = sum(
            1 for r in validation_results
            if r.get('status') == 'CONSISTENT_WITH_WARNING'
        )

        cache_data = {
            'version': '1.0',
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'folder_path': str(folder_path.absolute()),
            'tool_version': TOOL_VERSION,
            'metadata': {
                'pipeline_config_hash': pipeline_config_hash,
                'folder_content_hash': folder_content_hash,
                'validation_results_hash': validation_results_hash,
                'total_groups': total_groups,
                'consistent_groups': consistent_groups,
                'partial_groups': partial_groups,
                'inconsistent_groups': inconsistent_groups,
                'warning_groups': warning_groups
            },
            'validation_results': validation_results
        }

        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, default=str)

        return True
    except (IOError, OSError, PermissionError) as e:
        print(f"⚠ Warning: Could not save cache file: {e}")
        print("  Cache will not be available for next run.")
        return False


def load_pipeline_cache(folder_path: Path) -> Optional[dict]:
    """
    Load cached pipeline validation data from .pipeline_validation_cache.json file.

    Performs basic validation (file exists, valid JSON, version compatibility).
    Does NOT validate hashes - use validate_pipeline_cache() for that.

    Args:
        folder_path: Path to folder to check for cache

    Returns:
        dict or None: Cache data if exists and valid, None otherwise
    """
    cache_path = folder_path / '.pipeline_validation_cache.json'

    if not cache_path.exists():
        return None

    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache_data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"⚠ Warning: Could not read cache file: {e}")
        print("  Cache will be ignored and regenerated.")
        return None

    # Auto-invalidate on version mismatch (no user prompt)
    if not is_cache_version_compatible(cache_data):
        cached_version = cache_data.get('tool_version', '0.0.0')
        print(f"ℹ Cache version {cached_version} incompatible with {TOOL_VERSION}")
        print("  Regenerating cache with current version...")
        return None

    return cache_data


def is_cache_version_compatible(cache_data: dict) -> bool:
    """
    Check if cache version is compatible with current tool version.

    Uses semantic versioning: major version mismatch = incompatible.
    Minor/patch version differences are backward compatible.

    Args:
        cache_data: Loaded cache dictionary

    Returns:
        bool: True if compatible, False if invalidation required
    """
    cached_version = cache_data.get('tool_version', '0.0.0')

    try:
        # Semantic versioning: Major version mismatch = incompatible
        cached_major = int(cached_version.split('.')[0])
        current_major = int(TOOL_VERSION.split('.')[0])

        if cached_major != current_major:
            return False  # Major version change = breaking change

        # Minor/patch version differences are compatible
        return True
    except (ValueError, IndexError):
        # Invalid version format - treat as incompatible
        return False


def validate_pipeline_cache(
    cache_data: dict,
    config_path: Path,
    folder_path: Path
) -> dict:
    """
    Validate pipeline validation cache by comparing hashes.

    Checks three invalidation triggers:
    1. Pipeline config changed (pipeline_config_hash mismatch)
    2. Folder content changed (folder_content_hash mismatch)
    3. Cache manually edited (validation_results_hash mismatch)

    Args:
        cache_data: Dictionary loaded from cache file
        config_path: Path to current config.yaml
        folder_path: Path to analyzed folder

    Returns:
        dict: {
            'valid': bool,
            'pipeline_changed': bool,
            'folder_changed': bool,
            'cache_edited': bool
        }
    """
    if not cache_data:
        return {
            'valid': False,
            'pipeline_changed': True,
            'folder_changed': True,
            'cache_edited': False
        }

    try:
        # Check pipeline config hash
        current_pipeline_hash = calculate_pipeline_config_hash(config_path)
        cached_pipeline_hash = cache_data.get('metadata', {}).get('pipeline_config_hash', '')
        pipeline_changed = current_pipeline_hash != cached_pipeline_hash

        # Check folder content hash (from Photo Pairing cache)
        current_folder_hash = get_folder_content_hash(folder_path)
        cached_folder_hash = cache_data.get('metadata', {}).get('folder_content_hash', '')
        folder_changed = current_folder_hash != cached_folder_hash

        # Check validation results hash (detect manual edits)
        cached_validation_hash = cache_data.get('metadata', {}).get('validation_results_hash', '')
        recalculated_hash = calculate_validation_results_hash(
            cache_data.get('validation_results', [])
        )
        cache_edited = cached_validation_hash != recalculated_hash

        valid = not (pipeline_changed or folder_changed or cache_edited)

        return {
            'valid': valid,
            'pipeline_changed': pipeline_changed,
            'folder_changed': folder_changed,
            'cache_edited': cache_edited
        }
    except Exception as e:
        # Cache data is corrupted or malformed
        print(f"⚠ Warning: Cache validation failed: {e}")
        print("  Cache will be ignored and regenerated.")
        return {
            'valid': False,
            'pipeline_changed': True,
            'folder_changed': True,
            'cache_edited': True
        }


def prompt_cache_action(pipeline_changed: bool, folder_changed: bool, cache_edited: bool) -> Optional[str]:
    """
    Prompt user for action when pipeline validation cache is stale.

    Args:
        pipeline_changed: Boolean indicating if pipeline config changed
        folder_changed: Boolean indicating if folder content changed
        cache_edited: Boolean indicating if cache file was manually edited

    Returns:
        str: 'use_cache', 'regenerate', or None if cancelled
    """
    print("\n⚠ Found cached pipeline validation data")
    print("⚠ Changes detected:")
    print(f"  - Pipeline config: {'CHANGED' if pipeline_changed else 'OK'}")
    print(f"  - Folder content: {'CHANGED' if folder_changed else 'OK'}")
    print(f"  - Cache file: {'EDITED' if cache_edited else 'OK'}")
    print("\nChoose an option:")
    print("  (a) Use cached data anyway (fast, may be outdated)")
    print("  (b) Regenerate validation (slow, reflects current state)")

    try:
        choice = input("Your choice [a/b]: ").strip().lower()
        if choice == 'a':
            return 'use_cache'
        elif choice == 'b':
            return 'regenerate'
        else:
            print("Invalid choice. Please enter 'a' or 'b'.")
            return prompt_cache_action(pipeline_changed, folder_changed, cache_edited)
    except (KeyboardInterrupt, EOFError):
        print("\n\nInterrupted by user")
        return None


# =============================================================================
# HTML Report Generation Functions (Phase 7 - User Story 5)
# =============================================================================

def build_graph_visualization_table(pipeline: PipelineConfig, config: PhotoAdminConfig):
    """
    Build graph visualization table for debugging pipeline traversal.

    Generates a sample base filename and shows all paths through the pipeline
    with node IDs, depth, expected files, and truncation status.

    Args:
        pipeline: PipelineConfig object
        config: PhotoAdminConfig object

    Returns:
        ReportSection with table showing path details

    Example table:
        | Path # | Node Path      | Depth | Termination Type | Expected Files    | Truncated |
        |--------|----------------|-------|------------------|-------------------|-----------|
        | 1      | capture        | 3     | Black Box        | AB3D0742.CR3      | No        |
        |        | ->raw_image_1  |       |                  | AB3D0742.XMP      |           |
        |        | ->process      |       |                  | AB3D0742-Edit.DNG |           |
        |        | ->termination  |       |                  |                   |           |
    """
    from utils.report_renderer import ReportSection

    # Generate sample base filename
    sample_base_filename = generate_sample_base_filename(config)

    # Enumerate all paths (pairing-aware)
    all_paths = enumerate_paths_with_pairing(pipeline)

    # Build table rows
    headers = ["Path #", "Node Path", "Depth", "Termination Type", "Expected Files", "Truncated"]
    rows = []

    for path in all_paths:
        # Get termination info
        termination_node = path[-1] if path else None
        if termination_node:
            termination_type = termination_node.get('termination_type', 'Unknown')
            truncated = termination_node.get('truncated', False)
            truncated_str = "Yes" if truncated else "No"

            # Build node path string with newlines before arrows
            node_ids = [node.get('node_id', 'unknown') for node in path]
            if len(node_ids) > 0:
                # First node ID without arrow, then newline before each subsequent arrow
                node_path_parts = [node_ids[0]]
                for node_id in node_ids[1:]:
                    node_path_parts.append(f"\n->{node_id}")
                node_path_str = "".join(node_path_parts)
            else:
                node_path_str = "(empty path)"

            # Calculate depth (all nodes except first Capture and last Termination)
            # Depth = total nodes - 2 (Capture and Termination)
            # Minimum depth is 0 (just Capture -> Termination)
            depth = max(0, len(path) - 2)

            # Generate expected files for this path with newlines between files
            expected_files = generate_expected_files(path, sample_base_filename)
            if expected_files:
                files_str = "\n".join(expected_files)
            else:
                files_str = "(no files)"

            row = [
                None,  # Path # - will be assigned after sorting
                node_path_str,
                depth,  # Keep as int for sorting
                termination_type,
                files_str,
                truncated_str
            ]
            rows.append(row)

    # Sort rows by depth (index 2) - lower depth first for easier debugging
    rows.sort(key=lambda row: row[2])

    # Assign path numbers after sorting
    for i, row in enumerate(rows, 1):
        row[0] = str(i)
        row[2] = str(row[2])  # Convert depth back to string for display

    # Build section
    section = ReportSection(
        title=f"Pipeline Graph Visualization (Sample: {sample_base_filename})",
        type="table",
        data={
            'headers': headers,
            'rows': rows
        },
        description=f"This table shows all {len(all_paths)} paths enumerated through the pipeline graph using "
                   f"sample base filename '{sample_base_filename}'. Paths are sorted by depth (low to high) for easier debugging. "
                   f"Each path shows the node traversal sequence, depth (nodes excluding Capture/Termination), "
                   f"expected files (deduplicated - only final version of each file shown), and whether the path was truncated "
                   f"due to loop limits. Use this to debug graph traversal and verify expected files."
    )

    return section


def build_kpi_cards(validation_results: list) -> List:
    """
    Build KPI cards for executive summary statistics.

    Args:
        validation_results: List of ValidationResult dictionaries

    Returns:
        List of KPICard objects for report context
    """
    from utils.report_renderer import KPICard

    total_groups = len(validation_results)

    # Count by status
    consistent = sum(1 for r in validation_results if r.get('status') == 'CONSISTENT')
    partial = sum(1 for r in validation_results if r.get('status') == 'PARTIAL')
    inconsistent = sum(1 for r in validation_results if r.get('status') == 'INCONSISTENT')
    warning = sum(1 for r in validation_results if r.get('status') == 'CONSISTENT_WITH_WARNING')

    # Calculate archival readiness (count of groups reaching termination)
    archival_ready = consistent + warning

    kpis = [
        KPICard(
            title="Total Image Groups",
            value=str(total_groups),
            status="info",
            icon="📊"
        ),
        KPICard(
            title="Consistent",
            value=str(consistent),
            status="success",
            unit=f"{(consistent/total_groups*100):.1f}%" if total_groups > 0 else "0%",
            icon="✓",
            tooltip="All expected files present, pipeline complete"
        ),
        KPICard(
            title="Partial",
            value=str(partial),
            status="danger",
            unit=f"{(partial/total_groups*100):.1f}%" if total_groups > 0 else "0%",
            icon="⚠",
            tooltip="Missing expected files, pipeline incomplete"
        ),
        KPICard(
            title="With Warnings",
            value=str(warning),
            status="warning",
            unit=f"{(warning/total_groups*100):.1f}%" if total_groups > 0 else "0%",
            icon="!",
            tooltip="All expected files present, but extra files detected"
        ),
        KPICard(
            title="Archival Ready",
            value=str(archival_ready),
            status="success" if archival_ready == total_groups else "warning",
            unit=f"{(archival_ready/total_groups*100):.1f}%" if total_groups > 0 else "0%",
            icon="📦",
            tooltip="Groups that reached at least one termination node"
        )
    ]

    return kpis


def build_status_distribution_chart(validation_results: list):
    """
    Build pie chart showing status distribution.

    Args:
        validation_results: List of ValidationResult dictionaries

    Returns:
        ReportSection with pie chart data
    """
    from utils.report_renderer import ReportSection

    # Count by status
    status_counts = {
        'CONSISTENT': sum(1 for r in validation_results if r.get('status') == 'CONSISTENT'),
        'PARTIAL': sum(1 for r in validation_results if r.get('status') == 'PARTIAL'),
        'INCONSISTENT': sum(1 for r in validation_results if r.get('status') == 'INCONSISTENT'),
        'CONSISTENT-WITH-WARNING': sum(1 for r in validation_results if r.get('status') == 'CONSISTENT_WITH_WARNING')
    }

    # Filter out zero counts
    filtered_counts = {k: v for k, v in status_counts.items() if v > 0}

    # Chart data with 'values' key (required by base template)
    chart_data = {
        'labels': list(filtered_counts.keys()),
        'values': list(filtered_counts.values()),
        'colors': [
            'rgba(16, 185, 129, 0.8)',   # Green for CONSISTENT
            'rgba(239, 68, 68, 0.8)',    # Red for PARTIAL
            'rgba(220, 38, 38, 0.8)',    # Dark red for INCONSISTENT
            'rgba(245, 158, 11, 0.8)'    # Amber for CONSISTENT-WITH-WARNING
        ][:len(filtered_counts)]
    }

    return ReportSection(
        title="Status Distribution",
        type="chart_pie",
        data=chart_data,
        description="Distribution of validation statuses across all image groups"
    )


def build_chart_sections(validation_results: list) -> List:
    """
    Build chart sections for visualizations.

    Args:
        validation_results: List of ValidationResult dictionaries

    Returns:
        List of ReportSection objects with chart data
    """
    sections = []

    # Add pie chart for status distribution
    sections.append(build_status_distribution_chart(validation_results))

    # TODO: Add bar chart for groups per path (future enhancement)

    return sections


def build_table_sections(validation_results: list) -> List:
    """
    Build table sections for detailed group information.

    Args:
        validation_results: List of ValidationResult dictionaries

    Returns:
        List of ReportSection objects with table data
    """
    from utils.report_renderer import ReportSection

    sections = []

    # Group results by status
    by_status = {
        'CONSISTENT': [],
        'CONSISTENT_WITH_WARNING': [],
        'PARTIAL': [],
        'INCONSISTENT': []
    }

    for result in validation_results:
        status = result.get('status', 'INCONSISTENT')
        by_status[status].append(result)

    # Create table for each status with groups
    status_order = ['CONSISTENT', 'CONSISTENT_WITH_WARNING', 'PARTIAL', 'INCONSISTENT']
    status_labels = {
        'CONSISTENT': 'Consistent Groups',
        'CONSISTENT_WITH_WARNING': 'Groups with Warnings',
        'PARTIAL': 'Partial Groups (Missing Files)',
        'INCONSISTENT': 'Inconsistent Groups'
    }

    for status in status_order:
        groups = by_status[status]
        if not groups:
            continue

        # Build table rows (list of lists for base template)
        rows = []
        for group in groups:
            # Get first termination match for display
            termination_matches = group.get('termination_matches', [])
            if termination_matches:
                match = termination_matches[0]
                termination_type = match.get('termination_type', 'Unknown')
                expected_files = match.get('expected_files', [])
                actual_files = match.get('actual_files', [])
                missing_files = match.get('missing_files', [])
                extra_files = match.get('extra_files', [])
            else:
                termination_type = 'None'
                expected_files = []
                actual_files = []
                missing_files = []
                extra_files = []

            group_id = group.get('unique_id', group.get('group_id', 'Unknown'))

            # Build file list with symbols (plain text, no HTML)
            files_list = []
            for f in actual_files:
                files_list.append(f'✓ {f}')
            for f in missing_files:
                files_list.append(f'✗ {f}')
            for f in extra_files:
                files_list.append(f'⚠ {f}')

            # Join with newlines for display
            files_display = '\n'.join(files_list) if files_list else '(no files)'

            row = [
                group_id,
                status,
                termination_type,
                len(expected_files),
                len(actual_files),
                len(missing_files),
                len(extra_files),
                files_display
            ]
            rows.append(row)

        table_data = {
            'headers': ['Group ID', 'Status', 'Termination', 'Expected', 'Actual', 'Missing', 'Extra', 'Files'],
            'rows': rows
        }

        sections.append(ReportSection(
            title=status_labels[status],
            type="table",
            data=table_data,
            description=f"{len(groups)} group(s) with {status} status",
            collapsible=True
        ))

    return sections


def build_report_context(
    validation_results: list,
    scan_path: str,
    scan_start: datetime,
    scan_end: datetime,
    pipeline: Optional[PipelineConfig] = None,
    config: Optional[PhotoAdminConfig] = None,
    display_graph: bool = False
) -> 'ReportContext':
    """
    Build complete ReportContext from validation results.

    Args:
        validation_results: List of ValidationResult dictionaries
        scan_path: Path to scanned folder
        scan_start: Scan start timestamp
        scan_end: Scan end timestamp
        pipeline: Optional PipelineConfig for graph visualization
        config: Optional PhotoAdminConfig for graph visualization
        display_graph: Whether to include graph visualization section

    Returns:
        ReportContext ready for template rendering
    """
    from utils.report_renderer import ReportContext

    scan_duration = (scan_end - scan_start).total_seconds()

    # Build KPIs
    kpis = build_kpi_cards(validation_results)

    # Build sections
    sections = []

    # Add graph visualization section if requested
    if display_graph and pipeline and config:
        graph_section = build_graph_visualization_table(pipeline, config)
        sections.append(graph_section)

    sections.extend(build_chart_sections(validation_results))
    sections.extend(build_table_sections(validation_results))

    return ReportContext(
        tool_name="Pipeline Validation Tool",
        tool_version=TOOL_VERSION,
        scan_path=scan_path,
        scan_timestamp=scan_start,
        scan_duration=scan_duration,
        kpis=kpis,
        sections=sections,
        warnings=[],
        errors=[]
    )


def generate_html_report(
    validation_results: list,
    output_dir: Path,
    scan_path: str,
    scan_start: datetime,
    scan_end: datetime,
    pipeline: Optional[PipelineConfig] = None,
    config: Optional[PhotoAdminConfig] = None,
    display_graph: bool = False
) -> Path:
    """
    Generate HTML report with timestamped filename.

    Args:
        validation_results: List of ValidationResult dictionaries
        output_dir: Directory where report should be saved
        scan_path: Path to scanned folder
        scan_start: Scan start timestamp
        scan_end: Scan end timestamp
        pipeline: Optional PipelineConfig for graph visualization
        config: Optional PhotoAdminConfig for graph visualization
        display_graph: Whether to include graph visualization section

    Returns:
        Path to generated HTML report
    """
    from utils.report_renderer import ReportRenderer

    # Build report context
    context = build_report_context(
        validation_results=validation_results,
        scan_path=scan_path,
        scan_start=scan_start,
        scan_end=scan_end,
        pipeline=pipeline,
        config=config,
        display_graph=display_graph
    )

    # Generate timestamped filename
    timestamp_str = scan_start.strftime("%Y-%m-%d_%H-%M-%S")
    report_filename = f"pipeline_validation_report_{timestamp_str}.html"
    report_path = Path(output_dir) / report_filename

    # Render report using ReportRenderer
    renderer = ReportRenderer()
    renderer.render_report(
        context=context,
        template_name="pipeline_validation.html.j2",
        output_path=str(report_path)
    )

    return report_path


def main():
    """Main entry point for pipeline validation tool."""
    # Setup signal handlers for graceful CTRL+C
    setup_signal_handlers()

    # Parse command-line arguments
    args = parse_arguments()

    print(f"Pipeline Validation Tool v{TOOL_VERSION}")

    # Handle --validate-config mode (config validation only, no photo validation)
    if args.validate_config:
        print("Configuration Validation Mode")
        print("=" * 60)
        print()

        # Load configuration
        if args.verbose:
            print("Loading configuration file...")
        config = PhotoAdminConfig(config_path=args.config)
        print(f"Configuration file: {config.config_path}")
        print()

        # Validate pipeline configuration structure (YAML structure only)
        is_valid, errors = config.validate_pipeline_config_structure(
            pipeline_name='default',
            verbose=args.verbose
        )

        if not is_valid:
            print("\n✗ Configuration validation FAILED\n")
            print("Errors found:")
            for error in errors:
                print(f"  • {error}")
            print()
            return 1

        # If structure is valid, try loading the pipeline (tests node parsing)
        try:
            if args.verbose:
                print("\nLoading and parsing pipeline nodes...")
            pipeline = load_pipeline_config(config, pipeline_name='default', verbose=args.verbose)

            # Validate pipeline logic (graph structure, references, etc.)
            if args.verbose:
                print("\nValidating pipeline logic (node references, graph structure)...")
            validation_errors = validate_pipeline_structure(pipeline, config)

            if validation_errors:
                print("\n✗ Pipeline logic validation FAILED\n")
                print("Errors found:")
                for error in validation_errors:
                    print(f"  • {error}")
                print()
                return 1

            print("\n✓ Configuration validation PASSED\n")
            print(f"  Pipeline: default")
            print(f"  Nodes: {len(pipeline.nodes)}")
            print(f"  Capture nodes: {len([n for n in pipeline.nodes if isinstance(n, CaptureNode)])}")
            print(f"  File nodes: {len([n for n in pipeline.nodes if isinstance(n, FileNode)])}")
            print(f"  Process nodes: {len([n for n in pipeline.nodes if isinstance(n, ProcessNode)])}")
            print(f"  Pairing nodes: {len([n for n in pipeline.nodes if isinstance(n, PairingNode)])}")
            print(f"  Branching nodes: {len([n for n in pipeline.nodes if isinstance(n, BranchingNode)])}")
            print(f"  Termination nodes: {len([n for n in pipeline.nodes if isinstance(n, TerminationNode)])}")
            print()

            # If --display-graph is also specified, generate HTML report with graph visualization
            if args.display_graph:
                print("Generating graph visualization report...")
                scan_start = datetime.now()
                scan_end = datetime.now()

                # Generate empty validation results (graph visualization only)
                validation_results_dict = []

                try:
                    report_path = generate_html_report(
                        validation_results=validation_results_dict,
                        output_dir=Path.cwd(),
                        scan_path="(config validation mode - no folder scanned)",
                        scan_start=scan_start,
                        scan_end=scan_end,
                        pipeline=pipeline,
                        config=config,
                        display_graph=True
                    )
                    print(f"  ✓ HTML report generated: {report_path}")
                    print()
                except Exception as e:
                    print(f"  ⚠ Warning: HTML report generation failed: {e}")
                    print()

            return 0

        except ValueError as e:
            print(f"\n✗ Configuration validation FAILED\n")
            print(f"Error: {e}")
            print()
            return 1

    # Normal validation mode - validate prerequisites
    if not validate_prerequisites(args):
        sys.exit(1)

    print(f"Analyzing: {args.folder_path}")
    print()

    # Phase 2: Load configuration and data
    print("Loading configuration...")
    config = PhotoAdminConfig(config_path=args.config)

    # Load pipeline configuration using PhotoAdminConfig (per constitution)
    try:
        pipeline = load_pipeline_config(config, pipeline_name='default', verbose=args.verbose)
        print(f"  Loaded {len(pipeline.nodes)} pipeline nodes")
        print(f"  Using pipeline: default")
    except ValueError as e:
        # Error message is generated by PhotoAdminConfig (per constitution)
        print(f"⚠ Error loading pipeline configuration:\n")
        print(e)
        print()
        return 1
    print()

    # Track scan timestamps for report
    scan_start = datetime.now()

    # Phase 2: Load Photo Pairing results
    print("Loading Photo Pairing results...")
    imagegroups = load_or_generate_imagegroups(args.folder_path, force_regenerate=args.force_regenerate)
    print(f"  Loaded {len(imagegroups)} image groups")

    # Phase 2: Flatten to SpecificImages
    specific_images = flatten_imagegroups_to_specific_images(imagegroups)
    print(f"  Flattened to {len(specific_images)} specific images")
    print()

    # Phase 3 & 4: Validate images against pipeline
    print("Validating images against pipeline...")
    print(f"  Pipeline supports all 6 node types (Phases 3 & 4 complete)")
    validation_results = validate_all_images(specific_images, pipeline, show_progress=True)

    scan_end = datetime.now()

    print()
    print(f"  Validated {len(validation_results)} images")
    print()

    # Display summary statistics
    status_counts = {
        ValidationStatus.CONSISTENT: 0,
        ValidationStatus.CONSISTENT_WITH_WARNING: 0,
        ValidationStatus.PARTIAL: 0,
        ValidationStatus.INCONSISTENT: 0
    }

    for result in validation_results:
        # Count the most severe status across all terminations
        worst_status = ValidationStatus.CONSISTENT
        for term_match in result.termination_matches:
            if term_match.status.value > worst_status.value:
                worst_status = term_match.status
        status_counts[worst_status] += 1

    print("Validation Summary:")
    print(f"  ✓ Consistent: {status_counts[ValidationStatus.CONSISTENT]}")
    print(f"  ⚠ Consistent with warnings: {status_counts[ValidationStatus.CONSISTENT_WITH_WARNING]}")
    print(f"  ⚠ Partial: {status_counts[ValidationStatus.PARTIAL]}")
    print(f"  ✗ Inconsistent: {status_counts[ValidationStatus.INCONSISTENT]}")
    print()

    # Phase 7 (US5): Generate HTML report
    print("Generating HTML report...")

    # Convert ValidationResult objects to dictionaries for report functions
    validation_results_dict = []
    for result in validation_results:
        # Determine worst status across all terminations
        worst_status = ValidationStatus.CONSISTENT
        for term_match in result.termination_matches:
            if term_match.status.value > worst_status.value:
                worst_status = term_match.status

        # Convert termination matches to dictionaries
        termination_matches_dict = []
        for term_match in result.termination_matches:
            termination_matches_dict.append({
                'termination_type': term_match.termination_type,
                'status': term_match.status.name,
                'expected_files': term_match.expected_files,
                'actual_files': term_match.actual_files,
                'missing_files': term_match.missing_files,
                'extra_files': term_match.extra_files
            })

        validation_results_dict.append({
            'unique_id': result.unique_id,
            'group_id': result.group_id,
            'status': worst_status.name,
            'termination_matches': termination_matches_dict
        })

    # Generate HTML report (in current working directory, like other tools)
    try:
        report_path = generate_html_report(
            validation_results=validation_results_dict,
            output_dir=Path.cwd(),
            scan_path=str(args.folder_path),
            scan_start=scan_start,
            scan_end=scan_end,
            pipeline=pipeline,
            config=config,
            display_graph=args.display_graph
        )
        print(f"  ✓ HTML report generated: {report_path}")
        print()
    except Exception as e:
        print(f"  ⚠ Warning: HTML report generation failed: {e}")
        print()

    print("✓ Pipeline validation complete")
    print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
