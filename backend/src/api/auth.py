"""
Authentication API endpoints.

Provides OAuth 2.0 login flow endpoints:
- GET /auth/providers - List available OAuth providers
- GET /auth/login/{provider} - Initiate OAuth login
- GET /auth/callback/{provider} - Handle OAuth callback
- GET /auth/me - Get current user info
- POST /auth/logout - Clear session (logout)

All OAuth endpoints use PKCE for security.

Rate Limiting (T037):
- /auth/login: 10 requests per minute per IP
- /auth/callback: 10 requests per minute per IP
- /auth/me, /auth/status: 60 requests per minute per IP
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.src.db.database import get_db
from backend.src.services.auth_service import AuthService
from backend.src.services.exceptions import ValidationError
from backend.src.utils.logging_config import get_logger


logger = get_logger("api")

# Rate limiter for auth endpoints
limiter = Limiter(key_func=get_remote_address)


router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# Response Models
# ============================================================================


class OAuthProviderResponse(BaseModel):
    """OAuth provider information."""
    name: str
    display_name: str
    icon: str


class ProvidersResponse(BaseModel):
    """List of available OAuth providers."""
    providers: list[OAuthProviderResponse]


class UserInfoResponse(BaseModel):
    """Current user information."""
    user_guid: str
    email: str
    team_guid: str
    team_name: str
    display_name: Optional[str] = None
    picture_url: Optional[str] = None
    is_super_admin: bool = False
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class AuthStatusResponse(BaseModel):
    """Authentication status."""
    authenticated: bool
    user: Optional[UserInfoResponse] = None


class LogoutResponse(BaseModel):
    """Logout confirmation."""
    success: bool
    message: str


class ErrorResponse(BaseModel):
    """Authentication error."""
    error: str
    error_code: str
    message: str


# ============================================================================
# Endpoints
# ============================================================================


@router.get(
    "/providers",
    response_model=ProvidersResponse,
    summary="List available OAuth providers",
    description="Returns the list of configured OAuth providers that can be used for login.",
)
async def list_providers(
    db: Session = Depends(get_db),
) -> ProvidersResponse:
    """
    List available OAuth providers.

    Returns providers that are properly configured with client credentials.
    """
    auth_service = AuthService(db)
    providers = auth_service.get_available_providers()

    return ProvidersResponse(
        providers=[OAuthProviderResponse(**p) for p in providers]
    )


@router.get(
    "/login/{provider}",
    summary="Initiate OAuth login",
    description="Redirects to the OAuth provider's authorization page.",
    responses={
        302: {"description": "Redirect to OAuth provider"},
        400: {"model": ErrorResponse, "description": "Invalid provider"},
    },
)
@limiter.limit("10/minute")
async def login(
    provider: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Initiate OAuth login flow.

    Redirects the user to the OAuth provider's authorization page.
    After authorization, the user is redirected back to /auth/callback/{provider}.

    Args:
        provider: OAuth provider name ("google" or "microsoft")
        request: Starlette request (for session)
        db: Database session

    Returns:
        Redirect to OAuth provider
    """
    auth_service = AuthService(db)

    try:
        url, state = await auth_service.initiate_login(request, provider)
        logger.info(f"Redirecting to {provider} OAuth: {url[:50]}...")
        return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)

    except ValidationError as e:
        logger.warning(f"Invalid OAuth provider: {provider}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Invalid provider",
                "error_code": "invalid_provider",
                "message": str(e),
            },
        )


