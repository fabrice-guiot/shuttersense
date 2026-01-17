"""
Category service for managing event categories.

Provides business logic for creating, reading, updating, deleting, and reordering
event categories with validation and cascade protection.

Design:
- Categories have unique names (case-insensitive)
- Display order is user-controlled with reorder support
- Cannot delete categories with associated events (RESTRICT)
- Supports soft enable/disable via is_active flag
"""

from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from backend.src.models import Category
from backend.src.utils.logging_config import get_logger
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError
from backend.src.services.guid import GuidService


logger = get_logger("services")


class CategoryService:
    """
    Service for managing event categories.

    Handles CRUD operations for categories with automatic validation,
    display order management, and cascade protection.

    Usage:
        >>> service = CategoryService(db_session)
        >>> category = service.create(
        ...     name="Airshow",
        ...     icon="plane",
        ...     color="#3B82F6"
        ... )
    """

    def __init__(self, db: Session):
        """
        Initialize category service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(
        self,
        name: str,
        team_id: int,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        is_active: bool = True,
        display_order: Optional[int] = None,
    ) -> Category:
        """
        Create a new category.

        Args:
            name: Category name (must be unique within team, case-insensitive)
            team_id: Team ID for tenant isolation
            icon: Lucide icon name (e.g., "plane")
            color: Hex color code (e.g., "#3B82F6")
            is_active: Whether category is active (default: True)
            display_order: Sort order in UI (auto-assigned if None)

        Returns:
            Created Category instance

        Raises:
            ConflictError: If name already exists within team
            ValidationError: If color format is invalid
        """
        # Validate color format
        if color and not self._is_valid_color(color):
            raise ValidationError(
                f"Invalid color format: {color}. Must be hex format like #RRGGBB",
                field="color",
            )

        # Check for existing category with same name within team (case-insensitive)
        existing = (
            self.db.query(Category)
            .filter(func.lower(Category.name) == func.lower(name))
            .filter(Category.team_id == team_id)
            .first()
        )
        if existing:
            raise ConflictError(f"Category with name '{name}' already exists")

        # Auto-assign display_order if not provided (within team)
        if display_order is None:
            max_order = (
                self.db.query(func.max(Category.display_order))
                .filter(Category.team_id == team_id)
                .scalar() or -1
            )
            display_order = max_order + 1

        try:
            category = Category(
                name=name,
                icon=icon,
                color=color,
                is_active=is_active,
                display_order=display_order,
                team_id=team_id,
            )
            self.db.add(category)
            self.db.commit()
            self.db.refresh(category)

            logger.info(f"Created category: {category.name} ({category.guid}) for team_id={team_id}")
            return category

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to create category '{name}': {e}")
            raise ConflictError(f"Category with name '{name}' already exists")

    def get_by_guid(self, guid: str, team_id: Optional[int] = None) -> Category:
        """
        Get a category by GUID.

        Args:
            guid: Category GUID (cat_xxx format)
            team_id: Team ID for tenant isolation (if provided, filters by team)

        Returns:
            Category instance

        Raises:
            NotFoundError: If category not found or belongs to different team
        """
        # Validate GUID format
        if not GuidService.validate_guid(guid, "cat"):
            raise NotFoundError("Category", guid)

        # Extract UUID from GUID
        try:
            uuid_value = GuidService.parse_guid(guid, "cat")
        except ValueError:
            raise NotFoundError("Category", guid)

        query = self.db.query(Category).filter(Category.uuid == uuid_value)
        if team_id is not None:
            query = query.filter(Category.team_id == team_id)

        category = query.first()
        if not category:
            raise NotFoundError("Category", guid)

        return category

    def get_by_id(self, category_id: int) -> Category:
        """
        Get a category by internal ID.

        Args:
            category_id: Internal database ID

        Returns:
            Category instance

        Raises:
            NotFoundError: If category not found
        """
        category = self.db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise NotFoundError("Category", category_id)
        return category

    def list(
        self,
        team_id: int,
        active_only: bool = False,
        order_by_display: bool = True,
    ) -> List[Category]:
        """
        List all categories for a team.

        Args:
            team_id: Team ID for tenant isolation
            active_only: If True, only return active categories
            order_by_display: If True, order by display_order (default)

        Returns:
            List of Category instances
        """
        query = self.db.query(Category).filter(Category.team_id == team_id)

        if active_only:
            query = query.filter(Category.is_active == True)

        if order_by_display:
            query = query.order_by(Category.display_order.asc())
        else:
            query = query.order_by(Category.name.asc())

        return query.all()

    def update(
        self,
        guid: str,
        team_id: int,
        name: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Category:
        """
        Update an existing category.

        Args:
            guid: Category GUID
            team_id: Team ID for tenant isolation
            name: New name (optional)
            icon: New icon (optional)
            color: New color (optional)
            is_active: New active status (optional)

        Returns:
            Updated Category instance

        Raises:
            NotFoundError: If category not found or belongs to different team
            ConflictError: If new name conflicts with existing within team
            ValidationError: If color format is invalid
        """
        category = self.get_by_guid(guid, team_id=team_id)

        # Validate color format
        if color is not None and color and not self._is_valid_color(color):
            raise ValidationError(
                f"Invalid color format: {color}. Must be hex format like #RRGGBB",
                field="color",
            )

        # Check for name conflict within team (case-insensitive)
        if name and name.lower() != category.name.lower():
            existing = (
                self.db.query(Category)
                .filter(func.lower(Category.name) == func.lower(name))
                .filter(Category.team_id == team_id)
                .filter(Category.id != category.id)
                .first()
            )
            if existing:
                raise ConflictError(f"Category with name '{name}' already exists")

        # Apply updates
        if name is not None:
            category.name = name
        if icon is not None:
            category.icon = icon
        if color is not None:
            category.color = color
        if is_active is not None:
            category.is_active = is_active

        try:
            self.db.commit()
            self.db.refresh(category)
            logger.info(f"Updated category: {category.name} ({category.guid})")
            return category

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to update category {guid}: {e}")
            raise ConflictError(f"Category with name '{name}' already exists")

    def delete(self, guid: str, team_id: int) -> None:
        """
        Delete a category.

        Args:
            guid: Category GUID
            team_id: Team ID for tenant isolation

        Raises:
            NotFoundError: If category not found or belongs to different team
            ConflictError: If category has associated events/entities
        """
        category = self.get_by_guid(guid, team_id=team_id)

        # Check for dependent entities
        # Import here to avoid circular imports
        from backend.src.models import Event, Location, Organizer, Performer, EventSeries

        # Check events
        event_count = (
            self.db.query(func.count(Event.id))
            .filter(Event.category_id == category.id)
            .scalar()
        )
        if event_count > 0:
            raise ConflictError(
                f"Cannot delete category '{category.name}': {event_count} event(s) are using it"
            )

        # Check locations
        location_count = (
            self.db.query(func.count(Location.id))
            .filter(Location.category_id == category.id)
            .scalar()
        )
        if location_count > 0:
            raise ConflictError(
                f"Cannot delete category '{category.name}': {location_count} location(s) are using it"
            )

        # Check organizers
        organizer_count = (
            self.db.query(func.count(Organizer.id))
            .filter(Organizer.category_id == category.id)
            .scalar()
        )
        if organizer_count > 0:
            raise ConflictError(
                f"Cannot delete category '{category.name}': {organizer_count} organizer(s) are using it"
            )

        # Check performers
        performer_count = (
            self.db.query(func.count(Performer.id))
            .filter(Performer.category_id == category.id)
            .scalar()
        )
        if performer_count > 0:
            raise ConflictError(
                f"Cannot delete category '{category.name}': {performer_count} performer(s) are using it"
            )

        # Check event series
        series_count = (
            self.db.query(func.count(EventSeries.id))
            .filter(EventSeries.category_id == category.id)
            .scalar()
        )
        if series_count > 0:
            raise ConflictError(
                f"Cannot delete category '{category.name}': {series_count} event series are using it"
            )

        try:
            self.db.delete(category)
            self.db.commit()
            logger.info(f"Deleted category: {category.name} ({guid})")

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to delete category {guid}: {e}")
            raise ConflictError(
                f"Cannot delete category '{category.name}': it has associated entities"
            )

    def reorder(self, ordered_guids: List[str], team_id: int) -> List[Category]:
        """
        Reorder categories based on provided GUID list.

        Updates display_order for all provided categories to match
        their position in the list.

        Args:
            ordered_guids: List of category GUIDs in desired order
            team_id: Team ID for tenant isolation

        Returns:
            List of reordered Category instances

        Raises:
            NotFoundError: If any GUID is not found or belongs to different team
        """
        categories = []

        for index, guid in enumerate(ordered_guids):
            category = self.get_by_guid(guid, team_id=team_id)
            category.display_order = index
            categories.append(category)

        self.db.commit()
        for category in categories:
            self.db.refresh(category)

        logger.info(f"Reordered {len(categories)} categories")
        return categories

    def get_stats(self, team_id: int) -> dict:
        """
        Get category statistics for a team.

        Args:
            team_id: Team ID for tenant isolation

        Returns:
            Dictionary with category statistics
        """
        total = (
            self.db.query(func.count(Category.id))
            .filter(Category.team_id == team_id)
            .scalar()
        )
        active = (
            self.db.query(func.count(Category.id))
            .filter(Category.team_id == team_id)
            .filter(Category.is_active == True)
            .scalar()
        )

        return {
            "total_count": total,
            "active_count": active,
            "inactive_count": total - active,
        }

    def _is_valid_color(self, color: str) -> bool:
        """
        Validate hex color format.

        Args:
            color: Color string to validate

        Returns:
            True if valid hex color format
        """
        if not color:
            return True  # Empty/None is allowed

        if not color.startswith("#"):
            return False

        # Support both #RGB and #RRGGBB formats
        hex_part = color[1:]
        if len(hex_part) not in (3, 6):
            return False

        try:
            int(hex_part, 16)
            return True
        except ValueError:
            return False
