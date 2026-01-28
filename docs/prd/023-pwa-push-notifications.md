# PRD: Progressive Web Application with Push Notifications

**Issue**: TBD
**Status**: Draft
**Created**: 2026-01-28
**Last Updated**: 2026-01-28
**Related Documents**:
- [Domain Model](../domain-model.md)
- [021-distributed-agent-architecture.md](./021-distributed-agent-architecture.md) (Agent system)
- [022-storage-optimization-analysis-results.md](./022-storage-optimization-analysis-results.md) (Input State & transitions)
- [019-user-tenancy.md](./019-user-tenancy.md) (Multi-tenancy)

---

## Executive Summary

This PRD defines the requirements for converting ShutterSense.ai from a Single Page Application (SPA) into a Progressive Web Application (PWA) with push notification capabilities. The PWA will enable users to receive timely notifications on their devices (desktop and mobile) for high-value events such as job failures, analysis inflexion points, agent status changes, and upcoming event deadlines.

### Key Design Decisions

1. **PWA Foundation**: Implement service worker, web app manifest, and offline capabilities using `vite-plugin-pwa`
2. **Selective Notifications**: Only notify for high-value events (failures, inflexion points, agent status) - NOT routine job completions
3. **Inflexion Point Detection**: Trigger notifications when analysis results show actual changes (new HTML reports), not NO_CHANGE results
4. **User Control**: Granular notification preferences per notification category
5. **Multi-Tenant Isolation**: Push subscriptions scoped to user and team for data security
6. **iOS Compatibility**: Support iOS 16.4+ with "Add to Home Screen" PWA installation

### Primary Goals

1. Enable push notifications for critical system events
2. Improve user engagement through timely, relevant notifications
3. Support mobile workflows with installable PWA

### Secondary Goals

1. Offline access to cached application shell
2. Reduce server polling with push-based updates
3. Improve perceived performance with service worker caching

### Non-Goals (v1)

1. Full offline functionality (viewing cached analysis results)
2. Background sync for offline actions
3. Native app development (React Native, Flutter)
4. Email/SMS notification channels

---

## Background

### Current State

The ShutterSense.ai frontend is a React SPA that:
- Requires an active browser tab to receive updates
- Uses WebSocket connections for real-time job progress
- Displays toast notifications only when the app is open
- Has no offline capabilities
- Cannot be "installed" as a standalone app

**Existing Real-Time Infrastructure:**
- WebSocket manager (`backend/src/utils/websocket.py`) handles live updates
- `useAgentPoolStatus` hook monitors agent availability
- `useJobProgress` hook tracks individual job progress
- `sonner` library provides in-app toast notifications

### Problem Statement

Users miss critical events when not actively using the application:

1. **Job Failures**: Failed analysis jobs require attention but go unnoticed until next login
2. **Collection Changes**: When a collection's analysis shows new issues (inflexion point), users want to know immediately
3. **Agent Offline**: If all agents go offline, no jobs can execute - users should be alerted
4. **Deadline Reminders**: Event deadlines approach without notification

Current workarounds are inadequate:
- Keeping browser tab open drains battery and bandwidth
- Manual checking is tedious and often too late
- No mobile notification support at all

### Strategic Context

PWA push notifications provide:
- **Timely Awareness**: Users learn of issues when they happen, not hours later
- **Mobile Reach**: Photographers often work away from their desks
- **Engagement**: Proactive notifications bring users back for meaningful actions
- **Cost Efficiency**: No app store fees or native development costs
- **Cross-Platform**: Single implementation for desktop and mobile

---

## Goals

### Primary Goals

1. **PWA Foundation**: Convert SPA to installable PWA with service worker and manifest
2. **Push Infrastructure**: Implement Web Push API with VAPID authentication
3. **High-Value Notifications**: Notify only for actionable events (failures, inflexion points, agent issues)
4. **User Preferences**: Allow users to control which notification categories they receive
5. **Multi-Tenant Security**: Ensure notifications respect team boundaries

### Secondary Goals

1. **Offline Shell**: Cache application shell for instant loading
2. **Notification History**: Store recent notifications for in-app review
3. **Quiet Hours**: Allow users to set notification-free time periods
4. **Badge Count**: Show unread notification count on PWA icon

### Non-Goals (v1)

1. **Full Offline Mode**: Not caching analysis data or reports
2. **Notification Scheduling**: All notifications are event-driven, not scheduled
3. **Rich Media**: No images or action buttons in notifications (v1 keeps it simple)
4. **Email Fallback**: Push-only, no email notification channel
5. **Bulk Operations**: No "mark all read" or notification management

---

## User Personas

### Primary: Photographer / Collection Owner (Morgan)

- **Current Pain**: Misses job failures; discovers issues hours or days later
- **Desired Outcome**: Get notified immediately when something needs attention
- **This PRD Delivers**: Push notifications for failures, collection changes, and deadlines

### Secondary: Team Administrator (Jordan)

- **Current Pain**: Agents go offline without notice; jobs pile up
- **Desired Outcome**: Know immediately when infrastructure issues occur
- **This PRD Delivers**: Agent status notifications, aggregated failure alerts

### Tertiary: Mobile User (Taylor)

