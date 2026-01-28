# PhotoStats Tool

> **Note**: The standalone `photo_stats.py` CLI script has been removed. PhotoStats analysis is now available exclusively through the ShutterSense agent. See the usage examples below.

PhotoStats analyzes photo collections, providing detailed statistics and reports about your photo library.

## Features

- **Configurable File Types**: Support for customizable photo and metadata file extensions via YAML configuration
- **File Scanning**: Recursively scans folders for configured photo and XMP files
- **Statistics Collection**: Counts files by type and calculates storage usage
- **File Pairing Analysis**: Identifies orphaned images and XMP metadata files
- **XMP Metadata Extraction**: Parses and analyzes metadata from XMP sidecar files
- **HTML Reports**: Generates interactive HTML reports with charts

## Usage

### Test a Local Path

Validate a directory and run PhotoStats analysis before creating a collection:

```bash
shuttersense-agent test /path/to/photos --tool photostats
```

This will:
1. Validate the path is accessible
2. Scan the folder recursively for configured photo and metadata files
3. Collect statistics, analyze file pairing, and extract XMP metadata
4. Display a summary of results
5. Cache results for 24 hours

### Save an HTML Report

```bash
shuttersense-agent test /path/to/photos --tool photostats --output report.html
```

### Run Against a Registered Collection

```bash
# Online mode (uploads results to server)
shuttersense-agent run <collection-guid> --tool photostats

# Offline mode (saves results locally for later sync)
shuttersense-agent run <collection-guid> --tool photostats --offline

# With HTML report output
shuttersense-agent run <collection-guid> --tool photostats --output report.html
```

### Sync Offline Results

```bash
# Preview pending results
shuttersense-agent sync --dry-run

# Upload all pending results
shuttersense-agent sync
```

## What PhotoStats Analyzes

1. **File Type Distribution**: Counts how many files of each type exist
2. **Storage Analysis**: Calculates total storage used by each file type
3. **Pairing Analysis**: Identifies which images have corresponding XMP sidecars and which don't
4. **Orphan Detection**: Finds XMP files without matching images and images without required sidecars
5. **Metadata Extraction**: Parses XMP files to extract embedded metadata

## HTML Report Contents

The generated HTML report contains:

- **Summary Statistics**: Total images, total size, orphaned images/sidecars counts
- **Image Type Distribution Chart**: Visual breakdown of image file counts
- **Storage Distribution Chart**: Storage usage by image type
- **Pairing Status**: Lists of orphaned images and orphaned XMP sidecar files

## Understanding the Results

### Paired Files
Images that have matching XMP sidecar files (e.g., `IMG_001.CR3` paired with `IMG_001.xmp`).

### Orphaned Images
Images that require XMP sidecars (based on your configuration's `require_sidecar` setting) but don't have one. This might indicate missing metadata files, unprocessed files, or potential data loss.

### Orphaned XMP Files
XMP sidecar files that don't have a matching image file. This might indicate deleted images with retained metadata, naming mismatches, or files that need cleanup.

## Tips

- **Large Collections**: For very large photo collections, the scan may take several minutes. The tool provides progress updates.
- **Network Drives**: Scanning network drives will be slower than local drives.
- **Configuration**: Adjust your configuration file to match your specific workflow and file types.
- **Regular Checks**: Run PhotoStats periodically to ensure your photo collection integrity.

## Next Steps

- Learn about [configuration options](configuration.md)
- See the [Installation Guide](installation.md) for setup
- See the [Agent Installation Guide](agent-installation.md) for agent setup
