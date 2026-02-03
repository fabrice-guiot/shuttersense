"""
ShutterSense Agent - Distributed job execution worker.

This package provides the core agent functionality for executing analysis
jobs on user-owned hardware. The agent polls the ShutterSense server for
available jobs, executes them locally, and reports progress via WebSocket.

Key modules:
- main: Entry point and main polling loop
- config: Agent configuration management
- api_client: HTTP/WebSocket client for server communication
- job_executor: Tool execution wrapper
- progress_reporter: Real-time progress streaming
- credential_store: Local encrypted credential storage
- config_loader: ApiConfigLoader for tool configuration
"""

import os
import re
import subprocess
from typing import Optional


def _run_git_command(args: list[str]) -> Optional[str]:
    """Run a Git command and return its output."""
    try:
        result = subprocess.run(
            ['git'] + args,
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _get_version_from_git() -> Optional[str]:
    """
    Get version from Git tags.

    Version Format:
    - Tagged releases: "v1.2.3"
    - Development builds: "v1.2.3-dev.5+a1b2c3d"
    - No tags: "v0.0.0-dev+a1b2c3d"
    """
    # Try to get description from tags
    describe = _run_git_command(['describe', '--tags', '--long', '--always'])

    if describe:
        # Parse git describe output: "v1.2.3-0-ga1b2c3d" or "v1.2.3-5-ga1b2c3d"
        match = re.match(r'^(.+?)-(\d+)-g([a-f0-9]+)$', describe)

        if match:
            tag, commits_since, commit_hash = match.groups()
            commits_since = int(commits_since)

            if commits_since == 0:
                return tag  # Exactly on a tag
            else:
                return f"{tag}-dev.{commits_since}+{commit_hash}"

        # No tags exist - use development version with commit hash
        commit_hash = _run_git_command(['rev-parse', '--short', 'HEAD'])
        if commit_hash:
            return f"v0.0.0-dev+{commit_hash}"

    return None


def _get_version() -> str:
    """
    Get version with priority: SHUSAI_VERSION env var > _version.py > Git tags > fallback.

    Priority:
    1. SHUSAI_VERSION env var - explicit runtime override
    2. src._version - written by build scripts with correct version
    3. Git tags - development mode (running from source)
    4. Fallback - unknown version
    """
    # First, check explicit version override (runtime)
    env_version = os.environ.get('SHUSAI_VERSION')
    if env_version:
        return env_version

    # Try _version.py (written by build scripts or hatch-vcs)
    try:
        from src._version import __version__ as built_version
        return built_version
    except ImportError:
        pass

    # Try Git tags (development mode - running from source)
    git_version = _get_version_from_git()
    if git_version:
        return git_version

    # Fallback
    return 'v0.0.0-dev+unknown'


__version__ = _get_version()
