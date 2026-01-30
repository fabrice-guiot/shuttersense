# Photo Pairing Tool

> **Note**: The standalone `photo_pairing.py` CLI script has been removed. Photo Pairing analysis is now available exclusively through the ShutterSense agent. See the usage examples below.

The Photo Pairing Tool analyzes photo collections based on filename patterns to group related files, track camera usage, identify processing methods, and generate comprehensive HTML reports with visualizations.

## Overview

### What It Does

The Photo Pairing Tool helps photographers:

- **Group Related Files**: Automatically groups files belonging to the same photo (RAW, edited versions, different formats)
- **Track Camera Usage**: Identifies which cameras were used and how many photos were taken with each
- **Identify Processing Methods**: Detects processing methods applied to photos (HDR, B&W, panoramas, etc.)
- **Detect Invalid Filenames**: Finds files that don't follow the naming convention with specific error reasons
- **Generate Reports**: Creates interactive HTML reports with charts and statistics

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

### Test a Local Path

```bash
shuttersense-agent test /path/to/photos --tool photo_pairing
```

### Save an HTML Report

```bash
shuttersense-agent test /path/to/photos --tool photo_pairing --output report.html
```

### Run Against a Registered Collection

```bash
# Online mode (uploads results to server)
shuttersense-agent run <collection-guid> --tool photo_pairing

# Offline mode (saves results locally for later sync)
shuttersense-agent run <collection-guid> --tool photo_pairing --offline

# With HTML report output
shuttersense-agent run <collection-guid> --tool photo_pairing --output report.html
```

### Sync Offline Results

```bash
# Preview pending results
shuttersense-agent sync --dry-run

# Upload all pending results
shuttersense-agent sync
```

## HTML Report

The generated HTML report includes:

### Summary Statistics
- Total Groups, Total Images, Total Files
- Avg Files/Group, Cameras Used, Processing Methods
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

## Configuration

The tool uses the shared ShutterSense configuration system. See the [Configuration Guide](configuration.md) for details on setting up:

- `photo_extensions` - File types to scan
- `camera_mappings` - Camera ID to name/serial mappings
- `processing_methods` - Processing method descriptions

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

## Related Tools

- **PhotoStats**: Analyze photo collections for orphaned files and sidecar issues
- **Pipeline Validation**: Validate collections against processing workflows

## Next Steps

- Learn about [configuration options](configuration.md)
- See the [Agent Installation Guide](agent-installation.md) for agent setup
- See the main [README](../README.md) for project overview

## License

Copyright (C) 2024-2026 Fabrice Guiot

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

See LICENSE file for full details.
