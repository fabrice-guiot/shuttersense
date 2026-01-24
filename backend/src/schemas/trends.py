"""
Pydantic schemas for trends API request/response validation.

Provides data validation and serialization for:
- PhotoStats trend data (orphaned files over time)
- Photo Pairing trend data (camera usage over time)
- Pipeline Validation trend data (consistency ratios over time)
- Trend summary for dashboard

Design:
- Collection-grouped trend data for comparison charts
- Date range filtering support
- Tool-specific metrics extraction from JSONB
"""

from datetime import datetime
from datetime import date as DateType
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================================
# Query Parameter Schemas
# ============================================================================

class TrendsQueryParams(BaseModel):
    """
    Query parameters for trend endpoints.

    All parameters are optional for flexible filtering.
    """
    collection_ids: Optional[str] = Field(
        None,
        description="Comma-separated collection IDs"
    )
    from_date: Optional[DateType] = Field(None, description="Filter from date")
    to_date: Optional[DateType] = Field(None, description="Filter to date")
    limit: int = Field(50, ge=1, le=500, description="Maximum data points per collection")


class PipelineValidationTrendsQueryParams(TrendsQueryParams):
    """Query parameters for pipeline validation trends."""
    pipeline_id: Optional[int] = Field(None, gt=0, description="Filter by pipeline ID")
    pipeline_version: Optional[int] = Field(None, gt=0, description="Filter by pipeline version")


# ============================================================================
# PhotoStats Trend Schemas
# ============================================================================

class PhotoStatsTrendPoint(BaseModel):
    """Single data point for PhotoStats trend chart (comparison mode)."""
    date: datetime = Field(..., description="Execution timestamp")
    result_id: int = Field(..., description="Result ID for drill-down")
    orphaned_images_count: int = Field(0, description="Count of orphaned images")
    orphaned_xmp_count: int = Field(0, description="Count of orphaned XMP files")
    total_files: int = Field(0, description="Total files scanned")
    total_size: int = Field(0, description="Total storage size in bytes")
    no_change_copy: bool = Field(False, description="Whether this is a NO_CHANGE copy result (Issue #92)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "date": "2024-01-15T10:30:00Z",
                "result_id": 1,
                "orphaned_images_count": 5,
                "orphaned_xmp_count": 3,
                "total_files": 1250,
                "total_size": 52428800000,
                "no_change_copy": False
            }
        }
    }


class CollectionTrendData(BaseModel):
    """PhotoStats trend data for a single collection (comparison mode)."""
    collection_id: int = Field(..., description="Collection ID")
    collection_name: str = Field(..., description="Collection name")
    data_points: List[PhotoStatsTrendPoint] = Field(
        default_factory=list,
        description="Trend data points"
    )


class PhotoStatsAggregatedPoint(BaseModel):
    """
    Aggregated data point for PhotoStats trend chart.

    Data is aggregated (summed) across all collections for each date.
    Two series: Orphaned Images and Orphaned Metadata (XMP).

    Values can be None for dates without data points (to show gaps in timeline).
    """
    date: DateType = Field(..., description="Date (aggregated, YYYY-MM-DD)")
    orphaned_images: Optional[int] = Field(None, description="Total orphaned images across all collections (None if no data)")
    orphaned_metadata: Optional[int] = Field(None, description="Total orphaned metadata files (XMP) across all collections (None if no data)")
    collections_included: int = Field(0, ge=0, description="Number of collections with data for this date")
    no_change_count: int = Field(0, ge=0, description="Count of NO_CHANGE results included for this date (Issue #92)")
    has_transition: bool = Field(False, description="Whether this date has an Input State transition (no_change_copy=false after no_change_copy=true period)")
    calculated_count: int = Field(0, ge=0, description="Number of collections with filled (calculated) values for this date (Issue #105). 0 means all collections have actual results.")


class PhotoStatsTrendResponse(BaseModel):
    """
    Response for PhotoStats trend endpoint.

    Supports two modes:
    - aggregated: When no collection filter or >5 collections (default)
    - comparison: When 1-5 specific collections are selected
    """
    mode: str = Field("aggregated", description="Response mode: 'aggregated' or 'comparison'")
    # Aggregated mode data
    data_points: List[PhotoStatsAggregatedPoint] = Field(
        default_factory=list,
        description="Aggregated trend data (used in aggregated mode)"
    )
    # Comparison mode data
    collections: List[CollectionTrendData] = Field(
        default_factory=list,
        description="Trend data grouped by collection (used in comparison mode)"
    )


