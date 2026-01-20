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
    authorized_roots: List[str] = Field(
        default_factory=list,
        description="List of authorized local filesystem root paths"
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
                "authorized_roots": [
                    "/Users/photographer/Photos",
                    "/Volumes/External"
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
    authorized_roots: List[str] = Field(
        default_factory=list,
        description="Authorized filesystem roots for this agent"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "guid": "agt_01hgw2bbg...",
                "api_key": "agt_key_secret_token_here",
                "name": "MacBook Pro - Studio",
                "team_guid": "tea_01hgw2bbg...",
                "authorized_roots": ["/photos", "/backup"]
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
    authorized_roots: Optional[List[str]] = Field(
        None,
        description="Updated authorized roots list (if changed)"
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
                },
                "authorized_roots": [
                    "/Users/photographer/Photos",
                    "/Volumes/External",
                    "/Volumes/NewDrive"
                ]
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
    authorized_roots: List[str] = Field(default_factory=list, description="Authorized local filesystem roots")
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
                "authorized_roots": ["/Users/photographer/Photos", "/Volumes/External"],
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


# ============================================================================
# Job Schemas (Phase 5)
# ============================================================================

class JobClaimResponse(BaseModel):
    """Response schema for job claim."""

    guid: str = Field(..., description="Job GUID (job_xxx)")
    tool: str = Field(..., description="Tool to execute (photostats, photo_pairing, pipeline_validation, collection_test)")
    mode: Optional[str] = Field(None, description="Execution mode (e.g., 'collection')")
    collection_guid: Optional[str] = Field(None, description="Collection GUID if applicable")
    collection_path: Optional[str] = Field(None, description="Collection root path")
    pipeline_guid: Optional[str] = Field(None, description="Pipeline GUID if applicable")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Additional job parameters")
    signing_secret: str = Field(..., description="Base64-encoded signing secret for result attestation")
    priority: int = Field(..., description="Job priority")
    retry_count: int = Field(..., description="Current retry attempt")
    max_retries: int = Field(..., description="Maximum retry attempts")

    model_config = {
        "json_schema_extra": {
            "example": {
                "guid": "job_01hgw2bbg...",
                "tool": "photostats",
                "mode": "collection",
                "collection_guid": "col_01hgw2bbg...",
                "collection_path": "/Users/photos/collection",
                "parameters": {"collection_guid": "col_xxx", "collection_path": "/path/to/collection"},
                "signing_secret": "base64-encoded-secret",
                "priority": 0,
                "retry_count": 0,
                "max_retries": 3
            }
        }
    }


class JobProgressRequest(BaseModel):
    """Request schema for job progress update."""

    stage: str = Field(..., description="Current execution stage")
    percentage: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Progress percentage (0-100)"
    )
    files_scanned: Optional[int] = Field(None, description="Number of files scanned")
    total_files: Optional[int] = Field(None, description="Total files to scan")
    current_file: Optional[str] = Field(None, description="Currently processing file")
    message: Optional[str] = Field(None, description="Progress message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "stage": "scanning",
                "percentage": 45,
                "files_scanned": 1234,
                "total_files": 5000,
                "message": "Analyzing file patterns..."
            }
        }
    }


class JobCompleteRequest(BaseModel):
    """Request schema for job completion."""

    results: Dict[str, Any] = Field(..., description="Structured results dictionary")
    report_html: Optional[str] = Field(None, description="HTML report content")
    files_scanned: Optional[int] = Field(None, description="Total files scanned")
    issues_found: Optional[int] = Field(None, description="Issues detected")
    signature: str = Field(..., description="HMAC-SHA256 signature of results (hex-encoded)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "results": {
                    "total_files": 5000,
                    "orphaned_files": 12,
                    "missing_sidecars": 5
                },
                "files_scanned": 5000,
                "issues_found": 17,
                "signature": "abc123def456..."
            }
        }
    }


