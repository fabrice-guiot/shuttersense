# Pipeline Processor Enhancement - Implementation Plan (T026-T041)

## Current State Analysis

**File**: `utils/pipeline_processor.py` (1,301 lines)
**Tests**: `tests/test_pipeline_validation.py` (51 tests, all passing ✓)
**Current Functionality**:
- CLI-focused pipeline validation
- Data structures: `PipelineConfig`, 6 node types, `ValidationResult`, `SpecificImage`
- Path enumeration with pairing support
- File generation and validation
- Used by `pipeline_validation.py` CLI tool

**Critical Requirement**: All 51 existing tests MUST pass after enhancements.

---

## Implementation Plan by Task Group

### Group 1: Graph Representation (T026-T029) - 4 tasks

*Purpose*: Add graph-theoretic abstractions for web API/database integration

#### T026 [P]: Add Node and Edge dataclasses

**Location**: After line 112 (after PipelineNode type alias)

```python
@dataclass
class Node:
    """
    Simplified node representation for graph algorithms.
    Wraps existing PipelineNode for API compatibility.
    """
    id: str
    type: str
    properties: Dict[str, Any]  # Node-specific data (extension, method_ids, etc.)

@dataclass
class Edge:
    """
    Explicit edge representation for graph traversal.
    """
    from_node_id: str
    to_node_id: str
    edge_type: str = "sequential"  # or "pairing_input"
```

**Why here**: Immediately after existing node definitions, before `PipelineConfig`.
**Impact**: None - new classes don't affect existing code.

---

#### T027 [P]: Add PipelineGraph class

**Location**: After line 360 (after load_pipeline_config function)

```python
class PipelineGraph:
    """
    Graph representation of pipeline for structural validation.
    Wraps PipelineConfig with graph-theoretic operations.
    """

    def __init__(self, config: Union[PipelineConfig, Dict]):
        """Initialize from PipelineConfig or raw dict."""
        if isinstance(config, PipelineConfig):
            self.config = config
        else:
            self._parse_config(config)

        self._build_adjacency_lists()

    def _parse_config(self, config_dict: Dict):
        """Parse raw config dict into PipelineConfig."""
        # Delegates to existing parse_node_from_yaml logic
        pass

    def _build_adjacency_lists(self):
        """Build forward and reverse adjacency lists."""
        self.children: Dict[str, List[str]] = {}  # node_id -> [child_ids]
        self.parents: Dict[str, List[str]] = {}   # node_id -> [parent_ids]
        # Build from config.nodes

    def get_children(self, node_id: str) -> List[str]:
        """Get child node IDs."""
        return self.children.get(node_id, [])

    def get_parents(self, node_id: str) -> List[str]:
        """Get parent node IDs."""
        return self.parents.get(node_id, [])

    def get_nodes_by_type(self, node_type: str) -> List[PipelineNode]:
        """Get all nodes of a specific type."""
        # Filter config.nodes by type
        pass
```

**Why here**: Logical grouping after pipeline loading functions.
**Impact**: None - wraps existing PipelineConfig, doesn't modify it.

---

#### T028: Implement topological_sort

**Location**: Add as method to PipelineGraph class

```python
def topological_sort(self) -> tuple[List[str], bool]:
    """
    Topological sort using Kahn's algorithm.

    Returns:
        tuple: (sorted_node_ids, has_cycle)
            - sorted_node_ids: Topologically sorted list (empty if cycle)
            - has_cycle: True if cycle detected
    """
    # Kahn's algorithm:
    # 1. Count in-degrees
    # 2. Queue nodes with in-degree 0
    # 3. Process queue, decrement in-degrees
    # 4. If processed < total, cycle exists
    pass
```

**Why here**: Core graph algorithm, method of PipelineGraph.
**Impact**: None - new method, doesn't affect existing path enumeration.

---

#### T029: Implement dfs_from_nodes

**Location**: Add as method to PipelineGraph class

```python
def dfs_from_nodes(self, start_node_ids: List[str]) -> set[str]:
    """
    DFS from given start nodes to find all reachable nodes.
    Used for orphaned node detection.

    Args:
        start_node_ids: List of node IDs to start DFS from

    Returns:
        set: All node IDs reachable from start nodes
    """
    # Standard DFS with visited set
    pass
```

