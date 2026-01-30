# Implementation Plan: PWA with Push Notifications

**Branch**: `114-pwa-push-notifications` | **Date**: 2026-01-29 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/114-pwa-push-notifications/spec.md`

## Summary

Convert the ShutterSense.ai React SPA into an installable Progressive Web Application with Web Push notification capabilities. Users will receive push notifications on their devices for high-value events: job failures, analysis inflection points, agent status changes, approaching deadlines, and retry warnings. The implementation spans backend (notification service, push delivery, subscription management, dead agent safety net) and frontend (service worker, PWA manifest, notification preferences UI, notification history panel).

## Technical Context

**Language/Version**: Python 3.10+ (backend), TypeScript 5.9.3 (frontend)
**Primary Dependencies**: FastAPI (backend API), React 18.3.1 (frontend), pywebpush (push delivery), vite-plugin-pwa (service worker + manifest)
**Storage**: PostgreSQL 12+ (push_subscriptions, notifications tables), SQLite (tests)
**Testing**: pytest (backend), Vitest + Testing Library (frontend)
**Target Platform**: Web (desktop + mobile PWA). Desktop: Chrome 50+, Firefox 44+, Edge 17+, Safari 16+. Mobile: Chrome/Firefox Android, Safari iOS 16.4+
**Project Type**: Web application (frontend + backend)
**Performance Goals**: Notification delivery < 10 seconds from trigger event. Application shell loads < 1 second from cache. Unread count query < 100ms.
**Constraints**: Async notification delivery (must not block triggering request). VAPID keys in environment config (not in code). Multi-tenant isolation on all notification data.
**Scale/Scope**: Existing user base. New tables: push_subscriptions, notifications. New backend service. New frontend hooks, components, and service worker. ~8 new backend files, ~8 new frontend files, ~6 modified files.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Agent-Only Tool Execution (Principle I)**: This feature does not add standalone CLI tools. The `deadline_check` job type is executed through the agent job system, consistent with agent-only execution. The dead agent safety net is the only server-side scheduled task, justified because it monitors the agent infrastructure itself (same justification as PRD).
- [x] **Testing & Quality (Principle II)**: Tests planned for notification service (unit), push subscription service (unit), API endpoints (integration), frontend hooks and components (unit). Coverage targets align with project standards (>80% core logic).
- [x] **User-Centric Design (Principle III)**:
  - Not an analysis tool — no HTML report generation applicable
  - Error messages are clear: denied permission explains how to re-enable, failed delivery retries with logging
  - Implementation follows YAGNI: v1 excludes aggregation, mark-all-read, email/SMS
  - Structured logging included for notification delivery tracking
- [x] **Global Unique Identifiers (Principle IV)**: New entities use GuidMixin with registered prefixes: `sub_` (PushSubscription), `ntf_` (Notification). API responses expose `.guid`, not internal `.id`. Path parameters use `{guid}`.
- [x] **Multi-Tenancy and Authentication (Principle V)**: All notification endpoints require authentication via `require_auth` dependency. All data scoped to `team_id`. Push subscriptions and notifications have `team_id` FK. Cross-tenant access returns 404.
- [x] **Agent-Only Execution (Principle VI)**: Deadline checks scheduled through agent job system (`deadline_check` job type). Dead agent cron is the only server-side scheduled task, justified per PRD (monitors the agent infrastructure itself).
- [x] **Shared Infrastructure Standards**: UTF-8 encoding used for all file operations. Configuration via Pydantic BaseSettings (VAPID keys as env vars).
- [x] **Frontend UI Standards**:
  - TopHeader KPI: Unread notification count displayed in bell badge (existing placeholder)
  - Single Title Pattern: Notification preferences are a section in the Profile page (no new page title needed). No h1 elements added.
  - Action button positioning follows responsive stacking pattern.

**Violations/Exceptions**: None. The dead agent safety net (server-side background task) is explicitly permitted by the constitution and PRD as the one justified server-side scheduled task.

## Project Structure

### Documentation (this feature)

```text
specs/114-pwa-push-notifications/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research output
├── data-model.md        # Phase 1 data model
├── quickstart.md        # Phase 1 quickstart guide
├── contracts/
│   ├── api.yaml         # OpenAPI specification for notification endpoints
│   └── push-payload.md  # Push notification payload contract
├── checklists/
│   └── requirements.md  # Specification quality checklist
└── tasks.md             # Phase 2 task list (created by /speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   ├── push_subscription.py      # NEW: PushSubscription ORM model
│   │   ├── notification.py           # NEW: Notification ORM model
│   │   └── __init__.py               # MODIFIED: Register new models
│   ├── schemas/
│   │   └── notifications.py          # NEW: Pydantic request/response schemas
│   ├── services/
│   │   ├── notification_service.py       # NEW: Notification creation, preference check, push delivery
│   │   ├── push_subscription_service.py  # NEW: Subscription CRUD and cleanup
│   │   ├── guid.py                       # MODIFIED: Register sub_, ntf_ prefixes
│   │   ├── job_coordinator_service.py    # MODIFIED: Add notification triggers
│   │   └── agent_service.py              # MODIFIED: Add notification triggers
│   ├── api/
│   │   └── notifications.py          # NEW: API router for notification endpoints
│   ├── config/
│   │   └── settings.py               # MODIFIED: Add VAPID env vars
│   └── main.py                       # MODIFIED: Register router, start background task
├── tests/
│   └── unit/
│       ├── test_notification_service.py       # NEW
│       ├── test_push_subscription_service.py  # NEW
│       └── test_notifications_api.py          # NEW
└── src/db/migrations/versions/
    └── NNN_create_notification_tables.py  # NEW: Migration for both tables

frontend/
├── public/
│   └── icons/                        # NEW: PWA icons (192, 512, maskable, badge)
├── src/
│   ├── custom-sw.ts                  # NEW: Custom service worker (push + click handlers)
│   ├── hooks/
│   │   ├── useNotifications.ts           # NEW: Notification history and unread count
│   │   ├── useNotificationPreferences.ts # NEW: Preferences CRUD
│   │   └── usePushSubscription.ts        # NEW: Push subscription lifecycle
│   ├── services/
│   │   └── notifications.ts          # NEW: API client for notification endpoints
│   ├── components/
│   │   ├── notifications/
│   │   │   └── NotificationPanel.tsx      # NEW: Bell dropdown with notification list
│   │   └── profile/
│   │       └── NotificationPreferences.tsx # NEW: Notification preferences section
│   ├── components/layout/
│   │   └── TopHeader.tsx              # MODIFIED: Dynamic bell badge + panel integration
│   ├── pages/
│   │   └── ProfilePage.tsx            # MODIFIED: Add notification preferences section
│   └── contracts/
│       └── domain-labels.ts           # MODIFIED: Add notification category labels
├── index.html                         # MODIFIED: Add PWA meta tags
├── vite.config.ts                     # MODIFIED: Add vite-plugin-pwa
└── package.json                       # MODIFIED: Add vite-plugin-pwa dependency
```

**Structure Decision**: Web application structure (frontend + backend), consistent with existing project layout. All new backend files follow the established models/schemas/services/api pattern. All new frontend files follow the established hooks/services/components pattern.

## Complexity Tracking

> No Constitution Check violations. No complexity exceptions required.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
