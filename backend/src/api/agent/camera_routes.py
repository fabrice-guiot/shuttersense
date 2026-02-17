"""
Agent-facing Camera discovery endpoint.

Provides the discover endpoint for agents to register newly discovered
cameras during analysis. Uses agent authentication (AgentContext).

API: POST /api/agent/v1/cameras/discover
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.api.agent.dependencies import AgentContext, get_agent_context
from backend.src.schemas.camera import CameraDiscoverRequest, CameraDiscoverResponse
from backend.src.services.camera_service import CameraService
from backend.src.utils.logging_config import get_logger


logger = get_logger("api")

router = APIRouter(
    prefix="/api/agent/v1/cameras",
    tags=["Agents"],
)


def get_camera_service(db: Session = Depends(get_db)) -> CameraService:
    """Create CameraService instance with dependencies."""
    return CameraService(db=db)


@router.post(
    "/discover",
    response_model=CameraDiscoverResponse,
    summary="Discover cameras"
)
def discover_cameras(
    request: CameraDiscoverRequest,
    ctx: AgentContext = Depends(get_agent_context),
    service: CameraService = Depends(get_camera_service),
) -> CameraDiscoverResponse:
    """
    Idempotent camera discovery.

    Accepts a batch of camera IDs found during analysis. Creates Camera
    records with status "temporary" for any IDs not already registered.
    Returns all Camera records (existing + newly created) for the submitted IDs.
    """
    logger.info(
        f"Camera discovery: {len(request.camera_ids)} IDs from agent {ctx.agent_guid}"
    )
    return service.discover_cameras(
        team_id=ctx.team_id,
        camera_ids=request.camera_ids,
    )
