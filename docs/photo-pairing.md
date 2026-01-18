# Photo Pairing Tool

The Photo Pairing Tool analyzes photo collections based on filename patterns to group related files, track camera usage, identify processing methods, and generate comprehensive HTML reports with visualizations.

## Overview

### What It Does

The Photo Pairing Tool helps photographers:

- **Group Related Files**: Automatically groups files belonging to the same photo (RAW, edited versions, different formats)
- **Track Camera Usage**: Identifies which cameras were used and how many photos were taken with each
- **Identify Processing Methods**: Detects processing methods applied to photos (HDR, B&W, panoramas, etc.)
- **Detect Invalid Filenames**: Finds files that don't follow the naming convention with specific error reasons
- **Generate Reports**: Creates interactive HTML reports with charts and statistics
- **Cache Analysis**: Saves analysis results for instant report regeneration

### Key Features

- ✅ Filename validation with detailed error messages
- ✅ Interactive prompts for first-run configuration
- ✅ Smart caching for instant report regeneration
- ✅ Case-insensitive file extension handling
- ✅ Support for properties with spaces and underscores
- ✅ Comprehensive HTML reports with Chart.js visualizations
- ✅ Graceful error handling (permissions, corrupted cache, Ctrl+C)

## Filename Convention

Photos must follow this naming pattern:

```
{CAMERA_ID}{COUNTER}[-{PROPERTY}]*{.extension}
```

### Components

- **CAMERA_ID**: Exactly 4 uppercase alphanumeric characters `[A-Z0-9]`
  - Examples: `AB3D`, `XYZW`, `R5M2`

- **COUNTER**: Exactly 4 digits from `0001` to `9999` (`0000` not allowed)
  - Examples: `0001`, `0042`, `1234`, `9999`

- **PROPERTY** (optional): One or more dash-prefixed properties
  - Can contain letters, digits, spaces, and underscores
  - Numeric properties = separate images (e.g., `-2`, `-3`)
  - Alphanumeric properties = processing methods (e.g., `-HDR`, `-BW`)
  - Examples: `-HDR`, `-2`, `-HDR_BW`, `-Focus Stack`

- **Extension**: Case-insensitive file extension
  - Examples: `.dng`, `.DNG`, `.cr3`, `.CR3`, `.tiff`

### Valid Filename Examples

```
AB3D0001.dng                    # Basic photo
XYZW0035-HDR.tiff              # HDR processed
AB3D0042-2.cr3                 # Second image of same scene
R5M21234-HDR-BW.dng            # Multiple processing methods
AB3D0001-Focus Stack.tiff      # Property with spaces
XYZW0001-2-HDR_BW.dng          # Separate image with processing
```

### Invalid Filename Examples

```
ab3d0001.dng                   # Lowercase camera ID
AB3D0000.dng                   # Counter 0000 not allowed
AB3D001.dng                    # Counter too short
AB3D0001-.dng                  # Empty property
AB3D0001--HDR.dng              # Double dash (empty property)
AB3D0001-@#$.dng               # Invalid characters in property
```

## Usage

### Basic Usage

```bash
python3 photo_pairing.py /path/to/photos
```

This will:
1. Scan the folder for photo files (based on config)
2. Validate filenames and group related files
3. Prompt for camera and processing method information (first run)
4. Generate an HTML report with analytics
5. Save cache for fast future analysis

### First Run

On the first run, the tool will prompt you for information about:

1. **Camera IDs**: For each camera ID found (e.g., `AB3D`)
   - Camera name (e.g., "Canon EOS R5")
   - Serial number (optional, press Enter to skip)

2. **Processing Methods**: For each method keyword found (e.g., `HDR`)
   - Description (e.g., "High Dynamic Range")

This information is saved to the config file for future runs.

### Subsequent Runs

On subsequent runs:
- If folder content hasn't changed: Uses cached data for instant report generation
- If folder content changed: Prompts whether to use cache or re-analyze
- Config already has camera/method info: No prompts needed

### Cache Behavior

The tool creates a `.photo_pairing_imagegroups` cache file in the analyzed folder containing:
- ImageGroup structure
- Invalid files list
- Metadata (hashes, timestamps, statistics)

**Cache is used when:**
- Folder content hasn't changed (same files)
- Cache file hasn't been manually edited

**Cache is invalidated when:**
- Files are added/removed
- Cache file is manually edited

**User prompt for stale cache:**
- Option (a): Use cached data anyway (fast, ignores changes)
- Option (b): Re-analyze folder (slow, reflects current state)

## HTML Report

The generated HTML report includes:

### Summary Statistics

- Total Groups
- Total Images
- Total Files
- Avg Files/Group
- Cameras Used
- Processing Methods
- **Invalid Files** (count)

### Camera Usage

- Interactive bar chart (Chart.js)
- Table with: Camera ID, Name, Serial Number, Groups, Images

### Processing Methods

- Interactive bar chart (Chart.js)
- Table with: Method keyword, Description, Image count

### Invalid Files

- Table listing: Filename, Reason
- Only shown if invalid files exist

### Filename Format Requirements

- Complete naming convention documentation
- Examples for each component
- Helps photographers fix invalid filenames

