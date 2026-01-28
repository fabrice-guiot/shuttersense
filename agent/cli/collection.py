"""
Collection management CLI commands.

Provides subcommands for managing server-side Collections:
- create: Create a Collection from a local path
- list: List Collections bound to this agent
- sync: Refresh local collection cache from server
- test: Re-test a Collection's path accessibility

Issue #108 - Remove CLI Direct Usage
Tasks: T016, T025, T026, T027
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import click

from src import __version__
from src.api_client import (
    AgentApiClient,
    ApiError,
    AuthenticationError,
    ConnectionError as AgentConnectionError,
)
from src.cache import CachedCollection
from src.cache.test_cache import load_valid
from src.cache import collection_cache as col_cache
from src.config import AgentConfig


@click.group("collection")
def collection() -> None:
    """Manage Collections bound to this agent.

    Create, list, sync, and test Collections from the command line.

    \b
    Examples:
        shuttersense-agent collection create /photos/2024 --name "Vacation 2024"
        shuttersense-agent collection list
        shuttersense-agent collection sync
        shuttersense-agent collection test col_01hgw2bbg...
    """
    pass


@collection.command("create")
@click.argument("path", type=click.Path(exists=False))
@click.option(
    "--name",
    "-n",
    default=None,
    help="Collection display name (defaults to folder name).",
)
@click.option(
    "--skip-test",
    is_flag=True,
    default=False,
    help="Skip test validation (use with caution).",
)
@click.option(
    "--analyze",
    is_flag=True,
    default=False,
    help="Queue initial analysis after creation.",
)
@click.pass_context
def create(
    ctx: click.Context,
    path: str,
    name: Optional[str],
    skip_test: bool,
    analyze: bool,
) -> None:
    """Create a Collection on the server from a local path.

    PATH is the absolute path to the directory for the collection.

    Checks the local test cache for a valid entry (within 24 hours).
    If no valid cache exists and --skip-test is not set, runs the test
    command automatically before creating the collection.

    Requires server connection and a registered agent.

    \b
    Examples:
        shuttersense-agent collection create /photos/2024
        shuttersense-agent collection create /photos/2024 --name "Vacation 2024"
        shuttersense-agent collection create /photos/2024 --skip-test
    """
    resolved_path = str(Path(path).resolve())

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

    # --- Step 2: Check test cache ---
    test_entry = load_valid(resolved_path)

    if test_entry is not None:
        click.echo(f"Using cached test result for: {resolved_path}")
        click.echo(
            f"  Tested at: {test_entry.tested_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        click.echo(
            f"  Files: {test_entry.file_count:,} "
            f"({test_entry.photo_count:,} photos, {test_entry.sidecar_count:,} sidecars)"
        )
        if not test_entry.accessible:
            click.echo(
                click.style("Error: ", fg="red", bold=True)
                + "Cached test shows path is not accessible."
            )
            sys.exit(1)
    elif not skip_test:
        click.echo(f"No valid test cache found for: {resolved_path}")
        click.echo("Running test automatically...")
        click.echo()
        # Run the test command inline via Click's invoke
        from cli.test import test as test_cmd

        result = ctx.invoke(test_cmd, path=resolved_path, tool=None, check_only=True, output=None)
        # Re-load the cache after test
        test_entry = load_valid(resolved_path)
        if test_entry is None or not test_entry.accessible:
            click.echo(
                click.style("Error: ", fg="red", bold=True)
                + "Path test failed. Cannot create collection."
            )
            sys.exit(1)
        click.echo()
    else:
        click.echo(f"Skipping test for: {resolved_path}")

    # --- Step 3: Determine collection name ---
    if not name:
        default_name = Path(resolved_path).name
        name = click.prompt("Collection name", default=default_name)

    # --- Step 4: Build test results summary ---
    test_results_dict = None
    if test_entry is not None:
        test_results_dict = {
            "tested_at": test_entry.tested_at.isoformat(),
            "file_count": test_entry.file_count,
            "photo_count": test_entry.photo_count,
            "sidecar_count": test_entry.sidecar_count,
            "tools_tested": test_entry.tools_tested,
            "issues_found": test_entry.issues_found,
        }

    # --- Step 5: Create collection on server ---
    click.echo(f"\nCreating collection '{name}'...")

    try:
        result = asyncio.run(
            _create_collection_async(
                server_url=config.server_url,
                api_key=config.api_key,
                name=name,
                location=resolved_path,
                test_results=test_results_dict,
            )
        )
    except AgentConnectionError as e:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Connection failed: {e}"
        )
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
        if e.status_code == 409:
            sys.exit(3)
        sys.exit(2)
    except Exception as e:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Unexpected error: {e}"
        )
        sys.exit(2)

    # --- Step 6: Display result ---
    click.echo()
    click.echo(click.style("Collection created successfully!", fg="green", bold=True))
    click.echo(f"  GUID:     {result['guid']}")
    click.echo(f"  Name:     {result['name']}")
    click.echo(f"  Type:     {result['type']}")
    click.echo(f"  Location: {result['location']}")
    click.echo(f"  Web URL:  {result['web_url']}")

    if analyze:
        click.echo()
        click.echo("Note: --analyze flag acknowledged. Job creation will be available in a future release.")


async def _create_collection_async(
    server_url: str,
    api_key: str,
    name: str,
    location: str,
    test_results: Optional[dict] = None,
) -> dict:
    """Async helper to create collection via API client."""
    async with AgentApiClient(server_url=server_url, api_key=api_key) as client:
        return await client.create_collection(
            name=name,
            location=location,
            test_results=test_results,
        )


# ============================================================================
# list subcommand (T025)
# ============================================================================


@collection.command("list")
@click.option(
    "--type",
    "-t",
    "type_filter",
    default=None,
    type=click.Choice(["LOCAL", "S3", "GCS", "SMB"], case_sensitive=False),
    help="Filter by collection type.",
)
@click.option(
    "--status",
    "-s",
    "status_filter",
    default=None,
    type=click.Choice(["accessible", "inaccessible", "pending"], case_sensitive=False),
    help="Filter by accessibility status.",
)
@click.option(
    "--offline",
    is_flag=True,
    default=False,
    help="Use locally cached data instead of fetching from server.",
)
def list_cmd(
    type_filter: Optional[str],
    status_filter: Optional[str],
    offline: bool,
) -> None:
    """List Collections bound to this agent.

    Fetches collections from the server and displays them in tabular format.
    Use --offline to display locally cached data without server connection.

    \b
    Examples:
        shuttersense-agent collection list
        shuttersense-agent collection list --type LOCAL
        shuttersense-agent collection list --offline
    """
    # --- Load config ---
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

    if offline:
        # --- Offline mode: load from cache ---
        cache = col_cache.load()
        if cache is None:
            click.echo("No cached collection data found. Run 'collection sync' first.")
            sys.exit(1)

        click.echo(
            f"Cached data from: {cache.synced_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        if cache.is_expired():
            click.echo(
                click.style("Warning: ", fg="yellow", bold=True)
                + "Cache is expired. Run 'collection sync' to refresh."
            )
        items = cache.collections
        # Apply local filters
        if type_filter:
            items = [c for c in items if c.type == type_filter.upper()]
        if status_filter:
            if status_filter == "accessible":
                items = [c for c in items if c.is_accessible is True]
            elif status_filter == "inaccessible":
                items = [c for c in items if c.is_accessible is False]
            elif status_filter == "pending":
                items = [c for c in items if c.is_accessible is None]
        _display_collections(items, total=len(items))
    else:
        # --- Online mode: fetch from server ---
        try:
            result = asyncio.run(
                _list_collections_async(
                    server_url=config.server_url,
                    api_key=config.api_key,
                    type_filter=type_filter.upper() if type_filter else None,
                    status_filter=status_filter,
                )
            )
        except AgentConnectionError as e:
            click.echo(
                click.style("Error: ", fg="red", bold=True)
                + f"Connection failed: {e}"
            )
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

        items_data = result.get("collections", [])
        total = result.get("total_count", len(items_data))

        # Update local cache with full (unfiltered) data if no filters applied
        if not type_filter and not status_filter:
            try:
                cached_items = [
                    CachedCollection(
                        guid=c["guid"],
                        name=c["name"],
                        type=c["type"],
                        location=c["location"],
                        bound_agent_guid=c.get("bound_agent_guid"),
                        connector_guid=c.get("connector_guid"),
                        connector_name=c.get("connector_name"),
                        is_accessible=c.get("is_accessible"),
                        last_analysis_at=c.get("last_analysis_at"),
                        supports_offline=c.get("supports_offline", c["type"] == "LOCAL"),
                    )
                    for c in items_data
                ]
                cache = col_cache.make_cache(
                    agent_guid=config.agent_guid,
                    collections=cached_items,
                )
                col_cache.save(cache)
            except Exception:
                pass  # Cache update is best-effort

        _display_collections(items_data, total=total)


def _display_collections(items, total: int) -> None:
    """Display collection list in tabular format."""
    if not items:
        click.echo("No collections found.")
        return

    click.echo(f"\n{total} collection(s):\n")
    click.echo(f"  {'GUID':<34} {'Type':<6} {'Name':<30} {'Status':<12} {'Offline'}")
    click.echo(f"  {'-'*34} {'-'*6} {'-'*30} {'-'*12} {'-'*7}")

    for item in items:
        # Handle both dict (from API) and CachedCollection objects
        if isinstance(item, dict):
            guid = item.get("guid", "")
            ctype = item.get("type", "?")
            name = item.get("name", "")
            is_acc = item.get("is_accessible")
            offline = item.get("supports_offline", False)
        else:
            guid = item.guid
            ctype = item.type
            name = item.name
            is_acc = item.is_accessible
            offline = item.supports_offline

        # Format status
        if is_acc is True:
            status_str = click.style("accessible", fg="green")
        elif is_acc is False:
            status_str = click.style("inaccessible", fg="red")
        else:
            status_str = click.style("pending", fg="yellow")

        # Truncate name
        display_name = name[:28] + ".." if len(name) > 30 else name

        offline_str = "yes" if offline else "no"

        click.echo(
            f"  {guid:<34} {ctype:<6} {display_name:<30} {status_str:<21} {offline_str}"
        )


async def _list_collections_async(
    server_url: str,
    api_key: str,
    type_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> dict:
    """Async helper to list collections via API client."""
    async with AgentApiClient(server_url=server_url, api_key=api_key) as client:
        return await client.list_collections(
            type_filter=type_filter,
            status_filter=status_filter,
        )


# ============================================================================
# sync subcommand (T026)
# ============================================================================


@collection.command("sync")
def sync_cmd() -> None:
    """Refresh local collection cache from server.

    Fetches all bound Collections and updates the local cache file.
    The cache is used for offline listing and offline run commands.

    \b
    Examples:
        shuttersense-agent collection sync
    """
    # --- Load config ---
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

    click.echo("Syncing collections from server...")

    try:
        result = asyncio.run(
            _list_collections_async(
                server_url=config.server_url,
                api_key=config.api_key,
            )
        )
    except AgentConnectionError as e:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Connection failed: {e}"
        )
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

    items_data = result.get("collections", [])
    total = result.get("total_count", len(items_data))

    # Build and save cache
    try:
        cached_items = [
            CachedCollection(
                guid=c["guid"],
                name=c["name"],
                type=c["type"],
                location=c["location"],
                bound_agent_guid=c.get("bound_agent_guid"),
                connector_guid=c.get("connector_guid"),
                connector_name=c.get("connector_name"),
                is_accessible=c.get("is_accessible"),
                last_analysis_at=c.get("last_analysis_at"),
                supports_offline=c.get("supports_offline", c["type"] == "LOCAL"),
            )
            for c in items_data
        ]
        cache = col_cache.make_cache(
            agent_guid=config.agent_guid,
            collections=cached_items,
        )
        cache_path = col_cache.save(cache)
    except Exception as e:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Failed to save cache: {e}"
        )
        sys.exit(1)

    click.echo()
    click.echo(click.style("Sync complete!", fg="green", bold=True))
    click.echo(f"  Collections: {total}")
    click.echo(f"  Cache saved: {cache_path}")
    click.echo(
        f"  Synced at:   {cache.synced_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    click.echo(
        f"  Expires at:  {cache.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )

    # Summarize by type
    type_counts: dict[str, int] = {}
    for c in items_data:
        t = c.get("type", "?")
        type_counts[t] = type_counts.get(t, 0) + 1
    if type_counts:
        parts = [f"{count} {ctype}" for ctype, count in sorted(type_counts.items())]
        click.echo(f"  Types:       {', '.join(parts)}")


# ============================================================================
# test subcommand (T027)
# ============================================================================


@collection.command("test")
@click.argument("guid")
def test_cmd(guid: str) -> None:
    """Re-test a Collection's path accessibility.

    GUID is the collection identifier (e.g., col_01hgw2bbg...).

    Checks whether the collection's local path is accessible and reports
    the result to the server. Only works for LOCAL collections.

    \b
    Examples:
        shuttersense-agent collection test col_01hgw2bbg0000000000000001
    """
    # --- Load config ---
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

    # --- Find collection in cache to get path ---
    cache = col_cache.load()
    collection_entry = None
    if cache is not None:
        for c in cache.collections:
            if c.guid == guid:
                collection_entry = c
                break

    if collection_entry is None:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Collection {guid} not found in local cache. "
            + "Run 'collection sync' first."
        )
        sys.exit(1)

    if collection_entry.type != "LOCAL":
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Collection {guid} is type {collection_entry.type}. "
            + "Only LOCAL collections can be tested from the agent."
        )
        sys.exit(1)

    # --- Test path accessibility ---
    test_path = Path(collection_entry.location)
    click.echo(f"Testing path: {collection_entry.location}")

    is_accessible = False
    error_message = None
    file_count = None

    if not test_path.exists():
        error_message = "Path does not exist"
    elif not test_path.is_dir():
        error_message = "Path is not a directory"
    elif not os.access(str(test_path), os.R_OK):
        error_message = "Path is not readable"
    else:
        is_accessible = True
        try:
            file_count = sum(1 for _ in test_path.rglob("*") if _.is_file())
        except PermissionError:
            error_message = "Permission denied while scanning files"
            is_accessible = False
            file_count = None

    if is_accessible:
        click.echo(
            click.style("  Accessible: ", fg="green") + "yes"
        )
        click.echo(f"  Files found: {file_count:,}")
    else:
        click.echo(
            click.style("  Accessible: ", fg="red") + "no"
        )
        click.echo(f"  Error: {error_message}")

    # --- Report to server ---
    click.echo("\nReporting to server...")

    try:
        result = asyncio.run(
            _test_collection_async(
                server_url=config.server_url,
                api_key=config.api_key,
                collection_guid=guid,
                is_accessible=is_accessible,
                error_message=error_message,
                file_count=file_count,
            )
        )
    except AgentConnectionError as e:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Connection failed: {e}"
        )
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

    click.echo(click.style("Server updated.", fg="green"))
    click.echo(f"  Collection: {result.get('guid', guid)}")
    click.echo(f"  Accessible: {result.get('is_accessible', is_accessible)}")


async def _test_collection_async(
    server_url: str,
    api_key: str,
    collection_guid: str,
    is_accessible: bool,
    error_message: Optional[str] = None,
    file_count: Optional[int] = None,
) -> dict:
    """Async helper to test collection via API client."""
    async with AgentApiClient(server_url=server_url, api_key=api_key) as client:
        return await client.test_collection(
            collection_guid=collection_guid,
            is_accessible=is_accessible,
            error_message=error_message,
            file_count=file_count,
        )
