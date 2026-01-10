"""
Pydantic schemas for tools API request/response validation.

Provides data validation and serialization for:
- Tool run requests
- Job status responses
- Progress data
- Queue status

Design:
- Strict enum validation for tool types and job status
- GUID format for job IDs (job_xxx with Crockford Base32 encoding)
- Optional fields with sensible defaults
- DateTime serialization for API responses
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ToolType(str, Enum):
    """Available analysis tools."""
    PHOTOSTATS = "photostats"
    PHOTO_PAIRING = "photo_pairing"
    PIPELINE_VALIDATION = "pipeline_validation"


class ToolMode(str, Enum):
    """Execution mode for pipeline validation tool."""
    COLLECTION = "collection"      # Validate files in a collection against pipeline
    DISPLAY_GRAPH = "display_graph"  # Validate pipeline definition only (no collection)


class JobStatus(str, Enum):
    """Job execution status."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# Request Schemas
# ============================================================================

class ToolRunRequest(BaseModel):
    """
    Request to start a tool execution.

    Fields:
        tool: Tool to run (required)
        collection_guid: GUID of the collection to analyze (required for collection mode)
        pipeline_guid: Pipeline GUID (required for display_graph mode)
        mode: Execution mode for pipeline_validation (optional, defaults to collection)

    Mode-specific requirements:
        - PhotoStats/Photo Pairing: collection_guid required, mode ignored
        - Pipeline Validation (collection): collection_guid required, pipeline resolved from collection
        - Pipeline Validation (display_graph): pipeline_guid required, no collection needed

    Example (PhotoStats):
        >>> request = ToolRunRequest(collection_guid="col_xxx", tool=ToolType.PHOTOSTATS)

    Example (Pipeline Validation - display_graph):
        >>> request = ToolRunRequest(
        ...     tool=ToolType.PIPELINE_VALIDATION,
        ...     mode=ToolMode.DISPLAY_GRAPH,
        ...     pipeline_guid="pip_xxx"
        ... )
    """
    tool: ToolType = Field(..., description="Tool to run")
    collection_guid: Optional[str] = Field(
        None,
        pattern=r"^col_[0-9a-hjkmnp-tv-z]{26}$",
        description="GUID of the collection to analyze (col_xxx format, required for collection mode)"
    )
    pipeline_guid: Optional[str] = Field(
        None,
        pattern=r"^pip_[0-9a-hjkmnp-tv-z]{26}$",
        description="Pipeline GUID (pip_xxx format, required for display_graph mode)"
    )
    mode: Optional[ToolMode] = Field(
        None,
        description="Execution mode for pipeline_validation (defaults to collection)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tool": "photostats",
                    "collection_guid": "col_01hgw2bbg0000000000000001"
                },
                {
                    "tool": "pipeline_validation",
                    "mode": "display_graph",
                    "pipeline_guid": "pip_01hgw2bbg0000000000000001"
                }
            ]
        }
    }


# ============================================================================
# Response Schemas
# ============================================================================

class ProgressData(BaseModel):
    """
    Progress data for a running job.

    Fields:
        stage: Current processing stage
        files_scanned: Number of files processed so far (None for display_graph mode)
        total_files: Total files to process (None for display_graph mode)
        issues_found: Issues detected so far
        percentage: Completion percentage (0-100)
    """
    stage: str = Field("initializing", description="Current stage")
    files_scanned: Optional[int] = Field(None, ge=0, description="Files processed (null for display_graph)")
    total_files: Optional[int] = Field(None, ge=0, description="Total files (null for display_graph)")
    issues_found: int = Field(0, ge=0, description="Issues found")
    percentage: float = Field(0.0, ge=0, le=100, description="Completion percentage")


class JobResponse(BaseModel):
    """
    Job status response.

    Contains full job state including progress for running jobs
    and result_guid for completed jobs.
    """
    id: str = Field(..., description="Unique job identifier (job_xxx GUID format)")
    collection_guid: Optional[str] = Field(None, description="Collection GUID being analyzed (null for display_graph)")
    tool: ToolType = Field(..., description="Tool being run")
    mode: Optional[ToolMode] = Field(None, description="Execution mode (for pipeline_validation)")
    pipeline_guid: Optional[str] = Field(None, description="Pipeline GUID if applicable")
    status: JobStatus = Field(..., description="Current job status")
    position: Optional[int] = Field(None, ge=1, description="Queue position if queued")
    created_at: datetime = Field(..., description="Job creation time")
    started_at: Optional[datetime] = Field(None, description="Execution start time")
    completed_at: Optional[datetime] = Field(None, description="Execution end time")
    progress: Optional[ProgressData] = Field(None, description="Progress data if running")
    error_message: Optional[str] = Field(None, description="Error details if failed")
    result_guid: Optional[str] = Field(None, description="Analysis result GUID when completed")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "job_01hgw2bbg0000000000000001",
                "collection_guid": "col_01hgw2bbg0000000000000001",
                "tool": "photostats",
                "status": "running",
                "created_at": "2024-01-15T10:30:00Z",
                "started_at": "2024-01-15T10:30:05Z",
                "progress": {
                    "stage": "scanning",
                    "files_scanned": 150,
                    "total_files": 500,
                    "issues_found": 3,
                    "percentage": 30.0
                }
            }
        }
    }


class QueueStatusResponse(BaseModel):
    """
    Queue status statistics.

    Provides counts for each job state and the current running job ID.
    """
    queued_count: int = Field(0, ge=0, description="Jobs waiting in queue")
    running_count: int = Field(0, ge=0, description="Currently running jobs")
    completed_count: int = Field(0, ge=0, description="Completed jobs")
    failed_count: int = Field(0, ge=0, description="Failed jobs")
    cancelled_count: int = Field(0, ge=0, description="Cancelled jobs")
    current_job_id: Optional[str] = Field(None, description="Currently running job ID (job_xxx GUID format)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "queued_count": 2,
                "running_count": 1,
                "completed_count": 10,
                "failed_count": 1,
                "cancelled_count": 0,
                "current_job_id": "job_01hgw2bbg0000000000000001"
            }
        }
    }


class ConflictResponse(BaseModel):
    """
    Response when a tool is already running on a collection.
    """
    message: str = Field(..., description="Conflict description")
    existing_job_id: str = Field(..., description="ID of the existing job (job_xxx GUID format)")
    position: Optional[int] = Field(None, description="Queue position of existing job")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Tool photostats is already running on collection col_01hgw2bbg0000000000000001",
                "existing_job_id": "job_01hgw2bbg0000000000000001",
                "position": None
            }
        }
    }


class RunAllToolsResponse(BaseModel):
    """
    Response for running all tools on a collection.

    Returns the list of created jobs and any tools that were skipped
    (e.g., due to already running).
    """
    jobs: list[JobResponse] = Field(..., description="List of created jobs")
    skipped: list[str] = Field(default_factory=list, description="Tools skipped (already running)")
    message: str = Field(..., description="Summary message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "jobs": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "collection_guid": "col_01hgw2bbg0000000000000001",
                        "tool": "photostats",
                        "status": "queued",
                        "position": 1,
                        "created_at": "2024-01-15T10:30:00Z"
                    }
                ],
                "skipped": ["photo_pairing"],
                "message": "1 job queued, 1 skipped (already running)"
            }
        }
    }
