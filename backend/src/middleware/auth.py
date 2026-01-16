"""
Authentication middleware and dependencies for API routes.

Provides:
- require_auth: FastAPI dependency that requires authentication
- get_current_user: Get the current authenticated user
- require_super_admin: Require super admin privileges

These are thin wrappers around the tenant context for clearer API semantics.
The actual authentication logic is in tenant.py (session and API token validation).
"""

from fastapi import Depends

from backend.src.middleware.tenant import (
    TenantContext,
    get_tenant_context,
    require_super_admin as _require_super_admin
)


async def require_auth(
    ctx: TenantContext = Depends(get_tenant_context)
) -> TenantContext:
    """
    FastAPI dependency that requires authentication.

    Use this for any endpoint that requires the user to be authenticated.
    Returns the TenantContext which contains team_id for data filtering.

    Args:
        ctx: TenantContext from get_tenant_context dependency

    Returns:
        TenantContext with authenticated user/token information

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 403: If team or user is inactive

    Example:
        @router.get("/items")
        async def list_items(
            ctx: TenantContext = Depends(require_auth)
        ):
            # ctx.team_id available for filtering
            items = service.list_items(team_id=ctx.team_id)
            return items
    """
    # get_tenant_context already raises 401 if not authenticated
    # This is just a semantic wrapper for clarity
    return ctx


# Re-export require_super_admin for convenience
require_super_admin = _require_super_admin


__all__ = [
    "require_auth",
    "require_super_admin",
    "TenantContext",
]
