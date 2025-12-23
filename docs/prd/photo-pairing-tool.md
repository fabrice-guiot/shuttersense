# Product Requirements Document (PRD): Photo Pairing Tool

**Tool Name:** `photo_pairing.py`
**Version:** 1.0
**Last Updated:** 2025-12-23

---

## 1. Introduction

### 1.1 Goal

The goal of this tool is to provide a repository-level utility that analyzes image filenames within a folder to pair related files, extract specific properties, and map these properties to analytics dimensions. It is intended to run independently from the existing PhotoStats tool but leverage its configuration functions.

### 1.2 Success Metrics

- Accurate grouping of image files based on the first 8 characters of the filename
- Successful extraction and mapping of Camera IDs and Processing Methods to the configuration file
- Generation of an HTML report with all required metrics
- Seamless and persistent user configuration for new Camera IDs and Processing Methods

---

## 2. Scope

### 2.1 Tool Capabilities

The tool will:
- Analyze image files in a specified folder based on extensions activated in the configuration file
- Parse valid image filenames to extract pairing information, Camera ID, and Processing Methods
- Maintain and update a configuration file with new Camera ID and Processing Method mappings based on user input
- Generate a detailed HTML execution report

### 2.2 Out of Scope

- Analysis or processing of sidecar files (as identified in the config file) - **Version 1.0 will ignore sidecar files entirely**
- Future versions may include sidecar files in groups based on PhotoStats pairing logic
- Any functionality currently provided by the main PhotoStats tool, other than shared configuration functions

---

## 3. Detailed Requirements

### 3.1 Core Logic and Dependencies

- **Configuration:** The tool must utilize the same configuration functions as the current PhotoStats tool via the `PhotoAdminConfig` class from `config_manager.py`
- **Execution:** The tool must be designed to run independently from the current PhotoStats tool

### 3.2 Filename Analysis and Pairing

#### 3.2.1 Valid Filename Convention

A file is considered a "valid image filename" if it adheres to the following structure:

- **Starts with a sequence of exactly 4 characters:**
  - Alphanumeric characters only (A-Z, 0-9)
  - **All uppercase**
  - Example: `AB3D`, `XYZW`, `A1B2`

- **Followed by exactly 4 digits:**
  - Range: `0001` to `9999` (inclusive)
  - `0000` is **NOT valid**
  - Example: `0001`, `0035`, `9999`

**Valid filename examples:**
- `AB3D0001.dng`
- `XYZW0035-HDR.tiff`
- `A1B20123-property1-2.cr3`

**Invalid filename examples:**
- `ab3d0001.dng` (lowercase)
- `AB3D0000.dng` (counter is 0000)
- `ABC0001.dng` (only 3 characters in first group)
- `AB3DE0001.dng` (5 characters in first group)

#### 3.2.2 Invalid Files

- Any file that does not respect the valid filename convention must be tracked in an "invalid image file" list
- A counter for this list must be displayed in the execution report

#### 3.2.3 File Grouping

- Image files with the same first 8 characters (4-character camera ID + 4-digit counter) at the start of their name must be attached to the same group
- This group represents a unique image and its different file formats
- Example: `AB3D0035.dng`, `AB3D0035-HDR.tiff`, `AB3D0035-2.cr3` form a group for image `AB3D0035`

### 3.3 Analytics Dimension Extraction and Configuration

#### 3.3.1 Camera Identification (New Analytics Dimension)

- The first 4 characters of a valid image filename must be extracted and matched to a new analytics dimension: the camera used to take the picture

**Configuration Handling:**
- Every different sequence of 4 characters will be mapped to a Camera identification in the config file
- The mapping includes:
  - `name` (required): Human-readable camera name
  - `serial_number` (optional): Camera serial number
- If a new 4-character sequence is detected that lacks a mapping, the tool must:
  1. Prompt the user for the camera name
  2. Prompt the user for the optional serial number
  3. Add the mapping to the config file for future use

**Configuration Schema:**
```yaml
camera_mappings:
  AB3D:
    name: "Canon EOS R5"
    serial_number: "12345"  # optional
  XYZW:
    name: "Sony A7IV"
    serial_number: ""
```

#### 3.3.2 Processing Methods (New Analytics Dimension)

Properties are found in the rest of the filename, starting with a dash (`-`) and terminating with the next dash or the end of the filename (excluding the file extension).

