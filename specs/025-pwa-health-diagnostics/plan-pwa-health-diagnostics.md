# Plan: PWA Health Diagnostics Panel (2026-02-22)

## Context

Real-world deployment of ShutterSense's PWA revealed that PWA issues are **silent and persistent** — stale caches prevent installation, Edge/macOS requires a hidden flag for notifications, iOS requires Home Screen install, and corporate MDM policies silently block permissions. Users have no way to diagnose these issues without DevTools.

This plan implements PRD 025: a **PWA Health Diagnostics** panel accessible from the Notifications page, providing automated detection and actionable remediation for installation, service worker, cache, and push notification issues.

**PRD**: `docs/prd/025-pwa-health-diagnostics.md`

---

## Changes

### Phase 1: Foundation — Utility Extraction + Types + Vite Config

**Create:**
- `frontend/src/utils/pwa-detection.ts` — Extract pure helpers from `usePushSubscription.ts` (`getPermissionState`, `isIos`, `isStandalone`, `detectBrowserName`, `detectDeviceName`, `urlBase64ToUint8Array`) + new helpers (`detectPlatformName`, `isEdgeOnMacOS`, `isSafari`, `getDisplayMode`)
- `frontend/src/contracts/pwa-health.ts` — Type definitions: `DiagnosticStatus`, `DiagnosticCheck`, `DiagnosticSection`, `PwaHealthResult`

**Modify:**
- `frontend/src/hooks/usePushSubscription.ts` — Replace local definitions with imports from `@/utils/pwa-detection`
- `frontend/vite.config.ts` — Add `define: { __SW_VERSION__: JSON.stringify(new Date().toISOString()) }`

### Phase 2: Service Worker Version Handler + Backend Endpoint

**Modify:**
- `frontend/src/sw.ts` — Add `GET_VERSION` message handler in existing `message` listener
- `backend/src/schemas/notifications.py` — Add `PushHealthResponse` schema (`vapid_configured`, `subscription_count`, `last_push_at`)
- `backend/src/api/notifications.py` — Add `GET /push/health` endpoint (authenticated, rate-limited)
- `frontend/src/contracts/api/notification-api.ts` — Add `PushHealthResponse` type
- `frontend/src/services/notifications.ts` — Add `getPushHealth()` function

### Phase 3: Core Diagnostics Hook

**Create:**
- `frontend/src/hooks/usePwaHealth.ts` — Runs 5 sections of checks (Installation, Service Worker, Cache, Push Notifications, Platform Warnings), provides `copyDiagnostics()` and `clearCacheAndReload()` actions

### Phase 4: UI Components

**Create:**
- `frontend/src/components/notifications/DiagnosticCheck.tsx` — Status icon + label + message + remediation
- `frontend/src/components/notifications/DiagnosticSection.tsx` — Collapsible section with overall status
- `frontend/src/components/notifications/PwaHealthPanel.tsx` — All sections + action buttons
- `frontend/src/components/notifications/PwaHealthDialog.tsx` — Dialog wrapper

**Modify:**
- `frontend/src/pages/NotificationsPage.tsx` — Add "PWA Health" button + dialog

### Phase 5: Polish

- "Send Test Notification" via existing `usePushSubscription.testDevice()`
- "Clear Cache & Reload" with `AlertDialog` confirmation
- "Copy Diagnostics" formatted plain text to clipboard

## Files

| File | Action |
|------|--------|
| `frontend/src/utils/pwa-detection.ts` | Create |
| `frontend/src/contracts/pwa-health.ts` | Create |
| `frontend/src/hooks/usePwaHealth.ts` | Create |
| `frontend/src/components/notifications/DiagnosticCheck.tsx` | Create |
| `frontend/src/components/notifications/DiagnosticSection.tsx` | Create |
| `frontend/src/components/notifications/PwaHealthPanel.tsx` | Create |
| `frontend/src/components/notifications/PwaHealthDialog.tsx` | Create |
| `frontend/src/hooks/usePushSubscription.ts` | Modify (import extraction) |
| `frontend/src/sw.ts` | Modify (GET_VERSION handler) |
| `frontend/vite.config.ts` | Modify (define __SW_VERSION__) |
| `frontend/src/pages/NotificationsPage.tsx` | Modify (PWA Health button) |
| `frontend/src/services/notifications.ts` | Modify (getPushHealth) |
| `frontend/src/contracts/api/notification-api.ts` | Modify (PushHealthResponse) |
| `backend/src/schemas/notifications.py` | Modify (PushHealthResponse) |
| `backend/src/api/notifications.py` | Modify (GET /push/health) |

## Verification

1. `cd frontend && npx tsc --noEmit` — no type errors
2. `venv/bin/python -m pytest backend/tests/unit/ -v` — backend tests pass
3. Manual: Notifications page → "PWA Health" → all sections render correctly
4. Test notification arrives when clicked
5. Cache clear + reload works with confirmation
6. Copy diagnostics produces formatted text
7. Cross-browser: Edge/macOS shows flag warning, iOS shows install prompt