**Why here**: Graph traversal method of PipelineGraph.
**Impact**: None - similar to existing validate_pipeline_structure unreachable detection (line 421), but more general.

---

### Group 2: Validation Framework (T030-T033) - 4 tasks

*Purpose*: Add structured validation with actionable error messages

#### T030 [P]: Add ValidationError dataclass

**Location**: After line 215 (after ValidationResult dataclass)

```python
@dataclass
class ValidationError:
    """
    Structured validation error for API responses.
    """
    error_type: str  # "cycle", "orphaned_node", "dead_end", "invalid_reference", etc.
    message: str     # Human-readable error message
    node_ids: List[str] = field(default_factory=list)  # Affected nodes
    guidance: str = ""  # Actionable guidance for fixing
```

**Why here**: With other validation data structures.
**Impact**: None - new class for API use.

---

#### T031: Add StructureValidator class

**Location**: After line 437 (after validate_pipeline_structure function)

```python
class StructureValidator:
    """
    Comprehensive pipeline structure validation.
    Replaces and extends validate_pipeline_structure for API use.
    """

    def __init__(self, pipeline_graph: PipelineGraph, config: PhotoAdminConfig):
        self.graph = pipeline_graph
        self.config = config
        self.errors: List[ValidationError] = []

    def validate(self) -> List[ValidationError]:
        """
        Run all validation checks.

        Returns:
            List of ValidationError instances (empty if valid)
        """
        self.errors = []
        self.detect_cycles()
        self.find_orphaned_nodes()
        self.find_dead_ends()
        self.validate_nodes()
        self.validate_property_references()
        return self.errors

    def detect_cycles(self) -> List[ValidationError]:
        """Use topological_sort to detect cycles."""
        pass

    def find_orphaned_nodes(self) -> List[ValidationError]:
        """Find nodes unreachable from Capture nodes."""
        pass

    def find_dead_ends(self) -> List[ValidationError]:
        """Find nodes that don't lead to any Termination."""
        pass
```

**Why here**: After existing validation function, related functionality.
**Impact**: Existing `validate_pipeline_structure()` remains for CLI backward compatibility.

---

#### T032: Implement validate_nodes

**Location**: Add as method to StructureValidator class

```python
def validate_nodes(self) -> List[ValidationError]:
    """
    Validate node-specific constraints.

    Checks:
    - Capture: No inputs required
    - File: Must have extension
    - Process: Must have method_ids list
    - Pairing: Must have exactly 2 inputs
    - Branching: Must have multiple outputs
    - Termination: Must have termination_type
    """
    # Similar to existing validation logic but with structured errors
    pass
```

**Why here**: Method of StructureValidator.
**Impact**: None - complements existing checks, returns structured errors.

---

#### T033: Implement validate_property_references

**Location**: Add as method to StructureValidator class

```python
def validate_property_references(self) -> List[ValidationError]:
    """
    Validate processing_methods and extensions exist in config.

    Checks:
    - Process nodes: method_ids exist in config.processing_methods
    - File nodes: extensions exist in config.photo_extensions
    """
    # Extracts logic from existing validate_pipeline_structure (lines 394-415)
    # Returns structured ValidationError instead of strings
    pass
```

**Why here**: Method of StructureValidator.
**Impact**: Existing function remains unchanged for CLI.

---

### Group 3: Filename Preview (T034-T036) - 3 tasks

*Purpose*: Generate filename previews for UI display

#### T034 [P]: Add FilenamePreviewGenerator class

**Location**: After line 1056 (after generate_sample_base_filename function)

