"""
Agent local cache module.

Provides Pydantic models and storage for agent-side cached data:
- TestCacheEntry: Cached result of a local path test (24h TTL)
- CollectionCache / CachedCollection: Local snapshot of bound collections (7d TTL)
- TeamConfigCache / CachedPipeline: Team tool configuration from server (24h TTL)
- OfflineResult: Analysis result pending upload to server (no TTL)

All cache data is stored as JSON files in the platform-appropriate data
directory via platformdirs.

Issue #108 - Remove CLI Direct Usage
Tasks: T001, T003
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# ============================================================================
# Constants
# ============================================================================

TEST_CACHE_TTL_HOURS = 24
COLLECTION_CACHE_TTL_DAYS = 7
TEAM_CONFIG_CACHE_TTL_HOURS = 24

VALID_TOOLS = frozenset(["photostats", "photo_pairing", "pipeline_validation"])
VALID_COLLECTION_TYPES = frozenset(["LOCAL", "S3", "GCS", "SMB"])


# ============================================================================
# TestCacheEntry
# ============================================================================


class TestCacheEntry(BaseModel):
    """
    Cached result of a local path test.

    Stored at {data_dir}/test-cache/{path_hash}.json with a 24-hour TTL.
    Created by the ``test`` command. Read by ``collection create`` to
    avoid redundant testing.
    """

    path: str = Field(..., description="Absolute path that was tested")
    path_hash: str = Field(
        ..., description="SHA-256 hash of normalized path (filename key)"
    )
    tested_at: datetime = Field(..., description="When the test was executed")
    expires_at: datetime = Field(
        ..., description="tested_at + 24 hours"
    )
    accessible: bool = Field(..., description="Whether path was accessible")
    file_count: int = Field(..., ge=0, description="Total files found")
    photo_count: int = Field(..., ge=0, description="Files matching photo extensions")
    sidecar_count: int = Field(
        ..., ge=0, description="Files matching metadata extensions"
    )
    tools_tested: List[str] = Field(
        ..., description="Tools that were run (empty if --check-only)"
    )
    issues_found: Optional[Dict[str, Any]] = Field(
        None, description="Summary of issues per tool"
    )
    agent_id: str = Field(..., description="GUID of the agent that ran the test")
    agent_version: str = Field(..., description="Version of the agent binary")

    @field_validator("path")
    @classmethod
    def path_must_be_absolute(cls, v: str) -> str:
        if not v.startswith("/") and not (len(v) >= 3 and v[1] == ":"):
            raise ValueError("path must be absolute")
        return v

    @field_validator("tools_tested")
    @classmethod
    def tools_must_be_valid(cls, v: List[str]) -> List[str]:
        for tool in v:
            if tool not in VALID_TOOLS:
                raise ValueError(
                    f"Invalid tool '{tool}'. Must be one of: {sorted(VALID_TOOLS)}"
                )
        return v

    @model_validator(mode="after")
    def validate_counts_and_expiry(self) -> "TestCacheEntry":
        if self.file_count < self.photo_count + self.sidecar_count:
            raise ValueError(
                "file_count must be >= photo_count + sidecar_count"
            )
        expected_expires = self.tested_at + timedelta(hours=TEST_CACHE_TTL_HOURS)
        if abs((self.expires_at - expected_expires).total_seconds()) > 1:
            raise ValueError(
                "expires_at must be exactly 24 hours after tested_at"
            )
        return self

    def is_valid(self) -> bool:
        """Check if this cache entry has not expired."""
        return datetime.now(timezone.utc) < self.expires_at


# ============================================================================
# CachedCollection (embedded in CollectionCache)
# ============================================================================


class CachedCollection(BaseModel):
    """
    Local snapshot of a single Collection bound to the agent.

    Embedded within CollectionCache.
    """

    guid: str = Field(..., description="Collection GUID (e.g., col_01hgw2bbg...)")
    name: str = Field(..., description="Collection display name")
    type: str = Field(..., description="LOCAL, S3, GCS, or SMB")
    location: str = Field(..., description="Path (LOCAL) or bucket/prefix (remote)")
    bound_agent_guid: Optional[str] = Field(
        None, description="Agent GUID for LOCAL collections"
    )
    connector_guid: Optional[str] = Field(
        None, description="Connector GUID for remote collections"
    )
    connector_name: Optional[str] = Field(None, description="Connector display name")
    is_accessible: Optional[bool] = Field(
        None, description="Last known accessibility status"
    )
    last_analysis_at: Optional[datetime] = Field(
        None, description="When last analysis completed"
    )
    supports_offline: bool = Field(
        ..., description="true only for LOCAL type"
    )

    @field_validator("type")
    @classmethod
    def type_must_be_valid(cls, v: str) -> str:
        if v not in VALID_COLLECTION_TYPES:
            raise ValueError(
                f"Invalid type '{v}'. Must be one of: {sorted(VALID_COLLECTION_TYPES)}"
            )
        return v

    @model_validator(mode="after")
    def validate_type_constraints(self) -> "CachedCollection":
        if self.type == "LOCAL":
            if not self.supports_offline:
                raise ValueError("supports_offline must be true for LOCAL type")
            if not self.bound_agent_guid:
                raise ValueError("LOCAL collections must have bound_agent_guid")
        else:
            if self.supports_offline:
                raise ValueError("supports_offline must be false for non-LOCAL type")
            if not self.connector_guid:
                raise ValueError("Remote collections must have connector_guid")
        return self


# ============================================================================
# CollectionCache
# ============================================================================


class CollectionCache(BaseModel):
    """
    Local snapshot of all Collections bound to the agent.

    Stored at {data_dir}/collection-cache.json with a 7-day TTL.
    Created/updated by ``collection sync`` and ``collection list`` (online mode).
    Read by ``run --offline`` and ``collection list --offline``.
    """

    agent_guid: str = Field(..., description="GUID of this agent")
    synced_at: datetime = Field(
        ..., description="When cache was last refreshed from server"
    )
    expires_at: datetime = Field(..., description="synced_at + 7 days")
    collections: List[CachedCollection] = Field(
        ..., description="All bound collections"
    )

    @model_validator(mode="after")
    def validate_expiry(self) -> "CollectionCache":
        expected_expires = self.synced_at + timedelta(days=COLLECTION_CACHE_TTL_DAYS)
        if abs((self.expires_at - expected_expires).total_seconds()) > 1:
            raise ValueError(
                "expires_at must be exactly 7 days after synced_at"
            )
        return self

    def is_valid(self) -> bool:
        """Check if this cache has not expired."""
        return datetime.now(timezone.utc) < self.expires_at

    def is_expired(self) -> bool:
        """Check if this cache has expired (inverse of is_valid)."""
        return not self.is_valid()


# ============================================================================
# CachedPipeline (embedded in TeamConfigCache)
# ============================================================================


class CachedPipeline(BaseModel):
    """
    Cached pipeline definition from the server.

    Embedded within TeamConfigCache. Mirrors the PipelineData schema
    from the backend agent API.
    """

    guid: str = Field(..., description="Pipeline GUID (pip_xxx)")
    name: str = Field(..., description="Pipeline name")
    version: int = Field(..., description="Pipeline version number")
    nodes: List[Dict[str, Any]] = Field(..., description="Pipeline node definitions")
    edges: List[Dict[str, Any]] = Field(..., description="Pipeline edge connections")


# ============================================================================
# TeamConfigCache
# ============================================================================


class TeamConfigCache(BaseModel):
    """
    Cached team configuration for tool execution.

    Stored at {data_dir}/team-config-cache.json with a 24-hour TTL.
    Created by ``test`` and ``run`` commands when the server is available.
    Read when the server is unavailable for offline tool execution.
    """

    agent_guid: str = Field(..., description="GUID of the agent")
    fetched_at: datetime = Field(..., description="When config was fetched from server")
    expires_at: datetime = Field(..., description="fetched_at + 24 hours")

    # Tool config (matches JobConfigData on server)
    photo_extensions: List[str] = Field(..., description="Recognized photo file extensions")
    metadata_extensions: List[str] = Field(..., description="Metadata file extensions")
    cameras: Dict[str, List[Dict[str, Any]]] = Field(
        default_factory=dict, description="Camera ID to camera info mappings"
    )
    processing_methods: Dict[str, str] = Field(
        default_factory=dict, description="Processing method code to description"
    )
    require_sidecar: List[str] = Field(..., description="Extensions requiring sidecars")

    # Default pipeline
    default_pipeline: Optional[CachedPipeline] = Field(
        None, description="Default pipeline definition (if one exists)"
    )

    @model_validator(mode="after")
    def validate_expiry(self) -> "TeamConfigCache":
        expected_expires = self.fetched_at + timedelta(hours=TEAM_CONFIG_CACHE_TTL_HOURS)
        if abs((self.expires_at - expected_expires).total_seconds()) > 1:
            raise ValueError(
                "expires_at must be exactly 24 hours after fetched_at"
            )
        return self

    def is_valid(self) -> bool:
        """Check if this cache has not expired."""
        return datetime.now(timezone.utc) < self.expires_at

    def is_expired(self) -> bool:
        """Check if this cache has expired (inverse of is_valid)."""
        return not self.is_valid()


# ============================================================================
# OfflineResult
# ============================================================================


class OfflineResult(BaseModel):
    """
    Analysis result produced during offline execution, pending upload.

    Stored at {data_dir}/results/{result_id}.json with no TTL (persists
    until synced or manually deleted).
    Created by ``run --offline``. Uploaded by ``sync`` command.
    """

    result_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Locally generated UUID",
    )
    collection_guid: str = Field(
        ..., description="GUID of the collection analyzed"
    )
    collection_name: str = Field(
        ..., description="Display name (for sync preview)"
    )
    tool: str = Field(
        ..., description="Tool used: photostats, photo_pairing, pipeline_validation"
    )
    executed_at: datetime = Field(..., description="When the analysis ran")
    agent_guid: str = Field(..., description="GUID of the executing agent")
    agent_version: str = Field(..., description="Agent binary version")
    analysis_data: Dict[str, Any] = Field(
        ..., description="Full analysis output (tool-specific JSON)"
    )
    html_report_path: Optional[str] = Field(
        None, description="Path to locally saved HTML report"
    )
    synced: bool = Field(
        False, description="Whether this result has been uploaded"
    )

    @field_validator("tool")
    @classmethod
    def tool_must_be_valid(cls, v: str) -> str:
        if v not in VALID_TOOLS:
            raise ValueError(
                f"Invalid tool '{v}'. Must be one of: {sorted(VALID_TOOLS)}"
            )
        return v


__all__ = [
    "TEST_CACHE_TTL_HOURS",
    "COLLECTION_CACHE_TTL_DAYS",
    "TEAM_CONFIG_CACHE_TTL_HOURS",
    "VALID_TOOLS",
    "VALID_COLLECTION_TYPES",
    "TestCacheEntry",
    "CachedCollection",
    "CollectionCache",
    "CachedPipeline",
    "TeamConfigCache",
    "OfflineResult",
]
