"""
Photo Processing Pipeline Processor

Core business logic for pipeline validation - data structures, graph traversal,
and validation algorithms. This module is designed to be reusable across different
interfaces (CLI, API, GUI, etc.).

Key Components:
- Data structures for pipeline configuration and validation results
- Pipeline configuration loading and validation
- Graph traversal algorithms (with support for loops, branching, pairing nodes)
- Validation logic for classifying image status

Author: photo-admin project
License: AGPL-3.0
Version: 1.0.0
"""

import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from enum import Enum

# Import shared configuration manager
from utils.config_manager import PhotoAdminConfig


# =============================================================================
# Constants
# =============================================================================

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
    name: str
    output: List[str]  # List of node IDs that this node outputs to


@dataclass
class CaptureNode(NodeBase):
    """
    Capture node - represents camera capture (always the starting point).
    Expected: No input files, creates initial file(s).
    """
    type: str = field(default="Capture", init=False)


@dataclass
class FileNode(NodeBase):
    """
    File node - represents an expected file with a specific extension.
    Expected: File with given extension exists at this stage.
    """
    extension: str  # e.g., ".CR3", ".DNG", ".TIF"
    type: str = field(default="File", init=False)


@dataclass
class ProcessNode(NodeBase):
    """
    Process node - represents a processing step that adds a suffix to filenames.
    Expected: Process generates file(s) with method_id suffix appended.
    """
    method_ids: List[str]  # e.g., ["DxO_DeepPRIME_XD2s", "Edit"]
    type: str = field(default="Process", init=False)


@dataclass
class PairingNode(NodeBase):
    """
    Pairing node - represents merging of multiple input paths (e.g., HDR).
    Expected: Takes multiple input files and produces combined output.
    Note: Must have exactly 2 input nodes.
    """
    pairing_type: str  # e.g., "HDR", "Panorama", "FocusStack"
    input_count: int  # Number of inputs required (currently only 2 supported)
    type: str = field(default="Pairing", init=False)


@dataclass
class BranchingNode(NodeBase):
    """
    Branching node - represents a decision point (user choice).
    Expected: No files created, just directs flow to multiple outputs.
    """
    condition_description: str  # Description of the branching decision
    type: str = field(default="Branching", init=False)


@dataclass
class TerminationNode(NodeBase):
    """
    Termination node - represents an end state (archival readiness).
    Expected: Reaching this node means workflow is complete for this termination type.
    """
    termination_type: str  # e.g., "Black Box Archive", "Browsable Archive"
    type: str = field(default="Termination", init=False)


# Type alias for any pipeline node
PipelineNode = Union[CaptureNode, FileNode, ProcessNode, PairingNode, BranchingNode, TerminationNode]


@dataclass
class PipelineConfig:
    """
    Complete pipeline configuration with all nodes.
    Represents the entire directed graph of the processing workflow.
    """
    nodes: List[PipelineNode]
    capture_nodes: List[CaptureNode] = field(default_factory=list)
    file_nodes: List[FileNode] = field(default_factory=list)
    process_nodes: List[ProcessNode] = field(default_factory=list)
    pairing_nodes: List[PairingNode] = field(default_factory=list)
    branching_nodes: List[BranchingNode] = field(default_factory=list)
    termination_nodes: List[TerminationNode] = field(default_factory=list)

    @property
    def nodes_by_id(self) -> Dict[str, PipelineNode]:
        """Dictionary lookup of nodes by ID."""
        return {node.id: node for node in self.nodes}


# =============================================================================
# Data Structures - Validation Results
# =============================================================================

class ValidationStatus(Enum):
    """Validation status for a Specific Image."""
    CONSISTENT = "CONSISTENT"  # All expected files present, no extra files
    CONSISTENT_WITH_WARNING = "CONSISTENT_WITH_WARNING"  # All expected files present, extra files exist
    PARTIAL = "PARTIAL"  # Subset of expected files present (incomplete processing)
    INCONSISTENT = "INCONSISTENT"  # No valid path match, or critical files missing

    def __lt__(self, other):
        """Define ordering: CONSISTENT < CONSISTENT_WITH_WARNING < PARTIAL < INCONSISTENT."""
        if not isinstance(other, ValidationStatus):
            return NotImplemented
        priority = {
            ValidationStatus.CONSISTENT: 0,
            ValidationStatus.CONSISTENT_WITH_WARNING: 1,
            ValidationStatus.PARTIAL: 2,
            ValidationStatus.INCONSISTENT: 3,
        }
        return priority[self] < priority[other]


@dataclass
class SpecificImage:
    """
    Represents a single specific image (base filename + optional suffix for counter looping).
    E.g., AB3D0001 (suffix='') or AB3D0001-2 (suffix='2').
    """
    base_filename: str  # e.g., "AB3D0001" or "AB3D0001-2"
    camera_id: str  # e.g., "AB3D"
    counter: str  # e.g., "0001"
    suffix: str  # e.g., "" (primary) or "2", "3" (counter looping)
    properties: List[str]  # e.g., ["HDR", "BW"] - processing methods applied
    files: List[str]  # List of actual files present for this specific image
    group_id: str = ""  # Parent ImageGroup ID (camera_id + counter), e.g., "AB3D0001"

    def __post_init__(self):
        """Ensure files is always a list and set group_id if not provided."""
        if not isinstance(self.files, list):
            self.files = []
        if not self.group_id:
            self.group_id = f"{self.camera_id}{self.counter}"


