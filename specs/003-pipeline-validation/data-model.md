# Data Model: Photo Processing Pipeline Validation Tool

**Feature Branch**: `003-pipeline-validation`
**Date**: 2025-12-27
**Purpose**: Define core data structures for pipeline validation implementation

---

## Overview

This document defines the data structures used throughout the pipeline validation tool, organized by functional domain:

1. **Pipeline Configuration** - Node types defining the processing graph
2. **Path Traversal** - Runtime state during DFS graph traversal
3. **Validation Results** - Per-image validation outcomes
4. **Cache Metadata** - Cache file structure and invalidation tracking

---

## 1. Pipeline Configuration Data Structures

### 1.1 Node Base Structure

All nodes share common fields defined in the YAML configuration:

```python
@dataclass
class NodeBase:
    """Base structure for all pipeline nodes."""
    id: str              # Unique node identifier (e.g., "raw_image_1")
    type: str            # Node type: Capture, File, Process, Pairing, Branching, Termination
    name: str            # Human-readable name for reports
    output: list[str]    # List of output node IDs (empty for Termination nodes)
```

### 1.2 Capture Node

Start node for pipeline traversal. Represents the initial captured image.

```python
@dataclass
class CaptureNode(NodeBase):
    """Capture node - starting point of pipeline."""
    type: str = "Capture"
    output: list[str]    # Usually 1-2 outputs (raw file nodes)

    # No additional fields beyond NodeBase
```

**Example YAML:**
```yaml
- id: "capture"
  type: "Capture"
  name: "Camera Capture"
  output: ["raw_image_1"]
```

### 1.3 File Node

Represents an expected file in the Specific Image.

```python
@dataclass
class FileNode(NodeBase):
    """File node - represents expected file."""
    type: str = "File"
    extension: str       # File extension including dot (e.g., ".CR3", ".XMP", ".DNG")
    output: list[str]    # Subsequent nodes (often empty for metadata files)

    def generate_filename(self, base_filename: str, processing_suffix: str) -> str:
        """Generate expected filename for this File node."""
        return f"{base_filename}{processing_suffix}{self.extension}"
```

**Example YAML:**
```yaml
- id: "raw_image_1"
  type: "File"
  extension: ".CR3"
  name: "Canon Raw File"
  output: ["selection_process"]

- id: "xmp_metadata_1"
  type: "File"
  extension: ".XMP"
  name: "Metadata Sidecar"
  output: []  # Terminal file node
```

### 1.4 Process Node

Represents a processing step that may add a suffix to filenames.

```python
@dataclass
class ProcessNode(NodeBase):
    """Process node - represents editing/conversion step."""
    type: str = "Process"
    method_ids: list[str]   # List of processing method IDs from config
                            # Empty string ("") means no suffix added
    output: list[str]       # Subsequent nodes (often loops back or branches)

    def get_processing_suffix(self, config) -> str:
        """
        Get processing suffix from method_ids.

        Args:
            config: PhotoAdminConfig with processing_methods mapping

        Returns:
            str: Combined suffix (e.g., "-DxO_DeepPRIME_XD2s-Edit")
                 Empty string if all method_ids are ""
        """
        non_empty_methods = [m for m in self.method_ids if m]
        if not non_empty_methods:
            return ""
        return '-' + '-'.join(non_empty_methods)
```

**Example YAML:**
```yaml
- id: "selection_process"
  type: "Process"
  method_ids: [""]  # No suffix (just selection, no editing)
  name: "Image Selection"
  output: ["dng_conversion"]

- id: "individual_photoshop_process"
  type: "Process"
  method_ids: ["Edit"]
  name: "Photoshop Editing"
  output: ["tiff_generation_branching"]  # Can loop back
```

### 1.5 Pairing Node

Represents multi-branch path merging using Cartesian product logic. Pairing nodes combine all path combinations from exactly 2 upstream branches.

