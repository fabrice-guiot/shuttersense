# Filename Validation Contract

**Feature**: Photo Pairing Tool
**Date**: 2025-12-23
**Purpose**: Define the exact rules for valid photo filenames

## Overview

This contract specifies the filename pattern that the Photo Pairing Tool uses to identify valid image files. Files not matching this pattern are tracked as invalid.

## Filename Pattern Specification

### Complete Pattern (Regex)

```regex
^[A-Z0-9]{4}(0[0-9]{3}|[1-9][0-9]{3})(-[A-Za-z0-9 _]+)*\.[a-zA-Z0-9]+$
```

**Case-insensitive mode**: OFF (pattern is case-sensitive for camera ID, but extensions accept both uppercase and lowercase)

### Component Breakdown

A valid filename consists of four parts:

#### 1. Camera ID (Required)
- **Pattern**: `[A-Z0-9]{4}`
- **Length**: Exactly 4 characters
- **Allowed characters**: Uppercase letters A-Z and digits 0-9
- **Position**: Characters 1-4 of filename

**Valid examples**: `AB3D`, `XYZW`, `A1B2`, `9876`
**Invalid examples**: `abc` (too short), `ABCDE` (too long), `ab3d` (lowercase), `AB-D` (special char)

#### 2. Counter (Required)
- **Pattern**: `(0[0-9]{3}|[1-9][0-9]{3})`
- **Length**: Exactly 4 digits
- **Range**: 0001 to 9999 (inclusive)
- **Special rule**: 0000 is NOT valid
- **Position**: Characters 5-8 of filename

**Valid examples**: `0001`, `0042`, `1000`, `9999`
**Invalid examples**: `0000` (zero not allowed), `00` (too short), `10000` (too long)

#### 3. Properties (Optional, Multiple Allowed)
- **Pattern**: `(-[A-Za-z0-9 _]+)*`
- **Format**: Each property starts with a dash (`-`)
- **Allowed characters within property**:
  - Uppercase letters: A-Z
  - Lowercase letters: a-z
  - Digits: 0-9
  - Spaces
  - Underscores: _
- **Termination**: Next dash or file extension
- **Quantity**: Zero or more properties

**Valid examples**:
- `-HDR` (single property)
- `-HDR-BW` (two properties)
- `-property 2` (property with space)
- `-HDR_BW` (property with underscore)
- `-HDR-property 2-PANO` (multiple properties, one with space)
- `-high_res_output` (property with multiple underscores)
- `-123` (all-numeric property - valid syntax, treated as separate image ID)

**Invalid examples**:
- `-` (empty property - no characters after dash)
- `--HDR` (empty first property)
- `-HDR-` (empty last property)
- `-HDR.BW` (period not allowed within property)
- `-HDR@BW` (special characters not allowed)

#### 4. File Extension (Required)
- **Pattern**: `\.[a-zA-Z0-9]+`
- **Format**: Dot followed by one or more letters (uppercase or lowercase) or digits
- **Case-sensitivity**: Extensions are case-insensitive - `.DNG`, `.dng`, `.Dng` are all valid and equivalent
- **Examples**: `.dng`, `.DNG`, `.tiff`, `.TIFF`, `.cr3`, `.CR3`, `.jpg`, `.JPG`
- **Note**: Extension checking is done case-insensitively against PhotoAdminConfig's `photo_extensions` list

## Complete Examples

### Valid Filenames

| Filename | Camera ID | Counter | Properties | Extension |
|----------|-----------|---------|------------|-----------|
| `AB3D0001.dng` | AB3D | 0001 | (none) | .dng |
| `XYZW0035-HDR.tiff` | XYZW | 0035 | HDR | .tiff |
| `A1B20123-property1-2.cr3` | A1B2 | 0123 | property1, 2 | .cr3 |
| `9XYZ9999-HDR-BW-PANO.jpg` | 9XYZ | 9999 | HDR, BW, PANO | .jpg |
| `TEST0001-property with spaces.dng` | TEST | 0001 | property with spaces | .dng |
| `AB3D0035-HDR_BW.tiff` | AB3D | 0035 | HDR_BW | .tiff |
| `XYZW0042-high_res_output.dng` | XYZW | 0042 | high_res_output | .dng |
| `AB3D0035-123.dng` | AB3D | 0035 | 123 (sep. image) | .dng |
| `AB3D0001.DNG` | AB3D | 0001 | (none) | .DNG (uppercase) |
| `XYZW0035-HDR.TIFF` | XYZW | 0035 | HDR | .TIFF (uppercase) |
| `TEST0042-BW.Cr3` | TEST | 0042 | BW | .Cr3 (mixed case) |

### Invalid Filenames

