"""
Pydantic schemas for Agent API endpoints.

Defines request and response models for:
- Agent registration
- Heartbeat updates
- Agent status and metadata
- Agent collection management (Issue #108)
- Agent offline result upload (Issue #108)
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator

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
    platform: Optional[str] = Field(
        None,
        max_length=50,
        description="Agent platform identifier (e.g., 'darwin-arm64', 'linux-amd64')"
    )
    development_mode: bool = Field(
        False,
        description="Whether agent is running in development mode"
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
                "binary_checksum": "abc123def456...",
                "platform": "darwin-arm64",
                "development_mode": False
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

class AgentMetrics(BaseModel):
    """Schema for agent system resource metrics."""

    cpu_percent: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="CPU usage percentage (0-100)"
    )
    memory_percent: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Memory usage percentage (0-100)"
    )
    disk_free_gb: Optional[float] = Field(
        None,
        ge=0,
        description="Free disk space in GB"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "cpu_percent": 45.2,
                "memory_percent": 62.8,
                "disk_free_gb": 128.5
            }
        }
    }


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
    metrics: Optional[AgentMetrics] = Field(
        None,
        description="System resource metrics (CPU, memory, disk)"
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
                ],
                "metrics": {
                    "cpu_percent": 45.2,
                    "memory_percent": 62.8,
                    "disk_free_gb": 128.5
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
    hostname: Optional[str] = Field(None, description="Machine hostname")
    os_info: Optional[str] = Field(None, description="Operating system info")
    status: AgentStatus = Field(..., description="Current status")
    error_message: Optional[str] = Field(None, description="Error message if in ERROR state")
    last_heartbeat: Optional[datetime] = Field(None, description="Last heartbeat timestamp")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    authorized_roots: List[str] = Field(default_factory=list, description="Authorized local filesystem roots")
    version: Optional[str] = Field(None, description="Agent software version")
    created_at: datetime = Field(..., description="Registration timestamp")
    metrics: Optional[AgentMetrics] = Field(None, description="System resource metrics")

    # Relationships
    team_guid: str = Field(..., description="Team GUID")
    current_job_guid: Optional[str] = Field(None, description="Currently executing job GUID")

    # Load info (Phase 12)
    running_jobs_count: int = Field(0, description="Number of running/assigned jobs")

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
                "current_job_guid": None,
                "metrics": None,
                "running_jobs_count": 0
            }
        }
    }


class AgentJobHistoryItem(BaseModel):
    """Response schema for a job in agent's history."""

    guid: str = Field(..., description="Job GUID (job_xxx)")
    tool: str = Field(..., description="Tool name")
    collection_guid: Optional[str] = Field(None, description="Collection GUID")
    collection_name: Optional[str] = Field(None, description="Collection name")
    status: str = Field(..., description="Job status")
    started_at: Optional[datetime] = Field(None, description="When job started")
    completed_at: Optional[datetime] = Field(None, description="When job completed/failed")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "guid": "job_01hgw2bbg...",
                "tool": "photostats",
                "collection_guid": "col_01hgw2bbg...",
                "collection_name": "Wedding Photos",
                "status": "completed",
                "started_at": "2026-01-18T10:00:00.000Z",
                "completed_at": "2026-01-18T10:05:00.000Z",
                "error_message": None
            }
        }
    }


class AgentDetailResponse(BaseModel):
    """Response schema for agent detail view with extended information."""

    guid: str = Field(..., description="Agent GUID (agt_xxx)")
    name: str = Field(..., description="Agent display name")
    hostname: Optional[str] = Field(None, description="Machine hostname")
    os_info: Optional[str] = Field(None, description="Operating system info")
    status: AgentStatus = Field(..., description="Current status")
    error_message: Optional[str] = Field(None, description="Error message if in ERROR state")
    last_heartbeat: Optional[datetime] = Field(None, description="Last heartbeat timestamp")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    authorized_roots: List[str] = Field(default_factory=list, description="Authorized local filesystem roots")
    version: Optional[str] = Field(None, description="Agent software version")
    created_at: datetime = Field(..., description="Registration timestamp")
    metrics: Optional[AgentMetrics] = Field(None, description="System resource metrics")

    # Relationships
    team_guid: str = Field(..., description="Team GUID")
    current_job_guid: Optional[str] = Field(None, description="Currently executing job GUID")

    # Extended detail fields
    bound_collections_count: int = Field(0, description="Number of collections bound to this agent")
    total_jobs_completed: int = Field(0, description="Total jobs completed by this agent")
    total_jobs_failed: int = Field(0, description="Total jobs failed by this agent")
    recent_jobs: List[AgentJobHistoryItem] = Field(
        default_factory=list,
        description="Recent job history (last 10 jobs)"
    )

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
                "current_job_guid": "job_01hgw2bbg...",
                "metrics": {"cpu_percent": 45.2, "memory_percent": 62.8, "disk_free_gb": 128.5},
                "bound_collections_count": 3,
                "total_jobs_completed": 125,
                "total_jobs_failed": 2,
                "recent_jobs": []
            }
        }
    }


