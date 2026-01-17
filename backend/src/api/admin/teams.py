"""
Admin Teams API endpoints for super admin team management.

Provides endpoints for creating, listing, and managing teams.
All endpoints require super admin privileges.

Part of Issue #73 - User Story 5: Team Management
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.middleware.auth import require_super_admin, TenantContext
from backend.src.services.team_service import TeamService
from backend.src.services.user_service import UserService
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError
from backend.src.schemas.team import (
    CreateTeamRequest,
    TeamResponse,
    TeamWithAdminResponse,
    TeamListResponse,
    TeamStatsResponse,
    team_to_response,
)
from backend.src.utils.logging_config import get_logger


logger = get_logger("api")

router = APIRouter(prefix="/teams", tags=["Admin - Teams"])


# ============================================================================
# Team Management Endpoints (Super Admin Only)
# ============================================================================


@router.post("", response_model=TeamWithAdminResponse, status_code=201)
async def create_team(
    request: CreateTeamRequest,
    ctx: TenantContext = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Create a new team with an admin user.

    Creates a new team and a pending admin user. The admin will be able
    to log in via OAuth once they authenticate with the specified email.

    **Requires super admin privileges.**

    - **name**: Team display name (must be unique)
    - **admin_email**: Email address for the team's first admin user

    Returns the created team and admin user information.
    """
    service = TeamService(db)

    try:
        team, admin_user = service.create_with_admin(
            name=request.name,
            admin_email=request.admin_email,
        )

        logger.info(
            "Super admin created team",
            extra={
                "event": "admin.team.created",
                "admin_email": ctx.user_email,
                "admin_guid": ctx.user_guid,
                "team_guid": team.guid,
                "team_name": team.name,
                "team_admin_email": admin_user.email,
                "team_admin_guid": admin_user.guid,
            }
        )

        return TeamWithAdminResponse(
            team=team_to_response(team, user_count=1),
            admin_email=admin_user.email,
            admin_guid=admin_user.guid,
        )

    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=TeamListResponse)
async def list_teams(
    active_only: bool = Query(False, description="Only return active teams"),
    ctx: TenantContext = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    List all teams.

    Returns all teams in the system, optionally filtered by active status.

    **Requires super admin privileges.**

    - **active_only**: If true, only return active teams
    """
    team_service = TeamService(db)
    user_service = UserService(db)

    teams = team_service.list_all(active_only=active_only)

    # Get user counts for each team
    team_responses = []
    for team in teams:
        user_count = len(user_service.list_by_team(team.id))
        team_responses.append(team_to_response(team, user_count=user_count))

    return TeamListResponse(
        teams=team_responses,
        total=len(team_responses),
    )


@router.get("/stats", response_model=TeamStatsResponse)
async def get_team_stats(
    ctx: TenantContext = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Get team statistics for super admin dashboard.

    Returns counts of teams by status for dashboard KPIs.

    **Requires super admin privileges.**
    """
    service = TeamService(db)
    stats = service.get_stats()

    return TeamStatsResponse(
        total_teams=stats["total_teams"],
        active_teams=stats["active_teams"],
        inactive_teams=stats["inactive_teams"],
    )


@router.get("/{guid}", response_model=TeamResponse)
async def get_team(
    guid: str,
    ctx: TenantContext = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Get a specific team by GUID.

    **Requires super admin privileges.**
    """
    team_service = TeamService(db)
    user_service = UserService(db)

    try:
        team = team_service.get_by_guid(guid)
        user_count = len(user_service.list_by_team(team.id))
        return team_to_response(team, user_count=user_count)

    except NotFoundError:
        raise HTTPException(status_code=404, detail="Team not found")


@router.post("/{guid}/deactivate", response_model=TeamResponse)
async def deactivate_team(
    guid: str,
    ctx: TenantContext = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Deactivate a team.

    Deactivated teams prevent all members from logging in.
    This preserves the team data for audit purposes.

    **Requires super admin privileges.**

    Cannot deactivate your own team.
    """
    team_service = TeamService(db)
    user_service = UserService(db)

    try:
        team = team_service.get_by_guid(guid)

        # Cannot deactivate your own team
        if team.id == ctx.team_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot deactivate your own team"
            )

        updated = team_service.deactivate(guid)
        user_count = len(user_service.list_by_team(team.id))

        logger.info(
            "Super admin deactivated team",
            extra={
                "event": "admin.team.deactivated",
                "admin_email": ctx.user_email,
                "admin_guid": ctx.user_guid,
                "team_guid": team.guid,
                "team_name": team.name,
            }
        )

        return team_to_response(updated, user_count=user_count)

    except NotFoundError:
        raise HTTPException(status_code=404, detail="Team not found")


@router.post("/{guid}/reactivate", response_model=TeamResponse)
async def reactivate_team(
    guid: str,
    ctx: TenantContext = Depends(require_super_admin),
    db: Session = Depends(get_db),
):
    """
    Reactivate a deactivated team.

    Restores team members' ability to log in.

    **Requires super admin privileges.**
    """
    team_service = TeamService(db)
    user_service = UserService(db)

    try:
        team = team_service.get_by_guid(guid)
        updated = team_service.activate(guid)
        user_count = len(user_service.list_by_team(team.id))

        logger.info(
            "Super admin reactivated team",
            extra={
                "event": "admin.team.reactivated",
                "admin_email": ctx.user_email,
                "admin_guid": ctx.user_guid,
                "team_guid": team.guid,
                "team_name": team.name,
            }
        )

        return team_to_response(updated, user_count=user_count)

    except NotFoundError:
        raise HTTPException(status_code=404, detail="Team not found")
