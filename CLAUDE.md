# photo-admin Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-25

## Project Overview

Photo Administration toolbox - Python utilities for analyzing photo collections.

### Tools

1. **PhotoStats** - Analyze photo collections for orphaned files and sidecar issues
2. **Photo Pairing Tool** - Analyze filename patterns, group files, track camera usage

## Active Technologies
- Python 3.10+ (required for match/case syntax and modern type hinting) (003-pipeline-validation)

- **Python 3.10+**
- **PyYAML** (>=6.0) - Configuration file handling
- **Jinja2** (>=3.1.0) - HTML template rendering
- **pytest** - Testing framework with 109 comprehensive tests
- **Chart.js** - HTML report visualizations (via CDN)

## Project Structure

```text
photo-admin/
├── photo_stats.py              # PhotoStats tool
├── photo_pairing.py            # Photo Pairing tool
├── utils/                      # Shared utilities
│   ├── config_manager.py      # PhotoAdminConfig class
│   └── filename_parser.py     # FilenameParser class
├── config/
│   ├── template-config.yaml   # Configuration template
│   └── config.yaml            # User configuration (gitignored)
├── docs/                      # Documentation
│   ├── installation.md
│   ├── configuration.md
│   ├── photostats.md
│   └── photo-pairing.md
├── specs/                     # Design specifications
│   └── 001-photo-pairing-tool/
├── tests/                     # Test suites
│   ├── test_photo_stats.py    # 47 tests
│   └── test_photo_pairing.py  # 40 tests
└── requirements.txt           # Python dependencies
```

## Commands

### Running Tools

```bash
# PhotoStats - analyze photo collections
python3 photo_stats.py /path/to/photos

# Photo Pairing - analyze filename patterns
python3 photo_pairing.py /path/to/photos
```

### Testing

```bash
# Run all tests
python3 -m pytest tests/

# Run specific tool tests
python3 -m pytest tests/test_photo_stats.py -v
python3 -m pytest tests/test_photo_pairing.py -v

# Run with coverage
python3 -m pytest tests/ --cov=photo_pairing --cov=utils --cov-report=term-missing
```

### Code Quality

```bash
# Run linter (if ruff is installed)
ruff check .

# Format code (if black is installed)
black .
```

## Code Style

- **Python 3.10+**: Follow PEP 8 conventions
- **Docstrings**: All functions should have clear docstrings with Args/Returns
- **Type hints**: Use where beneficial for clarity
- **Testing**: Write tests alongside implementation (flexible TDD)

## Architecture Principles (Constitution)

### 1. Independent CLI Tools
- Each tool is a standalone Python script at repository root
- Tools can run independently without requiring other tools
- Use shared infrastructure (PhotoAdminConfig, utils/) but remain decoupled

### 2. Testing & Quality
- Comprehensive test coverage (target >80% for core logic)
- pytest framework with fixtures in conftest.py
- Both unit tests and integration tests
- Tests can be written alongside implementation (flexible approach)

### 3. User-Centric Design
- Interactive HTML reports with visualizations
- Clear, actionable error messages
- Progress indicators for long operations
- Simple, focused implementations (YAGNI principle)

### 4. Shared Infrastructure
- **PhotoAdminConfig**: Shared configuration management
- **Utils**: Reusable utility classes (FilenameParser, etc.)
- Standard config schema with extensible design
- Consistent file naming conventions

### 5. Simplicity
- Direct implementations without over-engineering
- No premature abstractions
- Minimal dependencies (PyYAML, Jinja2 for templates)
- Straightforward data structures
- Industry-standard tools (Jinja2 for templating)

## Configuration

### Config File Locations (Priority Order)

1. `./config/config.yaml` (current directory)
2. `./config.yaml` (current directory)
3. `~/.photo_stats_config.yaml` (home directory)
4. `<script-dir>/config/config.yaml` (installation directory)

### Config Schema

```yaml
photo_extensions:
  - .dng
  - .cr3
  - .tiff

metadata_extensions:
  - .xmp

require_sidecar:
  - .cr3

camera_mappings:
  AB3D:
    - name: Canon EOS R5
      serial_number: "12345"

processing_methods:
  HDR: High Dynamic Range
  BW: Black and White
```

