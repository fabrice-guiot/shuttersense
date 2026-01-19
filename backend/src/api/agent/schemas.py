"""
Pydantic schemas for Agent API endpoints.

Defines request and response models for:
- Agent registration
- Heartbeat updates
- Agent status and metadata
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from backend.src.models.agent import AgentStatus


# ============================================================================
# Registration Schemas
# ============================================================================

class AgentRegistrationRequest(BaseModel):
    """Request schema for agent registration."""

    registration_token: str = Field(
        ...,
        min_length=1,
        description="One-time registration token from server"
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Agent display name"
    )
    hostname: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Machine hostname"
    )
    os_info: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Operating system info (e.g., 'macOS 14.0')"
    )
    capabilities: List[str] = Field(
        default_factory=list,
        description="List of agent capabilities (tools, storage access)"
    )
    version: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Agent software version"
    )
    binary_checksum: Optional[str] = Field(
        None,
        max_length=64,
        description="SHA-256 checksum of agent binary"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "registration_token": "art_abc123...",
                "name": "MacBook Pro - Studio",
                "hostname": "studio-macbook.local",
                "os_info": "macOS 14.0 (Darwin 23.0.0)",
                "capabilities": [
                    "local_filesystem",
                    "tool:photostats:1.0.0",
                    "tool:photo_pairing:1.0.0"
                ],
                "version": "1.0.0",
                "binary_checksum": "abc123def456..."
            }
        }
    }


class AgentRegistrationResponse(BaseModel):
    """Response schema for successful agent registration."""

    guid: str = Field(..., description="Agent GUID (agt_xxx)")
    api_key: str = Field(
        ...,
        description="API key for authentication (only shown once!)"
    )
    name: str = Field(..., description="Agent display name")
    team_guid: str = Field(..., description="Team GUID (tea_xxx)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "guid": "agt_01hgw2bbg...",
                "api_key": "agt_key_secret_token_here",
                "name": "MacBook Pro - Studio",
                "team_guid": "tea_01hgw2bbg..."
            }
        }
    }


# ============================================================================
# Heartbeat Schemas
# ============================================================================

class HeartbeatRequest(BaseModel):
    """Request schema for agent heartbeat."""

    status: AgentStatus = Field(
        default=AgentStatus.ONLINE,
        description="Current agent status"
    )
    current_job_guid: Optional[str] = Field(
        None,
        description="GUID of job currently being executed"
    )
    current_job_progress: Optional[Dict[str, Any]] = Field(
        None,
        description="Progress info for current job"
    )
    error_message: Optional[str] = Field(
        None,
        max_length=1000,
        description="Error message if status is ERROR"
    )
    capabilities: Optional[List[str]] = Field(
        None,
        description="Updated capabilities list (if changed)"
    )
    version: Optional[str] = Field(
        None,
        max_length=50,
        description="Agent version (if changed)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "online",
                "current_job_guid": "job_01hgw2bbg...",
                "current_job_progress": {
                    "stage": "scanning",
                    "percentage": 45,
                    "files_scanned": 1234
                }
            }
        }
    }


class HeartbeatResponse(BaseModel):
    """Response schema for agent heartbeat."""

    acknowledged: bool = Field(
        default=True,
        description="Whether heartbeat was recorded"
    )
    server_time: datetime = Field(
        ...,
        description="Current server time (for clock sync)"
    )
    pending_commands: List[str] = Field(
        default_factory=list,
        description="Commands for agent to process"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "acknowledged": True,
                "server_time": "2026-01-18T12:00:00.000Z",
                "pending_commands": []
            }
        }
    }


# ============================================================================
# Agent Response Schemas
# ============================================================================

class AgentResponse(BaseModel):
    """Response schema for agent details."""

    guid: str = Field(..., description="Agent GUID (agt_xxx)")
    name: str = Field(..., description="Agent display name")
    hostname: str = Field(..., description="Machine hostname")
    os_info: str = Field(..., description="Operating system info")
    status: AgentStatus = Field(..., description="Current status")
    error_message: Optional[str] = Field(None, description="Error message if in ERROR state")
    last_heartbeat: Optional[datetime] = Field(None, description="Last heartbeat timestamp")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    version: str = Field(..., description="Agent software version")
    created_at: datetime = Field(..., description="Registration timestamp")

    # Relationships
    team_guid: str = Field(..., description="Team GUID")
    current_job_guid: Optional[str] = Field(None, description="Currently executing job GUID")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "guid": "agt_01hgw2bbg...",
                "name": "MacBook Pro - Studio",
                "hostname": "studio-macbook.local",
                "os_info": "macOS 14.0",
                "status": "online",
                "last_heartbeat": "2026-01-18T12:00:00.000Z",
                "capabilities": ["local_filesystem", "tool:photostats:1.0.0"],
                "version": "1.0.0",
                "created_at": "2026-01-18T10:00:00.000Z",
                "team_guid": "tea_01hgw2bbg...",
                "current_job_guid": None
            }
        }
    }


class AgentListResponse(BaseModel):
    """Response schema for listing agents."""

    agents: List[AgentResponse] = Field(default_factory=list)
    total_count: int = Field(..., description="Total number of agents")

    model_config = {
        "json_schema_extra": {
            "example": {
                "agents": [],
                "total_count": 0
            }
        }
    }


class AgentUpdateRequest(BaseModel):
    """Request schema for updating an agent."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="New agent display name"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Production Studio Mac"
            }
        }
    }


