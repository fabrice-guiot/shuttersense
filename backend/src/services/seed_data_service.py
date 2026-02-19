"""
Seed data service for initializing default team data.

Provides functions to seed default categories and configurations when a new
team is created. This ensures each team starts with a consistent baseline
of categories and event statuses.

Design:
- Called when seeding first team via CLI script
- Will be called by team creation API (Phase 9)
- Idempotent - safe to call multiple times for same team
- Uses same defaults as migration seeds (018, 019)
- Handles migration of orphaned data (team_id=NULL) from pre-tenancy migrations
"""

from typing import Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.src.models import Category, Configuration, ConfigSource
from backend.src.utils.logging_config import get_logger


logger = get_logger("services")


# Default categories matching migration 018_seed_default_categories
DEFAULT_CATEGORIES = [
    {'name': 'Airshow', 'icon': 'plane', 'color': '#3B82F6', 'display_order': 0},
    {'name': 'Wildlife', 'icon': 'bird', 'color': '#22C55E', 'display_order': 1},
    {'name': 'Wedding', 'icon': 'heart', 'color': '#EC4899', 'display_order': 2},
    {'name': 'Sports', 'icon': 'trophy', 'color': '#F97316', 'display_order': 3},
    {'name': 'Portrait', 'icon': 'user', 'color': '#8B5CF6', 'display_order': 4},
    {'name': 'Concert', 'icon': 'music', 'color': '#EF4444', 'display_order': 5},
    {'name': 'Motorsports', 'icon': 'car', 'color': '#6B7280', 'display_order': 6},
]

# Default event statuses matching migration 019_seed_default_event_statuses
DEFAULT_EVENT_STATUSES = [
    {'key': 'future', 'label': 'Future', 'display_order': 0, 'forces_skip': False},
    {'key': 'confirmed', 'label': 'Confirmed', 'display_order': 1, 'forces_skip': False},
    {'key': 'completed', 'label': 'Completed', 'display_order': 2, 'forces_skip': False},
    {'key': 'cancelled', 'label': 'Cancelled', 'display_order': 3, 'forces_skip': True},
]

# Default collection TTL values by state (in seconds)
DEFAULT_COLLECTION_TTL = {
    'live': {'value': 3600, 'label': 'Live (1 hour)'},
    'closed': {'value': 86400, 'label': 'Closed (24 hours)'},
    'archived': {'value': 604800, 'label': 'Archived (7 days)'},
}

# Default conflict detection rules
DEFAULT_CONFLICT_RULES = {
    'distance_threshold_miles': {'value': 150, 'label': 'Distance Threshold (miles)'},
    'consecutive_window_days': {'value': 1, 'label': 'Consecutive Window (days)'},
    'travel_buffer_days': {'value': 3, 'label': 'Travel Buffer (days)'},
    'colocation_radius_miles': {'value': 70, 'label': 'Co-location Radius (miles)'},
    'performer_ceiling': {'value': 5, 'label': 'Performer Ceiling'},
}

# Default scoring dimension weights
DEFAULT_SCORING_WEIGHTS = {
    'weight_venue_quality': {'value': 20, 'label': 'Venue Quality'},
    'weight_organizer_reputation': {'value': 20, 'label': 'Organizer Reputation'},
    'weight_performer_lineup': {'value': 20, 'label': 'Performer Lineup'},
    'weight_logistics_ease': {'value': 20, 'label': 'Logistics Ease'},
    'weight_readiness': {'value': 20, 'label': 'Readiness'},
}


