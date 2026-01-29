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
from typing import Any, Dict, List, Optional, Tuple

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

    # --- Step 5: Load file list and compute Input State hash ---
    location = collection_entry.location
    click.echo(f"Running {tool} on: {location}")
    click.echo(f"Collection: {collection_entry.name} ({collection_guid})")
    click.echo(f"Mode: {'offline' if offline else 'online'}")
    click.echo()

    try:
        file_infos, input_state_hash = _prepare_analysis(location, tool, team_config)
    except FileNotFoundError as e:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Path not accessible: {e}"
        )
        sys.exit(1)

    # --- Step 6: Online no-change check ---
    if not offline:
        previous = _fetch_previous_result(config, collection_guid, tool)
        if previous and previous.get("input_state_hash") == input_state_hash:
            click.echo("No changes detected since last analysis.")
            # Record NO_CHANGE result on server
            response = _record_no_change(
                config, collection_guid, tool,
                input_state_hash, previous["guid"],
            )
            if response:
                click.echo(f"  Result GUID: {response.get('result_guid', 'N/A')}")
            click.echo(f"  Source:      {previous.get('guid', 'N/A')}")
            click.echo(f"  Completed:   {previous.get('completed_at', 'N/A')}")
            sys.exit(0)

    # --- Step 7: Execute analysis ---
    start_time = time.time()
    executed_at = datetime.now(timezone.utc)

    try:
        analysis_data, report_html = _execute_tool(tool, file_infos, location, team_config)
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

    # --- Step 8: Save report if requested ---
    if output and report_html:
        output_path = Path(output)
        output_path.write_text(report_html, encoding="utf-8")
        click.echo(f"  Report saved:  {output_path}")

    # --- Step 9: Upload or store result ---
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
            input_state_hash=input_state_hash,
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
                    input_state_hash=input_state_hash,
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


def _prepare_analysis(
    location: str,
    tool: str,
    team_config: TeamConfigCache,
) -> Tuple[List, str]:
    """
    Load file list and compute Input State hash.

    Separates file loading from tool execution so the hash can be
    computed before running the tool (enabling online no-change detection).

    Args:
        location: Local filesystem path to analyze
        tool: Tool name (photostats, photo_pairing, pipeline_validation)
        team_config: Team configuration with extensions, cameras, pipeline

    Returns:
        Tuple of (file_infos list, input_state_hash string)

    Raises:
        FileNotFoundError: If the path doesn't exist or isn't a directory
    """
    from src.input_state import get_input_state_computer
    from src.remote.local_adapter import LocalAdapter

    path = Path(location)
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {location}")
    if not path.is_dir():
        raise FileNotFoundError(f"Path is not a directory: {location}")

    adapter = LocalAdapter({})
    file_infos = adapter.list_files_with_metadata(location)

    # Compute Input State hash
    computer = get_input_state_computer()
    file_hash, _ = computer.compute_file_list_hash_from_file_info(file_infos)

    # Build config dict matching the structure used by the job executor
    # and server-side hash computation (JobConfigData + pipeline).
    # Extensions must NOT be pre-sorted here — json.dumps(sort_keys=True)
    # sorts dict keys but not list values, so the list order must match
    # the server response order used by the job executor path.
    config_dict: Dict[str, Any] = {
        "photo_extensions": team_config.photo_extensions,
        "metadata_extensions": team_config.metadata_extensions,
        "require_sidecar": team_config.require_sidecar,
        "cameras": team_config.cameras,
        "processing_methods": team_config.processing_methods,
    }
    if team_config.default_pipeline:
        config_dict["pipeline"] = {
            "guid": team_config.default_pipeline.guid,
            "name": team_config.default_pipeline.name,
            "version": team_config.default_pipeline.version,
            "nodes": team_config.default_pipeline.nodes,
            "edges": team_config.default_pipeline.edges,
        }

    config_hash = computer.compute_configuration_hash(config_dict)
    input_state_hash = computer.compute_input_state_hash(file_hash, config_hash, tool)

    return file_infos, input_state_hash


def _fetch_previous_result(
    config: AgentConfig,
    collection_guid: str,
    tool: str,
) -> Optional[Dict[str, Any]]:
    """
    Fetch previous result from server for no-change comparison.

    Gracefully returns None on any error (connection, auth, 404, etc.)
    so that analysis always proceeds when the server is unreachable.

    Args:
        config: Agent configuration with server URL and API key
        collection_guid: Collection GUID
        tool: Tool name

    Returns:
        Previous result dict with guid, input_state_hash, completed_at or None
    """
    try:
        client = AgentApiClient(
            server_url=config.server_url,
            api_key=config.api_key,
        )
        return client.get_previous_result(collection_guid, tool)
    except Exception:
        return None


def _record_no_change(
    config: AgentConfig,
    collection_guid: str,
    tool: str,
    input_state_hash: str,
    source_result_guid: str,
) -> Optional[Dict[str, Any]]:
    """
    Record a NO_CHANGE result on the server.

    Gracefully returns None on any error so that the CLI still exits
    successfully (the no-change detection itself succeeded even if
    recording fails).

    Args:
        config: Agent configuration with server URL and API key
        collection_guid: Collection GUID
        tool: Tool name
        input_state_hash: SHA-256 hash of Input State
        source_result_guid: GUID of the previous result

    Returns:
        Server response dict or None on error
    """
    try:
        client = AgentApiClient(
            server_url=config.server_url,
            api_key=config.api_key,
        )
        return client.upload_no_change_result(
            collection_guid=collection_guid,
            tool=tool,
            input_state_hash=input_state_hash,
            source_result_guid=source_result_guid,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            "Failed to record no-change result on server: %s", e
        )
        return None