```python
@dataclass
class PairingNode(NodeBase):
    """Pairing node - multi-branch merge with Cartesian product."""
    type: str = "Pairing"
    pairing_type: str    # Type of pairing (e.g., "Metadata", "ImageGroup", "HDR")
    input_count: int     # MUST be 2 (validated at runtime)
    output: list[str]    # ALL outputs execute in parallel

    # CRITICAL RESTRICTIONS (enforced at runtime):
    # 1. Must have exactly 2 nodes outputting to this pairing node
    # 2. Cannot be in loops (MAX_ITERATIONS=1, truncate if encountered again)
    # 3. Processed in topological order (upstream pairing nodes first)

    # PATH MERGING LOGIC:
    # If branch 1 has N paths and branch 2 has M paths → N×M merged paths
    # Merged path properties:
    #   - depth = max(depth1, depth2)
    #   - files = union(files1, files2) [deduplicated]
    #   - node_iterations = max per node_id across both paths
```

**Example YAML:**
```yaml
- id: "metadata_pairing"
  type: "Pairing"
  pairing_type: "Metadata"
  input_count: 2
  name: "Raw + XMP Pairing"
  output: ["denoise_branching"]

- id: "image_group_pairing"
  type: "Pairing"
  pairing_type: "ImageGroup"
  input_count: 2
  name: "Image Group Pairing"
  output: ["termination_browsable"]
```

**Implementation Details:**

1. **Topological Ordering**: Pairing nodes are processed in topological order using longest-path algorithm to ensure upstream dependencies are resolved first.

2. **Path Enumeration Strategy**: Hybrid iterative approach treats pairing nodes as phase boundaries:
   - DFS from current frontier to pairing node
   - Group paths by which input they arrived on (input1 vs input2)
   - Generate Cartesian product: all combinations from branch1 × branch2
   - Continue DFS from pairing node's outputs to next pairing or termination

3. **Path Merging**: When merging two paths at a pairing node:
   ```python
   merged_path = path1 + unique_nodes_from_path2  # Deduplicate shared ancestors
   merged_depth = max(depth1, depth2)
   merged_iterations[node_id] = max(iterations1[node_id], iterations2[node_id])
   ```

4. **Loop Prevention**: If a pairing node is encountered during DFS (not as phase boundary), the path is marked as TRUNCATED to prevent infinite loops.

### 1.6 Branching Node

Represents conditional branching based on user decisions.

```python
@dataclass
class BranchingNode(NodeBase):
    """Branching node - conditional path selection."""
    type: str = "Branching"
    condition_description: str  # Human-readable condition explanation
    output: list[str]           # ALL outputs explored during validation
                                # (runtime only takes ONE, but we validate ALL)

    # NOTE: During validation, ALL branches are explored to enumerate
    # all possible valid states. At runtime, photographer chooses one.
```

**Example YAML:**
```yaml
- id: "tiff_generation_branching"
  type: "Branching"
  condition_description: "User decides: Create TIFF or continue editing"
  name: "TIFF Generation Decision"
  output: ["generate_tiff_process", "individual_photoshop_process"]  # Loop or continue
```

### 1.7 Termination Node

End node for pipeline traversal. Represents archival readiness state.

```python
@dataclass
class TerminationNode(NodeBase):
    """Termination node - end of pipeline (archival ready)."""
    type: str = "Termination"
    termination_type: str   # Type of archive (e.g., "Black Box Archive", "Browsable Archive")
    output: list[str] = field(default_factory=list)  # Always empty

    # Termination nodes are the "success" states for validation.
    # Reaching a Termination with 100% file match = archival ready.
```

**Example YAML:**
```yaml
- id: "termination_blackbox"
  type: "Termination"
  termination_type: "Black Box Archive"
  name: "Black Box Archive Ready"
  output: []

- id: "termination_browsable"
  type: "Termination"
  termination_type: "Browsable Archive"
  name: "Browsable Archive Ready"
  output: []
```

### 1.8 Pipeline Configuration Container

```python
@dataclass
class PipelineConfig:
    """Container for entire pipeline configuration."""
    nodes: dict[str, NodeBase]  # Mapping: node_id → Node object
    capture_node: CaptureNode   # Reference to Capture node (start)
    termination_nodes: list[TerminationNode]  # All Termination nodes

    def get_node(self, node_id: str) -> NodeBase:
        """
        Get node by ID.

        Raises:
            KeyError: If node_id not found in pipeline
        """
        return self.nodes[node_id]

    def validate_structure(self) -> list[str]:
        """
        Validate pipeline structure for common errors.

        Returns:
            list[str]: List of validation errors (empty if valid)
        """
        errors = []

        # Check that all output references exist
        for node in self.nodes.values():
            for output_id in node.output:
                if output_id not in self.nodes:
                    errors.append(f"Node '{node.id}' references non-existent output '{output_id}'")

        # Check that exactly one Capture node exists
        capture_count = sum(1 for n in self.nodes.values() if n.type == "Capture")
        if capture_count == 0:
            errors.append("Pipeline must have exactly one Capture node")
        elif capture_count > 1:
            errors.append(f"Pipeline has {capture_count} Capture nodes (expected 1)")

        # Check that at least one Termination node exists
        if not self.termination_nodes:
            errors.append("Pipeline must have at least one Termination node")

        # Check for unreachable nodes (future enhancement - skip for v1.0)

        return errors
```

