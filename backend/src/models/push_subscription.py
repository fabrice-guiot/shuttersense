"""
PushSubscription model for Web Push notification subscriptions.

Stores the push service endpoint and encryption keys needed to deliver
push notifications to a specific user's device/browser.

Each subscription is associated with a user and their team, supporting
multi-device notification delivery with tenant isolation.

Issue #114 - PWA with Push Notifications
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin, AuditMixin


class PushSubscription(Base, GuidMixin, AuditMixin):
    """
    Web Push subscription for a specific user on a specific device/browser.

    Attributes:
        endpoint: Push service URL (unique per subscription)
        p256dh_key: ECDH public key for payload encryption (Base64url)
        auth_key: Auth secret for message authentication (Base64url)
        device_name: Optional user-friendly label (e.g., "MacBook Pro")
        last_used_at: Timestamp of last successful push delivery
        expires_at: Subscription expiration reported by push service

    Lifecycle:
        Created when user enables notifications on a device.
        Removed when user disables notifications, subscription expires,
        or push service returns 410 Gone.

    Relationships:
        user: Owning User (many-to-one)
        team: Owning Team for tenant isolation (many-to-one)
    """

    __tablename__ = "push_subscriptions"
    GUID_PREFIX = "sub"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Tenant isolation
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)

    # Owning user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Push subscription data
    endpoint = Column(String(1024), nullable=False, unique=True)
    p256dh_key = Column(String(255), nullable=False)
    auth_key = Column(String(255), nullable=False)

    # Optional device label
    device_name = Column(String(100), nullable=True)

    # Tracking
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="push_subscriptions")
    team = relationship("Team")
