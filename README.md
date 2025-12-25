# photo-admin

[![Tests](https://github.com/fabrice-guiot/photo-admin/actions/workflows/test.yml/badge.svg)](https://github.com/fabrice-guiot/photo-admin/actions/workflows/test.yml)

Photo Administration toolbox - Python utility for analyzing photo collections

## Quick Start

```bash
# Clone the repository
git clone https://github.com/fabrice-guiot/photo-admin.git
cd photo-admin

# Install dependencies
pip install -r requirements.txt

# Run PhotoStats (first run will prompt for configuration)
python photo_stats.py /path/to/your/photos
```

## Documentation

- **[Installation Guide](docs/installation.md)** - Detailed installation instructions
- **[Configuration Guide](docs/configuration.md)** - How to configure file types and settings
- **[PhotoStats Tool](docs/photostats.md)** - Complete guide to using the PhotoStats tool
- **[Photo Pairing Tool](docs/photo-pairing.md)** - Complete guide to using the Photo Pairing tool

## Tools

### PhotoStats

PhotoStats analyzes photo collections and generates detailed HTML reports with statistics and charts.

**Features:**
- Configurable file type support for any RAW or image format
- Recursive folder scanning
- File pairing analysis (images with/without XMP sidecars)
- XMP metadata extraction
- Interactive HTML reports with charts

**Quick Usage:**

```bash
python photo_stats.py /path/to/your/photos
```

See the [PhotoStats documentation](docs/photostats.md) for complete usage details.

### Photo Pairing Tool

The Photo Pairing Tool analyzes photo collections based on filename patterns to group related files, track camera usage, and generate comprehensive analytics reports.

**Features:**
- Filename validation with detailed error messages
- Automatic file grouping by 8-character prefix (camera + counter)
- Interactive prompts for camera and processing method information
- Smart caching for instant report regeneration
- Support for separate images and processing method tracking
- Invalid filename detection with specific reasons
- Interactive HTML reports with Chart.js visualizations

**Filename Convention:**

```
{CAMERA_ID}{COUNTER}[-{PROPERTY}]*{.extension}

Examples:
  AB3D0001.dng              # Basic photo
  XYZW0035-HDR.tiff         # HDR processed
  AB3D0001-2-HDR_BW.dng     # Separate image with processing
```

**Quick Usage:**

```bash
python3 photo_pairing.py /path/to/photos
```

The tool will:
1. Scan folder and validate filenames
2. Group related files (same photo, different formats)
3. Prompt for camera/method info (first run only)
4. Generate timestamped HTML report
5. Save cache for fast future analysis

See the [Photo Pairing documentation](docs/photo-pairing.md) for complete usage details.

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

The test suite includes 87+ tests covering:

**PhotoStats (47 tests):**
- Initialization and configuration
- File scanning, filtering, and discovery
- Statistics collection and aggregation
- File pairing analysis (paired/orphaned files)
- XMP metadata extraction
- HTML report generation
- Utility functions and edge cases

**Photo Pairing (40 tests):**
- Filename validation and parsing
- Property type detection
- ImageGroup building and file grouping
- Cache operations (save/load/validation)
- Analytics calculations
- HTML report generation
- Integration workflows (first-run, cached, stale cache)

### Project Structure

```
photo-admin/
├── photo_stats.py              # PhotoStats tool
├── photo_pairing.py            # Photo Pairing tool
├── utils/                      # Shared utilities
│   ├── __init__.py            # Package init
│   ├── config_manager.py      # Configuration management
│   └── filename_parser.py     # Filename validation and parsing
├── config/
│   ├── template-config.yaml   # Configuration template
│   └── config.yaml            # User configuration (gitignored)
├── docs/                      # Documentation
│   ├── installation.md        # Installation guide
│   ├── configuration.md       # Configuration guide
│   ├── photostats.md          # PhotoStats tool documentation
│   └── photo-pairing.md       # Photo Pairing tool documentation
├── specs/                     # Design specifications
│   └── 001-photo-pairing-tool/
│       ├── constitution.md    # Design principles
│       ├── spec.md            # Technical specification
│       ├── plan.md            # Implementation plan
│       └── tasks.md           # Task breakdown
├── requirements.txt           # Python dependencies
├── pytest.ini                # Pytest configuration
├── .coveragerc               # Coverage configuration
├── tests/
│   ├── __init__.py           # Test package
│   ├── conftest.py           # Test fixtures and configuration
│   ├── test_photo_stats.py   # PhotoStats test suite (47 tests)
│   └── test_photo_pairing.py # Photo Pairing test suite (40 tests)
├── LICENSE                   # AGPL v3 license
└── README.md                 # This file
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
