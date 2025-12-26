# Flowchart to Node-Based Configuration Mapping

This document explains how the Photo Processing Pipeline flowchart translates into the node-based pipeline configuration system used in `pipeline-config-example.yaml`.

**Key Concept:** The pipeline is modeled as a **directed graph** where nodes represent different stages and decisions, and File nodes accumulate to define the expected files for a complete Specific Image.

---

## Flowchart Overview

The flowchart shows a photographer's workflow from camera capture through archival, with two archival endpoints:

- **Black Box Archive** - Long-term preservation storage (infrequent access, master files)
- **Browsable Archive** - Web-accessible storage (frequent browsing, includes web-optimized JPG files)

**Important Terminology:**
- **TIF** is the only lossless version of the final processed image
- **lowres JPG**: Lower resolution for web browsing (inherently lossy, smaller file)
- **hires JPG**: Higher resolution for sharing (inherently lossy, larger file)
- Both JPG versions can be rebuilt from the TIF file

---

## Node-Based Architecture

The pipeline uses **6 node types** to model complex workflows:

### 1. Capture Node
- **Purpose:** Starting point of the pipeline
- **Flowchart Equivalent:** "Camera captures" → "Raw File (CR3)"
- **Example:** `camera_capture_1`

### 2. File Node
- **Purpose:** Represents an actual file in the Specific Image
- **Critical:** File nodes encountered from Capture to Termination define the expected files
- **Flowchart Equivalent:** Any file type box (CR3, XMP, DNG, TIF, JPG)
- **Examples:** `raw_image_1` (.CR3), `xmp_metadata_1` (.XMP), `dng_image_1` (.DNG)

### 3. Pairing Node
- **Purpose:** Enforces that two files exist together (e.g., CR3+XMP)
- **Flowchart Equivalent:** Implicit relationship between "Raw File" and "Metadata File"
- **Example:** `cr3_xmp_pairing`

### 4. Process Node
- **Purpose:** Represents a transformation/processing step
- **Flowchart Equivalent:** Processing boxes (Import, Develop, Tone Mapping, Individual Processing)
- **Example:** `selection_process` (Import/Sanction), `individual_processing` (Photoshop editing)

### 5. Branching Node
- **Purpose:** Conditional path selection
- **Flowchart Equivalent:** Decision diamonds or path splits
- **Example:** `processing_choice` (decide whether to apply HDR, BW, etc.)

### 6. Termination Node
- **Purpose:** Valid endpoint, accumulates File nodes to define expected Specific Image
- **Archival Types:** `black_box` or `browsable`
- **Flowchart Equivalent:** Archive endpoints
- **Examples:** `raw_archive`, `dng_archive`, `browsable_archive`

---

## Critical Concept: File Node Accumulation

**How Validation Works:**

1. **Enumerate all paths** from Capture node to each Termination node
2. **Collect File nodes** encountered along each path
3. **Generate expected filenames** using base filename (e.g., `AB3D0001` or `AB3D0001-2`)
4. **Compare with actual files** in the Specific Image

**Example Path:**
```
Capture → File(CR3) → Process(Import) → File(XMP) → Pairing → Termination(raw_archive)
```

**File Nodes Encountered:** `raw_image_1` (.CR3), `xmp_metadata_1` (.XMP)

**Expected Files for `AB3D0001`:**
- `AB3D0001.CR3`
- `AB3D0001.XMP`

**Expected Files for `AB3D0001-2` (counter looped):**
- `AB3D0001-2.CR3`
- `AB3D0001-2.XMP`

---

## Validation Unit: Specific Images

**Critical Distinction:**

- **ImageGroup** (from Photo Pairing Tool): Container grouping files by camera_id + counter
- **Specific Image**: **THE UNIT FOR VALIDATION** - represents ONE captured image

**ImageGroup Structure:**
```python
{
    'group_id': 'AB3D0001',
    'camera_id': 'AB3D',
    'counter': '0001',
    'separate_images': {
        '': {  # First capture (Specific Image 1)
            'files': ['AB3D0001.CR3', 'AB3D0001.XMP', 'AB3D0001.DNG']
        },
        '2': {  # Second capture (Specific Image 2, counter looped)
            'files': ['AB3D0001-2.CR3', 'AB3D0001-2.XMP']
        }
    }
}
```

