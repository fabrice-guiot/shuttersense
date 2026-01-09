"""
Results API endpoints for managing analysis results.

Provides endpoints for:
- Listing results with filtering and pagination
- Getting result details
- Deleting results
- Downloading HTML reports
- Getting statistics for KPIs

Design:
- Uses dependency injection for services
- Query parameter validation
- Pagination support
- HTML report download with proper headers
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.models import ResultStatus
from backend.src.schemas.results import (
    SortField, SortOrder, ResultListResponse, AnalysisResultResponse,
    ResultStatsResponse, DeleteResponse
)
from backend.src.services.result_service import ResultService
from backend.src.services.exceptions import NotFoundError
from backend.src.utils.logging_config import get_logger


logger = get_logger("api")

router = APIRouter(
    prefix="/results",
    tags=["Results"],
)


# ============================================================================
# Dependencies
# ============================================================================

def get_result_service(db: Session = Depends(get_db)) -> ResultService:
    """Create ResultService instance with dependencies."""
    return ResultService(db=db)


# ============================================================================
# List and Query Endpoints
# ============================================================================

@router.get(
    "",
    response_model=ResultListResponse,
    summary="List analysis results"
)
def list_results(
    collection_id: Optional[int] = Query(None, gt=0, description="Filter by collection"),
    tool: Optional[str] = Query(None, description="Filter by tool type"),
    status: Optional[ResultStatus] = Query(None, description="Filter by status"),
    from_date: Optional[date] = Query(None, description="Filter from date"),
    to_date: Optional[date] = Query(None, description="Filter to date"),
    limit: int = Query(50, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Results to skip"),
    sort_by: SortField = Query(SortField.CREATED_AT, description="Sort field"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort direction"),
    service: ResultService = Depends(get_result_service)
) -> ResultListResponse:
    """
    List analysis results with filtering and pagination.

    Supports filtering by collection, tool, status, and date range.
    Returns paginated results sorted by the specified field.

    Args:
        collection_id: Filter by collection ID
        tool: Filter by tool type (photostats, photo_pairing, pipeline_validation)
        status: Filter by result status (COMPLETED, FAILED, CANCELLED)
        from_date: Filter from date (inclusive)
        to_date: Filter to date (inclusive)
        limit: Maximum results to return (default 50, max 100)
        offset: Number of results to skip for pagination
        sort_by: Field to sort by (created_at, duration_seconds, files_scanned)
        sort_order: Sort direction (asc, desc)

    Returns:
        Paginated list of result summaries
    """
    items, total = service.list_results(
        collection_id=collection_id,
        tool=tool,
        status=status,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order
    )

    return ResultListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get(
    "/stats",
    response_model=ResultStatsResponse,
    summary="Get results statistics"
)
def get_stats(
    service: ResultService = Depends(get_result_service)
) -> ResultStatsResponse:
    """
    Get aggregate statistics for results.

    Returns totals and counts by status and tool type for
    dashboard KPIs.

    Returns:
        Statistics including total results, counts by status and tool
    """
    return service.get_stats()


# ============================================================================
# Individual Result Endpoints
# ============================================================================

@router.get(
    "/{result_id}",
    response_model=AnalysisResultResponse,
    summary="Get result details"
)
def get_result(
    result_id: int,
    service: ResultService = Depends(get_result_service)
) -> AnalysisResultResponse:
    """
    Get full details for an analysis result.

    Includes tool-specific results data and collection/pipeline names.

    Args:
        result_id: Result ID

    Returns:
        Full result details

    Raises:
        404: Result not found
    """
    try:
        return service.get_result(result_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result {result_id} not found"
        )


@router.delete(
    "/{result_id}",
    response_model=DeleteResponse,
    summary="Delete a result"
)
def delete_result(
    result_id: int,
    service: ResultService = Depends(get_result_service)
) -> DeleteResponse:
    """
    Delete an analysis result.

    Permanently removes the result and its HTML report.

    Args:
        result_id: Result ID to delete

    Returns:
        Confirmation with deleted ID

    Raises:
        404: Result not found
    """
    try:
        deleted_id = service.delete_result(result_id)
        logger.info(f"Result {result_id} deleted")
        return DeleteResponse(
            message="Result deleted successfully",
            deleted_id=deleted_id
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result {result_id} not found"
        )


@router.get(
    "/{result_id}/report",
    summary="Download HTML report",
    responses={
        200: {
            "description": "HTML report file",
            "content": {"text/html": {"schema": {"type": "string"}}}
        },
        404: {"description": "Result or report not found"}
    }
)
def download_report(
    result_id: int,
    service: ResultService = Depends(get_result_service)
) -> Response:
    """
    Download HTML report for a result.

    Returns the pre-rendered HTML report as a downloadable file.
    Filename follows CLI tool conventions:
    {tool}_report_{collection_name}_{collection_id}_{timestamp}.html

    Args:
        result_id: Result ID

    Returns:
        HTML report with download headers

    Raises:
        404: Result not found or no report available
    """
    try:
        report_data = service.get_report_with_metadata(result_id)

        # Generate filename following CLI tool conventions
        # Format: {tool}_report_{collection_name}_{collection_id}_{timestamp}.html
        filename = (
            f"{report_data['tool']}_report_"
            f"{report_data['collection_name']}_"
            f"{report_data['collection_id']}_"
            f"{report_data['timestamp']}.html"
        )

        return Response(
            content=report_data["html"],
            media_type="text/html",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
