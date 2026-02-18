"""
Update CLI command for agent self-update.

Downloads the latest agent binary from the server and replaces
the current binary. Supports Linux and macOS; prints manual
instructions on Windows.

Issue #243 - Agent CLI self-update command & outdated warnings
"""

import os
import platform
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
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
from src.attestation import get_platform_identifier
from src.config import AgentConfig


# ============================================================================
# Service Detection
# ============================================================================


def _detect_service() -> Optional[dict]:
    """
    Detect how the agent is managed (systemd, launchd, or bare process).

    Returns:
        Dict with 'type' ('launchd', 'systemd', 'process', or None)
        and any relevant metadata (service_name, plist_label, pid).
    """
    system = platform.system()

    if system == "Darwin":
        # Try to detect launchd plist
        label = _detect_launchd_service()
        if label:
            return {"type": "launchd", "label": label}

    elif system == "Linux":
        # Try to detect systemd service
        service = _detect_systemd_service()
        if service:
            return {"type": "systemd", "service": service}

    # Fallback: detect running agent process
    pid = _detect_agent_process()
    if pid:
        return {"type": "process", "pid": pid}

    return None


def _detect_launchd_service() -> Optional[str]:
    """Detect a launchd plist for shuttersense-agent."""
    try:
        result = subprocess.run(
            ["launchctl", "list"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.splitlines():
            if "shuttersense" in line.lower():
                parts = line.split()
                if len(parts) >= 3:
                    return parts[-1]  # label is the last column
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None


def _detect_systemd_service() -> Optional[str]:
    """Detect a systemd service for shuttersense-agent."""
    for name in ("shuttersense-agent", "shuttersense-agent.service"):
        try:
            result = subprocess.run(
                ["systemctl", "is-enabled", name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return name
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
    return None


def _detect_agent_process() -> Optional[int]:
    """Detect a running shuttersense-agent process (not the current one)."""
    current_pid = os.getpid()
    try:
        result = subprocess.run(
            ["pgrep", "-f", "shuttersense-agent start"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.strip().splitlines():
            pid = int(line.strip())
            if pid != current_pid:
                return pid
    except (subprocess.SubprocessError, FileNotFoundError, ValueError):
        pass
    return None


# ============================================================================
# Service Control
# ============================================================================


def _stop_service(service_info: dict) -> bool:
    """
    Stop the agent service/process.

    Returns:
        True if stopped successfully, False otherwise.
    """
    stype = service_info["type"]

    try:
        if stype == "launchd":
            subprocess.run(
                ["launchctl", "stop", service_info["label"]],
                check=True,
                timeout=15,
            )
            return True

        elif stype == "systemd":
            subprocess.run(
                ["sudo", "systemctl", "stop", service_info["service"]],
                check=True,
                timeout=15,
            )
            return True

        elif stype == "process":
            os.kill(service_info["pid"], signal.SIGTERM)
            return True

    except (subprocess.SubprocessError, OSError) as e:
        click.echo(
            click.style("Warning: ", fg="yellow")
            + f"Failed to stop service: {e}"
        )
    return False


def _start_service(service_info: dict) -> bool:
    """
    Restart the agent service/process.

    Returns:
        True if started successfully, False otherwise.
    """
    stype = service_info["type"]

    try:
        if stype == "launchd":
            subprocess.run(
                ["launchctl", "start", service_info["label"]],
                check=True,
                timeout=15,
            )
            return True

        elif stype == "systemd":
            subprocess.run(
                ["sudo", "systemctl", "start", service_info["service"]],
                check=True,
                timeout=15,
            )
            return True

        elif stype == "process":
            # For bare processes, print instructions instead of auto-starting
            click.echo(
                "  The previous agent process was stopped. "
                "Please restart manually:"
            )
            click.echo(
                click.style("    shuttersense-agent start", fg="cyan")
            )
            return True

    except (subprocess.SubprocessError, OSError) as e:
        click.echo(
            click.style("Warning: ", fg="yellow")
            + f"Failed to start service: {e}"
        )
    return False


# ============================================================================
# Binary Location
# ============================================================================


def _get_current_binary_path() -> Optional[Path]:
    """
    Get the path to the currently running agent binary.

    Returns:
        Path to the binary if running as a frozen executable,
        or None if running as a Python script.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return None


# ============================================================================
# Update Logic
# ============================================================================


def _perform_update(
    config: AgentConfig,
    force: bool = False,
) -> int:
    """
    Perform the self-update.

    Steps:
    1. Check current version against server
    2. Download new binary via signed URL
    3. Verify checksum
    4. Detect service (launchd/systemd/process)
    5. Stop service
    6. Backup current binary
    7. Replace binary
    8. Set permissions
    9. Restart service
    10. Verify new version

    Args:
        config: Agent configuration
        force: Skip version check and update anyway

    Returns:
        Exit code (0 = success)
    """
    agent_platform = get_platform_identifier()

    click.echo(f"Current version: {__version__}")
    click.echo(f"Platform: {agent_platform}")
    click.echo()

    # Step 1: Get active release from server
    click.echo("Checking for updates...")
    client = AgentApiClient(
        server_url=config.server_url,
        api_key=config.api_key,
    )

    try:
        release = client.get_active_release()
    except AuthenticationError:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + "Authentication failed. Check your API key."
        )
        return 1
    except AgentConnectionError as e:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Cannot reach server: {e}"
        )
        return 1

    if not release:
        click.echo("No active release found on the server.")
        return 0

    latest_version = release["version"]

    # Find artifact for our platform
    artifact = None
    for a in release.get("artifacts", []):
        if a["platform"] == agent_platform:
            artifact = a
            break

    if not artifact:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"No binary available for platform '{agent_platform}'."
        )
        click.echo("Available platforms: " + ", ".join(
            a["platform"] for a in release.get("artifacts", [])
        ))
        return 1

    # Version check
    if not force and latest_version == __version__:
        click.echo(
            click.style("Already up to date", fg="green")
            + f" (version {__version__})."
        )
        return 0

    click.echo(f"Latest version: {latest_version}")

    signed_url = artifact.get("signed_url")
    download_url = artifact.get("download_url")
    expected_checksum = artifact.get("checksum")

    if not signed_url and not download_url:
        if release.get("dev_mode"):
            click.echo(
                click.style("Note: ", fg="yellow")
                + "Server is in development mode (no binary distribution configured)."
            )
            click.echo("Download the binary manually from the web UI.")
            return 1
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + "No download URL available."
        )
        return 1

    # Determine the binary we're replacing
    binary_path = _get_current_binary_path()
    if binary_path is None:
        click.echo(
            click.style("Note: ", fg="yellow")
            + "Running as a Python script (not a compiled binary)."
        )
        click.echo("Self-update is only supported for compiled agent binaries.")
        click.echo("To update, pull the latest code and rebuild.")
        return 1

    click.echo(f"Binary: {binary_path}")
    click.echo()

    # Step 2: Download new binary to a temp file
    url = signed_url or download_url
    click.echo("Downloading new binary...")

    tmp_dir = tempfile.mkdtemp(prefix="shuttersense-update-")
    tmp_binary = os.path.join(tmp_dir, binary_path.name)

    try:
        actual_checksum = client.download_binary(
            download_url=url,
            dest_path=tmp_binary,
            expected_checksum=expected_checksum,
        )
    except ApiError as e:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Download failed: {e}"
        )
        _cleanup_tmp(tmp_dir)
        return 1
    except AgentConnectionError as e:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Connection error during download: {e}"
        )
        _cleanup_tmp(tmp_dir)
        return 1

    click.echo(f"Download complete (checksum: {actual_checksum[:16]}...)")

    # Step 3: Detect running service
    service_info = _detect_service()
    if service_info:
        click.echo(f"Detected service: {service_info['type']}")

    # Step 4: Stop service
    if service_info:
        click.echo("Stopping agent service...")
        if not _stop_service(service_info):
            click.echo(
                click.style("Warning: ", fg="yellow")
                + "Could not stop the agent service. Continuing anyway..."
            )

    # Step 5: Backup current binary
    backup_path = str(binary_path) + ".bak"
    click.echo(f"Backing up current binary to {backup_path}...")
    try:
        shutil.copy2(str(binary_path), backup_path)
    except OSError as e:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Failed to create backup: {e}"
        )
        _cleanup_tmp(tmp_dir)
        return 1

    # Step 6: Replace binary
    click.echo("Replacing binary...")
    try:
        shutil.move(tmp_binary, str(binary_path))
    except OSError as e:
        click.echo(
            click.style("Error: ", fg="red", bold=True)
            + f"Failed to replace binary: {e}"
        )
        # Restore from backup
        click.echo("Restoring from backup...")
        try:
            shutil.move(backup_path, str(binary_path))
            click.echo("Backup restored successfully.")
        except OSError as e2:
            click.echo(
                click.style("CRITICAL: ", fg="red", bold=True)
                + f"Failed to restore backup: {e2}"
            )
            click.echo(f"Your backup is at: {backup_path}")
            click.echo(f"Manually copy it to: {binary_path}")
        _cleanup_tmp(tmp_dir)
        return 1

    # Step 7: Set permissions
    try:
        os.chmod(str(binary_path), stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
    except OSError:
        pass  # Best-effort on platforms that don't support chmod

    # Step 8: Restart service
    if service_info:
        click.echo("Restarting agent service...")
        if not _start_service(service_info):
            click.echo()
            click.echo(
                click.style("Warning: ", fg="yellow")
                + "Failed to restart the agent service."
            )
            click.echo("Please restart manually:")
            stype = service_info["type"]
            if stype == "launchd":
                click.echo(f"  launchctl start {service_info['label']}")
            elif stype == "systemd":
                click.echo(f"  sudo systemctl start {service_info['service']}")
            else:
                click.echo("  shuttersense-agent start")

    # Clean up
    _cleanup_tmp(tmp_dir)
    try:
        os.unlink(backup_path)
    except OSError:
        pass

    # Success
    click.echo()
    click.echo(
        click.style("Update successful!", fg="green", bold=True)
        + f" {__version__} -> {latest_version}"
    )

    return 0


def _cleanup_tmp(tmp_dir: str) -> None:
    """Remove temporary directory."""
    try:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except OSError:
        pass


# ============================================================================
# Click Command
# ============================================================================


@click.command()
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Force update even if already on latest version",
)
@click.pass_context
def update(ctx: click.Context, force: bool) -> None:
    """
    Update the agent to the latest version.

    Downloads the latest agent binary from the ShutterSense server,
    verifies its checksum, and replaces the current binary. If the
    agent is running as a service (launchd/systemd), it will be
    stopped and restarted automatically.

    \b
    Supported platforms:
      - macOS (darwin): Full self-update with launchd support
      - Linux: Full self-update with systemd support
      - Windows: Prints manual update instructions

    Example:

        shuttersense-agent update
        shuttersense-agent update --force
    """
    # Windows: not supported
    if platform.system() == "Windows":
        click.echo(
            click.style("Note: ", fg="yellow")
            + "Automatic updates are not supported on Windows."
        )
        click.echo()
        click.echo("To update manually:")
        click.echo("  1. Download the latest binary from the ShutterSense web UI")
        click.echo("     (Settings > Agents > Download Agent)")
        click.echo("  2. Stop the running agent (Ctrl+C or stop the service)")
        click.echo("  3. Replace the existing shuttersense-agent.exe")
        click.echo("  4. Restart the agent")
        ctx.exit(0)

    # Verify agent is registered
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

    exit_code = _perform_update(config, force=force)
    ctx.exit(exit_code)
