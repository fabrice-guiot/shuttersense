# Feature Specification: PWA with Push Notifications

**Feature Branch**: `114-pwa-push-notifications`
**Created**: 2026-01-29
**Status**: Draft
**Input**: Github issue #114, based on PRD: docs/prd/023-pwa-push-notifications.md

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Install ShutterSense as an App (Priority: P1)

As a user, I want to install ShutterSense as a standalone application on my desktop or mobile device so that I can access it quickly from my home screen or app launcher without opening a browser.

**Why this priority**: The installable PWA is the foundational prerequisite for all push notification functionality. Without a service worker and web app manifest, no other feature in this specification can work. This also provides immediate value through faster loading and a native-like experience.

**Independent Test**: Can be fully tested by visiting ShutterSense in a supported browser, installing it as an app, and verifying it launches in a standalone window with cached assets. Delivers value independently through faster access and native-like experience.

**Acceptance Scenarios**:

1. **Given** a user visits ShutterSense in a supported browser, **When** the browser detects PWA eligibility, **Then** an install prompt or indicator is displayed
2. **Given** a user installs the PWA, **When** they launch it from their device's app launcher, **Then** the application opens in a standalone window without browser chrome
3. **Given** a user has installed the PWA, **When** a new version of the application is deployed, **Then** the user is notified that an update is available and can refresh to load it
4. **Given** a user is on iOS Safari, **When** they have not yet added the app to their home screen, **Then** clear instructions are shown explaining how to install via "Add to Home Screen"
5. **Given** a user opens the installed PWA, **When** static assets have been previously cached, **Then** the application shell loads without waiting for a network response

---

### User Story 2 - Enable Push Notifications (Priority: P1)

As an authenticated user, I want to opt in to receiving push notifications so that I am alerted to critical events (job failures, analysis changes, agent outages) even when I am not actively using the application.

**Why this priority**: Push notification subscription is the core value proposition of this feature. Without subscription management, no notifications can be delivered. This story establishes the permission flow and subscription lifecycle.

**Independent Test**: Can be fully tested by logging in, clicking "Enable Notifications," granting browser permission, and verifying a test notification is received on the device. Delivers value by establishing the push channel for all subsequent notification categories.

**Acceptance Scenarios**:

1. **Given** an authenticated user who has not yet opted in, **When** they click "Enable Notifications" in settings, **Then** the browser's native permission dialog is shown
2. **Given** the user grants notification permission, **When** the subscription is created, **Then** the subscription is stored on the server and associated with the user's account
3. **Given** the user denies notification permission, **When** the permission dialog closes, **Then** the application displays a message explaining that notifications are disabled and how to re-enable them in browser settings
4. **Given** a user has enabled notifications on two devices, **When** a notification is triggered, **Then** both devices receive the notification
5. **Given** a user clicks "Disable Notifications" in settings, **When** the action completes, **Then** the push subscription is removed from the server and no further push messages are delivered to that device

---

### User Story 3 - Receive Job Failure Notifications (Priority: P1)

As a collection owner, I want to receive a push notification when an analysis job fails so that I can investigate and retry the job without delay.

**Why this priority**: Job failures are the highest-urgency event in the system. Users currently only discover failures by manually checking the application, which can cause hours or days of delay. This is the most impactful notification category.

**Independent Test**: Can be fully tested by triggering a job failure (or simulating one) and verifying the notification appears on the user's device with the correct job and collection details, and that clicking it navigates to the job details page.

**Acceptance Scenarios**:

1. **Given** a user has notifications enabled with job failures toggled on, **When** an analysis job transitions to FAILED status after exhausting all retry attempts, **Then** the user receives a push notification with the tool name, collection name, and error summary
2. **Given** a user has job failure notifications toggled off, **When** a job fails, **Then** no push notification is sent to that user
3. **Given** the user receives a job failure notification, **When** they click on it, **Then** the application opens (or focuses) and navigates to the job details page
4. **Given** multiple users belong to the same team, **When** a job on a collection in that team fails, **Then** all team members with notifications enabled receive the failure notification

---

### User Story 4 - Receive Analysis Inflection Point Notifications (Priority: P1)

As a collection owner, I want to receive a push notification when an analysis run detects actual changes in my collection (an inflection point) so that I can review new findings promptly.

