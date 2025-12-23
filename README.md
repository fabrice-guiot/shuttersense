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

The test suite includes 47 tests covering:

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
├── docs/                       # Documentation
│   ├── installation.md         # Installation guide
│   ├── configuration.md        # Configuration guide
│   └── photostats.md           # PhotoStats tool documentation
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
