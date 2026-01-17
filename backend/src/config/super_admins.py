"""
Super admin authorization configuration.

Super admin status is determined by comparing email hashes against a predefined set.
This approach:
- Requires no database tables
- Prevents email disclosure if code is compromised (SHA-256 hashed)
- Changes require deployment (acceptable security measure for v1)

Usage:
    from backend.src.config.super_admins import is_super_admin

    if is_super_admin(user.email):
        # Grant super admin access
        ...
"""

import hashlib
from typing import Set


# SHA-256 hashed email addresses of super admins
# To add a new super admin:
# 1. Run: python -c "import hashlib; print(hashlib.sha256('admin@example.com'.lower().encode()).hexdigest())"
# 2. Add the hash to this set
# 3. Deploy the update
SUPER_ADMIN_EMAIL_HASHES: Set[str] = set()
# To add super admin emails:
# 1. Run: python -c "import hashlib; print(hashlib.sha256('admin@example.com'.lower().encode()).hexdigest())"
# 2. Add the hash to the set above: SUPER_ADMIN_EMAIL_HASHES.add("hash_here")
#    Or modify this file to include the hash in the set literal
# 3. Deploy the update
SUPER_ADMIN_EMAIL_HASHES.add("bb3be22f0fbe8181dc7f0c7a6f406934beb84aab1d9b3d2cad3da2433cf1d1ed")


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