- **Current Pain**: Cannot receive updates when away from desk
- **Desired Outcome**: Install app on phone, receive notifications anywhere
- **This PRD Delivers**: Installable PWA with mobile push support

---

## Notification Categories

### Category 1: Job Failures (Priority: P0 - Critical)

**Trigger**: Job status changes to `FAILED` after all retry attempts exhausted

**Notification Content**:
- Title: "Analysis Failed"
- Body: "{Tool} analysis of {Collection} failed: {Error Summary}"
- Click Action: Navigate to job details page

**Rationale**: Failed jobs require user intervention; immediate notification prevents delays

**Example**:
```
Title: Analysis Failed
Body: PhotoStats analysis of "2024 Wedding Photos" failed: Connection timeout
```

---

### Category 2: Analysis Inflexion Points (Priority: P0 - Critical)

**Trigger**: Analysis result created with `status=COMPLETED` AND `no_change_copy=false` (a new HTML report was generated, indicating the collection state changed)

**NOT Triggered**: When `status=NO_CHANGE` (no new report, collection unchanged)

**Notification Content**:
- Title: "New Analysis Results"
- Body: "{Tool} found changes in {Collection}: {Issue Delta Summary}"
- Click Action: Navigate to analysis result / report

**Rationale**: Users want to know when their collection status actually changes, not when routine checks find nothing new. The inflexion point represents actionable information.

**Example**:
```
Title: New Analysis Results
Body: PhotoStats found changes in "Client Wedding": 12 new orphaned files detected
```

**Technical Note**: This leverages the Input State tracking from PRD-022. The key differentiator is:
- `no_change_copy=false` + `status=COMPLETED` = New report generated = Notify
- `no_change_copy=true` + `status=NO_CHANGE` = Identical to previous = Do NOT notify

---

### Category 3: Agent Status Changes (Priority: P1)

**Triggers**:
- **All Agents Offline**: Last online agent transitions to `OFFLINE` status
- **Agent Error**: Any agent transitions to `ERROR` status
- **Agent Revoked**: Agent is administratively revoked
- **Agent Recovery**: First agent comes back online after all were offline

**Notification Content**:
- Title: "Agent Status Alert"
- Body: Varies by trigger type

**Examples**:
```
Title: Agent Pool Offline
Body: All agents are offline. Jobs cannot be processed until an agent reconnects.
```

```
Title: Agent Error
Body: Agent "Home Server" reported an error: Disk space critical
```

```
Title: Agents Available
Body: Agent "Home Server" is back online. Job processing has resumed.
```

**Rationale**: Agent availability directly impacts job execution. Users need to know when processing is blocked.

---

### Category 4: Event Deadlines (Priority: P2)

**Trigger**: Configurable time before event deadline (1 day, 3 days, 1 week)

**Notification Content**:
- Title: "Deadline Approaching"
- Body: "{Event Name} deadline in {Time Remaining}"
- Click Action: Navigate to event details

**Example**:
```
Title: Deadline Approaching
Body: "Smith Wedding - Final Delivery" deadline in 3 days
```

**Rationale**: Event deadlines represent commitments to clients; reminders prevent missed deliveries.

**Technical Note**: Requires a scheduled job to check deadlines and trigger notifications. Consider running during job creation cleanup cycle or as a lightweight background process.

---

### Category 5: Retry Exhaustion Warning (Priority: P2)

**Trigger**: Job reaches final retry attempt (`retry_count = max_retries - 1`)

**Notification Content**:
- Title: "Job Retry Warning"
- Body: "{Tool} analysis of {Collection} is on final retry attempt"
- Click Action: Navigate to job details

**Rationale**: Gives users advance warning before a job fails completely, allowing intervention.

---

## User Stories

### User Story 1: PWA Installation (Priority: P0 - Critical)

**As** a user
**I want to** install ShutterSense as an app on my device
**So that** I can access it quickly and receive notifications

**Acceptance Criteria:**
- Web App Manifest provides app metadata (name, icons, theme)
- "Install" prompt appears in supported browsers
- Installed PWA launches in standalone window (no browser chrome)
- PWA icon appears in OS application launcher
- PWA works on desktop (Chrome, Edge, Firefox) and mobile (Chrome, Safari 16.4+)

**Technical Notes:**
- Implement via `vite-plugin-pwa` with `registerType: 'autoUpdate'`
- Manifest at `/manifest.webmanifest`
- Icons: 192x192 and 512x512 PNG, maskable versions for Android

---

### User Story 2: Push Notification Permission (Priority: P0 - Critical)

**As** a user
**I want to** grant permission for push notifications
**So that** I can receive updates when not using the app

**Acceptance Criteria:**
- Permission prompt appears after user opts in (not on first visit)
- Clear explanation of what notifications will be sent
- User can dismiss without granting permission
- Permission state persisted and respected
- Denied permission shows alternative (check app manually)

**Technical Notes:**
- Request permission via `Notification.requestPermission()`
- Only request after user clicks "Enable Notifications" button
- Store permission state in localStorage for UI consistency

---

### User Story 3: Push Subscription Management (Priority: P0 - Critical)

**As** the system
**I want to** manage push subscriptions for each user/device
**So that** I can deliver notifications to the correct endpoints

