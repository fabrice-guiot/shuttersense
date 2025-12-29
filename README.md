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

> **Note:** HTML reports generated before December 2025 used a different styling format. For consistent, improved reports with the latest features, please regenerate reports using the current version of the tools.

## Documentation

- **[Installation Guide](docs/installation.md)** - Detailed installation instructions
- **[Configuration Guide](docs/configuration.md)** - How to configure file types and settings
- **[PhotoStats Tool](docs/photostats.md)** - Complete guide to using the PhotoStats tool
- **[Photo Pairing Tool](docs/photo-pairing.md)** - Complete guide to using the Photo Pairing tool
- **[Pipeline Validation Tool](docs/pipeline-validation.md)** - Complete guide to using the Pipeline Validation tool

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

### Pipeline Validation Tool

The Pipeline Validation Tool validates photo collections against user-defined processing workflows (pipelines). It integrates with the Photo Pairing Tool to analyze file groups and check if images have completed expected processing steps.

**Features:**
- Validate processing workflows against directed graph pipelines
- Assess archival readiness across multiple termination endpoints
- Detect incomplete processing (PARTIAL status)
- Identify extra files (CONSISTENT-WITH-WARNING)
- Interactive HTML reports with validation statistics
- Smart caching for fast re-runs (10,000+ images in <60 seconds)
- Support for complex workflows (loops, branching, pairing nodes)

**Pipeline Concepts:**

Pipelines are directed graphs with 6 node types:
- **Capture**: Camera capture (starting point)
- **File**: Expected files (`.CR3`, `.DNG`, `.TIF`, `.JPG`, `.XMP`)
- **Process**: Processing steps that add suffixes (e.g., `-DxO_DeepPRIME_XD2s`, `-Edit`)
- **Branching**: User decision points (archive now vs. continue processing)
- **Pairing**: Merge multiple images (e.g., HDR from 3 bracketed exposures)
- **Termination**: End states (e.g., "Black Box Archive", "Browsable Archive")

**Validation Statuses:**
- ✅ **CONSISTENT**: All expected files present, no extras (archival ready)
- ⚠️ **CONSISTENT-WITH-WARNING**: All expected files present, extra files exist (archival ready)
- ⏳ **PARTIAL**: Incomplete processing (missing expected files)
- ❌ **INCONSISTENT**: No valid path match or critical files missing

**Quick Usage:**

```bash
# Step 1: Run Photo Pairing Tool first (prerequisite)
python3 photo_pairing.py /path/to/photos

# Step 2: Define pipeline in config/config.yaml (see docs for examples)

# Step 3: Validate against pipeline
python3 pipeline_validation.py /path/to/photos

# Step 4: Review HTML report
open pipeline_validation_report_*.html
```

See the [Pipeline Validation documentation](docs/pipeline-validation.md) for complete usage details and pipeline configuration examples.

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

The test suite includes 160 tests covering:

**PhotoStats (50 tests):**
- Initialization and configuration
- File scanning, filtering, and discovery
- Statistics collection and aggregation
- File pairing analysis (paired/orphaned files)
- XMP metadata extraction
- HTML report generation
- Help text and CLI argument parsing
- Utility functions and edge cases

**Photo Pairing (43 tests):**
- Filename validation and parsing
- Property type detection
- ImageGroup building and file grouping
- Cache operations (save/load/validation)
- Analytics calculations
- HTML report generation
- Help text and CLI argument parsing
- Integration workflows (first-run, cached, stale cache)

**Pipeline Validation (51 tests):**
- CLI interface and argument parsing
- Signal handling (SIGINT/CTRL+C)
- Prerequisite validation (Photo Pairing cache)
- Pipeline configuration loading and validation
- Photo Pairing integration
- Path enumeration (simple, branching, loops)
- File generation from pipeline nodes
- Validation status classification (CONSISTENT/PARTIAL/INCONSISTENT/CONSISTENT-WITH-WARNING)
- Custom pipelines (processing methods, pairing nodes)
- Counter looping with suffixes
- Caching (hash calculation, invalidation, reuse)
- HTML report generation
- Graph visualization and expected file examples
- Pairing node Cartesian product logic
- Process node branching for multiple methods

**Report Rendering (12 tests):**
- ReportContext and dataclass structures
- Template-based HTML generation
- Visual consistency across tools
- Atomic file writes

**Signal Handling (7 tests):**
- SIGINT (CTRL+C) graceful interruption
- Exit code 130 verification
- User-friendly error messages
- Atomic file write patterns

### Project Structure

```
photo-admin/
├── photo_stats.py                  # PhotoStats tool
├── photo_pairing.py                # Photo Pairing tool
├── pipeline_validation.py          # Pipeline Validation tool
├── utils/                          # Shared utilities
│   ├── __init__.py                # Package init
│   ├── config_manager.py          # Configuration management
│   ├── filename_parser.py         # Filename validation and parsing
│   └── report_renderer.py         # Jinja2-based HTML report generation
├── templates/                      # HTML report templates
│   ├── base.html.j2               # Base template with shared styling
│   ├── photo_stats.html.j2        # PhotoStats report template
│   ├── photo_pairing.html.j2      # Photo Pairing report template
│   └── pipeline_validation.html.j2 # Pipeline Validation report template
├── config/
│   ├── template-config.yaml       # Configuration template
│   └── config.yaml                # User configuration (gitignored)
├── docs/                          # Documentation
│   ├── installation.md            # Installation guide
│   ├── configuration.md           # Configuration guide
│   ├── photostats.md              # PhotoStats tool documentation
│   ├── photo-pairing.md           # Photo Pairing tool documentation
│   └── pipeline-validation.md     # Pipeline Validation tool documentation
├── specs/                         # Design specifications
│   ├── 001-photo-pairing-tool/
│   │   ├── constitution.md        # Design principles
│   │   ├── spec.md                # Technical specification
│   │   ├── plan.md                # Implementation plan
│   │   └── tasks.md               # Task breakdown
│   ├── 002-html-report-consistency/
│   │   ├── spec.md                # HTML consistency specification
│   │   ├── plan.md                # Implementation plan
│   │   └── tasks.md               # Task breakdown
│   └── 003-pipeline-validation/
│       ├── spec.md                # Pipeline validation specification
│       ├── plan.md                # Implementation plan
│       ├── tasks.md               # Task breakdown
│       ├── data-model.md          # Data model and structures
│       ├── research.md            # Technical research and decisions
│       ├── quickstart.md          # Quick start guide and examples
│       └── contracts/             # API contracts and test scenarios
├── requirements.txt               # Python dependencies (PyYAML, Jinja2)
├── pytest.ini                    # Pytest configuration
├── .coveragerc                   # Coverage configuration
├── tests/
│   ├── __init__.py                  # Test package
│   ├── conftest.py                  # Test fixtures and configuration
│   ├── test_photo_stats.py          # PhotoStats test suite (50 tests)
│   ├── test_photo_pairing.py        # Photo Pairing test suite (43 tests)
│   ├── test_pipeline_validation.py  # Pipeline Validation test suite (51 tests)
│   ├── test_report_renderer.py      # Report renderer tests (12 tests)
│   └── test_signal_handling.py      # Signal handling tests (7 tests)
├── LICENSE                       # AGPL v3 license
└── README.md                     # This file
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
