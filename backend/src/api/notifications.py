"""
Notifications API endpoints for push subscriptions, preferences, and history.

Provides endpoints for:
- Push subscription management (subscribe, unsubscribe, status)
- Notification preferences (get, update)
- Notification history (list, unread count, mark as read)
- VAPID public key retrieval

Issue #114 - PWA with Push Notifications
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.src.db.database import get_db
from backend.src.middleware.auth import require_auth, TenantContext
from backend.src.schemas.notifications import (
    PushSubscriptionCreate,
    PushSubscriptionResponse,
    PushSubscriptionUpdate,
    PushSubscriptionRemove,
    TestPushResponse,
    SubscriptionStatusResponse,
    NotificationPreferencesResponse,
    NotificationPreferencesUpdate,
    NotificationResponse,
    NotificationListResponse,
    NotificationStatsResponse,
    UnreadCountResponse,
    MarkAllReadResponse,
    VapidKeyResponse,
)
from backend.src.models.user import User
from backend.src.services.push_subscription_service import PushSubscriptionService
from backend.src.services.notification_service import NotificationService
from backend.src.services.exceptions import NotFoundError
from backend.src.config.settings import get_settings
from backend.src.utils.logging_config import get_logger


logger = get_logger("api")

# Use the shared limiter from main module
from backend.src.main import limiter

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


# ============================================================================
# Dependencies
# ============================================================================


def get_push_subscription_service(
    db: Session = Depends(get_db),
) -> PushSubscriptionService:
    """Create PushSubscriptionService instance with database session."""
    return PushSubscriptionService(db=db)


def get_notification_service(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_auth),
) -> NotificationService:
    """Create NotificationService instance with database session, VAPID config, and tenant context."""
    settings = get_settings()
    vapid_claims = {"sub": settings.vapid_subject} if settings.vapid_subject else {}
    return NotificationService(
        db=db,
        vapid_private_key=settings.vapid_private_key,
        vapid_claims=vapid_claims,
        tenant_context=ctx,
    )


def _get_user(db: Session, user_id: int) -> User:
    """Fetch user from database by ID. Raises 404 if not found."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


# ============================================================================
# Push Subscription Endpoints
# ============================================================================


@router.post(
    "/subscribe",
    response_model=PushSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a push subscription",
)
@limiter.limit("10/minute")
async def create_push_subscription(
    request: Request,
    body: PushSubscriptionCreate,
    ctx: TenantContext = Depends(require_auth),
    service: PushSubscriptionService = Depends(get_push_subscription_service),
    notif_service: NotificationService = Depends(get_notification_service),
):
    """
    Register a Web Push subscription for the authenticated user's current device.

    If a subscription with the same endpoint already exists, it is replaced.
    On first subscription, sends a welcome notification to confirm delivery works.
    """
    # Check if this is the user's first subscription (for in-app welcome record)
    existing = service.list_subscriptions(
        user_id=ctx.user_id, team_id=ctx.team_id
    )
    is_first = len(existing) == 0

    subscription = service.create_subscription(
        team_id=ctx.team_id,
        user_id=ctx.user_id,
        endpoint=body.endpoint,
        p256dh_key=body.p256dh_key,
        auth_key=body.auth_key,
        device_name=body.device_name,
    )

    # Create in-app welcome notification only on first subscription
    if is_first:
        notif_service.create_notification(
            team_id=ctx.team_id,
            user_id=ctx.user_id,
            category="agent_status",
            title="Notifications enabled",
            body=(
                "You've successfully enabled push notifications. "
                "You'll be notified about job failures, analysis changes, "
                "agent status, and upcoming deadlines."
            ),
            data={"url": "/profile"},
        )

    # Send confirmation push to the newly registered device (every registration)
    device_label = subscription.device_name or "this device"
    notif_service.deliver_push_to_subscription(
        subscription=subscription,
        payload={
            "title": "Device registered",
            "body": f"Device registered \u2014 {device_label} is now receiving notifications",
            "icon": "/icons/icon-192x192.png",
            "badge": "/icons/badge-72x72.png",
            "data": {"url": "/profile"},
        },
    )

    return PushSubscriptionResponse.model_validate(subscription)


@router.delete(
    "/subscribe",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a push subscription",
)
@limiter.limit("10/minute")
async def remove_push_subscription(
    request: Request,
    body: PushSubscriptionRemove,
    ctx: TenantContext = Depends(require_auth),
    service: PushSubscriptionService = Depends(get_push_subscription_service),
):
    """
    Remove the push subscription matching the given endpoint for the authenticated user.
    """
    try:
        service.remove_subscription(
            user_id=ctx.user_id,
            team_id=ctx.team_id,
            endpoint=body.endpoint,
        )
    except NotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        ) from err


