"""
Agent API routes for distributed agent architecture.

This module defines REST endpoints for agent operations:
- Registration (using one-time tokens)
- Heartbeat updates
- Job claiming and execution (Phase 3)
- Progress reporting (Phase 3)

API version: v1
Base path: /api/agent/v1
"""

import asyncio
import logging
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from backend.src.utils.websocket import get_connection_manager
from backend.src.services.tool_service import _db_job_to_response

from backend.src.db.database import get_db
from backend.src.middleware.tenant import TenantContext, get_tenant_context
from backend.src.services.agent_service import AgentService
from backend.src.services.connector_service import ConnectorService
from backend.src.api.connectors import get_connector_service
from backend.src.services.exceptions import NotFoundError, ValidationError as ServiceValidationError
from backend.src.models.connector import CredentialLocation
from backend.src.api.agent.schemas import (
    # Registration
    AgentRegistrationRequest,
    AgentRegistrationResponse,
    RegistrationTokenCreateRequest,
    RegistrationTokenResponse,
    RegistrationTokenListItem,
    RegistrationTokenListResponse,
    # Heartbeat
    HeartbeatRequest,
    HeartbeatResponse,
    # Agent management
    AgentResponse,
    AgentListResponse,
    AgentPoolStatusResponse,
    AgentUpdateRequest,
    AgentMetrics,
    # Agent detail (Phase 11)
    AgentDetailResponse,
    AgentJobHistoryItem,
    AgentJobHistoryResponse,
    # Job schemas (Phase 5)
    JobClaimResponse,
    JobProgressRequest,
    JobCompleteWithUploadRequest,
    JobFailRequest,
    JobNoChangeRequest,  # Storage Optimization (Issue #92)
    PreviousResultData,   # Storage Optimization (Issue #92)
    JobStatusResponse,
    JobConfigData,
    JobConfigResponse,
    PipelineData,
    ConnectorTestData,
    # Connector schemas (Phase 8)
    AgentConnectorResponse,
    AgentConnectorListResponse,
    AgentConnectorMetadataResponse,
    ReportConnectorCapabilityRequest,
    ReportConnectorCapabilityResponse,
    # Chunked upload schemas (Phase 15)
    InitiateUploadRequest,
    InitiateUploadResponse,
    ChunkUploadResponse,
    FinalizeUploadRequest,
    FinalizeUploadResponse,
    UploadStatusResponse,
    # Inventory validation schemas (Issue #107)
    InventoryValidationRequest,
    InventoryValidationResponse,
    # Inventory folders schemas (Issue #107)
    InventoryFoldersRequest,
    InventoryFoldersResponse,
)
from backend.src.api.agent.dependencies import AgentContext, get_agent_context, require_online_agent


# Create router with prefix and tags
router = APIRouter(prefix="/api/agent/v1", tags=["agents"])


# ============================================================================
# Helper Functions
# ============================================================================

def get_agent_service(db: Session = Depends(get_db)) -> AgentService:
    """Dependency to get AgentService."""
    return AgentService(db)


def agent_to_response(
    agent,
    current_job_guid: str = None,
    running_jobs_count: int = 0
) -> AgentResponse:
    """Convert Agent model to response schema."""
    from backend.src.api.agent.schemas import AgentMetrics

    # Convert metrics dict to schema if present
    metrics = None
    if agent.metrics:
        # Filter out the timestamp field for the schema
        metrics_data = {k: v for k, v in agent.metrics.items() if k != "metrics_updated_at"}
        metrics = AgentMetrics(**metrics_data) if metrics_data else None

    return AgentResponse(
        guid=agent.guid,
        name=agent.name,
        hostname=agent.hostname,
        os_info=agent.os_info,
        status=agent.status,
        error_message=agent.error_message,
        last_heartbeat=agent.last_heartbeat,
        capabilities=agent.capabilities,
        authorized_roots=agent.authorized_roots,
        version=agent.version,
        created_at=agent.created_at,
        team_guid=agent.team.guid if agent.team else "",
        current_job_guid=current_job_guid,
        metrics=metrics,
        running_jobs_count=running_jobs_count,
    )


# ============================================================================
# Public Endpoints (No Auth Required)
# ============================================================================

