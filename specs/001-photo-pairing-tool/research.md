# Research: Photo Pairing Tool

**Feature**: Photo Pairing Tool
**Date**: 2025-12-23
**Phase**: 0 - Research & Design Decisions

## Overview

This document captures research findings and design decisions for implementing the Photo Pairing Tool. The tool analyzes photo filenames, extracts metadata from naming patterns, and generates analytics reports.

## Key Design Decisions

### 1. Filename Parsing Strategy

**Decision**: Use regular expressions for initial validation, then string operations for property extraction

**Rationale**:
- Filename validation pattern is well-defined and complex (4 uppercase alphanumeric + 4 digits + optional dash-prefixed properties)
- Regex provides clear, testable validation in a single pattern
- String operations (split, startswith, isdigit) are simpler and more maintainable for property extraction
- Avoids over-engineering with full parser when simple string manipulation suffices

**Implementation Approach**:
```python
# Validation regex pattern
VALID_FILENAME_PATTERN = r'^[A-Z0-9]{4}(0[0-9]{3}|[1-9][0-9]{3})(-[^-]+)*\.[a-z0-9]+$'

# Then use string operations for extraction
parts = filename.split('-')
camera_id = parts[0][:4]
counter = parts[0][4:8]
properties = parts[1:] if len(parts) > 1 else []
```

**Alternatives Considered**:
- Full regex with capture groups: More complex, harder to maintain, overkill for this use case
- Pure string operations: Harder to validate complex patterns, more error-prone
- Parser library (pyparsing): Unnecessary dependency for simple filename structure

### 2. HTML Report Generation

**Decision**: Direct HTML string building using Python's string formatting (no template engine)

**Rationale**:
- Existing PhotoStats tool uses direct HTML generation successfully
- Consistency with codebase patterns
- No additional dependencies (YAGNI principle)
- Report structure is relatively simple (tables, basic charts)
- Maintainability is good with well-organized functions

**Implementation Approach**:
- Separate functions for each report section (header, summary, tables, charts)
- Use f-strings for readability
- Embed minimal JavaScript for interactivity (if needed)
- Follow PhotoStats HTML generation patterns

**Alternatives Considered**:
- Jinja2 templates: Adds dependency, overhead for simple reports, breaks YAGNI principle
- HTML generation library (dominate, htmlBuilder): Additional dependency, learning curve, no clear benefit
- JSON output + separate viewer: Complicates user workflow, requires two-step process

### 3. Interactive User Prompts

**Decision**: Use Python's built-in `input()` function with clear prompts and validation

**Rationale**:
- Simple and straightforward - no dependencies
- Sufficient for the tool's needs (text input for camera names and descriptions)
- Existing PhotoAdminConfig uses this approach for config creation prompts
- Cross-platform compatibility

**Implementation Approach**:
```python
def prompt_camera_info(camera_id):
    print(f"\nFound new camera ID: {camera_id}")
    name = input(f"  Camera name: ").strip()
    serial = input(f"  Serial number (optional, press Enter to skip): ").strip()
    return {"name": name, "serial_number": serial}
```

**User Experience Considerations**:
- Clear prompt messages with examples
- Allow skipping optional fields (serial number)
- Validate input before saving (non-empty camera names)
- Provide feedback after saving ("✓ Camera mapping saved")
- Allow Ctrl+C to cancel gracefully

**Alternatives Considered**:
- Rich/Click library for fancy prompts: Adds dependencies, unnecessary for simple text input
- GUI dialog: Breaks CLI workflow, adds significant complexity
- Config file editing: Less user-friendly, requires users to understand YAML syntax

### 4. Configuration Updates

**Decision**: Load config, modify in-memory, write back using PyYAML's safe_dump

**Rationale**:
- PyYAML already a dependency
- Preserves YAML structure and comments (when using safe_dump correctly)
- Atomic write approach minimizes corruption risk
- Simple and direct - no additional libraries

**Implementation Approach**:
```python
def update_config_with_camera(camera_id, name, serial_number):
    config_path = self.config.get_config_path()  # Add to PhotoAdminConfig

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    if 'camera_mappings' not in config:
        config['camera_mappings'] = {}

    # Store as list for future compatibility (multiple cameras per ID)
    # v1.0: Create single-entry list
    # Future: Can append additional cameras to list
    config['camera_mappings'][camera_id] = [{
        'name': name,
        'serial_number': serial_number
    }]

    with open(config_path, 'w') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
```

**Future Enhancement Notes**:
- Config structure supports multiple cameras per ID (stored as list)
- v1.0 always creates single-entry list and uses first entry (index 0)
- Future versions can add distinguishing logic based on processing methods, EXIF data, etc.

**Safety Considerations**:
- Validate config structure before saving
- Handle YAML parsing errors gracefully
- Consider atomic write (write to temp file, then rename) for safety
- Reload config after updates to ensure consistency

**Alternatives Considered**:
- ruamel.yaml for comment preservation: Adds dependency, might be overkill for auto-generated sections
- Manual YAML file editing: Error-prone, fragile
- Separate config file for pairing tool: Breaks constitution requirement for shared config

### 5. File Scanning Approach

**Decision**: Use Path.rglob() for recursive file discovery, filter by extension

**Rationale**:
- Built-in pathlib is cross-platform and reliable
- Existing PhotoStats uses similar approach
- Handles symlinks appropriately
- Efficient for typical photo folder sizes (thousands of files)

**Implementation Approach**:
```python
def scan_folder(folder_path, extensions):
    folder = Path(folder_path)
    for ext in extensions:
        for file_path in folder.rglob(f'*{ext}'):
            if file_path.is_file():
                yield file_path
```

**Performance Considerations**:
- For 10,000 files: negligible scan time (<1 second)
- Memory efficient with generator pattern
- No need for parallel scanning at this scale

