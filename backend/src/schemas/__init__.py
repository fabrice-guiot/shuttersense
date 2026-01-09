"""
Pydantic schemas for API request/response validation.

This module exports all schema classes for use in API endpoints.
"""

from backend.src.schemas.collection import (
    S3Credentials,
    GCSCredentials,
    SMBCredentials,
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    CollectionTestResponse,
    CollectionRefreshResponse,
    CollectionStatsResponse,
)
from backend.src.schemas.tools import (
    ToolType,
    JobStatus,
    ToolRunRequest,
    ProgressData,
    JobResponse,
    QueueStatusResponse,
    ConflictResponse,
)
from backend.src.schemas.results import (
    SortField,
    SortOrder,
    ResultsQueryParams,
    AnalysisResultSummary,
    ResultListResponse,
    PhotoStatsResults,
    PhotoPairingResults,
    PipelineValidationResults,
    AnalysisResultResponse,
    ResultStatsResponse,
    DeleteResponse,
)
from backend.src.schemas.config import (
    ConfigCategory,
    ConfigSourceType,
    ImportSessionStatus,
    ConfigItemCreate,
    ConfigItemUpdate,
    ConflictResolutionRequest,
    ConfigItemResponse,
    CategoryConfigResponse,
    ConfigurationResponse,
    ConfigConflict,
    ImportSessionResponse,
    ImportResultResponse,
    ConfigStatsResponse,
)

__all__ = [
    # Collection schemas
    "S3Credentials",
    "GCSCredentials",
    "SMBCredentials",
    "CollectionCreate",
    "CollectionUpdate",
    "CollectionResponse",
    "CollectionTestResponse",
    "CollectionRefreshResponse",
    "CollectionStatsResponse",
    # Tool schemas
    "ToolType",
    "JobStatus",
    "ToolRunRequest",
    "ProgressData",
    "JobResponse",
    "QueueStatusResponse",
    "ConflictResponse",
    # Result schemas
    "SortField",
    "SortOrder",
    "ResultsQueryParams",
    "AnalysisResultSummary",
    "ResultListResponse",
    "PhotoStatsResults",
    "PhotoPairingResults",
    "PipelineValidationResults",
    "AnalysisResultResponse",
    "ResultStatsResponse",
    "DeleteResponse",
    # Config schemas
    "ConfigCategory",
    "ConfigSourceType",
    "ImportSessionStatus",
    "ConfigItemCreate",
    "ConfigItemUpdate",
    "ConflictResolutionRequest",
    "ConfigItemResponse",
    "CategoryConfigResponse",
    "ConfigurationResponse",
    "ConfigConflict",
    "ImportSessionResponse",
    "ImportResultResponse",
    "ConfigStatsResponse",
]
