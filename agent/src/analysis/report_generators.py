"""
Shared HTML report generation functions for analysis tools.

Extracted from job_executor.py to allow reuse in CLI commands (run, test).
Each function builds a ReportContext and renders via Jinja2 templates,
with a plain HTML fallback on template errors.

Issue #108 - Remove CLI Direct Usage
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("shuttersense.agent.report_generators")


def _format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    size = float(size_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def generate_photostats_report(
    results: Dict[str, Any],
    location: str,
    connector: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate HTML report for PhotoStats results using Jinja2 templates.

    Args:
        results: PhotoStats results dictionary
        location: Collection path (display string)
        connector: Optional connector info (None for local collections)

    Returns:
        HTML report string
    """
    from utils.report_renderer import (
        ReportRenderer,
        ReportContext,
        KPICard,
        ReportSection,
        WarningMessage,
    )
    from version import __version__ as TOOL_VERSION

    is_remote = connector is not None

    try:
        display_location = location

        # Build KPI cards
        total_images = sum(
            count for ext, count in results.get('file_counts', {}).items()
            if ext not in {'.xmp'}
        )
        total_size = results.get('total_size', 0)
        kpis = [
            KPICard(
                title="Total Images",
                value=str(total_images),
                status="success",
                unit="files"
            ),
            KPICard(
                title="Total Size",
                value=_format_size(total_size),
                status="info"
            ),
            KPICard(
                title="Orphaned Images",
                value=str(len(results.get('orphaned_images', []))),
                status="warning" if results.get('orphaned_images') else "success",
                unit="files"
            ),
            KPICard(
                title="Orphaned Sidecars",
                value=str(len(results.get('orphaned_xmp', []))),
                status="warning" if results.get('orphaned_xmp') else "success",
                unit="files"
            )
        ]

        # Build chart sections
        file_counts = results.get('file_counts', {})
        image_labels = [ext.upper() for ext in file_counts.keys() if ext != '.xmp']
        image_counts = [file_counts[ext] for ext in file_counts.keys() if ext != '.xmp']

        sections = [
            ReportSection(
                title="Image Type Distribution",
                type="chart_pie",
                data={
                    "labels": image_labels,
                    "values": image_counts
                },
                description="Number of images by file type"
            )
        ]

        # Add Storage Distribution bar chart (storage by type in MB)
        storage_by_type = results.get('storage_by_type', {})
        if storage_by_type:
            storage_labels = [ext.upper() for ext in storage_by_type.keys()]
            storage_values_mb = [
                round(size_bytes / (1024 * 1024), 2)
                for size_bytes in storage_by_type.values()
            ]
            sections.append(
                ReportSection(
                    title="Storage Distribution",
                    type="chart_bar",
                    data={
                        "labels": storage_labels,
                        "values": storage_values_mb
                    },
                    description="Storage usage by image type (including paired sidecars) in MB"
                )
            )

        # Add file pairing status
        orphaned_count = len(results.get('orphaned_images', [])) + len(results.get('orphaned_xmp', []))
        if orphaned_count > 0:
            rows: List[List[str]] = []
            for file_path in results.get('orphaned_images', [])[:100]:
                filename = file_path.rsplit('/', 1)[-1] if '/' in file_path else file_path
                rows.append([filename, "Missing XMP sidecar"])
            for file_path in results.get('orphaned_xmp', [])[:100]:
                filename = file_path.rsplit('/', 1)[-1] if '/' in file_path else file_path
                rows.append([filename, "Missing image file"])

            sections.append(
                ReportSection(
                    title="File Pairing Status",
                    type="table",
                    data={
                        "headers": ["File", "Issue"],
                        "rows": rows
                    },
                    description=f"Found {orphaned_count} orphaned files"
                )
            )
        else:
            sections.append(
                ReportSection(
                    title="File Pairing Status",
                    type="html",
                    html_content='<div class="message-box" style="background: #d4edda; border-left: 4px solid #28a745; padding: 20px; border-radius: 8px;"><strong>All image files have corresponding XMP metadata files!</strong></div>'
                )
            )

        # Build warnings
        warnings = []
        if orphaned_count > 0:
            orphaned_details = []
            if results.get('orphaned_images'):
                orphaned_details.append(f"{len(results['orphaned_images'])} images without XMP files")
            if results.get('orphaned_xmp'):
                orphaned_details.append(f"{len(results['orphaned_xmp'])} XMP files without images")
            warnings.append(
                WarningMessage(
                    message=f"Found {orphaned_count} orphaned files",
                    details=orphaned_details,
                    severity="medium"
                )
            )

        # Build context and render using ReportRenderer
        footer_note = "Remote collection analysis" if is_remote else "Local collection analysis"
        context = ReportContext(
            tool_name="PhotoStats",
            tool_version=TOOL_VERSION,
            scan_path=display_location,
            scan_timestamp=datetime.now(),
            scan_duration=results.get('scan_time', 0),
            kpis=kpis,
            sections=sections,
            warnings=warnings,
            errors=[],
            footer_note=footer_note
        )

        renderer = ReportRenderer()
        return renderer.render_to_string(context, "photo_stats.html.j2")

    except Exception as e:
        logger.warning(f"Failed to render PhotoStats template: {e}", exc_info=True)

    # Fallback: simple HTML report
    orphaned_images = results.get('orphaned_images', [])
    orphaned_xmp = results.get('orphaned_xmp', [])
    collection_type = "Remote" if is_remote else "Local"
    return f"""
    <html>
    <head><title>PhotoStats Report</title></head>
    <body>
        <h1>PhotoStats Report ({collection_type} Collection)</h1>
        <p>Location: {location}</p>
        <p>Total Files: {results.get('total_files', 0)}</p>
        <p>Orphaned Images: {len(orphaned_images)}</p>
        <p>Orphaned XMP: {len(orphaned_xmp)}</p>
    </body>
    </html>
    """


