# PRD: PWA Health Diagnostics

**Issue**: TBD
**Status**: Draft
**Created**: 2026-02-22
**Last Updated**: 2026-02-22
**Related Documents**:
- [023-pwa-push-notifications.md](./023-pwa-push-notifications.md) (PWA & Push Notifications)
- [PWA Installation & Notifications Guide](../pwa-installation-and-notifications.md) (Operational reference)
- [Design System](../../frontend/docs/design-system.md)

---

## Executive Summary

This PRD defines a **PWA Health Diagnostics** panel that surfaces the installation state, service worker health, cache integrity, and push notification readiness of the ShutterSense PWA — all in a single, self-service troubleshooting interface.

Real-world deployment experience has revealed that PWA issues are **silent and persistent**. Stale caches from early deployments prevent installation in secondary browsers indefinitely. Edge on macOS requires an experimental flag for push notifications to work at all. iOS requires Home Screen installation before push is even available. Users have no way to know *which* of these issues is affecting them without opening DevTools or reading documentation.

This feature replaces manual troubleshooting with **automated detection and actionable guidance**.

### Key Design Decisions

1. **Unified diagnostics panel** — PWA installation health and push notification health are presented together, not as separate features. They share root causes (service worker state, cache validity) and the user's goal is the same: "make the app work properly on my device."
2. **Frontend-only checks with one new backend endpoint** — All diagnostic checks run client-side using standard Web APIs (`ServiceWorkerRegistration`, `PushManager`, `Notification`, `navigator.permissions`, `CacheStorage`). One new backend endpoint provides server-side VAPID/push health status.
3. **Actionable, not informational** — Each check produces a pass/warn/fail status with a specific remediation action, not just a raw value. Platform-specific guidance is tailored to the detected browser and OS.
4. **Non-destructive with opt-in repair** — Diagnostics are read-only by default. Destructive actions (cache purge, service worker re-registration) require explicit user confirmation.

### Primary Goals

1. Enable users to self-diagnose PWA installation and notification problems without DevTools
2. Surface platform-specific issues proactively (Edge attribution flag, iOS install requirement, corporate MDM blocks)
3. Detect and offer remediation for stale cache states that prevent PWA installation or updates
4. Reduce support burden for PWA-related issues

### Secondary Goals

5. Provide a "test notification" flow integrated with diagnostics to verify the full push pipeline
6. Inform deployment decisions by surfacing cache/SW version information

### Non-Goals (v1)

