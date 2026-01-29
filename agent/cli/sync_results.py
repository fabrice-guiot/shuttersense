"""
Sync offline results CLI command.

Uploads pending offline analysis results to the server and
cleans up local result files after successful upload.

Issue #108 - Remove CLI Direct Usage
Task: T035
"""

import asyncio
import sys
from typing import Optional

import click

from src.api_client import (
    AgentApiClient,
    ApiError,
    AuthenticationError,
    ConnectionError as AgentConnectionError,
)
from src.cache import OfflineResult
from src.cache import result_store
from src.config import AgentConfig


@click.command("sync")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="List pending results without uploading.",
)
def sync(dry_run: bool) -> None:
    """Upload offline analysis results to the server.

    Scans the local result store for pending results and uploads each one
    to the server. Successfully uploaded results are cleaned up from disk.

    Use --dry-run to preview which results would be uploaded.

    \b
    Examples:
        shuttersense-agent sync
        shuttersense-agent sync --dry-run
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

    # --- Find pending results ---
    pending = result_store.list_pending()

    if not pending:
        click.echo("No pending results to sync.")
        return

    click.echo(f"Found {len(pending)} pending result(s):\n")

    for i, result in enumerate(pending, 1):
        click.echo(
            f"  {i}. {result.tool} on {result.collection_name} "
            f"({result.collection_guid})"
        )
        click.echo(
            f"     Executed: {result.executed_at.strftime('%Y-%m-%d %H:%M:%S UTC')}  "
            f"ID: {result.result_id}"
        )

    if dry_run:
        click.echo(
            f"\nDry run: {len(pending)} result(s) would be uploaded."
        )
        return

    # --- Upload each result ---
    click.echo()
    uploaded = 0
    failed = 0

    for result in pending:
        click.echo(
            f"Uploading: {result.tool} on {result.collection_name}... ",
            nl=False,
        )

        try:
            asyncio.run(
                _upload_result_async(
                    server_url=config.server_url,
                    api_key=config.api_key,
                    result=result,
                )
            )
            # Mark as synced and delete local file
            result_store.mark_synced(result.result_id)
            result_store.delete(result.result_id)
            uploaded += 1
            click.echo(click.style("done", fg="green"))
        except AgentConnectionError as e:
            failed += 1
            click.echo(click.style(f"connection failed: {e}", fg="red"))
        except AuthenticationError as e:
            # AuthenticationError extends ApiError, so must be caught first
            failed += 1
            click.echo(click.style(f"auth failed: {e}", fg="red"))
        except ApiError as e:
            if e.status_code == 409:
                # Already uploaded - mark and clean up
                result_store.mark_synced(result.result_id)
                result_store.delete(result.result_id)
                uploaded += 1
                click.echo(click.style("already uploaded", fg="yellow"))
            else:
                failed += 1
                click.echo(click.style(f"failed: {e}", fg="red"))
        except Exception as e:
            failed += 1
            click.echo(click.style(f"error: {e}", fg="red"))

    # --- Summary ---
    click.echo()
    if failed == 0:
        click.echo(
            click.style("Sync complete!", fg="green", bold=True)
            + f" {uploaded} result(s) uploaded."
        )
    else:
        click.echo(
            click.style("Sync partially complete.", fg="yellow", bold=True)
            + f" {uploaded} uploaded, {failed} failed."
        )
        click.echo("Run 'shuttersense-agent sync' again to retry failed uploads.")
        sys.exit(2)


async def _upload_result_async(
    server_url: str,
    api_key: str,
    result: OfflineResult,
) -> dict:
    """Async helper to upload a single offline result."""
    async with AgentApiClient(server_url=server_url, api_key=api_key) as client:
        return await client.upload_result(
            result_id=result.result_id,
            collection_guid=result.collection_guid,
            tool=result.tool,
            executed_at=result.executed_at.isoformat(),
            analysis_data=result.analysis_data,
            html_report=None,  # HTML report stays local
            input_state_hash=result.input_state_hash,
        )
