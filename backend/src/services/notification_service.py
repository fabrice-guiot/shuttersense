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


# Agent notification debounce cache: (agent_id, transition_type) -> last_sent datetime
_agent_notification_debounce: Dict[tuple, datetime] = {}
AGENT_NOTIFICATION_DEBOUNCE_SECONDS = 300  # 5 minutes


# Default notification preferences (pre-opt-in)
DEFAULT_PREFERENCES = {
    "enabled": False,
    "job_failures": True,
    "inflection_points": True,
    "agent_status": True,
    "deadline": True,
    "conflict": True,
    "retry_warning": False,
    "deadline_days_before": 3,
    "timezone": "UTC",
    "retention_days": 30,
}

# Categories that map to preference keys
CATEGORY_PREFERENCE_KEYS = {
    "job_failure": "job_failures",
    "inflection_point": "inflection_points",
    "agent_status": "agent_status",
    "deadline": "deadline",
    "conflict": "conflict",
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

    def __init__(
        self,
        db: Session,
        vapid_private_key: str = "",
        vapid_claims: Optional[Dict[str, str]] = None,
        tenant_context: Optional[Any] = None,
    ):
        """
        Initialize notification service.

        Args:
            db: SQLAlchemy database session
            vapid_private_key: VAPID private key for push authentication
            vapid_claims: VAPID claims dict (e.g., {"sub": "mailto:..."})
            tenant_context: Optional TenantContext for tenant-scoped operations
        """
        self.db = db
        self.vapid_private_key = vapid_private_key
        self.vapid_claims = vapid_claims or {}
        self.tenant_context = tenant_context

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
            # Audit tracking
            created_by_user_id=user_id,
            updated_by_user_id=user_id,
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
        # Opportunistic cleanup of expired read notifications
        self.cleanup_read_notifications(user_id, team_id)

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
            if self.tenant_context is not None:
                notification.updated_by_user_id = self.tenant_context.user_id
            self.db.commit()
            self.db.refresh(notification)

        return notification

    def mark_all_as_read(self, user_id: int, team_id: int) -> int:
        """
        Mark all unread notifications as read for a user.

        Args:
            user_id: User's internal ID
            team_id: Team ID for tenant isolation

        Returns:
            Number of notifications that were marked as read
        """
        now = datetime.utcnow()
        update_values: Dict[str, Any] = {"read_at": now}
        if self.tenant_context is not None:
            update_values["updated_by_user_id"] = self.tenant_context.user_id
        updated = (
            self.db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.team_id == team_id,
                Notification.read_at.is_(None),
            )
            .update(update_values, synchronize_session="fetch")
        )
        self.db.commit()
        return updated

    def delete_old_notifications(self, days: int = 30, team_id: Optional[int] = None) -> int:
        """
        Delete notifications older than the specified number of days.

        Args:
            days: Age threshold in days (default 30)
            team_id: Team ID for tenant isolation. Falls back to
                      self.tenant_context.team_id if not provided.

        Returns:
            Number of notifications deleted

        Raises:
            ValueError: If no team_id is available from arguments or tenant_context
        """
        resolved_team_id = team_id
        if resolved_team_id is None and self.tenant_context is not None:
            resolved_team_id = self.tenant_context.team_id
        if resolved_team_id is None:
            raise ValueError("team_id is required for delete_old_notifications")

        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days)
        count = (
            self.db.query(Notification)
            .filter(
                Notification.team_id == resolved_team_id,
                Notification.created_at < cutoff,
            )
            .delete(synchronize_session=False)
        )
        self.db.commit()

        if count > 0:
            logger.info(f"Deleted {count} old notifications (>{days} days)")

        return count

    def cleanup_read_notifications(self, user_id: int, team_id: int) -> int:
        """
        Purge read notifications that exceed the user's retention_days preference.

        Only deletes notifications where read_at is not NULL and
        read_at is older than the user's configured retention period.
        Unread notifications are never purged.

        Args:
            user_id: User's internal ID
            team_id: Team ID for tenant isolation

        Returns:
            Number of read notifications deleted
        """
        # Resolve user to read retention_days preference
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return 0

        prefs = self.get_user_preferences(user)
        retention_days = prefs.get("retention_days", 30)

        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        count = (
            self.db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.team_id == team_id,
                Notification.read_at.isnot(None),
                Notification.read_at < cutoff,
            )
            .delete(synchronize_session=False)
        )
        self.db.commit()

        if count > 0:
            logger.info(
                f"Cleaned up {count} expired read notifications",
                extra={
                    "user_id": user_id,
                    "retention_days": retention_days,
                },
            )

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
        failed_count = 0
        removed_count = 0
        payload_json = json.dumps(payload)
        category = payload.get("data", {}).get("category", "unknown")

        for sub in subscriptions:
            endpoint_short = sub.endpoint[:60] if sub.endpoint else "?"
            try:
                self._send_push(sub, payload_json)
                sub.last_used_at = datetime.utcnow()
                success_count += 1
                logger.debug(
                    "Push delivered",
                    extra={
                        "subscription_guid": sub.guid,
                        "user_id": user_id,
                        "category": category,
                        "endpoint": endpoint_short,
                    },
                )
            except PushGoneError:
                # 410 Gone or 404 Not Found — subscription expired/invalid
                logger.info(
                    "Removing expired push subscription",
                    extra={
                        "subscription_guid": sub.guid,
                        "user_id": user_id,
                        "endpoint": endpoint_short,
                    },
                )
                self.db.delete(sub)
                removed_count += 1
            except PushDeliveryError as e:
                failed_count += 1
                logger.warning(
                    f"Push delivery failed: {e}",
                    extra={
                        "subscription_guid": sub.guid,
                        "user_id": user_id,
                        "category": category,
                        "endpoint": endpoint_short,
                    },
                )

        self.db.commit()

        if removed_count > 0 or failed_count > 0:
            logger.info(
                "Push delivery summary",
                extra={
                    "user_id": user_id,
                    "category": category,
                    "total": len(subscriptions),
                    "success": success_count,
                    "failed": failed_count,
                    "removed": removed_count,
                },
            )

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
        except ImportError as e:
            raise PushDeliveryError(
                "pywebpush is not installed. Install with: pip install pywebpush"
            ) from e

        try:
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
                ttl=86400,
                headers={"Urgency": "high"},
            )
        except WebPushException as e:
            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code
                # 410 Gone or 404 Not Found — subscription is expired/invalid
                if status_code in (410, 404):
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
            logger.debug(
                "Preference check: master toggle off",
                extra={"user_id": user.id, "category": category},
            )
            return False

        # Check category-specific preference
        pref_key = CATEGORY_PREFERENCE_KEYS.get(category)
        if not pref_key:
            logger.debug(
                "Preference check: unknown category",
                extra={"user_id": user.id, "category": category},
            )
            return False

        enabled = prefs.get(pref_key, False)
        if not enabled:
            logger.debug(
                "Preference check: category disabled",
                extra={"user_id": user.id, "category": category, "pref_key": pref_key},
            )
        return enabled

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

    def notify_conflict_detected(
        self,
        team_id: int,
        event_a_title: str,
        event_b_title: str,
        event_a_guid: str,
        event_b_guid: str,
        conflict_type: str,
        event_a_date: str,
        event_b_date: str,
    ) -> int:
        """
        Send conflict detection notifications to all active team members.

        Called after event create/update when new conflicts are detected.

        Args:
            team_id: Team that owns the events
            event_a_title: Title of the first conflicting event
            event_b_title: Title of the second conflicting event
            event_a_guid: GUID of the first event
            event_b_guid: GUID of the second event
            conflict_type: Type of conflict (time_overlap, distance, travel_buffer)
            event_a_date: ISO date string for the first event
            event_b_date: ISO date string for the second event

        Returns:
            Number of notifications actually sent (preference-filtered)
        """
        from backend.src.services.user_service import UserService

        type_label = conflict_type.replace("_", " ")
        title = "New scheduling conflict detected"

        # For cross-day conflicts, show both dates
        if event_a_date == event_b_date:
            date_str = event_a_date
        else:
            date_str = f"{event_a_date} and {event_b_date}"

        body = (
            f'"{event_a_title}" has a {type_label} conflict with '
            f'"{event_b_title}" on {date_str}'
        )

        # Navigate to the earlier date
        nav_date = min(event_a_date, event_b_date)
        data = {
            "url": f"/events?date={nav_date}",
            "event_guids": [event_a_guid, event_b_guid],
        }

        push_payload = {
            "title": title,
            "body": body,
            "icon": "/icons/icon-192x192.png",
            "badge": "/icons/badge-72x72.png",
            "tag": f"conflict_{event_a_guid}_{event_b_guid}",
            "data": {
                **data,
                "category": "conflict",
            },
        }

        user_service = UserService(db=self.db)
        team_members = user_service.list_by_team(
            team_id=team_id, active_only=True
        )

        sent_count = 0
        for user in team_members:
            notification = self.send_notification(
                user=user,
                team_id=team_id,
                category="conflict",
                title=title,
                body=body,
                data=data,
                push_payload=push_payload,
            )
            if notification is not None:
                sent_count += 1

        logger.info(
            "Conflict notifications sent",
            extra={
                "event_a_guid": event_a_guid,
                "event_b_guid": event_b_guid,
                "conflict_type": conflict_type,
                "sent_count": sent_count,
                "team_members": len(team_members),
            },
        )

        return sent_count

    def notify_inflection_point(self, job: Any, result: Any) -> int:
        """
        Send inflection point notifications when analysis detects changes.

        Only called for COMPLETED results where no_change_copy=False, meaning
        a new report was generated with potentially different findings.

        Calculates issue_delta from the previous result (if available) and
        builds notification content per push-payload.md inflection_point schema.

        Args:
            job: Completed Job instance (must have collection relationship loaded)
            result: New AnalysisResult instance

        Returns:
            Number of notifications actually sent (preference-filtered)
        """
        from backend.src.models.analysis_result import AnalysisResult
        from backend.src.models import ResultStatus
        from backend.src.services.user_service import UserService

        # Build notification content per contract
        tool_name = job.tool.replace("_", " ").title()
        collection_name = job.collection.name if job.collection else "Unknown"
        collection_guid = job.collection.guid if job.collection else None

        # Calculate issue delta from previous result
        issue_delta_summary = self._build_issue_delta_summary(
            job, result, AnalysisResult, ResultStatus
        )

        title = "New Analysis Results"
        body = f'{tool_name} found changes in "{collection_name}": {issue_delta_summary}'

        # Use analytics report page URL (consistent with job failure notifications)
        url = f"/analytics?tab=reports&id={result.guid}"

        data = {
            "url": url,
            "result_guid": result.guid,
            "collection_guid": collection_guid,
        }

        push_payload = {
            "title": title,
            "body": body,
            "icon": "/icons/icon-192x192.png",
            "badge": "/icons/badge-72x72.png",
            "tag": f"inflection_point_{result.guid}",
            "data": {
                **data,
                "category": "inflection_point",
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
                category="inflection_point",
                title=title,
                body=body,
                data=data,
                push_payload=push_payload,
            )
            if notification is not None:
                sent_count += 1

        logger.info(
            "Inflection point notifications sent",
            extra={
                "job_guid": job.guid,
                "result_guid": result.guid,
                "sent_count": sent_count,
                "team_members": len(team_members),
            },
        )

        return sent_count

    def _build_issue_delta_summary(
        self, job: Any, result: Any, AnalysisResult: type, ResultStatus: type
    ) -> str:
        """
        Build a human-readable issue delta summary by comparing with the
        previous result for the same collection and tool.

        Args:
            job: Completed Job instance
            result: New AnalysisResult instance
            AnalysisResult: The AnalysisResult model class
            ResultStatus: The ResultStatus enum class

        Returns:
            Summary string like "5 issues found (+2 from previous)"
        """
        current_issues = result.issues_found or 0
        current_files = result.files_scanned or 0

        # Find the previous completed result for the same collection + tool (team-scoped)
        previous = (
            self.db.query(AnalysisResult)
            .filter(
                AnalysisResult.team_id == job.team_id,
                AnalysisResult.collection_id == job.collection_id,
                AnalysisResult.tool == job.tool,
                AnalysisResult.status == ResultStatus.COMPLETED,
                AnalysisResult.id != result.id,
            )
            .order_by(AnalysisResult.created_at.desc())
            .first()
        )

        if previous and previous.issues_found is not None:
            delta = current_issues - previous.issues_found
            if delta > 0:
                return f"{current_issues} issues found (+{delta} new) across {current_files} files"
            elif delta < 0:
                return f"{current_issues} issues found ({delta} resolved) across {current_files} files"
            else:
                return f"{current_issues} issues found (unchanged) across {current_files} files"

        return f"{current_issues} issues found across {current_files} files"

    def notify_agent_status(
        self,
        agent: Any,
        team_id: int,
        transition_type: str,
        error_description: Optional[str] = None,
    ) -> int:
        """
        Send agent status notifications to all active team members.

        Builds notification content per push-payload.md agent status schemas
        and delegates to send_notification() for per-user preference checks.

        Debounces per (agent.id, transition_type) within 5-minute window.

        Args:
            agent: Agent instance (must have .id, .guid, .name, .team)
            team_id: Team ID for tenant isolation
            transition_type: One of "pool_offline", "agent_error", "agent_outdated", "pool_recovery"
            error_description: Error message (required for agent_error)

        Returns:
            Number of notifications actually sent (preference-filtered)
        """
        from backend.src.services.user_service import UserService

        # Debounce check
        debounce_key = (agent.id, transition_type)
        now = datetime.utcnow()
        last_sent = _agent_notification_debounce.get(debounce_key)
        if last_sent and (now - last_sent).total_seconds() < AGENT_NOTIFICATION_DEBOUNCE_SECONDS:
            logger.debug(
                "Agent notification debounced",
                extra={
                    "agent_guid": agent.guid,
                    "transition_type": transition_type,
                },
            )
            return 0

        # Build notification content per push-payload.md
        team_guid = agent.team.guid if agent.team else ""

        if transition_type == "pool_offline":
            title = "Agent Pool Offline"
            body = "All agents are offline. Jobs cannot be processed until an agent reconnects."
            tag = f"agent_pool_offline_{team_guid}"
            url = "/agents"
            data = {
                "url": url,
                "category": "agent_status",
            }
        elif transition_type == "agent_error":
            error_desc = (error_description or "Unknown error")[:200]
            title = "Agent Error"
            body = f'Agent "{agent.name}" reported an error: {error_desc}'
            tag = f"agent_error_{agent.guid}"
            url = f"/agents/{agent.guid}"
            data = {
                "url": url,
                "category": "agent_status",
                "agent_guid": agent.guid,
            }
        elif transition_type == "agent_outdated":
            agent_version = getattr(agent, 'version', 'unknown') or 'unknown'
            title = "Agent Outdated"
            body = f'Agent "{agent.name}" (v{agent_version}) has a newer version available.'
            tag = f"agent_outdated_{agent.guid}"
            url = f"/agents/{agent.guid}"
            data = {
                "url": url,
                "category": "agent_status",
                "agent_guid": agent.guid,
            }
        elif transition_type == "pool_recovery":
            title = "Agents Available"
            body = f'Agent "{agent.name}" is back online. Job processing has resumed.'
            tag = f"agent_recovery_{team_guid}"
            url = "/agents"
            data = {
                "url": url,
                "category": "agent_status",
            }
        else:
            logger.warning(
                f"Unknown agent transition type: {transition_type}",
                extra={"agent_guid": agent.guid},
            )
            return 0

        push_payload = {
            "title": title,
            "body": body,
            "icon": "/icons/icon-192x192.png",
            "badge": "/icons/badge-72x72.png",
            "tag": tag,
            "data": {
                **data,
                "category": "agent_status",
            },
        }

        # Resolve all active team members
        user_service = UserService(db=self.db)
        team_members = user_service.list_by_team(
            team_id=team_id, active_only=True
        )

        sent_count = 0
        for user in team_members:
            notification = self.send_notification(
                user=user,
                team_id=team_id,
                category="agent_status",
                title=title,
                body=body,
                data=data,
                push_payload=push_payload,
            )
            if notification is not None:
                sent_count += 1

        # Update debounce timestamp only if at least one notification was sent
        if sent_count > 0:
            _agent_notification_debounce[debounce_key] = now

        logger.info(
            "Agent status notifications sent",
            extra={
                "agent_guid": agent.guid,
                "transition_type": transition_type,
                "sent_count": sent_count,
                "team_members": len(team_members),
            },
        )

        return sent_count

    def notify_retry_warning(self, job: Any) -> int:
        """
        Send retry warning notifications when a job enters its final retry attempt.

        Builds notification content per push-payload.md retry_warning schema
        and delegates to send_notification() for per-user preference checks.
        The retry_warning preference is disabled by default.

        Args:
            job: Job instance on its final retry (must have collection relationship loaded)

        Returns:
            Number of notifications actually sent (preference-filtered)
        """
        from backend.src.services.user_service import UserService

        tool_name = job.tool.replace("_", " ").title()
        collection_name = job.collection.name if job.collection else "Unknown"

        title = "Job Retry Warning"
        body = f'{tool_name} analysis of "{collection_name}" is on final retry attempt'

        data = {
            "url": f"/tools?job={job.guid}",
            "job_guid": job.guid,
            "collection_guid": job.collection.guid if job.collection else None,
        }

        push_payload = {
            "title": title,
            "body": body,
            "icon": "/icons/icon-192x192.png",
            "badge": "/icons/badge-72x72.png",
            "tag": f"retry_warning_{job.guid}",
            "data": {
                **data,
                "category": "retry_warning",
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
                category="retry_warning",
                title=title,
                body=body,
                data=data,
                push_payload=push_payload,
            )
            if notification is not None:
                sent_count += 1

        logger.info(
            "Retry warning notifications sent",
            extra={
                "job_guid": job.guid,
                "retry_count": job.retry_count,
                "max_retries": job.max_retries,
                "sent_count": sent_count,
                "team_members": len(team_members),
            },
        )

        return sent_count

    # ========================================================================
    # Deadline Reminders (Phase 9 — T037)
    # ========================================================================

    def check_deadlines(self, team_id: int) -> int:
        """
        Check for approaching event deadlines and send reminder notifications.

        Queries events with deadline_date within the next 30 days, respects
        per-user deadline_days_before and timezone preferences, and deduplicates
        via existing notification records.

        Args:
            team_id: Team ID to check deadlines for

        Returns:
            Total number of new deadline reminders sent
        """
        from zoneinfo import ZoneInfo
        from backend.src.models import Event, EventStatus
        from backend.src.services.user_service import UserService

        # 1. Query upcoming deadlines for this team
        today_utc = date.today()
        max_window = today_utc + timedelta(days=30)

        events = (
            self.db.query(Event)
            .filter(
                Event.team_id == team_id,
                Event.deadline_date.isnot(None),
                Event.deadline_date >= today_utc,
                Event.deadline_date <= max_window,
                Event.status.notin_([
                    EventStatus.COMPLETED.value,
                    EventStatus.CANCELLED.value,
                ]),
                Event.deleted_at.is_(None),
            )
            .all()
        )

        if not events:
            return 0

        # 2. Resolve active team members
        user_service = UserService(db=self.db)
        team_members = user_service.list_by_team(
            team_id=team_id, active_only=True
        )

        if not team_members:
            return 0

        sent_count = 0

        # 3. Per-user processing
        for user in team_members:
            prefs = self.get_user_preferences(user)
            deadline_days_before = prefs.get("deadline_days_before", 3)
            user_tz_str = prefs.get("timezone", "UTC")

            try:
                user_tz = ZoneInfo(user_tz_str)
            except (KeyError, Exception):
                user_tz = ZoneInfo("UTC")

            # Compute user's "today" in their local timezone
            user_today = datetime.now(user_tz).date()

            for event in events:
                days_remaining = (event.deadline_date - user_today).days

                # Only send if within the user's configured window
                if days_remaining < 0 or days_remaining > deadline_days_before:
                    continue

                # 4. Deduplication check (scoped per team to avoid cross-tenant suppression)
                existing = (
                    self.db.query(Notification)
                    .filter(
                        Notification.team_id == team_id,
                        Notification.user_id == user.id,
                        Notification.category == "deadline",
                        Notification.data["event_guid"].as_string() == event.guid,
                        Notification.data["days_before"].as_string() == str(days_remaining),
                    )
                    .first()
                )

                if existing:
                    continue

                # 5. Build notification content
                if days_remaining == 0:
                    days_text = "today"
                elif days_remaining == 1:
                    days_text = "tomorrow"
                else:
                    days_text = f"in {days_remaining} days"

                title = "Deadline Approaching"
                body = f'"{event.title}" deadline {days_text}'
                tag = f"deadline_{event.guid}_{days_remaining}"
                data = {
                    "url": f"/events/{event.guid}",
                    "category": "deadline",
                    "event_guid": event.guid,
                    "days_before": str(days_remaining),
                }

                push_payload = {
                    "title": title,
                    "body": body,
                    "icon": "/icons/icon-192x192.png",
                    "badge": "/icons/badge-72x72.png",
                    "tag": tag,
                    "data": {
                        **data,
                        "category": "deadline",
                    },
                }

                # 6. Send via orchestration (checks preferences + creates record + pushes)
                notification = self.send_notification(
                    user=user,
                    team_id=team_id,
                    category="deadline",
                    title=title,
                    body=body,
                    data=data,
                    push_payload=push_payload,
                )
                if notification is not None:
                    sent_count += 1

        logger.info(
            "Deadline check completed",
            extra={
                "team_id": team_id,
                "events_checked": len(events),
                "users_checked": len(team_members),
                "sent_count": sent_count,
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
