"""
Connector model for remote storage authentication.

Represents authentication credentials for accessing remote storage systems (S3, GCS, SMB).
Multiple collections can share one connector for credential reuse and easier key rotation.

Design Rationale:
- Credential Reuse: Multiple collections (e.g., 50 S3 buckets) share one connector
- Easier Key Rotation: Master key rotation only re-encrypts Connector table
- Clearer Organization: Users can see which collections share the same cloud account
- Future-Proof: Enables connector-level access control for multi-user support
"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, String, DateTime, Enum, Text, Boolean, Index
from sqlalchemy.orm import relationship

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin


class ConnectorType(enum.Enum):
    """
    Remote storage connector type enumeration.

    Supported types:
    - S3: Amazon S3 (or S3-compatible storage)
    - GCS: Google Cloud Storage
    - SMB: SMB/CIFS network shares
    """
    S3 = "s3"
    GCS = "gcs"
    SMB = "smb"


class Connector(Base, GuidMixin):
    """
    Remote storage connector model.

    Stores encrypted authentication credentials for remote storage systems.
    Multiple collections can reference the same connector for credential reuse.

    Attributes:
        id: Primary key
        uuid: UUIDv7 for external identification (inherited from GuidMixin)
        guid: GUID string property (con_xxx, inherited from GuidMixin)
        name: User-friendly name (e.g., "Personal AWS Account", "Work GCS Project")
        type: Connector type (S3, GCS, SMB)
        credentials: Encrypted JSON string containing authentication credentials
        metadata_json: Optional user-defined metadata (tags, notes)
        is_active: Whether connector is active (for soft deactivation)
        last_validated: Timestamp of last successful connection test
        last_error: Last error message from connection test (if any)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        collections: Related collections (one-to-many relationship)

    Credentials Format (decrypted):
        S3: {"aws_access_key_id": "...", "aws_secret_access_key": "...", "region": "us-west-2"}
        GCS: {"service_account_json": "..."}
        SMB: {"server": "...", "share": "...", "username": "...", "password": "..."}

    Constraints:
        - name must be unique
        - type must be valid ConnectorType
        - credentials required and must be encrypted
        - RESTRICT delete if collections reference this connector

    Indexes:
        - name (unique)
        - uuid (unique, for GUID lookups)
        - type (for filtering by connector type)
        - is_active (for filtering active connectors)
    """

    __tablename__ = "connectors"

    # GUID prefix for Connector entities
    GUID_PREFIX = "con"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Core fields
    name = Column(String(255), unique=True, nullable=False, index=True)
    type = Column(Enum(ConnectorType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)

    # Credentials (encrypted with Fernet via CredentialEncryptor)
    credentials = Column(Text, nullable=False)

    # Optional metadata
    metadata_json = Column(Text, nullable=True)  # JSON string for flexibility

    # Status tracking
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_validated = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    collections = relationship(
        "Collection",
        back_populates="connector",
        lazy="dynamic"  # Enable filtering in queries like connector.collections.filter_by(state="LIVE")
    )

    # Table-level constraints
    __table_args__ = (
        Index("idx_connector_type", "type"),
        Index("idx_connector_active", "is_active"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Connector("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"type={self.type.value}, "
            f"is_active={self.is_active}"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.name} ({self.type.value})"
