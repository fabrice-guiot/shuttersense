# Data Model: Photo Pairing Tool

**Feature**: Photo Pairing Tool
**Date**: 2025-12-23
**Phase**: 1 - Data Model Design

## Overview

This document defines the data entities and their relationships for the Photo Pairing Tool. The tool uses simple Python data structures (dictionaries and lists) following the YAGNI principle.

## Core Entities

### ImageGroup

Represents a collection of related files that share the same 8-character filename prefix (camera ID + counter). Files are organized by separate image identifiers.

**Structure**:
```python
{
    'group_id': str,              # 8-character prefix (e.g., 'AB3D0001')
    'camera_id': str,             # First 4 characters (e.g., 'AB3D')
    'counter': str,               # Characters 5-8 (e.g., '0001')
    'separate_images': Dict[str, Dict[str, Any]],  # Image identifier -> {files, properties}
        # Structure per separate image:
        # {
        #     'files': List[Path],      # Files for this specific image
        #     'properties': Set[str]    # Processing methods for this specific image
        # }
}
```

**Example**:
```python
{
    'group_id': 'AB3D0035',
    'camera_id': 'AB3D',
    'counter': '0035',
    'separate_images': {
        '': {                                                  # Base image
            'files': [Path('AB3D0035.dng'), Path('AB3D0035-HDR.tiff')],
            'properties': {'HDR'}                              # HDR from AB3D0035-HDR.tiff
        },
        '2': {                                                 # Separate image #2
            'files': [Path('AB3D0035-2.cr3')],
            'properties': set()                                # No processing methods
        }
    }
}
```

**Key Design Points**:
- Empty string `''` as key represents base image (files without numeric suffix)
- Each separate image can have multiple files (different formats)
- Each separate image tracks its own properties (processing methods applied to files in that image)
- Total images in group = `len(separate_images)` (number of keys)
- Total files in group = `sum(len(img['files']) for img in separate_images.values())`
- Properties are deduplicated within each separate image (not at group level)

**Validation Rules**:
- `camera_id`: Exactly 4 uppercase alphanumeric characters [A-Z0-9]{4}
- `counter`: Exactly 4 digits, range 0001-9999 (0000 invalid)
- `separate_images`: Must contain at least one key (at minimum, base image with empty string key)
- Each separate image entry must have:
  - `files`: Non-empty list with at least one Path
  - `properties`: Set of strings (can be empty). Property names may contain letters, digits, spaces, and underscores
- All-numeric properties (e.g., '2', '123') become separate_images keys, not processing methods

**Analytics Calculations**:
- **Total images in group**: `len(group['separate_images'])`
- **Total files in group**: `sum(len(img['files']) for img in group['separate_images'].values())`
- **Total images across all groups**: `sum(len(g['separate_images']) for g in all_groups)`
- **Total files across all groups**: `sum(sum(len(img['files']) for img in g['separate_images'].values()) for g in all_groups)`
- **Images with specific property** (e.g., HDR): Count separate_images entries where property in their properties set

**Relationships**:
- One-to-one with CameraMapping (via camera_id)
- One-to-many with ProcessingMethod (via properties set)
- Contains one or more separate images, each potentially having multiple files

### CameraMapping

Associates a 4-character camera ID code with human-readable information. Config structure supports multiple cameras per ID for future enhancement.

**Structure (per camera entry)**:
```python
{
    'id': str,                    # 4-character camera ID (e.g., 'AB3D')
    'name': str,                  # Human-readable camera name (required)
    'serial_number': str          # Optional serial number (can be empty string)
}
```

**Storage**: Persisted in YAML config file under `camera_mappings` key

**YAML Structure (Future-Compatible)**:
```yaml
camera_mappings:
  AB3D:
    - name: "Canon EOS R5"
      serial_number: "12345"
    # Future: Multiple cameras can share same ID
    # - name: "Canon EOS R5 Mark II"
    #   serial_number: "67890"
  XYZW:
    - name: "Sony A7IV"
      serial_number: ""  # Optional - empty if not provided
```

**Version 1.0 Behavior**:
- Tool prompts for one camera per ID and creates single-entry list
- When reading config with multiple entries per ID, uses only the first entry (index 0)
- Future versions will add distinguishing logic (processing method compatibility, etc.) to select correct camera

