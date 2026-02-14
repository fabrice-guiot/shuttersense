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

import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from fastapi import Request, HTTPException, status, Depends
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.utils.client_ip import get_client_ip


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SEC-13: Per-IP failed token validation tracking
# ---------------------------------------------------------------------------
# In-memory tracker for failed API token validation attempts. Limits brute
# force attacks against the Bearer token endpoint without requiring Redis.
# ---------------------------------------------------------------------------
_TOKEN_FAILURE_WINDOW = 300  # 5 minutes
_TOKEN_FAILURE_WARN = 5  # log warning after this many failures
_TOKEN_FAILURE_BLOCK = 20  # block IP after this many failures
_TOKEN_FAILURE_BLOCK_DURATION = 300  # block for 5 minutes

_token_failures: dict[str, list[float]] = defaultdict(list)
_token_blocked: dict[str, float] = {}


def _record_token_failure(ip: str) -> None:
    """Record a failed token validation attempt for an IP."""
    now = time.monotonic()
    _token_failures[ip].append(now)
    # Prune old entries outside the window
    cutoff = now - _TOKEN_FAILURE_WINDOW
    _token_failures[ip] = [t for t in _token_failures[ip] if t > cutoff]

    count = len(_token_failures[ip])
    if count >= _TOKEN_FAILURE_BLOCK:
        _token_blocked[ip] = now
        logger.warning(
            "SEC-13: IP %s has %d failed token validations in the last %d minutes — blocking for %ds",
            ip, count, _TOKEN_FAILURE_WINDOW // 60, _TOKEN_FAILURE_BLOCK_DURATION,
            extra={
                "event": "token.validation.blocked",
                "client_ip": ip,
                "failure_count": count,
            },
        )
    elif count >= _TOKEN_FAILURE_WARN:
        logger.warning(
            "SEC-13: IP %s has %d failed token validations in the last %d minutes",
            ip, count, _TOKEN_FAILURE_WINDOW // 60,
            extra={
                "event": "token.validation.warning",
                "client_ip": ip,
                "failure_count": count,
            },
        )


def _is_token_blocked(ip: str) -> bool:
    """Check if an IP is currently blocked from token validation."""
    blocked_at = _token_blocked.get(ip)
    if blocked_at is None:
        return False
    if time.monotonic() - blocked_at > _TOKEN_FAILURE_BLOCK_DURATION:
        del _token_blocked[ip]
        _token_failures.pop(ip, None)
        return False
    return True