# ============================================================================
# Photo Pairing Trend Schemas
# ============================================================================

class PhotoPairingTrendPoint(BaseModel):
    """Single data point for Photo Pairing trend chart (comparison mode)."""
    date: datetime = Field(..., description="Execution timestamp")
    result_id: int = Field(..., description="Result ID for drill-down")
    group_count: int = Field(0, description="Number of image groups")
    image_count: int = Field(0, description="Total images in groups")
    camera_usage: Dict[str, int] = Field(
        default_factory=dict,
        description="Map of camera_id to image count"
    )
    no_change_copy: bool = Field(False, description="Whether this is a NO_CHANGE copy result (Issue #92)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "date": "2024-01-15T10:30:00Z",
                "result_id": 1,
                "group_count": 450,
                "image_count": 1200,
                "camera_usage": {
                    "AB3D": 500,
                    "XY7Z": 400,
                    "PQ9R": 300
                },
                "no_change_copy": False
            }
        }
    }


class PhotoPairingCollectionTrend(BaseModel):
    """Photo Pairing trend data for a single collection (comparison mode)."""
    collection_id: int = Field(..., description="Collection ID")
    collection_name: str = Field(..., description="Collection name")
    cameras: List[str] = Field(
        default_factory=list,
        description="List of camera IDs found across all results"
    )
    data_points: List[PhotoPairingTrendPoint] = Field(
        default_factory=list,
        description="Trend data points"
    )


class PhotoPairingAggregatedPoint(BaseModel):
    """
    Aggregated data point for Photo Pairing trend chart.

    Data is aggregated (summed) across all collections for each date.
    Two series: Image Groups and Total Images.
    Camera usage is NOT aggregated (differs per collection).

    Values can be None for dates without data points (to show gaps in timeline).
    """
    date: DateType = Field(..., description="Date (aggregated, YYYY-MM-DD)")
    group_count: Optional[int] = Field(None, description="Total image groups across all collections (None if no data)")
    image_count: Optional[int] = Field(None, description="Total images across all collections (None if no data)")
    collections_included: int = Field(0, ge=0, description="Number of collections with data for this date")
    no_change_count: int = Field(0, ge=0, description="Count of NO_CHANGE results included for this date (Issue #92)")
    has_transition: bool = Field(False, description="Whether this date has an Input State transition (no_change_copy=false after no_change_copy=true period)")
    calculated_count: int = Field(0, ge=0, description="Number of collections with filled (calculated) values for this date (Issue #105). 0 means all collections have actual results.")


class PhotoPairingTrendResponse(BaseModel):
    """
    Response for Photo Pairing trend endpoint.

    Supports two modes:
    - aggregated: When no collection filter or >5 collections (default)
    - comparison: When 1-5 specific collections are selected
    """
    mode: str = Field("aggregated", description="Response mode: 'aggregated' or 'comparison'")
    # Aggregated mode data
    data_points: List[PhotoPairingAggregatedPoint] = Field(
        default_factory=list,
        description="Aggregated trend data (used in aggregated mode)"
    )
    # Comparison mode data
    collections: List[PhotoPairingCollectionTrend] = Field(
        default_factory=list,
        description="Trend data grouped by collection (used in comparison mode)"
    )


# ============================================================================
# Pipeline Validation Trend Schemas
# ============================================================================