class AgentPoolStatusResponse(BaseModel):
    """Response schema for agent pool status (header badge)."""

    online_count: int = Field(..., description="Number of online agents")
    offline_count: int = Field(..., description="Number of offline agents")
    idle_count: int = Field(..., description="Online agents not running jobs")
    running_jobs_count: int = Field(..., description="Jobs currently executing")
    status: str = Field(
        ...,
        description="Pool status: offline, idle, or running"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "online_count": 3,
                "offline_count": 1,
                "idle_count": 2,
                "running_jobs_count": 1,
                "status": "running"
            }
        }
    }


# ============================================================================
# Registration Token Schemas (Admin)
# ============================================================================

class RegistrationTokenCreateRequest(BaseModel):
    """Request schema for creating a registration token."""

    name: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional name for the token (e.g., 'For Studio Mac')"
    )
    expires_in_hours: int = Field(
        default=24,
        ge=1,
        le=168,  # Max 1 week
        description="Hours until token expires"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "For Studio Mac",
                "expires_in_hours": 24
            }
        }
    }


class RegistrationTokenResponse(BaseModel):
    """Response schema for a registration token."""

    guid: str = Field(..., description="Token GUID (art_xxx)")
    token: str = Field(
        ...,
        description="The actual token value (only shown once at creation!)"
    )
    name: Optional[str] = Field(None, description="Token name")
    expires_at: datetime = Field(..., description="When the token expires")
    is_valid: bool = Field(..., description="Whether token is still valid")
    created_at: datetime = Field(..., description="Creation timestamp")
    created_by_email: Optional[str] = Field(None, description="Email of creator")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "guid": "art_01hgw2bbg...",
                "token": "art_secret_registration_token",
                "name": "For Studio Mac",
                "expires_at": "2026-01-19T12:00:00.000Z",
                "is_valid": True,
                "created_at": "2026-01-18T12:00:00.000Z",
                "created_by_email": "admin@example.com"
            }
        }
    }


class RegistrationTokenListItem(BaseModel):
    """Response schema for listing registration tokens (without token value)."""

    guid: str = Field(..., description="Token GUID (art_xxx)")
    name: Optional[str] = Field(None, description="Token name")
    expires_at: datetime = Field(..., description="When the token expires")
    is_valid: bool = Field(..., description="Whether token is still valid")
    is_used: bool = Field(..., description="Whether token has been used")
    used_by_agent_guid: Optional[str] = Field(
        None,
        description="GUID of agent that used this token"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    created_by_email: Optional[str] = Field(None, description="Email of creator")

    model_config = {
        "from_attributes": True
    }


class RegistrationTokenListResponse(BaseModel):
    """Response schema for listing registration tokens."""

    tokens: List[RegistrationTokenListItem] = Field(default_factory=list)
    total_count: int = Field(..., description="Total number of tokens")