**Acceptance Criteria:**
- Subscription created when user enables notifications
- Subscription stored with user ID, team ID, and device identifier
- Multiple devices per user supported
- Subscription removed when user disables notifications
- Expired/invalid subscriptions cleaned up automatically

**Technical Notes:**
- Use Web Push API with VAPID keys
- Store in new `push_subscriptions` table
- Endpoint, p256dh key, and auth secret per subscription
- Device fingerprint via subscription endpoint hash

---

### User Story 4: Notification Preferences (Priority: P1)

**As** a user
**I want to** choose which types of notifications I receive
**So that** I only get alerts that matter to me

**Acceptance Criteria:**
- Settings page includes "Notifications" section
- Toggle for each notification category (Failures, Inflexion Points, Agents, Deadlines)
- All categories enabled by default
- Changes take effect immediately
- Settings synced across devices for same user

**Technical Notes:**
- Store as user-level Configuration entries
- Category: `notification_preferences`
- Keys: `job_failures`, `inflexion_points`, `agent_status`, `deadlines`
- Values: boolean

---

### User Story 5: Job Failure Notification (Priority: P0 - Critical)

**As** a user
**I want to** receive a notification when a job fails
**So that** I can investigate and retry if needed

**Acceptance Criteria:**
- Notification sent when job status becomes FAILED
- Notification shows tool name and collection name
- Notification shows brief error summary
- Clicking notification opens job details page
- Notification only sent if user has enabled failure notifications

**Technical Notes:**
- Trigger in `JobCoordinatorService.fail_job()`
- Check user preferences before sending
- Include job GUID in notification data for navigation

---

### User Story 6: Inflexion Point Notification (Priority: P0 - Critical)

**As** a user
**I want to** receive a notification when analysis results change
**So that** I can review new findings in my collections

**Acceptance Criteria:**
- Notification sent when result has `status=COMPLETED` AND `no_change_copy=false`
- NOT sent for `NO_CHANGE` results (identical to previous)
- Notification shows what changed (issue count delta if available)
- Clicking notification opens analysis result page
- Only sent to users with access to the collection

**Technical Notes:**
- Trigger in `JobCoordinatorService.complete_job()` (not `complete_job_no_change()`)
- Calculate delta from previous result's `issues_found`
- Filter by notification preferences

---

### User Story 7: Agent Status Notification (Priority: P1)

**As** a team administrator
**I want to** receive notifications about agent availability
**So that** I know when job processing is impacted

**Acceptance Criteria:**
- Notification when all agents go offline
- Notification when an agent enters ERROR state
- Notification when first agent comes back online (recovery)
- No notification spam for individual agent flapping (debounce)
- Only sent to users with agent status notifications enabled

**Technical Notes:**
- Trigger in `AgentService.check_offline_agents()` and `process_heartbeat()`
- Debounce: don't notify for same agent state within 5 minutes
- Track "pool offline" state to detect recovery

---

### User Story 8: Deadline Reminder Notification (Priority: P2)

**As** a user
**I want to** receive reminders before event deadlines
**So that** I don't miss important delivery dates

