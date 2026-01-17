"""
API endpoints for API token management.

Phase 10: User Story 7 - API Token Authentication

Endpoints:
- POST /api/tokens - Create a new API token
- GET /api/tokens - List tokens created by current user
- GET /api/tokens/{guid} - Get token details
- DELETE /api/tokens/{guid} - Revoke a token
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.middleware.tenant import TenantContext, get_tenant_context
from backend.src.services.token_service import TokenService
from backend.src.services.exceptions import NotFoundError, ValidationError
from backend.src.config.settings import get_settings


router = APIRouter(prefix="/api/tokens", tags=["tokens"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class TokenCreate(BaseModel):
    """Request schema for creating an API token."""
    name: str = Field(..., min_length=1, max_length=100, description="Token name/description")
    expires_in_days: int = Field(default=90, ge=1, le=365, description="Days until expiration")


class TokenResponse(BaseModel):
    """Response schema for an API token (without the actual token value)."""
    guid: str
    name: str
    token_prefix: str
    scopes: List[str]
    expires_at: str
    last_used_at: Optional[str]
    is_active: bool
    created_at: str
    created_by_guid: Optional[str]
    created_by_email: Optional[str]  # Audit trail: email of creator

    class Config:
        from_attributes = True


class TokenCreateResponse(BaseModel):
    """Response schema for newly created token (includes the actual token value)."""
    guid: str
    name: str
    token: str  # The actual JWT - only shown once!
    token_prefix: str
    scopes: List[str]
    expires_at: str
    created_at: str

    class Config:
        from_attributes = True


class TokenStatsResponse(BaseModel):
    """Response schema for token statistics."""
    total_count: int
    active_count: int
    revoked_count: int


# ============================================================================
# Helper Functions
# ============================================================================

def get_token_service(db: Session = Depends(get_db)) -> TokenService:
    """Dependency to get TokenService."""
    settings = get_settings()
    return TokenService(db, settings.jwt_secret_key)


def token_to_response(api_token) -> TokenResponse:
    """Convert ApiToken model to response schema."""
    return TokenResponse(
        guid=api_token.guid,
        name=api_token.name,
        token_prefix=api_token.token_prefix,
        scopes=api_token.scopes,
        expires_at=api_token.expires_at.isoformat() if api_token.expires_at else None,
        last_used_at=api_token.last_used_at.isoformat() if api_token.last_used_at else None,
        is_active=api_token.is_active,
        created_at=api_token.created_at.isoformat() if api_token.created_at else None,
        created_by_guid=api_token.created_by.guid if api_token.created_by else None,
        created_by_email=api_token.created_by.email if api_token.created_by else None,
    )


# ============================================================================
# Endpoints
# ============================================================================

@router.post("", response_model=TokenCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_token(
    data: TokenCreate,
    ctx: TenantContext = Depends(get_tenant_context),
    service: TokenService = Depends(get_token_service),
):
    """
    Create a new API token.

    The actual token value is only returned once at creation time.
    Store it securely - it cannot be retrieved later.

    API tokens:
    - Are scoped to the current user's team
    - Cannot access super admin endpoints
    - Have an associated system user for authentication
    """
    # API tokens cannot be created by API tokens (require session auth)
    if ctx.is_api_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API tokens cannot create new tokens. Use session authentication."
        )

    try:
        jwt_token, api_token = service.generate_token(
            team_id=ctx.team_id,
            created_by_user_id=ctx.user_id,
            name=data.name,
            expires_in_days=data.expires_in_days,
        )

        return TokenCreateResponse(
            guid=api_token.guid,
            name=api_token.name,
            token=jwt_token,  # Only time this is returned!
            token_prefix=api_token.token_prefix,
            scopes=api_token.scopes,
            expires_at=api_token.expires_at.isoformat(),
            created_at=api_token.created_at.isoformat(),
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=List[TokenResponse])
async def list_tokens(
    ctx: TenantContext = Depends(get_tenant_context),
    service: TokenService = Depends(get_token_service),
    active_only: bool = False,
):
    """
    List API tokens created by the current user.

    Only shows tokens created by the authenticated user, not all team tokens.
    """
    # API tokens cannot list tokens
    if ctx.is_api_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API tokens cannot list tokens. Use session authentication."
        )

    tokens = service.list_by_user(ctx.user_id, active_only=active_only)
    return [token_to_response(t) for t in tokens]


@router.get("/stats", response_model=TokenStatsResponse)
async def get_token_stats(
    ctx: TenantContext = Depends(get_tenant_context),
    service: TokenService = Depends(get_token_service),
):
    """
    Get statistics for API tokens created by the current user.

    Returns counts of total, active, and revoked tokens.
    """
    if ctx.is_api_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API tokens cannot view token stats. Use session authentication."
        )

    tokens = service.list_by_user(ctx.user_id, active_only=False)
    total_count = len(tokens)
    active_count = sum(1 for t in tokens if t.is_active)
    revoked_count = total_count - active_count

    return TokenStatsResponse(
        total_count=total_count,
        active_count=active_count,
        revoked_count=revoked_count,
    )


@router.get("/{guid}", response_model=TokenResponse)
async def get_token(
    guid: str,
    ctx: TenantContext = Depends(get_tenant_context),
    service: TokenService = Depends(get_token_service),
):
    """
    Get details of a specific API token.

    Only the user who created the token can view it.
    """
    if ctx.is_api_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API tokens cannot view token details. Use session authentication."
        )

    try:
        api_token = service.get_by_guid(guid)

        # Only creator can view their own tokens
        if api_token.created_by_user_id != ctx.user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token not found"
            )

        return token_to_response(api_token)

    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )


@router.delete("/{guid}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(
    guid: str,
    ctx: TenantContext = Depends(get_tenant_context),
    service: TokenService = Depends(get_token_service),
):
    """
    Revoke (delete) an API token.

    This deactivates the token - it can no longer be used for authentication.
    Only the user who created the token can revoke it.
    """
    if ctx.is_api_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API tokens cannot revoke tokens. Use session authentication."
        )

    try:
        api_token = service.get_by_guid(guid)

        # Only creator can revoke their own tokens
        if api_token.created_by_user_id != ctx.user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token not found"
            )

        service.revoke_token(guid)
        return None

    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )
