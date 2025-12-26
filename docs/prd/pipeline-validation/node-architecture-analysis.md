# Node-Based Pipeline Architecture Analysis

## Critical Insight: File Nodes Define Valid Specific Images

### Executive Summary

The node-based pipeline architecture represents a fundamental shift from the original stage-based model. **File nodes are the critical element** that defines what constitutes a valid Specific Image in an ImageGroup (as defined by the Photo Pairing Tool).

**Key Principle:**
> A valid Specific Image = All File nodes encountered on a complete path from Capture to Termination

---

## Architecture Comparison

### Original Stage-Based Model (Deprecated)

```yaml
stages:
  - id: capture
    file_types: [.cr3]
  - id: import
    file_types: [.cr3, .xmp]
  - id: dng_conversion
    file_types: [.dng]

paths:
  - id: raw_archive
    stages: [capture, import]
```

**Limitations:**
- Linear progression only
- No branching or looping
- Difficult to represent parallel processes
- Cannot model conditional workflows
- Files tied to stages, not explicitly tracked

---

### New Node-Based Model

```yaml
nodes:
  - id: capture_1
    type: Capture
    output: [raw_image_1]

  - id: raw_image_1
    type: File
    extension: .CR3
    output: [selection_process]

  - id: selection_process
    type: Process
    method_ids: [""]
    output: [raw_image_2, xmp_metadata_1]

  - id: raw_image_2
    type: File
    extension: .CR3
    output: [metadata_pairing]

  - id: xmp_metadata_1
    type: File
    extension: .XMP
    output: [metadata_pairing]

  - id: termination_blackbox
    type: Termination
```

**Advantages:**
- Directed graph structure
- Supports branching and looping
- Explicit File nodes track actual files
- Processes can be chained
- Multiple termination points
- **File nodes = actual files in ImageGroup**

---

## Node Types Explained

### 1. Capture Node

**Purpose:** Start of the pipeline
**Cardinality:** Exactly one per pipeline
**Output:** Initial File node(s)

```yaml
- id: capture_1
  type: Capture
  name: "Camera capture"
  output:
    - raw_image_1
    - lowres_jpeg  # Camera-generated preview
```

**Represents:** The moment a photo is taken by the camera

---

### 2. File Node (★ CRITICAL ★)

**Purpose:** Represents an actual file that exists in the filesystem
**File Types:** Image or Metadata
**Extension:** Must match photo_extensions or metadata_extensions config

```yaml
- id: raw_image_1
  type: File
  file_type: Image
  extension: .CR3
  name: "Raw Image File (.CR3)"
  output: [selection_process]
```

**Why Critical:**
- **File nodes are collected during path traversal**
- **Each Termination accumulates all File nodes from Capture → Termination**
- **This collection = the Specific Image definition for ImageGroup validation**

**Example:**
```
Path: Capture → raw_image_1 (.CR3) → selection_process →
      raw_image_2 (.CR3) → xmp_metadata_1 (.XMP) → termination_blackbox

File nodes encountered:
  - raw_image_1: AB3D0001.CR3
  - raw_image_2: AB3D0001.CR3 (same file, post-selection)
  - xmp_metadata_1: AB3D0001.XMP

Specific Image = {AB3D0001.CR3, AB3D0001.XMP}
```

**Filename Preservation:**
- File nodes inherit base filename (camera_id + counter) from Capture
- Example: AB3D0001 throughout the pipeline
- Processing methods append to filename: AB3D0001-HDR.TIF

---

### 3. Process Node

**Purpose:** Transform files via processing methods
**Can Chain:** Yes (Process → Process without File interface)
**Can Loop:** Yes (output back to earlier node)
**Method IDs:** From processing_methods config

```yaml
- id: developing_process
  type: Process
  method_ids:
    - "DxO_DeepPRIME XD2s"
    - "DxO_DeepPRIME XD3"
  name: "Digital Developing Process with DxO"
  output: [openformat_raw_image]
```

**Method ID Behavior:**
- Empty string `""`: No property added to filename
- Non-empty: Appends to filename (AB3D0001 → AB3D0001-DxO_DeepPRIME_XD2s)
- Multiple methods: Can apply same method multiple times via loops

