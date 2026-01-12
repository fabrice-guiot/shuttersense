"""
Organizers API endpoints for managing event organizers.

Provides CRUD operations for event organizers:
- List organizers with filtering
- Create new organizers
- Get organizer details
- Update organizer properties
- Delete organizers (protected against referenced events)
- Get organizers by category (for event creation)
- Validate category matching

Design:
- Uses dependency injection for services
- Comprehensive error handling with meaningful HTTP status codes
- All endpoints use GUID format (org_xxx) for identifiers
- Organizers cannot be deleted if referenced by events
- Category matching ensures organizer compatibility with events

Issue #39 - Calendar Events feature (Phase 9)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.schemas.organizer import (
    OrganizerCreate,
    OrganizerUpdate,
    OrganizerResponse,
    OrganizerListResponse,
    OrganizerStatsResponse,
)
from backend.src.services.organizer_service import OrganizerService
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError
from backend.src.utils.logging_config import get_logger


logger = get_logger("api")

router = APIRouter(
    prefix="/organizers",
    tags=["Organizers"],
)


# ============================================================================
# Dependencies
# ============================================================================


def get_organizer_service(db: Session = Depends(get_db)) -> OrganizerService:
    """Create OrganizerService instance with database session."""
    return OrganizerService(db=db)


# ============================================================================
# API Endpoints
# ============================================================================


@router.get(
    "/stats",
    response_model=OrganizerStatsResponse,
    summary="Get organizer statistics",
    description="Get aggregated statistics for all organizers",
)
async def get_organizer_stats(
    organizer_service: OrganizerService = Depends(get_organizer_service),
) -> OrganizerStatsResponse:
    """
    Get aggregated statistics for all organizers.

    Returns:
        OrganizerStatsResponse with:
        - total_count: Count of all organizers
        - with_rating_count: Count of organizers with ratings
        - avg_rating: Average rating across rated organizers

    Example:
        GET /api/organizers/stats

        Response:
        {
          "total_count": 15,
          "with_rating_count": 12,
          "avg_rating": 3.8
        }
    """
    try:
        stats = organizer_service.get_stats()

        logger.info(
            "Retrieved organizer stats",
            extra={"total_count": stats["total_count"]},
        )

        return OrganizerStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting organizer stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get organizer statistics: {str(e)}",
        )


@router.get(
    "/by-category/{category_guid}",
    response_model=List[OrganizerResponse],
    summary="Get organizers by category",
    description="Get all organizers for a specific category (for event assignment)",
)
async def get_organizers_by_category(
    category_guid: str,
    organizer_service: OrganizerService = Depends(get_organizer_service),
) -> List[OrganizerResponse]:
    """
    Get organizers filtered by category.

    Used when creating/editing events to show only compatible organizers
    (organizers whose category matches the event's category).

    Path Parameters:
        category_guid: Category GUID (cat_xxx format)

    Returns:
        List of OrganizerResponse objects

    Raises:
        404 Not Found: If category doesn't exist

    Example:
        GET /api/organizers/by-category/cat_01hgw2bbg0000000000000001
    """
    try:
        organizers = organizer_service.get_by_category(category_guid=category_guid)

        logger.info(
            f"Listed {len(organizers)} organizers for category",
            extra={"category_guid": category_guid, "count": len(organizers)},
        )

        return [OrganizerResponse.model_validate(org) for org in organizers]

    except NotFoundError:
        logger.warning(f"Category not found: {category_guid}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category not found: {category_guid}",
        )

    except Exception as e:
        logger.error(f"Error listing organizers by category: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list organizers: {str(e)}",
        )


@router.get(
    "",
    response_model=OrganizerListResponse,
    summary="List organizers",
    description="List all organizers with optional filtering",
)
async def list_organizers(
    category_guid: Optional[str] = Query(
        None, description="Filter by category GUID"
    ),
    search: Optional[str] = Query(
        None, description="Search in name, website, notes"
    ),
    limit: int = Query(100, ge=1, le=500, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    organizer_service: OrganizerService = Depends(get_organizer_service),
) -> OrganizerListResponse:
    """
    List all organizers with optional filtering.

    Query Parameters:
        category_guid: Filter by category GUID (optional)
        search: Search term for name/website/notes (optional)
        limit: Maximum number of results (default: 100, max: 500)
        offset: Number of results to skip (default: 0)

    Returns:
        OrganizerListResponse with items and total count

    Example:
        GET /api/organizers
        GET /api/organizers?search=live+nation
        GET /api/organizers?category_guid=cat_01hgw2bbg0000000000000001
    """
    try:
        organizers, total = organizer_service.list(
            category_guid=category_guid,
            search=search,
            limit=limit,
            offset=offset,
        )

        logger.info(
            f"Listed {len(organizers)} organizers",
            extra={
                "total": total,
                "category_filter": category_guid,
                "search": search,
            },
        )

        return OrganizerListResponse(
            items=[OrganizerResponse.model_validate(org) for org in organizers],
            total=total,
        )

    except NotFoundError as e:
        logger.warning(f"Category not found: {e.identifier}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error listing organizers: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list organizers: {str(e)}",
        )


@router.post(
    "",
    response_model=OrganizerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create organizer",
    description="Create a new event organizer",
)
async def create_organizer(
    organizer: OrganizerCreate,
    organizer_service: OrganizerService = Depends(get_organizer_service),
) -> OrganizerResponse:
    """
    Create a new organizer.

    Request Body:
        OrganizerCreate schema with name, category_guid (required), and optional fields

    Returns:
        OrganizerResponse with created organizer details

    Raises:
        400 Bad Request: If validation fails (e.g., inactive category, invalid rating)
        404 Not Found: If category doesn't exist

    Example:
        POST /api/organizers
        {
          "name": "Live Nation",
          "category_guid": "cat_01hgw2bbg0000000000000001",
          "website": "https://livenation.com",
          "rating": 4,
          "ticket_required_default": true
        }
    """
    try:
        created_organizer = organizer_service.create(
            name=organizer.name,
            category_guid=organizer.category_guid,
            website=organizer.website,
            rating=organizer.rating,
            ticket_required_default=organizer.ticket_required_default,
            notes=organizer.notes,
        )

        logger.info(
            f"Created organizer: {organizer.name}",
            extra={"guid": created_organizer.guid},
        )

        return OrganizerResponse.model_validate(created_organizer)

    except NotFoundError as e:
        logger.warning(f"Category not found: {organizer.category_guid}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except ValidationError as e:
        logger.warning(f"Organizer validation failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(f"Error creating organizer: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create organizer: {str(e)}",
        )


@router.get(
    "/{guid}",
    response_model=OrganizerResponse,
    summary="Get organizer",
    description="Get a single organizer by GUID (e.g., org_01hgw...)",
)
async def get_organizer(
    guid: str,
    organizer_service: OrganizerService = Depends(get_organizer_service),
) -> OrganizerResponse:
    """
    Get organizer by GUID.

    Path Parameters:
        guid: Organizer GUID (org_xxx format)

    Returns:
        OrganizerResponse with organizer details

    Raises:
        404 Not Found: If organizer doesn't exist

    Example:
        GET /api/organizers/org_01hgw2bbg0000000000000001
    """
    try:
        organizer = organizer_service.get_by_guid(guid)

        logger.info(
            f"Retrieved organizer: {organizer.name}",
            extra={"guid": guid},
        )

        return OrganizerResponse.model_validate(organizer)

    except NotFoundError:
        logger.warning(f"Organizer not found: {guid}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organizer not found: {guid}",
        )


@router.patch(
    "/{guid}",
    response_model=OrganizerResponse,
    summary="Update organizer",
    description="Update organizer properties",
)
async def update_organizer(
    guid: str,
    organizer_update: OrganizerUpdate,
    organizer_service: OrganizerService = Depends(get_organizer_service),
) -> OrganizerResponse:
    """
    Update organizer properties by GUID.

    Only provided fields will be updated.

    Path Parameters:
        guid: Organizer GUID (org_xxx format)

    Request Body:
        OrganizerUpdate schema with optional fields

    Returns:
        OrganizerResponse with updated organizer

    Raises:
        400 Bad Request: If validation fails
        404 Not Found: If organizer or category doesn't exist

    Example:
        PATCH /api/organizers/org_01hgw2bbg0000000000000001
        {
          "rating": 5,
          "notes": "Great organizer, always well-organized events"
        }
    """
    try:
        updated_organizer = organizer_service.update(
            guid=guid,
            name=organizer_update.name,
            category_guid=organizer_update.category_guid,
            website=organizer_update.website,
            rating=organizer_update.rating,
            ticket_required_default=organizer_update.ticket_required_default,
            notes=organizer_update.notes,
        )

        logger.info(
            f"Updated organizer: {updated_organizer.name}",
            extra={"guid": guid},
        )

        return OrganizerResponse.model_validate(updated_organizer)

    except NotFoundError as e:
        logger.warning(f"Entity not found for update: {e.identifier}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except ValidationError as e:
        logger.warning(f"Organizer update validation failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(f"Error updating organizer: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update organizer: {str(e)}",
        )


@router.delete(
    "/{guid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete organizer",
    description="Delete organizer (protected: cannot delete if referenced by events)",
)
async def delete_organizer(
    guid: str,
    organizer_service: OrganizerService = Depends(get_organizer_service),
) -> None:
    """
    Delete organizer by GUID.

    PROTECTED OPERATION: Cannot delete if events or event series
    reference this organizer.

    Path Parameters:
        guid: Organizer GUID (org_xxx format)

    Returns:
        204 No Content on success

    Raises:
        404 Not Found: If organizer doesn't exist
        409 Conflict: If organizer is referenced by events

    Example:
        DELETE /api/organizers/org_01hgw2bbg0000000000000001

        Success: 204 No Content
        Error (has events): 409 Conflict with message:
        "Cannot delete organizer 'Live Nation': 5 event(s) are using it"
    """
    try:
        organizer_service.delete(guid)

        logger.info(f"Deleted organizer", extra={"guid": guid})

    except NotFoundError:
        logger.warning(f"Organizer not found for deletion: {guid}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organizer not found: {guid}",
        )

    except ConflictError as e:
        logger.warning(f"Cannot delete organizer with references: {guid}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error deleting organizer: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete organizer: {str(e)}",
        )


@router.get(
    "/{guid}/validate-category/{event_category_guid}",
    response_model=dict,
    summary="Validate organizer-event category match",
    description="Check if an organizer's category matches an event's category",
)
async def validate_category_match(
    guid: str,
    event_category_guid: str,
    organizer_service: OrganizerService = Depends(get_organizer_service),
) -> dict:
    """
    Validate that an organizer's category matches an event's category.

    This endpoint is used to verify compatibility when assigning an
    organizer to an event.

    Path Parameters:
        guid: Organizer GUID (org_xxx format)
        event_category_guid: Event's category GUID (cat_xxx format)

    Returns:
        Dictionary with match result: {"matches": true/false}

    Raises:
        404 Not Found: If organizer doesn't exist

    Example:
        GET /api/organizers/org_01.../validate-category/cat_01...

        Response:
        {"matches": true}
    """
    try:
        matches = organizer_service.validate_category_match(
            organizer_guid=guid,
            event_category_guid=event_category_guid,
        )

        logger.info(
            f"Validated category match",
            extra={
                "organizer_guid": guid,
                "event_category_guid": event_category_guid,
                "matches": matches,
            },
        )

        return {"matches": matches}

    except NotFoundError:
        logger.warning(f"Organizer not found for category validation: {guid}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organizer not found: {guid}",
        )