1. Automated cache repair without user consent
2. Server-side push subscription health monitoring (separate future work, see [push subscription health](#future-push-subscription-health-monitoring))
3. Admin-facing dashboard of all users' PWA health
4. Safari Declarative Web Push support (separate feature, see [pwa-installation-and-notifications.md](../pwa-installation-and-notifications.md#3-declarative-web-push-support-safari-184))

---

## Background

### Problem Statement

PWA issues are **silent failures with long-lasting consequences**:

1. **Stale cache prevents installation.** If a browser visited the app before the service worker or manifest was correctly configured (e.g., during initial production deployment), it caches broken responses. The PWA install prompt never appears. The only fix is clearing all site data — but users don't know this is the problem. This was confirmed on ShutterSense production deployments where clearing cached data restored the ability to install the PWA from a secondary browser.

2. **Push notifications silently fail on Edge/macOS.** Edge on macOS requires `edge://flags/#enable-mac-pwas-notification-attribution` to be **Enabled** for PWA push notifications to work. The flag defaults to "Default" (disabled). Notifications are silently dropped with no error surfaced to the user or the application. This was the root cause of weeks of debugging on a production macOS device.

3. **Corporate MDM blocks Chrome notifications.** Managed macOS devices may have Chrome notifications disabled by system policy. The notification permission dialog never appears, or permission is silently denied. There is no indication in the app that this is a system-level block.

4. **iOS requires Home Screen installation.** Push notifications on iOS only work for installed PWAs, not browser tabs. Users who haven't installed the PWA see the notification UI but cannot enable push — the current error messaging doesn't explain why.

5. **Service worker version drift.** After deployments, some clients may run a stale service worker for extended periods if the update lifecycle fails (network errors during `registration.update()`, browser bugs). There is no visibility into which SW version is active.

### Current State

The existing `usePushSubscription` hook (`frontend/src/hooks/usePushSubscription.ts`) already performs several checks:

- `isSupported` — detects Push API availability
- `isIosNotInstalled` — detects iOS browser tab (not standalone PWA)
- `permissionState` — tracks `Notification.permission`
- Permission revocation detection via Permissions API
- Browser/platform detection (`detectBrowserName()`, `detectDeviceName()`)

However, these checks are:
- **Scattered** — embedded in the subscription hook, not surfaced as a diagnostic UI
- **Incomplete** — no service worker version check, no cache health check, no Edge flag detection, no manifest validation
- **Not actionable** — raw state values, no remediation guidance

### Strategic Context

Push notifications are the **primary reason** users install the ShutterSense PWA. If notifications don't work, the PWA provides minimal value over a browser tab. Every silent failure reduces trust and engagement. A diagnostics panel that proactively detects and explains issues transforms a frustrating debugging experience into a guided resolution flow.

---

## Goals

### Primary Goals

1. **Detect and display PWA installation state** — Is the app running as an installed PWA or in a browser tab? Which browser and platform? Is the manifest valid?

2. **Detect and display service worker health** — Is a service worker registered? Is it active? What version is it? Is it the latest version? Is an update waiting?

3. **Detect and display push notification readiness** — Is the Push API supported? Is notification permission granted? Is VAPID configured on the server? Is there an active push subscription? Can the server reach the push endpoint?

4. **Surface platform-specific issues with remediation** — Edge attribution flag, iOS install requirement, corporate notification blocks, Safari ITP service worker eviction.

5. **Detect stale cache states** — Report cache names, entry counts, and total size. Offer a "clear and reload" action when the cache appears stale or oversized.

### Secondary Goals

6. **Integrated test notification** — "Send test notification" button that validates the full pipeline (server → push service → service worker → OS notification).

7. **Deployment version visibility** — Show the app build version, service worker version, and whether they match.

---

## User Personas

| Persona | Context | Primary Need |
|---------|---------|-------------|
| **Photographer (primary user)** | Uses PWA on personal macOS/iOS device | "Why aren't my notifications working?" |
| **Team Admin** | Sets up PWA on multiple devices | "Which of my devices are properly configured?" |
| **Self-hosted deployer** | Runs ShutterSense on own infrastructure | "Did my deployment break PWA/push for existing users?" |

---

## User Stories

### US1: View PWA Health Summary
**As a** user, **I want to** see an at-a-glance summary of my PWA health, **so that** I know if everything is working without opening DevTools.

**Acceptance Criteria:**
- Diagnostics panel accessible from Notifications page (or Settings)
- Shows pass/warn/fail status for: installation state, service worker, notifications, push subscription
- Each status has a one-line summary and expandable detail

### US2: Diagnose Notification Failure
**As a** user on Edge/macOS who isn't receiving notifications, **I want to** be told exactly what's wrong, **so that** I can fix it without hours of debugging.

**Acceptance Criteria:**
- Detects Edge on macOS and warns about the attribution flag
- Provides the exact `edge://flags` URL to open
- Re-checks status after user returns to the app (focus event)

### US3: Fix Stale Cache
**As a** user who visited the app before PWA was configured, **I want to** clear stale cached data, **so that** I can install the PWA.

**Acceptance Criteria:**
- Detects when the app is not installable but should be
- Shows cache age and size information
- Offers a "Clear cache and reload" button with confirmation
- After reload, the install prompt should appear

### US4: Verify Deployment Health
**As a** self-hosted deployer, **I want to** check that VAPID keys are configured and the service worker is up to date, **so that** I know push notifications will work for my users.

**Acceptance Criteria:**
- Shows VAPID key status (configured/not configured) from server endpoint
- Shows service worker version and whether it matches the app build
- Shows if a service worker update is waiting to activate

### US5: Understand iOS Limitations
**As an** iOS user, **I want to** understand why push notifications require installation, **so that** I can complete the setup correctly.

**Acceptance Criteria:**
- Detects iOS browser tab (not standalone)
- Shows step-by-step instructions for "Add to Home Screen"
- After installation, diagnostics show push as available

---

## Functional Requirements

### FR-01: Diagnostics Panel Location

The diagnostics panel MUST be accessible from a "PWA Health" or "Diagnostics" button/tab on the Notifications page. Rationale: notifications are the primary PWA use case, and users experiencing notification issues will naturally navigate here.

### FR-02: Diagnostic Check Categories

The panel MUST organize checks into the following categories:

#### Category 1: Installation

| Check | Detection Method | Pass | Warn | Fail |
|-------|-----------------|------|------|------|
| Display mode | `matchMedia('(display-mode: standalone)')` + `navigator.standalone` | Standalone (installed PWA) | Browser tab (installable) | Browser tab (not installable) |
| Manifest | `navigator.getInstalledRelatedApps()` or manifest link presence | Valid manifest with icons | Manifest present but missing fields | No manifest detected |
| Browser | `navigator.userAgentData` / UA parsing | Supported browser | Limited support (Firefox, Safari in-tab) | Unsupported browser |

#### Category 2: Service Worker

| Check | Detection Method | Pass | Warn | Fail |
|-------|-----------------|------|------|------|
| Registration | `navigator.serviceWorker.getRegistration()` | Active SW registered | SW waiting to activate | No SW registered |
| Version | Custom message channel to SW | SW version matches app build | Version mismatch (update pending) | Cannot determine version |
| Update status | `registration.waiting`, `registration.installing` | Up to date | Update installing/waiting | Stale (no updates detected) |

#### Category 3: Cache

| Check | Detection Method | Pass | Warn | Fail |
|-------|-----------------|------|------|------|
| Cache storage | `caches.keys()` + `cache.keys()` | Expected caches present | Unexpected/extra caches | No caches (SW not caching) |
| Cache size | Iterate cache entries, sum `Content-Length` or `blob.size` | Under threshold | Large cache (>50MB) | Cache API unavailable |
| Precache status | Check workbox precache manifest entries | All precached assets present | Some missing | Precache empty |

#### Category 4: Push Notifications

| Check | Detection Method | Pass | Warn | Fail |
|-------|-----------------|------|------|------|
| Push API | `'PushManager' in window` | Supported | — | Not supported |
| Permission | `Notification.permission` | Granted | Default (not yet asked) | Denied |
| VAPID keys | `GET /api/notifications/push/health` (new endpoint) | Configured | — | Not configured |
| Subscription | `registration.pushManager.getSubscription()` + server match | Active and server-matched | Browser has subscription but server doesn't (or vice versa) | No subscription |
| Platform issues | Browser + OS detection | No known issues | Advisory (e.g., Safari ITP) | Blocking issue (Edge flag, iOS not installed) |

### FR-03: Platform-Specific Warnings

The diagnostics MUST detect and surface the following platform-specific issues:

| Platform | Condition | Severity | Message | Remediation |
|----------|-----------|----------|---------|-------------|
| Edge + macOS | Any Edge version on macOS | Warn | "Edge on macOS requires an experimental flag for PWA notifications" | Link to `edge://flags/#enable-mac-pwas-notification-attribution` with step-by-step instructions |
| Chrome + macOS (managed) | `Notification.permission === 'denied'` and cannot re-request | Fail | "Notification permission is blocked, possibly by a system policy" | Guidance to check System Settings > Notifications > Google Chrome Helper (Alerts) and contact IT |
| iOS + browser tab | `isIos() && !isStandalone()` | Fail | "Push notifications require the app to be installed on your Home Screen" | Step-by-step Add to Home Screen instructions |
| Safari + macOS | Running in Safari (not "Add to Dock") | Warn | "For best notification support on macOS, add this app to your Dock" | File > Add to Dock instructions |
| Safari (any) | Service worker may be evicted by ITP | Info | "Safari may remove background workers for sites you don't visit regularly" | Suggest periodic app visits or Home Screen install |

### FR-04: Cache Repair Action

The diagnostics MUST offer a "Clear cache and reload" action when:
- The app is in a browser tab but should be installable (manifest is valid but install prompt doesn't appear)
- Cache entries are older than the current app build
- Cache size exceeds a configurable threshold

This action MUST:
1. Show a confirmation dialog explaining what will happen
2. Call `caches.keys()` and `caches.delete()` for all app caches
3. Unregister the service worker via `registration.unregister()`
4. Reload the page via `window.location.reload()`

### FR-05: Test Notification Button

The diagnostics panel MUST include a "Send test notification" button that:
1. Is only enabled when all push checks pass
2. Calls the existing `POST /api/notifications/push/test/{guid}` endpoint
3. Reports success or failure with the specific error from the server
4. Times out after 10 seconds with a "notification may have been blocked by your OS" message

### FR-06: Service Worker Version Reporting

The service worker MUST respond to a version query message:

```typescript
// In sw.ts — add message handler
self.addEventListener('message', (event) => {
  if (event.data?.type === 'GET_VERSION') {
    event.ports[0]?.postMessage({
      type: 'VERSION',
      version: SW_VERSION, // injected at build time
      precacheCount: self.__WB_MANIFEST?.length ?? 0,
    })
  }
})
```

The diagnostics panel queries this via `MessageChannel` and compares with the app's build version.

### FR-07: Backend Health Endpoint

A new endpoint `GET /api/notifications/push/health` MUST return:

```json
{
  "vapid_configured": true,
  "vapid_subject": "mailto:admin@example.com",
  "active_subscriptions": 3,
  "last_push_sent_at": "2026-02-22T10:30:00Z",
  "last_push_error": null
}
```

This endpoint requires authentication but not admin privileges. It returns health information scoped to the requesting user's team.

### FR-08: Diagnostics Data Export

The diagnostics panel MUST include a "Copy diagnostics" button that copies a text summary of all checks to the clipboard, formatted for pasting into a support request or GitHub issue. Example:

```
ShutterSense PWA Health Report — 2026-02-22T10:30:00Z

Installation
  Display mode: standalone (installed PWA)
  Browser: Edge 131 on macOS 15.3
  Manifest: valid

Service Worker
  Registration: active
  Version: v1.5.2 (matches app)
  Update: up to date

Cache
  Caches: workbox-precache-v2 (142 entries, 4.2 MB), api-cache (12 entries, 0.1 MB)

Push Notifications
  Push API: supported
  Permission: granted
  VAPID: configured
  Subscription: active (endpoint matches server)
  Platform: ⚠ Edge on macOS — ensure edge://flags/#enable-mac-pwas-notification-attribution is Enabled
```

---

## Non-Functional Requirements

### NFR-01: Performance
- All client-side diagnostic checks MUST complete within 2 seconds
- The backend health endpoint MUST respond within 200ms
- Cache size calculation MAY be deferred (lazy-loaded on expand)

### NFR-02: Privacy
- The diagnostics export MUST NOT include push subscription endpoints, VAPID keys, or user credentials
- The backend health endpoint MUST NOT expose other users' subscription data

### NFR-03: Compatibility
- Diagnostics MUST gracefully degrade when APIs are unavailable (e.g., no `caches` API, no `navigator.permissions`)
- Each check MUST handle API unavailability as a distinct "unsupported" state, not an error

### NFR-04: Accessibility
- Pass/warn/fail states MUST use both color and icon (not color alone)
- All interactive elements MUST be keyboard-accessible
- Screen readers MUST announce check results and severity

---

## Technical Approach

### Architecture

```
┌─────────────────────────────────────────────────┐
│                 Diagnostics Panel                │
│                                                  │
│  ┌──────────┐ ┌──────────┐ ┌───────┐ ┌───────┐ │
│  │Install   │ │Service   │ │Cache  │ │Push   │ │
│  │Checks    │ │Worker    │ │Health │ │Notifs │ │
│  └────┬─────┘ └────┬─────┘ └───┬───┘ └───┬───┘ │
│       │             │           │         │     │
│  Browser APIs  MessageChannel  CacheAPI   │     │
│  (display-mode  (SW ↔ page)   (caches.*)  │     │
│   UA detection)                           │     │
│                                           │     │
│                              ┌────────────┘     │
│                              │                  │
│                     GET /api/notifications/      │
│                         push/health             │
└─────────────────────────────────────────────────┘
```

### Key Files (New)

| File | Purpose |
|------|---------|
| `frontend/src/hooks/usePwaHealth.ts` | Core diagnostics hook — runs all checks, returns structured results |
| `frontend/src/components/notifications/PwaHealthPanel.tsx` | Diagnostics UI panel with collapsible check categories |
| `backend/src/api/routes/notification_push_health.py` | `GET /api/notifications/push/health` endpoint |

### Key Files (Modified)

| File | Change |
|------|--------|
| `frontend/src/sw.ts` | Add `GET_VERSION` message handler |
| `frontend/src/pages/NotificationsPage.tsx` | Add "PWA Health" button/tab to access diagnostics |
| `frontend/src/hooks/usePushSubscription.ts` | Extract browser/platform detection helpers to shared utility |
| `frontend/vite.config.ts` | Inject build version constant into SW via `define` |

### Implementation Phases

**Phase 1: Core Diagnostics Hook + Panel UI**
- Create `usePwaHealth` hook with all client-side checks
- Build `PwaHealthPanel` component with pass/warn/fail display
- Add SW version message handler
- Wire into NotificationsPage

**Phase 2: Platform-Specific Warnings**
- Implement Edge/macOS attribution flag detection
- Implement iOS not-installed detection (reuse existing)
- Implement Safari ITP advisory
- Implement corporate MDM detection heuristic

**Phase 3: Cache Health + Repair**
- Enumerate caches and compute sizes
- Detect stale precache entries
- Implement "Clear cache and reload" with confirmation dialog

**Phase 4: Backend Health Endpoint + Integration**
- Create `/api/notifications/push/health` endpoint
- Integrate VAPID status, subscription count, last push status
- Wire into diagnostics panel

**Phase 5: Polish**
- "Copy diagnostics" export
- Test notification integration
- Accessibility audit

---

## UI Wireframe

```
┌─────────────────────────────────────────────────────┐
│ Notifications                        [PWA Health]   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  PWA Health Diagnostics              [Copy Report]  │
│                                                     │
│  ┌─ Installation ──────────────────────── ✓ ──────┐ │
│  │  ✓ Running as installed PWA (standalone)       │ │
│  │  ✓ Edge 131 on macOS 15.3                      │ │
│  │  ✓ Manifest valid (5 icons)                    │ │
│  └────────────────────────────────────────────────┘ │
│                                                     │
│  ┌─ Service Worker ────────────────────── ✓ ──────┐ │
│  │  ✓ Active (v1.5.2)                             │ │
│  │  ✓ Version matches app build                   │ │
│  │  ✓ No update pending                           │ │
│  └────────────────────────────────────────────────┘ │
│                                                     │
│  ┌─ Cache ─────────────────────────────── ✓ ──────┐ │
│  │  ✓ 2 caches (154 entries, 4.3 MB)              │ │
│  │    workbox-precache-v2: 142 entries, 4.2 MB     │ │
│  │    api-cache: 12 entries, 0.1 MB                │ │
│  └────────────────────────────────────────────────┘ │
│                                                     │
│  ┌─ Push Notifications ───────────────── ⚠ ──────┐ │
│  │  ✓ Push API supported                          │ │
│  │  ✓ Permission granted                          │ │
│  │  ✓ VAPID keys configured                       │ │
│  │  ✓ Subscription active                         │ │
│  │  ⚠ Edge on macOS: ensure notification          │ │
│  │    attribution flag is enabled                  │ │
│  │    → Open edge://flags/#enable-mac-pwas-        │ │
│  │      notification-attribution and set           │ │
│  │      to "Enabled"                               │ │
│  │                                                 │ │
│  │  [Send Test Notification]                       │ │
│  └────────────────────────────────────────────────┘ │
│                                                     │
└─────────────────────────────────────────────────────┘
```

When a critical issue is detected (e.g., stale cache blocking install):

```
┌─ Installation ──────────────────────── ✗ ──────┐
│  ✗ Running in browser tab (not installed)      │
│  ⚠ PWA install prompt not available            │
│    Stale cached data may be preventing          │
│    installation. This can happen if the app     │
│    was visited before PWA was fully configured. │
│                                                 │
│    [Clear Cache & Reload]                       │
│                                                 │
│  ℹ After clearing, look for the install icon    │
│    (⊕) in the address bar.                     │
└─────────────────────────────────────────────────┘
```

---

## Future Considerations

### Future: Push Subscription Health Monitoring

Server-side monitoring of push delivery success rates (track 410 Gone, 429 Rate Limited, timeouts per subscription). Alert users when their subscription is silently failing. This is complementary to the client-side diagnostics in this PRD but requires backend work to track delivery outcomes per push.

### Future: Declarative Web Push (Safari 18.4+)

Safari's Declarative Web Push standard eliminates service worker dependency for push delivery. When adopted, the diagnostics panel should detect Safari 18.4+ and show "Declarative Web Push available" as a positive signal, and potentially recommend Safari/Add to Dock for users experiencing Chrome/Edge push issues.

### Future: Admin Deployment Health Dashboard

An admin-facing view showing aggregated PWA health across all users: how many are running stale service workers, how many have broken push subscriptions, success/failure rates for recent push deliveries. Useful for self-hosted deployers monitoring rollout health.

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Time to diagnose push notification failure | < 2 minutes (down from hours/days) |
| Support requests for PWA/notification issues | 50% reduction |
| Users who successfully resolve issues via diagnostics | > 70% |
| Diagnostics panel load time | < 2 seconds |

---

## References

- [PWA Installation & Notifications Guide](../pwa-installation-and-notifications.md)
- [023-pwa-push-notifications.md](./023-pwa-push-notifications.md) — Original PWA PRD
- [Chromium Issue #40874345](https://issues.chromium.org/issues/40874345) — PWA notification attribution on macOS
- [WebKit Blog — Meet Declarative Web Push](https://webkit.org/blog/16535/meet-declarative-web-push/)
- [MDN — Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [MDN — Cache API](https://developer.mozilla.org/en-US/docs/Web/API/Cache)
- [web.dev — PWA Installation](https://web.dev/learn/pwa/installation)
