# Notifications Guide

ShutterSense supports both in-app notifications and Web Push notifications for keeping users informed about job completions, agent status changes, and event deadlines.

## Overview

| Type | Mechanism | Requires |
|------|-----------|----------|
| In-app | Polling + bell icon | Nothing (always available) |
| Web Push | Service Worker + Push API | VAPID keys + HTTPS |

## In-App Notifications

In-app notifications appear in the notification bell in the top header. They include:

- **Job completed** - Analysis job finished successfully
- **Job failed** - Analysis job encountered an error
- **Agent online** - An agent connected to the server
- **Agent pool offline** - All agents are offline
- **Deadline approaching** - Event deadline is within the configured reminder window

### Notification Preferences

Users can configure notification preferences per category:

1. Navigate to **Notifications** (click the bell icon, then "View all")
2. Click **Preferences**
3. Toggle categories on/off for in-app and push independently

## Web Push Notifications

Push notifications are delivered even when the browser is closed (on supported platforms).

### Prerequisites

- HTTPS (required by the Web Push standard)
- VAPID keys configured on the server
- User grants notification permission in the browser

### VAPID Key Generation

Generate VAPID (Voluntary Application Server Identification) keys:

```bash
# Option A: Using py-vapid
pip install py-vapid
python3 -c "
from py_vapid import Vapid
v = Vapid()
v.generate_keys()
print('VAPID_PUBLIC_KEY=' + v.public_key)
print('VAPID_PRIVATE_KEY=' + v.private_key)
"

# Option B: Using openssl
openssl ecparam -genkey -name prime256v1 -out vapid_private.pem
openssl ec -in vapid_private.pem -pubout -out vapid_public.pem
# Then base64url-encode the keys
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `VAPID_PUBLIC_KEY` | Base64url-encoded ECDSA public key | Yes (for push) |
| `VAPID_PRIVATE_KEY` | Base64url-encoded ECDSA private key | Yes (for push) |
| `VAPID_SUBJECT` | Contact URI (`mailto:` or `https:`) | Yes (for push) |

Example:
```bash
export VAPID_PUBLIC_KEY="BNbx..."
export VAPID_PRIVATE_KEY="abc..."
export VAPID_SUBJECT="mailto:admin@example.com"
```

### Push Subscription Flow

1. User visits the app (must be served over HTTPS)
2. Frontend checks if push is supported and VAPID public key is available
3. User clicks "Enable push notifications" in the notification preferences
4. Browser prompts for notification permission
5. If granted, browser creates a push subscription
6. Frontend sends subscription to `POST /api/notifications/push/subscribe`
7. Server stores the subscription for the user
8. When events occur, server sends push messages to all subscribed endpoints

### PWA Installation

For the best push notification experience, install ShutterSense as a PWA:

**Desktop (Chrome/Edge):**
1. Click the install icon in the address bar
2. Click "Install"

**Mobile (iOS Safari):**
1. Tap the Share button
2. Tap "Add to Home Screen"

**Mobile (Android Chrome):**
1. Tap the three-dot menu
2. Tap "Install app" or "Add to Home Screen"

### Service Worker

The service worker (`frontend/src/sw.ts`) handles:

- Receiving push events from the server
- Displaying native notifications
- Handling notification click actions (navigating to relevant pages)
- Badge count updates (where supported)

## Notification Types

| Type | In-App | Push | Trigger |
|------|--------|------|---------|
| `job_completed` | Yes | Yes | Analysis job completes |
| `job_failed` | Yes | Yes | Analysis job fails |
| `agent_online` | Yes | No | Agent connects |
| `pool_offline` | Yes | Yes | All agents go offline |
| `deadline_approaching` | Yes | Yes | Event deadline within reminder window |

## Troubleshooting

### Push notifications not working

1. **Check HTTPS** - Push notifications require HTTPS in production
2. **Check VAPID keys** - Verify all three VAPID environment variables are set
3. **Check permissions** - Browser must have notification permission granted
4. **Check subscription** - Visit Notifications page and re-enable push
5. **Check service worker** - Open DevTools > Application > Service Workers

### Notifications not appearing

1. **Check preferences** - Ensure the notification category is enabled
2. **Check "Do Not Disturb"** - OS-level DND blocks push notifications
3. **Check browser** - Some browsers limit notification frequency

### Badge count not updating

The Badging API (`navigator.setAppBadge()`) is supported in:
- Chrome 81+ (desktop and Android)
- Edge 81+
- Safari 17+ (with limitations)

Firefox does not support the Badging API.
