"""
Super admin authorization configuration.

Super admin status is determined by comparing email hashes against a
configurable set loaded from the ``SHUSAI_SUPER_ADMIN_HASHES`` environment
variable.

This approach:
- Requires no database tables
- Prevents email disclosure if environment is compromised (SHA-256 hashed)
- Can be changed without code deployment

Usage:
    from backend.src.config.super_admins import is_super_admin

    if is_super_admin(user.email):
        # Grant super admin access
        ...

Configuration:
    Set the SHUSAI_SUPER_ADMIN_HASHES environment variable to a
    comma-separated list of SHA-256 email hashes::

        export SHUSAI_SUPER_ADMIN_HASHES="hash1,hash2,hash3"

    Generate a hash with::

        python -c "import hashlib; print(hashlib.sha256('admin@example.com'.lower().encode()).hexdigest())"
"""

import hashlib
import os
from typing import Set


def _load_super_admin_hashes() -> Set[str]:
    """Load super admin email hashes from environment variable.

    Returns:
        Set of SHA-256 hex digests loaded from SHUSAI_SUPER_ADMIN_HASHES.
    """
    env_value = os.environ.get("SHUSAI_SUPER_ADMIN_HASHES", "")
    hashes: Set[str] = set()
    for entry in env_value.split(","):
        entry = entry.strip()
        if entry:
            hashes.add(entry)
    return hashes


SUPER_ADMIN_EMAIL_HASHES: Set[str] = _load_super_admin_hashes()


def is_super_admin(email: str) -> bool:
    """
    Check if an email belongs to a super admin.

    Args:
        email: Email address to check (case-insensitive)

    Returns:
        True if the email's hash is in the SUPER_ADMIN_EMAIL_HASHES set

    Example:
        >>> is_super_admin("Admin@Example.com")
        False  # Unless hash is in SUPER_ADMIN_EMAIL_HASHES
    """
    if not email:
        return False

    # Normalize email: lowercase and strip whitespace
    normalized_email = email.lower().strip()

    # Compute SHA-256 hash
    email_hash = hashlib.sha256(normalized_email.encode("utf-8")).hexdigest()

    return email_hash in SUPER_ADMIN_EMAIL_HASHES


def generate_email_hash(email: str) -> str:
    """
    Generate SHA-256 hash for an email address.

    Utility function for administrators to generate hashes to add to
    SUPER_ADMIN_EMAIL_HASHES.

    Args:
        email: Email address to hash

    Returns:
        SHA-256 hex digest of the normalized (lowercase, stripped) email

    Example:
        >>> generate_email_hash("admin@example.com")
        '409e8c3ed5d78e8e1d9a6f9d8b7c6a5e4d3c2b1a0f9e8d7c6b5a4f3e2d1c0b9a8'
    """
    normalized_email = email.lower().strip()
    return hashlib.sha256(normalized_email.encode("utf-8")).hexdigest()
