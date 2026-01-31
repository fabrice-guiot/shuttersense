"""
Location service for managing event venues.

Provides business logic for creating, reading, updating, and deleting
event locations with category matching validation and geocoding support.

Design:
- Locations require a category (for event matching)
- Category matching enforced: location's category must match event's category
- Supports geocoding for address resolution and timezone detection
- Known locations are saved for reuse, vs one-time locations
- Default logistics settings (timeoff, travel) applied to new events
"""

from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

from backend.src.models import Location, Category
from backend.src.utils.logging_config import get_logger
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError
from backend.src.services.guid import GuidService
from backend.src.services.geocoding_service import GeocodingService


logger = get_logger("services")


class LocationService:
    """
    Service for managing event locations.

    Handles CRUD operations for locations with category matching validation,
    geocoding support, and default logistics settings.

    Usage:
        >>> service = LocationService(db_session)
        >>> location = service.create(
        ...     name="Madison Square Garden",
        ...     category_guid="cat_01hgw2bbg0000000000000001",
        ...     city="New York",
        ...     country="United States"
        ... )
    """

    def __init__(
        self,
        db: Session,
        geocoding_service: Optional[GeocodingService] = None,
    ):
        """
        Initialize location service.

        Args:
            db: SQLAlchemy database session
            geocoding_service: Optional geocoding service for address resolution
        """
        self.db = db
        self._geocoding_service = geocoding_service

    @property
    def geocoding_service(self) -> GeocodingService:
        """Lazy-initialized geocoding service."""
        if self._geocoding_service is None:
            self._geocoding_service = GeocodingService()
        return self._geocoding_service

    def create(
        self,
        name: str,
        category_guid: str,
        team_id: int,
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        postal_code: Optional[str] = None,
        instagram_handle: Optional[str] = None,
        latitude: Optional[Decimal] = None,
        longitude: Optional[Decimal] = None,
        timezone: Optional[str] = None,
        rating: Optional[int] = None,
        timeoff_required_default: bool = False,
        travel_required_default: bool = False,
        notes: Optional[str] = None,
        is_known: bool = True,
        user_id: Optional[int] = None,
    ) -> Location:
        """
        Create a new location.

        Args:
            name: Location display name
            category_guid: Category GUID (must be active)
            team_id: Team ID for tenant isolation
            address: Full street address
            city: City name
            state: State/province
            country: Country name
            postal_code: ZIP/postal code
            instagram_handle: Instagram username (without @)
            latitude: Geocoded latitude (-90 to 90)
            longitude: Geocoded longitude (-180 to 180)
            timezone: IANA timezone identifier
            rating: Location rating (1-5)
            timeoff_required_default: Default time-off setting for events
            travel_required_default: Default travel setting for events
            notes: Additional notes
            is_known: Whether this is a saved "known location"

        Returns:
            Created Location instance

        Raises:
            NotFoundError: If category not found
            ValidationError: If category inactive or coordinates incomplete
        """
        # Resolve category from GUID
        category = self._resolve_category(category_guid)

        # Validate category is active
        if not category.is_active:
            raise ValidationError(
                f"Category '{category.name}' is inactive. Please select an active category.",
                field="category_guid",
            )

        # Validate coordinates (must provide both or neither)
        if (latitude is None) != (longitude is None):
            raise ValidationError(
                "Both latitude and longitude must be provided together",
                field="latitude" if latitude is None else "longitude",
            )

        # Validate rating range
        if rating is not None and (rating < 1 or rating > 5):
            raise ValidationError(
                "Rating must be between 1 and 5",
                field="rating",
            )

        try:
            location = Location(
                name=name,
                category_id=category.id,
                team_id=team_id,
                address=address,
                city=city,
                state=state,
                country=country,
                postal_code=postal_code,
                instagram_handle=instagram_handle,
                latitude=latitude,
                longitude=longitude,
                timezone=timezone,
                rating=rating,
                timeoff_required_default=timeoff_required_default,
                travel_required_default=travel_required_default,
                notes=notes,
                is_known=is_known,
                created_by_user_id=user_id,
                updated_by_user_id=user_id,
            )
            self.db.add(location)
            self.db.commit()
            self.db.refresh(location)

            logger.info(f"Created location: {location.name} ({location.guid}, team_id={team_id})")
            return location

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to create location '{name}': {e}")
            raise ValidationError(f"Failed to create location: database constraint violation")

    def get_by_guid(self, guid: str, team_id: Optional[int] = None) -> Location:
        """
        Get a location by GUID.

        Args:
            guid: Location GUID (loc_xxx format)
            team_id: Team ID for tenant isolation (if provided, filters by team)

        Returns:
            Location instance

        Raises:
            NotFoundError: If location not found or belongs to different team
        """
        # Validate GUID format
        if not GuidService.validate_guid(guid, "loc"):
            raise NotFoundError("Location", guid)

        # Extract UUID from GUID
        try:
            uuid_value = GuidService.parse_guid(guid, "loc")
        except ValueError:
            raise NotFoundError("Location", guid)

        query = self.db.query(Location).filter(Location.uuid == uuid_value)
        if team_id is not None:
            query = query.filter(Location.team_id == team_id)

        location = query.first()
        if not location:
            raise NotFoundError("Location", guid)

        return location

    def get_by_id(self, location_id: int) -> Location:
        """
        Get a location by internal ID.

        Args:
            location_id: Internal database ID

        Returns:
            Location instance

        Raises:
            NotFoundError: If location not found
        """
        location = self.db.query(Location).filter(Location.id == location_id).first()
        if not location:
            raise NotFoundError("Location", location_id)
        return location

    def list(
        self,
        team_id: int,
        category_guid: Optional[str] = None,
        known_only: bool = False,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[Location], int]:
        """
        List locations with optional filtering.

        Args:
            team_id: Team ID for tenant isolation
            category_guid: Filter by category GUID
            known_only: If True, only return known locations
            search: Search term for name/city/address
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (list of Location instances, total count)
        """
        query = self.db.query(Location).filter(Location.team_id == team_id)

        # Filter by category
        if category_guid:
            category = self._resolve_category(category_guid)
            query = query.filter(Location.category_id == category.id)

        # Filter known locations only
        if known_only:
            query = query.filter(Location.is_known == True)

        # Search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Location.name.ilike(search_term)) |
                (Location.city.ilike(search_term)) |
                (Location.address.ilike(search_term)) |
                (Location.country.ilike(search_term)) |
                (Location.instagram_handle.ilike(search_term))
            )

        # Get total count before pagination
        total = query.count()

        # Apply pagination and ordering
        locations = (
            query
            .order_by(Location.name.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return locations, total

    def update(
        self,
        guid: str,
        team_id: int,
        name: Optional[str] = None,
        category_guid: Optional[str] = None,
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        postal_code: Optional[str] = None,
        instagram_handle: Optional[str] = None,
        latitude: Optional[Decimal] = None,
        longitude: Optional[Decimal] = None,
        timezone: Optional[str] = None,
        rating: Optional[int] = None,
        timeoff_required_default: Optional[bool] = None,
        travel_required_default: Optional[bool] = None,
        notes: Optional[str] = None,
        is_known: Optional[bool] = None,
        user_id: Optional[int] = None,
    ) -> Location:
        """
        Update an existing location.

        Args:
            guid: Location GUID
            team_id: Team ID for tenant isolation
            name: New name
            category_guid: New category GUID
            address: New address
            city: New city
            state: New state
            country: New country
            postal_code: New postal code
            instagram_handle: New Instagram handle (empty string to clear)
            latitude: New latitude
            longitude: New longitude
            timezone: New timezone
            rating: New rating (1-5)
            timeoff_required_default: New time-off default
            travel_required_default: New travel default
            notes: New notes
            is_known: Update known status

        Returns:
            Updated Location instance

        Raises:
            NotFoundError: If location or category not found or belongs to different team
            ValidationError: If category inactive or coordinates incomplete
        """
        location = self.get_by_guid(guid, team_id=team_id)

        # Validate and resolve new category if provided
        if category_guid is not None:
            category = self._resolve_category(category_guid)
            if not category.is_active:
                raise ValidationError(
                    f"Category '{category.name}' is inactive. Please select an active category.",
                    field="category_guid",
                )
            location.category_id = category.id

        # Validate rating range
        if rating is not None and (rating < 1 or rating > 5):
            raise ValidationError(
                "Rating must be between 1 and 5",
                field="rating",
            )

        # Apply updates (None means no change, explicit None for clearing handled specially)
        if name is not None:
            location.name = name
        if address is not None:
            location.address = address if address else None
        if city is not None:
            location.city = city if city else None
        if state is not None:
            location.state = state if state else None
        if country is not None:
            location.country = country if country else None
        if postal_code is not None:
            location.postal_code = postal_code if postal_code else None
        if instagram_handle is not None:
            location.instagram_handle = instagram_handle if instagram_handle else None
        if latitude is not None:
            location.latitude = latitude
        if longitude is not None:
            location.longitude = longitude
        if timezone is not None:
            location.timezone = timezone if timezone else None
        if rating is not None:
            location.rating = rating
        if timeoff_required_default is not None:
            location.timeoff_required_default = timeoff_required_default
        if travel_required_default is not None:
            location.travel_required_default = travel_required_default
        if notes is not None:
            location.notes = notes if notes else None
        if is_known is not None:
            location.is_known = is_known

        # Validate coordinates (must have both or neither after update)
        if (location.latitude is None) != (location.longitude is None):
            raise ValidationError(
                "Both latitude and longitude must be provided together",
                field="latitude" if location.latitude is None else "longitude",
            )

        if user_id is not None:
            location.updated_by_user_id = user_id

        try:
            self.db.commit()
            self.db.refresh(location)
            logger.info(f"Updated location: {location.name} ({location.guid})")
            return location

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to update location {guid}: {e}")
            raise ValidationError("Failed to update location: database constraint violation")

    def delete(self, guid: str, team_id: int) -> None:
        """
        Delete a location.

        Args:
            guid: Location GUID
            team_id: Team ID for tenant isolation

        Raises:
            NotFoundError: If location not found or belongs to different team
            ConflictError: If location has associated events
        """
        location = self.get_by_guid(guid, team_id=team_id)

        # Check for dependent events
        from backend.src.models import Event, EventSeries

        event_count = (
            self.db.query(func.count(Event.id))
            .filter(Event.location_id == location.id)
            .scalar()
        )
        if event_count > 0:
            raise ConflictError(
                f"Cannot delete location '{location.name}': {event_count} event(s) are using it"
            )

        # Check for event series
        series_count = (
            self.db.query(func.count(EventSeries.id))
            .filter(EventSeries.location_id == location.id)
            .scalar()
        )
        if series_count > 0:
            raise ConflictError(
                f"Cannot delete location '{location.name}': {series_count} event series are using it"
            )

        try:
            self.db.delete(location)
            self.db.commit()
            logger.info(f"Deleted location: {location.name} ({guid})")

        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Failed to delete location {guid}: {e}")
            raise ConflictError(
                f"Cannot delete location '{location.name}': it has associated entities"
            )

    def geocode_address(
        self,
        address: str,
    ) -> Optional[dict]:
        """
        Geocode an address to get coordinates and timezone.

        Args:
            address: Full address string to geocode

        Returns:
            Dictionary with geocoding results or None if failed:
            {
                "address": str,
                "city": str,
                "state": str,
                "country": str,
                "postal_code": str,
                "latitude": Decimal,
                "longitude": Decimal,
                "timezone": str
            }
        """
        result = self.geocoding_service.geocode_address(address)
        if result is None:
            return None

        return {
            "address": result.street_address,  # Just the street portion, not full address
            "city": result.city,
            "state": result.state,
            "country": result.country,
            "postal_code": result.postal_code,
            "latitude": float(result.latitude),
            "longitude": float(result.longitude),
            "timezone": result.timezone,
        }

    def get_stats(self, team_id: int) -> dict:
        """
        Get location statistics for a team.

        Args:
            team_id: Team ID for tenant isolation

        Returns:
            Dictionary with location statistics:
            {
                "total_count": int,
                "known_count": int,
                "with_coordinates_count": int,
                "with_instagram_count": int
            }
        """
        total = self.db.query(func.count(Location.id)).filter(
            Location.team_id == team_id
        ).scalar()
        known = (
            self.db.query(func.count(Location.id))
            .filter(
                Location.team_id == team_id,
                Location.is_known == True
            )
            .scalar()
        )
        with_coords = (
            self.db.query(func.count(Location.id))
            .filter(
                Location.team_id == team_id,
                Location.latitude.isnot(None),
                Location.longitude.isnot(None)
            )
            .scalar()
        )
        with_instagram = (
            self.db.query(func.count(Location.id))
            .filter(
                Location.team_id == team_id,
                Location.instagram_handle.isnot(None)
            )
            .scalar()
        )

        return {
            "total_count": total,
            "known_count": known,
            "with_coordinates_count": with_coords,
            "with_instagram_count": with_instagram,
        }

    def validate_category_match(
        self,
        location_guid: str,
        event_category_guid: str,
        team_id: int,
    ) -> bool:
        """
        Validate that a location's category matches an event's category.

        Used when assigning a location to an event to ensure compatibility.

        Args:
            location_guid: Location GUID to validate
            event_category_guid: Event's category GUID
            team_id: Team ID for tenant isolation

        Returns:
            True if categories match, False otherwise

        Raises:
            NotFoundError: If location not found or belongs to different team
        """
        location = self.get_by_guid(location_guid, team_id=team_id)
        return location.category.guid == event_category_guid

    def get_by_category(
        self,
        team_id: int,
        category_guid: str,
        known_only: bool = True,
    ) -> List[Location]:
        """
        Get all locations for a specific category.

        Useful for populating location dropdown when creating/editing events.

        Args:
            team_id: Team ID for tenant isolation
            category_guid: Category GUID to filter by
            known_only: If True, only return known (saved) locations

        Returns:
            List of Location instances matching the category
        """
        category = self._resolve_category(category_guid)
        query = self.db.query(Location).filter(
            Location.team_id == team_id,
            Location.category_id == category.id
        )

        if known_only:
            query = query.filter(Location.is_known == True)

        return query.order_by(Location.name.asc()).all()

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