**Example Chain:**
```
tiff_image → individual_photoshop_process (method: "Edit") →
tiff_generation_branching → topaz_process (method: "topaz") →
tiff_generation_branching → tiff_image

Result: AB3D0001-Edit-topaz.TIF
```

---

### 4. Pairing Node

**Purpose:** Combine multiple File nodes into a logical pair
**Use Case:** Metadata pairing (CR3 + XMP)

```yaml
- id: metadata_pairing
  type: Pairing
  name: "Raw + XMP Pairing"
  output: [denoise_branching]
```

**Validation:**
- Ensures both files exist before proceeding
- Matches PhotoStats' CR3+XMP pairing logic
- Multiple files must share same base filename

**Example:**
```
Inputs: raw_image_2 (AB3D0001.CR3) + xmp_metadata_1 (AB3D0001.XMP)
Validation: Both files exist with base AB3D0001
Output: Paired unit proceeds to next node
```

---

### 5. Branching Node

**Purpose:** Conditional path selection
**Behavior:** Only ONE output path selected per traversal
**Looping:** Can loop back, allowing multiple selections over time

```yaml
- id: denoise_branching
  type: Branching
  name: "Denoise Process Choice"
  output:
    - developing_process      # Option 1: DNG conversion
    - targeted_tone_mapping_process  # Option 2: Direct tone mapping
```

**Traversal Logic:**
```
At denoise_branching, choose ONE of:
  1. developing_process (creates DNG)
  2. targeted_tone_mapping_process (skip DNG)

If loop back to denoise_branching, can choose differently
```

**Contrast with Parallel Outputs:**
```yaml
# Branching: Choose ONE
output:
  - option_a
  - option_b

# Parallel: Execute ALL
output:
  - parallel_task_1
  - parallel_task_2
```

---

### 6. Termination Node

**Purpose:** End of pipeline, defines archival endpoint
**Cardinality:** Multiple allowed per pipeline
**Critical Function:** **Accumulates all File nodes from Capture to this point**

```yaml
- id: termination_blackbox
  type: Termination
  name: "Blackbox Termination"
  output: []
```

**File Accumulation:**
```
Capture → File1 → Process1 → File2 → Process2 → File3 → Termination

Termination accumulates: {File1, File2, File3}
This = Specific Image for ImageGroup validation
```

**Example Path to termination_blackbox:**
```
capture_1 →
  raw_image_1 (.CR3) →
  selection_process →
    raw_image_2 (.CR3) →
    xmp_metadata_1 (.XMP) →
  metadata_pairing →
  denoise_branching →
  developing_process →
    openformat_raw_image (.DNG) →
  targeted_tone_mapping_process →
  tiff_generation_branching →
    tiff_image (.TIF) →
  termination_blackbox

Files accumulated:
  - raw_image_1: AB3D0001.CR3
  - raw_image_2: AB3D0001.CR3 (same file after selection)
  - xmp_metadata_1: AB3D0001.XMP
  - openformat_raw_image: AB3D0001-DxO_DeepPRIME_XD2s.DNG
  - tiff_image: AB3D0001-DxO_DeepPRIME_XD2s.TIF

Specific Image = {
  AB3D0001.CR3,
  AB3D0001.XMP,
  AB3D0001-DxO_DeepPRIME_XD2s.DNG,
  AB3D0001-DxO_DeepPRIME_XD2s.TIF
}
```

---

## Integration with Photo Pairing Tool

### CRITICAL: Specific Images vs ImageGroups

**ImageGroup** (from Photo Pairing Tool):
- Container grouping files by `camera_id + counter`
- Contains multiple **Specific Images** when counter loops

**Specific Image** (within ImageGroup):
- **THE UNIT FOR PIPELINE VALIDATION**
- Represents ONE captured image and all its processed derivatives
- Has unique identifier: `camera_id + counter + suffix`
- Suffix differentiates separate captures when counter loops

**Important Distinction:**
- Numerical suffixes (2, 3, etc.) = Different captured images (counter looped)
- Processing properties (HDR, BW, etc.) = Processing stages within SAME capture

### ImageGroup Structure (Existing)

