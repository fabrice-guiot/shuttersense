"""
Tenant context middleware and dependencies for multi-tenancy support.

Provides:
- TenantContext: Dataclass containing tenant identification info
- get_tenant_context: FastAPI dependency to extract tenant context from requests

The tenant context is derived from:
1. Session authentication (for browser-based access)
2. API token authentication (for programmatic access)

All tenant-scoped service operations should use the team_id from TenantContext
to filter data appropriately.
"""

from dataclasses import dataclass
from typing import Optional
import uuid

from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session

from backend.src.db.database import get_db


@dataclass
class TenantContext:
    """
    Represents the current tenant context for a request.

    This dataclass carries information about the authenticated user and their
    team, enabling tenant-scoped data access throughout the request lifecycle.

    Attributes:
        team_id: Internal team ID for database queries (FK filtering)
        team_guid: Team's external GUID (ten_xxx) for API responses
        user_id: Internal user ID (if authenticated via session)
        user_guid: User's external GUID (usr_xxx) for API responses
        user_email: User's email address
        is_super_admin: Whether the user has super admin privileges
        is_api_token: Whether authentication was via API token

    Usage:
        @router.get("/items")
        async def list_items(
            ctx: TenantContext = Depends(get_tenant_context)
        ):
            # Filter by team_id for tenant isolation
            items = service.list_items(team_id=ctx.team_id)
            return items
    """

    # Team identification
    team_id: int
    team_guid: str

    # User identification (None for unauthenticated or token-only auth)
    user_id: Optional[int] = None
    user_guid: Optional[str] = None
    user_email: Optional[str] = None

    # Authorization flags
    is_super_admin: bool = False
    is_api_token: bool = False

    # API token info (only set when is_api_token=True)
    token_id: Optional[int] = None
    token_guid: Optional[str] = None

    def __post_init__(self):
        """Validate required fields."""
        if not self.team_id or not self.team_guid:
            raise ValueError("team_id and team_guid are required")


async def get_tenant_context(
    request: Request,
    db: Session = Depends(get_db)
) -> TenantContext:
    """
    FastAPI dependency to extract tenant context from the request.

    This dependency attempts authentication in the following order:
    1. Check for API token in Authorization header (Bearer token)
    2. Check for session cookie (browser-based auth)

    If neither is present or valid, raises 401 Unauthorized.

    Args:
        request: FastAPI Request object
        db: Database session

    Returns:
        TenantContext with authenticated user/token information

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 403: If team or user is inactive

    Example:
        @router.get("/items")
        async def list_items(
            ctx: TenantContext = Depends(get_tenant_context)
        ):
            items = item_service.list(team_id=ctx.team_id)
            return items
    """
    # Import here to avoid circular imports
    from backend.src.config.super_admins import is_super_admin as check_super_admin

    # Try API token authentication first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return await _authenticate_api_token(
            auth_header[7:], db, check_super_admin
        )

    # Try session authentication
    session = request.session if hasattr(request, 'session') else {}
    user_id = session.get("user_id")
    if user_id:
        return await _authenticate_session(
            user_id, db, check_super_admin
        )

    # No valid authentication
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"}
    )


async def get_optional_tenant_context(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[TenantContext]:
    """
    FastAPI dependency for optional authentication.

    Returns TenantContext if authenticated, None otherwise.
    Use this for endpoints that work both with and without authentication.

    Args:
        request: FastAPI Request object
        db: Database session

    Returns:
        TenantContext if authenticated, None otherwise
    """
    try:
        return await get_tenant_context(request, db)
    except HTTPException:
        return None


async def _authenticate_api_token(
    token: str,
    db: Session,
    check_super_admin
) -> TenantContext:
    """
    Authenticate using an API token.

    API tokens use JWT format and are validated through the TokenService.
    API tokens NEVER grant super admin privileges (security requirement).

    Args:
        token: JWT token string
        db: Database session
        check_super_admin: Function to check super admin status (unused for tokens)

    Returns:
        TenantContext for the token's user and team with:
        - is_api_token=True
        - is_super_admin=False (always, for security)

    Raises:
        HTTPException 401: If token is invalid, expired, or revoked
        HTTPException 403: If token, user, or team is inactive
    """
    # Import TokenService here to avoid circular imports
    from backend.src.services.token_service import TokenService
    from backend.src.config.settings import get_settings

    settings = get_settings()

    # Validate token using TokenService
    service = TokenService(db, settings.jwt_secret_key)
    ctx = service.validate_token(token)

    if not ctx:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked API token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # ctx from TokenService already has:
    # - is_api_token=True
    # - is_super_admin=False (enforced by TokenService)
    return ctx


async def _authenticate_session(
    user_id: int,
    db: Session,
    check_super_admin
) -> TenantContext:
    """
    Authenticate using session data.

    Args:
        user_id: User ID from session
        db: Database session
        check_super_admin: Function to check super admin status

    Returns:
        TenantContext for the session's user and team

    Raises:
        HTTPException 401: If session is invalid
        HTTPException 403: If user or team is inactive
    """
    # Import models here to avoid circular imports
    from backend.src.models import User, Team

    # Lookup user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Check user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    # Check team is active
    team = user.team
    if not team or not team.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team is inactive"
        )

    # Build context
    return TenantContext(
        team_id=team.id,
        team_guid=team.guid,
        user_id=user.id,
        user_guid=user.guid,
        user_email=user.email,
        is_super_admin=check_super_admin(user.email),
        is_api_token=False
    )


def require_super_admin(ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
    """
    Dependency that requires super admin privileges.

    Use this for endpoints that should only be accessible to super admins.
    API tokens are NEVER allowed, even if the creating user was a super admin.

    Args:
        ctx: Tenant context from get_tenant_context

    Returns:
        TenantContext if user is super admin (via session auth)

    Raises:
        HTTPException 403: If user is not a super admin OR using API token

    Example:
        @router.delete("/teams/{guid}")
        async def delete_team(
            ctx: TenantContext = Depends(require_super_admin)
        ):
            # Only super admins can delete teams
            ...
    """
    # API tokens cannot access admin endpoints (security requirement)
    if ctx.is_api_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API tokens cannot access admin endpoints"
        )

    if not ctx.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required"
        )
    return ctx