**Acceptance Criteria:**
- Notification sent at configured time before deadline (1 day, 3 days, 1 week)
- User can configure reminder timing in settings
- Only one reminder per deadline (don't repeat daily)
- Clicking notification opens event details
- Respects user's timezone for deadline calculation

**Technical Notes:**
- Requires scheduled check (during job cleanup or dedicated cron)
- Store `last_reminder_sent` to prevent duplicates
- Use event's `deadline_date` and `deadline_time` fields
- Calculate relative to user's configured timezone

---

### User Story 9: Notification History (Priority: P2)

**As** a user
**I want to** see a history of recent notifications
**So that** I can review what I missed

**Acceptance Criteria:**
- Notification bell icon in header shows unread count
- Clicking bell opens notification panel/dropdown
- Panel shows last 20 notifications
- Notifications marked as read when viewed
- "Mark all read" option available
- Notifications older than 30 days auto-deleted

**Technical Notes:**
- Store in new `notifications` table
- Fields: guid, user_id, team_id, category, title, body, data, read_at, created_at
- Poll or WebSocket for new notification indicator
- Consider separate from push (in-app notification history)

---

### User Story 10: Service Worker Caching (Priority: P1)

**As** a user
**I want to** the app to load quickly, even on slow connections
**So that** I can access ShutterSense efficiently

**Acceptance Criteria:**
- Application shell cached by service worker
- Static assets (JS, CSS, images) cached
- Cache updated when new version deployed
- User notified of available update
- Refresh loads new version

**Technical Notes:**
- Use Workbox `precacheAndRoute` for build assets
- Stale-while-revalidate for API responses (optional)
- Update notification via service worker lifecycle events

---

## Key Entities

### PushSubscription (New)

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto | Internal database ID |
| `guid` | String(35) | unique, not null | External identifier (prefix: `sub_`) |
| `user_id` | Integer | FK, not null | Owning user |
| `team_id` | Integer | FK, not null | User's team (for tenant isolation) |
| `endpoint` | String(500) | not null | Push service endpoint URL |
| `p256dh_key` | String(100) | not null | ECDH public key |
| `auth_key` | String(50) | not null | Auth secret |
| `device_name` | String(100) | nullable | User-friendly device name |
| `created_at` | DateTime | not null | Subscription creation time |
| `last_used_at` | DateTime | nullable | Last successful push delivery |
| `expires_at` | DateTime | nullable | Subscription expiration (from push service) |

**GUID Prefix**: `sub_` (add to domain model)

---

### Notification (New)

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto | Internal database ID |
| `guid` | String(35) | unique, not null | External identifier (prefix: `ntf_`) |
| `user_id` | Integer | FK, not null | Recipient user |
| `team_id` | Integer | FK, not null | User's team |
| `category` | String(30) | not null | Notification category |
| `title` | String(100) | not null | Notification title |
| `body` | String(500) | not null | Notification body |
| `data` | JSONB | nullable | Additional data (job_guid, result_guid, etc.) |
| `read_at` | DateTime | nullable | When user viewed notification |
| `created_at` | DateTime | not null | When notification was created |

**GUID Prefix**: `ntf_` (add to domain model)

**Category Values**: `job_failure`, `inflexion_point`, `agent_status`, `deadline`, `retry_warning`

---

### Configuration Entries (User-Level)

New user-level notification preferences:

| Category | Key | Type | Default | Description |
|----------|-----|------|---------|-------------|
| `notification_preferences` | `enabled` | Boolean | false | Master enable/disable |
| `notification_preferences` | `job_failures` | Boolean | true | Job failure notifications |
| `notification_preferences` | `inflexion_points` | Boolean | true | Analysis change notifications |
| `notification_preferences` | `agent_status` | Boolean | true | Agent availability notifications |
| `notification_preferences` | `deadlines` | Boolean | true | Event deadline reminders |
| `notification_preferences` | `deadline_days_before` | Integer | 3 | Days before deadline to remind |

---

## Requirements

### Functional Requirements

#### FR-100: PWA Infrastructure

- **FR-100.1**: Generate Web App Manifest with app metadata
- **FR-100.2**: Include icons in required sizes (192x192, 512x512, maskable)
- **FR-100.3**: Register service worker on app load
- **FR-100.4**: Service worker caches application shell and static assets
- **FR-100.5**: Service worker handles push events
- **FR-100.6**: Service worker handles notification click events
- **FR-100.7**: Display update prompt when new version available
- **FR-100.8**: Add PWA meta tags to index.html (theme-color, apple-mobile-web-app-capable)

#### FR-200: Push Subscription Management

- **FR-200.1**: Request notification permission only after user opt-in
- **FR-200.2**: Create push subscription using Web Push API
- **FR-200.3**: Generate VAPID keys for server-side push delivery
- **FR-200.4**: Store subscription details in database (endpoint, keys)
- **FR-200.5**: Associate subscription with authenticated user
- **FR-200.6**: Support multiple subscriptions per user (multiple devices)
- **FR-200.7**: Remove subscription when user disables notifications
- **FR-200.8**: Handle expired/invalid subscriptions gracefully
- **FR-200.9**: Provide API endpoint to check subscription status

#### FR-300: Notification Preferences

- **FR-300.1**: Store notification preferences at user level
- **FR-300.2**: Provide UI to toggle each notification category
- **FR-300.3**: Master toggle to enable/disable all notifications
- **FR-300.4**: Preferences checked before sending any notification
- **FR-300.5**: Default all categories to enabled when user first enables notifications
- **FR-300.6**: Sync preferences across devices (server-side storage)

#### FR-400: Notification Delivery

- **FR-400.1**: Deliver push notifications using pywebpush library
- **FR-400.2**: Queue notifications to prevent blocking main request
- **FR-400.3**: Retry failed deliveries with exponential backoff
- **FR-400.4**: Remove subscription after repeated failures (410 Gone)
- **FR-400.5**: Include notification data for click handling (navigation URL)
- **FR-400.6**: Log notification delivery for debugging
- **FR-400.7**: Respect rate limits from push services

#### FR-500: Job Failure Notifications

- **FR-500.1**: Trigger notification when job status becomes FAILED
- **FR-500.2**: Include job details (tool, collection, error summary)
- **FR-500.3**: Send to all users with access to the collection
- **FR-500.4**: Check user preferences before sending
- **FR-500.5**: Store in notification history

#### FR-600: Inflexion Point Notifications

- **FR-600.1**: Trigger when `complete_job()` creates result (not `complete_job_no_change()`)
- **FR-600.2**: Only notify for `status=COMPLETED` AND `no_change_copy=false`
- **FR-600.3**: Include issue count delta when available
- **FR-600.4**: Send to users with access to the collection
- **FR-600.5**: Check user preferences before sending
- **FR-600.6**: Store in notification history

#### FR-700: Agent Status Notifications

- **FR-700.1**: Notify when all agents transition to OFFLINE
- **FR-700.2**: Notify when any agent enters ERROR state
- **FR-700.3**: Notify when first agent recovers from all-offline state
- **FR-700.4**: Debounce notifications (5-minute window per agent)
- **FR-700.5**: Send to all users in the team
- **FR-700.6**: Check user preferences before sending

#### FR-800: Deadline Notifications

- **FR-800.1**: Check for upcoming deadlines on schedule (e.g., during cleanup)
- **FR-800.2**: Notify based on user's configured days-before preference
- **FR-800.3**: Send only one reminder per deadline
- **FR-800.4**: Use user's timezone for deadline calculation
- **FR-800.5**: Check user preferences before sending
- **FR-800.6**: Store in notification history

#### FR-900: Notification History

- **FR-900.1**: Store all sent notifications in database
- **FR-900.2**: Provide API to list user's notifications
- **FR-900.3**: Track read/unread status
- **FR-900.4**: Provide unread count for UI badge
- **FR-900.5**: Auto-delete notifications older than 30 days
- **FR-900.6**: Mark notification as read when user views it

---

### Non-Functional Requirements

#### NFR-100: Performance

- **NFR-100.1**: Service worker installation < 3 seconds
- **NFR-100.2**: Notification delivery < 5 seconds from trigger
- **NFR-100.3**: Notification history query < 100ms
- **NFR-100.4**: Push subscription creation < 2 seconds

#### NFR-200: Reliability

- **NFR-200.1**: Graceful degradation when push not supported
- **NFR-200.2**: Retry failed push deliveries (max 3 attempts)
- **NFR-200.3**: Handle push service outages without data loss
- **NFR-200.4**: Service worker updates don't disrupt active sessions

#### NFR-300: Security

- **NFR-300.1**: VAPID keys stored securely (not in code)
- **NFR-300.2**: Subscription endpoints validated before use
- **NFR-300.3**: Notifications scoped to user's team (no cross-tenant)
- **NFR-300.4**: Push payload encrypted (standard Web Push encryption)

#### NFR-400: Compatibility

- **NFR-400.1**: Desktop: Chrome 50+, Firefox 44+, Edge 17+
- **NFR-400.2**: Android: Chrome 50+, Firefox 44+
- **NFR-400.3**: iOS: Safari 16.4+ (PWA installed to home screen required)
- **NFR-400.4**: Graceful fallback for unsupported browsers

#### NFR-500: Testing

- **NFR-500.1**: Unit tests for notification service
- **NFR-500.2**: Integration tests for push subscription flow
- **NFR-500.3**: E2E tests for notification preferences UI
- **NFR-500.4**: Manual testing on iOS PWA

---

## Technical Approach

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Service Worker                            ││
│  │  - Caches application shell                                  ││
│  │  - Handles push events                                       ││
│  │  - Displays notifications                                    ││
│  │  - Routes notification clicks                                ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                 Notification Manager                         ││
│  │  - Requests permission                                       ││
│  │  - Manages subscription                                      ││
│  │  - Syncs with backend                                        ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Notification Settings UI                        ││
│  │  - Enable/disable toggle                                     ││
│  │  - Category preferences                                      ││
│  │  - Notification history panel                                ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼ REST API
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │               NotificationService (New)                      ││
│  │  - Send push to user's subscriptions                         ││
│  │  - Check preferences before sending                          ││
│  │  - Store in notification history                             ││
│  │  - Handle delivery failures                                  ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │            PushSubscriptionService (New)                     ││
│  │  - CRUD for subscriptions                                    ││
│  │  - Validate endpoints                                        ││
│  │  - Clean expired subscriptions                               ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │        Integration Points (Existing Services)                ││
│  │  JobCoordinatorService.fail_job()     → NotificationService  ││
│  │  JobCoordinatorService.complete_job() → NotificationService  ││
│  │  AgentService.check_offline_agents()  → NotificationService  ││
│  │  (Deadline check - new scheduled)     → NotificationService  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Push Services                             │
│  - Firebase Cloud Messaging (Chrome, Android)                    │
│  - Mozilla Push Service (Firefox)                                │
│  - Apple Push Notification service (Safari/iOS)                  │
│  - Windows Push Notification Services (Edge)                     │
└─────────────────────────────────────────────────────────────────┘
```

### Service Worker Structure

```typescript
// service-worker.ts (generated by vite-plugin-pwa with custom additions)

// Precache application shell
precacheAndRoute(self.__WB_MANIFEST)

// Handle push events
self.addEventListener('push', (event) => {
  const data = event.data?.json() ?? {}

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/icons/icon-192x192.png',
      badge: '/icons/badge-72x72.png',
      data: data.data, // Contains navigation URL
      tag: data.tag,   // Prevents duplicate notifications
    })
  )
})

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  event.notification.close()

  const url = event.notification.data?.url ?? '/'

  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((clientList) => {
      // Focus existing window or open new one
      for (const client of clientList) {
        if (client.url === url && 'focus' in client) {
          return client.focus()
        }
      }
      return clients.openWindow(url)
    })
  )
})
```

### Push Subscription Flow

```
User                           Frontend                         Backend
  │                               │                                │
  │  Click "Enable Notifications" │                                │
  │──────────────────────────────>│                                │
  │                               │                                │
  │                               │  Notification.requestPermission()
  │                               │────────────────>│               │
  │                               │                 │               │
  │  <Grant Permission>           │<────────────────│               │
  │                               │                                │
  │                               │  PushManager.subscribe({        │
  │                               │    applicationServerKey: VAPID_PUBLIC
  │                               │  })                             │
  │                               │                                │
  │                               │  POST /api/notifications/subscribe
  │                               │  {                              │
  │                               │    endpoint: "https://fcm...",  │
  │                               │    keys: { p256dh, auth }       │
  │                               │  }                              │
  │                               │────────────────────────────────>│
  │                               │                                │
  │                               │                                │ Store subscription
  │                               │                                │ Associate with user
  │                               │                                │
  │                               │  200 OK { guid: "sub_..." }    │
  │                               │<────────────────────────────────│
  │                               │                                │
  │  "Notifications enabled"      │                                │
  │<──────────────────────────────│                                │
