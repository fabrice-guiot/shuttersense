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
VALID_CATEGORIES = {"extensions", "cameras", "processing_methods", "event_statuses", "collection_ttl"}

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
        team_id: int,
        description: Optional[str] = None,
        source: ConfigSource = ConfigSource.DATABASE
    ) -> ConfigItemResponse:
        """
        Create a new configuration item.

        Args:
            category: Configuration category (extensions, cameras, processing_methods)
            key: Configuration key within category
            value: Configuration value (any JSON-serializable type)
            team_id: Team ID for tenant isolation
            description: Optional human-readable description
            source: Source of configuration (database or yaml_import)

        Returns:
            Created configuration item

        Raises:
            ValidationError: If category is invalid
            ConflictError: If category/key combination already exists for this team
        """
        # Validate category
        if category not in VALID_CATEGORIES:
            raise ValidationError(
                f"Invalid category: {category}. "
                f"Valid categories: {', '.join(VALID_CATEGORIES)}"
            )

        # Check for duplicate within team
        existing = self.db.query(Configuration).filter(
            Configuration.category == category,
            Configuration.key == key,
            Configuration.team_id == team_id
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
            source=source,
            team_id=team_id
        )

        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)

        logger.info(
            f"Created configuration {category}.{key}",
            extra={"category": category, "key": key, "source": source.value, "team_id": team_id}
        )

        return self._to_response(config)

    def get(
        self,
        category: str,
        key: str,
        team_id: Optional[int] = None
    ) -> Optional[ConfigItemResponse]:
        """
        Get configuration by category and key.

        Args:
            category: Configuration category
            key: Configuration key
            team_id: Team ID for tenant isolation (if provided, filters by team)

        Returns:
            Configuration item or None if not found
        """
        query = self.db.query(Configuration).filter(
            Configuration.category == category,
            Configuration.key == key
        )
        if team_id is not None:
            query = query.filter(Configuration.team_id == team_id)

        config = query.first()

        if not config:
            return None

        return self._to_response(config)

    def get_by_id(
        self,
        config_id: int,
        team_id: Optional[int] = None
    ) -> ConfigItemResponse:
        """
        Get configuration by ID.

        Args:
            config_id: Configuration item ID
            team_id: Team ID for tenant isolation (if provided, filters by team)

        Returns:
            Configuration item

        Raises:
            NotFoundError: If configuration doesn't exist or belongs to different team
        """
        query = self.db.query(Configuration).filter(
            Configuration.id == config_id
        )
        if team_id is not None:
            query = query.filter(Configuration.team_id == team_id)

        config = query.first()

        if not config:
            raise NotFoundError("Configuration", config_id)

        return self._to_response(config)

    def list(
        self,
        team_id: int,
        category_filter: Optional[str] = None
    ) -> List[ConfigItemResponse]:
        """
        List all configuration items for a team.

        Args:
            team_id: Team ID for tenant isolation
            category_filter: Optional category to filter by

        Returns:
            List of configuration items
        """
        query = self.db.query(Configuration).filter(Configuration.team_id == team_id)

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
        team_id: int,
        value: Optional[Any] = None,
        description: Optional[str] = None
    ) -> ConfigItemResponse:
        """
        Update a configuration item.

        Args:
            category: Configuration category
            key: Configuration key
            team_id: Team ID for tenant isolation
            value: New value (optional)
            description: New description (optional)

        Returns:
            Updated configuration item

        Raises:
            NotFoundError: If configuration doesn't exist or belongs to different team
        """
        config = self.db.query(Configuration).filter(
            Configuration.category == category,
            Configuration.key == key,
            Configuration.team_id == team_id
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

    def delete(self, category: str, key: str, team_id: int) -> int:
        """
        Delete a configuration item.

        Args:
            category: Configuration category
            key: Configuration key
            team_id: Team ID for tenant isolation

        Returns:
            ID of deleted configuration

        Raises:
            NotFoundError: If configuration doesn't exist or belongs to different team
        """
        config = self.db.query(Configuration).filter(
            Configuration.category == category,
            Configuration.key == key,
            Configuration.team_id == team_id
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

    def get_all(self, team_id: int) -> Dict[str, Dict[str, Any]]:
        """
        Get all configuration organized by category for a team.

        Args:
            team_id: Team ID for tenant isolation

        Returns:
            Dictionary with categories as keys
        """
        result = {
            "extensions": {},
            "cameras": {},
            "processing_methods": {},
            "event_statuses": {},
            "collection_ttl": {}
        }

        configs = self.db.query(Configuration).filter(
            Configuration.team_id == team_id
        ).all()

        for config in configs:
            if config.category == "extensions":
                result["extensions"][config.key] = config.value_json
            elif config.category == "cameras":
                result["cameras"][config.key] = config.value_json
            elif config.category == "processing_methods":
                result["processing_methods"][config.key] = config.value_json
            elif config.category == "event_statuses":
                result["event_statuses"][config.key] = config.value_json
            elif config.category == "collection_ttl":
                result["collection_ttl"][config.key] = config.value_json

        return result

    def get_category(self, category: str, team_id: int) -> List[ConfigItemResponse]:
        """
        Get all configuration items for a category.

        Args:
            category: Configuration category
            team_id: Team ID for tenant isolation

        Returns:
            List of configuration items in category

        Raises:
            ValidationError: If category is invalid
        """
        if category not in VALID_CATEGORIES:
            raise ValidationError(f"Invalid category: {category}")

        return self.list(team_id=team_id, category_filter=category)

    def get_event_statuses(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get event statuses ordered by their display_order value.

        Args:
            team_id: Team ID for tenant isolation

        Returns:
            List of status objects with key, label, and display_order
        """
        configs = self.db.query(Configuration).filter(
            Configuration.category == "event_statuses",
            Configuration.team_id == team_id
        ).all()

        # Each status value_json contains: {"label": "...", "display_order": N}
        statuses = []
        for config in configs:
            value = config.value_json if isinstance(config.value_json, dict) else {}
            statuses.append({
                "key": config.key,
                "label": value.get("label", config.key.replace("_", " ").title()),
                "display_order": value.get("display_order", 999)
            })

        # Sort by display_order
        statuses.sort(key=lambda x: x["display_order"])
        return statuses

    def get_collection_ttl(self, team_id: int) -> Dict[str, int]:
        """
        Get collection TTL values for a team.

        Returns TTL values (in seconds) for each collection state.
        Falls back to hardcoded defaults if team config is missing.

        Args:
            team_id: Team ID for tenant isolation

        Returns:
            Dict mapping state to TTL in seconds: {'live': 3600, 'closed': 86400, 'archived': 604800}
        """
        # Hardcoded defaults as fallback
        defaults = {
            'live': 3600,       # 1 hour
            'closed': 86400,   # 24 hours
            'archived': 604800  # 7 days
        }

        configs = self.db.query(Configuration).filter(
            Configuration.category == "collection_ttl",
            Configuration.team_id == team_id
        ).all()

        if not configs:
            logger.debug(f"No collection TTL config found for team {team_id}, using defaults")
            return defaults

        # Build result from configs
        result = {}
        for config in configs:
            value = config.value_json if isinstance(config.value_json, dict) else {}
            ttl_value = value.get("value")
            if ttl_value is not None and isinstance(ttl_value, (int, float)):
                result[config.key] = int(ttl_value)

        # Fill in any missing states with defaults
        for state, default_ttl in defaults.items():
            if state not in result:
                result[state] = default_ttl

        return result

    # =========================================================================
    # Extension Seeding
    # =========================================================================

    # Default extension keys that must always exist
    DEFAULT_EXTENSION_KEYS = ["photo_extensions", "metadata_extensions", "require_sidecar"]

    def seed_default_extensions(self, team_id: int) -> None:
        """
        Ensure the default extension keys exist with empty arrays for a team.

        This method is idempotent - it only creates keys that don't exist.
        Called on application startup to ensure extensions are always editable.

        Args:
            team_id: Team ID for tenant isolation
        """
        for key in self.DEFAULT_EXTENSION_KEYS:
            existing = self.db.query(Configuration).filter(
                Configuration.category == "extensions",
                Configuration.key == key,
                Configuration.team_id == team_id
            ).first()

            if not existing:
                config = Configuration(
                    category="extensions",
                    key=key,
                    value_json=[],
                    description=f"Default {key.replace('_', ' ')}",
                    source=ConfigSource.DATABASE,
                    team_id=team_id
                )
                self.db.add(config)
                logger.info(f"Seeded default extension key: {key} for team {team_id}")

        self.db.commit()

    # =========================================================================
    # Import Operations
    # =========================================================================

    def start_import(
        self,
        yaml_content: str,
        team_id: int,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start a YAML import session with conflict detection.

        Args:
            yaml_content: YAML configuration content
            team_id: Team ID for tenant isolation
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
        conflicts = self.detect_conflicts(data, team_id)

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
            "conflicts": conflicts,
            "team_id": team_id
        }

        logger.info(
            f"Started import session {session_id}",
            extra={
                "session_id": session_id,
                "total_items": len(items),
                "conflicts": len(conflicts),
                "team_id": team_id
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
        team_id = session["team_id"]

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
                Configuration.key == key,
                Configuration.team_id == team_id
            ).first()

            if existing:
                existing.value_json = value
                existing.source = ConfigSource.YAML_IMPORT
            else:
                config = Configuration(
                    category=category,
                    key=key,
                    value_json=value,
                    source=ConfigSource.YAML_IMPORT,
                    team_id=team_id
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
                "items_skipped": items_skipped,
                "team_id": team_id
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

    def detect_conflicts(self, yaml_data: Dict[str, Any], team_id: int) -> List[Dict[str, Any]]:
        """
        Detect conflicts between YAML data and existing configuration.

        Args:
            yaml_data: Parsed YAML configuration
            team_id: Team ID for tenant isolation

        Returns:
            List of conflicts
        """
        conflicts = []

        # Check extensions
        for ext_key in ["photo_extensions", "metadata_extensions", "require_sidecar"]:
            if ext_key in yaml_data:
                existing = self.get("extensions", ext_key, team_id=team_id)
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
                existing = self.get("cameras", camera_id, team_id=team_id)
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
                existing = self.get("processing_methods", method_code, team_id=team_id)
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

    def export_to_yaml(self, team_id: int) -> str:
        """
        Export all configuration to YAML format for a team.

        Args:
            team_id: Team ID for tenant isolation

        Returns:
            YAML string
        """
        all_config = self.get_all(team_id)

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

    def get_stats(self, team_id: int) -> ConfigStatsResponse:
        """
        Get configuration statistics for dashboard KPIs.

        Args:
            team_id: Team ID for tenant isolation

        Returns:
            Statistics including counts and source breakdown
        """
        total = self.db.query(func.count(Configuration.id)).filter(
            Configuration.team_id == team_id
        ).scalar() or 0

        cameras = self.db.query(func.count(Configuration.id)).filter(
            Configuration.team_id == team_id,
            Configuration.category == "cameras"
        ).scalar() or 0

        methods = self.db.query(func.count(Configuration.id)).filter(
            Configuration.team_id == team_id,
            Configuration.category == "processing_methods"
        ).scalar() or 0

        # Source breakdown
        database_count = self.db.query(func.count(Configuration.id)).filter(
            Configuration.team_id == team_id,
            Configuration.source == ConfigSource.DATABASE
        ).scalar() or 0

        yaml_count = self.db.query(func.count(Configuration.id)).filter(
            Configuration.team_id == team_id,
            Configuration.source == ConfigSource.YAML_IMPORT
        ).scalar() or 0

        # Last import timestamp
        last_import = self.db.query(func.max(Configuration.updated_at)).filter(
            Configuration.team_id == team_id,
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
