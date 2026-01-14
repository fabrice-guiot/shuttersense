"""
Events API endpoints for managing calendar events.

Provides endpoints for:
- Listing events with date range and filtering
- Getting event details
- Creating single events and event series
- Updating events (with scope for series)
- Deleting events (soft delete with scope)
- Event statistics for KPIs

Phase 4 (MVP): List and get operations
Phase 5: Create, update, delete operations

Design:
- Uses dependency injection for services
- Comprehensive error handling with meaningful HTTP status codes
- All endpoints use GUID format (evt_xxx) for identifiers
- Date range queries support calendar views

Issue #39 - Calendar Events feature
"""

from typing import List, Optional
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.schemas.event import (
    EventCreate,
    EventSeriesCreate,
    EventSeriesUpdate,
    EventUpdate,
    EventResponse,
    EventDetailResponse,
    EventStatsResponse,
    EventStatus,
    AttendanceStatus,
    UpdateScope,
)
from backend.src.schemas.event_series import EventSeriesResponse
from backend.src.services.event_service import EventService
from backend.src.services.exceptions import NotFoundError, ValidationError, ConflictError, DeadlineProtectionError
from backend.src.schemas.performer import (
    EventPerformerCreate,
    EventPerformerUpdate,
    EventPerformerResponse,
    EventPerformersListResponse,
    PerformerResponse,
)
from backend.src.utils.logging_config import get_logger


logger = get_logger("api")

router = APIRouter(
    prefix="/events",
    tags=["Events"],
)


# ============================================================================
# Dependencies
# ============================================================================


def get_event_service(db: Session = Depends(get_db)) -> EventService:
    """Create EventService instance with database session."""
    return EventService(db=db)


# ============================================================================
# API Endpoints
# ============================================================================


@router.get(
    "/stats",
    response_model=EventStatsResponse,
    summary="Get event statistics",
    description="Get aggregated statistics for all events",
)
async def get_event_stats(
    event_service: EventService = Depends(get_event_service),
) -> EventStatsResponse:
    """
    Get aggregated statistics for all events.

    Returns:
        EventStatsResponse with:
        - total_count: Total non-deleted events
        - upcoming_count: Future events
        - this_month_count: Events this month
        - attended_count: Events marked as attended

    Example:
        GET /api/events/stats

        Response:
        {
          "total_count": 42,
          "upcoming_count": 15,
          "this_month_count": 3,
          "attended_count": 27
        }
    """
    try:
        stats = event_service.get_stats()

        logger.info(
            "Retrieved event stats",
            extra={"total_count": stats["total_count"]},
        )

        return EventStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting event stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve event statistics",
        )


@router.get(
    "",
    response_model=List[EventResponse],
    summary="List events",
    description="List events with optional date range and filtering",
)
async def list_events(
    start_date: Optional[date] = Query(
        default=None,
        description="Start of date range (inclusive)",
    ),
    end_date: Optional[date] = Query(
        default=None,
        description="End of date range (inclusive)",
    ),
    category_guid: Optional[str] = Query(
        default=None,
        description="Filter by category GUID",
    ),
    status: Optional[EventStatus] = Query(
        default=None,
        description="Filter by event status",
    ),
    attendance: Optional[AttendanceStatus] = Query(
        default=None,
        description="Filter by attendance status",
    ),
    include_deleted: bool = Query(
        default=False,
        description="Include soft-deleted events",
    ),
    include_deadlines: bool = Query(
        default=True,
        description="Include deadline entries (is_deadline=true). Set to false to exclude them.",
    ),
    event_service: EventService = Depends(get_event_service),
) -> List[EventResponse]:
    """
    List events with optional filtering.

    Query Parameters:
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)
        category_guid: Filter by category GUID
        status: Filter by event status (future, confirmed, completed, cancelled)
        attendance: Filter by attendance (planned, attended, skipped)
        include_deleted: Include soft-deleted events

    Returns:
        List of events ordered by date

    Example:
        GET /api/events?start_date=2026-01-01&end_date=2026-01-31

        Response:
        [
          {
            "guid": "evt_xxx",
            "title": "Airshow Day 1",
            "event_date": "2026-01-15",
            ...
          }
        ]
    """
    try:
        events = event_service.list(
            start_date=start_date,
            end_date=end_date,
            category_guid=category_guid,
            status=status.value if status else None,
            attendance=attendance.value if attendance else None,
            include_deleted=include_deleted,
            include_deadlines=include_deadlines,
        )

        logger.info(
            "Listed events",
            extra={
                "count": len(events),
                "start_date": str(start_date) if start_date else None,
                "end_date": str(end_date) if end_date else None,
            },
        )

        # Build response objects
        return [
            EventResponse(**event_service.build_event_response(event))
            for event in events
        ]

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error listing events: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list events",
        )


