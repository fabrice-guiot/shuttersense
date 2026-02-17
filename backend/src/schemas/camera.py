"""
Pydantic schemas for Camera API request/response validation.

Provides data validation and serialization for:
- Camera CRUD operations
- Camera discovery (agent-facing)
- Camera statistics for KPIs
"""

from datetime import datetime
from typing import Literal, Optional, List, Dict, Any

from pydantic import BaseModel, Field

from backend.src.schemas.audit import AuditInfo


# ============================================================================
# Response Schemas
# ============================================================================

class CameraResponse(BaseModel):
    """Full camera details for API responses."""
    guid: str = Field(..., description="External identifier (cam_xxx)")
    camera_id: str = Field(..., description="Short alphanumeric ID from filenames")
    status: Literal["temporary", "confirmed"] = Field(..., description="Camera status: temporary or confirmed")
    display_name: Optional[str] = Field(None, description="User-assigned friendly name")
    make: Optional[str] = Field(None, description="Camera manufacturer")
    model: Optional[str] = Field(None, description="Camera model name")
    serial_number: Optional[str] = Field(None, description="Camera serial number")
    notes: Optional[str] = Field(None, description="Free-form notes")
    metadata_json: Optional[Dict[str, Any]] = Field(None, description="Custom metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    audit: Optional[AuditInfo] = None

    model_config = {
        "from_attributes": True,
    }


class CameraListResponse(BaseModel):
    """Paginated list of cameras."""
    items: List[CameraResponse] = Field(..., description="Camera records")
    total: int = Field(..., ge=0, description="Total matching records")
    limit: int = Field(..., ge=1, description="Page size")
    offset: int = Field(..., ge=0, description="Page offset")


# ============================================================================
# Request Schemas
# ============================================================================

class CameraUpdateRequest(BaseModel):
    """Request to update camera details."""
    status: Optional[Literal["temporary", "confirmed"]] = Field(None, description="Camera status: temporary or confirmed")
    display_name: Optional[str] = Field(None, max_length=100, description="Friendly name")
    make: Optional[str] = Field(None, max_length=100, description="Camera manufacturer")
    model: Optional[str] = Field(None, max_length=100, description="Camera model name")
    serial_number: Optional[str] = Field(None, max_length=100, description="Serial number")
    notes: Optional[str] = Field(None, max_length=1000, description="Free-form notes")


# ============================================================================
# Statistics Schema
# ============================================================================

class CameraStatsResponse(BaseModel):
    """Camera statistics for KPIs."""
    total_cameras: int = Field(0, ge=0, description="Total camera count")
    confirmed_count: int = Field(0, ge=0, description="Confirmed cameras")
    temporary_count: int = Field(0, ge=0, description="Temporary cameras")


# ============================================================================
# Discovery Schemas (Agent-facing)
# ============================================================================

class CameraDiscoverRequest(BaseModel):
    """Request to discover cameras during analysis."""
    camera_ids: List[str] = Field(
        ...,
        max_length=50,
        description="Unique camera IDs discovered during analysis"
    )


class CameraDiscoverItem(BaseModel):
    """Minimal camera info returned from discovery."""
    guid: str = Field(..., description="External identifier (cam_xxx)")
    camera_id: str = Field(..., description="Short alphanumeric ID")
    status: Literal["temporary", "confirmed"] = Field(..., description="Camera status: temporary or confirmed")
    display_name: Optional[str] = Field(None, description="Display name for reports")
    audit: Optional[AuditInfo] = None

    model_config = {
        "from_attributes": True,
    }


class CameraDiscoverResponse(BaseModel):
    """Response from camera discovery endpoint."""
    cameras: List[CameraDiscoverItem] = Field(..., description="Discovered camera records")


# ============================================================================
# Query Parameter Schemas
# ============================================================================

class CameraListQueryParams(BaseModel):
    """Query parameters for listing cameras."""
    limit: int = Field(50, ge=1, le=200, description="Page size")
    offset: int = Field(0, ge=0, description="Page offset")
    status: Optional[Literal["temporary", "confirmed"]] = Field(None, description="Filter by status: temporary or confirmed")
    search: Optional[str] = Field(None, description="Search by camera_id, display_name, make, or model")


# ============================================================================
# Delete Response
# ============================================================================

class CameraDeleteResponse(BaseModel):
    """Response after deleting a camera."""
    message: str = Field(..., description="Confirmation message")
    deleted_guid: str = Field(..., description="GUID of deleted camera (cam_xxx)")