def generate_photo_pairing_report(
    results: Dict[str, Any],
    invalid_files: list,
    location: str,
    connector: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate HTML report for Photo Pairing results using Jinja2 templates.

    Args:
        results: Photo Pairing results dictionary
        invalid_files: List of invalid file paths
        location: Collection path (display string)
        connector: Optional connector info (None for local collections)

    Returns:
        HTML report string
    """
    is_remote = connector is not None
    from utils.report_renderer import (
        ReportRenderer,
        ReportContext,
        KPICard,
        ReportSection,
        WarningMessage,
    )
    from version import __version__ as TOOL_VERSION

    try:
        display_location = location

        camera_usage = results.get('camera_usage', {})
        method_usage = results.get('method_usage', {})

        # Build KPI cards
        kpis = [
            KPICard(
                title="Total Groups",
                value=str(results.get('group_count', 0)),
                status="success",
                unit="groups"
            ),
            KPICard(
                title="Total Images",
                value=str(results.get('image_count', 0)),
                status="success",
                unit="images"
            ),
            KPICard(
                title="Cameras Used",
                value=str(len(camera_usage)),
                status="info",
                unit="cameras"
            ),
            KPICard(
                title="Processing Methods",
                value=str(len(method_usage)),
                status="info",
                unit="methods"
            ),
            KPICard(
                title="Invalid Files",
                value=str(results.get('invalid_files_count', 0)),
                status="danger" if invalid_files else "success",
                unit="files"
            )
        ]

        # Build sections
        sections = []

        # Camera usage chart
        if camera_usage:
            sections.append(
                ReportSection(
                    title="Camera Usage",
                    type="chart_pie",
                    data={
                        "labels": list(camera_usage.keys()),
                        "values": list(camera_usage.values())
                    },
                    description="Images captured by each camera"
                )
            )

        # Processing methods chart
        if method_usage:
            sections.append(
                ReportSection(
                    title="Processing Methods",
                    type="chart_bar",
                    data={
                        "labels": list(method_usage.keys()),
                        "values": list(method_usage.values())
                    },
                    description="Usage of processing methods"
                )
            )

        # Invalid files table
        if invalid_files:
            rows = [[f.rsplit('/', 1)[-1] if '/' in f else f, "Invalid filename pattern"]
                    for f in invalid_files[:100]]
            sections.append(
                ReportSection(
                    title="Invalid Filenames",
                    type="table",
                    data={
                        "headers": ["File", "Issue"],
                        "rows": rows
                    },
                    description=f"Found {len(invalid_files)} files with non-standard filenames"
                )
            )

        # Warnings
        warnings = []
        if invalid_files:
            warnings.append(
                WarningMessage(
                    message=f"Found {len(invalid_files)} files with invalid filenames",
                    details=["These files don't match the expected naming pattern"],
                    severity="medium"
                )
            )

        # Build context and render
        footer_note = "Remote collection analysis" if is_remote else "Local collection analysis"
        context = ReportContext(
            tool_name="Photo Pairing",
            tool_version=TOOL_VERSION,
            scan_path=display_location,
            scan_timestamp=datetime.now(),
            scan_duration=results.get('scan_time', 0),
            kpis=kpis,
            sections=sections,
            warnings=warnings,
            errors=[],
            footer_note=footer_note
        )

        renderer = ReportRenderer()
        return renderer.render_to_string(context, "photo_pairing.html.j2")

    except Exception as e:
        logger.warning(f"Failed to render Photo Pairing template: {e}", exc_info=True)

    # Fallback: simple HTML report
    collection_type = "Remote" if is_remote else "Local"
    return f"""
    <html>
    <head><title>Photo Pairing Report</title></head>
    <body>
        <h1>Photo Pairing Report ({collection_type} Collection)</h1>
        <p>Location: {location}</p>
        <p>Total Images: {results.get('image_count', 0)}</p>
        <p>Image Groups: {results.get('group_count', 0)}</p>
        <p>Invalid Files: {len(invalid_files)}</p>
    </body>
    </html>
    """


def generate_pipeline_validation_report(
    results: Dict[str, Any],
    validation_result: Dict[str, Any],
    location: str,
    connector: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate HTML report for pipeline validation results.

    Args:
        results: Summary results dict
        validation_result: Full validation result from run_pipeline_validation()
        location: Collection path (display string)
        connector: Optional connector info (None for local collections)

    Returns:
        HTML report string
    """
    is_remote = connector is not None
    from utils.report_renderer import (
        ReportRenderer,
        ReportContext,
        KPICard,
        ReportSection,
        WarningMessage,
    )
    from version import __version__ as TOOL_VERSION

    try:
        display_location = location

        overall_status = results.get('overall_status', {})
        consistent = overall_status.get('CONSISTENT', 0)
        partial = overall_status.get('PARTIAL', 0)
        inconsistent = overall_status.get('INCONSISTENT', 0)
        total_images = results.get('total_images', 0)

        # Determine overall validation status
        if inconsistent > 0:
            validation_status = "FAILED"
        elif partial > 0:
            validation_status = "PARTIAL"
        else:
            validation_status = "PASSED"

        # Build KPI cards
        kpis = [
            KPICard(
                title="Total Images",
                value=str(total_images),
                status="success",
                unit="images"
            ),
            KPICard(
                title="Consistent",
                value=str(consistent),
                status="success" if consistent > 0 else "muted",
                unit="images"
            ),
            KPICard(
                title="Partial",
                value=str(partial),
                status="warning" if partial > 0 else "success",
                unit="images"
            ),
            KPICard(
                title="Inconsistent",
                value=str(inconsistent),
                status="danger" if inconsistent > 0 else "success",
                unit="images"
            ),
        ]

        # Build sections
        sections = []

        # Validation status summary
        if validation_status == "PASSED":
            sections.append(
                ReportSection(
                    title="Validation Result",
                    type="html",
                    html_content='<div class="message-box" style="background: #d4edda; border-left: 4px solid #28a745; padding: 20px; border-radius: 8px;"><strong>Pipeline validation PASSED!</strong><br>All images meet the pipeline requirements.</div>'
                )
            )
        elif validation_status == "PARTIAL":
            sections.append(
                ReportSection(
                    title="Validation Result",
                    type="html",
                    html_content=f'<div class="message-box" style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 20px; border-radius: 8px;"><strong>Pipeline validation PARTIAL</strong><br>{partial} images have partial compliance with the pipeline.</div>'
                )
            )
        else:
            sections.append(
                ReportSection(
                    title="Validation Result",
                    type="html",
                    html_content=f'<div class="message-box" style="background: #f8d7da; border-left: 4px solid #dc3545; padding: 20px; border-radius: 8px;"><strong>Pipeline validation FAILED!</strong><br>{inconsistent} images are inconsistent with the pipeline requirements.</div>'
                )
            )

        # Status distribution chart (overall)
        if total_images > 0:
            sections.append(
                ReportSection(
                    title="Overall Status Distribution",
                    type="chart_pie",
                    data={
                        "labels": ["Consistent", "Partial", "Inconsistent"],
                        "values": [consistent, partial, inconsistent]
                    },
                    description="Distribution of validation statuses across all images"
                )
            )

        # Per-termination type pie charts
        by_termination = results.get('by_termination', {})
        for term_type, counts in sorted(by_termination.items()):
            term_consistent = counts.get('CONSISTENT', 0)
            term_partial = counts.get('PARTIAL', 0)
            term_inconsistent = counts.get('INCONSISTENT', 0)
            term_total = term_consistent + term_partial + term_inconsistent

            if term_total > 0:
                sections.append(
                    ReportSection(
                        title=f"{term_type} Status",
                        type="chart_pie",
                        data={
                            "labels": ["Consistent", "Partial", "Inconsistent"],
                            "values": [term_consistent, term_partial, term_inconsistent]
                        },
                        description=f"Validation status for {term_type} termination type ({term_total} images)"
                    )
                )

        # Warnings
        warnings = []
        if inconsistent > 0:
            warnings.append(
                WarningMessage(
                    message=f"{inconsistent} images are inconsistent with the pipeline",
                    details=["Review the validation results to identify missing files"],
                    severity="high"
                )
            )
        if partial > 0:
            warnings.append(
                WarningMessage(
                    message=f"{partial} images have partial compliance",
                    details=["Some expected outputs may be missing"],
                    severity="medium"
                )
            )

        # Build context and render
        footer_note = "Remote collection validation" if is_remote else "Local collection validation"
        context = ReportContext(
            tool_name="Pipeline Validation",
            tool_version=TOOL_VERSION,
            scan_path=display_location,
            scan_timestamp=datetime.now(),
            scan_duration=results.get('scan_time', 0),
            kpis=kpis,
            sections=sections,
            warnings=warnings,
            errors=[],
            footer_note=footer_note
        )

        renderer = ReportRenderer()
        return renderer.render_to_string(context, "pipeline_validation.html.j2")

    except Exception as e:
        logger.warning(f"Failed to render Pipeline Validation template: {e}", exc_info=True)

    # Fallback: simple HTML report
    overall_status = results.get('overall_status', {})
    collection_type = "Remote" if is_remote else "Local"

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Pipeline Validation Report - {collection_type} Collection</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; }}
        h1, h2 {{ color: #333; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <h1>Pipeline Validation Report ({collection_type} Collection)</h1>
    <div class="summary">
        <p><strong>Path:</strong> {location}</p>
        <p><strong>Total Images:</strong> {results.get('total_images', 0)}</p>
        <p><strong>Consistent:</strong> {overall_status.get('CONSISTENT', 0)}</p>
        <p><strong>Partial:</strong> {overall_status.get('PARTIAL', 0)}</p>
        <p><strong>Inconsistent:</strong> {overall_status.get('INCONSISTENT', 0)}</p>
    </div>
    <p><em>Generated by ShutterSense Agent</em></p>
</body>
</html>"""
