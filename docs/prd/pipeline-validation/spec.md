# PRD: Photo Processing Pipeline Validation Tool

**Feature ID:** 003-pipeline-validation
**Version:** 1.0.0 (Draft)
**Date:** 2025-12-25
**Author:** Claude (Generated from flowchart analysis)
**Status:** Draft - Awaiting Review

---

## Executive Summary

A new tool to validate photo file collections against defined processing pipeline paths, ensuring image groups contain all expected file types from camera capture through archival. This tool combines the image grouping capabilities of the Photo Pairing Tool with the metadata linking logic of PhotoStats to classify groups as **consistent** (complete pipeline path) or **inconsistent** (missing expected files).

---

## Background & Motivation

### Current State

**Existing Tools:**
1. **PhotoStats** - Identifies valid CR3+XMP metadata pairs based on matching filenames
2. **Photo Pairing Tool** - Groups files by camera ID and counter (e.g., AB3D0001.CR3, AB3D0001.DNG, AB3D0001.TIF)

### Problem Statement

Photographers follow complex processing workflows where a single captured image flows through multiple stages:
- Camera capture → Raw file (CR3)
- Import → Metadata application (XMP sidecar)
- Conversion → Open format (DNG)
- Processing → Developed files (TIF, the only lossless version of final processed image)
- Export → Web formats (Low-resolution JPG for browsing, High-resolution JPG for sharing)
- Archive → Two endpoints: Black Box Archive or Browsable Archive

**Note:** JPG format is inherently lossy by design. The distinction between low-resolution and high-resolution JPG is primarily in pixel count and compression aggressiveness, not lossiness. Both can be rebuilt from the TIF file.

**Current tools cannot:**
1. Validate that a group of files represents a **complete, valid pipeline path**
2. Identify which files are **missing** from an incomplete workflow
3. Classify groups by their **archival readiness** (Black Box vs Browsable)
4. Configure and validate against **user-defined pipeline paths**

### Business Value

- **Quality Assurance:** Ensure archival collections are complete before storage
- **Workflow Validation:** Detect incomplete processing workflows
- **Storage Planning:** Classify which archives are ready for long-term storage
- **Audit Trail:** Document which processing paths were used for each image

---

## Goals & Non-Goals

### Goals

1. **Pipeline Configuration**
   - Define processing pipeline stages and their expected file types in `config.yaml`
   - Support multiple valid pipeline paths (different workflows)
   - Configure archival endpoints (Black Box Archive, Browsable Archive)

2. **Image Group Validation**
   - Classify image groups as **consistent** (complete path) or **inconsistent** (missing files)
   - Identify which specific pipeline path a consistent group follows
   - Report missing file types for inconsistent groups

3. **Metadata Integration**
   - Link raw files to their metadata sidecars (CR3→XMP) using PhotoStats logic
   - Validate metadata presence at appropriate pipeline stages

4. **Reporting**
   - Interactive HTML reports with pipeline visualizations
   - Statistics on consistency rates by pipeline path
   - List of incomplete groups with actionable remediation steps

### Non-Goals (v1.0)

- **File generation:** Tool will NOT create missing files
- **Automatic remediation:** Tool will NOT move or delete files
- **Multi-image workflows:** Advanced features like HDR merging, panorama stitching (may be v2.0)
- **Cloud storage integration:** Local filesystem analysis only
- **Real-time monitoring:** Batch analysis mode only

---

## Functional Requirements

### FR-1: Pipeline Configuration (Node-Based Architecture)

**Description:** Allow users to define processing pipeline workflows using a directed graph of nodes in `config.yaml`

**Architecture Overview:**
The pipeline is defined as a directed graph with different node types that represent the complete workflow from camera capture to archival. **File nodes are critical** as they define the actual files that constitute a valid Specific Image in an ImageGroup.

**Node Types:**

1. **Capture**: Start of pipeline (exactly one per pipeline)
2. **File**: Represents actual files (Image or Metadata) - **CRITICAL FOR VALIDATION**
3. **Process**: Transforms files via processing methods, can chain and loop
4. **Pairing**: Combines multiple files (e.g., CR3+XMP)
5. **Branching**: Conditional path selection (choose ONE output)
6. **Termination**: End of pipeline, accumulates File nodes = Specific Image

