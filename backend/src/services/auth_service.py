"""
Authentication service for OAuth login flows.

Handles the business logic for:
- Initiating OAuth login flows
- Processing OAuth callbacks
- Validating users and teams
- Managing session data
- Syncing OAuth profile information

Security:
- Pre-provisioned users only (must exist before login)
- Team active status verified on each login
- User active status verified on each login
- OAuth subject stored for identity verification
"""

from datetime import datetime
from typing import Optional, Tuple
from dataclasses import dataclass

from sqlalchemy.orm import Session
from starlette.requests import Request

from backend.src.models import User, UserStatus, UserType
from backend.src.services.user_service import UserService
from backend.src.services.team_service import TeamService
from backend.src.services.exceptions import NotFoundError, ValidationError
from backend.src.config.oauth import get_oauth_settings
from backend.src.config.super_admins import is_super_admin
from backend.src.auth.oauth_client import (
    create_authorization_url,
    fetch_token,
    get_user_info,
    get_available_providers,
    is_provider_configured,
)
from backend.src.utils.logging_config import get_logger


logger = get_logger("auth")


@dataclass
class AuthResult:
    """
    Result of an authentication attempt.

    Attributes:
        success: Whether authentication succeeded
        user: Authenticated user (if success)
        error: Error message (if failed)
        error_code: Error code for frontend handling
    """
    success: bool
    user: Optional[User] = None
    error: Optional[str] = None
    error_code: Optional[str] = None