```python
{
    'group_id': 'AB3D0001',
    'camera_id': 'AB3D',
    'counter': '0001',
    'separate_images': {  # Each entry = ONE captured image (Specific Image)
        '': {  # First capture (no suffix, blank key)
            'files': [
                'AB3D0001.CR3',
                'AB3D0001.XMP',
                'AB3D0001.DNG',
                'AB3D0001.TIF',
                'AB3D0001-HDR.TIF'  # HDR is processing property, same capture
            ],
            'properties': []  # No properties at group level
        },
        '2': {  # Second capture (counter looped, suffix=2)
            'files': [
                'AB3D0001-2.CR3',
                'AB3D0001-2.XMP',
                'AB3D0001-2.DNG'
            ],
            'properties': []
        },
        '3': {  # Third capture (counter looped again, suffix=3)
            'files': [
                'AB3D0001-3.CR3',
                'AB3D0001-3.XMP'
            ],
            'properties': []
        }
    }
}
```

**This ImageGroup contains 3 Specific Images:**
1. `AB3D0001` (suffix='') - First captured image
2. `AB3D0001-2` (suffix='2') - Second captured image (counter looped)
3. `AB3D0001-3` (suffix='3') - Third captured image (counter looped)

**Each Specific Image is validated independently against the pipeline.**

### How Pipeline Validation Uses This

**Step 0: Flatten ImageGroups to Specific Images**
```python
# Input: ImageGroup with 3 separate_images
ImageGroup AB3D0001

# Flatten to Specific Images:
SpecificImage 1: AB3D0001 (suffix='')
  Files: [AB3D0001.CR3, AB3D0001.XMP, AB3D0001.DNG, AB3D0001.TIF, AB3D0001-HDR.TIF]

SpecificImage 2: AB3D0001-2 (suffix='2')
  Files: [AB3D0001-2.CR3, AB3D0001-2.XMP, AB3D0001-2.DNG]

SpecificImage 3: AB3D0001-3 (suffix='3')
  Files: [AB3D0001-3.CR3, AB3D0001-3.XMP]
```

**Step 1: Validate Each Specific Image Independently**

For SpecificImage 1 (AB3D0001):
```
Files in this Specific Image:
  AB3D0001.CR3
  AB3D0001.XMP
  AB3D0001.DNG
  AB3D0001.TIF
  AB3D0001-HDR.TIF  # HDR is processing property from individual_photoshop_process

→ Validate against pipeline using base_filename = "AB3D0001"
```

For SpecificImage 2 (AB3D0001-2):
```
Files in this Specific Image:
  AB3D0001-2.CR3
  AB3D0001-2.XMP
  AB3D0001-2.DNG

→ Validate against pipeline using base_filename = "AB3D0001-2"
```

**Step 2: Pipeline Traversal (per Specific Image)**
```
For each Specific Image:
  For each Termination node:
    1. Traverse from Capture to Termination
    2. Collect all File nodes encountered
    3. Generate expected filenames:
       - Use Specific Image's base_filename (e.g., "AB3D0001-2")
       - Append processing methods from Process nodes
       - Add extensions from File nodes
    4. Compare with actual files in this Specific Image only
```

**Step 3: Classification (per Specific Image)**
```python
# For SpecificImage 1 (AB3D0001):
expected_files = traverse_to_termination('termination_blackbox', base='AB3D0001')
# Returns: {
#   'AB3D0001.CR3',
#   'AB3D0001.XMP',
#   'AB3D0001-DxO_DeepPRIME_XD2s.DNG',
#   'AB3D0001-DxO_DeepPRIME_XD2s.TIF',
#   'AB3D0001-DxO_DeepPRIME_XD2s-HDR.TIF'  # If individual_photoshop_process
# }

actual_files_for_this_specific_image = {
    'AB3D0001.CR3',
    'AB3D0001.XMP',
    'AB3D0001.DNG',
    'AB3D0001.TIF',
    'AB3D0001-HDR.TIF'
}

if expected_files == actual_files_for_this_specific_image:
    result = {
        'unique_id': 'AB3D0001',
        'status': 'CONSISTENT',
        'archival_ready': True
    }

# For SpecificImage 2 (AB3D0001-2):
expected_files = traverse_to_termination('termination_blackbox', base='AB3D0001-2')
# Returns: {
#   'AB3D0001-2.CR3',
#   'AB3D0001-2.XMP',
#   'AB3D0001-2-DxO_DeepPRIME_XD2s.DNG',
#   'AB3D0001-2-DxO_DeepPRIME_XD2s.TIF'
# }

actual_files_for_this_specific_image = {
    'AB3D0001-2.CR3',
    'AB3D0001-2.XMP',
    'AB3D0001-2.DNG'
}

if expected_files != actual_files_for_this_specific_image:
    result = {
        'unique_id': 'AB3D0001-2',
        'status': 'INCONSISTENT',
        'missing_files': ['AB3D0001-2-DxO_DeepPRIME_XD2s.TIF'],
        'archival_ready': False
    }
```