@dataclass
class TerminationMatchResult:
    """Result of matching a Specific Image against a single termination path."""
    termination_type: str  # e.g., "Black Box Archive"
    status: ValidationStatus  # CONSISTENT, PARTIAL, INCONSISTENT, etc.
    expected_files: List[str]  # Expected files for this path
    missing_files: List[str]  # Missing files (for PARTIAL status)
    extra_files: List[str]  # Extra files (for CONSISTENT_WITH_WARNING)
    actual_files: List[str]  # Actual files present
    completion_percentage: float  # 0.0 to 100.0
    is_archival_ready: bool  # True if CONSISTENT or CONSISTENT_WITH_WARNING
    is_truncated: bool = False  # True if path hit MAX_ITERATIONS limit


@dataclass
class ValidationResult:
    """Complete validation result for a Specific Image across all termination paths."""
    base_filename: str  # e.g., "AB3D0001" or "AB3D0001-2"
    camera_id: str
    counter: str
    suffix: str  # e.g., "" or "2"
    properties: List[str]  # e.g., ["HDR"]
    actual_files: List[str]  # Actual files present
    termination_matches: List[TerminationMatchResult]  # Results for each termination type
    overall_status: ValidationStatus  # Worst status across all terminations
    overall_archival_ready: bool  # True if at least one termination is ready

    def get_match_for_termination(self, termination_type: str) -> Optional[TerminationMatchResult]:
        """Get the validation result for a specific termination type."""
        for match in self.termination_matches:
            if match.termination_type == termination_type:
                return match
        return None


# =============================================================================
# Pipeline Configuration Loading and Validation
# =============================================================================

def parse_node_from_yaml(node_dict: Dict[str, Any]) -> PipelineNode:
    """
    Parse a YAML node dictionary into the appropriate node type.

    Args:
        node_dict: Dictionary from YAML configuration

    Returns:
        Appropriate node instance (CaptureNode, FileNode, etc.)

    Raises:
        ValueError: If node type is unknown or required fields are missing
    """
    node_type = node_dict.get('type')
    node_id = node_dict.get('id')
    name = node_dict.get('name', '')
    output = node_dict.get('output', [])

    if not node_id:
        raise ValueError(f"Node missing required 'id' field: {node_dict}")

    if not node_type:
        raise ValueError(f"Node '{node_id}' missing required 'type' field")

    if node_type == 'Capture':
        return CaptureNode(id=node_id, name=name, output=output)

    elif node_type == 'File':
        extension = node_dict.get('extension', '')
        if not extension:
            raise ValueError(f"FileNode '{node_id}' missing required 'extension' field")
        return FileNode(id=node_id, name=name, output=output, extension=extension)

    elif node_type == 'Process':
        method_ids = node_dict.get('method_ids', [])
        if not isinstance(method_ids, list):
            method_ids = [method_ids]
        return ProcessNode(id=node_id, name=name, output=output, method_ids=method_ids)

    elif node_type == 'Pairing':
        pairing_type = node_dict.get('pairing_type', '')
        input_count = node_dict.get('input_count', 2)
        return PairingNode(
            id=node_id, name=name, output=output,
            pairing_type=pairing_type, input_count=input_count
        )

    elif node_type == 'Branching':
        condition_description = node_dict.get('condition_description', '')
        return BranchingNode(
            id=node_id, name=name, output=output,
            condition_description=condition_description
        )

    elif node_type == 'Termination':
        termination_type = node_dict.get('termination_type', '')
        return TerminationNode(
            id=node_id, name=name, output=output,
            termination_type=termination_type
        )

    else:
        raise ValueError(f"Unknown node type '{node_type}' for node '{node_id}'")


def load_pipeline_config(config: PhotoAdminConfig, pipeline_name: str = 'default', verbose: bool = False) -> PipelineConfig:
    """
    Load pipeline configuration from PhotoAdminConfig.

    Args:
        config: PhotoAdminConfig instance with pipeline configuration
        pipeline_name: Name of pipeline to load (default: 'default')
        verbose: If True, print detailed loading information

    Returns:
        PipelineConfig instance with all nodes

    Raises:
        ValueError: If pipeline configuration is missing or invalid
    """
    if not hasattr(config, 'processing_pipelines') or not config.processing_pipelines:
        raise ValueError(
            "No pipeline configuration found in config file. "
            "Add a 'processing_pipelines' section with 'nodes' list. "
            "See template-config.yaml for examples."
        )

    pipelines = config.processing_pipelines

    # Check if pipeline_name exists
    if pipeline_name not in pipelines:
        available_pipelines = list(pipelines.keys())
        raise ValueError(
            f"Pipeline '{pipeline_name}' not found in configuration. "
            f"Available pipelines: {available_pipelines}"
        )

    pipeline_data = pipelines[pipeline_name]
    nodes_data = pipeline_data.get('nodes', [])

    if not nodes_data:
        raise ValueError(
            f"Pipeline '{pipeline_name}' has no nodes. "
            f"Add nodes to the 'processing_pipelines.{pipeline_name}.nodes' list."
        )

    # Parse all nodes
    nodes = []
    for node_dict in nodes_data:
        try:
            node = parse_node_from_yaml(node_dict)
            nodes.append(node)
        except ValueError as e:
            raise ValueError(f"Error parsing node: {e}")

    # Categorize nodes by type
    pipeline_config = PipelineConfig(nodes=nodes)
    for node in nodes:
        if isinstance(node, CaptureNode):
            pipeline_config.capture_nodes.append(node)
        elif isinstance(node, FileNode):
            pipeline_config.file_nodes.append(node)
        elif isinstance(node, ProcessNode):
            pipeline_config.process_nodes.append(node)
        elif isinstance(node, PairingNode):
            pipeline_config.pairing_nodes.append(node)
        elif isinstance(node, BranchingNode):
            pipeline_config.branching_nodes.append(node)
        elif isinstance(node, TerminationNode):
            pipeline_config.termination_nodes.append(node)

    if verbose:
        print(f"Loaded pipeline '{pipeline_name}' with {len(nodes)} nodes:")
        print(f"  Capture: {len(pipeline_config.capture_nodes)}")
        print(f"  File: {len(pipeline_config.file_nodes)}")
        print(f"  Process: {len(pipeline_config.process_nodes)}")
        print(f"  Pairing: {len(pipeline_config.pairing_nodes)}")
        print(f"  Branching: {len(pipeline_config.branching_nodes)}")
        print(f"  Termination: {len(pipeline_config.termination_nodes)}")

    return pipeline_config


