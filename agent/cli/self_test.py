"""
Self-test CLI command for verifying agent configuration.

Checks server connectivity, registration validity, tool availability,
and authorized root accessibility. Provides actionable remediation
suggestions for any failures.

Issue #108 - Remove CLI Direct Usage (Phase 8)
Task: T053
"""

import asyncio
import os
import time
from pathlib import Path
from typing import Optional

import click
import httpx

from src.config import AgentConfig
from src.capabilities import detect_capabilities
from src.api_client import (
    AgentApiClient,
    AuthenticationError,
    AgentRevokedError,
    ConnectionError as AgentConnectionError,
    ApiError,
)


# ============================================================================
# Result Tracking
# ============================================================================


class CheckResult:
    """Result of a single self-test check."""

    def __init__(self, label: str, status: str, detail: str = ""):
        """
        Initialize a check result.

        Args:
            label: Display label for the check
            status: "OK", "WARN", or "FAIL"
            detail: Additional detail text
        """
        self.label = label
        self.status = status
        self.detail = detail


def _format_status(status: str) -> str:
    """Format a status string with color."""
    if status == "OK":
        return click.style("OK", fg="green")
    elif status == "WARN":
        return click.style("WARN", fg="yellow")
    else:
        return click.style("FAIL", fg="red")


def _print_result(result: CheckResult, indent: int = 2) -> None:
    """Print a formatted check result."""
    prefix = " " * indent
    status = _format_status(result.status)
    if result.detail:
        click.echo(f"{prefix}{result.label}: {result.detail}  {status}")
    else:
        click.echo(f"{prefix}{result.label}  {status}")


# ============================================================================
# Check Functions
# ============================================================================


def _check_server_connection(config: AgentConfig) -> list[CheckResult]:
    """
    Check server connectivity and measure latency.

    Args:
        config: Agent configuration

    Returns:
        List of check results for server connection
    """
    results = []

    if not config.server_url:
        results.append(CheckResult(
            "URL", "FAIL",
            "(not configured)"
        ))
        return results

    results.append(CheckResult("URL", "OK", config.server_url))

    # Measure latency by hitting the health endpoint
    try:
        start = time.monotonic()
        response = httpx.get(
            f"{config.server_url.rstrip('/')}/health",
            timeout=10.0,
        )
        elapsed_ms = (time.monotonic() - start) * 1000

        if response.status_code == 200:
            results.append(CheckResult(
                "Latency", "OK", f"{elapsed_ms:.0f}ms"
            ))
        else:
            results.append(CheckResult(
                "Latency", "WARN",
                f"{elapsed_ms:.0f}ms (status {response.status_code})"
            ))
    except httpx.ConnectError:
        results.append(CheckResult(
            "Reachable", "FAIL",
            "Connection refused"
        ))
    except httpx.TimeoutException:
        results.append(CheckResult(
            "Reachable", "FAIL",
            "Connection timed out"
        ))
    except Exception as e:
        results.append(CheckResult(
            "Reachable", "FAIL",
            str(e)
        ))

    return results


def _check_registration(config: AgentConfig) -> list[CheckResult]:
    """
    Check agent registration validity by sending a heartbeat.

    Args:
        config: Agent configuration

    Returns:
        List of check results for registration
    """
    results = []

    if not config.agent_guid:
        results.append(CheckResult(
            "Agent ID", "FAIL",
            "(not registered)"
        ))
        return results

    results.append(CheckResult("Agent ID", "OK", config.agent_guid))

    if not config.api_key:
        results.append(CheckResult(
            "API Key", "FAIL",
            "(not configured)"
        ))
        return results

    if not config.server_url:
        results.append(CheckResult(
            "Status", "WARN",
            "Cannot verify (no server URL)"
        ))
        return results

    # Validate API key by sending heartbeat
    try:
        asyncio.run(_heartbeat_check(config))
        results.append(CheckResult("Status", "OK", "ONLINE"))
    except AuthenticationError:
        results.append(CheckResult(
            "Status", "FAIL",
            "Invalid API key"
        ))
    except AgentRevokedError:
        results.append(CheckResult(
            "Status", "FAIL",
            "Agent has been revoked"
        ))
    except AgentConnectionError:
        results.append(CheckResult(
            "Status", "WARN",
            "Server unreachable (cannot verify)"
        ))
    except Exception as e:
        results.append(CheckResult(
            "Status", "FAIL",
            str(e)
        ))

    return results


async def _heartbeat_check(config: AgentConfig) -> dict:
    """Send a heartbeat to verify registration."""
    async with AgentApiClient(
        server_url=config.server_url,
        api_key=config.api_key,
    ) as client:
        return await client.heartbeat(status="online")


def _check_tools() -> list[CheckResult]:
    """
    Check tool availability by detecting capabilities.

    Returns:
        List of check results for each tool
    """
    results = []

    capabilities = detect_capabilities()

    # Expected tools
    expected_tools = ["photostats", "photo_pairing", "pipeline_validation"]

    # Parse tool capabilities
    available_tools = {}
    for cap in capabilities:
        if cap.startswith("tool:"):
            parts = cap.split(":")
            if len(parts) >= 2:
                tool_name = parts[1]
                version = parts[2] if len(parts) > 2 else "unknown"
                available_tools[tool_name] = version

    for tool in expected_tools:
        if tool in available_tools:
            results.append(CheckResult(tool, "OK"))
        else:
            results.append(CheckResult(tool, "WARN", "(not found)"))

    return results