def _execute_tool(
    tool: str,
    file_infos: list,
    location: str,
    team_config: TeamConfigCache,
) -> tuple[Dict[str, Any], Optional[str]]:
    """
    Execute an analysis tool against pre-loaded file data.

    Args:
        tool: Tool name (photostats, photo_pairing, pipeline_validation)
        file_infos: Pre-loaded list of FileInfo objects
        location: Local filesystem path (for report display)
        team_config: Team configuration with extensions, cameras, pipeline

    Returns:
        Tuple of (analysis_data dict, optional HTML report string)

    Raises:
        Exception: If analysis fails
    """
    photo_extensions = set(team_config.photo_extensions)
    metadata_extensions = set(team_config.metadata_extensions)
    require_sidecar = set(team_config.require_sidecar)

    if tool == "photostats":
        return _run_photostats(
            file_infos, photo_extensions, metadata_extensions, require_sidecar, location
        )
    elif tool == "photo_pairing":
        return _run_photo_pairing(file_infos, photo_extensions, location)
    elif tool == "pipeline_validation":
        return _run_pipeline_validation(
            file_infos, photo_extensions, metadata_extensions, team_config, location
        )
    else:
        raise ValueError(f"Unknown tool: {tool}")


def _run_photostats(
    file_infos: list,
    photo_extensions: set[str],
    metadata_extensions: set[str],
    require_sidecar: set[str],
    location: str,
) -> tuple[Dict[str, Any], Optional[str]]:
    """Run PhotoStats analysis and generate HTML report."""
    from src.analysis.photostats_analyzer import analyze_pairing, calculate_stats
    from src.analysis.report_generators import generate_photostats_report

    stats = calculate_stats(file_infos, photo_extensions, metadata_extensions)
    pairing = analyze_pairing(
        file_infos, photo_extensions, metadata_extensions, require_sidecar
    )

    orphaned_count = len(pairing.get("orphaned_images", [])) + len(
        pairing.get("orphaned_xmp", [])
    )

    # Compute storage_by_type from file_sizes (sum of per-file sizes per extension)
    storage_by_type = {
        ext: sum(sizes)
        for ext, sizes in stats.get("file_sizes", {}).items()
    }

    results = {
        "total_files": stats.get("total_files", 0),
        "total_size": stats.get("total_size", 0),
        "file_counts": stats.get("file_counts", {}),
        "storage_by_type": storage_by_type,
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

    report_html = generate_photostats_report(results, location)
    return results, report_html


def _run_photo_pairing(
    file_infos: list,
    photo_extensions: set[str],
    location: str,
) -> tuple[Dict[str, Any], Optional[str]]:
    """Run Photo Pairing analysis and generate HTML report."""
    from src.analysis.photo_pairing_analyzer import (
        build_imagegroups,
        calculate_analytics,
    )
    from src.analysis.report_generators import generate_photo_pairing_report

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
        "invalid_files_count": len(invalid_files),
        "camera_usage": analytics.get("camera_usage", {}),
        "method_usage": analytics.get("method_usage", {}),
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

    invalid_file_paths = [f["path"] for f in invalid_files] if invalid_files and isinstance(invalid_files[0], dict) else invalid_files
    report_html = generate_photo_pairing_report(results, invalid_file_paths, location)
    return results, report_html


def _run_pipeline_validation(
    file_infos: list,
    photo_extensions: set[str],
    metadata_extensions: set[str],
    team_config: TeamConfigCache,
    location: str,
) -> tuple[Dict[str, Any], Optional[str]]:
    """Run Pipeline Validation analysis and generate HTML report."""
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
    from src.analysis.report_generators import generate_pipeline_validation_report

    pipeline = team_config.default_pipeline
    pipeline_config = build_pipeline_config(
        nodes_json=pipeline.nodes,
        edges_json=pipeline.edges,
    )

    validation_result = run_pipeline_validation(
        file_infos,
        pipeline_config=pipeline_config,
        photo_extensions=photo_extensions,
        metadata_extensions=metadata_extensions,
    )

    status_counts = validation_result.get("status_counts", {})
    issues = status_counts.get("partial", 0) + status_counts.get("inconsistent", 0)

    # Build overall_status with uppercase keys (matches job_executor format)
    overall_status = {
        "CONSISTENT": status_counts.get("consistent", 0) + status_counts.get("consistent_with_warning", 0),
        "PARTIAL": status_counts.get("partial", 0),
        "INCONSISTENT": status_counts.get("inconsistent", 0),
    }

    results = {
        "total_files": len(file_infos),
        "files_scanned": len(file_infos),
        "total_images": validation_result.get("total_images", 0),
        "overall_status": overall_status,
        "status_counts": status_counts,
        "by_termination": validation_result.get("by_termination", {}),
        "issues_found": issues,
        "issues_count": issues,
        "results": {
            "total_images": validation_result.get("total_images", 0),
            "total_groups": validation_result.get("total_groups", 0),
            "status_counts": status_counts,
            "by_termination": validation_result.get("by_termination", {}),
            "invalid_files_count": validation_result.get("invalid_files_count", 0),
        },
    }

    report_html = generate_pipeline_validation_report(results, validation_result, location)
    return results, report_html


async def _upload_result_async(
    server_url: str,
    api_key: str,
    result_id: str,
    collection_guid: str,
    tool: str,
    executed_at: str,
    analysis_data: Dict[str, Any],
    html_report: Optional[str] = None,
    input_state_hash: Optional[str] = None,
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
            input_state_hash=input_state_hash,
        )