**Why this priority**: Inflection points represent actionable information - the collection state has changed. This differentiates meaningful results from routine no-change confirmations, ensuring notifications remain high-value and users do not experience notification fatigue.

**Independent Test**: Can be fully tested by running an analysis that produces a new report (not a no-change copy) and verifying the notification arrives with change details. Separately verify that a no-change result does NOT trigger a notification.

**Acceptance Scenarios**:

1. **Given** a user has notifications enabled with inflection points toggled on, **When** an analysis completes with new results (a new report is generated, not a no-change copy), **Then** the user receives a notification with the tool name, collection name, and a summary of changes
2. **Given** an analysis completes with no changes detected (identical to previous result), **When** the result is recorded, **Then** NO notification is sent
3. **Given** the user receives an inflection point notification, **When** they click on it, **Then** the application navigates to the analysis result or report page
4. **Given** a previous result exists for the same collection and tool, **When** a new result is created with a different issue count, **Then** the notification includes the issue count change (e.g., "+12 new issues" or "-5 issues resolved")

---

### User Story 5 - Configure Notification Preferences (Priority: P2)

As a user, I want to control which categories of notifications I receive so that I only get alerts that are relevant to me without being overwhelmed.

**Why this priority**: User control over notification categories is essential for preventing notification fatigue, which would lead users to disable notifications entirely. However, the core notification infrastructure (Stories 1-4) must exist first.

**Independent Test**: Can be fully tested by navigating to the user's profile page, toggling notification categories on and off, and verifying that only enabled categories produce notifications. Delivers value by giving users fine-grained control over their notification experience.

**Acceptance Scenarios**:

1. **Given** an authenticated user navigates to their profile page (via avatar dropdown), **When** the page loads, **Then** a notification preferences section displays toggle controls for each notification category (Job Failures, Inflection Points, Agent Status, Deadlines, Retry Warnings) with a master enable/disable toggle
2. **Given** a user toggles off the "Agent Status" category, **When** an agent goes offline, **Then** no agent status notification is sent to that user (but other users with the category enabled still receive it)
3. **Given** a user disables the master notification toggle, **When** any notification event occurs, **Then** no push notifications are sent to that user for any category
4. **Given** a user changes preferences on one device, **When** they check preferences on another device, **Then** the preferences are consistent (synced via server-side storage)
5. **Given** a user enables notifications for the first time, **When** default preferences are applied, **Then** all categories except Retry Warnings are enabled by default

---

### User Story 6 - Receive Agent Status Notifications (Priority: P2)

As a team member, I want to receive notifications about agent availability changes so that I know when job processing is impacted or restored.

**Why this priority**: Agent availability directly affects whether jobs can be processed. Users need awareness of infrastructure state, but this is less urgent than individual job failures because it is a team-level event rather than a user-initiated action.

**Independent Test**: Can be fully tested by simulating agent state transitions (all agents going offline, an agent entering error state, first agent recovering) and verifying the correct notifications are sent to team members.

**Acceptance Scenarios**:

1. **Given** a team has multiple agents online, **When** the last online agent transitions to OFFLINE status, **Then** all team members with agent status notifications enabled receive a "pool offline" notification
2. **Given** all agents are offline, **When** the first agent comes back online, **Then** team members receive a recovery notification indicating job processing has resumed
3. **Given** an agent transitions to ERROR status, **When** the error is detected, **Then** team members receive an error notification with the agent name and error description
4. **Given** an agent flaps between online and offline rapidly, **When** status changes occur within a 5-minute window, **Then** only one notification per state change direction is sent (debounced)
5. **Given** all agents crash without graceful shutdown, **When** heartbeat timeouts are exceeded, **Then** the system's safety net mechanism detects the outage and triggers offline notifications within a reasonable timeframe

---

### User Story 7 - Receive Deadline Reminder Notifications (Priority: P3)

As an event organizer, I want to receive reminder notifications before event deadlines approach so that I do not miss important delivery dates.

**Why this priority**: Deadline reminders are valuable but less urgent than failure/change notifications because deadlines are measured in days, not seconds. This feature requires a scheduling mechanism through the agent job system, adding complexity.

