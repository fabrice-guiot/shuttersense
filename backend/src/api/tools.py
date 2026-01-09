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
- Rate limiting to prevent resource exhaustion (T168)
"""

import asyncio
from typing import List, Optional
from uuid import UUID

from fastapi import (
    APIRouter, Depends, HTTPException, Query, Request, WebSocket,
    WebSocketDisconnect, status
)
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.schemas.tools import (
    ToolType, ToolMode, JobStatus, ToolRunRequest, JobResponse,
    QueueStatusResponse, ConflictResponse, RunAllToolsResponse
)
from backend.src.services.tool_service import ToolService
from backend.src.services.exceptions import ConflictError, CollectionNotAccessibleError
from backend.src.utils.websocket import ConnectionManager, get_connection_manager
from backend.src.utils.logging_config import get_logger


logger = get_logger("api")

router = APIRouter(
    prefix="/tools",
    tags=["Tools"],
)

# Rate limiter instance - shared from main app
limiter = Limiter(key_func=get_remote_address)


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
        429: {"description": "Too many requests - rate limit exceeded"},
    }
)
@limiter.limit("10/minute")  # Rate limit: 10 tool executions per minute (T168)
async def run_tool(
    request: Request,  # Required for rate limiter - must be named 'request'
    tool_request: ToolRunRequest = ...,  # Body parameter renamed to avoid conflict
    service: ToolService = Depends(get_tool_service)
) -> JobResponse:
    """
    Start a tool execution.

    Creates a new job and adds it to the execution queue.
    Returns immediately with job details; use WebSocket or
    polling to monitor progress.

    For most tools, collection_id is required. For pipeline_validation
    in display_graph mode, pipeline_id is required instead.

    Args:
        tool_request: Tool run request with tool, and mode-specific parameters

    Returns:
        Created job details

    Raises:
        400: Invalid request (missing required fields, invalid tool)
        409: Tool already running on this collection/pipeline
    """
    import asyncio

    try:
        job = service.run_tool(
            tool=tool_request.tool,
            collection_id=tool_request.collection_id,
            pipeline_id=tool_request.pipeline_id,
            mode=tool_request.mode
        )

        # Start processing queue in background using asyncio.create_task
        # This ensures the task runs truly asynchronously without blocking the response
        asyncio.create_task(service.process_queue())

        # Log appropriately based on mode
        if tool_request.mode == ToolMode.DISPLAY_GRAPH:
            logger.info(f"Job {job.id} queued: {tool_request.tool.value} (display_graph) on pipeline {tool_request.pipeline_id}")
        else:
            logger.info(f"Job {job.id} queued: {tool_request.tool.value} on collection {tool_request.collection_id}")
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
        429: {"description": "Too many requests - rate limit exceeded"},
    }
)
@limiter.limit("5/minute")  # Rate limit: 5 run-all requests per minute (T168)
async def run_all_tools(
    request: Request,  # Required for rate limiter
    collection_id: int,
    service: ToolService = Depends(get_tool_service)
) -> RunAllToolsResponse:
    """
    Run all available analysis tools on a collection.

    Queues photostats, photo_pairing, and pipeline_validation tools for execution.
    Pipeline validation uses the default pipeline if none is specified.

    For inaccessible collections, returns 422 with a warning message.
    Tools already running on the collection are skipped.

    Args:
        collection_id: ID of the collection to analyze

    Returns:
        List of created jobs and any skipped tools
    """
    # Tools to run (pipeline_validation uses default pipeline)
    tools_to_run = [ToolType.PHOTOSTATS, ToolType.PHOTO_PAIRING, ToolType.PIPELINE_VALIDATION]

    created_jobs = []
    skipped_tools = []

    for tool in tools_to_run:
        try:
            job = service.run_tool(
                tool=tool,
                collection_id=collection_id
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
            error_msg = str(e)
            # For pipeline_validation, skip if no default pipeline is configured
            if tool == ToolType.PIPELINE_VALIDATION and "default pipeline" in error_msg.lower():
                skipped_tools.append(tool.value)
                logger.info(f"Skipped {tool.value} on collection {collection_id}: no default pipeline configured")
            elif "not found" in error_msg.lower() and "collection" in error_msg.lower():
                # Collection not found - fail immediately
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_msg
                )
            else:
                # Other ValueError - skip this tool but continue
                skipped_tools.append(tool.value)
                logger.warning(f"Skipped {tool.value} on collection {collection_id}: {error_msg}")

    # Start processing queue in background (only if we created jobs)
    if created_jobs:
        asyncio.create_task(service.process_queue())

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

@router.websocket("/ws/jobs/all")
async def global_jobs_websocket(
    websocket: WebSocket
):
    """
    WebSocket endpoint for real-time job list updates.

    Connect to receive updates for all jobs. This eliminates the need
    for polling the jobs list endpoint.

    Messages are JSON objects with job updates:
    {
        "type": "job_update",
        "job": { ...full job object... }
    }
    """
    manager = get_connection_manager()
    channel_id = manager.GLOBAL_JOBS_CHANNEL

    await manager.connect(channel_id, websocket)
    logger.info("WebSocket connected for global jobs channel")

    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                try:
                    await websocket.send_text('{"type": "heartbeat"}')
                except Exception:
                    break
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected from global jobs channel")
    finally:
        manager.disconnect(channel_id, websocket)


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