---

## 2. Path Traversal Data Structures

### 2.1 Path State (DFS Traversal)

State carried through DFS recursion during path enumeration.

```python
@dataclass
class PathState:
    """State maintained during DFS path traversal."""
    node_sequence: list[str]         # Ordered list of node IDs visited
    file_nodes: set[str]             # Set of File node IDs collected (deduplicated)
    processing_methods: list[str]    # Ordered list of processing method IDs
    iteration_counts: dict[str, int] # {node_id: iteration_count} for loop tracking
    truncated: bool = False          # Set True if loop limit exceeded
    truncation_node: str | None = None  # Node ID where truncation occurred

    def copy(self) -> 'PathState':
        """Create independent copy for branching paths."""
        return PathState(
            node_sequence=self.node_sequence.copy(),
            file_nodes=self.file_nodes.copy(),
            processing_methods=self.processing_methods.copy(),
            iteration_counts=self.iteration_counts.copy(),
            truncated=self.truncated,
            truncation_node=self.truncation_node
        )

    def increment_iteration(self, node_id: str) -> None:
        """Increment iteration count for a node."""
        current_count = self.iteration_counts.get(node_id, 0)
        self.iteration_counts[node_id] = current_count + 1
```

### 2.2 Enumerated Path (Result of DFS)

Complete path from Capture to Termination after DFS traversal.

```python
@dataclass
class EnumeratedPath:
    """
    Complete path from Capture to Termination.

    This is the output of path enumeration, used for validation.
    """
    termination_id: str              # Termination node ID this path reaches
    node_sequence: list[str]         # Full sequence of nodes traversed
    file_nodes: set[str]             # Deduplicated File node IDs
    processing_methods: list[str]    # Accumulated processing methods
    truncated: bool                  # Whether path was truncated due to loop limit
    truncation_node: str | None      # Node where truncation occurred

    def generate_expected_files(
        self,
        base_filename: str,
        pipeline_config: PipelineConfig
    ) -> set[str]:
        """
        Generate expected filenames from File nodes.

        Args:
            base_filename: Specific Image base (e.g., "AB3D0001" or "AB3D0001-2")
            pipeline_config: Pipeline configuration with node definitions

        Returns:
            set[str]: Expected filenames (deduplicated)
        """
        expected_files = set()

        # Build processing suffix from accumulated methods
        non_empty_methods = [m for m in self.processing_methods if m]
        processing_suffix = ''
        if non_empty_methods:
            processing_suffix = '-' + '-'.join(non_empty_methods)

        # Generate filename for each File node
        for node_id in self.file_nodes:
            file_node = pipeline_config.get_node(node_id)
            filename = file_node.generate_filename(base_filename, processing_suffix)
            expected_files.add(filename)

        return expected_files
```

### 2.3 Pairing-Specific Path Enumeration Functions

The pipeline validation tool includes specialized functions for handling pairing nodes with Cartesian product logic.

#### `find_pairing_nodes_in_topological_order(pipeline: PipelineConfig) -> List[PairingNode]`

Finds all pairing nodes and returns them in topological order (upstream first) using longest-path algorithm.

**Algorithm**: Dynamic programming (Bellman-Ford variant) to compute longest path from Capture to each node, ensuring correct dependency ordering when nodes can be reached via multiple paths.

**Returns**: List of pairing nodes sorted by depth (earliest/upstream first)

#### `validate_pairing_node_inputs(pairing_node: PairingNode, pipeline: PipelineConfig) -> tuple[str, str]`

Validates that a pairing node has exactly 2 input nodes.

**Returns**: (input1_id, input2_id) tuple

**Raises**: ValueError if not exactly 2 inputs

