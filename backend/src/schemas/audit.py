"""
Audit trail schemas for API response serialization.

Provides AuditUserSummary and AuditInfo Pydantic models that are embedded
in all entity API responses to expose user attribution data.

Issue #120: Audit Trail Visibility Enhancement
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AuditUserSummary(BaseModel):
    """
    Minimal user representation for audit attribution display.

    Contains only the fields needed to identify and display the acting user
    in audit trail UI components (popover, section).

    Attributes:
        guid: User GUID (usr_xxx format) — never the internal numeric ID.
        display_name: Human-readable name (may be null for system users).
        email: User email address.
    """

    guid: str = Field(..., description="User GUID (usr_xxx)")
    display_name: Optional[str] = Field(
        default=None, description="User display name"
    )
    email: str = Field(..., description="User email")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "guid": "usr_01hgw2bbg0000000000000001",
                "display_name": "John Doe",
                "email": "john@example.com",
            }
        },
    }


class AuditInfo(BaseModel):
    """
    Structured audit trail included in all entity API responses.

    Combines creation and modification timestamps with their respective
    user summaries. Null users indicate historical records (created before
    audit tracking) or deleted users (FK SET NULL).

    Attributes:
        created_at: Record creation timestamp (always present from entity).
        created_by: User who created the record (null for historical data).
        updated_at: Last modification timestamp (always present from entity).
        updated_by: User who last modified the record (null for historical data).
    """

    created_at: datetime = Field(..., description="Creation timestamp")
    created_by: Optional[AuditUserSummary] = Field(
        default=None, description="User who created the record"
    )
    updated_at: datetime = Field(..., description="Last modification timestamp")
    updated_by: Optional[AuditUserSummary] = Field(
        default=None, description="User who last modified the record"
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "created_at": "2026-01-15T15:45:00Z",
                "created_by": {
                    "guid": "usr_01hgw2bbg0000000000000001",
                    "display_name": "John Doe",
                    "email": "john@example.com",
                },
                "updated_at": "2026-01-20T09:12:00Z",
                "updated_by": {
                    "guid": "usr_01hgw2bbg0000000000000002",
                    "display_name": "Jane Smith",
                    "email": "jane@example.com",
                },
            }
        },
    }
