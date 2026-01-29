"""
Run analysis tool CLI command.

Executes an analysis tool against a Collection identified by GUID.
Online mode executes and uploads results to server.
Offline mode executes locally and stores results for later sync.

Issue #108 - Remove CLI Direct Usage
Task: T034
"""

import asyncio
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import click

from src import __version__
from src.api_client import (
    AgentApiClient,
    ApiError,
    AuthenticationError,
    ConnectionError as AgentConnectionError,
)
from src.cache import VALID_TOOLS, OfflineResult, TeamConfigCache
from src.cache import collection_cache as col_cache
from src.cache import result_store
from src.config import AgentConfig
from src.config_resolver import resolve_team_config


@click.command("run")
@click.argument("collection_guid")
@click.option(
    "--tool",
    "-t",
    required=True,
    type=click.Choice(sorted(VALID_TOOLS), case_sensitive=False),
    help="Analysis tool to run.",
)
@click.option(
    "--offline",
    is_flag=True,
    default=False,
    help="Run locally and store result for later sync.",
)
@click.option(
    "--output",
    "-o",
    default=None,
    type=click.Path(),
    help="Save HTML report to this path.",
)
def run(
    collection_guid: str,
    tool: str,
    offline: bool,
    output: Optional[str],
) -> None:
    """Run an analysis tool against a Collection.

    COLLECTION_GUID is the collection identifier (e.g., col_01hgw2bbg...).

    Online mode executes the tool locally and uploads results to the server.
    Offline mode executes locally and stores results for later sync with
    'shuttersense-agent sync'.

    \b
    Examples:
        shuttersense-agent run col_01hgw... --tool photostats
        shuttersense-agent run col_01hgw... --tool photo_pairing --offline
        shuttersense-agent run col_01hgw... --tool photostats --output report.html
    """
    # --- Step 1: Load agent config ---
    try:
        config = AgentConfig()
    except Exception as e:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Failed to load agent config: {e}"
        )
        sys.exit(1)

    if not config.is_registered:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + "Agent is not registered. Run 'shuttersense-agent register' first."
        )
        sys.exit(1)

    # --- Step 2: Find collection in cache ---
    cache = col_cache.load()
    collection_entry = None
    if cache is not None:
        for c in cache.collections:
            if c.guid == collection_guid:
                collection_entry = c
                break

    if collection_entry is None:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Collection {collection_guid} not found in local cache. "
            + "Run 'collection sync' first."
        )
        sys.exit(1)

    # --- Step 3: Validate offline constraints ---
    if offline and collection_entry.type != "LOCAL":
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Collection {collection_guid} is type {collection_entry.type}. "
            + "Offline mode only supports LOCAL collections."
        )
        sys.exit(1)

    if not offline and collection_entry.type != "LOCAL":
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + "Remote collection execution is not yet supported via CLI. "
            + "Use the web UI to create jobs for remote collections."
        )
        sys.exit(1)

    # --- Step 4: Resolve team config ---
    click.echo("Fetching team config... ", nl=False)
    result = resolve_team_config()

    if result.config is None:
        click.echo(click.style("FAIL", fg="red", bold=True))
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"{result.message}\n"
            "  Team configuration is required to run analysis tools."
        )
        sys.exit(1)

    team_config = result.config
    if result.source == "expired_cache":
        click.echo(click.style("WARN", fg="yellow", bold=True) + f" ({result.message})")
    elif result.source == "cache":
        click.echo(click.style("OK", fg="green", bold=True) + f" ({result.message})")
    else:
        click.echo(click.style("OK", fg="green", bold=True) + f" ({result.message})")

    # --- Step 5: Execute analysis ---
    location = collection_entry.location
    click.echo(f"Running {tool} on: {location}")
    click.echo(f"Collection: {collection_entry.name} ({collection_guid})")
    click.echo(f"Mode: {'offline' if offline else 'online'}")
    click.echo()

    start_time = time.time()
    executed_at = datetime.now(timezone.utc)

    try:
        analysis_data, report_html = _execute_tool(tool, location, team_config)
    except FileNotFoundError as e:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Path not accessible: {e}"
        )
        sys.exit(1)
    except Exception as e:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Analysis failed: {e}"
        )
        sys.exit(1)

    elapsed = time.time() - start_time
    click.echo(f"Analysis complete in {elapsed:.1f}s")

    # Display summary
    files_scanned = (
        analysis_data.get("total_files")
        or analysis_data.get("files_scanned")
        or 0
    )
    issues_count = (
        analysis_data.get("issues_count")
        or analysis_data.get("issues_found")
        or 0
    )
    click.echo(f"  Files scanned: {files_scanned:,}")
    click.echo(f"  Issues found:  {issues_count}")

    # --- Step 5: Save report if requested ---
    if output and report_html:
        output_path = Path(output)
        output_path.write_text(report_html, encoding="utf-8")
        click.echo(f"  Report saved:  {output_path}")

    # --- Step 6: Upload or store result ---
    if offline:
        # Save to local result store
        offline_result = OfflineResult(
            collection_guid=collection_guid,
            collection_name=collection_entry.name,
            tool=tool,
            executed_at=executed_at,
            agent_guid=config.agent_guid,
            agent_version=__version__,
            analysis_data=analysis_data,
            html_report_path=output if output else None,
        )
        result_path = result_store.save(offline_result)
        click.echo()
        click.echo(click.style("Result saved locally.", fg="green", bold=True))
        click.echo(f"  Result ID:  {offline_result.result_id}")
        click.echo(f"  Saved to:   {result_path}")
        click.echo("  Run 'shuttersense-agent sync' to upload to server.")
    else:
        # Upload to server
        click.echo()
        click.echo("Uploading result to server...")

        import uuid

        result_id = str(uuid.uuid4())
        try:
            upload_response = asyncio.run(
                _upload_result_async(
                    server_url=config.server_url,
                    api_key=config.api_key,
                    result_id=result_id,
                    collection_guid=collection_guid,
                    tool=tool,
                    executed_at=executed_at.isoformat(),
                    analysis_data=analysis_data,
                    html_report=report_html,
                )
            )
        except AgentConnectionError as e:
            click.echo(
                click.style("Error: ", fg="red", bold=True)
                + f"Connection failed: {e}"
            )
            click.echo("Tip: Use --offline to save results locally for later sync.")
            sys.exit(2)
        except AuthenticationError as e:
            click.echo(
                click.style("Error: ", fg="red", bold=True)
                + f"Authentication failed: {e}"
            )
            sys.exit(2)
        except ApiError as e:
            click.echo(
                click.style("Error: ", fg="red", bold=True)
                + f"{e}"
            )
            sys.exit(2)
        except Exception as e:
            click.echo(
                click.style("Error: ", fg="red", bold=True)
                + f"Unexpected error: {e}"
            )
            sys.exit(2)

        click.echo(click.style("Result uploaded successfully!", fg="green", bold=True))
        click.echo(f"  Job GUID:    {upload_response.get('job_guid', 'N/A')}")
        click.echo(f"  Result GUID: {upload_response.get('result_guid', 'N/A')}")


