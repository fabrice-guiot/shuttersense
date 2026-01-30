"""
Version management for ShutterSense toolbox.

This module provides a single source of truth for version information across
all CLI tools, backend API, and frontend. It automatically determines the version
from Git tags with intelligent fallback behavior for development builds.

Version Format:
- Tagged releases: "v1.2.3"
- Development builds: "v1.2.3-dev.5+a1b2c3d" (latest tag + commits since + hash)
- No tags: "v0.0.0-dev+a1b2c3d" (development with commit hash)

Usage:
    from version import __version__

    print(f"ShutterSense version {__version__}")
"""

import subprocess
import re
from typing import Optional, Tuple


# Cache to avoid repeated Git subprocess calls
_VERSION_CACHE: Optional[str] = None


def _run_git_command(args: list[str]) -> Optional[str]:
    """
    Run a Git command and return its output.

    Args:
        args: List of command arguments (e.g., ['describe', '--tags'])

    Returns:
        Command output as string, or None if command failed
    """
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
    Extract version from Git tags.

    Tries to use 'git describe --tags' to get version information.
    If on a tagged commit, returns the clean tag (e.g., "v1.2.3").
    If ahead of a tag, returns tag with development suffix (e.g., "v1.2.3-dev.5+a1b2c3d").

    Returns:
        Version string or None if Git is not available
    """
    # Try to get description from tags
    describe = _run_git_command(['describe', '--tags', '--long', '--always'])

    if not describe:
        return None

    # Parse git describe output
    # Format: "v1.2.3-0-ga1b2c3d" (on tag) or "v1.2.3-5-ga1b2c3d" (5 commits after tag)
    match = re.match(r'^(.+?)-(\d+)-g([a-f0-9]+)$', describe)

    if match:
        tag, commits_since, commit_hash = match.groups()
        commits_since = int(commits_since)

        if commits_since == 0:
            # Exactly on a tag
            return tag
        else:
            # Development build - add suffix with commits and hash
            return f"{tag}-dev.{commits_since}+{commit_hash}"

    # If no tags exist, describe returns just the commit hash
    # Check if there are any tags at all
    has_tags = _run_git_command(['tag', '--list'])

    if not has_tags:
        # No tags exist yet - use development version with commit hash
        commit_hash = _run_git_command(['rev-parse', '--short', 'HEAD'])
        if commit_hash:
            return f"v0.0.0-dev+{commit_hash}"

    # Fallback if parsing failed
    return None


def _get_fallback_version() -> str:
    """
    Get fallback version when Git is not available.

    Returns:
        Default development version string
    """
    # Try to get version from environment variable (useful for CI/CD)
    import os
    env_version = os.environ.get('SHUSAI_VERSION')
    if env_version:
        return env_version

    # Final fallback
    return "v0.0.0-dev+unknown"


def get_version() -> str:
    """
    Get the current version of ShutterSense.

    This function caches the result to avoid repeated subprocess calls.
    The version is determined from Git tags with the following logic:

    - On a tagged commit: Returns the tag (e.g., "v1.2.3")
    - Ahead of a tag: Returns tag with dev suffix (e.g., "v1.2.3-dev.5+a1b2c3d")
    - No tags: Returns development version (e.g., "v0.0.0-dev+a1b2c3d")
    - No Git: Returns fallback version from environment or "v0.0.0-dev+unknown"

    Returns:
        Version string
    """
    global _VERSION_CACHE

    if _VERSION_CACHE is not None:
        return _VERSION_CACHE

    # Try to get version from Git
    version = _get_version_from_git()

    if version is None:
        # Git not available or other error - use fallback
        version = _get_fallback_version()

    _VERSION_CACHE = version
    return version


def get_version_tuple() -> Tuple[int, int, int, Optional[str]]:
    """
    Parse version string into a tuple for comparison.

    Returns:
        Tuple of (major, minor, patch, pre_release)
        Example: "v1.2.3-dev.5+abc" -> (1, 2, 3, "dev.5+abc")
                 "v1.2.3" -> (1, 2, 3, None)
    """
    version = get_version()

    # Remove 'v' prefix if present
    version_str = version.lstrip('v')

    # Match semantic version pattern
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$', version_str)

    if match:
        major, minor, patch, pre_release = match.groups()
        return (int(major), int(minor), int(patch), pre_release)

    # Fallback for unparseable versions
    return (0, 0, 0, version_str)


# Module-level constants for easy import
__version__ = get_version()
__version_info__ = get_version_tuple()


# For compatibility with common Python patterns
VERSION = __version__