**Independent Test**: Can be fully tested by creating an event with a deadline set a configurable number of days in the future, waiting for the daily deadline check to run, and verifying the reminder notification arrives at the correct time.

**Acceptance Scenarios**:

1. **Given** a user has deadline notifications enabled with a "3 days before" preference, **When** an event deadline is 3 days away, **Then** the user receives a reminder notification with the event name and time remaining
2. **Given** a reminder has already been sent for a specific deadline at a specific interval, **When** the deadline check runs again, **Then** no duplicate reminder is sent for that same deadline and interval
3. **Given** the system was unavailable for several days, **When** the deadline check resumes, **Then** any deadlines that entered the reminder window during the outage are still caught and notified (backfill)
4. **Given** the user clicks a deadline notification, **When** the application opens, **Then** it navigates to the event details page
5. **Given** an event has been completed or cancelled, **When** the deadline check runs, **Then** no reminder is sent for that event

---

### User Story 8 - Receive Retry Warning Notifications (Priority: P3)

As a collection owner, I want to receive a warning notification when a job is on its final retry attempt so that I can investigate before it fails completely.

**Why this priority**: This is a proactive alert that gives users a chance to intervene. It is less critical than failure notifications (Story 3) because the job hasn't failed yet and may still succeed.

**Independent Test**: Can be fully tested by triggering a job that reaches its final retry attempt and verifying the warning notification is received. Note that this category is disabled by default.

**Acceptance Scenarios**:

1. **Given** a user has opted in to retry warning notifications, **When** a job reaches its final retry attempt, **Then** the user receives a warning notification with the tool name and collection name
2. **Given** retry warnings are disabled by default, **When** a new user enables notifications, **Then** retry warnings are NOT sent unless the user explicitly enables the category
3. **Given** the user clicks a retry warning notification, **When** the application opens, **Then** it navigates to the job details page

---

### User Story 9 - View Notification History (Priority: P3)

As a user, I want to see a history of recent notifications within the application so that I can review alerts I may have missed.

**Why this priority**: Notification history serves as a fallback for missed push notifications and provides a centralized view of recent events. It enhances the notification system but is not required for the core push delivery pipeline.

**Independent Test**: Can be fully tested by triggering several notification events and verifying they appear in the in-app notification panel with correct details, read/unread status, and navigation links.

**Acceptance Scenarios**:

1. **Given** notifications have been sent to the user, **When** the user clicks the notification bell icon in the header, **Then** a panel or dropdown displays the most recent 20 notifications
2. **Given** the user has unread notifications, **When** the application header is visible, **Then** the notification bell icon displays an unread count badge
3. **Given** the user views a notification in the panel, **When** they click on it, **Then** the notification is marked as read and the unread count decreases
4. **Given** a notification is older than 30 days, **When** the system performs routine cleanup, **Then** the notification is automatically removed from history
5. **Given** the user has no notifications, **When** they open the notification panel, **Then** an empty state message is displayed

---

### Edge Cases

- What happens when a user's push subscription expires or becomes invalid? The system must gracefully remove the subscription (on receiving a 410 Gone response from the push service) and stop attempting delivery to that endpoint.
- What happens when a user revokes browser notification permission outside the application? The application should detect the permission state change on next visit and update the UI accordingly, indicating notifications are disabled.
- What happens when the same notification event targets a user who is currently viewing the application? The in-app notification history should still be updated, but the push notification should still be sent (the user may have the app open on a different device or tab).
- What happens when a notification is triggered for a user with no active push subscriptions? The notification is still stored in the history table for in-app viewing, but no push delivery is attempted.
- What happens on iOS when the user has not installed the PWA to their home screen? Push notifications are not available. The application should detect this state and display clear instructions for how to install the PWA to enable notifications.
- What happens when multiple job failures occur in rapid succession? Each failure generates its own notification. Aggregation of batch failures into a single notification is out of scope for v1.
- What happens when the notification delivery service is unavailable? Notifications are stored in history regardless of push delivery success. Failed push deliveries are retried with exponential backoff up to 3 attempts, after which the delivery is marked as failed.

## Requirements *(mandatory)*

### Functional Requirements

#### PWA Infrastructure