class AgentJobHistoryResponse(BaseModel):
    """Response schema for paginated agent job history."""

    jobs: List[AgentJobHistoryItem] = Field(default_factory=list)
    total_count: int = Field(..., description="Total number of jobs")
    offset: int = Field(..., description="Current offset")
    limit: int = Field(..., description="Items per page")

    model_config = {
        "json_schema_extra": {
            "example": {
                "jobs": [],
                "total_count": 127,
                "offset": 0,
                "limit": 20
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

class PreviousResultData(BaseModel):
    """
    Previous result data for Input State comparison (Issue #92).

    Provided in job claim response when a previous result exists
    for the same collection+tool combination.
    """

    guid: str = Field(..., description="Result GUID (res_xxx)")
    input_state_hash: Optional[str] = Field(
        None,
        description="SHA-256 hash of Input State (null for legacy results without hash)"
    )
    completed_at: datetime = Field(..., description="When the previous result was created")

    model_config = {
        "json_schema_extra": {
            "example": {
                "guid": "res_01hgw2bbg...",
                "input_state_hash": "e3b0c44298fc1c149afbf4c8996fb924...",
                "completed_at": "2026-01-20T10:00:00.000Z"
            }
        }
    }


class CachedFileInfo(BaseModel):
    """
    Cached FileInfo from inventory import (Issue #107 - T071).

    Represents a file's metadata from the bucket inventory, used to skip
    cloud API calls when computing Input State hashes.
    """
    key: str = Field(..., description="Full object key/path (e.g., '2020/vacation/IMG_001.CR3')")
    size: int = Field(..., ge=0, description="File size in bytes")
    last_modified: str = Field(..., description="ISO8601 timestamp of last modification")
    etag: Optional[str] = Field(None, description="Object ETag (for change detection)")
    storage_class: Optional[str] = Field(None, description="Storage class (e.g., STANDARD, GLACIER)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "key": "2020/vacation/IMG_001.CR3",
                "size": 25000000,
                "last_modified": "2022-11-25T13:30:49.000Z",
                "etag": "371e1101d4248ef2609e269697bb0221-2",
                "storage_class": "STANDARD"
            }
        }
    }


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

    # Storage Optimization Fields (Issue #92)
    previous_result: Optional[PreviousResultData] = Field(
        None,
        description="Previous result for comparison (null if no previous result exists)"
    )

    # Cached FileInfo from Inventory Import (Issue #107 - T071)
    file_info: Optional[List[CachedFileInfo]] = Field(
        None,
        description="Cached file metadata from inventory import. When present, agent should "
                    "use this instead of calling cloud APIs (unless force_cloud_refresh is true)."
    )
    file_info_source: Optional[str] = Field(
        None,
        description="Source of file_info: 'inventory' (from bucket inventory) or 'api' (from cloud API)"
    )

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
                "max_retries": 3,
                "previous_result": {
                    "guid": "res_01hgw2bbg...",
                    "input_state_hash": "e3b0c44298fc1c149afbf4c8996fb924...",
                    "completed_at": "2026-01-20T10:00:00.000Z"
                },
                "file_info": [
                    {
                        "key": "2020/vacation/IMG_001.CR3",
                        "size": 25000000,
                        "last_modified": "2022-11-25T13:30:49.000Z"
                    }
                ],
                "file_info_source": "inventory"
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

    # Storage Optimization Fields (Issue #92)
    input_state_hash: Optional[str] = Field(
        None,
        min_length=64,
        max_length=64,
        description="SHA-256 hash of Input State (64 char hex string)"
    )
    input_state_json: Optional[str] = Field(
        None,
        description="Full Input State JSON (only sent in DEBUG mode for troubleshooting)"
    )

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
                "signature": "abc123def456...",
                "input_state_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            }
        }
    }


class JobNoChangeRequest(BaseModel):
    """
    Request schema for NO_CHANGE job completion (Issue #92).

    Used when the agent detects the Input State hash matches
    a previous result, indicating no changes to the collection.
    """

    input_state_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA-256 hash of Input State (must match previous_result)"
    )
    source_result_guid: str = Field(
        ...,
        pattern=r"^res_[0-9a-hjkmnp-tv-z]{26}$",
        description="GUID of the previous result being referenced (res_xxx)"
    )
    signature: str = Field(..., description="HMAC-SHA256 signature of request (hex-encoded)")
    input_state_json: Optional[str] = Field(
        None,
        description="Full Input State JSON (only in DEBUG mode)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "input_state_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "source_result_guid": "res_01hgw2bbg0000000000000001",
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
    cameras: Dict[str, List[Dict[str, Any]]] = Field(
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
                "cameras": {},
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
    inventory_config: Optional[Dict[str, Any]] = Field(
        None,
        description="Inventory configuration for inventory_validate jobs"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "guid": "con_01hgw2bbg...",
                "type": "s3",
                "name": "Production AWS S3",
                "credential_location": "agent",
                "credentials": None,
                "inventory_config": None
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


class TeamConfigResponse(BaseModel):
    """Standalone team configuration (not job-specific).

    Used by agent CLI commands (test, run) to get the team's tool
    configuration without needing a job. Includes the default pipeline
    definition if one exists.
    """

    config: JobConfigData = Field(..., description="Team tool configuration")
    default_pipeline: Optional[PipelineData] = Field(
        None,
        description="Default pipeline definition (if one exists)"
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


# ============================================================================
# Chunked Upload Schemas (Phase 15)
# ============================================================================

class InitiateUploadRequest(BaseModel):
    """Request schema for initiating a chunked upload."""

    upload_type: str = Field(
        ...,
        description="Type of content: 'results_json', 'report_html', or 'file_info'"
    )
    expected_size: int = Field(
        ...,
        gt=0,
        description="Total size in bytes of the content to upload"
    )
    chunk_size: Optional[int] = Field(
        None,
        gt=0,
        le=10485760,  # 10MB max
        description="Optional custom chunk size (default 5MB, max 10MB)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "upload_type": "results_json",
                "expected_size": 5000000,
                "chunk_size": 5242880
            }
        }
    }


class InitiateUploadResponse(BaseModel):
    """Response schema for initiating a chunked upload."""

    upload_id: str = Field(
        ...,
        description="Unique upload session ID"
    )
    chunk_size: int = Field(
        ...,
        description="Size of each chunk (except last)"
    )
    total_chunks: int = Field(
        ...,
        description="Total number of chunks expected"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "upload_id": "abc123def456...",
                "chunk_size": 5242880,
                "total_chunks": 2
            }
        }
    }


