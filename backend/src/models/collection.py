"""
Collection model for photo collections (local and remote).

Represents a photo collection with location, state, and accessibility tracking.
Collections can be local (filesystem) or remote (S3, GCS, SMB via connectors).

Design Rationale:
- Collection State: Live (active work), Closed (finished), Archived (long-term storage)
- Accessibility Tracking: is_accessible flag with last_error for troubleshooting
- Cache TTL: Configurable per collection or state-based defaults
- Connector Foreign Key: RESTRICT delete to prevent orphaned collections
- Pipeline Assignment: Optional pipeline+version for tool execution (SET NULL on delete)
"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Enum, Text, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin
from backend.src.utils.cache import COLLECTION_STATE_TTL


class CollectionType(enum.Enum):
    """
    Collection type enumeration.

    Supported types:
    - LOCAL: Local filesystem
    - S3: Amazon S3 (via connector)
    - GCS: Google Cloud Storage (via connector)
    - SMB: SMB/CIFS network share (via connector)
    """
    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"
    SMB = "smb"


class CollectionState(enum.Enum):
    """
    Collection lifecycle state enumeration.

    States:
    - LIVE: Active photography work in progress (frequent changes, 1hr cache TTL)
    - CLOSED: Photography finished, infrequent changes (24hr cache TTL)
    - ARCHIVED: Long-term storage, infrastructure monitoring only (7d cache TTL)
    """
    LIVE = "live"
    CLOSED = "closed"
    ARCHIVED = "archived"


class Collection(Base, GuidMixin):
    """
    Photo collection model.

    Represents a collection of photos stored locally or remotely with state tracking,
    accessibility monitoring, and configurable caching behavior.

    Attributes:
        id: Primary key
        uuid: UUIDv7 for external identification (inherited from GuidMixin)
        guid: GUID string property (col_xxx, inherited from GuidMixin)
        connector_id: Foreign key to Connector (NULL for local, required for remote)
        pipeline_id: Foreign key to Pipeline (NULL = use default, SET NULL on delete)
        pipeline_version: Pinned pipeline version (NULL if using current/default)
        name: User-friendly collection name (unique)
        type: Collection type (LOCAL, S3, GCS, SMB)
        location: Storage location path/URI
        state: Collection lifecycle state (LIVE, CLOSED, ARCHIVED)
        cache_ttl: Custom cache TTL in seconds (overrides state default)
        is_accessible: Whether collection is currently accessible
        last_error: Last error message from accessibility test
        metadata_json: Optional user-defined metadata (tags, notes, custom fields)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        connector: Related connector (many-to-one, NULL for local)
        pipeline: Related pipeline (many-to-one, NULL = use default)
        analysis_results: Related analysis results (one-to-many, cascade delete)

    Location Format:
        LOCAL: /absolute/path/to/photos
        S3: bucket-name/optional/prefix
        GCS: bucket-name/optional/prefix
        SMB: /share-path/optional/prefix

    Constraints:
        - name must be unique
        - type must be valid CollectionType
        - state must be valid CollectionState
        - connector_id required for remote types, NULL for LOCAL
        - connector_id uses RESTRICT on delete
        - pipeline_id uses SET NULL on delete
        - pipeline_version must be set when pipeline_id is set
        - cache_ttl if provided must be positive integer

    Indexes:
        - name (unique)
        - uuid (unique, for GUID lookups)
        - state (for filtering by state)
        - type (for filtering by type)
        - is_accessible (for filtering accessible collections)
        - connector_id (for foreign key lookups)
        - pipeline_id (for foreign key lookups)

    Methods:
        get_effective_cache_ttl(): Returns user override or state-based default TTL
    """

    __tablename__ = "collections"

    # GUID prefix for Collection entities
    GUID_PREFIX = "col"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    connector_id = Column(
        Integer,
        ForeignKey("connectors.id", ondelete="RESTRICT"),
        nullable=True,  # NULL for local collections, required for remote
        index=True
    )
    pipeline_id = Column(
        Integer,
        ForeignKey("pipelines.id", ondelete="SET NULL"),
        nullable=True,  # NULL = use default pipeline at runtime
        index=True
    )

    # Pipeline version (pinned when explicitly assigned)
    pipeline_version = Column(Integer, nullable=True)

    # Core fields
    name = Column(String(255), unique=True, nullable=False, index=True)
    type = Column(Enum(CollectionType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    location = Column(String(1024), nullable=False)
    state = Column(
        Enum(CollectionState, values_callable=lambda x: [e.value for e in x]),
        default=CollectionState.LIVE,
        nullable=False,
        index=True
    )

    # Cache configuration
    cache_ttl = Column(Integer, nullable=True)  # Seconds, NULL = use state default

    # Accessibility tracking
    is_accessible = Column(Boolean, default=True, nullable=False, index=True)
    last_error = Column(Text, nullable=True)

    # Optional metadata
    metadata_json = Column(Text, nullable=True)  # JSON string for flexibility

    # KPI statistics (populated during collection scan/refresh)
    storage_bytes = Column(BigInteger, nullable=True)  # Total storage in bytes
    file_count = Column(Integer, nullable=True)  # Total number of files
    image_count = Column(Integer, nullable=True)  # Number of images after grouping

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    connector = relationship("Connector", back_populates="collections")
    pipeline = relationship("Pipeline", back_populates="collections")
    analysis_results = relationship(
        "AnalysisResult",
        back_populates="collection",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    # Table-level constraints
    __table_args__ = (
        Index("idx_collection_state", "state"),
        Index("idx_collection_type", "type"),
        Index("idx_collection_accessible", "is_accessible"),
    )

    def get_effective_cache_ttl(self) -> int:
        """
        Get the effective cache TTL for this collection.

        Returns user-configured TTL if set, otherwise returns state-based default:
        - LIVE: 3600 seconds (1 hour)
        - CLOSED: 86400 seconds (24 hours)
        - ARCHIVED: 604800 seconds (7 days)

        Returns:
            Cache TTL in seconds

        Example:
            >>> collection = Collection(state=CollectionState.LIVE)
            >>> collection.get_effective_cache_ttl()
            3600
            >>> collection.cache_ttl = 7200
            >>> collection.get_effective_cache_ttl()
            7200
        """
        if self.cache_ttl is not None:
            return self.cache_ttl

        # Return state-based default from COLLECTION_STATE_TTL mapping
        state_name = self.state.value.capitalize()  # "live" -> "Live"
        return COLLECTION_STATE_TTL.get(state_name, 3600)  # Default to 1 hour

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Collection("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"type={self.type.value}, "
            f"state={self.state.value}, "
            f"accessible={self.is_accessible}"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.name} ({self.type.value}, {self.state.value})"
