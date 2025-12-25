# Data Model: HTML Report Consistency & Tool Improvements

**Feature**: 002-html-report-consistency
**Created**: 2025-12-25
**Purpose**: Define data structures for template rendering, help text, and signal handling

## Overview

This feature introduces shared data structures that enable consistent HTML report generation across all tools in the photo-admin toolbox. The primary entity is the **ReportContext** which encapsulates all data needed for template rendering.

## Core Entities

### 1. ReportContext

The unified data structure passed to Jinja2 templates for rendering HTML reports.

**Purpose**: Standardize the data interface between tools and templates, ensuring all reports have consistent metadata and structure.

**Attributes**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `tool_name` | string | Yes | Display name of the tool (e.g., "PhotoStats", "Photo Pairing") | Non-empty, alphanumeric with spaces |
| `tool_version` | string | Yes | Semantic version of the tool | Format: "X.Y.Z" or "X.Y" |
| `scan_path` | string | Yes | Absolute path to scanned folder | Valid filesystem path |
| `scan_timestamp` | datetime | Yes | When the scan was initiated | ISO 8601 format |
| `scan_duration` | float | Yes | Duration in seconds | Non-negative number |
| `kpis` | list[KPICard] | Yes | Summary metrics displayed as cards | Min 1 KPI |
| `sections` | list[ReportSection] | Yes | Content sections (charts, tables, warnings) | Min 1 section |
| `warnings` | list[WarningMessage] | No | Non-critical issues found | Default: empty list |
| `errors` | list[ErrorMessage] | No | Critical issues found | Default: empty list |
| `footer_note` | string | No | Optional tool-specific footer text | Max 500 chars |

**Relationships**:
- Has many `KPICard` items (1..n)
- Has many `ReportSection` items (1..n)
- Has zero or more `WarningMessage` items (0..n)
- Has zero or more `ErrorMessage` items (0..n)

**Example**:
```python
ReportContext(
    tool_name="PhotoStats",
    tool_version="1.0.0",
    scan_path="/Users/user/Photos",
    scan_timestamp=datetime(2025, 12, 25, 10, 30, 0),
    scan_duration=12.5,
    kpis=[
        KPICard(title="Total Photos", value="1,234", unit="files", status="success"),
        KPICard(title="Orphaned Files", value="5", unit="files", status="warning")
    ],
    sections=[
        ReportSection(
            title="File Type Distribution",
            type="chart_bar",
            data={"labels": ["DNG", "CR3"], "values": [800, 434]}
        )
    ],
    warnings=[WarningMessage(message="5 orphaned .xmp files found", details=[...])],
    errors=[],
    footer_note="Scan completed successfully"
)
```

---

### 2. KPICard

A summary metric displayed prominently at the top of reports.

**Purpose**: Provide at-a-glance insights into key statistics.

**Attributes**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `title` | string | Yes | Metric name (e.g., "Total Photos") | Non-empty, max 50 chars |
| `value` | string | Yes | Formatted metric value (e.g., "1,234") | Non-empty, max 20 chars |
| `unit` | string | No | Unit label (e.g., "files", "MB", "%") | Max 20 chars |
| `status` | string | Yes | Visual indicator: "success", "info", "warning", "danger" | One of enum values |
| `icon` | string | No | Optional icon name for visual enhancement | Valid icon identifier |
| `tooltip` | string | No | Hover text explaining the metric | Max 200 chars |

**Status Color Mapping**:
- `success`: Green gradient (data is good)
- `info`: Blue gradient (neutral information)
- `warning`: Orange gradient (attention needed)
- `danger`: Red gradient (critical issue)

**Example**:
```python
KPICard(
    title="Total Photos",
    value="1,234",
    unit="files",
    status="success",
    icon="photo",
    tooltip="Total number of photo files found in scanned directory"
)
```

---

### 3. ReportSection

A content block within the report (chart, table, or custom HTML).

**Purpose**: Modular content sections that tools can customize while maintaining consistent styling.

**Attributes**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `title` | string | Yes | Section heading | Non-empty, max 100 chars |
| `type` | string | Yes | Section type: "chart_bar", "chart_pie", "chart_line", "table", "html" | One of enum values |
| `data` | dict | Conditional | Chart/table data (required for chart/table types) | Varies by type |
| `html_content` | string | Conditional | Raw HTML (required for "html" type) | Valid HTML fragment |
| `description` | string | No | Section explanation displayed under title | Max 500 chars |
| `collapsible` | bool | No | Whether section can be collapsed | Default: false |

**Data Format by Type**:

- **chart_bar / chart_line**:
  ```python
  {
      "labels": ["Label1", "Label2", ...],
      "values": [100, 200, ...],
      "colors": ["#ff6384", "#36a2eb", ...]  # Optional
  }
  ```

