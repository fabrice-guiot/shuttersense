# Quick Start Guide: Pipeline Validation Tool

**Feature**: Photo Processing Pipeline Validation
**Version**: 1.0.0
**Date**: 2025-12-27

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Installation](#installation)
4. [Basic Usage](#basic-usage)
5. [Configuration](#configuration)
6. [Pipeline Definition Examples](#pipeline-definition-examples)
7. [Common Workflows](#common-workflows)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The Pipeline Validation Tool validates your photo collections against user-defined processing workflows (pipelines). It analyzes your folder of photos, compares them against expected file patterns, and generates an interactive HTML report showing:

- **Archival Readiness**: Which images are ready for archival storage
- **Incomplete Processing**: Which images are missing expected processing steps
- **Extra Files**: Which files exist but aren't defined in your pipeline
- **Multi-Termination Statistics**: Images can satisfy multiple archival endpoints simultaneously

**Key Benefits:**
- Analyze 10,000+ images in under 60 seconds (with caching)
- No file creation/modification (read-only analysis)
- Interactive HTML reports with visualizations
- Persistent caching for fast re-runs

---

## Prerequisites

### Required

1. **Python 3.10+** (required for match/case syntax)
2. **Photo Pairing Tool** (must run first to generate ImageGroups)
3. **Configuration file** (`config/config.yaml`)

### Dependencies

Automatically installed with requirements.txt:
- PyYAML >=6.0
- Jinja2 >=3.1.0
- pytest (for development)

---

## Installation

```bash
# Clone repository (if not already done)
cd /path/to/photo-admin

# Install dependencies
pip install -r requirements.txt

# Verify installation
python3 pipeline_validation.py --help
```

---

## Basic Usage

### Step 1: Run Photo Pairing Tool

The Pipeline Validation Tool depends on Photo Pairing results.

```bash
# Analyze folder structure first
python3 photo_pairing.py /Users/photographer/Photos/2025-01-15

# This creates:
# - .photo_pairing_imagegroups (cache file with grouped images)
# - photo_pairing_report_2025-12-27_14-30-00.html
```

### Step 2: Define Your Pipeline

Add a `processing_pipelines` section to `config/config.yaml` (see [Configuration](#configuration) below).

### Step 3: Run Pipeline Validation

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

### Step 4: Review HTML Report

Open the generated HTML report in your browser:

```bash
open pipeline_validation_report_2025-12-27_14-35-22.html
```

The report shows:
- **KPI Cards**: Total images, archival readiness counts, status distribution
- **Charts**: Pie chart (status distribution), bar chart (groups per termination)
- **Tables**: Detailed file lists for CONSISTENT, PARTIAL, and INCONSISTENT images

---

## Configuration

### Minimal Pipeline Configuration

Add to `config/config.yaml`:

```yaml
# Existing sections
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

**Validation:**
- If all 3 files exist → **CONSISTENT** (archival ready)
- If CR3 + XMP exist, DNG missing → **PARTIAL** (incomplete processing)
- If extra files exist (e.g., AB3D0001.JPG) → **CONSISTENT-WITH-WARNING**

---

## Pipeline Definition Examples

### Example 1: Simple Raw Archive

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

**Expected:** `AB3D0001.CR3`, `AB3D0001.XMP`

---

### Example 2: Iterative Photoshop Editing (with Loop)

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

**Loop Limit:** Maximum 5 iterations. If photographer did 8 edits, validation truncates at 5 and marks path as truncated (still validates collected files).

---

### Example 3: HDR Pairing

```yaml
processing_pipelines:
  nodes:
    - id: "capture"
      type: "Capture"
      name: "Camera Capture"
      output: ["raw_image_1", "raw_image_2", "raw_image_3"]

    # Three raw files for HDR
    - id: "raw_image_1"
      type: "File"
      extension: ".CR3"
      name: "Raw File 1 (Underexposed)"
      output: ["hdr_pairing"]

    - id: "raw_image_2"
      type: "File"
      extension: ".CR3"
      name: "Raw File 2 (Normal)"
      output: ["hdr_pairing"]

    - id: "raw_image_3"
      type: "File"
      extension: ".CR3"
      name: "Raw File 3 (Overexposed)"
      output: ["hdr_pairing"]

    # Pairing: Merge 3 images
    - id: "hdr_pairing"
      type: "Pairing"
      pairing_type: "HDR"
      input_count: 3
      name: "HDR Merge"
      output: ["hdr_result"]

    - id: "hdr_result"
      type: "File"
      extension: ".DNG"
      name: "HDR Merged DNG"
      output: ["termination_hdr"]

    - id: "termination_hdr"
      type: "Termination"
      termination_type: "HDR Archive"
      name: "HDR Archive Ready"
      output: []
```

**Expected for AB3D0001 (primary image) and AB3D0001-2, AB3D0001-3 (HDR bracketed images):**
- `AB3D0001.CR3`, `AB3D0001-2.CR3`, `AB3D0001-3.CR3`
- `AB3D0001.DNG` (merged HDR result)

---

### Example 4: Multi-Termination Pipeline

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

**Archival Readiness:** Image can be counted in both termination statistics simultaneously!

---

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

---

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

---

### Workflow 3: Monitoring Large Archives

```bash
# 1. Initial validation (uncached - may take ~40 seconds for 10,000 images)
python3 pipeline_validation.py ~/Photos/2024-Complete

# 2. Later re-checks (cached - ~2 seconds)
python3 pipeline_validation.py ~/Photos/2024-Complete

# 3. If folder changed, Photo Pairing cache auto-invalidates
# Tool prompts: "(r)egenerate Photo Pairing or (u)se cache anyway?"
```

---

### Workflow 4: Force Regeneration

```bash
# Ignore all caches and regenerate from scratch
python3 pipeline_validation.py ~/Photos/2025-01-15 --force-regenerate

# Or manually delete cache files
rm ~/Photos/2025-01-15/.photo_pairing_imagegroups
rm ~/Photos/2025-01-15/.pipeline_validation_cache.json
python3 pipeline_validation.py ~/Photos/2025-01-15
```

---

## Command-Line Options

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

---

## Understanding Validation Statuses

### CONSISTENT ✅
- **Meaning**: All expected files present, no extra files
- **Archival Ready**: YES
- **Action**: None - processing complete

**Example:**
- Expected: `AB3D0001.CR3`, `AB3D0001.DNG`, `AB3D0001.XMP`
- Actual: `AB3D0001.CR3`, `AB3D0001.DNG`, `AB3D0001.XMP`

---

### CONSISTENT-WITH-WARNING ⚠️
- **Meaning**: All expected files present, extra files exist
- **Archival Ready**: YES (per clarification)
- **Action**: Review extra files - may be backups or test exports

**Example:**
- Expected: `AB3D0001.CR3`, `AB3D0001.DNG`, `AB3D0001.XMP`
- Actual: `AB3D0001.CR3`, `AB3D0001.DNG`, `AB3D0001.XMP`, `AB3D0001-backup.CR3`
- Extra: `AB3D0001-backup.CR3`

---

### PARTIAL ⏳
- **Meaning**: Subset of expected files present (incomplete processing)
- **Archival Ready**: NO
- **Action**: Complete missing processing steps

**Example:**
- Expected: `AB3D0001.CR3`, `AB3D0001.DNG`, `AB3D0001-Edit.TIF`
- Actual: `AB3D0001.CR3`, `AB3D0001.DNG`
- Missing: `AB3D0001-Edit.TIF`
- Completion: 66.7%

---

### INCONSISTENT ❌
- **Meaning**: No valid path match, or critical files missing
- **Archival Ready**: NO
- **Action**: Investigate - may need to reprocess or fix pipeline definition

**Example:**
- Expected: `AB3D0001.CR3`, `AB3D0001.DNG`
- Actual: `AB3D0001.JPG` (only JPG exists)
- No valid paths matched

---

## Troubleshooting

### Problem: "Photo Pairing cache not found"

**Solution:**
```bash
# Run Photo Pairing Tool first
python3 photo_pairing.py /path/to/folder
```

---

### Problem: "Pipeline configuration has errors: Node 'foo' references non-existent output 'bar'"

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

---

### Problem: "Unknown processing method: 'HDR'"

**Solution:**
- Add missing method to `processing_methods` section in config:
```yaml
processing_methods:
  HDR: "High Dynamic Range Merge"
  DxO_DeepPRIME_XD2s: "DNG Conversion with DxO DeepPRIME XD2s"
  Edit: "Photoshop Editing"
```

---

### Problem: All images show INCONSISTENT

**Solution:**
- Verify pipeline matches your actual workflow
- Check file extensions in pipeline match actual files (case-sensitive!)
- Review expected filenames in validation report
- Example: Pipeline expects `.TIF` but files are `.TIFF` → no match

---

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

---

### Problem: "Path truncated after 5 iterations"

**Meaning:**
- You have a looping Process node (e.g., iterative Photoshop editing)
- Photographer performed more than 5 iterations
- Validation truncated path at 5 iterations for performance

**Solution:**
- This is expected behavior for safety
- Validation still checks files from first 5 iterations
- If this is common, consider updating pipeline to better model your workflow

---

### Problem: Manual cache edits not detected

**Solution:**
- Ensure JSON syntax is valid (tool won't load invalid JSON)
- Cache invalidation relies on hash mismatch
- If you want to force regeneration: `--force-regenerate`

---

## Performance Tips

1. **Use Caching**: Let Photo Pairing cache persist between runs
2. **Batch Validation**: Validate multiple folders sequentially (each benefits from tool initialization)
3. **Pipeline Simplicity**: Simpler pipelines (fewer nodes) validate faster
4. **Archival Workflow**: Validate before archiving to ensure completeness

---

## Next Steps

- **Read Specification**: See `spec.md` for complete feature requirements
- **Review Data Model**: See `data-model.md` for data structure details
- **Explore Research**: See `research.md` for architectural decisions
- **Run Tests**: `pytest tests/test_pipeline_validation.py -v`

---

**Quick Start Guide Complete**: 2025-12-27
**Reviewed By**: Claude Sonnet 4.5
**Status**: Ready for `/speckit.tasks` (Phase 2)
