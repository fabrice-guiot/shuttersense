"""
Pydantic schemas for tools API request/response validation.

Provides data validation and serialization for:
- Tool run requests
- Job status responses
- Progress data
- Queue status

Design:
- Strict enum validation for tool types and job status
- UUID format for job IDs
- Optional fields with sensible defaults
- DateTime serialization for API responses
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID
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
        collection_id: ID of the collection to analyze (required for collection mode)
        pipeline_id: Pipeline ID (required for display_graph mode)
        mode: Execution mode for pipeline_validation (optional, defaults to collection)

    Mode-specific requirements:
        - PhotoStats/Photo Pairing: collection_id required, mode ignored
        - Pipeline Validation (collection): collection_id required, pipeline resolved from collection
        - Pipeline Validation (display_graph): pipeline_id required, no collection needed

    Example (PhotoStats):
        >>> request = ToolRunRequest(collection_id=1, tool=ToolType.PHOTOSTATS)

    Example (Pipeline Validation - display_graph):
        >>> request = ToolRunRequest(
        ...     tool=ToolType.PIPELINE_VALIDATION,
        ...     mode=ToolMode.DISPLAY_GRAPH,
        ...     pipeline_id=1
        ... )
    """
    tool: ToolType = Field(..., description="Tool to run")
    collection_id: Optional[int] = Field(
        None,
        gt=0,
        description="ID of the collection to analyze (required for collection mode)"
    )
    pipeline_id: Optional[int] = Field(
        None,
        gt=0,
        description="Pipeline ID (required for display_graph mode)"
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
                    "collection_id": 1
                },
                {
                    "tool": "pipeline_validation",
                    "mode": "display_graph",
                    "pipeline_id": 1
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
    and result_id for completed jobs.
    """
    id: UUID = Field(..., description="Unique job identifier")
    collection_id: Optional[int] = Field(None, description="Collection being analyzed (null for display_graph)")
    tool: ToolType = Field(..., description="Tool being run")
    mode: Optional[ToolMode] = Field(None, description="Execution mode (for pipeline_validation)")
    pipeline_id: Optional[int] = Field(None, description="Pipeline ID if applicable")
    status: JobStatus = Field(..., description="Current job status")
    position: Optional[int] = Field(None, ge=1, description="Queue position if queued")
    created_at: datetime = Field(..., description="Job creation time")
    started_at: Optional[datetime] = Field(None, description="Execution start time")
    completed_at: Optional[datetime] = Field(None, description="Execution end time")
    progress: Optional[ProgressData] = Field(None, description="Progress data if running")
    error_message: Optional[str] = Field(None, description="Error details if failed")
    result_id: Optional[int] = Field(None, description="Analysis result ID when completed")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "collection_id": 1,
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
    current_job_id: Optional[UUID] = Field(None, description="Currently running job ID")

    model_config = {
        "json_schema_extra": {
            "example": {
                "queued_count": 2,
                "running_count": 1,
                "completed_count": 10,
                "failed_count": 1,
                "cancelled_count": 0,
                "current_job_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    }


class ConflictResponse(BaseModel):
    """
    Response when a tool is already running on a collection.
    """
    message: str = Field(..., description="Conflict description")
    existing_job_id: UUID = Field(..., description="ID of the existing job")
    position: Optional[int] = Field(None, description="Queue position of existing job")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Tool photostats is already running on collection 1",
                "existing_job_id": "550e8400-e29b-41d4-a716-446655440000",
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
                        "collection_id": 1,
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
