# Quickstart: PWA with Push Notifications

**Feature Branch**: `114-pwa-push-notifications`

## Prerequisites

- Node.js >= 20.0.0 (frontend)
- Python 3.10+ (backend)
- PostgreSQL 12+ (database)
- Git checkout on branch `114-pwa-push-notifications`

## Setup Steps

### 1. Install New Dependencies

**Backend** — add pywebpush for Web Push delivery:
```bash
pip install pywebpush>=2.0.0
```

**Frontend** — add PWA plugin:
```bash
cd frontend
npm install --save-dev vite-plugin-pwa
```

### 2. Generate VAPID Keys

VAPID keys are required for the Web Push protocol. Generate them once:

```bash
npx web-push generate-vapid-keys
```

Add the output to your `.env` file:

```bash
VAPID_PUBLIC_KEY=BEl62iUY...your-public-key...
VAPID_PRIVATE_KEY=xYz123...your-private-key...
VAPID_SUBJECT=mailto:admin@shuttersense.ai
```

### 3. Run Database Migration

After the migration files are created:

```bash
cd backend
alembic upgrade head
```

This creates the `push_subscriptions` and `notifications` tables.

### 4. Start Development Servers

**Backend** (from project root):
```bash
uvicorn backend.src.main:app --reload --port 8000
```

**Frontend** (from frontend directory):
```bash
cd frontend
npm run dev
```

### 5. Test PWA Installation

1. Open `https://localhost:3000` in Chrome (HTTPS required for service workers in production; localhost is exempt in dev)
2. Open DevTools → Application → Service Workers → verify registered
3. Open DevTools → Application → Manifest → verify manifest loads
4. Look for the install indicator in the browser URL bar

### 6. Test Push Notifications

1. Log in to ShutterSense
2. Navigate to Settings → Notifications tab
3. Click "Enable Notifications"
4. Grant browser notification permission when prompted
5. Use the test endpoint (dev only) to send a test push:

```bash
curl -X POST http://localhost:8000/api/notifications/test \
  -H "Content-Type: application/json" \
  -H "Cookie: session=<your-session-cookie>" \
  -d '{"title": "Test", "body": "Hello from ShutterSense!"}'
```

### 7. Test Notification Preferences

1. Click the user avatar in the top bar → "View Profile"
2. Scroll to the Notification Preferences section
3. Toggle individual categories on/off
4. Verify changes persist across page refreshes
5. Verify changes apply on different devices (same account)

## Key Files (New)

### Backend

| File | Purpose |
|------|---------|
| `backend/src/models/push_subscription.py` | PushSubscription ORM model |
| `backend/src/models/notification.py` | Notification ORM model |
| `backend/src/schemas/notifications.py` | Pydantic request/response schemas |
| `backend/src/services/notification_service.py` | Notification creation and push delivery |
| `backend/src/services/push_subscription_service.py` | Subscription CRUD and cleanup |
| `backend/src/api/notifications.py` | API router for all notification endpoints |
| `backend/src/db/migrations/versions/NNN_create_notification_tables.py` | Database migration |

### Frontend

| File | Purpose |
|------|---------|
| `frontend/src/custom-sw.ts` | Custom service worker additions (push handler, click handler) |
| `frontend/src/hooks/useNotifications.ts` | Notification history, unread count, mark-as-read |
| `frontend/src/hooks/useNotificationPreferences.ts` | Preferences CRUD hook |
| `frontend/src/hooks/usePushSubscription.ts` | Push subscription lifecycle (subscribe/unsubscribe) |
| `frontend/src/components/profile/NotificationPreferences.tsx` | Notification preferences section on Profile page |
| `frontend/src/components/notifications/NotificationPanel.tsx` | Dropdown panel from bell icon |
| `frontend/src/services/notifications.ts` | API client for notification endpoints |

### Modified Files

| File | Change |
|------|--------|
| `frontend/vite.config.ts` | Add `vite-plugin-pwa` configuration |
| `frontend/index.html` | Add PWA meta tags (theme-color, apple-mobile-web-app-capable) |
| `frontend/src/components/layout/TopHeader.tsx` | Replace static bell badge with dynamic unread count + panel |
| `frontend/src/pages/ProfilePage.tsx` | Add notification preferences section |
| `backend/src/config/settings.py` | Add VAPID environment variables |
| `backend/src/models/__init__.py` | Register new models |
| `backend/src/services/guid.py` | Register `sub_` and `ntf_` GUID prefixes |
| `backend/src/services/job_coordinator_service.py` | Add notification triggers in `fail_job()` and `complete_job()` |
| `backend/src/services/agent_service.py` | Add notification triggers in status change methods |
| `backend/src/main.py` | Register notification router and dead agent background task |

## Testing

### Backend Tests

```bash
# Run notification service tests
python -m pytest backend/tests/unit/test_notification_service.py -v

# Run push subscription tests
python -m pytest backend/tests/unit/test_push_subscription_service.py -v

# Run notification API tests
python -m pytest backend/tests/unit/test_notifications_api.py -v
```

### Frontend Tests

```bash
cd frontend

# Run notification component tests
npx vitest run src/hooks/useNotifications.test.ts
npx vitest run src/components/notifications/NotificationPanel.test.tsx
npx vitest run src/components/profile/NotificationPreferences.test.tsx
```

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VAPID_PUBLIC_KEY` | Yes | — | Web Push VAPID public key (Base64url) |
| `VAPID_PRIVATE_KEY` | Yes | — | Web Push VAPID private key (Base64url) |
| `VAPID_SUBJECT` | Yes | — | VAPID subject (mailto: or https: URL) |

## Troubleshooting

### Push notifications not appearing

1. Check DevTools → Application → Service Workers → verify active
2. Check browser notification permission: `Notification.permission` should be `"granted"`
3. Check server logs for push delivery errors
4. Verify VAPID keys are configured in `.env`

### PWA not installable

1. Check DevTools → Application → Manifest → verify no errors
2. Ensure HTTPS (required for production; localhost exempt in dev)
3. Check that service worker registered successfully
4. Verify icons exist in `public/icons/` at required sizes

### iOS notifications not working

1. PWA must be installed to home screen (not just opened in Safari)
2. iOS 16.4+ required
3. Only works in Safari (not Chrome/Firefox on iOS)
4. User must grant permission after PWA is installed