def validate_pipeline_structure(pipeline: PipelineConfig, config) -> List[str]:
    """
    Validate pipeline structure for common configuration errors.

    Args:
        pipeline: PipelineConfig instance to validate
        config: PhotoAdminConfig for checking processing methods

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Build node ID lookup
    node_ids = {node.id for node in pipeline.nodes}

    # Check 1: At least one Capture node
    if not pipeline.capture_nodes:
        errors.append("Pipeline must have at least one Capture node")

    # Check 2: At least one Termination node
    if not pipeline.termination_nodes:
        errors.append("Pipeline must have at least one Termination node")

    # Check 3: All output references are valid
    for node in pipeline.nodes:
        for output_id in node.output:
            if output_id not in node_ids:
                errors.append(f"Node '{node.id}' references non-existent output node '{output_id}'")

    # Check 4: Process nodes use valid method_ids
    if hasattr(config, 'processing_methods'):
        valid_methods = set(config.processing_methods.keys())
        valid_methods.add("")  # Empty string is valid (no suffix)

        for process_node in pipeline.process_nodes:
            for method_id in process_node.method_ids:
                if method_id not in valid_methods:
                    errors.append(
                        f"Process node '{process_node.id}' uses undefined method_id '{method_id}'. "
                        f"Add it to processing_methods in config.yaml"
                    )

    # Check 5: File node extensions are valid
    if hasattr(config, 'photo_extensions'):
        valid_extensions = set(ext.upper() for ext in config.photo_extensions)
        valid_extensions.update(set(ext.upper() for ext in getattr(config, 'metadata_extensions', [])))

        for file_node in pipeline.file_nodes:
            ext_upper = file_node.extension.upper()
            if ext_upper not in valid_extensions:
                # This is a warning, not an error - could be intentional
                pass

    # Check 6: Pairing nodes have exactly 2 inputs (structural requirement)
    # This is checked during path enumeration, not here

    # Check 7: No unreachable nodes (all nodes reachable from Capture)
    reachable = set()
    to_visit = [node.id for node in pipeline.capture_nodes]
    while to_visit:
        current_id = to_visit.pop()
        if current_id in reachable:
            continue
        reachable.add(current_id)
        # Find current node
        current_node = next((n for n in pipeline.nodes if n.id == current_id), None)
        if current_node:
            to_visit.extend(current_node.output)

    unreachable = node_ids - reachable
    if unreachable:
        errors.append(f"Unreachable nodes (not connected to any Capture node): {', '.join(sorted(unreachable))}")

    return errors


# =============================================================================
# Graph Traversal - Path Enumeration
# =============================================================================

@dataclass
class PathState:
    """State for path enumeration tracking."""
    path: List[Dict[str, Any]]
    current_node_id: str
    iteration_counts: Dict[str, int]


def enumerate_all_paths(pipeline: PipelineConfig) -> List[List[Dict[str, Any]]]:
    """
    Enumerate all paths through the pipeline using DFS.

    IMPORTANT: This function does NOT handle Pairing nodes. Use enumerate_paths_with_pairing()
    if pipeline contains pairing nodes. This function is kept for backward compatibility
    and for pipelines without pairing nodes.

    Algorithm:
    - Start from each Capture node
    - DFS through the graph, tracking visited nodes per path
    - Apply MAX_ITERATIONS limit to File, Process, and Branching nodes
    - File nodes add themselves to path
    - Process nodes add suffix to filename accumulator
    - Branching nodes just branch (no file/suffix added)
    - Termination nodes end the path
    - Pairing nodes are NOT supported by this function

    Args:
        pipeline: PipelineConfig instance

    Returns:
        List of paths, where each path is a list of node info dicts
    """
    all_paths = []
    node_lookup = {node.id: node for node in pipeline.nodes}

    def dfs(current_node_id: str, current_path: List[Dict[str, Any]], iteration_counts: Dict[str, int]):
        """
        Depth-first search through pipeline graph.

        Args:
            current_node_id: ID of current node
            current_path: Path so far (list of node info dicts)
            iteration_counts: Iteration count for each node ID in this path
        """
        if current_node_id not in node_lookup:
            return

        current_node = node_lookup[current_node_id]

        # Check iteration limit for File, Process, Branching nodes
        if isinstance(current_node, (FileNode, ProcessNode, BranchingNode)):
            iterations = iteration_counts.get(current_node_id, 0)
            if iterations >= MAX_ITERATIONS:
                # Hit iteration limit - truncate path
                truncation_info = {
                    'id': None,
                    'type': 'Termination',
                    'term_type': 'TRUNCATED',
                    'truncated': True
                }
                all_paths.append(current_path + [truncation_info])
                return
            iteration_counts = {**iteration_counts, current_node_id: iterations + 1}

        # Build node info for this step
        node_info = {'id': current_node.id, 'type': current_node.type}

        if isinstance(current_node, FileNode):
            node_info['extension'] = current_node.extension
            current_path = current_path + [node_info]

        elif isinstance(current_node, ProcessNode):
            # Process nodes with multiple method_ids create parallel paths
            # Each method_id becomes a separate branch
            if len(current_node.method_ids) > 1:
                # Multiple methods - create separate path for each
                for method_id in current_node.method_ids:
                    method_node_info = {**node_info, 'method_id': method_id}
                    method_path = current_path + [method_node_info]
                    # Continue DFS for each method path
                    for next_node_id in current_node.output:
                        dfs(next_node_id, method_path, iteration_counts.copy())
                return  # Don't continue DFS here, it's handled in loop
            else:
                # Single method or empty - standard processing
                method_id = current_node.method_ids[0] if current_node.method_ids else ""
                node_info['method_id'] = method_id
                current_path = current_path + [node_info]

        elif isinstance(current_node, BranchingNode):
            node_info['condition'] = current_node.condition_description
            current_path = current_path + [node_info]

        elif isinstance(current_node, TerminationNode):
            node_info['term_type'] = current_node.termination_type
            current_path = current_path + [node_info]
            all_paths.append(current_path)
            return

        elif isinstance(current_node, CaptureNode):
            current_path = current_path + [node_info]

        elif isinstance(current_node, PairingNode):
            # This function does NOT support Pairing nodes
            # Use enumerate_paths_with_pairing() instead
            raise NotImplementedError(
                f"Pairing node '{current_node.id}' found. Use enumerate_paths_with_pairing() "
                "for pipelines with pairing nodes."
            )

        # Continue DFS to output nodes
        for next_node_id in current_node.output:
            dfs(next_node_id, current_path, iteration_counts.copy())

    # Start DFS from each Capture node
    for capture_node in pipeline.capture_nodes:
        dfs(capture_node.id, [], {})

    return all_paths


# =============================================================================
# Pairing Node Support - Cartesian Product Logic
# =============================================================================

def find_pairing_nodes_in_topological_order(pipeline: PipelineConfig) -> List[PairingNode]:
    """
    Find all pairing nodes and sort them in topological order (earliest to latest).

    Uses longest-path algorithm: distance from Capture node determines order.
    Pairing nodes closer to Capture are processed first.

    Args:
        pipeline: PipelineConfig instance

    Returns:
        List of PairingNode instances sorted by topological order
    """
    if not pipeline.pairing_nodes:
        return []

    # Build adjacency list (reverse graph for distance calculation)
    node_lookup = {node.id: node for node in pipeline.nodes}
    reverse_edges = {node.id: [] for node in pipeline.nodes}

    for node in pipeline.nodes:
        for output_id in node.output:
            if output_id in reverse_edges:
                reverse_edges[output_id].append(node.id)

    # Calculate longest distance from any Capture node using dynamic programming
    distances = {node.id: -1 for node in pipeline.nodes}

    # Initialize: Capture nodes have distance 0
    for capture_node in pipeline.capture_nodes:
        distances[capture_node.id] = 0

    # Iteratively update distances (relaxation)
    changed = True
    iterations = 0
    max_iterations = len(pipeline.nodes) + 1  # Prevent infinite loop

    while changed and iterations < max_iterations:
        changed = False
        iterations += 1

        for node in pipeline.nodes:
            if distances[node.id] == -1:
                # Check if any predecessor has been assigned a distance
                for pred_id in reverse_edges[node.id]:
                    if distances[pred_id] >= 0:
                        # Take maximum distance from predecessors + 1
                        new_distance = distances[pred_id] + 1
                        if distances[node.id] < new_distance:
                            distances[node.id] = new_distance
                            changed = True
            else:
                # Already has distance - check if we can improve it
                for pred_id in reverse_edges[node.id]:
                    if distances[pred_id] >= 0:
                        new_distance = distances[pred_id] + 1
                        if distances[node.id] < new_distance:
                            distances[node.id] = new_distance
                            changed = True

    # Sort pairing nodes by distance
    pairing_with_distance = [(distances[pn.id], pn) for pn in pipeline.pairing_nodes]
    pairing_with_distance.sort(key=lambda x: x[0])

    return [pn for _, pn in pairing_with_distance]


def validate_pairing_node_inputs(pairing_node: PairingNode, pipeline: PipelineConfig) -> tuple:
    """
    Validate that a pairing node has exactly 2 input branches.

    Args:
        pairing_node: PairingNode to validate
        pipeline: PipelineConfig instance

    Returns:
        Tuple of (input1_id, input2_id) - the two input node IDs

    Raises:
        ValueError: If pairing node doesn't have exactly 2 inputs
    """
    # Find all nodes that output to this pairing node
    input_node_ids = []
    for node in pipeline.nodes:
        if pairing_node.id in node.output:
            input_node_ids.append(node.id)

    if len(input_node_ids) != 2:
        raise ValueError(
            f"Pairing node '{pairing_node.id}' must have exactly 2 input nodes, "
            f"found {len(input_node_ids)}: {input_node_ids}"
        )

    return input_node_ids[0], input_node_ids[1]


def merge_two_paths(path1: List[Dict[str, Any]], path2: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merge two paths at a pairing node using Cartesian product semantics.

    The merged path contains all unique nodes from both input paths,
    representing the union of all nodes traversed by either branch.

    Args:
        path1: First path (list of node info dicts)
        path2: Second path (list of node info dicts)

    Returns:
        Merged path containing all unique nodes from both paths
    """
    # Start with the first path
    merged_path = path1.copy()

    # Track which node IDs we've already included (to avoid duplicates)
    included_ids = set(node['id'] for node in path1 if 'id' in node)

    # Add nodes from path2 that aren't already in the merged path
    for node_info in path2:
        node_id = node_info.get('id')
        if node_id and node_id not in included_ids:
            merged_path.append(node_info)
            included_ids.add(node_id)

    return merged_path