**Output: 3 independent validation results (one per Specific Image)**
```python
[
    {'unique_id': 'AB3D0001', 'status': 'CONSISTENT', 'archival_ready': True},
    {'unique_id': 'AB3D0001-2', 'status': 'INCONSISTENT', 'archival_ready': False},
    {'unique_id': 'AB3D0001-3', 'status': 'INCONSISTENT', 'archival_ready': False}
]
```

---

## Path Traversal Algorithm

### Pseudocode

```python
def traverse_pipeline(start_node, end_node, pipeline_config):
    """
    Traverse pipeline from start to end, collecting File nodes.

    Returns:
        List of File nodes encountered on path
    """
    visited = set()
    file_nodes = []

    def dfs(current_node, path=[]):
        if current_node.id in visited:
            # Handle loops (track iterations)
            return

        visited.add(current_node.id)
        path.append(current_node)

        # Collect File nodes
        if current_node.type == 'File':
            file_nodes.append(current_node)

        # Terminal condition
        if current_node.id == end_node.id:
            return path

        # Handle branching
        if current_node.type == 'Branching':
            # For validation, explore ALL branches
            for output_id in current_node.output:
                next_node = get_node(output_id)
                dfs(next_node, path.copy())
        else:
            # Normal traversal
            for output_id in current_node.output:
                next_node = get_node(output_id)
                dfs(next_node, path.copy())

    dfs(start_node)
    return file_nodes
```

### Example: All Paths to termination_blackbox

```
Path 1 (with DNG conversion):
  capture_1 → raw_image_1 → selection_process → raw_image_2 →
  xmp_metadata_1 → metadata_pairing → denoise_branching →
  developing_process → openformat_raw_image →
  targeted_tone_mapping_process → tiff_generation_branching →
  tiff_image → termination_blackbox

  Files: {.CR3, .XMP, .DNG, .TIF}

Path 2 (skip DNG):
  capture_1 → raw_image_1 → selection_process → raw_image_2 →
  xmp_metadata_1 → metadata_pairing → denoise_branching →
  targeted_tone_mapping_process → tiff_generation_branching →
  tiff_image → termination_blackbox

  Files: {.CR3, .XMP, .TIF}

Path 3 (with Photoshop edit):
  ... → tiff_generation_branching → individual_photoshop_process →
  tiff_generation_branching → tiff_image → termination_blackbox

  Files: {.CR3, .XMP, .DNG/.TIF, .TIF (with Edit property)}
```

**Validation Strategy:**
- ImageGroup must match AT LEAST ONE complete path
- If matches multiple paths, report all matching paths
- If matches NO complete paths, identify closest match and missing files

---

## Filename Construction Rules

### Base Filename Preservation

**Rule:** All files in a pipeline share the same base (camera_id + counter)

```
Capture creates: AB3D0001
All downstream files: AB3D0001.CR3, AB3D0001.XMP, AB3D0001.DNG, etc.
```

### Processing Method Appending

**Rule:** Process nodes append method_id to filename

```yaml
Process:
  method_ids: ["DxO_DeepPRIME_XD2s"]

Input: AB3D0001.CR3
Output: AB3D0001-DxO_DeepPRIME_XD2s.DNG
```

