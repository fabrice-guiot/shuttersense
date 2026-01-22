"""
Capabilities CLI command for viewing agent capabilities.

Shows what capabilities this agent has, including:
- Built-in capabilities (local_filesystem, tools)
- Connector credentials configured locally

Issue #90 - Distributed Agent Architecture (Phase 8)
Task: T143
"""

import click
import json

from src.config import AgentConfig
from src.credential_store import CredentialStore
from src.capabilities import detect_capabilities


@click.command("capabilities")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Output as JSON",
)
def capabilities(as_json: bool):
    """
    Show agent capabilities.

    Displays all capabilities that this agent can report to the server,
    including:
    - Built-in capabilities (local_filesystem access)
    - Tool capabilities (photostats, photo_pairing, pipeline_validation)
    - Connector credentials stored locally
    """
    config = AgentConfig()
    store = CredentialStore()

    # Get built-in capabilities
    builtin_caps = detect_capabilities()

    # Get connector capabilities
    connector_guids = store.list_connector_guids()
    connector_caps = [f"connector:{guid}" for guid in connector_guids]

    # Combine all capabilities
    all_caps = builtin_caps + connector_caps

    if as_json:
        data = {
            "capabilities": all_caps,
            "builtin": builtin_caps,
            "connectors": connector_guids,
            "total": len(all_caps),
        }
        click.echo(json.dumps(data, indent=2))
        return

    click.echo()
    click.echo("Agent Capabilities")
    click.echo("=" * 50)
    click.echo()

    # Built-in capabilities
    click.echo("Built-in Capabilities:")
    for cap in builtin_caps:
        if cap == "local_filesystem":
            click.echo(f"  • {cap} - Can access local filesystem")
        elif cap.startswith("tool:"):
            parts = cap.split(":")
            tool_name = parts[1] if len(parts) > 1 else "unknown"
            version = parts[2] if len(parts) > 2 else "unknown"
            click.echo(f"  • {cap} - Tool: {tool_name} v{version}")
        else:
            click.echo(f"  • {cap}")

    click.echo()

    # Connector capabilities
    click.echo("Connector Credentials:")
    if connector_guids:
        for guid in connector_guids:
            click.echo(f"  • {guid}")
    else:
        click.echo("  (none configured)")

    click.echo()
    click.echo(f"Total capabilities: {len(all_caps)}")

    # Show authorized roots if configured
    if config.authorized_roots:
        click.echo()
        click.echo("Authorized Local Roots:")
        for root in config.authorized_roots:
            click.echo(f"  • {root}")
