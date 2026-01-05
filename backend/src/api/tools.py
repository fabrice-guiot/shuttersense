"""
Tools API endpoints for job management and tool execution.

Provides endpoints for:
- Running analysis tools on collections
- Managing job queue
- Monitoring job progress via WebSocket
- Cancelling queued jobs

Design:
- Uses dependency injection for services
- Async endpoints for non-blocking execution
- WebSocket support for real-time progress
- Comprehensive error handling
"""

import asyncio
from typing import List, Optional
from uuid import UUID

from fastapi import (
    APIRouter, Depends, HTTPException, Query, Request, WebSocket,
    WebSocketDisconnect, BackgroundTasks, status
)
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.schemas.tools import (
    ToolType, JobStatus, ToolRunRequest, JobResponse,
    QueueStatusResponse, ConflictResponse, RunAllToolsResponse
)
from backend.src.services.tool_service import ToolService
from backend.src.services.exceptions import ConflictError, NotFoundError, CollectionNotAccessibleError
from backend.src.utils.websocket import ConnectionManager, get_connection_manager
from backend.src.utils.logging_config import get_logger


logger = get_logger("api")

router = APIRouter(
    prefix="/tools",
    tags=["Tools"],
)


# ============================================================================
# Dependencies
# ============================================================================

def get_websocket_manager(request: Request) -> ConnectionManager:
    """Get WebSocket connection manager from application state."""
    return request.app.state.websocket_manager


def get_encryptor(request: Request):
    """Get credential encryptor from application state."""
    return request.app.state.credential_encryptor


def get_tool_service(
    db: Session = Depends(get_db),
    ws_manager: ConnectionManager = Depends(get_websocket_manager),
    encryptor = Depends(get_encryptor)
) -> ToolService:
    """Create ToolService instance with dependencies."""
    return ToolService(db=db, websocket_manager=ws_manager, encryptor=encryptor)


# ============================================================================
# Tool Execution Endpoints
# ============================================================================

@router.post(
    "/run",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start tool execution",
    responses={
        202: {"description": "Job accepted and queued"},
        400: {"description": "Invalid request"},
        409: {"description": "Tool already running on collection", "model": ConflictResponse},
    }
)
async def run_tool(
    request: ToolRunRequest,
    background_tasks: BackgroundTasks,
    service: ToolService = Depends(get_tool_service)
) -> JobResponse:
    """
    Start a tool execution on a collection.

    Creates a new job and adds it to the execution queue.
    Returns immediately with job details; use WebSocket or
    polling to monitor progress.

    Args:
        request: Tool run request with collection_id, tool, and optional pipeline_id

    Returns:
        Created job details

    Raises:
        400: Invalid request (missing required fields, invalid tool)
        409: Tool already running on this collection
    """
    try:
        job = service.run_tool(
            collection_id=request.collection_id,
            tool=request.tool,
            pipeline_id=request.pipeline_id
        )

        # Start processing queue in background
        background_tasks.add_task(service.process_queue)

        logger.info(f"Job {job.id} queued: {request.tool.value} on collection {request.collection_id}")
        return job

    except CollectionNotAccessibleError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": e.message,
                "collection_id": e.collection_id,
                "collection_name": e.collection_name
            }
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": e.message,
                "existing_job_id": str(e.existing_job_id) if e.existing_job_id else None,
                "position": e.position
            }
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/run-all/{collection_id}",
    response_model=RunAllToolsResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Run all analysis tools on a collection",
    responses={
        202: {"description": "Jobs accepted and queued"},
        404: {"description": "Collection not found"},
        422: {"description": "Collection not accessible"},
    }
)
async def run_all_tools(
    collection_id: int,
    background_tasks: BackgroundTasks,
    service: ToolService = Depends(get_tool_service)
) -> RunAllToolsResponse:
    """
    Run all available analysis tools on a collection.

    Queues photostats and photo_pairing tools for execution.
    Pipeline validation is excluded as it requires a pipeline_id.

    For inaccessible collections, returns 422 with a warning message.
    Tools already running on the collection are skipped.

    Args:
        collection_id: ID of the collection to analyze

    Returns:
        List of created jobs and any skipped tools
    """
    # Tools to run (excluding pipeline_validation which requires pipeline_id)
    tools_to_run = [ToolType.PHOTOSTATS, ToolType.PHOTO_PAIRING]

    created_jobs = []
    skipped_tools = []

    for tool in tools_to_run:
        try:
            job = service.run_tool(
                collection_id=collection_id,
                tool=tool
            )
            created_jobs.append(job)
            logger.info(f"Job {job.id} queued: {tool.value} on collection {collection_id}")
        except CollectionNotAccessibleError as e:
            # If collection is not accessible, fail immediately
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": f"Cannot run tools: {e.message}",
                    "collection_id": e.collection_id,
                    "collection_name": e.collection_name
                }
            )
        except ConflictError:
            # Tool already running - skip it
            skipped_tools.append(tool.value)
            logger.info(f"Skipped {tool.value} on collection {collection_id}: already running")
        except ValueError as e:
            # Collection not found - fail immediately
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )

    # Start processing queue in background (only if we created jobs)
    if created_jobs:
        background_tasks.add_task(service.process_queue)

    # Build summary message
    queued_count = len(created_jobs)
    skipped_count = len(skipped_tools)

    if queued_count == 0:
        message = f"No jobs queued, {skipped_count} skipped (already running)"
    elif skipped_count == 0:
        message = f"{queued_count} analysis job{'s' if queued_count > 1 else ''} queued"
    else:
        message = f"{queued_count} job{'s' if queued_count > 1 else ''} queued, {skipped_count} skipped (already running)"

    return RunAllToolsResponse(
        jobs=created_jobs,
        skipped=skipped_tools,
        message=message
    )