class PipelineValidationTrendPoint(BaseModel):
    """Single data point for Pipeline Validation trend chart (comparison mode)."""
    date: datetime = Field(..., description="Execution timestamp")
    result_id: int = Field(..., description="Result ID for drill-down")
    pipeline_id: Optional[int] = Field(None, description="Pipeline ID")
    pipeline_name: Optional[str] = Field(None, description="Pipeline name")
    consistent_count: int = Field(0, description="CONSISTENT status count")
    partial_count: int = Field(0, description="PARTIAL status count")
    inconsistent_count: int = Field(0, description="INCONSISTENT status count")
    consistent_ratio: float = Field(0.0, description="Percentage CONSISTENT (0-100)")
    partial_ratio: float = Field(0.0, description="Percentage PARTIAL (0-100)")
    inconsistent_ratio: float = Field(0.0, description="Percentage INCONSISTENT (0-100)")
    no_change_copy: bool = Field(False, description="Whether this is a NO_CHANGE copy result (Issue #92)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "date": "2024-01-15T10:30:00Z",
                "result_id": 1,
                "pipeline_id": 1,
                "pipeline_name": "Standard RAW Workflow",
                "consistent_count": 1150,
                "partial_count": 75,
                "inconsistent_count": 25,
                "consistent_ratio": 92.0,
                "partial_ratio": 6.0,
                "inconsistent_ratio": 2.0,
                "no_change_copy": False
            }
        }
    }


class PipelineValidationCollectionTrend(BaseModel):
    """Pipeline Validation trend data for a single collection (comparison mode)."""
    collection_id: int = Field(..., description="Collection ID")
    collection_name: str = Field(..., description="Collection name")
    data_points: List[PipelineValidationTrendPoint] = Field(
        default_factory=list,
        description="Trend data points"
    )


class PipelineValidationAggregatedPoint(BaseModel):
    """
    Aggregated data point for Pipeline Validation trend chart.

    Data is aggregated across all collections for each date.
    Percentages are RECALCULATED from summed counts (not averaged).

    Series:
    - overall_consistency_pct: Total CONSISTENT / Total images
    - black_box_consistency_pct: CONSISTENT in Black Box Archive / Total Black Box
    - browsable_consistency_pct: CONSISTENT in Browsable Archive / Total Browsable
    - overall_inconsistent_pct: Total INCONSISTENT / Total images

    Values can be None for dates without data points (to show gaps in timeline).
    """
    date: DateType = Field(..., description="Date (aggregated, YYYY-MM-DD)")
    # Overall percentages (recalculated from summed counts)
    overall_consistency_pct: Optional[float] = Field(None, description="Overall consistency % across all collections (None if no data)")
    overall_inconsistent_pct: Optional[float] = Field(None, description="Overall inconsistent % across all collections (None if no data)")
    # Per-termination type percentages
    black_box_consistency_pct: Optional[float] = Field(None, description="Consistency % for Black Box Archive termination (None if no data)")
    browsable_consistency_pct: Optional[float] = Field(None, description="Consistency % for Browsable Archive termination (None if no data)")
    # Underlying counts (for debugging/tooltips)
    total_images: Optional[int] = Field(None, description="Total images validated (None if no data)")
    consistent_count: Optional[int] = Field(None, description="Total CONSISTENT count (None if no data)")
    inconsistent_count: Optional[int] = Field(None, description="Total INCONSISTENT count (None if no data)")
    collections_included: int = Field(0, ge=0, description="Number of collections with data for this date")
    no_change_count: int = Field(0, ge=0, description="Count of NO_CHANGE results included for this date (Issue #92)")
    has_transition: bool = Field(False, description="Whether this date has an Input State transition (no_change_copy=false after no_change_copy=true period)")
    calculated_count: int = Field(0, ge=0, description="Number of collections with filled (calculated) values for this date (Issue #105). 0 means all collections have actual results.")


class PipelineValidationTrendResponse(BaseModel):
    """
    Response for Pipeline Validation trend endpoint.

    Supports two modes:
    - aggregated: When no collection filter or >5 collections (default)
    - comparison: When 1-5 specific collections are selected
    """
    mode: str = Field("aggregated", description="Response mode: 'aggregated' or 'comparison'")
    # Aggregated mode data
    data_points: List[PipelineValidationAggregatedPoint] = Field(
        default_factory=list,
        description="Aggregated trend data (used in aggregated mode)"
    )
    # Comparison mode data
    collections: List[PipelineValidationCollectionTrend] = Field(
        default_factory=list,
        description="Trend data grouped by collection (used in comparison mode)"
    )


# ============================================================================
# Display Graph Trend Schemas
# ============================================================================

# Standard termination types - all pipelines must use these
TERMINATION_TYPES = ['Black Box Archive', 'Browsable Archive']