@router.delete(
    "/subscribe/{guid}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a push subscription by GUID",
)
@limiter.limit("10/minute")
async def remove_push_subscription_by_guid(
    request: Request,
    guid: str,
    ctx: TenantContext = Depends(require_auth),
    service: PushSubscriptionService = Depends(get_push_subscription_service),
):
    """
    Remove a push subscription by its GUID.

    Allows users to remove subscriptions from devices they no longer have access to
    (e.g., lost or decommissioned devices) by referencing the subscription GUID
    shown in the device list.
    """
    try:
        service.remove_subscription_by_guid(
            user_id=ctx.user_id,
            team_id=ctx.team_id,
            guid=guid,
        )
    except NotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        ) from err


@router.post(
    "/subscribe/{guid}/test",
    response_model=TestPushResponse,
    summary="Send a test push notification to a specific device",
)
@limiter.limit("5/minute")
async def test_push_subscription(
    request: Request,
    guid: str,
    ctx: TenantContext = Depends(require_auth),
    service: PushSubscriptionService = Depends(get_push_subscription_service),
    notif_service: NotificationService = Depends(get_notification_service),
):
    """
    Send a test push notification to a specific subscription to verify delivery.

    Useful for confirming a registered device can actually receive notifications.
    Rate limited to 5 requests per minute to prevent abuse.
    """
    try:
        subscription = service.get_subscription_by_guid(
            user_id=ctx.user_id, team_id=ctx.team_id, guid=guid
        )
    except NotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        ) from err

    device_label = subscription.device_name or "this device"
    success = notif_service.deliver_push_to_subscription(
        subscription=subscription,
        payload={
            "title": "Simulated notification",
            "body": f"Simulated notification \u2014 Push is working on {device_label}",
            "icon": "/icons/icon-192x192.png",
            "badge": "/icons/badge-72x72.png",
            "data": {"url": "/profile"},
        },
    )

    if success:
        return TestPushResponse(success=True)
    return TestPushResponse(success=False, error="Push delivery failed")


@router.patch(
    "/subscribe/{guid}",
    response_model=PushSubscriptionResponse,
    summary="Update a push subscription",
)
@limiter.limit("10/minute")
async def update_push_subscription(
    request: Request,
    guid: str,
    body: PushSubscriptionUpdate,
    ctx: TenantContext = Depends(require_auth),
    service: PushSubscriptionService = Depends(get_push_subscription_service),
):
    """
    Update a push subscription's device name.

    Allows users to assign friendly names to their devices.
    """
    try:
        subscription = service.rename_subscription(
            user_id=ctx.user_id,
            team_id=ctx.team_id,
            guid=guid,
            device_name=body.device_name,
        )
    except NotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        ) from err

    return PushSubscriptionResponse.model_validate(subscription)


@router.get(
    "/status",
    response_model=SubscriptionStatusResponse,
    summary="Check push subscription status",
)
@limiter.limit("10/minute")
async def get_subscription_status(
    request: Request,
    ctx: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db),
    sub_service: PushSubscriptionService = Depends(get_push_subscription_service),
    notif_service: NotificationService = Depends(get_notification_service),
):
    """
    Returns notification enablement status and active subscriptions for the authenticated user.
    """
    user = _get_user(db, ctx.user_id)
    prefs = notif_service.get_user_preferences(user)
    subscriptions = sub_service.list_subscriptions(
        user_id=ctx.user_id, team_id=ctx.team_id
    )
    return SubscriptionStatusResponse(
        notifications_enabled=prefs.get("enabled", False),
        subscriptions=[
            PushSubscriptionResponse.model_validate(s) for s in subscriptions
        ],
    )


# ============================================================================
# Notification Preferences Endpoints
# ============================================================================


@router.get(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    summary="Get notification preferences",
)
@limiter.limit("10/minute")
async def get_notification_preferences(
    request: Request,
    ctx: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db),
    service: NotificationService = Depends(get_notification_service),
):
    """
    Returns the authenticated user's notification preference settings.
    """
    user = _get_user(db, ctx.user_id)
    prefs = service.get_user_preferences(user)
    return NotificationPreferencesResponse(**prefs)


@router.put(
    "/preferences",
    response_model=NotificationPreferencesResponse,
    summary="Update notification preferences",
)
@limiter.limit("10/minute")
async def update_notification_preferences(
    request: Request,
    body: NotificationPreferencesUpdate,
    ctx: TenantContext = Depends(require_auth),
    db: Session = Depends(get_db),
    service: NotificationService = Depends(get_notification_service),
):
    """
    Update the authenticated user's notification preferences.

    All fields are optional; only provided fields are updated.
    """
    # Validate timezone if provided
    if body.timezone is not None:
        try:
            from zoneinfo import available_timezones

            if body.timezone not in available_timezones():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid timezone: {body.timezone}",
                )
        except ImportError:
            pass  # zoneinfo not available, skip validation

    # Validate deadline_days_before range (Pydantic handles ge=1, le=30)

    user = _get_user(db, ctx.user_id)
    updates = body.model_dump(exclude_none=True)
    updated_prefs = service.update_preferences(user, updates)
    return NotificationPreferencesResponse(**updated_prefs)


