# Quickstart: Migrating Tools to Centralized Templates

**Audience**: Developers adding new tools to the photo-admin toolbox
**Purpose**: Guide for adopting the standardized HTML report system
**Updated**: 2025-12-25

## Overview

All tools in the photo-admin toolbox must generate HTML reports using the centralized Jinja2 template system. This guide shows you how to integrate your tool with the existing template infrastructure.

## Prerequisites

1. **Dependencies installed**: `pip install -r requirements.txt` (includes Jinja2>=3.1.0)
2. **Familiarity with**: Python 3.10+, CLI tool structure, basic Jinja2 syntax
3. **Reference tools**: PhotoStats (`photo_stats.py`) and Photo Pairing (`photo_pairing.py`)

## Quick Integration (5 Steps)

### Step 1: Import Report Renderer

```python
from utils.report_renderer import ReportRenderer, ReportContext, KPICard, ReportSection
```

### Step 2: Build Report Context

During your analysis, collect data into a `ReportContext` object:

```python
# After completing your analysis
context = ReportContext(
    tool_name="My Photo Tool",
    tool_version="1.0.0",
    scan_path=folder_path,
    scan_timestamp=datetime.now(),
    scan_duration=time.time() - start_time,
    kpis=[
        KPICard(
            title="Total Files",
            value=f"{total_files:,}",
            unit="files",
            status="success"
        ),
        # Add more KPIs...
    ],
    sections=[
        ReportSection(
            title="File Distribution",
            type="chart_bar",
            data={
                "labels": ["Type1", "Type2"],
                "values": [100, 200]
            }
        ),
        # Add more sections...
    ],
    warnings=warnings_list,  # Optional
    errors=errors_list        # Optional
)
```

### Step 3: Create Tool-Specific Template

Create `templates/my_tool.html.j2`:

```jinja2
{% extends "base.html.j2" %}

{% block tool_specific_styles %}
{# Optional: Add tool-specific CSS here #}
<style>
    .my-custom-class {
        color: blue;
    }
</style>
{% endblock %}

{% block tool_specific_scripts %}
{# Optional: Add tool-specific JavaScript here #}
<script>
    // Custom chart setup or interactions
</script>
{% endblock %}
```

That's it! The base template handles:
- Header with tool name and metadata
- KPI cards layout
- Section rendering (charts, tables, HTML)
- Warnings and errors styling
- Footer with timestamp and attribution

### Step 4: Render HTML Report

```python
renderer = ReportRenderer()
output_path = f"my_tool_report_{timestamp}.html"

try:
    renderer.render_report(
        context=context,
        template_name="my_tool.html.j2",
        output_path=output_path
    )
    print(f"Report generated: {output_path}")
except Exception as e:
    print(f"ERROR: Failed to generate HTML report: {e}")
    print("Analysis results are available in console output above.")
    sys.exit(1)
```

### Step 5: Add Help Text and Signal Handling

```python
import argparse
import signal
import sys

# Global flag for clean shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    global shutdown_requested
    shutdown_requested = True
    print("\nOperation interrupted by user")
    sys.exit(130)

def main():
    # Register signal handler
    signal.signal(signal.SIGINT, signal_handler)

    # Argument parsing with help
    parser = argparse.ArgumentParser(
        description="My Photo Tool - Brief description of what it does",
        epilog="""
Examples:
  python3 my_tool.py /path/to/photos
  python3 my_tool.py ~/Pictures/2024

Configuration:
  Uses config from: ./config/config.yaml or ~/.photo-admin/config.yaml
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('folder_path', help='Path to photo collection to analyze')
    # Add more arguments as needed

    args = parser.parse_args()

    # Your tool logic here
    # Check shutdown_requested periodically during long operations
```

## Complete Example

See `examples/minimal_tool.py` for a complete working example that demonstrates:
- Argument parsing with help text
- Signal handling (CTRL+C)
- Analysis loop with interruption checks
- Building ReportContext
- Template rendering with error handling

## Section Types Reference

### 1. Bar Chart

```python
ReportSection(
    title="File Type Distribution",
    type="chart_bar",
    data={
        "labels": ["DNG", "CR3", "TIFF"],
        "values": [800, 434, 50]
    },
    description="Breakdown by file extension"
)
```

### 2. Pie Chart

```python
ReportSection(
    title="Camera Usage",
    type="chart_pie",
    data={
        "labels": ["Camera A", "Camera B"],
        "values": [60, 40]
    }
)
```

### 3. Line Chart

```python
ReportSection(
    title="Photos Over Time",
    type="chart_line",
    data={
        "labels": ["Jan", "Feb", "Mar"],
        "values": [100, 150, 200]
    }
)
```

### 4. Table

```python
ReportSection(
    title="Invalid Files",
    type="table",
    data={
        "headers": ["Filename", "Issue", "Suggested Fix"],
        "rows": [
            ["IMG_0001.dng", "Missing XMP", "Create sidecar file"],
            ["BAD_NAME.cr3", "Invalid format", "Rename to AB3D0001.cr3"]
        ]
    }
)
```