| Filename | Reason |
|----------|--------|
| `abc0001.dng` | Camera ID must be uppercase |
| `AB3D0000.dng` | Counter cannot be 0000 |
| `ABC0001.dng` | Camera ID must be exactly 4 characters (only 3) |
| `AB3DE0001.dng` | Camera ID must be exactly 4 characters (5 given) |
| `AB3D001.dng` | Counter must be exactly 4 digits (only 3) |
| `AB3D00001.dng` | Counter must be exactly 4 digits (5 given) |
| `AB3D0035-.ext` | Empty property name (dash with nothing after) |
| `AB3D0035-HDR-.ext` | Empty property name (second property empty) |
| `AB3D0035-HDR.BW.ext` | Invalid character in property (period in HDR.BW) |
| `AB3D0035-HDR@BW.ext` | Invalid character in property (@ symbol) |
| `AB 3D0001.dng` | Space in camera ID not allowed |
| `AB3D-0001.dng` | Dash separates camera ID from counter (makes "AB3D" 4 chars and "0001" a property) |

## Property Type Identification

Properties are further classified based on their content:

### Processing Method Properties

Properties that contain at least one non-digit character.

**Examples**:
- `HDR` → Processing method
- `BW` → Processing method
- `property 2` → Processing method (contains letter 'p')
- `123ABC` → Processing method (contains letters)

**Behavior**:
- Checked against config's `processing_methods` mapping
- User prompted if not found
- Added to ImageGroup's `properties` set
- Counted in analytics as processing method usage

### Separate Image Identifiers

Properties that contain ONLY digits.

**Examples**:
- `2` → Separate image ID
- `123` → Separate image ID
- `0005` → Separate image ID

**Behavior**:
- NOT processing methods
- Identify different images within same group
- Added to ImageGroup's `separate_images` dictionary
- Increase total image count for the group
- Do NOT trigger user prompts

### Duplicate Property Handling

If a filename contains the same property multiple times, attach it only once.

**Example**:
- Filename: `AB3D0035-HDR-BW-HDR.dng`
- Properties attached: `{'HDR', 'BW'}` (HDR appears only once in set)

## Edge Cases

### Empty Properties

`AB3D0035-.ext` or `AB3D0035-HDR-.ext`

**Validation**: INVALID
**Reason**: Empty property name detected
**Explanation**: Dash must be followed by at least one allowed character before next dash or extension

### Leading/Trailing Dashes in Extension

`AB3D0035.dng-` or `AB3D0035-.dng`

**Validation**: INVALID
**Reason**: Dash after extension not part of property pattern; Dash before extension is empty property

### Mixed Case in Camera ID

`Ab3D0001.dng`

**Validation**: INVALID
**Reason**: Camera ID must be ALL UPPERCASE

### Spaces in Properties

`AB3D0035-property with spaces.dng`

**Validation**: VALID
**Properties**: `['property with spaces']`
**Note**: Spaces are explicitly allowed within property keywords

### Case-Insensitive File Extensions

`AB3D0001.DNG`, `AB3D0001.dng`, `AB3D0001.Dng`

**Validation**: ALL VALID (equivalent)
**Extension**: .DNG / .dng / .Dng (all treated as same extension)
**Note**: File extensions are case-insensitive. The system normalizes extensions to lowercase for comparison with the configured `photo_extensions` list. Both validation and file scanning treat `.DNG`, `.dng`, `.TIFF`, `.tiff` as equivalent.

### All-Numeric Properties

`AB3D0035-2-HDR.dng`

**Validation**: VALID
**Separate Image ID**: `2`
**Properties**: `['HDR']`
**Explanation**: First all-numeric property becomes separate image ID; subsequent alphanumeric properties are processing methods

### Multiple Numeric Properties

`AB3D0035-2-3-HDR.dng`

**Validation**: VALID
**Separate Image ID**: `2` (first numeric property)
**Properties**: `['3', 'HDR']`
**Explanation**: Only the FIRST all-numeric property is treated as separate image ID; later numeric properties become regular processing methods (though unusual)

## Testing Contract

### Unit Test Requirements

Each filename validation rule MUST have dedicated tests:

1. **Camera ID validation**:
   - Exactly 4 characters (test 3, 4, 5 chars)
   - Uppercase only (test lowercase, mixed case)
   - Alphanumeric only (test special chars)

2. **Counter validation**:
   - Exactly 4 digits (test 3, 4, 5 digits)
   - Range 0001-9999 (test 0000, 0001, 9999, 10000)
   - Numeric only

3. **Property validation**:
   - Optional presence (test with/without)
   - Multiple properties (test 0, 1, 3, 10 properties)
   - Valid characters (test alphanumeric + spaces + underscores)
   - Invalid characters (test period, @ symbol, etc.)
   - Empty properties (test trailing dash, double dash)
   - Spaces in properties (test "property with spaces")
   - Underscores in properties (test "HDR_BW", "high_res_output")

4. **Property type identification**:
   - All-numeric = separate image ID (test "2", "123")
   - Alphanumeric = processing method (test "HDR", "BW")
   - First numeric wins (test "2-HDR" vs "HDR-2")

5. **Extension validation**:
   - Case-insensitive matching (test ".dng", ".DNG", ".Dng" all valid)
   - Against allowed extensions list (normalized to lowercase)
   - Mixed case extensions (test ".TIFF", ".tiff", ".TiFf")
   - File scanning respects case-insensitivity

### Integration Test Requirements

1. Parse batch of valid filenames, verify correct grouping
2. Parse batch of invalid filenames, verify each has correct error reason
3. Parse mixed batch, verify valid/invalid segregation
4. Parse filenames with various property combinations
5. Verify duplicate property deduplication
