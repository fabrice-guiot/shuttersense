"""
Security settings for path validation and access control.

This module provides path security settings loaded from environment variables.
These settings establish allowlists for filesystem access, providing defense
against path traversal attacks.

Environment Variables:
    PHOTO_ADMIN_AUTHORIZED_LOCAL_ROOTS: Comma-separated list of authorized root
        paths for local collections (e.g., "/photos,/media,~/Pictures").
        User-provided collection paths must be subpaths of one of these roots.
        If not set, local collections are disabled for security.

    PHOTO_ADMIN_SPA_DIST_PATH: Path to the SPA distribution directory.
        If not set, defaults to frontend/dist relative to project root.
        Static file serving is restricted to this directory.

Usage:
    >>> from backend.src.utils.security_settings import (
    ...     get_authorized_local_roots,
    ...     is_path_authorized,
    ...     get_spa_dist_path
    ... )
    >>> roots = get_authorized_local_roots()
    >>> is_valid = is_path_authorized("/photos/2024/vacation", roots)
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple
from functools import lru_cache

from backend.src.utils.logging_config import get_logger

logger = get_logger("services")


# Environment variable names
ENV_AUTHORIZED_LOCAL_ROOTS = "PHOTO_ADMIN_AUTHORIZED_LOCAL_ROOTS"
ENV_SPA_DIST_PATH = "PHOTO_ADMIN_SPA_DIST_PATH"


@lru_cache(maxsize=1)
def get_authorized_local_roots() -> List[Path]:
    """
    Get the list of authorized root paths for local collections.

    Parses the PHOTO_ADMIN_AUTHORIZED_LOCAL_ROOTS environment variable,
    which should contain comma-separated paths. Each path is:
    - Expanded (~ -> home directory)
    - Resolved to absolute path
    - Validated to exist (warnings logged for non-existent paths)

    Returns:
        List of authorized root Path objects. Empty list if not configured.

    Example:
        # Set env var: PHOTO_ADMIN_AUTHORIZED_LOCAL_ROOTS="/photos,/media,~/Pictures"
        >>> roots = get_authorized_local_roots()
        >>> print(roots)
        [PosixPath('/photos'), PosixPath('/media'), PosixPath('/home/user/Pictures')]
    """
    env_value = os.environ.get(ENV_AUTHORIZED_LOCAL_ROOTS, "").strip()

    if not env_value:
        logger.warning(
            f"{ENV_AUTHORIZED_LOCAL_ROOTS} not configured. "
            "Local collections will be disabled for security."
        )
        return []

    roots = []
    for path_str in env_value.split(","):
        path_str = path_str.strip()
        if not path_str:
            continue

        try:
            # Expand ~ and resolve to absolute path
            path = Path(path_str).expanduser().resolve()
            roots.append(path)

            if not path.exists():
                logger.warning(
                    f"Authorized root path does not exist: {path}. "
                    "Collections under this path will fail accessibility checks."
                )
            elif not path.is_dir():
                logger.warning(
                    f"Authorized root path is not a directory: {path}."
                )
        except (OSError, ValueError) as e:
            logger.error(f"Invalid authorized root path '{path_str}': {e}")

    if roots:
        logger.info(
            f"Configured {len(roots)} authorized local root(s): "
            f"{', '.join(str(r) for r in roots)}"
        )
    else:
        logger.warning(
            f"{ENV_AUTHORIZED_LOCAL_ROOTS} is set but contains no valid paths. "
            "Local collections will be disabled."
        )

    return roots


def is_path_authorized(
    path: str,
    authorized_roots: Optional[List[Path]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Check if a path is authorized (is a subpath of an authorized root).

    This function provides the core security check for path validation:
    1. Rejects paths containing ".." (path traversal sequences)
    2. Normalizes and resolves the path to absolute form
    3. Verifies the path is a subpath of an authorized root

    Args:
        path: The path to validate (can be relative or use ~)
        authorized_roots: List of authorized root paths. If None, fetches from
            environment using get_authorized_local_roots().

    Returns:
        Tuple of (is_authorized: bool, error_message: Optional[str])
        - (True, None) if path is authorized
        - (False, error_message) if path is not authorized or invalid

    Example:
        >>> is_authorized, error = is_path_authorized("/photos/2024/vacation")
        >>> if not is_authorized:
        ...     print(f"Access denied: {error}")
    """
    # Get authorized roots if not provided
    if authorized_roots is None:
        authorized_roots = get_authorized_local_roots()

    # Check if any roots are configured
    if not authorized_roots:
        return False, (
            "Local collections are disabled. "
            f"Configure {ENV_AUTHORIZED_LOCAL_ROOTS} environment variable "
            "with authorized root paths."
        )

    # Security: Reject obvious path traversal attempts
    if ".." in path:
        return False, "Path traversal sequences (..) not allowed"

    try:
        # Normalize and resolve to absolute path
        resolved_path = Path(path).expanduser().resolve()
    except (OSError, ValueError) as e:
        return False, f"Invalid path: {e}"

    # Check if path is under an authorized root
    for root in authorized_roots:
        try:
            if resolved_path.is_relative_to(root):
                return True, None
        except (ValueError, TypeError):
            # is_relative_to raises ValueError for paths on different drives
            continue

    # Path is not under any authorized root
    return False, (
        f"Path is not under an authorized root directory. "
        f"Authorized roots: {', '.join(str(r) for r in authorized_roots)}"
    )


