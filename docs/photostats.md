# PhotoStats Tool

PhotoStats is a Python utility for analyzing photo collections, providing detailed statistics and reports about your photo library.

## Features

- **Configurable File Types**: Support for customizable photo and metadata file extensions via YAML configuration
- **File Scanning**: Recursively scans folders for configured photo and XMP files
- **Statistics Collection**: Counts files by type and calculates storage usage
- **File Pairing Analysis**: Identifies orphaned images and XMP metadata files
- **XMP Metadata Extraction**: Parses and analyzes metadata from XMP sidecar files
- **HTML Reports**: Generates beautiful, interactive HTML reports with charts

## Prerequisites

Before using PhotoStats, make sure you have:
1. [Installed the tool](installation.md)
2. [Configured the file types](configuration.md) you want to scan

## Usage

### Basic Usage

Scan a folder and generate a report:

```bash
python photo_stats.py /path/to/your/photos
```

This will:
1. Load configuration to determine which file types to scan
2. Scan the specified folder recursively
3. Collect statistics on all configured photo files and metadata files
4. Analyze file pairing (images with/without XMP files)
5. Extract and analyze XMP metadata
6. Generate an HTML report named `photo_stats_report.html` in the current directory

### Custom Output File

Specify a custom output filename:

```bash
python photo_stats.py /path/to/your/photos my_report.html
```

### Custom Configuration File

Use a specific configuration file:

```bash
python photo_stats.py /path/to/your/photos my_report.html config/config.yaml
```

## What PhotoStats Analyzes

The tool performs several types of analysis on your photo collection:

1. **File Type Distribution**: Counts how many files of each type exist
2. **Storage Analysis**: Calculates total storage used by each file type
3. **Pairing Analysis**: Identifies which images have corresponding XMP sidecars and which don't
4. **Orphan Detection**: Finds XMP files without matching images and images without required sidecars
5. **Metadata Extraction**: Parses XMP files to extract embedded metadata

## Output

### Console Output

The tool provides progress information and a summary in the console:

```
Scanning folder: /Users/you/Photos
Found 1234 files
Analyzing file pairing...
Extracting XMP metadata...
Scan completed in 2.45 seconds
Generating HTML report: photo_stats_report.html

==================================================
SUMMARY
==================================================
Total files: 1234
Total size: 45.67 GB
Paired files: 580
Orphaned images: 12
Orphaned XMP: 3

File counts:
  .CR3: 600
  .DNG: 150
  .TIFF: 432
  .XMP: 52

==================================================

✓ HTML report saved to: /path/to/photo_stats_report.html
```

### HTML Report

The generated HTML report contains:

- **Summary Statistics**:
  - Total images (excluding sidecars)
  - Total size
  - Orphaned images count
  - Orphaned sidecars count

- **Image Type Distribution Chart**:
  - Visual breakdown of image file counts
  - Sidecars excluded except orphaned ones

- **Storage Distribution Chart**:
  - Storage usage by image type
  - Combines each image with its paired sidecar size

- **Pairing Status**:
  - Lists of orphaned images (missing required sidecars)
  - Lists of orphaned XMP sidecar files (no matching image)

## Understanding the Results

### Paired Files

Images that have matching XMP sidecar files (e.g., `IMG_001.CR3` paired with `IMG_001.xmp`).

### Orphaned Images

Images that require XMP sidecars (based on your configuration's `require_sidecar` setting) but don't have one. This might indicate:
- Missing metadata files
- Files that haven't been processed yet
- Potential data loss

### Orphaned XMP Files

XMP sidecar files that don't have a matching image file. This might indicate:
- Deleted images but metadata retained
- Naming mismatches
- Files that need cleanup

## Examples

### Scan a photo library

```bash
python photo_stats.py ~/Pictures/2024
```

### Generate a report for a specific project

```bash
python photo_stats.py /Volumes/Photos/Wedding_Project wedding_stats.html
```

### Use a custom configuration for RAW files

```bash
python photo_stats.py ~/Photos/RAW raw_report.html config/raw-only-config.yaml
```

## Tips

- **Large Collections**: For very large photo collections, the scan may take several minutes. The tool provides progress updates.
- **Network Drives**: Scanning network drives will be slower than local drives.
- **Configuration**: Adjust your configuration file to match your specific workflow and file types.
- **Regular Checks**: Run PhotoStats periodically to ensure your photo collection integrity.

## Troubleshooting

### No configuration file found

If you see this message, follow the prompts to create a configuration file from the template, or see the [Configuration Guide](configuration.md).

### No files found

This might mean:
- The folder path is incorrect
- No files match your configured file types
- The folder is empty

Check your configuration and folder path.

### Report not generated

Ensure you have write permissions in the output directory.

## Next Steps

- Learn more about [configuration options](configuration.md)
- Check out the [Installation guide](installation.md) for development setup
- See the main [README](../README.md) for information about running tests
