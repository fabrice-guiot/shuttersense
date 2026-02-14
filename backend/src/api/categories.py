"""
Categories API endpoints for managing event categories.

Provides CRUD operations for event categories:
- List categories with filtering
- Create new categories
- Get category details
- Update category properties
- Delete categories (protected against referenced entities)
- Reorder categories for display

Design:
- Uses dependency injection for services
- Comprehensive error handling with meaningful HTTP status codes
- All endpoints use GUID format (cat_xxx) for identifiers
- Categories cannot be deleted if referenced by events/entities

Issue #39 - Calendar Events feature
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.middleware.auth import require_auth, TenantContext
from backend.src.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryReorderRequest,
    CategorySeedResponse,
    CategoryStatsResponse,
)
from backend.src.services.category_service import CategoryService
from backend.src.services.seed_data_service import SeedDataService
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError
from backend.src.utils.logging_config import get_logger


logger = get_logger("api")

router = APIRouter(
    prefix="/categories",
    tags=["Categories"],
)


# ============================================================================
# Dependencies
# ============================================================================


def get_category_service(db: Session = Depends(get_db)) -> CategoryService:
    """Create CategoryService instance with database session."""
    return CategoryService(db=db)


def get_seed_data_service(db: Session = Depends(get_db)) -> SeedDataService:
    """Create SeedDataService instance with database session."""
    return SeedDataService(db=db)


# ============================================================================
# API Endpoints
# ============================================================================


@router.get(
    "/stats",
    response_model=CategoryStatsResponse,
    summary="Get category statistics",
    description="Get aggregated statistics for all categories",
)
async def get_category_stats(
    ctx: TenantContext = Depends(require_auth),
    category_service: CategoryService = Depends(get_category_service),
) -> CategoryStatsResponse:
    """
    Get aggregated statistics for all categories.

    Returns:
        CategoryStatsResponse with:
        - total_count: Count of all categories
        - active_count: Count of active categories
        - inactive_count: Count of inactive categories

    Example:
        GET /api/categories/stats

        Response:
        {
          "total_count": 7,
          "active_count": 6,
          "inactive_count": 1
        }
    """
    try:
        stats = category_service.get_stats(team_id=ctx.team_id)

        logger.info(
            "Retrieved category stats",
            extra={"total_count": stats["total_count"]},
        )

        return CategoryStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting category stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        )


@router.post(
    "/seed-defaults",
    response_model=CategorySeedResponse,
    summary="Seed default categories",
    description="Restore missing default categories. Existing categories are not affected.",
)
async def seed_default_categories(
    ctx: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db),
    seed_service: SeedDataService = Depends(get_seed_data_service),
    category_service: CategoryService = Depends(get_category_service),
) -> CategorySeedResponse:
    """
    Seed default categories for the current team.

    Idempotent: only creates categories whose names don't already exist.
    Existing categories are never modified or deleted.

    Returns:
        CategorySeedResponse with count of created categories and full list

    Example:
        POST /api/categories/seed-defaults

        Response:
        {
          "categories_created": 3,
          "categories": [...]
        }
    """
    try:
        categories_created = seed_service.seed_categories(team_id=ctx.team_id, user_id=ctx.user_id)
        if categories_created > 0:
            db.commit()

        # Return the full updated list
        categories = category_service.list(team_id=ctx.team_id)

        logger.info(
            f"Seeded {categories_created} default categories",
            extra={"categories_created": categories_created},
        )

        return CategorySeedResponse(
            categories_created=categories_created,
            categories=[CategoryResponse.model_validate(c) for c in categories],
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding default categories: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        )


@router.get(
    "",
    response_model=List[CategoryResponse],
    summary="List categories",
    description="List all categories with optional filtering by active status",
)
async def list_categories(
    ctx: TenantContext = Depends(require_auth),
    is_active: Optional[bool] = Query(
        None, description="Filter by active status (true/false)"
    ),
    category_service: CategoryService = Depends(get_category_service),
) -> List[CategoryResponse]:
    """
    List all categories with optional filtering.

    Query Parameters:
        is_active: Filter by active status (optional)

    Returns:
        List of CategoryResponse objects ordered by display_order

    Example:
        GET /api/categories
        GET /api/categories?is_active=true
    """
    try:
        # Only filter by active if explicitly set
        active_only = is_active if is_active is True else False
        categories = category_service.list(team_id=ctx.team_id, active_only=active_only)

        logger.info(
            f"Listed {len(categories)} categories",
            extra={"is_active_filter": is_active, "count": len(categories)},
        )

        return [CategoryResponse.model_validate(c) for c in categories]

    except Exception as e:
        logger.error(f"Error listing categories: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        )


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create category",
    description="Create a new event category",
)
async def create_category(
    category: CategoryCreate,
    ctx: TenantContext = Depends(require_auth),
    category_service: CategoryService = Depends(get_category_service),
) -> CategoryResponse:
    """
    Create a new category.

    Request Body:
        CategoryCreate schema with name (required), icon, color, is_active

    Returns:
        CategoryResponse with created category details

    Raises:
        400 Bad Request: If validation fails (e.g., invalid color format)
        409 Conflict: If category name already exists

    Example:
        POST /api/categories
        {
          "name": "Airshow",
          "icon": "plane",
          "color": "#3B82F6",
          "is_active": true
        }
    """
    try:
        created_category = category_service.create(
            name=category.name,
            team_id=ctx.team_id,
            user_id=ctx.user_id,
            icon=category.icon,
            color=category.color,
            is_active=category.is_active,
            display_order=category.display_order,
        )

        logger.info(
            f"Created category: {category.name}",
            extra={"guid": created_category.guid},
        )

        return CategoryResponse.model_validate(created_category)

    except ConflictError as e:
        logger.warning(f"Category name conflict: {category.name}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    except ValidationError as e:
        logger.warning(f"Category validation failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(f"Error creating category: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        )


@router.get(
    "/{guid}",
    response_model=CategoryResponse,
    summary="Get category",
    description="Get a single category by GUID (e.g., cat_01hgw...)",
)
async def get_category(
    guid: str,
    ctx: TenantContext = Depends(require_auth),
    category_service: CategoryService = Depends(get_category_service),
) -> CategoryResponse:
    """
    Get category by GUID.

    Path Parameters:
        guid: Category GUID (cat_xxx format)

    Returns:
        CategoryResponse with category details

    Raises:
        404 Not Found: If category doesn't exist

    Example:
        GET /api/categories/cat_01hgw2bbg0000000000000001
    """
    try:
        category = category_service.get_by_guid(guid, team_id=ctx.team_id)

        logger.info(
            f"Retrieved category: {category.name}",
            extra={"guid": guid},
        )

        return CategoryResponse.model_validate(category)

    except NotFoundError:
        logger.warning(f"Category not found: {guid}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category not found: {guid}",
        )


@router.patch(
    "/{guid}",
    response_model=CategoryResponse,
    summary="Update category",
    description="Update category properties",
)
async def update_category(
    guid: str,
    category_update: CategoryUpdate,
    ctx: TenantContext = Depends(require_auth),
    category_service: CategoryService = Depends(get_category_service),
) -> CategoryResponse:
    """
    Update category properties by GUID.

    Only provided fields will be updated.

    Path Parameters:
        guid: Category GUID (cat_xxx format)

    Request Body:
        CategoryUpdate schema with optional fields

    Returns:
        CategoryResponse with updated category

    Raises:
        400 Bad Request: If validation fails
        404 Not Found: If category doesn't exist
        409 Conflict: If name conflicts with existing category

    Example:
        PATCH /api/categories/cat_01hgw2bbg0000000000000001
        {
          "name": "Aviation Events",
          "color": "#1E40AF"
        }
    """
    try:
        updated_category = category_service.update(
            guid=guid,
            team_id=ctx.team_id,
            user_id=ctx.user_id,
            name=category_update.name,
            icon=category_update.icon,
            color=category_update.color,
            is_active=category_update.is_active,
        )

        logger.info(
            f"Updated category: {updated_category.name}",
            extra={"guid": guid},
        )

        return CategoryResponse.model_validate(updated_category)

    except NotFoundError:
        logger.warning(f"Category not found for update: {guid}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category not found: {guid}",
        )

    except ConflictError as e:
        logger.warning(f"Category name conflict during update: {category_update.name}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    except ValidationError as e:
        logger.warning(f"Category update validation failed: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    except Exception as e:
        logger.error(f"Error updating category: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        )


@router.delete(
    "/{guid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete category",
    description="Delete category (protected: cannot delete if referenced by entities)",
)
async def delete_category(
    guid: str,
    ctx: TenantContext = Depends(require_auth),
    category_service: CategoryService = Depends(get_category_service),
) -> None:
    """
    Delete category by GUID.

    PROTECTED OPERATION: Cannot delete if events, locations, organizers,
    or performers reference this category.

    Path Parameters:
        guid: Category GUID (cat_xxx format)

    Returns:
        204 No Content on success

    Raises:
        404 Not Found: If category doesn't exist
        409 Conflict: If category is referenced by other entities

    Example:
        DELETE /api/categories/cat_01hgw2bbg0000000000000001

        Success: 204 No Content
        Error (has events): 409 Conflict with message:
        "Cannot delete category 'Airshow': 5 event(s) are using it"
    """
    try:
        category_service.delete(guid, team_id=ctx.team_id)

        logger.info(f"Deleted category", extra={"guid": guid})

    except NotFoundError:
        logger.warning(f"Category not found for deletion: {guid}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category not found: {guid}",
        )

    except ConflictError as e:
        logger.warning(f"Cannot delete category with references: {guid}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error deleting category: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        )


@router.post(
    "/reorder",
    response_model=List[CategoryResponse],
    summary="Reorder categories",
    description="Update display order of categories",
)
async def reorder_categories(
    reorder_request: CategoryReorderRequest,
    ctx: TenantContext = Depends(require_auth),
    category_service: CategoryService = Depends(get_category_service),
) -> List[CategoryResponse]:
    """
    Reorder categories based on provided GUID list.

    Updates display_order for all provided categories to match
    their position in the list.

    Request Body:
        CategoryReorderRequest with ordered_guids list

    Returns:
        List of CategoryResponse with updated display_order

    Raises:
        404 Not Found: If any GUID is not found

    Example:
        POST /api/categories/reorder
        {
          "ordered_guids": [
            "cat_01hgw2bbg0000000000000003",
            "cat_01hgw2bbg0000000000000001",
            "cat_01hgw2bbg0000000000000002"
          ]
        }
    """
    try:
        categories = category_service.reorder(reorder_request.ordered_guids, team_id=ctx.team_id)

        logger.info(f"Reordered {len(categories)} categories")

        return [CategoryResponse.model_validate(c) for c in categories]

    except NotFoundError as e:
        logger.warning(f"Category not found during reorder: {e.identifier}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error reordering categories: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred",
        )
