# Quickstart: Audit Trail Visibility

## Integration Scenario 1: Creating a Collection (Session Auth)

**Before**:
```
POST /api/collections
Authorization: cookie (session)
→ CollectionService.create_collection(name, type, location, team_id)
→ Collection created without attribution
```

**After**:
```
POST /api/collections
Authorization: cookie (session)
→ CollectionService.create_collection(name, type, location, team_id, user_id=ctx.user_id)
→ Collection.created_by_user_id = ctx.user_id
→ Collection.updated_by_user_id = ctx.user_id
→ Response includes audit.created_by = {guid, display_name, email}
```

## Integration Scenario 2: Updating a Connector (API Token Auth)

**Before**:
```
PUT /api/connectors/{guid}
Authorization: Bearer tok_xxx
→ ConnectorService.update_connector(connector_id, name, ...)
→ Connector updated without attribution
```

**After**:
```
PUT /api/connectors/{guid}
Authorization: Bearer tok_xxx
→ ctx.user_id = system_user.id (resolved by TokenService.validate_token)
→ ConnectorService.update_connector(connector_id, name, ..., user_id=ctx.user_id)
→ Connector.updated_by_user_id = system_user.id
→ Response includes audit.updated_by = {guid: "usr_xxx", display_name: "API Token: My Token", email: "tok_xxx@system.shuttersense"}
```

## Integration Scenario 3: Agent Completing a Job

**Before**:
```
POST /api/agent/jobs/{guid}/complete
Agent Auth: api_key_hash
→ JobService.complete_job(job, result)
→ Job completed without user attribution
```

**After**:
```
POST /api/agent/jobs/{guid}/complete
Agent Auth: api_key_hash
→ agent = get_authenticated_agent(...)
→ JobService.complete_job(job, result, user_id=agent.system_user_id)
→ Job.updated_by_user_id = agent.system_user_id
→ AnalysisResult.created_by_user_id = agent.system_user_id
```

## Integration Scenario 4: Frontend List View

**Before**:
```
CollectionList.tsx columns: Name, Type, State, ..., Actions
No "Modified" column
```

**After**:
```
CollectionList.tsx columns: Name, Type, State, ..., Modified, Actions

Modified column:
  Desktop: "5 min ago" → hover → popover with created/modified details
  Mobile (card): "Modified: 5 min ago" as detail row
```

## Integration Scenario 5: Historical Record (No Attribution)

```
GET /api/collections
→ Collection created before audit tracking:
{
  "guid": "col_xxx",
  "name": "Old Collection",
  "created_at": "2025-11-01T10:00:00Z",
  "updated_at": "2025-11-15T14:30:00Z",
  "audit": {
    "created_at": "2025-11-01T10:00:00Z",
    "created_by": null,        ← No attribution
    "updated_at": "2025-11-15T14:30:00Z",
    "updated_by": null         ← No attribution
  }
}

Frontend renders: "2 months ago" with popover showing "Created: Nov 1, 2025 by —"
```

## Integration Scenario 6: Deleted User Attribution

```
1. User "john@example.com" creates a collection → created_by_user_id = 42
2. User 42 is deleted from the system
3. FK ON DELETE SET NULL → created_by_user_id = NULL
4. API response: audit.created_by = null
5. Frontend renders: "Created: Jan 15, 2026 by —"
```

## FK ON DELETE SET NULL: Implications & Design Decision

### Behavior (as shown in Scenario 6)

When a user is deleted from the system, `ON DELETE SET NULL` on the `created_by_user_id` and `updated_by_user_id` foreign keys causes the attribution to be silently cleared:

```
created_by_user_id = 42  →  (user 42 deleted)  →  created_by_user_id = NULL
```

The API then returns `audit.created_by = null`, and the frontend renders "—" for the user name.

### Implications

1. **Irreversible audit trail gaps**: Once a user is deleted and FKs are set to NULL, the original attribution is permanently lost. There is no way to recover who created or modified a record.
2. **Compliance risks**: Regulatory frameworks (SOC 2, GDPR audit logs, HIPAA) may require audit trail retention for a defined period. Losing attribution on user deletion could violate retention requirements.
3. **Investigation limitations**: If a security incident or data issue requires tracing who performed an action, deleted-user records will show no attribution.

### Alternative Approach: ON DELETE RESTRICT + Soft Deletes

An alternative design uses `ON DELETE RESTRICT` on the user FK and implements soft deletes for User entities:

- **FK behavior**: `ON DELETE RESTRICT` prevents user deletion if any audit trail references exist, preserving attribution integrity.
- **Soft delete**: Users are marked `is_deleted = true` (or `deleted_at = now()`) rather than physically removed. Their display_name and guid remain available for audit rendering.
- **API impact**: `audit.created_by` always returns a user summary (possibly with `display_name: "Deleted User"` annotation) instead of `null`.
- **Tradeoff**: Requires a soft-delete mechanism for Users (migration + model + service changes) and may retain PII longer than desired under GDPR right-to-erasure requests.

### Chosen Approach & Justification

This implementation uses **ON DELETE SET NULL** for the following reasons:

1. **Simplicity**: No additional soft-delete infrastructure is needed for the User model.
2. **GDPR compliance**: Physical user deletion satisfies right-to-erasure requests without complex PII scrubbing of soft-deleted records.
3. **Acceptable loss**: For v1, losing attribution when a user is deleted is an accepted tradeoff. The timestamps (`created_at`, `updated_at`) are always preserved regardless.
4. **Future upgrade path**: If audit retention requirements change, the FK strategy can be migrated from `SET NULL` to `RESTRICT` with a soft-delete User model in a future release without data loss (existing NULLs would remain but new deletions would be soft).

### Acceptance Criteria for Attribution Loss

Attribution loss via SET NULL is acceptable when:
- The user has been intentionally removed from the system (admin action or GDPR erasure).
- The record timestamps are sufficient to correlate events without user identity.
- No active compliance audit requires user-level attribution for the affected records.

Attribution loss is **not** acceptable (and would require the RESTRICT + soft-delete approach) when:
- Regulatory audits require named-user attribution for a defined retention period.
- The organization's security policy requires full audit trails for all entity mutations.

## Key File Touchpoints

### Backend Files (New)
- `backend/src/models/mixins/audit.py` — AuditMixin class
- `backend/src/schemas/audit.py` — AuditInfo, AuditUserSummary schemas
- `backend/src/db/migrations/versions/058_add_audit_user_columns.py` — Migration

### Backend Files (Modified)
- 14 model files — Add AuditMixin
- 3 model files (Agent, ApiToken, AgentRegistrationToken) — Add updated_by_user_id
- ~12 service files — Add user_id parameter to create/update methods
- ~17 route handler files — Pass ctx.user_id to service methods
- ~10 schema files — Add audit field to response schemas

### Frontend Files (New)
- `frontend/src/contracts/api/audit-api.ts` — TypeScript types
- `frontend/src/components/ui/audit-trail-popover.tsx` — Popover + Section components

### Frontend Files (Modified)
- ~15 entity type files — Add audit field
- 11 list view files — Add/replace Modified column
- 2+ detail dialog files — Add AuditTrailSection
