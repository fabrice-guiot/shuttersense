"""
User Pydantic schemas for API request/response validation.

Defines schemas for user invitation, listing, and management operations.
Part of Issue #73 - User Story 3: User Pre-Provisioning
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ============================================================================
# Request Schemas
# ============================================================================


class InviteUserRequest(BaseModel):
    """Request schema for inviting a new user."""

    email: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Email address of the user to invite (globally unique)",
        json_schema_extra={"example": "user@example.com"}
    )

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "email": "newuser@example.com"
            }
        }


# ============================================================================
# Response Schemas
# ============================================================================


class TeamInfo(BaseModel):
    """Minimal team information for user response."""

    guid: str = Field(..., description="Team GUID (ten_xxx)")
    name: str = Field(..., description="Team name")
    slug: str = Field(..., description="Team slug")


class UserResponse(BaseModel):
    """Response schema for a single user."""

    guid: str = Field(..., description="User GUID (usr_xxx)")
    email: str = Field(..., description="User email address")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    display_name: Optional[str] = Field(None, description="Display name")
    picture_url: Optional[str] = Field(None, description="Profile picture URL")
    status: str = Field(..., description="User status (pending, active, deactivated)")
    is_active: bool = Field(..., description="Whether user is active")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    team: Optional[TeamInfo] = Field(None, description="User's team information")

    class Config:
        """Pydantic config."""
        from_attributes = True
        json_schema_extra = {
            "example": {
                "guid": "usr_01hgw2bbg0000000000000001",
                "email": "user@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "display_name": "John Doe",
                "picture_url": "https://example.com/photo.jpg",
                "status": "active",
                "is_active": True,
                "last_login_at": "2026-01-15T10:30:00Z",
                "created_at": "2026-01-01T00:00:00Z",
                "team": {
                    "guid": "ten_01hgw2bbg0000000000000001",
                    "name": "Acme Corp",
                    "slug": "acme-corp"
                }
            }
        }


class UserListResponse(BaseModel):
    """Response schema for listing users."""

    users: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "users": [
                    {
                        "guid": "usr_01hgw2bbg0000000000000001",
                        "email": "user1@example.com",
                        "first_name": "John",
                        "last_name": "Doe",
                        "display_name": "John Doe",
                        "picture_url": None,
                        "status": "active",
                        "is_active": True,
                        "last_login_at": "2026-01-15T10:30:00Z",
                        "created_at": "2026-01-01T00:00:00Z",
                        "team": None
                    }
                ],
                "total": 1
            }
        }


class UserStatsResponse(BaseModel):
    """Response schema for user statistics (TopHeader KPIs)."""

    total_users: int = Field(..., description="Total number of users in team")
    active_users: int = Field(..., description="Number of active users")
    pending_users: int = Field(..., description="Number of pending users")
    deactivated_users: int = Field(..., description="Number of deactivated users")

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "total_users": 10,
                "active_users": 7,
                "pending_users": 2,
                "deactivated_users": 1
            }
        }


# ============================================================================
# Adapter Functions
# ============================================================================


def user_to_response(user, include_team: bool = True) -> UserResponse:
    """
    Convert User model to UserResponse schema.

    Args:
        user: User model instance
        include_team: Whether to include team information

    Returns:
        UserResponse schema instance
    """
    team_info = None
    if include_team and user.team:
        team_info = TeamInfo(
            guid=user.team.guid,
            name=user.team.name,
            slug=user.team.slug,
        )

    return UserResponse(
        guid=user.guid,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        display_name=user.display_name,
        picture_url=user.picture_url,
        status=user.status.value if hasattr(user.status, 'value') else str(user.status),
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        team=team_info,
    )