**Empty Method ID:**
```yaml
Process:
  method_ids: [""]

Input: AB3D0001.CR3
Output: AB3D0001.DNG  # No property appended
```

### Chained Processing

**Rule:** Multiple processes chain their method_ids

```
Process 1: method_id = "Edit"
  AB3D0001.TIF → AB3D0001-Edit.TIF

Process 2: method_id = "topaz"
  AB3D0001-Edit.TIF → AB3D0001-Edit-topaz.TIF
```

### Loop Handling

**Rule:** Looping back can apply same method multiple times

```
Loop iteration 1: AB3D0001 → AB3D0001-Edit
Loop iteration 2: AB3D0001-Edit → AB3D0001-Edit-Edit
Loop iteration 3: AB3D0001-Edit-Edit → AB3D0001-Edit-Edit-Edit
```

**Note:** Photo Pairing Tool already handles this via property parsing

---

## Validation Examples

### Example 1: Complete Path (Consistent)

**ImageGroup Files:**
```
AB3D0001.CR3
AB3D0001.XMP
AB3D0001-DxO_DeepPRIME_XD2s.DNG
AB3D0001-DxO_DeepPRIME_XD2s.TIF
```

**Pipeline Traversal to termination_blackbox:**
```
File nodes collected:
  - raw_image_1: .CR3
  - raw_image_2: .CR3 (same file)
  - xmp_metadata_1: .XMP
  - openformat_raw_image: .DNG (with DxO method)
  - tiff_image: .TIF (with DxO method)

Expected files:
  AB3D0001.CR3
  AB3D0001.XMP
  AB3D0001-DxO_DeepPRIME_XD2s.DNG
  AB3D0001-DxO_DeepPRIME_XD2s.TIF
```

**Result:**
```yaml
status: CONSISTENT
matched_termination: termination_blackbox
archival_ready: true
missing_files: []
```

---

### Example 2: Missing DNG (Inconsistent)

**ImageGroup Files:**
```
AB3D0001.CR3
AB3D0001.XMP
AB3D0001.TIF
```

**Pipeline Traversal:**
```
Expected (Path 1 with DNG):
  AB3D0001.CR3 ✓
  AB3D0001.XMP ✓
  AB3D0001-DxO_DeepPRIME_XD2s.DNG ✗ MISSING
  AB3D0001-DxO_DeepPRIME_XD2s.TIF ≠ AB3D0001.TIF

Expected (Path 2 skip DNG):
  AB3D0001.CR3 ✓
  AB3D0001.XMP ✓
  AB3D0001.TIF ✓ (no method ID expected)
```

**Result:**
```yaml
status: PARTIAL
matched_termination: null  # No complete match
closest_match:
  path: "Path 2 (skip DNG)"
  completion: 100%
  note: "Matches path without DNG conversion"
archival_ready: true  # If Path 2 is terminal
missing_files: []
```

---

### Example 3: Browsable Archive

**ImageGroup Files:**
```
AB3D0001.CR3
AB3D0001.XMP
AB3D0001-DxO_DeepPRIME_XD2s.DNG
AB3D0001-DxO_DeepPRIME_XD2s.TIF
AB3D0001-DxO_DeepPRIME_XD2s-lowres.JPG
AB3D0001-DxO_DeepPRIME_XD2s-highres.JPG
```

**Pipeline Traversal to termination_browsable:**
```
File nodes collected:
  - All from termination_blackbox path
  - lowres_jpeg: .JPG (lowres property)
  - highres_jpeg: .JPG (highres property)

Expected files:
  AB3D0001.CR3
  AB3D0001.XMP
  AB3D0001-DxO_DeepPRIME_XD2s.DNG
  AB3D0001-DxO_DeepPRIME_XD2s.TIF
  AB3D0001-DxO_DeepPRIME_XD2s-lowres.JPG
  AB3D0001-DxO_DeepPRIME_XD2s-highres.JPG
```

**Result:**
```yaml
status: CONSISTENT
matched_termination: termination_browsable
archival_ready: true
archival_type: browsable
missing_files: []
```

---

## Edge Cases

### 1. Duplicate File Extensions

**Scenario:** lowres_jpeg and highres_jpeg both create .JPG files

