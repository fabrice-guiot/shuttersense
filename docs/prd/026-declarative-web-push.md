# PRD: Declarative Web Push Support

**Issue**: TBD
**Status**: Draft
**Created**: 2026-02-22
**Last Updated**: 2026-02-22
**Related Documents**:
- [023-pwa-push-notifications.md](./023-pwa-push-notifications.md) (Original PWA & Push Notifications)
- [025-pwa-health-diagnostics.md](./025-pwa-health-diagnostics.md) (PWA Health Diagnostics)
- [PWA Installation & Notifications Guide](../pwa-installation-and-notifications.md)

---

## Executive Summary

This PRD defines the adoption of **Declarative Web Push** — a Safari-originated standard (shipped in Safari 18.4+, available in Safari 26 / iOS 26) that enables push notifications to be delivered and displayed **without Service Worker JavaScript execution**. The browser parses a standardized JSON payload and renders the notification directly, removing the dependency on an active, healthy Service Worker.

### Why Now

Push notifications are the primary reason users install the ShutterSense PWA. On iOS — where Safari is the only engine that matters — the biggest reliability problem is **silent notification loss due to Service Worker eviction**. Safari's Intelligent Tracking Prevention (ITP) can evict Service Workers for sites not visited within ~7 days. When this happens, traditional push subscriptions break silently: the push message arrives at the device, but with no Service Worker to handle it, the notification is lost and the user never knows.

Declarative Web Push solves this by design. Push subscriptions are decoupled from the Service Worker lifecycle. Even when ITP removes the SW, the subscription persists and the browser displays notifications directly from the JSON payload. This is the single most impactful improvement available for iOS push reliability today.

Safari 26 (iOS 26) ships Declarative Web Push as a stable, default-enabled feature — no flags required. With iOS 26 adoption expected to reach the majority of iOS users by late 2026, implementing support now ensures ShutterSense push notifications work reliably across the growing Safari/iOS user base.

### Key Design Decisions

1. **Declarative-first, backward-compatible** — All push payloads are sent in the Declarative Web Push JSON format with `Content-Type: application/notification+json`. On Safari 18.4+, the browser handles display natively. On Chromium browsers (Chrome, Edge), the payload arrives at the existing Service Worker `push` event handler, which parses the same JSON and calls `showNotification()` as before.
2. **No separate subscription flow** — The existing `PushManager.subscribe()` via Service Worker registration continues to work. Declarative Web Push does not require `window.pushManager` — it works with existing subscriptions. We adopt the payload format change only, not the alternative subscription API.
3. **Immutable notifications by default** — Notifications are not marked `mutable`, so the Service Worker is never needed for display. This maximizes ITP resilience.
4. **Same VAPID keys** — No changes to key generation, storage, or authentication.

### Primary Goals

1. Eliminate silent notification loss on Safari/iOS caused by Service Worker eviction
2. Improve push delivery reliability on all Safari platforms (iOS, iPadOS, macOS)
3. Maintain full backward compatibility with Chromium-based browsers

### Secondary Goals

4. Reduce power consumption on Safari (no JS execution for notification display)
5. Simplify the push failure surface (fewer failure modes = easier debugging)
6. Position for future W3C standardization adoption by other browsers

### Non-Goals (v1)

1. Adopting `window.pushManager` subscription API (requires dropping SW-based subscription for Safari users)
2. Mutable notifications (SW-mediated transformation of declarative payloads)
3. End-to-end encryption with client-side decryption (requires mutable notifications)
4. Notification action buttons (supported by the spec but not used in ShutterSense today)
5. Per-browser payload routing (sending different formats to Safari vs Chrome)

---

## Background

### Current Push Architecture

```text
Server                          Push Service              Client
  │                                │                        │
  │  webpush(payload_json,         │                        │
  │    vapid_claims, headers)      │                        │
  │  ─────────────────────────────>│                        │
  │  Content-Type: application/json│                        │
  │  Urgency: high                 │                        │
  │  TTL: 86400                    │                        │
  │                                │   Push message         │
  │                                │  ──────────────────>   │
  │                                │                        │
  │                                │          SW push event │
  │                                │          event.data.json()
  │                                │          showNotification()
```

**Current payload format** (`notification_service.py:1500-1512`):
```json
{
  "title": "Job Failed",
  "body": "PhotoStats analysis for 'Wedding' failed: timeout",
  "icon": "/icons/icon-192x192.png",
  "badge": "/icons/badge-72x72.png",
  "data": {
    "url": "/collections/col_01hgw.../results",
    "category": "job_failure",
    "notification_guid": "ntf_01hgw..."
  }
}
```

