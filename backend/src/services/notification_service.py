"""
Notification service for creating, delivering, and managing notifications.

Provides business logic for:
- Creating notification records in the database
- Delivering push notifications via Web Push protocol
- Managing user notification preferences
- Checking category preferences before sending
- Orchestrating the full notification flow (prefs → create → push)

Issue #114 - PWA with Push Notifications
"""

import json
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from backend.src.models.notification import Notification
from backend.src.models.push_subscription import PushSubscription
from backend.src.models.user import User
from backend.src.services.exceptions import NotFoundError, ValidationError
from backend.src.services.guid import GuidService
from backend.src.utils.logging_config import get_logger


logger = get_logger("services")


# Default notification preferences (pre-opt-in)
DEFAULT_PREFERENCES = {
    "enabled": False,
    "job_failures": True,
    "inflection_points": True,
    "agent_status": True,
    "deadline": True,
    "retry_warning": False,
    "deadline_days_before": 3,
    "timezone": "UTC",
}

# Categories that map to preference keys
CATEGORY_PREFERENCE_KEYS = {
    "job_failure": "job_failures",
    "inflection_point": "inflection_points",
    "agent_status": "agent_status",
    "deadline": "deadline",
    "retry_warning": "retry_warning",
}


class NotificationService:
    """
    Service for notification creation, delivery, and preference management.

    Orchestrates the full notification lifecycle:
    1. Check user preferences for the category
    2. Create notification record in database
    3. Deliver push notification to all user subscriptions (async)
    """

    def __init__(self, db: Session, vapid_private_key: str = "", vapid_claims: Optional[Dict[str, str]] = None):
        """
        Initialize notification service.

        Args:
            db: SQLAlchemy database session
            vapid_private_key: VAPID private key for push authentication
            vapid_claims: VAPID claims dict (e.g., {"sub": "mailto:..."})
        """
        self.db = db
        self.vapid_private_key = vapid_private_key
        self.vapid_claims = vapid_claims or {}

    # ========================================================================
    # Notification CRUD
    # ========================================================================

    def create_notification(
        self,
        team_id: int,
        user_id: int,
        category: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        """
        Create a notification record in the database.

        Args:
            team_id: Team ID for tenant isolation
            user_id: Recipient user's internal ID
            category: Notification category (job_failure, inflection_point, etc.)
            title: Notification title (max 200 chars)
            body: Notification body (max 500 chars)
            data: Optional JSONB data (navigation URL, entity GUIDs)

        Returns:
            Created Notification instance
        """
        notification = Notification(
            team_id=team_id,
            user_id=user_id,
            category=category,
            title=title[:200],
            body=body[:500],
            data=data,
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        logger.info(
            "Created notification",
            extra={
                "guid": notification.guid,
                "category": category,
                "user_id": user_id,
            },
        )
        return notification

    def get_notification_by_guid(
        self, guid: str, team_id: int
    ) -> Notification:
        """
        Get a notification by GUID with team isolation.

        Args:
            guid: Notification GUID (ntf_xxx)
            team_id: Team ID for tenant isolation

        Returns:
            Notification instance

        Raises:
            NotFoundError: If not found or belongs to different team
        """
        if not GuidService.validate_guid(guid, "ntf"):
            raise NotFoundError("Notification", guid)

        try:
            uuid_value = GuidService.parse_guid(guid, "ntf")
        except ValueError:
            raise NotFoundError("Notification", guid)

        notification = (
            self.db.query(Notification)
            .filter(
                Notification.uuid == uuid_value,
                Notification.team_id == team_id,
            )
            .first()
        )

        if not notification:
            raise NotFoundError("Notification", guid)

        return notification

    def list_notifications(
        self,
        user_id: int,
        team_id: int,
        limit: int = 20,
        offset: int = 0,
        category: Optional[str] = None,
        unread_only: bool = False,
        search: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        read_only: bool = False,
    ) -> tuple:
        """
        List notifications for a user with pagination and filtering.

        Args:
            user_id: User's internal ID
            team_id: Team ID for tenant isolation
            limit: Maximum results (1-50)
            offset: Number to skip
            category: Optional category filter
            unread_only: If True, only return unread notifications
            search: Optional text search on title and body (ILIKE)
            from_date: Optional ISO date string, filter created_at >=
            to_date: Optional ISO date string, filter created_at <= end of day
            read_only: If True, only return read notifications

        Returns:
            Tuple of (notifications list, total count)
        """
        query = self.db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.team_id == team_id,
        )

        if category:
            query = query.filter(Notification.category == category)

        if unread_only:
            query = query.filter(Notification.read_at.is_(None))

        if read_only:
            query = query.filter(Notification.read_at.isnot(None))

        if search:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Notification.title.ilike(pattern),
                    Notification.body.ilike(pattern),
                )
            )

        if from_date:
            try:
                parsed = date.fromisoformat(from_date)
                query = query.filter(
                    Notification.created_at >= datetime(parsed.year, parsed.month, parsed.day)
                )
            except ValueError:
                pass  # Ignore invalid date

        if to_date:
            try:
                parsed = date.fromisoformat(to_date)
                end_of_day = datetime(parsed.year, parsed.month, parsed.day, 23, 59, 59)
                query = query.filter(Notification.created_at <= end_of_day)
            except ValueError:
                pass  # Ignore invalid date

        total = query.count()

        notifications = (
            query.order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return notifications, total

    def get_unread_count(self, user_id: int, team_id: int) -> int:
        """
        Get the count of unread notifications for a user.

        Uses the partial index on (user_id WHERE read_at IS NULL).

        Args:
            user_id: User's internal ID
            team_id: Team ID for tenant isolation

        Returns:
            Number of unread notifications
        """
        return (
            self.db.query(func.count(Notification.id))
            .filter(
                Notification.user_id == user_id,
                Notification.team_id == team_id,
                Notification.read_at.is_(None),
            )
            .scalar()
        )

    def get_stats(self, user_id: int, team_id: int) -> dict:
        """
        Get notification stats for the TopHeader KPIs.

        Args:
            user_id: User's internal ID
            team_id: Team ID for tenant isolation

        Returns:
            Dict with total_count, unread_count, this_week_count
        """
        base_filter = [
            Notification.user_id == user_id,
            Notification.team_id == team_id,
        ]

        total_count = (
            self.db.query(func.count(Notification.id))
            .filter(*base_filter)
            .scalar()
        )

        unread_count = (
            self.db.query(func.count(Notification.id))
            .filter(*base_filter, Notification.read_at.is_(None))
            .scalar()
        )

        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        this_week_count = (
            self.db.query(func.count(Notification.id))
            .filter(*base_filter, Notification.created_at >= seven_days_ago)
            .scalar()
        )

        return {
            "total_count": total_count,
            "unread_count": unread_count,
            "this_week_count": this_week_count,
        }

    def mark_as_read(self, guid: str, team_id: int) -> Notification:
        """
        Mark a notification as read (idempotent).

        Args:
            guid: Notification GUID (ntf_xxx)
            team_id: Team ID for tenant isolation

        Returns:
            Updated Notification instance

        Raises:
            NotFoundError: If not found or belongs to different team
        """
        notification = self.get_notification_by_guid(guid, team_id)

        if notification.read_at is None:
            notification.read_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(notification)

        return notification

    def delete_old_notifications(self, days: int = 30) -> int:
        """
        Delete notifications older than the specified number of days.

        Args:
            days: Age threshold in days (default 30)

        Returns:
            Number of notifications deleted
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)
        count = (
            self.db.query(Notification)
            .filter(Notification.created_at < cutoff)
            .delete(synchronize_session=False)
        )
        self.db.commit()

        if count > 0:
            logger.info(f"Deleted {count} old notifications (>{days} days)")

        return count

    # ========================================================================
    # Push Delivery
    # ========================================================================

    def deliver_push(self, user_id: int, team_id: int, payload: Dict[str, Any]) -> int:
        """
        Send a push notification to all of a user's subscriptions.

        Args:
            user_id: Recipient user's internal ID
            team_id: Team ID for tenant isolation
            payload: Push notification payload (title, body, data, etc.)

        Returns:
            Number of successful deliveries
        """
        subscriptions = (
            self.db.query(PushSubscription)
            .filter(
                PushSubscription.user_id == user_id,
                PushSubscription.team_id == team_id,
            )
            .all()
        )

        if not subscriptions:
            return 0

        success_count = 0
        payload_json = json.dumps(payload)

        for sub in subscriptions:
            try:
                self._send_push(sub, payload_json)
                sub.last_used_at = datetime.utcnow()
                success_count += 1
                logger.debug(
                    "Push delivered",
                    extra={"subscription_guid": sub.guid, "user_id": user_id},
                )
            except PushGoneError:
                # 410 Gone — subscription is invalid, remove it
                logger.info(
                    "Removing invalid subscription (410 Gone)",
                    extra={"subscription_guid": sub.guid},
                )
                self.db.delete(sub)
            except PushDeliveryError as e:
                logger.warning(
                    f"Push delivery failed: {e}",
                    extra={"subscription_guid": sub.guid, "user_id": user_id},
                )

        self.db.commit()
        return success_count

    def _send_push(self, subscription: PushSubscription, payload_json: str) -> None:
        """
        Send a push notification to a single subscription via pywebpush.

        Args:
            subscription: Target push subscription
            payload_json: JSON-encoded push payload

        Raises:
            PushGoneError: If subscription returned 410 Gone
            PushDeliveryError: If delivery failed for other reasons
        """
        try:
            from pywebpush import webpush, WebPushException

            subscription_info = {
                "endpoint": subscription.endpoint,
                "keys": {
                    "p256dh": subscription.p256dh_key,
                    "auth": subscription.auth_key,
                },
            }

            webpush(
                subscription_info=subscription_info,
                data=payload_json,
                vapid_private_key=self.vapid_private_key,
                vapid_claims=self.vapid_claims,
            )
        except WebPushException as e:
            if hasattr(e, "response") and e.response is not None and e.response.status_code == 410:
                raise PushGoneError(subscription.endpoint) from e
            raise PushDeliveryError(str(e)) from e
        except Exception as e:
            raise PushDeliveryError(str(e)) from e

    # ========================================================================
    # Preferences Management (T013)
    # ========================================================================

    def get_default_preferences(self) -> Dict[str, Any]:
        """
        Get the default notification preferences.

        Returns:
            Dict with default preference values per data-model.md
        """
        return dict(DEFAULT_PREFERENCES)

    def get_user_preferences(self, user: User) -> Dict[str, Any]:
        """
        Get notification preferences for a user.

        Reads from User.preferences_json, falling back to defaults
        for any missing keys.

        Args:
            user: User instance

        Returns:
            Dict with notification preferences
        """
        defaults = self.get_default_preferences()

        if not user.preferences_json:
            return defaults

        try:
            prefs_data = json.loads(user.preferences_json)
        except (json.JSONDecodeError, TypeError):
            return defaults

        notification_prefs = prefs_data.get("notifications", {})

        # Merge with defaults (defaults fill missing keys)
        result = dict(defaults)
        for key in defaults:
            if key in notification_prefs:
                result[key] = notification_prefs[key]

        return result

    def update_preferences(
        self, user: User, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update notification preferences for a user (partial merge).

        Args:
            user: User instance
            updates: Dict of preference keys to update

        Returns:
            Updated preferences dict
        """
        # Get current full preferences
        current = self.get_user_preferences(user)

        # Apply updates (only known keys)
        valid_keys = set(DEFAULT_PREFERENCES.keys())
        for key, value in updates.items():
            if key in valid_keys and value is not None:
                current[key] = value

        # Read existing preferences_json or create new
        if user.preferences_json:
            try:
                full_prefs = json.loads(user.preferences_json)
            except (json.JSONDecodeError, TypeError):
                full_prefs = {}
        else:
            full_prefs = {}

        # Write back under "notifications" key
        full_prefs["notifications"] = current
        user.preferences_json = json.dumps(full_prefs)
        self.db.commit()
        self.db.refresh(user)

        logger.info(
            "Updated notification preferences",
            extra={"user_id": user.id},
        )

        return current

    def check_preference(self, user: User, category: str) -> bool:
        """
        Check if a user has a specific notification category enabled.

        Args:
            user: User instance
            category: Notification category (e.g., "job_failure")

        Returns:
            True if the category is enabled and master toggle is on
        """
        prefs = self.get_user_preferences(user)

        # Master toggle must be on
        if not prefs.get("enabled", False):
            return False

        # Check category-specific preference
        pref_key = CATEGORY_PREFERENCE_KEYS.get(category)
        if not pref_key:
            return False

        return prefs.get(pref_key, False)

    # ========================================================================
    # Domain Event Notifications
    # ========================================================================

    def notify_job_failure(self, job: Any) -> int:
        """
        Send job failure notifications to all active team members.

        Builds notification content per push-payload.md job_failure schema
        and delegates to send_notification() for per-user preference checks.

        Args:
            job: Failed Job instance (must have collection relationship loaded)

        Returns:
            Number of notifications actually sent (preference-filtered)
        """
        from backend.src.services.user_service import UserService

        # Build notification content per contract
        tool_name = job.tool.replace("_", " ").title()
        collection_name = job.collection.name if job.collection else "Unknown"
        error_summary = (job.error_message or "Unknown error")[:200]

        title = "Analysis Failed"
        body = f'{tool_name} analysis of "{collection_name}" failed: {error_summary}'

        result_guid = job.result.guid if job.result else None
        url = (
            f"/analytics?tab=reports&id={result_guid}"
            if result_guid
            else "/analytics?tab=reports"
        )

        data = {
            "url": url,
            "job_guid": job.guid,
            "collection_guid": job.collection.guid if job.collection else None,
            "result_guid": result_guid,
        }

        push_payload = {
            "title": title,
            "body": body,
            "icon": "/icons/icon-192x192.png",
            "badge": "/icons/badge-72x72.png",
            "tag": f"job_failure_{job.guid}",
            "data": {
                **data,
                "category": "job_failure",
            },
        }

        # Resolve all active team members
        user_service = UserService(db=self.db)
        team_members = user_service.list_by_team(
            team_id=job.team_id, active_only=True
        )

        sent_count = 0
        for user in team_members:
            notification = self.send_notification(
                user=user,
                team_id=job.team_id,
                category="job_failure",
                title=title,
                body=body,
                data=data,
                push_payload=push_payload,
            )
            if notification is not None:
                sent_count += 1

        logger.info(
            "Job failure notifications sent",
            extra={
                "job_guid": job.guid,
                "sent_count": sent_count,
                "team_members": len(team_members),
            },
        )

        return sent_count

    # ========================================================================
    # Orchestration
    # ========================================================================

    def send_notification(
        self,
        user: User,
        team_id: int,
        category: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        push_payload: Optional[Dict[str, Any]] = None,
    ) -> Optional[Notification]:
        """
        Orchestrate the full notification flow.

        1. Check user preferences for the category
        2. Create notification record in database
        3. Deliver push notification to all user subscriptions

        Args:
            user: Recipient User instance
            team_id: Team ID for tenant isolation
            category: Notification category
            title: Notification title
            body: Notification body
            data: JSONB data for notification record
            push_payload: Custom push payload (if different from notification content)

        Returns:
            Created Notification if category enabled, None if suppressed
        """
        # Check preferences
        if not self.check_preference(user, category):
            logger.debug(
                f"Notification suppressed by preference",
                extra={"user_id": user.id, "category": category},
            )
            return None

        # Create notification record
        notification = self.create_notification(
            team_id=team_id,
            user_id=user.id,
            category=category,
            title=title,
            body=body,
            data=data,
        )

        # Build push payload
        if push_payload is None:
            push_payload = {
                "title": title,
                "body": body,
                "icon": "/icons/icon-192x192.png",
                "badge": "/icons/badge-72x72.png",
                "data": {
                    **(data or {}),
                    "category": category,
                    "notification_guid": notification.guid,
                },
            }
        else:
            # Ensure notification_guid is in the push payload data
            if "data" not in push_payload:
                push_payload["data"] = {}
            push_payload["data"]["notification_guid"] = notification.guid

        # Deliver push notification
        self.deliver_push(user.id, team_id, push_payload)

        return notification


# ============================================================================
# Push Delivery Exceptions
# ============================================================================


class PushGoneError(Exception):
    """Raised when push service returns 410 Gone (subscription invalid)."""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        super().__init__(f"Push subscription gone: {endpoint[:60]}")


class PushDeliveryError(Exception):
    """Raised when push delivery fails."""
    pass
