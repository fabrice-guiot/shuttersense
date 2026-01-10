"""
Pydantic schemas for results API request/response validation.

Provides data validation and serialization for:
- Analysis result listing with filtering
- Result details with tool-specific data
- Result statistics for KPIs

Design:
- Pagination support with limit/offset
- Tool-specific result schemas
- DateTime serialization for API responses
"""

from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from backend.src.models import ResultStatus


class SortField(str, Enum):
    """Sortable fields for results."""
    CREATED_AT = "created_at"
    DURATION_SECONDS = "duration_seconds"
    FILES_SCANNED = "files_scanned"


class SortOrder(str, Enum):
    """Sort direction."""
    ASC = "asc"
    DESC = "desc"


# ============================================================================
# Query Parameter Schemas
# ============================================================================

class ResultsQueryParams(BaseModel):
    """
    Query parameters for listing results.

    All parameters are optional for flexible filtering.
    """
    collection_guid: Optional[str] = Field(None, description="Filter by collection GUID (col_xxx)")
    tool: Optional[str] = Field(None, description="Filter by tool type")
    status: Optional[ResultStatus] = Field(None, description="Filter by status")
    from_date: Optional[date] = Field(None, description="Filter from date")
    to_date: Optional[date] = Field(None, description="Filter to date")
    limit: int = Field(50, ge=1, le=100, description="Maximum results to return")
    offset: int = Field(0, ge=0, description="Number of results to skip")
    sort_by: SortField = Field(SortField.CREATED_AT, description="Sort field")
    sort_order: SortOrder = Field(SortOrder.DESC, description="Sort direction")


# ============================================================================
# Response Schemas
# ============================================================================

class AnalysisResultSummary(BaseModel):
    """
    Summary of an analysis result for list views.

    Contains essential information without full result details.
    For pipeline-only results (display_graph mode), collection fields are null.
    """
    guid: str = Field(..., description="External identifier (res_xxx)")
    collection_guid: Optional[str] = Field(None, description="Collection GUID (col_xxx, null for display_graph)")
    collection_name: Optional[str] = Field(None, description="Collection name (null for display_graph)")
    tool: str = Field(..., description="Tool that produced this result")
    pipeline_guid: Optional[str] = Field(None, description="Pipeline GUID (pip_xxx) if applicable")
    pipeline_version: Optional[int] = Field(None, description="Pipeline version used")
    pipeline_name: Optional[str] = Field(None, description="Pipeline name if applicable")
    status: str = Field(..., description="Result status")
    started_at: datetime = Field(..., description="Execution start time")
    completed_at: datetime = Field(..., description="Execution end time")
    duration_seconds: float = Field(..., description="Execution duration")
    files_scanned: Optional[int] = Field(None, description="Files processed")
    issues_found: Optional[int] = Field(None, description="Issues detected")
    has_report: bool = Field(..., description="Whether HTML report is available")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "guid": "res_01hgw2bbg0000000000000003",
                    "collection_guid": "col_01hgw2bbg0000000000000001",
                    "collection_name": "Vacation 2024",
                    "tool": "pipeline_validation",
                    "pipeline_guid": "pip_01hgw2bbg0000000000000002",
                    "pipeline_version": 3,
                    "pipeline_name": "Standard RAW Workflow",
                    "status": "COMPLETED",
                    "started_at": "2024-01-15T10:30:00Z",
                    "completed_at": "2024-01-15T10:32:15Z",
                    "duration_seconds": 135.5,
                    "files_scanned": 1250,
                    "issues_found": 15,
                    "has_report": True
                },
                {
                    "guid": "res_01hgw2bbg0000000000000004",
                    "collection_guid": None,
                    "collection_name": None,
                    "tool": "pipeline_validation",
                    "pipeline_guid": "pip_01hgw2bbg0000000000000002",
                    "pipeline_version": 3,
                    "pipeline_name": "Standard RAW Workflow",
                    "status": "COMPLETED",
                    "started_at": "2024-01-15T11:00:00Z",
                    "completed_at": "2024-01-15T11:00:05Z",
                    "duration_seconds": 5.2,
                    "files_scanned": None,
                    "issues_found": 0,
                    "has_report": True
                }
            ]
        }
    }


class ResultListResponse(BaseModel):
    """
    Paginated list of analysis results.
    """
    items: List[AnalysisResultSummary] = Field(..., description="Result summaries")
    total: int = Field(..., ge=0, description="Total results matching filters")
    limit: int = Field(..., description="Results per page")
    offset: int = Field(..., description="Current offset")

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [],
                "total": 25,
                "limit": 50,
                "offset": 0
            }
        }
    }


