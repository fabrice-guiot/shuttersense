# Plan: Push Notification Device Registration & Debugging Improvements (2026-02-21)

## Context

Push notifications work inconsistently across devices. Key problems observed:
- Only the first registered device receives a confirmation push; subsequent devices get nothing
- No way to test if a registered device is actually receiving notifications
- Device names show unhelpful values like "Not a brand on Android"
- No ability to rename devices to friendly names
- macOS PWA receives badge updates but no OS toast notifications
- The "Add this device" banner appears after first enablement due to a race condition
- Possible: PWA updates may invalidate push subscriptions silently

Related spec: `specs/114-pwa-push-notifications/`

## Changes

### 1. Confirmation push on every device registration (not just first)

**Problem**: Welcome notification fires only when `is_first` (no existing subscriptions). Second+ devices register silently — user has no way to confirm the registration worked.

**Fix**: Send a targeted confirmation push to the *newly registered device only* on every subscription, not just the first. Change the welcome notification to a device-specific confirmation push.

**Backend** (`backend/src/api/notifications.py:96-161`):
- Remove the `is_first` gate around the push delivery
- Keep `is_first` only for creating the in-app welcome notification record (first device still gets the history entry)
- After `create_subscription()`, send a targeted push to *only that subscription* (not `deliver_push` which hits all devices). Add a `deliver_push_to_subscription()` method that sends to a single subscription.
- Payload: "Device registered — {device_name} is now receiving notifications"

**Backend** (`backend/src/services/notification_service.py`):
- Add `deliver_push_to_subscription(subscription, payload)` — wraps `_send_push()` for a single subscription with logging and error handling. Returns success boolean.

### 2. Test push button per device

**Problem**: No way to verify a registered device can actually receive notifications without waiting for a real event.

**Backend** (`backend/src/api/notifications.py`):
- Add `POST /notifications/subscribe/{guid}/test` endpoint
- Sends a test push to that specific subscription only (via `deliver_push_to_subscription`)
- Payload: "Test notification — Push is working on {device_name}"
- Rate limit: 5/minute (prevent abuse)
- Returns `{ "success": true/false, "error": "..." }` so the UI can show delivery result

**Frontend** (`frontend/src/services/notifications.ts`):
- Add `testDevice(guid: string)` API client method

**Frontend** (`frontend/src/hooks/usePushSubscription.ts`):
- Add `testDevice(guid)` function exposed from hook
- Track `testingGuid` state for loading indicator

**Frontend** (`frontend/src/components/profile/NotificationPreferences.tsx`):
- Add a "Send test" button (ghost variant, Bell icon) next to the delete button per device
- Show loading spinner while test in progress
- Toast success/error based on result

### 3. Device rename capability

**Problem**: Device names are auto-detected and often unhelpful ("Not a brand on Android"). No way to assign friendly names.

**Backend** (`backend/src/api/notifications.py`):
- Add `PATCH /notifications/subscribe/{guid}` endpoint
- Accepts `{ "device_name": "My Pixel 8" }` (validated: 1-100 chars, trimmed)
- Returns updated `PushSubscriptionResponse`

**Backend** (`backend/src/services/push_subscription_service.py`):
- Add `rename_subscription(user_id, team_id, guid, device_name)` method

**Backend** (`backend/src/schemas/notifications.py`):
- Add `PushSubscriptionUpdate` schema with optional `device_name` field

**Frontend** (`frontend/src/services/notifications.ts`):
- Add `renameDevice(guid, deviceName)` API client method

**Frontend** (`frontend/src/hooks/usePushSubscription.ts`):
- Add `renameDevice(guid, name)` function
- After rename, refresh subscription list

**Frontend** (`frontend/src/components/profile/NotificationPreferences.tsx`):
- Add `Pencil` icon button next to device name
- Clicking opens a Radix Dialog with text input pre-filled with current name, Save/Cancel buttons
- Show toast on success

### 4. Improve device name detection