@router.post(
    "/register",
    response_model=AgentRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new agent",
    description="Register a new agent using a one-time registration token. "
                "The API key is only returned once - store it securely."
)
async def register_agent(
    data: AgentRegistrationRequest,
    service: AgentService = Depends(get_agent_service),
):
    """
    Register a new agent using a one-time registration token.

    This endpoint is public (no auth required) because the agent doesn't
    have credentials yet - it's obtaining them through registration.

    The registration token was generated by an admin through the web UI.
    """
    import logging
    logger = logging.getLogger("agent")

    try:
        result = service.register_agent(
            plaintext_token=data.registration_token,
            name=data.name,
            hostname=data.hostname,
            os_info=data.os_info,
            capabilities=data.capabilities,
            authorized_roots=data.authorized_roots,
            version=data.version,
            binary_checksum=data.binary_checksum,
            platform=data.platform,
            development_mode=data.development_mode,
        )

        # Broadcast pool status update after registration
        if result.agent.team_id:
            pool_status = service.get_pool_status(result.agent.team_id)
            manager = get_connection_manager()
            asyncio.create_task(
                manager.broadcast_agent_pool_status(result.agent.team_id, pool_status)
            )

        return AgentRegistrationResponse(
            guid=result.agent.guid,
            api_key=result.api_key,
            name=result.agent.name,
            team_guid=result.agent.team.guid if result.agent.team else "",
            authorized_roots=result.agent.authorized_roots,
        )

    except ServiceValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.exception(f"Unexpected error during agent registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


# ============================================================================
# Agent-Authenticated Endpoints
# ============================================================================

@router.post(
    "/heartbeat",
    response_model=HeartbeatResponse,
    summary="Send agent heartbeat",
    description="Send periodic heartbeat to maintain online status. "
                "Agents should send heartbeat every 30 seconds."
)
async def send_heartbeat(
    data: HeartbeatRequest,
    ctx: AgentContext = Depends(get_agent_context),
    service: AgentService = Depends(get_agent_service),
):
    """
    Process agent heartbeat.

    Updates agent status, last_heartbeat timestamp, and optionally
    capabilities/version if changed. Also updates job progress if provided.
    """
    # Get agent from database
    agent = service.get_agent_by_guid(ctx.agent_guid, ctx.team_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Process heartbeat
    # Note: current_job_guid and progress are handled via job service (Phase 3)
    # Convert metrics to dict if provided
    metrics_dict = None
    if data.metrics:
        metrics_dict = data.metrics.model_dump(exclude_none=True)

    service.process_heartbeat(
        agent=agent,
        status=data.status,
        capabilities=data.capabilities,
        authorized_roots=data.authorized_roots,
        version=data.version,
        error_message=data.error_message,
        metrics=metrics_dict,
    )

    # Get pending commands for this agent
    pending_commands = service.get_and_clear_commands(ctx.agent_id)

    # Broadcast pool status update to connected clients (T059)
    pool_status = service.get_pool_status(ctx.team_id)
    manager = get_connection_manager()
    asyncio.create_task(
        manager.broadcast_agent_pool_status(ctx.team_id, pool_status)
    )

    return HeartbeatResponse(
        acknowledged=True,
        server_time=datetime.utcnow(),
        pending_commands=pending_commands,
    )


@router.get(
    "/me",
    response_model=AgentResponse,
    summary="Get current agent info",
    description="Get information about the currently authenticated agent."
)
async def get_current_agent(
    ctx: AgentContext = Depends(get_agent_context),
    service: AgentService = Depends(get_agent_service),
):
    """Get information about the currently authenticated agent."""
    agent = service.get_agent_by_guid(ctx.agent_guid, ctx.team_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # TODO: Get current job GUID if any (Phase 3)
    return agent_to_response(agent)


@router.post(
    "/disconnect",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect agent",
    description="Gracefully disconnect the agent and mark it as offline. "
                "Called by the agent during shutdown."
)
async def disconnect_agent(
    ctx: AgentContext = Depends(get_agent_context),
    service: AgentService = Depends(get_agent_service),
):
    """
    Gracefully disconnect the agent.

    Called by the agent when it's shutting down. This immediately marks
    the agent as OFFLINE and releases any assigned jobs.
    """
    agent = service.get_agent_by_guid(ctx.agent_guid, ctx.team_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    service.disconnect_agent(agent)

    # Broadcast pool status update after disconnect
    pool_status = service.get_pool_status(ctx.team_id)
    manager = get_connection_manager()
    asyncio.create_task(
        manager.broadcast_agent_pool_status(ctx.team_id, pool_status)
    )

    return None


# ============================================================================
# Job Endpoints (Agent Auth Required - Phase 5)
# ============================================================================

@router.post(
    "/jobs/claim",
    response_model=JobClaimResponse,
    responses={204: {"description": "No jobs available"}},
    summary="Claim next available job",
    description="Claim the next available job for execution. Returns 204 if no jobs available."
)
async def claim_job(
    ctx: AgentContext = Depends(require_online_agent),
    service: AgentService = Depends(get_agent_service),
    db: Session = Depends(get_db),
):
    """
    Claim the next available job for the agent.

    Uses FOR UPDATE SKIP LOCKED for atomic claiming. Requires the agent
    to be in ONLINE status.

    Returns 204 No Content if no jobs are available.
    """
    from backend.src.services.job_coordinator_service import JobCoordinatorService

    coordinator = JobCoordinatorService(db)

    # Get agent to retrieve capabilities
    agent = service.get_agent_by_guid(ctx.agent_guid, ctx.team_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Try to claim a job
    result = coordinator.claim_job(
        agent_id=ctx.agent_id,
        team_id=ctx.team_id,
        agent_capabilities=agent.capabilities,
    )

    if not result:
        # No jobs available - return 204
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    job = result.job

    # Build response with collection path if applicable
    collection_guid = None
    collection_path = None
    if job.collection:
        collection_guid = job.collection.guid
        collection_path = job.collection.location

    pipeline_guid = None
    if job.pipeline:
        pipeline_guid = job.pipeline.guid

    # Broadcast updates
    manager = get_connection_manager()

    # Broadcast pool status update (job assigned = running)
    pool_status = service.get_pool_status(ctx.team_id)
    asyncio.create_task(
        manager.broadcast_agent_pool_status(ctx.team_id, pool_status)
    )

    # Broadcast job update so frontend shows the job as running
    job_response = _db_job_to_response(job)
    asyncio.create_task(
        manager.broadcast_global_job_update(job_response.model_dump(mode="json"))
    )

    # Get previous result for Input State comparison (Issue #92)
    previous_result = None
    if result.previous_result:
        previous_result = PreviousResultData(
            guid=result.previous_result.guid,
            input_state_hash=result.previous_result.input_state_hash,
            completed_at=result.previous_result.completed_at,
        )

    return JobClaimResponse(
        guid=job.guid,
        tool=job.tool,
        mode=job.mode,
        collection_guid=collection_guid,
        collection_path=collection_path,
        pipeline_guid=pipeline_guid,
        parameters=job.parameters,
        signing_secret=result.signing_secret,
        priority=job.priority,
        retry_count=job.retry_count,
        max_retries=job.max_retries,
        previous_result=previous_result,
    )


@router.post(
    "/jobs/{job_guid}/progress",
    response_model=JobStatusResponse,
    summary="Update job progress",
    description="Update progress for a running job."
)
async def update_job_progress(
    job_guid: str,
    data: JobProgressRequest,
    ctx: AgentContext = Depends(require_online_agent),
    service: AgentService = Depends(get_agent_service),
    db: Session = Depends(get_db),
):
    """
    Update progress for a running job.

    The job must be assigned to this agent. Progress updates are
    broadcast to connected WebSocket clients.
    """
    from backend.src.services.job_coordinator_service import JobCoordinatorService

    coordinator = JobCoordinatorService(db)

    try:
        # Build progress dict
        progress = {
            "stage": data.stage,
            "percentage": data.percentage,
            "files_scanned": data.files_scanned,
            "total_files": data.total_files,
            "current_file": data.current_file,
            "message": data.message,
        }
        # Remove None values
        progress = {k: v for k, v in progress.items() if v is not None}

        job = coordinator.update_progress(
            job_guid=job_guid,
            agent_id=ctx.agent_id,
            team_id=ctx.team_id,
            progress=progress,
        )

        # Broadcast updates
        manager = get_connection_manager()

        # Broadcast job progress to WebSocket clients
        asyncio.create_task(
            manager.broadcast_job_progress(ctx.team_id, job.guid, progress)
        )

        # Also broadcast full job update (for status changes like ASSIGNED -> RUNNING)
        job_response = _db_job_to_response(job)
        asyncio.create_task(
            manager.broadcast_global_job_update(job_response.model_dump(mode="json"))
        )

        return JobStatusResponse(
            guid=job.guid,
            status=job.status.value,
            tool=job.tool,
            progress=job.progress,
            error_message=job.error_message,
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ServiceValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/jobs/{job_guid}/no-change",
    response_model=JobStatusResponse,
    summary="Complete job with NO_CHANGE status",
    description="Mark a job as NO_CHANGE when Input State hash matches previous result. "
                "Issue #92: Storage Optimization for Analysis Results."
)
async def complete_job_no_change(
    job_guid: str,
    data: JobNoChangeRequest,
    ctx: AgentContext = Depends(get_agent_context),
    service: AgentService = Depends(get_agent_service),
    db: Session = Depends(get_db),
):
    """
    Complete a job with NO_CHANGE status.

    Called when the agent detects the Input State hash matches a previous
    result, indicating no changes to the collection since the last analysis.

    Creates a NO_CHANGE AnalysisResult that:
    - Copies results_json, files_scanned, issues_found from source result
    - Sets download_report_from to reference source result's report
    - Does NOT store report_html (saves storage)
    - Triggers intermediate copy cleanup
    """
    from backend.src.services.job_coordinator_service import JobCoordinatorService

    coordinator = JobCoordinatorService(db)

    try:
        job = coordinator.complete_job_no_change(
            job_guid=job_guid,
            agent_id=ctx.agent_id,
            team_id=ctx.team_id,
            input_state_hash=data.input_state_hash,
            source_result_guid=data.source_result_guid,
            signature=data.signature,
            input_state_json=data.input_state_json,
        )

        # Refresh job to get result relationship
        db.refresh(job)

        # Broadcast updates
        manager = get_connection_manager()

        # Broadcast pool status update (job completed)
        pool_status = service.get_pool_status(ctx.team_id)
        asyncio.create_task(
            manager.broadcast_agent_pool_status(ctx.team_id, pool_status)
        )

        # Broadcast full job update so frontend updates the card
        job_response = _db_job_to_response(job)
        asyncio.create_task(
            manager.broadcast_global_job_update(job_response.model_dump(mode="json"))
        )

        return JobStatusResponse(
            guid=job.guid,
            status=job.status.value,
            tool=job.tool,
            progress=None,
            error_message=None,
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ServiceValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/jobs/{job_guid}/complete",
    response_model=JobStatusResponse,
    summary="Complete job with results",
    description="Mark a job as completed and submit results. Supports both inline content and chunked upload references."
)
async def complete_job(
    job_guid: str,
    data: JobCompleteWithUploadRequest,
    ctx: AgentContext = Depends(get_agent_context),
    service: AgentService = Depends(get_agent_service),
    db: Session = Depends(get_db),
):
    """
    Complete a job with results.

    Supports two modes:
    1. Inline: Provide results directly in the request body
    2. Chunked: Provide upload_ids for pre-uploaded large content

    Creates an AnalysisResult record and links it to the job.
    The signature must match the HMAC-SHA256 of the results using
    the signing secret provided during claim.
    """
    from backend.src.services.job_coordinator_service import (
        JobCoordinatorService,
        JobCompletionData,
    )

    coordinator = JobCoordinatorService(db)

    # Debug logging for storage optimization (Issue #92)
    hash_preview = data.input_state_hash[:16] + "..." if data.input_state_hash else "None"
    logger.info(
        f"Job completion request for {job_guid}: input_state_hash={hash_preview}, "
        f"results_upload_id={data.results_upload_id}, report_upload_id={data.report_upload_id}"
    )

    try:
        completion_data = JobCompletionData(
            results=data.results,
            report_html=data.report_html,
            results_upload_id=data.results_upload_id,
            report_upload_id=data.report_upload_id,
            files_scanned=data.files_scanned,
            issues_found=data.issues_found,
            signature=data.signature,
            # Storage optimization fields (Issue #92)
            input_state_hash=data.input_state_hash,
            input_state_json=data.input_state_json,
        )

        job = coordinator.complete_job(
            job_guid=job_guid,
            agent_id=ctx.agent_id,
            team_id=ctx.team_id,
            completion_data=completion_data,
        )

        # Refresh job to get result relationship
        db.refresh(job)

        # Broadcast updates
        manager = get_connection_manager()

        # Broadcast pool status update (job completed)
        pool_status = service.get_pool_status(ctx.team_id)
        asyncio.create_task(
            manager.broadcast_agent_pool_status(ctx.team_id, pool_status)
        )

        # Broadcast full job update so frontend updates the card
        job_response = _db_job_to_response(job)
        asyncio.create_task(
            manager.broadcast_global_job_update(job_response.model_dump(mode="json"))
        )

        return JobStatusResponse(
            guid=job.guid,
            status=job.status.value,
            tool=job.tool,
            progress=None,
            error_message=None,
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ServiceValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/jobs/{job_guid}/fail",
    response_model=JobStatusResponse,
    summary="Mark job as failed",
    description="Mark a job as failed with an error message."
)
async def fail_job(
    job_guid: str,
    data: JobFailRequest,
    ctx: AgentContext = Depends(get_agent_context),
    service: AgentService = Depends(get_agent_service),
    db: Session = Depends(get_db),
):
    """
    Mark a job as failed.

    The job must be assigned to this agent. Failed jobs may be
    retried if retry_count < max_retries.
    """
    from backend.src.services.job_coordinator_service import JobCoordinatorService

    coordinator = JobCoordinatorService(db)

    try:
        job = coordinator.fail_job(
            job_guid=job_guid,
            agent_id=ctx.agent_id,
            team_id=ctx.team_id,
            error_message=data.error_message,
            signature=data.signature,
        )

        # Refresh job to get result relationship
        db.refresh(job)

        # Broadcast updates
        manager = get_connection_manager()

        # Broadcast pool status update (job failed)
        pool_status = service.get_pool_status(ctx.team_id)
        asyncio.create_task(
            manager.broadcast_agent_pool_status(ctx.team_id, pool_status)
        )

        # Broadcast full job update so frontend updates the card
        job_response = _db_job_to_response(job)
        asyncio.create_task(
            manager.broadcast_global_job_update(job_response.model_dump(mode="json"))
        )

        return JobStatusResponse(
            guid=job.guid,
            status=job.status.value,
            tool=job.tool,
            progress=None,
            error_message=job.error_message,
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ServiceValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/jobs/{job_guid}/config",
    response_model=JobConfigResponse,
    summary="Get job-specific configuration",
    description="Get configuration needed for executing a specific job."
)
async def get_job_config(
    job_guid: str,
    ctx: AgentContext = Depends(get_agent_context),
    db: Session = Depends(get_db),
    connector_service: ConnectorService = Depends(get_connector_service),
):
    """
    Get configuration for a specific job.

    Returns the team configuration plus job-specific details like the
    collection path. The requesting agent must be assigned to the job.
    """
    from backend.src.models.job import Job
    from backend.src.services.config_loader import DatabaseConfigLoader

    # Parse job GUID
    try:
        job_uuid = Job.parse_guid(job_guid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Get job
    job = db.query(Job).filter(
        Job.uuid == job_uuid,
        Job.team_id == ctx.team_id,
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Verify agent is assigned to this job
    if job.agent_id != ctx.agent_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Job is not assigned to this agent"
        )

    # Get config from database
    loader = DatabaseConfigLoader(team_id=ctx.team_id, db=db)

    # Get collection path if applicable
    collection_path = None
    if job.collection:
        collection_path = job.collection.location

    # Get pipeline data if applicable
    # If job has no pipeline assigned, use the default pipeline for pipeline_validation tool
    pipeline_guid = None
    pipeline_data = None
    pipeline = job.pipeline

    # Resolve default pipeline if job has no explicit pipeline
    if not pipeline and job.tool == "pipeline_validation":
        from backend.src.models.pipeline import Pipeline
        pipeline = db.query(Pipeline).filter(
            Pipeline.team_id == ctx.team_id,
            Pipeline.is_default == True
        ).first()

    if pipeline:
        pipeline_guid = pipeline.guid
        pipeline_data = PipelineData(
            guid=pipeline.guid,
            name=pipeline.name,
            version=job.pipeline_version or pipeline.version,  # Use job's version or current
            nodes=pipeline.nodes_json or [],
            edges=pipeline.edges_json or [],
        )

    # Get connector data for ALL jobs with connectors (not just collection_test)
    # This allows agents to use storage adapters for remote collections
    connector_data = None
    inventory_config = None

    # For inventory_validate and inventory_import jobs, get connector from job.progress
    if job.tool in ("inventory_validate", "inventory_import") and job.progress:
        connector_guid = job.progress.get("connector_guid")
        inventory_config = job.progress.get("config")
        if connector_guid:
            connector = connector_service.get_by_guid(connector_guid, team_id=ctx.team_id)
            if connector:
                # For SERVER credentials, decrypt and include credentials
                # For AGENT credentials, agent uses locally stored credentials
                credentials = None
                if connector.credential_location == CredentialLocation.SERVER:
                    connector_with_creds = connector_service.get_by_guid(
                        connector.guid,
                        team_id=ctx.team_id,
                        decrypt_credentials=True
                    )
                    if connector_with_creds:
                        credentials = getattr(connector_with_creds, 'decrypted_credentials', None)

                connector_data = ConnectorTestData(
                    guid=connector.guid,
                    type=connector.type.value,
                    name=connector.name,
                    credential_location=connector.credential_location.value,
                    credentials=credentials,
                    inventory_config=inventory_config,
                )

    elif job.collection and job.collection.connector:
        connector = job.collection.connector

        # For SERVER credentials, decrypt and include credentials
        # For AGENT credentials, agent uses locally stored credentials
        credentials = None
        if connector.credential_location == CredentialLocation.SERVER:
            # Get connector with decrypted credentials
            connector_with_creds = connector_service.get_by_guid(
                connector.guid,
                team_id=ctx.team_id,
                decrypt_credentials=True
            )
            if connector_with_creds:
                credentials = getattr(connector_with_creds, 'decrypted_credentials', None)

        connector_data = ConnectorTestData(
            guid=connector.guid,
            type=connector.type.value,
            name=connector.name,
            credential_location=connector.credential_location.value,
            credentials=credentials,
        )

    return JobConfigResponse(
        job_guid=job.guid,
        config=JobConfigData(
            photo_extensions=loader.photo_extensions,
            metadata_extensions=loader.metadata_extensions,
            camera_mappings=loader.camera_mappings,
            processing_methods=loader.processing_methods,
            require_sidecar=loader.require_sidecar,
        ),
        collection_path=collection_path,
        pipeline_guid=pipeline_guid,
        pipeline=pipeline_data,
        connector=connector_data,
    )


# ============================================================================
# Chunked Upload Endpoints (Agent Auth Required - Phase 15)
# ============================================================================

# Module-level upload service instance (shared across requests)
_upload_service = None


def get_upload_service():
    """Get or create the chunked upload service singleton."""
    global _upload_service
    if _upload_service is None:
        from backend.src.services.chunked_upload_service import ChunkedUploadService
        _upload_service = ChunkedUploadService()
    return _upload_service


@router.post(
    "/jobs/{job_guid}/uploads/initiate",
    response_model=InitiateUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate chunked upload",
    description="Start a chunked upload session for large results or HTML reports."
)
async def initiate_upload(
    job_guid: str,
    data: InitiateUploadRequest,
    ctx: AgentContext = Depends(get_agent_context),
    db: Session = Depends(get_db),
):
    """
    Initiate a chunked upload for a job.

    Used when results JSON exceeds 1MB or for HTML reports.
    Returns upload_id and chunk info for subsequent uploads.
    """
    from backend.src.models.job import Job
    from backend.src.services.chunked_upload_service import UploadType

    # Parse job GUID
    try:
        job_uuid = Job.parse_guid(job_guid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Verify job exists and is assigned to this agent
    job = db.query(Job).filter(
        Job.uuid == job_uuid,
        Job.team_id == ctx.team_id,
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    if job.agent_id != ctx.agent_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Job is not assigned to this agent"
        )

    # Validate upload type
    try:
        upload_type = UploadType(data.upload_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid upload_type: {data.upload_type}. Must be 'results_json' or 'report_html'"
        )

    # Initiate upload
    upload_service = get_upload_service()
    result = upload_service.initiate_upload(
        job_guid=job_guid,
        agent_id=ctx.agent_id,
        team_id=ctx.team_id,
        upload_type=upload_type,
        expected_size=data.expected_size,
        chunk_size=data.chunk_size,
    )

    return InitiateUploadResponse(
        upload_id=result.upload_id,
        chunk_size=result.chunk_size,
        total_chunks=result.total_chunks,
    )


@router.put(
    "/uploads/{upload_id}/{chunk_index}",
    response_model=ChunkUploadResponse,
    summary="Upload a chunk",
    description="Upload a single chunk of data. Idempotent - duplicate uploads return success."
)
async def upload_chunk(
    upload_id: str,
    chunk_index: int,
    request: Request,
    ctx: AgentContext = Depends(get_agent_context),
):
    """
    Upload a chunk of data.

    The request body should be the raw chunk bytes.
    Returns progress information.
    """
    from backend.src.services.chunked_upload_service import ChunkedUploadService

    # Read raw body
    chunk_data = await request.body()

    if not chunk_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty chunk data"
        )

    upload_service = get_upload_service()

    try:
        is_new = upload_service.upload_chunk(
            upload_id=upload_id,
            chunk_index=chunk_index,
            chunk_data=chunk_data,
            agent_id=ctx.agent_id,
            team_id=ctx.team_id,
        )

        # Get session for progress info
        session = upload_service.get_session(upload_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload session not found"
            )

        return ChunkUploadResponse(
            received=is_new,
            chunk_index=chunk_index,
            chunks_received=len(session.chunks),
            total_chunks=session.total_chunks,
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ServiceValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/uploads/{upload_id}/status",
    response_model=UploadStatusResponse,
    summary="Get upload status",
    description="Get the current status of an upload session."
)
async def get_upload_status(
    upload_id: str,
    ctx: AgentContext = Depends(get_agent_context),
):
    """Get upload session status including progress and missing chunks."""
    upload_service = get_upload_service()

    try:
        status_data = upload_service.get_upload_status(
            upload_id=upload_id,
            agent_id=ctx.agent_id,
            team_id=ctx.team_id,
        )
        return UploadStatusResponse(**status_data)

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ServiceValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/uploads/{upload_id}/finalize",
    response_model=FinalizeUploadResponse,
    summary="Finalize upload",
    description="Finalize an upload by verifying checksum and validating content."
)
async def finalize_upload(
    upload_id: str,
    data: FinalizeUploadRequest,
    ctx: AgentContext = Depends(get_agent_context),
):
    """
    Finalize an upload.

    Verifies SHA-256 checksum and validates content (JSON schema, HTML security).
    The content is returned to be used with job completion.
    """
    upload_service = get_upload_service()

    try:
        result = upload_service.finalize_upload(
            upload_id=upload_id,
            expected_checksum=data.checksum,
            agent_id=ctx.agent_id,
            team_id=ctx.team_id,
        )

        return FinalizeUploadResponse(
            success=result.success,
            upload_type=result.content_type.value,
            content_size=len(result.content) if result.content else 0,
        )

    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ServiceValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/uploads/{upload_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel upload",
    description="Cancel an in-progress upload and clean up resources."
)
async def cancel_upload(
    upload_id: str,
    ctx: AgentContext = Depends(get_agent_context),
):
    """Cancel an in-progress upload."""
    upload_service = get_upload_service()

    try:
        cancelled = upload_service.cancel_upload(
            upload_id=upload_id,
            agent_id=ctx.agent_id,
            team_id=ctx.team_id,
        )

        if not cancelled:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload session not found"
            )

        return None

    except ServiceValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# Admin Endpoints (User Auth Required)
# ============================================================================

@router.post(
    "/tokens",
    response_model=RegistrationTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create registration token",
    description="Create a one-time registration token for agent setup. "
                "Requires user authentication (session or API token)."
)
async def create_registration_token(
    data: RegistrationTokenCreateRequest,
    ctx: TenantContext = Depends(get_tenant_context),
    service: AgentService = Depends(get_agent_service),
    db: Session = Depends(get_db),
):
    """
    Create a one-time registration token.

    This endpoint is protected by user authentication (not agent auth).
    Only authenticated users can create registration tokens.
    """
    result = service.create_registration_token(
        team_id=ctx.team_id,
        created_by_user_id=ctx.user_id,
        name=data.name,
        expiration_hours=data.expires_in_hours,
    )

    # Get creator email for response
    from backend.src.models import User
    creator = db.query(User).filter(User.id == ctx.user_id).first()
    creator_email = creator.email if creator else None

    return RegistrationTokenResponse(
        guid=result.token.guid,
        token=result.plaintext_token,
        name=result.token.name,
        expires_at=result.token.expires_at,
        is_valid=result.token.is_valid,
        created_at=result.token.created_at,
        created_by_email=creator_email,
    )


@router.get(
    "/tokens",
    response_model=RegistrationTokenListResponse,
    summary="List registration tokens",
    description="List all registration tokens for the current team."
)
async def list_registration_tokens(
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
    include_used: bool = False,
):
    """List registration tokens for the current team."""
    from backend.src.models.agent_registration_token import AgentRegistrationToken
    from backend.src.models import User
    from backend.src.models.agent import Agent

    query = db.query(AgentRegistrationToken).filter(
        AgentRegistrationToken.team_id == ctx.team_id
    )

    if not include_used:
        query = query.filter(AgentRegistrationToken.is_used == False)

    tokens = query.order_by(AgentRegistrationToken.created_at.desc()).all()

    items = []
    for token in tokens:
        creator = db.query(User).filter(User.id == token.created_by_user_id).first()
        # Get agent GUID if used
        agent_guid = None
        if token.used_by_agent_id:
            agent = db.query(Agent).filter(Agent.id == token.used_by_agent_id).first()
            agent_guid = agent.guid if agent else None

        items.append(RegistrationTokenListItem(
            guid=token.guid,
            name=token.name,
            expires_at=token.expires_at,
            is_valid=token.is_valid,
            is_used=token.is_used,
            used_by_agent_guid=agent_guid,
            created_at=token.created_at,
            created_by_email=creator.email if creator else None,
        ))

    return RegistrationTokenListResponse(
        tokens=items,
        total_count=len(items),
    )


@router.delete(
    "/tokens/{guid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete registration token",
    description="Delete an unused registration token."
)
async def delete_registration_token(
    guid: str,
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    """Delete an unused registration token."""
    from backend.src.models.agent_registration_token import AgentRegistrationToken

    # Parse GUID to get UUID for database query
    try:
        token_uuid = AgentRegistrationToken.parse_guid(guid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration token not found"
        )

    token = db.query(AgentRegistrationToken).filter(
        AgentRegistrationToken.uuid == token_uuid,
        AgentRegistrationToken.team_id == ctx.team_id,
    ).first()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registration token not found"
        )

    if token.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a used registration token"
        )

    db.delete(token)
    db.commit()
    return None


@router.get(
    "",
    response_model=AgentListResponse,
    summary="List agents",
    description="List all agents for the current team."
)
async def list_agents(
    ctx: TenantContext = Depends(get_tenant_context),
    service: AgentService = Depends(get_agent_service),
    db: Session = Depends(get_db),
    include_revoked: bool = False,
):
    """List all agents for the current team."""
    agents = service.list_agents(
        team_id=ctx.team_id,
        include_revoked=include_revoked,
    )

    # Get running jobs count for each agent (Phase 12 - Load Balancing)
    from backend.src.models.job import Job, JobStatus
    from sqlalchemy import func

    running_counts_query = db.query(
        Job.agent_id,
        func.count(Job.id).label('count')
    ).filter(
        Job.team_id == ctx.team_id,
        Job.status.in_([JobStatus.ASSIGNED, JobStatus.RUNNING])
    ).group_by(Job.agent_id).all()

    running_counts = {row.agent_id: row.count for row in running_counts_query}

    return AgentListResponse(
        agents=[
            agent_to_response(a, running_jobs_count=running_counts.get(a.id, 0))
            for a in agents
        ],
        total_count=len(agents),
    )


@router.get(
    "/pool-status",
    response_model=AgentPoolStatusResponse,
    summary="Get agent pool status",
    description="Get aggregate status for the agent pool (for header badge)."
)
async def get_pool_status(
    ctx: TenantContext = Depends(get_tenant_context),
    service: AgentService = Depends(get_agent_service),
):
    """Get agent pool status for header badge."""
    status_data = service.get_pool_status(ctx.team_id)

    return AgentPoolStatusResponse(
        online_count=status_data["online_count"],
        offline_count=status_data["offline_count"],
        idle_count=status_data["idle_count"],
        running_jobs_count=status_data["running_jobs_count"],
        status=status_data["status"],
    )


# ============================================================================
# Agent Connector Endpoints (Agent Auth Required - Phase 8)
# Must be defined BEFORE /{guid} to avoid route conflicts
# ============================================================================

# Credential field definitions for each connector type
CONNECTOR_CREDENTIAL_FIELDS = {
    "s3": [
        {"name": "aws_access_key_id", "type": "string", "required": True, "description": "AWS Access Key ID"},
        {"name": "aws_secret_access_key", "type": "password", "required": True, "description": "AWS Secret Access Key"},
        {"name": "region", "type": "string", "required": True, "description": "AWS Region (e.g., us-east-1)"},
        {"name": "bucket", "type": "string", "required": False, "description": "Default bucket (optional)"},
    ],
    "gcs": [
        {"name": "service_account_json", "type": "json", "required": True, "description": "Service Account JSON key file content"},
        {"name": "bucket", "type": "string", "required": False, "description": "Default bucket (optional)"},
    ],
    "smb": [
        {"name": "server", "type": "string", "required": True, "description": "Server address (hostname or IP)"},
        {"name": "share", "type": "string", "required": True, "description": "Share name"},
        {"name": "username", "type": "string", "required": True, "description": "Username"},
        {"name": "password", "type": "password", "required": True, "description": "Password"},
        {"name": "domain", "type": "string", "required": False, "description": "Domain (optional)"},
    ],
}


@router.get(
    "/connectors",
    response_model=AgentConnectorListResponse,
    summary="List connectors for credential configuration",
    description="List connectors that the agent can configure credentials for. "
                "Use pending_only=true to filter to only pending connectors."
)
async def list_connectors_for_agent(
    pending_only: bool = False,
    agent_ctx: AgentContext = Depends(require_online_agent),
    connector_service: ConnectorService = Depends(get_connector_service),
):
    import logging
    logging.getLogger("agent").info(f"list_connectors_for_agent called, agent={agent_ctx.agent_guid}")
    """
    List connectors available for agent credential configuration.

    Query Parameters:
        pending_only: If true, only return connectors with credential_location=pending

    Returns:
        List of connectors with their configuration status
    """
    # Get all connectors for the agent's team
    connectors = connector_service.list_connectors(team_id=agent_ctx.agent.team_id)

    # Filter based on credential_location
    # Agents can configure: pending (needs initial config) or agent (update/expand)
    # Agents cannot configure: server (credentials stored on server)
    filtered = []
    for conn in connectors:
        # Skip server-side credential connectors
        if conn.credential_location == CredentialLocation.SERVER:
            continue

        # If pending_only, only include pending connectors
        if pending_only and conn.credential_location != CredentialLocation.PENDING:
            continue

        # Check if this agent has credentials for this connector
        agent_capabilities = agent_ctx.agent.capabilities or []
        has_local = f"connector:{conn.guid}" in agent_capabilities

        filtered.append(AgentConnectorResponse(
            guid=conn.guid,
            name=conn.name,
            type=conn.type.value,
            credential_location=conn.credential_location.value,
            is_active=conn.is_active,
            created_at=conn.created_at,
            has_local_credentials=has_local,
        ))

    return AgentConnectorListResponse(connectors=filtered, total=len(filtered))


@router.get(
    "/connectors/{guid}/metadata",
    response_model=AgentConnectorMetadataResponse,
    summary="Get connector metadata for configuration",
    description="Get connector details and credential field definitions for configuration."
)
async def get_connector_metadata(
    guid: str,
    agent_ctx: AgentContext = Depends(require_online_agent),
    connector_service: ConnectorService = Depends(get_connector_service),
):
    """
    Get connector metadata needed for credential configuration.

    Path Parameters:
        guid: Connector GUID (con_xxx)

    Returns:
        Connector details and credential field definitions
    """
    # Get connector by GUID with team filtering
    connector = connector_service.get_by_guid(guid, team_id=agent_ctx.agent.team_id)

    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector not found: {guid}"
        )

    # Cannot configure server-side credentials from agent
    if connector.credential_location == CredentialLocation.SERVER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot configure credentials for server-side connector from agent"
        )

    # Get credential field definitions for this connector type
    credential_fields = CONNECTOR_CREDENTIAL_FIELDS.get(connector.type.value, [])

    return AgentConnectorMetadataResponse(
        guid=connector.guid,
        name=connector.name,
        type=connector.type.value,
        credential_location=connector.credential_location.value,
        credential_fields=credential_fields,
    )


@router.post(
    "/connectors/{guid}/report-capability",
    response_model=ReportConnectorCapabilityResponse,
    summary="Report connector credential capability",
    description="Report that this agent has (or no longer has) credentials for a connector."
)
async def report_connector_capability(
    guid: str,
    request: ReportConnectorCapabilityRequest,
    agent_ctx: AgentContext = Depends(require_online_agent),
    agent_service: AgentService = Depends(get_agent_service),
    connector_service: ConnectorService = Depends(get_connector_service),
):
    """
    Report that this agent has credentials configured for a connector.

    Path Parameters:
        guid: Connector GUID (con_xxx)

    Request Body:
        has_credentials: Whether agent has valid credentials
        last_tested: When credentials were last successfully tested

    Returns:
        Acknowledgement and whether credential_location was updated

    Side Effects:
        - Updates agent capabilities to include/exclude connector:{guid}
        - If connector is pending and has_credentials=true, updates to agent
    """
    # Get connector by GUID with team filtering
    connector = connector_service.get_by_guid(guid, team_id=agent_ctx.agent.team_id)

    if not connector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector not found: {guid}"
        )

    # Cannot configure server-side credentials from agent
    if connector.credential_location == CredentialLocation.SERVER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot report capability for server-side connector"
        )

    agent = agent_ctx.agent
    capabilities = list(agent.capabilities or [])
    capability_key = f"connector:{guid}"

    credential_location_updated = False

    if request.has_credentials:
        # Add capability if not present
        if capability_key not in capabilities:
            capabilities.append(capability_key)

        # If connector is pending, flip to agent (activation is user's decision in WebUI)
        if connector.credential_location == CredentialLocation.PENDING:
            connector_service.update_connector(
                connector_id=connector.id,
                credential_location=CredentialLocation.AGENT,
                update_credentials=False,  # Don't try to update server credentials
            )
            credential_location_updated = True
    else:
        # Remove capability if present
        if capability_key in capabilities:
            capabilities.remove(capability_key)

    # Update agent capabilities
    agent_service.update_capabilities(agent, capabilities)

    return ReportConnectorCapabilityResponse(
        acknowledged=True,
        credential_location_updated=credential_location_updated,
    )


