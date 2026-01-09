"""
Pydantic schemas for pipelines API request/response validation.

Provides data validation and serialization for:
- Pipeline CRUD operations
- Pipeline validation
- Filename preview
- Version history
- Statistics for KPIs

Design:
- Uses JSONB for nodes/edges storage
- Supports validation error reporting
- Version history tracking
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Pipeline node types."""
    CAPTURE = "capture"
    FILE = "file"
    PROCESS = "process"
    PAIRING = "pairing"
    BRANCHING = "branching"
    TERMINATION = "termination"


class ValidationErrorType(str, Enum):
    """Types of validation errors."""
    # Note: Cycles are allowed in pipelines - the CLI pipeline_validation tool
    # handles loop execution limits to prevent infinite loops at runtime.
    ORPHANED_NODE = "orphaned_node"
    INVALID_REFERENCE = "invalid_reference"
    MISSING_REQUIRED_NODE = "missing_required_node"
    INVALID_PROPERTY = "invalid_property"


# ============================================================================
# Node and Edge Schemas
# ============================================================================

class PipelineNode(BaseModel):
    """
    Pipeline node definition.

    Nodes represent processing steps in the pipeline graph.
    """
    id: str = Field(..., min_length=1, max_length=100, description="Unique node identifier")
    type: NodeType = Field(..., description="Node type")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Node properties")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "file_raw",
                "type": "file",
                "properties": {"extension": ".dng", "optional": False}
            }
        }
    }


class PipelineEdge(BaseModel):
    """
    Pipeline edge definition.

    Edges connect nodes in the pipeline graph.
    """
    from_node: str = Field(..., alias="from", min_length=1, description="Source node ID")
    to_node: str = Field(..., alias="to", min_length=1, description="Target node ID")

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "from": "capture_1",
                "to": "file_raw"
            }
        }
    }


class ValidationError(BaseModel):
    """
    Validation error detail.

    Provides context for pipeline validation errors.
    """
    type: ValidationErrorType = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    node_id: Optional[str] = Field(None, description="Node ID where error occurred")
    suggestion: Optional[str] = Field(None, description="Suggested fix")

    model_config = {
        "json_schema_extra": {
            "example": {
                "type": "cycle_detected",
                "message": "Cycle detected between nodes: a -> b -> c -> a",
                "node_id": "a",
                "suggestion": "Remove one of the edges to break the cycle"
            }
        }
    }


# ============================================================================
# Request Schemas
# ============================================================================

class PipelineCreateRequest(BaseModel):
    """
    Request to create a new pipeline.
    """
    name: str = Field(..., min_length=1, max_length=255, description="Pipeline name")
    description: Optional[str] = Field(None, description="Pipeline description")
    nodes: List[PipelineNode] = Field(..., min_length=1, description="Node definitions")
    edges: List[PipelineEdge] = Field(default_factory=list, description="Edge connections")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Standard RAW Workflow",
                "description": "RAW capture to processed TIFF export",
                "nodes": [
                    {"id": "capture", "type": "capture", "properties": {"sample_filename": "AB3D0001", "filename_regex": "([A-Z0-9]{4})([0-9]{4})", "camera_id_group": "1"}},
                    {"id": "raw", "type": "file", "properties": {"extension": ".dng"}}
                ],
                "edges": [
                    {"from": "capture", "to": "raw"}
                ]
            }
        }
    }