```python
class FilenamePreviewGenerator:
    """
    Generate filename previews for pipeline visualization.
    Used by web UI to show example filenames for each path.
    """

    def __init__(self, pipeline: PipelineConfig):
        self.pipeline = pipeline

    def generate_preview(
        self,
        camera_id: str = "AB3D",
        counter: str = "0001"
    ) -> Dict[str, List[str]]:
        """
        Generate preview filenames for all termination types.

        Args:
            camera_id: Camera ID for preview (default: "AB3D")
            counter: Counter for preview (default: "0001")

        Returns:
            Dict mapping termination_type to list of example filenames
        """
        paths = self._find_all_paths()
        previews = {}

        for path in paths:
            term_type = self._get_termination_type(path)
            if term_type:
                filenames = self._apply_path_transformations(path, camera_id, counter)
                if term_type not in previews:
                    previews[term_type] = []
                previews[term_type].extend(filenames)

        # Deduplicate
        for term_type in previews:
            previews[term_type] = sorted(set(previews[term_type]))

        return previews
```

**Why here**: After filename generation functions, related functionality.
**Impact**: None - uses existing path enumeration logic.

---

#### T035: Implement _find_all_paths

**Location**: Add as method to FilenamePreviewGenerator class

```python
def _find_all_paths(self) -> List[List[Dict[str, Any]]]:
    """
    Find all Capture → Termination paths.
    Delegates to existing enumerate_paths_with_pairing().
    """
    return enumerate_paths_with_pairing(self.pipeline)
```

**Why here**: Method of FilenamePreviewGenerator.
**Impact**: None - calls existing function.

---

#### T036: Implement _apply_path_transformations

**Location**: Add as method to FilenamePreviewGenerator class

```python
def _apply_path_transformations(
    self,
    path: List[Dict[str, Any]],
    camera_id: str,
    counter: str
) -> List[str]:
    """
    Build filename from path node properties.
    Delegates to existing generate_expected_files().

    Args:
        path: Path through pipeline
        camera_id: Camera ID
        counter: Counter value

    Returns:
        List of filenames for this path
    """
    base = f"{camera_id}{counter}"
    return generate_expected_files(path, base, suffix="")
```

**Why here**: Method of FilenamePreviewGenerator.
**Impact**: None - calls existing function.

---

### Group 4: Collection Validation (T037-T040) - 4 tasks

*Purpose*: Add collection-level validation for web API

#### T037 [P]: Add ImageGroupStatus enum

**Location**: After line 157 (after ValidationStatus enum)

```python
class ImageGroupStatus(Enum):
    """
    Validation status for Image Groups (web API).
    Simplified from ValidationStatus for database storage.
    """
    CONSISTENT = "CONSISTENT"      # All expected files present
    PARTIAL = "PARTIAL"            # Some files present
    INCONSISTENT = "INCONSISTENT"  # No valid match or critical files missing

    @classmethod
    def from_validation_status(cls, status: ValidationStatus) -> 'ImageGroupStatus':
        """Convert ValidationStatus to ImageGroupStatus."""
        if status == ValidationStatus.CONSISTENT:
            return cls.CONSISTENT
        elif status in (ValidationStatus.CONSISTENT_WITH_WARNING, ValidationStatus.PARTIAL):
            return cls.PARTIAL
        else:
            return cls.INCONSISTENT
```

**Why here**: With other status enums.
**Impact**: None - new enum for API use.

---

#### T038 [P]: Add ImageGroup dataclass

**Location**: After line 179 (after SpecificImage dataclass)

```python
@dataclass
class ImageGroup:
    """
    Image group representation for web API/database.
    Aggregates multiple SpecificImage instances.
    """
    base: str  # e.g., "AB3D0001" (camera_id + counter, no suffix)
    files: List[str]  # All files for this group
    status: ImageGroupStatus
    completed_nodes: List[str] = field(default_factory=list)  # Node IDs reached
    missing_files: List[str] = field(default_factory=list)    # Files not present
```

**Why here**: With other image data structures.
**Impact**: None - new class for API use.

---

#### T039: Add CollectionValidator class

**Location**: After line 1300 (end of file)