**Extraction Rules:**
- Properties start with a dash (`-`)
- Property keywords can contain:
  - Alphanumeric characters (A-Z, a-z, 0-9)
  - Spaces
  - **No other special characters**
  - **No dashes** (dashes terminate the property)
- Multiple properties can be found in sequence
  - Example: `AB3D0035-property1-property 2.ext`
- Spaces are allowed within a property identifier
  - Example: `property 2` is valid
- Duplicate properties in the filename must only be attached once to the file
  - Example: `AB3D0035-property1-property1.ext` → only attach `property1` once
- Empty properties make the filename **invalid**
  - Example: `AB3D0035-.ext` is invalid

**Mapping:**
- Any new property detected via this dash-prefix method must be added to a new dimension: the processing method(s)

**Configuration Handling:**
- The keyword for the processing method detected in the filename must be checked for a corresponding description in the config file
- If the mapping does not exist:
  1. Prompt the user to provide a description for the new property
  2. Add the mapping to the config file for future use

**Configuration Schema:**
```yaml
processing_methods:
  "HDR": "High Dynamic Range processing"
  "BW": "Black and white conversion"
  "PANO": "Panorama stitching"
  "property 2": "Description for property 2"
```

**Note:** Keys can include spaces and must be quoted in YAML when they contain spaces.

#### 3.3.3 Separate Image Identification (All-Numeric Suffix)

A special property which starts with a dash (`-`) and whose "name" contains **only digits** identifies separate images within a group.

**Rules:**
- Numeric suffix MUST be preceded by a dash to count as a separate image ID
- These numeric identifiers are NOT processing methods
- They distinguish multiple images within the same group

**Examples:**

1. **Group AB3D0035:**
   - `AB3D0035-someprop.ext` → Image `AB3D0035` with property `someprop`
   - `AB3D0035-someprop-2.ext` → Image `AB3D0035-2` with property `someprop`
   - `AB3D0035-somepropB-3.ext` → Image `AB3D0035-3` with property `somepropB`
   - **Result:** 3 candidate images detected in group AB3D0035

2. **Distinguishing numeric IDs from properties:**
   - `AB3D0035-123.ext` → Image `AB3D0035-123` (numeric = separate image ID)
   - `AB3D0035-HDR.ext` → Image `AB3D0035` with property `HDR` (alphanumeric = processing method)

### 3.4 File Processing Rules

- The tool will analyze a folder and parse the filename for all extensions activated in the config file (`photo_extensions`)
- **Sidecar files** as identified by the extension configured in `metadata_extensions` should **NOT be analyzed** in version 1.0
  - Future versions will include sidecar files in groups based on PhotoStats pairing logic
- Only files with extensions in `photo_extensions` are processed

---

## 4. Reporting

The tool must produce an HTML report containing the following information:

### 4.1 Group Metrics
- Number of groups detected
- Average number of files per group
- Maximum number of files per group

### 4.2 Image and File Counts
- **Total number of images detected:**
  - Calculated by cumulating the number of separate images in each group
  - Separate images are identified by the all-numeric suffix property
- **Total number of files with an invalid image filename:**
  - Based on the format documented in this specification

### 4.3 Breakdowns by Analytics Dimension
- **Total number of images per camera:**
  - Breakdown based on the first 4 characters
  - Display camera name from config mapping
- **Total number of images per Processing method:**
  - Breakdown based on the dash-prefixed properties
  - Display processing method description from config mapping

---

## 5. Technical Architecture

### 5.1 File Structure

```
photo-admin/
├── photo_pairing.py          # New tool (main entry point)
├── config_manager.py          # Existing (shared with PhotoStats)
├── config/
│   ├── template-config.yaml   # Updated with new dimensions
│   └── config.yaml            # User config (auto-updated)
├── docs/
│   └── prd/
│       └── photo-pairing-tool.md  # This document
└── tests/
    └── test_photo_pairing.py  # Test suite for new tool
```

### 5.2 Integration with PhotoAdminConfig

- The tool will instantiate `PhotoAdminConfig` from `config_manager.py`
- Use existing properties:
  - `photo_extensions`
  - `metadata_extensions`
- Access new properties via `raw_config` or new helper methods:
  - `camera_mappings`
  - `processing_methods`

