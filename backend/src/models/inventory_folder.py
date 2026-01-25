"""
InventoryFolder model for discovered folders from cloud inventory.

Represents a folder discovered from AWS S3 Inventory or GCS Storage Insights reports.
Each folder is linked to a Connector and may optionally be mapped to a Collection.

Design Rationale:
- Folder Discovery: Extracted from inventory CSV files during import pipeline Phase A
- Collection Mapping: Folders can be mapped to Collections for FileInfo population
- Statistics Tracking: Object count and total size for folder-level metrics
- GUID Format: fld_{26-char Crockford Base32 UUIDv7}
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin


class InventoryFolder(Base, GuidMixin):
    """
    Folder discovered from cloud inventory data.

    Represents a folder path discovered during inventory import. Folders are extracted
    from object keys in the inventory CSV files and stored for user selection when
    creating Collections.

    Attributes:
        id: Primary key
        uuid: UUIDv7 for external identification (inherited from GuidMixin)
        guid: GUID string property (fld_xxx, inherited from GuidMixin)
        connector_id: Foreign key to parent Connector
        path: Full folder path ending with "/" (e.g., "2020/Event/")
        object_count: Number of objects directly in this folder
        total_size_bytes: Sum of object sizes in this folder
        deepest_modified: Most recent object modification timestamp in folder
        discovered_at: When this folder was first discovered
        collection_guid: GUID of mapped Collection (if any)

    Constraints:
        - path must be unique within a connector
        - path must end with "/"
        - object_count must be >= 0
        - total_size_bytes must be >= 0

    Indexes:
        - Unique: (connector_id, path)
        - connector_id (for folder listing)
        - collection_guid (for mapping lookup)

    Example:
        >>> folder = InventoryFolder(
        ...     connector_id=1,
        ...     path="2020/Vacation/",
        ...     object_count=150,
        ...     total_size_bytes=1024000000
        ... )
        >>> print(folder.guid)  # fld_01hgw2bbg...
    """

    __tablename__ = "inventory_folders"

    # GUID prefix for InventoryFolder entities
    GUID_PREFIX = "fld"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to Connector
    connector_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("connectors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Folder path (must end with "/")
    path: Mapped[str] = mapped_column(String(1024), nullable=False)

    # Statistics
    object_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    deepest_modified: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # Discovery timestamp
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Collection mapping (optional - set when folder is mapped to a Collection)
    collection_guid: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Relationships
    connector: Mapped["Connector"] = relationship(
        "Connector", back_populates="inventory_folders"
    )

    # Table-level constraints and indexes
    __table_args__ = (
        UniqueConstraint("connector_id", "path", name="uq_inventory_folder_path"),
        Index("ix_inventory_folder_connector", "connector_id"),
        Index("ix_inventory_folder_collection", "collection_guid"),
    )

    @property
    def is_mapped(self) -> bool:
        """
        Check if this folder is mapped to a Collection.

        Returns:
            True if collection_guid is set
        """
        return self.collection_guid is not None

    @property
    def name(self) -> str:
        """
        Get the folder name (last path component).

        Returns:
            The folder name without trailing slash

        Example:
            >>> folder = InventoryFolder(path="2020/Vacation/")
            >>> folder.name
            'Vacation'
        """
        # Remove trailing slash and get last component
        clean_path = self.path.rstrip("/")
        if "/" in clean_path:
            return clean_path.rsplit("/", 1)[-1]
        return clean_path

    @property
    def depth(self) -> int:
        """
        Get the folder depth (number of path segments).

        Returns:
            Depth as integer (1 for top-level folders)

        Example:
            >>> folder = InventoryFolder(path="2020/Vacation/Photos/")
            >>> folder.depth
            3
        """
        clean_path = self.path.rstrip("/")
        if not clean_path:
            return 0
        return clean_path.count("/") + 1

    @property
    def parent_path(self) -> Optional[str]:
        """
        Get the parent folder path.

        Returns:
            Parent path with trailing slash, or None for top-level folders

        Example:
            >>> folder = InventoryFolder(path="2020/Vacation/")
            >>> folder.parent_path
            '2020/'
        """
        clean_path = self.path.rstrip("/")
        if "/" not in clean_path:
            return None
        parent = clean_path.rsplit("/", 1)[0]
        return f"{parent}/"

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<InventoryFolder("
            f"id={self.id}, "
            f"path='{self.path}', "
            f"objects={self.object_count}, "
            f"size={self.total_size_bytes}, "
            f"mapped={self.is_mapped}"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        size_mb = self.total_size_bytes / (1024 * 1024) if self.total_size_bytes else 0
        return f"{self.path} ({self.object_count} objects, {size_mb:.1f} MB)"