class SeedDataService:
    """
    Service for seeding default data for new teams.

    Ensures each team has baseline categories and configurations
    for immediate use after creation.

    Usage:
        >>> service = SeedDataService(db_session)
        >>> categories, configs = service.seed_team_defaults(team_id=1)
        >>> print(f"Seeded {len(categories)} categories, {len(configs)} configs")
    """

    def __init__(self, db: Session):
        """
        Initialize seed data service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def seed_team_defaults(
        self, team_id: int, user_id: Optional[int] = None
    ) -> Tuple[int, int, int, int, int]:
        """
        Seed all default data for a team.

        Creates default categories and configurations if they don't exist.
        Idempotent - safe to call multiple times.

        Args:
            team_id: Team ID to seed data for
            user_id: Optional user ID for audit trail (created_by/updated_by)

        Returns:
            Tuple of (categories_created, event_statuses_created, ttl_configs_created,
                       conflict_rules_created, scoring_weights_created)
        """
        categories_created = self.seed_categories(team_id, user_id=user_id)
        event_statuses_created = self.seed_event_statuses(team_id, user_id=user_id)
        ttl_configs_created = self.seed_collection_ttl(team_id, user_id=user_id)
        conflict_rules_created = self.seed_conflict_rules(team_id, user_id=user_id)
        scoring_weights_created = self.seed_scoring_weights(team_id, user_id=user_id)

        total_configs = (
            event_statuses_created + ttl_configs_created
            + conflict_rules_created + scoring_weights_created
        )
        if categories_created > 0 or total_configs > 0:
            self.db.commit()
            logger.info(
                f"Seeded team {team_id}: {categories_created} categories, "
                f"{event_statuses_created} event statuses, {ttl_configs_created} TTL configs, "
                f"{conflict_rules_created} conflict rules, {scoring_weights_created} scoring weights"
            )

        return (
            categories_created, event_statuses_created, ttl_configs_created,
            conflict_rules_created, scoring_weights_created,
        )

    def seed_categories(self, team_id: int, user_id: Optional[int] = None) -> int:
        """
        Seed default categories for a team.

        Creates categories only if they don't already exist for this team.
        Uses category name for uniqueness check within the team.

        Args:
            team_id: Team ID to seed categories for
            user_id: Optional user ID for audit trail (created_by/updated_by)

        Returns:
            Number of categories created
        """
        created_count = 0

        for cat_data in DEFAULT_CATEGORIES:
            # Check if category already exists for this team
            existing = self.db.query(Category).filter(
                Category.team_id == team_id,
                func.lower(Category.name) == func.lower(cat_data['name'])
            ).first()

            if existing:
                logger.debug(f"Category '{cat_data['name']}' already exists for team {team_id}")
                continue

            category = Category(
                team_id=team_id,
                name=cat_data['name'],
                icon=cat_data['icon'],
                color=cat_data['color'],
                is_active=True,
                display_order=cat_data['display_order'],
                created_by_user_id=user_id,
                updated_by_user_id=user_id,
            )
            self.db.add(category)
            created_count += 1
            logger.debug(f"Created category '{cat_data['name']}' for team {team_id}")

        return created_count

    def seed_event_statuses(self, team_id: int, user_id: Optional[int] = None) -> int:
        """
        Seed default event statuses for a team.

        Creates event status configurations only if they don't already exist
        for this team.

        Args:
            team_id: Team ID to seed event statuses for
            user_id: Optional user ID for audit trail (created_by/updated_by)

        Returns:
            Number of event statuses created
        """
        created_count = 0

        for status_data in DEFAULT_EVENT_STATUSES:
            # Check if status already exists for this team
            existing = self.db.query(Configuration).filter(
                Configuration.team_id == team_id,
                Configuration.category == 'event_statuses',
                Configuration.key == status_data['key']
            ).first()

            if existing:
                logger.debug(
                    f"Event status '{status_data['key']}' already exists for team {team_id}"
                )
                continue

            config = Configuration(
                team_id=team_id,
                category='event_statuses',
                key=status_data['key'],
                value_json={
                    'label': status_data['label'],
                    'display_order': status_data['display_order'],
                    'forces_skip': status_data.get('forces_skip', False),
                },
                description=f"Event status: {status_data['label']}",
                source=ConfigSource.DATABASE,
                created_by_user_id=user_id,
                updated_by_user_id=user_id,
            )
            self.db.add(config)
            created_count += 1
            logger.debug(f"Created event status '{status_data['key']}' for team {team_id}")

        return created_count

    def seed_collection_ttl(self, team_id: int, user_id: Optional[int] = None) -> int:
        """
        Seed default collection TTL configurations for a team.

        Creates collection TTL configurations for each collection state
        (live, closed, archived) if they don't already exist for this team.

        Args:
            team_id: Team ID to seed collection TTL for
            user_id: Optional user ID for audit trail (created_by/updated_by)

        Returns:
            Number of TTL configurations created
        """
        created_count = 0

        for state_key, ttl_data in DEFAULT_COLLECTION_TTL.items():
            # Check if TTL config already exists for this team
            existing = self.db.query(Configuration).filter(
                Configuration.team_id == team_id,
                Configuration.category == 'collection_ttl',
                Configuration.key == state_key
            ).first()

            if existing:
                logger.debug(
                    f"Collection TTL '{state_key}' already exists for team {team_id}"
                )
                continue

            config = Configuration(
                team_id=team_id,
                category='collection_ttl',
                key=state_key,
                value_json=ttl_data,
                description=f"Collection cache TTL for {state_key} state",
                source=ConfigSource.DATABASE,
                created_by_user_id=user_id,
                updated_by_user_id=user_id,
            )
            self.db.add(config)
            created_count += 1
            logger.debug(f"Created collection TTL '{state_key}' for team {team_id}")

        return created_count

    def seed_conflict_rules(self, team_id: int, user_id: Optional[int] = None) -> int:
        """
        Seed default conflict detection rules for a team.

        Creates conflict rule configurations if they don't already exist.
        Does NOT commit — caller must commit.

        Args:
            team_id: Team ID to seed conflict rules for
            user_id: Optional user ID for audit trail

        Returns:
            Number of conflict rules created
        """
        created_count = 0

        for key, data in DEFAULT_CONFLICT_RULES.items():
            existing = self.db.query(Configuration).filter(
                Configuration.team_id == team_id,
                Configuration.category == 'conflict_rules',
                Configuration.key == key,
            ).first()

            if existing:
                continue

            config = Configuration(
                team_id=team_id,
                category='conflict_rules',
                key=key,
                value_json=data,
                description=f"Conflict rule: {data['label']}",
                source=ConfigSource.DATABASE,
                created_by_user_id=user_id,
                updated_by_user_id=user_id,
            )
            self.db.add(config)
            created_count += 1

        return created_count

    def seed_scoring_weights(self, team_id: int, user_id: Optional[int] = None) -> int:
        """
        Seed default scoring dimension weights for a team.

        Creates scoring weight configurations if they don't already exist.
        Does NOT commit — caller must commit.

        Args:
            team_id: Team ID to seed scoring weights for
            user_id: Optional user ID for audit trail

        Returns:
            Number of scoring weights created
        """
        created_count = 0

        for key, data in DEFAULT_SCORING_WEIGHTS.items():
            existing = self.db.query(Configuration).filter(
                Configuration.team_id == team_id,
                Configuration.category == 'scoring_weights',
                Configuration.key == key,
            ).first()

            if existing:
                continue

            config = Configuration(
                team_id=team_id,
                category='scoring_weights',
                key=key,
                value_json=data,
                description=f"Scoring weight: {data['label']}",
                source=ConfigSource.DATABASE,
                created_by_user_id=user_id,
                updated_by_user_id=user_id,
            )
            self.db.add(config)
            created_count += 1

        return created_count

    def get_seed_summary(self, team_id: int) -> Dict[str, Any]:
        """
        Get summary of seeded data for a team.

        Args:
            team_id: Team ID to check

        Returns:
            Dictionary with counts of existing seed data
        """
        categories_count = self.db.query(func.count(Category.id)).filter(
            Category.team_id == team_id
        ).scalar() or 0

        event_statuses_count = self.db.query(func.count(Configuration.id)).filter(
            Configuration.team_id == team_id,
            Configuration.category == 'event_statuses'
        ).scalar() or 0

        collection_ttl_count = self.db.query(func.count(Configuration.id)).filter(
            Configuration.team_id == team_id,
            Configuration.category == 'collection_ttl'
        ).scalar() or 0

        return {
            'team_id': team_id,
            'categories': categories_count,
            'event_statuses': event_statuses_count,
            'collection_ttl': collection_ttl_count,
            'expected_categories': len(DEFAULT_CATEGORIES),
            'expected_event_statuses': len(DEFAULT_EVENT_STATUSES),
            'expected_collection_ttl': len(DEFAULT_COLLECTION_TTL),
        }

    def migrate_orphaned_data(self, team_id: int) -> Tuple[int, int]:
        """
        Migrate orphaned data (team_id=NULL) to the specified team.

        This handles data created by migrations 018 and 019 before the
        team_id column was added. Only used during initial team setup.

        Args:
            team_id: Team ID to assign orphaned data to

        Returns:
            Tuple of (categories_migrated, configs_migrated)
        """
        categories_migrated = self._migrate_orphaned_categories(team_id)
        configs_migrated = self._migrate_orphaned_configurations(team_id)

        if categories_migrated > 0 or configs_migrated > 0:
            self.db.commit()
            logger.info(
                f"Migrated orphaned data to team {team_id}: "
                f"{categories_migrated} categories, {configs_migrated} configurations"
            )

        return categories_migrated, configs_migrated

    def _migrate_orphaned_categories(self, team_id: int) -> int:
        """
        Migrate categories with team_id=NULL to the specified team.

        Args:
            team_id: Team ID to assign categories to

        Returns:
            Number of categories migrated
        """
        orphaned = self.db.query(Category).filter(
            Category.team_id.is_(None)
        ).all()

        migrated_count = 0
        for category in orphaned:
            # Check if a category with same name already exists for this team
            existing = self.db.query(Category).filter(
                Category.team_id == team_id,
                func.lower(Category.name) == func.lower(category.name)
            ).first()

            if existing:
                # Category already exists for team - delete the orphan
                logger.debug(
                    f"Category '{category.name}' already exists for team {team_id}, "
                    f"deleting orphan"
                )
                self.db.delete(category)
            else:
                # Assign orphan to team
                category.team_id = team_id
                migrated_count += 1
                logger.debug(f"Migrated category '{category.name}' to team {team_id}")

        return migrated_count

    def _migrate_orphaned_configurations(self, team_id: int) -> int:
        """
        Migrate configurations with team_id=NULL to the specified team.

        Args:
            team_id: Team ID to assign configurations to

        Returns:
            Number of configurations migrated
        """
        orphaned = self.db.query(Configuration).filter(
            Configuration.team_id.is_(None)
        ).all()

        migrated_count = 0
        for config in orphaned:
            # Check if a config with same category+key already exists for this team
            existing = self.db.query(Configuration).filter(
                Configuration.team_id == team_id,
                Configuration.category == config.category,
                Configuration.key == config.key
            ).first()

            if existing:
                # Config already exists for team - delete the orphan
                logger.debug(
                    f"Config '{config.category}.{config.key}' already exists for team "
                    f"{team_id}, deleting orphan"
                )
                self.db.delete(config)
            else:
                # Assign orphan to team
                config.team_id = team_id
                migrated_count += 1
                logger.debug(
                    f"Migrated config '{config.category}.{config.key}' to team {team_id}"
                )

        return migrated_count

    def get_orphaned_data_summary(self) -> Dict[str, int]:
        """
        Get count of orphaned data (team_id=NULL).

        Returns:
            Dictionary with counts of orphaned categories and configurations
        """
        orphaned_categories = self.db.query(func.count(Category.id)).filter(
            Category.team_id.is_(None)
        ).scalar() or 0

        orphaned_configs = self.db.query(func.count(Configuration.id)).filter(
            Configuration.team_id.is_(None)
        ).scalar() or 0

        return {
            'orphaned_categories': orphaned_categories,
            'orphaned_configurations': orphaned_configs,
        }