### 5.3 Configuration Update Mechanism

- When new Camera IDs or Processing Methods are detected:
  1. Pause file processing
  2. Display interactive prompt to user
  3. Collect user input (name, description, etc.)
  4. Update the in-memory config dictionary
  5. Write updated config back to YAML file using `yaml.safe_dump()`
  6. Resume file processing

### 5.4 HTML Report Generation

- Follow similar approach to PhotoStats HTML report generation
- Include:
  - Summary statistics
  - Tables for breakdowns by camera and processing method
  - List of invalid files
  - Optional: Charts/visualizations for distributions

---

## 6. Configuration Schema Extensions

The existing `config.yaml` will be extended with two new top-level keys:

```yaml
# Existing configuration
photo_extensions:
  - .dng
  - .tiff
  - .tif
  - .cr3

metadata_extensions:
  - .xmp

require_sidecar:
  - .cr3

# NEW: Camera ID mappings
camera_mappings:
  AB3D:
    name: "Canon EOS R5"
    serial_number: "12345"
  XYZW:
    name: "Sony A7IV"
    serial_number: ""

# NEW: Processing method descriptions
processing_methods:
  "HDR": "High Dynamic Range processing"
  "BW": "Black and white conversion"
  "PANO": "Panorama stitching"
  "property with spaces": "Description for multi-word property"
```

**Notes:**
- Keys in `processing_methods` can include spaces (must be quoted in YAML)
- `serial_number` in `camera_mappings` is optional (can be empty string)

---

## 7. User Interaction Flow

### 7.1 First Run / New Camera ID Detected

```
Scanning folder: /path/to/photos
Found new camera ID: AB3D

Please provide information for camera ID 'AB3D':
  Camera name: Canon EOS R5
  Serial number (optional, press Enter to skip): 12345

✓ Camera mapping saved to config file.
Continuing scan...
```

### 7.2 New Processing Method Detected

```
Found new processing method: HDR

Please provide a description for processing method 'HDR':
  Description: High Dynamic Range processing

✓ Processing method mapping saved to config file.
Continuing scan...
```

### 7.3 Progress Indicators

```
Scanning folder: /path/to/photos
Found 150 files
Analyzing filenames...
  ✓ Valid files: 145
  ✗ Invalid files: 5
Extracting properties...
Generating report...
✓ Report saved to: photo_pairing_report_2025-12-23_14-30-45.html
```

### 7.4 Error Messages

**Invalid filename examples:**
```
Warning: Invalid filename detected: abc0001.dng
  Reason: First 4 characters must be uppercase alphanumeric

Warning: Invalid filename detected: AB3D0000.dng
  Reason: Counter must be between 0001 and 9999

Warning: Invalid filename detected: AB3D0035-.ext
  Reason: Empty property name detected
```

---

## 8. Error Handling and Edge Cases

### 8.1 Filename Validation

| Scenario | Example | Valid? | Action |
|----------|---------|--------|--------|
| Lowercase camera ID | `ab3d0001.dng` | ❌ | Add to invalid list |
| Counter = 0000 | `AB3D0000.dng` | ❌ | Add to invalid list |
| Counter > 9999 | `AB3D10000.dng` | ❌ | Add to invalid list |
| Empty property | `AB3D0035-.ext` | ❌ | Add to invalid list |
| Only 3 chars in camera ID | `ABC0001.dng` | ❌ | Add to invalid list |
| Space in camera ID | `AB D0001.dng` | ❌ | Add to invalid list |
| Valid with properties | `AB3D0035-HDR.dng` | ✅ | Process normally |
| Valid with numeric suffix | `AB3D0035-2.dng` | ✅ | Process as image #2 |
| Duplicate properties | `AB3D0035-HDR-HDR.dng` | ✅ | Attach `HDR` once |

### 8.2 Configuration Handling

- **Missing config file:** Use PhotoAdminConfig's existing logic to create from template
- **Corrupted YAML:** Display error and exit with helpful message
- **User cancels input:** Skip the mapping for this run, but continue processing other files
- **Duplicate user input:** Overwrite existing mapping with new values

### 8.3 File System Errors

- **Folder not found:** Display error and exit
- **Permission denied:** Display error for specific files, continue with others
- **Symlinks:** Follow symlinks (same behavior as PhotoStats)

---

## 9. Command-Line Interface

