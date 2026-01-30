# Research: PWA with Push Notifications

**Feature Branch**: `114-pwa-push-notifications`
**Date**: 2026-01-29

## Research Questions & Findings

### RQ-1: PWA Service Worker Strategy

**Decision**: Use `vite-plugin-pwa` with Workbox `precacheAndRoute` for the service worker, configured with `registerType: 'autoUpdate'`.

**Rationale**: The project already uses Vite 6.0.5 with React. `vite-plugin-pwa` is the standard integration for Vite-based PWAs. It generates the web app manifest, configures Workbox for asset caching, and provides hooks for service worker lifecycle management. The plugin supports custom service worker code for push event handling alongside Workbox precaching.

**Alternatives Considered**:
- Manual service worker (rejected: excessive boilerplate for caching, no manifest generation, error-prone lifecycle management)
- Workbox CLI standalone (rejected: doesn't integrate with Vite build pipeline)

**Codebase Context**:
- `frontend/vite.config.ts`: Currently uses `@vitejs/plugin-react` and `rollup-plugin-visualizer`. No PWA plugin installed.
- `frontend/package.json`: No PWA-related dependencies exist. Needs `vite-plugin-pwa` added as dev dependency.
- `frontend/index.html`: Has favicons (192px, SVG, ICO, apple-touch-icon) but no PWA meta tags (`theme-color`, `apple-mobile-web-app-capable`, manifest link).

### RQ-2: Push Notification Delivery Library

**Decision**: Use `pywebpush` on the backend for Web Push protocol delivery with VAPID authentication.

**Rationale**: `pywebpush` is the standard Python library for Web Push, supporting VAPID key signing and payload encryption per RFC 8291/8292. It integrates with any push service (FCM, Mozilla, APNs, WNS) transparently via the standard Web Push protocol.

**Alternatives Considered**:
- Firebase Admin SDK (rejected: vendor lock-in, unnecessary complexity for standard Web Push)
- Custom HTTP implementation (rejected: encryption and signing complexity, maintenance burden)

**Codebase Context**:
- `backend/requirements.txt`: No push-related dependencies. Needs `pywebpush>=2.0.0`.
- `backend/src/config/settings.py`: Uses Pydantic `BaseSettings` with env vars. New VAPID env vars needed: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`.

### RQ-3: GUID Prefix Selection for New Entities

**Decision**: Use `sub_` for PushSubscription and `ntf_` for Notification.

**Rationale**: The PRD specifies these prefixes explicitly. The existing GUID system uses 3-character prefixes (`col_`, `evt_`, `agt_`, etc.) registered in `GuidService.ENTITY_PREFIXES`. Both `sub` and `ntf` are unused in the current registry (17 prefixes registered as of now).

**Codebase Context**:
- `backend/src/services/guid.py` (lines 38-58): `ENTITY_PREFIXES` dict must be updated with new entries.
- `backend/src/models/mixins/guid.py`: New models use `GuidMixin` with `GUID_PREFIX` class variable.

### RQ-4: Notification Trigger Integration Points

**Decision**: Integrate notification triggers into existing service methods via a new `NotificationService` injected as a dependency.

**Rationale**: The existing services already have clear trigger points:
- `JobCoordinatorService.fail_job()` — triggers job failure notification
- `JobCoordinatorService.complete_job()` — triggers inflection point notification (only when `no_change_copy=false`)
- `AgentService.check_offline_agents()` — triggers pool offline notification
- `AgentService.process_heartbeat()` — triggers recovery/error notifications

Each method already has the data needed (job details, agent status, team_id) to construct notifications. Adding a `NotificationService.notify_*()` call at the end of each method is the simplest integration.

**Codebase Context**:
- `backend/src/services/job_coordinator_service.py`: `fail_job()` at line 2166, `complete_job()` at line 1136.
- `backend/src/services/agent_service.py`: `check_offline_agents()` at line 594, `process_heartbeat()` at line 483.

### RQ-5: User Notification Preferences Storage

**Decision**: Store notification preferences as a JSON object in the existing `User.preferences_json` column, using a structured schema validated by Pydantic.

**Rationale**: The `User` model already has a `preferences_json` TEXT column (nullable). Using this avoids a new table and migration for preferences alone. A Pydantic model provides type safety and validation. Server-side storage ensures preferences sync across devices.

**Alternatives Considered**:
- New `notification_preferences` table (rejected: over-engineering for a simple key-value structure per user; the preferences are always loaded with the user and have no independent lifecycle)
- User-level `Configuration` entries (rejected: the existing config system is for application-level settings, not per-user preferences)

**Codebase Context**:
- `backend/src/models/user.py`: `preferences_json = Column(Text, nullable=True)` exists but is unused.

### RQ-6: Dead Agent Safety Net Implementation

**Decision**: Implement as a FastAPI startup background task using `asyncio.sleep(120)` loop, not a system crontab.

**Rationale**: A FastAPI background task is self-contained within the application, requires no external cron configuration, and can directly access the database session and NotificationService. It runs in the same process, simplifying deployment. The check is lightweight (single indexed query, <5ms) and idempotent.

**Alternatives Considered**:
- System crontab + management command (rejected: adds deployment complexity, requires external configuration, harder to test)
- Celery beat (rejected: not in current stack, massive dependency for one periodic task)

**Codebase Context**:
- `backend/src/services/agent_service.py`: `check_offline_agents()` already implements the core logic for a single team. The safety net extends this to all teams in one query.

### RQ-7: Notification History and Bell Icon Integration

**Decision**: Use the existing bell icon placeholder in `TopHeader.tsx` and replace the hardcoded badge with a dynamic unread count from a new `useNotifications` hook. Notification panel will be a dropdown/popover from the bell icon.

**Rationale**: The TopHeader already has a bell button with a static badge ("3") at line 164-175 of `TopHeader.tsx`. Converting this to a dynamic component with a dropdown is the minimal change. A popover/dropdown avoids adding a new route and keeps the notification flow within the existing layout.

**Codebase Context**:
- `frontend/src/components/layout/TopHeader.tsx` (line 164-175): Existing bell button with hardcoded badge.
- `frontend/src/hooks/`: 29 existing hooks follow consistent useState/useCallback/useEffect pattern.
- Notification preferences placed on the Profile page (`/profile`), not SettingsPage — see RQ-10 for rationale.

### RQ-8: Asynchronous Notification Delivery

**Decision**: Use Python `asyncio.create_task()` within the FastAPI request handler to fire-and-forget notification delivery, ensuring the triggering API call returns without waiting.

**Rationale**: FastAPI is async-native. Using `create_task()` for notification delivery prevents blocking the job completion or agent heartbeat response. Failed deliveries are handled by the task itself (retry logic, error logging). This is simpler than introducing a task queue (Celery, RQ) for this single use case.

**Alternatives Considered**:
- Celery task queue (rejected: heavy dependency not in current stack, over-engineering for this use case)
- Synchronous delivery in same request (rejected: blocks the triggering operation, violates FR-019)
- Database-backed queue with worker (rejected: adds complexity; async task is sufficient for expected notification volume)

### RQ-9: Deadline Check Job Type

**Decision**: Add `deadline_check` as a new job type in the agent job system. The server creates one job per team per day. The agent claims it and calls a server-side API endpoint to execute the lightweight deadline query.

**Rationale**: This follows the established agent-only execution architecture (Constitution Principle VI). The deadline query is simple enough to run server-side via an internal API call, but routing it through the agent system maintains architectural consistency and enables future extensibility.

**Codebase Context**:
- `backend/src/services/job_service.py`: Existing job creation and claiming patterns.
- `backend/src/services/job_coordinator_service.py`: Orchestrates job lifecycle.

### RQ-10: Notification Preferences UI Placement

**Decision**: Add notification preferences to the user's **Profile page** (`/profile`), not the application-level Settings page. The Profile page is accessible from the avatar dropdown in the top bar.

**Rationale**: The Settings page (`/settings`) contains team/application-level configuration (cameras, categories, connectors, API tokens, retention policies) — all scoped to the team and shared across team members. Notification preferences are personal to each user (which categories *I* want, *my* push devices, *my* deadline timing). Placing them in the Profile area (accessible via the avatar dropdown) maintains the architectural separation between team-level settings and user-level preferences.

The Profile page currently displays read-only user information (name, email, organization). Adding a "Notification Preferences" section extends it into a user preferences hub, which is the natural home for any future user-level settings (theme, language, etc.).

**Alternatives Considered**:
- Add a "Notifications" tab to the Settings page (rejected: Settings is team/application-level, notification preferences are user-level — mixing scopes creates confusion)
- Create a separate `/preferences` page (rejected: over-engineering for a single preferences section; extending the existing Profile page is simpler and more discoverable)

**Codebase Context**:
- `frontend/src/pages/ProfilePage.tsx`: Read-only user info (124 lines). Currently displays avatar, name, email, organization.
- `frontend/src/components/layout/TopHeader.tsx` (lines 180-232): Avatar dropdown with "View Profile" → `/profile`, "Team" → `/team`, "Log out".
- `frontend/src/pages/SettingsPage.tsx`: Team-level settings with tabs (Configuration, Categories, Connectors, API Tokens, Teams, Release Manifests). NOT the right place for user-level preferences.

### RQ-11: Database Migration Numbering

**Decision**: The next available migration number needs to be determined at implementation time. Currently at migration 057.

**Codebase Context**:
- `backend/src/db/migrations/versions/`: 57 migration files. New migrations for `push_subscriptions` and `notifications` tables will follow the existing numbered sequence.

## Technology Decisions Summary

| Area | Decision | Key Dependency |
|------|----------|---------------|
| PWA Framework | vite-plugin-pwa | `vite-plugin-pwa ^0.20.0` |
| Push Delivery | pywebpush | `pywebpush >=2.0.0` |
| VAPID Auth | Environment variables | `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT` |
| Preferences Storage | User.preferences_json | Existing column |
| Safety Net | FastAPI background task | Built-in asyncio |
| Async Delivery | asyncio.create_task() | Built-in asyncio |
| Notification Panel | TopHeader dropdown | Existing bell icon |
| Preferences UI | Profile page section | Existing `/profile` page |
