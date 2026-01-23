"""
Configuration model for persistent application settings.

Stores configuration items (extensions, cameras, processing methods) in the database
as an alternative to YAML file configuration. Supports import/export for migration.

Design Rationale:
- Database-first: Configuration stored in database for web UI management
- YAML compatibility: Structure mirrors YAML config for import/export
- Category organization: Items grouped by category (extensions, cameras, processing_methods)
- Source tracking: Records whether config came from database or YAML import
"""

import enum
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import Column, Integer, String, DateTime, Text, Enum, Index, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB

from backend.src.models import Base


class ConfigSource(enum.Enum):
    """
    Source of configuration item.

    Values:
    - DATABASE: Created or modified through web UI/API
    - YAML_IMPORT: Imported from YAML configuration file
    """
    DATABASE = "database"
    YAML_IMPORT = "yaml_import"


class Configuration(Base):
    """
    Configuration model for application settings.

    Stores key-value configuration items organized by category, supporting
    multiple data types through JSONB value storage.

    Attributes:
        id: Primary key
        category: Configuration category (extensions, cameras, processing_methods)
        key: Configuration key within category
        value_json: Configuration value (JSONB for type flexibility)
        description: Optional description of the configuration item
        source: Where this config came from (database, yaml_import)
        created_at: Creation timestamp
        updated_at: Last modification timestamp

    Categories:
        extensions:
            - photo_extensions: [".dng", ".cr3", ...]
            - metadata_extensions: [".xmp"]
            - require_sidecar: [".cr3"]

        cameras:
            - AB3D: {"name": "Canon EOS R5", "serial_number": "12345"}
            - CD5E: {"name": "Sony A7R IV", "serial_number": "67890"}

        processing_methods:
            - HDR: "High Dynamic Range"
            - BW: "Black and White"
            - PANO: "Panorama"

    Constraints:
        - (team_id, category, key) must be unique (team-scoped uniqueness)
        - category must be one of: extensions, cameras, processing_methods, result_retention
        - value_json must be valid JSON

    Indexes:
        - idx_config_category: category
        - uq_config_team_category_key: (team_id, category, key) unique
        - idx_config_source: source
    """

    __tablename__ = "configurations"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Tenant isolation
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)

    # Core fields
    category = Column(String(50), nullable=False, index=True)
    key = Column(String(255), nullable=False)
    # JSONB for PostgreSQL, JSON fallback for SQLite testing
    value_json = Column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    description = Column(Text, nullable=True)

    # Source tracking
    source = Column(
        Enum(ConfigSource, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ConfigSource.DATABASE,
        index=True
    )

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Indexes and constraints
    __table_args__ = (
        Index("idx_config_category", "category"),
        # Team-scoped unique constraint: each team can have its own config keys
        Index("uq_config_team_category_key", "team_id", "category", "key", unique=True),
        Index("idx_config_source", "source"),
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<Configuration("
            f"id={self.id}, "
            f"category='{self.category}', "
            f"key='{self.key}', "
            f"source={self.source.value if self.source else None}"
            f")>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.category}.{self.key} = {self.value_json}"

    def get_value(self) -> Any:
        """
        Get the configuration value.

        Returns:
            The value stored in value_json
        """
        return self.value_json

    def set_value(self, value: Any, source: Optional[ConfigSource] = None) -> None:
        """
        Set the configuration value.

        Args:
            value: New value to store
            source: Optional source to update (defaults to keeping current)
        """
        self.value_json = value
        if source is not None:
            self.source = source

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for API responses.

        Returns:
            Dictionary representation of the configuration item
        """
        return {
            "category": self.category,
            "key": self.key,
            "value": self.value_json,
            "description": self.description,
            "source": self.source.value if self.source else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_yaml_item(
        cls,
        category: str,
        key: str,
        value: Any,
        description: Optional[str] = None
    ) -> "Configuration":
        """
        Create a Configuration instance from YAML import data.

        Args:
            category: Configuration category
            key: Configuration key
            value: Configuration value
            description: Optional description

        Returns:
            New Configuration instance with YAML_IMPORT source
        """
        return cls(
            category=category,
            key=key,
            value_json=value,
            description=description,
            source=ConfigSource.YAML_IMPORT
        )
