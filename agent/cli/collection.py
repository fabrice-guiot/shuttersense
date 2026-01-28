"""
Collection management CLI commands.

Provides `collection create` subcommand for creating server-side
Collections from local paths. Uses test cache to avoid redundant testing.

Issue #108 - Remove CLI Direct Usage
Task: T016
"""

import asyncio
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
from src.cache.test_cache import load_valid
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