**Validation Rules**:
- `id`: Must match [A-Z0-9]{4} pattern
- `name`: Required, non-empty string after strip()
- `serial_number`: Optional, can be empty string
- List must contain at least one camera entry

**Lifecycle**:
1. Tool discovers new camera ID in filename
2. Prompts user for name and optional serial number
3. Creates single-entry list and saves to config file immediately
4. Used for all future files with that camera ID (v1.0 always uses first entry in list)

### ProcessingMethod

Describes a post-processing technique identified by dash-prefixed keywords in filenames.

**Structure**:
```python
{
    'keyword': str,               # Keyword from filename (e.g., 'HDR', 'property 2')
    'description': str            # User-provided description
}
```

**Storage**: Persisted in YAML config file under `processing_methods` key

**YAML Example**:
```yaml
processing_methods:
  "HDR": "High Dynamic Range processing"
  "BW": "Black and white conversion"
  "PANO": "Panorama stitching"
  "property 2": "Description for property 2"  # Spaces allowed in keywords
  "high_res": "High resolution output"  # Underscores allowed in keywords
  "HDR_BW": "Processing Method HDR_BW"  # Placeholder generated when user provides empty input
```

**Extraction Rules**:
- Keywords start with dash (`-`) in filename
- Terminate at next dash or file extension
- Can contain: alphanumeric (A-Z, a-z, 0-9), spaces, and underscores
- No other special characters allowed
- Case-sensitive
- Empty keywords make filename invalid

**Validation Rules**:
- `keyword`: Non-empty, alphanumeric + spaces + underscores only
- `description`: Mandatory (required field). If user provides empty input, system generates placeholder "Processing Method {keyword}"
- All-numeric keywords (e.g., `-2`, `-123`) are NOT processing methods - they're separate image identifiers

