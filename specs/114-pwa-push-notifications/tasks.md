# Tasks: PWA with Push Notifications

**Input**: Design documents from `/specs/114-pwa-push-notifications/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Constitution Principle II requires test coverage. Test tasks are in Phase 13.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Install dependencies, configure VAPID keys, and register GUID prefixes

- [x] T001 Add `pywebpush>=2.0.0` to `backend/requirements.txt`
- [x] T002 Install `vite-plugin-pwa` as dev dependency in `frontend/package.json`
- [x] T003 Add VAPID environment variables (`VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_SUBJECT`) to `backend/src/config/settings.py` AppSettings class
- [x] T004 [P] Register `sub` and `ntf` GUID prefixes in `backend/src/services/guid.py` ENTITY_PREFIXES dict
- [x] T005 [P] Add notification category labels and icons to `frontend/src/contracts/domain-labels.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create database models, migration, schemas, and core services that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

### Database Models & Migration

- [x] T006 [P] Create PushSubscription model with GuidMixin, team_id FK, user_id FK, endpoint, p256dh_key, auth_key, device_name, last_used_at, expires_at, timestamps in `backend/src/models/push_subscription.py`
- [x] T007 [P] Create Notification model with GuidMixin, team_id FK, user_id FK, category, title, body, data (JSONB), read_at, created_at in `backend/src/models/notification.py`
- [x] T008 Register PushSubscription and Notification models in `backend/src/models/__init__.py`
- [x] T009 Create Alembic migration for `push_subscriptions` and `notifications` tables with all indexes (uuid unique, user_id, team_id, endpoint unique, user unread partial index, created_at) in `backend/src/db/migrations/versions/`

### Pydantic Schemas

- [x] T010 Create Pydantic request/response schemas in `backend/src/schemas/notifications.py`: PushSubscriptionCreate, PushSubscriptionResponse, SubscriptionStatusResponse, NotificationPreferencesResponse, NotificationPreferencesUpdate, NotificationResponse, NotificationListResponse — per contracts/api.yaml

### Core Services

- [x] T011 Create PushSubscriptionService in `backend/src/services/push_subscription_service.py` with: create_subscription (upsert by endpoint), remove_subscription (by endpoint + user), list_subscriptions (by user), cleanup_expired, remove_invalid (410 Gone handling)
- [x] T012 Create NotificationService in `backend/src/services/notification_service.py` with: create_notification (stores in DB), deliver_push (sends to all user subscriptions via pywebpush), get_user_preferences (reads from User.preferences_json), check_preference (verifies category enabled for user), send_notification (orchestrates: check prefs → create record → async push delivery)
- [x] T013 Create notification preferences helper in `backend/src/services/notification_service.py`: get_default_preferences(), update_preferences() — reads/writes User.preferences_json with Pydantic validation per data-model.md schema

### API Router

- [x] T014 Create notification API router in `backend/src/api/notifications.py` with all endpoints per contracts/api.yaml: POST/DELETE /subscribe, GET /status, GET/PUT /preferences, GET /notifications, GET /unread-count, POST /{guid}/read, GET /vapid-key
- [x] T015 Register notification router and add VAPID key dependency injection in `backend/src/main.py`

### Frontend API Client

- [x] T016 Create notifications API service in `frontend/src/services/notifications.ts` with functions for all endpoints: subscribe, unsubscribe, getStatus, getPreferences, updatePreferences, listNotifications, getUnreadCount, markAsRead, getVapidKey

**Checkpoint**: Foundation ready — database, services, API, and frontend client all in place. User story implementation can now begin.

---

## Phase 3: User Story 1 — Install ShutterSense as an App (Priority: P1) MVP

**Goal**: Convert the SPA into an installable PWA with service worker caching and update prompts

**Independent Test**: Visit ShutterSense in a supported browser, install as app, verify standalone window launch, verify cached assets load fast, verify update prompt on new deploy

### Implementation for User Story 1

