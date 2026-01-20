# Analysis Modules

## Overview

The shared analysis modules live in `agent/src/analysis/` and provide tool-specific logic that works with `FileInfo` objects.

## Module Structure

```
agent/src/analysis/
├── __init__.py
├── photo_pairing_analyzer.py    # build_imagegroups(), calculate_analytics()
├── photostats_analyzer.py       # analyze_pairing(), calculate_stats()
└── pipeline_analyzer.py         # run_pipeline_validation()
```

## photo_pairing_analyzer.py

### Functions

#### `build_imagegroups(files: List[FileInfo]) -> Dict[str, Any]`

Core Photo Pairing algorithm. Builds ImageGroup structure from file list.

**Input:** List of FileInfo objects (filtered to photo extensions)

**Output:**
```python
{
    'imagegroups': [
        {
            'group_id': 'AB3D0001',
            'camera_id': 'AB3D',
            'counter': '0001',
            'separate_images': {
                # Base image (no numeric suffix) with HDR processing applied
                '': {'files': ['AB3D0001.dng', 'AB3D0001-HDR.dng'], 'properties': ['HDR']},
                # Separate image 2 (numeric suffix identifies separate capture)
                '2': {'files': ['AB3D0001-2.dng', 'AB3D0001-2-BW.dng'], 'properties': ['BW']}
            }
        },
        ...
    ],
    'invalid_files': [
        {'filename': 'bad_name.dng', 'path': 'folder/bad_name.dng', 'reason': 'Invalid pattern'}
    ]
}
```

**Key distinction:**
- **Separate image suffix**: ALL NUMERIC (e.g., "2", "3") - identifies different captures in the same group
- **Processing method suffix**: NOT all numeric (e.g., "HDR", "BW") - identifies processing applied to an image

