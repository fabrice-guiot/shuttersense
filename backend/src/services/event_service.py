"""
Event service for managing calendar events.

Provides business logic for listing, retrieving, creating, updating, and
deleting calendar events with support for event series.

Design:
- Events can be standalone or part of a series
- Series events inherit properties from EventSeries
- Soft delete preserves event history
- Date range queries support calendar views
"""

from typing import List, Optional, Dict, Any
from datetime import date, datetime

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_

from backend.src.models import Event, EventSeries, Category, Location, Organizer, EventPerformer, Performer
from backend.src.utils.logging_config import get_logger
from backend.src.services.exceptions import NotFoundError, ValidationError, ConflictError
from backend.src.services.guid import GuidService


logger = get_logger("services")


class EventService:
    """
    Service for managing calendar events.

    Handles CRUD operations for events with support for:
    - Date range queries for calendar views
    - Event series (multi-day events)
    - Filtering by category, status, attendance
    - Soft delete

    Usage:
        >>> service = EventService(db_session)
        >>> events = service.list(
        ...     start_date=date(2026, 1, 1),
        ...     end_date=date(2026, 1, 31)
        ... )
    """

    def __init__(self, db: Session):
        """
        Initialize event service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_by_guid(self, guid: str, include_deleted: bool = False) -> Event:
        """
        Get an event by GUID.

        Args:
            guid: Event GUID (evt_xxx format)
            include_deleted: If True, include soft-deleted events

        Returns:
            Event instance with relationships loaded

        Raises:
            NotFoundError: If event not found
        """
        # Validate GUID format
        if not GuidService.validate_guid(guid, "evt"):
            raise NotFoundError("Event", guid)

        # Extract UUID from GUID
        try:
            uuid_value = GuidService.parse_guid(guid, "evt")
        except ValueError:
            raise NotFoundError("Event", guid)

        query = (
            self.db.query(Event)
            .options(
                joinedload(Event.category),
                joinedload(Event.series),
                joinedload(Event.location),
                joinedload(Event.organizer),
            )
            .filter(Event.uuid == uuid_value)
        )

        if not include_deleted:
            query = query.filter(Event.deleted_at.is_(None))

        event = query.first()
        if not event:
            raise NotFoundError("Event", guid)

        return event

    def get_by_id(self, event_id: int, include_deleted: bool = False) -> Event:
        """
        Get an event by internal ID.

        Args:
            event_id: Internal database ID
            include_deleted: If True, include soft-deleted events

        Returns:
            Event instance

        Raises:
            NotFoundError: If event not found
        """
        query = self.db.query(Event).filter(Event.id == event_id)

        if not include_deleted:
            query = query.filter(Event.deleted_at.is_(None))

        event = query.first()
        if not event:
            raise NotFoundError("Event", event_id)

        return event

    def list(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        category_guid: Optional[str] = None,
        status: Optional[str] = None,
        attendance: Optional[str] = None,
        include_deleted: bool = False,
        include_deadlines: bool = True,
    ) -> List[Event]:
        """
        List events with optional filtering.

        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            category_guid: Filter by category GUID
            status: Filter by event status
            attendance: Filter by attendance status
            include_deleted: If True, include soft-deleted events
            include_deadlines: If False, exclude deadline entries (is_deadline=True)

        Returns:
            List of Event instances ordered by date
        """
        query = self.db.query(Event).options(
            joinedload(Event.category),
            joinedload(Event.series),
            joinedload(Event.location),
        )

        # Exclude soft-deleted unless requested
        if not include_deleted:
            query = query.filter(Event.deleted_at.is_(None))

        # Exclude deadline entries if requested (T043)
        if not include_deadlines:
            query = query.filter(Event.is_deadline == False)

        # Date range filter
        if start_date:
            query = query.filter(Event.event_date >= start_date)
        if end_date:
            query = query.filter(Event.event_date <= end_date)

        # Category filter
        if category_guid:
            if not GuidService.validate_guid(category_guid, "cat"):
                raise ValidationError(f"Invalid category GUID: {category_guid}", field="category_guid")
            try:
                cat_uuid = GuidService.parse_guid(category_guid, "cat")
                category = (
                    self.db.query(Category)
                    .filter(Category.uuid == cat_uuid)
                    .first()
                )
                if category:
                    # Include events directly in category OR in series with that category
                    query = query.outerjoin(Event.series).filter(
                        or_(
                            Event.category_id == category.id,
                            and_(
                                Event.category_id.is_(None),
                                EventSeries.category_id == category.id,
                            ),
                        )
                    )
            except ValueError:
                pass  # Invalid GUID, will return no results

        # Status filter
        if status:
            query = query.filter(Event.status == status)

        # Attendance filter
        if attendance:
            query = query.filter(Event.attendance == attendance)

        # Order by date, then by start time
        query = query.order_by(Event.event_date.asc(), Event.start_time.asc())

        return query.all()

    def list_by_month(self, year: int, month: int, include_deleted: bool = False) -> List[Event]:
        """
        List events for a specific month.

        Convenience method for calendar views.

        Args:
            year: Year (e.g., 2026)
            month: Month (1-12)
            include_deleted: If True, include soft-deleted events

        Returns:
            List of Event instances for the month
        """
        # Calculate first and last day of month
        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1)
        else:
            last_day = date(year, month + 1, 1)

        # Subtract one day to get actual last day of month
        from datetime import timedelta
        last_day = last_day - timedelta(days=1)

        return self.list(
            start_date=first_day,
            end_date=last_day,
            include_deleted=include_deleted,
        )

    def get_stats(self) -> dict:
        """
        Get event statistics for KPIs.

        Returns:
            Dictionary with event statistics:
            - total_count: Total non-deleted events
            - upcoming_count: Events with status 'future' or 'confirmed'
            - this_month_count: Events in current month
            - attended_count: Events with attendance 'attended'
        """
        today = date.today()
        first_of_month = date(today.year, today.month, 1)
        if today.month == 12:
            first_of_next_month = date(today.year + 1, 1, 1)
        else:
            first_of_next_month = date(today.year, today.month + 1, 1)

        # Base query for non-deleted events
        base_query = self.db.query(func.count(Event.id)).filter(
            Event.deleted_at.is_(None)
        )

        total = base_query.scalar()

        upcoming = (
            base_query.filter(
                Event.event_date >= today,
                Event.status.in_(["future", "confirmed"]),
            ).scalar()
        )

        this_month = (
            base_query.filter(
                Event.event_date >= first_of_month,
                Event.event_date < first_of_next_month,
            ).scalar()
        )

        attended = (
            base_query.filter(Event.attendance == "attended").scalar()
        )

        return {
            "total_count": total or 0,
            "upcoming_count": upcoming or 0,
            "this_month_count": this_month or 0,
            "attended_count": attended or 0,
        }

    def get_series_by_guid(self, guid: str) -> EventSeries:
        """
        Get an event series by GUID.

        Args:
            guid: Series GUID (ser_xxx format)

        Returns:
            EventSeries instance with events loaded

        Raises:
            NotFoundError: If series not found
        """
        if not GuidService.validate_guid(guid, "ser"):
            raise NotFoundError("EventSeries", guid)

        try:
            uuid_value = GuidService.parse_guid(guid, "ser")
        except ValueError:
            raise NotFoundError("EventSeries", guid)

        series = (
            self.db.query(EventSeries)
            .options(joinedload(EventSeries.category))
            .filter(EventSeries.uuid == uuid_value)
            .first()
        )

        if not series:
            raise NotFoundError("EventSeries", guid)

        return series

    def build_event_response(self, event: Event) -> dict:
        """
        Build a response dictionary for an event.

        Computes effective fields (title, category) and includes
        series information.

        Args:
            event: Event instance with relationships loaded

        Returns:
            Dictionary suitable for EventResponse schema
        """
        # Get effective category (from event or series)
        category = event.category
        if not category and event.series:
            category = event.series.category

        category_data = None
        if category:
            category_data = {
                "guid": category.guid,
                "name": category.name,
                "icon": category.icon,
                "color": category.color,
            }

        # Build location data
        location_data = None
        if event.location:
            location_data = {
                "guid": event.location.guid,
                "name": event.location.name,
                "city": event.location.city,
                "country": event.location.country,
                "timezone": event.location.timezone,
            }

        # Get effective logistics (from event or inherit from series)
        ticket_required = event.ticket_required
        ticket_status = event.ticket_status
        timeoff_required = event.timeoff_required
        timeoff_status = event.timeoff_status
        travel_required = event.travel_required
        travel_status = event.travel_status

        # Inherit from series if event values are None
        if event.series:
            if ticket_required is None:
                ticket_required = event.series.ticket_required
            if timeoff_required is None:
                timeoff_required = event.series.timeoff_required
            if travel_required is None:
                travel_required = event.series.travel_required

        response = {
            "guid": event.guid,
            "title": event.effective_title,
            "event_date": event.event_date,
            "start_time": event.start_time,
            "end_time": event.end_time,
            "is_all_day": event.is_all_day,
            "input_timezone": event.input_timezone,
            "status": event.status,
            "attendance": event.attendance,
            "category": category_data,
            "location": location_data,
            "series_guid": event.series.guid if event.series else None,
            "sequence_number": event.sequence_number,
            "series_total": event.series.total_events if event.series else None,
            # Logistics summary
            "ticket_required": ticket_required,
            "ticket_status": ticket_status,
            "timeoff_required": timeoff_required,
            "timeoff_status": timeoff_status,
            "travel_required": travel_required,
            "travel_status": travel_status,
            # Deadline flag
            "is_deadline": event.is_deadline,
            "created_at": event.created_at,
            "updated_at": event.updated_at,
        }

        return response

    def build_event_detail_response(self, event: Event) -> dict:
        """
        Build a detailed response dictionary for an event.

        Includes all event fields plus related entities.

        Args:
            event: Event instance with relationships loaded

        Returns:
            Dictionary suitable for EventDetailResponse schema
        """
        response = self.build_event_response(event)

        # Add description (effective, falls back to series description)
        response["description"] = event.effective_description

        # Note: location is already included from build_event_response

        # Add organizer
        if event.organizer:
            response["organizer"] = {
                "guid": event.organizer.guid,
                "name": event.organizer.name,
            }
        else:
            response["organizer"] = None

        # Add performers
        performers = []
        for ep in event.event_performers:
            if ep.performer:
                performers.append({
                    "guid": ep.performer.guid,
                    "name": ep.performer.name,
                    "instagram_handle": ep.performer.instagram_handle,
                    "status": ep.status,
                })
        response["performers"] = performers

        # Add series details (including deadline info)
        if event.series:
            # Get deadline entry GUID if exists
            deadline_entry = self._get_deadline_entry(event.series.id)
            response["series"] = {
                "guid": event.series.guid,
                "title": event.series.title,
                "total_events": event.series.total_events,
                "deadline_date": event.series.deadline_date.isoformat() if event.series.deadline_date else None,
                "deadline_time": event.series.deadline_time.isoformat() if event.series.deadline_time else None,
                "deadline_entry_guid": deadline_entry.guid if deadline_entry else None,
            }
        else:
            response["series"] = None

        # Add logistics
        response["ticket_required"] = event.ticket_required
        response["ticket_status"] = event.ticket_status
        response["ticket_purchase_date"] = event.ticket_purchase_date
        response["timeoff_required"] = event.timeoff_required
        response["timeoff_status"] = event.timeoff_status
        response["timeoff_booking_date"] = event.timeoff_booking_date
        response["travel_required"] = event.travel_required
        response["travel_status"] = event.travel_status
        response["travel_booking_date"] = event.travel_booking_date
        response["deadline_date"] = event.deadline_date
        response["deadline_time"] = event.deadline_time

        # Add soft delete
        response["deleted_at"] = event.deleted_at

        return response

    # =========================================================================
    # Helper Methods for CRUD
    # =========================================================================

    def _get_category_by_guid(self, guid: str) -> Category:
        """
        Get a category by GUID.

        Args:
            guid: Category GUID (cat_xxx format)

        Returns:
            Category instance

        Raises:
            ValidationError: If category not found or invalid GUID
        """
        if not GuidService.validate_guid(guid, "cat"):
            raise ValidationError(f"Invalid category GUID: {guid}", field="category_guid")

        try:
            uuid_value = GuidService.parse_guid(guid, "cat")
        except ValueError:
            raise ValidationError(f"Invalid category GUID: {guid}", field="category_guid")

        category = self.db.query(Category).filter(Category.uuid == uuid_value).first()
        if not category:
            raise ValidationError(f"Category not found: {guid}", field="category_guid")

        return category

    def _get_location_by_guid(self, guid: str) -> Optional[Location]:
        """
        Get a location by GUID.

        Args:
            guid: Location GUID (loc_xxx format)

        Returns:
            Location instance or None

        Raises:
            ValidationError: If location not found or invalid GUID
        """
        if not guid:
            return None

        if not GuidService.validate_guid(guid, "loc"):
            raise ValidationError(f"Invalid location GUID: {guid}", field="location_guid")

        try:
            uuid_value = GuidService.parse_guid(guid, "loc")
        except ValueError:
            raise ValidationError(f"Invalid location GUID: {guid}", field="location_guid")

        location = self.db.query(Location).filter(Location.uuid == uuid_value).first()
        if not location:
            raise ValidationError(f"Location not found: {guid}", field="location_guid")

        return location

    def _get_organizer_by_guid(self, guid: str) -> Optional[Organizer]:
        """
        Get an organizer by GUID.

        Args:
            guid: Organizer GUID (org_xxx format)

        Returns:
            Organizer instance or None

        Raises:
            ValidationError: If organizer not found or invalid GUID
        """
        if not guid:
            return None

        if not GuidService.validate_guid(guid, "org"):
            raise ValidationError(f"Invalid organizer GUID: {guid}", field="organizer_guid")

        try:
            uuid_value = GuidService.parse_guid(guid, "org")
        except ValueError:
            raise ValidationError(f"Invalid organizer GUID: {guid}", field="organizer_guid")

        organizer = self.db.query(Organizer).filter(Organizer.uuid == uuid_value).first()
        if not organizer:
            raise ValidationError(f"Organizer not found: {guid}", field="organizer_guid")

        return organizer

    # =========================================================================
    # Create Operations
    # =========================================================================

    def create(
        self,
        title: str,
        category_guid: str,
        event_date: date,
        description: Optional[str] = None,
        location_guid: Optional[str] = None,
        organizer_guid: Optional[str] = None,
        start_time: Optional[Any] = None,
        end_time: Optional[Any] = None,
        is_all_day: bool = False,
        input_timezone: Optional[str] = None,
        status: str = "future",
        attendance: str = "planned",
        ticket_required: Optional[bool] = None,
        timeoff_required: Optional[bool] = None,
        travel_required: Optional[bool] = None,
        deadline_date: Optional[date] = None,
        deadline_time: Optional[Any] = None,
    ) -> Event:
        """
        Create a new standalone event.

        Args:
            title: Event title
            category_guid: Category GUID (cat_xxx)
            event_date: Date of the event
            description: Optional event description
            location_guid: Optional location GUID
            organizer_guid: Optional organizer GUID
            start_time: Optional start time
            end_time: Optional end time
            is_all_day: Whether event spans full day
            input_timezone: Optional IANA timezone
            status: Event status (default: future)
            attendance: Attendance status (default: planned)
            ticket_required: Optional ticket requirement
            timeoff_required: Optional time-off requirement
            travel_required: Optional travel requirement
            deadline_date: Optional workflow deadline date
            deadline_time: Optional workflow deadline time

        Returns:
            Created Event instance

        Raises:
            ValidationError: If category, location, or organizer not found
        """
        # Resolve foreign keys
        category = self._get_category_by_guid(category_guid)
        location = self._get_location_by_guid(location_guid) if location_guid else None
        organizer = self._get_organizer_by_guid(organizer_guid) if organizer_guid else None

        # Apply default logistics from organizer and location if not explicitly set
        effective_ticket_required = ticket_required
        effective_timeoff_required = timeoff_required
        effective_travel_required = travel_required

        if effective_ticket_required is None and organizer and organizer.ticket_required_default:
            effective_ticket_required = True
            logger.debug(f"Applied ticket_required default from organizer: {organizer.name}")

        if effective_timeoff_required is None and location and location.timeoff_required_default:
            effective_timeoff_required = True
            logger.debug(f"Applied timeoff_required default from location: {location.name}")

        if effective_travel_required is None and location and location.travel_required_default:
            effective_travel_required = True
            logger.debug(f"Applied travel_required default from location: {location.name}")

        # Create event
        event = Event(
            title=title,
            description=description,
            category_id=category.id,
            location_id=location.id if location else None,
            organizer_id=organizer.id if organizer else None,
            event_date=event_date,
            start_time=start_time,
            end_time=end_time,
            is_all_day=is_all_day,
            input_timezone=input_timezone,
            status=status,
            attendance=attendance,
            ticket_required=effective_ticket_required,
            timeoff_required=effective_timeoff_required,
            travel_required=effective_travel_required,
            deadline_date=deadline_date,
            deadline_time=deadline_time,
        )

        self.db.add(event)
        self.db.flush()  # Get ID for deadline entry creation

        # Create deadline entry if deadline_date is set
        if deadline_date:
            self._sync_standalone_deadline_entry(event)

        self.db.commit()
        self.db.refresh(event)

        logger.info(f"Created event: {event.guid} - {title}")
        return event

    def create_series(
        self,
        title: str,
        category_guid: str,
        event_dates: List[date],
        description: Optional[str] = None,
        location_guid: Optional[str] = None,
        organizer_guid: Optional[str] = None,
        start_time: Optional[Any] = None,
        end_time: Optional[Any] = None,
        is_all_day: bool = False,
        input_timezone: Optional[str] = None,
        ticket_required: bool = False,
        timeoff_required: bool = False,
        travel_required: bool = False,
        status: str = "future",
        attendance: str = "planned",
        deadline_date: Optional[date] = None,
        deadline_time: Optional[Any] = None,
    ) -> EventSeries:
        """
        Create a new event series with individual events.

        Args:
            title: Series title (shared by all events)
            category_guid: Category GUID (cat_xxx)
            event_dates: List of dates (minimum 2)
            description: Optional series description
            location_guid: Optional default location GUID
            organizer_guid: Optional default organizer GUID
            start_time: Optional default start time
            end_time: Optional default end time
            is_all_day: Whether events span full day
            input_timezone: Optional IANA timezone
            ticket_required: Default ticket requirement
            timeoff_required: Default time-off requirement
            travel_required: Default travel requirement
            status: Initial status for all events (default: future)
            attendance: Initial attendance for all events (default: planned)
            deadline_date: Optional deadline date for deliverables
            deadline_time: Optional deadline time

        Returns:
            Created EventSeries instance with events

        Raises:
            ValidationError: If dates < 2, or category/location/organizer not found
        """
        # Validate minimum dates
        if len(event_dates) < 2:
            raise ValidationError(
                "Event series requires at least 2 dates",
                field="event_dates"
            )

        # Sort dates chronologically
        sorted_dates = sorted(event_dates)

        # Resolve foreign keys
        category = self._get_category_by_guid(category_guid)
        location = self._get_location_by_guid(location_guid) if location_guid else None
        organizer = self._get_organizer_by_guid(organizer_guid) if organizer_guid else None

        # Apply default logistics from organizer and location if not explicitly set
        effective_ticket_required = ticket_required
        effective_timeoff_required = timeoff_required
        effective_travel_required = travel_required

        if not effective_ticket_required and organizer and organizer.ticket_required_default:
            effective_ticket_required = True
            logger.debug(f"Applied ticket_required default from organizer: {organizer.name}")

        if not effective_timeoff_required and location and location.timeoff_required_default:
            effective_timeoff_required = True
            logger.debug(f"Applied timeoff_required default from location: {location.name}")

        if not effective_travel_required and location and location.travel_required_default:
            effective_travel_required = True
            logger.debug(f"Applied travel_required default from location: {location.name}")

        # Create series
        series = EventSeries(
            title=title,
            description=description,
            category_id=category.id,
            location_id=location.id if location else None,
            organizer_id=organizer.id if organizer else None,
            input_timezone=input_timezone,
            ticket_required=effective_ticket_required,
            timeoff_required=effective_timeoff_required,
            travel_required=effective_travel_required,
            total_events=len(sorted_dates),
            deadline_date=deadline_date,
            deadline_time=deadline_time,
        )

        self.db.add(series)
        self.db.flush()  # Get series ID

        # Create individual events
        for i, event_date in enumerate(sorted_dates, start=1):
            event = Event(
                series_id=series.id,
                sequence_number=i,
                # These inherit from series via effective_* properties
                title=None,  # Inherits from series
                category_id=None,  # Inherits from series
                location_id=location.id if location else None,
                organizer_id=organizer.id if organizer else None,
                event_date=event_date,
                start_time=start_time,
                end_time=end_time,
                is_all_day=is_all_day,
                input_timezone=input_timezone,
                status=status,
                attendance=attendance,
                # Logistics inherit from series
                ticket_required=None,
                timeoff_required=None,
                travel_required=None,
                # Deadline is synced across all events in series
                deadline_date=deadline_date,
                deadline_time=deadline_time,
            )
            self.db.add(event)

        # Sync deadline entry if deadline_date is set
        self._sync_deadline_entry(series)

        self.db.commit()
        self.db.refresh(series)

        logger.info(f"Created event series: {series.guid} - {title} ({len(sorted_dates)} events)")
        return series

    # =========================================================================
    # Update Operations
    # =========================================================================

    def update_series(
        self,
        guid: str,
        **updates: Any
    ) -> EventSeries:
        """
        Update an event series and sync deadline entry.

        Args:
            guid: Series GUID (ser_xxx)
            **updates: Fields to update (deadline_date, deadline_time, title, etc.)

        Returns:
            Updated EventSeries instance

        Raises:
            NotFoundError: If series not found
            ValidationError: If invalid update data
        """
        series = self.get_series_by_guid(guid)

        # Handle foreign key resolutions
        if "category_guid" in updates:
            category_guid = updates.pop("category_guid")
            if category_guid:
                category = self._get_category_by_guid(category_guid)
                updates["category_id"] = category.id
            else:
                updates["category_id"] = None

        if "location_guid" in updates:
            location_guid = updates.pop("location_guid")
            if location_guid:
                location = self._get_location_by_guid(location_guid)
                updates["location_id"] = location.id
            else:
                updates["location_id"] = None

        if "organizer_guid" in updates:
            organizer_guid = updates.pop("organizer_guid")
            if organizer_guid:
                organizer = self._get_organizer_by_guid(organizer_guid)
                updates["organizer_id"] = organizer.id
            else:
                updates["organizer_id"] = None

        # Check if deadline fields are being updated
        has_deadline_date = "deadline_date" in updates
        has_deadline_time = "deadline_time" in updates
        deadline_changed = has_deadline_date or has_deadline_time
        deadline_date_value = updates.get("deadline_date") if has_deadline_date else None
        deadline_time_value = updates.get("deadline_time") if has_deadline_time else None

        # Apply updates to series
        for field, value in updates.items():
            if hasattr(series, field):
                setattr(series, field, value)
        series.updated_at = datetime.utcnow()

        # Sync deadline across all events and create/update deadline entry
        if deadline_changed:
            # Sync deadline_date and deadline_time to ALL events in the series
            all_events = (
                self.db.query(Event)
                .filter(
                    Event.series_id == series.id,
                    Event.is_deadline == False,
                    Event.deleted_at.is_(None)
                )
                .all()
            )
            for e in all_events:
                if has_deadline_date:
                    e.deadline_date = deadline_date_value
                if has_deadline_time:
                    e.deadline_time = deadline_time_value
                e.updated_at = datetime.utcnow()
            logger.info(f"Synced deadline across {len(all_events)} series events")

            # Sync the deadline entry (create/update/delete)
            self._sync_deadline_entry(series)

        self.db.commit()
        self.db.refresh(series)

        logger.info(f"Updated event series: {series.guid}")
        return series

    def build_series_response(self, series: EventSeries) -> dict:
        """
        Build a response dictionary for an event series.

        Args:
            series: EventSeries instance with relationships loaded

        Returns:
            Dictionary suitable for EventSeriesResponse schema
        """
        # Get deadline entry GUID if exists
        deadline_entry = self._get_deadline_entry(series.id)
        deadline_entry_guid = deadline_entry.guid if deadline_entry else None

        # Get events in series (excluding deadline entries)
        events = (
            self.db.query(Event)
            .filter(
                Event.series_id == series.id,
                Event.is_deadline == False,
                Event.deleted_at.is_(None)
            )
            .order_by(Event.event_date.asc())
            .all()
        )

        events_data = [
            {
                "guid": e.guid,
                "event_date": e.event_date.isoformat() if e.event_date else None,
                "sequence_number": e.sequence_number,
                "attendance": e.attendance,
            }
            for e in events
        ]

        return {
            "guid": series.guid,
            "title": series.title,
            "description": series.description,
            "category_guid": series.category.guid if series.category else None,
            "category_name": series.category.name if series.category else None,
            "location_guid": series.location.guid if series.location else None,
            "organizer_guid": series.organizer.guid if series.organizer else None,
            "input_timezone": series.input_timezone,
            "ticket_required": series.ticket_required,
            "timeoff_required": series.timeoff_required,
            "travel_required": series.travel_required,
            "deadline_date": series.deadline_date,
            "deadline_time": series.deadline_time,
            "deadline_entry_guid": deadline_entry_guid,
            "total_events": series.total_events,
            "events": events_data,
            "created_at": series.created_at,
            "updated_at": series.updated_at,
        }

    def update(
        self,
        guid: str,
        scope: str = "single",
        **updates: Any
    ) -> Event:
        """
        Update an event.

        Args:
            guid: Event GUID (evt_xxx)
            scope: Update scope for series events:
                - "single": Only this event
                - "this_and_future": This and all future events in series
                - "all": All events in series
            **updates: Fields to update

        Returns:
            Updated Event instance

        Raises:
            NotFoundError: If event not found
            ValidationError: If invalid update data

        Note:
            Location changes on series events are ALWAYS applied to all events
            in the series, regardless of scope. This is because location is
            considered a series-level property.
        """
        event = self.get_by_guid(guid)

        # Resolve foreign keys if provided
        if "category_guid" in updates:
            category_guid = updates.pop("category_guid")
            if category_guid:
                category = self._get_category_by_guid(category_guid)
                updates["category_id"] = category.id
            else:
                updates["category_id"] = None

        # Handle location_guid - extract separately for series sync
        # Track both the value and whether it was provided (to handle null values)
        location_id_update = None
        updating_location = "location_guid" in updates
        if updating_location:
            location_guid = updates.pop("location_guid")
            if location_guid:
                location = self._get_location_by_guid(location_guid)
                location_id_update = location.id
            else:
                location_id_update = None

        # Handle organizer_guid - extract separately for series sync
        # Organizer is a series-level property, always synced across all events
        organizer_id_update = None
        updating_organizer = "organizer_guid" in updates
        if updating_organizer:
            organizer_guid = updates.pop("organizer_guid")
            if organizer_guid:
                organizer = self._get_organizer_by_guid(organizer_guid)
                organizer_id_update = organizer.id
            else:
                organizer_id_update = None

        # Handle deadline fields - series-level property
        # Deadline is stored on EventSeries, synced via deadline entry
        has_deadline_date = "deadline_date" in updates
        has_deadline_time = "deadline_time" in updates
        updating_deadline = has_deadline_date or has_deadline_time
        deadline_date_update = updates.pop("deadline_date", None) if has_deadline_date else None
        deadline_time_update = updates.pop("deadline_time", None) if has_deadline_time else None

        # Remove scope from updates (it's not an event field)
        updates.pop("scope", None)

        # Determine which events to update based on scope
        if event.series and scope != "single":
            events_to_update = self._get_series_events_for_update(event, scope)
        else:
            events_to_update = [event]

        # Apply regular updates based on scope
        for e in events_to_update:
            for field, value in updates.items():
                if hasattr(e, field):
                    setattr(e, field, value)
            e.updated_at = datetime.utcnow()

        # Handle location sync for series events
        # Location is always synced across ALL events in a series
        if updating_location:
            if event.series:
                # Get ALL events in the series (regardless of scope)
                all_series_events = self._get_series_events_for_update(event, "all")
                for e in all_series_events:
                    e.location_id = location_id_update
                    if e not in events_to_update:
                        e.updated_at = datetime.utcnow()
                logger.info(f"Synced location across {len(all_series_events)} series events")
            else:
                # Standalone event - just update location
                event.location_id = location_id_update

        # Handle organizer sync for series events
        # Organizer is always synced across ALL events in a series
        if updating_organizer:
            if event.series:
                # Get ALL events in the series (regardless of scope)
                all_series_events = self._get_series_events_for_update(event, "all")
                for e in all_series_events:
                    e.organizer_id = organizer_id_update
                    if e not in events_to_update:
                        e.updated_at = datetime.utcnow()
                logger.info(f"Synced organizer across {len(all_series_events)} series events")
            else:
                # Standalone event - just update organizer
                event.organizer_id = organizer_id_update

        # Handle deadline sync for series events
        # Deadline is a series-level property: update series, sync to all events, and create deadline entry
        if updating_deadline:
            if event.series:
                series = event.series
                if has_deadline_date:
                    series.deadline_date = deadline_date_update
                if has_deadline_time:
                    series.deadline_time = deadline_time_update
                series.updated_at = datetime.utcnow()

                # Sync deadline_date and deadline_time to ALL events in the series (like location/organizer)
                all_series_events = self._get_series_events_for_update(event, "all")
                for e in all_series_events:
                    if not e.is_deadline:  # Don't update deadline entry's deadline_date/time
                        if has_deadline_date:
                            e.deadline_date = deadline_date_update
                        if has_deadline_time:
                            e.deadline_time = deadline_time_update
                        if e not in events_to_update:
                            e.updated_at = datetime.utcnow()
                logger.info(f"Synced deadline across {len(all_series_events)} series events")

                # Sync the deadline entry (create/update/delete)
                self._sync_deadline_entry(series)
                logger.info(f"Synced deadline entry for series: {series.guid}")
            else:
                # Standalone event - update deadline_date and deadline_time, sync entry
                if has_deadline_date:
                    event.deadline_date = deadline_date_update
                if has_deadline_time:
                    event.deadline_time = deadline_time_update

                # Sync the deadline entry for standalone event (create/update/delete)
                self._sync_standalone_deadline_entry(event)
                logger.info(f"Synced deadline entry for standalone event: {event.guid}")

        self.db.commit()
        self.db.refresh(event)

        logger.info(f"Updated event: {event.guid} (scope: {scope}, events: {len(events_to_update)})")
        return event

    def _get_series_events_for_update(
        self,
        event: Event,
        scope: str
    ) -> List[Event]:
        """
        Get events to update based on scope.

        Args:
            event: Reference event
            scope: Update scope ("this_and_future" or "all")

        Returns:
            List of events to update
        """
        if not event.series:
            return [event]

        query = (
            self.db.query(Event)
            .filter(
                Event.series_id == event.series_id,
                Event.deleted_at.is_(None)
            )
        )

        if scope == "this_and_future":
            query = query.filter(Event.event_date >= event.event_date)
        # "all" scope doesn't need additional filtering

        return query.order_by(Event.event_date.asc()).all()

    # =========================================================================
    # Delete Operations
    # =========================================================================

    def soft_delete(
        self,
        guid: str,
        scope: str = "single"
    ) -> Event:
        """
        Soft delete an event.

        Args:
            guid: Event GUID (evt_xxx)
            scope: Delete scope for series events:
                - "single": Only this event
                - "this_and_future": This and all future events in series
                - "all": All events in series

        Returns:
            Deleted Event instance

        Raises:
            NotFoundError: If event not found
        """
        event = self.get_by_guid(guid)
        now = datetime.utcnow()

        # Determine which events to delete
        if event.series and scope != "single":
            events_to_delete = self._get_series_events_for_update(event, scope)
        else:
            events_to_delete = [event]

        # Soft delete events
        for e in events_to_delete:
            e.deleted_at = now

        # Update series total if needed
        if event.series and scope != "single":
            self._update_series_total(event.series)

        self.db.commit()
        self.db.refresh(event)

        logger.info(f"Soft deleted event: {event.guid} (scope: {scope}, events: {len(events_to_delete)})")
        return event

    def restore(self, guid: str) -> Event:
        """
        Restore a soft-deleted event.

        Args:
            guid: Event GUID (evt_xxx)

        Returns:
            Restored Event instance

        Raises:
            NotFoundError: If event not found
        """
        event = self.get_by_guid(guid, include_deleted=True)

        if not event.deleted_at:
            return event  # Already not deleted

        event.deleted_at = None
        event.updated_at = datetime.utcnow()

        # Update series total if part of series
        if event.series:
            self._update_series_total(event.series)

        self.db.commit()
        self.db.refresh(event)

        logger.info(f"Restored event: {event.guid}")
        return event

    def _update_series_total(self, series: EventSeries) -> None:
        """
        Update series total_events count based on non-deleted events.

        Args:
            series: EventSeries to update
        """
        count = (
            self.db.query(func.count(Event.id))
            .filter(
                Event.series_id == series.id,
                Event.deleted_at.is_(None)
            )
            .scalar()
        )

        series.total_events = count or 0
        series.updated_at = datetime.utcnow()

    # =========================================================================
    # Deadline Entry Sync (T018-T022)
    # =========================================================================

    def _get_deadline_entry(self, series_id: int) -> Optional[Event]:
        """
        Get the deadline entry for a series.

        Args:
            series_id: Internal series ID

        Returns:
            Event instance if deadline entry exists, None otherwise
        """
        return (
            self.db.query(Event)
            .filter(
                Event.series_id == series_id,
                Event.is_deadline == True,
                Event.deleted_at.is_(None)
            )
            .first()
        )

    def _create_deadline_entry(self, series: EventSeries) -> Event:
        """
        Create a deadline entry for a series.

        The deadline entry is a special Event record with is_deadline=True.
        It appears in the calendar on the deadline date.

        Note: Only organizer is copied to deadline entry, not location or performers.

        Args:
            series: EventSeries with deadline_date set

        Returns:
            Created Event instance
        """
        deadline_entry = Event(
            series_id=series.id,
            sequence_number=None,  # Not part of series sequence
            title=f"{series.title} - Deadline",
            category_id=series.category_id,
            location_id=None,  # Deadline entries don't have a location
            organizer_id=series.organizer_id,
            event_date=series.deadline_date,
            start_time=series.deadline_time,
            end_time=None,
            is_all_day=series.deadline_time is None,
            input_timezone=series.input_timezone,
            status="future",
            attendance="planned",
            is_deadline=True,
        )
        self.db.add(deadline_entry)
        self.db.flush()  # Get ID for logging

        logger.info(
            f"Created deadline entry for series",
            extra={
                "series_guid": series.guid,
                "deadline_entry_guid": deadline_entry.guid,
                "deadline_date": str(series.deadline_date)
            }
        )

        return deadline_entry

    def _update_deadline_entry(self, existing: Event, series: EventSeries) -> Event:
        """
        Update an existing deadline entry with new deadline data.

        Note: Only organizer is synced to deadline entry, not location or performers.

        Args:
            existing: Existing deadline Event record
            series: EventSeries with updated deadline data

        Returns:
            Updated Event instance
        """
        existing.event_date = series.deadline_date
        existing.start_time = series.deadline_time
        existing.is_all_day = series.deadline_time is None
        existing.title = f"{series.title} - Deadline"
        existing.category_id = series.category_id
        existing.location_id = None  # Deadline entries don't have a location
        existing.organizer_id = series.organizer_id
        existing.input_timezone = series.input_timezone
        existing.updated_at = datetime.utcnow()

        logger.info(
            f"Updated deadline entry for series",
            extra={
                "series_guid": series.guid,
                "deadline_entry_guid": existing.guid,
                "deadline_date": str(series.deadline_date)
            }
        )

        return existing

    def _delete_deadline_entry(self, existing: Event) -> None:
        """
        Delete a deadline entry (hard delete).

        Args:
            existing: Deadline Event to delete
        """
        guid = existing.guid
        series_guid = existing.series.guid if existing.series else None

        self.db.delete(existing)

        logger.info(
            f"Deleted deadline entry for series",
            extra={
                "series_guid": series_guid,
                "deadline_entry_guid": guid
            }
        )

    def _sync_deadline_entry(self, series: EventSeries) -> Optional[Event]:
        """
        Synchronize deadline entry with series deadline data.

        Creates, updates, or deletes the deadline entry based on whether
        the series has a deadline_date set.

        Args:
            series: EventSeries to sync deadline for

        Returns:
            Deadline Event if created/updated, None if deleted/no deadline
        """
        existing = self._get_deadline_entry(series.id)

        if series.deadline_date:
            if existing:
                # Update existing deadline entry
                return self._update_deadline_entry(existing, series)
            else:
                # Create new deadline entry
                return self._create_deadline_entry(series)
        else:
            if existing:
                # Remove deadline entry since deadline was cleared
                self._delete_deadline_entry(existing)
            return None

    # =========================================================================
    # Standalone Event Deadline Entry Sync
    # =========================================================================

    def _get_standalone_deadline_entry(self, event_id: int) -> Optional[Event]:
        """
        Get the deadline entry for a standalone event.

        Args:
            event_id: Internal event ID

        Returns:
            Event instance if deadline entry exists, None otherwise
        """
        return (
            self.db.query(Event)
            .filter(
                Event.parent_event_id == event_id,
                Event.is_deadline == True,
                Event.deleted_at.is_(None)
            )
            .first()
        )

    def _create_standalone_deadline_entry(self, event: Event) -> Event:
        """
        Create a deadline entry for a standalone event.

        The deadline entry is a special Event record with is_deadline=True
        linked to the parent event via parent_event_id.

        Note: Only organizer is copied to deadline entry, not location or performers.

        Args:
            event: Standalone Event with deadline_date set

        Returns:
            Created Event instance
        """
        deadline_entry = Event(
            parent_event_id=event.id,
            sequence_number=None,
            title=f"{event.title} - Deadline",
            category_id=event.category_id,
            location_id=None,  # Deadline entries don't have a location
            organizer_id=event.organizer_id,
            event_date=event.deadline_date,
            start_time=event.deadline_time,
            end_time=None,
            is_all_day=event.deadline_time is None,
            input_timezone=event.input_timezone,
            status="future",
            attendance="planned",
            is_deadline=True,
        )
        self.db.add(deadline_entry)
        self.db.flush()

        logger.info(
            f"Created deadline entry for standalone event",
            extra={
                "event_guid": event.guid,
                "deadline_entry_guid": deadline_entry.guid,
                "deadline_date": str(event.deadline_date)
            }
        )

        return deadline_entry

    def _update_standalone_deadline_entry(self, existing: Event, event: Event) -> Event:
        """
        Update an existing deadline entry for a standalone event.

        Note: Only organizer is synced to deadline entry, not location or performers.

        Args:
            existing: Existing deadline Event record
            event: Standalone Event with updated deadline data

        Returns:
            Updated Event instance
        """
        existing.event_date = event.deadline_date
        existing.start_time = event.deadline_time
        existing.is_all_day = event.deadline_time is None
        existing.title = f"{event.title} - Deadline"
        existing.category_id = event.category_id
        existing.location_id = None  # Deadline entries don't have a location
        existing.organizer_id = event.organizer_id
        existing.input_timezone = event.input_timezone
        existing.updated_at = datetime.utcnow()

        logger.info(
            f"Updated deadline entry for standalone event",
            extra={
                "event_guid": event.guid,
                "deadline_entry_guid": existing.guid,
                "deadline_date": str(event.deadline_date)
            }
        )

        return existing

    def _sync_standalone_deadline_entry(self, event: Event) -> Optional[Event]:
        """
        Synchronize deadline entry with standalone event deadline data.

        Creates, updates, or deletes the deadline entry based on whether
        the event has a deadline_date set.

        Args:
            event: Standalone Event to sync deadline for

        Returns:
            Deadline Event if created/updated, None if deleted/no deadline
        """
        existing = self._get_standalone_deadline_entry(event.id)

        if event.deadline_date:
            if existing:
                return self._update_standalone_deadline_entry(existing, event)
            else:
                return self._create_standalone_deadline_entry(event)
        else:
            if existing:
                # Remove deadline entry since deadline was cleared
                guid = existing.guid
                self.db.delete(existing)
                logger.info(
                    f"Deleted deadline entry for standalone event",
                    extra={
                        "event_guid": event.guid,
                        "deadline_entry_guid": guid
                    }
                )
            return None

    # =========================================================================
    # Event Performer Management (T115)
    # =========================================================================

    def add_performer_to_event(
        self,
        event_guid: str,
        performer_guid: str,
        status: str = "announced"
    ) -> EventPerformer:
        """
        Add a performer to an event.

        For series events, the performer is added to ALL events in the series
        with the specified status. Performer assignments are a series-level property.

        Args:
            event_guid: Event GUID (evt_xxx format)
            performer_guid: Performer GUID (prf_xxx format)
            status: Performer status ('confirmed' or 'cancelled')

        Returns:
            Created EventPerformer instance for the requested event

        Raises:
            NotFoundError: If event or performer not found
            ValidationError: If category mismatch
            ConflictError: If performer already added to event
        """
        event = self.get_by_guid(event_guid)
        performer = self._get_performer_by_guid(performer_guid)

        # Validate category match
        if performer.category_id != event.category_id:
            raise ValidationError(
                f"Performer '{performer.name}' category does not match event category",
                field="performer_guid"
            )

        # Check if already added to this event
        existing = (
            self.db.query(EventPerformer)
            .filter(
                EventPerformer.event_id == event.id,
                EventPerformer.performer_id == performer.id
            )
            .first()
        )
        if existing:
            raise ConflictError(
                f"Performer '{performer.name}' is already added to this event"
            )

        # Get all events to add performer to (for series sync)
        if event.series:
            events_to_update = self._get_series_events_for_update(event, "all")
        else:
            events_to_update = [event]

        # Create association for all events
        primary_event_performer = None
        added_count = 0
        for evt in events_to_update:
            # Skip if already added to this series event
            existing_in_series = (
                self.db.query(EventPerformer)
                .filter(
                    EventPerformer.event_id == evt.id,
                    EventPerformer.performer_id == performer.id
                )
                .first()
            )
            if existing_in_series:
                continue

            event_performer = EventPerformer(
                event_id=evt.id,
                performer_id=performer.id,
                status=status
            )
            self.db.add(event_performer)
            added_count += 1

            # Track the one for the original event to return
            if evt.id == event.id:
                primary_event_performer = event_performer

        self.db.commit()
        if primary_event_performer:
            self.db.refresh(primary_event_performer)

        logger.info(
            f"Added performer to event(s)",
            extra={
                "event_guid": event_guid,
                "performer_guid": performer_guid,
                "status": status,
                "events_updated": added_count,
                "is_series": event.series is not None
            }
        )

        return primary_event_performer

    def update_performer_status(
        self,
        event_guid: str,
        performer_guid: str,
        status: str
    ) -> EventPerformer:
        """
        Update a performer's status on an event.

        Note: Unlike add/remove operations, status updates are event-specific
        and do NOT sync across series events. This allows tracking different
        confirmation statuses for each event in a series.

        Args:
            event_guid: Event GUID
            performer_guid: Performer GUID
            status: New status ('confirmed' or 'cancelled')

        Returns:
            Updated EventPerformer instance

        Raises:
            NotFoundError: If event, performer, or association not found
        """
        event = self.get_by_guid(event_guid)
        performer = self._get_performer_by_guid(performer_guid)

        event_performer = (
            self.db.query(EventPerformer)
            .filter(
                EventPerformer.event_id == event.id,
                EventPerformer.performer_id == performer.id
            )
            .first()
        )
        if not event_performer:
            raise NotFoundError("EventPerformer", f"{event_guid}/{performer_guid}")

        event_performer.status = status
        self.db.commit()
        self.db.refresh(event_performer)

        logger.info(
            f"Updated performer status on event",
            extra={
                "event_guid": event_guid,
                "performer_guid": performer_guid,
                "status": status
            }
        )

        return event_performer

    def remove_performer_from_event(
        self,
        event_guid: str,
        performer_guid: str
    ) -> None:
        """
        Remove a performer from an event.

        For series events, the performer is removed from ALL events in the series.
        Performer assignments are a series-level property.

        Args:
            event_guid: Event GUID
            performer_guid: Performer GUID

        Raises:
            NotFoundError: If event, performer, or association not found
        """
        event = self.get_by_guid(event_guid)
        performer = self._get_performer_by_guid(performer_guid)

        # Verify the performer is associated with this event
        event_performer = (
            self.db.query(EventPerformer)
            .filter(
                EventPerformer.event_id == event.id,
                EventPerformer.performer_id == performer.id
            )
            .first()
        )
        if not event_performer:
            raise NotFoundError("EventPerformer", f"{event_guid}/{performer_guid}")

        # Get all events to remove performer from (for series sync)
        if event.series:
            events_to_update = self._get_series_events_for_update(event, "all")
        else:
            events_to_update = [event]

        # Remove association from all events
        removed_count = 0
        for evt in events_to_update:
            ep_to_delete = (
                self.db.query(EventPerformer)
                .filter(
                    EventPerformer.event_id == evt.id,
                    EventPerformer.performer_id == performer.id
                )
                .first()
            )
            if ep_to_delete:
                self.db.delete(ep_to_delete)
                removed_count += 1

        self.db.commit()

        logger.info(
            f"Removed performer from event(s)",
            extra={
                "event_guid": event_guid,
                "performer_guid": performer_guid,
                "events_updated": removed_count,
                "is_series": event.series is not None
            }
        )

    def list_event_performers(
        self,
        event_guid: str
    ) -> list:
        """
        List all performers for an event.

        Args:
            event_guid: Event GUID

        Returns:
            List of EventPerformer instances with loaded performers

        Raises:
            NotFoundError: If event not found
        """
        event = self.get_by_guid(event_guid)

        event_performers = (
            self.db.query(EventPerformer)
            .options(joinedload(EventPerformer.performer).joinedload(Performer.category))
            .filter(EventPerformer.event_id == event.id)
            .order_by(EventPerformer.created_at.asc())
            .all()
        )

        return event_performers

    def _get_performer_by_guid(self, guid: str) -> Performer:
        """
        Get a performer by GUID.

        Args:
            guid: Performer GUID (prf_xxx format)

        Returns:
            Performer instance

        Raises:
            NotFoundError: If performer not found
        """
        if not GuidService.validate_guid(guid, "prf"):
            raise NotFoundError("Performer", guid)

        try:
            uuid_value = GuidService.parse_guid(guid, "prf")
        except ValueError:
            raise NotFoundError("Performer", guid)

        performer = (
            self.db.query(Performer)
            .filter(Performer.uuid == uuid_value)
            .first()
        )
        if not performer:
            raise NotFoundError("Performer", guid)

        return performer