class ChunkUploadResponse(BaseModel):
    """Response schema for chunk upload."""

    received: bool = Field(
        ...,
        description="Whether chunk was received (True for new, False for duplicate)"
    )
    chunk_index: int = Field(
        ...,
        description="Index of the chunk that was uploaded"
    )
    chunks_received: int = Field(
        ...,
        description="Total chunks received so far"
    )
    total_chunks: int = Field(
        ...,
        description="Total chunks expected"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "received": True,
                "chunk_index": 0,
                "chunks_received": 1,
                "total_chunks": 2
            }
        }
    }


class FinalizeUploadRequest(BaseModel):
    """Request schema for finalizing an upload."""

    checksum: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA-256 checksum of the complete content (hex-encoded)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            }
        }
    }


class FinalizeUploadResponse(BaseModel):
    """Response schema for finalizing an upload."""

    success: bool = Field(
        ...,
        description="Whether the upload was finalized successfully"
    )
    upload_type: str = Field(
        ...,
        description="Type of content that was uploaded"
    )
    content_size: int = Field(
        ...,
        description="Size of the finalized content"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "upload_type": "results_json",
                "content_size": 5000000
            }
        }
    }


class UploadStatusResponse(BaseModel):
    """Response schema for upload status."""

    upload_id: str = Field(..., description="Upload session ID")
    job_guid: str = Field(..., description="Associated job GUID")
    upload_type: str = Field(..., description="Type of content being uploaded")
    expected_size: int = Field(..., description="Total expected bytes")
    received_size: int = Field(..., description="Bytes received so far")
    total_chunks: int = Field(..., description="Total chunks expected")
    received_chunks: int = Field(..., description="Chunks received so far")
    received_chunk_indices: List[int] = Field(..., description="Indices of received chunks")
    missing_chunk_indices: List[int] = Field(..., description="Indices of missing chunks")
    is_complete: bool = Field(..., description="Whether all chunks received")
    expires_at: str = Field(..., description="Session expiration timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "upload_id": "abc123def456...",
                "job_guid": "job_01hgw2bbg...",
                "upload_type": "results_json",
                "expected_size": 5000000,
                "received_size": 2621440,
                "total_chunks": 2,
                "received_chunks": 1,
                "received_chunk_indices": [0],
                "missing_chunk_indices": [1],
                "is_complete": False,
                "expires_at": "2026-01-18T13:00:00.000Z"
            }
        }
    }


class JobCompleteWithUploadRequest(BaseModel):
    """
    Request schema for job completion with chunked upload support.

    Supports two modes:
    1. Inline: Provide results directly (for small results < 1MB)
    2. Chunked: Provide upload_ids for pre-uploaded content

    At least one of results or results_upload_id must be provided.
    """

    results_upload_id: Optional[str] = Field(
        None,
        description="Upload ID for chunked results JSON (if > 1MB)"
    )
    report_upload_id: Optional[str] = Field(
        None,
        description="Upload ID for chunked HTML report"
    )
    results: Optional[Dict[str, Any]] = Field(
        None,
        description="Inline results (only if < 1MB, mutually exclusive with results_upload_id)"
    )
    report_html: Optional[str] = Field(
        None,
        description="Inline HTML report (for small reports, mutually exclusive with report_upload_id)"
    )
    files_scanned: Optional[int] = Field(None, description="Total files scanned")
    issues_found: Optional[int] = Field(None, description="Issues detected")
    signature: str = Field(..., description="HMAC-SHA256 signature of results (hex-encoded)")

    # Storage Optimization Fields (Issue #92)
    input_state_hash: Optional[str] = Field(
        None,
        min_length=64,
        max_length=64,
        description="SHA-256 hash of Input State (64 char hex string)"
    )
    input_state_json: Optional[str] = Field(
        None,
        description="Full Input State JSON (only sent in DEBUG mode)"
    )

    @model_validator(mode='after')
    def validate_results_source(self) -> 'JobCompleteWithUploadRequest':
        """Ensure either results or results_upload_id is provided."""
        # Use 'is None' check instead of truthiness to allow empty dicts
        if self.results is None and self.results_upload_id is None:
            raise ValueError("Either 'results' or 'results_upload_id' must be provided")
        if self.results is not None and self.results_upload_id is not None:
            raise ValueError("Cannot provide both 'results' and 'results_upload_id'")
        if self.report_html is not None and self.report_upload_id is not None:
            raise ValueError("Cannot provide both 'report_html' and 'report_upload_id'")
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "results_upload_id": "abc123def456...",
                "report_upload_id": "xyz789ghi012...",
                "files_scanned": 5000,
                "issues_found": 17,
                "signature": "abc123def456..."
            }
        }
    }


