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
→ Response includes audit.updated_by = {guid: "usr_xxx", display_name: "API Token: My Token", email: "tok_xxx@system"}
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