- [x] T017 [P] [US1] Create PWA icon set in `frontend/public/icons/`: icon-192x192.png, icon-512x512.png, maskable-icon-192x192.png, maskable-icon-512x512.png, badge-72x72.png (generate from existing favicon-192.png or SVG source)
- [x] T018 [P] [US1] Add PWA meta tags to `frontend/index.html`: theme-color, apple-mobile-web-app-capable, apple-mobile-web-app-status-bar-style, manifest link
- [x] T019 [US1] Configure `vite-plugin-pwa` in `frontend/vite.config.ts`: registerType 'autoUpdate', manifest config (name, short_name, icons, theme_color, background_color, display: standalone, start_url), workbox precaching for build assets
- [x] T020 [US1] Create custom service worker additions in `frontend/src/sw.ts`: push event listener (showNotification from payload), notificationclick handler (focus existing window or open new one with data.url) — integrated via vite-plugin-pwa injectManifest
- [x] T021 [US1] Add iOS PWA detection and "Add to Home Screen" guidance component: detect `navigator.userAgent` iOS + `display-mode: standalone` not matched, show installation instructions banner. Place in MainLayout or TopHeader area

**Checkpoint**: App is installable as PWA. Service worker caches assets. Update prompts work. iOS users see guidance.

---

## Phase 4: User Story 2 — Enable Push Notifications (Priority: P1)

**Goal**: Users can opt in/out of push notifications, subscribe their device, and receive test pushes

**Independent Test**: Log in, click "Enable Notifications" on Profile page, grant browser permission, verify subscription stored on server, verify test push received. Disable and verify subscription removed.

**Depends on**: US1 (service worker must be registered for PushManager)

### Implementation for User Story 2

- [x] T022 [P] [US2] Create usePushSubscription hook in `frontend/src/hooks/usePushSubscription.ts`: subscribe (request permission → PushManager.subscribe with VAPID key → POST to server), unsubscribe (PushManager unsubscribe → DELETE on server), check permission state, detect iOS not-installed state
- [x] T023 [P] [US2] Create useNotificationPreferences hook in `frontend/src/hooks/useNotificationPreferences.ts`: fetch preferences (GET /preferences), update preferences (PUT /preferences), loading/error states — following existing hooks pattern (useState, useCallback, useEffect)
- [x] T024 [US2] Create NotificationPreferences component in `frontend/src/components/profile/NotificationPreferences.tsx`: master enable/disable toggle (triggers push subscription flow), per-category toggles (Job Failures, Inflection Points, Agent Status, Deadlines, Retry Warnings), deadline days-before selector, timezone selector (using existing `timezone-combobox.tsx` component, auto-detected from `Intl.DateTimeFormat().resolvedOptions().timeZone` on first enable), device list showing active subscriptions. Uses shadcn/ui Switch, Select, Card components. Follows responsive stacking pattern.
- [x] T025 [US2] Integrate NotificationPreferences section into ProfilePage in `frontend/src/pages/ProfilePage.tsx`: add section below existing user info card, load preferences and subscription status on mount
- [x] T026 [US2] Handle permission denied and iOS not-installed states: show informational message with re-enable instructions when permission is denied, show "Add to Home Screen" instructions on iOS when not in standalone mode

**Checkpoint**: Users can enable/disable push notifications per device and per category. Subscriptions stored on server.

---

## Phase 5: User Story 3 — Receive Job Failure Notifications (Priority: P1)

**Goal**: Push notification delivered when a job fails, with tool name, collection name, error summary, and click-to-navigate

**Independent Test**: Trigger a job failure (or simulate via fail_job), verify push notification appears with correct details, click notification to navigate to job details page

**Depends on**: US2 (push subscription must exist)

### Implementation for User Story 3

- [x] T027 [US3] Add notify_job_failure() method to NotificationService in `backend/src/services/notification_service.py`: accept job object, build title/body/data per push-payload.md job_failure schema, resolve all team members (collection belongs to team; all members have access), check preferences, create notification record, async deliver push
- [x] T028 [US3] Integrate notification trigger into JobCoordinatorService.fail_job() in `backend/src/services/job_coordinator_service.py`: after job status set to FAILED, call notification_service.notify_job_failure() via asyncio.create_task() (non-blocking)

**Checkpoint**: Job failures trigger push notifications to relevant users.

---

## Phase 6: User Story 4 — Receive Analysis Inflection Point Notifications (Priority: P1)

**Goal**: Push notification delivered when analysis detects actual changes (new report generated, NOT no-change), with issue delta

**Independent Test**: Complete a job with new results (no_change_copy=false) and verify notification. Complete a no-change job and verify NO notification.

**Depends on**: US2 (push subscription must exist)

### Implementation for User Story 4