**Validation Process:**
1. Flatten ImageGroup into individual Specific Images
2. Validate EACH Specific Image independently against all pipeline paths
3. Each Specific Image gets its own CONSISTENT/PARTIAL/INCONSISTENT classification

---

## Path Mapping: Flowchart → Node Sequences

### Path 1: Raw Archive (Black Box)

**Flowchart Path:**
```
Camera → Raw File (CR3) → Import → Sanction → [Black Box Archive]
```

**Node Sequence:**
```
camera_capture_1 (Capture)
  → raw_image_1 (File: .CR3)
  → selection_process (Process: Import/Sanction)
  → xmp_metadata_1 (File: .XMP)
  → cr3_xmp_pairing (Pairing)
  → raw_archive (Termination: black_box)
```

**File Nodes Accumulated:**
- `raw_image_1` → `.CR3`
- `xmp_metadata_1` → `.XMP`

**Expected Files for Specific Image `AB3D0001`:**
- `AB3D0001.CR3`
- `AB3D0001.XMP`

**Validation:**
- Status: **CONSISTENT** if both files exist
- Archival ready: **YES** (black_box)

**Configuration Reference:**
```yaml
nodes:
  - id: "camera_capture_1"
    type: "Capture"
    output: ["raw_image_1"]

  - id: "raw_image_1"
    type: "File"
    extension: ".CR3"
    output: ["selection_process"]

  - id: "selection_process"
    type: "Process"
    method_ids: [""]
    output: ["raw_image_2", "xmp_metadata_1"]

  - id: "xmp_metadata_1"
    type: "File"
    extension: ".XMP"
    output: ["cr3_xmp_pairing"]

  - id: "cr3_xmp_pairing"
    type: "Pairing"
    required_files: ["raw_image_2", "xmp_metadata_1"]
    output: ["dng_conversion", "raw_archive"]

  - id: "raw_archive"
    type: "Termination"
    archival_type: "black_box"
```

---

### Path 2: DNG Archive (Black Box)

**Flowchart Path:**
```
... → Raw Archive → Digital Photo Developing → DNG File → [Black Box Archive]
```

**Node Sequence:**
```
camera_capture_1 (Capture)
  → raw_image_1 (File: .CR3)
  → selection_process (Process)
  → xmp_metadata_1 (File: .XMP)
  → cr3_xmp_pairing (Pairing)
  → dng_conversion (Process: DNG Conversion)
  → dng_image_1 (File: .DNG)
  → dng_archive (Termination: black_box)
```

**File Nodes Accumulated:**
- `raw_image_1` → `.CR3`
- `xmp_metadata_1` → `.XMP`
- `dng_image_1` → `.DNG`

**Expected Files for Specific Image `AB3D0001`:**
- `AB3D0001.CR3`
- `AB3D0001.XMP`
- `AB3D0001.DNG`

