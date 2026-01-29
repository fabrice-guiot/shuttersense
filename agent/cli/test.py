"""
Test command for validating local paths.

Checks accessibility of a local directory, lists and categorizes files,
and optionally runs analysis tools (photostats, photo_pairing,
pipeline_validation). Results are cached for 24 hours.

When running analysis tools, team configuration is required (extensions,
camera mappings, processing methods, pipeline definition). Config is
fetched from the server if available, or loaded from cache.

Issue #108 - Remove CLI Direct Usage
Task: T009
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from src import __version__
from src.cache import VALID_TOOLS, TeamConfigCache
from src.cache.test_cache import load_valid, make_entry, save
from src.config import AgentConfig
from src.config_resolver import resolve_team_config
from src.remote.base import FileInfo
from src.remote.local_adapter import LocalAdapter

# Auto-generated report filename patterns per tool
_REPORT_FILENAMES = {
    "photostats": "photo_stats_report",
    "photo_pairing": "photo_pairing_report",
    "pipeline_validation": "pipeline_validation_report",
}

# Default extensions used only for --check-only mode (file categorization)
DEFAULT_PHOTO_EXTENSIONS = {".dng", ".cr3", ".tiff", ".tif"}
DEFAULT_METADATA_EXTENSIONS = {".xmp"}
DEFAULT_REQUIRE_SIDECAR = {".cr3"}


def _categorize_files(
    files: list[FileInfo],
    photo_extensions: set[str],
    metadata_extensions: set[str],
) -> tuple[int, int, int]:
    """Categorize files into totals, photos, and sidecars.

    Returns:
        Tuple of (total_files, photo_count, sidecar_count)
    """
    photo_count = 0
    sidecar_count = 0
    for f in files:
        ext = f.extension
        if ext in photo_extensions:
            photo_count += 1
        elif ext in metadata_extensions:
            sidecar_count += 1
    return len(files), photo_count, sidecar_count


def _run_photostats(
    files: list[FileInfo],
    photo_extensions: set[str],
    metadata_extensions: set[str],
    require_sidecar: set[str],
) -> dict:
    """Run photostats analysis and return results."""
    from src.analysis.photostats_analyzer import analyze_pairing, calculate_stats

    stats = calculate_stats(files, photo_extensions, metadata_extensions)
    pairing = analyze_pairing(
        files, photo_extensions, metadata_extensions, require_sidecar
    )
    return {"stats": stats, "pairing": pairing}


def _run_photo_pairing(
    files: list[FileInfo],
    photo_extensions: set[str],
) -> dict:
    """Run photo pairing analysis and return results."""
    from src.analysis.photo_pairing_analyzer import build_imagegroups

    # Filter to photo files using team config extensions
    photo_files = [f for f in files if f.extension in photo_extensions]
    result = build_imagegroups(photo_files)
    return result


def _run_pipeline_validation(
    files: list[FileInfo],
    photo_extensions: set[str],
    metadata_extensions: set[str],
    team_config: Optional[TeamConfigCache],
) -> dict:
    """Run pipeline validation analysis and return results.

    Requires a cached pipeline definition from the team config.
    If no pipeline is available, returns a skipped result.
    """
    if team_config is None or team_config.default_pipeline is None:
        return {
            "skipped": True,
            "reason": "No default pipeline definition available. "
                      "Configure a default pipeline on the server.",
            "status_counts": {},
        }

    from src.analysis.pipeline_analyzer import run_pipeline_validation
    from src.analysis.pipeline_config_builder import build_pipeline_config

    pipeline = team_config.default_pipeline
    pipeline_config = build_pipeline_config(
        nodes_json=pipeline.nodes,
        edges_json=pipeline.edges,
    )

    result = run_pipeline_validation(
        files,
        pipeline_config=pipeline_config,
        photo_extensions=photo_extensions,
        metadata_extensions=metadata_extensions,
    )
    return result


def _count_issues(tool: str, result: dict) -> int:
    """Count issues from a tool result."""
    if tool == "photostats":
        pairing = result.get("pairing", {})
        orphaned_images = len(pairing.get("orphaned_images", []))
        orphaned_xmp = len(pairing.get("orphaned_xmp", []))
        return orphaned_images + orphaned_xmp
    elif tool == "photo_pairing":
        return len(result.get("invalid_files", []))
    elif tool == "pipeline_validation":
        if result.get("skipped"):
            return 0
        status_counts = result.get("status_counts", {})
        return status_counts.get("partial", 0) + status_counts.get("inconsistent", 0)
    return 0


def _generate_report_for_tool(
    tool: str,
    result: dict,
    location: str,
) -> Optional[str]:
    """Generate an HTML report string for a tool result.

    Args:
        tool: Tool name (photostats, photo_pairing, pipeline_validation)
        result: Raw result dict from the tool's _run_* function
        location: Directory path being analyzed

    Returns:
        HTML report string, or None if the tool was skipped
    """
    if result.get("skipped"):
        return None

    from src.analysis.report_generators import (
        generate_photo_pairing_report,
        generate_photostats_report,
        generate_pipeline_validation_report,
    )

    if tool == "photostats":
        stats = result.get("stats", {})
        pairing = result.get("pairing", {})
        # Build the results dict expected by the report generator
        storage_by_type = {
            ext: sum(sizes)
            for ext, sizes in stats.get("file_sizes", {}).items()
        }
        report_data = {
            "total_files": stats.get("total_files", 0),
            "total_size": stats.get("total_size", 0),
            "file_counts": stats.get("file_counts", {}),
            "storage_by_type": storage_by_type,
            "orphaned_images": pairing.get("orphaned_images", []),
            "orphaned_xmp": pairing.get("orphaned_xmp", []),
        }
        return generate_photostats_report(report_data, location)

    elif tool == "photo_pairing":
        from src.analysis.photo_pairing_analyzer import calculate_analytics

        imagegroups = result.get("imagegroups", [])
        invalid_files = result.get("invalid_files", [])
        analytics = calculate_analytics(imagegroups, {})
        report_data = {
            "image_count": analytics.get("image_count", 0),
            "group_count": analytics.get("group_count", 0),
            "camera_usage": analytics.get("camera_usage", {}),
            "method_usage": analytics.get("method_usage", {}),
            "invalid_files_count": len(invalid_files),
        }
        invalid_file_paths = (
            [f["path"] for f in invalid_files]
            if invalid_files and isinstance(invalid_files[0], dict)
            else invalid_files
        )
        return generate_photo_pairing_report(report_data, invalid_file_paths, location)

    elif tool == "pipeline_validation":
        status_counts = result.get("status_counts", {})
        overall_status = {
            "CONSISTENT": status_counts.get("consistent", 0)
            + status_counts.get("consistent_with_warning", 0),
            "PARTIAL": status_counts.get("partial", 0),
            "INCONSISTENT": status_counts.get("inconsistent", 0),
        }
        report_data = {
            "total_images": result.get("total_images", 0),
            "overall_status": overall_status,
            "by_termination": result.get("by_termination", {}),
        }
        return generate_pipeline_validation_report(report_data, result, location)

    return None


@click.command("test")
@click.argument("path", type=click.Path(exists=False))
@click.option(
    "--tool",
    type=click.Choice(sorted(VALID_TOOLS), case_sensitive=False),
    default=None,
    help="Run only this analysis tool (default: all).",
)
@click.option(
    "--check-only",
    is_flag=True,
    default=False,
    help="Only check accessibility, skip analysis.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default=None,
    help="Save HTML report. File path with --tool, directory path without.",
)
def test(path: str, tool: Optional[str], check_only: bool, output: Optional[str]) -> None:
    """Test a local directory for accessibility and run analysis tools.

    PATH is the absolute path to the directory to test.

    Checks whether the directory is readable and counts files. Optionally
    runs photostats, photo_pairing, or pipeline_validation analysis.
    Results are cached locally for 24 hours.

    Analysis tools require team configuration from the server (extensions,
    camera mappings, processing methods, pipeline definition). Use
    --check-only to skip analysis when the server is unavailable and no
    cached config exists.

    \b
    Examples:
        shuttersense-agent test /photos/2024
        shuttersense-agent test /photos/2024 --check-only
        shuttersense-agent test /photos/2024 --tool photostats
        shuttersense-agent test /photos/2024 --tool photostats -o report.html
        shuttersense-agent test /photos/2024 -o ./reports/
    """
    resolved_path = str(Path(path).resolve())

    # Validate --output semantics early
    if output and not tool:
        output_path = Path(output)
        # If --output looks like a file (has .html extension) but no --tool, error
        if output_path.suffix.lower() == ".html":
            click.echo(
                click.style("Error: ", fg="red", bold=True)
                + "Cannot write all tool reports to a single file.\n"
                "  Use --tool to select a specific tool, or specify a directory "
                "to save all reports.\n"
                "  Example: --tool photostats --output report.html\n"
                "  Example: --output ./reports/"
            )
            sys.exit(1)

    click.echo(f"Testing path: {resolved_path}")

    # --- Step 1: Check accessibility ---
    click.echo("  Checking accessibility... ", nl=False)
    adapter = LocalAdapter({})
    try:
        files = adapter.list_files_with_metadata(resolved_path)
    except FileNotFoundError:
        click.echo(click.style("FAIL", fg="red", bold=True))
        click.echo(f"  Error: Path does not exist: {resolved_path}")
        sys.exit(1)
    except PermissionError:
        click.echo(click.style("FAIL", fg="red", bold=True))
        click.echo(f"  Error: Permission denied: {resolved_path}")
        sys.exit(1)
    except Exception as e:
        click.echo(click.style("FAIL", fg="red", bold=True))
        click.echo(f"  Error: {e}")
        sys.exit(1)

    click.echo(
        click.style("OK", fg="green", bold=True)
        + f" (readable, {len(files):,} files found)"
    )

    if check_only:
        # Use default extensions for basic categorization
        file_count, photo_count, sidecar_count = _categorize_files(
            files, DEFAULT_PHOTO_EXTENSIONS, DEFAULT_METADATA_EXTENSIONS
        )
        _save_cache(
            resolved_path, True, file_count, photo_count, sidecar_count, [], None
        )
        _print_summary(file_count, photo_count, sidecar_count, {})
        sys.exit(0)

    # --- Step 2: Resolve team config for analysis tools ---
    click.echo("  Fetching team config... ", nl=False)
    result = resolve_team_config()

    if result.config is None:
        click.echo(click.style("FAIL", fg="red", bold=True))
        click.echo(
            click.style("  Error: ", fg="red", bold=True)
            + f"{result.message}\n"
            "  Team configuration is required to run analysis tools.\n"
            "  Use --check-only for accessibility testing without analysis."
        )
        sys.exit(1)

    team_config = result.config
    if result.source == "expired_cache":
        click.echo(click.style("WARN", fg="yellow", bold=True) + f" ({result.message})")
    elif result.source == "cache":
        click.echo(click.style("OK", fg="green", bold=True) + f" ({result.message})")
    else:
        click.echo(click.style("OK", fg="green", bold=True) + f" ({result.message})")

    # Use team config for extensions
    photo_extensions = set(team_config.photo_extensions)
    metadata_extensions = set(team_config.metadata_extensions)
    require_sidecar = set(team_config.require_sidecar)

    # Categorize files with real config
    file_count, photo_count, sidecar_count = _categorize_files(
        files, photo_extensions, metadata_extensions
    )

    # --- Step 3: Run analysis tools ---
    tools_to_run = [tool] if tool else sorted(VALID_TOOLS)
    tools_tested: list[str] = []
    issues_found: dict = {}
    all_results: dict = {}

    for t in tools_to_run:
        click.echo(f"  Running {t}... ", nl=False)
        try:
            if t == "photostats":
                result = _run_photostats(
                    files, photo_extensions, metadata_extensions, require_sidecar
                )
            elif t == "photo_pairing":
                result = _run_photo_pairing(files, photo_extensions)
            elif t == "pipeline_validation":
                result = _run_pipeline_validation(
                    files, photo_extensions, metadata_extensions, team_config
                )
            else:
                click.echo(click.style("SKIP", fg="yellow"))
                continue

            all_results[t] = result
            tools_tested.append(t)

            # Handle skipped tools (e.g., pipeline_validation without pipeline)
            if result.get("skipped"):
                reason = result.get("reason", "")
                click.echo(
                    click.style("SKIP", fg="yellow")
                    + f" ({reason})"
                )
                continue

            issue_count = _count_issues(t, result)
            if issue_count > 0:
                issues_found[t] = issue_count
            click.echo(click.style("OK", fg="green", bold=True) + " (analysis complete)")
        except Exception as e:
            click.echo(click.style("FAIL", fg="red", bold=True))
            click.echo(f"    Error: {e}")
            issues_found[t] = {"error": str(e)}
            # Continue with other tools — don't exit on individual failure

    # --- Step 3: Save to cache ---
    _save_cache(
        resolved_path,
        True,
        file_count,
        photo_count,
        sidecar_count,
        tools_tested,
        issues_found if issues_found else None,
    )

    # --- Step 4: Output report if requested ---
    if output and all_results:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        if tool:
            # Single tool → write to the specified file path
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            result_data = all_results.get(tool)
            if result_data and not result_data.get("skipped"):
                report_html = _generate_report_for_tool(tool, result_data, resolved_path)
                if report_html:
                    output_path.write_text(report_html, encoding="utf-8")
                    click.echo(f"  Report saved: {output_path}")
        else:
            # All tools → treat output as a directory
            output_dir = Path(output)
            output_dir.mkdir(parents=True, exist_ok=True)
            for t, result_data in all_results.items():
                if result_data.get("skipped"):
                    continue
                report_html = _generate_report_for_tool(t, result_data, resolved_path)
                if report_html:
                    base_name = _REPORT_FILENAMES.get(t, f"{t}_report")
                    report_path = output_dir / f"{base_name}_{timestamp}.html"
                    report_path.write_text(report_html, encoding="utf-8")
                    click.echo(f"  Report saved: {report_path}")

    # --- Step 5: Print summary ---
    _print_summary(file_count, photo_count, sidecar_count, issues_found)

    # Exit code 2 if any analysis tool had errors (not just issues)
    has_errors = any(
        isinstance(v, dict) and "error" in v for v in issues_found.values()
    )
    if has_errors:
        sys.exit(2)


def _save_cache(
    path: str,
    accessible: bool,
    file_count: int,
    photo_count: int,
    sidecar_count: int,
    tools_tested: list[str],
    issues_found: Optional[dict],
) -> None:
    """Save test results to the local cache."""
    try:
        config = AgentConfig()
        agent_id = config.agent_guid or "unregistered"
    except Exception:
        agent_id = "unregistered"

    entry = make_entry(
        path=path,
        accessible=accessible,
        file_count=file_count,
        photo_count=photo_count,
        sidecar_count=sidecar_count,
        tools_tested=tools_tested,
        agent_id=agent_id,
        agent_version=__version__,
        issues_found=issues_found,
    )
    try:
        save(entry)
    except OSError as e:
        click.echo(f"  Warning: Failed to save cache: {e}", err=True)


def _print_summary(
    file_count: int,
    photo_count: int,
    sidecar_count: int,
    issues_found: dict,
) -> None:
    """Print the test summary."""
    click.echo("")
    click.echo("Test Summary:")
    other_count = file_count - photo_count - sidecar_count
    parts = [f"{photo_count:,} photos", f"{sidecar_count:,} sidecars"]
    if other_count > 0:
        parts.append(f"{other_count:,} other")
    click.echo(f"  Files: {file_count:,} ({', '.join(parts)})")

    total_issues = 0
    issue_details: list[str] = []
    for tool_name, count_or_detail in issues_found.items():
        if isinstance(count_or_detail, int):
            total_issues += count_or_detail
            issue_details.append(f"{count_or_detail} from {tool_name}")
        elif isinstance(count_or_detail, dict) and "error" in count_or_detail:
            issue_details.append(f"{tool_name}: error")

    if total_issues > 0:
        click.echo(f"  Issues: {total_issues} ({', '.join(issue_details)})")
    elif issue_details:
        click.echo(f"  Issues: {', '.join(issue_details)}")
    else:
        click.echo("  Issues: None")

    has_errors = any(
        isinstance(v, dict) and "error" in v for v in issues_found.values()
    )
    if has_errors:
        ready_text = click.style("No", fg="red") + " (tool errors must be resolved first)"
    elif total_issues > 0:
        ready_text = (
            click.style("Yes", fg="green")
            + ", but consider resolving the issues first"
        )
    else:
        ready_text = click.style("Yes", fg="green")
    click.echo(f"  Ready to create Collection: {ready_text}")