### Report Metadata

- Folder path scanned
- Generation timestamp
- Scan duration (excluding user input time)

## Configuration

The tool uses the shared ShutterSense configuration system.

### Config File Location

The tool searches for `config.yaml` in:
1. `./config/config.yaml` (current directory)
2. `./config.yaml` (current directory)
3. `~/.photo_stats_config.yaml` (home directory)
4. `<script-dir>/config/config.yaml` (installation directory)

### Config File Format

```yaml
photo_extensions:
  - .dng
  - .cr3
  - .tiff
  - .tif
  - .DNG
  - .CR3

metadata_extensions:
  - .xmp

camera_mappings:
  AB3D:
    - name: Canon EOS R5
      serial_number: "12345"
  XYZW:
    - name: Sony A7R5
      serial_number: "67890"

processing_methods:
  HDR: High Dynamic Range
  BW: Black and White
  Pano: Panorama
  Focus Stack: Focus Stacking
```

### First Run Setup

If no config exists, the tool will:
1. Look for `template-config.yaml`
2. Offer to create `config/config.yaml`
3. Copy template and prompt user to customize

## Error Handling

### Graceful Ctrl+C Handling

Pressing Ctrl+C during analysis:
- Displays interrupt message
- Exits cleanly without saving cache
- No corrupted state left behind

### Permission Errors

**Individual file errors**: Warning displayed, file skipped, analysis continues

**Folder-level errors**: Error message displayed, tool exits with helpful message

### Corrupted Cache

- Automatically detected via hash validation
- Cache ignored and regenerated
- User notified of cache corruption

### Cache Write Failures

- Warning displayed if cache can't be saved
- Report still generated successfully
- Next run will perform full analysis

## Examples

### Analyze Photos from Recent Shoot

```bash
python3 photo_pairing.py ~/Photos/2025-01-Shoot
```

### Re-analyze After Adding Files

```bash
# Tool detects changes and prompts:
# (a) Use cached data anyway
# (b) Re-analyze folder
# Choose (b) to see new files in report
```

### Update Camera Names

1. Edit `config/config.yaml` and update camera names
2. Re-run tool on same folder
3. Choose option (a) to use cached analysis
4. Report regenerates instantly with updated names

## Troubleshooting

### "No configuration file found"

**Solution**: Tool will offer to create one from template. Answer 'Y' to create it.

### "Error: Cannot access folder contents"

**Solution**: Check folder permissions. Ensure you have read access to the folder and files.

### "Cache validation failed"

**Cause**: Cache file manually edited or corrupted

**Solution**: Tool will automatically regenerate cache. No action needed.

### Invalid files detected in report

**Solution**: Review the "Invalid Files" table in the HTML report for specific error reasons. Refer to "Filename Format Requirements" section in report to fix filenames.

### Missing camera/method in report

**Cause**: First run hasn't prompted yet, or config doesn't have entry

**Solution**: Delete `.photo_pairing_imagegroups` cache and re-run. Tool will prompt for missing information.

## Performance

### First Run (Full Analysis)

- Scan 1000 files: ~0.5 seconds
- Scan 10000 files: ~3-5 seconds
- Plus time for user prompts (first run only)

### Cached Analysis

- Any number of files: < 2 seconds
- Only limited by config file reload and HTML generation

### Cache File Size

- ~1-2 KB per 100 image groups
- Minimal disk space usage

## Tips and Best Practices

### Organizing Photos

- Use consistent camera IDs across all shoots
- Use descriptive processing method keywords
- Avoid special characters in properties (use spaces or underscores)

### Config Management

- Keep camera mappings up to date
- Use descriptive method descriptions
- Back up your config file

### Report Generation

- Reports are timestamped (won't overwrite previous reports)
- Archive important reports for future reference
- Use cached analysis when updating camera/method descriptions

### Workflow Integration

1. Import photos from camera
2. Rename according to convention
3. Run photo pairing tool
4. Review HTML report
5. Fix any invalid filenames
6. Re-run to verify all files valid

## Advanced Features

### Separate Images

Numeric properties (e.g., `-2`, `-3`) indicate separate images of the same scene:

```
AB3D0001.dng          # Main image
AB3D0001-2.dng        # Second exposure
AB3D0001-3.dng        # Third exposure
AB3D0001-2-HDR.dng    # HDR version of second exposure
```

Each separate image can have its own processing methods.

### Property Deduplication

If the same property appears on multiple files in an image group, it's listed only once:

```
AB3D0001-HDR.dng      # Properties: [HDR]
AB3D0001-HDR.cr3      # Properties: [HDR]
AB3D0001-HDR.tiff     # Properties: [HDR]

Result: Base image with property "HDR" and 3 files
```

### Hash-Based Change Detection

The tool uses SHA256 hashes to detect:
- Folder content changes (files added/removed)
- Cache file manual edits

This ensures cache is only used when truly valid.

## Related Tools

- **PhotoStats**: Analyze photo collections for orphaned files and sidecar issues
- See `docs/photostats.md` for details

## License

Copyright (C) 2024 Fabrice Guiot

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

See LICENSE file for full details.