- [x] T029 [US4] Add notify_inflection_point() method to NotificationService in `backend/src/services/notification_service.py`: accept job and result objects, calculate issue_delta from previous result if available, build title/body/data per push-payload.md inflection_point schema, resolve all team members, check preferences, create notification record, async deliver push
- [x] T030 [US4] Integrate notification trigger into JobCoordinatorService.complete_job() in `backend/src/services/job_coordinator_service.py`: ONLY when result has status=COMPLETED and no_change_copy=false, call notification_service.notify_inflection_point() via asyncio.create_task(). Do NOT trigger in complete_job_no_change().

**Checkpoint**: Inflection point notifications work. No-change results do not trigger notifications.

---

## Phase 7: User Story 5 — Configure Notification Preferences (Priority: P2)

**Goal**: Users can granularly control which notification categories they receive, with preferences synced across devices

**Independent Test**: Toggle categories on/off on Profile page, verify changes persist across page refresh, verify disabled categories suppress notifications

**Depends on**: US2 (preferences UI already placed, this phase refines behavior and validation)

### Implementation for User Story 5

- [x] T031 [US5] Add default preference initialization logic in `backend/src/services/notification_service.py`: when user first enables notifications (enabled goes from false→true), populate all default values per data-model.md (all categories true except retry_warning false, deadline_days_before=3, timezone from request or fallback to "UTC")
- [x] T032 [US5] Add preference validation in PUT /preferences endpoint in `backend/src/api/notifications.py`: validate deadline_days_before range (1-30), validate timezone is a valid IANA timezone identifier (use `zoneinfo.available_timezones()` from Python 3.9+ stdlib), ensure partial updates merge with existing preferences (not replace), return updated preferences

**Checkpoint**: Notification preferences fully functional with defaults, validation, and cross-device sync.

---

## Phase 8: User Story 6 — Receive Agent Status Notifications (Priority: P2)

**Goal**: Push notifications for agent pool state changes: all offline, error, recovery — with debouncing

**Independent Test**: Simulate agent going offline (all agents), verify pool-offline notification. Bring agent back, verify recovery notification. Trigger rapid flapping, verify debounce.

**Depends on**: US2 (push subscription must exist)

### Implementation for User Story 6

- [x] T033 [US6] Add notify_agent_status() method to NotificationService in `backend/src/services/notification_service.py`: accept agent, team, and transition type (pool_offline, agent_error, pool_recovery), build title/body/data per push-payload.md agent status schemas, resolve all team members, check preferences, debounce within 5-minute window per agent (track last notification timestamp per agent+type in memory or DB), create notification record, async deliver push
- [x] T034 [US6] Integrate agent notification triggers into AgentService in `backend/src/services/agent_service.py`: in check_offline_agents() — after marking agents offline, check if pool is now empty and trigger pool_offline notification; in process_heartbeat() — detect ERROR status and trigger agent_error, detect ONLINE transition from all-offline state and trigger pool_recovery
- [x] T035 [US6] Implement dead agent safety net background task in `backend/src/main.py`: FastAPI startup event creates asyncio task with 120-second loop, queries all agents across all teams WHERE status='ONLINE' AND last_heartbeat < cutoff, forces OFFLINE, releases jobs to PENDING, triggers agent status notifications per affected team. Must be idempotent (no duplicate notifications for already-offline agents).

**Checkpoint**: Agent status notifications work across all three detection layers (graceful shutdown, heartbeat timeout, dead agent safety net).

---

## Phase 9: User Story 7 — Receive Deadline Reminder Notifications (Priority: P3)

**Goal**: Daily deadline checks via agent job system, with configurable reminder timing, idempotent delivery, and backfill

**Independent Test**: Create event with deadline 3 days away, run deadline_check job, verify reminder notification. Run again, verify no duplicate. Simulate outage and verify backfill.

**Depends on**: US2 (push subscription), US5 (deadline_days_before preference)

### Implementation for User Story 7