## Shared Utilities

### PhotoAdminConfig (utils/config_manager.py)

Manages configuration loading and interactive prompts:

```python
from utils.config_manager import PhotoAdminConfig

config = PhotoAdminConfig()
# Or with explicit path:
config = PhotoAdminConfig(config_path='/path/to/config.yaml')

# Access configuration
photo_exts = config.photo_extensions
camera_map = config.camera_mappings

# Interactive prompts (auto-saves to config)
camera_info = config.ensure_camera_mapping('AB3D')
method_desc = config.ensure_processing_method('HDR')
```

### FilenameParser (utils/filename_parser.py)

Validates and parses photo filenames:

```python
from utils.filename_parser import FilenameParser

# Validate filename
is_valid, error = FilenameParser.validate_filename('AB3D0001-HDR.dng')

# Parse filename
parsed = FilenameParser.parse_filename('AB3D0001-HDR.dng')
# Returns: {'camera_id': 'AB3D', 'counter': '0001',
#           'properties': ['HDR'], 'extension': '.dng'}

# Detect property type
prop_type = FilenameParser.detect_property_type('2')  # 'separate_image'
prop_type = FilenameParser.detect_property_type('HDR')  # 'processing_method'
```

## Recent Changes
- 003-pipeline-validation: Added Python 3.10+ (required for match/case syntax and modern type hinting)

### HTML Report Consistency & Tool Improvements (2025-12-25)
- ✅ Feature 002: Complete implementation (56 tasks across 6 phases)
- ✅ **Centralized Jinja2 templating** for consistent HTML reports
  - Created templates/base.html.j2 with shared styling and Chart.js theme
  - Tool-specific templates extend base for PhotoStats and Photo Pairing
  - Removed 640+ lines of duplicate HTML generation code
  - Migrated PhotoStats from manual argv parsing to argparse
  - Enhanced Photo Pairing help with examples and workflow
  - Both tools support --help and -h flags
  - User-friendly "Operation interrupted by user" message
  - Exit code 130 (standard for SIGINT)
  - Atomic file writes prevent partial reports
  - Shutdown checks in scan loops and before report generation
  - PhotoStats: photo_stats_report_YYYY-MM-DD_HH-MM-SS.html
  - Photo Pairing: photo_pairing_report_YYYY-MM-DD_HH-MM-SS.html
  - Report renderer tests (12): template rendering, visual consistency
  - Help text tests (6): --help/-h flag validation
  - Signal handling tests (7): CTRL+C graceful interruption

### Photo Pairing Tool (2025-12-25)

### Code Refactoring (2025-12-24)

## Testing Guidelines

### Test Organization

- **Fixtures**: Define reusable test data in fixtures
- **Test Classes**: Group related tests by functionality
- **Integration Tests**: Test complete workflows end-to-end
- **Mocking**: Use monkeypatch for user input, file I/O, etc.

### Coverage Targets

- Core business logic: >80%
- Utility functions: >85%
- Overall: >65% (accounts for CLI code)

### Example Test Structure

```python
import pytest
from utils.filename_parser import FilenameParser

class TestFilenameValidation:
    """Tests for filename validation"""

    def test_valid_filename(self):
        is_valid, error = FilenameParser.validate_filename('AB3D0001.dng')
        assert is_valid
        assert error is None

    def test_invalid_counter(self):
        is_valid, error = FilenameParser.validate_filename('AB3D0000.dng')
        assert not is_valid
        assert 'Counter cannot be 0000' in error
```

## Documentation Standards

### Code Documentation

- Module-level docstrings explaining purpose
- Function docstrings with Args, Returns, and Raises
- Inline comments for complex logic only

### User Documentation

- Installation guide (docs/installation.md)
- Configuration guide (docs/configuration.md)
- Tool-specific guides (docs/photostats.md, docs/photo-pairing.md)
- README.md with quick start and overview

### Tool Help Output

- Include usage examples in `--help`
- Show expected workflow
- Provide sample commands

## License

GNU Affero General Public License v3.0 (AGPL-3.0)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