def _clear_token_failures(ip: str) -> None:
    """Clear failure tracking for an IP after successful validation."""
    _token_failures.pop(ip, None)
    _token_blocked.pop(ip, None)


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
        client_ip = get_client_ip(request)
        return await _authenticate_api_token(
            auth_header[7:], db, check_super_admin, client_ip
        )

    # Try session authentication
    session = request.session if hasattr(request, 'session') else {}
    user_guid = session.get("user_guid")
    if user_guid:
        return await _authenticate_session(
            user_guid, db, check_super_admin
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
    check_super_admin,
    client_ip: str = "unknown",
) -> TenantContext:
    """
    Authenticate using an API token.

    API tokens use JWT format and are validated through the TokenService.
    API tokens NEVER grant super admin privileges (security requirement).

    Includes per-IP rate limiting for failed validation attempts (SEC-13).

    Args:
        token: JWT token string
        db: Database session
        check_super_admin: Function to check super admin status (unused for tokens)
        client_ip: Client IP address for rate limiting

    Returns:
        TenantContext for the token's user and team with:
        - is_api_token=True
        - is_super_admin=False (always, for security)

    Raises:
        HTTPException 401: If token is invalid, expired, or revoked
        HTTPException 403: If token, user, or team is inactive
        HTTPException 429: If IP is blocked due to too many failed attempts
    """
    # SEC-13: Check if IP is blocked from too many failures
    if _is_token_blocked(client_ip):
        logger.warning(
            "SEC-13: Rejecting token validation from blocked IP %s", client_ip,
            extra={
                "event": "token.validation.rejected",
                "client_ip": client_ip,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed authentication attempts. Try again later.",
        )

    # Import TokenService here to avoid circular imports
    from backend.src.services.token_service import TokenService
    from backend.src.config.settings import get_settings

    settings = get_settings()

    # Validate token using TokenService
    service = TokenService(db, settings.jwt_secret_key)
    ctx = service.validate_token(token)

    if not ctx:
        _record_token_failure(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked API token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Successful validation — clear any failure tracking for this IP
    _clear_token_failures(client_ip)

    # ctx from TokenService already has:
    # - is_api_token=True
    # - is_super_admin=False (enforced by TokenService)
    return ctx


async def _authenticate_session(
    user_guid: str,
    db: Session,
    check_super_admin
) -> TenantContext:
    """
    Authenticate using session data.

    Args:
        user_guid: User GUID from session (usr_xxx format)
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
    from backend.src.services.guid import GuidService

    # Parse GUID to UUID and look up user
    try:
        user_uuid = GuidService.parse_identifier(user_guid, expected_prefix="usr")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
            headers={"WWW-Authenticate": "Bearer"}
        )
    user = db.query(User).filter(User.uuid == user_uuid).first()
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


async def get_websocket_tenant_context(
    websocket,
    db: Session
) -> Optional[TenantContext]:
    """
    Extract tenant context from a WebSocket connection.

    WebSocket connections have access to the same session as HTTP requests
    when using Starlette's SessionMiddleware. This function extracts the
    user_id from the session and builds a TenantContext.

    DEPRECATED: Use get_websocket_tenant_context_standalone() for WebSocket
    endpoints to avoid holding database connections for the WebSocket lifetime.

    Args:
        websocket: WebSocket connection
        db: Database session

    Returns:
        TenantContext if authenticated, None otherwise

    Usage:
        @router.websocket("/ws/something")
        async def websocket_endpoint(
            websocket: WebSocket,
            db: Session = Depends(get_db)
        ):
            await websocket.accept()
            ctx = await get_websocket_tenant_context(websocket, db)
            if not ctx:
                await websocket.close(code=4001, reason="Authentication required")
                return
            # Use ctx.team_id for tenant-scoped data
    """
    # Import here to avoid circular imports
    from backend.src.models import User
    from backend.src.config.super_admins import is_super_admin as check_super_admin
    from backend.src.services.guid import GuidService

    # Access session from WebSocket scope
    session = websocket.session if hasattr(websocket, 'session') else {}
    user_guid = session.get("user_guid")

    if not user_guid:
        return None

    # Parse GUID to UUID and look up user
    try:
        user_uuid = GuidService.parse_identifier(user_guid, expected_prefix="usr")
    except ValueError:
        return None
    user = db.query(User).filter(User.uuid == user_uuid).first()
    if not user or not user.is_active:
        return None

    # Check team is active
    team = user.team
    if not team or not team.is_active:
        return None

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


async def get_websocket_tenant_context_standalone(
    websocket,
) -> Optional[TenantContext]:
    """
    Extract tenant context from a WebSocket connection using a short-lived DB session.

    This function creates its own database session, performs authentication,
    and immediately closes the session. This prevents WebSocket connections
    from holding database connections for their entire lifetime, which can
    exhaust the connection pool.

    Args:
        websocket: WebSocket connection

    Returns:
        TenantContext if authenticated, None otherwise

    Usage:
        @router.websocket("/ws/something")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            ctx = await get_websocket_tenant_context_standalone(websocket)
            if not ctx:
                await websocket.close(code=4001, reason="Authentication required")
                return
            # Use ctx.team_id for tenant-scoped data
            # Note: ctx is now detached from the DB session
    """
    # Import here to avoid circular imports
    from backend.src.models import User
    from backend.src.config.super_admins import is_super_admin as check_super_admin
    from backend.src.services.guid import GuidService
    from backend.src.db.database import SessionLocal

    # Access session from WebSocket scope
    session = websocket.session if hasattr(websocket, 'session') else {}
    user_guid = session.get("user_guid")

    if not user_guid:
        return None

    # Parse GUID to UUID and look up user
    try:
        user_uuid = GuidService.parse_identifier(user_guid, expected_prefix="usr")
    except ValueError:
        return None

    # Create short-lived DB session for authentication only
    db = SessionLocal()
    try:
        # Lookup user
        user = db.query(User).filter(User.uuid == user_uuid).first()
        if not user or not user.is_active:
            return None

        # Check team is active
        team = user.team
        if not team or not team.is_active:
            return None

        # Build context (capture all needed values before closing session)
        return TenantContext(
            team_id=team.id,
            team_guid=team.guid,
            user_id=user.id,
            user_guid=user.guid,
            user_email=user.email,
            is_super_admin=check_super_admin(user.email),
            is_api_token=False
        )
    finally:
        db.close()


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
