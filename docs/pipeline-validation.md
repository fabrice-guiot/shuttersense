# Pipeline Validation Tool

The Pipeline Validation Tool validates photo collections against user-defined processing workflows (pipelines). It analyzes your folder of photos, compares them against expected file patterns, and generates interactive HTML reports showing archival readiness, incomplete processing, and workflow compliance.

## Overview

### What It Does

The Pipeline Validation Tool helps photographers:

- **Validate Processing Workflows**: Automatically checks if images have completed expected processing steps
- **Assess Archival Readiness**: Identifies which images are ready for archival storage
- **Detect Incomplete Processing**: Finds images missing expected processing steps (PARTIAL status)
- **Identify Extra Files**: Detects files that exist but aren't defined in your pipeline (CONSISTENT-WITH-WARNING)
- **Multi-Termination Analysis**: Tracks images against multiple archival endpoints simultaneously
- **Generate Reports**: Creates interactive HTML reports with charts and statistics

### Key Features

- ✅ Analyze 10,000+ images in under 60 seconds (with caching)
- ✅ Read-only operation (no file creation/modification)
- ✅ Interactive HTML reports with Chart.js visualizations
- ✅ Persistent caching for fast re-runs
- ✅ Integrates with Photo Pairing Tool for file grouping
- ✅ Support for complex workflows (loops, branching, multi-termination)
- ✅ Graceful error handling (permissions, invalid config, Ctrl+C)

## Prerequisites

Before using the Pipeline Validation Tool, make sure you have:

1. **Python 3.10+** (required for match/case syntax)
2. **Photo Pairing Tool** (must run first to generate ImageGroups)
3. **Configured** [config file](configuration.md) with pipeline definition
4. [Installed the dependencies](installation.md)

## Pipeline Concepts

### Pipeline Structure

A pipeline is a directed graph of nodes that defines your photo processing workflow:

- **Capture Node**: Starting point (camera capture)
- **File Nodes**: Expected files at each stage (e.g., `.CR3`, `.DNG`, `.TIF`)
- **Process Nodes**: Processing steps that add suffixes (e.g., `-DxO_DeepPRIME_XD2s`, `-Edit`)
- **Branching Nodes**: User decision points (e.g., archive now vs. continue processing)
- **Pairing Nodes**: Merge multiple images (e.g., HDR from 3 bracketed exposures)
- **Termination Nodes**: End states (e.g., "Black Box Archive", "Browsable Archive")

### Validation Statuses

Each image is validated against the pipeline and assigned one of four statuses:

- **CONSISTENT** ✅: All expected files present, no extra files (archival ready)
- **CONSISTENT-WITH-WARNING** ⚠️: All expected files present, extra files exist (archival ready)
- **PARTIAL** ⏳: Subset of expected files present (incomplete processing)
- **INCONSISTENT** ❌: No valid path match or critical files missing

### Multi-Termination

Images can satisfy multiple termination endpoints simultaneously:

- Example: Image with basic DNG conversion → Black Box Archive CONSISTENT
- Same image with full editing workflow → Browsable Archive CONSISTENT
- Both termination statistics include the image

## Usage

### Basic Workflow

#### Step 1: Run Photo Pairing Tool

The Pipeline Validation Tool depends on Photo Pairing results:

```bash
# Analyze folder structure first
python3 photo_pairing.py /Users/photographer/Photos/2025-01-15

# This creates:
# - .photo_pairing_imagegroups (cache file with grouped images)
# - photo_pairing_report_2025-12-27_14-30-00.html
```

#### Step 2: Define Your Pipeline