class JobFailRequest(BaseModel):
    """Request schema for job failure."""

    error_message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Error message describing the failure"
    )
    signature: Optional[str] = Field(None, description="Optional HMAC signature")

    model_config = {
        "json_schema_extra": {
            "example": {
                "error_message": "Failed to access collection path: Permission denied"
            }
        }
    }


class JobStatusResponse(BaseModel):
    """Response schema for job status."""

    guid: str = Field(..., description="Job GUID")
    status: str = Field(..., description="Job status")
    tool: str = Field(..., description="Tool name")
    progress: Optional[Dict[str, Any]] = Field(None, description="Current progress")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    model_config = {
        "from_attributes": True
    }


class JobConfigData(BaseModel):
    """Configuration data for job execution."""

    photo_extensions: List[str] = Field(
        ...,
        description="List of recognized photo file extensions"
    )
    metadata_extensions: List[str] = Field(
        ...,
        description="List of metadata file extensions (e.g., .xmp)"
    )
    camera_mappings: Dict[str, List[Dict[str, Any]]] = Field(
        ...,
        description="Camera ID to camera info mappings"
    )
    processing_methods: Dict[str, str] = Field(
        ...,
        description="Processing method code to description mappings"
    )
    require_sidecar: List[str] = Field(
        ...,
        description="Extensions that require sidecar files"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "photo_extensions": [".dng", ".cr3", ".tiff"],
                "metadata_extensions": [".xmp"],
                "camera_mappings": {},
                "processing_methods": {"HDR": "High Dynamic Range"},
                "require_sidecar": [".cr3"]
            }
        }
    }


class PipelineData(BaseModel):
    """Pipeline definition for job execution."""

    guid: str = Field(..., description="Pipeline GUID (pip_xxx)")
    name: str = Field(..., description="Pipeline name")
    version: int = Field(..., description="Pipeline version number")
    nodes: List[Dict[str, Any]] = Field(..., description="Pipeline node definitions")
    edges: List[Dict[str, Any]] = Field(..., description="Pipeline edge connections")

    model_config = {
        "json_schema_extra": {
            "example": {
                "guid": "pip_01hgw2bbg...",
                "name": "Standard RAW Workflow",
                "version": 1,
                "nodes": [
                    {"id": "capture_1", "type": "capture", "properties": {}},
                    {"id": "file_raw", "type": "file", "properties": {"extension": ".dng"}}
                ],
                "edges": [
                    {"from": "capture_1", "to": "file_raw"}
                ]
            }
        }
    }


class ConnectorTestData(BaseModel):
    """
    Connector information for jobs accessing remote collections.

    For AGENT credential mode: Agent looks up credentials locally using the GUID.
    For SERVER credential mode: Credentials are included in this response.
    """

    guid: str = Field(..., description="Connector GUID (con_xxx)")
    type: str = Field(..., description="Connector type (s3, gcs, smb)")
    name: str = Field(..., description="Connector display name")
    credential_location: str = Field(
        ...,
        description="Credential storage location (server, agent)"
    )
    credentials: Optional[Dict[str, Any]] = Field(
        None,
        description="Decrypted credentials (only for server credential mode)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "guid": "con_01hgw2bbg...",
                "type": "s3",
                "name": "Production AWS S3",
                "credential_location": "agent",
                "credentials": None
            }
        }
    }


class JobConfigResponse(BaseModel):
    """Response schema for job-specific configuration."""

    job_guid: str = Field(..., description="Job GUID this config is for")
    config: JobConfigData = Field(..., description="Configuration data")
    collection_path: Optional[str] = Field(
        None,
        description="Root path for the collection (if applicable)"
    )
    pipeline_guid: Optional[str] = Field(
        None,
        description="Pipeline GUID (if applicable)"
    )
    pipeline: Optional[PipelineData] = Field(
        None,
        description="Pipeline definition (if applicable)"
    )
    connector: Optional[ConnectorTestData] = Field(
        None,
        description="Connector info for remote collection tests (agent-credential mode)"
    )