So `AB3D0001-HDR.dng` belongs to separate_image `''` (base) with property `HDR`, while `AB3D0001-2.dng` belongs to separate_image `'2'`.
```

**Algorithm:**
1. For each file, validate filename using `FilenameParser.validate_filename()`
2. Parse valid filenames using `FilenameParser.parse_filename()`
3. Group by `camera_id + counter` (e.g., "AB3D0001")
4. For each file's properties (suffixes after counter):
   - First ALL-NUMERIC suffix becomes the `separate_image_id` (identifies different captures)
   - All other suffixes are `processing_methods` (identify edits/processing)
5. Build nested structure: ImageGroup > separate_images > files + properties

**Example parsing:**
- `AB3D0001.dng` -> separate_image='', properties=[]
- `AB3D0001-HDR.dng` -> separate_image='', properties=['HDR']
- `AB3D0001-2.dng` -> separate_image='2', properties=[]
- `AB3D0001-2-BW.dng` -> separate_image='2', properties=['BW']
- `AB3D0001-HDR-2.dng` -> separate_image='2', properties=['HDR'] (numeric is always the separate_image identifier)

#### `calculate_analytics(imagegroups: List[Dict], config: Dict) -> Dict[str, Any]`

Calculate analytics from imagegroups with config-based label resolution.

**Input:**
- `imagegroups`: List of ImageGroup dicts
- `config`: Config with `camera_mappings` and `processing_methods`

**Output:**
```python
{
    'camera_usage': {'Canon EOS R5': 150, 'Sony A7R IV': 36},  # Resolved names
    'method_usage': {'High Dynamic Range': 12, 'Black and White': 5},  # Resolved descriptions
    'image_count': 186,
    'group_count': 186,
}
```

---

## photostats_analyzer.py

### Functions

#### `calculate_stats(files, photo_extensions, metadata_extensions) -> Dict`

Calculate file counts and sizes by extension.

**Input:**
- `files`: List of FileInfo objects
- `photo_extensions`: Set like `{'.dng', '.cr3'}`
- `metadata_extensions`: Set like `{'.xmp'}`

**Output:**
```python
{
    'file_counts': {'.dng': 150, '.xmp': 150, '.cr3': 36},
    'file_sizes': {'.dng': [size1, size2, ...], '.cr3': [...]},
    'total_files': 336,
    'total_size': 85899345920  # bytes
}
```

#### `analyze_pairing(files, photo_extensions, metadata_extensions, require_sidecar) -> Dict`

Analyze file pairing (images with XMP sidecars).

**Input:**
- `files`: List of FileInfo objects
- `photo_extensions`: Set of photo extensions
- `metadata_extensions`: Set like `{'.xmp'}`
- `require_sidecar`: Set of extensions that require sidecars (e.g., `{'.cr3'}`)

**Output:**
```python
{
    'paired_files': [
        {'base_name': 'AB3D0001', 'files': ['AB3D0001.cr3', 'AB3D0001.xmp']}
    ],
    'orphaned_images': ['AB3D0002.cr3'],  # Missing XMP
    'orphaned_xmp': ['AB3D0003.xmp']       # Missing image
}
```

**Algorithm:**
1. Group files by `stem` (base name without extension)
2. For each group, check if has image AND has xmp
3. Classify as paired, orphaned_image, or orphaned_xmp

---

## pipeline_analyzer.py

### Functions

#### `flatten_imagegroups_to_specific_images(imagegroups) -> List[SpecificImage]`

Convert ImageGroups to SpecificImage objects for pipeline validation.

**Input:** List of ImageGroup dicts (from `build_imagegroups()`)

**Output:** List of `SpecificImage` objects (from `utils/pipeline_processor.py`)

Each separate_image in an ImageGroup becomes one SpecificImage:
- `AB3D0001` with suffix `''` (base) -> SpecificImage(base_filename='AB3D0001')
- `AB3D0001` with suffix `'2'` (numeric) -> SpecificImage(base_filename='AB3D0001-2')
- `AB3D0001` with suffix `'3'` (numeric) -> SpecificImage(base_filename='AB3D0001-3')

**Note:** Only numeric suffixes create separate SpecificImages. Processing method suffixes (like 'HDR', 'BW') are stored as properties within a SpecificImage, not as separate images.

#### `add_metadata_files(specific_images, all_files, metadata_extensions) -> None`

Add metadata files (XMP) to SpecificImage objects.

**Side effect:** Modifies `specific_images` in-place by appending matching metadata files.

**Logic:**
1. Build lookup from base_filename to SpecificImage
2. For each file with metadata extension, find matching SpecificImage by stem
3. Append file path to SpecificImage.files

#### `run_pipeline_validation(files, pipeline_config, photo_extensions, metadata_extensions) -> Dict`

Full pipeline validation entry point.

**Input:**
- `files`: List of FileInfo objects
- `pipeline_config`: Pipeline definition dict
- `photo_extensions`: Set of photo extensions
- `metadata_extensions`: Set of metadata extensions

**Output:**
```python
{
    'total_images': 186,
    'total_groups': 186,
    'status_counts': {
        'consistent': 150,
        'consistent_with_warning': 10,
        'partial': 20,
        'inconsistent': 6
    },
    'validation_results': [...],  # List of ValidationResult.to_dict()
    'invalid_files_count': 2
}
```

**Algorithm:**
1. Filter to photo files
2. Call `build_imagegroups()` (shared with Photo Pairing)
3. Call `flatten_imagegroups_to_specific_images()`
4. Call `add_metadata_files()` to include XMP files
5. Call `validate_all_images()` from pipeline_processor
6. Aggregate status counts

---

## Dependencies

### External (from utils/)

- `utils.filename_parser.FilenameParser` - Filename validation and parsing
- `utils.pipeline_processor.*` - Pipeline validation core logic

### Internal (from agent/src/remote/)

- `src.remote.base.FileInfo` - Unified file information

---

## Usage Examples

### Photo Pairing Analysis

```python
from src.analysis import build_imagegroups, calculate_analytics
from src.remote import S3Adapter

# Get files from remote
adapter = S3Adapter(credentials)
files = adapter.list_files_with_metadata("bucket/photos")

# Filter to photos
photo_files = [f for f in files if f.extension in {'.dng', '.cr3'}]

# Build groups
result = build_imagegroups(photo_files)
imagegroups = result['imagegroups']

# Calculate analytics with config
analytics = calculate_analytics(imagegroups, config)
print(f"Images: {analytics['image_count']}, Groups: {analytics['group_count']}")
```

### PhotoStats Analysis

```python
from src.analysis import calculate_stats, analyze_pairing

stats = calculate_stats(files, photo_exts, metadata_exts)
pairing = analyze_pairing(files, photo_exts, metadata_exts, require_sidecar)

results = {**stats, **pairing}
```

### Pipeline Validation

```python
from src.analysis import run_pipeline_validation

results = run_pipeline_validation(
    files=files,
    pipeline_config=pipeline_def,
    photo_extensions={'.dng', '.cr3'},
    metadata_extensions={'.xmp'}
)

print(f"Consistent: {results['status_counts']['consistent']}")
print(f"Partial: {results['status_counts']['partial']}")
```