Add a `processing_pipelines` section to `config/config.yaml` (see [Configuration](#configuration) below).

#### Step 3: Run Pipeline Validation

```bash
# Validate folder against pipeline
python3 pipeline_validation.py /Users/photographer/Photos/2025-01-15

# Output:
# ✓ Using Photo Pairing cache
# ✓ Pipeline configuration loaded (12 nodes)
# Validating 1,124 specific images...
# ✓ Validation complete in 2.3 seconds
#
# Report generated: pipeline_validation_report_2025-12-27_14-35-22.html
```

#### Step 4: Review HTML Report

Open the generated HTML report in your browser:

```bash
open pipeline_validation_report_2025-12-27_14-35-22.html
```

The report shows:
- **KPI Cards**: Total images, archival readiness counts, status distribution
- **Charts**: Pie chart (status distribution), bar chart (groups per termination)
- **Tables**: Detailed file lists for CONSISTENT, PARTIAL, and INCONSISTENT images

### Command-Line Options

```bash
# Basic usage
python3 pipeline_validation.py <folder_path>

# Show help
python3 pipeline_validation.py --help
python3 pipeline_validation.py -h

# Specify custom config file
python3 pipeline_validation.py <folder_path> --config /path/to/custom-config.yaml

# Force regeneration (ignore caches)
python3 pipeline_validation.py <folder_path> --force-regenerate

# Show cache status without running validation
python3 pipeline_validation.py <folder_path> --cache-status

# Dry run (validate pipeline config only, don't analyze folder)
python3 pipeline_validation.py --validate-config
```

## Configuration

### Minimal Pipeline Configuration

Add to `config/config.yaml`:

```yaml
# Existing sections (required)
photo_extensions:
  - .cr3
  - .dng
  - .tiff
  - .jpg

metadata_extensions:
  - .xmp

camera_mappings:
  AB3D:
    - name: Canon EOS R5
      serial_number: "12345"

processing_methods:
  DxO_DeepPRIME_XD2s: "DNG Conversion with DxO DeepPRIME XD2s"
  Edit: "Photoshop Editing"

# NEW SECTION: Pipeline Definition
processing_pipelines:
  nodes:
    # Start: Camera capture
    - id: "capture"
      type: "Capture"
      name: "Camera Capture"
      output: ["raw_image_1"]

    # File: Raw camera file (.CR3)
    - id: "raw_image_1"
      type: "File"
      extension: ".CR3"
      name: "Canon Raw File"
      output: ["selection_process"]

    # Process: Select images (no suffix added)
    - id: "selection_process"
      type: "Process"
      method_ids: [""]  # Empty = no suffix
      name: "Image Selection"
      output: ["dng_conversion"]

    # Process: Convert to DNG with DxO processing
    - id: "dng_conversion"
      type: "Process"
      method_ids: ["DxO_DeepPRIME_XD2s"]
      name: "DNG Conversion"
      output: ["openformat_raw_image", "xmp_metadata_1"]

    # File: DNG file (expected: AB3D0001-DxO_DeepPRIME_XD2s.DNG)
    - id: "openformat_raw_image"
      type: "File"
      extension: ".DNG"
      name: "Open Format Raw"
      output: ["termination_blackbox"]

    # File: XMP metadata
    - id: "xmp_metadata_1"
      type: "File"
      extension: ".XMP"
      name: "XMP Metadata"
      output: []

    # End: Archive ready state
    - id: "termination_blackbox"
      type: "Termination"
      termination_type: "Black Box Archive"
      name: "Black Box Archive Ready"
      output: []
```

**Expected Files for AB3D0001:**
- `AB3D0001.CR3` (from raw_image_1)
- `AB3D0001.XMP` (from xmp_metadata_1)
- `AB3D0001-DxO_DeepPRIME_XD2s.DNG` (from openformat_raw_image after dng_conversion)

**Validation Results:**
- If all 3 files exist → **CONSISTENT** (archival ready)
- If CR3 + XMP exist, DNG missing → **PARTIAL** (incomplete processing)
- If extra files exist (e.g., AB3D0001.JPG) → **CONSISTENT-WITH-WARNING**

## Pipeline Configuration Examples

### Example 1: Simple Raw Archive

Basic pipeline for archiving raw files with XMP metadata:

```yaml
processing_pipelines:
  nodes:
    - id: "capture"
      type: "Capture"
      name: "Camera Capture"
      output: ["raw_image"]

    - id: "raw_image"
      type: "File"
      extension: ".CR3"
      name: "Canon Raw File"
      output: ["xmp_metadata"]

    - id: "xmp_metadata"
      type: "File"
      extension: ".XMP"
      name: "XMP Metadata"
      output: ["termination_raw"]

    - id: "termination_raw"
      type: "Termination"
      termination_type: "Raw Archive"
      name: "Raw Archive Ready"
      output: []
```

**Expected Files:** `AB3D0001.CR3`, `AB3D0001.XMP`

### Example 2: Iterative Photoshop Editing (with Loop)

Pipeline supporting multiple Photoshop edit iterations:

```yaml
processing_pipelines:
  nodes:
    - id: "capture"
      type: "Capture"
      name: "Camera Capture"
      output: ["raw_image"]

    - id: "raw_image"
      type: "File"
      extension: ".CR3"
      name: "Canon Raw File"
      output: ["dng_conversion"]

    - id: "dng_conversion"
      type: "Process"
      method_ids: ["DxO_DeepPRIME_XD2s"]
      name: "DNG Conversion"
      output: ["openformat_raw"]

    - id: "openformat_raw"
      type: "File"
      extension: ".DNG"
      name: "Open Format Raw"
      output: ["photoshop_process"]

    - id: "photoshop_process"
      type: "Process"
      method_ids: ["Edit"]
      name: "Photoshop Editing"
      output: ["tiff_branching"]

    # Branching: User decides to create TIFF or continue editing
    - id: "tiff_branching"
      type: "Branching"
      condition_description: "User decides: Create TIFF or continue editing"
      name: "TIFF Generation Decision"
      output: ["generate_tiff", "photoshop_process"]  # Loop back for more edits

    - id: "generate_tiff"
      type: "Process"
      method_ids: [""]  # No additional suffix
      name: "Generate TIFF"
      output: ["tiff_image"]

    - id: "tiff_image"
      type: "File"
      extension: ".TIF"
      name: "TIFF File"
      output: ["termination_blackbox"]

    - id: "termination_blackbox"
      type: "Termination"
      termination_type: "Black Box Archive"
      name: "Black Box Archive Ready"
      output: []
```

**Expected for AB3D0001 (3 Photoshop iterations):**
- `AB3D0001.CR3`
- `AB3D0001-DxO_DeepPRIME_XD2s.DNG`
- `AB3D0001-DxO_DeepPRIME_XD2s-Edit-Edit-Edit.TIF`

**Note:** Loop limit is 5 iterations maximum. If you did 8 edits, validation truncates at 5 and marks the path as truncated (but still validates the collected files).

### Example 3: Multi-Termination Pipeline

Pipeline with multiple archival endpoints (Black Box Archive and Browsable Archive):

```yaml
processing_pipelines:
  nodes:
    - id: "capture"
      type: "Capture"
      name: "Camera Capture"
      output: ["raw_image"]

    - id: "raw_image"
      type: "File"
      extension: ".CR3"
      name: "Canon Raw File"
      output: ["dng_conversion"]

    - id: "dng_conversion"
      type: "Process"
      method_ids: ["DxO_DeepPRIME_XD2s"]
      name: "DNG Conversion"
      output: ["openformat_raw", "xmp_metadata"]

    - id: "openformat_raw"
      type: "File"
      extension: ".DNG"
      name: "Open Format Raw"
      output: ["photoshop_process", "termination_blackbox"]  # Can archive here OR continue

    - id: "xmp_metadata"
      type: "File"
      extension: ".XMP"
      name: "XMP Metadata"
      output: []

    - id: "photoshop_process"
      type: "Process"
      method_ids: ["Edit"]
      name: "Photoshop Editing"
      output: ["tiff_image"]

    - id: "tiff_image"
      type: "File"
      extension: ".TIF"
      name: "TIFF File"
      output: ["web_export"]

    - id: "web_export"
      type: "Process"
      method_ids: ["Web"]
      name: "Web Export"
      output: ["lowres_jpg", "hires_jpg"]

    - id: "lowres_jpg"
      type: "File"
      extension: ".JPG"
      name: "Low-Res Web Export"
      output: ["termination_browsable"]

    - id: "hires_jpg"
      type: "File"
      extension: ".JPG"
      name: "High-Res Web Export"
      output: ["termination_browsable"]

    # Termination 1: Black Box Archive (raw + DNG only)
    - id: "termination_blackbox"
      type: "Termination"
      termination_type: "Black Box Archive"
      name: "Black Box Archive Ready"
      output: []

    # Termination 2: Browsable Archive (full workflow with web exports)
    - id: "termination_browsable"
      type: "Termination"
      termination_type: "Browsable Archive"
      name: "Browsable Archive Ready"
      output: []
```

**Validation for AB3D0001:**

| Files Present | Black Box Status | Browsable Status |
|---------------|------------------|------------------|
| CR3, XMP, DNG | ✅ CONSISTENT | ❌ PARTIAL (missing TIF, JPGs) |
| CR3, XMP, DNG, TIF, lowres.JPG, hires.JPG | ✅ CONSISTENT | ✅ CONSISTENT |

**Archival Readiness:** An image can be counted in both termination statistics simultaneously!

## Understanding Validation Results

### CONSISTENT ✅
- **Meaning**: All expected files present, no extra files
- **Archival Ready**: YES
- **Action**: None - processing complete

**Example:**
- Expected: `AB3D0001.CR3`, `AB3D0001.DNG`, `AB3D0001.XMP`
- Actual: `AB3D0001.CR3`, `AB3D0001.DNG`, `AB3D0001.XMP`

### CONSISTENT-WITH-WARNING ⚠️
- **Meaning**: All expected files present, extra files exist
- **Archival Ready**: YES
- **Action**: Review extra files - may be backups or test exports

**Example:**
- Expected: `AB3D0001.CR3`, `AB3D0001.DNG`, `AB3D0001.XMP`
- Actual: `AB3D0001.CR3`, `AB3D0001.DNG`, `AB3D0001.XMP`, `AB3D0001-backup.CR3`
- Extra: `AB3D0001-backup.CR3`

### PARTIAL ⏳
- **Meaning**: Subset of expected files present (incomplete processing)
- **Archival Ready**: NO
- **Action**: Complete missing processing steps

**Example:**
- Expected: `AB3D0001.CR3`, `AB3D0001.DNG`, `AB3D0001-Edit.TIF`
- Actual: `AB3D0001.CR3`, `AB3D0001.DNG`
- Missing: `AB3D0001-Edit.TIF`
- Completion: 66.7%

### INCONSISTENT ❌
- **Meaning**: No valid path match, or critical files missing
- **Archival Ready**: NO
- **Action**: Investigate - may need to reprocess or fix pipeline definition

**Example:**
- Expected: `AB3D0001.CR3`, `AB3D0001.DNG`
- Actual: `AB3D0001.JPG` (only JPG exists)
- No valid paths matched

## Common Workflows

### Workflow 1: First-Time Validation

```bash
# 1. Analyze folder structure
python3 photo_pairing.py ~/Photos/2025-01-15

# 2. Validate against pipeline
python3 pipeline_validation.py ~/Photos/2025-01-15

# 3. Review HTML report
open pipeline_validation_report_*.html

# 4. Fix incomplete processing, re-run
# (validation uses cached Photo Pairing results if folder unchanged)
python3 pipeline_validation.py ~/Photos/2025-01-15
```

### Workflow 2: Iterative Pipeline Development

```bash
# 1. Start with minimal pipeline (test with small folder)
python3 pipeline_validation.py ~/Photos/test-folder

# 2. Review validation errors in report

# 3. Update pipeline configuration in config.yaml

# 4. Re-run validation (fast - uses caches)
python3 pipeline_validation.py ~/Photos/test-folder

# 5. Repeat until validation matches expectations
```

### Workflow 3: Monitoring Large Archives

```bash
# 1. Initial validation (uncached - may take ~40 seconds for 10,000 images)
python3 pipeline_validation.py ~/Photos/2024-Complete

# 2. Later re-checks (cached - ~2 seconds)
python3 pipeline_validation.py ~/Photos/2024-Complete

# 3. If folder changed, Photo Pairing cache auto-invalidates
# Tool prompts: "(r)egenerate Photo Pairing or (u)se cache anyway?"
```

### Workflow 4: Force Regeneration

```bash
# Ignore all caches and regenerate from scratch
python3 pipeline_validation.py ~/Photos/2025-01-15 --force-regenerate

# Or manually delete cache files
rm ~/Photos/2025-01-15/.photo_pairing_imagegroups
rm ~/Photos/2025-01-15/.pipeline_validation_cache.json
python3 pipeline_validation.py ~/Photos/2025-01-15
```

## Troubleshooting

### Problem: "Photo Pairing cache not found"

**Cause:** Pipeline Validation depends on Photo Pairing Tool output.

**Solution:**
```bash
# Run Photo Pairing Tool first
python3 photo_pairing.py /path/to/folder
```

### Problem: "Pipeline configuration has errors: Node 'foo' references non-existent output 'bar'"

**Cause:** Pipeline configuration has invalid node references.

**Solution:**
- Check `processing_pipelines.nodes` in `config.yaml`
- Ensure all `output` values reference existing node IDs
- Example fix:
```yaml
# BEFORE (error)
- id: "raw_image"
  output: ["dng_converion"]  # Typo!

# AFTER (fixed)
- id: "raw_image"
  output: ["dng_conversion"]
```

### Problem: "Unknown processing method: 'HDR'"

**Cause:** Processing method used in pipeline but not defined in config.

**Solution:**
Add missing method to `processing_methods` section in config:
```yaml
processing_methods:
  HDR: "High Dynamic Range Merge"
  DxO_DeepPRIME_XD2s: "DNG Conversion with DxO DeepPRIME XD2s"
  Edit: "Photoshop Editing"
```

### Problem: All images show INCONSISTENT

**Cause:** Pipeline doesn't match your actual workflow.

**Solution:**
- Verify pipeline matches your actual workflow
- Check file extensions in pipeline match actual files (case-sensitive!)
- Review expected filenames in validation report
- Example: Pipeline expects `.TIF` but files are `.TIFF` → no match

### Problem: Validation is slow (>60 seconds for 10,000 images)

**Diagnosis:**
```bash
# Check cache status
python3 pipeline_validation.py /path/to/folder --cache-status
```

**Solutions:**
- **First run**: Expected to take ~40 seconds (file scanning)
- **Subsequent runs**: Should be ~2 seconds (cached)
- If still slow, check:
  - Is folder on network drive? (slower I/O)
  - Did folder content change? (invalidates cache)
  - Did pipeline config change? (invalidates validation cache)

### Problem: "Path truncated after 5 iterations"

**Meaning:**
- You have a looping Process node (e.g., iterative Photoshop editing)
- Photographer performed more than 5 iterations
- Validation truncated path at 5 iterations for performance

**Solution:**
- This is expected behavior for safety
- Validation still checks files from first 5 iterations
- If this is common, consider updating pipeline to better model your workflow

### Problem: Manual cache edits not detected

**Solution:**
- Ensure JSON syntax is valid (tool won't load invalid JSON)
- Cache invalidation relies on hash mismatch
- If you want to force regeneration: `--force-regenerate`

### Problem: "Pairing node must have exactly 2 inputs"

**Cause:** Pairing nodes require exactly 2 upstream branches to merge.

**Solution:**
- Check your pipeline topology
- Pairing nodes combine paths from 2 separate branches
- Example: HDR workflow needs 3 File nodes, not 1 Pairing node with 3 inputs
- Correct approach: Use nested Pairing nodes or redesign topology

### Problem: UTF-8 encoding errors on Windows

**Cause:** Windows default encoding may not be UTF-8.

**Solution:**
- Tool uses `encoding='utf-8'` for all file operations
- If errors persist, check Python environment: `python -c "import sys; print(sys.getdefaultencoding())"`
- Set environment variable: `set PYTHONUTF8=1` (Windows CMD) or `$env:PYTHONUTF8=1` (PowerShell)

## Performance Tips

1. **Use Caching**: Let Photo Pairing cache persist between runs
2. **Batch Validation**: Validate multiple folders sequentially (each benefits from tool initialization)
3. **Pipeline Simplicity**: Simpler pipelines (fewer nodes) validate faster
4. **Archival Workflow**: Validate before archiving to ensure completeness

## Advanced Features

### Cache Management

Two cache files are used:

1. **Photo Pairing Cache** (`.photo_pairing_imagegroups`):
   - Generated by Photo Pairing Tool
   - Contains file groupings and metadata
   - Invalidated when folder content changes

2. **Pipeline Validation Cache** (`.pipeline_validation_cache.json`):
   - Generated by Pipeline Validation Tool
   - Contains validation results
   - Invalidated when pipeline config changes or folder changes

### Cache Invalidation Triggers

The tool automatically invalidates caches when:

1. **Pipeline config changes** (file hash mismatch)
2. **Folder content changes** (Photo Pairing detects)
3. **Manual cache edits** (user modified cache directly)
4. **Version mismatch** (cache from older tool version)

### Interactive Prompts

When cache validity is uncertain, the tool prompts:

```
Photo Pairing cache exists but folder may have changed.
(r)egenerate, (u)se cache anyway, (a)bort?
```

- **r**: Force regeneration (slow but accurate)
- **u**: Use existing cache (fast but may be stale)
- **a**: Cancel operation

## Performance Benchmarks

Target performance (tested on M1 Mac with SSD):

- **10,000 image groups** (uncached): ~40 seconds
- **10,000 image groups** (cached): <2 seconds
- **HTML report generation** (5,000 groups): <2 seconds
- **Graph traversal** (complex pipeline with loops): <1 second

## What Pipeline Validation Analyzes

The tool performs comprehensive analysis:

1. **File Existence**: Checks which expected files are present
2. **File Grouping**: Uses Photo Pairing results for image group relationships
3. **Path Traversal**: Enumerates all valid pipeline paths from Capture to Termination
4. **Status Classification**: Assigns CONSISTENT/CONSISTENT-WITH-WARNING/PARTIAL/INCONSISTENT
5. **Multi-Termination**: Tracks image status across all termination endpoints
6. **Performance**: Measures validation time and caching efficiency

## Output

### Console Output

The tool provides progress information and a summary in the console:

```
Pipeline Validation Tool v1.0.0
Analyzing: /Users/photographer/Photos/2025-01-15

Loading configuration...
Loaded configuration from: /Users/photographer/config/config.yaml
  Loaded 19 pipeline nodes
  Using pipeline: default

Loading Photo Pairing results...
  Loaded 10 image groups
  Flattened to 12 specific images

Validating images against pipeline...
  Validating images: 12/12 (100.0%)

  Validated 12 images
  ✓ Consistent: 8
  ⚠ Consistent-with-warning: 2
  ⏳ Partial: 1
  ✗ Inconsistent: 1

Generating HTML report...
  Report saved: pipeline_validation_report_2025-12-27_14-35-22.html

Scan completed in 2.35 seconds
```

### HTML Report

The HTML report includes:

1. **Summary Section**:
   - Total images validated
   - Validation status distribution
   - Archival readiness counts per termination type

2. **Charts**:
   - Pie chart: Status distribution
   - Bar chart: Image groups per termination type

3. **Detailed Tables**:
   - CONSISTENT images (ready for archival)
   - PARTIAL images (incomplete processing)
   - INCONSISTENT images (needs investigation)
   - For each image: base filename, files present, files expected, files missing, completion %

## See Also

- [Installation Guide](installation.md) - How to install the tool
- [Configuration Guide](configuration.md) - How to configure file types and pipelines
- [Photo Pairing Tool](photo-pairing.md) - Prerequisite tool for file grouping
- [PhotoStats Tool](photostats.md) - Alternative analysis tool for orphan detection

## License

GNU Affero General Public License v3.0 (AGPL-3.0)