**Lifecycle**:
1. Tool finds dash-prefixed keyword in filename
2. Checks if keyword is all-numeric (skip if true - it's a separate image ID)
3. Checks if mapping exists in config
4. If not, prompts user for description
5. If user provides empty input (presses Enter), generates placeholder "Processing Method {keyword}"
6. Saves description (user-provided or placeholder) to config file
7. Attaches keyword to ImageGroup's properties set for that separate image

### SeparateImage

Identifies distinct images within a group using all-numeric dash-prefixed suffixes. Base images (no numeric suffix) and numbered images are stored separately.

**Concept**: Files like `AB3D0035-2.dng` represent a different image than `AB3D0035.dng`, even though they share the same 8-character base. Each distinct image (base or numbered) can have multiple files.

**Structure** (embedded in ImageGroup):
```python
# Within ImageGroup.separate_images dictionary
'separate_images': {
    '': {                                                      # Base image
        'files': [Path('AB3D0035.dng'), Path('AB3D0035-HDR.tiff')],
        'properties': {'HDR'}
    },
    '2': {                                                     # Separate image #2
        'files': [Path('AB3D0035-2.cr3'), Path('AB3D0035-2-HDR.tiff')],
        'properties': {'HDR'}
    },
    '123': {                                                   # Separate image #123
        'files': [Path('AB3D0035-123.dng')],
        'properties': set()
    }
}
```

**Key Concepts**:
- **Empty string `''` key**: Represents base image (files without numeric identifier)
- **Numeric string keys** (`'2'`, `'123'`, etc.): Represent separate images with explicit identifiers
- Each key's value is a dict with `files` (list of Path objects) and `properties` (set of processing methods)

**Detection Logic**:
- Scan filename for dash-prefixed properties
- First all-numeric property (`property.isdigit() == True`) determines separate image ID
- If no all-numeric property found, file belongs to base image (empty string key)
- Later properties (after numeric ID) are processing methods

**Example Parsing**:
- `AB3D0035.dng` → Base image (`''` key)
- `AB3D0035-HDR.tiff` → Base image (`''` key) with HDR processing
- `AB3D0035-2.dng` → Separate image #2 (`'2'` key)
- `AB3D0035-HDR-2.dng` → Separate image #2 (`'2'` key) with HDR processing
- `AB3D0035-2-HDR.dng` → Separate image #2 (`'2'` key) with HDR processing

**Complete Example Group**:
```python
{
    'group_id': 'AB3D0035',
    'camera_id': 'AB3D',
    'counter': '0035',
    'separate_images': {
        '': {
            'files': [Path('AB3D0035.dng'), Path('AB3D0035-HDR.tiff')],
            'properties': {'HDR'}
        },
        '2': {
            'files': [Path('AB3D0035-2.cr3')],
            'properties': set()
        },
        '3': {
            'files': [Path('AB3D0035-3.dng'), Path('AB3D0035-3.jpg')],
            'properties': set()
        }
    }
}
# Total images: 3 (base, #2, #3)
# Total files: 5
# Images with HDR: 1 (only base image)
```

**Impact on Analytics**:
- Total images in group = `len(separate_images)` (count of keys, including empty string)
- Group with only base image: `{'': {'files': [...], 'properties': set()}}` = 1 image
- Group with base + numbered images: `{'': {...}, '2': {...}, '3': {...}}` = 3 images
- Processing method analytics: Count how many separate_images entries have the property
- Calculation is simplified: just count dictionary keys

### InvalidFile

Tracks files that don't conform to the expected naming convention.

**Structure**:
```python
{
    'filename': str,              # Just the filename, not full path
    'path': Path,                 # Full path for reference
    'reason': str                 # Specific validation failure message
}
```

**Example**:
```python
{
    'filename': 'abc0001.dng',
    'path': Path('/photos/abc0001.dng'),
    'reason': 'Camera ID must be uppercase alphanumeric [A-Z0-9]'
}
```

**Validation Failure Reasons**:
- "Camera ID must be uppercase alphanumeric [A-Z0-9]" - lowercase or special chars
- "Camera ID must be exactly 4 characters" - too short/long
- "Counter must be 4 digits between 0001 and 9999" - invalid counter
- "Counter cannot be 0000" - specifically 0000
- "Empty property name detected" - filename has `--` or ends with `-` before extension
- "Invalid characters in property name" - property contains special chars (not alphanumeric or space)

**Reporting**:
- Count displayed in HTML report
- Table listing all invalid files with reasons
- Helps users identify files to rename

## Analytics Aggregations

### CameraUsage

**Structure**:
```python
{
    'AB3D': {
        'name': 'Canon EOS R5',
        'serial_number': '12345',
        'image_count': 150,       # Total images (including separate images)
        'group_count': 125        # Total groups
    },
    'XYZW': {
        'name': 'Sony A7IV',
        'serial_number': '',
        'image_count': 75,
        'group_count': 70
    }
}
```

**Calculation**:
```python
# For each camera_id:
camera_groups = [g for g in all_groups if g['camera_id'] == camera_id]

# Image count: sum of separate_images keys across all groups for this camera
image_count = sum(len(group['separate_images']) for group in camera_groups)

# Group count: number of groups for this camera
group_count = len(camera_groups)
```

### MethodUsage

**Structure**:
```python
{
    'HDR': {
        'description': 'High Dynamic Range processing',
        'image_count': 45         # Images with this processing method
    },
    'BW': {
        'description': 'Black and white conversion',
        'image_count': 30
    }
}
```

**Calculation**:
```python
# For each processing method (e.g., 'HDR'):
image_count = sum(
    sum(1 for img in group['separate_images'].values() if method in img['properties'])
    for group in all_groups
)
# Counts how many separate_images entries across all groups have this method in their properties
```

### ReportStatistics

**Structure**:
```python
{
    'total_files_scanned': int,
    'total_groups': int,
    'total_images': int,              # Sum of len(separate_images) across all groups
    'total_invalid_files': int,
    'avg_files_per_group': float,
    'max_files_per_group': int,
    'cameras_used': int,              # Unique camera IDs
    'processing_methods_used': int    # Unique processing methods
}
```

**Calculation Formulas**:
```python
# Total groups (simple)
total_groups = len(all_groups)

# Total images (count all separate_images keys across all groups)
total_images = sum(len(group['separate_images']) for group in all_groups)

# Total files (sum all file lists across all groups)
total_files = sum(
    sum(len(img['files']) for img in group['separate_images'].values())
    for group in all_groups
)

# Average files per group
avg_files_per_group = total_files / total_groups if total_groups > 0 else 0

# Max files per group
max_files_per_group = max(
    sum(len(img['files']) for img in group['separate_images'].values())
    for group in all_groups
) if all_groups else 0
```

**Example**:
```python
{
    'total_files_scanned': 500,
    'total_groups': 200,
    'total_images': 225,              # e.g., 200 groups with avg 1.125 images per group
    'total_invalid_files': 5,
    'avg_files_per_group': 2.5,
    'max_files_per_group': 8,
    'cameras_used': 3,
    'processing_methods_used': 5
}
```

## Data Flow

1. **Scanning Phase**:
   - Read folder, discover files with photo extensions
   - Validate each filename against pattern
   - Build ImageGroup dictionary by 8-char prefix
   - Accumulate invalid files list

2. **Configuration Phase**:
   - For each unique camera_id in groups, check CameraMapping
   - For each unique property in groups, check ProcessingMethod
   - Prompt user for missing mappings
   - Save updates to YAML config file

3. **Analytics Phase**:
   - Calculate CameraUsage from groups
   - Calculate MethodUsage from groups
   - Compute ReportStatistics

4. **Reporting Phase**:
   - Generate HTML with all aggregations
   - Include tables and charts for visualizations
   - List invalid files with reasons

## Persistence

### Configuration (YAML)
- **Location**: `./config/config.yaml` or `~/.photo-admin/config.yaml`
- **Managed by**: PhotoAdminConfig class
- **Updated by**: Tool when new cameras/methods discovered
- **Format**: YAML with camera_mappings and processing_methods keys

### ImageGroup Cache (JSON)
- **Location**: `.photo_pairing_imagegroups` in analyzed folder
- **Purpose**: Cache ImageGroup structure to skip re-analysis on unchanged folders
- **Created**: After successful analysis completion (not on Ctrl+C)
- **Format**: JSON with metadata for integrity checking

**Structure**:
```json
{
  "version": "1.0",
  "created_at": "2025-12-23T14:30:45Z",
  "folder_path": "/absolute/path/to/analyzed/folder",
  "tool_version": "1.0.0",
  "metadata": {
    "file_list_hash": "sha256:abc123...",
    "imagegroups_hash": "sha256:def456...",
    "total_files": 500,
    "total_groups": 200,
    "total_images": 225,
    "total_invalid_files": 5
  },
  "imagegroups": [
    {
      "group_id": "AB3D0001",
      "camera_id": "AB3D",
      "counter": "0001",
      "separate_images": {
        "": {
          "files": ["AB3D0001.dng", "AB3D0001-HDR.tiff"],
          "properties": ["HDR"]
        }
      }
    }
  ],
  "invalid_files": [
    {
      "filename": "abc0001.dng",
      "path": "abc0001.dng",
      "reason": "Camera ID must be uppercase alphanumeric [A-Z0-9]"
    }
  ]
}
```

**Hash Calculation**:
- `file_list_hash`: SHA256 of sorted list of relative file paths (all photo extension files in folder)
- `imagegroups_hash`: SHA256 of JSON-serialized imagegroups structure (excluding metadata)

**Cache Validation Workflow**:
1. On tool startup, check if `.photo_pairing_imagegroups` exists in target folder
2. If exists:
   - Load and parse JSON
   - Scan folder and calculate current file_list_hash
   - Calculate current imagegroups_hash from loaded data
   - Compare both hashes with metadata values
3. If both hashes match:
   - Cache is valid, skip analysis
   - Use cached ImageGroup data to generate report
   - User can update camera/method descriptions in config and regenerate report instantly
4. If either hash doesn't match:
   - Cache is stale or manually edited
   - Prompt user:
     - **(a) Use cached data anyway**: Generate report from cached structure (ignores folder changes)
     - **(b) Re-analyze**: Scan folder, rebuild ImageGroup structure, update cache file
5. If file doesn't exist or is corrupted:
   - Perform full analysis
   - Create new cache file on successful completion

**Cache Invalidation Scenarios**:
- File added to folder → file_list_hash changes
- File removed from folder → file_list_hash changes
- File renamed in folder → file_list_hash changes
- User manually edits `.photo_pairing_imagegroups` → imagegroups_hash changes
- None of the above → hashes match, cache valid

**Benefits**:
- Fast report regeneration (no re-scanning) when only config changes (camera names, method descriptions)
- Integrity checking prevents using stale or corrupted data
- User control: choose to use cached data or re-analyze

### Reports (HTML)
- **Location**: Current directory
- **Filename**: `photo_pairing_report_YYYY-MM-DD_HH-MM-SS.html`
- **Content**: Self-contained (embedded CSS/JS via CDN)
- **Generated from**: Either fresh analysis or cached ImageGroup data