# ============================================================================
# Connector Schemas (for agent credential configuration)
# ============================================================================

class AgentConnectorResponse(BaseModel):
    """
    Response schema for connector details visible to agents.

    Note: Credentials are NEVER sent to agents via this endpoint.
    Agents configure and store credentials locally.
    """

    guid: str = Field(..., description="Connector GUID (con_xxx)")
    name: str = Field(..., description="Connector display name")
    type: str = Field(..., description="Connector type (s3, gcs, smb)")
    credential_location: str = Field(
        ...,
        description="Credential storage location (server, agent, pending)"
    )
    is_active: bool = Field(..., description="Whether connector is active")
    created_at: datetime = Field(..., description="Creation timestamp")

    # Indicates if THIS agent has credentials configured for this connector
    has_local_credentials: bool = Field(
        default=False,
        description="Whether this agent has credentials configured locally"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "guid": "con_01hgw2bbg...",
                "name": "Studio NAS",
                "type": "smb",
                "credential_location": "pending",
                "is_active": False,
                "created_at": "2026-01-18T10:00:00.000Z",
                "has_local_credentials": False
            }
        }
    }


class AgentConnectorListResponse(BaseModel):
    """Response schema for listing connectors available to agent."""

    connectors: List[AgentConnectorResponse] = Field(
        ...,
        description="List of connectors"
    )
    total: int = Field(..., description="Total number of connectors")

    model_config = {
        "json_schema_extra": {
            "example": {
                "connectors": [
                    {
                        "guid": "con_01hgw2bbg...",
                        "name": "Studio NAS",
                        "type": "smb",
                        "credential_location": "pending",
                        "is_active": False,
                        "created_at": "2026-01-18T10:00:00.000Z",
                        "has_local_credentials": False
                    }
                ],
                "total": 1
            }
        }
    }


class AgentConnectorMetadataResponse(BaseModel):
    """
    Response schema for connector metadata needed for credential configuration.

    Provides type-specific field requirements for the agent CLI to prompt for.
    """

    guid: str = Field(..., description="Connector GUID (con_xxx)")
    name: str = Field(..., description="Connector display name")
    type: str = Field(..., description="Connector type (s3, gcs, smb)")
    credential_location: str = Field(..., description="Credential storage location")

    # Type-specific credential field definitions
    credential_fields: List[Dict[str, Any]] = Field(
        ...,
        description="List of credential fields required for this connector type"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "guid": "con_01hgw2bbg...",
                "name": "Studio NAS",
                "type": "smb",
                "credential_location": "pending",
                "credential_fields": [
                    {"name": "server", "type": "string", "required": True, "description": "Server address"},
                    {"name": "share", "type": "string", "required": True, "description": "Share name"},
                    {"name": "username", "type": "string", "required": True, "description": "Username"},
                    {"name": "password", "type": "password", "required": True, "description": "Password"},
                    {"name": "domain", "type": "string", "required": False, "description": "Domain (optional)"}
                ]
            }
        }
    }


class ReportConnectorCapabilityRequest(BaseModel):
    """Request schema for reporting connector capability from agent."""

    has_credentials: bool = Field(
        ...,
        description="Whether agent has valid credentials for this connector"
    )
    last_tested: Optional[datetime] = Field(
        None,
        description="When credentials were last successfully tested"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "has_credentials": True,
                "last_tested": "2026-01-18T12:00:00.000Z"
            }
        }
    }


class ReportConnectorCapabilityResponse(BaseModel):
    """Response schema for connector capability report."""

    acknowledged: bool = Field(
        default=True,
        description="Whether capability was recorded"
    )
    credential_location_updated: bool = Field(
        default=False,
        description="Whether credential_location was changed (pending -> agent)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "acknowledged": True,
                "credential_location_updated": True
            }
        }
    }