**Configuration Schema:**
```yaml
# Processing pipeline configuration
processing_pipelines:
  version: "v1"
  nodes:
    # Capture Node - Start of pipeline
    - id: "capture_1"
      type: "Capture"
      name: "Camera capture"
      output:
        - "raw_image_1"
        - "lowres_jpeg"  # Camera preview

    # File Node - Raw Image (CRITICAL: Defines AB3D0001.CR3 file)
    - id: "raw_image_1"
      type: "File"
      file_type: "Image"
      extension: ".CR3"
      name: "Raw Image File (.CR3)"
      output:
        - "selection_process"

    # Process Node - Selection
    - id: "selection_process"
      type: "Process"
      method_ids:
        - ""  # Empty = no property added to filename
      name: "Image Selection Process"
      output:
        - "raw_image_2"
        - "xmp_metadata_1"

    # File Node - Raw Image after Selection (same physical file as raw_image_1)
    - id: "raw_image_2"
      type: "File"
      file_type: "Image"
      extension: ".CR3"
      name: "Raw Image File (.CR3 after Selection)"
      output:
        - "metadata_pairing"

    # File Node - XMP Metadata (CRITICAL: Defines AB3D0001.XMP file)
    - id: "xmp_metadata_1"
      type: "File"
      file_type: "Metadata"
      extension: ".XMP"
      name: "XMP Metadata File"
      output:
        - "metadata_pairing"

    # Pairing Node - Raw + XMP (validates both files exist)
    - id: "metadata_pairing"
      type: "Pairing"
      name: "Raw + XMP Pairing"
      output:
        - "denoise_branching"

    # Branching Node - Choose ONE of the following processes
    - id: "denoise_branching"
      type: "Branching"
      name: "Denoise Process Choice"
      output:
        - "developing_process"  # Option 1: DNG conversion
        - "targeted_tone_mapping_process"  # Option 2: Skip to tone mapping

    # Process Node - DNG Conversion with denoise
    - id: "developing_process"
      type: "Process"
      method_ids:
        - "DxO_DeepPRIME XD2s"
        - "DxO_DeepPRIME XD3"  # Multiple IDs = branching choice
      name: "Digital Developing Process with DxO"
      output:
        - "openformat_raw_image"

    # File Node - DNG Image (CRITICAL: Defines AB3D0001-DxO_DeepPRIME_XD2s.DNG)
    - id: "openformat_raw_image"
      type: "File"
      file_type: "Image"
      extension: ".DNG"
      name: "DNG Image File"
      output:
        - "targeted_tone_mapping_process"

    # Process Node - Tone Mapping
    - id: "targeted_tone_mapping_process"
      type: "Process"
      method_ids:
        - ""  # No property added
      name: "Targeted Tone Mapping Process with Adobe Lightroom"
      output:
        - "tiff_generation_branching"

    # Branching Node - TIFF Generation options
    - id: "tiff_generation_branching"
      type: "Branching"
      name: "TIFF Generation Process Choice"
      output:
        - "tiff_image"  # Direct export
        - "individual_photoshop_process"  # Photoshop editing
        - "topaz_process"  # Topaz AI processing

    # File Node - TIFF Image (CRITICAL: Defines AB3D0001-DxO_DeepPRIME_XD2s.TIF)
    - id: "tiff_image"
      type: "File"
      file_type: "Image"
      extension: ".TIF"
      name: "TIFF Image File"
      output:
        - "termination_blackbox"  # Can terminate here
        - "lowres_jpeg"  # Or continue to JPG export
        - "highres_jpeg"

    # Process Node - Photoshop Edits (can loop back)
    - id: "individual_photoshop_process"
      type: "Process"
      method_ids:
        - "Edit"
      name: "Individual Photoshop Edits"
      output:
        - "tiff_generation_branching"  # Loop back for more edits

    # Process Node - Topaz AI (can loop back)
    - id: "topaz_process"
      type: "Process"
      method_ids:
        - "topaz"
      name: "Topaz Photo AI Process"
      output:
        - "tiff_generation_branching"  # Loop back

    # File Node - Low-Res JPEG
    - id: "lowres_jpeg"
      type: "File"
      file_type: "Image"
      extension: ".JPG"
      name: "Low-Res JPEG File"
      output:
        - "image_group_pairing"

    # File Node - High-Res JPEG
    - id: "highres_jpeg"
      type: "File"
      file_type: "Image"
      extension: ".JPG"
      name: "High-Res JPEG File"
      output:
        - "image_group_pairing"

    # Pairing Node - Image Group
    - id: "image_group_pairing"
      type: "Pairing"
      name: "Image Group Pairing"
      output:
        - "termination_browsable"

    # Termination Node - Black Box Archive
    # CRITICAL: Accumulates all File nodes from capture_1 to here
    - id: "termination_blackbox"
      type: "Termination"
      name: "Blackbox Termination"
      output: []

    # Termination Node - Browsable Archive
    # CRITICAL: Accumulates all File nodes from capture_1 to here
    - id: "termination_browsable"
      type: "Termination"
      name: "Browsable Termination"
      output: []
```

**How File Nodes Define Valid Specific Images:**

When validating an ImageGroup, the tool:
1. Traverses from Capture to each Termination node
2. **Collects all File nodes encountered on the path**
3. Generates expected filenames based on processing methods
4. Compares expected files vs actual files in ImageGroup

**Example Path to termination_blackbox:**
```
capture_1 →
  raw_image_1 (.CR3) →
  selection_process →
    raw_image_2 (.CR3) →
    xmp_metadata_1 (.XMP) →
  metadata_pairing →
  denoise_branching →
  developing_process (DxO_DeepPRIME_XD2s) →
    openformat_raw_image (.DNG) →
  targeted_tone_mapping_process →
  tiff_generation_branching →
    tiff_image (.TIF) →
  termination_blackbox

File nodes collected:
  - raw_image_1: .CR3
  - raw_image_2: .CR3 (same file, deduplicated)
  - xmp_metadata_1: .XMP
  - openformat_raw_image: .DNG
  - tiff_image: .TIF

Expected Specific Image = {
  AB3D0001.CR3,
  AB3D0001.XMP,
  AB3D0001-DxO_DeepPRIME_XD2s.DNG,
  AB3D0001-DxO_DeepPRIME_XD2s.TIF
}
```

**Validation Rules:**
- Exactly one Capture node per pipeline version
- All node IDs must be unique within version
- All output references must point to valid node IDs
- At least one Termination node required
- File extensions must match `photo_extensions` or `metadata_extensions` config
- Processing method IDs must match `processing_methods` config
- No orphaned nodes (all nodes must be reachable from Capture)
- Pairing nodes must have exactly 2+ input paths
- Branching nodes must have exactly 2+ output paths
- Termination nodes must have empty output array

---

### FR-2: Specific Image Validation (Node-Based Traversal)

**Description:** Validate **Specific Images** (not ImageGroups) by traversing the node-based pipeline and comparing actual files against File nodes collected from Capture to Termination

**Critical Distinction:**
- **ImageGroup** (from Photo Pairing Tool): Container grouping files by `camera_id + counter`
- **Specific Image** (within ImageGroup): The actual unit for pipeline validation
  - Represents a **single captured image** and all its processed derivatives
  - Has unique identifier: `camera_id + counter + suffix`
  - Suffix differentiates separate captures with same camera_id + counter (due to counter looping)