# ============================================================================
# Notification History Endpoints
# ============================================================================


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List notification history",
)
@limiter.limit("10/minute")
async def list_notifications(
    request: Request,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    category: Optional[str] = Query(
        default=None,
        description="Filter by category",
    ),
    unread_only: bool = Query(default=False),
    search: Optional[str] = Query(
        default=None,
        max_length=100,
        description="Search text in title and body",
    ),
    from_date: Optional[str] = Query(
        default=None,
        description="ISO date string, filter created_at >=",
    ),
    to_date: Optional[str] = Query(
        default=None,
        description="ISO date string, filter created_at <= end of day",
    ),
    read_only: bool = Query(
        default=False,
        description="Filter for read-only notifications",
    ),
    ctx: TenantContext = Depends(require_auth),
    service: NotificationService = Depends(get_notification_service),
):
    """
    Returns the authenticated user's recent notifications.
    """
    notifications, total = service.list_notifications(
        user_id=ctx.user_id,
        team_id=ctx.team_id,
        limit=limit,
        offset=offset,
        category=category,
        unread_only=unread_only,
        search=search,
        from_date=from_date,
        to_date=to_date,
        read_only=read_only,
    )
    return NotificationListResponse(
        items=[
            NotificationResponse.model_validate(n) for n in notifications
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/stats",
    response_model=NotificationStatsResponse,
    summary="Get notification stats",
)
@limiter.limit("10/minute")
async def get_notification_stats(
    request: Request,
    ctx: TenantContext = Depends(require_auth),
    service: NotificationService = Depends(get_notification_service),
):
    """
    Returns notification statistics for the TopHeader KPIs:
    total count, unread count, and this week's count.
    """
    stats = service.get_stats(user_id=ctx.user_id, team_id=ctx.team_id)
    return NotificationStatsResponse(**stats)


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread notification count",
)
@limiter.limit("10/minute")
async def get_unread_count(
    request: Request,
    ctx: TenantContext = Depends(require_auth),
    service: NotificationService = Depends(get_notification_service),
):
    """
    Returns the count of unread notifications for the notification bell badge.
    """
    count = service.get_unread_count(
        user_id=ctx.user_id, team_id=ctx.team_id
    )
    return UnreadCountResponse(unread_count=count)


@router.post(
    "/mark-all-read",
    response_model=MarkAllReadResponse,
    summary="Mark all notifications as read",
)
@limiter.limit("10/minute")
async def mark_all_notifications_read(
    request: Request,
    ctx: TenantContext = Depends(require_auth),
    service: NotificationService = Depends(get_notification_service),
):
    """
    Mark all unread notifications as read for the authenticated user.

    Returns the number of notifications that were marked as read.
    Idempotent — calling when all notifications are already read returns 0.
    """
    updated_count = service.mark_all_as_read(
        user_id=ctx.user_id, team_id=ctx.team_id
    )
    return MarkAllReadResponse(updated_count=updated_count)


@router.post(
    "/{guid}/read",
    response_model=NotificationResponse,
    summary="Mark notification as read",
)
@limiter.limit("10/minute")
async def mark_notification_read(
    request: Request,
    guid: str,
    ctx: TenantContext = Depends(require_auth),
    service: NotificationService = Depends(get_notification_service),
):
    """
    Mark a single notification as read. Idempotent — marking an already-read
    notification is a no-op.
    """
    try:
        notification = service.mark_as_read(guid=guid, team_id=ctx.team_id)
        return NotificationResponse.model_validate(notification)
    except NotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        ) from err


# ============================================================================
# Deadline Check Endpoint (Phase 9 — T038)
# ============================================================================


@router.post(
    "/deadline-check",
    summary="Run deadline reminder check",
    description="Manually trigger deadline reminder check for the current team. "
                "Sends notifications for approaching event deadlines. Idempotent.",
)
@limiter.limit("5/minute")
async def run_deadline_check(
    request: Request,
    ctx: TenantContext = Depends(require_auth),
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    """
    Run a deadline reminder check for the authenticated user's team.

    Returns the number of new deadline reminder notifications sent.
    Idempotent — calling again will not produce duplicate notifications.
    """
    sent_count = service.check_deadlines(team_id=ctx.team_id)
    return {"sent_count": sent_count}


# ============================================================================
# VAPID Key Endpoint
# ============================================================================


@router.get(
    "/vapid-key",
    response_model=VapidKeyResponse,
    summary="Get VAPID public key",
)
@limiter.limit("10/minute")
async def get_vapid_key(
    request: Request,
    ctx: TenantContext = Depends(require_auth),
):
    """
    Returns the server's VAPID public key for creating push subscriptions.
    """
    settings = get_settings()
    if not settings.vapid_public_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Push notifications not configured",
        )
    return VapidKeyResponse(vapid_public_key=settings.vapid_public_key)