class PipelineUpdateRequest(BaseModel):
    """
    Request to update an existing pipeline.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Pipeline name")
    description: Optional[str] = Field(None, description="Pipeline description")
    nodes: Optional[List[PipelineNode]] = Field(None, min_length=1, description="Node definitions")
    edges: Optional[List[PipelineEdge]] = Field(None, description="Edge connections")
    change_summary: Optional[str] = Field(None, max_length=500, description="Summary of changes")

    model_config = {
        "json_schema_extra": {
            "example": {
                "description": "Updated workflow with HDR processing",
                "nodes": [
                    {"id": "capture", "type": "capture", "properties": {"sample_filename": "AB3D0001", "filename_regex": "([A-Z0-9]{4})([0-9]{4})", "camera_id_group": "1"}},
                    {"id": "raw", "type": "file", "properties": {"extension": ".dng"}},
                    {"id": "hdr", "type": "process", "properties": {"method_ids": ["HDR"]}}
                ],
                "edges": [
                    {"from": "capture", "to": "raw"},
                    {"from": "raw", "to": "hdr"}
                ],
                "change_summary": "Added HDR processing step"
            }
        }
    }


class FilenamePreviewRequest(BaseModel):
    """
    Request to preview expected filenames.

    No parameters needed - the preview uses sample_filename from the
    pipeline's Capture node configuration.
    """
    pass


# ============================================================================
# Response Schemas
# ============================================================================

class PipelineSummary(BaseModel):
    """
    Summary of a pipeline for list views.

    Contains essential information without full node/edge details.
    """
    id: int = Field(..., description="Pipeline ID")
    name: str = Field(..., description="Pipeline name")
    description: Optional[str] = Field(None, description="Pipeline description")
    version: int = Field(..., description="Current version")
    is_active: bool = Field(..., description="Whether pipeline is active (valid and ready for use)")
    is_default: bool = Field(..., description="Whether this is the default pipeline for tool execution")
    is_valid: bool = Field(..., description="Whether structure is valid")
    node_count: int = Field(..., description="Number of nodes")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "name": "Standard RAW Workflow",
                "description": "RAW capture to processed TIFF export",
                "version": 3,
                "is_active": True,
                "is_default": True,
                "is_valid": True,
                "node_count": 6,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T14:45:00Z"
            }
        }
    }


class PipelineResponse(BaseModel):
    """
    Full pipeline details.

    Contains all information including nodes and edges.
    """
    id: int = Field(..., description="Pipeline ID")
    name: str = Field(..., description="Pipeline name")
    description: Optional[str] = Field(None, description="Pipeline description")
    nodes: List[PipelineNode] = Field(..., description="Node definitions")
    edges: List[PipelineEdge] = Field(..., description="Edge connections")
    version: int = Field(..., description="Current version")
    is_active: bool = Field(..., description="Whether pipeline is active (valid and ready for use)")
    is_default: bool = Field(..., description="Whether this is the default pipeline for tool execution")
    is_valid: bool = Field(..., description="Whether structure is valid")
    validation_errors: Optional[List[str]] = Field(None, description="Validation errors if invalid")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "name": "Standard RAW Workflow",
                "description": "RAW capture to processed TIFF export",
                "nodes": [
                    {"id": "capture", "type": "capture", "properties": {"sample_filename": "AB3D0001", "filename_regex": "([A-Z0-9]{4})([0-9]{4})", "camera_id_group": "1"}},
                    {"id": "raw", "type": "file", "properties": {"extension": ".dng"}}
                ],
                "edges": [
                    {"from": "capture", "to": "raw"}
                ],
                "version": 1,
                "is_active": False,
                "is_default": False,
                "is_valid": True,
                "validation_errors": None,
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z"
            }
        }
    }


class PipelineListResponse(BaseModel):
    """
    List of pipeline summaries.
    """
    items: List[PipelineSummary] = Field(..., description="Pipeline summaries")

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": []
            }
        }
    }


class ValidationResult(BaseModel):
    """
    Result of pipeline validation.
    """
    is_valid: bool = Field(..., description="Whether pipeline is valid")
    errors: List[ValidationError] = Field(default_factory=list, description="Validation errors")

    model_config = {
        "json_schema_extra": {
            "example": {
                "is_valid": True,
                "errors": []
            }
        }
    }


class ExpectedFile(BaseModel):
    """
    Expected file from filename preview.
    """
    path: str = Field(..., description="Node path that leads to this file")
    filename: str = Field(..., description="Expected filename")
    optional: bool = Field(..., description="Whether file is optional")


class FilenamePreviewResponse(BaseModel):
    """
    Result of filename preview.
    """
    base_filename: str = Field(..., description="Base filename used")
    expected_files: List[ExpectedFile] = Field(..., description="Expected files from pipeline")

    model_config = {
        "json_schema_extra": {
            "example": {
                "base_filename": "AB3D0001",
                "expected_files": [
                    {"path": "capture -> raw", "filename": "AB3D0001.dng", "optional": False},
                    {"path": "capture -> raw -> xmp", "filename": "AB3D0001.xmp", "optional": False}
                ]
            }
        }
    }


class PipelineHistoryEntry(BaseModel):
    """
    Pipeline version history entry.
    """
    id: int = Field(..., description="History entry ID")
    version: int = Field(..., description="Version number")
    change_summary: Optional[str] = Field(None, description="Summary of changes")
    changed_by: Optional[str] = Field(None, description="Who made the change")
    created_at: datetime = Field(..., description="When version was created")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "version": 2,
                "change_summary": "Added HDR processing step",
                "changed_by": None,
                "created_at": "2024-01-15T14:45:00Z"
            }
        }
    }


class PipelineStatsResponse(BaseModel):
    """
    Pipeline statistics for KPIs.
    """
    total_pipelines: int = Field(0, ge=0, description="Total pipeline count")
    valid_pipelines: int = Field(0, ge=0, description="Valid pipeline count")
    active_pipeline_count: int = Field(0, ge=0, description="Number of active pipelines")
    default_pipeline_id: Optional[int] = Field(None, description="ID of default pipeline")
    default_pipeline_name: Optional[str] = Field(None, description="Name of default pipeline")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_pipelines": 5,
                "valid_pipelines": 4,
                "active_pipeline_count": 3,
                "default_pipeline_id": 1,
                "default_pipeline_name": "Standard RAW Workflow"
            }
        }
    }


class DeleteResponse(BaseModel):
    """
    Response after deleting a pipeline.
    """
    message: str = Field(..., description="Confirmation message")
    deleted_id: int = Field(..., description="ID of deleted pipeline")

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Pipeline deleted successfully",
                "deleted_id": 1
            }
        }
    }


# ============================================================================
# Query Parameter Schemas
# ============================================================================

class PipelineListQueryParams(BaseModel):
    """
    Query parameters for listing pipelines.
    """
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    is_default: Optional[bool] = Field(None, description="Filter by default status")
    is_valid: Optional[bool] = Field(None, description="Filter by validation status")


# ============================================================================
# Error Response Schemas
# ============================================================================

class ValidationErrorResponse(BaseModel):
    """
    Error response for validation failures.
    """
    detail: str = Field(..., description="Error message")
    validation_errors: List[ValidationError] = Field(default_factory=list, description="Validation errors")

    model_config = {
        "json_schema_extra": {
            "example": {
                "detail": "Pipeline validation failed",
                "validation_errors": [
                    {
                        "type": "cycle_detected",
                        "message": "Cycle detected between nodes: a -> b -> a",
                        "node_id": "a",
                        "suggestion": "Remove one of the edges"
                    }
                ]
            }
        }
    }
