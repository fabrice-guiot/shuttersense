"""
Team Pydantic schemas for API request/response validation.

Defines schemas for team creation, listing, and management operations.
Part of Issue #73 - User Story 5: Team Management
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ============================================================================
# Request Schemas
# ============================================================================


class CreateTeamRequest(BaseModel):
    """Request schema for creating a new team with admin."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Team display name (must be unique)",
        json_schema_extra={"example": "Acme Photography"}
    )
    admin_email: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Email address for the team's first admin user",
        json_schema_extra={"example": "admin@acme.com"}
    )

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "name": "Acme Photography",
                "admin_email": "admin@acme.com"
            }
        }


# ============================================================================
# Response Schemas
# ============================================================================


class TeamResponse(BaseModel):
    """Response schema for a single team."""

    guid: str = Field(..., description="Team GUID (ten_xxx)")
    name: str = Field(..., description="Team display name")
    slug: str = Field(..., description="URL-safe team identifier")
    is_active: bool = Field(..., description="Whether team is active")
    user_count: int = Field(0, description="Number of users in team")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        """Pydantic config."""
        from_attributes = True
        json_schema_extra = {
            "example": {
                "guid": "ten_01hgw2bbg0000000000000001",
                "name": "Acme Photography",
                "slug": "acme-photography",
                "is_active": True,
                "user_count": 5,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-15T10:30:00Z"
            }
        }


class TeamWithAdminResponse(BaseModel):
    """Response schema for team creation with admin user."""

    team: TeamResponse = Field(..., description="Created team")
    admin_email: str = Field(..., description="Admin user email")
    admin_guid: str = Field(..., description="Admin user GUID")

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "team": {
                    "guid": "ten_01hgw2bbg0000000000000001",
                    "name": "Acme Photography",
                    "slug": "acme-photography",
                    "is_active": True,
                    "user_count": 1,
                    "created_at": "2026-01-01T00:00:00Z",
                    "updated_at": None
                },
                "admin_email": "admin@acme.com",
                "admin_guid": "usr_01hgw2bbg0000000000000001"
            }
        }


class TeamListResponse(BaseModel):
    """Response schema for listing teams."""

    teams: List[TeamResponse] = Field(..., description="List of teams")
    total: int = Field(..., description="Total number of teams")

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "teams": [
                    {
                        "guid": "ten_01hgw2bbg0000000000000001",
                        "name": "Acme Photography",
                        "slug": "acme-photography",
                        "is_active": True,
                        "user_count": 5,
                        "created_at": "2026-01-01T00:00:00Z",
                        "updated_at": None
                    }
                ],
                "total": 1
            }
        }


class TeamStatsResponse(BaseModel):
    """Response schema for team statistics (super admin dashboard KPIs)."""

    total_teams: int = Field(..., description="Total number of teams")
    active_teams: int = Field(..., description="Number of active teams")
    inactive_teams: int = Field(..., description="Number of inactive teams")

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "total_teams": 10,
                "active_teams": 8,
                "inactive_teams": 2
            }
        }


# ============================================================================
# Adapter Functions
# ============================================================================


def team_to_response(team, user_count: int = 0) -> TeamResponse:
    """
    Convert Team model to TeamResponse schema.

    Args:
        team: Team model instance
        user_count: Number of users in the team

    Returns:
        TeamResponse schema instance
    """
    return TeamResponse(
        guid=team.guid,
        name=team.name,
        slug=team.slug,
        is_active=team.is_active,
        user_count=user_count,
        created_at=team.created_at,
        updated_at=team.updated_at,
    )
