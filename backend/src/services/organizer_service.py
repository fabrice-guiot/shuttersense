"""
Organizer service for managing event organizers.

Provides business logic for creating, reading, updating, and deleting
event organizers with category matching validation.

Design:
- Organizers require a category (for event matching)
- Category matching enforced: organizer's category must match event's category
- Default ticket_required setting applied to new events
- Rating (1-5) helps prioritize favorite organizers

Issue #39 - Calendar Events feature (Phase 9)
"""

from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from backend.src.models import Organizer, Category
from backend.src.utils.logging_config import get_logger
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError
from backend.src.services.guid import GuidService


logger = get_logger("services")


class OrganizerService:
    """
    Service for managing event organizers.

    Handles CRUD operations for organizers with category matching validation
    and default ticket settings.

    Usage:
        >>> service = OrganizerService(db_session)
        >>> organizer = service.create(
        ...     name="Live Nation",
        ...     category_guid="cat_01hgw2bbg0000000000000001",
        ...     website="https://livenation.com",
        ...     rating=4
        ... )
    """

    def __init__(self, db: Session):
        """
        Initialize organizer service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(
        self,
        name: str,
        category_guid: str,
        team_id: int,
        website: Optional[str] = None,
        instagram_handle: Optional[str] = None,
        rating: Optional[int] = None,
        ticket_required_default: bool = False,
        notes: Optional[str] = None,
    ) -> Organizer:
        """
        Create a new organizer.

        Args:
            name: Organizer display name
            category_guid: Category GUID (must be active)
            team_id: Team ID for tenant isolation
            website: Organizer website URL
            instagram_handle: Instagram username (without @)
            rating: Organizer rating (1-5)
            ticket_required_default: Default ticket setting for events
            notes: Additional notes

        Returns:
            Created Organizer instance

        Raises:
            NotFoundError: If category not found
            ValidationError: If category inactive or rating invalid
        """
        # Resolve category from GUID
        category = self._resolve_category(category_guid)

        # Validate category is active
        if not category.is_active:
            raise ValidationError(
                f"Category '{category.name}' is inactive. Please select an active category.",
                field="category_guid",
            )

        # Validate rating range
        if rating is not None and (rating < 1 or rating > 5):
            raise ValidationError(
                "Rating must be between 1 and 5",
                field="rating",
            )

        try:
            organizer = Organizer(
                name=name,
                category_id=category.id,
                team_id=team_id,
                website=website,
                instagram_handle=instagram_handle,
                rating=rating,
                ticket_required_default=ticket_required_default,
                notes=notes,
            )
            self.db.add(organizer)
            self.db.commit()
            self.db.refresh(organizer)

            logger.info(f"Created organizer: {organizer.name} ({organizer.guid}) for team_id={team_id}")
            return organizer

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to create organizer '{name}': {e}")
            raise ValidationError("Failed to create organizer: database constraint violation")

    def get_by_guid(self, guid: str, team_id: Optional[int] = None) -> Organizer:
        """
        Get an organizer by GUID.

        Args:
            guid: Organizer GUID (org_xxx format)
            team_id: Team ID for tenant isolation (if provided, filters by team)

        Returns:
            Organizer instance

        Raises:
            NotFoundError: If organizer not found or belongs to different team
        """
        # Validate GUID format
        if not GuidService.validate_guid(guid, "org"):
            raise NotFoundError("Organizer", guid)

        # Extract UUID from GUID
        try:
            uuid_value = GuidService.parse_guid(guid, "org")
        except ValueError:
            raise NotFoundError("Organizer", guid)

        query = self.db.query(Organizer).filter(Organizer.uuid == uuid_value)
        if team_id is not None:
            query = query.filter(Organizer.team_id == team_id)

        organizer = query.first()
        if not organizer:
            raise NotFoundError("Organizer", guid)

        return organizer

    def get_by_id(self, organizer_id: int) -> Organizer:
        """
        Get an organizer by internal ID.

        Args:
            organizer_id: Internal database ID

        Returns:
            Organizer instance

        Raises:
            NotFoundError: If organizer not found
        """
        organizer = self.db.query(Organizer).filter(Organizer.id == organizer_id).first()
        if not organizer:
            raise NotFoundError("Organizer", organizer_id)
        return organizer

    def list(
        self,
        team_id: int,
        category_guid: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[Organizer], int]:
        """
        List organizers with optional filtering.

        Args:
            team_id: Team ID for tenant isolation
            category_guid: Filter by category GUID
            search: Search term for name/website/notes
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (list of Organizer instances, total count)
        """
        query = self.db.query(Organizer).filter(Organizer.team_id == team_id)

        # Filter by category
        if category_guid:
            category = self._resolve_category(category_guid)
            query = query.filter(Organizer.category_id == category.id)

        # Search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Organizer.name.ilike(search_term)) |
                (Organizer.website.ilike(search_term)) |
                (Organizer.instagram_handle.ilike(search_term)) |
                (Organizer.notes.ilike(search_term))
            )

        # Get total count before pagination
        total = query.count()

        # Apply pagination and ordering
        organizers = (
            query
            .order_by(Organizer.name.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return organizers, total

    def update(
        self,
        guid: str,
        team_id: Optional[int] = None,
        name: Optional[str] = None,
        category_guid: Optional[str] = None,
        website: Optional[str] = None,
        instagram_handle: Optional[str] = None,
        rating: Optional[int] = None,
        ticket_required_default: Optional[bool] = None,
        notes: Optional[str] = None,
    ) -> Organizer:
        """
        Update an existing organizer.

        Args:
            guid: Organizer GUID
            team_id: Team ID for tenant isolation (if provided, validates ownership)
            name: New name
            category_guid: New category GUID
            website: New website URL
            instagram_handle: New Instagram handle (empty string to clear)
            rating: New rating (1-5)
            ticket_required_default: New ticket default
            notes: New notes

        Returns:
            Updated Organizer instance

        Raises:
            NotFoundError: If organizer or category not found or belongs to different team
            ValidationError: If category inactive or rating invalid
        """
        organizer = self.get_by_guid(guid, team_id=team_id)

        # Validate and resolve new category if provided
        if category_guid is not None:
            category = self._resolve_category(category_guid)
            if not category.is_active:
                raise ValidationError(
                    f"Category '{category.name}' is inactive. Please select an active category.",
                    field="category_guid",
                )
            organizer.category_id = category.id

        # Validate rating range
        if rating is not None and (rating < 1 or rating > 5):
            raise ValidationError(
                "Rating must be between 1 and 5",
                field="rating",
            )

        # Apply updates (None means no change, empty string clears for optional fields)
        if name is not None:
            organizer.name = name
        if website is not None:
            organizer.website = website if website else None
        if instagram_handle is not None:
            organizer.instagram_handle = instagram_handle if instagram_handle else None
        if rating is not None:
            organizer.rating = rating
        if ticket_required_default is not None:
            organizer.ticket_required_default = ticket_required_default
        if notes is not None:
            organizer.notes = notes if notes else None

        try:
            self.db.commit()
            self.db.refresh(organizer)
            logger.info(f"Updated organizer: {organizer.name} ({organizer.guid})")
            return organizer

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to update organizer {guid}: {e}")
            raise ValidationError("Failed to update organizer: database constraint violation")

    def delete(self, guid: str, team_id: Optional[int] = None) -> None:
        """
        Delete an organizer.

        Args:
            guid: Organizer GUID
            team_id: Team ID for tenant isolation (if provided, validates ownership)

        Raises:
            NotFoundError: If organizer not found or belongs to different team
            ConflictError: If organizer has associated events
        """
        organizer = self.get_by_guid(guid, team_id=team_id)

        # Check for dependent events
        from backend.src.models import Event, EventSeries

        event_count = (
            self.db.query(func.count(Event.id))
            .filter(Event.organizer_id == organizer.id)
            .scalar()
        )
        if event_count > 0:
            raise ConflictError(
                f"Cannot delete organizer '{organizer.name}': {event_count} event(s) are using it"
            )

        # Check for event series
        series_count = (
            self.db.query(func.count(EventSeries.id))
            .filter(EventSeries.organizer_id == organizer.id)
            .scalar()
        )
        if series_count > 0:
            raise ConflictError(
                f"Cannot delete organizer '{organizer.name}': {series_count} event series are using it"
            )

        try:
            self.db.delete(organizer)
            self.db.commit()
            logger.info(f"Deleted organizer: {organizer.name} ({guid})")

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to delete organizer {guid}: {e}")
            raise ConflictError(
                f"Cannot delete organizer '{organizer.name}': it has associated entities"
            )

    def get_stats(self, team_id: int) -> dict:
        """
        Get organizer statistics.

        Args:
            team_id: Team ID for tenant isolation

        Returns:
            Dictionary with organizer statistics:
            {
                "total_count": int,
                "with_rating_count": int,
                "with_instagram_count": int,
                "avg_rating": Optional[float]
            }
        """
        total = (
            self.db.query(func.count(Organizer.id))
            .filter(Organizer.team_id == team_id)
            .scalar()
        )
        with_rating = (
            self.db.query(func.count(Organizer.id))
            .filter(Organizer.team_id == team_id)
            .filter(Organizer.rating.isnot(None))
            .scalar()
        )
        with_instagram = (
            self.db.query(func.count(Organizer.id))
            .filter(Organizer.team_id == team_id)
            .filter(Organizer.instagram_handle.isnot(None))
            .scalar()
        )
        avg_rating = (
            self.db.query(func.avg(Organizer.rating))
            .filter(Organizer.team_id == team_id)
            .filter(Organizer.rating.isnot(None))
            .scalar()
        )

        return {
            "total_count": total,
            "with_rating_count": with_rating,
            "with_instagram_count": with_instagram,
            "avg_rating": round(float(avg_rating), 1) if avg_rating else None,
        }

    def validate_category_match(
        self,
        organizer_guid: str,
        event_category_guid: str,
        team_id: Optional[int] = None,
    ) -> bool:
        """
        Validate that an organizer's category matches an event's category.

        Used when assigning an organizer to an event to ensure compatibility.

        Args:
            organizer_guid: Organizer GUID to validate
            event_category_guid: Event's category GUID
            team_id: Team ID for tenant isolation (if provided, validates ownership)

        Returns:
            True if categories match, False otherwise

        Raises:
            NotFoundError: If organizer not found or belongs to different team
        """
        organizer = self.get_by_guid(organizer_guid, team_id=team_id)
        return organizer.category.guid == event_category_guid

    def get_by_category(
        self,
        category_guid: str,
        team_id: int,
    ) -> List[Organizer]:
        """
        Get all organizers for a specific category.

        Useful for populating organizer dropdown when creating/editing events.

        Args:
            category_guid: Category GUID to filter by
            team_id: Team ID for tenant isolation

        Returns:
            List of Organizer instances matching the category
        """
        category = self._resolve_category(category_guid)
        return (
            self.db.query(Organizer)
            .filter(Organizer.category_id == category.id)
            .filter(Organizer.team_id == team_id)
            .order_by(Organizer.name.asc())
            .all()
        )

    def _resolve_category(self, category_guid: str) -> Category:
        """
        Resolve a category GUID to a Category instance.

        Args:
            category_guid: Category GUID to resolve

        Returns:
            Category instance

        Raises:
            NotFoundError: If category not found
        """
        if not GuidService.validate_guid(category_guid, "cat"):
            raise NotFoundError("Category", category_guid)

        try:
            uuid_value = GuidService.parse_guid(category_guid, "cat")
        except ValueError:
            raise NotFoundError("Category", category_guid)

        category = (
            self.db.query(Category).filter(Category.uuid == uuid_value).first()
        )
        if not category:
            raise NotFoundError("Category", category_guid)

        return category
