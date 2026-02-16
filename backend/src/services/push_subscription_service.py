"""
Push subscription service for managing Web Push subscriptions.

Provides business logic for subscribing, unsubscribing, listing,
and cleaning up push notification subscriptions.

Issue #114 - PWA with Push Notifications
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.src.models.push_subscription import PushSubscription
from backend.src.services.exceptions import NotFoundError
from backend.src.utils.logging_config import get_logger


logger = get_logger("services")


class PushSubscriptionService:
    """
    Service for managing Web Push subscriptions.

    Handles subscription lifecycle:
    - Create (upsert by endpoint)
    - Remove (by endpoint + user)
    - List (by user)
    - Cleanup expired subscriptions
    - Remove invalid (410 Gone) subscriptions
    """

    def __init__(self, db: Session):
        self.db = db

    def create_subscription(
        self,
        team_id: int,
        user_id: int,
        endpoint: str,
        p256dh_key: str,
        auth_key: str,
        device_name: Optional[str] = None,
    ) -> PushSubscription:
        """
        Create or replace a push subscription.

        If a subscription with the same endpoint already exists for this user,
        it is updated. If it exists for a different user, the old one is removed
        and a new one created (endpoint transfer).

        Args:
            team_id: Team ID for tenant isolation
            user_id: Owning user's internal ID
            endpoint: Push service endpoint URL
            p256dh_key: ECDH public key (Base64url)
            auth_key: Auth secret (Base64url)
            device_name: Optional user-friendly device label

        Returns:
            Created or updated PushSubscription
        """
        # Check for existing subscription with this endpoint
        existing = (
            self.db.query(PushSubscription)
            .filter(PushSubscription.endpoint == endpoint)
            .first()
        )

        if existing:
            # Update existing subscription (may be same or different user)
            existing.user_id = user_id
            existing.team_id = team_id
            existing.p256dh_key = p256dh_key
            existing.auth_key = auth_key
            existing.device_name = device_name
            self.db.commit()
            self.db.refresh(existing)
            logger.info(
                "Updated push subscription",
                extra={"endpoint_prefix": endpoint[:60], "user_id": user_id},
            )
            return existing

        # Create new subscription
        subscription = PushSubscription(
            team_id=team_id,
            user_id=user_id,
            endpoint=endpoint,
            p256dh_key=p256dh_key,
            auth_key=auth_key,
            device_name=device_name,
        )
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        logger.info(
            "Created push subscription",
            extra={"guid": subscription.guid, "user_id": user_id},
        )
        return subscription

    def remove_subscription_by_guid(self, user_id: int, team_id: int, guid: str) -> bool:
        """
        Remove a push subscription by its GUID.

        Allows users to remove subscriptions from other devices (e.g., lost devices)
        by referencing the subscription GUID shown in the device list.

        Args:
            user_id: Owning user's internal ID
            team_id: Team ID for tenant isolation
            guid: Subscription GUID (sub_xxx)

        Returns:
            True if subscription was found and removed

        Raises:
            NotFoundError: If no subscription matches guid + user + team
        """
        try:
            sub_uuid = PushSubscription.parse_guid(guid)
        except ValueError:
            raise NotFoundError("PushSubscription", guid)

        subscription = (
            self.db.query(PushSubscription)
            .filter(
                PushSubscription.uuid == sub_uuid,
                PushSubscription.user_id == user_id,
                PushSubscription.team_id == team_id,
            )
            .first()
        )

        if not subscription:
            raise NotFoundError("PushSubscription", guid)

        self.db.delete(subscription)
        self.db.commit()
        logger.info(
            "Removed push subscription by GUID",
            extra={"guid": guid, "user_id": user_id},
        )
        return True

    def remove_subscription(self, user_id: int, team_id: int, endpoint: str) -> bool:
        """
        Remove a push subscription by endpoint for a specific user.

        Args:
            user_id: Owning user's internal ID
            team_id: Team ID for tenant isolation
            endpoint: Push service endpoint URL

        Returns:
            True if subscription was found and removed

        Raises:
            NotFoundError: If no subscription matches endpoint + user + team
        """
        subscription = (
            self.db.query(PushSubscription)
            .filter(
                PushSubscription.endpoint == endpoint,
                PushSubscription.user_id == user_id,
                PushSubscription.team_id == team_id,
            )
            .first()
        )

        if not subscription:
            raise NotFoundError("PushSubscription", endpoint)

        self.db.delete(subscription)
        self.db.commit()
        logger.info(
            "Removed push subscription",
            extra={"endpoint_prefix": endpoint[:60], "user_id": user_id},
        )
        return True

    def list_subscriptions(self, user_id: int, team_id: int) -> List[PushSubscription]:
        """
        List all active push subscriptions for a user.

        Args:
            user_id: User's internal ID
            team_id: Team ID for tenant isolation

        Returns:
            List of PushSubscription instances
        """
        return (
            self.db.query(PushSubscription)
            .filter(
                PushSubscription.user_id == user_id,
                PushSubscription.team_id == team_id,
            )
            .order_by(PushSubscription.created_at.desc())
            .all()
        )

    def cleanup_expired(self) -> int:
        """
        Remove subscriptions that have passed their expiration date.

        Returns:
            Number of subscriptions removed
        """
        now = datetime.utcnow()
        expired = (
            self.db.query(PushSubscription)
            .filter(
                PushSubscription.expires_at.isnot(None),
                PushSubscription.expires_at < now,
            )
            .all()
        )

        count = len(expired)
        for sub in expired:
            self.db.delete(sub)

        if count > 0:
            self.db.commit()
            logger.info(f"Cleaned up {count} expired push subscriptions")

        return count

    def remove_invalid(self, endpoint: str) -> None:
        """
        Remove a subscription that returned 410 Gone from the push service.

        Called when push delivery receives a 410 response, indicating
        the subscription is no longer valid.

        Args:
            endpoint: The invalid push service endpoint
        """
        subscription = (
            self.db.query(PushSubscription)
            .filter(PushSubscription.endpoint == endpoint)
            .first()
        )

        if subscription:
            logger.info(
                "Removing invalid push subscription (410 Gone)",
                extra={"guid": subscription.guid, "endpoint_prefix": endpoint[:60]},
            )
            self.db.delete(subscription)
            self.db.commit()

    def update_last_used(self, subscription: PushSubscription) -> None:
        """
        Update the last_used_at timestamp after successful push delivery.

        Args:
            subscription: The subscription that was used
        """
        subscription.last_used_at = datetime.utcnow()
        self.db.commit()