**Current Service Worker handler** (`sw.ts:92-125`):
```typescript
self.addEventListener('push', (event: PushEvent) => {
  const payload = event.data.json()
  self.registration.showNotification(payload.title, {
    body: payload.body,
    icon: payload.icon || '/icons/icon-192x192.png',
    badge: payload.badge || '/icons/badge-72x72.png',
    tag: payload.tag,
    renotify: !!payload.tag,
    data: payload.data,
  })
})
```

**Current delivery** (`notification_service.py:637-643`):
```python
webpush(
    subscription_info=subscription_info,
    data=payload_json,
    vapid_private_key=self.vapid_private_key,
    vapid_claims=self.vapid_claims,
    ttl=86400,
    headers={"Urgency": "high"},
)
```

### Problem: ITP Service Worker Eviction

Safari's Intelligent Tracking Prevention (ITP) aggressively manages website data for privacy:

1. User installs ShutterSense PWA on iOS (Add to Home Screen)
2. User grants push notification permission
3. Push subscription is created and stored on server
4. User doesn't open the PWA for 7+ days
5. **ITP evicts the Service Worker registration**
6. Server sends push message → push service delivers to device
7. **No Service Worker exists to handle the `push` event**
8. **Notification is silently lost** — user never sees it
9. User is unaware they missed critical alerts (job failures, agent offline)

This is not a theoretical risk — it is the primary failure mode for web push on iOS/Safari. The ShutterSense PWA is particularly vulnerable because users may go days between analysis runs, meaning the PWA is exactly the type of "infrequently visited" site that ITP targets.

### How Declarative Web Push Fixes This

```text
Server                          Push Service              Client
  │                                │                        │
  │  webpush(payload_json,         │                        │
  │    vapid_claims, headers)      │                        │
  │  ─────────────────────────────>│                        │
  │  Content-Type:                 │                        │
  │    application/notification+json                        │
  │  Urgency: high                 │                        │
  │  TTL: 86400                    │                        │
  │                                │   Push message         │
  │                                │  ──────────────────>   │
  │                                │                        │
  │                                │   Safari 18.4+:        │
  │                                │   Parse JSON directly  │
  │                                │   Display notification │
  │                                │   (no SW needed)       │
  │                                │                        │
  │                                │   Chrome/Edge:         │
  │                                │   SW push event fires  │
  │                                │   (backward compat)    │
```

Key mechanism: The `Content-Type: application/notification+json` header tells Safari to handle the notification declaratively. Chromium browsers that don't recognize this Content-Type simply deliver the payload to the Service Worker's `push` event as before.

### Self-Healing Lifecycle After SW Eviction

A critical property of Declarative Web Push is that the notification-tap-to-open flow **automatically restores** the Service Worker, making the system self-healing:

