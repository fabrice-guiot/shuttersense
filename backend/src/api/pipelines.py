"""
Pipelines API endpoints for managing photo processing workflows.

Provides endpoints for:
- CRUD operations on pipelines
- Validation of pipeline structure
- Activation/deactivation for validation runs
- Filename preview based on pipeline structure
- Version history
- YAML import/export
- Statistics for dashboard KPIs

Design:
- Uses dependency injection for services
- Pydantic validation for request/response
- YAML file upload for import
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, File, status
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.schemas.pipelines import (
    PipelineCreateRequest, PipelineUpdateRequest, PipelineSummary, PipelineResponse,
    PipelineListResponse, ValidationResult, FilenamePreviewResponse,
    PipelineHistoryEntry, PipelineStatsResponse, DeleteResponse
)
from backend.src.services.pipeline_service import PipelineService
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError
from backend.src.utils.logging_config import get_logger


logger = get_logger("api")

router = APIRouter(
    prefix="/pipelines",
    tags=["Pipelines"],
)


# ============================================================================
# Dependencies
# ============================================================================

def get_pipeline_service(db: Session = Depends(get_db)) -> PipelineService:
    """Create PipelineService instance with dependencies."""
    return PipelineService(db=db)


# ============================================================================
# List and Stats Endpoints
# ============================================================================

@router.get(
    "",
    response_model=PipelineListResponse,
    summary="List all pipelines"
)
def list_pipelines(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_default: Optional[bool] = Query(None, description="Filter by default status"),
    is_valid: Optional[bool] = Query(None, description="Filter by validation status"),
    service: PipelineService = Depends(get_pipeline_service)
) -> PipelineListResponse:
    """
    List all pipelines with optional filters.

    Args:
        is_active: Filter by active status
        is_default: Filter by default status
        is_valid: Filter by validation status

    Returns:
        List of pipeline summaries
    """
    items = service.list(is_active=is_active, is_default=is_default, is_valid=is_valid)
    return PipelineListResponse(items=items)


@router.get(
    "/stats",
    response_model=PipelineStatsResponse,
    summary="Get pipeline statistics"
)
def get_stats(
    service: PipelineService = Depends(get_pipeline_service)
) -> PipelineStatsResponse:
    """
    Get aggregate statistics for pipelines.

    Returns totals, active count, and default pipeline info for dashboard KPIs.

    Returns:
        Statistics including total, valid count, active count, and default pipeline
    """
    return service.get_stats()


# ============================================================================
# CRUD Endpoints
# ============================================================================

@router.post(
    "",
    response_model=PipelineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new pipeline"
)
def create_pipeline(
    request: PipelineCreateRequest,
    service: PipelineService = Depends(get_pipeline_service)
) -> PipelineResponse:
    """
    Create a new pipeline.

    Pipeline is validated on creation. If structure has errors,
    is_valid will be False and validation_errors will contain details.

    Args:
        request: Pipeline creation data

    Returns:
        Created pipeline

    Raises:
        409: Pipeline name already exists
    """
    try:
        # Convert Pydantic models to dicts
        nodes = [n.model_dump() for n in request.nodes]
        edges = [e.model_dump(by_alias=True) for e in request.edges]

        return service.create(
            name=request.name,
            description=request.description,
            nodes=nodes,
            edges=edges
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.get(
    "/{pipeline_id}",
    response_model=PipelineResponse,
    summary="Get pipeline details"
)
def get_pipeline(
    pipeline_id: int,
    service: PipelineService = Depends(get_pipeline_service)
) -> PipelineResponse:
    """
    Get full details for a pipeline.

    Includes nodes, edges, and validation status.

    Args:
        pipeline_id: Pipeline ID

    Returns:
        Full pipeline details

    Raises:
        404: Pipeline not found
    """
    try:
        return service.get(pipeline_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline {pipeline_id} not found"
        )


@router.put(
    "/{pipeline_id}",
    response_model=PipelineResponse,
    summary="Update a pipeline"
)
def update_pipeline(
    pipeline_id: int,
    request: PipelineUpdateRequest,
    service: PipelineService = Depends(get_pipeline_service)
) -> PipelineResponse:
    """
    Update a pipeline.

    Creates a history entry before updating. Version is incremented.
    If structure changes, validation is re-run.

    Args:
        pipeline_id: Pipeline ID
        request: Update data

    Returns:
        Updated pipeline

    Raises:
        404: Pipeline not found
        409: New name already exists
    """
    try:
        # Convert Pydantic models to dicts if provided
        nodes = [n.model_dump() for n in request.nodes] if request.nodes else None
        edges = [e.model_dump(by_alias=True) for e in request.edges] if request.edges else None

        return service.update(
            pipeline_id=pipeline_id,
            name=request.name,
            description=request.description,
            nodes=nodes,
            edges=edges,
            change_summary=request.change_summary
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline {pipeline_id} not found"
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.delete(
    "/{pipeline_id}",
    response_model=DeleteResponse,
    summary="Delete a pipeline"
)
def delete_pipeline(
    pipeline_id: int,
    service: PipelineService = Depends(get_pipeline_service)
) -> DeleteResponse:
    """
    Delete a pipeline.

    Cannot delete the default or active pipeline. Remove default status
    and deactivate it first.

    Args:
        pipeline_id: Pipeline ID

    Returns:
        Confirmation with deleted ID

    Raises:
        404: Pipeline not found
        409: Cannot delete default or active pipeline
    """
    try:
        deleted_id = service.delete(pipeline_id)
        logger.info(f"Pipeline {pipeline_id} deleted")
        return DeleteResponse(
            message="Pipeline deleted successfully",
            deleted_id=deleted_id
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline {pipeline_id} not found"
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


# ============================================================================
# Activation Endpoints
# ============================================================================

@router.post(
    "/{pipeline_id}/activate",
    response_model=PipelineResponse,
    summary="Activate a pipeline"
)
def activate_pipeline(
    pipeline_id: int,
    service: PipelineService = Depends(get_pipeline_service)
) -> PipelineResponse:
    """
    Activate a pipeline.

    Multiple pipelines can be active at the same time.
    Active pipelines are valid and ready for use.
    To use a pipeline for tool execution, set it as default.

    Args:
        pipeline_id: Pipeline ID

    Returns:
        Activated pipeline

    Raises:
        400: Pipeline has validation errors
        404: Pipeline not found
    """
    try:
        return service.activate(pipeline_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline {pipeline_id} not found"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{pipeline_id}/deactivate",
    response_model=PipelineResponse,
    summary="Deactivate a pipeline"
)
def deactivate_pipeline(
    pipeline_id: int,
    service: PipelineService = Depends(get_pipeline_service)
) -> PipelineResponse:
    """
    Deactivate a pipeline.

    If the pipeline is the default, it also loses default status.

    Args:
        pipeline_id: Pipeline ID

    Returns:
        Deactivated pipeline

    Raises:
        404: Pipeline not found
    """
    try:
        return service.deactivate(pipeline_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline {pipeline_id} not found"
        )


@router.post(
    "/{pipeline_id}/set-default",
    response_model=PipelineResponse,
    summary="Set a pipeline as default"
)
def set_default_pipeline(
    pipeline_id: int,
    service: PipelineService = Depends(get_pipeline_service)
) -> PipelineResponse:
    """
    Set a pipeline as the default for tool execution.

    Only one pipeline can be default at a time. Setting a new default
    automatically removes default status from the previous default.
    The pipeline must be active to be set as default.

    Args:
        pipeline_id: Pipeline ID

    Returns:
        Pipeline with is_default=True

    Raises:
        400: Pipeline is not active
        404: Pipeline not found
    """
    try:
        return service.set_default(pipeline_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline {pipeline_id} not found"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{pipeline_id}/unset-default",
    response_model=PipelineResponse,
    summary="Remove default status from a pipeline"
)
def unset_default_pipeline(
    pipeline_id: int,
    service: PipelineService = Depends(get_pipeline_service)
) -> PipelineResponse:
    """
    Remove default status from a pipeline.

    After this, no pipeline will be the default until another is set.

    Args:
        pipeline_id: Pipeline ID

    Returns:
        Pipeline with is_default=False

    Raises:
        404: Pipeline not found
    """
    try:
        return service.unset_default(pipeline_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline {pipeline_id} not found"
        )


# ============================================================================
# Validation Endpoints
# ============================================================================

@router.post(
    "/{pipeline_id}/validate",
    response_model=ValidationResult,
    summary="Validate pipeline structure"
)
def validate_pipeline(
    pipeline_id: int,
    service: PipelineService = Depends(get_pipeline_service)
) -> ValidationResult:
    """
    Validate pipeline structure.

    Checks for cycles, orphaned nodes, invalid references, etc.
    Updates the pipeline's is_valid flag.

    Args:
        pipeline_id: Pipeline ID

    Returns:
        Validation result with errors if any

    Raises:
        404: Pipeline not found
    """
    try:
        return service.validate(pipeline_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline {pipeline_id} not found"
        )


# ============================================================================
# Preview Endpoints
# ============================================================================

@router.post(
    "/{pipeline_id}/preview",
    response_model=FilenamePreviewResponse,
    summary="Preview expected filenames"
)
def preview_filenames(
    pipeline_id: int,
    service: PipelineService = Depends(get_pipeline_service)
) -> FilenamePreviewResponse:
    """
    Preview expected filenames for a pipeline.

    Shows what files would be expected based on the pipeline structure.
    Uses sample_filename from the pipeline's Capture node.

    Args:
        pipeline_id: Pipeline ID

    Returns:
        Expected filenames

    Raises:
        400: Pipeline has validation errors
        404: Pipeline not found
    """
    try:
        return service.preview_filenames(pipeline_id=pipeline_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline {pipeline_id} not found"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# History Endpoints
# ============================================================================

@router.get(
    "/{pipeline_id}/history",
    response_model=List[PipelineHistoryEntry],
    summary="Get pipeline version history"
)
def get_history(
    pipeline_id: int,
    service: PipelineService = Depends(get_pipeline_service)
) -> List[PipelineHistoryEntry]:
    """
    Get version history for a pipeline.

    Returns history entries ordered by version descending.

    Args:
        pipeline_id: Pipeline ID

    Returns:
        List of history entries

    Raises:
        404: Pipeline not found
    """
    try:
        return service.get_history(pipeline_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline {pipeline_id} not found"
        )


@router.get(
    "/{pipeline_id}/versions/{version}",
    response_model=PipelineResponse,
    summary="Get a specific version of a pipeline"
)
def get_version(
    pipeline_id: int,
    version: int,
    service: PipelineService = Depends(get_pipeline_service)
) -> PipelineResponse:
    """
    Get a specific historical version of a pipeline.

    Returns the pipeline's nodes and edges as they were at the specified version.

    Args:
        pipeline_id: Pipeline ID
        version: Version number to retrieve

    Returns:
        Pipeline data at that version

    Raises:
        404: Pipeline or version not found
    """
    try:
        return service.get_version(pipeline_id, version)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ============================================================================
# Import/Export Endpoints
# ============================================================================

@router.post(
    "/import",
    response_model=PipelineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import pipeline from YAML"
)
async def import_pipeline(
    file: UploadFile = File(..., description="YAML file to import"),
    service: PipelineService = Depends(get_pipeline_service)
) -> PipelineResponse:
    """
    Import pipeline from YAML file.

    Creates a new pipeline from the uploaded YAML definition.

    Args:
        file: YAML file to import

    Returns:
        Created pipeline

    Raises:
        400: Invalid YAML or structure
        409: Pipeline name already exists
    """
    try:
        content = await file.read()
        yaml_content = content.decode("utf-8")
        return service.import_from_yaml(yaml_content)
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


@router.get(
    "/{pipeline_id}/export",
    summary="Export pipeline as YAML",
    responses={
        200: {
            "description": "YAML file",
            "content": {"application/x-yaml": {"schema": {"type": "string"}}}
        },
        404: {"description": "Pipeline not found"}
    }
)
def export_pipeline(
    pipeline_id: int,
    service: PipelineService = Depends(get_pipeline_service)
) -> Response:
    """
    Export pipeline as YAML file.

    Returns a YAML file with the pipeline definition.

    Args:
        pipeline_id: Pipeline ID

    Returns:
        YAML file with Content-Disposition header

    Raises:
        404: Pipeline not found
    """
    try:
        yaml_content = service.export_to_yaml(pipeline_id)
        pipeline = service.get(pipeline_id)

        # Generate safe filename
        safe_name = "".join(
            c if c.isalnum() or c in "-_" else "_"
            for c in pipeline.name
        ).strip("_")
        filename = f"{safe_name}.yaml"

        return Response(
            content=yaml_content,
            media_type="application/x-yaml",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline {pipeline_id} not found"
        )


@router.get(
    "/{pipeline_id}/versions/{version}/export",
    summary="Export a specific version of a pipeline as YAML",
    responses={
        200: {
            "description": "YAML file",
            "content": {"application/x-yaml": {"schema": {"type": "string"}}}
        },
        404: {"description": "Pipeline or version not found"}
    }
)
def export_pipeline_version(
    pipeline_id: int,
    version: int,
    service: PipelineService = Depends(get_pipeline_service)
) -> Response:
    """
    Export a specific version of a pipeline as YAML file.

    Returns a YAML file with the pipeline definition at the specified version.

    Args:
        pipeline_id: Pipeline ID
        version: Version number to export

    Returns:
        YAML file with Content-Disposition header

    Raises:
        404: Pipeline or version not found
    """
    try:
        yaml_content = service.export_version_to_yaml(pipeline_id, version)
        pipeline = service.get(pipeline_id)

        # Generate safe filename with version
        safe_name = "".join(
            c if c.isalnum() or c in "-_" else "_"
            for c in pipeline.name
        ).strip("_")
        filename = f"{safe_name}_v{version}.yaml"

        return Response(
            content=yaml_content,
            media_type="application/x-yaml",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