- **chart_pie**:
  ```python
  {
      "labels": ["Slice1", "Slice2", ...],
      "values": [30, 70, ...],
      "colors": ["#ff6384", "#36a2eb", ...]  # Optional
  }
  ```

- **table**:
  ```python
  {
      "headers": ["Column1", "Column2", ...],
      "rows": [
          ["Cell1", "Cell2", ...],
          ["Cell3", "Cell4", ...]
      ]
  }
  ```

**Example**:
```python
ReportSection(
    title="File Type Distribution",
    type="chart_bar",
    data={
        "labels": ["DNG", "CR3", "TIFF", "XMP"],
        "values": [800, 434, 50, 839]
    },
    description="Breakdown of files by extension type"
)
```

---

### 4. WarningMessage

A non-critical issue or concern found during analysis.

**Purpose**: Highlight items that need user attention but don't prevent analysis completion.

**Attributes**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `message` | string | Yes | Summary of the warning | Non-empty, max 200 chars |
| `details` | list[string] | No | Specific examples or affected items | Each detail max 500 chars |
| `severity` | string | No | "low", "medium", "high" | Default: "medium" |

**Example**:
```python
WarningMessage(
    message="5 orphaned .xmp files found without corresponding photos",
    details=[
        "/Photos/IMG_001.xmp (no DNG found)",
        "/Photos/IMG_002.xmp (no CR3 found)",
        "... 3 more"
    ],
    severity="medium"
)
```

---

### 5. ErrorMessage

A critical issue that prevented full analysis or indicates data corruption.

**Purpose**: Clearly communicate serious problems that require user action.

**Attributes**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `message` | string | Yes | Summary of the error | Non-empty, max 200 chars |
| `details` | list[string] | No | Specific examples or stack trace info | Each detail max 1000 chars |
| `actionable_fix` | string | No | Suggested remediation step | Max 300 chars |

**Example**:
```python
ErrorMessage(
    message="12 files have invalid naming format",
    details=[
        "AB3D0000.dng: Counter cannot be 0000",
        "INVALID.cr3: Missing camera ID",
        "... 10 more"
    ],
    actionable_fix="Rename files to match the pattern: [CAMERA_ID][COUNTER]-[PROPERTIES].[ext]"
)
```

---

### 6. HelpTextSpec

Structure for help text content (used in argument parsing).

**Purpose**: Standardize help text format across all tools.

**Attributes**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | string | Yes | Tool description (1-2 sentences) |
| `arguments` | list[ArgumentHelp] | Yes | Description of each CLI argument |
| `examples` | list[string] | Yes | Usage examples (min 2) |
| `config_notes` | string | Yes | Configuration file information |

**ArgumentHelp Sub-Entity**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Argument name (e.g., "folder_path") |
| `flags` | list[string] | Yes | CLI flags (e.g., ["-f", "--folder"]) |
| `description` | string | Yes | What the argument does |
| `required` | bool | Yes | Whether argument is mandatory |
| `default` | string | No | Default value if not provided |

---

## State Transitions

### ReportContext Lifecycle

```
[Tool Initialization]
         ↓
[Scan & Analysis] → Build ReportContext
         ↓
[Template Rendering] → Pass context to Jinja2
         ↓
[HTML Generation] → Write report file
         ↓
[Completion]
```

**Interruption Flow (SIGINT)**:
```
[Any State]
     ↓ (CTRL+C pressed)
[Signal Handler Triggered]
     ↓
[Check: Is report file being written?]
     ↓
     ├─ Yes → Complete atomic write (temp → final)
     └─ No  → Skip report generation
     ↓
[Display interruption message]
     ↓
[Exit with code 130]
```

---

## Validation Rules

### Cross-Entity Constraints

1. **KPI Status Consistency**: If `errors` list is non-empty, at least one KPI should have `status="danger"`
2. **Section Data Integrity**: `data` field must match the schema for the specified `type`
3. **Timestamp Validity**: `scan_timestamp` must be in the past (not future)
4. **Duration Reasonableness**: `scan_duration` should be < 24 hours (sanity check)
5. **Chart Data Alignment**: For charts, `len(labels) == len(values)`

### Template-Specific Constraints

- **PhotoStats-specific**: Must include sections for orphaned files and sidecar status
- **Photo Pairing-specific**: Must include sections for filename patterns and camera usage

---

## Template Context Schema

See `contracts/template-context.schema.json` for the complete JSON Schema definition of ReportContext and related entities. This schema is used for:
- Validating context data before template rendering
- Generating TypeScript interfaces for tooling
- Documentation generation