```python
class CollectionValidator:
    """
    Validate entire photo collection against pipeline.
    Aggregates SpecificImage validations into ImageGroups for API.
    """

    def __init__(self, pipeline: PipelineConfig):
        self.pipeline = pipeline

    def validate(
        self,
        files: List[str],
        show_progress: bool = False
    ) -> Dict[str, ImageGroup]:
        """
        Validate collection files.

        Args:
            files: List of filenames in collection
            show_progress: Show progress indicator

        Returns:
            Dict mapping base filename to ImageGroup
        """
        # Group files by base
        grouped = self._group_files(files)

        # Validate each group
        results = {}
        for base, group_files in grouped.items():
            results[base] = self._validate_group(base, group_files)

        return results

    def _group_files(self, files: List[str]) -> Dict[str, List[str]]:
        """Group files by base filename (camera_id + counter)."""
        # Parse filenames using FilenameParser
        # Group by camera_id + counter
        pass

    def _validate_group(self, base: str, files: List[str]) -> ImageGroup:
        """Validate single image group."""
        # Get expected files
        expected = self._get_expected_files_for_base(base)

        # Compare actual vs expected
        status = self._determine_status(set(files), expected)

        return ImageGroup(
            base=base,
            files=files,
            status=status,
            completed_nodes=self._identify_completed_nodes(files, expected),
            missing_files=self._identify_missing_files(files, expected)
        )
```

**Why here**: End of file, high-level API functionality.
**Impact**: None - new class, uses existing validation logic.

---

#### T040: Implement _get_expected_files_for_base

**Location**: Add as method to CollectionValidator class

```python
def _get_expected_files_for_base(self, base: str) -> Dict[str, List[str]]:
    """
    Get expected files for base filename using preview logic.

    Args:
        base: Base filename (e.g., "AB3D0001")

    Returns:
        Dict mapping termination_type to list of expected files
    """
    # Parse base into camera_id and counter
    # camera_id = first 4 chars, counter = last 4 chars
    camera_id = base[:4]
    counter = base[4:]

    # Use FilenamePreviewGenerator to get expected files
    generator = FilenamePreviewGenerator(self.pipeline)
    return generator.generate_preview(camera_id, counter)
```

**Why here**: Method of CollectionValidator.
**Impact**: None - uses new FilenamePreviewGenerator.

---

### Group 5: Readiness Calculation (T041) - 1 task

*Purpose*: Calculate archival readiness metrics

#### T041 [P]: Add ReadinessCalculator class

**Location**: After CollectionValidator class (end of file)

```python
class ReadinessCalculator:
    """
    Calculate archival readiness metrics for collections.
    Used by web API to show progress statistics.
    """

    def __init__(self, pipeline: PipelineConfig):
        self.pipeline = pipeline

    def calculate(
        self,
        validation_results: Dict[str, ImageGroup]
    ) -> Dict[str, Any]:
        """
        Calculate readiness metrics.

        Args:
            validation_results: Dict of base -> ImageGroup from CollectionValidator

        Returns:
            Dict with metrics:
            - total_groups: Total image groups
            - consistent_groups: Groups with CONSISTENT status
            - partial_groups: Groups with PARTIAL status
            - inconsistent_groups: Groups with INCONSISTENT status
            - archival_ready_percentage: % of CONSISTENT groups
            - node_completion: Dict of node_id -> count of groups reaching it
        """
        total = len(validation_results)
        consistent = sum(1 for g in validation_results.values() if g.status == ImageGroupStatus.CONSISTENT)
        partial = sum(1 for g in validation_results.values() if g.status == ImageGroupStatus.PARTIAL)
        inconsistent = sum(1 for g in validation_results.values() if g.status == ImageGroupStatus.INCONSISTENT)

        return {
            'total_groups': total,
            'consistent_groups': consistent,
            'partial_groups': partial,
            'inconsistent_groups': inconsistent,
            'archival_ready_percentage': (consistent / total * 100) if total > 0 else 0,
            'node_completion': self._count_groups_reaching_node(validation_results)
        }

    def _count_groups_reaching_node(
        self,
        validation_results: Dict[str, ImageGroup]
    ) -> Dict[str, int]:
        """
        Count how many groups reached each node.

        Returns:
            Dict mapping node_id to count
        """
        counts = {}
        for group in validation_results.values():
            for node_id in group.completed_nodes:
                counts[node_id] = counts.get(node_id, 0) + 1
        return counts
```

**Why here**: End of file, analytics functionality.
**Impact**: None - new class for API metrics.

---

## File Structure After Implementation

