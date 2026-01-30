# Data Model: PWA with Push Notifications

**Feature Branch**: `114-pwa-push-notifications`
**Date**: 2026-01-29

## New Entities

### PushSubscription

Represents a Web Push subscription for a specific user on a specific device/browser. Each subscription holds the push service endpoint and encryption keys needed to deliver push notifications.

**Table**: `push_subscriptions`
**GUID Prefix**: `sub_`

| Field | Type | Constraints | Description |
| ----- | ---- | ----------- | ----------- |
| `id` | Integer | PK, auto-increment | Internal database ID |
| `uuid` | UUID (UUIDv7) | unique, not null, indexed | GUID source (via GuidMixin) |
| `user_id` | Integer | FK → users.id, not null, indexed | Owning user |
| `team_id` | Integer | FK → teams.id, not null, indexed | User's team (tenant isolation) |
| `endpoint` | String(1024) | not null, unique | Push service endpoint URL |
| `p256dh_key` | String(255) | not null | ECDH public key (Base64url) |
| `auth_key` | String(255) | not null | Auth secret (Base64url) |
| `device_name` | String(100) | nullable | User-friendly device label |
| `last_used_at` | DateTime | nullable | Last successful push delivery |
| `expires_at` | DateTime | nullable | Subscription expiration (from push service) |
| `created_at` | DateTime | not null, default=utcnow | Record creation timestamp |
| `updated_at` | DateTime | not null, auto-update | Last modification timestamp |

**Relationships**:
- `user` → User (many-to-one)
- `team` → Team (many-to-one)

**Indexes**:
- `ix_push_subscriptions_uuid` (unique)
- `ix_push_subscriptions_user_id`
- `ix_push_subscriptions_team_id`
- `uq_push_subscriptions_endpoint` (unique constraint on endpoint)

**Validation Rules**:
- `endpoint` must start with `https://`
- One subscription per endpoint (duplicate endpoints replaced)
- Subscription removed on 410 Gone response from push service

---

### Notification

Represents a notification event sent to a user. Stores the notification content and metadata for in-app history viewing, independent of push delivery status.

**Table**: `notifications`
**GUID Prefix**: `ntf_`

| Field | Type | Constraints | Description |
| ----- | ---- | ----------- | ----------- |
| `id` | Integer | PK, auto-increment | Internal database ID |
| `uuid` | UUID (UUIDv7) | unique, not null, indexed | GUID source (via GuidMixin) |
| `user_id` | Integer | FK → users.id, not null, indexed | Recipient user |
| `team_id` | Integer | FK → teams.id, not null, indexed | User's team (tenant isolation) |
| `category` | String(30) | not null | Notification category (see enum below) |
| `title` | String(200) | not null | Notification title text |
| `body` | String(500) | not null | Notification body text |
| `data` | JSONB | nullable | Additional data (navigation URL, entity GUIDs) |
| `read_at` | DateTime | nullable | When user viewed the notification (null = unread) |
| `created_at` | DateTime | not null, default=utcnow | Record creation timestamp |

**Relationships**:
- `user` → User (many-to-one)
- `team` → Team (many-to-one)

**Indexes**:
- `ix_notifications_uuid` (unique)
- `ix_notifications_user_id`
- `ix_notifications_team_id`
- `ix_notifications_user_unread` — partial index on `user_id` WHERE `read_at IS NULL` (for unread count queries)
- `ix_notifications_created_at` — for cleanup of old notifications (>30 days)

**Category Enum Values**:
- `job_failure` — Analysis job failed after all retries
- `inflection_point` — Analysis detected collection changes (new report generated)
- `agent_status` — Agent pool state change (offline, error, recovery)
- `deadline` — Event deadline approaching
- `retry_warning` — Job on final retry attempt

**Data Field Schema** (JSONB):
```json
{
  "url": "/tools?job=job_01abc",
  "job_guid": "job_01abc",
  "collection_guid": "col_01xyz",
  "result_guid": "res_01def",
  "event_guid": "evt_01ghi",
  "agent_guid": "agt_01jkl",
  "tag": "job_failure_job_01abc"
}
```

