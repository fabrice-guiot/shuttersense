"""
Performers API endpoints for managing event performers.

Provides CRUD operations for event performers:
- List performers with filtering
- Create new performers
- Get performer details
- Update performer properties
- Delete performers (protected against event associations)
- Get performers by category (for event creation)
- Validate category matching

Design:
- Uses dependency injection for services
- Comprehensive error handling with meaningful HTTP status codes
- All endpoints use GUID format (prf_xxx) for identifiers
- Performers cannot be deleted if associated with events
- Category matching ensures performer compatibility with events

Issue #39 - Calendar Events feature (Phase 11)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.schemas.performer import (
    PerformerCreate,
    PerformerUpdate,
    PerformerResponse,
    PerformerListResponse,
    PerformerStatsResponse,
)
from backend.src.services.performer_service import PerformerService
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError
from backend.src.utils.logging_config import get_logger


logger = get_logger("api")

router = APIRouter(
    prefix="/performers",
    tags=["Performers"],
)


# ============================================================================
# Dependencies
# ============================================================================


def get_performer_service(db: Session = Depends(get_db)) -> PerformerService:
    """Create PerformerService instance with database session."""
    return PerformerService(db=db)


# ============================================================================
# API Endpoints
# ============================================================================


@router.get(
    "/stats",
    response_model=PerformerStatsResponse,
    summary="Get performer statistics",
    description="Get aggregated statistics for all performers",
)
async def get_performer_stats(
    performer_service: PerformerService = Depends(get_performer_service),
) -> PerformerStatsResponse:
    """
    Get aggregated statistics for all performers.

    Returns:
        PerformerStatsResponse with:
        - total_count: Count of all performers
        - with_instagram_count: Count of performers with Instagram handles
        - with_website_count: Count of performers with websites

    Example:
        GET /api/performers/stats

        Response:
        {
          "total_count": 25,
          "with_instagram_count": 18,
          "with_website_count": 15
        }
    """
    try:
        stats = performer_service.get_stats()

        logger.info(
            "Retrieved performer stats",
            extra={"total_count": stats["total_count"]},
        )

        return PerformerStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting performer stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get performer statistics: {str(e)}",
        )


@router.get(
    "/by-category/{category_guid}",
    response_model=List[PerformerResponse],
    summary="Get performers by category",
    description="Get all performers for a specific category (for event assignment)",
)
async def get_performers_by_category(
    category_guid: str,
    search: Optional[str] = Query(None, description="Search term for name"),
    performer_service: PerformerService = Depends(get_performer_service),
) -> List[PerformerResponse]:
    """
    Get performers filtered by category.

    Used when creating/editing events to show only compatible performers
    (performers whose category matches the event's category).

    Path Parameters:
        category_guid: Category GUID (cat_xxx format)

    Query Parameters:
        search: Optional search term for performer name

    Returns:
        List of PerformerResponse objects

    Raises:
        404 Not Found: If category doesn't exist

    Example:
        GET /api/performers/by-category/cat_01hgw2bbg0000000000000001
        GET /api/performers/by-category/cat_01hgw2bbg0000000000000001?search=blue
    """
    try:
        performers = performer_service.get_by_category(
            category_guid=category_guid,
            search=search,
        )

        logger.info(
            f"Listed {len(performers)} performers for category",
            extra={"category_guid": category_guid, "count": len(performers)},
        )

        return [
            PerformerResponse(**performer_service.build_performer_response(p))
            for p in performers
        ]

    except NotFoundError:
        logger.warning(f"Category not found: {category_guid}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category not found: {category_guid}",
        )

    except Exception as e:
        logger.error(f"Error listing performers by category: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list performers: {str(e)}",
        )


@router.get(
    "",
    response_model=PerformerListResponse,
    summary="List performers",
    description="List all performers with optional filtering",
)
async def list_performers(
    category_guid: Optional[str] = Query(
        None, description="Filter by category GUID"
    ),
    search: Optional[str] = Query(
        None, description="Search in name, instagram, additional_info"
    ),
    limit: int = Query(100, ge=1, le=500, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    performer_service: PerformerService = Depends(get_performer_service),
) -> PerformerListResponse:
    """
    List all performers with optional filtering.

    Query Parameters:
        category_guid: Filter by category GUID (optional)
        search: Search term for name/instagram/additional_info (optional)
        limit: Maximum number of results (default: 100, max: 500)
        offset: Number of results to skip (default: 0)

    Returns:
        PerformerListResponse with items and total count

    Example:
        GET /api/performers
        GET /api/performers?search=angels
        GET /api/performers?category_guid=cat_01hgw2bbg0000000000000001
    """
    try:
        performers, total = performer_service.list(
            category_guid=category_guid,
            search=search,
            limit=limit,
            offset=offset,
        )

        logger.info(
            f"Listed {len(performers)} performers",
            extra={
                "total": total,
                "category_filter": category_guid,
                "search": search,
            },
        )

        return PerformerListResponse(
            items=[
                PerformerResponse(**performer_service.build_performer_response(p))
                for p in performers
            ],
            total=total,
        )

    except NotFoundError as e:
        logger.warning(f"Category not found: {e.identifier}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error listing performers: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list performers: {str(e)}",
        )


@router.post(
    "",
    response_model=PerformerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create performer",
    description="Create a new event performer",
)
async def create_performer(
    performer: PerformerCreate,
    performer_service: PerformerService = Depends(get_performer_service),
) -> PerformerResponse:
    """
    Create a new performer.

    Request Body:
        PerformerCreate schema with name, category_guid (required), and optional fields

    Returns:
        PerformerResponse with created performer details

    Raises:
        400 Bad Request: If validation fails (e.g., inactive category)
        404 Not Found: If category doesn't exist

    Example:
        POST /api/performers
        {
          "name": "Blue Angels",
          "category_guid": "cat_01hgw2bbg0000000000000001",
          "website": "https://www.blueangels.navy.mil",
          "instagram_handle": "usaborngirl",
          "additional_info": "U.S. Navy flight demonstration squadron"
        }
    """
    try:
        created_performer = performer_service.create(
            name=performer.name,
            category_guid=performer.category_guid,
            website=performer.website,
            instagram_handle=performer.instagram_handle,
            additional_info=performer.additional_info,
        )

        logger.info(
            f"Created performer: {performer.name}",
            extra={"guid": created_performer.guid},
        )

        return PerformerResponse(
            **performer_service.build_performer_response(created_performer)
        )

    except NotFoundError as e:
        logger.warning(f"Category not found: {performer.category_guid}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except ValidationError as e:
        logger.warning(f"Performer validation failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(f"Error creating performer: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create performer: {str(e)}",
        )


@router.get(
    "/{guid}",
    response_model=PerformerResponse,
    summary="Get performer",
    description="Get a single performer by GUID (e.g., prf_01hgw...)",
)
async def get_performer(
    guid: str,
    performer_service: PerformerService = Depends(get_performer_service),
) -> PerformerResponse:
    """
    Get performer by GUID.

    Path Parameters:
        guid: Performer GUID (prf_xxx format)

    Returns:
        PerformerResponse with performer details

    Raises:
        404 Not Found: If performer doesn't exist

    Example:
        GET /api/performers/prf_01hgw2bbg0000000000000001
    """
    try:
        performer = performer_service.get_by_guid(guid)

        logger.info(
            f"Retrieved performer: {performer.name}",
            extra={"guid": guid},
        )

        return PerformerResponse(
            **performer_service.build_performer_response(performer)
        )

    except NotFoundError:
        logger.warning(f"Performer not found: {guid}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Performer not found: {guid}",
        )


@router.patch(
    "/{guid}",
    response_model=PerformerResponse,
    summary="Update performer",
    description="Update performer properties",
)
async def update_performer(
    guid: str,
    performer_update: PerformerUpdate,
    performer_service: PerformerService = Depends(get_performer_service),
) -> PerformerResponse:
    """
    Update performer properties by GUID.

    Only provided fields will be updated.

    Path Parameters:
        guid: Performer GUID (prf_xxx format)

    Request Body:
        PerformerUpdate schema with optional fields

    Returns:
        PerformerResponse with updated performer

    Raises:
        400 Bad Request: If validation fails
        404 Not Found: If performer or category doesn't exist

    Example:
        PATCH /api/performers/prf_01hgw2bbg0000000000000001
        {
          "instagram_handle": "newhandle",
          "additional_info": "Updated bio information"
        }
    """
    try:
        updated_performer = performer_service.update(
            guid=guid,
            name=performer_update.name,
            category_guid=performer_update.category_guid,
            website=performer_update.website,
            instagram_handle=performer_update.instagram_handle,
            additional_info=performer_update.additional_info,
        )

        logger.info(
            f"Updated performer: {updated_performer.name}",
            extra={"guid": guid},
        )

        return PerformerResponse(
            **performer_service.build_performer_response(updated_performer)
        )

    except NotFoundError as e:
        logger.warning(f"Entity not found for update: {e.identifier}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except ValidationError as e:
        logger.warning(f"Performer update validation failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(f"Error updating performer: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update performer: {str(e)}",
        )


@router.delete(
    "/{guid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete performer",
    description="Delete performer (protected: cannot delete if associated with events)",
)
async def delete_performer(
    guid: str,
    performer_service: PerformerService = Depends(get_performer_service),
) -> None:
    """
    Delete performer by GUID.

    PROTECTED OPERATION: Cannot delete if the performer is
    associated with any events.

    Path Parameters:
        guid: Performer GUID (prf_xxx format)

    Returns:
        204 No Content on success

    Raises:
        404 Not Found: If performer doesn't exist
        409 Conflict: If performer is associated with events

    Example:
        DELETE /api/performers/prf_01hgw2bbg0000000000000001

        Success: 204 No Content
        Error (has events): 409 Conflict with message:
        "Cannot delete performer 'Blue Angels': associated with 3 event(s)"
    """
    try:
        performer_service.delete(guid)

        logger.info(f"Deleted performer", extra={"guid": guid})

    except NotFoundError:
        logger.warning(f"Performer not found for deletion: {guid}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Performer not found: {guid}",
        )

    except ConflictError as e:
        logger.warning(f"Cannot delete performer with event associations: {guid}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error deleting performer: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete performer: {str(e)}",
        )


@router.get(
    "/{guid}/validate-category/{event_category_guid}",
    response_model=dict,
    summary="Validate performer-event category match",
    description="Check if a performer's category matches an event's category",
)
async def validate_category_match(
    guid: str,
    event_category_guid: str,
    performer_service: PerformerService = Depends(get_performer_service),
) -> dict:
    """
    Validate that a performer's category matches an event's category.

    This endpoint is used to verify compatibility when assigning a
    performer to an event.

    Path Parameters:
        guid: Performer GUID (prf_xxx format)
        event_category_guid: Event's category GUID (cat_xxx format)

    Returns:
        Dictionary with match result: {"matches": true/false}

    Raises:
        404 Not Found: If performer doesn't exist

    Example:
        GET /api/performers/prf_01.../validate-category/cat_01...

        Response:
        {"matches": true}
    """
    try:
        matches = performer_service.validate_category_match(
            performer_guid=guid,
            event_category_guid=event_category_guid,
        )

        logger.info(
            f"Validated category match",
            extra={
                "performer_guid": guid,
                "event_category_guid": event_category_guid,
                "matches": matches,
            },
        )

        return {"matches": matches}

    except NotFoundError:
        logger.warning(f"Performer not found for category validation: {guid}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Performer not found: {guid}",
        )
