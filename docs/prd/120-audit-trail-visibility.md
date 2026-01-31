# PRD: Audit Trail Visibility Enhancement

**Issue**: [#120](https://github.com/fabrice-guiot/shuttersense/issues/120)
**Status**: Draft
**Created**: 2026-01-31
**Last Updated**: 2026-01-31
**Related Documents**:
- [Domain Model](../domain-model.md)
- [Design System](../../frontend/docs/design-system.md)
- [Mobile Responsive Tables & Tabs](./024-mobile-responsive-tables-tabs.md)
- [User Tenancy](./019-user-tenancy.md)
- [Distributed Agent Architecture](./021-distributed-agent-architecture.md)

---

## Executive Summary

ShutterSense currently stores `created_at` and `updated_at` timestamps on all entities but does not track **who** created or modified records. The web UI displays these timestamps inconsistently and never attributes changes to a user. This PRD defines a complete audit trail visibility enhancement that adds user attribution to all tenant-scoped entities and surfaces this information in two ways: a compact **"Modified"** summary column in list views (with a hover popover showing full audit details) and an **audit trail section** in detail dialogs.

### Key Design Decisions

1. **Column-level tracking, not a separate audit log**: `created_by_user_id` and `updated_by_user_id` foreign keys are added directly to each entity table rather than maintaining a separate audit log table. This is simpler, avoids joins on every list query, and satisfies the stated requirements without over-engineering.
2. **System user attribution**: Actions performed by agents and API tokens are attributed to the dedicated system user associated with that agent or token. Both `Agent.system_user_id` and `ApiToken.system_user_id` already exist in the data model. For API tokens, `TokenService.validate_token` sets `TenantContext.user_id = system_user.id`, so route handlers use the same `ctx.user_id` pattern regardless of whether the caller is a browser session or an API token — no special-casing required.
3. **Hover popover in list views**: A single "Modified" column shows relative time (e.g., "5 min ago") with a hover popover revealing the full audit card (created by, created at, modified by, modified at). This keeps tables compact while making full details accessible.
4. **Reusable `<AuditTrailPopover>` component**: One shared component used in both table rows and detail dialogs, ensuring consistent presentation.
5. **Graceful handling of historical data**: Existing records without `created_by`/`updated_by` display "System" or "—" rather than failing.

---

## Background

### Current State

**Backend (23 models with timestamps)**:
- All entities have `created_at` (default `datetime.utcnow`) and `updated_at` (auto-updated via SQLAlchemy `onupdate`).
- Only 3 entities track `created_by_user_id`: `Agent`, `ApiToken`, and `AgentRegistrationToken`.
- No entity tracks `updated_by_user_id`.
- `PipelineHistory` has a `changed_by` string field (not a foreign key).
- `TenantContext` carries `user_id` in every authenticated request but services do not capture it during create/update operations.

**Authentication paths and `TenantContext.user_id` resolution** (see `backend/src/middleware/tenant.py`):

| Auth Method | `ctx.user_id` resolves to | `ctx.is_api_token` | Source |
|---|---|---|---|
| Session (browser) | Human user's `User.id` | `False` | `_authenticate_session` → `user.id` |
| API Token (Bearer) | Token's `system_user.id` | `True` | `TokenService.validate_token` → `api_token.system_user.id` |
| Agent (agent auth) | N/A — uses separate auth | N/A | `get_authenticated_agent` dependency |

This means `ctx.user_id` already points to the correct attribution user for both session and API token auth. For API tokens, the `system_user` is a dedicated `User` row representing that token (created during token provisioning), so audit records attributed to it are clearly distinguishable from human user actions.

**Frontend**:
- `formatDateTime()` and `formatRelativeTime()` utilities exist in `frontend/src/utils/dateFormat.ts`.
- Some list views show `created_at` (Connectors, Locations, Organizers, Performers) but most hide it on mobile (`cardRole: 'hidden'`).
- No list view or detail dialog shows who created or modified a record.
- `UserInfo` type is available via `useAuth()` context.

**API Schemas**:
- Response schemas include `created_at` and `updated_at` as `datetime` fields.
- No response schema includes `created_by` or `updated_by` user information.

### Problem Statement

Users have no visibility into who created or last modified any record. In a multi-user team environment, this creates accountability gaps:
- Cannot determine who changed a collection's state or pipeline assignment.
- Cannot identify who created a misconfigured connector.
- Cannot audit which user or API token modified an event or category.
- Agent-initiated changes are indistinguishable from user-initiated changes.

### Strategic Context

Audit trail visibility is foundational for:
- **Team collaboration**: Multiple users managing the same collections need to know who changed what.
- **Troubleshooting**: When a configuration breaks, identifying the last modifier accelerates resolution.
- **Compliance readiness**: Organizations increasingly require change attribution for data management systems.
- **Agent transparency**: Distinguishing agent-automated changes from manual user actions.

---

## Goals

### Primary Goals

1. **User attribution on all mutations**: Every create and update operation on tenant-scoped entities records the acting user.
2. **System user attribution**: Agent and API token actions are attributed to their associated system user.
3. **List view audit summary**: All list views show a "Modified" column with relative time and a hover popover revealing full audit details.
4. **Detail dialog audit section**: All detail dialogs include an audit trail section showing created/modified timestamps and users.

### Secondary Goals

1. **Consistent formatting**: Audit timestamps use `formatRelativeTime()` for summary and `formatDateTime()` for expanded details.
2. **Mobile-friendly**: Audit information renders appropriately on mobile card layouts.
3. **Reusable component**: A single `<AuditTrailPopover>` component used across all pages.

### Non-Goals (v1)

1. **Full audit log**: A separate audit log table recording every field-level change is out of scope. This PRD tracks only current state (who created, who last modified).
2. **Audit log API**: No dedicated `/api/audit-log` endpoint for querying change history.
3. **Undo/rollback**: No ability to revert changes based on audit trail.
4. **Bulk change attribution**: Bulk operations attribute to the requesting user; individual item-level tracking within a bulk operation is not required.
5. **Email notifications on changes**: No alerts when records are modified.

---

## User Personas

### Primary: Team Member (Photographer/Admin)

- **Need**: Understand who last touched a collection, connector, or event configuration.
- **Pain Point**: Currently impossible to determine who made a change without asking the team.
- **Goal**: Hover over the "Modified" column in a list view to see full audit details without navigating away.

### Secondary: Team Admin

- **Need**: Audit team activity to ensure correct processes are followed.
- **Pain Point**: No record of who created or modified any entity.
- **Goal**: Quickly identify the user behind any configuration change from both list views and detail dialogs.

---

## Requirements

### Functional Requirements

#### FR-100: Backend — User Attribution Columns

- **FR-100.1**: Add `created_by_user_id` (FK to `users.id`, nullable) to all tenant-scoped entity tables: `collections`, `connectors`, `pipelines`, `jobs`, `analysis_results`, `events`, `event_series`, `categories`, `locations`, `organizers`, `performers`, `configurations`, `push_subscriptions`, `notifications`.
- **FR-100.2**: Add `updated_by_user_id` (FK to `users.id`, nullable) to the same tables.
- **FR-100.3**: Create a single Alembic migration adding both columns to all affected tables. Existing rows will have NULL values for both columns (graceful historical handling).
- **FR-100.4**: Entities that already have `created_by_user_id` (`agents`, `api_tokens`, `agent_registration_tokens`) retain their existing columns and gain `updated_by_user_id` only.
- **FR-100.5**: Both columns use `SET NULL` on delete — if a user is deleted, the attribution is cleared rather than blocking the delete.

#### FR-200: Backend — Service Layer Attribution

- **FR-200.1**: All service `create_*` methods accept `user_id: Optional[int]` and set `created_by_user_id` and `updated_by_user_id` on the new entity.
- **FR-200.2**: All service `update_*` methods accept `user_id: Optional[int]` and set `updated_by_user_id` on the modified entity.
- **FR-200.3**: All API route handlers pass `ctx.user_id` from `TenantContext` to service methods. This single pattern covers **both** session and API token authentication because `TenantContext.user_id` already resolves to the correct user in each case:
  - **Session auth** (browser): `ctx.user_id` = the human user's `User.id`
  - **API token auth** (Bearer): `ctx.user_id` = the token's `system_user.id` (set by `TokenService.validate_token` at `token_service.py:247`). This system user is a dedicated `User` row representing the API token, so mutations performed via API tokens are attributed to that token's system user — clearly distinguishable from human-initiated actions.
- **FR-200.4**: Agent-facing API endpoints (`/api/agent/*`) use a separate authentication path (`get_authenticated_agent` dependency) that returns the `Agent` object directly. These handlers pass `agent.system_user_id` to service methods for attribution.
- **FR-200.5**: No special-casing is needed for API token auth in route handlers. The standard `ctx.user_id` pattern (FR-200.3) already handles it correctly. Implementors MUST NOT add conditional logic like `if ctx.is_api_token: ...` — the middleware abstraction handles this transparently.

#### FR-300: Backend — API Response Schemas

- **FR-300.1**: Add an `AuditInfo` nested schema to all entity response schemas:
  ```python
  class AuditUserSummary(BaseModel):
      guid: str          # usr_xxx
      display_name: Optional[str]
      email: str

  class AuditInfo(BaseModel):
      created_at: datetime
      created_by: Optional[AuditUserSummary]
      updated_at: datetime
      updated_by: Optional[AuditUserSummary]
  ```
- **FR-300.2**: Response schemas include an `audit` field of type `AuditInfo`. The existing top-level `created_at` and `updated_at` fields remain for backward compatibility.
- **FR-300.3**: When `created_by_user_id` or `updated_by_user_id` is NULL (historical records), `created_by`/`updated_by` returns `null`.

#### FR-400: Frontend — AuditTrailPopover Component

- **FR-400.1**: Create `frontend/src/components/ui/audit-trail-popover.tsx` with the following interface:
  ```typescript
  interface AuditInfo {
    created_at: string
    created_by: { guid: string; display_name: string | null; email: string } | null
    updated_at: string
    updated_by: { guid: string; display_name: string | null; email: string } | null
  }

  interface AuditTrailPopoverProps {
    audit: AuditInfo
  }
  ```
- **FR-400.2**: The popover trigger displays `formatRelativeTime(audit.updated_at)` (or `audit.created_at` if `updated_at` equals `created_at`).
- **FR-400.3**: The popover content displays a card with four rows:
  - **Created**: `formatDateTime(created_at)` — by `display_name || email` (or "—" if null)
  - **Modified**: `formatDateTime(updated_at)` — by `display_name || email` (or "—" if null)
- **FR-400.4**: Use Radix UI `Popover` primitive (already available via shadcn/ui) for hover/focus activation.
- **FR-400.5**: The component gracefully handles null `created_by`/`updated_by` by displaying "—" for historical records.

#### FR-500: Frontend — List View Integration

- **FR-500.1**: Add a "Modified" column to all 11 list view tables using `<AuditTrailPopover>`.
- **FR-500.2**: The column renders `<AuditTrailPopover audit={item.audit} />` displaying relative time as the summary.
- **FR-500.3**: The column's `cardRole` is `detail` on mobile, showing the relative time as a key-value row.
- **FR-500.4**: The "Modified" column is positioned as the second-to-last column (before Actions).

**Affected tables:**

| Table | File | New Column Position |
|---|---|---|
| Collections | `CollectionList.tsx` | Before Actions |
| Connectors | `ConnectorList.tsx` | Before Actions (replaces existing Created column) |
| Results | `ResultsTable.tsx` | Before Actions |
| Locations | `LocationsTab.tsx` | Before Actions (replaces existing Created column) |
| Organizers | `OrganizersTab.tsx` | Before Actions (replaces existing Created column) |
| Performers | `PerformersTab.tsx` | Before Actions (replaces existing Created column) |
| Agents | `AgentsPage.tsx` | Before Actions |
| Categories | `CategoriesTab.tsx` | Before Actions (replaces existing Created column) |
| Teams | `TeamsTab.tsx` | Before Actions |
| Tokens | `TokensTab.tsx` | Before Actions (replaces existing Created column) |
| Release Manifests | `ReleaseManifestsTab.tsx` | Before Actions |

- **FR-500.5**: Existing standalone "Created" columns that currently display `formatDateTime(created_at)` are replaced by the new "Modified" column (which includes creation info in the hover popover).

#### FR-600: Frontend — Detail Dialog Integration

- **FR-600.1**: Add an audit trail section at the bottom of all detail dialogs displaying the same information as the popover but in an expanded inline format (no hover required).
- **FR-600.2**: The section renders as a `border-t` separated area with a "History" or "Audit" label.
- **FR-600.3**: Display format:
  ```
  ─────────────────────────────
  Created   Jan 15, 2026, 3:45 PM   by John Doe (john@example.com)
  Modified  Jan 20, 2026, 9:12 AM   by Jane Smith (jane@example.com)
  ```
- **FR-600.4**: If `created_by` or `updated_by` is null, display "—" in place of user info.

**Affected dialogs:**

| Dialog | File |
|---|---|
| Agent Details | `AgentDetailsDialog.tsx` |
| Notification Detail | `NotificationDetailDialog.tsx` |
| Collection Edit (if dialog exists) | Various |
| Any future detail dialog | — |

#### FR-700: Frontend — Type Definitions

- **FR-700.1**: Add `AuditInfo` and `AuditUserSummary` types to `frontend/src/contracts/api/`.
- **FR-700.2**: Update all entity API types (Collection, Connector, Agent, etc.) to include an `audit: AuditInfo` field.

### Non-Functional Requirements

#### NFR-100: Performance

- **NFR-100.1**: Audit user lookups must not introduce N+1 queries. Use `joinedload` or `selectinload` on the `created_by` and `updated_by` relationships.
- **NFR-100.2**: List API endpoints must not increase response time by more than 10% from adding audit user info.
- **NFR-100.3**: The `AuditTrailPopover` renders on hover/focus only — no additional API calls when opening the popover.

#### NFR-200: Data Integrity

- **NFR-200.1**: `created_by_user_id` is set once at creation time and never modified afterward.
- **NFR-200.2**: `updated_by_user_id` is updated on every mutation, including state changes, metadata updates, and relationship changes.
- **NFR-200.3**: Both columns are nullable to support historical data and edge cases (e.g., system migrations).

#### NFR-300: Backward Compatibility

- **NFR-300.1**: Existing API responses retain `created_at` and `updated_at` at the top level. The new `audit` object is additive.
- **NFR-300.2**: Frontend gracefully handles API responses without the `audit` field (transitional state during deployment).
- **NFR-300.3**: Agent API payloads are not affected — agents report results, and the server attributes the action to the agent's system user.

#### NFR-400: Testing

- **NFR-400.1**: Unit tests verify `created_by_user_id` is set on creation for each service.
- **NFR-400.2**: Unit tests verify `updated_by_user_id` is updated on modification for each service.
- **NFR-400.3**: Unit tests verify `AuditInfo` serialization in response schemas, including null user handling.
- **NFR-400.4**: Frontend tests verify `<AuditTrailPopover>` renders correctly with full, partial, and null audit data.

---

## Technical Approach

### 1. Database Schema — AuditMixin

**File**: `backend/src/models/mixins/audit.py` (new)

```python
from sqlalchemy import Column, Integer, ForeignKey


class AuditMixin:
    """
    Mixin that adds created_by_user_id and updated_by_user_id
    foreign key columns to any model.

    Both columns are nullable to support:
    - Historical records created before audit tracking
    - System-level operations without a user context
    - SET NULL on user deletion
    """
    created_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    updated_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
```

Apply to all tenant-scoped models:

```python
# backend/src/models/collection.py
class Collection(Base, GuidMixin, AuditMixin):
    ...
```

### 2. Database Migration

A single Alembic migration adds both columns **and** their indexes to all affected tables. The migration is split into two phases: (1) add columns, (2) create indexes. Indexes use `postgresql_concurrently=True` for large tables to avoid holding `ACCESS EXCLUSIVE` locks during creation.

**Important**: PostgreSQL `CREATE INDEX CONCURRENTLY` cannot run inside a transaction. Alembic migrations run inside a transaction by default, so the index-creation phase must use `op.execute("COMMIT")` to end the implicit transaction before concurrent index creation, or the migration can be split into two files (one transactional for columns, one non-transactional for indexes). The example below uses the single-file approach with explicit transaction management.

```python
# backend/src/db/migrations/versions/0XX_add_audit_user_columns.py

"""Add audit user attribution columns and indexes to all tenant-scoped tables."""

# Tables that need BOTH created_by_user_id and updated_by_user_id
NEW_AUDIT_TABLES = [
    "collections", "connectors", "pipelines", "jobs",
    "analysis_results", "events", "event_series", "categories",
    "locations", "organizers", "performers", "configurations",
    "push_subscriptions", "notifications",
]

# Tables that already have created_by_user_id — only need updated_by_user_id
EXISTING_CREATED_BY_TABLES = [
    "agents", "api_tokens", "agent_registration_tokens",
]

# Tables likely to be large in production — use CONCURRENTLY for indexes
LARGE_TABLES = {"collections", "jobs", "analysis_results", "events", "notifications"}


def upgrade():
    # ── Phase 1: Add columns (transactional, safe) ──────────────────────

    for table in NEW_AUDIT_TABLES:
        op.add_column(table, sa.Column(
            "created_by_user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True
        ))
        op.add_column(table, sa.Column(
            "updated_by_user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True
        ))

    for table in EXISTING_CREATED_BY_TABLES:
        op.add_column(table, sa.Column(
            "updated_by_user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True
        ))

    # ── Phase 2: Create indexes ─────────────────────────────────────────
    # End the implicit transaction so we can use CREATE INDEX CONCURRENTLY
    # for large tables. Small tables use regular (transactional) indexes.
    op.execute("COMMIT")

    all_tables = NEW_AUDIT_TABLES + EXISTING_CREATED_BY_TABLES

    for table in all_tables:
        concurrent = table in LARGE_TABLES

        # created_by_user_id index — skip for tables that already had it
        if table not in EXISTING_CREATED_BY_TABLES:
            op.create_index(
                f"ix_{table}_created_by_user_id",
                table,
                ["created_by_user_id"],
                postgresql_concurrently=concurrent,
            )

        # updated_by_user_id index — all tables need this
        op.create_index(
            f"ix_{table}_updated_by_user_id",
            table,
            ["updated_by_user_id"],
            postgresql_concurrently=concurrent,
        )


def downgrade():
    all_tables = NEW_AUDIT_TABLES + EXISTING_CREATED_BY_TABLES

    for table in reversed(all_tables):
        op.drop_index(f"ix_{table}_updated_by_user_id", table_name=table)
        if table not in EXISTING_CREATED_BY_TABLES:
            op.drop_index(f"ix_{table}_created_by_user_id", table_name=table)

    for table in reversed(EXISTING_CREATED_BY_TABLES):
        op.drop_column(table, "updated_by_user_id")

    for table in reversed(NEW_AUDIT_TABLES):
        op.drop_column(table, "updated_by_user_id")
        op.drop_column(table, "created_by_user_id")
```

**Index naming convention**: `ix_<table>_<column>` (e.g., `ix_collections_created_by_user_id`, `ix_jobs_updated_by_user_id`). This matches Alembic's default naming and is consistent with existing indexes in the schema.

**Concurrency considerations**: Tables in `LARGE_TABLES` use `postgresql_concurrently=True` to avoid blocking reads/writes during index creation. The set should be adjusted based on actual production data volumes. Smaller tables use standard index creation which is faster and simpler.

### 3. Service Layer Pattern

Each service's create and update methods gain user attribution:

```python
# Example: backend/src/services/collection_service.py

def create_collection(
    self,
    data: CollectionCreate,
    team_id: int,
    user_id: Optional[int] = None,  # NEW
) -> Collection:
    collection = Collection(
        name=data.name,
        type=data.type,
        location=data.location,
        team_id=team_id,
        created_by_user_id=user_id,     # NEW
        updated_by_user_id=user_id,     # NEW
        ...
    )
    self.db.add(collection)
    self.db.flush()
    return collection


def update_collection(
    self,
    collection: Collection,
    data: CollectionUpdate,
    user_id: Optional[int] = None,  # NEW
) -> Collection:
    if data.name is not None:
        collection.name = data.name
    ...
    collection.updated_by_user_id = user_id  # NEW
    self.db.flush()
    return collection
```

### 4. Route Handler Pattern — Three Authentication Paths

All three authentication paths converge to a single `user_id: int` parameter passed to service methods. No conditional logic is needed in route handlers.

#### 4a. Session Auth (Browser — Human Users)

`TenantContext.user_id` = the logged-in human user's `User.id`.

```python
# Example: backend/src/api/collection_router.py

@router.post("/", response_model=CollectionResponse)
async def create_collection(
    data: CollectionCreate,
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    service = CollectionService(db)
    collection = service.create_collection(
        data=data,
        team_id=ctx.team_id,
        user_id=ctx.user_id,  # Human user's User.id
    )
    ...
```

#### 4b. API Token Auth (Bearer — Programmatic Access)

`TenantContext.user_id` = the API token's `system_user.id`. This is set automatically by `TokenService.validate_token` (`token_service.py:244-252`), which resolves `api_token.system_user` and sets `user_id=system_user.id` on the `TenantContext`.

The **same route handler code** works for both session and API token auth — no branching needed:

```python
# The SAME handler above also handles API token requests.
# When a Bearer token authenticates:
#   ctx.user_id = api_token.system_user.id  (token's dedicated system user)
#   ctx.is_api_token = True
#
# The service receives the token's system user ID, so the audit trail
# shows: "Modified by API Token: My CI Token (tok_01hgw...)"

@router.put("/{guid}", response_model=CollectionResponse)
async def update_collection(
    guid: str,
    data: CollectionUpdate,
    ctx: TenantContext = Depends(get_tenant_context),
    db: Session = Depends(get_db),
):
    service = CollectionService(db)
    collection = service.update_collection(
        collection=existing,
        data=data,
        user_id=ctx.user_id,  # Token's system_user.id when is_api_token=True
    )
    ...
```

#### 4c. Agent Auth (Agent-Facing Endpoints)

Agent endpoints use a separate `get_authenticated_agent` dependency that returns the `Agent` model directly. The agent's `system_user_id` is passed explicitly:

```python
# backend/src/api/agent/job_router.py

@router.post("/{guid}/complete")
async def complete_job(
    guid: str,
    result: JobCompleteRequest,
    agent: Agent = Depends(get_authenticated_agent),
    db: Session = Depends(get_db),
):
    service = JobService(db)
    service.complete_job(
        job=job,
        result=result,
        user_id=agent.system_user_id,  # Agent's dedicated system user
    )
```

#### Summary: User ID Resolution by Auth Method

| Auth Method | Route Dependency | `user_id` Passed to Service | Display Name in Audit Trail |
|---|---|---|---|
| Session (browser) | `get_tenant_context` | `ctx.user_id` (human `User.id`) | "John Doe (john@example.com)" |
| API Token (Bearer) | `get_tenant_context` | `ctx.user_id` (token's `system_user.id`) | "API Token: My CI Token (tok_xxx@system)" |
| Agent | `get_authenticated_agent` | `agent.system_user_id` | "Agent: Home Mac (agt_xxx@system)" |

### 5. Response Schema — AuditInfo

**File**: `backend/src/schemas/audit.py` (new)

```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AuditUserSummary(BaseModel):
    """Minimal user info for audit attribution."""
    guid: str = Field(..., description="User GUID (usr_xxx)")
    display_name: Optional[str] = Field(None, description="User display name")
    email: str = Field(..., description="User email")

    model_config = {"from_attributes": True}


class AuditInfo(BaseModel):
    """Audit trail information for an entity."""
    created_at: datetime = Field(..., description="Creation timestamp")
    created_by: Optional[AuditUserSummary] = Field(
        None, description="User who created the entity"
    )
    updated_at: datetime = Field(..., description="Last modification timestamp")
    updated_by: Optional[AuditUserSummary] = Field(
        None, description="User who last modified the entity"
    )

    model_config = {"from_attributes": True}
```

Entity response schemas include the `audit` field:

```python
class CollectionResponse(BaseModel):
    guid: str
    name: str
    ...
    # Existing — kept for backward compatibility
    created_at: datetime
    updated_at: datetime
    # New — structured audit info
    audit: Optional[AuditInfo] = None
```

### 6. Model Relationships for Eager Loading

```python
# In Collection model (and all other audited models):
created_by_user = relationship(
    "User",
    foreign_keys=[created_by_user_id],
    lazy="joined",
)
updated_by_user = relationship(
    "User",
    foreign_keys=[updated_by_user_id],
    lazy="joined",
)
```

Using `lazy="joined"` avoids N+1 queries since audit user info is always needed in list responses.

### 7. Frontend — AuditTrailPopover Component

**File**: `frontend/src/components/ui/audit-trail-popover.tsx`

```tsx
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { formatDateTime, formatRelativeTime } from '@/utils/dateFormat'

interface AuditUserSummary {
  guid: string
  display_name: string | null
  email: string
}

interface AuditInfo {
  created_at: string
  created_by: AuditUserSummary | null
  updated_at: string
  updated_by: AuditUserSummary | null
}

interface AuditTrailPopoverProps {
  audit: AuditInfo
}

function userName(user: AuditUserSummary | null): string {
  if (!user) return '—'
  return user.display_name || user.email
}

export function AuditTrailPopover({ audit }: AuditTrailPopoverProps) {
  const isUnmodified = audit.created_at === audit.updated_at
  const summaryTime = formatRelativeTime(audit.updated_at)

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button className="text-sm text-muted-foreground hover:text-foreground
                           underline decoration-dotted underline-offset-4 cursor-default">
          {summaryTime}
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-72 text-sm space-y-2">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Created</span>
          <span>{formatDateTime(audit.created_at)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">by</span>
          <span>{userName(audit.created_by)}</span>
        </div>
        {!isUnmodified && (
          <>
            <div className="border-t border-border pt-2 flex justify-between">
              <span className="text-muted-foreground">Modified</span>
              <span>{formatDateTime(audit.updated_at)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">by</span>
              <span>{userName(audit.updated_by)}</span>
            </div>
          </>
        )}
      </PopoverContent>
    </Popover>
  )
}
```

### 8. Frontend — List View Column Integration

```tsx
// Example: CollectionList.tsx
const columns: ColumnDef<Collection>[] = [
  // ... existing columns ...
  {
    header: 'Modified',
    cell: (item) => item.audit
      ? <AuditTrailPopover audit={item.audit} />
      : <span className="text-muted-foreground">{formatRelativeTime(item.updated_at)}</span>,
    cardRole: 'detail',
  },
  {
    header: 'Actions',
    cell: (item) => <ActionButtons item={item} />,
    cardRole: 'action',
  },
]
```

### 9. Frontend — Detail Dialog Audit Section

```tsx
// Reusable audit section for detail dialogs
function AuditTrailSection({ audit }: { audit: AuditInfo }) {
  return (
    <div className="border-t border-border pt-4 mt-4 space-y-2 text-sm">
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground w-20">Created</span>
        <span>{formatDateTime(audit.created_at)}</span>
        {audit.created_by && (
          <span className="text-muted-foreground">
            by {audit.created_by.display_name || audit.created_by.email}
          </span>
        )}
      </div>
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground w-20">Modified</span>
        <span>{formatDateTime(audit.updated_at)}</span>
        {audit.updated_by && (
          <span className="text-muted-foreground">
            by {audit.updated_by.display_name || audit.updated_by.email}
          </span>
        )}
      </div>
    </div>
  )
}
```

---

## Implementation Plan

### Phase 1: Backend — Database Schema & Migration

**Tasks:**

1. Create `AuditMixin` in `backend/src/models/mixins/audit.py`
2. Apply `AuditMixin` to all tenant-scoped models (14 entities)
3. Add `updated_by_user_id` to the 3 entities that already have `created_by_user_id`
4. Add `created_by_user` and `updated_by_user` relationships to all audited models
5. Create Alembic migration for all column additions
6. Run migration and verify schema

**Checkpoint**: All tables have `created_by_user_id` and `updated_by_user_id` columns. Migration applies cleanly.

---

### Phase 2: Backend — Service Layer & Route Handlers

**Tasks:**

1. Create `AuditInfo` and `AuditUserSummary` Pydantic schemas in `backend/src/schemas/audit.py`
2. Update all service `create_*` methods to accept and set `user_id`
3. Update all service `update_*` methods to accept and set `user_id`
4. Update all route handlers to pass `ctx.user_id` to service methods
5. Update agent-facing route handlers to pass `agent.system_user_id`
6. Add `audit` field to all entity response schemas with `AuditInfo` serialization
7. Write unit tests for user attribution in create/update flows
8. Write unit tests for `AuditInfo` schema serialization (including null users)

**Checkpoint**: API responses include `audit` object with user info. Tests pass.

---

### Phase 3: Frontend — Components & Type Definitions

**Tasks:**

1. Add `AuditInfo` and `AuditUserSummary` TypeScript types in `frontend/src/contracts/api/audit-api.ts`
2. Update all entity API types to include `audit: AuditInfo` field
3. Create `<AuditTrailPopover>` component in `frontend/src/components/ui/audit-trail-popover.tsx`
4. Create `<AuditTrailSection>` component for detail dialogs (same file or separate)
5. Write unit tests for both components (full data, partial data, null users)

**Checkpoint**: Components render correctly in isolation.

---

### Phase 4: Frontend — List View Migrations

**Tasks:**

1. Add "Modified" column to `CollectionList.tsx`
2. Replace "Created" column with "Modified" in `ConnectorList.tsx`
3. Add "Modified" column to `ResultsTable.tsx`
4. Replace "Created" column with "Modified" in `LocationsTab.tsx`, `OrganizersTab.tsx`, `PerformersTab.tsx`
5. Add "Modified" column to `AgentsPage.tsx`
6. Replace "Created" column with "Modified" in `CategoriesTab.tsx`, `TokensTab.tsx`
7. Add "Modified" column to `TeamsTab.tsx`, `ReleaseManifestsTab.tsx`

**Checkpoint**: All 11 list views show the "Modified" column with popover.

---

### Phase 5: Frontend — Detail Dialog Integration

**Tasks:**

1. Add `<AuditTrailSection>` to `AgentDetailsDialog.tsx`
2. Add `<AuditTrailSection>` to `NotificationDetailDialog.tsx`
3. Add `<AuditTrailSection>` to any other detail dialogs or detail views
4. Visual QA across all pages

**Checkpoint**: All detail views show audit trail. Feature complete.

---

## Alternatives Considered

### Audit Storage Strategy

| Approach | Pros | Cons | Decision |
|---|---|---|---|
| **Column-level tracking (chosen)** | Simple; no extra table; fast reads; minimal migration | Only tracks current state (last modifier) | Chosen — satisfies requirements without complexity |
| Separate audit_log table | Full change history; field-level diffs | Complex joins for list views; storage growth; overkill for v1 | Rejected for v1 |
| Event sourcing | Complete history; replayable | Massive architectural change; not justified | Rejected |

### List View Presentation

| Approach | Pros | Cons | Decision |
|---|---|---|---|
| **Hover popover (chosen)** | Compact; no extra space; progressive disclosure | Requires hover (mitigated by focus support) | Chosen — best balance of density and detail |
| Dedicated audit columns | Always visible | Adds 3-4 columns to already wide tables | Rejected |
| Tooltip | Even simpler | Limited formatting; accessibility concerns | Rejected |
| Expandable row | Full details inline | Disrupts table flow; inconsistent with current patterns | Rejected |

---

## Risks and Mitigation

### Risk 1: N+1 Query Performance

- **Impact**: High — Every list query would execute additional queries per row.
- **Probability**: Low — Mitigated by design.
- **Mitigation**: Use `lazy="joined"` on `created_by_user` and `updated_by_user` relationships. Only `guid`, `display_name`, and `email` are included in the `AuditUserSummary` — no deep user object serialization.

### Risk 2: Migration on Large Tables

- **Impact**: Medium — Adding nullable columns with foreign keys to large tables may lock them during migration.
- **Probability**: Low — Nullable columns without defaults are fast to add in PostgreSQL (metadata-only change).
- **Mitigation**: Nullable columns without defaults are essentially free in PostgreSQL. Index creation uses `CONCURRENTLY` if needed.

### Risk 3: Historical Data Without Attribution

- **Impact**: Low — Existing records show "—" for creator/modifier.
- **Probability**: Certain — All existing data predates audit tracking.
- **Mitigation**: UI gracefully handles null values. Over time, as records are updated, `updated_by_user_id` will be populated. A backfill script could optionally attribute existing records to the team's first admin user.

### Risk 4: Popover Usability on Touch Devices

- **Impact**: Medium — Hover is not a native interaction on touch devices.
- **Probability**: Medium — Mobile users cannot hover.
- **Mitigation**: On mobile (`cardRole: 'detail'`), the "Modified" row shows the relative time. Tapping an item and opening its detail dialog reveals full audit info in the `<AuditTrailSection>`. The popover is a desktop enhancement.

### Risk 5: Service Method Signature Changes

- **Impact**: Medium — All service create/update methods gain a new `user_id` parameter.
- **Probability**: Certain — By design.
- **Mitigation**: The parameter is `Optional[int]` with default `None`, so existing internal callers (tests, scripts) continue to work without changes. Only route handlers need updating.

---

## Affected Entities Summary

| Entity | Table | Has `created_by`? | Needs `created_by`? | Needs `updated_by`? |
|---|---|---|---|---|
| Collection | `collections` | No | Yes | Yes |
| Connector | `connectors` | No | Yes | Yes |
| Pipeline | `pipelines` | No | Yes | Yes |
| Job | `jobs` | No | Yes | Yes |
| AnalysisResult | `analysis_results` | No | Yes | Yes |
| Event | `events` | No | Yes | Yes |
| EventSeries | `event_series` | No | Yes | Yes |
| Category | `categories` | No | Yes | Yes |
| Location | `locations` | No | Yes | Yes |
| Organizer | `organizers` | No | Yes | Yes |
| Performer | `performers` | No | Yes | Yes |
| Configuration | `configurations` | No | Yes | Yes |
| PushSubscription | `push_subscriptions` | No | Yes | Yes |
| Notification | `notifications` | No | Yes | Yes |
| Agent | `agents` | Yes | — | Yes |
| ApiToken | `api_tokens` | Yes | — | Yes |
| AgentRegistrationToken | `agent_registration_tokens` | Yes | — | Yes |

---

## Success Metrics

- **M1**: 100% of tenant-scoped entities have `created_by_user_id` and `updated_by_user_id` columns.
- **M2**: All 11 list views display the "Modified" column with audit popover.
- **M3**: All detail dialogs include the audit trail section.
- **M4**: New records created after deployment have non-null `created_by_user_id`.
- **M5**: List API response time increase is <10% compared to pre-implementation baseline.

---

## Future Enhancements

### v1.1
- **Backfill script**: Attribute existing records to team admin based on creation timestamp.
- **"Last modified by me" filter**: Filter list views to show only records the current user last modified.

### v2.0
- **Full audit log table**: Record every field-level change with before/after values.
- **Audit log API**: `GET /api/audit-log?entity_type=collection&entity_guid=col_xxx` endpoint.
- **Activity feed**: Dashboard widget showing recent changes across all entities.
- **Change diff view**: Side-by-side comparison of before/after for a specific change.

---

## Revision History

- **2026-01-31 (v1.2)**: Added explicit index creation to migration
  - Rewrote §2 (Database Migration) to include `op.create_index` calls with `ix_<table>_<column>` naming
  - Added `postgresql_concurrently=True` for large tables (`collections`, `jobs`, `analysis_results`, `events`, `notifications`)
  - Split migration into Phase 1 (add columns, transactional) and Phase 2 (create indexes, non-transactional via explicit `COMMIT`)
  - Skip `created_by_user_id` index for tables that already had the column (`agents`, `api_tokens`, `agent_registration_tokens`)
  - Added `downgrade()` function that drops indexes before columns
- **2026-01-31 (v1.1)**: Clarified API token audit attribution
  - Expanded Background section with auth method resolution table showing how `ctx.user_id` maps to the correct user for session, API token, and agent auth
  - Rewrote FR-200.3 through FR-200.5 to explicitly document that API token auth resolves `ctx.user_id` to `api_token.system_user.id` (via `TokenService.validate_token`)
  - Added FR-200.5 clarification that no special-casing is needed in route handlers
  - Expanded Technical Approach §4 into three subsections (4a/4b/4c) with per-auth-path code examples and a summary resolution table
- **2026-01-31 (v1.0)**: Initial draft
  - Defined column-level audit tracking approach with AuditMixin
  - Specified service layer and route handler attribution patterns
  - Designed AuditTrailPopover and AuditTrailSection frontend components
  - Catalogued all 17 affected entities and 11 list views
  - Created 5-phase implementation plan
  - Documented alternatives considered and risks
