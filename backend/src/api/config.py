"""
Configuration API endpoints for managing application settings.

Provides endpoints for:
- CRUD operations on configuration items
- YAML import with conflict detection and resolution
- YAML export for migration
- Statistics for dashboard KPIs

Design:
- Uses dependency injection for services
- Pydantic validation for request/response
- Session-based import workflow
- Rate limiting on import endpoints (T168)

Note: Route order matters! Specific routes (stats, export, import) must come
before parameterized routes (/{category}, /{category}/{key}).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, File, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.schemas.config import (
    ConfigItemCreate, ConfigItemUpdate, ConfigItemResponse,
    CategoryConfigResponse, ConfigurationResponse,
    ImportSessionResponse, ConflictResolutionRequest, ImportResultResponse,
    ConfigStatsResponse, DeleteResponse, ConfigConflict
)
from backend.src.services.config_service import ConfigService
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError
from backend.src.utils.logging_config import get_logger


logger = get_logger("api")

router = APIRouter(
    prefix="/config",
    tags=["Configuration"],
)

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)


# ============================================================================
# Dependencies
# ============================================================================

def get_config_service(db: Session = Depends(get_db)) -> ConfigService:
    """Create ConfigService instance with dependencies."""
    return ConfigService(db=db)


# ============================================================================
# Statistics Endpoint (must be before /{category})
# ============================================================================

@router.get(
    "/stats",
    response_model=ConfigStatsResponse,
    summary="Get configuration statistics"
)
def get_stats(
    service: ConfigService = Depends(get_config_service)
) -> ConfigStatsResponse:
    """
    Get aggregate statistics for configuration.

    Returns totals, category counts, and source breakdown for dashboard KPIs.

    Returns:
        Statistics including total items, cameras, methods, and source breakdown
    """
    return service.get_stats()


# ============================================================================
# Export Endpoint (must be before /{category})
# ============================================================================

@router.get(
    "/export",
    summary="Export configuration as YAML"
)
def export_config(
    service: ConfigService = Depends(get_config_service)
) -> Response:
    """
    Export all configuration as a YAML file.

    Returns:
        YAML file download
    """
    try:
        yaml_content = service.export_to_yaml()

        return Response(
            content=yaml_content,
            media_type="application/x-yaml",
            headers={
                "Content-Disposition": "attachment; filename=config.yaml"
            }
        )
    except Exception as e:
        logger.error(f"Error exporting config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export configuration: {str(e)}"
        )


# ============================================================================
# Import Endpoints (must be before /{category})
# ============================================================================

@router.post(
    "/import",
    response_model=ImportSessionResponse,
    summary="Start YAML import",
    responses={
        429: {"description": "Too many requests - rate limit exceeded"},
    }
)
@limiter.limit("5/minute")  # Rate limit: 5 imports per minute (T168)
async def start_import(
    request: Request,  # Required for rate limiter
    file: UploadFile = File(...),
    service: ConfigService = Depends(get_config_service)
) -> ImportSessionResponse:
    """
    Start a YAML import with conflict detection.

    Uploads a YAML configuration file and detects conflicts with existing
    configuration. Returns a session ID for resolving conflicts.

    Args:
        file: YAML configuration file

    Returns:
        Import session with conflicts
    """
    try:
        content = await file.read()
        yaml_content = content.decode("utf-8")

        session = service.start_import(yaml_content, filename=file.filename)

        return ImportSessionResponse(
            session_id=session["session_id"],
            status=session["status"],
            expires_at=session["expires_at"],
            file_name=session["file_name"],
            total_items=session["total_items"],
            new_items=session["new_items"],
            conflicts=[ConfigConflict(**c) for c in session["conflicts"]]
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error starting import: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start import: {str(e)}"
        )


@router.get(
    "/import/{session_id}",
    response_model=ImportSessionResponse,
    summary="Get import session"
)
def get_import_session(
    session_id: str,
    service: ConfigService = Depends(get_config_service)
) -> ImportSessionResponse:
    """
    Get import session status and conflicts.

    Args:
        session_id: Session UUID

    Returns:
        Import session details
    """
    try:
        session = service.get_import_session(session_id)

        return ImportSessionResponse(
            session_id=session["session_id"],
            status=session["status"],
            expires_at=session["expires_at"],
            file_name=session["file_name"],
            total_items=session["total_items"],
            new_items=session["new_items"],
            conflicts=[ConfigConflict(**c) for c in session["conflicts"]]
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post(
    "/import/{session_id}/resolve",
    response_model=ImportResultResponse,
    summary="Resolve conflicts and apply import"
)
def resolve_import(
    session_id: str,
    request: ConflictResolutionRequest,
    service: ConfigService = Depends(get_config_service)
) -> ImportResultResponse:
    """
    Resolve conflicts and apply the import.

    Args:
        session_id: Session UUID
        request: Conflict resolutions

    Returns:
        Import result
    """
    try:
        resolutions = [r.model_dump() for r in request.resolutions]
        result = service.apply_import(session_id, resolutions)

        return ImportResultResponse(
            success=result["success"],
            items_imported=result["items_imported"],
            items_skipped=result["items_skipped"],
            message=result["message"]
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error resolving import: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve import: {str(e)}"
        )


@router.post(
    "/import/{session_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel import session"
)
def cancel_import(
    session_id: str,
    service: ConfigService = Depends(get_config_service)
) -> dict:
    """
    Cancel an import session.

    Args:
        session_id: Session UUID

    Returns:
        Confirmation
    """
    try:
        service.cancel_import(session_id)
        return {"message": "Import cancelled"}
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================================================
# Get All Configuration
# ============================================================================

@router.get(
    "",
    response_model=ConfigurationResponse,
    summary="Get all configuration"
)
def get_all_config(
    category: Optional[str] = Query(None, description="Filter by category"),
    service: ConfigService = Depends(get_config_service)
) -> ConfigurationResponse:
    """
    Get all configuration organized by category.

    Args:
        category: Optional filter by category (extensions, cameras, processing_methods)

    Returns:
        Configuration organized by category
    """
    try:
        all_config = service.get_all()

        if category:
            # Filter to specific category
            if category not in all_config:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid category: {category}"
                )

        return ConfigurationResponse(
            extensions=all_config.get("extensions", {}),
            cameras=all_config.get("cameras", {}),
            processing_methods=all_config.get("processing_methods", {})
        )
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting all config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get configuration: {str(e)}"
        )


# ============================================================================
# Category Endpoints
# ============================================================================

@router.get(
    "/{category}",
    response_model=CategoryConfigResponse,
    summary="Get category configuration"
)
def get_category_config(
    category: str,
    service: ConfigService = Depends(get_config_service)
) -> CategoryConfigResponse:
    """
    Get all configuration items for a specific category.

    Args:
        category: Configuration category

    Returns:
        Category with its configuration items
    """
    try:
        items = service.get_category(category)
        return CategoryConfigResponse(category=category, items=items)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting category {category}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get category: {str(e)}"
        )


# ============================================================================
# Item CRUD Endpoints
# ============================================================================

@router.get(
    "/{category}/{key}",
    response_model=ConfigItemResponse,
    summary="Get configuration value"
)
def get_config_value(
    category: str,
    key: str,
    service: ConfigService = Depends(get_config_service)
) -> ConfigItemResponse:
    """
    Get a specific configuration value.

    Args:
        category: Configuration category
        key: Configuration key

    Returns:
        Configuration item
    """
    result = service.get(category, key)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Configuration {category}.{key} not found"
        )
    return result


@router.post(
    "/{category}/{key}",
    response_model=ConfigItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create configuration value"
)
def create_config_value(
    category: str,
    key: str,
    request: ConfigItemCreate,
    service: ConfigService = Depends(get_config_service)
) -> ConfigItemResponse:
    """
    Create a new configuration value.

    Args:
        category: Configuration category (from path)
        key: Configuration key (from path)
        request: Configuration data

    Returns:
        Created configuration item
    """
    try:
        return service.create(
            category=category,
            key=key,
            value=request.value,
            description=request.description
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create configuration: {str(e)}"
        )


@router.put(
    "/{category}/{key}",
    response_model=ConfigItemResponse,
    summary="Update configuration value"
)
def update_config_value(
    category: str,
    key: str,
    request: ConfigItemUpdate,
    service: ConfigService = Depends(get_config_service)
) -> ConfigItemResponse:
    """
    Update a configuration value.

    Args:
        category: Configuration category
        key: Configuration key
        request: Update data

    Returns:
        Updated configuration item
    """
    try:
        return service.update(
            category=category,
            key=key,
            value=request.value,
            description=request.description
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )


@router.delete(
    "/{category}/{key}",
    response_model=DeleteResponse,
    summary="Delete configuration value"
)
def delete_config_value(
    category: str,
    key: str,
    service: ConfigService = Depends(get_config_service)
) -> DeleteResponse:
    """
    Delete a configuration value.

    Args:
        category: Configuration category
        key: Configuration key

    Returns:
        Deletion confirmation
    """
    try:
        deleted_id = service.delete(category, key)
        return DeleteResponse(
            message="Configuration deleted successfully",
            deleted_id=deleted_id
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete configuration: {str(e)}"
        )
