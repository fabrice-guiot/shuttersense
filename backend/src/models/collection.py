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
from typing import Dict, List, Optional, Any

from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Enum, Text, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship

from backend.src.models.types import JSONBType

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin, AuditMixin
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


class Collection(Base, GuidMixin, AuditMixin):
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
        bound_agent_id: Agent bound to this LOCAL collection (FK to agents)
        last_refresh_at: Last completed refresh timestamp
        created_at: Creation timestamp
        updated_at: Last update timestamp
        connector: Related connector (many-to-one, NULL for local)
        pipeline: Related pipeline (many-to-one, NULL = use default)
        bound_agent: Bound agent for LOCAL collections (many-to-one)
        analysis_results: Related analysis results (one-to-many, cascade delete)
        jobs: Related jobs (one-to-many)

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

    # Tenant isolation
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)

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
    # NULL = pending/unknown (test in progress), True = accessible, False = not accessible
    is_accessible = Column(Boolean, default=True, nullable=True, index=True)
    last_error = Column(Text, nullable=True)

    # Optional metadata
    metadata_json = Column(Text, nullable=True)  # JSON string for flexibility

    # KPI statistics (populated during collection scan/refresh)
    storage_bytes = Column(BigInteger, nullable=True)  # Total storage in bytes
    file_count = Column(Integer, nullable=True)  # Total number of files
    image_count = Column(Integer, nullable=True)  # Number of images after grouping

    # Agent binding (for LOCAL collections)
    bound_agent_id = Column(
        Integer,
        ForeignKey("agents.id", name="fk_collections_bound_agent_id"),
        nullable=True,
        index=True
    )

    # Last refresh timestamp (updated when tool completes)
    last_refresh_at = Column(DateTime, nullable=True)

    # FileInfo cache from inventory import (Issue #107 - Bucket Inventory Import)
    # JSONB array of FileInfo objects: {key, size, last_modified, etag, storage_class}
    file_info = Column(JSONBType, nullable=True)
    # When FileInfo was last updated from inventory or API
    file_info_updated_at = Column(DateTime, nullable=True)
    # Source of FileInfo: "api" (direct cloud list) or "inventory" (from inventory import)
    file_info_source = Column(String(20), nullable=True)
    # Delta summary from last inventory import: {new_count, modified_count, deleted_count, computed_at}
    file_info_delta = Column(JSONBType, nullable=True)

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
    bound_agent = relationship(
        "Agent",
        back_populates="bound_collections",
        lazy="joined"
    )
    analysis_results = relationship(
        "AnalysisResult",
        back_populates="collection",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    jobs = relationship(
        "Job",
        back_populates="collection",
        lazy="dynamic"
    )

    # Table-level constraints
    __table_args__ = (
        Index("idx_collection_state", "state"),
        Index("idx_collection_type", "type"),
        Index("idx_collection_accessible", "is_accessible"),
    )

    @property
    def is_local(self) -> bool:
        """
        Check if this is a local collection.

        Returns:
            True if collection type is LOCAL
        """
        return self.type == CollectionType.LOCAL

    @property
    def requires_bound_agent(self) -> bool:
        """
        Check if this collection requires a bound agent.

        LOCAL collections require a bound agent for job execution.

        Returns:
            True if collection is LOCAL type
        """
        return self.type == CollectionType.LOCAL

    @property
    def has_bound_agent(self) -> bool:
        """
        Check if this collection has a bound agent.

        Returns:
            True if bound_agent_id is set
        """
        return self.bound_agent_id is not None

    @property
    def has_file_info(self) -> bool:
        """
        Check if this collection has cached FileInfo.

        Returns:
            True if file_info is set and not empty
        """
        return self.file_info is not None and len(self.file_info) > 0

    @property
    def has_inventory_file_info(self) -> bool:
        """
        Check if this collection has FileInfo from inventory import.

        Returns:
            True if file_info_source is "inventory"
        """
        return self.file_info_source == "inventory"

    @property
    def file_info_count(self) -> int:
        """
        Get the number of files in cached FileInfo.

        Returns:
            Number of FileInfo entries, or 0 if not cached
        """
        if self.file_info is None:
            return 0
        return len(self.file_info)

    def get_effective_cache_ttl(self, team_ttl_config: Optional[Dict[str, int]] = None) -> int:
        """
        Get the effective cache TTL for this collection.

        Priority order:
        1. Team TTL config (if provided) - from team's collection_ttl configuration
        2. Hardcoded defaults based on collection state

        Args:
            team_ttl_config: Optional dict mapping state to TTL in seconds.
                             Expected keys: 'live', 'closed', 'archived'.
                             If not provided, falls back to hardcoded defaults.

        Returns:
            Cache TTL in seconds

        Defaults (if no team config):
        - LIVE: 3600 seconds (1 hour)
        - CLOSED: 86400 seconds (24 hours)
        - ARCHIVED: 604800 seconds (7 days)

        Example:
            >>> collection = Collection(state=CollectionState.LIVE)
            >>> collection.get_effective_cache_ttl()
            3600
            >>> collection.get_effective_cache_ttl({'live': 1800, 'closed': 43200, 'archived': 259200})
            1800
        """
        # Get the state value (lowercase)
        state_value = self.state.value  # "live", "closed", or "archived"

        # Use team config if provided
        if team_ttl_config is not None and state_value in team_ttl_config:
            return team_ttl_config[state_value]

        # Fall back to hardcoded defaults from COLLECTION_STATE_TTL mapping
        state_name = state_value.capitalize()  # "live" -> "Live"
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
