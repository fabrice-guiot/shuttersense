"""
Admin API module.

Contains endpoints for super admin operations:
- Team management (create, list, deactivate, reactivate)

Part of Issue #73 - User Story 5: Team Management
"""

from backend.src.api.admin.teams import router as teams_router

__all__ = ["teams_router"]
