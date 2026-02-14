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
- Tenant isolation via require_auth middleware

Note: Route order matters! Specific routes (stats, export, import) must come
before parameterized routes (/{category}, /{category}/{key}).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, File, status
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.schemas.config import (
    ConfigItemCreate, ConfigItemUpdate, ConfigItemResponse,
    CategoryConfigResponse, ConfigurationResponse,
    ImportSessionResponse, ConflictResolutionRequest, ImportResultResponse,
    ConfigStatsResponse, DeleteResponse, ConfigConflict,
    EventStatusItem, EventStatusesResponse
)
from backend.src.schemas.conflict import (
    ConflictRulesResponse, ConflictRulesUpdateRequest,
    ScoringWeightsResponse, ScoringWeightsUpdateRequest,
)
from backend.src.schemas.retention import (
    RetentionSettingsResponse, RetentionSettingsUpdate
)
from backend.src.services.config_service import ConfigService
from backend.src.services.retention_service import RetentionService
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError
from backend.src.utils.logging_config import get_logger
from backend.src.middleware.auth import require_auth, TenantContext


logger = get_logger("api")

router = APIRouter(
    prefix="/config",
    tags=["Configuration"],
)

# Use the shared limiter from main module
from backend.src.main import limiter


# ============================================================================
# Dependencies
# ============================================================================

def get_config_service(db: Session = Depends(get_db)) -> ConfigService:
    """Create ConfigService instance with dependencies."""
    return ConfigService(db=db)


def get_retention_service(db: Session = Depends(get_db)) -> RetentionService:
    """Create RetentionService instance with dependencies."""
    return RetentionService(db=db)


# ============================================================================
# Statistics Endpoint (must be before /{category})
# ============================================================================

@router.get(
    "/stats",
    response_model=ConfigStatsResponse,
    summary="Get configuration statistics"
)
def get_stats(
    ctx: TenantContext = Depends(require_auth),
    service: ConfigService = Depends(get_config_service)
) -> ConfigStatsResponse:
    """
    Get aggregate statistics for configuration.

    Returns totals, category counts, and source breakdown for dashboard KPIs.

    Args:
        ctx: Tenant context with team_id

    Returns:
        Statistics including total items, cameras, methods, and source breakdown
    """
    return service.get_stats(team_id=ctx.team_id)


# ============================================================================
# Event Statuses Endpoint (must be before /{category})
# ============================================================================

# ============================================================================
# Retention Settings Endpoints (must be before /{category})
# Issue #92: Storage Optimization for Analysis Results
# ============================================================================

@router.get(
    "/retention",
    response_model=RetentionSettingsResponse,
    summary="Get retention settings"
)
def get_retention_settings(
    ctx: TenantContext = Depends(require_auth),
    service: RetentionService = Depends(get_retention_service)
) -> RetentionSettingsResponse:
    """
    Get retention settings for the authenticated user's team.

    Returns default values if settings have not been configured:
    - job_completed_days: 2 (days to retain completed jobs)
    - job_failed_days: 7 (days to retain failed jobs)
    - result_completed_days: 0 (unlimited, days to retain completed results)
    - preserve_per_collection: 1 (minimum results to keep per collection+tool)

    Args:
        ctx: Tenant context with team_id

    Returns:
        Current retention settings with defaults applied
    """
    return service.get_settings(ctx)


@router.put(
    "/retention",
    response_model=RetentionSettingsResponse,
    summary="Update retention settings"
)
def update_retention_settings(
    update: RetentionSettingsUpdate,
    ctx: TenantContext = Depends(require_auth),
    service: RetentionService = Depends(get_retention_service)
) -> RetentionSettingsResponse:
    """
    Update retention settings for the authenticated user's team.

    All fields are optional; only provided fields are updated.
    Valid values:
    - job_completed_days, job_failed_days, result_completed_days:
      0 (unlimited), 1, 2, 5, 7, 14, 30, 90, 180, 365
    - preserve_per_collection: 1, 2, 3, 5, 10

    Args:
        update: Update request with optional fields
        ctx: Tenant context with team_id

    Returns:
        Updated retention settings

    Raises:
        400: If any value is not in the allowed options
    """
    try:
        return service.update_settings(ctx, update=update)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/event_statuses",
    response_model=EventStatusesResponse,
    summary="Get event status options"
)
def get_event_statuses(
    ctx: TenantContext = Depends(require_auth),
    service: ConfigService = Depends(get_config_service)
) -> EventStatusesResponse:
    """
    Get event status options ordered by display order.

    Returns an ordered list of available event statuses for use in dropdowns
    and forms. Each status has a key (used in code), label (for display),
    and display_order (for sorting).

    Args:
        ctx: Tenant context with team_id

    Returns:
        List of event statuses ordered by display_order
    """
    statuses = service.get_event_statuses(team_id=ctx.team_id)
    return EventStatusesResponse(
        statuses=[EventStatusItem(**s) for s in statuses]
    )


