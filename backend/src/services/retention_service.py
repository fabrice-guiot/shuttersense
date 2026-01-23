"""
Retention service for managing team-level retention settings.

Issue #92: Storage Optimization for Analysis Results
Provides CRUD operations for retention policy configuration stored in the
Configuration model with category `result_retention`.

Design:
- Uses existing Configuration model for storage
- Returns defaults when settings don't exist
- Validates values against allowed options
- Tenant-scoped via TenantContext
"""

from typing import Dict, Any

from sqlalchemy.orm import Session

from backend.src.middleware.tenant import TenantContext
from backend.src.models import Configuration, ConfigSource
from backend.src.schemas.retention import (
    RetentionSettingsResponse,
    RetentionSettingsUpdate,
    VALID_RETENTION_DAYS,
    VALID_PRESERVE_COUNTS,
    DEFAULT_JOB_COMPLETED_DAYS,
    DEFAULT_JOB_FAILED_DAYS,
    DEFAULT_RESULT_COMPLETED_DAYS,
    DEFAULT_PRESERVE_PER_COLLECTION,
)
from backend.src.services.exceptions import ValidationError
from backend.src.utils.logging_config import get_logger


logger = get_logger("services")

# Configuration category for retention settings
RETENTION_CATEGORY = "result_retention"

# Retention setting keys
KEY_JOB_COMPLETED_DAYS = "job_completed_days"
KEY_JOB_FAILED_DAYS = "job_failed_days"
KEY_RESULT_COMPLETED_DAYS = "result_completed_days"
KEY_PRESERVE_PER_COLLECTION = "preserve_per_collection"


