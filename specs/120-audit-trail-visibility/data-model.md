# Data Model: Audit Trail Visibility

## New Mixin: AuditMixin

**File**: `backend/src/models/mixins/audit.py`

Provides user attribution columns and relationships to any model that inherits it.

### Columns

| Column | Type | FK | Nullable | OnDelete | Index | Description |
|--------|------|-----|----------|----------|-------|-------------|
| `created_by_user_id` | Integer | `users.id` | Yes | SET NULL | Yes | User who created the record |
| `updated_by_user_id` | Integer | `users.id` | Yes | SET NULL | Yes | User who last modified the record |

### Relationships

| Name | Target | FK Column | Lazy | Description |
|------|--------|-----------|------|-------------|
| `created_by_user` | User | `created_by_user_id` | joined | Eagerly loaded for list queries |
| `updated_by_user` | User | `updated_by_user_id` | joined | Eagerly loaded for list queries |

### Behavior Rules

- `created_by_user_id` is set once at creation and never modified afterward.
- `updated_by_user_id` is set at creation and updated on every subsequent mutation.
- Both are nullable to support historical records and edge cases.
- `SET NULL` on user deletion — attribution is cleared, not blocked.

## Affected Entities

### Group A: Apply Full AuditMixin (14 entities)

These entities gain both `created_by_user_id` and `updated_by_user_id`:

| Entity | Model Class | Table | Mixin Applied |
|--------|-------------|-------|---------------|
| Collection | `Collection` | `collections` | `AuditMixin` |
| Connector | `Connector` | `connectors` | `AuditMixin` |
| Pipeline | `Pipeline` | `pipelines` | `AuditMixin` |
| Job | `Job` | `jobs` | `AuditMixin` |
| AnalysisResult | `AnalysisResult` | `analysis_results` | `AuditMixin` |
| Event | `Event` | `events` | `AuditMixin` |
| EventSeries | `EventSeries` | `event_series` | `AuditMixin` |
| Category | `Category` | `categories` | `AuditMixin` |
| Location | `Location` | `locations` | `AuditMixin` |
| Organizer | `Organizer` | `organizers` | `AuditMixin` |
| Performer | `Performer` | `performers` | `AuditMixin` |
| Configuration | `Configuration` | `configurations` | `AuditMixin` |
| PushSubscription | `PushSubscription` | `push_subscriptions` | `AuditMixin` |
| Notification | `Notification` | `notifications` | `AuditMixin` |

### Group B: Add `updated_by_user_id` Only (3 entities)

These entities already have `created_by_user_id` — only `updated_by_user_id` is added:

| Entity | Model Class | Table | Existing Column | New Column |
|--------|-------------|-------|-----------------|------------|
| Agent | `Agent` | `agents` | `created_by_user_id` | `updated_by_user_id` |
| ApiToken | `ApiToken` | `api_tokens` | `created_by_user_id` | `updated_by_user_id` |
| AgentRegistrationToken | `AgentRegistrationToken` | `agent_registration_tokens` | `created_by_user_id` | `updated_by_user_id` |

For Group B entities, the `updated_by_user_id` column and `updated_by_user` relationship are added directly (not via the full mixin, since they already have their own `created_by_user_id` column with a different relationship name `created_by`).

## New Schema: AuditInfo

**File**: `backend/src/schemas/audit.py`

### AuditUserSummary

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `guid` | str | Yes | User GUID (`usr_xxx`) |
| `display_name` | str \| null | No | User display name |
| `email` | str | Yes | User email |

### AuditInfo

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `created_at` | datetime | Yes | Creation timestamp |
| `created_by` | AuditUserSummary \| null | No | User who created (null for historical) |
| `updated_at` | datetime | Yes | Last modification timestamp |
| `updated_by` | AuditUserSummary \| null | No | User who last modified (null for historical) |

### Integration with Entity Schemas

All entity response schemas gain:

```
audit: AuditInfo | null  (Optional, null during transitional deployment)
```

Existing `created_at` and `updated_at` top-level fields are retained for backward compatibility.

## Database Migration

**Revision**: `058_add_audit_user_columns`
**Down revision**: `057_push_notifications`

### Phase 1: Add Columns (transactional)

For Group A tables (14): Add `created_by_user_id` and `updated_by_user_id` with FK to `users.id`, `ondelete=SET NULL`.

For Group B tables (3): Add `updated_by_user_id` only.

### Phase 2: Create Indexes

All 17 tables get `ix_{table}_updated_by_user_id` index.
Group A tables (14) get `ix_{table}_created_by_user_id` index.

Large tables (`collections`, `jobs`, `analysis_results`, `events`, `notifications`) use `CONCURRENTLY` for index creation (PostgreSQL only).

## Entity Relationship Summary

```
User (users)
  ├── created_by_user_id  ←── Collection, Connector, Pipeline, Job, ...  (FK, SET NULL)
  └── updated_by_user_id  ←── Collection, Connector, Pipeline, Job, ...  (FK, SET NULL)
```

All relationships are many-to-one from the audited entity to the User model.