class AuthenticationError(Exception):
    """Exception raised for authentication failures."""

    def __init__(self, message: str, error_code: str):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class AuthService:
    """
    Service for managing OAuth authentication.

    Handles the complete OAuth flow from login initiation to session creation,
    including user validation and profile syncing.

    Usage:
        >>> service = AuthService(db_session)
        >>> url, state = await service.initiate_login(request, "google")
        >>> # User redirected to provider...
        >>> result = await service.handle_callback(request, "google")
        >>> if result.success:
        ...     service.create_session(request, result.user)
    """

    def __init__(self, db: Session):
        """
        Initialize auth service.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.user_service = UserService(db)
        self.team_service = TeamService(db)
        self.settings = get_oauth_settings()

    def get_available_providers(self) -> list[dict]:
        """
        Get list of available OAuth providers with metadata.

        Returns:
            List of provider info dicts with name and display info
        """
        providers = []

        if self.settings.google_enabled:
            providers.append({
                "name": "google",
                "display_name": "Google",
                "icon": "google",
            })

        if self.settings.microsoft_enabled:
            providers.append({
                "name": "microsoft",
                "display_name": "Microsoft",
                "icon": "microsoft",
            })

        return providers

    async def initiate_login(
        self,
        request: Request,
        provider: str,
    ) -> Tuple[str, str]:
        """
        Initiate OAuth login flow.

        Generates the authorization URL and state for the specified provider.

        Args:
            request: Starlette request (for session storage)
            provider: OAuth provider name ("google" or "microsoft")

        Returns:
            Tuple of (authorization_url, state)

        Raises:
            ValidationError: If provider is not configured
        """
        if not is_provider_configured(provider):
            raise ValidationError(
                f"OAuth provider '{provider}' is not configured",
                field="provider"
            )

        # Get redirect URI from settings
        if provider == "google":
            redirect_uri = self.settings.google_redirect_uri
        else:
            redirect_uri = self.settings.microsoft_redirect_uri

        logger.info(
            "OAuth login initiated",
            extra={
                "event": "auth.login.initiated",
                "provider": provider,
            }
        )

        url, state = await create_authorization_url(
            request=request,
            provider=provider,
            redirect_uri=redirect_uri,
        )

        return url, state

    async def handle_callback(
        self,
        request: Request,
        provider: str,
    ) -> AuthResult:
        """
        Handle OAuth callback after user authorization.

        Exchanges the authorization code for tokens, extracts user info,
        validates the user, and syncs profile data.

        Args:
            request: Starlette request with authorization code
            provider: OAuth provider name

        Returns:
            AuthResult with success status and user or error
        """
        try:
            # Exchange code for tokens
            logger.info(
                "Processing OAuth callback",
                extra={
                    "event": "auth.callback.processing",
                    "provider": provider,
                }
            )
            token = await fetch_token(request, provider)

            # Extract user info from ID token
            user_info = await get_user_info(provider, token)

            if not user_info:
                logger.error(
                    "No user info returned from provider",
                    extra={
                        "event": "auth.login.failed",
                        "provider": provider,
                        "reason": "no_user_info",
                    }
                )
                return AuthResult(
                    success=False,
                    error="Failed to retrieve user information from provider",
                    error_code="no_user_info",
                )

            # Extract email and subject
            email = user_info.get("email")
            oauth_subject = user_info.get("sub")

            if not email:
                logger.error(
                    "No email in user info from provider",
                    extra={
                        "event": "auth.login.failed",
                        "provider": provider,
                        "reason": "no_email",
                    }
                )
                return AuthResult(
                    success=False,
                    error="Email not provided by OAuth provider",
                    error_code="no_email",
                )

            # Validate and authenticate user
            result = self._validate_and_authenticate(
                email=email,
                provider=provider,
                oauth_subject=oauth_subject,
                user_info=user_info,
            )

            return result

        except Exception as e:
            logger.error(f"OAuth callback error: {e}", exc_info=True)
            return AuthResult(
                success=False,
                error=f"Authentication failed: {str(e)}",
                error_code="callback_error",
            )

    def _validate_and_authenticate(
        self,
        email: str,
        provider: str,
        oauth_subject: str,
        user_info: dict,
    ) -> AuthResult:
        """
        Validate user and complete authentication.

        Args:
            email: User's email from OAuth provider
            provider: OAuth provider name
            oauth_subject: OAuth sub claim
            user_info: Full user info from provider

        Returns:
            AuthResult with success status
        """
        # Look up user by email
        user = self.user_service.get_by_email(email)

        if not user:
            logger.warning(
                "Login attempt for unknown email",
                extra={
                    "event": "auth.login.failed",
                    "provider": provider,
                    "email": email,
                    "reason": "user_not_found",
                }
            )
            return AuthResult(
                success=False,
                error="No account found for this email. Please contact your administrator.",
                error_code="user_not_found",
            )

        # Check user is not a system user (system users cannot OAuth login)
        if user.user_type == UserType.SYSTEM:
            logger.warning(
                "OAuth login attempt by system user blocked",
                extra={
                    "event": "auth.login.failed",
                    "provider": provider,
                    "email": email,
                    "user_guid": user.guid,
                    "reason": "system_user_login_blocked",
                }
            )
            return AuthResult(
                success=False,
                error="This account cannot be used for interactive login.",
                error_code="system_user_login_blocked",
            )

        # Check user is active
        if not user.is_active:
            logger.warning(
                "Login attempt for inactive user",
                extra={
                    "event": "auth.login.failed",
                    "provider": provider,
                    "email": email,
                    "user_guid": user.guid,
                    "reason": "user_inactive",
                }
            )
            return AuthResult(
                success=False,
                error="Your account has been deactivated. Please contact your administrator.",
                error_code="user_inactive",
            )

        if user.status == UserStatus.DEACTIVATED:
            logger.warning(
                "Login attempt for deactivated user",
                extra={
                    "event": "auth.login.failed",
                    "provider": provider,
                    "email": email,
                    "user_guid": user.guid,
                    "reason": "user_deactivated",
                }
            )
            return AuthResult(
                success=False,
                error="Your account has been deactivated. Please contact your administrator.",
                error_code="user_deactivated",
            )

        # Check team is active
        team = user.team
        if not team or not team.is_active:
            logger.warning(
                "Login attempt for user in inactive team",
                extra={
                    "event": "auth.login.failed",
                    "provider": provider,
                    "email": email,
                    "user_guid": user.guid,
                    "team_guid": team.guid if team else None,
                    "reason": "team_inactive",
                }
            )
            return AuthResult(
                success=False,
                error="Your organization's account is inactive. Please contact your administrator.",
                error_code="team_inactive",
            )

        # Update OAuth profile data
        display_name = user_info.get("name")
        picture_url = user_info.get("picture")

        # Debug: Log available user_info fields for troubleshooting
        logger.debug(f"OAuth user_info fields for {provider}: {list(user_info.keys())}")
        if not picture_url:
            logger.debug(f"No 'picture' field in user_info. Available: {user_info}")

        self.user_service.update_oauth_profile(
            user=user,
            provider=provider,
            oauth_subject=oauth_subject,
            display_name=display_name,
            picture_url=picture_url,
        )

        logger.info(
            "User authenticated successfully",
            extra={
                "event": "auth.login.success",
                "provider": provider,
                "email": email,
                "user_guid": user.guid,
                "team_guid": team.guid,
            }
        )

        return AuthResult(
            success=True,
            user=user,
        )

    def create_session(self, request: Request, user: User) -> None:
        """
        Create session for authenticated user.

        Stores user ID and metadata in the session cookie.

        Args:
            request: Starlette request with session
            user: Authenticated user

        Raises:
            RuntimeError: If session middleware is not installed
        """
        if not self._has_session(request):
            raise RuntimeError(
                "Cannot create session: SessionMiddleware not installed. "
                "Set SESSION_SECRET_KEY environment variable."
            )

        request.session["user_id"] = user.id
        request.session["user_guid"] = user.guid
        request.session["team_id"] = user.team_id
        request.session["team_guid"] = user.team.guid
        request.session["email"] = user.email
        request.session["is_super_admin"] = is_super_admin(user.email)
        request.session["authenticated_at"] = datetime.utcnow().isoformat()

        logger.info(
            "Session created",
            extra={
                "event": "auth.session.created",
                "email": user.email,
                "user_guid": user.guid,
                "team_guid": user.team.guid,
                "is_super_admin": request.session["is_super_admin"],
            }
        )

    def clear_session(self, request: Request) -> None:
        """
        Clear the user's session (logout).

        Args:
            request: Starlette request with session
        """
        if not self._has_session(request):
            # No session middleware, nothing to clear
            return

        email = request.session.get("email", "unknown")
        user_guid = request.session.get("user_guid")
        team_guid = request.session.get("team_guid")
        request.session.clear()

        logger.info(
            "User logged out",
            extra={
                "event": "auth.logout",
                "email": email,
                "user_guid": user_guid,
                "team_guid": team_guid,
            }
        )

    def get_session_user(self, request: Request) -> Optional[User]:
        """
        Get the current user from session.

        Args:
            request: Starlette request with session

        Returns:
            User instance or None if not authenticated or session not configured
        """
        if not self._has_session(request):
            return None

        user_id = request.session.get("user_id")
        if not user_id:
            return None

        try:
            return self.user_service.get_by_id(user_id)
        except NotFoundError:
            # User deleted, clear invalid session
            request.session.clear()
            return None

    def _has_session(self, request: Request) -> bool:
        """
        Check if session middleware is installed.

        Returns False if SESSION_SECRET_KEY is not configured.
        """
        return "session" in request.scope

    def is_authenticated(self, request: Request) -> bool:
        """
        Check if the request has a valid session.

        Args:
            request: Starlette request

        Returns:
            True if user is authenticated, False if not or if session not configured
        """
        if not self._has_session(request):
            return False
        return request.session.get("user_id") is not None

    def get_current_user_info(self, request: Request) -> Optional[dict]:
        """
        Get current user information from session.

        Returns minimal user info without database lookup.

        Args:
            request: Starlette request

        Returns:
            User info dict or None if not authenticated
        """
        if not self.is_authenticated(request):
            return None

        return {
            "user_id": request.session.get("user_id"),
            "user_guid": request.session.get("user_guid"),
            "team_id": request.session.get("team_id"),
            "team_guid": request.session.get("team_guid"),
            "email": request.session.get("email"),
            "is_super_admin": request.session.get("is_super_admin", False),
        }
