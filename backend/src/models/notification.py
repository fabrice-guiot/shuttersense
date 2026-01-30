"""
Notification model for in-app notification history.

Stores notification events sent to users, independent of push delivery status.
Notifications are created when trigger events occur (job failures, inflection
points, agent status changes, deadline reminders, retry warnings) and serve
as the source of truth for the notification bell panel in the UI.

Issue #114 - PWA with Push Notifications
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from backend.src.models import Base
from backend.src.models.mixins import GuidMixin


class Notification(Base, GuidMixin):
    """
    Notification event sent to a user.

    Attributes:
        category: Notification type (job_failure, inflection_point,
                  agent_status, deadline, retry_warning)
        title: Short notification title (max 200 chars)
        body: Notification body text (max 500 chars)
        data: JSONB with navigation URL and entity GUIDs
        read_at: Timestamp when user viewed the notification (null = unread)

    Lifecycle:
        Created when a notification event is triggered (regardless of push
        delivery success). read_at set when user views/clicks. Auto-deleted
        when older than 30 days.

    Relationships:
        user: Recipient User (many-to-one)
        team: Owning Team for tenant isolation (many-to-one)
    """

    __tablename__ = "notifications"
    GUID_PREFIX = "ntf"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Tenant isolation
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)

    # Recipient user
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Notification content
    category = Column(String(30), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(String(500), nullable=False)
    data = Column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)

    # Read tracking
    read_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="notifications")
    team = relationship("Team")

    # Partial index for efficient unread count queries
    __table_args__ = (
        Index(
            "ix_notifications_user_unread",
            "user_id",
            postgresql_where=(read_at.is_(None)),
        ),
    )