@router.get(
    "/{guid}",
    response_model=EventDetailResponse,
    summary="Get event by GUID",
    description="Get detailed information about a specific event",
)
async def get_event(
    guid: str,
    include_deleted: bool = Query(
        default=False,
        description="Include soft-deleted event",
    ),
    event_service: EventService = Depends(get_event_service),
) -> EventDetailResponse:
    """
    Get event details by GUID.

    Path Parameters:
        guid: Event GUID (evt_xxx format)

    Query Parameters:
        include_deleted: Include soft-deleted event

    Returns:
        Full event details including related entities

    Raises:
        404: Event not found

    Example:
        GET /api/events/evt_01hgw2bbg0000000000000001

        Response:
        {
          "guid": "evt_01hgw2bbg0000000000000001",
          "title": "Oshkosh Airshow 2026",
          "description": "Annual EAA AirVenture",
          "event_date": "2026-07-27",
          ...
        }
    """
    try:
        event = event_service.get_by_guid(guid, include_deleted=include_deleted)

        logger.info(f"Retrieved event: {guid}")

        return EventDetailResponse(
            **event_service.build_event_detail_response(event)
        )

    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {guid} not found",
        )

    except Exception as e:
        logger.error(f"Error getting event {guid}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve event",
        )


# ============================================================================
# Create Endpoints (Phase 5)
# ============================================================================


@router.post(
    "",
    response_model=EventDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new event",
    description="Create a new standalone event",
)
async def create_event(
    event_data: EventCreate,
    event_service: EventService = Depends(get_event_service),
) -> EventDetailResponse:
    """
    Create a new standalone event.

    Request Body:
        title: Event title (required)
        category_guid: Category GUID (required)
        event_date: Date of the event (required)
        description: Event description
        location_guid: Location GUID
        organizer_guid: Organizer GUID
        start_time: Start time (HH:MM)
        end_time: End time (HH:MM)
        is_all_day: Whether event spans full day
        input_timezone: IANA timezone
        status: Event status
        attendance: Attendance status
        ticket_required: Whether ticket is needed
        timeoff_required: Whether time-off is needed
        travel_required: Whether travel is needed
        deadline_date: Workflow deadline

    Returns:
        Created event details (201 Created)

    Raises:
        400: Invalid data (missing fields, invalid GUIDs)
        422: Validation error

    Example:
        POST /api/events
        {
          "title": "Airshow Day 1",
          "category_guid": "cat_xxx",
          "event_date": "2026-03-15",
          "start_time": "09:00",
          "end_time": "17:00"
        }
    """
    try:
        event = event_service.create(
            title=event_data.title,
            category_guid=event_data.category_guid,
            event_date=event_data.event_date,
            description=event_data.description,
            location_guid=event_data.location_guid,
            organizer_guid=event_data.organizer_guid,
            start_time=event_data.start_time,
            end_time=event_data.end_time,
            is_all_day=event_data.is_all_day,
            input_timezone=event_data.input_timezone,
            status=event_data.status.value,
            attendance=event_data.attendance.value,
            ticket_required=event_data.ticket_required,
            timeoff_required=event_data.timeoff_required,
            travel_required=event_data.travel_required,
            deadline_date=event_data.deadline_date,
            deadline_time=event_data.deadline_time,
        )

        # Reload with relationships
        event = event_service.get_by_guid(event.guid)

        logger.info(f"Created event: {event.guid}")

        return EventDetailResponse(
            **event_service.build_event_detail_response(event)
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error creating event: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create event",
        )