# ============================================================================
# Export Endpoint (must be before /{category})
# ============================================================================

@router.get(
    "/export",
    summary="Export configuration as YAML"
)
def export_config(
    ctx: TenantContext = Depends(require_auth),
    service: ConfigService = Depends(get_config_service)
) -> Response:
    """
    Export all configuration as a YAML file.

    Args:
        ctx: Tenant context with team_id

    Returns:
        YAML file download
    """
    try:
        yaml_content = service.export_to_yaml(team_id=ctx.team_id)

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
    ctx: TenantContext = Depends(require_auth),
    service: ConfigService = Depends(get_config_service)
) -> ImportSessionResponse:
    """
    Start a YAML import with conflict detection.

    Uploads a YAML configuration file and detects conflicts with existing
    configuration. Returns a session ID for resolving conflicts.

    Args:
        file: YAML configuration file
        ctx: Tenant context with team_id

    Returns:
        Import session with conflicts
    """
    # Limit YAML import to 1MB to prevent memory exhaustion
    max_import_size = 1 * 1024 * 1024  # 1MB
    try:
        content = await file.read(max_import_size + 1)
        if len(content) > max_import_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"YAML file exceeds maximum import size of {max_import_size // (1024 * 1024)}MB",
            )
        yaml_content = content.decode("utf-8")

        session = service.start_import(yaml_content, team_id=ctx.team_id, filename=file.filename)

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
    ctx: TenantContext = Depends(require_auth),
    service: ConfigService = Depends(get_config_service)
) -> ImportSessionResponse:
    """
    Get import session status and conflicts.

    Args:
        session_id: Session UUID
        ctx: Tenant context with team_id

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
    ctx: TenantContext = Depends(require_auth),
    service: ConfigService = Depends(get_config_service)
) -> ImportResultResponse:
    """
    Resolve conflicts and apply the import.

    Args:
        session_id: Session UUID
        request: Conflict resolutions
        ctx: Tenant context with team_id

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
    ctx: TenantContext = Depends(require_auth),
    service: ConfigService = Depends(get_config_service)
) -> dict:
    """
    Cancel an import session.

    Args:
        session_id: Session UUID
        ctx: Tenant context with team_id

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
# Conflict Rules Endpoints (must be before /{category})
# ============================================================================


@router.get(
    "/conflict_rules",
    response_model=ConflictRulesResponse,
    summary="Get conflict rule settings",
)
def get_conflict_rules(
    ctx: TenantContext = Depends(require_auth),
    service: ConfigService = Depends(get_config_service),
) -> ConflictRulesResponse:
    """Get the team's conflict detection configuration."""
    from backend.src.services.conflict_service import ConflictService
    conflict_service = ConflictService(service.db)
    return conflict_service.get_conflict_rules(ctx.team_id)


@router.put(
    "/conflict_rules",
    response_model=ConflictRulesResponse,
    summary="Update conflict rule settings",
)
def update_conflict_rules(
    update: ConflictRulesUpdateRequest,
    ctx: TenantContext = Depends(require_auth),
    service: ConfigService = Depends(get_config_service),
) -> ConflictRulesResponse:
    """Update one or more conflict detection settings."""
    try:
        updates = update.model_dump(exclude_unset=True)
        for key, value in updates.items():
            existing = service.get("conflict_rules", key, team_id=ctx.team_id)
            if existing:
                current = existing.value if isinstance(existing.value, dict) else {}
                current["value"] = value
                service.update(
                    category="conflict_rules", key=key,
                    team_id=ctx.team_id, value=current,
                    user_id=ctx.user_id,
                )
            else:
                service.create(
                    category="conflict_rules", key=key,
                    value={"value": value, "label": key.replace("_", " ").title()},
                    team_id=ctx.team_id, user_id=ctx.user_id,
                )

        from backend.src.services.conflict_service import ConflictService
        conflict_service = ConflictService(service.db)
        return conflict_service.get_conflict_rules(ctx.team_id)

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


# ============================================================================
# Scoring Weights Endpoints (must be before /{category})
# ============================================================================


