"""
Configuration service for managing application settings.

Provides CRUD operations, YAML import/export, and conflict resolution for:
- Extension settings (photo_extensions, metadata_extensions, require_sidecar)
- Camera mappings (camera_id -> camera info)
- Processing methods (method_code -> description)

Design:
- Database-first: Configuration stored in database
- YAML compatibility: Import/export for migration
- Session-based import: Conflict detection and resolution
- Source tracking: Know where each config came from
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import yaml

from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.src.models import Configuration, ConfigSource
from backend.src.schemas.config import (
    ConfigItemResponse, ConfigStatsResponse, ConfigConflict
)
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError
from backend.src.services.guid import GuidService
from backend.src.utils.logging_config import get_logger


logger = get_logger("services")

# Valid configuration categories
VALID_CATEGORIES = {"extensions", "cameras", "processing_methods"}

# Import session expiry time (1 hour)
IMPORT_SESSION_TTL = timedelta(hours=1)


class ConfigService:
    """
    Service for managing application configuration.

    Handles CRUD operations, YAML import/export, and conflict resolution
    for configuration items stored in the database.

    Usage:
        >>> service = ConfigService(db_session)
        >>> config = service.create(
        ...     category="cameras",
        ...     key="AB3D",
        ...     value={"name": "Canon EOS R5"}
        ... )
        >>> all_config = service.get_all()
    """

    # Class-level storage for import sessions (shared across all instances)
    # In production, consider using Redis or database storage for persistence
    _import_sessions: Dict[str, Dict[str, Any]] = {}

    def __init__(self, db: Session):
        """
        Initialize configuration service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    def create(
        self,
        category: str,
        key: str,
        value: Any,
        description: Optional[str] = None,
        source: ConfigSource = ConfigSource.DATABASE
    ) -> ConfigItemResponse:
        """
        Create a new configuration item.

        Args:
            category: Configuration category (extensions, cameras, processing_methods)
            key: Configuration key within category
            value: Configuration value (any JSON-serializable type)
            description: Optional human-readable description
            source: Source of configuration (database or yaml_import)

        Returns:
            Created configuration item

        Raises:
            ValidationError: If category is invalid
            ConflictError: If category/key combination already exists
        """
        # Validate category
        if category not in VALID_CATEGORIES:
            raise ValidationError(
                f"Invalid category: {category}. "
                f"Valid categories: {', '.join(VALID_CATEGORIES)}"
            )

        # Check for duplicate
        existing = self.db.query(Configuration).filter(
            Configuration.category == category,
            Configuration.key == key
        ).first()

        if existing:
            raise ConflictError(
                f"Configuration {category}.{key} already exists"
            )

        # Create new configuration
        config = Configuration(
            category=category,
            key=key,
            value_json=value,
            description=description,
            source=source
        )

        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)

        logger.info(
            f"Created configuration {category}.{key}",
            extra={"category": category, "key": key, "source": source.value}
        )

        return self._to_response(config)

    def get(self, category: str, key: str) -> Optional[ConfigItemResponse]:
        """
        Get configuration by category and key.

        Args:
            category: Configuration category
            key: Configuration key

        Returns:
            Configuration item or None if not found
        """
        config = self.db.query(Configuration).filter(
            Configuration.category == category,
            Configuration.key == key
        ).first()

        if not config:
            return None

        return self._to_response(config)

    def get_by_id(self, config_id: int) -> ConfigItemResponse:
        """
        Get configuration by ID.

        Args:
            config_id: Configuration item ID

        Returns:
            Configuration item

        Raises:
            NotFoundError: If configuration doesn't exist
        """
        config = self.db.query(Configuration).filter(
            Configuration.id == config_id
        ).first()

        if not config:
            raise NotFoundError("Configuration", config_id)

        return self._to_response(config)

    def list(
        self,
        category_filter: Optional[str] = None
    ) -> List[ConfigItemResponse]:
        """
        List all configuration items.

        Args:
            category_filter: Optional category to filter by

        Returns:
            List of configuration items
        """
        query = self.db.query(Configuration)

        if category_filter:
            if category_filter not in VALID_CATEGORIES:
                raise ValidationError(f"Invalid category: {category_filter}")
            query = query.filter(Configuration.category == category_filter)

        configs = query.order_by(
            Configuration.category,
            Configuration.key
        ).all()

        return [self._to_response(c) for c in configs]

    def update(
        self,
        category: str,
        key: str,
        value: Optional[Any] = None,
        description: Optional[str] = None
    ) -> ConfigItemResponse:
        """
        Update a configuration item.

        Args:
            category: Configuration category
            key: Configuration key
            value: New value (optional)
            description: New description (optional)

        Returns:
            Updated configuration item

        Raises:
            NotFoundError: If configuration doesn't exist
        """
        config = self.db.query(Configuration).filter(
            Configuration.category == category,
            Configuration.key == key
        ).first()

        if not config:
            raise NotFoundError("Configuration", f"{category}.{key}")

        if value is not None:
            config.value_json = value
            config.source = ConfigSource.DATABASE

        if description is not None:
            config.description = description

        self.db.commit()
        self.db.refresh(config)

        logger.info(
            f"Updated configuration {category}.{key}",
            extra={"category": category, "key": key}
        )

        return self._to_response(config)

    def delete(self, category: str, key: str) -> int:
        """
        Delete a configuration item.

        Args:
            category: Configuration category
            key: Configuration key

        Returns:
            ID of deleted configuration

        Raises:
            NotFoundError: If configuration doesn't exist
        """
        config = self.db.query(Configuration).filter(
            Configuration.category == category,
            Configuration.key == key
        ).first()

        if not config:
            raise NotFoundError("Configuration", f"{category}.{key}")

        config_id = config.id
        self.db.delete(config)
        self.db.commit()

        logger.info(
            f"Deleted configuration {category}.{key}",
            extra={"category": category, "key": key, "config_id": config_id}
        )

        return config_id

    # =========================================================================
    # Get All Configuration
    # =========================================================================

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all configuration organized by category.

        Returns:
            Dictionary with categories as keys
        """
        result = {
            "extensions": {},
            "cameras": {},
            "processing_methods": {}
        }

        configs = self.db.query(Configuration).all()

        for config in configs:
            if config.category == "extensions":
                result["extensions"][config.key] = config.value_json
            elif config.category == "cameras":
                result["cameras"][config.key] = config.value_json
            elif config.category == "processing_methods":
                result["processing_methods"][config.key] = config.value_json

        return result

    def get_category(self, category: str) -> List[ConfigItemResponse]:
        """
        Get all configuration items for a category.

        Args:
            category: Configuration category

        Returns:
            List of configuration items in category

        Raises:
            ValidationError: If category is invalid
        """
        if category not in VALID_CATEGORIES:
            raise ValidationError(f"Invalid category: {category}")

        return self.list(category_filter=category)

    # =========================================================================
    # Extension Seeding
    # =========================================================================

    # Default extension keys that must always exist
    DEFAULT_EXTENSION_KEYS = ["photo_extensions", "metadata_extensions", "require_sidecar"]

    def seed_default_extensions(self) -> None:
        """
        Ensure the default extension keys exist with empty arrays.

        This method is idempotent - it only creates keys that don't exist.
        Called on application startup to ensure extensions are always editable.
        """
        for key in self.DEFAULT_EXTENSION_KEYS:
            existing = self.db.query(Configuration).filter(
                Configuration.category == "extensions",
                Configuration.key == key
            ).first()

            if not existing:
                config = Configuration(
                    category="extensions",
                    key=key,
                    value_json=[],
                    description=f"Default {key.replace('_', ' ')}",
                    source=ConfigSource.DATABASE
                )
                self.db.add(config)
                logger.info(f"Seeded default extension key: {key}")

        self.db.commit()

    # =========================================================================
    # Import Operations
    # =========================================================================

    def start_import(
        self,
        yaml_content: str,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start a YAML import session with conflict detection.

        Args:
            yaml_content: YAML configuration content
            filename: Original filename (optional)

        Returns:
            Import session with conflicts

        Raises:
            ValidationError: If YAML is invalid
        """
        # Parse YAML
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML: {str(e)}")

        if not isinstance(data, dict):
            raise ValidationError("YAML must be a dictionary")

        # Convert YAML structure to flat items
        items = self._parse_yaml_config(data)

        # Detect conflicts
        conflicts = self.detect_conflicts(data)

        # Create session with GUID format
        session_id = GuidService.generate_guid("imp")
        expires_at = datetime.utcnow() + IMPORT_SESSION_TTL

        self._import_sessions[session_id] = {
            "session_id": session_id,
            "status": "pending",
            "expires_at": expires_at,
            "file_name": filename,
            "yaml_data": data,
            "items": items,
            "total_items": len(items),
            "new_items": len(items) - len(conflicts),
            "conflicts": conflicts
        }

        logger.info(
            f"Started import session {session_id}",
            extra={
                "session_id": session_id,
                "total_items": len(items),
                "conflicts": len(conflicts)
            }
        )

        return self._import_sessions[session_id]

    def get_import_session(self, session_id: str) -> Dict[str, Any]:
        """
        Get import session by ID.

        Args:
            session_id: Session UUID

        Returns:
            Import session data

        Raises:
            NotFoundError: If session doesn't exist or expired
        """
        session = self._import_sessions.get(session_id)

        if not session:
            raise NotFoundError("Import session", session_id)

        # Check expiration
        if datetime.utcnow() > session["expires_at"]:
            del self._import_sessions[session_id]
            raise NotFoundError("Import session", session_id)

        return session

    def apply_import(
        self,
        session_id: str,
        resolutions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Apply import with conflict resolutions.

        Args:
            session_id: Session UUID
            resolutions: List of conflict resolutions

        Returns:
            Import result

        Raises:
            NotFoundError: If session doesn't exist
            ValidationError: If unresolved conflicts remain
        """
        session = self.get_import_session(session_id)

        # Build resolution map
        resolution_map = {
            (r["category"], r["key"]): r["use_yaml"]
            for r in resolutions
        }

        items_imported = 0
        items_skipped = 0

        # Apply each item
        for item in session["items"]:
            category = item["category"]
            key = item["key"]
            value = item["value"]

            # Check if this is a conflict
            is_conflict = any(
                c["category"] == category and c["key"] == key
                for c in session["conflicts"]
            )

            if is_conflict:
                # Check resolution
                use_yaml = resolution_map.get((category, key))
                if use_yaml is None:
                    # No resolution provided, skip
                    items_skipped += 1
                    continue
                elif not use_yaml:
                    # Keep database value
                    items_skipped += 1
                    continue

            # Apply the item
            existing = self.db.query(Configuration).filter(
                Configuration.category == category,
                Configuration.key == key
            ).first()

            if existing:
                existing.value_json = value
                existing.source = ConfigSource.YAML_IMPORT
            else:
                config = Configuration(
                    category=category,
                    key=key,
                    value_json=value,
                    source=ConfigSource.YAML_IMPORT
                )
                self.db.add(config)

            items_imported += 1

        self.db.commit()

        # Mark session as applied
        session["status"] = "applied"

        logger.info(
            f"Applied import session {session_id}",
            extra={
                "session_id": session_id,
                "items_imported": items_imported,
                "items_skipped": items_skipped
            }
        )

        return {
            "success": True,
            "items_imported": items_imported,
            "items_skipped": items_skipped,
            "message": f"Import completed: {items_imported} items imported, {items_skipped} skipped"
        }

    def cancel_import(self, session_id: str) -> None:
        """
        Cancel an import session.

        Args:
            session_id: Session UUID

        Raises:
            NotFoundError: If session doesn't exist
        """
        if session_id not in self._import_sessions:
            raise NotFoundError("Import session", session_id)

        del self._import_sessions[session_id]

        logger.info(f"Cancelled import session {session_id}")

    def detect_conflicts(self, yaml_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Detect conflicts between YAML data and existing configuration.

        Args:
            yaml_data: Parsed YAML configuration

        Returns:
            List of conflicts
        """
        conflicts = []

        # Check extensions
        for ext_key in ["photo_extensions", "metadata_extensions", "require_sidecar"]:
            if ext_key in yaml_data:
                existing = self.get("extensions", ext_key)
                if existing and existing.value != yaml_data[ext_key]:
                    conflicts.append({
                        "category": "extensions",
                        "key": ext_key,
                        "database_value": existing.value,
                        "yaml_value": yaml_data[ext_key],
                        "resolved": False,
                        "resolution": None
                    })

        # Check camera mappings
        if "camera_mappings" in yaml_data:
            for camera_id, camera_info in yaml_data["camera_mappings"].items():
                existing = self.get("cameras", camera_id)
                if existing and existing.value != camera_info:
                    conflicts.append({
                        "category": "cameras",
                        "key": camera_id,
                        "database_value": existing.value,
                        "yaml_value": camera_info,
                        "resolved": False,
                        "resolution": None
                    })

        # Check processing methods
        if "processing_methods" in yaml_data:
            for method_code, description in yaml_data["processing_methods"].items():
                existing = self.get("processing_methods", method_code)
                if existing and existing.value != description:
                    conflicts.append({
                        "category": "processing_methods",
                        "key": method_code,
                        "database_value": existing.value,
                        "yaml_value": description,
                        "resolved": False,
                        "resolution": None
                    })

        return conflicts

    # =========================================================================
    # Export Operations
    # =========================================================================

    def export_to_yaml(self) -> str:
        """
        Export all configuration to YAML format.

        Returns:
            YAML string
        """
        all_config = self.get_all()

        # Build YAML structure matching config.yaml format
        yaml_data = {}

        # Extensions
        for key in ["photo_extensions", "metadata_extensions", "require_sidecar"]:
            if key in all_config["extensions"]:
                yaml_data[key] = all_config["extensions"][key]

        # Camera mappings
        if all_config["cameras"]:
            yaml_data["camera_mappings"] = all_config["cameras"]

        # Processing methods
        if all_config["processing_methods"]:
            yaml_data["processing_methods"] = all_config["processing_methods"]

        return yaml.safe_dump(yaml_data, default_flow_style=False, sort_keys=False)

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> ConfigStatsResponse:
        """
        Get configuration statistics for dashboard KPIs.

        Returns:
            Statistics including counts and source breakdown
        """
        total = self.db.query(func.count(Configuration.id)).scalar() or 0

        cameras = self.db.query(func.count(Configuration.id)).filter(
            Configuration.category == "cameras"
        ).scalar() or 0

        methods = self.db.query(func.count(Configuration.id)).filter(
            Configuration.category == "processing_methods"
        ).scalar() or 0

        # Source breakdown
        database_count = self.db.query(func.count(Configuration.id)).filter(
            Configuration.source == ConfigSource.DATABASE
        ).scalar() or 0

        yaml_count = self.db.query(func.count(Configuration.id)).filter(
            Configuration.source == ConfigSource.YAML_IMPORT
        ).scalar() or 0

        # Last import timestamp
        last_import = self.db.query(func.max(Configuration.updated_at)).filter(
            Configuration.source == ConfigSource.YAML_IMPORT
        ).scalar()

        return ConfigStatsResponse(
            total_items=total,
            cameras_configured=cameras,
            processing_methods_configured=methods,
            last_import=last_import,
            source_breakdown={
                "database": database_count,
                "yaml_import": yaml_count
            }
        )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _to_response(self, config: Configuration) -> ConfigItemResponse:
        """
        Convert Configuration model to response schema.

        Args:
            config: Configuration model

        Returns:
            Configuration response
        """
        return ConfigItemResponse(
            id=config.id,
            category=config.category,
            key=config.key,
            value=config.value_json,
            description=config.description,
            source=config.source.value if config.source else "database",
            created_at=config.created_at,
            updated_at=config.updated_at
        )

    def _parse_yaml_config(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse YAML config structure into flat list of items.

        Args:
            data: Parsed YAML data

        Returns:
            List of config items with category, key, value
        """
        items = []

        # Extensions
        for ext_key in ["photo_extensions", "metadata_extensions", "require_sidecar"]:
            if ext_key in data:
                items.append({
                    "category": "extensions",
                    "key": ext_key,
                    "value": data[ext_key]
                })

        # Camera mappings
        if "camera_mappings" in data:
            for camera_id, camera_info in data["camera_mappings"].items():
                items.append({
                    "category": "cameras",
                    "key": camera_id,
                    "value": camera_info
                })

        # Processing methods
        if "processing_methods" in data:
            for method_code, description in data["processing_methods"].items():
                items.append({
                    "category": "processing_methods",
                    "key": method_code,
                    "value": description
                })

        return items