# ============================================================================
# Inventory Validation Schemas (Issue #107)
# ============================================================================

class InventoryValidationRequest(BaseModel):
    """Request schema for reporting inventory validation results."""

    connector_guid: str = Field(
        ...,
        description="Connector GUID (con_xxx) being validated"
    )
    success: bool = Field(
        ...,
        description="Whether validation succeeded"
    )
    error_message: Optional[str] = Field(
        None,
        max_length=500,
        description="Error message if validation failed"
    )
    manifest_count: Optional[int] = Field(
        None,
        ge=0,
        description="Number of manifests found (if successful)"
    )
    latest_manifest: Optional[str] = Field(
        None,
        max_length=500,
        description="Path of the latest manifest.json (e.g., '2026-01-26T01-00Z/manifest.json')"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "connector_guid": "con_01hgw2bbg0000000000000001",
                "success": True,
                "manifest_count": 3,
                "latest_manifest": "2026-01-26T01-00Z/manifest.json"
            }
        }
    }


class InventoryValidationResponse(BaseModel):
    """Response schema for inventory validation result submission."""

    status: str = Field(
        ...,
        description="Validation status (validated/failed)"
    )
    message: str = Field(
        ...,
        description="Status message"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "validated",
                "message": "Inventory configuration validated successfully"
            }
        }
    }


# ============================================================================
# Inventory Folders Schemas (Issue #107)
# ============================================================================

class InventoryFoldersRequest(BaseModel):
    """Request schema for reporting discovered inventory folders."""

    connector_guid: str = Field(
        ...,
        description="Connector GUID (con_xxx)"
    )
    folders: List[str] = Field(
        ...,
        description="List of discovered folder paths"
    )
    folder_stats: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Stats per folder (file_count, total_size)"
    )
    total_files: int = Field(
        ...,
        ge=0,
        description="Total files processed"
    )
    total_size: int = Field(
        ...,
        ge=0,
        description="Total size in bytes"
    )
    latest_manifest: Optional[str] = Field(
        default=None,
        description="Display path of the manifest used for this import (e.g., '2026-01-26T01-00Z/manifest.json')"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "connector_guid": "con_01hgw2bbg0000000000000001",
                "folders": ["2020/", "2020/Vacation/", "2021/"],
                "folder_stats": {
                    "2020/": {"file_count": 150, "total_size": 3750000000},
                    "2020/Vacation/": {"file_count": 100, "total_size": 2500000000}
                },
                "total_files": 250,
                "total_size": 6250000000,
                "latest_manifest": "2026-01-26T01-00Z/manifest.json"
            }
        }
    }


class InventoryFoldersResponse(BaseModel):
    """Response schema for inventory folders submission."""

    status: str = Field(
        ...,
        description="Processing status (success/error)"
    )
    message: str = Field(
        ...,
        description="Status message"
    )
    folders_stored: int = Field(
        ...,
        ge=0,
        description="Number of folders stored/updated"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "message": "Stored 42 inventory folders",
                "folders_stored": 42
            }
        }
    }


# ============================================================================
# Inventory FileInfo Schemas (Issue #107 - Phase B)
# ============================================================================

class CollectionFileInfoItem(BaseModel):
    """FileInfo item for a single file."""

    key: str = Field(
        ...,
        description="Full object key/path"
    )
    size: int = Field(
        ...,
        ge=0,
        description="File size in bytes"
    )
    last_modified: str = Field(
        ...,
        description="ISO8601 timestamp of last modification"
    )
    etag: Optional[str] = Field(
        None,
        description="Object ETag (for change detection)"
    )
    storage_class: Optional[str] = Field(
        None,
        description="Storage class (e.g., STANDARD, GLACIER)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "key": "2020/vacation/IMG_001.CR3",
                "size": 25000000,
                "last_modified": "2022-11-25T13:30:49.000Z",
                "etag": "371e1101d4248ef2609e269697bb0221-2",
                "storage_class": "STANDARD"
            }
        }
    }


class CollectionFileInfo(BaseModel):
    """FileInfo for a single collection from inventory."""

    collection_guid: str = Field(
        ...,
        description="Collection GUID (col_xxx)"
    )
    file_info: List[CollectionFileInfoItem] = Field(
        ...,
        description="List of FileInfo items for this collection"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "collection_guid": "col_01hgw2bbg0000000000000001",
                "file_info": [
                    {
                        "key": "2020/vacation/IMG_001.CR3",
                        "size": 25000000,
                        "last_modified": "2022-11-25T13:30:49.000Z"
                    }
                ]
            }
        }
    }