#### `dfs_to_target_node(start_node_id, target_node_id, seed_path, seed_state, pipeline) -> List[tuple]`

DFS that treats target node as temporary termination. Used to enumerate all paths from frontier to pairing node.

**Returns**: List of (path, state, arrived_from_node_id) tuples

**Truncation**: If another pairing node is encountered (not the target), path is truncated

#### `merge_two_paths(path1, path2, pairing_node, state1, state2) -> tuple`

Merges two paths that meet at a pairing node.

**Logic**:
- Start with path1 as base
- Add unique nodes from path2 (deduplicate shared ancestors)
- Merged depth = max(depth1, depth2)
- Merged iterations[node_id] = max(iterations1[node_id], iterations2[node_id])

**Returns**: (merged_path, merged_state) tuple

#### `enumerate_paths_with_pairing(pipeline: PipelineConfig) -> List[List[Dict]]`

Main path enumeration function that handles pairing nodes correctly.

**Algorithm**:
1. Find pairing nodes in topological order
2. For each pairing node:
   - DFS from current frontier to pairing node
   - Group paths by input edge (branch 1 vs branch 2)
   - Generate Cartesian product (branch1 × branch2)
   - Update frontier with merged paths starting from pairing outputs
3. Final DFS from last frontier to termination nodes

**Complexity**: O(nodes × paths × pairing_nodes), where paths can grow exponentially with branching but is bounded by MAX_ITERATIONS=5 per node

**Example**: If metadata_pairing has 3 paths from branch1 and 2 paths from branch2, it generates 6 merged paths (3×2=6)

#### `dfs_to_termination_nodes(start_node_id, seed_path, seed_state, pipeline) -> List[List[Dict]]`

DFS from arbitrary start node to termination nodes. Used after last pairing node.

**Truncation**: If pairing node encountered during DFS, path is truncated (prevents loops)

**Returns**: List of complete paths reaching termination nodes

---

## 3. Validation Result Data Structures

### 3.1 Specific Image

Flattened representation of a single processable image (from ImageGroup).

```python
@dataclass
class SpecificImage:
    """
    Represents a single specific image for validation.

    Flattened from ImageGroup's separate_images structure.
    """
    group_id: str                    # Parent ImageGroup ID (e.g., "AB3D0001")
    camera_id: str                   # Camera identifier (e.g., "AB3D")
    counter: str                     # Counter string (e.g., "0001")
    suffix: str                      # Separate image suffix (e.g., "", "2", "HDR")
    base_filename: str               # Generated base (e.g., "AB3D0001-2")
    actual_files: set[str]           # Set of actual filenames found
    processing_properties: list[str] # Processing properties from filename
```

### 3.2 Validation Status

Enum for validation status classification.

```python
from enum import Enum

class ValidationStatus(Enum):
    """Validation status for Specific Image against a path."""
    CONSISTENT = "CONSISTENT"
    # All expected files present, no extra files, archival ready

    CONSISTENT_WITH_WARNING = "CONSISTENT-WITH-WARNING"
    # All expected files present, extra files not in pipeline, archival ready

    PARTIAL = "PARTIAL"
    # Subset of expected files present (incomplete processing)

    INCONSISTENT = "INCONSISTENT"
    # No valid path match found, or critical files missing
```

### 3.3 Termination Match Result

Result of validating Specific Image against one Termination's paths.

```python
@dataclass
class TerminationMatchResult:
    """Result of validating against one Termination node."""
    termination_id: str              # Termination node ID
    termination_type: str            # Type (e.g., "Black Box Archive")
    status: ValidationStatus         # Validation status for this termination
    matched_path: EnumeratedPath | None  # Best matching path (None if INCONSISTENT)
    completion_percentage: float     # % of expected files present (0-100)
    missing_files: list[str]         # Missing expected files
    extra_files: list[str]           # Extra files not in pipeline
    truncated: bool                  # Whether matched path was truncated
    truncation_note: str | None      # Human-readable truncation description

    @property
    def is_archival_ready(self) -> bool:
        """Check if this termination is archival ready."""
        return self.status in (ValidationStatus.CONSISTENT, ValidationStatus.CONSISTENT_WITH_WARNING)
```

### 3.4 Validation Result

Complete validation result for one Specific Image.

