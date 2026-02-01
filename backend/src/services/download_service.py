"""
Download service for authenticated agent binary distribution.

Provides HMAC-signed URL generation/verification and secure file resolution
for the Agent Setup Wizard binary download feature.

Issue #136 - Agent Setup Wizard
"""

import hashlib
import hmac
import re
import time
from pathlib import Path
from typing import Optional, Tuple


# Version string validation: semver-like, no path traversal characters
VERSION_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9.\-+]*$')

# Default signed URL validity period (1 hour)
DEFAULT_SIGNED_URL_EXPIRY_SECONDS = 3600


def generate_signed_download_url(
    manifest_guid: str,
    platform: str,
    secret_key: str,
    expires_in_seconds: int = DEFAULT_SIGNED_URL_EXPIRY_SECONDS,
) -> Tuple[str, int]:
    """
    Generate a time-limited signed download URL.

    The URL uses HMAC-SHA256 to sign the combination of manifest GUID,
    platform, and expiry timestamp.

    Args:
        manifest_guid: Release manifest GUID (e.g., "rel_01hgw2bbg...")
        platform: Platform identifier (e.g., "darwin-arm64")
        secret_key: HMAC signing key (JWT_SECRET_KEY)
        expires_in_seconds: URL validity period (default: 3600 = 1 hour)

    Returns:
        Tuple of (relative_url, expires_timestamp)
    """
    expires = int(time.time()) + expires_in_seconds
    message = f"{manifest_guid}:{platform}:{expires}"
    signature = hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    url = (
        f"/api/agent/v1/releases/{manifest_guid}"
        f"/download/{platform}"
        f"?expires={expires}&signature={signature}"
    )
    return url, expires


def verify_signed_download_url(
    manifest_guid: str,
    platform: str,
    expires: int,
    signature: str,
    secret_key: str,
) -> Tuple[bool, Optional[str]]:
    """
    Verify a signed download URL.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        manifest_guid: Release manifest GUID
        platform: Platform identifier
        expires: Unix timestamp when the URL expires
        signature: HMAC-SHA256 hex digest from the URL
        secret_key: HMAC signing key (JWT_SECRET_KEY)

    Returns:
        Tuple of (is_valid, error_message). error_message is None when valid.
    """
    # Check expiry first
    if int(time.time()) > expires:
        return False, "Download link has expired. Please request a new link from the wizard."

    # Compute expected signature
    message = f"{manifest_guid}:{platform}:{expires}"
    expected = hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison
    if not hmac.compare_digest(signature, expected):
        return False, "Invalid download link. Please request a new link from the wizard."

    return True, None


def resolve_binary_path(
    dist_dir: str,
    version: str,
    filename: str,
) -> Tuple[Optional[Path], Optional[str]]:
    """
    Resolve and validate the binary file path within the distribution directory.

    Performs path traversal prevention by:
    1. Validating the version string format
    2. Validating the filename (no path separators)
    3. Resolving the absolute path and verifying it's within dist_dir

    Args:
        dist_dir: Absolute path to the agent distribution directory
        version: Release version string (e.g., "1.0.0")
        filename: Artifact filename (e.g., "shuttersense-agent-darwin-arm64")

    Returns:
        Tuple of (resolved_path, error_message). resolved_path is None on error.
    """
    # Validate version string
    if not version or not VERSION_PATTERN.match(version):
        return None, "Invalid version format"

    # Validate filename has no path separators
    if not filename or '/' in filename or '\\' in filename:
        return None, "Invalid filename"

    # Construct and resolve the path
    dist_path = Path(dist_dir).resolve()
    file_path = (dist_path / version / filename).resolve()

    # Verify the resolved path is within the distribution directory
    # This prevents path traversal attacks (e.g., version="../../etc")
    if not str(file_path).startswith(str(dist_path)):
        return None, "Invalid file path"

    # Check file exists
    if not file_path.is_file():
        return None, "Agent binary file not found on server. Contact your administrator."

    return file_path, None
