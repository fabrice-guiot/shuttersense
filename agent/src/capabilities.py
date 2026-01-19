"""
Agent capability detection.

Detects available tools and storage capabilities for the agent.

Issue #90 - Distributed Agent Architecture (Phase 5)
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


def _get_base_version() -> str:
    """
    Get the base version (tag only, no commit hash) for capability reporting.

    Version sources (in priority order):
    1. Git tag (e.g., "v1.2.3" from "v1.2.3-dev.5+abc123")
    2. SHUSAI_VERSION environment variable
    3. Fallback to "v0.0.0"

    Returns:
        Version string without commit hash suffix
    """
    # Try Git first
    try:
        result = subprocess.run(
            ['git', 'describe', '--tags', '--abbrev=0'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        tag = result.stdout.strip()
        if tag:
            return tag
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Try environment variable (strip any dev/commit suffix)
    env_version = os.environ.get('SHUSAI_VERSION', '')
    if env_version:
        # Extract base version from formats like "v1.2.3-dev.5+abc123"
        match = re.match(r'^(v?\d+\.\d+\.\d+)', env_version)
        if match:
            return match.group(1)
        return env_version

    # Fallback
    return "v0.0.0"


def _find_repo_root() -> Optional[Path]:
    """
    Find the repository root directory.

    Returns:
        Path to repo root or None if not found
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            check=True,
            timeout=5
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _is_tool_available(module_name: str, tool_filename: str) -> bool:
    """
    Check if a tool is available.

    Tries multiple detection methods:
    1. Direct module import (if in Python path)
    2. Check if tool file exists in repo root
    3. Check if tool file exists relative to agent package

    Args:
        module_name: Python module name to try importing
        tool_filename: Filename of the tool (e.g., "photo_stats.py")

    Returns:
        True if tool is available
    """
    # Method 1: Try direct import
    try:
        __import__(module_name)
        return True
    except ImportError:
        pass

    # Method 2: Check repo root
    repo_root = _find_repo_root()
    if repo_root:
        tool_path = repo_root / tool_filename
        if tool_path.exists():
            # Add repo root to path so import will work
            if str(repo_root) not in sys.path:
                sys.path.insert(0, str(repo_root))
            # Try import again
            try:
                __import__(module_name)
                return True
            except ImportError:
                pass

    return False


def detect_capabilities() -> list[str]:
    """
    Detect agent capabilities.

    Checks for available tools and storage access. This function is called:
    - During registration to report initial capabilities
    - On agent startup to update capabilities (in case of upgrades)

    Returns:
        List of capability strings in format:
        - "local_filesystem" for storage access
        - "tool:{name}:{version}" for each available tool
    """
    capabilities = []

    # Always include local filesystem access
    capabilities.append("local_filesystem")

    # Get version for capability strings (tag only, no commit hash)
    version = _get_base_version()

    # Check for tool availability
    tools = [
        ("photostats", "photo_stats", "photo_stats.py"),
        ("photo_pairing", "photo_pairing", "photo_pairing.py"),
        ("pipeline_validation", "pipeline_validation", "pipeline_validation.py"),
    ]

    for tool_name, module_name, filename in tools:
        if _is_tool_available(module_name, filename):
            capabilities.append(f"tool:{tool_name}:{version}")

    return capabilities
