# photo-admin

Photo Administration toolbox - Python utility for analyzing photo collections

## Features

- **File Scanning**: Recursively scans folders for DNG, TIFF, CR3, and XMP files
- **Statistics Collection**: Counts files by type and calculates storage usage
- **File Pairing Analysis**: Identifies orphaned images and XMP metadata files
- **XMP Metadata Extraction**: Parses and analyzes metadata from XMP sidecar files
- **HTML Reports**: Generates beautiful, interactive HTML reports with charts

## Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

Note: `python-xmp-toolkit` may require additional system libraries. On macOS with Homebrew:

```bash
brew install exempi
```

## Usage

Basic usage:

```bash
python photo_stats.py /path/to/your/photos
```

Specify custom output file:

```bash
python photo_stats.py /path/to/your/photos my_report.html
```

The tool will:
1. Scan the specified folder recursively
2. Collect statistics on all photo files (DNG, TIFF, CR3, XMP)
3. Analyze file pairing (images with/without XMP files)
4. Extract and analyze XMP metadata
5. Generate an HTML report with interactive charts

## Output

The tool generates an HTML report containing:

- **Summary Statistics**: Total files, total size, paired files, orphaned files
- **File Type Distribution Chart**: Visual breakdown of file counts
- **Storage Distribution Chart**: Storage usage by file type
- **Detailed File Type Table**: Counts, sizes, and averages per type
- **Pairing Status**: Lists of orphaned images and XMP files
- **XMP Metadata Analysis**: Common metadata fields and sample values

## Example Output

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

## Supported File Types

- **DNG** (Digital Negative)
- **TIFF** (Tagged Image File Format)
- **CR3** (Canon Raw 3)
- **XMP** (Extensible Metadata Platform)