@router.get(
    "/callback/{provider}",
    summary="Handle OAuth callback",
    description="Processes the OAuth callback and creates a session on success.",
    responses={
        302: {"description": "Redirect to dashboard or login page"},
    },
)
@limiter.limit("10/minute")
async def callback(
    provider: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Handle OAuth callback.

    Processes the authorization code, validates the user, creates a session,
    and redirects to the appropriate page.

    Success: Redirects to / (dashboard)
    Failure: Redirects to /login?error={error_code}

    Args:
        provider: OAuth provider name
        request: Starlette request with authorization code
        db: Database session

    Returns:
        Redirect to dashboard or login page with error
    """
    auth_service = AuthService(db)

    result = await auth_service.handle_callback(request, provider)

    if result.success and result.user:
        # Create session and redirect to dashboard
        auth_service.create_session(request, result.user)
        logger.info(f"OAuth login successful for {result.user.email}")
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    else:
        # Redirect to login with error
        error_code = result.error_code or "unknown"
        logger.warning(f"OAuth login failed: {result.error} ({error_code})")
        return RedirectResponse(
            url=f"/login?error={error_code}",
            status_code=status.HTTP_302_FOUND,
        )


@router.get(
    "/me",
    response_model=AuthStatusResponse,
    summary="Get current user info",
    description="Returns the currently authenticated user's information.",
)
async def get_me(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthStatusResponse:
    """
    Get current user information.

    Returns user info if authenticated, or authenticated=False if not.
    Does not require authentication - allows frontend to check status.

    Args:
        request: Starlette request with session
        db: Database session

    Returns:
        Authentication status and user info
    """
    auth_service = AuthService(db)

    if not auth_service.is_authenticated(request):
        return AuthStatusResponse(authenticated=False)

    user = auth_service.get_session_user(request)

    if not user:
        # Session exists but user not found (deleted?)
        auth_service.clear_session(request)
        return AuthStatusResponse(authenticated=False)

    # Check user and team are still active
    if not user.is_active or not user.team or not user.team.is_active:
        auth_service.clear_session(request)
        return AuthStatusResponse(authenticated=False)

    from backend.src.config.super_admins import is_super_admin

    return AuthStatusResponse(
        authenticated=True,
        user=UserInfoResponse(
            user_guid=user.guid,
            email=user.email,
            team_guid=user.team.guid,
            team_name=user.team.name,
            display_name=user.display_name,
            picture_url=user.picture_url,
            is_super_admin=is_super_admin(user.email),
            first_name=user.first_name,
            last_name=user.last_name,
        ),
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Logout",
    description="Clears the session cookie and logs out the user.",
)
async def logout(
    request: Request,
    db: Session = Depends(get_db),
) -> LogoutResponse:
    """
    Logout the current user.

    Clears the session cookie. Safe to call even if not authenticated.

    Args:
        request: Starlette request with session
        db: Database session

    Returns:
        Logout confirmation
    """
    auth_service = AuthService(db)
    auth_service.clear_session(request)

    return LogoutResponse(
        success=True,
        message="Successfully logged out",
    )


@router.get(
    "/status",
    response_model=AuthStatusResponse,
    summary="Check authentication status",
    description="Quick check if the user is authenticated (alias for /me).",
)
async def check_status(
    request: Request,
    db: Session = Depends(get_db),
) -> AuthStatusResponse:
    """
    Check authentication status.

    Lightweight endpoint to check if user is authenticated.
    Same as /me but explicitly named for clarity.
    """
    return await get_me(request, db)


class ProfileDebugResponse(BaseModel):
    """Debug information about the user's profile."""
    user_guid: str
    email: str
    display_name: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    picture_url: Optional[str]
    oauth_provider: Optional[str]
    oauth_subject: Optional[str]
    last_login_at: Optional[str]
    message: str


@router.get(
    "/profile/debug",
    response_model=ProfileDebugResponse,
    summary="Debug profile information",
    description="Shows stored profile data for debugging. Log out and back in to refresh OAuth profile.",
)
async def debug_profile(
    request: Request,
    db: Session = Depends(get_db),
) -> ProfileDebugResponse:
    """
    Get debug information about the current user's profile.

    Shows what's stored in the database for the authenticated user.
    To refresh profile data from OAuth provider, log out and log back in.

    Returns:
        Profile debug information including OAuth fields
    """
    auth_service = AuthService(db)

    if not auth_service.is_authenticated(request):
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = auth_service.get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return ProfileDebugResponse(
        user_guid=user.guid,
        email=user.email,
        display_name=user.display_name,
        first_name=user.first_name,
        last_name=user.last_name,
        picture_url=user.picture_url,
        oauth_provider=user.oauth_provider,
        oauth_subject=user.oauth_subject,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        message="To refresh profile data from OAuth provider, log out and log back in.",
    )