- [x] T036 [US7] Add deadline_check job type support: register `DEADLINE_CHECK` in `ToolType` enum (`backend/src/schemas/tools.py`), add hourly `deadline_check_scheduler()` background task in `backend/src/main.py` following `dead_agent_safety_net()` pattern
- [x] T037 [US7] Implement deadline check execution logic in `backend/src/services/notification_service.py`: `check_deadlines(team_id)` queries events WHERE team_id=? AND deadline_date BETWEEN today AND today+30 AND status NOT IN (completed, cancelled) AND deleted_at IS NULL, calculates days until deadline per user's deadline_days_before preference and timezone, deduplicates via existing notification data->>event_guid + data->>days_before, sends push via `send_notification()`
- [x] T038 [US7] Add deadline check API endpoint in `backend/src/api/notifications.py`: POST /api/notifications/deadline-check — authenticated endpoint that calls `check_deadlines(team_id)`, returns `{"sent_count": N}`, idempotent

**Checkpoint**: Deadline reminders work via agent job system. Idempotent. Backfill window catches missed checks.

---

## Phase 10: User Story 8 — Receive Retry Warning Notifications (Priority: P3)

**Goal**: Push notification when a job reaches its final retry attempt (disabled by default)

**Independent Test**: Enable retry_warning preference, trigger a job that reaches final retry, verify warning notification. Verify default-off behavior.

**Depends on**: US2 (push subscription), US5 (retry_warning preference disabled by default)

### Implementation for User Story 8

- [x] T039 [US8] Add notify_retry_warning() method to NotificationService in `backend/src/services/notification_service.py`: accepts job object, builds title/body/data per push-payload.md retry_warning schema, resolves all team members, checks preferences (retry_warning disabled by default), creates notification record, delivers push
- [x] T040 [US8] Integrate retry warning trigger into agent job release logic in `backend/src/services/agent_service.py`: in `_release_agent_jobs()`, after `prepare_retry()`, detects when `retry_count == max_retries - 1` (final attempt), calls `notify_retry_warning(job)` with non-blocking error handling

**Checkpoint**: Retry warnings delivered on final attempt. Default-off respected.

---

## Phase 11: User Story 9 — View Notification History (Priority: P3)

**Goal**: In-app notification panel accessible from bell icon, with unread count badge, mark-as-read, and auto-cleanup

**Independent Test**: Trigger notifications, click bell icon, verify panel shows recent 20 notifications with correct details. Click notification, verify marked as read and count decreases. Verify 30-day auto-cleanup.

**Depends on**: Phase 2 foundational (Notification model + API already exist)

### Implementation for User Story 9

- [x] T041 [P] [US9] Create useNotifications hook in `frontend/src/hooks/useNotifications.ts`: fetch notification list (GET /notifications with pagination), fetch unread count (GET /unread-count), mark as read (POST /{guid}/read), auto-refresh unread count on interval (30 seconds), loading/error states
- [x] T042 [US9] Create NotificationPanel component in `frontend/src/components/notifications/NotificationPanel.tsx`: Popover/dropdown triggered by bell icon click, renders list of notifications with category icon, title, body, relative timestamp, read/unread indicator. Click navigates to data.url and marks as read. Empty state when no notifications. Uses shadcn/ui Popover, ScrollArea, Badge.
- [x] T043 [US9] Integrate NotificationPanel into TopHeader in `frontend/src/components/layout/TopHeader.tsx`: replace hardcoded bell badge with dynamic unread count from useNotifications hook, attach NotificationPanel popover to bell button, hide badge when count is 0
- [x] T044 [US9] Add notification cleanup logic in `backend/src/services/notification_service.py`: delete_old_notifications() method that removes notifications WHERE created_at < NOW() - 30 days, called from the dead agent safety net loop (piggyback on existing periodic task) or as a separate daily cleanup

**Checkpoint**: Full notification history UI working. Bell badge dynamic. Read/unread tracking. Auto-cleanup.

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, graceful degradation, and final integration

- [ ] T045 Handle push subscription expiry and 410 Gone responses in push delivery logic in `backend/src/services/notification_service.py`: on 410 response, delete subscription from DB; on expired subscription, skip and log
- [ ] T046 Add browser permission state detection in `frontend/src/hooks/usePushSubscription.ts`: check `Notification.permission` on mount, detect external permission revocation, sync UI state accordingly
- [ ] T047 [P] Add graceful degradation for unsupported browsers in `frontend/src/components/profile/NotificationPreferences.tsx`: check for `'serviceWorker' in navigator` and `'PushManager' in window`, hide notification features and show informational message on unsupported browsers
- [ ] T048 [P] Add structured logging for notification delivery in `backend/src/services/notification_service.py`: log each delivery attempt (user_guid, category, success/failure, endpoint), log subscription cleanup events, log preference checks
- [ ] T049 Verify multi-tenant isolation in notification endpoints: ensure all queries filter by ctx.team_id, ensure cross-team notification GUID access returns 404, review all service methods for team_id parameter usage