**Problem**: The `detectBrowserName()` regex `!/not[\s._\-;)\/]?a/i` doesn't catch all "Not a brand" variations (e.g., "Not/A)Brand", "Not_A Brand" with spaces).

**Frontend** (`frontend/src/hooks/usePushSubscription.ts:107-108`):
- Strengthen the regex to catch more filler brand patterns: `/not[^a-z]*a[^a-z]*brand/i`
- This catches: "Not A;Brand", "Not/A)Brand", "Not_A Brand", "Not.A" followed by "Brand", etc.

### 5. Investigate macOS toast behavior (documentation / SW change)

**Problem**: macOS PWA updates the badge but doesn't show OS toast notifications. The service worker calls `self.registration.showNotification()` which *should* produce a toast on macOS.

**Root cause hypothesis**: macOS may suppress toast notifications when the PWA window is focused (showing badges only). This is platform behavior, not a bug we can fix. However, we should ensure:

**Frontend** (`frontend/src/sw.ts:106-120`):
- Add `renotify: true` to notification options when a `tag` is present (forces re-display even for same-tag notifications)
- Add `requireInteraction: false` explicitly (macOS default)
- These are defensive measures; macOS toast behavior is controlled by OS notification settings

**No backend changes needed** — this is entirely a service worker / OS settings issue.

### 6. Fix race condition: "Add this device" banner shown after first enablement

**Problem**: When re-enabling notifications (toggle on), `handleMasterToggle(true)` calls `subscribe()` then `updatePreferences({ enabled: true })` sequentially. But `subscribe()` calls `refreshStatus()` at the end, which fetches `notifications_enabled` from the server — and at that point the preferences haven't been updated yet (`enabled` is still `false`). So:
1. `subscribe()` registers the device, but `refreshStatus()` sees `notifications_enabled=false`
2. `updatePreferences({ enabled: true })` sets `enabled=true`, the UI re-renders with `isEnabled=true`
3. The device list section appears but `currentDeviceEndpoint` is stale (resolved during step 1 when `enabled` was false), so the "Add this device" banner shows even though the device is already registered.

**Fix** (`frontend/src/components/profile/NotificationPreferences.tsx`):
- In `handleMasterToggle(true)`: swap the order — call `updatePreferences({ enabled: true })` first, then `subscribe()`. This way, when `subscribe()` calls `refreshStatus()`, the server already has `enabled=true` and `currentDeviceEndpoint` resolves correctly.
- Belt-and-suspenders: add a final `refreshStatus()` call after both operations complete.

## Files

### Backend
- `backend/src/api/notifications.py` — new endpoints (test, rename), confirmation push on every registration
- `backend/src/services/notification_service.py` — `deliver_push_to_subscription()` method
- `backend/src/services/push_subscription_service.py` — `rename_subscription()` method
- `backend/src/schemas/notifications.py` — `PushSubscriptionUpdate` schema, test push response schema

### Frontend
- `frontend/src/hooks/usePushSubscription.ts` — improved device detection, `testDevice()`, `renameDevice()`
- `frontend/src/components/profile/NotificationPreferences.tsx` — test button, rename dialog, toggle race fix
- `frontend/src/services/notifications.ts` — `testDevice()`, `renameDevice()` API methods
- `frontend/src/contracts/api/notification-api.ts` — new type definitions
- `frontend/src/sw.ts` — defensive notification options (renotify, requireInteraction)

## Verification

1. **Race condition fix**: Toggle notifications off then on → device list shows immediately without "Add this device" banner
2. **Confirmation push**: Register a new device → should receive an OS notification immediately
3. **Test push**: Click "Send test" on any device → that device receives a test notification
4. **Rename**: Click pencil icon → dialog opens → edit name → Save → name persists across page reloads
5. **Device detection**: New registrations should show "Chrome on Android" instead of "Not a brand on Android"
6. **Backend tests**: `venv/bin/python -m pytest backend/tests/unit/ -k notification -v`
7. **Frontend types**: `cd frontend && npx tsc --noEmit`
