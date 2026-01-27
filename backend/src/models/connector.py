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

from sqlalchemy import Column, Integer, String, DateTime, Enum, Text, Boolean, Index, ForeignKey
from sqlalchemy.orm import relationship

from backend.src.models.types import JSONBType

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


class CredentialLocation(str, enum.Enum):
    """
    Credential storage location enumeration.

    Specifies where connector credentials are stored:
    - SERVER: Encrypted on server (default, current behavior)
    - AGENT: Only on agent(s), NOT on server
    - PENDING: No credentials yet, awaiting configuration
    """
    SERVER = "server"
    AGENT = "agent"
    PENDING = "pending"


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
        credential_location: Where credentials are stored (server/agent/pending)
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

    # Tenant isolation
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)

    # Core fields
    # Note: name uniqueness is team-scoped via composite constraint in __table_args__
    # No separate index on name since the composite index (team_id, name) covers lookups
    name = Column(String(255), nullable=False)
    type = Column(Enum(ConnectorType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)

    # Credential storage location (server/agent/pending)
    credential_location = Column(
        Enum(CredentialLocation, values_callable=lambda x: [e.value for e in x]),
        default=CredentialLocation.SERVER,
        nullable=False,
        index=True
    )

    # Credentials (encrypted with Fernet via CredentialEncryptor)
    # Note: When credential_location=AGENT, this may be empty/null
    credentials = Column(Text, nullable=True)  # Changed to nullable for AGENT/PENDING modes

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

    # Inventory configuration fields (Issue #107 - Bucket Inventory Import)
    # JSONB containing S3InventoryConfig or GCSInventoryConfig
    inventory_config = Column(JSONBType, nullable=True)
    # Validation status: "pending" / "validating" / "validated" / "failed"
    inventory_validation_status = Column(String(20), nullable=True)
    # Error message if validation failed
    inventory_validation_error = Column(String(500), nullable=True)
    # Latest detected manifest path (e.g., "2026-01-26T01-00Z/manifest.json")
    inventory_latest_manifest = Column(String(500), nullable=True)
    # Timestamp of last successful inventory import
    inventory_last_import_at = Column(DateTime, nullable=True)
    # Schedule: "manual" / "daily" / "weekly"
    inventory_schedule = Column(String(20), default="manual", nullable=True)

    # Relationships
    collections = relationship(
        "Collection",
        back_populates="connector",
        lazy="dynamic"  # Enable filtering in queries like connector.collections.filter_by(state="LIVE")
    )
    inventory_folders = relationship(
        "InventoryFolder",
        back_populates="connector",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    # Table-level constraints
    __table_args__ = (
        Index("idx_connector_type", "type"),
        Index("idx_connector_active", "is_active"),
        # Team-scoped name uniqueness (different teams can have same connector name)
        Index("uq_connectors_team_name", "team_id", "name", unique=True),
    )

    @property
    def has_server_credentials(self) -> bool:
        """
        Check if credentials are stored on the server.

        Returns:
            True if credential_location is SERVER
        """
        return self.credential_location == CredentialLocation.SERVER

    @property
    def requires_agent_credentials(self) -> bool:
        """
        Check if this connector requires agent-side credentials.

        Returns:
            True if credential_location is AGENT
        """
        return self.credential_location == CredentialLocation.AGENT

    @property
    def is_pending_configuration(self) -> bool:
        """
        Check if this connector is awaiting credential configuration.

        Returns:
            True if credential_location is PENDING
        """
        return self.credential_location == CredentialLocation.PENDING

    @property
    def has_inventory_config(self) -> bool:
        """
        Check if this connector has inventory configuration.

        Returns:
            True if inventory_config is set
        """
        return self.inventory_config is not None

    @property
    def is_inventory_validated(self) -> bool:
        """
        Check if inventory configuration has been validated successfully.

        Returns:
            True if inventory_validation_status is "validated"
        """
        return self.inventory_validation_status == "validated"

    @property
    def supports_inventory(self) -> bool:
        """
        Check if this connector type supports inventory import.

        Only S3 and GCS connectors support inventory (SMB does not).

        Returns:
            True if connector type is S3 or GCS
        """
        return self.type in (ConnectorType.S3, ConnectorType.GCS)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Connector("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"type={self.type.value}, "
            f"credential_location={self.credential_location.value}, "
            f"is_active={self.is_active}"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.name} ({self.type.value})"
