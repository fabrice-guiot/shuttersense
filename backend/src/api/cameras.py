"""
Camera API endpoints for managing camera equipment records.

Provides endpoints for:
- List cameras (paginated, filtered, searchable)
- Get camera by GUID
- Update camera details
- Delete camera
- Camera statistics for KPIs
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.schemas.camera import (
    CameraResponse, CameraListResponse, CameraUpdateRequest,
    CameraStatsResponse, CameraDeleteResponse,
)
from backend.src.services.camera_service import CameraService
from backend.src.services.exceptions import NotFoundError, ConflictError
from backend.src.utils.logging_config import get_logger
from backend.src.middleware.auth import require_auth, TenantContext


logger = get_logger("api")

router = APIRouter(
    prefix="/cameras",
    tags=["Cameras"],
)


# ============================================================================
# Dependencies
# ============================================================================

def get_camera_service(db: Session = Depends(get_db)) -> CameraService:
    """Create CameraService instance with dependencies."""
    return CameraService(db=db)


# ============================================================================
# List and Stats Endpoints
# ============================================================================

@router.get(
    "",
    response_model=CameraListResponse,
    summary="List cameras"
)
def list_cameras(
    ctx: TenantContext = Depends(require_auth),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: temporary or confirmed"),
    search: Optional[str] = Query(None, description="Search by camera_id, display_name, make, or model"),
    service: CameraService = Depends(get_camera_service),
) -> CameraListResponse:
    """List cameras with pagination, filtering, and search."""
    return service.list(
        team_id=ctx.team_id,
        limit=limit,
        offset=offset,
        status=status_filter,
        search=search,
    )


@router.get(
    "/stats",
    response_model=CameraStatsResponse,
    summary="Get camera statistics"
)
def get_camera_stats(
    ctx: TenantContext = Depends(require_auth),
    service: CameraService = Depends(get_camera_service),
) -> CameraStatsResponse:
    """Get aggregate camera statistics for dashboard KPIs."""
    return service.get_stats(team_id=ctx.team_id)


# ============================================================================
# CRUD Endpoints
# ============================================================================

@router.get(
    "/{guid}",
    response_model=CameraResponse,
    summary="Get camera by GUID"
)
def get_camera(
    guid: str,
    ctx: TenantContext = Depends(require_auth),
    service: CameraService = Depends(get_camera_service),
) -> CameraResponse:
    """Get full details for a camera by GUID."""
    try:
        return service.get_by_guid(guid, team_id=ctx.team_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera not found: {guid}"
        )


@router.put(
    "/{guid}",
    response_model=CameraResponse,
    summary="Update camera"
)
def update_camera(
    guid: str,
    request: CameraUpdateRequest,
    ctx: TenantContext = Depends(require_auth),
    service: CameraService = Depends(get_camera_service),
) -> CameraResponse:
    """Update camera details (status, display_name, make, model, etc.)."""
    try:
        return service.update(
            guid=guid,
            team_id=ctx.team_id,
            status=request.status,
            display_name=request.display_name,
            make=request.make,
            model=request.model,
            serial_number=request.serial_number,
            notes=request.notes,
            user_id=ctx.user_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera not found: {guid}"
        )


@router.delete(
    "/{guid}",
    response_model=CameraDeleteResponse,
    summary="Delete camera"
)
def delete_camera(
    guid: str,
    ctx: TenantContext = Depends(require_auth),
    service: CameraService = Depends(get_camera_service),
) -> CameraDeleteResponse:
    """Delete a camera by GUID."""
    try:
        deleted_guid = service.delete(guid=guid, team_id=ctx.team_id)
        return CameraDeleteResponse(
            message="Camera deleted successfully",
            deleted_guid=deleted_guid,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera not found: {guid}"
        )