@router.post(
    "/series",
    response_model=List[EventResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create an event series",
    description="Create a multi-day event series with individual events",
)
async def create_event_series(
    series_data: EventSeriesCreate,
    event_service: EventService = Depends(get_event_service),
) -> List[EventResponse]:
    """
    Create a multi-day event series.

    Creates an EventSeries and individual Event records for each date.
    Events inherit properties from the series unless overridden.

    Request Body:
        title: Series title (required)
        category_guid: Category GUID (required)
        event_dates: List of dates - minimum 2 (required)
        description: Series description
        location_guid: Default location GUID
        organizer_guid: Default organizer GUID
        start_time: Default start time
        end_time: Default end time
        is_all_day: Whether events span full day
        input_timezone: IANA timezone
        ticket_required: Default ticket requirement
        timeoff_required: Default time-off requirement
        travel_required: Default travel requirement

    Returns:
        List of created events (201 Created)

    Raises:
        400: Invalid data (less than 2 dates, invalid GUIDs)
        422: Validation error

    Example:
        POST /api/events/series
        {
          "title": "Oshkosh Airshow 2026",
          "category_guid": "cat_xxx",
          "event_dates": ["2026-07-27", "2026-07-28", "2026-07-29"],
          "start_time": "08:00",
          "end_time": "18:00",
          "ticket_required": true
        }
    """
    try:
        series = event_service.create_series(
            title=series_data.title,
            category_guid=series_data.category_guid,
            event_dates=series_data.event_dates,
            description=series_data.description,
            location_guid=series_data.location_guid,
            organizer_guid=series_data.organizer_guid,
            start_time=series_data.start_time,
            end_time=series_data.end_time,
            is_all_day=series_data.is_all_day,
            input_timezone=series_data.input_timezone,
            ticket_required=series_data.ticket_required,
            timeoff_required=series_data.timeoff_required,
            travel_required=series_data.travel_required,
            deadline_date=series_data.deadline_date,
            deadline_time=series_data.deadline_time,
        )

        # Get all events in the series (including deadline entry if present)
        # Expand date range to include deadline_date if it's beyond the event dates
        end_date = max(series_data.event_dates)
        if series_data.deadline_date and series_data.deadline_date > end_date:
            end_date = series_data.deadline_date

        events = event_service.list(
            start_date=min(series_data.event_dates),
            end_date=end_date,
        )

        # Filter to just this series
        series_events = [e for e in events if e.series_id == series.id]

        logger.info(f"Created event series: {series.guid} ({len(series_events)} events)")

        return [
            EventResponse(**event_service.build_event_response(e))
            for e in series_events
        ]

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error creating event series: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create event series",
        )


@router.get(
    "/series/{guid}",
    response_model=EventSeriesResponse,
    summary="Get event series by GUID",
    description="Get detailed information about an event series",
)
async def get_event_series(
    guid: str,
    event_service: EventService = Depends(get_event_service),
) -> EventSeriesResponse:
    """
    Get event series details by GUID.

    Path Parameters:
        guid: Series GUID (ser_xxx format)

    Returns:
        Full series details including events

    Raises:
        404: Series not found
    """
    try:
        series = event_service.get_series_by_guid(guid)

        logger.info(f"Retrieved event series: {guid}")

        return EventSeriesResponse(**event_service.build_series_response(series))

    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event series {guid} not found",
        )

    except Exception as e:
        logger.error(f"Error getting event series {guid}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve event series",
        )


@router.patch(
    "/series/{guid}",
    response_model=EventSeriesResponse,
    summary="Update an event series",
    description="Update series-level properties (deadline changes sync automatically)",
)
async def update_event_series(
    guid: str,
    series_data: EventSeriesUpdate,
    event_service: EventService = Depends(get_event_service),
) -> EventSeriesResponse:
    """
    Update an event series.

    Updates series-level properties. Changes to deadline_date/deadline_time
    will automatically create, update, or delete the deadline calendar entry.

    Path Parameters:
        guid: Series GUID (ser_xxx format)

    Request Body:
        Any series field to update (all optional)

    Returns:
        Updated series details

    Raises:
        400: Invalid data
        404: Series not found

    Example:
        PATCH /api/events/series/ser_xxx
        {
          "deadline_date": "2026-08-15",
          "deadline_time": "23:59"
        }
    """
    try:
        updates = series_data.model_dump(exclude_unset=True)

        series = event_service.update_series(guid=guid, **updates)

        logger.info(f"Updated event series: {guid}")

        return EventSeriesResponse(**event_service.build_series_response(series))

    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event series {guid} not found",
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error updating event series {guid}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update event series",
        )


# ============================================================================
# Update Endpoints (Phase 5)
# ============================================================================