```

### Notification Delivery Flow

```
Event Trigger                    Backend                        Push Service
  │                                │                                │
  │  Job fails                     │                                │
  │───────────────────────────────>│                                │
  │                                │                                │
  │                                │ Get affected users             │
  │                                │ Check preferences              │
  │                                │ Get subscriptions              │
  │                                │                                │
  │                                │ For each subscription:         │
  │                                │   POST {endpoint}              │
  │                                │   Authorization: vapid ...     │
  │                                │   Body: encrypted payload      │
  │                                │────────────────────────────────>│
  │                                │                                │
  │                                │  201 Created / 410 Gone       │
  │                                │<────────────────────────────────│
  │                                │                                │
  │                                │ Store in notification history  │
  │                                │ Update last_used_at            │
  │                                │ Remove if 410 Gone             │
```

### Inflexion Point Detection Logic

```python
# In JobCoordinatorService

def complete_job(self, job_guid: str, result_data: dict, ...):
    """Complete job with actual results (inflexion point)."""

    # ... existing completion logic ...

    result = AnalysisResult(
        status=ResultStatus.COMPLETED,
        no_change_copy=False,  # This is a real completion
        report_html=result_data.get('report_html'),
        # ...
    )

    # Calculate issue delta for notification
    previous_result = self._get_previous_result(job)
    issue_delta = None
    if previous_result:
        issue_delta = result.issues_found - previous_result.issues_found

    # Trigger notification (inflexion point detected)
    self.notification_service.notify_inflexion_point(
        job=job,
        result=result,
        issue_delta=issue_delta
    )

    return result


