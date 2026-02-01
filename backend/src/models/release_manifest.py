"""
Release Manifest model for agent binary attestation.

Stores known-good checksums for released agent binaries. During registration,
an agent's self-reported checksum is validated against this manifest to ensure
only trusted binaries can connect.

Design Rationale:
- Release manifests are global (not team-scoped) since they're about binaries
- Super admin endpoint manages manifest entries
- Version/checksum uniquely identifies a valid binary
- Platforms stored as JSON array for universal binaries (e.g., macOS universal)
- Inactive entries allow deprecating old versions without breaking existing agents
"""

import json
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import validates

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin
from backend.src.models.mixins.audit import AuditMixin


class ReleaseManifest(Base, GuidMixin, AuditMixin):
    """
    Release manifest entry for agent binary attestation.

    Each entry represents a valid agent binary that is allowed to register.
    The checksum is the SHA-256 hash of the binary file.

    Attributes:
        id: Primary key (internal, never exposed)
        uuid: UUIDv7 for external identification (inherited from GuidMixin)
        guid: GUID string property (rel_xxx, inherited from GuidMixin)
        version: Semantic version string (e.g., "1.0.0", "1.2.3-beta")
        platforms_json: List of target platforms (e.g., ["darwin-arm64", "darwin-amd64"])
        checksum: SHA-256 hash of the binary (64 hex characters)
        is_active: Whether this version is allowed for registration
        notes: Optional notes about this release
        created_at: When this manifest entry was created
        updated_at: When this manifest entry was last modified

    Constraints:
        - (version, checksum) must be unique
        - checksum must be 64 hex characters (SHA-256)
        - platforms must be valid identifiers

    Indexes:
        - checksum (for fast lookup during registration)
        - (version, checksum) unique constraint
        - is_active (for filtering active versions)
    """

    __tablename__ = "release_manifests"

    # GUID prefix for ReleaseManifest entities
    GUID_PREFIX = "rel"

    # Primary key (internal only)
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Release identification
    version = Column(String(50), nullable=False, index=True)

    # Platforms as JSON array (JSONB for PostgreSQL, falls back to Text for SQLite)
    platforms_json = Column(
        JSONB().with_variant(Text, "sqlite"),
        nullable=False,
        default="[]"
    )

    # Binary checksum (SHA-256 = 64 hex chars)
    checksum = Column(String(64), nullable=False, index=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Optional notes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Table-level constraints
    __table_args__ = (
        Index('uq_release_version_checksum', 'version', 'checksum', unique=True),
    )

    # Valid platforms
    VALID_PLATFORMS = [
        'darwin-arm64',   # macOS Apple Silicon
        'darwin-amd64',   # macOS Intel
        'linux-amd64',    # Linux x86_64
        'linux-arm64',    # Linux ARM64
        'windows-amd64',  # Windows x86_64
    ]

    @property
    def platforms(self) -> List[str]:
        """
        Get platforms list from JSON column.

        Returns:
            List of platform identifier strings
        """
        if self.platforms_json is None:
            return []
        if isinstance(self.platforms_json, str):
            # SQLite returns string, parse it
            return json.loads(self.platforms_json) if self.platforms_json else []
        if isinstance(self.platforms_json, list):
            return self.platforms_json
        return []

    @platforms.setter
    def platforms(self, value: List[str]) -> None:
        """
        Set platforms list, normalizing to lowercase.

        Args:
            value: List of platform identifier strings
        """
        # For SQLite compatibility, serialize to JSON string
        # PostgreSQL JSONB handles lists natively, but we serialize for both
        if value is None:
            self.platforms_json = "[]"  # type: ignore
        elif isinstance(value, list):
            normalized = [p.lower() for p in value]
            self.platforms_json = json.dumps(normalized)  # type: ignore
        else:
            self.platforms_json = value  # type: ignore

    def supports_platform(self, platform: str) -> bool:
        """Check if this manifest supports the given platform."""
        return platform.lower() in self.platforms

    @validates('checksum')
    def validate_checksum(self, key: str, value: str) -> str:
        """Validate checksum is a valid SHA-256 hex string."""
        if not value:
            raise ValueError("Checksum is required")
        value = value.lower()
        if len(value) != 64:
            raise ValueError("Checksum must be 64 hex characters (SHA-256)")
        try:
            int(value, 16)
        except ValueError:
            raise ValueError("Checksum must be valid hexadecimal")
        return value

    @validates('version')
    def validate_version(self, key: str, value: str) -> str:
        """Validate version is not empty."""
        if not value or not value.strip():
            raise ValueError("Version is required")
        return value.strip()

    def __repr__(self) -> str:
        platforms_str = ', '.join(self.platforms) if self.platforms else 'none'
        return (
            f"<ReleaseManifest(guid='{self.guid}', "
            f"version='{self.version}', platforms=[{platforms_str}], "
            f"active={self.is_active})>"
        )

    @classmethod
    def find_by_checksum(cls, db_session, checksum: str, active_only: bool = True):
        """
        Find a release manifest by checksum.

        Args:
            db_session: Database session
            checksum: SHA-256 checksum to search for
            active_only: If True, only return active manifests

        Returns:
            ReleaseManifest or None
        """
        query = db_session.query(cls).filter(cls.checksum == checksum.lower())
        if active_only:
            query = query.filter(cls.is_active == True)
        return query.first()