@router.get(
    "/scoring_weights",
    response_model=ScoringWeightsResponse,
    summary="Get scoring weight settings",
)
def get_scoring_weights(
    ctx: TenantContext = Depends(require_auth),
    service: ConfigService = Depends(get_config_service),
) -> ScoringWeightsResponse:
    """Get the team's scoring dimension weights."""
    from backend.src.services.conflict_service import ConflictService
    conflict_service = ConflictService(service.db)
    return conflict_service.get_scoring_weights(ctx.team_id)


@router.put(
    "/scoring_weights",
    response_model=ScoringWeightsResponse,
    summary="Update scoring weight settings",
)
def update_scoring_weights(
    update: ScoringWeightsUpdateRequest,
    ctx: TenantContext = Depends(require_auth),
    service: ConfigService = Depends(get_config_service),
) -> ScoringWeightsResponse:
    """Update one or more scoring dimension weights."""
    try:
        updates = update.model_dump(exclude_unset=True)
        for key, value in updates.items():
            existing = service.get("scoring_weights", key, team_id=ctx.team_id)
            if existing:
                current = existing.value if isinstance(existing.value, dict) else {}
                current["value"] = value
                service.update(
                    category="scoring_weights", key=key,
                    team_id=ctx.team_id, value=current,
                    user_id=ctx.user_id,
                )
            else:
                service.create(
                    category="scoring_weights", key=key,
                    value={"value": value, "label": key.replace("_", " ").title()},
                    team_id=ctx.team_id, user_id=ctx.user_id,
                )

        from backend.src.services.conflict_service import ConflictService
        conflict_service = ConflictService(service.db)
        return conflict_service.get_scoring_weights(ctx.team_id)

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
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
    ctx: TenantContext = Depends(require_auth),
    category: Optional[str] = Query(None, description="Filter by category"),
    service: ConfigService = Depends(get_config_service)
) -> ConfigurationResponse:
    """
    Get all configuration organized by category.

    Args:
        ctx: Tenant context with team_id
        category: Optional filter by category (extensions, cameras, processing_methods)

    Returns:
        Configuration organized by category
    """
    try:
        all_config = service.get_all(team_id=ctx.team_id)

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
            processing_methods=all_config.get("processing_methods", {}),
            event_statuses=all_config.get("event_statuses", {})
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
    ctx: TenantContext = Depends(require_auth),
    service: ConfigService = Depends(get_config_service)
) -> CategoryConfigResponse:
    """
    Get all configuration items for a specific category.

    Args:
        category: Configuration category
        ctx: Tenant context with team_id

    Returns:
        Category with its configuration items
    """
    try:
        items = service.get_category(category, team_id=ctx.team_id)
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
    ctx: TenantContext = Depends(require_auth),
    service: ConfigService = Depends(get_config_service)
) -> ConfigItemResponse:
    """
    Get a specific configuration value.

    Args:
        category: Configuration category
        key: Configuration key
        ctx: Tenant context with team_id

    Returns:
        Configuration item
    """
    result = service.get(category, key, team_id=ctx.team_id)
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
    ctx: TenantContext = Depends(require_auth),
    service: ConfigService = Depends(get_config_service)
) -> ConfigItemResponse:
    """
    Create a new configuration value.

    Args:
        category: Configuration category (from path)
        key: Configuration key (from path)
        request: Configuration data
        ctx: Tenant context with team_id

    Returns:
        Created configuration item
    """
    try:
        return service.create(
            category=category,
            key=key,
            value=request.value,
            team_id=ctx.team_id,
            description=request.description,
            user_id=ctx.user_id
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
    ctx: TenantContext = Depends(require_auth),
    service: ConfigService = Depends(get_config_service)
) -> ConfigItemResponse:
    """
    Update a configuration value.

    Args:
        category: Configuration category
        key: Configuration key
        request: Update data
        ctx: Tenant context with team_id

    Returns:
        Updated configuration item
    """
    try:
        return service.update(
            category=category,
            key=key,
            team_id=ctx.team_id,
            value=request.value,
            description=request.description,
            user_id=ctx.user_id
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
    ctx: TenantContext = Depends(require_auth),
    service: ConfigService = Depends(get_config_service)
) -> DeleteResponse:
    """
    Delete a configuration value.

    Args:
        category: Configuration category
        key: Configuration key
        ctx: Tenant context with team_id

    Returns:
        Deletion confirmation
    """
    try:
        deleted_id = service.delete(category, key, team_id=ctx.team_id)
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