def complete_job_no_change(self, job_guid: str, referenced_result_guid: str, ...):
    """Complete job with no-change status (NOT an inflexion point)."""

    # ... existing no-change logic ...

    result = AnalysisResult(
        status=ResultStatus.NO_CHANGE,
        no_change_copy=True,  # This is a reference
        download_report_from=referenced_result_guid,
        # ...
    )

    # NO notification - this is not an inflexion point

    return result
```

### API Endpoints

```
POST   /api/notifications/subscribe     - Register push subscription
DELETE /api/notifications/subscribe     - Remove push subscription
GET    /api/notifications/status        - Check subscription status

GET    /api/notifications/preferences   - Get notification preferences
PUT    /api/notifications/preferences   - Update notification preferences

GET    /api/notifications               - List notification history
GET    /api/notifications/unread-count  - Get unread count for badge
POST   /api/notifications/{guid}/read   - Mark notification as read

POST   /api/notifications/test          - Send test notification (dev only)
```

### Database Migration

```sql
-- Migration: Add push subscription and notification tables

CREATE TABLE push_subscriptions (
    id SERIAL PRIMARY KEY,
    guid VARCHAR(35) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    endpoint VARCHAR(500) NOT NULL,
    p256dh_key VARCHAR(100) NOT NULL,
    auth_key VARCHAR(50) NOT NULL,
    device_name VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,

    CONSTRAINT uq_subscription_endpoint UNIQUE (endpoint)
);

CREATE INDEX idx_push_subscriptions_user ON push_subscriptions(user_id);
CREATE INDEX idx_push_subscriptions_team ON push_subscriptions(team_id);

CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    guid VARCHAR(35) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    category VARCHAR(30) NOT NULL,
    title VARCHAR(100) NOT NULL,
    body VARCHAR(500) NOT NULL,
    data JSONB,
    read_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_user_unread ON notifications(user_id) WHERE read_at IS NULL;
CREATE INDEX idx_notifications_created ON notifications(created_at);
```

### Frontend Dependencies

Add to `package.json`:

```json
{
  "devDependencies": {
    "vite-plugin-pwa": "^0.20.0",
    "@vite-pwa/assets-generator": "^0.2.0"
  }
}
```

### Backend Dependencies

Add to `requirements.txt`:

```
pywebpush>=2.0.0
```

### Environment Configuration

```bash
# .env additions