def _execute_tool(
    tool: str,
    location: str,
    team_config: TeamConfigCache,
) -> tuple[Dict[str, Any], Optional[str]]:
    """
    Execute an analysis tool against a local path.

    Args:
        tool: Tool name (photostats, photo_pairing, pipeline_validation)
        location: Local filesystem path to analyze
        team_config: Team configuration with extensions, cameras, pipeline

    Returns:
        Tuple of (analysis_data dict, optional HTML report string)

    Raises:
        FileNotFoundError: If the path doesn't exist
        Exception: If analysis fails
    """
    from src.remote.local_adapter import LocalAdapter

    path = Path(location)
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {location}")
    if not path.is_dir():
        raise FileNotFoundError(f"Path is not a directory: {location}")

    adapter = LocalAdapter({})
    file_infos = adapter.list_files_with_metadata(location)

    photo_extensions = set(team_config.photo_extensions)
    metadata_extensions = set(team_config.metadata_extensions)
    require_sidecar = set(team_config.require_sidecar)

    if tool == "photostats":
        return _run_photostats(
            file_infos, photo_extensions, metadata_extensions, require_sidecar
        )
    elif tool == "photo_pairing":
        return _run_photo_pairing(file_infos, photo_extensions)
    elif tool == "pipeline_validation":
        return _run_pipeline_validation(
            file_infos, photo_extensions, metadata_extensions, team_config
        )
    else:
        raise ValueError(f"Unknown tool: {tool}")


