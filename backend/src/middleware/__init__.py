"""
Middleware components for photo-admin backend.

This module provides:
- TenantContext: Dataclass representing the current tenant context
- get_tenant_context: FastAPI dependency for extracting tenant context from requests
- require_auth: FastAPI dependency for requiring authentication
- require_super_admin: FastAPI dependency for requiring super admin privileges
"""

from backend.src.middleware.tenant import TenantContext, get_tenant_context, require_super_admin
from backend.src.middleware.auth import require_auth

__all__ = [
    "TenantContext",
    "get_tenant_context",
    "require_auth",
    "require_super_admin",
]