```python
@dataclass
class ValidationResult:
    """Complete validation result for one Specific Image."""
    # Identity
    unique_id: str                   # Unique identifier (base_filename)
    group_id: str                    # Parent ImageGroup ID
    camera_id: str                   # Camera identifier
    counter: str                     # Counter string
    suffix: str                      # Separate image suffix

    # Files
    actual_files: list[str]          # Actual files found (sorted for display)

    # Validation outcomes per termination
    termination_matches: list[TerminationMatchResult]

    # Overall status (worst status across all terminations)
    overall_status: ValidationStatus

    # Archival readiness summary
    archival_ready_for: list[str]    # List of termination_types that are archival ready

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'unique_id': self.unique_id,
            'group_id': self.group_id,
            'camera_id': self.camera_id,
            'counter': self.counter,
            'suffix': self.suffix,
            'actual_files': self.actual_files,
            'termination_matches': [
                {
                    'termination_id': tm.termination_id,
                    'termination_type': tm.termination_type,
                    'status': tm.status.value,
                    'completion_percentage': tm.completion_percentage,
                    'missing_files': tm.missing_files,
                    'extra_files': tm.extra_files,
                    'truncated': tm.truncated,
                    'truncation_note': tm.truncation_note
                }
                for tm in self.termination_matches
            ],
            'overall_status': self.overall_status.value,
            'archival_ready_for': self.archival_ready_for
        }
```

---

## 4. Cache Data Structures

### 4.1 Cache Metadata

Metadata stored in pipeline validation cache for invalidation tracking.

```python
@dataclass
class CacheMetadata:
    """Metadata for pipeline validation cache."""
    # Version tracking
    version: str                     # Cache format version (e.g., "1.0")
    tool_version: str                # Tool version that created cache (e.g., "1.0.0")

    # Timestamps
    created_at: str                  # ISO 8601 timestamp
    folder_path: str                 # Absolute path to analyzed folder

    # Invalidation hashes
    pipeline_config_hash: str        # SHA256 of processing_pipelines section
    folder_content_hash: str         # SHA256 from Photo Pairing cache
    photo_pairing_cache_hash: str    # SHA256 of Photo Pairing imagegroups
    validation_results_hash: str     # SHA256 of validation_results list

    # Statistics (for quick display without parsing results)
    total_groups: int                # Total ImageGroups analyzed
    total_specific_images: int       # Total Specific Images validated
    consistent_count: int            # Count of CONSISTENT images
    warning_count: int               # Count of CONSISTENT-WITH-WARNING images
    partial_count: int               # Count of PARTIAL images
    inconsistent_count: int          # Count of INCONSISTENT images

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'version': self.version,
            'tool_version': self.tool_version,
            'created_at': self.created_at,
            'folder_path': self.folder_path,
            'pipeline_config_hash': self.pipeline_config_hash,
            'folder_content_hash': self.folder_content_hash,
            'photo_pairing_cache_hash': self.photo_pairing_cache_hash,
            'validation_results_hash': self.validation_results_hash,
            'total_groups': self.total_groups,
            'total_specific_images': self.total_specific_images,
            'consistent_count': self.consistent_count,
            'warning_count': self.warning_count,
            'partial_count': self.partial_count,
            'inconsistent_count': self.inconsistent_count
        }
```

### 4.2 Pipeline Validation Cache

Complete cache file structure.

```python
@dataclass
class PipelineValidationCache:
    """Complete pipeline validation cache structure."""
    metadata: CacheMetadata
    validation_results: list[dict]   # List of ValidationResult.to_dict() outputs

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'version': self.metadata.version,
            'tool_version': self.metadata.tool_version,
            'created_at': self.metadata.created_at,
            'folder_path': self.metadata.folder_path,
            'metadata': self.metadata.to_dict(),
            'validation_results': self.validation_results
        }

    @staticmethod
    def from_dict(data: dict) -> 'PipelineValidationCache':
        """Load from dictionary (deserialized JSON)."""
        metadata = CacheMetadata(
            version=data['metadata']['version'],
            tool_version=data['metadata']['tool_version'],
            created_at=data['metadata']['created_at'],
            folder_path=data['metadata']['folder_path'],
            pipeline_config_hash=data['metadata']['pipeline_config_hash'],
            folder_content_hash=data['metadata']['folder_content_hash'],
            photo_pairing_cache_hash=data['metadata']['photo_pairing_cache_hash'],
            validation_results_hash=data['metadata']['validation_results_hash'],
            total_groups=data['metadata']['total_groups'],
            total_specific_images=data['metadata']['total_specific_images'],
            consistent_count=data['metadata']['consistent_count'],
            warning_count=data['metadata']['warning_count'],
            partial_count=data['metadata']['partial_count'],
            inconsistent_count=data['metadata']['inconsistent_count']
        )

        return PipelineValidationCache(
            metadata=metadata,
            validation_results=data['validation_results']
        )
```

**Example JSON Structure:**
```json
{
  "version": "1.0",
  "tool_version": "1.0.0",
  "created_at": "2025-12-27T14:30:45Z",
  "folder_path": "/Users/photographer/Photos/2025-01-15",
  "metadata": {
    "version": "1.0",
    "tool_version": "1.0.0",
    "created_at": "2025-12-27T14:30:45Z",
    "folder_path": "/Users/photographer/Photos/2025-01-15",
    "pipeline_config_hash": "abc123def456...",
    "folder_content_hash": "789ghi012jkl...",
    "photo_pairing_cache_hash": "mno345pqr678...",
    "validation_results_hash": "stu901vwx234...",
    "total_groups": 892,
    "total_specific_images": 1124,
    "consistent_count": 654,
    "warning_count": 45,
    "partial_count": 203,
    "inconsistent_count": 222
  },
  "validation_results": [
    {
      "unique_id": "AB3D0001",
      "group_id": "AB3D0001",
      "camera_id": "AB3D",
      "counter": "0001",
      "suffix": "",
      "actual_files": ["AB3D0001.CR3", "AB3D0001.XMP", "AB3D0001.DNG"],
      "termination_matches": [
        {
          "termination_id": "termination_blackbox",
          "termination_type": "Black Box Archive",
          "status": "CONSISTENT",
          "completion_percentage": 100.0,
          "missing_files": [],
          "extra_files": [],
          "truncated": false,
          "truncation_note": null
        }
      ],
      "overall_status": "CONSISTENT",
      "archival_ready_for": ["Black Box Archive"]
    }
  ]
}
```

---

## 5. Configuration Extensions

### 5.1 Processing Pipelines Section (config.yaml)

Extension to shared PhotoAdminConfig for pipeline definitions.

```yaml
# Existing sections: photo_extensions, metadata_extensions, camera_mappings, processing_methods

# NEW SECTION: Processing Pipelines
processing_pipelines:
  nodes:
    - id: "capture"
      type: "Capture"
      name: "Camera Capture"
      output: ["raw_image_1"]

    - id: "raw_image_1"
      type: "File"
      extension: ".CR3"
      name: "Canon Raw File"
      output: ["selection_process"]

    # ... (see pipeline-config-schema.yaml for full schema)
```

---

## 6. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│ Photo Pairing Tool Output                                          │
│ ┌─────────────────────┐                                            │
│ │ ImageGroup          │                                            │
│ │ - group_id          │                                            │
│ │ - separate_images   │                                            │
│ │   {"": {...}, "2": {...}}                                        │
│ └─────────────────────┘                                            │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ▼ Flatten to Specific Images
┌─────────────────────────────────────────────────────────────────────┐
│ Specific Images                                                     │
│ ┌──────────────────┐  ┌──────────────────┐                         │
│ │ SpecificImage    │  │ SpecificImage    │                         │
│ │ - base_filename  │  │ - base_filename  │                         │
│ │ - actual_files   │  │ - actual_files   │                         │
│ └──────────────────┘  └──────────────────┘                         │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ▼ For each Specific Image, for each Termination
┌─────────────────────────────────────────────────────────────────────┐
│ Path Enumeration (DFS)                                              │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ PathState                                                       │ │
│ │ - node_sequence: [capture, raw_1, selection, ...]              │ │
│ │ - file_nodes: {raw_1, xmp_1, dng_1}                            │ │
│ │ - processing_methods: []                                        │ │
│ │ - iteration_counts: {selection: 1, dng_conv: 1}                │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                            ▼                                        │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ EnumeratedPath (result)                                         │ │
│ │ - termination_id: "termination_blackbox"                        │ │
│ │ - file_nodes: {raw_1, xmp_1, dng_1}                            │ │
│ │ - generate_expected_files() → {"AB3D0001.CR3", ...}            │ │
│ └─────────────────────────────────────────────────────────────────┘ │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ▼ Compare expected vs actual files
┌─────────────────────────────────────────────────────────────────────┐
│ Validation                                                          │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ TerminationMatchResult                                          │ │
│ │ - status: CONSISTENT                                            │ │
│ │ - completion_percentage: 100.0                                  │ │
│ │ - missing_files: []                                             │ │
│ │ - extra_files: []                                               │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                            ▼                                        │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ ValidationResult                                                │ │
│ │ - unique_id: "AB3D0001"                                         │ │
│ │ - termination_matches: [TerminationMatchResult, ...]           │ │
│ │ - overall_status: CONSISTENT                                    │ │
│ │ - archival_ready_for: ["Black Box Archive"]                    │ │
│ └─────────────────────────────────────────────────────────────────┘ │
└────────────────┬────────────────────────────────────────────────────┘
                 │
                 ▼ Serialize to cache
