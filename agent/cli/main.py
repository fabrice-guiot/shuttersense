"""
Agent CLI entry point.

Main command group for the ShutterSense agent CLI.

Issue #90 - Distributed Agent Architecture (Phase 3)
Task: T041
"""

import click

from src import __version__


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


# Import and register subcommands
from cli.register import register  # noqa: E402
from cli.start import start  # noqa: E402
from cli.config import config  # noqa: E402
from cli.connectors import connectors  # noqa: E402
from cli.capabilities import capabilities  # noqa: E402
from cli.test import test  # noqa: E402

cli.add_command(register)
cli.add_command(start)
cli.add_command(config)
cli.add_command(connectors)
cli.add_command(capabilities)
cli.add_command(test)


# Additional commands will be added here as they are implemented:
# - collection: Collection management (Issue #108, US2/US4)
# - run: Run analysis tool (Issue #108, US3)
# - sync: Upload offline results (Issue #108, US3)
# - self-test: Verify configuration (Issue #108, US6)


def main() -> None:
    """Main entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
