# Photo Pairing Tool - Quickstart Guide

**Version**: 1.0
**Last Updated**: 2025-12-23

## What is the Photo Pairing Tool?

The Photo Pairing Tool analyzes your photo collection based on filenames to:
- **Group related files** (same photo in different formats)
- **Track camera usage** (which cameras took how many photos)
- **Identify processing methods** (HDR, black & white, panoramas, etc.)
- **Generate interactive HTML reports** with charts and breakdowns
- **Find non-compliant filenames** to help maintain naming consistency

## Quick Start

### 1. Run the Tool

```bash
python photo_pairing.py /path/to/your/photos
```

### 2. First Run: Configure Cameras and Methods

If the tool encounters camera IDs or processing methods it hasn't seen before, it will prompt you:

```
Found new camera ID: AB3D

Please provide information for camera ID 'AB3D':
  Camera name: Canon EOS R5
  Serial number (optional, press Enter to skip): 12345

✓ Camera mapping saved to config file.
```

```
Found new processing method: HDR

Please provide a description for processing method 'HDR':
  Description: High Dynamic Range processing

✓ Processing method mapping saved to config file.
```

### 3. View Your Report

After analysis completes, open the generated HTML report:

```
✓ Analysis complete
✓ Cache saved to: .photo_pairing_imagegroups
✓ Report saved to: photo_pairing_report_2025-12-23_14-30-45.html
```

The report shows:
- Total groups and images analyzed
- Average files per group
- Images per camera (with chart)
- Images per processing method (with chart)
- List of invalid files (if any)

### 4. Fast Report Regeneration

The tool creates a `.photo_pairing_imagegroups` cache file in the analyzed folder. On subsequent runs:

**If folder hasn't changed:**
```bash
python photo_pairing.py /path/to/your/photos

✓ Found cached analysis data
✓ Folder content unchanged - using cache
✓ Report saved to: photo_pairing_report_2025-12-23_15-45-12.html
```
Report generated in under 2 seconds! Perfect for updating camera names or method descriptions in config.

**If folder content changed:**
```bash
python photo_pairing.py /path/to/your/photos

⚠ Found cached analysis data
⚠ Folder content has changed (files added/removed/renamed)

Choose an option:
  (a) Use cached data and generate report (fast, ignores changes)
  (b) Re-analyze folder and update cache (slow, reflects current state)

Your choice [a/b]: b

Scanning folder...
```

## How It Works

### Filename Requirements

Your photo filenames must follow this pattern to be recognized:

```
CCCC####-property1-property2.ext
```

Where:
- **CCCC**: 4 uppercase characters (A-Z, 0-9) = Camera ID
- **####**: 4 digits (0001-9999) = Photo counter
- **-property**: Optional processing methods (can have multiple)
- **.ext**: File extension (.dng, .cr3, .tiff, etc.)

### Valid Filename Examples

```
AB3D0001.dng                    # Basic: camera AB3D, photo #1
XYZW0035-HDR.tiff               # With processing: HDR applied
A1B20123-HDR-BW.cr3             # Multiple methods: HDR and BW
TEST0100-property with spaces.jpg   # Spaces allowed in properties
AB3D0035-2.dng                  # Separate image: variant #2 of photo 35
```

### Invalid Filename Examples

```
abc0001.dng         # ❌ Camera ID must be UPPERCASE
AB3D0000.dng        # ❌ Counter can't be 0000 (use 0001-9999)
ABC0001.dng         # ❌ Camera ID must be exactly 4 characters
AB3D0035-.dng       # ❌ Empty property (dash with nothing after)
```

## Understanding the Report

### Groups

A **group** is a set of files with the same 8-character prefix (camera ID + counter).

Example group `AB3D0035`:
```
AB3D0035.dng        # Original RAW file
AB3D0035-HDR.tiff   # HDR-processed TIFF
AB3D0035-BW.jpg     # Black & white JPEG
```

This is ONE group with 3 files, representing ONE photo in different formats/processing.

### Separate Images

A separate image is identified by an all-numeric property:

```
AB3D0035.dng        # Base image
AB3D0035-2.dng      # Separate image #2
AB3D0035-3.dng      # Separate image #3
```

This group has 3 separate images (base + 2 + 3).

### Camera Analytics

The report shows which cameras you used and how many images each captured:

```
Camera Usage:
- Canon EOS R5 (AB3D): 150 images
- Sony A7IV (XYZW): 75 images
```

### Processing Method Analytics

See which processing techniques you applied most:

```
Processing Methods:
- HDR (High Dynamic Range): 45 images
- BW (Black & white): 30 images
- PANO (Panorama): 12 images
```

### Invalid Files

Files that don't match the naming pattern are listed with reasons:

```
Invalid Files (5):
1. abc0001.dng - Camera ID must be uppercase alphanumeric [A-Z0-9]
2. AB3D0000.dng - Counter must be between 0001 and 9999
3. AB3D0035-.jpg - Empty property name detected
```

## Subsequent Runs

