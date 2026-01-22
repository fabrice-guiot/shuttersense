"""
Admin API module.

Contains endpoints for super admin operations:
- Team management (create, list, deactivate, reactivate)
- Release manifest management (agent binary attestation)

Part of Issue #73 - User Story 5: Team Management
Part of Issue #90 - Distributed Agent Architecture (Phase 14)
"""

from backend.src.api.admin.teams import router as teams_router
from backend.src.api.admin.release_manifests import router as release_manifests_router

__all__ = ["teams_router", "release_manifests_router"]