**Why Specific Images, Not ImageGroups?**

When a camera's counter loops (resets to 0001), multiple captures can share the same camera ID and counter:
```
First capture:  AB3D0001.CR3 (counter first time at 0001)
Second capture: AB3D0001.CR3 (counter looped, back to 0001)
```

When exported to the same folder, collision prevention adds a numerical suffix:
```
First capture:  AB3D0001.CR3      (suffix = "" or blank)
Second capture: AB3D0001-2.CR3    (suffix = "2")
Third capture:  AB3D0001-3.CR3    (suffix = "3")
```

**Important:** The suffix indicates **different captured images**, NOT different processing methods (HDR, BW, etc.). Processing properties are part of the filename but represent processing stages within the SAME capture's pipeline.

**ImageGroup Data Structure (from Photo Pairing Tool):**
```python
{
    'group_id': 'AB3D0001',
    'camera_id': 'AB3D',
    'counter': '0001',
    'separate_images': {  # Each entry = one Specific Image (one captured image)
        '': {  # First capture (no suffix, blank key)
            'files': [
                'AB3D0001.CR3',
                'AB3D0001.XMP',
                'AB3D0001.DNG',
                'AB3D0001.TIF'
            ],
            'properties': []  # No processing properties at image group level
        },
        '2': {  # Second capture (counter looped, suffix=2)
            'files': [
                'AB3D0001-2.CR3',
                'AB3D0001-2.XMP',
                'AB3D0001-2.DNG',
                'AB3D0001-2-HDR.TIF'  # HDR is processing property, not a separate image
            ],
            'properties': []
        }
    }
}
```

**Flattening ImageGroups to Specific Images:**

Before pipeline validation, flatten ImageGroups into individual Specific Images:

```python
def flatten_imagegroup_to_specific_images(image_group):
    """
    Convert ImageGroup with multiple separate_images into individual
    Specific Images for validation.

    Args:
        image_group: ImageGroup from Photo Pairing Tool

    Returns:
        List of SpecificImage objects, each validated independently
    """
    specific_images = []

    for suffix, image_data in image_group['separate_images'].items():
        specific_image = {
            'camera_id': image_group['camera_id'],
            'counter': image_group['counter'],
            'suffix': suffix,  # '' (blank) for first capture, '2', '3', etc. for looped
            'unique_id': f"{image_group['camera_id']}{image_group['counter']}" +
                        (f"-{suffix}" if suffix else ""),  # e.g., "AB3D0001" or "AB3D0001-2"
            'files': image_data['files'],  # All files for this specific captured image
            'base_filename': f"{image_group['camera_id']}{image_group['counter']}" +
                           (f"-{suffix}" if suffix else "")  # e.g., "AB3D0001-2"
        }
        specific_images.append(specific_image)

    return specific_images

# Example output:
# [
#   {
#     'camera_id': 'AB3D',
#     'counter': '0001',
#     'suffix': '',
#     'unique_id': 'AB3D0001',
#     'base_filename': 'AB3D0001',
#     'files': ['AB3D0001.CR3', 'AB3D0001.XMP', 'AB3D0001.DNG', 'AB3D0001.TIF']
#   },
#   {
#     'camera_id': 'AB3D',
#     'counter': '0001',
#     'suffix': '2',
#     'unique_id': 'AB3D0001-2',
#     'base_filename': 'AB3D0001-2',
#     'files': ['AB3D0001-2.CR3', 'AB3D0001-2.XMP', 'AB3D0001-2.DNG', 'AB3D0001-2-HDR.TIF']
#   }
# ]
```

**Input:**
- ImageGroups from Photo Pairing Tool (flattened to Specific Images)
- Node-based pipeline configuration from `processing_pipelines`

**Processing Logic:**
```python
def validate_specific_image(specific_image, pipeline_config):
    """
    Traverse pipeline graph from Capture to each Termination,
    collecting File nodes to define expected files for this Specific Image.

    Args:
        specific_image: Single Specific Image (one captured image)
        pipeline_config: Node-based pipeline configuration

    Returns:
        Validation result for this Specific Image
    """
    # 1. Get actual files for this Specific Image only
    actual_files = set(specific_image['files'])

    # 2. Find Capture and Termination nodes
    capture_node = find_node_by_type(pipeline_config, 'Capture')
    termination_nodes = find_nodes_by_type(pipeline_config, 'Termination')

    # 3. For each Termination, traverse and collect File nodes
    matching_terminations = []

    for termination in termination_nodes:
        # Traverse all paths from Capture to this Termination
        paths = enumerate_all_paths(capture_node, termination, pipeline_config)

        for path in paths:
            # Collect File nodes encountered on this path
            file_nodes = [node for node in path if node.type == 'File']

            # Generate expected filenames based on:
            # - Base filename from Specific Image (e.g., "AB3D0001" or "AB3D0001-2")
            # - Processing methods from Process nodes on path (e.g., "HDR", "topaz")
            # - File extensions from File nodes
            expected_files = generate_expected_filenames(
                base=specific_image['base_filename'],  # "AB3D0001-2" if suffix=2
                file_nodes=file_nodes,
                path=path
            )

            # Check if actual files match expected files
            if expected_files == actual_files:
                matching_terminations.append({
                    'termination': termination,
                    'path': path,
                    'file_nodes': file_nodes,
                    'completion': 100
                })
            elif expected_files.issubset(actual_files):
                # Partial match: expected files present but extra files exist
                matching_terminations.append({
                    'termination': termination,
                    'path': path,
                    'file_nodes': file_nodes,
                    'completion': calculate_completion_percentage(expected_files, actual_files),
                    'extra_files': actual_files - expected_files
                })

    # 4. Classify Specific Image based on matching terminations
    if matching_terminations:
        perfect_matches = [m for m in matching_terminations if m['completion'] == 100]
        if perfect_matches:
            return {
                'unique_id': specific_image['unique_id'],
                'status': 'CONSISTENT',
                'matched_terminations': perfect_matches,
                'archival_ready': True
            }
        else:
            return {
                'unique_id': specific_image['unique_id'],
                'status': 'PARTIAL',
                'matched_terminations': matching_terminations,
                'archival_ready': False
            }
    else:
        # No matches: find closest match for helpful error message
        closest = find_closest_termination(actual_files, termination_nodes, pipeline_config)
        return {
            'unique_id': specific_image['unique_id'],
            'status': 'INCONSISTENT',
            'closest_match': closest,
            'missing_files': closest['expected_files'] - actual_files,
            'extra_files': actual_files - closest['expected_files'],
            'archival_ready': False
        }


def validate_all_imagegroups(imagegroups, pipeline_config):
    """
    Main validation function: flatten ImageGroups to Specific Images,
    then validate each independently.

    Args:
        imagegroups: List of ImageGroups from Photo Pairing Tool
        pipeline_config: Pipeline configuration

    Returns:
        Validation results for all Specific Images
    """
    results = []

    for image_group in imagegroups:
        # Flatten ImageGroup to individual Specific Images
        specific_images = flatten_imagegroup_to_specific_images(image_group)

        # Validate each Specific Image independently
        for specific_image in specific_images:
            validation_result = validate_specific_image(specific_image, pipeline_config)
            results.append(validation_result)

    return results
```


