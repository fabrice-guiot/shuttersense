# API Contract: Audit Schema

## New Schema Objects

### AuditUserSummary

Minimal user representation for audit attribution display.

```json
{
  "guid": "usr_01hgw2bbg0000000000000001",
  "display_name": "John Doe",
  "email": "john@example.com"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| guid | string | Yes | User GUID (usr_xxx format) |
| display_name | string \| null | No | May be null for system users without a display name |
| email | string | Yes | Always present |

### AuditInfo

Structured audit trail included in all entity responses.

```json
{
  "created_at": "2026-01-15T15:45:00Z",
  "created_by": {
    "guid": "usr_01hgw2bbg0000000000000001",
    "display_name": "John Doe",
    "email": "john@example.com"
  },
  "updated_at": "2026-01-20T09:12:00Z",
  "updated_by": {
    "guid": "usr_01hgw2bbg0000000000000002",
    "display_name": "Jane Smith",
    "email": "jane@example.com"
  }
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| created_at | datetime (ISO 8601) | Yes | Always present (from entity timestamp) |
| created_by | AuditUserSummary \| null | No | Null for historical records |
| updated_at | datetime (ISO 8601) | Yes | Always present (from entity timestamp) |
| updated_by | AuditUserSummary \| null | No | Null for historical records |

### AuditInfo for Historical Records (null users)

```json
{
  "created_at": "2025-12-01T10:00:00Z",
  "created_by": null,
  "updated_at": "2025-12-15T14:30:00Z",
  "updated_by": null
}
```

## Entity Response Changes

All entity response schemas add an `audit` field. Existing `created_at`/`updated_at` top-level fields remain.

### Example: CollectionResponse (before)

```json
{
  "guid": "col_01hgw2bbg0000000000000001",
  "name": "My Collection",
  "created_at": "2026-01-15T15:45:00Z",
  "updated_at": "2026-01-20T09:12:00Z"
}
```

### Example: CollectionResponse (after)

```json
{
  "guid": "col_01hgw2bbg0000000000000001",
  "name": "My Collection",
  "created_at": "2026-01-15T15:45:00Z",
  "updated_at": "2026-01-20T09:12:00Z",
  "audit": {
    "created_at": "2026-01-15T15:45:00Z",
    "created_by": {
      "guid": "usr_01hgw2bbg0000000000000001",
      "display_name": "John Doe",
      "email": "john@example.com"
    },
    "updated_at": "2026-01-20T09:12:00Z",
    "updated_by": {
      "guid": "usr_01hgw2bbg0000000000000002",
      "display_name": "API Token: CI Pipeline",
      "email": "tok_ci@system.shuttersense"
    }
  }
}
```

### Example: Agent-Modified Collection

```json
{
  "guid": "col_01hgw2bbg0000000000000001",
  "audit": {
    "created_at": "2026-01-15T15:45:00Z",
    "created_by": {
      "guid": "usr_01hgw2bbg0000000000000001",
      "display_name": "John Doe",
      "email": "john@example.com"
    },
    "updated_at": "2026-01-22T08:00:00Z",
    "updated_by": {
      "guid": "usr_01hgw2bbg0000000000000005",
      "display_name": "Agent: Home Mac",
      "email": "agt_home_mac@system.shuttersense"
    }
  }
}
```

## Affected Entity Responses (17 total)

All of the following response schemas gain the `audit: AuditInfo | null` field:

| Response Schema | Router File |
|----------------|-------------|
| CollectionResponse | collections.py |
| ConnectorResponse | connectors.py |
| PipelineResponse | pipelines.py |
| JobResponse | tools.py |
| AnalysisResultSummary / AnalysisResultResponse | results.py |
| EventResponse / EventDetailResponse | events.py |
| EventSeriesResponse | events.py |
| CategoryResponse | categories.py |
| LocationResponse | locations.py |
| OrganizerResponse | organizers.py |
| PerformerResponse | performers.py |
| ConfigurationResponse | config.py |
| PushSubscriptionResponse | notifications.py |
| NotificationResponse | notifications.py |
| AgentResponse | admin/teams.py, agent/routes.py |
| ApiTokenResponse | tokens.py |
| AgentRegistrationTokenResponse | admin/teams.py |

## No New Endpoints

This feature adds no new API endpoints. The `audit` field is embedded in existing entity responses.

## Backend Test Requirements

1. **Schema serialization tests**: Verify AuditInfo serializes correctly with full data, partial data (null users), and null audit.
2. **Service create tests**: Verify `created_by_user_id` and `updated_by_user_id` are set on creation.
3. **Service update tests**: Verify `updated_by_user_id` is updated; `created_by_user_id` is preserved.
4. **User deletion tests**: Verify SET NULL behavior when attributed user is deleted.
5. **Response integration tests**: Verify entity API responses include `audit` field.