class RetentionService:
    """
    Service for managing retention settings.

    Handles retrieval and updates of team-level retention policy
    configuration stored in the Configuration model.

    Usage:
        >>> service = RetentionService(db_session)
        >>> settings = service.get_settings(ctx)
        >>> service.update_settings(ctx, update)
    """

    def __init__(self, db: Session):
        """
        Initialize retention service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_settings(self, ctx: TenantContext) -> RetentionSettingsResponse:
        """
        Get retention settings for a team.

        Returns default values if settings have not been configured.

        Args:
            ctx: Tenant context for team isolation

        Returns:
            Current retention settings with defaults applied
        """
        team_id = ctx.team_id

        # Query all retention settings for this team
        configs = (
            self.db.query(Configuration)
            .filter(
                Configuration.team_id == team_id,
                Configuration.category == RETENTION_CATEGORY
            )
            .all()
        )

        # Build a lookup dict
        config_map: Dict[str, Any] = {c.key: c.value_json for c in configs}

        # Return settings with defaults for missing values
        return RetentionSettingsResponse(
            job_completed_days=config_map.get(
                KEY_JOB_COMPLETED_DAYS, DEFAULT_JOB_COMPLETED_DAYS
            ),
            job_failed_days=config_map.get(
                KEY_JOB_FAILED_DAYS, DEFAULT_JOB_FAILED_DAYS
            ),
            result_completed_days=config_map.get(
                KEY_RESULT_COMPLETED_DAYS, DEFAULT_RESULT_COMPLETED_DAYS
            ),
            preserve_per_collection=config_map.get(
                KEY_PRESERVE_PER_COLLECTION, DEFAULT_PRESERVE_PER_COLLECTION
            ),
        )

    def update_settings(
        self,
        ctx: TenantContext,
        update: RetentionSettingsUpdate,
    ) -> RetentionSettingsResponse:
        """
        Update retention settings for a team.

        Only provided fields are updated; others remain unchanged.

        Args:
            ctx: Tenant context for team isolation
            update: Update request with optional fields

        Returns:
            Updated retention settings

        Raises:
            ValidationError: If any value is not in the allowed options
        """
        team_id = ctx.team_id
        updates = update.model_dump(exclude_none=True)

        if not updates:
            # No changes requested, return current settings
            return self.get_settings(ctx)

        # Validate all provided values
        for key, value in updates.items():
            self._validate_setting(key, value)

        # Update each provided setting
        for key, value in updates.items():
            self._upsert_setting(team_id, key, value)

        self.db.commit()

        logger.info(
            f"Updated retention settings for team {team_id}: {updates}",
            extra={"team_id": team_id, "updates": updates}
        )

        return self.get_settings(ctx)

    def get_settings_by_team_id(self, team_id: int) -> RetentionSettingsResponse:
        """
        Get retention settings for a team by raw team_id.

        This is an internal method for service-to-service calls where
        TenantContext is not available (e.g., cleanup service, metrics service).
        For API endpoints, use get_settings(ctx) instead.

        Args:
            team_id: Team ID for tenant isolation

        Returns:
            Current retention settings with defaults applied
        """
        # Query all retention settings for this team
        configs = (
            self.db.query(Configuration)
            .filter(
                Configuration.team_id == team_id,
                Configuration.category == RETENTION_CATEGORY
            )
            .all()
        )

        # Build a lookup dict
        config_map: Dict[str, Any] = {c.key: c.value_json for c in configs}

        # Return settings with defaults for missing values
        return RetentionSettingsResponse(
            job_completed_days=config_map.get(
                KEY_JOB_COMPLETED_DAYS, DEFAULT_JOB_COMPLETED_DAYS
            ),
            job_failed_days=config_map.get(
                KEY_JOB_FAILED_DAYS, DEFAULT_JOB_FAILED_DAYS
            ),
            result_completed_days=config_map.get(
                KEY_RESULT_COMPLETED_DAYS, DEFAULT_RESULT_COMPLETED_DAYS
            ),
            preserve_per_collection=config_map.get(
                KEY_PRESERVE_PER_COLLECTION, DEFAULT_PRESERVE_PER_COLLECTION
            ),
        )

    def seed_defaults(self, team_id: int) -> None:
        """
        Seed default retention settings for a team.

        Creates all retention settings with default values if they don't exist.
        Called during team creation or for migrating existing teams.

        Args:
            team_id: Team ID to seed settings for
        """
        defaults = {
            KEY_JOB_COMPLETED_DAYS: DEFAULT_JOB_COMPLETED_DAYS,
            KEY_JOB_FAILED_DAYS: DEFAULT_JOB_FAILED_DAYS,
            KEY_RESULT_COMPLETED_DAYS: DEFAULT_RESULT_COMPLETED_DAYS,
            KEY_PRESERVE_PER_COLLECTION: DEFAULT_PRESERVE_PER_COLLECTION,
        }

        for key, value in defaults.items():
            # Check if setting already exists
            existing = (
                self.db.query(Configuration)
                .filter(
                    Configuration.team_id == team_id,
                    Configuration.category == RETENTION_CATEGORY,
                    Configuration.key == key
                )
                .first()
            )

            if not existing:
                config = Configuration(
                    team_id=team_id,
                    category=RETENTION_CATEGORY,
                    key=key,
                    value_json=value,
                    description=f"Default retention setting for {key}",
                    source=ConfigSource.DATABASE,
                )
                self.db.add(config)

        self.db.commit()
        logger.info(f"Seeded default retention settings for team {team_id}")

    def _validate_setting(self, key: str, value: int) -> None:
        """
        Validate a retention setting value.

        Args:
            key: Setting key
            value: Setting value

        Raises:
            ValidationError: If value is not in allowed options
        """
        if key == KEY_PRESERVE_PER_COLLECTION:
            if value not in VALID_PRESERVE_COUNTS:
                raise ValidationError(
                    f"Invalid value for {key}: must be one of {VALID_PRESERVE_COUNTS}",
                    field=key
                )
        else:
            # All other keys use retention days
            if value not in VALID_RETENTION_DAYS:
                raise ValidationError(
                    f"Invalid value for {key}: must be one of {VALID_RETENTION_DAYS}",
                    field=key
                )

    def _upsert_setting(self, team_id: int, key: str, value: int) -> None:
        """
        Insert or update a retention setting.

        Args:
            team_id: Team ID
            key: Setting key
            value: Setting value
        """
        existing = (
            self.db.query(Configuration)
            .filter(
                Configuration.team_id == team_id,
                Configuration.category == RETENTION_CATEGORY,
                Configuration.key == key
            )
            .first()
        )

        if existing:
            existing.value_json = value
            existing.source = ConfigSource.DATABASE
        else:
            config = Configuration(
                team_id=team_id,
                category=RETENTION_CATEGORY,
                key=key,
                value_json=value,
                source=ConfigSource.DATABASE,
            )
            self.db.add(config)