- **FR-001**: System MUST provide a web app manifest with application name, icons, theme color, and display mode for standalone installation
- **FR-002**: System MUST register a service worker that caches the application shell and static assets for fast loading
- **FR-003**: System MUST provide application icons in standard sizes (192x192, 512x512) including maskable variants for Android
- **FR-004**: System MUST detect when a new application version is available and prompt the user to update
- **FR-005**: System MUST include appropriate meta tags for PWA compatibility across desktop and mobile browsers (theme color, mobile web app capable)

#### Push Subscription Management

- **FR-006**: System MUST request browser notification permission only after the user explicitly opts in (no permission prompt on first visit)
- **FR-007**: System MUST create a push subscription using the Web Push protocol with server-generated signing keys
- **FR-008**: System MUST store each push subscription associated with the authenticated user and their team
- **FR-009**: System MUST support multiple push subscriptions per user (one per device)
- **FR-010**: System MUST remove a push subscription when the user disables notifications on that device
- **FR-011**: System MUST handle expired or invalid subscriptions by removing them automatically upon delivery failure (410 Gone response)
- **FR-012**: System MUST provide a way for users to check their current subscription status

#### Notification Preferences

- **FR-013**: System MUST store notification preferences at the user level, synced across all of the user's devices
- **FR-014**: System MUST provide a master toggle to enable or disable all notifications
- **FR-015**: System MUST provide individual toggles for each notification category: Job Failures, Inflection Points, Agent Status, Deadlines, Retry Warnings
- **FR-016**: System MUST default all categories to enabled except Retry Warnings (disabled by default) when a user first enables notifications
- **FR-017**: System MUST check user preferences before sending any notification and respect the user's choices

#### Notification Delivery

- **FR-018**: System MUST deliver push notifications to all of a user's subscribed devices when a notification event is triggered
- **FR-019**: System MUST not block the triggering operation (job completion, agent status change, etc.) while delivering notifications (asynchronous delivery)
- **FR-020**: System MUST retry failed push deliveries with exponential backoff, up to 3 attempts
- **FR-021**: System MUST include navigation data in each notification so that clicking it opens the relevant page in the application
- **FR-022**: System MUST log notification delivery attempts for troubleshooting purposes

#### Job Failure Notifications

- **FR-023**: System MUST send a notification when a job transitions to FAILED status after all retry attempts are exhausted
- **FR-024**: Job failure notifications MUST include the tool name, collection name, and a brief error summary
- **FR-025**: Job failure notifications MUST be sent to all team members who have the category enabled (collections belong to the team; all team members have access)

#### Analysis Inflection Point Notifications

- **FR-026**: System MUST send a notification when an analysis job completes with actual new results (a new report is generated, not a no-change copy)
- **FR-027**: System MUST NOT send an inflection point notification when an analysis result indicates no change from the previous run
- **FR-028**: Inflection point notifications SHOULD include the issue count delta compared to the previous result, when available
- **FR-029**: Inflection point notifications MUST be sent to all team members who have the category enabled

#### Agent Status Notifications

- **FR-030**: System MUST send a notification when all agents in a team transition to OFFLINE status (pool offline)
- **FR-031**: System MUST send a notification when any agent transitions to ERROR status
- **FR-032**: System MUST send a notification when the first agent recovers after all agents were offline (pool recovery)
- **FR-033**: System MUST debounce agent status notifications within a 5-minute window per agent to prevent notification spam from flapping
- **FR-034**: Agent status notifications MUST be sent to all team members with the category enabled
- **FR-035**: System MUST detect agent failures through multiple mechanisms: graceful shutdown reporting, heartbeat timeout detection, and a server-side safety net check for scenarios where all agents are unreachable
- **FR-036**: The server-side safety net MUST run periodically (every 2 minutes), detect agents with stale heartbeats, force their status to offline, release their assigned jobs back to the queue, and trigger notifications — in a multi-tenant, idempotent manner

#### Deadline Notifications

- **FR-037**: System MUST check for approaching event deadlines once per day per team, scheduled through the existing agent job system
- **FR-038**: Deadline reminders MUST be sent based on the user's configured "days before" preference (default: 3 days)
- **FR-039**: System MUST send only one reminder per deadline per configured interval to prevent duplicate notifications
- **FR-040**: System MUST use the user's timezone (stored as IANA identifier in notification preferences, auto-detected from browser on first enable, user-overridable) when calculating deadline proximity
- **FR-041**: System MUST support a backfill window of 7 days so that deadlines entering the reminder window during a system outage are still caught
- **FR-042**: Deadline checks MUST skip events that are completed or cancelled