def enumerate_all_paths(start_node, end_node, pipeline_config):
    """
    DFS traversal to enumerate all possible paths from start to end.
    Handles branching, looping, and parallel outputs.
    """
    all_paths = []
    visited_in_path = set()

    def dfs(current_node, path=[]):
        # Avoid infinite loops: limit revisits
        if current_node.id in visited_in_path:
            # Allow limited looping (e.g., max 3 times)
            loop_count = sum(1 for n in path if n.id == current_node.id)
            if loop_count >= 3:
                return

        visited_in_path.add(current_node.id)
        new_path = path + [current_node]

        # Terminal condition
        if current_node.id == end_node.id:
            all_paths.append(new_path)
            visited_in_path.remove(current_node.id)
            return

        # Traverse outputs
        if current_node.type == 'Branching':
            # Branching: explore ALL branches (validation checks all possibilities)
            for output_id in current_node.output:
                next_node = pipeline_config.get_node(output_id)
                dfs(next_node, new_path)
        else:
            # Normal node: follow all outputs (parallel execution)
            for output_id in current_node.output:
                next_node = pipeline_config.get_node(output_id)
                dfs(next_node, new_path)

        visited_in_path.remove(current_node.id)

    dfs(start_node)
    return all_paths


def generate_expected_filenames(base, file_nodes, path):
    """
    Generate expected filenames for File nodes based on processing methods.

    Args:
        base: Base filename (camera_id + counter), e.g., "AB3D0001"
        file_nodes: List of File nodes from path
        path: Complete path including Process nodes

    Returns:
        Set of expected filenames
    """
    expected = set()

    # Track accumulated processing methods from Process nodes
    accumulated_methods = []

    for node in path:
        if node.type == 'Process':
            # Process nodes add their method_id to the filename
            for method_id in node.method_ids:
                if method_id != "":  # Empty string = no property added
                    accumulated_methods.append(method_id)

        elif node.type == 'File':
            # Construct filename from base + accumulated methods + extension
            if accumulated_methods:
                method_str = '-'.join(accumulated_methods)
                filename = f"{base}-{method_str}{node.extension}"
            else:
                filename = f"{base}{node.extension}"

            expected.add(filename)

    return expected
```

**Output Structure (Per Specific Image):**
```python
{
    'unique_id': 'AB3D0001-2',  # camera_id + counter + suffix
    'camera_id': 'AB3D',
    'counter': '0001',
    'suffix': '2',  # '' (blank) for first capture, '2', '3', etc. for looped counter
    'base_filename': 'AB3D0001-2',  # Used for filename generation
    'status': 'CONSISTENT' | 'PARTIAL' | 'INCONSISTENT',
    'matched_terminations': [
        {
            'termination_id': 'termination_blackbox',
            'termination_name': 'Blackbox Termination',
            'archival_type': 'black_box',
            'path_traversed': [...],  # List of node IDs from Capture to Termination
            'file_nodes_collected': [...],  # File nodes encountered on path
            'completion': 100  # percentage
        }
    ],
    'files': [
        {
            'filename': 'AB3D0001-2.CR3',
            'file_node_id': 'raw_image_1',
            'metadata_sidecar': 'AB3D0001-2.XMP',
            'metadata_status': 'LINKED'
        },
        {
            'filename': 'AB3D0001-2.DNG',
            'file_node_id': 'openformat_raw_image',
            'metadata_sidecar': 'AB3D0001-2.XMP',
            'metadata_status': 'SHARED'
        },
        {
            'filename': 'AB3D0001-2-HDR.TIF',  # HDR is processing property
            'file_node_id': 'tiff_image',
            'metadata_sidecar': None,
            'metadata_status': 'EMBEDDED'
        }
    ],
    'missing_files': [
        {
            'expected_filename': 'AB3D0001-2-hires.JPG',
            'file_node_id': 'highres_jpeg',
            'reason': 'Required for complete browsable_termination path'
        }
    ],
    'archival_ready': true | false
}
```

**Aggregated Output (All Specific Images):**
```python
{
    'total_specific_images': 125,
    'summary': {
        'consistent': 85,  # 68%
        'partial': 28,     # 22%
        'inconsistent': 12 # 10%
    },
    'archival_ready_by_type': {
        'black_box': 65,
        'browsable': 20,
        'not_ready': 40
    },
    'specific_images': [
        # List of validation results (structure above) for each Specific Image
        {...},  # AB3D0001 (suffix='')
        {...},  # AB3D0001-2 (suffix='2')
        {...},  # AB3D0002 (suffix='')
        # etc.
    ]
}
```

**Example: Multiple Specific Images from Same ImageGroup:**

```python
# Input ImageGroup with 2 Specific Images (counter looped):
ImageGroup AB3D0001 → 2 Specific Images

# Output: 2 independent validation results
[
    {
        'unique_id': 'AB3D0001',  # First capture
        'suffix': '',
        'status': 'CONSISTENT',
        'archival_ready': True
    },
    {
        'unique_id': 'AB3D0001-2',  # Second capture (counter looped)
        'suffix': '2',
        'status': 'PARTIAL',
        'archival_ready': False
    }
]
```

---

### FR-3: Metadata Sidecar Validation

**Description:** Validate metadata files are present at required pipeline stages

**Requirements:**
1. **CR3→XMP Linking:** Use PhotoStats' base filename matching
   - `AB3D0001.cr3` must have `AB3D0001.xmp`

2. **DNG Metadata:**
   - Can share XMP with CR3 (`AB3D0001.xmp` used by both)
   - Or have separate XMP (`AB3D0001-DNG.xmp`)
   - Or embed metadata (no XMP required if `metadata_required: false`)

3. **TIF Metadata:**
   - Typically embeds metadata (XMP optional)
   - If `metadata_required: false`, XMP absence is valid

4. **Stage-Specific Validation:**
   - `import` stage: XMP **must** exist for CR3 files
   - `capture` stage: XMP **may** exist but not required

**Validation Logic:**
```python
def validate_metadata_at_stage(file, stage_config):
    if stage_config.metadata_sidecar is None:
        return {'status': 'NOT_REQUIRED', 'sidecar': None}

    # Look for metadata sidecar
    sidecar_path = find_metadata_sidecar(file, stage_config.metadata_sidecar)

    if sidecar_path:
        return {'status': 'LINKED', 'sidecar': sidecar_path}
    elif stage_config.metadata_required:
        return {'status': 'MISSING_REQUIRED', 'sidecar': None}
    else:
        return {'status': 'MISSING_OPTIONAL', 'sidecar': None}
```

---

### FR-4: Consistency Classification

**Description:** Classify image groups into consistency tiers

**Classification Tiers:**

| Status | Description | Criteria | Archival Ready |
|--------|-------------|----------|----------------|
| **CONSISTENT** | Complete valid pipeline path | Matches at least one `terminal: true` path with 100% file completion | **YES** |
| **PARTIAL** | Matches non-terminal path | Matches path but not marked as terminal archival endpoint | **NO** |
| **INCONSISTENT** | Missing files from all paths | Does not match any complete path | **NO** |
| **INVALID** | Has validation errors | Metadata required but missing, or other validation failures | **NO** |

**Edge Cases:**
- **Multiple Path Match:** Group matches multiple valid paths → report all matching paths
- **Superset Path:** Group has MORE files than required by path → still CONSISTENT if minimum requirements met
- **Processing Properties:** Files with properties (e.g., `AB3D0001-HDR.tif`) → match `individual_processing` stage

---

### FR-5: HTML Report Generation

**Description:** Generate interactive HTML report using Jinja2 templates (consistent with existing tools)

**Report Sections:**

1. **Executive Summary**
   - Total image groups analyzed
   - Consistency breakdown (pie chart)
   - Archival readiness statistics

2. **Pipeline Path Statistics**
   - For each configured path:
     - Number of groups matching this path
     - Completion rate
     - Archival type distribution

3. **Consistent Groups**
   - Table of groups ready for archival
   - Matched pipeline path(s)
   - File inventory

4. **Inconsistent Groups**
   - Table of incomplete groups
   - Missing files highlighted
   - Recommended actions

5. **Metadata Validation**
   - Groups with metadata issues
   - Missing required XMP files
   - Orphaned metadata

6. **Pipeline Visualization**
   - Flowchart showing configured pipeline
   - Highlight which paths are most common
   - Show dropout points (where groups become inconsistent)

**Visualizations (Chart.js):**
- Pie chart: Consistency status distribution
- Bar chart: Groups per pipeline path
- Stacked bar chart: Stage completion rates
- Sankey diagram: Flow through pipeline stages (v2.0)

---

## Technical Design

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Pipeline Validation Tool                    │
│                   (pipeline_validation.py)                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Photo Pairing│    │  PhotoStats  │    │   Config     │
│  (Grouping)  │    │  (Metadata)  │    │  (Pipeline)  │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │   Validator  │
                    │    Engine    │
                    └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │HTML Reporter │
                    │  (Jinja2)    │
                    └──────────────┘
```

### Module Structure

**New Files:**
```
photo-admin/
├── pipeline_validation.py          # Main CLI tool
├── utils/
│   ├── pipeline_config.py         # Pipeline config parser
│   └── pipeline_validator.py      # Validation engine
├── templates/
│   └── pipeline_report.html.j2    # Jinja2 template
├── config/
│   └── pipeline-template.yaml     # Default pipeline config
└── tests/
    └── test_pipeline_validation.py
```

**Class Hierarchy:**

```python
# utils/pipeline_config.py
class PipelineStage:
    id: str
    name: str
    file_types: List[FileTypeRequirement]

class FileTypeRequirement:
    extension: str
    required: bool
    metadata_sidecar: Optional[str]
    metadata_required: bool
    properties: Optional[List[str]]

class PipelinePath:
    id: str
    name: str
    description: str
    archival_type: Optional[str]  # 'black_box' | 'browsable' | null
    stages: List[str]  # stage IDs
    validation: PathValidation

class PathValidation:
    must_have_all: bool
    terminal: bool

class PipelineConfig:
    stages: List[PipelineStage]
    paths: List[PipelinePath]

    @classmethod
    def load_from_yaml(cls, config_path: Path)

    def validate(self) -> Tuple[bool, Optional[str]]
```