```
utils/pipeline_processor.py (est. ~2,100 lines)

Lines 1-42:    [Existing] Imports, Constants
Lines 43-112:  [Existing] Node dataclasses (Capture, File, Process, etc.)
Lines 113-120: [NEW] Node and Edge dataclasses (T026)
Lines 121-133: [Existing] PipelineConfig
Lines 134-214: [Existing] ValidationStatus, SpecificImage, TerminationMatchResult, ValidationResult
Lines 215-222: [NEW] ValidationError dataclass (T030)
Lines 223-230: [NEW] ImageGroupStatus enum (T037)
Lines 231-241: [NEW] ImageGroup dataclass (T038)
Lines 242-360: [Existing] parse_node_from_yaml, load_pipeline_config
Lines 361-437: [NEW] PipelineGraph class (T027-T029)
Lines 438-520: [Existing] validate_pipeline_structure
Lines 521-600: [NEW] StructureValidator class (T031-T033)
Lines 601-976: [Existing] Path enumeration, pairing support
Lines 977-1056: [Existing] File generation functions
Lines 1057-1150: [NEW] FilenamePreviewGenerator class (T034-T036)
Lines 1151-1300: [Existing] Validation logic
Lines 1301-1450: [NEW] CollectionValidator class (T039-T040)
Lines 1451-1550: [NEW] ReadinessCalculator class (T041)
```

---

## Testing Strategy

### Pre-Implementation Verification

✅ **DONE**: All 51 tests passing in `tests/test_pipeline_validation.py`

### During Implementation

- Add new classes incrementally (groups 1-5)
- Run tests after each group to catch regressions early
- New classes don't modify existing functionality, only add to it

### Post-Implementation Verification

1. **Run full test suite**:
   ```bash
   python3 -m pytest tests/test_pipeline_validation.py -v
   ```
   **Expected**: All 51 tests pass (no regressions)

2. **Smoke test new classes**:
   ```python
   # Quick validation that new classes can be instantiated
   from utils.pipeline_processor import (
       Node, Edge, PipelineGraph, ValidationError,
       StructureValidator, FilenamePreviewGenerator,
       ImageGroupStatus, ImageGroup, CollectionValidator,
       ReadinessCalculator
   )
   ```

3. **Integration test**:
   - Load existing test pipeline config
   - Instantiate each new class with test data
   - Verify no exceptions raised

### Success Criteria

- ✅ All 51 existing tests pass
- ✅ No import errors
- ✅ New classes can be instantiated with test data
- ✅ Existing CLI tool (`pipeline_validation.py`) still works

---

## Risk Mitigation

**Risk**: Adding 800+ lines could introduce import/syntax errors
**Mitigation**: Incremental implementation by task group, test after each group

**Risk**: Name collisions with existing code
**Mitigation**: All new class names verified unique (PipelineGraph, StructureValidator, etc. don't exist)

**Risk**: Performance degradation
**Mitigation**: New code only runs when explicitly called, doesn't affect existing CLI path

**Risk**: Accidental modification of existing functions
**Mitigation**: Only APPEND to file, never modify existing lines 1-1301

---

## Implementation Order

1. **T026** (Node, Edge) - Simple dataclasses, no dependencies
2. **T030, T037, T038** (ValidationError, ImageGroupStatus, ImageGroup) - Simple dataclasses
3. **T027-T029** (PipelineGraph) - Requires Node/Edge
4. **T031-T033** (StructureValidator) - Requires PipelineGraph, ValidationError
5. **T034-T036** (FilenamePreviewGenerator) - Uses existing functions
6. **T039-T040** (CollectionValidator) - Requires ImageGroup, FilenamePreviewGenerator
7. **T041** (ReadinessCalculator) - Requires ImageGroup
8. **Test** - Run full test suite

---

## Summary

**What's Being Added**: 5 new classes, 3 new dataclasses, 1 new enum (~800 lines total)
**What's NOT Changing**: All existing classes, functions, and logic (lines 1-1301)
**Why It's Safe**: New code is append-only, doesn't modify existing functionality
**Test Coverage**: 51 existing tests ensure no regressions
**Time Estimate**: ~45-60 minutes to implement and test all tasks

**Implementation Status**: PENDING
**Created**: 2025-12-29
**Author**: Claude Code (Sonnet 4.5)