---

## Phase 13: Tests (Constitution Principle II)

**Purpose**: Automated test coverage for all new services, API endpoints, hooks, and components. Required by Constitution Principle II: "All features MUST have test coverage."

### Backend Unit Tests

- [ ] T050 [P] Create NotificationService unit tests in `backend/tests/unit/test_notification_service.py`: test create_notification, deliver_push (mock pywebpush), check_preference, get_user_preferences, update_preferences, get_default_preferences, send_notification orchestration (prefs → create → async push), default preference initialization on first enable, 410 Gone subscription removal, retry with exponential backoff (3 attempts). Covers FR-017, FR-019, FR-020, FR-011, FR-016
- [ ] T051 [P] Create PushSubscriptionService unit tests in `backend/tests/unit/test_push_subscription_service.py`: test create_subscription (upsert by endpoint), remove_subscription (by endpoint + user), list_subscriptions (by user), cleanup_expired, remove_invalid (410 Gone). Covers FR-008, FR-009, FR-010, FR-011

### Backend API Integration Tests

- [ ] T052 Create notification API integration tests in `backend/tests/unit/test_notifications_api.py`: test all 8 endpoints per contracts/api.yaml — POST /subscribe (201, 400), DELETE /subscribe (204, 404), GET /status (200), GET /preferences (200), PUT /preferences (200, 400 for invalid deadline_days_before), GET /notifications (200 with pagination, category filter, unread_only), GET /unread-count (200), POST /{guid}/read (200, 404), GET /vapid-key (200). Test 401 on unauthenticated requests. Test multi-tenant isolation: cross-team notification GUID returns 404 (FR-050, FR-051). Depends on T050, T051

### Frontend Hook & Component Tests

- [ ] T053 [P] Create useNotifications hook tests in `frontend/src/hooks/useNotifications.test.ts`: test fetch notification list, fetch unread count, mark-as-read updates state, auto-refresh interval (30s), loading and error states. Mock notifications API service
- [ ] T054 Create NotificationPanel component tests in `frontend/src/components/notifications/NotificationPanel.test.tsx`: test renders notification list with category icons and relative timestamps, click marks as read and navigates, empty state message, read/unread visual indicator, popover open/close behavior. Depends on T053
- [ ] T055 Create NotificationPreferences component tests in `frontend/src/components/profile/NotificationPreferences.test.tsx`: test master toggle enables/disables all, per-category toggles, deadline days-before selector, permission denied state shows re-enable instructions, iOS not-installed state shows guidance, unsupported browser hides notification features (FR-054). Depends on T023

### Backend Trigger Integration Tests

- [ ] T056 [P] Create notification trigger tests for JobCoordinatorService in `backend/tests/unit/test_notification_triggers.py`: test fail_job() calls notify_job_failure (FR-023), complete_job() calls notify_inflection_point only when no_change_copy=false (FR-026), complete_job_no_change() does NOT trigger notification (FR-027), retry at max_retries-1 calls notify_retry_warning (FR-043), retry_warning respects default-off preference (FR-044). Mock NotificationService
- [ ] T057 [P] Create notification trigger tests for AgentService in `backend/tests/unit/test_agent_notification_triggers.py`: test check_offline_agents() triggers pool_offline when last agent goes offline (FR-030), process_heartbeat() triggers agent_error on ERROR status (FR-031), process_heartbeat() triggers pool_recovery on first agent back online (FR-032), debounce within 5-minute window suppresses duplicate (FR-033), dead agent safety net forces OFFLINE and triggers notifications (FR-035, FR-036). Mock NotificationService

