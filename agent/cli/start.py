"""
Start CLI command.

Starts the agent polling loop.

Issue #90 - Distributed Agent Architecture (Phase 3)
Task: T043
"""

import sys

import click

from agent.src.config import AgentConfig
from agent.src.main import run_agent


@click.command()
@click.pass_context
def start(ctx: click.Context) -> None:
    """
    Start the ShutterSense agent.

    The agent will connect to the configured server and begin polling
    for jobs. The agent must be registered first using the 'register' command.

    The agent runs continuously until stopped with Ctrl+C or SIGTERM.

    Example:

        shuttersense-agent start
    """
    # Load config and verify registration
    config = AgentConfig()

    if not config.is_registered:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + "Agent is not registered."
        )
        click.echo("Run 'shuttersense-agent register' first.")
        ctx.exit(1)

    if not config.is_configured:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + "Agent is not configured with a server URL."
        )
        ctx.exit(1)

    click.echo(f"Starting agent '{config.agent_name}'...")
    click.echo(f"  Server: {config.server_url}")
    click.echo(f"  Agent GUID: {config.agent_guid}")
    click.echo()
    click.echo("Press Ctrl+C to stop")
    click.echo()

    # Run the agent
    exit_code = run_agent()
    sys.exit(exit_code)
