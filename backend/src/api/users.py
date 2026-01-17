"""
Users API endpoints for user pre-provisioning and management.

Provides endpoints for inviting users, listing team users,
and deleting pending invitations.

Part of Issue #73 - User Story 3: User Pre-Provisioning
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.middleware.auth import require_auth, TenantContext
from backend.src.services.user_service import UserService
from backend.src.services.exceptions import NotFoundError, ConflictError, ValidationError
from backend.src.schemas.user import (
    InviteUserRequest,
    UserResponse,
    UserListResponse,
    UserStatsResponse,
    user_to_response,
)
from backend.src.models import UserStatus
from backend.src.utils.logging_config import get_logger


logger = get_logger("api")

router = APIRouter(prefix="/users", tags=["Users"])


# ============================================================================
# User Management Endpoints
# ============================================================================


@router.post("", response_model=UserResponse, status_code=201)
async def invite_user(
    request: InviteUserRequest,
    tenant: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Invite a new user to the team.

    Pre-provisions a user by email. The user will receive PENDING status
    and can activate their account on first OAuth login.

    - **email**: User's email address (must be globally unique)

    Returns the created user with PENDING status.
    """
    service = UserService(db)

    try:
        user = service.invite(
            team_id=tenant.team_id,
            email=request.email,
        )
        logger.info(
            f"User invited: {user.email} to team {tenant.team_id} by user {tenant.user_id}"
        )
        return user_to_response(user)

    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("", response_model=UserListResponse)
async def list_users(
    status: Optional[str] = Query(
        None,
        description="Filter by status (pending, active, deactivated)"
    ),
    active_only: bool = Query(
        False,
        description="Only return active users"
    ),
    tenant: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    List all users in the team.

    Returns users in the authenticated user's team, optionally filtered
    by status or active state.

    - **status**: Filter by user status (pending, active, deactivated)
    - **active_only**: If true, only return active users
    """
    service = UserService(db)

    # Parse status filter
    status_filter = None
    if status:
        try:
            status_filter = UserStatus(status.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}. Must be one of: pending, active, deactivated"
            )

    users = service.list_by_team(
        team_id=tenant.team_id,
        active_only=active_only,
        status_filter=status_filter,
    )

    return UserListResponse(
        users=[user_to_response(u, include_team=False) for u in users],
        total=len(users),
    )


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    tenant: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Get user statistics for the team.

    Returns counts of users by status for TopHeader KPIs.
    """
    service = UserService(db)

    # Get counts by status
    all_users = service.list_by_team(tenant.team_id)

    total = len(all_users)
    active = len([u for u in all_users if u.status == UserStatus.ACTIVE])
    pending = len([u for u in all_users if u.status == UserStatus.PENDING])
    deactivated = len([u for u in all_users if u.status == UserStatus.DEACTIVATED])

    return UserStatsResponse(
        total_users=total,
        active_users=active,
        pending_users=pending,
        deactivated_users=deactivated,
    )


@router.get("/{guid}", response_model=UserResponse)
async def get_user(
    guid: str,
    tenant: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Get a specific user by GUID.

    Returns user details if the user belongs to the authenticated user's team.
    """
    service = UserService(db)

    try:
        user = service.get_by_guid(guid)

        # Verify user is in the same team (tenant isolation)
        if user.team_id != tenant.team_id:
            raise HTTPException(status_code=404, detail="User not found")

        return user_to_response(user)

    except NotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


@router.delete("/{guid}", status_code=204)
async def delete_pending_user(
    guid: str,
    tenant: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Delete a pending user invitation.

    Only users with PENDING status can be deleted. Active and
    deactivated users cannot be deleted to preserve history.

    Returns 204 No Content on success.
    """
    service = UserService(db)

    try:
        user = service.get_by_guid(guid)

        # Verify user is in the same team (tenant isolation)
        if user.team_id != tenant.team_id:
            raise HTTPException(status_code=404, detail="User not found")

        service.delete_pending(guid)
        logger.info(
            f"Pending user deleted: {user.email} by user {tenant.user_id}"
        )

    except NotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{guid}/deactivate", response_model=UserResponse)
async def deactivate_user(
    guid: str,
    tenant: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Deactivate a user.

    Deactivated users cannot log in. This preserves the user record
    for audit purposes.

    Cannot deactivate yourself.
    """
    service = UserService(db)

    try:
        user = service.get_by_guid(guid)

        # Verify user is in the same team (tenant isolation)
        if user.team_id != tenant.team_id:
            raise HTTPException(status_code=404, detail="User not found")

        # Cannot deactivate yourself
        if user.id == tenant.user_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot deactivate yourself"
            )

        updated = service.deactivate(guid)
        logger.info(
            f"User deactivated: {user.email} by user {tenant.user_id}"
        )
        return user_to_response(updated)

    except NotFoundError:
        raise HTTPException(status_code=404, detail="User not found")


@router.post("/{guid}/reactivate", response_model=UserResponse)
async def reactivate_user(
    guid: str,
    tenant: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Reactivate a deactivated user.

    Restores user's ability to log in. Status is set to:
    - ACTIVE if user has previously logged in
    - PENDING if user has never logged in
    """
    service = UserService(db)

    try:
        user = service.get_by_guid(guid)

        # Verify user is in the same team (tenant isolation)
        if user.team_id != tenant.team_id:
            raise HTTPException(status_code=404, detail="User not found")

        updated = service.activate(guid)
        logger.info(
            f"User reactivated: {user.email} by user {tenant.user_id}"
        )
        return user_to_response(updated)

    except NotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