@router.patch(
    "/{guid}",
    response_model=EventDetailResponse,
    summary="Update an event",
    description="Update an existing event (with scope for series events)",
)
async def update_event(
    guid: str,
    event_data: EventUpdate,
    event_service: EventService = Depends(get_event_service),
) -> EventDetailResponse:
    """
    Update an existing event.

    For series events, use the `scope` field to control update behavior:
    - "single": Only update this event (default)
    - "this_and_future": Update this and all future events in series
    - "all": Update all events in series

    Path Parameters:
        guid: Event GUID (evt_xxx format)

    Request Body:
        Any event field to update (all optional)
        scope: Update scope for series events

    Returns:
        Updated event details

    Raises:
        400: Invalid data
        403: Cannot modify deadline entry directly
        404: Event not found
        422: Validation error

    Example:
        PATCH /api/events/evt_xxx
        {
          "attendance": "attended",
          "ticket_status": "ready"
        }

        PATCH /api/events/evt_xxx (series event)
        {
          "start_time": "10:00",
          "scope": "all"
        }
    """
    try:
        # Check if this is a protected deadline entry
        event = event_service.get_by_guid(guid)
        if event.is_deadline:
            # Get parent reference for helpful error message
            series_guid = event.series.guid if event.series else None
            parent_event_guid = event.parent_event.guid if event.parent_event else None
            raise DeadlineProtectionError(
                event_guid=guid,
                series_guid=series_guid,
                parent_event_guid=parent_event_guid
            )

        # Build update dict from non-None fields, excluding scope
        updates = event_data.model_dump(exclude_unset=True, exclude={"scope"})

        event = event_service.update(
            guid=guid,
            scope=event_data.scope.value,
            **updates
        )

        # Reload with relationships
        event = event_service.get_by_guid(event.guid)

        logger.info(f"Updated event: {guid}")

        return EventDetailResponse(
            **event_service.build_event_detail_response(event)
        )

    except DeadlineProtectionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": e.message,
                "series_guid": e.series_guid,
                "parent_event_guid": e.parent_event_guid,
            },
        )

    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {guid} not found",
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error updating event {guid}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update event",
        )


# ============================================================================
# Delete Endpoints (Phase 5)
# ============================================================================


@router.delete(
    "/{guid}",
    response_model=EventDetailResponse,
    summary="Delete an event",
    description="Soft delete an event (with scope for series events)",
)
async def delete_event(
    guid: str,
    scope: UpdateScope = Query(
        default=UpdateScope.SINGLE,
        description="Delete scope for series events",
    ),
    event_service: EventService = Depends(get_event_service),
) -> EventDetailResponse:
    """
    Soft delete an event.

    For series events, use the `scope` query parameter to control deletion:
    - "single": Only delete this event (default)
    - "this_and_future": Delete this and all future events in series
    - "all": Delete all events in series

    Path Parameters:
        guid: Event GUID (evt_xxx format)

    Query Parameters:
        scope: Delete scope for series events

    Returns:
        Deleted event details (with deleted_at timestamp)

    Raises:
        403: Cannot delete deadline entry directly
        404: Event not found

    Example:
        DELETE /api/events/evt_xxx
        DELETE /api/events/evt_xxx?scope=all
    """
    try:
        # Check if this is a protected deadline entry
        event = event_service.get_by_guid(guid)
        if event.is_deadline:
            # Get parent reference for helpful error message
            series_guid = event.series.guid if event.series else None
            parent_event_guid = event.parent_event.guid if event.parent_event else None
            raise DeadlineProtectionError(
                event_guid=guid,
                series_guid=series_guid,
                parent_event_guid=parent_event_guid
            )

        event = event_service.soft_delete(
            guid=guid,
            scope=scope.value,
        )

        # Reload with relationships
        event = event_service.get_by_guid(event.guid, include_deleted=True)

        logger.info(f"Deleted event: {guid} (scope: {scope.value})")

        return EventDetailResponse(
            **event_service.build_event_detail_response(event)
        )

    except DeadlineProtectionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": e.message,
                "series_guid": e.series_guid,
                "parent_event_guid": e.parent_event_guid,
            },
        )

    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {guid} not found",
        )

    except Exception as e:
        logger.error(f"Error deleting event {guid}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete event",
        )


@router.post(
    "/{guid}/restore",
    response_model=EventDetailResponse,
    summary="Restore a deleted event",
    description="Restore a soft-deleted event",
)
async def restore_event(
    guid: str,
    event_service: EventService = Depends(get_event_service),
) -> EventDetailResponse:
    """
    Restore a soft-deleted event.

    Path Parameters:
        guid: Event GUID (evt_xxx format)

    Returns:
        Restored event details (with deleted_at = null)

    Raises:
        404: Event not found

    Example:
        POST /api/events/evt_xxx/restore
    """
    try:
        event = event_service.restore(guid=guid)

        # Reload with relationships
        event = event_service.get_by_guid(event.guid)

        logger.info(f"Restored event: {guid}")

        return EventDetailResponse(
            **event_service.build_event_detail_response(event)
        )

    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {guid} not found",
        )

    except Exception as e:
        logger.error(f"Error restoring event {guid}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore event",
        )