# VAPID keys for Web Push (generate with: npx web-push generate-vapid-keys)
VAPID_PUBLIC_KEY=BEl62iUYgU...
VAPID_PRIVATE_KEY=xYz123...
VAPID_SUBJECT=mailto:admin@shuttersense.ai
```

---

## Implementation Plan

### Phase 1: PWA Foundation (Priority: P0)

**Tasks:**

1. **Add vite-plugin-pwa**
   - Install and configure plugin
   - Generate manifest with app metadata
   - Configure workbox for asset caching

2. **Create PWA Icons**
   - Generate icon set (192x192, 512x512, maskable)
   - Add favicon variants
   - Create badge icon for notifications

3. **Update index.html**
   - Add manifest link
   - Add theme-color meta tag
   - Add apple-mobile-web-app meta tags
   - Add apple-touch-icon

4. **Service Worker Basics**
   - Register service worker
   - Implement asset precaching
   - Handle update prompts

**Checkpoint**: App installable as PWA, assets cached

---

### Phase 2: Push Infrastructure (Priority: P0)

**Tasks:**

1. **Backend Push Setup**
   - Generate VAPID keys
   - Add pywebpush dependency
   - Create PushSubscription model
   - Create database migration

2. **Subscription API**
   - POST /api/notifications/subscribe endpoint
   - DELETE /api/notifications/subscribe endpoint
   - GET /api/notifications/status endpoint

3. **Frontend Subscription Manager**
   - Permission request flow
   - PushManager.subscribe integration
   - Subscription sync with backend

4. **Service Worker Push Handling**
   - Push event listener
   - Notification display
   - Click handling with navigation

**Checkpoint**: Can subscribe and receive test push notifications

---

### Phase 3: Notification Preferences (Priority: P1)

**Tasks:**

1. **Backend Preferences**
   - Add configuration entries for notification prefs
   - Create preferences API endpoints
   - Default values handling

2. **Settings UI**
   - Add Notifications section to Settings page
   - Enable/disable master toggle
   - Category toggles with descriptions
   - Device management (view subscribed devices)

3. **Preference Checks**
   - NotificationService checks prefs before sending
   - Handle disabled notifications gracefully

**Checkpoint**: Users can configure notification preferences

---

### Phase 4: Core Notifications (Priority: P0)

**Tasks:**

1. **NotificationService**
   - Create service for sending notifications
   - Implement preference checking
   - Handle delivery failures
   - Queue notifications (avoid blocking)

2. **Job Failure Notifications**
   - Integrate with JobCoordinatorService.fail_job()
   - Identify affected users
   - Send push notifications
   - Store in history

3. **Inflexion Point Notifications**
   - Integrate with JobCoordinatorService.complete_job()
   - Skip for no_change_copy=true results
   - Calculate issue delta
   - Send to collection owners

**Checkpoint**: Receiving notifications for failures and inflexion points

---

### Phase 5: Agent Notifications (Priority: P1)

**Tasks:**

1. **Agent Status Tracking**
   - Track "all offline" state
   - Detect state transitions
   - Implement debouncing

2. **Agent Notifications**
   - Notify on all-offline transition
   - Notify on agent error
   - Notify on recovery (first online)

3. **Team-Wide Delivery**
   - Send to all team members
   - Respect individual preferences

**Checkpoint**: Receiving agent status notifications

---

### Phase 6: Deadline Notifications (Priority: P2)

**Tasks:**

1. **Deadline Check Scheduler**
   - Add deadline check to cleanup cycle
   - Or implement lightweight cron job
   - Query upcoming deadlines

2. **Deadline Notifications**
   - Calculate days until deadline
   - Match user's days_before preference
   - Track sent reminders (no duplicates)
   - Respect user timezone

3. **Retry Warning Notifications**
   - Detect final retry attempt
   - Send warning notification
   - Link to job details

**Checkpoint**: Receiving deadline reminders

---

### Phase 7: Notification History (Priority: P2)

**Tasks:**

1. **Notification Model**
   - Create notifications table
   - Store all sent notifications
   - Track read/unread status

2. **History API**
   - GET /api/notifications (paginated)
   - GET /api/notifications/unread-count
   - POST /api/notifications/{guid}/read

3. **History UI**
   - Notification bell in header
   - Unread count badge
   - Dropdown panel with history
   - Mark as read functionality

4. **Cleanup**
   - Auto-delete notifications older than 30 days
   - Run during existing cleanup cycles

**Checkpoint**: Full notification history available in UI

---

### Phase 8: Polish and iOS Support (Priority: P2)

**Tasks:**

1. **iOS PWA Guide**
   - Add "Add to Home Screen" instructions
   - Detect iOS and show guidance
   - Handle iOS-specific quirks

2. **Update Prompts**
   - Detect service worker updates
   - Show user-friendly update prompt
   - Handle update installation

3. **Error Handling**
   - Graceful degradation for unsupported browsers
   - Clear error messages for permission denied
   - Retry logic for transient failures

4. **Testing and QA**
   - Test on all target platforms
   - Test offline behavior
   - Test notification edge cases

**Checkpoint**: Production-ready PWA with notifications

---

## iOS Considerations

### Limitations

Push notifications on iOS have specific requirements:

1. **iOS 16.4+ Required**: Earlier versions do not support Web Push
2. **PWA Must Be Installed**: Push only works when app is added to home screen
3. **User Action Required**: Cannot prompt for push without user interaction
4. **Safari Only**: No support in Chrome/Firefox on iOS (WebKit requirement)

### User Guidance

Provide clear instructions for iOS users:

```
To receive notifications on iOS:

1. Tap the Share button in Safari
2. Select "Add to Home Screen"
3. Open ShutterSense from your home screen
4. Enable notifications in Settings
```

### Detection and Messaging

```typescript
const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent)
const isStandalone = window.matchMedia('(display-mode: standalone)').matches