```python
# utils/pipeline_validator.py
class ImageGroupValidator:
    def __init__(self, pipeline_config: PipelineConfig)

    def validate_group(self, image_group: dict) -> GroupValidationResult

    def match_pipeline_paths(self, image_group: dict) -> List[PipelinePath]

    def calculate_missing_files(self, image_group: dict, target_path: PipelinePath) -> List[dict]

    def validate_metadata_links(self, image_group: dict) -> List[MetadataLink]

class GroupValidationResult:
    status: str  # 'CONSISTENT' | 'PARTIAL' | 'INCONSISTENT' | 'INVALID'
    matched_paths: List[PipelinePath]
    missing_files: List[dict]
    metadata_status: List[MetadataLink]
    archival_ready: bool
```

### Integration with Existing Tools

**Reuse from Photo Pairing Tool:**
- `scan_folder()` - File discovery
- `build_imagegroups()` - Group files by camera_id + counter
- FilenameParser validation

**Reuse from PhotoStats:**
- `_analyze_pairing()` - Metadata sidecar detection
- Base filename matching logic

**Reuse from PhotoAdminConfig:**
- YAML configuration loading
- `photo_extensions` and `metadata_extensions`

**New Configuration Section:**
- Add `processing_pipelines` to existing `config.yaml`
- Maintain backward compatibility with existing tools

---

## User Experience

### CLI Usage

```bash
# Basic usage - analyze current directory
python3 pipeline_validation.py /path/to/photos

# Specify custom config
python3 pipeline_validation.py /path/to/photos --config /path/to/config.yaml

# Filter by archival type
python3 pipeline_validation.py /path/to/photos --archival-type black_box

# Show only inconsistent groups
python3 pipeline_validation.py /path/to/photos --show-inconsistent

# Output JSON instead of HTML
python3 pipeline_validation.py /path/to/photos --output-format json
```

### Help Text

```
Photo Pipeline Validation Tool - Validate photo collections against processing workflows

USAGE:
    python3 pipeline_validation.py <folder> [options]

ARGUMENTS:
    <folder>    Path to folder containing photo files

OPTIONS:
    --config PATH               Custom config file path
    --archival-type TYPE        Filter by archival type (black_box, browsable)
    --show-inconsistent         Show only inconsistent groups
    --output-format FORMAT      Output format: html (default), json
    --help, -h                  Show this help message

EXAMPLE WORKFLOW:
    1. Configure pipeline paths in config/config.yaml
    2. Run tool on photo collection:
       $ python3 pipeline_validation.py ~/Photos/2024
    3. Review HTML report for:
       - Groups ready for Black Box Archive
       - Groups ready for Browsable Archive
       - Incomplete groups needing additional processing
    4. Take action based on report recommendations

CONFIGURATION:
    The tool uses config/config.yaml to define:
    - Processing pipeline stages (capture, import, develop, export)
    - Valid pipeline paths (raw archive, DNG archive, browsable archive)
    - Archival readiness criteria

    See config/pipeline-template.yaml for examples.

For more information, see docs/pipeline-validation.md
```

### Interactive Configuration

When pipeline config is missing or incomplete:

```
⚠ Warning: No pipeline configuration found in config.yaml

Would you like to:
  1. Generate default pipeline configuration
  2. Specify custom pipeline config file
  3. Skip pipeline validation (analyze groups only)

Enter choice (1-3): 1

✓ Generated default pipeline configuration in config/config.yaml

Default pipeline includes:
  - Raw Archive Path (CR3 + XMP → Black Box)
  - DNG Archive Path (CR3 → DNG + XMP → Black Box)
  - Browsable Archive Path (Full workflow → JPG → Browsable)

You can customize these paths by editing config/config.yaml
Continue with analysis? (y/n): y
```

### Report Preview

```
================================================================================
                    Pipeline Validation Report
================================================================================
Scanned: /home/user/Photos/2024
Analysis Date: 2025-12-25 14:30:00
Total Image Groups: 1,247

Summary:
  ✓ Consistent (Archival Ready):     892 groups (71.5%)
  ⚠ Partial Processing:               203 groups (16.3%)
  ✗ Inconsistent (Missing Files):     152 groups (12.2%)

Archival Readiness:
  Black Box Archive Ready:  654 groups (52.4%)
  Browsable Archive Ready:  238 groups (19.1%)
  Not Ready:                355 groups (28.5%)

Pipeline Path Distribution:
  Raw Archive Path:         420 groups (33.7%)
  DNG Archive Path:         234 groups (18.8%)
  Browsable Archive:        238 groups (19.1%)
  Partial/Inconsistent:     355 groups (28.5%)

Metadata Status:
  ✓ All metadata linked:    1,095 groups (87.8%)
  ⚠ Missing optional XMP:      98 groups (7.9%)
  ✗ Missing required XMP:      54 groups (4.3%)

📄 Full report saved to: pipeline_validation_report_2025-12-25_14-30-00.html
================================================================================
```

---

## Testing Strategy

### Unit Tests

1. **Pipeline Configuration**
   - Load valid pipeline config from YAML
   - Detect invalid stage references
   - Validate circular dependencies
   - Test default config generation

2. **Stage Matching**
   - Match file to correct stage
   - Handle file with properties (HDR, BW)
   - Detect unknown file types

3. **Path Validation**
   - Group matches complete path
   - Group matches partial path
   - Group matches no paths
   - Group matches multiple paths