class InventoryFileInfoRequest(BaseModel):
    """Request schema for reporting FileInfo from inventory import Phase B.

    Supports two modes:
    1. Inline: Provide connector_guid and collections directly (for small FileInfo)
    2. Chunked: Provide file_info_upload_id (for large FileInfo > 1MB)

    Issue #107: Added chunked upload support for large collections.
    """

    connector_guid: Optional[str] = Field(
        None,
        description="Connector GUID (con_xxx) - required for inline mode"
    )
    collections: Optional[List[CollectionFileInfo]] = Field(
        None,
        description="List of collections with their FileInfo - required for inline mode"
    )
    file_info_upload_id: Optional[str] = Field(
        None,
        description="Upload session ID from chunked upload (for large FileInfo > 1MB)"
    )

    @model_validator(mode="after")
    def validate_mode(self) -> "InventoryFileInfoRequest":
        """Validate that either inline or chunked mode is used, not both or neither."""
        has_inline = self.connector_guid is not None and self.collections is not None
        has_chunked = self.file_info_upload_id is not None

        if has_inline and has_chunked:
            raise ValueError("Cannot provide both inline (connector_guid/collections) and chunked (file_info_upload_id) data")
        if not has_inline and not has_chunked:
            raise ValueError("Must provide either inline (connector_guid and collections) or chunked (file_info_upload_id) data")
        if self.connector_guid is not None and self.collections is None:
            raise ValueError("connector_guid requires collections")
        if self.collections is not None and self.connector_guid is None:
            raise ValueError("collections requires connector_guid")

        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "description": "Inline mode (small FileInfo)",
                    "value": {
                        "connector_guid": "con_01hgw2bbg0000000000000001",
                        "collections": [
                            {
                                "collection_guid": "col_01hgw2bbg0000000000000001",
                                "file_info": [
                                    {
                                        "key": "2020/vacation/IMG_001.CR3",
                                        "size": 25000000,
                                        "last_modified": "2022-11-25T13:30:49.000Z"
                                    }
                                ]
                            }
                        ]
                    }
                },
                {
                    "description": "Chunked mode (large FileInfo)",
                    "value": {
                        "file_info_upload_id": "abc123def456..."
                    }
                }
            ]
        }
    }


class InventoryFileInfoResponse(BaseModel):
    """Response schema for FileInfo submission."""

    status: str = Field(
        ...,
        description="Processing status (success/error)"
    )
    message: str = Field(
        ...,
        description="Status message"
    )
    collections_updated: int = Field(
        ...,
        ge=0,
        description="Number of collections updated with FileInfo"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "message": "Updated FileInfo for 5 collections",
                "collections_updated": 5
            }
        }
    }


# ============================================================================
# Connector Collections Query (Issue #107 - Phase B)
# ============================================================================

class ConnectorCollectionInfo(BaseModel):
    """Collection info for inventory FileInfo population and delta detection."""

    collection_guid: str = Field(
        ...,
        description="Collection GUID (col_xxx)"
    )
    folder_path: str = Field(
        ...,
        description="Inventory folder path prefix for this collection"
    )
    file_info: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Stored FileInfo for delta detection (Phase C). None if first import."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "collection_guid": "col_01hgw2bbg0000000000000001",
                "folder_path": "2020/vacation/",
                "file_info": [{"key": "2020/vacation/IMG_001.CR3", "size": 25000000}]
            }
        }
    }


class ConnectorCollectionsResponse(BaseModel):
    """Response with collections mapped to a connector's inventory folders."""

    connector_guid: str = Field(
        ...,
        description="Connector GUID (con_xxx)"
    )
    collections: List[ConnectorCollectionInfo] = Field(
        default_factory=list,
        description="Collections with their folder path prefix"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "connector_guid": "con_01hgw2bbg0000000000000001",
                "collections": [
                    {
                        "collection_guid": "col_01hgw2bbg0000000000000001",
                        "folder_path": "2020/vacation/"
                    },
                    {
                        "collection_guid": "col_01hgw2bbg0000000000000002",
                        "folder_path": "2021/wedding/"
                    }
                ]
            }
        }
    }


# ============================================================================
# Inventory Delta Reporting (Issue #107 - Phase C / Phase 8)
# Tasks: T091, T092
# ============================================================================

class DeltaSummary(BaseModel):
    """Summary of changes detected for a collection."""

    new_count: int = Field(..., ge=0, description="Number of new files")
    modified_count: int = Field(..., ge=0, description="Number of modified files")
    deleted_count: int = Field(..., ge=0, description="Number of deleted files")
    new_size_bytes: int = Field(default=0, ge=0, description="Total size of new files")
    modified_size_change_bytes: int = Field(default=0, description="Net size change from modifications")
    deleted_size_bytes: int = Field(default=0, ge=0, description="Total size of deleted files")
    total_changes: int = Field(..., ge=0, description="Total number of changes")

    model_config = {
        "json_schema_extra": {
            "example": {
                "new_count": 10,
                "modified_count": 5,
                "deleted_count": 2,
                "new_size_bytes": 250000000,
                "modified_size_change_bytes": 50000000,
                "deleted_size_bytes": 10000000,
                "total_changes": 17
            }
        }
    }