if (isIOS && !isStandalone) {
  // Show "Add to Home Screen" instructions
}
```

---

## Risks and Mitigation

### Risk 1: Push Service Unreliability

- **Impact**: High - Users miss critical notifications
- **Probability**: Low - Major push services are reliable
- **Mitigation**:
  - Retry failed deliveries
  - Store in notification history (in-app fallback)
  - Consider WebSocket fallback for online users

### Risk 2: Notification Fatigue

- **Impact**: Medium - Users disable notifications entirely
- **Probability**: Medium - If we notify too frequently
- **Mitigation**:
  - Only notify for high-value events (no routine completions)
  - Granular preferences per category
  - Debounce agent status notifications
  - Aggregate multiple failures if they occur simultaneously

### Risk 3: iOS Adoption Barrier

- **Impact**: Medium - iOS users may not install PWA
- **Probability**: High - Extra steps required
- **Mitigation**:
  - Clear installation instructions
  - In-app prompts for iOS users
  - Highlight benefits of installation
  - Consider future native app if demand exists

### Risk 4: VAPID Key Management

- **Impact**: High - Lost keys = lost subscriptions
- **Probability**: Low - Standard secret management
- **Mitigation**:
  - Store keys in secure environment config
  - Document key backup procedures
  - Rotation plan with subscription re-enrollment

### Risk 5: Cross-Tenant Data Leak

- **Impact**: Critical - Security breach
- **Probability**: Very Low - With proper implementation
- **Mitigation**:
  - Team ID checked on all subscription operations
  - Notifications filtered by team membership
  - Code review for tenant isolation
  - Security testing

---

## Success Metrics

### Adoption Metrics

- **PWA Installation Rate**: % of users who install PWA
- **Notification Opt-In Rate**: % of users who enable notifications
- **Category Enablement**: Distribution of enabled categories

### Engagement Metrics

- **Notification Click-Through Rate**: % of notifications that lead to app opens
- **Time to Action**: Time between notification and user action
- **Retention Impact**: User retention with vs without notifications

### Technical Metrics

- **Delivery Success Rate**: % of notifications successfully delivered
- **Delivery Latency**: Time from trigger to notification display
- **Subscription Churn**: Rate of subscription expiration/removal

### Quality Metrics

- **False Positive Rate**: Notifications for non-actionable events
- **User Feedback**: Complaints about notification frequency/relevance

---

## Open Questions

1. **Notification Aggregation**: Should multiple job failures within a short window be aggregated into a single notification? (e.g., "3 jobs failed in the last 5 minutes")

2. **Quiet Hours**: Should users be able to set quiet hours (no notifications during certain times)?

3. **Critical Override**: Should some notifications (e.g., all agents offline) bypass quiet hours?

4. **Notification Actions**: Should notifications include action buttons (e.g., "View Details", "Retry Job") in v1?

5. **Team Admin Notifications**: Should team admins receive notifications for all team events, or only their own?

6. **Mobile vs Desktop**: Should users be able to configure different preferences per device?

7. **Webhook Alternative**: Should we also support webhook notifications for power users/integrations?

---

## Appendix

### A. VAPID Key Generation

```bash
# Generate VAPID keys using web-push CLI
npx web-push generate-vapid-keys

# Output:
# Public Key: BEl62iUYgU...
# Private Key: xYz123...
```

Store these in environment variables:
```
VAPID_PUBLIC_KEY=BEl62iUYgU...
VAPID_PRIVATE_KEY=xYz123...
VAPID_SUBJECT=mailto:admin@shuttersense.ai
```

### B. Notification Payload Format

```json
{
  "title": "Analysis Failed",
  "body": "PhotoStats analysis of \"Wedding Photos\" failed: Connection timeout",
  "icon": "/icons/icon-192x192.png",
  "badge": "/icons/badge-72x72.png",
  "tag": "job_failure_job_01abc",
  "data": {
    "url": "/tools?job=job_01abc",
    "category": "job_failure",
    "job_guid": "job_01abc",
    "collection_guid": "col_01xyz"
  }
}
```

### C. Browser Support Matrix

| Browser | Push Support | PWA Install | Notes |
|---------|--------------|-------------|-------|
| Chrome (Desktop) | Yes | Yes | Full support |
| Chrome (Android) | Yes | Yes | Full support |
| Firefox (Desktop) | Yes | Limited | No install prompt |
| Firefox (Android) | Yes | Yes | Full support |
| Edge (Desktop) | Yes | Yes | Full support |
| Safari (macOS) | Yes (16.4+) | Limited | Requires extension |
| Safari (iOS) | Yes (16.4+) | Yes | Requires home screen install |

### D. Notification Category Reference

| Category | ID | Default | Trigger | Recipients |
|----------|-----|---------|---------|------------|
| Job Failures | `job_failure` | On | Job status → FAILED | Collection owners |
| Inflexion Points | `inflexion_point` | On | Result with no_change_copy=false | Collection owners |
| Agent Status | `agent_status` | On | Agent state changes | Team members |
| Deadlines | `deadline` | On | N days before deadline | Event owners |
| Retry Warning | `retry_warning` | Off | Final retry attempt | Collection owners |

### E. Entity GUID Prefixes (New)

| Entity | Prefix |
|--------|--------|
| PushSubscription | `sub_` |
| Notification | `ntf_` |

---

## Revision History

- **2026-01-28 (v1.0)**: Initial draft
  - Defined PWA requirements and notification categories
  - Specified inflexion point detection logic
  - Created implementation plan with 8 phases
  - Identified iOS considerations and risks
