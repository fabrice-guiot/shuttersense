"""
Pydantic schemas for notification API request/response validation.

Provides data validation and serialization for:
- Push subscription management (create, response, status)
- Notification preferences (get, update)
- Notification history (list, detail, unread count)

Issue #114 - PWA with Push Notifications
"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, field_serializer, field_validator

from backend.src.schemas.audit import AuditInfo


# ============================================================================
# Push Subscription Schemas
# ============================================================================


class PushSubscriptionCreate(BaseModel):
    """
    Schema for creating a push subscription.

    Required:
        endpoint: Push service endpoint URL (must be HTTPS)
        p256dh_key: Base64url-encoded ECDH public key
        auth_key: Base64url-encoded auth secret

    Optional:
        device_name: User-friendly device label
    """

    endpoint: str = Field(..., description="Push service endpoint URL (must be HTTPS)")
    p256dh_key: str = Field(..., description="Base64url-encoded ECDH public key")
    auth_key: str = Field(..., description="Base64url-encoded auth secret")
    device_name: Optional[str] = Field(default=None, max_length=100, description="Optional device name")

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint_https(cls, v: str) -> str:
        """Ensure endpoint uses HTTPS."""
        if not v.startswith("https://"):
            raise ValueError("Push subscription endpoint must use HTTPS")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "endpoint": "https://fcm.googleapis.com/fcm/send/abc123...",
                "p256dh_key": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0...",
                "auth_key": "tBHItJI5svbpC7htUH8g...",
                "device_name": "MacBook Pro",
            }
        }
    }


class PushSubscriptionResponse(BaseModel):
    """Response schema for a push subscription."""

    guid: str = Field(..., description="Subscription GUID (sub_xxx)")
    endpoint: str
    device_name: Optional[str] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None
    audit: Optional[AuditInfo] = None

    @field_serializer("created_at", "last_used_at")
    @classmethod
    def serialize_datetime_utc(cls, v: Optional[datetime]) -> Optional[str]:
        """Serialize datetime as ISO 8601 with explicit UTC timezone."""
        return v.isoformat() + "Z" if v else None

    model_config = {"from_attributes": True}


class SubscriptionStatusResponse(BaseModel):
    """Response schema for push subscription status check."""

    notifications_enabled: bool = Field(
        ..., description="Whether the user has the master notification toggle enabled"
    )
    subscriptions: List[PushSubscriptionResponse] = Field(
        default_factory=list, description="Active push subscriptions for this user"
    )


class PushSubscriptionRemove(BaseModel):
    """Schema for removing a push subscription by endpoint."""

    endpoint: str = Field(..., description="The push service endpoint URL to unsubscribe")


# ============================================================================
# Notification Preferences Schemas
# ============================================================================


class NotificationPreferencesResponse(BaseModel):
    """Response schema for notification preferences."""

    enabled: bool = Field(False, description="Master notification toggle")
    job_failures: bool = True
    inflection_points: bool = True
    agent_status: bool = True
    deadline: bool = True
    retry_warning: bool = False
    deadline_days_before: int = Field(3, ge=1, le=30)
    timezone: str = Field("UTC", description="IANA timezone identifier")
    retention_days: int = Field(30, ge=7, le=365, description="Days to keep read notifications")


class NotificationPreferencesUpdate(BaseModel):
    """
    Schema for updating notification preferences.

    All fields are optional — only provided fields are updated.
    """

    enabled: Optional[bool] = None
    job_failures: Optional[bool] = None
    inflection_points: Optional[bool] = None
    agent_status: Optional[bool] = None
    deadline: Optional[bool] = None
    retry_warning: Optional[bool] = None
    deadline_days_before: Optional[int] = Field(default=None, ge=1, le=30)
    timezone: Optional[str] = Field(
        default=None,
        description="IANA timezone identifier (e.g., 'America/New_York')"
    )
    retention_days: Optional[int] = Field(default=None, ge=7, le=365, description="Days to keep read notifications")


# ============================================================================
# Notification History Schemas
# ============================================================================


class NotificationDataResponse(BaseModel):
    """Schema for notification data payload."""

    url: Optional[str] = None
    job_guid: Optional[str] = None
    collection_guid: Optional[str] = None
    result_guid: Optional[str] = None
    event_guid: Optional[str] = None
    agent_guid: Optional[str] = None

    model_config = {"from_attributes": True}


class NotificationResponse(BaseModel):
    """Response schema for a single notification."""

    guid: str = Field(..., description="Notification GUID (ntf_xxx)")
    category: str = Field(..., description="Notification category")
    title: str
    body: str
    data: Optional[NotificationDataResponse] = None
    read_at: Optional[datetime] = None
    created_at: datetime
    audit: Optional[AuditInfo] = None

    @field_serializer("read_at", "created_at")
    @classmethod
    def serialize_datetime_utc(cls, v: Optional[datetime]) -> Optional[str]:
        """Serialize datetime as ISO 8601 with explicit UTC timezone."""
        return v.isoformat() + "Z" if v else None

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """Response schema for paginated notification list."""

    items: List[NotificationResponse]
    total: int = Field(..., ge=0, description="Total notifications matching filter")
    limit: int
    offset: int


class UnreadCountResponse(BaseModel):
    """Response schema for unread notification count."""

    unread_count: int = Field(..., ge=0, description="Number of unread notifications")


class NotificationStatsResponse(BaseModel):
    """Response schema for notification stats (TopHeader KPIs)."""

    total_count: int = Field(..., ge=0, description="Total notifications")
    unread_count: int = Field(..., ge=0, description="Unread notifications")
    this_week_count: int = Field(..., ge=0, description="Notifications in the last 7 days")


class VapidKeyResponse(BaseModel):
    """Response schema for VAPID public key."""

    vapid_public_key: str = Field(..., description="Base64url-encoded VAPID public key")