class FileDeltaItem(BaseModel):
    """Individual file change item."""

    key: str = Field(..., description="File path/key")
    change_type: str = Field(..., description="Type of change: new, modified, deleted")
    size: int = Field(..., ge=0, description="File size")
    previous_size: Optional[int] = Field(None, description="Previous size (for modified files)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "key": "2020/vacation/IMG_001.CR3",
                "change_type": "new",
                "size": 25000000
            }
        }
    }


class CollectionDeltaItem(BaseModel):
    """Delta result for a single collection."""

    collection_guid: str = Field(..., description="Collection GUID (col_xxx)")
    summary: DeltaSummary = Field(..., description="Summary of changes")
    is_first_import: bool = Field(default=False, description="True if no previous FileInfo existed")
    changes: List[FileDeltaItem] = Field(default_factory=list, description="List of individual changes (may be truncated)")
    changes_truncated: bool = Field(default=False, description="True if changes list was truncated")

    model_config = {
        "json_schema_extra": {
            "example": {
                "collection_guid": "col_01hgw2bbg0000000000000001",
                "summary": {
                    "new_count": 10,
                    "modified_count": 5,
                    "deleted_count": 2,
                    "new_size_bytes": 250000000,
                    "modified_size_change_bytes": 50000000,
                    "deleted_size_bytes": 10000000,
                    "total_changes": 17
                },
                "is_first_import": False,
                "changes": [],
                "changes_truncated": True
            }
        }
    }


class InventoryDeltaRequest(BaseModel):
    """Request schema for reporting delta detection results from Phase C.

    Supports two modes:
    1. Inline: Provide connector_guid and deltas directly (for small payloads)
    2. Chunked: Provide delta_upload_id (for large payloads > 1MB)

    Issue #107 Phase 8: Delta Detection Between Inventories
    """

    connector_guid: Optional[str] = Field(
        None,
        description="Connector GUID (con_xxx) - required for inline mode"
    )
    deltas: Optional[List[CollectionDeltaItem]] = Field(
        None,
        description="List of collection deltas - required for inline mode"
    )
    delta_upload_id: Optional[str] = Field(
        None,
        description="Upload session ID from chunked upload (for large deltas > 1MB)"
    )

    @model_validator(mode="after")
    def validate_mode(self) -> "InventoryDeltaRequest":
        """Validate that either inline or chunked mode is used."""
        has_inline = self.connector_guid is not None and self.deltas is not None
        has_chunked = self.delta_upload_id is not None

        if has_inline and has_chunked:
            raise ValueError("Cannot provide both inline (connector_guid/deltas) and chunked (delta_upload_id) data")
        if not has_inline and not has_chunked:
            raise ValueError("Must provide either inline (connector_guid and deltas) or chunked (delta_upload_id) data")
        if self.connector_guid is not None and self.deltas is None:
            raise ValueError("connector_guid requires deltas")
        if self.deltas is not None and self.connector_guid is None:
            raise ValueError("deltas requires connector_guid")

        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "description": "Inline mode (small deltas)",
                    "value": {
                        "connector_guid": "con_01hgw2bbg0000000000000001",
                        "deltas": [
                            {
                                "collection_guid": "col_01hgw2bbg0000000000000001",
                                "summary": {
                                    "new_count": 10,
                                    "modified_count": 5,
                                    "deleted_count": 2,
                                    "new_size_bytes": 250000000,
                                    "modified_size_change_bytes": 50000000,
                                    "deleted_size_bytes": 10000000,
                                    "total_changes": 17
                                },
                                "is_first_import": False,
                                "changes": [],
                                "changes_truncated": True
                            }
                        ]
                    }
                },
                {
                    "description": "Chunked mode (large deltas)",
                    "value": {
                        "delta_upload_id": "abc123def456..."
                    }
                }
            ]
        }
    }


class InventoryDeltaResponse(BaseModel):
    """Response schema for delta submission."""

    status: str = Field(..., description="Processing status (success/error)")
    message: str = Field(..., description="Status message")
    collections_updated: int = Field(..., ge=0, description="Number of collections with delta stored")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "message": "Stored delta for 5 collections",
                "collections_updated": 5
            }
        }
    }


# ============================================================================
# Agent Collection Schemas (Issue #108)
# Tasks: T004, T005
# ============================================================================

class TestResultSummary(BaseModel):
    """Optional test results from the agent's local test cache."""

    tested_at: datetime = Field(..., description="When the test was executed")
    file_count: int = Field(..., ge=0, description="Total files found")
    photo_count: int = Field(..., ge=0, description="Files matching photo extensions")
    sidecar_count: int = Field(..., ge=0, description="Files matching metadata extensions")
    tools_tested: List[str] = Field(
        default_factory=list,
        description="Tools that were run"
    )
    issues_found: Optional[Dict[str, Any]] = Field(
        None,
        description="Summary of issues per tool"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "tested_at": "2026-01-28T12:00:00.000Z",
                "file_count": 5000,
                "photo_count": 4500,
                "sidecar_count": 450,
                "tools_tested": ["photostats", "photo_pairing"],
                "issues_found": {"photostats": {"orphaned_files": 3}}
            }
        }
    }