┌─────────────────────────────────────────────────────────────────────┐
│ Cache Storage                                                       │
│ .pipeline_validation_cache.json                                     │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ PipelineValidationCache                                         │ │
│ │ - metadata: {hashes, counts, timestamps}                        │ │
│ │ - validation_results: [ValidationResult.to_dict(), ...]        │ │
│ └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 7. Key Design Decisions

### 7.1 Immutable Data Structures

All dataclasses use `frozen=True` where appropriate to prevent accidental mutation during traversal:

```python
@dataclass(frozen=True)
class FileNode(NodeBase):
    """Immutable File node."""
    # ...
```

**Rationale**: Prevents bugs during DFS recursion where mutable state could leak between paths.

### 7.2 Set-Based File Deduplication

File nodes stored as `set[str]` (node IDs), not `list[str]`:

```python
file_nodes: set[str]  # Automatic deduplication by node ID
```

**Rationale**: Same File node appearing multiple times in path (e.g., loop scenarios) is automatically deduplicated. Filename deduplication happens later during `generate_expected_files()`.

### 7.3 Per-Termination Validation Results

Each Specific Image has separate validation results for each Termination:

```python
termination_matches: list[TerminationMatchResult]  # One per Termination node
```

**Rationale**: Supports multi-termination statistics (FR-022). A Specific Image can be archival ready for Black Box but not Browsable.

### 7.4 Truncation Transparency

Truncated paths included in results with explicit flags:

```python
truncated: bool
truncation_note: str | None  # Human-readable explanation
```

**Rationale**: Users need to know when validation is partial due to loop limits. Transparency builds trust.

---

## 8. Type Safety and Validation

### 8.1 Runtime Type Checking (Optional)

For production robustness, consider using Pydantic for runtime validation:

```python
from pydantic import BaseModel, validator

class FileNode(BaseModel):
    id: str
    type: str = "File"
    extension: str
    name: str
    output: list[str]

    @validator('extension')
    def validate_extension(cls, v):
        if not v.startswith('.'):
            raise ValueError(f"Extension must start with '.': {v}")
        return v

    class Config:
        frozen = True  # Immutable
```

**Decision for v1.0**: Use standard dataclasses for simplicity. Add Pydantic in v2.0 if needed.

---

## 9. Memory Footprint Estimates

For 10,000 ImageGroups (~12,000 Specific Images):

| Structure | Count | Size/Item | Total |
|-----------|-------|-----------|-------|
| SpecificImage | 12,000 | ~400 bytes | ~4.8 MB |
| EnumeratedPath | ~24,000 (2 terminations × 12k images) | ~300 bytes | ~7.2 MB |
| ValidationResult | 12,000 | ~600 bytes | ~7.2 MB |
| **Total Runtime Memory** | - | - | **~19 MB** |

**Cache File Size**: ~8-10 MB JSON (gzip would reduce to ~2 MB if needed).

**Conclusion**: Memory is not a constraint for target scale (10,000 groups).

---

## 10. JSON Schema References

See `contracts/` directory for formal JSON schemas:
- `pipeline-config-schema.yaml` - YAML schema for pipeline configuration
- `validation-result-schema.json` - JSON schema for validation result structure

---

**Data Model Complete**: 2025-12-27
**Reviewed By**: Claude Sonnet 4.5
**Status**: Ready for contract schema generation (Phase 1 continued)