class DisplayGraphTrendPoint(BaseModel):
    """
    Aggregated data point for display-graph trend.

    Data is aggregated across all pipelines for each date.
    Values can be None for dates without data points (to show gaps in timeline).
    """
    date: DateType = Field(..., description="Date (aggregated, YYYY-MM-DD)")
    total_paths: Optional[int] = Field(None, description="Total paths enumerated (None if no data)")
    valid_paths: Optional[int] = Field(None, description="Valid paths (non-truncated) (None if no data)")
    black_box_archive_paths: Optional[int] = Field(None, description="Paths to Black Box Archive (None if no data)")
    browsable_archive_paths: Optional[int] = Field(None, description="Paths to Browsable Archive (None if no data)")


class PipelineIncluded(BaseModel):
    """Info about a pipeline included in aggregation."""
    pipeline_id: int = Field(..., description="Pipeline ID")
    pipeline_name: str = Field(..., description="Pipeline name")
    result_count: int = Field(0, ge=0, description="Number of results from this pipeline")


class DisplayGraphTrendResponse(BaseModel):
    """Response for display-graph trend endpoint."""
    data_points: List[DisplayGraphTrendPoint] = Field(
        default_factory=list,
        description="Aggregated trend data points"
    )
    pipelines_included: List[PipelineIncluded] = Field(
        default_factory=list,
        description="Pipelines included in aggregation"
    )


# ============================================================================
# Trend Summary Schema
# ============================================================================

class TrendDirection(str, Enum):
    """Direction of trend movement."""
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    INSUFFICIENT_DATA = "insufficient_data"


class DataPointCounts(BaseModel):
    """Count of data points available per tool."""
    photostats: int = Field(0, ge=0)
    photo_pairing: int = Field(0, ge=0)
    pipeline_validation: int = Field(0, ge=0)


class StablePeriodInfo(BaseModel):
    """Information about stable periods (consecutive NO_CHANGE results)."""
    photostats_stable: bool = Field(False, description="Whether latest PhotoStats result is NO_CHANGE")
    photostats_stable_days: int = Field(0, ge=0, description="Days in current stable period for PhotoStats")
    photo_pairing_stable: bool = Field(False, description="Whether latest Photo Pairing result is NO_CHANGE")
    photo_pairing_stable_days: int = Field(0, ge=0, description="Days in current stable period for Photo Pairing")
    pipeline_validation_stable: bool = Field(False, description="Whether latest Pipeline Validation result is NO_CHANGE")
    pipeline_validation_stable_days: int = Field(0, ge=0, description="Days in current stable period for Pipeline Validation")


class TrendSummaryResponse(BaseModel):
    """
    Trend summary for dashboard overview.

    Provides quick indicators of trend direction across tools.
    """
    collection_id: Optional[int] = Field(None, description="Collection ID (null for all)")
    orphaned_trend: TrendDirection = Field(
        TrendDirection.INSUFFICIENT_DATA,
        description="Trend direction for orphaned files"
    )
    consistency_trend: TrendDirection = Field(
        TrendDirection.INSUFFICIENT_DATA,
        description="Trend direction for consistency"
    )
    last_photostats: Optional[datetime] = Field(
        None,
        description="Most recent PhotoStats execution"
    )
    last_photo_pairing: Optional[datetime] = Field(
        None,
        description="Most recent Photo Pairing execution"
    )
    last_pipeline_validation: Optional[datetime] = Field(
        None,
        description="Most recent Pipeline Validation execution"
    )
    data_points_available: DataPointCounts = Field(
        default_factory=DataPointCounts,
        description="Count of data points per tool"
    )
    stable_periods: StablePeriodInfo = Field(
        default_factory=StablePeriodInfo,
        description="Information about stable periods (consecutive NO_CHANGE results)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "collection_id": 1,
                "orphaned_trend": "improving",
                "consistency_trend": "stable",
                "last_photostats": "2024-01-15T10:30:00Z",
                "last_photo_pairing": "2024-01-15T10:45:00Z",
                "last_pipeline_validation": "2024-01-15T11:00:00Z",
                "data_points_available": {
                    "photostats": 15,
                    "photo_pairing": 12,
                    "pipeline_validation": 10
                }
            }
        }
    }
