"""
Analytics API endpoints for storage metrics and optimization statistics.

Provides endpoints for:
- Storage metrics dashboard (cumulative and real-time statistics)

Issue #92 - Storage Optimization for Analysis Results (Phase 9)
Tasks: T058, T059, T060
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.src.db.database import get_db
from backend.src.middleware.auth import require_auth, TenantContext
from backend.src.services.storage_metrics_service import (
    StorageMetricsService,
    StorageMetricsResponse
)
from backend.src.utils.logging_config import get_logger


logger = get_logger("api")

router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


# ============================================================================
# Response Schemas
# ============================================================================

class StorageStatsResponse(BaseModel):
    """Response schema for storage metrics API."""

    # Cumulative counters from StorageMetrics table
    total_reports_generated: int = Field(
        ...,
        description="Cumulative count of all job completions (COMPLETED, NO_CHANGE, FAILED)"
    )
    completed_jobs_purged: int = Field(
        ...,
        description="Cumulative count of completed jobs deleted by cleanup"
    )
    failed_jobs_purged: int = Field(
        ...,
        description="Cumulative count of failed jobs deleted by cleanup"
    )
    completed_results_purged_original: int = Field(
        ...,
        description="Cumulative count of original results purged (no_change_copy=false)"
    )
    completed_results_purged_copy: int = Field(
        ...,
        description="Cumulative count of copy results purged (no_change_copy=true)"
    )
    estimated_bytes_purged: int = Field(
        ...,
        description="Cumulative estimated bytes freed from DB (JSON + HTML sizes)"
    )

    # Real-time statistics (computed from current data)
    total_results_retained: int = Field(
        ...,
        description="Current total number of retained results"
    )
    original_results_retained: int = Field(
        ...,
        description="Current number of original results (no_change_copy=false)"
    )
    copy_results_retained: int = Field(
        ...,
        description="Current number of copy results (no_change_copy=true)"
    )
    preserved_results_count: int = Field(
        ...,
        description="Count of results protected by preserve_per_collection policy"
    )
    reports_retained_json_bytes: int = Field(
        ...,
        description="Total bytes used by JSON result data"
    )
    reports_retained_html_bytes: int = Field(
        ...,
        description="Total bytes used by HTML reports"
    )

    # Derived metrics
    deduplication_ratio: float = Field(
        ...,
        description="Percentage of results that are copies (storage optimization ratio)"
    )
    storage_savings_bytes: int = Field(
        ...,
        description="Estimated bytes saved by deduplication (HTML reports not stored for copies)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_reports_generated": 1500,
                "completed_jobs_purged": 200,
                "failed_jobs_purged": 15,
                "completed_results_purged_original": 150,
                "completed_results_purged_copy": 300,
                "estimated_bytes_purged": 52428800,
                "total_results_retained": 850,
                "original_results_retained": 350,
                "copy_results_retained": 500,
                "preserved_results_count": 100,
                "reports_retained_json_bytes": 10485760,
                "reports_retained_html_bytes": 41943040,
                "deduplication_ratio": 58.8,
                "storage_savings_bytes": 25000000
            }
        }
    }


# ============================================================================
# Dependencies
# ============================================================================

def get_storage_metrics_service(db: Session = Depends(get_db)) -> StorageMetricsService:
    """Create StorageMetricsService instance with dependencies."""
    return StorageMetricsService(db=db)


# ============================================================================
# Endpoints
# ============================================================================

@router.get(
    "/storage",
    response_model=StorageStatsResponse,
    summary="Get storage metrics"
)
def get_storage_stats(
    ctx: TenantContext = Depends(require_auth),
    service: StorageMetricsService = Depends(get_storage_metrics_service)
) -> StorageStatsResponse:
    """
    Get storage optimization metrics for the current team.

    Returns both cumulative metrics (persisted in database) and
    real-time statistics (computed from current data).

    Cumulative metrics:
    - total_reports_generated: Total jobs completed over all time
    - completed_jobs_purged: Jobs removed by retention cleanup
    - failed_jobs_purged: Failed jobs removed by cleanup
    - completed_results_purged_*: Results removed by cleanup (by type)
    - estimated_bytes_purged: Estimated storage freed

    Real-time statistics:
    - total_results_retained: Current result count
    - original_results_retained: Results with full HTML reports
    - copy_results_retained: NO_CHANGE results (no HTML stored)
    - preserved_results_count: Results protected by retention policy
    - reports_retained_*_bytes: Current storage usage

    Derived metrics:
    - deduplication_ratio: Percentage of results that are copies
    - storage_savings_bytes: Estimated storage saved by deduplication
    """
    metrics = service.get_metrics(team_id=ctx.team_id)

    return StorageStatsResponse(
        total_reports_generated=metrics.total_reports_generated,
        completed_jobs_purged=metrics.completed_jobs_purged,
        failed_jobs_purged=metrics.failed_jobs_purged,
        completed_results_purged_original=metrics.completed_results_purged_original,
        completed_results_purged_copy=metrics.completed_results_purged_copy,
        estimated_bytes_purged=metrics.estimated_bytes_purged,
        total_results_retained=metrics.total_results_retained,
        original_results_retained=metrics.original_results_retained,
        copy_results_retained=metrics.copy_results_retained,
        preserved_results_count=metrics.preserved_results_count,
        reports_retained_json_bytes=metrics.reports_retained_json_bytes,
        reports_retained_html_bytes=metrics.reports_retained_html_bytes,
        deduplication_ratio=metrics.deduplication_ratio,
        storage_savings_bytes=metrics.storage_savings_bytes
    )
