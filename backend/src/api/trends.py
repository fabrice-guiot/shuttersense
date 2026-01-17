"""
Trends API endpoints for historical analysis data visualization.

Provides endpoints for:
- PhotoStats trends (orphaned files over time)
- Photo Pairing trends (camera usage over time)
- Pipeline Validation trends (consistency ratios over time)
- Trend summary for dashboard

Design:
- Collection-grouped data for comparison charts
- Flexible date range filtering
- Limit controls for performance
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.middleware.auth import require_auth, TenantContext
from backend.src.schemas.trends import (
    PhotoStatsTrendResponse,
    PhotoPairingTrendResponse,
    PipelineValidationTrendResponse,
    DisplayGraphTrendResponse,
    TrendSummaryResponse,
)
from backend.src.services.trend_service import TrendService
from backend.src.utils.logging_config import get_logger


logger = get_logger("api")

router = APIRouter(
    prefix="/trends",
    tags=["Trends"],
)


# ============================================================================
# Dependencies
# ============================================================================

def get_trend_service(db: Session = Depends(get_db)) -> TrendService:
    """Create TrendService instance with dependencies."""
    return TrendService(db=db)


# ============================================================================
# PhotoStats Trends
# ============================================================================

@router.get(
    "/photostats",
    response_model=PhotoStatsTrendResponse,
    summary="Get PhotoStats trends"
)
def get_photostats_trends(
    ctx: TenantContext = Depends(require_auth),
    collection_ids: Optional[str] = Query(
        None,
        description="Comma-separated collection IDs"
    ),
    from_date: Optional[date] = Query(None, description="Filter from date"),
    to_date: Optional[date] = Query(None, description="Filter to date"),
    limit: int = Query(
        50,
        ge=1,
        le=500,
        description="Maximum data points per collection"
    ),
    service: TrendService = Depends(get_trend_service)
) -> PhotoStatsTrendResponse:
    """
    Get PhotoStats trend data for trend visualization.

    Returns orphaned file counts and storage metrics over time,
    grouped by collection for comparison charts.

    Args:
        collection_ids: Comma-separated collection IDs to include
        from_date: Filter from date (inclusive)
        to_date: Filter to date (inclusive)
        limit: Maximum data points per collection (default 50, max 500)

    Returns:
        PhotoStats trend data grouped by collection
    """
    return service.get_photostats_trends(
        team_id=ctx.team_id,
        collection_ids=collection_ids,
        from_date=from_date,
        to_date=to_date,
        limit=limit
    )


# ============================================================================
# Photo Pairing Trends
# ============================================================================

@router.get(
    "/photo-pairing",
    response_model=PhotoPairingTrendResponse,
    summary="Get Photo Pairing trends"
)
def get_photo_pairing_trends(
    ctx: TenantContext = Depends(require_auth),
    collection_ids: Optional[str] = Query(
        None,
        description="Comma-separated collection IDs"
    ),
    from_date: Optional[date] = Query(None, description="Filter from date"),
    to_date: Optional[date] = Query(None, description="Filter to date"),
    limit: int = Query(
        50,
        ge=1,
        le=500,
        description="Maximum data points per collection"
    ),
    service: TrendService = Depends(get_trend_service)
) -> PhotoPairingTrendResponse:
    """
    Get Photo Pairing trend data for trend visualization.

    Returns camera usage and group counts over time,
    grouped by collection for multi-line charts.

    Args:
        collection_ids: Comma-separated collection IDs to include
        from_date: Filter from date (inclusive)
        to_date: Filter to date (inclusive)
        limit: Maximum data points per collection (default 50, max 500)

    Returns:
        Photo Pairing trend data grouped by collection
    """
    return service.get_photo_pairing_trends(
        team_id=ctx.team_id,
        collection_ids=collection_ids,
        from_date=from_date,
        to_date=to_date,
        limit=limit
    )


# ============================================================================
# Pipeline Validation Trends
# ============================================================================

@router.get(
    "/pipeline-validation",
    response_model=PipelineValidationTrendResponse,
    summary="Get Pipeline Validation trends"
)
def get_pipeline_validation_trends(
    ctx: TenantContext = Depends(require_auth),
    collection_ids: Optional[str] = Query(
        None,
        description="Comma-separated collection IDs"
    ),
    pipeline_id: Optional[int] = Query(
        None,
        gt=0,
        description="Filter by pipeline ID"
    ),
    pipeline_version: Optional[int] = Query(
        None,
        gt=0,
        description="Filter by pipeline version"
    ),
    from_date: Optional[date] = Query(None, description="Filter from date"),
    to_date: Optional[date] = Query(None, description="Filter to date"),
    limit: int = Query(
        50,
        ge=1,
        le=500,
        description="Maximum data points per collection"
    ),
    service: TrendService = Depends(get_trend_service)
) -> PipelineValidationTrendResponse:
    """
    Get Pipeline Validation trend data for trend visualization.

    Returns consistency ratios over time, grouped by collection
    for stacked area charts.

    Args:
        collection_ids: Comma-separated collection IDs to include
        pipeline_id: Filter by specific pipeline
        pipeline_version: Filter by specific pipeline version
        from_date: Filter from date (inclusive)
        to_date: Filter to date (inclusive)
        limit: Maximum data points per collection (default 50, max 500)

    Returns:
        Pipeline Validation trend data grouped by collection
    """
    return service.get_pipeline_validation_trends(
        team_id=ctx.team_id,
        collection_ids=collection_ids,
        pipeline_id=pipeline_id,
        pipeline_version=pipeline_version,
        from_date=from_date,
        to_date=to_date,
        limit=limit
    )


# ============================================================================
# Display Graph Trends
# ============================================================================

@router.get(
    "/display-graph",
    response_model=DisplayGraphTrendResponse,
    summary="Get Display Graph trends"
)
def get_display_graph_trends(
    ctx: TenantContext = Depends(require_auth),
    pipeline_ids: Optional[str] = Query(
        None,
        description="Comma-separated pipeline IDs"
    ),
    from_date: Optional[date] = Query(None, description="Filter from date"),
    to_date: Optional[date] = Query(None, description="Filter to date"),
    limit: int = Query(
        50,
        ge=1,
        le=500,
        description="Maximum data points per pipeline"
    ),
    service: TrendService = Depends(get_trend_service)
) -> DisplayGraphTrendResponse:
    """
    Get Display Graph trend data for trend visualization.

    Returns pipeline path enumeration metrics over time,
    grouped by pipeline for comparison charts.

    Args:
        pipeline_ids: Comma-separated pipeline IDs to include
        from_date: Filter from date (inclusive)
        to_date: Filter to date (inclusive)
        limit: Maximum data points per pipeline (default 50, max 500)

    Returns:
        Display Graph trend data grouped by pipeline
    """
    return service.get_display_graph_trends(
        team_id=ctx.team_id,
        pipeline_ids=pipeline_ids,
        from_date=from_date,
        to_date=to_date,
        limit=limit
    )


# ============================================================================
# Trend Summary
# ============================================================================

@router.get(
    "/summary",
    response_model=TrendSummaryResponse,
    summary="Get trend summary"
)
def get_trend_summary(
    ctx: TenantContext = Depends(require_auth),
    collection_id: Optional[int] = Query(
        None,
        gt=0,
        description="Filter by collection ID"
    ),
    service: TrendService = Depends(get_trend_service)
) -> TrendSummaryResponse:
    """
    Get trend summary for dashboard overview.

    Provides quick indicators of trend direction for orphaned files
    and consistency metrics.

    Args:
        collection_id: Optional collection ID filter

    Returns:
        Trend summary with direction indicators and latest timestamps
    """
    return service.get_trend_summary(team_id=ctx.team_id, collection_id=collection_id)