After your first run, the tool remembers:
- Camera ID mappings (you won't be prompted for "AB3D" again)
- Processing method descriptions

It will only prompt when it discovers NEW camera IDs or methods.

## Configuration

### Location

The tool uses shared configuration from:
- `./config/config.yaml` (in current directory)
- Or `~/.photo-admin/config.yaml` (in home directory)

### Viewing Your Mappings

Open `config/config.yaml` to see your saved mappings:

```yaml
camera_mappings:
  AB3D:
    - name: "Canon EOS R5"
      serial_number: "12345"
  XYZW:
    - name: "Sony A7IV"
      serial_number: ""

processing_methods:
  "HDR": "High Dynamic Range processing"
  "BW": "Black and white conversion"
  "PANO": "Panorama stitching"
```

**Note**: Camera mappings are stored as lists (notice the `-` before each entry). Version 1.0 uses only the first camera in each list. Future versions will support multiple cameras per ID with distinguishing logic.

### Editing Mappings

You can manually edit this file to:
- Update camera names or serial numbers (edit the first entry in each list)
- Fix typos in processing method descriptions
- Add new mappings in advance (to avoid prompts)

## Tips & Best Practices

### Naming Your Photos

1. **Choose consistent 4-character camera IDs**
   - Examples: `R5MK` (Canon R5 Mark II), `A7R5` (Sony A7R V), `Z9NK` (Nikon Z9)
   - Use uppercase letters and numbers only
   - Keep the same ID for each camera

2. **Use meaningful counter values**
   - Start from 0001 for each camera
   - Increment sequentially as you shoot
   - Avoid gaps (makes analytics clearer)

3. **Apply processing method tags consistently**
   - Decide on standard keywords: `HDR`, `BW`, `PANO`, etc.
   - Keep them short and memorable
   - Be consistent (don't mix `BW` and `BlackWhite`)

4. **Use numeric suffixes for variants**
   - `-2`, `-3`, etc. for multiple exposures
   - Bracketing shots of the same scene
   - Alternative compositions

### Common Workflows

**Workflow 1: Analyze After Import**
```bash
# Import photos to folder
# Run tool to see what you captured
python photo_pairing.py ~/Photos/2025-01-15-Shoot

# Open report to review camera usage and processing
```

**Workflow 2: Find Naming Errors**
```bash
# Run tool on existing collection
python photo_pairing.py ~/Photos/Archive

# Check "Invalid Files" section in report
# Rename files to fix issues
# Re-run to verify
```

**Workflow 3: Track Processing Pipeline**
```bash
# After batch processing (HDR, panoramas, etc.)
python photo_pairing.py ~/Photos/Processed

# See which processing methods were applied most
# Identify photos with multiple processing applied
```

**Workflow 4: Update Camera Names Without Re-Scanning**
```bash
# Initial analysis
python photo_pairing.py ~/Photos/2025-01

# Later: realize camera name was generic placeholder
# Edit config/config.yaml: change "Unknown Camera AB3D" to "Canon EOS R5"

# Regenerate report instantly (uses cached .photo_pairing_imagegroups)
python photo_pairing.py ~/Photos/2025-01

# Report now shows proper camera name - no re-scanning!
```

## Troubleshooting

### "No configuration file found"

**Solution**: The tool will offer to create one from the template. Press Y to accept.

### "Camera ID must be uppercase"

**Problem**: Filename has lowercase letters in first 4 characters
**Solution**: Rename file to use UPPERCASE for camera ID

### "Counter cannot be 0000"

**Problem**: Photos use 0000 as counter value
**Solution**: Use 0001-9999 range instead

### "Empty property name detected"

**Problem**: Filename has `--` or ends with `-` before extension
**Solution**: Remove extra dashes or add property name after dash

### Tool runs but shows 0 groups

**Problem**: No files match the naming pattern
**Possible causes**:
- Files use different naming convention
- File extensions not in config's `photo_extensions` list

**Solution**:
1. Check `config/config.yaml` for `photo_extensions`
2. Add your file extensions if missing (e.g., `.arw`, `.nef`)
3. Or rename files to match the required pattern

### Cache file causing issues

**Problem**: Tool keeps using old analysis data after folder changes

**Solution**: Delete `.photo_pairing_imagegroups` file in the analyzed folder to force re-analysis:
```bash
rm /path/to/photos/.photo_pairing_imagegroups
python photo_pairing.py /path/to/photos
```

**Problem**: Tool says cache is invalid or corrupted

**Solution**: The file will be recreated automatically. Just choose option (b) to re-analyze when prompted, or delete the file manually.

## Advanced Usage

### Analyzing Specific File Types

Edit `config/config.yaml` to control which extensions are analyzed:

```yaml
photo_extensions:
  - .dng
  - .cr3
  - .tiff
  - .tif
  - .jpg
  - .jpeg
  - .arw    # Add Sony RAW
  - .nef    # Add Nikon RAW
```

### Excluding Sidecar Files

Sidecar files (`.xmp`) are automatically ignored in version 1.0:

```yaml
metadata_extensions:
  - .xmp  # These won't be analyzed
```

## Getting Help

- **Documentation**: See `docs/` folder for detailed guides
- **Issues**: Report bugs at [GitHub Issues](https://github.com/fabrice-guiot/photo-admin/issues)
- **Examples**: Check `docs/prd/photo-pairing-tool.md` for detailed specifications

## Version Notes

**Version 1.0**:
- Filename analysis and grouping
- Camera ID and processing method extraction
- Interactive HTML reports
- Configuration persistence
- Invalid filename detection

**Future Enhancements**:
- Sidecar file integration (group `.xmp` with images)
- Batch folder processing
- Export to CSV/JSON formats
- Comparison between two scan runs