def enumerate_paths_with_pairing(pipeline: PipelineConfig) -> List[List[Dict[str, Any]]]:
    """
    Enumerate all paths through pipeline with support for Pairing nodes.

    This is the primary path enumeration function that should be used when
    pipeline contains pairing nodes. Falls back to enumerate_all_paths() if
    no pairing nodes are present.

    Algorithm:
    1. Find all pairing nodes in topological order
    2. For each pairing node (earliest to latest):
       a. Find paths to the pairing node from both inputs
       b. Compute Cartesian product of input paths
       c. Merge each pair using merge_two_paths()
       d. Continue enumeration from pairing node to termination
    3. Handle Process nodes with multiple method_ids as branching

    Args:
        pipeline: PipelineConfig instance

    Returns:
        List of paths, where each path is a list of node info dicts
    """
    # Check if pipeline has pairing nodes
    pairing_nodes = find_pairing_nodes_in_topological_order(pipeline)

    if not pairing_nodes:
        # No pairing nodes - use standard enumeration
        return enumerate_all_paths(pipeline)

    # Validate pairing nodes
    for pn in pairing_nodes:
        validate_pairing_node_inputs(pn, pipeline)

    # Build node lookup
    node_lookup = {node.id: node for node in pipeline.nodes}

    # Find all nodes that input to pairing nodes
    pairing_input_nodes = set()
    for pn in pairing_nodes:
        for node in pipeline.nodes:
            if pn.id in node.output:
                pairing_input_nodes.add(node.id)

    # Process pairing nodes one at a time in topological order
    # Start with paths from Capture to first pairing node

    # Helper function: DFS to target node (pairing node or termination)
    def dfs_to_target(
        current_node_id: str,
        target_node_id: Optional[str],
        current_path: List[Dict[str, Any]],
        iteration_counts: Dict[str, int],
        stop_at_pairing: bool = False
    ) -> List[List[Dict[str, Any]]]:
        """
        DFS to target node, collecting all paths.

        If target_node_id is None, goes to termination.
        If stop_at_pairing is True, stops when hitting ANY pairing node.
        """
        paths = []

        if current_node_id not in node_lookup:
            return paths

        current_node = node_lookup[current_node_id]

        # Check iteration limit
        if isinstance(current_node, (FileNode, ProcessNode, BranchingNode)):
            iterations = iteration_counts.get(current_node_id, 0)
            if iterations >= MAX_ITERATIONS:
                truncation_info = {
                    'id': None,
                    'type': 'Termination',
                    'term_type': 'TRUNCATED',
                    'truncated': True
                }
                return [current_path + [truncation_info]]
            iteration_counts = {**iteration_counts, current_node_id: iterations + 1}

        # Build node info
        node_info = {'id': current_node.id, 'type': current_node.type}

        if isinstance(current_node, FileNode):
            node_info['extension'] = current_node.extension
            current_path = current_path + [node_info]

        elif isinstance(current_node, ProcessNode):
            # Handle multiple method_ids as branching
            if len(current_node.method_ids) > 1:
                for method_id in current_node.method_ids:
                    method_node_info = {**node_info, 'method_id': method_id}
                    method_path = current_path + [method_node_info]
                    for next_node_id in current_node.output:
                        paths.extend(dfs_to_target(
                            next_node_id, target_node_id, method_path,
                            iteration_counts.copy(), stop_at_pairing
                        ))
                return paths
            else:
                method_id = current_node.method_ids[0] if current_node.method_ids else ""
                node_info['method_id'] = method_id
                current_path = current_path + [node_info]

        elif isinstance(current_node, BranchingNode):
            node_info['condition'] = current_node.condition_description
            current_path = current_path + [node_info]

        elif isinstance(current_node, TerminationNode):
            node_info['term_type'] = current_node.termination_type
            current_path = current_path + [node_info]
            return [current_path]

        elif isinstance(current_node, CaptureNode):
            current_path = current_path + [node_info]

        elif isinstance(current_node, PairingNode):
            # Reached a pairing node
            if current_node_id == target_node_id:
                # This pairing node is the target - return path without adding it
                return [current_path]
            elif stop_at_pairing:
                # Hit a pairing node before reaching target
                # Return current path (which is the path before this pairing node)
                # This allows us to stop at nodes that input to this pairing
                return []  # We'll handle this differently - stop DFS here
            else:
                # Continue through pairing node (shouldn't happen in this algorithm)
                node_info['pairing_type'] = current_node.pairing_type
                current_path = current_path + [node_info]

        # Check if we reached target
        if target_node_id and current_node_id == target_node_id:
            return [current_path]

        # Continue DFS
        for next_node_id in current_node.output:
            next_node = node_lookup.get(next_node_id)

            # If stop_at_pairing and next node is a pairing node, stop here
            if stop_at_pairing and next_node and isinstance(next_node, PairingNode):
                # Don't continue into the pairing node
                # Only collect this path if we don't have a specific target
                # (If we have a target, we only want paths that reach it)
                if target_node_id is None:
                    paths.append(current_path)
                continue

            paths.extend(dfs_to_target(
                next_node_id, target_node_id, current_path,
                iteration_counts.copy(), stop_at_pairing
            ))

        return paths

    # Process each pairing node in topological order
    # Maintain a frontier of partial paths that need further processing
    all_final_paths = []
    frontier_paths = None  # None means start from Capture

    for pairing_idx, pairing_node in enumerate(pairing_nodes):
        # Find the two input nodes to this pairing node
        input_node_ids = [node.id for node in pipeline.nodes if pairing_node.id in node.output]

        if len(input_node_ids) != 2:
            continue  # Already validated, but double-check

        input1_paths = []
        input2_paths = []

        if frontier_paths is None:
            # First pairing node - start from Capture
            for capture_node in pipeline.capture_nodes:
                input1_paths.extend(dfs_to_target(
                    capture_node.id, input_node_ids[0], [], {}, stop_at_pairing=True
                ))
                input2_paths.extend(dfs_to_target(
                    capture_node.id, input_node_ids[1], [], {}, stop_at_pairing=True
                ))
        else:
            # Subsequent pairing node - start from frontier paths
            for frontier_path in frontier_paths:
                if not frontier_path:
                    continue

                # Start DFS from the frontier path (not removing last node)
                # Find paths from the frontier to each input node
                # We need to check if the frontier already ends at an input node
                last_node_id = frontier_path[-1].get('id')

                if last_node_id == input_node_ids[0]:
                    # Already at input1 - just use this path
                    input1_paths.append(frontier_path)
                else:
                    # Need to DFS to input1
                    paths_to_input1 = dfs_to_target(
                        last_node_id, input_node_ids[0], frontier_path[:-1], {}, stop_at_pairing=True
                    )
                    input1_paths.extend(paths_to_input1)

                if last_node_id == input_node_ids[1]:
                    # Already at input2 - just use this path
                    input2_paths.append(frontier_path)
                else:
                    # Need to DFS to input2
                    paths_to_input2 = dfs_to_target(
                        last_node_id, input_node_ids[1], frontier_path[:-1], {}, stop_at_pairing=True
                    )
                    input2_paths.extend(paths_to_input2)

        # Compute Cartesian product: merge all combinations
        merged_paths = []
        for path1 in input1_paths:
            for path2 in input2_paths:
                merged = merge_two_paths(path1, path2)
                merged_paths.append(merged)

        # Continue from pairing node - either to next pairing or to termination
        next_pairing_node = pairing_nodes[pairing_idx + 1] if pairing_idx + 1 < len(pairing_nodes) else None
        new_frontier = []

        for merged_path in merged_paths:
            # Add pairing node to path
            pairing_info = {
                'id': pairing_node.id,
                'type': 'Pairing',
                'pairing_type': pairing_node.pairing_type
            }
            path_with_pairing = merged_path + [pairing_info]

            # Continue from pairing node output
            for next_node_id in pairing_node.output:
                if next_pairing_node:
                    # There's another pairing node - DFS and collect paths that reach
                    # either termination OR inputs of next pairing
                    next_pairing_input_ids = [n.id for n in pipeline.nodes if next_pairing_node.id in n.output]

                    partial_paths = dfs_to_target(
                        next_node_id, None, path_with_pairing, {}, stop_at_pairing=True
                    )
                    for partial_path in partial_paths:
                        if not partial_path:
                            continue
                        last_node = partial_path[-1]
                        last_id = last_node.get('id')

                        if last_node.get('type') == 'Termination':
                            # Early termination before next pairing
                            all_final_paths.append(partial_path)
                        elif last_id in next_pairing_input_ids:
                            # Reached an input to the next pairing - add to frontier
                            new_frontier.append(partial_path)
                        # Otherwise path was truncated by hitting a pairing node - ignore it
                else:
                    # No more pairing nodes - go to termination
                    final_paths = dfs_to_target(
                        next_node_id, None, path_with_pairing, {}, stop_at_pairing=False
                    )
                    all_final_paths.extend(final_paths)

        # Update frontier for next pairing node
        frontier_paths = new_frontier

    # Also need to handle paths that don't go through pairing nodes
    # (early termination before reaching pairing node)
    non_pairing_paths = []
    for capture_node in pipeline.capture_nodes:
        # DFS with stop_at_pairing=True to find early terminations
        paths_before_pairing = dfs_to_target(
            capture_node.id, None, [], {}, stop_at_pairing=True
        )
        for path in paths_before_pairing:
            # Check if this path ends at a Termination node
            if path and path[-1].get('type') == 'Termination':
                non_pairing_paths.append(path)

    # Combine all paths
    all_final_paths.extend(non_pairing_paths)

    return all_final_paths


