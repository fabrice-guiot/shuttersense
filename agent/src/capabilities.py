"""
Agent capability detection.

Detects available tools and storage capabilities for the agent.

Issue #90 - Distributed Agent Architecture (Phase 5)
Issue #108 - Analysis tools are now built into the agent package
"""

import os
import re
import subprocess


def _get_base_version() -> str:
    """
    Get the base version (tag only, no commit hash) for capability reporting.

    Version sources (in priority order):
    1. Git tag (e.g., "v1.2.3" from "v1.2.3-dev.5+abc123")
    2. SHUTTERSENSE_VERSION environment variable
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
    env_version = os.environ.get('SHUTTERSENSE_VERSION', '')
    if env_version:
        # Extract base version from formats like "v1.2.3-dev.5+abc123"
        match = re.match(r'^(v?\d+\.\d+\.\d+)', env_version)
        if match:
            return match.group(1)
        return env_version

    # Fallback
    return "v0.0.0"


def detect_capabilities() -> list[str]:
    """
    Detect agent capabilities.

    Checks for available tools and storage access. This function is called:
    - During registration to report initial capabilities
    - On agent startup to update capabilities (in case of upgrades)

    All analysis tools (photostats, photo_pairing, pipeline_validation)
    are built into the agent package under src/analysis/ and are always
    available. Cloud storage adapters are optional runtime dependencies.

    Returns:
        List of capability strings in format:
        - "local_filesystem" for storage access
        - "s3" / "gcs" for cloud storage access
        - "tool:{name}:{version}" for each available tool
    """
    capabilities = []

    # Always include local filesystem access
    capabilities.append("local_filesystem")

    # Get version for capability strings (tag only, no commit hash)
    version = _get_base_version()

    # Check for cloud storage adapter availability
    # S3 support via boto3
    try:
        import boto3  # noqa: F401
        capabilities.append("s3")
    except ImportError:
        pass

    # GCS support via google-cloud-storage
    try:
        from google.cloud import storage  # noqa: F401
        capabilities.append("gcs")
    except ImportError:
        pass

    # Built-in analysis tools (always available — bundled in agent/src/analysis/)
    capabilities.append(f"tool:photostats:{version}")
    capabilities.append(f"tool:photo_pairing:{version}")
    capabilities.append(f"tool:pipeline_validation:{version}")

    # Built-in agent tools (always available)
    # inventory_import and inventory_validate work with S3/GCS connectors
    capabilities.append(f"tool:inventory_import:{version}")
    capabilities.append(f"tool:inventory_validate:{version}")

    return capabilities