**Checkpoint**: All backend services, API endpoints, frontend hooks, and components have automated test coverage. Constitution Principle II satisfied.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phase 3 (US1 - PWA)**: Depends on Phase 2, no other story dependencies
- **Phase 4 (US2 - Push Subscribe)**: Depends on Phase 2 + US1 (service worker required for PushManager)
- **Phase 5 (US3 - Job Failures)**: Depends on Phase 2 + US2 (subscription required)
- **Phase 6 (US4 - Inflection Points)**: Depends on Phase 2 + US2 (subscription required)
- **Phase 7 (US5 - Preferences)**: Depends on Phase 2 + US2 (preferences UI already placed in US2)
- **Phase 8 (US6 - Agent Status)**: Depends on Phase 2 + US2 (subscription required)
- **Phase 9 (US7 - Deadlines)**: Depends on Phase 2 + US2 + US5 (deadline_days_before preference)
- **Phase 10 (US8 - Retry Warnings)**: Depends on Phase 2 + US2 + US5 (retry_warning preference)
- **Phase 11 (US9 - History)**: Depends on Phase 2 (foundational model + API)
- **Phase 12 (Polish)**: Depends on all desired user stories being complete
- **Phase 13 (Tests)**: Backend unit tests (T050-T051) can start after Phase 2. API tests (T052) after T050+T051. Frontend tests (T053-T055) after Phase 4. Trigger tests (T056-T057) after Phases 5-8

### User Story Dependencies

```text
Phase 1 (Setup) → Phase 2 (Foundational)
                        │
                        ├─→ US1 (PWA Install)
                        │       │
                        │       └─→ US2 (Push Subscribe)
                        │               │
                        │               ├─→ US3 (Job Failures)     [P1, can parallel with US4]
                        │               ├─→ US4 (Inflection Points) [P1, can parallel with US3]
                        │               ├─→ US5 (Preferences)       [P2]
                        │               │       │
                        │               │       ├─→ US7 (Deadlines)      [P3]
                        │               │       └─→ US8 (Retry Warnings) [P3]
                        │               │
                        │               └─→ US6 (Agent Status)     [P2, can parallel with US5]
                        │
                        └─→ US9 (History) [P3, independent of push stories]
```

### Within Each User Story

- Models before services
- Services before endpoints/UI
- Backend before frontend (for API-dependent components)
- Core implementation before edge cases

### Parallel Opportunities

- **Phase 2**: T006 and T007 (models) can run in parallel. T011 and T012 (services) can run in parallel after models.
- **Phase 3**: T017 and T018 (icons + meta tags) can run in parallel.
- **Phase 4**: T022 and T023 (hooks) can run in parallel.
- **Phase 5 + Phase 6**: US3 and US4 can run in parallel (both only modify NotificationService + different coordinator methods).
- **Phase 7 + Phase 8**: US5 and US6 can run in parallel (different services).
- **Phase 11**: US9 can start as soon as Phase 2 is complete (only needs Notification model + API).
- **Phase 13**: T050 and T051 (backend unit tests) can run in parallel. T053, T056, and T057 can run in parallel. Frontend tests (T053-T055) can run in parallel with backend trigger tests (T056-T057).

---

## Parallel Example: After Phase 2

```text
# These can all launch in parallel after Foundational is complete:

Stream A (PWA → Push):
  US1 (T017-T021) → US2 (T022-T026) → US3 (T027-T028) + US4 (T029-T030)

Stream B (History — independent):
  US9 (T041-T044)
```

---

## Implementation Strategy

### MVP First (User Stories 1-4)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: US1 — PWA Installation
4. Complete Phase 4: US2 — Push Subscription
5. Complete Phase 5: US3 — Job Failure Notifications
6. Complete Phase 6: US4 — Inflection Point Notifications
7. **STOP and VALIDATE**: Test all P1 stories independently
8. Deploy/demo — users can install PWA and receive failure + inflection notifications

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. US1 → Installable PWA (value: fast loading, standalone window)
3. US2 → Push channel established (value: subscription infrastructure)
4. US3 + US4 → Core notifications (value: failure + change alerts)
5. US5 + US6 → Preferences + agent alerts (value: user control + infrastructure awareness)
6. US7 + US8 → Deadline + retry (value: proactive reminders)
7. US9 → History panel (value: missed notification recovery)
8. Polish → Production-ready

### Parallel Team Strategy

With multiple developers after Phase 2:

- **Developer A**: US1 → US2 → US3 + US4 (PWA + push pipeline)
- **Developer B**: US9 (notification history — independent) → US5 (preferences refinement)
- **Developer C**: US6 (agent status) → US7 + US8 (deadlines + retry)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- US9 (History) is uniquely independent — can start as soon as Phase 2 completes, parallel with US1