**Alternatives Considered**:
- os.walk(): More complex, less Pythonic than pathlib
- Parallel scanning: Premature optimization for this use case
- External tools (find command): Platform-dependent, adds complexity

### 6. Data Structures

**Decision**: Use dictionaries and lists for grouping, minimal custom classes

**Rationale**:
- Python dictionaries are fast for lookups (O(1) for group membership)
- Simple to serialize to JSON for potential future features
- Follows YAGNI - no need for complex OOP hierarchy
- Easy to test and debug

**Core Data Structures**:
```python
groups = {
    'AB3D0001': {
        'files': ['AB3D0001.dng', 'AB3D0001-HDR.tiff'],
        'camera_id': 'AB3D',
        'counter': '0001',
        'properties': {'HDR'},
        'separate_images': set()  # Numeric suffixes
    }
}

invalid_files = [
    {'filename': 'abc0001.dng', 'reason': 'Camera ID must be uppercase'},
    {'filename': 'AB3D0000.dng', 'reason': 'Counter must be 0001-9999'}
]

camera_usage = {
    'AB3D': {'name': 'Canon EOS R5', 'count': 150},
    'XYZW': {'name': 'Sony A7IV', 'count': 75}
}
```

**Alternatives Considered**:
- Custom classes (ImageGroup, Camera, etc.): Adds verbosity without clear benefit
- Dataclasses: Overkill for simple dictionaries
- Named tuples: Less flexible for dynamic data

### 7. HTML Charts/Visualizations

**Decision**: Use embedded Chart.js via CDN for simple interactive charts

**Rationale**:
- Lightweight, well-documented, no build step
- PhotoStats may already use charts (verify implementation)
- CDN = no local dependencies
- Good balance of features vs complexity

**Chart Types**:
- Bar chart: Images per camera
- Bar chart: Images per processing method
- Summary statistics: Total groups, avg files per group

**Alternatives Considered**:
- matplotlib/plotly: Generate static images, less interactive, adds dependencies
- D3.js: More complex, higher learning curve
- No charts: Less user-friendly, harder to see patterns

### 8. ImageGroup Persistence & Caching

**Decision**: Persist ImageGroup structure to JSON file in analyzed folder with hash-based validation

**Rationale**:
- ImageGroup data is expensive to compute (file scanning, parsing, grouping)
- Structure is independent of config (camera names, method descriptions)
- Enables instant report regeneration when only config changes
- Users often tweak camera/method names after initial analysis
- Hash validation ensures data integrity and freshness

**Implementation Approach**:
```python
import json
import hashlib
from pathlib import Path

def calculate_file_list_hash(folder_path, extensions):
    """Calculate SHA256 hash of sorted file paths."""
    files = sorted([str(f.relative_to(folder_path))
                   for ext in extensions
                   for f in folder_path.rglob(f'*{ext}')])
    file_list_str = '\n'.join(files)
    return hashlib.sha256(file_list_str.encode()).hexdigest()

def calculate_imagegroups_hash(imagegroups):
    """Calculate SHA256 hash of ImageGroup structure."""
    # Convert to JSON (excluding metadata), sort keys for consistency
    data_str = json.dumps(imagegroups, sort_keys=True, default=str)
    return hashlib.sha256(data_str.encode()).hexdigest()

def save_cache(folder_path, imagegroups, invalid_files):
    """Save ImageGroup structure to .photo_pairing_imagegroups"""
    cache_path = folder_path / '.photo_pairing_imagegroups'

    cache_data = {
        'version': '1.0',
        'created_at': datetime.utcnow().isoformat() + 'Z',
        'folder_path': str(folder_path.absolute()),
        'tool_version': '1.0.0',
        'metadata': {
            'file_list_hash': calculate_file_list_hash(...),
            'imagegroups_hash': calculate_imagegroups_hash(imagegroups),
            'total_files': sum(...),
            'total_groups': len(imagegroups),
            'total_images': sum(len(g['separate_images']) for g in imagegroups),
            'total_invalid_files': len(invalid_files)
        },
        'imagegroups': imagegroups,
        'invalid_files': invalid_files
    }

    with open(cache_path, 'w') as f:
        json.dump(cache_data, f, indent=2, default=str)
```

**Cache Validation Flow**:
1. Check if `.photo_pairing_imagegroups` exists in target folder
2. Load and parse JSON
3. Calculate current file_list_hash from folder
4. Compare with cached file_list_hash
5. Calculate imagegroups_hash from loaded data
6. Compare with cached imagegroups_hash
7. If both match: use cache, skip analysis
8. If either doesn't match: prompt user for action

**User Prompt on Mismatch**:
```
⚠ Found cached analysis data
⚠ Changes detected:
  - Folder content: [CHANGED/OK]
  - Cache file: [EDITED/OK]

Choose an option:
  (a) Use cached data anyway (fast, ignores changes)
  (b) Re-analyze folder (slow, reflects current state)
Your choice [a/b]:
```

**Format Choice**: JSON over YAML
- Simpler to parse in Python (stdlib `json` module)
- Better for programmatic access (not meant for manual editing)
- Slightly more compact for large datasets
- Standard for data interchange

**Alternatives Considered**:
- YAML: More human-readable, but adds dependency and parsing overhead
- Pickle: Not human-readable, version-incompatible, security concerns
- SQLite: Overkill for simple key-value storage, adds dependency
- No caching: Simple but wasteful - re-scan every time even for config-only changes

## Open Questions (Resolved)

All technical questions resolved through design decisions above. No blockers for implementation.

## Next Steps

Proceed to Phase 1:
- Create data-model.md with entity definitions
- Create filename-validation contract specification
- Create quickstart.md for user guidance
- Update agent context with technology decisions