def _check_authorized_roots(config: AgentConfig) -> list[CheckResult]:
    """
    Check accessibility of authorized roots.

    Args:
        config: Agent configuration

    Returns:
        List of check results for each root
    """
    results = []

    roots = config.authorized_roots
    if not roots:
        results.append(CheckResult(
            "(none configured)", "WARN", ""
        ))
        return results

    for root_path in roots:
        path = Path(root_path)
        if not path.exists():
            results.append(CheckResult(
                root_path, "WARN", "(not mounted)"
            ))
        elif not path.is_dir():
            results.append(CheckResult(
                root_path, "WARN", "(not a directory)"
            ))
        elif not os.access(root_path, os.R_OK):
            results.append(CheckResult(
                root_path, "FAIL", "(not readable)"
            ))
        else:
            results.append(CheckResult(
                root_path, "OK", "(readable)"
            ))

    return results


# ============================================================================
# Remediation Suggestions
# ============================================================================


def _print_remediation(
    server_results: list[CheckResult],
    registration_results: list[CheckResult],
    tool_results: list[CheckResult],
    root_results: list[CheckResult],
) -> None:
    """Print remediation suggestions for any failures."""
    suggestions = []

    # Server connection issues
    for r in server_results:
        if r.status == "FAIL":
            if "not configured" in r.detail:
                suggestions.append(
                    "Register with a server: "
                    "shuttersense-agent register --server <url> --token <token>"
                )
            elif "refused" in r.detail.lower() or "timed out" in r.detail.lower():
                suggestions.append(
                    "Check that the server is running and the URL is correct"
                )
            break

    # Registration issues
    for r in registration_results:
        if r.status == "FAIL":
            if "not registered" in r.detail:
                suggestions.append(
                    "Register the agent: "
                    "shuttersense-agent register --server <url> --token <token>"
                )
            elif "Invalid API key" in r.detail:
                suggestions.append(
                    "Re-register the agent with a valid token: "
                    "shuttersense-agent register --server <url> --token <token> --force"
                )
            elif "revoked" in r.detail.lower():
                suggestions.append(
                    "This agent has been revoked by the server administrator. "
                    "Contact your admin for a new registration token."
                )
            break

    # Root access issues
    for r in root_results:
        if r.status == "WARN" and "not mounted" in r.detail:
            suggestions.append(
                f"Mount or create the directory: {r.label}"
            )
        elif r.status == "FAIL" and "not readable" in r.detail:
            suggestions.append(
                f"Fix permissions for: {r.label}"
            )

    if suggestions:
        click.echo()
        click.echo(click.style("Suggestions:", bold=True))
        for s in suggestions:
            click.echo(f"  • {s}")


# ============================================================================
# Self-Test Command
# ============================================================================


@click.command("self-test")
def self_test() -> None:
    """
    Verify agent configuration and server connectivity.

    Performs diagnostic checks to validate the agent is correctly
    configured and can communicate with the server:

    \b
    - Server connectivity (URL reachable, latency)
    - Agent registration (API key valid, not revoked)
    - Tool availability (analysis tools importable)
    - Authorized roots (configured paths accessible)

    Exit codes: 0 = all pass, 1 = warnings only, 2 = failures
    """
    config = AgentConfig()

    click.echo()
    click.echo("Agent Self-Test")
    click.echo("\u2550" * 50)

    # --- Server Connection ---
    click.echo()
    click.echo("Server Connection:")
    server_results = _check_server_connection(config)
    for r in server_results:
        _print_result(r)

    # --- Agent Registration ---
    click.echo()
    click.echo("Agent Registration:")
    registration_results = _check_registration(config)
    for r in registration_results:
        _print_result(r)

    # --- Tools ---
    click.echo()
    click.echo("Tools:")
    tool_results = _check_tools()
    for r in tool_results:
        _print_result(r)

    # --- Authorized Roots ---
    click.echo()
    click.echo("Authorized Roots:")
    root_results = _check_authorized_roots(config)
    for r in root_results:
        _print_result(r)

    # --- Summary ---
    click.echo()
    click.echo("\u2550" * 50)

    all_results = server_results + registration_results + tool_results + root_results
    failures = sum(1 for r in all_results if r.status == "FAIL")
    warnings = sum(1 for r in all_results if r.status == "WARN")

    if failures > 0:
        summary_parts = []
        if failures:
            summary_parts.append(f"{failures} failure{'s' if failures != 1 else ''}")
        if warnings:
            summary_parts.append(f"{warnings} warning{'s' if warnings != 1 else ''}")
        click.echo(
            click.style("Self-test complete: ", bold=True)
            + click.style(", ".join(summary_parts), fg="red")
        )
        _print_remediation(server_results, registration_results, tool_results, root_results)
        raise SystemExit(2)
    elif warnings > 0:
        click.echo(
            click.style("Self-test complete: ", bold=True)
            + click.style(
                f"{warnings} warning{'s' if warnings != 1 else ''}",
                fg="yellow",
            )
        )
        _print_remediation(server_results, registration_results, tool_results, root_results)
        raise SystemExit(1)
    else:
        click.echo(
            click.style("Self-test complete: ", bold=True)
            + click.style("all checks passed", fg="green")
        )
