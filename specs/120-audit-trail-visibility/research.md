# Research: Audit Trail Visibility

## Decision 1: Audit Storage Strategy

**Decision**: Column-level tracking on existing entity tables (not a separate audit log table).

**Rationale**:
- Adding `created_by_user_id` and `updated_by_user_id` FK columns directly to each entity table is the simplest approach that satisfies all requirements.
- No extra table joins needed for list queries — audit user info is loaded via eager-joined relationships.
- The PRD explicitly scopes this to "who created/last modified" (current state), not full change history.

**Alternatives considered**:
- **Separate audit_log table**: Full change history with field-level diffs. Rejected — overkill for v1, introduces complex joins for every list query, significant storage growth.
- **Event sourcing**: Complete replayable history. Rejected — massive architectural change not justified by requirements.

## Decision 2: AuditMixin vs Inline Columns

**Decision**: Create an `AuditMixin` class in `backend/src/models/mixins/audit.py` that provides both columns and relationships.

**Rationale**:
- Follows the existing GuidMixin pattern (`backend/src/models/mixins/guid.py`).
- DRY — 14 models need both columns, 3 models need only `updated_by_user_id`.
- The mixin can declare `created_by_user_id`, `updated_by_user_id` columns and `created_by_user`, `updated_by_user` relationships.

**Alternatives considered**:
- **Inline columns on each model**: Rejected — too much duplication across 17 models.
- **SQLAlchemy event listener** (auto-set on flush): Rejected — event listeners lack access to HTTP request context (user_id); explicit passing is clearer and testable.

## Decision 3: TenantContext.user_id for API Token Auth

**Decision**: `ctx.user_id` is already populated for API token auth — no special-casing needed.

**Rationale** (verified in code):
- `TokenService.validate_token()` at `token_service.py:247` sets `user_id=system_user.id` on the returned TenantContext.
- `_authenticate_api_token()` in `tenant.py:218-282` returns this context directly.
- The system_user is a dedicated `User` row (UserType.SYSTEM) created when the API token is provisioned.
- Route handlers can use `ctx.user_id` uniformly for session and API token auth.

**Note**: The docstring comment on TenantContext says "None for unauthenticated or token-only auth" which is **outdated**. The implementation populates user_id for tokens.

## Decision 4: Agent-Facing Route Attribution

**Decision**: Agent endpoints use `agent.system_user_id` passed explicitly to service methods.

**Rationale**:
- Agent auth uses a separate `get_authenticated_agent` dependency returning `AgentContext` (not TenantContext).
- `AgentContext` has `agent_id` but not `user_id` — the agent's system_user_id must be accessed via `agent.system_user_id`.
- Agent service registration creates a system user for each agent at `agent_service.py:279-283`.

## Decision 5: Eager Loading Strategy

**Decision**: Use `lazy="joined"` on `created_by_user` and `updated_by_user` relationships.

**Rationale**:
- List endpoints always need audit user info (for the "Modified" column).
- `joinedload` adds a LEFT JOIN, fetching user data in the same query — no N+1.
- Only 3 lightweight fields are serialized: `guid`, `display_name`, `email`.

**Alternatives considered**:
- **`selectinload`**: Rejected — issues a separate SELECT per relationship, slightly worse for list queries where all rows need the data.
- **`lazy="select"` (default)**: Rejected — N+1 queries for list views.

## Decision 6: Service Method Signature

**Decision**: Add `user_id: Optional[int] = None` to all create/update service methods.

**Rationale**:
- Optional with default None maintains backward compatibility (tests, scripts, internal callers).
- Only route handlers need updating to pass `ctx.user_id`.
- Single parameter works for all three auth paths (session user_id, token system_user_id, agent system_user_id).

## Decision 7: Migration Strategy

**Decision**: Single Alembic migration (revision `058_add_audit_user_columns`) adding columns to all 17 tables.

**Rationale**:
- Adding nullable columns without defaults is a metadata-only change in PostgreSQL — essentially free.
- Index creation uses `CONCURRENTLY` for large tables to avoid blocking.
- The migration needs dialect-aware code (PostgreSQL vs SQLite for tests).
- Follows the existing pattern of sequential numeric revision IDs (head is `057_push_notifications`).

## Decision 8: Frontend Popover vs Tooltip

**Decision**: Use Radix UI Popover (already available via shadcn/ui) for the audit detail card.

**Rationale**:
- Popovers support richer content (multi-line, structured) compared to tooltips.
- The existing Popover component at `frontend/src/components/ui/popover.tsx` is ready to use.
- Popover supports both hover and focus activation for accessibility.
- On mobile, the relative time is shown inline and full audit info is in detail dialogs.

## Decision 9: Entities Requiring Audit Columns

**Verified against codebase — 17 entities total**:

### Need BOTH `created_by_user_id` and `updated_by_user_id` (14 entities):
1. `collections` — tenant-scoped, has team_id
2. `connectors` — tenant-scoped, has team_id
3. `pipelines` — tenant-scoped, has team_id
4. `jobs` — tenant-scoped, has team_id
5. `analysis_results` — tenant-scoped, has team_id
6. `events` — tenant-scoped, has team_id
7. `event_series` — tenant-scoped, has team_id
8. `categories` — tenant-scoped, has team_id
9. `locations` — tenant-scoped, has team_id
10. `organizers` — tenant-scoped, has team_id
11. `performers` — tenant-scoped, has team_id
12. `configurations` — tenant-scoped, has team_id
13. `push_subscriptions` — tenant-scoped, has team_id
14. `notifications` — tenant-scoped, has team_id

### Need ONLY `updated_by_user_id` (3 entities — already have `created_by_user_id`):
15. `agents` — has `created_by_user_id` (FK to users.id, required)
16. `api_tokens` — has `created_by_user_id` (FK to users.id, required)
17. `agent_registration_tokens` — has `created_by_user_id` (FK to users.id, required)

### Excluded from audit tracking:
- `users` — root entity, not tenant-scoped in the relevant sense
- `teams` — root entity
- `event_performers` — junction table, no GUID
- `release_manifests` — super-admin global entity, no team_id
- `storage_metrics` — system metrics
- `inventory_folders` — system inventory data
- `pipeline_history` — has `changed_by` string field (separate tracking)

## Decision 10: Services Requiring user_id Parameter Addition

**Verified — 12 services with create/update methods affecting audited entities**:

1. `CollectionService` — create_collection, update_collection
2. `ConnectorService` — create_connector, update_connector
3. `PipelineService` — create, update, activate, deactivate, set_default
4. `EventService` — create, create_series, update, update_series, soft_delete, restore
5. `CategoryService` — create, update
6. `LocationService` — create, update
7. `OrganizerService` — create, update
8. `PerformerService` — create, update
9. `ResultService` — create_result, update_result
10. `JobCoordinatorService` — create_job (and internal state changes)
11. `NotificationService` — create_notification
12. `ConfigService` — create/update configuration

Agent, Token, and Registration Token services already have `created_by_user_id` in their creation flows.
