"""
Agent CLI entry point.

Main command group for the ShutterSense agent CLI.

Issue #90 - Distributed Agent Architecture (Phase 3)
Task: T041
"""

import click

from src import __version__
from src.version_cache import read_cached_version_state


def _show_outdated_warning() -> None:
    """Print a warning banner if the agent is outdated (from cached heartbeat data)."""
    state = read_cached_version_state()
    if state and state.get("is_outdated"):
        latest = state.get("latest_version") or "unknown"
        click.echo(
            click.style(
                f"WARNING: This agent ({__version__}) is outdated. "
                f"Latest version: {latest}",
                fg="yellow",
                bold=True,
            )
        )
        click.echo(
            click.style(
                "Run 'shuttersense-agent update' to upgrade.",
                fg="yellow",
            )
        )
        click.echo()


@click.group()
@click.version_option(version=__version__, prog_name="shuttersense-agent")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """
    ShutterSense Agent - Distributed job execution worker.

    The ShutterSense agent runs on user-owned hardware and executes
    analysis jobs for photo collections. It communicates with the
    ShutterSense server via secure REST API.

    Use 'shuttersense-agent COMMAND --help' for more information on a command.
    """
    # Ensure context object exists for subcommands
    ctx.ensure_object(dict)

    # Show outdated warning banner on every command (Issue #243)
    _show_outdated_warning()


# Import and register subcommands
from cli.register import register  # noqa: E402
from cli.start import start  # noqa: E402
from cli.config import config  # noqa: E402
from cli.connectors import connectors  # noqa: E402
from cli.capabilities import capabilities  # noqa: E402
from cli.test import test  # noqa: E402
from cli.collection import collection  # noqa: E402
from cli.run import run  # noqa: E402
from cli.sync_results import sync  # noqa: E402
from cli.self_test import self_test  # noqa: E402
from cli.update import update  # noqa: E402

cli.add_command(register)
cli.add_command(start)
cli.add_command(config)
cli.add_command(connectors)
cli.add_command(capabilities)
cli.add_command(test)
cli.add_command(collection)
cli.add_command(run)
cli.add_command(sync)
cli.add_command(self_test)
cli.add_command(update)

# Debug commands - only available in development mode
import os as _os  # noqa: E402
if _os.environ.get("SHUSAI_DEBUG_COMMANDS", "").lower() in ("1", "true", "yes"):
    try:
        from cli.debug import debug  # noqa: E402
        cli.add_command(debug)
    except ImportError:
        pass


def main() -> None:
    """Main entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
