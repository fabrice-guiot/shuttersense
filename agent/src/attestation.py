"""
Binary attestation module for agent self-verification.

Computes SHA-256 hash of the running binary/script for attestation during
registration. The server validates this checksum against known-good releases.

Design Rationale:
- For compiled binaries: Hash the executable file itself
- For Python scripts: Hash the main module and key dependencies
- The checksum is sent during registration and validated by the server
- This ensures only trusted agent versions can connect
"""

import hashlib
import sys
import os
from pathlib import Path
from typing import Optional, Tuple


def get_binary_checksum() -> Tuple[str, str]:
    """
    Compute SHA-256 checksum of the running agent binary/script.

    For frozen executables (PyInstaller, etc.): hashes the executable file.
    For Python scripts: hashes the main module file.

    Returns:
        Tuple of (checksum, method) where:
        - checksum: 64-character hex SHA-256 hash
        - method: How the checksum was computed ('binary', 'script', 'unknown')

    Raises:
        RuntimeError: If unable to determine or hash the binary
    """
    # Check if running as frozen executable (PyInstaller, cx_Freeze, etc.)
    if getattr(sys, 'frozen', False):
        return _hash_frozen_binary()

    # Running as Python script - hash the main module
    return _hash_script()


def _hash_frozen_binary() -> Tuple[str, str]:
    """
    Hash a frozen/compiled executable.

    For PyInstaller: sys.executable points to the bundled executable.
    For other freezers: similar behavior expected.

    Returns:
        Tuple of (checksum, 'binary')
    """
    executable_path = sys.executable

    if not os.path.isfile(executable_path):
        raise RuntimeError(f"Cannot find executable at: {executable_path}")

    checksum = _hash_file(executable_path)
    return (checksum, 'binary')


def _hash_script() -> Tuple[str, str]:
    """
    Hash the main Python script.

    Uses __main__.__file__ if available, falls back to sys.argv[0].

    Returns:
        Tuple of (checksum, 'script')
    """
    # Try to get the main module's file
    main_file = None

    # First try: __main__.__file__
    try:
        import __main__
        if hasattr(__main__, '__file__') and __main__.__file__:
            main_file = __main__.__file__
    except Exception:
        pass

    # Fallback: sys.argv[0]
    if not main_file and sys.argv and sys.argv[0]:
        main_file = sys.argv[0]

    if not main_file:
        raise RuntimeError("Cannot determine main script path")

    # Resolve to absolute path
    main_path = Path(main_file).resolve()

    if not main_path.is_file():
        raise RuntimeError(f"Main script not found: {main_path}")

    checksum = _hash_file(str(main_path))
    return (checksum, 'script')


def _hash_file(filepath: str) -> str:
    """
    Compute SHA-256 hash of a file.

    Args:
        filepath: Path to the file to hash

    Returns:
        64-character lowercase hex string

    Raises:
        RuntimeError: If file cannot be read
    """
    hasher = hashlib.sha256()

    try:
        with open(filepath, 'rb') as f:
            # Read in chunks for memory efficiency with large files
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
    except (IOError, OSError) as e:
        raise RuntimeError(f"Failed to read file for hashing: {e}")

    return hasher.hexdigest()


def get_platform_identifier() -> str:
    """
    Get the platform identifier for the current system.

    Format: {os}-{arch}
    Examples: darwin-arm64, linux-amd64, windows-amd64

    Returns:
        Platform identifier string
    """
    import platform

    # Map Python's platform.system() to standard names
    os_name = platform.system().lower()
    if os_name == 'darwin':
        os_name = 'darwin'
    elif os_name == 'linux':
        os_name = 'linux'
    elif os_name == 'windows':
        os_name = 'windows'

    # Map Python's platform.machine() to standard arch names
    machine = platform.machine().lower()
    if machine in ('x86_64', 'amd64'):
        arch = 'amd64'
    elif machine in ('arm64', 'aarch64'):
        arch = 'arm64'
    elif machine in ('i386', 'i686', 'x86'):
        arch = '386'
    else:
        arch = machine

    return f"{os_name}-{arch}"


def verify_checksum(expected: str, actual: Optional[str] = None) -> bool:
    """
    Verify the current binary's checksum matches an expected value.

    Args:
        expected: Expected SHA-256 checksum (64 hex chars)
        actual: Actual checksum to compare (if None, computes current)

    Returns:
        True if checksums match, False otherwise
    """
    if actual is None:
        actual, _ = get_binary_checksum()

    # Normalize to lowercase for comparison
    return expected.lower() == actual.lower()


# Development mode flag - can be set to bypass attestation
# This should NEVER be True in production builds
_DEVELOPMENT_MODE = os.environ.get('SHUSAI_AGENT_DEV_MODE', '').lower() == 'true'


def is_development_mode() -> bool:
    """
    Check if agent is running in development mode.

    In development mode, attestation checks can be bypassed.
    This should NEVER be enabled in production.

    Returns:
        True if development mode is enabled
    """
    return _DEVELOPMENT_MODE


def get_attestation_info() -> dict:
    """
    Get full attestation information for registration.

    Returns:
        Dictionary with:
        - checksum: SHA-256 hash of binary/script
        - method: How checksum was computed
        - platform: Platform identifier
        - development_mode: Whether dev mode is enabled
    """
    try:
        checksum, method = get_binary_checksum()
    except RuntimeError:
        checksum = None
        method = 'unknown'

    return {
        'checksum': checksum,
        'method': method,
        'platform': get_platform_identifier(),
        'development_mode': is_development_mode(),
    }