4. **Metadata Validation**
   - CR3 with XMP (linked)
   - CR3 without XMP (orphaned)
   - DNG sharing CR3's XMP
   - TIF without XMP (embedded metadata)

### Integration Tests

1. **Complete Workflows**
   - Raw archive path (CR3 + XMP only)
   - DNG archive path (CR3 + DNG + XMP)
   - Browsable archive path (full workflow)

2. **Incomplete Workflows**
   - Missing XMP at import stage
   - Missing DNG in conversion path
   - Missing JPG in browsable path

3. **Edge Cases**
   - Group with extra files (superset)
   - Group with mixed archival paths
   - Group with separate images (AB3D0001-2.cr3)

### Test Coverage Targets

- Pipeline configuration: >90%
- Validation engine: >85%
- Overall: >70%

---

## Success Metrics

### Launch Metrics (v1.0)

- **Adoption:** 50% of PhotoStats users try pipeline validation within 1 month
- **Usefulness:** Users run pipeline validation at least monthly
- **Configuration:** 80% of users customize at least one pipeline path

### Quality Metrics

- **Accuracy:** 95% accurate classification of consistent vs inconsistent groups
- **Performance:** Analyze 10,000 image groups in under 60 seconds
- **Usability:** Users can configure pipeline without reading full documentation

### User Feedback

- Collect feedback via GitHub issues
- Track most common pipeline configurations
- Identify missing pipeline stages or paths

---

## Open Questions

1. **Multi-Image Workflows:**
   - How to handle HDR merges (3 CR3 files → 1 TIF)?
   - Should pipeline validation support group-to-group relationships?
   - **Recommendation:** Defer to v2.0, focus on 1:1 file evolution in v1.0

2. **Separate Images:**
   - Files like `AB3D0001-2.cr3` represent separate captures with same counter
   - Should each separate image follow its own pipeline path?
   - **Recommendation:** YES - treat as separate image groups (AB3D0001-2, AB3D0001-3, etc.)

3. **Property Inheritance:**
   - If `AB3D0001.cr3` exists, can `AB3D0001-HDR.dng` reference it?
   - Should properties be inherited through pipeline stages?
   - **Recommendation:** Properties apply to specific processing stages, not inherited

4. **Partial Path Archival:**
   - Should "partial" groups (non-terminal paths) ever be archival-ready?
   - What if user wants to archive at intermediate stage?
   - **Recommendation:** Allow configuration flag `allow_intermediate_archival: true` per path

5. **XMP Sharing:**
   - Can CR3 and DNG share the same XMP file?
   - How to handle conflicting metadata?
   - **Recommendation:** YES - share by default unless separate XMP exists (e.g., `AB3D0001-DNG.xmp`)

---

## Dependencies

### Required

- Python 3.10+
- PyYAML >= 6.0 (existing)
- Jinja2 >= 3.1.0 (existing)
- pytest (testing)

### Optional

- Graphviz (for pipeline visualization - future)
- jsonschema (for YAML validation - future)

---

## Timeline (Estimated)

**Phase 1: Foundation (Week 1-2)**
- Design pipeline config schema
- Implement PipelineConfig class
- Write configuration validator
- Create default pipeline templates

**Phase 2: Validation Engine (Week 3-4)**
- Implement ImageGroupValidator
- Add stage matching logic
- Integrate metadata validation from PhotoStats
- Write unit tests (>85% coverage)

**Phase 3: CLI & Reporting (Week 5-6)**
- Build main CLI tool (pipeline_validation.py)
- Create Jinja2 HTML template
- Add Chart.js visualizations
- Implement JSON output format

**Phase 4: Testing & Documentation (Week 7-8)**
- Write integration tests
- Create user documentation (docs/pipeline-validation.md)
- Update CLAUDE.md with new tool
- Beta testing with sample photo collections

**Phase 5: Polish & Release (Week 9)**
- Address beta feedback
- Performance optimization
- Final QA
- Release v1.0.0

---

## Future Enhancements (v2.0+)

1. **Advanced Workflows:**
   - HDR merging (N:1 relationships)
   - Panorama stitching (N:1 relationships)
   - Focus stacking (N:1 relationships)

2. **Automated Remediation:**
   - Generate scripts to create missing files
   - Batch processing suggestions
   - Integration with Lightroom/Photoshop automation

3. **Cloud Storage:**
   - Validate files across multiple storage locations
   - Check cloud backup completeness
   - S3/Google Drive integration

4. **Real-Time Monitoring:**
   - Watch folders for new files
   - Alert when group becomes consistent
   - Webhook notifications

5. **Pipeline Templates:**
   - Share pipeline configurations
   - Import common workflows
   - Industry-standard pipeline presets

6. **Graphical Pipeline Editor:**
   - Visual pipeline configuration
   - Drag-and-drop stage builder
   - Interactive path testing

---

## Configuration Example

Here's a complete example of the pipeline configuration in `config.yaml`:

```yaml
# Existing configuration sections (unchanged)
photo_extensions:
  - .cr3
  - .dng
  - .tif
  - .tiff
  - .jpg
  - .jpeg

metadata_extensions:
  - .xmp

require_sidecar:
  - .cr3

camera_mappings:
  AB3D:
    - name: "Canon EOS R5"
      serial_number: "12345"

processing_methods:
  HDR: "High Dynamic Range processing"
  BW: "Black and White conversion"
  lowres: "Low-resolution JPG export for web browsing"
  hires: "High-resolution JPG export for sharing"

# NEW: Processing pipeline configuration
processing_pipelines:
  stages:
    - id: capture
      name: "Camera Capture"
      file_types:
        - extension: .cr3
          required: true
          metadata_sidecar: .xmp
          metadata_required: false

    - id: import
      name: "Import & Sanction"
      file_types:
        - extension: .cr3
          required: true
          metadata_sidecar: .xmp
          metadata_required: true

    - id: dng_conversion
      name: "DNG Conversion"
      file_types:
        - extension: .dng
          required: true
          metadata_sidecar: .xmp
          metadata_required: true

    - id: tone_mapping
      name: "Tone Mapping"
      file_types:
        - extension: .tif
          required: true
          metadata_sidecar: .xmp
          metadata_required: false

    - id: individual_processing
      name: "Individual Processing"
      file_types:
        - extension: .tif
          required: true
          properties:
            - HDR
            - BW

    - id: web_export_hires
      name: "High-Resolution JPG Export"
      file_types:
        - extension: .jpg
          required: true
          properties:
            - hires

  paths:
    - id: raw_archive
      name: "Raw Archive - Black Box"
      description: "Original CR3 + XMP, ready for long-term storage"
      archival_type: black_box
      stages:
        - capture
        - import
      validation:
        must_have_all: true
        terminal: true

    - id: dng_archive
      name: "DNG Archive - Black Box"
      description: "Converted to open DNG format for preservation"
      archival_type: black_box
      stages:
        - capture
        - import
        - dng_conversion
      validation:
        must_have_all: true
        terminal: true

    - id: browsable_archive
      name: "Browsable Archive - Web Ready"
      description: "Complete workflow with high-resolution JPG exports"
      archival_type: browsable
      stages:
        - capture
        - import
        - dng_conversion
        - tone_mapping
        - individual_processing
        - web_export_hires
      validation:
        must_have_all: true
        terminal: true
```

---

## Appendix A: Flowchart Analysis

Based on the provided flowchart, here are the identified pipeline paths:

### Path 1: Raw Archive (Black Box)
```
Camera Capture → Raw File (CR3) → Import → Sanction → CR3 + XMP → Black Box Archive
```

**Files Expected:**
- `AB3D0001.cr3`
- `AB3D0001.xmp`

### Path 2: DNG Archive (Black Box)
```
Camera Capture → Raw File (CR3) → Import → Digital Photo Developing → DNG + XMP → Black Box Archive
```

**Files Expected:**
- `AB3D0001.cr3` (may be discarded after conversion)
- `AB3D0001.dng`
- `AB3D0001.xmp`

### Path 3: Developed Archive (Black Box)
```
... → DNG → Export from Lightroom → Targeted Tone Mapping → TIF → Black Box Archive
```

**Files Expected:**
- `AB3D0001.cr3`
- `AB3D0001.dng`
- `AB3D0001.xmp`
- `AB3D0001.tif`

### Path 4: Browsable Archive
```
... → TIF → Individual Processing → TIF (processed) → Low-res JPG → High-res JPG → Browsable Archive
```

**Files Expected:**
- `AB3D0001.cr3`
- `AB3D0001.dng`
- `AB3D0001.xmp`
- `AB3D0001.tif` (or `AB3D0001-HDR.tif`, the only lossless final processed image)
- `AB3D0001-lowres.jpg` (for web browsing)
- `AB3D0001-hires.jpg` (for sharing)

### Inconsistent Examples

**Missing XMP at Import:**
```
Files: AB3D0001.cr3
Status: INCONSISTENT
Missing: AB3D0001.xmp (required at import stage)
```

**Missing DNG for Archive:**
```
Files: AB3D0001.cr3, AB3D0001.xmp
Status: PARTIAL (matches raw_archive but not dng_archive)
```

**Missing JPG for Browsable:**
```
Files: AB3D0001.cr3, AB3D0001.dng, AB3D0001.xmp, AB3D0001.tif
Status: PARTIAL (matches developed_archive but not browsable_archive)
```

---

## Appendix B: Sample Validation Output

```json
{
  "scan_timestamp": "2025-12-25T14:30:00Z",
  "folder_path": "/home/user/Photos/2024",
  "total_groups": 1247,
  "summary": {
    "consistent": 892,
    "partial": 203,
    "inconsistent": 152
  },
  "archival_ready": {
    "black_box": 654,
    "browsable": 238,
    "not_ready": 355
  },
  "groups": [
    {
      "group_id": "AB3D0001",
      "camera_id": "AB3D",
      "counter": "0001",
      "status": "CONSISTENT",
      "archival_ready": true,
      "matched_paths": [
        {
          "path_id": "dng_archive",
          "path_name": "DNG Archive - Black Box",
          "archival_type": "black_box",
          "completion": 100
        }
      ],
      "files": [
        {
          "filename": "AB3D0001.cr3",
          "stage": "capture",
          "metadata_sidecar": "AB3D0001.xmp",
          "metadata_status": "LINKED"
        },
        {
          "filename": "AB3D0001.dng",
          "stage": "dng_conversion",
          "metadata_sidecar": "AB3D0001.xmp",
          "metadata_status": "SHARED"
        },
        {
          "filename": "AB3D0001.xmp",
          "stage": "import",
          "metadata_status": "PRIMARY"
        }
      ],
      "missing_files": []
    },
    {
      "group_id": "AB3D0042",
      "camera_id": "AB3D",
      "counter": "0042",
      "status": "INCONSISTENT",
      "archival_ready": false,
      "matched_paths": [],
      "files": [
        {
          "filename": "AB3D0042.cr3",
          "stage": "capture",
          "metadata_sidecar": null,
          "metadata_status": "MISSING_REQUIRED"
        }
      ],
      "missing_files": [
        {
          "stage": "import",
          "expected_extension": ".xmp",
          "reason": "Required for all archival paths"
        }
      ]
    }
  ]
}
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-25 | Claude | Initial draft based on flowchart analysis |

---

## Approval

- [ ] Product Owner
- [ ] Technical Lead
- [ ] User Representative

**Feedback & Questions:**
Please submit feedback via GitHub issue or email.