class PhotoStatsResults(BaseModel):
    """PhotoStats tool-specific results."""
    total_size: int = Field(0, description="Total size in bytes")
    total_files: int = Field(0, description="Total file count")
    file_counts: Dict[str, int] = Field(default_factory=dict, description="Files by extension")
    orphaned_images: List[str] = Field(default_factory=list, description="Orphaned image files")
    orphaned_xmp: List[str] = Field(default_factory=list, description="Orphaned XMP files")


class PhotoPairingResults(BaseModel):
    """Photo Pairing tool-specific results."""
    group_count: int = Field(0, description="Number of image groups")
    image_count: int = Field(0, description="Total images in groups")
    camera_usage: Dict[str, int] = Field(default_factory=dict, description="Images per camera")


class PipelineValidationResults(BaseModel):
    """Pipeline Validation tool-specific results."""
    consistency_counts: Dict[str, int] = Field(
        default_factory=lambda: {"CONSISTENT": 0, "PARTIAL": 0, "INCONSISTENT": 0},
        description="Counts by consistency status"
    )


class AnalysisResultResponse(BaseModel):
    """
    Full analysis result details.

    Contains all result information including tool-specific results.
    For pipeline-only results (display_graph mode), collection fields are null.
    """
    guid: str = Field(..., description="External identifier (res_xxx)")
    collection_guid: Optional[str] = Field(None, description="Collection GUID (col_xxx, null for display_graph)")
    collection_name: Optional[str] = Field(None, description="Collection name (null for display_graph)")
    tool: str = Field(..., description="Tool that produced this result")
    pipeline_guid: Optional[str] = Field(None, description="Pipeline GUID (pip_xxx) if applicable")
    pipeline_version: Optional[int] = Field(None, description="Pipeline version used at execution time")
    pipeline_name: Optional[str] = Field(None, description="Pipeline name if applicable")
    status: str = Field(..., description="Result status")
    started_at: datetime = Field(..., description="Execution start time")
    completed_at: datetime = Field(..., description="Execution end time")
    duration_seconds: float = Field(..., description="Execution duration")
    files_scanned: Optional[int] = Field(None, description="Files processed")
    issues_found: Optional[int] = Field(None, description="Issues detected")
    error_message: Optional[str] = Field(None, description="Error details if failed")
    has_report: bool = Field(..., description="Whether HTML report is available")
    results: Dict[str, Any] = Field(..., description="Tool-specific results")
    created_at: datetime = Field(..., description="Record creation time")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "guid": "res_01hgw2bbg0000000000000003",
                "collection_guid": "col_01hgw2bbg0000000000000001",
                "collection_name": "Vacation 2024",
                "tool": "pipeline_validation",
                "pipeline_guid": "pip_01hgw2bbg0000000000000002",
                "pipeline_version": 3,
                "pipeline_name": "Standard RAW Workflow",
                "status": "COMPLETED",
                "started_at": "2024-01-15T10:30:00Z",
                "completed_at": "2024-01-15T10:32:15Z",
                "duration_seconds": 135.5,
                "files_scanned": 1250,
                "issues_found": 15,
                "has_report": True,
                "results": {
                    "consistency_counts": {"CONSISTENT": 1200, "PARTIAL": 35, "INCONSISTENT": 15}
                },
                "created_at": "2024-01-15T10:32:15Z"
            }
        }
    }


class ResultStatsResponse(BaseModel):
    """
    Results statistics for KPIs.

    Provides aggregate statistics across all results.
    """
    total_results: int = Field(0, ge=0, description="Total analysis results")
    completed_count: int = Field(0, ge=0, description="Completed results")
    failed_count: int = Field(0, ge=0, description="Failed results")
    by_tool: Dict[str, int] = Field(default_factory=dict, description="Results by tool type")
    last_run: Optional[datetime] = Field(None, description="Most recent execution time")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_results": 50,
                "completed_count": 45,
                "failed_count": 5,
                "by_tool": {
                    "photostats": 25,
                    "photo_pairing": 15,
                    "pipeline_validation": 10
                },
                "last_run": "2024-01-15T10:32:15Z"
            }
        }
    }


class DeleteResponse(BaseModel):
    """Response after deleting a result."""
    message: str = Field(..., description="Confirmation message")
    deleted_guid: str = Field(..., description="GUID of deleted result (res_xxx)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Result deleted successfully",
                "deleted_guid": "res_01hgw2bbg0000000000000003"
            }
        }
    }
