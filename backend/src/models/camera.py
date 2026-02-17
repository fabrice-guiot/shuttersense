"""
Camera model for physical camera equipment tracking.

Tracks cameras discovered during analysis or manually created by users.
Each camera belongs to a team and is identified by a short alphanumeric
camera_id extracted from filenames (e.g., "AB3D").

Design Rationale:
- Auto-discovered cameras start as "temporary" and can be confirmed by users
- camera_id is unique per team (same physical camera across collections)
- GuidMixin provides external identification (cam_xxx)
- AuditMixin tracks who created/modified each record
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin, AuditMixin


class Camera(Base, GuidMixin, AuditMixin):
    """
    Camera model for physical camera equipment.

    Represents a camera identified by its short alphanumeric ID from filenames.
    Cameras are auto-discovered during analysis or manually created by users.

    Attributes:
        id: Primary key (internal, never exposed)
        uuid: UUIDv7 for external identification (inherited from GuidMixin)
        guid: GUID string property (cam_xxx, inherited from GuidMixin)
        team_id: Team ID for tenant isolation
        camera_id: Short alphanumeric ID from filenames (e.g., "AB3D")
        status: "temporary" (auto-discovered) or "confirmed" (user-verified)
        display_name: User-assigned friendly name (e.g., "Canon EOS R5")
        make: Camera manufacturer
        model: Camera model name
        serial_number: Camera serial number
        notes: Free-form notes
        metadata_json: Custom metadata

    Constraints:
        - (team_id, camera_id) must be unique
        - status must be "temporary" or "confirmed"

    Indexes:
        - uuid (unique, for GUID lookups)
        - team_id (for tenant-scoped queries)
        - status (for filtering)
    """

    __tablename__ = "cameras"

    # GUID prefix for Camera entities
    GUID_PREFIX = "cam"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Tenant isolation
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)

    # Core fields
    camera_id = Column(String(10), nullable=False)
    status = Column(String(20), nullable=False, server_default="temporary")
    display_name = Column(String(100), nullable=True)
    make = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    metadata_json = Column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    team = relationship("Team", back_populates="cameras")

    # Table-level constraints and indexes
    __table_args__ = (
        UniqueConstraint("team_id", "camera_id", name="uq_cameras_team_camera_id"),
        Index("ix_cameras_status", "status"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Camera("
            f"id={self.id}, "
            f"camera_id='{self.camera_id}', "
            f"status='{self.status}', "
            f"display_name='{self.display_name}'"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        name = self.display_name or self.camera_id
        return f"{name} ({self.status})"