# =============================================================================
# File Generation from Paths
# =============================================================================

def generate_expected_files(path: List[Dict[str, Any]], base_filename: str, suffix: str = '') -> List[str]:
    """
    Generate list of expected filenames for a given path and base filename.

    Algorithm:
    1. Start with base (camera_id + counter, e.g., "AB3D0001")
    2. For each Process node: append "-{method_id}" to accumulator
    3. For each File node: create filename = accumulator + suffix + extension
    4. Deduplicate filenames (same extension can appear multiple times)

    IMPORTANT: Suffix comes AFTER processing methods:
    - Correct: AB3D0001-DxO_DeepPRIME-2.dng (base + method + suffix + ext)
    - Wrong: AB3D0001-2-DxO_DeepPRIME.dng (base + suffix + method + ext)

    Args:
        path: List of node info dicts representing a path through pipeline
        base_filename: Base filename WITHOUT suffix (e.g., "AB3D0001")
        suffix: Numerical suffix for counter looping (e.g., "" or "2" or "3")

    Returns:
        List of expected filenames (deduplicated, sorted)
    """
    expected_files = []
    filename_accumulator = base_filename  # Just camera_id + counter

    for node_info in path:
        node_type = node_info.get('type')

        if node_type == 'Process':
            method_id = node_info.get('method_id', '')
            if method_id:  # Empty method_id means no suffix
                filename_accumulator += f"-{method_id}"

        elif node_type == 'File':
            extension = node_info.get('extension', '')
            if extension:
                # Generate filename: base + methods + suffix + extension
                # Suffix comes AFTER all processing methods
                if suffix:
                    filename = f"{filename_accumulator}-{suffix}{extension}"
                else:
                    filename = filename_accumulator + extension
                expected_files.append(filename)

        elif node_type in ['Capture', 'Branching', 'Pairing', 'Termination']:
            # These nodes don't affect filename generation
            pass

    # Deduplicate and sort
    expected_files = sorted(set(expected_files))

    return expected_files