# ============================================================================
# Event Performer Management Endpoints (T115)
# ============================================================================


def _build_event_performer_response(
    event_performer,
    performer_service_build_fn=None
) -> dict:
    """Build response dict for an EventPerformer."""
    performer = event_performer.performer
    return {
        "performer": {
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
        },
        "status": event_performer.status,
        "added_at": event_performer.created_at,
    }


@router.get(
    "/{guid}/performers",
    response_model=EventPerformersListResponse,
    summary="List event performers",
    description="Get all performers associated with an event",
)
async def list_event_performers(
    guid: str,
    event_service: EventService = Depends(get_event_service),
) -> EventPerformersListResponse:
    """
    Get all performers for an event.

    Path Parameters:
        guid: Event GUID (evt_xxx format)

    Returns:
        EventPerformersListResponse with performers and count

    Example:
        GET /api/events/evt_xxx/performers
    """
    try:
        event_performers = event_service.list_event_performers(guid)

        items = [
            EventPerformerResponse(**_build_event_performer_response(ep))
            for ep in event_performers
        ]

        return EventPerformersListResponse(items=items, total=len(items))

    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {guid} not found",
        )


@router.post(
    "/{guid}/performers",
    response_model=EventPerformerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add performer to event",
    description="Add a performer to an event",
)
async def add_performer_to_event(
    guid: str,
    performer_data: EventPerformerCreate,
    event_service: EventService = Depends(get_event_service),
) -> EventPerformerResponse:
    """
    Add a performer to an event.

    Validates that the performer's category matches the event's category.

    Path Parameters:
        guid: Event GUID (evt_xxx format)

    Request Body:
        EventPerformerCreate with performer_guid and optional status

    Returns:
        EventPerformerResponse with the new association

    Raises:
        400: Category mismatch
        404: Event or performer not found
        409: Performer already added

    Example:
        POST /api/events/evt_xxx/performers
        {"performer_guid": "prf_xxx", "status": "confirmed"}
    """
    try:
        event_performer = event_service.add_performer_to_event(
            event_guid=guid,
            performer_guid=performer_data.performer_guid,
            status=performer_data.status,
        )

        logger.info(
            f"Added performer to event",
            extra={"event_guid": guid, "performer_guid": performer_data.performer_guid}
        )

        return EventPerformerResponse(**_build_event_performer_response(event_performer))

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.patch(
    "/{guid}/performers/{performer_guid}",
    response_model=EventPerformerResponse,
    summary="Update performer status",
    description="Update a performer's status on an event",
)
async def update_event_performer(
    guid: str,
    performer_guid: str,
    update_data: EventPerformerUpdate,
    event_service: EventService = Depends(get_event_service),
) -> EventPerformerResponse:
    """
    Update a performer's status on an event.

    Path Parameters:
        guid: Event GUID (evt_xxx format)
        performer_guid: Performer GUID (prf_xxx format)

    Request Body:
        EventPerformerUpdate with new status

    Returns:
        Updated EventPerformerResponse

    Example:
        PATCH /api/events/evt_xxx/performers/prf_xxx
        {"status": "cancelled"}
    """
    try:
        event_performer = event_service.update_performer_status(
            event_guid=guid,
            performer_guid=performer_guid,
            status=update_data.status,
        )

        logger.info(
            f"Updated performer status on event",
            extra={"event_guid": guid, "performer_guid": performer_guid}
        )

        return EventPerformerResponse(**_build_event_performer_response(event_performer))

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete(
    "/{guid}/performers/{performer_guid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove performer from event",
    description="Remove a performer from an event",
)
async def remove_performer_from_event(
    guid: str,
    performer_guid: str,
    event_service: EventService = Depends(get_event_service),
) -> None:
    """
    Remove a performer from an event.

    Path Parameters:
        guid: Event GUID (evt_xxx format)
        performer_guid: Performer GUID (prf_xxx format)

    Returns:
        204 No Content on success

    Example:
        DELETE /api/events/evt_xxx/performers/prf_xxx
    """
    try:
        event_service.remove_performer_from_event(
            event_guid=guid,
            performer_guid=performer_guid,
        )

        logger.info(
            f"Removed performer from event",
            extra={"event_guid": guid, "performer_guid": performer_guid}
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
