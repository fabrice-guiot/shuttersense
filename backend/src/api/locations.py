"""
Locations API endpoints for managing event locations.

Provides CRUD operations for event locations:
- List locations with filtering
- Create new locations
- Get location details
- Update location properties
- Delete locations (protected against referenced events)
- Geocode addresses to coordinates and timezone
- Get locations by category (for event creation)

Design:
- Uses dependency injection for services
- Comprehensive error handling with meaningful HTTP status codes
- All endpoints use GUID format (loc_xxx) for identifiers
- Locations cannot be deleted if referenced by events
- Category matching ensures location compatibility with events

Issue #39 - Calendar Events feature (Phase 8)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.schemas.location import (
    LocationCreate,
    LocationUpdate,
    LocationResponse,
    LocationListResponse,
    LocationStatsResponse,
    GeocodeRequest,
    GeocodeResponse,
)
from backend.src.services.location_service import LocationService
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError
from backend.src.utils.logging_config import get_logger


logger = get_logger("api")

router = APIRouter(
    prefix="/locations",
    tags=["Locations"],
)


# ============================================================================
# Dependencies
# ============================================================================


def get_location_service(db: Session = Depends(get_db)) -> LocationService:
    """Create LocationService instance with database session."""
    return LocationService(db=db)


# ============================================================================
# API Endpoints
# ============================================================================


@router.get(
    "/stats",
    response_model=LocationStatsResponse,
    summary="Get location statistics",
    description="Get aggregated statistics for all locations",
)
async def get_location_stats(
    location_service: LocationService = Depends(get_location_service),
) -> LocationStatsResponse:
    """
    Get aggregated statistics for all locations.

    Returns:
        LocationStatsResponse with:
        - total_count: Count of all locations
        - known_count: Count of saved "known" locations
        - with_coordinates_count: Count of geocoded locations

    Example:
        GET /api/locations/stats

        Response:
        {
          "total_count": 25,
          "known_count": 20,
          "with_coordinates_count": 18
        }
    """
    try:
        stats = location_service.get_stats()

        logger.info(
            "Retrieved location stats",
            extra={"total_count": stats["total_count"]},
        )

        return LocationStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting location stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get location statistics: {str(e)}",
        )


@router.get(
    "/by-category/{category_guid}",
    response_model=List[LocationResponse],
    summary="Get locations by category",
    description="Get all locations for a specific category (for event assignment)",
)
async def get_locations_by_category(
    category_guid: str,
    known_only: bool = Query(
        True, description="Only return saved 'known' locations"
    ),
    location_service: LocationService = Depends(get_location_service),
) -> List[LocationResponse]:
    """
    Get locations filtered by category.

    Used when creating/editing events to show only compatible locations
    (locations whose category matches the event's category).

    Path Parameters:
        category_guid: Category GUID (cat_xxx format)

    Query Parameters:
        known_only: If True, only return saved locations (default: True)

    Returns:
        List of LocationResponse objects

    Raises:
        404 Not Found: If category doesn't exist

    Example:
        GET /api/locations/by-category/cat_01hgw2bbg0000000000000001
    """
    try:
        locations = location_service.get_by_category(
            category_guid=category_guid,
            known_only=known_only,
        )

        logger.info(
            f"Listed {len(locations)} locations for category",
            extra={"category_guid": category_guid, "count": len(locations)},
        )

        return [LocationResponse.model_validate(loc) for loc in locations]

    except NotFoundError:
        logger.warning(f"Category not found: {category_guid}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category not found: {category_guid}",
        )

    except Exception as e:
        logger.error(f"Error listing locations by category: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list locations: {str(e)}",
        )


@router.post(
    "/geocode",
    response_model=GeocodeResponse,
    summary="Geocode address",
    description="Geocode an address to get coordinates and timezone",
)
async def geocode_address(
    request: GeocodeRequest,
    location_service: LocationService = Depends(get_location_service),
) -> GeocodeResponse:
    """
    Geocode an address string to coordinates and timezone.

    Request Body:
        GeocodeRequest with address field

    Returns:
        GeocodeResponse with coordinates, address components, and timezone

    Raises:
        400 Bad Request: If geocoding fails (address not found)

    Example:
        POST /api/locations/geocode
        {
          "address": "Madison Square Garden, New York, NY"
        }

        Response:
        {
          "latitude": 40.7505,
          "longitude": -73.9934,
          "address": "Madison Square Garden, 4 Pennsylvania Plaza, New York, NY 10001",
          "city": "New York",
          "state": "New York",
          "country": "United States",
          "postal_code": "10001",
          "timezone": "America/New_York"
        }
    """
    try:
        result = location_service.geocode_address(request.address)

        if result is None:
            logger.warning(f"Geocoding failed for address: {request.address[:50]}...")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not geocode the provided address. Please verify the address and try again.",
            )

        logger.info(
            f"Geocoded address successfully",
            extra={"address": request.address[:50]},
        )

        return GeocodeResponse(**result)

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error geocoding address: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to geocode address: {str(e)}",
        )


@router.get(
    "",
    response_model=LocationListResponse,
    summary="List locations",
    description="List all locations with optional filtering",
)
async def list_locations(
    category_guid: Optional[str] = Query(
        None, description="Filter by category GUID"
    ),
    known_only: bool = Query(
        False, description="Only return saved 'known' locations"
    ),
    search: Optional[str] = Query(
        None, description="Search in name, city, address, country"
    ),
    limit: int = Query(100, ge=1, le=500, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    location_service: LocationService = Depends(get_location_service),
) -> LocationListResponse:
    """
    List all locations with optional filtering.

    Query Parameters:
        category_guid: Filter by category GUID (optional)
        known_only: Only return known locations (default: False)
        search: Search term for name/city/address/country (optional)
        limit: Maximum number of results (default: 100, max: 500)
        offset: Number of results to skip (default: 0)

    Returns:
        LocationListResponse with items and total count

    Example:
        GET /api/locations
        GET /api/locations?known_only=true
        GET /api/locations?search=new+york
        GET /api/locations?category_guid=cat_01hgw2bbg0000000000000001
    """
    try:
        locations, total = location_service.list(
            category_guid=category_guid,
            known_only=known_only,
            search=search,
            limit=limit,
            offset=offset,
        )

        logger.info(
            f"Listed {len(locations)} locations",
            extra={
                "total": total,
                "category_filter": category_guid,
                "known_only": known_only,
                "search": search,
            },
        )

        return LocationListResponse(
            items=[LocationResponse.model_validate(loc) for loc in locations],
            total=total,
        )

    except NotFoundError as e:
        logger.warning(f"Category not found: {e.identifier}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error listing locations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list locations: {str(e)}",
        )


@router.post(
    "",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create location",
    description="Create a new event location",
)
async def create_location(
    location: LocationCreate,
    location_service: LocationService = Depends(get_location_service),
) -> LocationResponse:
    """
    Create a new location.

    Request Body:
        LocationCreate schema with name, category_guid (required), and optional fields

    Returns:
        LocationResponse with created location details

    Raises:
        400 Bad Request: If validation fails (e.g., inactive category, incomplete coordinates)
        404 Not Found: If category doesn't exist

    Example:
        POST /api/locations
        {
          "name": "Madison Square Garden",
          "category_guid": "cat_01hgw2bbg0000000000000001",
          "city": "New York",
          "country": "United States",
          "rating": 5,
          "is_known": true
        }
    """
    try:
        created_location = location_service.create(
            name=location.name,
            category_guid=location.category_guid,
            address=location.address,
            city=location.city,
            state=location.state,
            country=location.country,
            postal_code=location.postal_code,
            latitude=location.latitude,
            longitude=location.longitude,
            timezone=location.timezone,
            rating=location.rating,
            timeoff_required_default=location.timeoff_required_default,
            travel_required_default=location.travel_required_default,
            notes=location.notes,
            is_known=location.is_known,
        )

        logger.info(
            f"Created location: {location.name}",
            extra={"guid": created_location.guid},
        )

        return LocationResponse.model_validate(created_location)

    except NotFoundError as e:
        logger.warning(f"Category not found: {location.category_guid}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except ValidationError as e:
        logger.warning(f"Location validation failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(f"Error creating location: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create location: {str(e)}",
        )


@router.get(
    "/{guid}",
    response_model=LocationResponse,
    summary="Get location",
    description="Get a single location by GUID (e.g., loc_01hgw...)",
)
async def get_location(
    guid: str,
    location_service: LocationService = Depends(get_location_service),
) -> LocationResponse:
    """
    Get location by GUID.

    Path Parameters:
        guid: Location GUID (loc_xxx format)

    Returns:
        LocationResponse with location details

    Raises:
        404 Not Found: If location doesn't exist

    Example:
        GET /api/locations/loc_01hgw2bbg0000000000000001
    """
    try:
        location = location_service.get_by_guid(guid)

        logger.info(
            f"Retrieved location: {location.name}",
            extra={"guid": guid},
        )

        return LocationResponse.model_validate(location)

    except NotFoundError:
        logger.warning(f"Location not found: {guid}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location not found: {guid}",
        )


@router.patch(
    "/{guid}",
    response_model=LocationResponse,
    summary="Update location",
    description="Update location properties",
)
async def update_location(
    guid: str,
    location_update: LocationUpdate,
    location_service: LocationService = Depends(get_location_service),
) -> LocationResponse:
    """
    Update location properties by GUID.

    Only provided fields will be updated.

    Path Parameters:
        guid: Location GUID (loc_xxx format)

    Request Body:
        LocationUpdate schema with optional fields

    Returns:
        LocationResponse with updated location

    Raises:
        400 Bad Request: If validation fails
        404 Not Found: If location or category doesn't exist

    Example:
        PATCH /api/locations/loc_01hgw2bbg0000000000000001
        {
          "rating": 4,
          "notes": "Great venue, easy parking"
        }
    """
    try:
        updated_location = location_service.update(
            guid=guid,
            name=location_update.name,
            category_guid=location_update.category_guid,
            address=location_update.address,
            city=location_update.city,
            state=location_update.state,
            country=location_update.country,
            postal_code=location_update.postal_code,
            latitude=location_update.latitude,
            longitude=location_update.longitude,
            timezone=location_update.timezone,
            rating=location_update.rating,
            timeoff_required_default=location_update.timeoff_required_default,
            travel_required_default=location_update.travel_required_default,
            notes=location_update.notes,
            is_known=location_update.is_known,
        )

        logger.info(
            f"Updated location: {updated_location.name}",
            extra={"guid": guid},
        )

        return LocationResponse.model_validate(updated_location)

    except NotFoundError as e:
        logger.warning(f"Entity not found for update: {e.identifier}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except ValidationError as e:
        logger.warning(f"Location update validation failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(f"Error updating location: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update location: {str(e)}",
        )


@router.delete(
    "/{guid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete location",
    description="Delete location (protected: cannot delete if referenced by events)",
)
async def delete_location(
    guid: str,
    location_service: LocationService = Depends(get_location_service),
) -> None:
    """
    Delete location by GUID.

    PROTECTED OPERATION: Cannot delete if events or event series
    reference this location.

    Path Parameters:
        guid: Location GUID (loc_xxx format)

    Returns:
        204 No Content on success

    Raises:
        404 Not Found: If location doesn't exist
        409 Conflict: If location is referenced by events

    Example:
        DELETE /api/locations/loc_01hgw2bbg0000000000000001

        Success: 204 No Content
        Error (has events): 409 Conflict with message:
        "Cannot delete location 'Madison Square Garden': 5 event(s) are using it"
    """
    try:
        location_service.delete(guid)

        logger.info(f"Deleted location", extra={"guid": guid})

    except NotFoundError:
        logger.warning(f"Location not found for deletion: {guid}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location not found: {guid}",
        )

    except ConflictError as e:
        logger.warning(f"Cannot delete location with references: {guid}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error deleting location: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete location: {str(e)}",
        )


@router.get(
    "/{guid}/validate-category/{event_category_guid}",
    response_model=dict,
    summary="Validate location-event category match",
    description="Check if a location's category matches an event's category",
)
async def validate_category_match(
    guid: str,
    event_category_guid: str,
    location_service: LocationService = Depends(get_location_service),
) -> dict:
    """
    Validate that a location's category matches an event's category.

    This endpoint is used to verify compatibility when assigning a
    location to an event.

    Path Parameters:
        guid: Location GUID (loc_xxx format)
        event_category_guid: Event's category GUID (cat_xxx format)

    Returns:
        Dictionary with match result: {"matches": true/false}

    Raises:
        404 Not Found: If location doesn't exist

    Example:
        GET /api/locations/loc_01.../validate-category/cat_01...

        Response:
        {"matches": true}
    """
    try:
        matches = location_service.validate_category_match(
            location_guid=guid,
            event_category_guid=event_category_guid,
        )

        logger.info(
            f"Validated category match",
            extra={
                "location_guid": guid,
                "event_category_guid": event_category_guid,
                "matches": matches,
            },
        )

        return {"matches": matches}

    except NotFoundError:
        logger.warning(f"Location not found for category validation: {guid}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location not found: {guid}",
        )
