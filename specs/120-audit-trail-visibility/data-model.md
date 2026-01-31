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

### Immutability Enforcement for `created_by_user_id`

The immutability of `created_by_user_id` is enforced at three levels:

#### 1. Database Trigger (PostgreSQL only)

A `BEFORE UPDATE` trigger on each audited table raises an error if a query attempts to change `created_by_user_id` to a different non-null value:

```sql
-- backend/src/db/migrations/versions/058_add_audit_user_columns.py (within upgrade())
CREATE OR REPLACE FUNCTION prevent_created_by_mutation()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.created_by_user_id IS NOT NULL
     AND NEW.created_by_user_id IS DISTINCT FROM OLD.created_by_user_id THEN
    RAISE EXCEPTION 'created_by_user_id is immutable once set (table: %, old: %, new: %)',
      TG_TABLE_NAME, OLD.created_by_user_id, NEW.created_by_user_id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Applied to each Group A table, e.g.:
CREATE TRIGGER trg_collections_immutable_created_by
  BEFORE UPDATE ON collections
  FOR EACH ROW
  EXECUTE FUNCTION prevent_created_by_mutation();
```

Note: The trigger allows `NULL → value` transitions (backfill) and `value → NULL` transitions (user deletion SET NULL), but blocks `value_A → value_B` changes.

SQLite does not support this trigger. In test/dev environments, rely on the service-layer and model-level protections below.

#### 2. SQLAlchemy Model Protection

The AuditMixin does not expose a public setter for `created_by_user_id`. The column is populated only on insert via the model's `__init__` or the service layer's create method. Any direct assignment after initial flush is blocked by SQLAlchemy's attribute event:

```python
# backend/src/models/mixins/audit.py
from sqlalchemy import event

@event.listens_for(AuditMixin.created_by_user_id, "set", propagate=True)
def _block_created_by_mutation(target, value, oldvalue, initiator):
    from sqlalchemy.orm import object_session
    session = object_session(target)
    if session is not None and target in session.dirty:
        if oldvalue is not None and value != oldvalue:
            raise ValueError(
                f"created_by_user_id is immutable once set "
                f"(current={oldvalue}, attempted={value})"
            )
```

#### 3. Service-Layer Validation

Service create/update methods enforce the rule: update methods never include `created_by_user_id` in the mutation payload. If an update request payload contains a `created_by_user_id` value differing from the current record, the service rejects it before persisting:

```python
# Pattern for service update methods:
def update_entity(self, entity_id, data, user_id=None):
    entity = self._get_entity(entity_id)
    # Never overwrite created_by_user_id on update
    if hasattr(data, 'created_by_user_id'):
        del data.created_by_user_id  # or raise if explicitly provided
    entity.updated_by_user_id = user_id
    # ... persist
```

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
| `email` | str \| null | No | User email — optional to avoid unconditional PII exposure; populated only when requester is authorized |

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

### CONCURRENTLY Index Operations: Rollback, Recovery & Environment Differences

#### PostgreSQL: CONCURRENTLY Constraints

`CREATE INDEX CONCURRENTLY` cannot run inside a transaction block. The Alembic migration must use `op.execute()` with `autocommit` mode (or Alembic's `op.get_context().autocommit_block()`) for these statements. This means:

- These index operations are **not transactional** — if the migration is interrupted mid-way, some indexes may exist while others do not.
- A failed `CONCURRENTLY` creation may leave an **invalid index** in the catalog (visible via `pg_indexes` with `indisvalid = false`).

#### Recovery from Failed CONCURRENTLY Index Creation

If a `CREATE INDEX CONCURRENTLY` fails or is interrupted:

1. **Check for invalid indexes**:
   ```sql
   SELECT indexrelid::regclass AS index_name, indrelid::regclass AS table_name
   FROM pg_index WHERE NOT indisvalid;
   ```

2. **Remove the invalid index**:
   ```sql
   DROP INDEX CONCURRENTLY IF EXISTS ix_collections_created_by_user_id;
   ```
   If `DROP INDEX CONCURRENTLY` fails (e.g., due to lock contention), fall back to:
   ```sql
   DROP INDEX IF EXISTS ix_collections_created_by_user_id;
   ```
   (This takes a brief exclusive lock but always succeeds.)

3. **Re-create the index**:
   ```sql
   CREATE INDEX CONCURRENTLY ix_collections_created_by_user_id
     ON collections (created_by_user_id);
   ```

4. **Retry logic**: The migration should include a comment or helper noting that `CONCURRENTLY` operations are idempotent-safe when combined with `IF NOT EXISTS`:
   ```sql
   CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_jobs_updated_by_user_id
     ON jobs (updated_by_user_id);
   ```

#### Downgrade (Rollback) Procedure

The `downgrade()` function must drop audit indexes before removing columns:

- **PostgreSQL**: Use `DROP INDEX CONCURRENTLY IF EXISTS` for the large-table indexes (`collections`, `jobs`, `analysis_results`, `events`, `notifications`) to avoid blocking production queries. If `CONCURRENTLY` drop fails, fall back to `DROP INDEX IF EXISTS` (non-concurrent, brief lock).
- **Small tables**: Use standard `DROP INDEX IF EXISTS` (no `CONCURRENTLY` needed).

```python
# downgrade() pattern
def downgrade():
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    large_tables = ["collections", "jobs", "analysis_results", "events", "notifications"]

    for table in all_tables:
        for col in ["created_by_user_id", "updated_by_user_id"]:
            idx_name = f"ix_{table}_{col}"
            if is_pg and table in large_tables:
                # Try CONCURRENTLY first, fall back to standard
                try:
                    op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {idx_name}")
                except Exception:
                    op.execute(f"DROP INDEX IF EXISTS {idx_name}")
            else:
                op.drop_index(idx_name, table_name=table, if_exists=True)

        # Then drop columns...
```

#### SQLite / Development Environment

SQLite does not support `CONCURRENTLY`. The migration must use conditional branches:

```python
bind = op.get_bind()
if bind.dialect.name == "postgresql":
    op.execute("CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_jobs_updated_by_user_id ON jobs (updated_by_user_id)")
else:
    # SQLite and other dialects: standard index creation (always transactional)
    op.create_index("ix_jobs_updated_by_user_id", "jobs", ["updated_by_user_id"])
```

In SQLite environments, all index operations run inside the migration transaction and are fully rollback-safe. No special recovery steps are needed.

## Entity Relationship Summary

```
User (users)
  ├── created_by_user_id  ←── Collection, Connector, Pipeline, Job, ...  (FK, SET NULL)
  └── updated_by_user_id  ←── Collection, Connector, Pipeline, Job, ...  (FK, SET NULL)
```

All relationships are many-to-one from the audited entity to the User model.