def generate_sample_base_filename(config: PhotoAdminConfig) -> str:
    """
    Generate a sample base filename for documentation/testing.

    Uses the first camera mapping if available, otherwise uses "ABCD0001".

    Args:
        config: PhotoAdminConfig instance

    Returns:
        Sample base filename (e.g., "AB3D0001")
    """
    # Try to use first camera mapping
    if hasattr(config, 'camera_mappings') and config.camera_mappings:
        camera_ids = list(config.camera_mappings.keys())
        if camera_ids:
            return f"{camera_ids[0]}0001"

    # Default fallback
    return "ABCD0001"


# =============================================================================
# Validation Logic
# =============================================================================

def classify_validation_status(actual_files: set, expected_files: set) -> ValidationStatus:
    """
    Classify validation status based on actual vs expected files.

    Algorithm:
    - If actual == expected: CONSISTENT
    - If expected ⊂ actual (all expected present, plus extras): CONSISTENT_WITH_WARNING
    - If actual ⊂ expected (subset present): PARTIAL
    - Otherwise: INCONSISTENT

    Args:
        actual_files: Set of actual files present
        expected_files: Set of expected files

    Returns:
        ValidationStatus enum value
    """
    if not expected_files:
        # No expected files - this shouldn't happen in valid pipelines
        return ValidationStatus.INCONSISTENT

    if actual_files == expected_files:
        return ValidationStatus.CONSISTENT

    elif expected_files.issubset(actual_files):
        # All expected files present, plus extras
        return ValidationStatus.CONSISTENT_WITH_WARNING

    elif actual_files.issubset(expected_files):
        # Subset of expected files present
        if not actual_files:
            # No files present at all
            return ValidationStatus.INCONSISTENT
        return ValidationStatus.PARTIAL

    else:
        # Some overlap, but neither subset nor superset
        # Check if at least some expected files are present
        if actual_files.intersection(expected_files):
            return ValidationStatus.PARTIAL
        else:
            return ValidationStatus.INCONSISTENT


