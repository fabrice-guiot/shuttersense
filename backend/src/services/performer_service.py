"""
Performer service for managing event performers.

Provides business logic for creating, reading, updating, and deleting
event performers with category matching validation.

Design:
- Performers require a category (for event matching)
- Category matching enforced: performer's category must match event's category
- Instagram handles stored without @ symbol
- Many-to-many relationship with events via EventPerformer junction

Issue #39 - Calendar Events feature (Phase 11)
"""

from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from backend.src.models import Performer, Category, EventPerformer
from backend.src.utils.logging_config import get_logger
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError
from backend.src.services.guid import GuidService


logger = get_logger("services")


class PerformerService:
    """
    Service for managing event performers.

    Handles CRUD operations for performers with category matching validation.

    Usage:
        >>> service = PerformerService(db_session)
        >>> performer = service.create(
        ...     name="Blue Angels",
        ...     category_guid="cat_01hgw2bbg0000000000000001",
        ...     instagram_handle="usaborngirl"
        ... )
    """

    def __init__(self, db: Session):
        """
        Initialize performer service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(
        self,
        name: str,
        category_guid: str,
        website: Optional[str] = None,
        instagram_handle: Optional[str] = None,
        additional_info: Optional[str] = None,
    ) -> Performer:
        """
        Create a new performer.

        Args:
            name: Performer display name
            category_guid: Category GUID (must be active)
            website: Performer website URL
            instagram_handle: Instagram username (without @)
            additional_info: Additional notes/bio

        Returns:
            Created Performer instance

        Raises:
            NotFoundError: If category not found
            ValidationError: If category inactive
        """
        # Resolve category from GUID
        category = self._resolve_category(category_guid)

        # Validate category is active
        if not category.is_active:
            raise ValidationError(
                f"Category '{category.name}' is inactive. Please select an active category.",
                field="category_guid",
            )

        try:
            performer = Performer(
                name=name,
                category_id=category.id,
                website=website,
                instagram_handle=instagram_handle,
                additional_info=additional_info,
            )
            self.db.add(performer)
            self.db.commit()
            self.db.refresh(performer)

            logger.info(f"Created performer: {performer.name} ({performer.guid})")
            return performer

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to create performer '{name}': {e}")
            raise ValidationError("Failed to create performer: database constraint violation")

    def get_by_guid(self, guid: str) -> Performer:
        """
        Get a performer by GUID.

        Args:
            guid: Performer GUID (prf_xxx format)

        Returns:
            Performer instance

        Raises:
            NotFoundError: If performer not found
        """
        # Validate GUID format
        if not GuidService.validate_guid(guid, "prf"):
            raise NotFoundError("Performer", guid)

        # Extract UUID from GUID
        try:
            uuid_value = GuidService.parse_guid(guid, "prf")
        except ValueError:
            raise NotFoundError("Performer", guid)

        performer = (
            self.db.query(Performer).filter(Performer.uuid == uuid_value).first()
        )
        if not performer:
            raise NotFoundError("Performer", guid)

        return performer

    def get_by_id(self, performer_id: int) -> Performer:
        """
        Get a performer by internal ID.

        Args:
            performer_id: Internal database ID

        Returns:
            Performer instance

        Raises:
            NotFoundError: If performer not found
        """
        performer = self.db.query(Performer).filter(Performer.id == performer_id).first()
        if not performer:
            raise NotFoundError("Performer", performer_id)
        return performer

    def list(
        self,
        category_guid: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[Performer], int]:
        """
        List performers with optional filtering.

        Args:
            category_guid: Filter by category GUID
            search: Search term for name/instagram/additional_info
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (list of Performer instances, total count)
        """
        query = self.db.query(Performer)

        # Filter by category
        if category_guid:
            category = self._resolve_category(category_guid)
            query = query.filter(Performer.category_id == category.id)

        # Search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Performer.name.ilike(search_term)) |
                (Performer.instagram_handle.ilike(search_term)) |
                (Performer.additional_info.ilike(search_term))
            )

        # Get total count before pagination
        total = query.count()

        # Apply pagination and ordering
        performers = (
            query
            .order_by(Performer.name.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return performers, total

    def update(
        self,
        guid: str,
        name: Optional[str] = None,
        category_guid: Optional[str] = None,
        website: Optional[str] = None,
        instagram_handle: Optional[str] = None,
        additional_info: Optional[str] = None,
    ) -> Performer:
        """
        Update an existing performer.

        Args:
            guid: Performer GUID
            name: New name
            category_guid: New category GUID
            website: New website URL (empty string to clear)
            instagram_handle: New Instagram handle (empty string to clear)
            additional_info: New notes (empty string to clear)

        Returns:
            Updated Performer instance

        Raises:
            NotFoundError: If performer or category not found
            ValidationError: If category inactive
        """
        performer = self.get_by_guid(guid)

        # Validate and resolve new category if provided
        if category_guid is not None:
            category = self._resolve_category(category_guid)
            if not category.is_active:
                raise ValidationError(
                    f"Category '{category.name}' is inactive. Please select an active category.",
                    field="category_guid",
                )
            performer.category_id = category.id

        # Apply updates (None means no change, empty string clears for optional fields)
        if name is not None:
            performer.name = name
        if website is not None:
            performer.website = website if website else None
        if instagram_handle is not None:
            performer.instagram_handle = instagram_handle if instagram_handle else None
        if additional_info is not None:
            performer.additional_info = additional_info if additional_info else None

        try:
            self.db.commit()
            self.db.refresh(performer)
            logger.info(f"Updated performer: {performer.name} ({performer.guid})")
            return performer

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to update performer {guid}: {e}")
            raise ValidationError("Failed to update performer: database constraint violation")

    def delete(self, guid: str) -> None:
        """
        Delete a performer.

        Args:
            guid: Performer GUID

        Raises:
            NotFoundError: If performer not found
            ConflictError: If performer has event associations
        """
        performer = self.get_by_guid(guid)

        # Check for event associations
        event_count = (
            self.db.query(func.count(EventPerformer.id))
            .filter(EventPerformer.performer_id == performer.id)
            .scalar()
        )
        if event_count > 0:
            raise ConflictError(
                f"Cannot delete performer '{performer.name}': associated with {event_count} event(s)"
            )

        try:
            self.db.delete(performer)
            self.db.commit()
            logger.info(f"Deleted performer: {performer.name} ({guid})")

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to delete performer {guid}: {e}")
            raise ConflictError(
                f"Cannot delete performer '{performer.name}': it has associated entities"
            )

    def get_stats(self) -> dict:
        """
        Get performer statistics.

        Returns:
            Dictionary with performer statistics:
            {
                "total_count": int,
                "with_instagram_count": int,
                "with_website_count": int
            }
        """
        total = self.db.query(func.count(Performer.id)).scalar()
        with_instagram = (
            self.db.query(func.count(Performer.id))
            .filter(Performer.instagram_handle.isnot(None))
            .scalar()
        )
        with_website = (
            self.db.query(func.count(Performer.id))
            .filter(Performer.website.isnot(None))
            .scalar()
        )

        return {
            "total_count": total,
            "with_instagram_count": with_instagram,
            "with_website_count": with_website,
        }

    def validate_category_match(
        self,
        performer_guid: str,
        event_category_guid: str,
    ) -> bool:
        """
        Validate that a performer's category matches an event's category.

        Used when assigning a performer to an event to ensure compatibility.

        Args:
            performer_guid: Performer GUID to validate
            event_category_guid: Event's category GUID

        Returns:
            True if categories match, False otherwise

        Raises:
            NotFoundError: If performer not found
        """
        performer = self.get_by_guid(performer_guid)
        return performer.category.guid == event_category_guid

    def get_by_category(
        self,
        category_guid: str,
        search: Optional[str] = None,
        limit: int = 100,
    ) -> List[Performer]:
        """
        Get performers for a specific category.

        Convenience method for populating performer pickers in the UI.

        Args:
            category_guid: Category GUID to filter by
            search: Optional search term
            limit: Maximum results

        Returns:
            List of performers matching the category

        Raises:
            NotFoundError: If category not found
        """
        category = self._resolve_category(category_guid)
        query = (
            self.db.query(Performer)
            .filter(Performer.category_id == category.id)
        )

        if search:
            search_term = f"%{search}%"
            query = query.filter(Performer.name.ilike(search_term))

        return query.order_by(Performer.name.asc()).limit(limit).all()

    def build_performer_response(self, performer: Performer) -> dict:
        """
        Build a response dictionary for a performer.

        Args:
            performer: Performer instance with category loaded

        Returns:
            Dictionary suitable for PerformerResponse schema
        """
        return {
            "guid": performer.guid,
            "name": performer.name,
            "website": performer.website,
            "instagram_handle": performer.instagram_handle,
            "instagram_url": performer.instagram_url,
            "category": {
                "guid": performer.category.guid,
                "name": performer.category.name,
                "icon": performer.category.icon,
                "color": performer.category.color,
            },
            "additional_info": performer.additional_info,
            "created_at": performer.created_at,
            "updated_at": performer.updated_at,
        }

    def _resolve_category(self, category_guid: str) -> Category:
        """
        Resolve a category from its GUID.

        Args:
            category_guid: Category GUID (cat_xxx format)

        Returns:
            Category instance

        Raises:
            NotFoundError: If category not found
        """
        # Validate GUID format
        if not GuidService.validate_guid(category_guid, "cat"):
            raise NotFoundError("Category", category_guid)

        # Extract UUID from GUID
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
