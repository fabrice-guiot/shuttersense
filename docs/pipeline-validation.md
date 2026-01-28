# Pipeline Validation Tool

> **Note**: The standalone `pipeline_validation.py` CLI script has been removed. Pipeline Validation analysis is now available exclusively through the ShutterSense agent. See the usage examples below.

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

- Analyze 10,000+ images in under 60 seconds (with caching)
- Read-only operation (no file creation/modification)
- Interactive HTML reports with Chart.js visualizations
- Support for complex workflows (loops, branching, multi-termination)
- Integrates with Photo Pairing analysis for file grouping

## Usage

### Test a Local Path

```bash
shuttersense-agent test /path/to/photos --tool pipeline_validation
```

### Save an HTML Report

```bash
shuttersense-agent test /path/to/photos --tool pipeline_validation --output report.html
```

### Run Against a Registered Collection

```bash
# Online mode (uploads results to server)
shuttersense-agent run <collection-guid> --tool pipeline_validation

# Offline mode (saves results locally for later sync)
shuttersense-agent run <collection-guid> --tool pipeline_validation --offline

# With HTML report output
shuttersense-agent run <collection-guid> --tool pipeline_validation --output report.html
```

### Sync Offline Results

```bash
# Preview pending results
shuttersense-agent sync --dry-run

# Upload all pending results
shuttersense-agent sync
```

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

- **CONSISTENT**: All expected files present, no extra files (archival ready)
- **CONSISTENT-WITH-WARNING**: All expected files present, extra files exist (archival ready)
- **PARTIAL**: Subset of expected files present (incomplete processing)
- **INCONSISTENT**: No valid path match or critical files missing

### Multi-Termination

Images can satisfy multiple termination endpoints simultaneously:

- Example: Image with basic DNG conversion -> Black Box Archive CONSISTENT
- Same image with full editing workflow -> Browsable Archive CONSISTENT
- Both termination statistics include the image

## Configuration

### Minimal Pipeline Configuration

Add a `processing_pipelines` section to your configuration:

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

# Pipeline Definition
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
- If all 3 files exist -> **CONSISTENT** (archival ready)
- If CR3 + XMP exist, DNG missing -> **PARTIAL** (incomplete processing)
- If extra files exist (e.g., AB3D0001.JPG) -> **CONSISTENT-WITH-WARNING**

## Understanding Validation Results

### CONSISTENT
- **Meaning**: All expected files present, no extra files
- **Archival Ready**: YES
- **Action**: None - processing complete

### CONSISTENT-WITH-WARNING
- **Meaning**: All expected files present, extra files exist
- **Archival Ready**: YES
- **Action**: Review extra files - may be backups or test exports

### PARTIAL
- **Meaning**: Subset of expected files present (incomplete processing)
- **Archival Ready**: NO
- **Action**: Complete missing processing steps

### INCONSISTENT
- **Meaning**: No valid path match, or critical files missing
- **Archival Ready**: NO
- **Action**: Investigate - may need to reprocess or fix pipeline definition

## Troubleshooting

### Problem: "Pipeline configuration has errors"

**Cause:** Pipeline configuration has invalid node references.

**Solution:**
- Check `processing_pipelines.nodes` in your config
- Ensure all `output` values reference existing node IDs

### Problem: All images show INCONSISTENT

**Cause:** Pipeline doesn't match your actual workflow.

**Solution:**
- Verify pipeline matches your actual workflow
- Check file extensions in pipeline match actual files (case-sensitive!)
- Review expected filenames in validation report

### Problem: "Path truncated after 5 iterations"

**Meaning:** You have a looping Process node and the photographer performed more than 5 iterations. Validation truncated at 5 iterations for performance. This is expected behavior.

## Related Tools

- **PhotoStats**: Analyze photo collections for orphaned files and sidecar issues
- **Photo Pairing**: Group related files by filename patterns and track camera usage

## Next Steps

- Learn about [configuration options](configuration.md)
- See the [Agent Installation Guide](agent-installation.md) for agent setup
- See the main [README](../README.md) for project overview

## License

GNU Affero General Public License v3.0 (AGPL-3.0)
