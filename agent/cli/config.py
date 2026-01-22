"""
Config CLI commands.

Handles agent configuration management, particularly authorized roots.

Issue #90 - Distributed Agent Architecture (Phase 6b)
Task: T123
"""

from pathlib import Path
from typing import List, Optional

import click

from src.config import AgentConfig


# ============================================================================
# Config Command Group
# ============================================================================


@click.group()
@click.pass_context
def config(ctx: click.Context) -> None:
    """
    Manage agent configuration.

    These commands allow you to configure the agent's settings,
    including authorized local filesystem roots.
    """
    # Ensure context object exists for subcommands
    ctx.ensure_object(dict)


# ============================================================================
# Authorized Roots Commands
# ============================================================================


@config.command("set-roots")
@click.argument("paths", nargs=-1, required=True)
@click.pass_context
def set_roots(ctx: click.Context, paths: tuple) -> None:
    """
    Set authorized local filesystem roots.

    Replaces any existing authorized roots with the specified paths.
    These paths define which local directories the agent is allowed to access.

    Example:

        shuttersense-agent config set-roots /Users/photographer/Photos /Volumes/External
    """
    agent_config = AgentConfig()

    # Validate and normalize paths
    validated_paths: List[str] = []
    for path_str in paths:
        path = Path(path_str).expanduser().resolve()
        if not path.exists():
            click.echo(
                click.style("Warning: ", fg="yellow")
                + f"Path does not exist: {path_str}"
            )
        validated_paths.append(str(path))

    # Update and save config
    agent_config.authorized_roots = validated_paths
    agent_config.save()

    click.echo(click.style("Authorized roots updated:", fg="green"))
    for path in validated_paths:
        click.echo(f"  • {path}")

    # Remind user to restart agent if running
    if agent_config.is_registered:
        click.echo()
        click.echo(
            click.style("Note: ", fg="cyan")
            + "Restart the agent for changes to take effect."
        )


@config.command("get-roots")
@click.pass_context
def get_roots(ctx: click.Context) -> None:
    """
    Display current authorized roots.

    Shows the list of local filesystem paths that the agent is
    authorized to access.

    Example:

        shuttersense-agent config get-roots
    """
    agent_config = AgentConfig()
    roots = agent_config.authorized_roots

    if not roots:
        click.echo("No authorized roots configured.")
        click.echo()
        click.echo("To add roots, run:")
        click.echo(
            click.style(
                "  shuttersense-agent config set-roots /path/to/photos",
                fg="cyan",
            )
        )
        return

    click.echo("Authorized roots:")
    for path in roots:
        # Check if path exists
        exists = Path(path).exists()
        status = click.style("✓", fg="green") if exists else click.style("✗ (not found)", fg="yellow")
        click.echo(f"  {status} {path}")


@config.command("add-root")
@click.argument("path", required=True)
@click.pass_context
def add_root(ctx: click.Context, path: str) -> None:
    """
    Add a single authorized root.

    Adds the specified path to the list of authorized roots without
    removing existing ones.

    Example:

        shuttersense-agent config add-root /Volumes/External
    """
    agent_config = AgentConfig()

    # Normalize path
    normalized_path = str(Path(path).expanduser().resolve())

    # Check if already in list
    if normalized_path in agent_config.authorized_roots:
        click.echo(
            click.style("Note: ", fg="yellow")
            + f"Path is already in authorized roots: {normalized_path}"
        )
        return

    # Validate path exists
    if not Path(normalized_path).exists():
        click.echo(
            click.style("Warning: ", fg="yellow")
            + f"Path does not exist: {path}"
        )

    # Add to list and save
    agent_config.authorized_roots = agent_config.authorized_roots + [normalized_path]
    agent_config.save()

    click.echo(
        click.style("Root added: ", fg="green") + normalized_path
    )

    # Remind user to restart agent if running
    if agent_config.is_registered:
        click.echo()
        click.echo(
            click.style("Note: ", fg="cyan")
            + "Restart the agent for changes to take effect."
        )


@config.command("remove-root")
@click.argument("path", required=True)
@click.pass_context
def remove_root(ctx: click.Context, path: str) -> None:
    """
    Remove an authorized root.

    Removes the specified path from the list of authorized roots.

    Example:

        shuttersense-agent config remove-root /Volumes/OldDrive
    """
    agent_config = AgentConfig()

    # Normalize path for comparison
    normalized_path = str(Path(path).expanduser().resolve())

    # Check if in list
    if normalized_path not in agent_config.authorized_roots:
        # Also try the original path as-is
        if path not in agent_config.authorized_roots:
            click.echo(
                click.style("Error: ", fg="red")
                + f"Path not found in authorized roots: {path}"
            )
            click.echo()
            click.echo("Current authorized roots:")
            for root in agent_config.authorized_roots:
                click.echo(f"  • {root}")
            ctx.exit(1)
        # Use original path if it matches
        normalized_path = path

    # Remove from list and save
    new_roots = [r for r in agent_config.authorized_roots if r != normalized_path]
    agent_config.authorized_roots = new_roots
    agent_config.save()

    click.echo(
        click.style("Root removed: ", fg="green") + normalized_path
    )

    # Remind user to restart agent if running
    if agent_config.is_registered:
        click.echo()
        click.echo(
            click.style("Note: ", fg="cyan")
            + "Restart the agent for changes to take effect."
        )