#### Retry Warning Notifications

- **FR-043**: System MUST send a warning notification when a job reaches its final retry attempt
- **FR-044**: Retry warning notifications MUST be disabled by default and only sent to users who explicitly enable the category

#### Notification History

- **FR-045**: System MUST store all triggered notifications in a persistent history accessible within the application
- **FR-046**: System MUST provide an unread notification count displayed as a badge on the notification bell icon in the application header
- **FR-047**: System MUST display the most recent 20 notifications in a notification panel or dropdown
- **FR-048**: System MUST allow users to mark individual notifications as read
- **FR-049**: System MUST automatically remove notifications older than 30 days

#### Multi-Tenant Security

- **FR-050**: All push subscriptions MUST be scoped to the user's team to prevent cross-tenant notification delivery
- **FR-051**: Notification queries and deliveries MUST filter by team membership so that no user receives notifications for another team's events

#### Browser Compatibility

- **FR-052**: System MUST support PWA installation and push notifications on desktop browsers: Chrome 50+, Firefox 44+, Edge 17+, Safari 16+ (macOS)
- **FR-053**: System MUST support PWA installation and push notifications on mobile: Chrome 50+ (Android), Firefox 44+ (Android), Safari 16.4+ (iOS, requires home screen installation)
- **FR-054**: System MUST gracefully degrade on unsupported browsers by hiding notification features and displaying an informational message

### Key Entities

- **PushSubscription**: Represents a single push notification channel for a specific user on a specific device. Key attributes: owning user, team, push service endpoint, encryption keys, device name, creation time, last successful delivery time, expiration time. GUID prefix: `sub_`
- **Notification**: Represents a single notification event sent to a user. Key attributes: recipient user, team, category (job_failure, inflection_point, agent_status, deadline, retry_warning), title, body, associated data (job/result/event identifiers), read status, creation time. GUID prefix: `ntf_`
- **NotificationPreferences**: User-level configuration controlling which notification categories are enabled. Key attributes: master enabled toggle, per-category toggles, deadline reminder days-before setting. Stored as user-level configuration entries.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can install ShutterSense as a standalone application on desktop and mobile devices within 2 taps/clicks of the install prompt
- **SC-002**: Users who opt in to notifications receive push alerts on their devices within 10 seconds of the triggering event, even when the application is not open
- **SC-003**: At least 50% of active users install the PWA within the first month of availability
- **SC-004**: At least 30% of active users opt in to push notifications within the first month
- **SC-005**: Notification click-through rate exceeds 40%, indicating notifications are perceived as relevant and actionable
- **SC-006**: Users can enable notifications and configure their preferences in under 1 minute
- **SC-007**: Zero cross-tenant notification deliveries occur (security: notifications are never sent to users outside the owning team)
- **SC-008**: The application shell loads from cache in under 1 second on repeat visits after PWA installation
- **SC-009**: Notification delivery success rate exceeds 95% across all supported browsers and platforms
- **SC-010**: Users who missed push notifications can find them in the in-app notification history within 2 clicks (bell icon → notification panel)

## Assumptions

- Users have modern browsers that support the Web Push protocol and service workers (see FR-052/FR-053 for specific versions)
- The existing authentication and multi-tenancy infrastructure is functional and stable
- The existing agent job system can support the addition of a new `deadline_check` job type without architectural changes
- The existing WebSocket infrastructure for real-time updates continues to operate alongside push notifications for in-app updates
- iOS users understand that PWA installation to the home screen is required for push notification support (guided by in-app instructions)
- The server has outbound HTTPS access to third-party push services (Firebase Cloud Messaging, Mozilla Push, Apple Push Notification service)
- VAPID keys will be generated once during initial deployment and securely stored in environment configuration
- Notification aggregation (batching multiple rapid-fire events into a single notification) is out of scope for v1; each event produces its own notification
- "Mark all read" and bulk notification management operations are out of scope for v1
- Email/SMS notification channels are out of scope for v1; push-only delivery
- Full offline functionality (viewing cached analysis results) is out of scope; only the application shell is cached
