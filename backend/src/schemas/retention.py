"""
Pydantic schemas for retention configuration API.

Issue #92: Storage Optimization for Analysis Results
Provides validation and serialization for team-level retention settings.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field


# Valid retention period options (days, 0 = unlimited)
RetentionDays = Literal[0, 1, 2, 5, 7, 14, 30, 90, 180, 365]

# Valid preserve count options
PreserveCount = Literal[1, 2, 3, 5, 10]

# Default values for retention settings
DEFAULT_JOB_COMPLETED_DAYS = 2
DEFAULT_JOB_FAILED_DAYS = 7
DEFAULT_RESULT_COMPLETED_DAYS = 0  # Unlimited by default
DEFAULT_PRESERVE_PER_COLLECTION = 1


class RetentionSettingsResponse(BaseModel):
    """
    Current retention settings for a team.

    Returned by GET /api/config/retention endpoint.
    """
    job_completed_days: int = Field(
        ...,
        description="Days to retain completed jobs (0 = unlimited)"
    )
    job_failed_days: int = Field(
        ...,
        description="Days to retain failed jobs (0 = unlimited)"
    )
    result_completed_days: int = Field(
        ...,
        description="Days to retain completed results (0 = unlimited)"
    )
    preserve_per_collection: int = Field(
        ...,
        description="Minimum results to keep per (collection, tool) combination"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_completed_days": 2,
                "job_failed_days": 7,
                "result_completed_days": 0,
                "preserve_per_collection": 1
            }
        }
    }


class RetentionSettingsUpdate(BaseModel):
    """
    Update request for retention settings.

    All fields are optional; only provided fields are updated.
    Used by PUT /api/config/retention endpoint.
    """
    job_completed_days: Optional[RetentionDays] = Field(
        None,
        description="Days to retain completed jobs (0 = unlimited)"
    )
    job_failed_days: Optional[RetentionDays] = Field(
        None,
        description="Days to retain failed jobs (0 = unlimited)"
    )
    result_completed_days: Optional[RetentionDays] = Field(
        None,
        description="Days to retain completed results (0 = unlimited)"
    )
    preserve_per_collection: Optional[PreserveCount] = Field(
        None,
        description="Minimum results to keep per (collection, tool) combination"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "job_completed_days": 7,
                "preserve_per_collection": 2
            }
        }
    }


# List of valid retention day values for validation
VALID_RETENTION_DAYS = [0, 1, 2, 5, 7, 14, 30, 90, 180, 365]

# List of valid preserve count values for validation
VALID_PRESERVE_COUNTS = [1, 2, 3, 5, 10]