**Note:** CR3 may be deleted after DNG conversion to save space (photographer's choice). The validation should support this as an optional file in future iterations.

**Validation:**
- Status: **CONSISTENT** if all files exist
- Archival ready: **YES** (black_box)

---

### Path 3: Developed Archive (Black Box)

**Flowchart Path:**
```
... → DNG → Export from Lightroom → Tone Mapping → TIF → [Black Box Archive]
```

**Node Sequence:**
```
... (all previous nodes from DNG path)
  → dng_image_1 (File: .DNG)
  → tone_mapping_export (Process: Tone Mapping)
  → tiff_image_1 (File: .TIF)
  → developed_archive (Termination: black_box)
```

**File Nodes Accumulated:**
- `raw_image_1` → `.CR3`
- `xmp_metadata_1` → `.XMP`
- `dng_image_1` → `.DNG`
- `tiff_image_1` → `.TIF`

**Expected Files for Specific Image `AB3D0001`:**
- `AB3D0001.CR3`
- `AB3D0001.XMP`
- `AB3D0001.DNG`
- `AB3D0001.TIF`

**Validation:**
- Status: **CONSISTENT** if all files exist
- Archival ready: **YES** (black_box, master preservation)

---

### Path 4: Browsable Archive with Individual Processing

**Flowchart Path:**
```
... → TIF → Individual Processing (HDR/BW) → TIF (processed) → lowres JPG → hires JPG → [Browsable Archive]
```

**Node Sequence (HDR processing example):**
```
... (all previous nodes from Developed path)
  → tiff_image_1 (File: .TIF, base tone mapping)
  → processing_choice (Branching: Apply HDR?)
  → individual_processing (Process: method_id="HDR")
  → tiff_image_2 (File: .TIF, with HDR property)
  → lowres_jpeg_export (Process)
  → lowres_jpeg (File: .JPG, lowres property)
  → highres_jpeg_export (Process)
  → highres_jpeg (File: .JPG, hires property)
  → browsable_archive (Termination: browsable)
```

**File Nodes Accumulated:**
- `raw_image_1` → `.CR3`
- `xmp_metadata_1` → `.XMP`
- `dng_image_1` → `.DNG`
- `tiff_image_1` → `.TIF` (base)
- `tiff_image_2` → `.TIF` (with HDR property)
- `lowres_jpeg` → `.JPG` (lowres property)
- `highres_jpeg` → `.JPG` (hires property)

**Expected Files for Specific Image `AB3D0001` with HDR processing:**
- `AB3D0001.CR3`
- `AB3D0001.XMP`
- `AB3D0001.DNG`
- `AB3D0001.TIF` (base tone mapping)
- `AB3D0001-HDR.TIF` (individual processing)
- `AB3D0001-HDR-lowres.JPG` (web browsing)
- `AB3D0001-HDR-hires.JPG` (sharing/download)

**Validation:**
- Status: **CONSISTENT** if all files exist
- Archival ready: **YES** (browsable, web-ready)

**Configuration Reference:**
```yaml
nodes:
  - id: "processing_choice"
    type: "Branching"
    description: "Photographer decides which processing to apply"
    output: ["individual_processing", "no_processing_needed"]

  - id: "individual_processing"
    type: "Process"
    method_ids: ["HDR", "BW", "topaz", "focus_stacking"]
    output: ["tiff_image_2"]

  - id: "tiff_image_2"
    type: "File"
    extension: ".TIF"
    output: ["lowres_jpeg_export"]

  - id: "lowres_jpeg"
    type: "File"
    extension: ".JPG"
    property: "lowres"
    output: ["highres_jpeg_export"]

  - id: "highres_jpeg"
    type: "File"
    extension: ".JPG"
    property: "hires"
    output: ["browsable_archive"]
```

---

## Processing Properties and Filename Generation

### Property Accumulation Rules

**Processing Properties** (HDR, BW, topaz, etc.) are added by Process nodes with `method_ids`:

```yaml
- id: "individual_processing"
  type: "Process"
  method_ids: ["HDR", "BW", "topaz", "focus_stacking"]
```

**When a path goes through this node:**
- If `method_id = "HDR"`, add `-HDR` to filename
- If `method_id = "BW"`, add `-BW` to filename
- If `method_id = ""` (empty), add nothing (no processing)

**File-Level Properties** (lowres, hires) are specified on File nodes:

```yaml
- id: "lowres_jpeg"
  type: "File"
  extension: ".JPG"
  property: "lowres"
```

**Filename construction:**
```
base_filename + processing_properties + file_property + extension

Examples:
  AB3D0001 + "" + "" + .CR3 = AB3D0001.CR3
  AB3D0001 + "-HDR" + "" + .TIF = AB3D0001-HDR.TIF
  AB3D0001 + "-HDR" + "-lowres" + .JPG = AB3D0001-HDR-lowres.JPG
  AB3D0001-2 + "-BW" + "-hires" + .JPG = AB3D0001-2-BW-hires.JPG
```

---

## Specific Image Validation Examples

### Example 1: Simple Raw Archive (Specific Image)

**Specific Image Data:**
```python
{
    'camera_id': 'AB3D',
    'counter': '0001',
    'suffix': '',  # First capture
    'unique_id': 'AB3D0001',
    'base_filename': 'AB3D0001',
    'files': ['AB3D0001.CR3', 'AB3D0001.XMP']
}
```

**Validation Against `raw_archive` path:**
- Expected files: `AB3D0001.CR3`, `AB3D0001.XMP`
- Actual files: `AB3D0001.CR3`, `AB3D0001.XMP`
- **Result: CONSISTENT** ✓
- Archival ready: YES (black_box)

---

### Example 2: Counter Looped Specific Image

**Specific Image Data:**
```python
{
    'camera_id': 'AB3D',
    'counter': '0001',
    'suffix': '2',  # Second capture (counter looped)
    'unique_id': 'AB3D0001-2',
    'base_filename': 'AB3D0001-2',
    'files': ['AB3D0001-2.CR3', 'AB3D0001-2.XMP', 'AB3D0001-2.DNG']
}
```

**Validation Against `dng_archive` path:**
- Expected files: `AB3D0001-2.CR3`, `AB3D0001-2.XMP`, `AB3D0001-2.DNG`
- Actual files: `AB3D0001-2.CR3`, `AB3D0001-2.XMP`, `AB3D0001-2.DNG`
- **Result: CONSISTENT** ✓
- Archival ready: YES (black_box)

**Important:** This Specific Image is validated completely independently from `AB3D0001` (first capture).

---

### Example 3: Partial Browsable Archive (Missing hires JPG)

**Specific Image Data:**
```python
{
    'camera_id': 'AB3D',
    'counter': '0001',
    'suffix': '',
    'unique_id': 'AB3D0001',
    'base_filename': 'AB3D0001',
    'files': [
        'AB3D0001.CR3',
        'AB3D0001.XMP',
        'AB3D0001.DNG',
        'AB3D0001.TIF',
        'AB3D0001-HDR.TIF',
        'AB3D0001-HDR-lowres.JPG'
        # Missing: AB3D0001-HDR-hires.JPG
    ]
}
```

**Validation Against `browsable_archive` path:**
- Expected files: All above + `AB3D0001-HDR-hires.JPG`
- Actual files: Missing `AB3D0001-HDR-hires.JPG`
- **Result: PARTIAL** ⚠
- Matched paths: `developed_archive` (100%) ✓
- Archival ready: YES (black_box) / NO (browsable)

**Report:**
```
⚠ Specific Image AB3D0001: PARTIAL
  Ready for: Developed Archive (Black Box) ✓
  Not ready for: Browsable Archive

  Missing for Browsable Archive:
    • AB3D0001-HDR-hires.JPG
    Action: Export HDR TIF as high-resolution JPG
```

---

### Example 4: Inconsistent (Missing XMP)

**Specific Image Data:**
```python
{
    'camera_id': 'AB3D',
    'counter': '0001',
    'suffix': '',
    'unique_id': 'AB3D0001',
    'base_filename': 'AB3D0001',
    'files': ['AB3D0001.CR3']  # Missing XMP
}
```

**Validation Against ALL paths:**
- All paths require XMP after import/selection process
- XMP is missing
- **Result: INCONSISTENT** ✗
- Archival ready: NO

**Report:**
```
✗ Specific Image AB3D0001: INCONSISTENT
  Ready for archival: NO
  Matched paths: None

  Missing required files:
    • AB3D0001.XMP (needed for all archival paths)
    Action: Import CR3 file into Lightroom to create XMP sidecar
```

---

## Multiple Specific Images in One ImageGroup

**ImageGroup with 3 Specific Images:**
```python
{
    'group_id': 'AB3D0001',
    'separate_images': {
        '': {
            'files': ['AB3D0001.CR3', 'AB3D0001.XMP', 'AB3D0001.DNG']
        },
        '2': {
            'files': ['AB3D0001-2.CR3', 'AB3D0001-2.XMP']
        },
        '3': {
            'files': ['AB3D0001-3.CR3']  # Missing XMP
        }
    }
}
```

**Validation Results (per Specific Image):**

| Specific Image | Status | Matched Paths | Archival Ready |
|----------------|--------|---------------|----------------|
| AB3D0001 | CONSISTENT | `dng_archive` | YES (black_box) |
| AB3D0001-2 | CONSISTENT | `raw_archive` | YES (black_box) |
| AB3D0001-3 | INCONSISTENT | None | NO |

**Report Summary:**
```
ImageGroup AB3D0001: MIXED RESULTS

✓ AB3D0001: CONSISTENT
  • Ready for DNG Archive (Black Box)

✓ AB3D0001-2: CONSISTENT
  • Ready for Raw Archive (Black Box)

✗ AB3D0001-3: INCONSISTENT
  • Missing: AB3D0001-3.XMP
  • Action: Import into Lightroom to create XMP sidecar
```

---

## Tool Integration

### Photo Pairing Tool Integration

**What Photo Pairing Does:**
1. Groups files by `camera_id + counter`
2. Detects separate captures using numerical suffixes (2, 3, etc.)
3. Creates `separate_images` structure within ImageGroup

**What Pipeline Validation Adds:**
1. **Flattens** ImageGroup into individual Specific Images
2. **Validates** each Specific Image against all pipeline paths
3. **Identifies** which archival endpoints each Specific Image is ready for
4. **Reports** missing files with actionable recommendations

**Combined Workflow:**
```
Photo Pairing Tool
  ↓ Produces ImageGroup with separate_images
Pipeline Validation
  ↓ Flattens to Specific Images
  ↓ Validates each independently
  ↓ Generates per-Specific-Image reports
User
  ↓ Sees exactly what's missing for each captured image
```

---

### PhotoStats Integration

**What PhotoStats Does:**
- Identifies CR3 files requiring XMP sidecars
- Reports orphaned CR3 files (no XMP)

**What Pipeline Validation Adds:**
- **Node-aware pairing:** Pairing nodes enforce CR3+XMP requirement
- **Path-based validation:** XMP requirement depends on which archival path
- **Shared metadata:** Future support for CR3 and DNG sharing same XMP

**Combined Result:**
```
PhotoStats: "AB3D0001.CR3 is missing XMP sidecar"
  ↓
Pipeline Validation: "AB3D0001 cannot match any archival path without XMP"
  ↓
User Action: "Import AB3D0001.CR3 into Lightroom to create XMP"
```

---

## Graph Traversal Algorithm

**Pseudocode for validation:**

```python
def validate_specific_image(specific_image, pipeline_config):
    """
    Validate ONE Specific Image against pipeline configuration.
    """
    actual_files = set(specific_image['files'])
    base_filename = specific_image['base_filename']  # e.g., "AB3D0001-2"

    # Find all paths from Capture to Terminations
    capture_node = find_node_by_type(pipeline_config, 'Capture')
    termination_nodes = find_nodes_by_type(pipeline_config, 'Termination')

    matching_terminations = []

    for termination in termination_nodes:
        # Enumerate all paths using DFS
        paths = enumerate_all_paths(capture_node, termination, pipeline_config)

        for path in paths:
            # Collect File nodes encountered on this path
            file_nodes = [node for node in path if node.type == 'File']

            # Collect processing properties from Process nodes
            processing_properties = collect_processing_properties(path)

            # Generate expected filenames
            expected_files = generate_expected_filenames(
                base=base_filename,
                file_nodes=file_nodes,
                properties=processing_properties
            )

            # Check if actual files match expected
            if expected_files == actual_files:
                matching_terminations.append({
                    'termination': termination,
                    'path': path,
                    'completion': 100
                })

    # Classify result
    if matching_terminations:
        return {
            'unique_id': specific_image['unique_id'],
            'status': 'CONSISTENT',
            'matched_terminations': matching_terminations,
            'archival_ready': True
        }
    else:
        return {
            'unique_id': specific_image['unique_id'],
            'status': 'INCONSISTENT',
            'matched_terminations': [],
            'archival_ready': False,
            'missing_files': identify_missing_files(actual_files, pipeline_config)
        }
```

---

## Summary

The node-based architecture provides a powerful and flexible way to model complex photo processing workflows:

1. **6 Node Types** model different workflow elements (Capture, File, Process, Pairing, Branching, Termination)

2. **File Nodes** are critical - they define what files should exist in a complete Specific Image

3. **Graph Traversal** enumerates all valid paths from Capture to Termination, collecting File nodes

4. **Specific Images** are validated independently, not ImageGroups

5. **Property Accumulation** builds filenames by collecting processing properties along paths

6. **Termination Nodes** define archival endpoints (black_box or browsable)

7. **Validation** compares actual files against expected files for all paths

8. **Classification** reports CONSISTENT, PARTIAL, or INCONSISTENT per Specific Image

This approach supports:
- Branching workflows (different processing methods)
- Parallel execution (multiple JPG exports)
- Optional files (CR3 deletion after DNG conversion)
- Shared metadata (CR3 and DNG using same XMP)
- Counter looping (multiple captures with same camera_id + counter)
- Flexible archival strategies (black_box vs browsable)

The result is a comprehensive validation tool that tells photographers exactly what files are missing to achieve their archival goals.