@lru_cache(maxsize=1)
def get_spa_dist_path() -> Path:
    """
    Get the configured SPA distribution directory path.

    Returns the path from PHOTO_ADMIN_SPA_DIST_PATH environment variable,
    or defaults to frontend/dist relative to the project root.

    Returns:
        Resolved Path to the SPA dist directory
    """
    env_value = os.environ.get(ENV_SPA_DIST_PATH, "").strip()

    if env_value:
        spa_path = Path(env_value).expanduser().resolve()
        logger.info(f"Using configured SPA dist path: {spa_path}")
    else:
        # Default: frontend/dist relative to project root
        # Project root is 4 levels up from this file:
        # backend/src/utils/security_settings.py -> project root
        project_root = Path(__file__).parent.parent.parent.parent
        spa_path = (project_root / "frontend" / "dist").resolve()
        logger.debug(f"Using default SPA dist path: {spa_path}")

    return spa_path


def is_safe_static_file_path(
    requested_path: str,
    base_dir: Optional[Path] = None
) -> Tuple[bool, Optional[Path]]:
    """
    Validate and resolve a requested static file path safely.

    This function ensures that a requested file path:
    1. Does not contain path traversal sequences
    2. Resolves to a location within the base directory
    3. Is a regular file (not a directory or symlink to outside)

    Args:
        requested_path: The path requested (from URL, user input, etc.)
        base_dir: The base directory files must be within. If None, uses
            get_spa_dist_path().

    Returns:
        Tuple of (is_safe: bool, resolved_path: Optional[Path])
        - (True, resolved_path) if the path is safe and exists
        - (False, None) if the path is unsafe or doesn't exist

    Example:
        >>> is_safe, file_path = is_safe_static_file_path("favicon.ico")
        >>> if is_safe:
        ...     return FileResponse(file_path)
    """
    if base_dir is None:
        base_dir = get_spa_dist_path()

    # Resolve base_dir to handle symlinks (e.g., /var -> /private/var on macOS)
    resolved_base_dir = base_dir.resolve()

    # Reject empty paths
    if not requested_path:
        return False, None

    # Security: Reject obvious path traversal attempts
    if ".." in requested_path:
        logger.warning(f"Path traversal attempt detected: {requested_path}")
        return False, None

    # Reject absolute paths in requests
    if requested_path.startswith("/") or (
        len(requested_path) > 1 and requested_path[1] == ":"
    ):
        logger.warning(f"Absolute path in static file request: {requested_path}")
        return False, None

    try:
        # Resolve the full path relative to the resolved_base_dir
        # Using resolved_base_dir ensures both base and child share the same root
        full_path = (resolved_base_dir / requested_path).resolve()

        # Verify the resolved path is still within resolved_base_dir
        # This catches symlinks that point outside and prevents directory traversal
        base_parts = resolved_base_dir.parts
        full_parts = full_path.parts
        if len(full_parts) < len(base_parts) or full_parts[: len(base_parts)] != base_parts:
            logger.warning(
                f"Static file path escapes base directory: "
                f"requested={requested_path}, resolved={full_path}, base={resolved_base_dir}"
            )
            return False, None

        # Check if file exists and is a regular file
        if full_path.exists() and full_path.is_file():
            return True, full_path

        return False, None

    except (OSError, ValueError) as e:
        logger.warning(f"Error resolving static file path '{requested_path}': {e}")
        return False, None


def clear_security_settings_cache() -> None:
    """
    Clear cached security settings.

    Use this when environment variables change (e.g., in tests).
    """
    get_authorized_local_roots.cache_clear()
    get_spa_dist_path.cache_clear()