# ============================================================================
# Job Management Endpoints
# ============================================================================

@router.get(
    "/jobs",
    response_model=List[JobResponse],
    summary="List all jobs"
)
def list_jobs(
    status: Optional[JobStatus] = Query(None, description="Filter by status"),
    collection_id: Optional[int] = Query(None, description="Filter by collection"),
    tool: Optional[ToolType] = Query(None, description="Filter by tool"),
    service: ToolService = Depends(get_tool_service)
) -> List[JobResponse]:
    """
    List all jobs with optional filtering.

    Returns jobs in descending order by creation time.

    Args:
        status: Filter by job status (queued, running, completed, failed, cancelled)
        collection_id: Filter by collection ID
        tool: Filter by tool type

    Returns:
        List of job details
    """
    jobs = service.list_jobs(
        status=status,
        collection_id=collection_id,
        tool=tool
    )
    return jobs


@router.get(
    "/jobs/{job_id}",
    response_model=JobResponse,
    summary="Get job details"
)
def get_job(
    job_id: UUID,
    service: ToolService = Depends(get_tool_service)
) -> JobResponse:
    """
    Get details for a specific job.

    Args:
        job_id: Job identifier

    Returns:
        Job details including progress if running

    Raises:
        404: Job not found
    """
    job = service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    return job


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=JobResponse,
    summary="Cancel a queued job"
)
def cancel_job(
    job_id: UUID,
    service: ToolService = Depends(get_tool_service)
) -> JobResponse:
    """
    Cancel a queued job.

    Only queued jobs can be cancelled. Running jobs cannot be
    safely interrupted.

    Args:
        job_id: Job identifier

    Returns:
        Updated job details

    Raises:
        400: Job is running and cannot be cancelled
        404: Job not found
    """
    try:
        job = service.cancel_job(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        logger.info(f"Job {job_id} cancelled")
        return job
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/queue/status",
    response_model=QueueStatusResponse,
    summary="Get queue status"
)
def get_queue_status(
    service: ToolService = Depends(get_tool_service)
) -> QueueStatusResponse:
    """
    Get queue statistics.

    Returns counts of jobs by status and the currently
    running job ID if any.

    Returns:
        Queue status with job counts
    """
    stats = service.get_queue_status()
    return QueueStatusResponse(**stats)


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@router.websocket("/ws/jobs/{job_id}")
async def job_progress_websocket(
    websocket: WebSocket,
    job_id: UUID,
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time job progress updates.

    Connect to receive progress updates for a specific job.
    Messages are JSON objects with job status and progress data.

    Message format:
    {
        "job_id": "uuid",
        "status": "running",
        "progress": {
            "stage": "scanning",
            "files_scanned": 150,
            "total_files": 500,
            "percentage": 30.0
        }
    }
    """
    manager = get_connection_manager()

    await manager.connect(str(job_id), websocket)
    logger.info(f"WebSocket connected for job {job_id}")

    try:
        # Keep connection alive and receive any client messages
        while True:
            try:
                # Wait for client messages (heartbeat, close, etc.)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0  # 30 second timeout
                )
                # Echo heartbeat
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                try:
                    await websocket.send_text('{"type": "heartbeat"}')
                except Exception:
                    break
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job {job_id}")
    finally:
        manager.disconnect(str(job_id), websocket)