class AgentCreateCollectionRequest(BaseModel):
    """Request schema for agent-initiated collection creation."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Collection display name"
    )
    location: str = Field(
        ...,
        min_length=1,
        description="Absolute path to the local directory"
    )
    test_results: Optional[TestResultSummary] = Field(
        None,
        description="Optional test results from the local test cache"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Vacation Photos 2024",
                "location": "/photos/2024",
                "test_results": {
                    "tested_at": "2026-01-28T12:00:00.000Z",
                    "file_count": 5000,
                    "photo_count": 4500,
                    "sidecar_count": 450,
                    "tools_tested": ["photostats"],
                    "issues_found": None
                }
            }
        }
    }


class AgentCreateCollectionResponse(BaseModel):
    """Response schema for successful agent collection creation."""

    guid: str = Field(..., description="Collection GUID (col_xxx)")
    name: str = Field(..., description="Collection display name")
    type: str = Field(..., description="Collection type (always LOCAL)")
    location: str = Field(..., description="Absolute path")
    bound_agent_guid: str = Field(..., description="Agent GUID (agt_xxx)")
    web_url: str = Field(
        ...,
        description="URL to view this collection in the web UI"
    )
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "guid": "col_01hgw2bbg0000000000000001",
                "name": "Vacation Photos 2024",
                "type": "LOCAL",
                "location": "/photos/2024",
                "bound_agent_guid": "agt_01hgw2bbg0000000000000001",
                "web_url": "https://app.shuttersense.ai/collections/col_01hgw2bbg0000000000000001",
                "created_at": "2026-01-28T12:00:00.000Z"
            }
        }
    }


class AgentCollectionItem(BaseModel):
    """Item in the agent collection list response."""

    guid: str = Field(..., description="Collection GUID (col_xxx)")
    name: str = Field(..., description="Collection display name")
    type: str = Field(..., description="Collection type: LOCAL, S3, GCS, SMB")
    location: str = Field(..., description="Path or bucket/prefix")
    bound_agent_guid: Optional[str] = Field(
        None, description="Agent GUID for LOCAL collections"
    )
    connector_guid: Optional[str] = Field(
        None, description="Connector GUID for remote collections"
    )
    connector_name: Optional[str] = Field(
        None, description="Connector display name"
    )
    is_accessible: Optional[bool] = Field(
        None, description="Last known accessibility status"
    )
    last_analysis_at: Optional[datetime] = Field(
        None, description="When last analysis completed"
    )
    supports_offline: bool = Field(
        ..., description="True only for LOCAL collections"
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "guid": "col_01hgw2bbg0000000000000001",
                "name": "Vacation Photos 2024",
                "type": "LOCAL",
                "location": "/photos/2024",
                "bound_agent_guid": "agt_01hgw2bbg0000000000000001",
                "connector_guid": None,
                "connector_name": None,
                "is_accessible": True,
                "last_analysis_at": "2026-01-28T12:00:00.000Z",
                "supports_offline": True
            }
        }
    }


class AgentCollectionListResponse(BaseModel):
    """Response schema for listing agent-bound collections."""

    collections: List[AgentCollectionItem] = Field(
        default_factory=list,
        description="List of bound collections"
    )
    total_count: int = Field(..., description="Total number of bound collections")

    model_config = {
        "json_schema_extra": {
            "example": {
                "collections": [],
                "total_count": 0
            }
        }
    }


class AgentCollectionTestRequest(BaseModel):
    """Request schema for reporting collection accessibility test results."""

    is_accessible: bool = Field(
        ...,
        description="Whether the path is currently accessible"
    )
    error_message: Optional[str] = Field(
        None,
        max_length=1000,
        description="Error details if not accessible"
    )
    file_count: Optional[int] = Field(
        None,
        ge=0,
        description="Number of files found (if accessible)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "is_accessible": True,
                "error_message": None,
                "file_count": 5000
            }
        }
    }


class AgentCollectionTestResponse(BaseModel):
    """Response schema for collection accessibility test update."""

    guid: str = Field(..., description="Collection GUID (col_xxx)")
    is_accessible: bool = Field(
        ..., description="Updated accessibility status"
    )
    updated_at: datetime = Field(..., description="When status was updated")

    model_config = {
        "json_schema_extra": {
            "example": {
                "guid": "col_01hgw2bbg0000000000000001",
                "is_accessible": True,
                "updated_at": "2026-01-28T12:00:00.000Z"
            }
        }
    }


# ============================================================================
# Agent Offline Result Upload Schemas (Issue #108)
# Task: T006
# ============================================================================

class AgentPrepareResultUploadRequest(BaseModel):
    """Request schema for preparing a chunked offline result upload.

    Creates a placeholder Job so the agent can use the existing chunked
    upload infrastructure (POST /jobs/{guid}/uploads/initiate) before
    submitting the final result via POST /results/upload.
    """

    result_id: str = Field(
        ...,
        min_length=1,
        description="Locally generated UUID for idempotent upload"
    )
    collection_guid: str = Field(
        ...,
        min_length=1,
        description="GUID of the collection analyzed (col_xxx)"
    )
    tool: str = Field(
        ...,
        min_length=1,
        description="Tool used: photostats, photo_pairing, pipeline_validation"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "result_id": "550e8400-e29b-41d4-a716-446655440000",
                "collection_guid": "col_01hgw2bbg0000000000000001",
                "tool": "photostats",
            }
        }
    }


class AgentPrepareResultUploadResponse(BaseModel):
    """Response schema for prepare result upload (returns job_guid for chunked uploads)."""

    job_guid: str = Field(
        ..., description="GUID of the placeholder Job (job_xxx) — use for chunked uploads"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_guid": "job_01hgw2bbg0000000000000001",
            }
        }
    }


class AgentUploadResultRequest(BaseModel):
    """Request schema for uploading an offline analysis result.

    Supports two modes:
    1. Inline: Provide analysis_data and optional html_report directly.
    2. Chunked: Provide analysis_data_upload_id and/or report_upload_id
       from pre-uploaded chunked content (requires prior /results/upload/prepare).
    """

    result_id: str = Field(
        ...,
        min_length=1,
        description="Locally generated UUID for idempotent upload"
    )
    collection_guid: str = Field(
        ...,
        min_length=1,
        description="GUID of the collection analyzed (col_xxx)"
    )
    tool: str = Field(
        ...,
        min_length=1,
        description="Tool used: photostats, photo_pairing, pipeline_validation"
    )
    executed_at: datetime = Field(
        ...,
        description="When the analysis was executed on the agent"
    )
    # Inline mode fields
    analysis_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Full analysis output (inline mode)"
    )
    html_report: Optional[str] = Field(
        None,
        description="HTML report string (inline mode)"
    )
    # Chunked mode fields
    analysis_data_upload_id: Optional[str] = Field(
        None,
        description="Upload ID for chunked analysis data (from chunked upload)"
    )
    report_upload_id: Optional[str] = Field(
        None,
        description="Upload ID for chunked HTML report (from chunked upload)"
    )
    # Storage Optimization (Issue #92 + Issue #108)
    input_state_hash: Optional[str] = Field(
        None,
        min_length=64,
        max_length=64,
        description="SHA-256 hash of Input State for no-change detection"
    )

    @model_validator(mode='after')
    def validate_data_source(self) -> 'AgentUploadResultRequest':
        """Ensure analysis_data is provided either inline or via upload_id."""
        has_inline = self.analysis_data is not None
        has_upload = self.analysis_data_upload_id is not None
        if not has_inline and not has_upload:
            raise ValueError(
                "Must provide either 'analysis_data' (inline) or "
                "'analysis_data_upload_id' (chunked upload)"
            )
        if has_inline and has_upload:
            raise ValueError(
                "Cannot provide both 'analysis_data' and 'analysis_data_upload_id'"
            )
        # html_report and report_upload_id are mutually exclusive
        if self.html_report is not None and self.report_upload_id is not None:
            raise ValueError(
                "Cannot provide both 'html_report' and 'report_upload_id'"
            )
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "result_id": "550e8400-e29b-41d4-a716-446655440000",
                "collection_guid": "col_01hgw2bbg0000000000000001",
                "tool": "photostats",
                "executed_at": "2026-01-28T10:00:00.000Z",
                "analysis_data": {
                    "total_files": 5000,
                    "orphaned_files": 12,
                    "missing_sidecars": 5
                },
                "html_report": None
            }
        }
    }


class AgentNoChangeResultRequest(BaseModel):
    """Request schema for recording a NO_CHANGE result from CLI.

    Used when the agent CLI detects the Input State hash matches a previous
    result, indicating no changes to the collection since the last analysis.
    No HMAC signature required — the agent is already authenticated via API key.
    """

    collection_guid: str = Field(
        ...,
        min_length=1,
        description="Collection GUID (col_xxx)"
    )
    tool: str = Field(
        ...,
        min_length=1,
        description="Tool name: photostats, photo_pairing, pipeline_validation"
    )
    input_state_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA-256 hash of Input State (64 char hex string)"
    )
    source_result_guid: str = Field(
        ...,
        pattern=r"^res_[0-9a-hjkmnp-tv-z]{26}$",
        description="GUID of the previous result being referenced (res_xxx)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "collection_guid": "col_01hgw2bbg0000000000000001",
                "tool": "photostats",
                "input_state_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "source_result_guid": "res_01hgw2bbg0000000000000001",
            }
        }
    }


class AgentUploadResultResponse(BaseModel):
    """Response schema for successful offline result upload."""

    job_guid: str = Field(
        ..., description="GUID of the created Job record (job_xxx)"
    )
    result_guid: str = Field(
        ..., description="GUID of the created AnalysisResult (res_xxx)"
    )
    collection_guid: str = Field(
        ..., description="Collection GUID (col_xxx)"
    )
    status: str = Field(
        ..., description="Upload status (uploaded)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_guid": "job_01hgw2bbg0000000000000001",
                "result_guid": "res_01hgw2bbg0000000000000001",
                "collection_guid": "col_01hgw2bbg0000000000000001",
                "status": "uploaded"
            }
        }
    }