### 5. Custom HTML

```python
ReportSection(
    title="Custom Analysis",
    type="html",
    html_content="<div class='custom'>Your HTML content here</div>"
)
```

## KPI Status Guidelines

Choose the appropriate status based on the metric's meaning:

- **`success`** (green): Good metrics, goals achieved
  - Example: "All files paired correctly"

- **`info`** (blue): Neutral information, counts, statistics
  - Example: "Total files scanned: 1,234"

- **`warning`** (orange): Needs attention, minor issues
  - Example: "5 orphaned files found"

- **`danger`** (red): Critical issues, errors
  - Example: "12 files with invalid names"

## Warnings vs Errors

### Use Warnings for:
- Non-critical issues that don't prevent analysis
- Recommendations or suggestions
- Minor data quality concerns
- Performance observations

```python
warnings=[
    WarningMessage(
        message="5 .xmp files without matching photos",
        details=["file1.xmp", "file2.xmp", "..."],
        severity="medium"
    )
]
```

### Use Errors for:
- Critical validation failures
- Data corruption or integrity issues
- Invalid configurations that must be fixed
- Issues that affect analysis accuracy

```python
errors=[
    ErrorMessage(
        message="12 files have invalid naming format",
        details=["List of specific files..."],
        actionable_fix="Rename files to match: [CAMERA_ID][COUNTER]-[PROPS].[ext]"
    )
]
```

## Testing Your Integration

### 1. Unit Tests for Context Building

```python
def test_build_report_context():
    context = build_report_context(analysis_results)
    assert context.tool_name == "My Tool"
    assert len(context.kpis) >= 1
    assert len(context.sections) >= 1
    # Validate context against schema
```

### 2. Template Rendering Tests

```python
def test_render_report(tmp_path):
    context = create_test_context()
    renderer = ReportRenderer()
    output = tmp_path / "test_report.html"

    renderer.render_report(context, "my_tool.html.j2", str(output))

    assert output.exists()
    html_content = output.read_text()
    assert "My Tool" in html_content
    assert context.kpis[0].value in html_content
```

### 3. Signal Handling Tests

```python
def test_ctrl_c_handling(monkeypatch):
    # Simulate SIGINT during operation
    # Verify clean shutdown with exit code 130
    # Verify no partial report file created
```

## Validation Checklist

Before submitting your tool:

- [ ] `--help` and `-h` flags work and display comprehensive usage info
- [ ] CTRL+C interrupts cleanly with exit code 130
- [ ] No partial HTML reports created when interrupted
- [ ] Template renders successfully with test data
- [ ] All KPIs have appropriate status colors
- [ ] Charts display correctly in generated HTML
- [ ] Warnings and errors sections work (test both populated and empty)
- [ ] Report footer includes tool name and generation timestamp
- [ ] Visual styling matches other tools (colors, fonts, layout)
- [ ] Template failure shows clear console error message
- [ ] Tests cover template rendering, help text, and signal handling

## Common Issues & Solutions

### Issue: Template Not Found

**Error**: `jinja2.exceptions.TemplateNotFound: my_tool.html.j2`

**Solution**: Ensure your template file exists in `templates/` directory at repository root.

### Issue: Chart Not Displaying

**Problem**: Chart section appears empty in report.

**Solution**: Check that `data["labels"]` and `data["values"]` have the same length and contain valid data.

### Issue: Colors Don't Match Other Tools

**Problem**: KPI cards or charts use different colors than PhotoStats/Photo Pairing.

**Solution**: Don't override colors in your template. Base template already defines consistent color theme.

### Issue: CTRL+C Creates Partial Report

**Problem**: Interrupted scan still creates HTML file.

**Solution**: Use atomic file write pattern (write to temp file → rename). See `utils/report_renderer.py` for example.

## Advanced Customization

### Custom Chart Colors

```python
ReportSection(
    title="Custom Colored Chart",
    type="chart_bar",
    data={
        "labels": ["A", "B", "C"],
        "values": [10, 20, 30],
        "colors": ["#ff6384", "#36a2eb", "#ffce56"]  # Custom colors
    }
)
```

### Collapsible Sections

```python
ReportSection(
    title="Detailed Data (Click to Expand)",
    type="table",
    data={...},
    collapsible=True
)
```

### Tool-Specific Footer Note

```python
context = ReportContext(
    # ... other fields ...
    footer_note="Special note: Camera mappings can be updated in config.yaml"
)
```

## Support

- **Examples**: See `photo_stats.py` and `photo_pairing.py` for complete reference implementations
- **Schema**: Check `specs/002-html-report-consistency/contracts/template-context.schema.json` for data structure validation
- **Issues**: Report problems at https://github.com/fabrice-guiot/photo-admin/issues
- **Constitution**: Review `.specify/memory/constitution.md` for architectural principles