**Lifecycle**:
- Created when a notification event is triggered (regardless of push delivery success)
- `read_at` set when user views/clicks the notification
- Auto-deleted when `created_at` > 30 days old

---

## Modified Entities

### User (Existing)

**Table**: `users`

The existing `preferences_json` column will be used to store notification preferences.

**Modified Fields**: None (uses existing `preferences_json` column)

**Notification Preferences Schema** (stored in `preferences_json`):
```json
{
  "notifications": {
    "enabled": false,
    "job_failures": true,
    "inflection_points": true,
    "agent_status": true,
    "deadline": true,
    "retry_warning": false,
    "deadline_days_before": 3,
    "timezone": "America/New_York"
  }
}
```

**Initial Defaults** (pre-opt-in — values used when the `notifications` key is absent from `preferences_json`; `enabled` is `false` until the user explicitly opts in via the Profile page):
- `enabled`: `false` (user must explicitly opt in; set to `true` when user clicks "Enable Notifications")
- `job_failures`: `true`
- `inflection_points`: `true`
- `agent_status`: `true`
- `deadline`: `true`
- `retry_warning`: `false`
- `deadline_days_before`: `3`
- `timezone`: auto-detected from browser via `Intl.DateTimeFormat().resolvedOptions().timeZone`, falling back to `"UTC"`. User can override via timezone selector (existing `timezone-combobox.tsx` component). IANA timezone identifier (e.g., `"America/New_York"`, `"Europe/London"`).

**New Relationships on User**:
- `push_subscriptions` → PushSubscription[] (one-to-many)
- `notifications` → Notification[] (one-to-many)

---

## Entity Relationship Diagram

```text
┌─────────────┐        ┌─────────────────────┐
│    Team      │───────<│  PushSubscription    │
│              │        │  (sub_)              │
│  tea_xxx     │        │                     │
└──────┬───────┘        │  endpoint           │
       │                │  p256dh_key         │
       │                │  auth_key           │
       │                │  device_name        │
       │                │  last_used_at       │
       │                │  expires_at         │
       │                └──────────┬──────────┘
       │                           │
       │                    user_id│
       │                           │
       │                ┌──────────┴──────────┐
       │                │    User              │
       ├────────────────│                      │
       │                │  usr_xxx             │
       │                │                      │
       │                │  preferences_json    │
       │                │    └─ notifications:  │
       │                │       enabled, ...    │
       │                └──────────┬──────────┘
       │                           │
       │                    user_id│
       │                           │
       │                ┌──────────┴──────────┐
       │                │  Notification        │
       └───────────────<│  (ntf_)              │
                        │                      │
                        │  category            │
                        │  title               │
                        │  body                │
                        │  data (JSONB)        │
                        │  read_at             │
                        └──────────────────────┘
```

## State Transitions

### PushSubscription Lifecycle

```text
[Created] ──── User enables notifications on a device
    │
    ▼
[Active] ──── Normal state, receives push notifications
    │
    ├──→ [Expired] ──── Push service reports subscription expired
    │        │           (detected on next delivery attempt)
    │        ▼
    │    [Removed] ──── Cleaned up from database
    │
    ├──→ [Invalid] ──── Push service returns 410 Gone
    │        │
    │        ▼
    │    [Removed] ──── Cleaned up from database
    │
    └──→ [Removed] ──── User disables notifications on device
```

### Notification Lifecycle

```text
[Created] ──── Notification event triggered
    │           (stored in history, push delivered async)
    │
    ├──→ [Unread] ──── read_at IS NULL
    │        │
    │        ▼
    │    [Read] ──── User views notification (read_at set)
    │
    └──→ [Expired] ──── created_at > 30 days ago
             │
             ▼
         [Deleted] ──── Removed by cleanup job
```

## Migration Plan

Two new tables in a single migration:

1. **`push_subscriptions`** — Web Push subscription storage
2. **`notifications`** — Notification history

No modifications to existing tables (preferences use the existing `preferences_json` column on `users`).

**GUID Service Updates**:
- Register `sub` → `PushSubscription` in `ENTITY_PREFIXES`
- Register `ntf` → `Notification` in `ENTITY_PREFIXES`