**Solution:** Use file_type or additional property distinguisher
```yaml
- id: lowres_jpeg
  type: File
  extension: .JPG
  property_suffix: "lowres"  # AB3D0001-lowres.JPG

- id: highres_jpeg
  type: File
  extension: .JPG
  property_suffix: "highres"  # AB3D0001-highres.JPG
```

### 2. Same File, Different Nodes

**Scenario:** raw_image_1 and raw_image_2 both represent AB3D0001.CR3

**Solution:** Deduplication during File node collection
```python
file_nodes_dedup = {}
for node in file_nodes:
    key = (node.extension, node.get_filename(base))
    if key not in file_nodes_dedup:
        file_nodes_dedup[key] = node
```

### 3. Multiple Method IDs in One Process

**Scenario:** Process has method_ids: ["DxO_DeepPRIME_XD2s", "DxO_DeepPRIME_XD3"]

**Interpretation:** Branching choice (similar to Branching node)
```
User can choose EITHER:
  - DxO_DeepPRIME_XD2s
  - DxO_DeepPRIME_XD3

Creates two possible paths through this Process node
```

### 4. Parallel Outputs (Non-Branching)

**Scenario:** Node outputs to multiple nodes without Branching type

**Behavior:** ALL outputs executed (parallel paths)
```yaml
- id: tiff_image
  output:
    - termination_blackbox  # Path 1
    - lowres_jpeg           # Path 2
    - highres_jpeg          # Path 3

All three paths execute simultaneously
```

---

## Implementation Implications

### 1. Configuration Validation

**Must Validate:**
- Exactly one Capture node per pipeline
- All node IDs unique
- All output references valid node IDs
- No orphaned nodes (unreachable from Capture)
- At least one Termination node
- File extensions match photo_extensions config
- Processing method IDs match processing_methods config

### 2. Path Enumeration

**Algorithm:** DFS from Capture to each Termination
```python
def enumerate_all_paths(pipeline):
    capture = find_capture_node(pipeline)
    terminations = find_termination_nodes(pipeline)

    all_paths = []
    for termination in terminations:
        paths = dfs_all_paths(capture, termination)
        all_paths.extend(paths)

    return all_paths
```

### 3. ImageGroup Matching

**Algorithm:** Compare ImageGroup files against all enumerated paths
```python
def validate_imagegroup(imagegroup, pipeline):
    all_paths = enumerate_all_paths(pipeline)

    for path in all_paths:
        expected_files = collect_file_nodes(path)
        expected_filenames = generate_filenames(expected_files, imagegroup.base)

        if imagegroup.files == expected_filenames:
            return {'status': 'CONSISTENT', 'path': path}

    # No exact match, find closest
    return find_closest_match(imagegroup, all_paths)
```

### 4. Missing File Identification

**Algorithm:** Set difference between expected and actual
```python
def find_missing_files(imagegroup, target_path):
    expected = collect_file_nodes(target_path)
    expected_filenames = generate_filenames(expected, imagegroup.base)

    actual_filenames = set(imagegroup.files)

    missing = expected_filenames - actual_filenames
    extra = actual_filenames - expected_filenames

    return {'missing': missing, 'extra': extra}
```

---

## Summary

**Key Takeaways:**

1. **File nodes are the foundation** of Specific Image validation
2. **Termination nodes accumulate File nodes** encountered from Capture
3. **This accumulation defines the expected file set** for that archival path
4. **ImageGroup validation = comparing actual files vs accumulated File nodes**
5. **Node-based architecture supports complex workflows** (branching, looping, parallel)
6. **Filename construction follows processing method chain**
7. **Photo Pairing Tool groups files; Pipeline Validation validates completeness**

**Integration Flow:**
```
Photo Collection
  ↓
Photo Pairing Tool: Group by camera_id + counter
  ↓
ImageGroups with Specific Images
  ↓
Pipeline Validation: Traverse configured pipeline
  ↓
Collect File nodes from Capture → Termination
  ↓
Compare expected vs actual files
  ↓
Classification: CONSISTENT | PARTIAL | INCONSISTENT
```

This architecture provides the flexibility needed to model real-world photography workflows while maintaining clear validation criteria for archival readiness.