### 9.1 Basic Usage

```bash
python photo_pairing.py /path/to/photos
```

### 9.2 Optional Flags (Future Enhancement)

```bash
# Specify custom config file
python photo_pairing.py /path/to/photos --config /path/to/config.yaml

# Specify output report location
python photo_pairing.py /path/to/photos --output /path/to/report.html

# Non-interactive mode (skip prompts, only use existing mappings)
python photo_pairing.py /path/to/photos --no-interactive
```

### 9.3 Output

- HTML report saved to current directory
- Filename format: `photo_pairing_report_YYYY-MM-DD_HH-MM-SS.html`
- Console output shows summary and path to report

---

## 10. Testing Strategy

### 10.1 Test Cases for Filename Validation

- Valid filenames with various camera IDs
- Invalid filenames (lowercase, wrong counter, etc.)
- Edge cases (empty properties, duplicate properties)
- Unicode characters in extensions
- Very long filenames

### 10.2 Test Cases for Property Extraction

- Single property
- Multiple properties in sequence
- Properties with spaces
- All-numeric properties (separate image IDs)
- Duplicate properties
- Mixed alphanumeric and numeric properties

### 10.3 Test Cases for Grouping

- Files with same 8-character prefix
- Files with different camera IDs
- Files with different counters
- Multiple file formats in same group
- Groups with separate image IDs

### 10.4 Test Cases for Configuration

- Initial config creation from template
- Adding new camera mappings
- Adding new processing methods
- Persisting config across runs
- Handling spaces in processing method keys

### 10.5 Test Cases for Reporting

- Report contains all required metrics
- Correct calculation of totals and averages
- Proper breakdown by camera and processing method
- Invalid files list is accurate
- HTML is well-formed and displays correctly

---

## 11. Future Enhancements

### Version 1.1
- Include sidecar files in groups based on PhotoStats pairing logic
- Add support for custom report templates
- Export report data to JSON/CSV formats

### Version 1.2
- Batch processing of multiple folders
- Comparison reports between two scans
- Integration with PhotoStats for unified reporting

### Version 2.0
- Machine learning-based property detection
- Automatic camera ID detection from EXIF data
- Web-based UI for configuration and reporting

---

## 12. Acceptance Criteria

The tool is considered complete when:

1. ✅ It successfully scans a folder and identifies valid/invalid filenames
2. ✅ It correctly groups files by the first 8 characters
3. ✅ It extracts camera IDs and processing methods accurately
4. ✅ It prompts users for new mappings and saves them to config
5. ✅ It generates an HTML report with all required metrics
6. ✅ It handles all edge cases without crashing
7. ✅ It has comprehensive test coverage (>80%)
8. ✅ It has clear documentation and user-friendly error messages
9. ✅ Config updates persist across runs
10. ✅ It runs independently from PhotoStats while sharing config infrastructure

---

## Appendix A: Example Scenarios

### Scenario 1: First Run on New Photo Collection

**Input Files:**
```
AB3D0001.dng
AB3D0001-HDR.tiff
AB3D0002.dng
XYZW0001.cr3
XYZW0001-BW.tiff
invalid123.dng
```

**User Interaction:**
```
Found new camera ID: AB3D
  Camera name: Canon EOS R5
  Serial number: 12345

Found new camera ID: XYZW
  Camera name: Sony A7IV
  Serial number: [Enter]

Found new processing method: HDR
  Description: High Dynamic Range processing

Found new processing method: BW
  Description: Black and white conversion
```

**Report Output:**
- Groups detected: 3 (AB3D0001, AB3D0002, XYZW0001)
- Total images: 3
- Invalid files: 1 (invalid123.dng)
- Images per camera: AB3D=2, XYZW=1
- Images per method: HDR=1, BW=1

### Scenario 2: Subsequent Run (Config Already Exists)

**Input Files:**
```
AB3D0003.dng
AB3D0003-HDR.tiff
AB3D0003-2.cr3
```

**User Interaction:**
- No prompts (camera AB3D and method HDR already in config)

**Report Output:**
- Groups detected: 1 (AB3D0003)
- Total images: 2 (AB3D0003 and AB3D0003-2)
- Images per camera: AB3D=2
- Images per method: HDR=2

---

**Document Version History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-23 | AI Assistant | Initial comprehensive PRD |
