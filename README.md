# photo-admin

[![Tests](https://github.com/fabrice-guiot/photo-admin/actions/workflows/test.yml/badge.svg)](https://github.com/fabrice-guiot/photo-admin/actions/workflows/test.yml)

Photo Administration toolbox - Python utility for analyzing photo collections

## Features

- **Configurable File Types**: Support for customizable photo and metadata file extensions via YAML configuration
- **File Scanning**: Recursively scans folders for configured photo and XMP files
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

## Usage

Basic usage:

```bash
python photo_stats.py /path/to/your/photos
```

Specify custom output file:

```bash
python photo_stats.py /path/to/your/photos my_report.html
```

Specify a custom configuration file:

```bash
python photo_stats.py /path/to/your/photos my_report.html config/config.yaml
```

The tool will:
1. Load configuration (if available) to determine which file types to scan
2. Scan the specified folder recursively
3. Collect statistics on all configured photo files and metadata files
4. Analyze file pairing (images with/without XMP files)
5. Extract and analyze XMP metadata
6. Generate an HTML report with interactive charts

## Configuration

**Configuration is required** to run this tool. The tool uses a YAML configuration file to specify which file types should be treated as photos and which should have XMP sidecars.

### First-Time Setup

When you run the tool for the first time without a configuration file, it will:

1. **Automatically detect** that no configuration exists
2. **Prompt you** to create one from the template
3. **Create the config file** for you if you accept (just press Enter)

Example:
```
$ python photo_stats.py /path/to/photos

No configuration file found.
Template found at: config/template-config.yaml

Would you like to create a configuration file at: config/config.yaml
Create config file? [Y/n]:

✓ Configuration file created: config/config.yaml

You can now modify this file to customize file type settings for your needs.
The tool will use this configuration for all future runs.
```

### Manual Configuration Setup

You can also manually create your configuration:

```bash
cp config/template-config.yaml config/config.yaml
```

Then edit `config/config.yaml` to customize the file extensions for your needs.

**Note:** The `config/config.yaml` file is ignored by git, so your personal configuration won't be committed.

### Configuration File Locations

The tool will automatically look for configuration files in the following locations (in order):
1. `config/config.yaml` in the current directory
2. `config.yaml` in the current directory
3. `~/.photo_stats_config.yaml` in your home directory
4. `config/config.yaml` in the script directory

You can also explicitly specify a configuration file as the third command-line argument.

### Configuration File Format

The configuration file uses YAML format with three key sections:

1. **photo_extensions**: All file types to scan and count
2. **require_sidecar**: File types that MUST have XMP sidecars (orphaned if missing)
3. **metadata_extensions**: Valid sidecar file extensions

See `config/template-config.yaml` for a complete example:

```yaml
# Photo Statistics Configuration

# File types that should be scanned
photo_extensions:
  - .dng      # DNG files (already contain metadata, no sidecar needed)
  - .tiff     # TIFF files (already contain metadata, no sidecar needed)
  - .tif      # TIFF files (already contain metadata, no sidecar needed)
  - .cr3      # Canon CR3 RAW (requires XMP sidecar)
  - .nef      # Nikon RAW (requires XMP sidecar)
  # Add more formats as needed

# File types that REQUIRE XMP sidecar files
# Only these will be flagged as "orphaned" if missing sidecars
require_sidecar:
  - .cr3
  - .nef
  # Note: DNG and TIFF embed metadata, so they don't need sidecars

# Valid metadata sidecar file extensions
metadata_extensions:
  - .xmp
```

### Understanding File Pairing

**Key Concept**: Not all photo files need XMP sidecars!

- **DNG and TIFF** files embed their metadata internally, so they don't need sidecars
- **RAW formats** (CR3, NEF, ARW, etc.) typically require external XMP files for metadata

The `require_sidecar` setting lets you specify which formats need sidecars in YOUR workflow. Only files listed there will be flagged as "orphaned" when they lack an XMP file.

### Template Configuration

The template file (`config/template-config.yaml`) provides default settings:
- **Photo extensions**: `.dng`, `.tiff`, `.tif`, `.cr3`
- **Require sidecar**: `.cr3` only
- **Metadata extensions**: `.xmp`

You can uncomment additional format options in the template or add your own custom extensions.

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

The tool is configurable and can support any RAW or image format. By default, it supports:

- **DNG** (Digital Negative)
- **TIFF** (Tagged Image File Format)
- **CR3** (Canon Raw 3)
- **XMP** (Extensible Metadata Platform)

Additional formats can be added via the configuration file, including:
- **NEF** (Nikon RAW)
- **ARW** (Sony RAW)
- **ORF** (Olympus RAW)
- **RW2** (Panasonic RAW)
- **PEF** (Pentax RAW)
- **RAF** (Fujifilm RAW)
- **CR2** (Canon RAW, older format)
- **RAW**, **CRW**, and other manufacturer-specific formats

## Development

### Running Tests

This project includes a comprehensive test suite using pytest. To run the tests:

```bash
# Install development dependencies
pip install -r requirements.txt

# Run all tests
python -m pytest tests/

# Run tests with verbose output
python -m pytest tests/ -v

# Run tests with coverage report
pip install pytest-cov
python -m pytest tests/ --cov=photo_stats --cov-report=html

# Run specific test class
python -m pytest tests/test_photo_stats.py::TestFileScanningFunctionality -v

# Run specific test
python -m pytest tests/test_photo_stats.py::TestFileScanningFunctionality::test_scan_valid_folder -v
```

### Test Coverage

The test suite includes 34 tests covering:

- **Initialization**: PhotoStats class instantiation and configuration
- **File Scanning**: Recursive scanning, file filtering, and discovery
- **Statistics Collection**: File counting, size tracking, and aggregation
- **File Pairing Analysis**: Detecting paired and orphaned files
- **XMP Metadata Extraction**: Parsing and extracting metadata from XMP files
- **HTML Report Generation**: Report creation and content validation
- **Utility Functions**: Size formatting and helper methods
- **Edge Cases**: Special characters, large files, unicode, symlinks, etc.

### Project Structure

```
photo-admin/
├── photo_stats.py              # Main application
├── config/
│   ├── template-config.yaml    # Configuration template
│   └── config.yaml             # User configuration (gitignored)
├── requirements.txt            # Python dependencies
├── pytest.ini                 # Pytest configuration
├── .coveragerc                # Coverage configuration
├── tests/
│   ├── __init__.py            # Test package
│   ├── conftest.py            # Test fixtures and configuration
│   └── test_photo_stats.py    # Test suite
├── LICENSE                    # AGPL v3 license
└── README.md                  # This file
```

## License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).

See the [LICENSE](LICENSE) file for details.

### What this means:

- ✅ You can use, modify, and distribute this software freely
- ✅ If you run a modified version on a server, you must make the source code available to users
- ✅ Any derivative works must also be licensed under AGPL v3
- ✅ This ensures the software remains free and open for the community

For more information, visit: https://www.gnu.org/licenses/agpl-3.0.html
