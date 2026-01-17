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
from backend.src.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryReorderRequest,
    CategoryResponse,
    CategoryListResponse,
    CategoryStatsResponse,
)
from backend.src.schemas.user import (
    InviteUserRequest,
    TeamInfo,
    UserResponse,
    UserListResponse,
    UserStatsResponse,
    user_to_response,
)
from backend.src.schemas.team import (
    CreateTeamRequest,
    TeamResponse,
    TeamWithAdminResponse,
    TeamListResponse,
    TeamStatsResponse,
    team_to_response,
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
    # Category schemas (Calendar Events)
    "CategoryCreate",
    "CategoryUpdate",
    "CategoryReorderRequest",
    "CategoryResponse",
    "CategoryListResponse",
    "CategoryStatsResponse",
    # User schemas (Issue #73)
    "InviteUserRequest",
    "TeamInfo",
    "UserResponse",
    "UserListResponse",
    "UserStatsResponse",
    "user_to_response",
    # Team schemas (Issue #73)
    "CreateTeamRequest",
    "TeamResponse",
    "TeamWithAdminResponse",
    "TeamListResponse",
    "TeamStatsResponse",
    "team_to_response",
]