@router.websocket("/ws/pool-status")
async def pool_status_websocket(
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    """
    WebSocket endpoint for real-time agent pool status updates.

    Clients subscribe to receive pool status updates when agents come
    online/offline, start/complete jobs, etc.

    Authentication: Session-based (same as HTTP endpoints).
    The team is derived from the authenticated user's session.

    Issue #90 - Distributed Agent Architecture (Phase 4)
    Task: T057
    """
    from backend.src.middleware.tenant import get_websocket_tenant_context

    # Must accept the WebSocket connection BEFORE any validation
    # Otherwise close() fails with 403 since connection isn't established
    await websocket.accept()

    # Authenticate using session (same as HTTP endpoints)
    ctx = await get_websocket_tenant_context(websocket, db)
    if not ctx:
        await websocket.close(code=4001, reason="Authentication required")
        return

    team_id = ctx.team_id
    manager = get_connection_manager()
    channel = manager.get_agent_pool_channel(team_id)

    # Register this already-accepted connection to the channel
    await manager.register_accepted(channel, websocket)

    try:
        # Send initial pool status
        service = AgentService(db)
        initial_status = service.get_pool_status(team_id)
        await websocket.send_json({
            "type": "agent_pool_status",
            "pool_status": initial_status
        })

        # Keep connection alive and handle pings
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                try:
                    await websocket.send_json({"type": "heartbeat"})
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(channel, websocket)


@router.get(
    "/{guid}/detail",
    response_model=AgentDetailResponse,
    summary="Get agent detail view",
    description="Get detailed information about an agent including job statistics and recent history."
)
async def get_agent_detail(
    guid: str,
    ctx: TenantContext = Depends(get_tenant_context),
    service: AgentService = Depends(get_agent_service),
    db: Session = Depends(get_db),
):
    """
    Get detailed information about a specific agent.

    Includes:
    - Basic agent info (name, hostname, status, etc.)
    - System metrics (CPU, memory, disk)
    - Bound collections count
    - Job statistics (completed, failed)
    - Recent job history (last 10 jobs)
    """
    from sqlalchemy import func
    from backend.src.models.job import Job, JobStatus

    try:
        agent = service.get_agent_by_guid(guid, ctx.team_id)
    except (ValueError, NotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Get bound collections count
    bound_collections_count = agent.bound_collections.count()

    # Get job statistics
    total_jobs_completed = db.query(func.count(Job.id)).filter(
        Job.agent_id == agent.id,
        Job.status == JobStatus.COMPLETED
    ).scalar() or 0

    total_jobs_failed = db.query(func.count(Job.id)).filter(
        Job.agent_id == agent.id,
        Job.status == JobStatus.FAILED
    ).scalar() or 0

    # Get recent jobs (last 10)
    recent_jobs_query = db.query(Job).filter(
        Job.agent_id == agent.id
    ).order_by(Job.created_at.desc()).limit(10).all()

    recent_jobs = []
    for job in recent_jobs_query:
        recent_jobs.append(AgentJobHistoryItem(
            guid=job.guid,
            tool=job.tool,
            collection_guid=job.collection.guid if job.collection else None,
            collection_name=job.collection.name if job.collection else None,
            status=job.status.value,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
        ))

    # Convert metrics to schema if present
    metrics = None
    if agent.metrics:
        metrics_data = {k: v for k, v in agent.metrics.items() if k != "metrics_updated_at"}
        metrics = AgentMetrics(**metrics_data) if metrics_data else None

    # Get current job GUID if running
    current_job = db.query(Job).filter(
        Job.agent_id == agent.id,
        Job.status.in_([JobStatus.ASSIGNED, JobStatus.RUNNING])
    ).first()

    return AgentDetailResponse(
        guid=agent.guid,
        name=agent.name,
        hostname=agent.hostname,
        os_info=agent.os_info,
        status=agent.status,
        error_message=agent.error_message,
        last_heartbeat=agent.last_heartbeat,
        capabilities=agent.capabilities,
        authorized_roots=agent.authorized_roots,
        version=agent.version,
        created_at=agent.created_at,
        team_guid=agent.team.guid if agent.team else "",
        current_job_guid=current_job.guid if current_job else None,
        metrics=metrics,
        bound_collections_count=bound_collections_count,
        total_jobs_completed=total_jobs_completed,
        total_jobs_failed=total_jobs_failed,
        recent_jobs=recent_jobs,
    )


@router.get(
    "/{guid}/jobs",
    response_model=AgentJobHistoryResponse,
    summary="Get agent job history",
    description="Get paginated job history for a specific agent."
)
async def get_agent_jobs(
    guid: str,
    offset: int = 0,
    limit: int = 20,
    ctx: TenantContext = Depends(get_tenant_context),
    service: AgentService = Depends(get_agent_service),
    db: Session = Depends(get_db),
):
    """
    Get paginated job history for a specific agent.

    Args:
        guid: Agent GUID
        offset: Number of items to skip (default 0)
        limit: Maximum items to return (default 20, max 100)
    """
    from sqlalchemy import func
    from backend.src.models.job import Job

    # Clamp limit
    limit = min(limit, 100)

    try:
        agent = service.get_agent_by_guid(guid, ctx.team_id)
    except (ValueError, NotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # Get total count
    total_count = db.query(func.count(Job.id)).filter(
        Job.agent_id == agent.id
    ).scalar() or 0

    # Get paginated jobs
    jobs_query = db.query(Job).filter(
        Job.agent_id == agent.id
    ).order_by(Job.created_at.desc()).offset(offset).limit(limit).all()

    jobs = []
    for job in jobs_query:
        jobs.append(AgentJobHistoryItem(
            guid=job.guid,
            tool=job.tool,
            collection_guid=job.collection.guid if job.collection else None,
            collection_name=job.collection.name if job.collection else None,
            status=job.status.value,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message,
        ))

    return AgentJobHistoryResponse(
        jobs=jobs,
        total_count=total_count,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{guid}",
    response_model=AgentResponse,
    summary="Get agent by GUID",
    description="Get details of a specific agent."
)
async def get_agent(
    guid: str,
    ctx: TenantContext = Depends(get_tenant_context),
    service: AgentService = Depends(get_agent_service),
):
    """Get details of a specific agent."""
    try:
        agent = service.get_agent_by_guid(guid, ctx.team_id)
    except (ValueError, NotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    return agent_to_response(agent)


@router.patch(
    "/{guid}",
    response_model=AgentResponse,
    summary="Update agent",
    description="Update agent name."
)
async def update_agent(
    guid: str,
    data: AgentUpdateRequest,
    ctx: TenantContext = Depends(get_tenant_context),
    service: AgentService = Depends(get_agent_service),
):
    """Update agent name."""
    try:
        agent = service.get_agent_by_guid(guid, ctx.team_id)
    except (ValueError, NotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    agent = service.rename_agent(agent, data.name)
    return agent_to_response(agent)


@router.delete(
    "/{guid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke agent",
    description="Revoke an agent's access. The agent will no longer be able to connect."
)
async def revoke_agent(
    guid: str,
    reason: str = "Revoked by administrator",
    ctx: TenantContext = Depends(get_tenant_context),
    service: AgentService = Depends(get_agent_service),
):
    """Revoke an agent's access."""
    try:
        agent = service.get_agent_by_guid(guid, ctx.team_id)
    except (ValueError, NotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    service.revoke_agent(agent, reason)

    # Broadcast pool status update after revocation
    pool_status = service.get_pool_status(ctx.team_id)
    manager = get_connection_manager()
    asyncio.create_task(
        manager.broadcast_agent_pool_status(ctx.team_id, pool_status)
    )

    return None


# ============================================================================
# Inventory Validation Endpoints (Issue #107)
# ============================================================================

@router.post(
    "/jobs/{job_guid}/inventory/validate",
    response_model=InventoryValidationResponse,
    summary="Report inventory validation result",
    description="Submit the result of an inventory configuration validation job."
)
async def report_inventory_validation(
    job_guid: str,
    data: InventoryValidationRequest,
    ctx: AgentContext = Depends(get_agent_context),
    service: AgentService = Depends(get_agent_service),
    db: Session = Depends(get_db),
):
    """
    Report inventory validation result.

    Called by agents after validating inventory configuration accessibility.
    Updates the connector's inventory_validation_status based on the result.

    Path Parameters:
        job_guid: GUID of the validation job (job_xxx format)

    Request Body:
        InventoryValidationRequest with validation results

    Returns:
        InventoryValidationResponse with status update confirmation

    Raises:
        404: If job or connector not found
        400: If job is not an inventory validation job
        403: If job is not assigned to this agent
    """
    from backend.src.models.job import Job, JobStatus
    from backend.src.services.job_coordinator_service import JobCoordinatorService
    from backend.src.services.inventory_service import InventoryService

    # Parse job GUID
    try:
        job_uuid = Job.parse_guid(job_guid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Get job
    job = db.query(Job).filter(
        Job.uuid == job_uuid,
        Job.team_id == ctx.team_id,
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Verify job type is inventory_validate
    if job.tool != "inventory_validate":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job is not an inventory validation job"
        )

    # Verify agent is assigned to this job
    if job.agent_id != ctx.agent_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Job is not assigned to this agent"
        )

    # Get connector from job progress
    progress = job.progress or {}
    connector_id = progress.get("connector_id")
    connector_guid = progress.get("connector_guid")

    if not connector_id:
        # Try to get connector by GUID from request
        if data.connector_guid:
            from backend.src.services.guid import GuidService
            try:
                connector_uuid = GuidService.parse_identifier(data.connector_guid, expected_prefix="con")
                from backend.src.models import Connector
                connector = db.query(Connector).filter(
                    Connector.uuid == connector_uuid,
                    Connector.team_id == ctx.team_id,
                ).first()
                if connector:
                    connector_id = connector.id
            except ValueError:
                pass

    if not connector_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not determine connector from job"
        )

    # Update connector validation status
    inventory_service = InventoryService(db)
    try:
        connector = inventory_service.update_validation_status(
            connector_id=connector_id,
            success=data.success,
            error_message=data.error_message,
            latest_manifest=data.latest_manifest,
            team_id=ctx.team_id
        )
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connector not found"
        )

    db.commit()

    # NOTE: Job completion is NOT done here.
    # The agent should call the standard /jobs/{guid}/complete endpoint after
    # reporting validation results. This follows the standard tool pattern where
    # specialized data endpoints only store intermediate results, and job lifecycle
    # is managed by the standard completion flow.

    status_str = "validated" if data.success else "failed"
    message = "Inventory configuration validated successfully" if data.success else f"Validation failed: {data.error_message}"

    logger.info(
        f"Inventory validation completed",
        extra={
            "job_guid": job_guid,
            "connector_guid": connector.guid if connector else connector_guid,
            "success": data.success
        }
    )

    return InventoryValidationResponse(
        status=status_str,
        message=message
    )


@router.post(
    "/jobs/{job_guid}/inventory/folders",
    response_model=InventoryFoldersResponse,
    summary="Report inventory folders",
    description="Submit discovered folders from inventory import job."
)
async def report_inventory_folders(
    job_guid: str,
    data: InventoryFoldersRequest,
    ctx: AgentContext = Depends(get_agent_context),
    service: AgentService = Depends(get_agent_service),
    db: Session = Depends(get_db),
):
    """
    Report discovered inventory folders.

    Called by agents after completing inventory import to submit
    the discovered folder structure.

    Path Parameters:
        job_guid: GUID of the import job (job_xxx format)

    Request Body:
        InventoryFoldersRequest with folders and statistics

    Returns:
        InventoryFoldersResponse with storage confirmation

    Raises:
        404: If job or connector not found
        400: If job is not an inventory import job
        403: If job is not assigned to this agent
    """
    from backend.src.models.job import Job, JobStatus
    from backend.src.services.job_coordinator_service import JobCoordinatorService
    from backend.src.services.inventory_service import InventoryService

    # Parse job GUID
    try:
        job_uuid = Job.parse_guid(job_guid)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Get job
    job = db.query(Job).filter(
        Job.uuid == job_uuid,
        Job.team_id == ctx.team_id,
    ).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Verify job type is inventory_import
    if job.tool != "inventory_import":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not an inventory import job (tool: {job.tool})"
        )

    # Verify job is assigned to this agent
    if job.agent_id != ctx.agent_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Job is not assigned to this agent"
        )

    # Get connector from job progress
    progress = job.progress or {}
    connector_id = progress.get("connector_id")

    if not connector_id:
        # Try to get connector by GUID from request
        if data.connector_guid:
            from backend.src.services.guid import GuidService
            try:
                connector_uuid = GuidService.parse_identifier(data.connector_guid, expected_prefix="con")
                from backend.src.models import Connector
                connector = db.query(Connector).filter(
                    Connector.uuid == connector_uuid,
                    Connector.team_id == ctx.team_id,
                ).first()
                if connector:
                    connector_id = connector.id
            except ValueError:
                pass

    if not connector_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not determine connector from job"
        )

    # Store the discovered folders
    inventory_service = InventoryService(db)
    try:
        folders_stored = inventory_service.store_folders(
            connector_id=connector_id,
            team_id=ctx.team_id,
            folders=data.folders,
            folder_stats=data.folder_stats,
            total_files=data.total_files,
            total_size=data.total_size
        )
    except Exception as e:
        logger.error(f"Error storing inventory folders: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store folders: {str(e)}"
        )

    db.commit()

    # NOTE: Job completion is NOT done here.
    # The agent should call the standard /jobs/{guid}/complete endpoint after
    # reporting folders. This follows the standard tool pattern where specialized
    # data endpoints only store intermediate results, and job lifecycle is managed
    # by the standard completion flow.

    logger.info(
        f"Inventory import completed",
        extra={
            "job_guid": job_guid,
            "connector_guid": data.connector_guid,
            "folders_stored": folders_stored,
            "total_files": data.total_files
        }
    )

    return InventoryFoldersResponse(
        status="success",
        message=f"Stored {folders_stored} inventory folders",
        folders_stored=folders_stored
    )