def validate_specific_image(
    specific_image: SpecificImage,
    pipeline: PipelineConfig,
    show_progress: bool = False
) -> ValidationResult:
    """
    Validate a single SpecificImage against the pipeline.

    Algorithm:
    1. Enumerate all paths through pipeline (to all terminations)
    2. Group paths by termination_type
    3. For each termination type:
       a. Generate expected files for each path
       b. Classify status (CONSISTENT/PARTIAL/etc.)
       c. Select best path (best status, then fewest missing files, then shortest path)
    4. Overall status = worst status across all terminations
    5. Overall archival ready = at least one termination is ready

    Args:
        specific_image: SpecificImage instance to validate
        pipeline: PipelineConfig instance
        show_progress: If True, print progress indicator

    Returns:
        ValidationResult with status for each termination type
    """
    # Enumerate paths (with pairing support if needed)
    try:
        all_paths = enumerate_paths_with_pairing(pipeline)
    except NotImplementedError:
        # Fallback to basic enumeration if pairing not supported
        all_paths = enumerate_all_paths(pipeline)

    # Group paths by termination type
    paths_by_termination = {}
    for path in all_paths:
        # Find termination node at end of path
        if not path:
            continue

        last_node = path[-1]
        if last_node.get('type') == 'Termination':
            term_type = last_node.get('term_type', 'Unknown')
            is_truncated = last_node.get('truncated', False)

            # Skip truncated paths (they don't represent complete workflows)
            if is_truncated:
                continue

            if term_type not in paths_by_termination:
                paths_by_termination[term_type] = []
            paths_by_termination[term_type].append(path)

    # Prepare actual files set
    # Normalize filenames to lowercase for case-insensitive comparison
    # (filesystems like APFS, NTFS, FAT32 are case-insensitive)
    actual_files_set = set(f.lower() for f in specific_image.files)

    # Validate against each termination type
    termination_matches = []

    for term_type, paths in paths_by_termination.items():
        # Find best path for this termination
        best_status = ValidationStatus.INCONSISTENT
        best_expected = []
        best_expected_original = []  # Original case for display
        best_missing = []
        best_extra = []
        best_completion = 0.0

        for path in paths:
            # Generate expected files for this path
            # Pass camera_id+counter (without suffix) and suffix separately
            base = f"{specific_image.camera_id}{specific_image.counter}"
            expected_files = generate_expected_files(path, base, specific_image.suffix)
            # Normalize expected files to lowercase for comparison
            expected_files_set = set(f.lower() for f in expected_files)

            # Classify status (case-insensitive)
            status = classify_validation_status(actual_files_set, expected_files_set)

            # Calculate missing and extra files (case-insensitive)
            missing_files = sorted(expected_files_set - actual_files_set)
            extra_files = sorted(actual_files_set - expected_files_set)

            # Calculate completion percentage
            if expected_files_set:
                completion = (len(expected_files_set.intersection(actual_files_set)) / len(expected_files_set)) * 100.0
            else:
                completion = 0.0

            # Select best path:
            # 1. Best validation status (CONSISTENT > CONSISTENT_WITH_WARNING > PARTIAL > INCONSISTENT)
            # 2. Fewest missing files
            # 3. Shortest path depth
            if status < best_status:
                # Better status
                best_status = status
                best_expected_original = expected_files  # Original case for display
                best_expected = list(expected_files_set)  # Lowercase for comparison
                best_missing = missing_files
                best_extra = extra_files
                best_completion = completion
            elif status == best_status:
                # Same status - compare missing files count
                if len(missing_files) < len(best_missing):
                    best_status = status
                    best_expected_original = expected_files
                    best_expected = list(expected_files_set)
                    best_missing = missing_files
                    best_extra = extra_files
                    best_completion = completion
                elif len(missing_files) == len(best_missing):
                    # Same missing count - prefer shorter path
                    if len(path) < len(best_expected):
                        best_status = status
                        best_expected_original = expected_files
                        best_expected = list(expected_files_set)
                        best_missing = missing_files
                        best_extra = extra_files
                        best_completion = completion

        # Create termination match result
        is_archival_ready = best_status in [ValidationStatus.CONSISTENT, ValidationStatus.CONSISTENT_WITH_WARNING]

        # Use original-case expected files for display
        # Missing/extra files are in lowercase (normalized)
        match = TerminationMatchResult(
            termination_type=term_type,
            status=best_status,
            expected_files=best_expected_original,
            missing_files=best_missing,
            extra_files=best_extra,
            actual_files=specific_image.files,  # Original case
            completion_percentage=best_completion,
            is_archival_ready=is_archival_ready,
            is_truncated=False
        )
        termination_matches.append(match)

    # Calculate overall status (worst across all terminations)
    if termination_matches:
        overall_status = max(match.status for match in termination_matches)
        overall_archival_ready = any(match.is_archival_ready for match in termination_matches)
    else:
        # No termination matches - inconsistent
        overall_status = ValidationStatus.INCONSISTENT
        overall_archival_ready = False

    # Build validation result
    result = ValidationResult(
        base_filename=specific_image.base_filename,
        camera_id=specific_image.camera_id,
        counter=specific_image.counter,
        suffix=specific_image.suffix,
        properties=specific_image.properties,
        actual_files=specific_image.files,
        termination_matches=termination_matches,
        overall_status=overall_status,
        overall_archival_ready=overall_archival_ready
    )

    return result


def validate_all_images(
    specific_images: List[SpecificImage],
    pipeline: PipelineConfig,
    show_progress: bool = False
) -> List[ValidationResult]:
    """
    Validate all SpecificImages against the pipeline.

    Args:
        specific_images: List of SpecificImage instances
        pipeline: PipelineConfig instance
        show_progress: If True, show progress indicator

    Returns:
        List of ValidationResult instances (one per SpecificImage)
    """
    results = []
    total = len(specific_images)

    for idx, specific_image in enumerate(specific_images, 1):
        result = validate_specific_image(specific_image, pipeline, show_progress=False)
        results.append(result)

        if show_progress and idx % 10 == 0:
            print(f"  Validating images: {idx}/{total} ({100.0 * idx / total:.1f}%)", end='\r')

    if show_progress and total > 0:
        print(f"  Validating images: {total}/{total} (100.0%)")

    return results