1. ITP evicts the Service Worker (user hasn't opened the PWA in 7+ days)
2. Push arrives → browser displays notification from JSON (no SW needed)
3. User taps notification → Safari opens the `navigate` URL natively (no SW `notificationclick` handler needed)
4. PWA loads → `main.tsx` runs `initServiceWorkerLifecycle()` → vite-plugin-pwa re-registers the SW
5. SW installs, precaches assets, activates — **fully restored**
6. Push subscription was never lost (decoupled from SW in declarative mode)

Compare this to the **death spiral** without Declarative Web Push: the notification is silently lost (step 2 fails), the user never opens the app, the SW stays evicted, and all subsequent notifications are also lost indefinitely.

**Expected behavior on first load after SW restoration:** The precache is empty when the SW is first re-registered, so the initial page load fetches all assets from the network (slightly slower than a cache hit). The SW precaches assets during installation, so subsequent loads return to full cache speed. This is a minor, one-time UX blip that does not require mitigation.

---

## Technical Specification

### Declarative Web Push Payload Format

The push payload MUST follow the Declarative Web Push JSON schema (RFC 8030 magic key):

```json
{
  "web_push": 8030,
  "notification": {
    "title": "Job Failed",
    "body": "PhotoStats analysis for 'Wedding' failed: timeout",
    "navigate": "/collections/col_01hgw.../results",
    "tag": "job_failure_job_01hgw...",
    "silent": false,
    "data": {
      "category": "job_failure",
      "notification_guid": "ntf_01hgw..."
    }
  },
  "app_badge": 1
}
```

**Required fields:**
| Field | Type | Description |
|-------|------|-------------|
| `web_push` | `integer` | Must be `8030` (RFC 8030 identifier) |
| `notification.title` | `string` | Notification heading |
| `notification.navigate` | `string` | URL to open on click (relative or absolute, must be same-origin) |

**Optional fields:**
| Field | Type | Description |
|-------|------|-------------|
| `notification.body` | `string` | Notification body text |
| `notification.tag` | `string` | Notification grouping/replacement key |
| `notification.silent` | `boolean` | Suppress sound/vibration (default `false`) |
| `notification.lang` | `string` | Language tag |
| `notification.dir` | `string` | Text direction (`"ltr"` or `"rtl"`) |
| `notification.data` | `object` | Arbitrary data passed to click handler |
| `app_badge` | `integer` | Home screen badge count |

### Content-Type Header

The pywebpush `headers` parameter MUST include:

```python
headers={
    "Urgency": "high",
    "Content-Type": "application/notification+json",
}
```

This is the mechanism that triggers declarative handling on Safari 18.4+. On Chromium browsers, this Content-Type is not recognized as special, so the payload is delivered to the Service Worker `push` event handler as before.

> **Note on pywebpush:** The `webpush()` function sets `Content-Type` to `application/octet-stream` by default (for the encrypted payload). The actual Content-Type of the *decrypted* payload is communicated inside the encrypted envelope via the `Content-Encoding` mechanism defined in RFC 8291. We need to verify whether pywebpush supports passing a Content-Type for the inner payload or whether we need to set it at the HTTP level. See [Implementation Phase 1](#phase-1-payload-format-migration) for the investigation task.

### Payload Mapping

Current payload fields map to Declarative Web Push as follows:

| Current Field | Declarative Field | Notes |
|---------------|-------------------|-------|
| `title` | `notification.title` | Direct mapping |
| `body` | `notification.body` | Direct mapping |
| `icon` | *(not in spec)* | Safari uses the PWA icon automatically; Chromium SW handler provides fallback |
| `badge` | *(not in spec)* | Safari uses the PWA badge; `app_badge` integer replaces this |
| `tag` | `notification.tag` | Direct mapping |
| `data.url` | `notification.navigate` | Promoted to top-level notification field |
| `data.*` | `notification.data.*` | Nested under `notification.data` |

### Service Worker Backward Compatibility

The Service Worker `push` event handler MUST be updated to parse both the declarative format and the legacy format. On Chromium browsers, the declarative JSON arrives as the `push` event data:

```typescript
self.addEventListener('push', (event: PushEvent) => {
  if (!event.data) return

  let payload: Record<string, unknown>
  try {
    payload = event.data.json()
  } catch {
    return
  }

  // Declarative format: extract from notification object
  let title: string
  let body: string
  let tag: string | undefined
  let data: Record<string, unknown> | undefined
  let navigate: string | undefined

  if (payload.web_push === 8030 && payload.notification) {
    const notif = payload.notification as Record<string, unknown>
    title = (notif.title as string) || 'Notification'
    body = (notif.body as string) || ''
    tag = notif.tag as string | undefined
    data = notif.data as Record<string, unknown> | undefined
    navigate = notif.navigate as string | undefined
    // Merge navigate into data for notificationclick handler
    if (navigate && data) {
      data.url = navigate
    } else if (navigate) {
      data = { url: navigate }
    }
  } else {
    // Legacy format (existing behavior)
    title = (payload.title as string) || 'Notification'
    body = (payload.body as string) || ''
    tag = payload.tag as string | undefined
    data = payload.data as Record<string, unknown> | undefined
  }

  const options: NotificationOptions & { renotify?: boolean } = {
    body,
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    tag,
    renotify: !!tag,
    requireInteraction: false,
    data,
  }

  // Extract app_badge from declarative payload top level
  const appBadge =
    payload.web_push === 8030
      ? (payload.app_badge as number | undefined)
      : undefined

  event.waitUntil(
    Promise.all([
      self.registration.showNotification(title, options),
      appBadge !== undefined
        ? self.navigator.setAppBadge?.(appBadge)
        : self.navigator.setAppBadge?.(),
    ])
  )
})
```

The existing `notificationclick` handler (`sw.ts:131-167`) requires no changes — it already reads `event.notification.data?.url` and navigates to it. The declarative format's `navigate` field is mapped to `data.url` in the push handler above.

---

## Functional Requirements

### FR-01: Declarative Payload Format

The backend MUST construct push payloads in the Declarative Web Push JSON format with the `web_push: 8030` magic key and the `notification` object.

### FR-02: Content-Type Header

The backend MUST send push messages with `Content-Type: application/notification+json` (or ensure the equivalent inner Content-Type reaches Safari's parser). If pywebpush does not support this directly, a wrapper or library patch is required.

### FR-03: Backward-Compatible Service Worker

The Service Worker `push` event handler MUST parse both the declarative format (`web_push: 8030`) and the legacy format (top-level `title`/`body`). This ensures:
- Chromium browsers continue to work (they receive the declarative JSON via the SW)
- Any in-flight legacy push messages from before the migration are still handled

### FR-04: Navigate URL

All push payloads MUST include `notification.navigate` with the same-origin URL that the notification should open when clicked. This replaces the `data.url` field in the legacy format.

On Safari, the browser handles click-to-navigate automatically from this field. On Chromium, the SW `notificationclick` handler continues to use `data.url` (mapped from `navigate` in the push handler).

### FR-05: App Badge

Push payloads SHOULD include `app_badge` with the user's current unread notification count. On Safari, this sets the Home Screen badge declaratively. On Chromium, the SW continues to use `navigator.setAppBadge()`.

### FR-06: Tag-Based Notification Replacement

Push payloads MUST include `notification.tag` with a stable identifier per notification source (e.g., `job_failure_{job_guid}`) to enable notification replacement. This prevents notification spam when multiple pushes fire for the same entity.

### FR-07: Test Notification

The existing test notification endpoint (`POST /api/notifications/push/test/{guid}`) MUST send payloads in the declarative format, so users can verify that declarative push works on their device.

### FR-08: Graceful Fallback for Icon/Badge

The declarative format does not include `icon` or `badge` image URLs — Safari uses the PWA's manifest icons automatically. The Service Worker handler MUST continue to provide fallback `icon` and `badge` values for Chromium browsers where the SW processes the notification.

---

## Non-Functional Requirements

### NFR-01: Zero Subscription Disruption

Existing push subscriptions MUST continue to work without re-registration. The change is payload-format-only — no subscription migration is required.

### NFR-02: No Database Changes

This feature requires no new database tables, columns, or migrations. The `PushSubscription` model stores endpoint and keys, which are unchanged.

### NFR-03: pywebpush Compatibility

The implementation MUST work with pywebpush 2.0+. If a pywebpush upgrade is needed for Content-Type support, it MUST be verified against all existing push functionality before deployment.

### NFR-04: Rollback Safety

If declarative push causes unexpected issues on any platform, the backend MUST be able to revert to legacy format by changing only the payload construction code. No client-side changes should be needed for rollback (the SW handles both formats).

---

## Implementation Plan

### Phase 1: Payload Format Migration (Backend)

**Scope:** Change the push payload format in `notification_service.py` and verify Content-Type handling.

**Tasks:**
1. **Investigate pywebpush Content-Type support.** Determine how pywebpush handles the Content-Type of the encrypted payload. The `headers` parameter may set HTTP-level headers but the Content-Type for the inner (decrypted) payload may need different handling. Read pywebpush source code and RFC 8291 content encoding to determine the correct approach.
2. **Update `send_notification()` payload construction** (`notification_service.py:1500-1512`). Transform the payload from the current flat format to the Declarative Web Push JSON format with `web_push: 8030` and nested `notification` object.
3. **Update `_send_push()` headers** (`notification_service.py:637-643`). Add `Content-Type: application/notification+json` to the headers dict if supported by pywebpush.
4. **Update test notification payload** in the test push endpoint to use the declarative format.
5. **Update backend unit tests** to verify the new payload format.

**Key file:** `backend/src/services/notification_service.py`

### Phase 2: Service Worker Update (Frontend)

**Scope:** Update the SW push event handler to parse both formats.

**Tasks:**
1. **Update the `push` event handler** in `sw.ts` to detect `web_push: 8030` and extract fields from the `notification` object, falling back to the legacy flat format.
2. **Preserve the `notificationclick` handler** — map `notification.navigate` to `data.url` so the existing click handler works unchanged.
3. **Update app badge handling** — read `app_badge` from the declarative payload for the Badging API call.
4. **Test with Chromium browsers** to verify the SW correctly handles the declarative JSON.

**Key file:** `frontend/src/sw.ts`

### Phase 3: End-to-End Verification

**Scope:** Test the full push pipeline across platforms.

**Tasks:**
1. **Safari on macOS** — Verify declarative push works in both browser and "Add to Dock" web app modes.
2. **Safari on iOS** — Verify declarative push works in the installed PWA (Home Screen). Specifically test the ITP eviction scenario:
   - Install PWA, enable push
   - Don't open for 7+ days (or manually clear the SW registration via DevTools)
   - Send a push notification
   - Verify it is displayed by the browser without a SW
3. **Chrome on macOS/Windows** — Verify the SW correctly handles the declarative JSON and displays notifications as before.
4. **Edge on macOS** — Verify compatibility with the attribution flag workflow.
5. **Test notification flow** — Verify the "Send test notification" button works across all platforms.

### Phase 4: Documentation Update

**Scope:** Update operational documentation.

**Tasks:**
1. Update `docs/pwa-installation-and-notifications.md` — Document the declarative push change, remove the "Future Improvements" section for Declarative Web Push (now implemented), update the Safari section.
2. Update `docs/notifications.md` — Note the payload format change for anyone inspecting push payloads in DevTools.
3. Update the PWA Health Diagnostics PRD (025) — Diagnostics panel should detect Safari 18.4+ and show "Declarative Web Push: active" as a positive signal.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| pywebpush doesn't support `application/notification+json` Content-Type for inner payload | Medium | High | Investigate before committing. If unsupported, either contribute a PR to pywebpush, use a fork, or set the header at the HTTP level if that's how Safari detects it. |
| Chromium browsers misinterpret the new Content-Type | Low | High | Chromium ignores unknown inner Content-Types and delivers to SW as before. Verify in Phase 3. |
| Safari rejects payloads with extra fields (e.g., `notification.data`) | Low | Medium | The spec explicitly allows arbitrary fields in `notification.data`. Test in Phase 3. |
| `notification.navigate` requires absolute URL on Safari | Low | Low | Convert relative URLs to absolute using the app's origin before sending. |
| ITP behavior changes in future Safari versions | Low | Low | Declarative push is designed to be ITP-resilient by architecture, not by workaround. |

---

## Browser Support Matrix

| Browser | Declarative Handling | SW Fallback | Notes |
|---------|---------------------|-------------|-------|
| Safari 18.4+ (iOS 18.4+) | Native | Not needed | ITP-resilient; PWA Home Screen required |
| Safari 18.5+ (macOS 15.5+) | Native | Not needed | Also works in "Add to Dock" web apps |
| Safari 26 (iOS 26) | Native | Not needed | Stable, default-enabled |
| Chrome (all platforms) | No | Yes, via SW | SW parses same JSON, works identically |
| Edge (all platforms) | No | Yes, via SW | Same as Chrome; macOS still needs attribution flag |
| Firefox | No | Yes, via SW | Limited PWA support (Windows-only experimentally) |

**Tracking for future adoption:**
- Chrome: [Chromium Issue #382298314](https://issues.chromium.org/issues/382298314)
- Firefox: [Mozilla Bug #1935325](https://bugzilla.mozilla.org/show_bug.cgi?id=1935325)

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Push delivery success rate on Safari/iOS | Unknown (no visibility into silent failures) | >95% |
| Notification loss due to SW eviction | Occurs for users who don't open app for 7+ days | Zero |
| Push delivery regression on Chrome/Edge | Baseline | No change (0% regression) |
| Backend code change footprint | N/A | <50 lines changed in `notification_service.py` |

---

## References

- [WebKit Blog — Meet Declarative Web Push](https://webkit.org/blog/16535/meet-declarative-web-push/) — Definitive technical reference
- [WebKit Explainer — Declarative Web Push](https://github.com/WebKit/explainers/blob/main/DeclarativeWebPush/README.md) — Full JSON schema and specification
- [WWDC25 Session 235 — Learn more about Declarative Web Push](https://developer.apple.com/videos/play/wwdc2025/235/) — Apple's implementation guidance
- [WebKit Features in Safari 18.4](https://webkit.org/blog/16574/webkit-features-in-safari-18-4/) — iOS/iPadOS launch
- [WebKit Features in Safari 18.5](https://webkit.org/blog/16923/webkit-features-in-safari-18-5/) — macOS launch
- [W3C Push API Issue #360](https://github.com/w3c/push-api/issues/360) — Standardization discussion (closed September 2025)
- [RFC 8030 — Generic Event Delivery Using HTTP Push](https://www.rfc-editor.org/rfc/rfc8030) — The "8030" magic key origin
- [RFC 8291 — Message Encryption for Web Push](https://www.rfc-editor.org/rfc/rfc8291) — Payload encryption (unchanged)
- [Chromium Issue #382298314](https://issues.chromium.org/issues/382298314) — Chrome tracking
- [Mozilla Bug #1935325](https://bugzilla.mozilla.org/show_bug.cgi?id=1935325) — Firefox tracking
