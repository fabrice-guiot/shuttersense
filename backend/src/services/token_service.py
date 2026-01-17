"""
Token service for API token management.

Phase 10: User Story 7 - API Token Authentication

Handles:
- JWT token generation with associated system users
- Token validation and context creation
- Token revocation
- Token lifecycle management

Design:
- Each API token has an associated system user (UserType.SYSTEM)
- System users are auto-created when tokens are generated
- Tokens are JWTs signed with a secret key
- Token hash is stored in DB for revocation lookup
- Tokens never grant super admin access
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

from jose import jwt, JWTError
from sqlalchemy.orm import Session

from backend.src.models import User, UserStatus, UserType, Team, ApiToken
from backend.src.middleware.auth import TenantContext
from backend.src.services.exceptions import NotFoundError, ValidationError
from backend.src.services.guid import GuidService
from backend.src.utils.logging_config import get_logger


logger = get_logger("services")


# Token configuration
TOKEN_ALGORITHM = "HS256"
TOKEN_PREFIX_LENGTH = 8  # First 8 chars shown to users for identification
DEFAULT_TOKEN_EXPIRY_DAYS = 90


class TokenService:
    """
    Service for managing API tokens.

    Handles token generation, validation, and revocation with associated
    system users for authentication.

    Usage:
        >>> service = TokenService(db_session, jwt_secret)
        >>> token, api_token = service.generate_token(
        ...     team_id=1,
        ...     created_by_user_id=5,
        ...     name="CI/CD Token",
        ...     expires_in_days=30
        ... )
        >>> ctx = service.validate_token(token)
        >>> if ctx:
        ...     print(f"Authenticated as team {ctx.team_id}")
    """

    def __init__(self, db: Session, jwt_secret: str):
        """
        Initialize token service.

        Args:
            db: SQLAlchemy database session
            jwt_secret: Secret key for JWT signing
        """
        self.db = db
        self.jwt_secret = jwt_secret

    def generate_token(
        self,
        team_id: int,
        created_by_user_id: int,
        name: str,
        expires_in_days: int = DEFAULT_TOKEN_EXPIRY_DAYS,
        scopes: Optional[list] = None,
    ) -> Tuple[str, ApiToken]:
        """
        Generate a new API token with associated system user.

        Creates a system user for the token and generates a JWT. The full
        token is only returned once - store it securely.

        Args:
            team_id: Team to scope the token to
            created_by_user_id: Human user creating the token (audit trail)
            name: User-provided name/description for the token
            expires_in_days: Days until token expires (default: 90)
            scopes: Optional list of scopes (default: ["*"] for full access)

        Returns:
            Tuple of (jwt_token_string, ApiToken model)

        Raises:
            NotFoundError: If team or creating user not found
            ValidationError: If name is empty or too long
        """
        # Validate inputs
        if not name or not name.strip():
            raise ValidationError("Token name cannot be empty", field="name")
        name = name.strip()
        if len(name) > 100:
            raise ValidationError(
                "Token name cannot exceed 100 characters", field="name"
            )

        # Verify team exists
        team = self.db.query(Team).filter(Team.id == team_id).first()
        if not team:
            raise NotFoundError("Team", team_id)

        # Verify creating user exists and is human
        creating_user = self.db.query(User).filter(User.id == created_by_user_id).first()
        if not creating_user:
            raise NotFoundError("User", created_by_user_id)
        if creating_user.user_type != UserType.HUMAN:
            raise ValidationError(
                "Only human users can create API tokens", field="created_by_user_id"
            )

        # Generate unique identifier for this token
        token_id = secrets.token_urlsafe(16)

        # Create system user for this token
        system_user = User(
            team_id=team_id,
            email=f"token-{token_id}@system.local",
            display_name=f"API Token: {name}",
            status=UserStatus.ACTIVE,
            user_type=UserType.SYSTEM,
            is_active=True,
        )
        self.db.add(system_user)
        self.db.flush()  # Get the user ID

        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        # Create JWT payload
        payload = {
            "sub": system_user.guid,  # Subject is the system user GUID
            "team_guid": team.guid,
            "token_id": token_id,
            "exp": expires_at,
            "iat": datetime.utcnow(),
            "type": "api_token",
        }

        # Sign the JWT
        jwt_token = jwt.encode(payload, self.jwt_secret, algorithm=TOKEN_ALGORITHM)

        # Hash the token for storage (for revocation lookup)
        token_hash = hashlib.sha256(jwt_token.encode()).hexdigest()
        token_prefix = jwt_token[:TOKEN_PREFIX_LENGTH]

        # Create ApiToken record
        api_token = ApiToken(
            system_user_id=system_user.id,
            created_by_user_id=created_by_user_id,
            team_id=team_id,
            name=name,
            token_hash=token_hash,
            token_prefix=token_prefix,
            scopes=scopes or ["*"],
            expires_at=expires_at,
            is_active=True,
        )
        self.db.add(api_token)
        self.db.commit()
        self.db.refresh(api_token)

        logger.info(
            f"Generated API token '{name}' ({api_token.guid}) "
            f"for team {team.name} by user {creating_user.email}"
        )

        return jwt_token, api_token

    def validate_token(self, token: str) -> Optional[TenantContext]:
        """
        Validate a JWT API token and return authentication context.

        Args:
            token: JWT token string (from Authorization header)

        Returns:
            TenantContext if valid, None if invalid/expired/revoked
        """
        try:
            # Decode and verify JWT
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[TOKEN_ALGORITHM],
            )

            # Check token type
            if payload.get("type") != "api_token":
                logger.warning("Token validation failed: not an API token")
                return None

            # Look up token by hash to check if revoked
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            api_token = (
                self.db.query(ApiToken)
                .filter(ApiToken.token_hash == token_hash)
                .first()
            )

            if not api_token:
                logger.warning("Token validation failed: token not found in database")
                return None

            if not api_token.is_active:
                logger.warning(f"Token validation failed: token {api_token.guid} is revoked")
                return None

            if api_token.is_expired:
                logger.warning(f"Token validation failed: token {api_token.guid} is expired")
                return None

            # Get system user and team
            system_user = api_token.system_user
            if not system_user or not system_user.is_active:
                logger.warning(f"Token validation failed: system user inactive")
                return None

            team = api_token.team
            if not team or not team.is_active:
                logger.warning(f"Token validation failed: team inactive")
                return None

            # Update last_used_at
            api_token.last_used_at = datetime.utcnow()
            self.db.commit()

            # Return context with is_api_token=True and is_super_admin=False (always)
            return TenantContext(
                team_id=team.id,
                team_guid=team.guid,
                user_id=system_user.id,
                user_guid=system_user.guid,
                user_email=system_user.email,
                is_super_admin=False,  # API tokens NEVER have super admin access
                is_api_token=True,
            )

        except JWTError as e:
            logger.warning(f"Token validation failed: JWT error - {e}")
            return None
        except Exception as e:
            logger.error(f"Token validation error: {e}", exc_info=True)
            return None

    def revoke_token(self, token_guid: str) -> ApiToken:
        """
        Revoke an API token.

        Deactivates the token and its associated system user.

        Args:
            token_guid: GUID of the token to revoke

        Returns:
            Updated ApiToken instance

        Raises:
            NotFoundError: If token not found
        """
        # Validate GUID format
        if not GuidService.validate_guid(token_guid, "tok"):
            raise NotFoundError("ApiToken", token_guid)

        # Look up token
        try:
            uuid_value = GuidService.parse_guid(token_guid, "tok")
        except ValueError:
            raise NotFoundError("ApiToken", token_guid)

        api_token = (
            self.db.query(ApiToken)
            .filter(ApiToken.uuid == uuid_value)
            .first()
        )
        if not api_token:
            raise NotFoundError("ApiToken", token_guid)

        # Deactivate token
        api_token.is_active = False

        # Deactivate associated system user
        if api_token.system_user:
            api_token.system_user.is_active = False
            api_token.system_user.status = UserStatus.DEACTIVATED

        self.db.commit()
        self.db.refresh(api_token)

        logger.info(f"Revoked API token: {api_token.name} ({token_guid})")

        return api_token

    def get_by_guid(self, token_guid: str) -> ApiToken:
        """
        Get an API token by GUID.

        Args:
            token_guid: Token GUID (tok_xxx format)

        Returns:
            ApiToken instance

        Raises:
            NotFoundError: If token not found
        """
        if not GuidService.validate_guid(token_guid, "tok"):
            raise NotFoundError("ApiToken", token_guid)

        try:
            uuid_value = GuidService.parse_guid(token_guid, "tok")
        except ValueError:
            raise NotFoundError("ApiToken", token_guid)

        api_token = (
            self.db.query(ApiToken)
            .filter(ApiToken.uuid == uuid_value)
            .first()
        )
        if not api_token:
            raise NotFoundError("ApiToken", token_guid)

        return api_token

    def list_by_team(
        self,
        team_id: int,
        active_only: bool = False,
    ) -> list:
        """
        List API tokens for a team.

        Args:
            team_id: Team ID
            active_only: If True, only return active (not revoked) tokens

        Returns:
            List of ApiToken instances
        """
        query = self.db.query(ApiToken).filter(ApiToken.team_id == team_id)

        if active_only:
            query = query.filter(ApiToken.is_active == True)

        return query.order_by(ApiToken.created_at.desc()).all()

    def list_by_user(
        self,
        user_id: int,
        active_only: bool = False,
    ) -> list:
        """
        List API tokens created by a user.

        Args:
            user_id: ID of the human user who created the tokens
            active_only: If True, only return active tokens

        Returns:
            List of ApiToken instances
        """
        query = self.db.query(ApiToken).filter(ApiToken.created_by_user_id == user_id)

        if active_only:
            query = query.filter(ApiToken.is_active == True)

        return query.order_by(ApiToken.created_at.desc()).all()