def _run_photostats(
    file_infos: list,
    photo_extensions: set[str],
    metadata_extensions: set[str],
    require_sidecar: set[str],
) -> tuple[Dict[str, Any], Optional[str]]:
    """Run PhotoStats analysis."""
    from src.analysis.photostats_analyzer import analyze_pairing, calculate_stats

    stats = calculate_stats(file_infos, photo_extensions, metadata_extensions)
    pairing = analyze_pairing(
        file_infos, photo_extensions, metadata_extensions, require_sidecar
    )

    orphaned_count = len(pairing.get("orphaned_images", [])) + len(
        pairing.get("orphaned_xmp", [])
    )

    results = {
        "total_files": stats.get("total_files", 0),
        "total_size": stats.get("total_size", 0),
        "file_counts": stats.get("file_counts", {}),
        "orphaned_images": pairing.get("orphaned_images", []),
        "orphaned_xmp": pairing.get("orphaned_xmp", []),
        "files_scanned": stats.get("total_files", 0),
        "issues_found": orphaned_count,
        "issues_count": orphaned_count,
        "results": {
            "total_files": stats.get("total_files", 0),
            "total_size": stats.get("total_size", 0),
            "file_counts": stats.get("file_counts", {}),
            "orphaned_images": pairing.get("orphaned_images", []),
            "orphaned_xmp": pairing.get("orphaned_xmp", []),
        },
    }

    return results, None  # No HTML report in CLI mode for now


def _run_photo_pairing(
    file_infos: list,
    photo_extensions: set[str],
) -> tuple[Dict[str, Any], Optional[str]]:
    """Run Photo Pairing analysis."""
    from src.analysis.photo_pairing_analyzer import (
        build_imagegroups,
        calculate_analytics,
    )

    # Filter to photo files only
    photo_files = [f for f in file_infos if f.extension in photo_extensions]

    group_result = build_imagegroups(photo_files)
    imagegroups = group_result.get("imagegroups", [])
    invalid_files = group_result.get("invalid_files", [])

    analytics = calculate_analytics(imagegroups, {})

    results = {
        "total_files": len(file_infos),
        "photo_files": len(photo_files),
        "image_count": analytics.get("image_count", 0),
        "group_count": analytics.get("group_count", 0),
        "invalid_files": len(invalid_files),
        "camera_usage": analytics.get("camera_usage", {}),
        "files_scanned": len(file_infos),
        "issues_found": len(invalid_files),
        "issues_count": len(invalid_files),
        "results": {
            "image_count": analytics.get("image_count", 0),
            "group_count": analytics.get("group_count", 0),
            "file_count": analytics.get("file_count", 0),
            "invalid_files": invalid_files,
            "camera_usage": analytics.get("camera_usage", {}),
        },
    }

    return results, None


def _run_pipeline_validation(
    file_infos: list,
    photo_extensions: set[str],
    metadata_extensions: set[str],
    team_config: TeamConfigCache,
) -> tuple[Dict[str, Any], Optional[str]]:
    """Run Pipeline Validation analysis using cached pipeline config."""
    if team_config.default_pipeline is None:
        click.echo(
            click.style("Warning: ", fg="yellow")
            + "No default pipeline configured on the server. "
            "Skipping pipeline validation."
        )
        results = {
            "total_files": len(file_infos),
            "files_scanned": len(file_infos),
            "issues_found": 0,
            "issues_count": 0,
            "skipped": True,
            "results": {
                "total_files": len(file_infos),
                "note": "No default pipeline definition available. "
                        "Configure a default pipeline on the server.",
            },
        }
        return results, None

    from src.analysis.pipeline_analyzer import run_pipeline_validation
    from src.analysis.pipeline_config_builder import build_pipeline_config

    pipeline = team_config.default_pipeline
    pipeline_config = build_pipeline_config(
        nodes_json=pipeline.nodes,
        edges_json=pipeline.edges,
    )

    result = run_pipeline_validation(
        file_infos,
        pipeline_config=pipeline_config,
        photo_extensions=photo_extensions,
        metadata_extensions=metadata_extensions,
    )

    status_counts = result.get("status_counts", {})
    issues = status_counts.get("partial", 0) + status_counts.get("inconsistent", 0)

    results = {
        "total_files": len(file_infos),
        "files_scanned": len(file_infos),
        "total_images": result.get("total_images", 0),
        "status_counts": status_counts,
        "by_termination": result.get("by_termination", {}),
        "issues_found": issues,
        "issues_count": issues,
        "results": {
            "total_images": result.get("total_images", 0),
            "total_groups": result.get("total_groups", 0),
            "status_counts": status_counts,
            "by_termination": result.get("by_termination", {}),
            "invalid_files_count": result.get("invalid_files_count", 0),
        },
    }

    return results, None


async def _upload_result_async(
    server_url: str,
    api_key: str,
    result_id: str,
    collection_guid: str,
    tool: str,
    executed_at: str,
    analysis_data: Dict[str, Any],
    html_report: Optional[str] = None,
) -> dict:
    """Async helper to upload result via API client."""
    async with AgentApiClient(server_url=server_url, api_key=api_key) as client:
        return await client.upload_result(
            result_id=result_id,
            collection_guid=collection_guid,
            tool=tool,
            executed_at=executed_at,
            analysis_data=analysis_data,
            html_report=html_report,
        )
