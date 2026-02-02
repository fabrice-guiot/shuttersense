"""
Release Artifact model for per-platform agent binary metadata.

Stores individual downloadable agent binaries for each platform within a
release manifest. Each artifact represents a specific binary file (e.g.,
shuttersense-agent-darwin-arm64) with its own checksum and file size.

Design Rationale:
- Child entity of ReleaseManifest — always accessed through parent
- No GuidMixin (Constitution IV exception, documented in plan.md Complexity Tracking):
  artifacts are identified by (manifest_id, platform) composite key and never
  referenced independently in APIs or URLs
- No AuditMixin: global entity (not tenant-scoped), inherits audit context from parent
- CASCADE delete: artifacts have no meaning without their parent manifest

Issue #136 - Agent Setup Wizard
"""

import re
from datetime import datetime

from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import validates, relationship

from backend.src.models import Base


# Valid platform identifiers
VALID_PLATFORMS = [
    'darwin-arm64',
    'darwin-amd64',
    'linux-amd64',
    'linux-arm64',
    'windows-amd64',
]

# Checksum format: optional "sha256:" prefix followed by 64 hex chars
CHECKSUM_PATTERN = re.compile(r'^(sha256:)?[0-9a-fA-F]{64}$')


class ReleaseArtifact(Base):
    """
    Per-platform agent binary artifact within a release manifest.

    Attributes:
        id: Primary key (internal only)
        manifest_id: FK to release_manifests.id (CASCADE delete)
        platform: Platform identifier (e.g., 'darwin-arm64')
        filename: Binary filename (no path separators)
        checksum: sha256:-prefixed hex checksum
        file_size: File size in bytes (nullable — may not be known at creation)
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Constraints:
        - (manifest_id, platform) must be unique
        - platform must be one of VALID_PLATFORMS
        - checksum must match sha256: prefix pattern
        - filename must not contain path separators

    Note:
        ExternalIdMixin (GUID) is intentionally omitted per Constitution IV.
        Artifacts are child entities always accessed through their parent
        ReleaseManifest and identified by (manifest_id, platform) composite
        key — no independent GUID-based reference is needed.
    """

    __tablename__ = "release_artifacts"

    id = Column(Integer, primary_key=True, autoincrement=True)

    manifest_id = Column(
        Integer,
        ForeignKey("release_manifests.id", ondelete="CASCADE"),
        nullable=False,
    )

    platform = Column(String(50), nullable=False)
    filename = Column(String(255), nullable=False)
    checksum = Column(String(73), nullable=False)  # "sha256:" (7) + 64 hex = 71, with margin
    file_size = Column(BigInteger, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationship to parent manifest
    manifest = relationship("ReleaseManifest", back_populates="artifacts")

    __table_args__ = (
        UniqueConstraint('manifest_id', 'platform', name='uq_artifact_manifest_platform'),
        Index('ix_release_artifacts_manifest_id', 'manifest_id'),
        Index('ix_release_artifacts_platform', 'platform'),
    )

    @validates('platform')
    def validate_platform(self, key: str, value: str) -> str:
        """Validate platform is a known identifier.

        Args:
            key: Field name being validated (always "platform").
            value: Platform string to validate.

        Returns:
            Normalized lowercase platform string.

        Raises:
            ValueError: If value is empty or not in VALID_PLATFORMS.
        """
        if not value:
            raise ValueError("Platform is required")
        value = value.lower().strip()
        if value not in VALID_PLATFORMS:
            raise ValueError(
                f"Invalid platform '{value}'. Must be one of: {', '.join(VALID_PLATFORMS)}"
            )
        return value

    @validates('filename')
    def validate_filename(self, key: str, value: str) -> str:
        """Validate filename contains no path separators.

        Args:
            key: Field name being validated (always "filename").
            value: Filename string to validate.

        Returns:
            Trimmed filename string.

        Raises:
            ValueError: If value is empty or contains path separators (/ or \\).
        """
        if not value:
            raise ValueError("Filename is required")
        if '/' in value or '\\' in value:
            raise ValueError("Filename must not contain path separators (/ or \\)")
        return value.strip()

    @validates('checksum')
    def validate_checksum(self, key: str, value: str) -> str:
        """Validate checksum matches expected format.

        Args:
            key: Field name being validated (always "checksum").
            value: Checksum string to validate.

        Returns:
            Validated checksum string (optionally sha256:-prefixed, 64 hex chars).

        Raises:
            ValueError: If value is empty or does not match CHECKSUM_PATTERN.
        """
        if not value:
            raise ValueError("Checksum is required")
        if not CHECKSUM_PATTERN.match(value):
            raise ValueError(
                "Checksum must be a 64-character hex string, optionally prefixed with 'sha256:'"
            )
        return value

    def __repr__(self) -> str:
        """Return a stable debug representation of the artifact.

        Returns:
            str: Debug string with manifest_id, platform, and filename.

        Raises:
            None.
        """
        return (
            f"<ReleaseArtifact(manifest_id={self.manifest_id}, "
            f"platform='{self.platform}', filename='{self.filename}')>"
        )
