# ShutterSense API Reference

The ShutterSense backend exposes a RESTful API with 140+ endpoints. This document covers API conventions and provides an index of all endpoint groups.

## Interactive Documentation

When the server is running, interactive API documentation is available at:

- **Swagger UI**: `http://localhost:8000/api-docs`
- **ReDoc**: `http://localhost:8000/api-redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## API Conventions

### Base URL

All API endpoints are prefixed with `/api/` except health and version:

```
GET  /health          # Health check (no /api prefix)
GET  /api/version     # Application version
GET  /api/collections # Collection listing
```

### Authentication

Most endpoints require authentication. Two methods are supported:

| Method | Header | Use Case |
|--------|--------|----------|
| Session cookie | `Cookie: shusai_session=...` | Web UI (set by OAuth flow) |
| API Token | `Authorization: Bearer tok_...` | Agents, scripts |

**Public endpoints** (no auth required):
- `GET /health`
- `GET /api/version`
- `GET /api/auth/*` (OAuth flows)
- `POST /api/agent/v1/register` (one-time token)

### GUID-Based Identifiers

All entities use GUIDs in API paths and responses:

```
GET /api/collections/col_01hgw2bbg0000000000000001
```

Internal numeric IDs are never exposed. Response bodies include `.guid` properties.

### Tenant Scoping

All data is scoped to the authenticated user's team. Accessing another team's data returns `404 Not Found` (not `403 Forbidden`).

### Pagination

List endpoints support pagination:

```
GET /api/collections?page=1&page_size=20
```

Response includes pagination metadata in the response body.

### Error Format

Error responses follow a consistent format:

```json
{
  "detail": "Collection not found",
  "status_code": 404
}
```

Validation errors (422) include field-level details:

```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Endpoint Groups

### Authentication (`/api/auth`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/auth/google/login` | Initiate Google OAuth flow |
| GET | `/api/auth/google/callback` | Google OAuth callback |
| GET | `/api/auth/microsoft/login` | Initiate Microsoft OAuth flow |
| GET | `/api/auth/microsoft/callback` | Microsoft OAuth callback |
| POST | `/api/auth/logout` | End session |
| GET | `/api/auth/me` | Get current user info |

### Collections (`/api/collections`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/collections/stats` | Collection KPI statistics |
| GET | `/api/collections` | List collections |
| POST | `/api/collections` | Create collection |
| GET | `/api/collections/{guid}` | Get collection details |
| PUT | `/api/collections/{guid}` | Update collection |
| DELETE | `/api/collections/{guid}` | Delete collection |
| POST | `/api/collections/{guid}/test` | Test accessibility |
| POST | `/api/collections/{guid}/refresh` | Refresh file listing cache |
| POST | `/api/collections/{guid}/assign-pipeline` | Assign pipeline |
| POST | `/api/collections/{guid}/clear-pipeline` | Clear pipeline assignment |
| POST | `/api/collections/from-inventory` | Create from inventory |
| POST | `/api/collections/{guid}/clear-inventory-cache` | Clear inventory cache |

### Connectors (`/api/connectors`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/connectors` | List connectors |
| POST | `/api/connectors` | Create connector |
| GET | `/api/connectors/{guid}` | Get connector details |
| PUT | `/api/connectors/{guid}` | Update connector |
| DELETE | `/api/connectors/{guid}` | Delete connector |
| POST | `/api/connectors/{guid}/test` | Test connection |
| GET | `/api/connectors/stats` | Connector statistics |

### Events (`/api/events`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/events` | List events (date range, category, status filters) |
| POST | `/api/events` | Create standalone event |
| POST | `/api/events/series` | Create event series |
| GET | `/api/events/{guid}` | Get event details |
| PATCH | `/api/events/{guid}` | Update event |
| DELETE | `/api/events/{guid}` | Soft-delete event |
| GET | `/api/events/stats` | Event KPI statistics |
| POST | `/api/events/{guid}/performers` | Link performer |
| DELETE | `/api/events/{guid}/performers/{performer_guid}` | Unlink performer |

### Categories (`/api/categories`)

Standard CRUD: `GET` list, `POST` create, `GET/{guid}`, `PATCH/{guid}`, `DELETE/{guid}`

### Locations (`/api/locations`)

Standard CRUD: `GET` list, `POST` create, `GET/{guid}`, `PATCH/{guid}`, `DELETE/{guid}`

### Organizers (`/api/organizers`)

Standard CRUD: `GET` list, `POST` create, `GET/{guid}`, `PATCH/{guid}`, `DELETE/{guid}`

### Performers (`/api/performers`)

Standard CRUD: `GET` list, `POST` create, `GET/{guid}`, `PATCH/{guid}`, `DELETE/{guid}`

### Pipelines (`/api/pipelines`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/pipelines` | List pipelines |
| POST | `/api/pipelines` | Create pipeline |
| GET | `/api/pipelines/{guid}` | Get pipeline details |
| PUT | `/api/pipelines/{guid}` | Update pipeline |
| DELETE | `/api/pipelines/{guid}` | Delete pipeline |
| POST | `/api/pipelines/{guid}/validate` | Validate pipeline structure |
| POST | `/api/pipelines/{guid}/activate` | Activate pipeline |
| POST | `/api/pipelines/{guid}/set-default` | Set as default |
| GET | `/api/pipelines/{guid}/history` | Get version history |

### Tools & Jobs (`/api/tools`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/tools/run` | Create a new job |
| POST | `/api/tools/run-all/{collection_guid}` | Run all tools on collection |
| GET | `/api/tools/jobs` | List jobs |
| GET | `/api/tools/jobs/{job_id}` | Get job details |
| POST | `/api/tools/jobs/{job_id}/cancel` | Cancel job |
| POST | `/api/tools/jobs/{job_id}/retry` | Retry failed job |
| GET | `/api/tools/queue/status` | Queue status |
| WS | `/api/tools/ws/jobs/all` | All jobs progress (WebSocket) |
| WS | `/api/tools/ws/jobs/{job_id}` | Single job progress (WebSocket) |

### Results (`/api/results`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/results` | List analysis results |
| GET | `/api/results/{guid}` | Get result details |
| GET | `/api/results/{guid}/report` | Get HTML report |
| DELETE | `/api/results/{guid}` | Delete result |

### Trends (`/api/trends`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/trends` | Get trend data |
| GET | `/api/trends/metrics` | Available metrics |
| GET | `/api/trends/collections` | Collections with trend data |

### Analytics (`/api/analytics`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/analytics/stats` | Global analytics KPIs |
| GET | `/api/analytics/storage` | Storage metrics |
| GET | `/api/analytics/activity` | Recent activity feed |

### Notifications (`/api/notifications`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/notifications` | List notifications |
| PATCH | `/api/notifications/{guid}/read` | Mark as read |
| POST | `/api/notifications/mark-all-read` | Mark all as read |
| GET | `/api/notifications/preferences` | Get preferences |
| PUT | `/api/notifications/preferences` | Update preferences |
| POST | `/api/notifications/push/subscribe` | Subscribe to push |
| DELETE | `/api/notifications/push/unsubscribe` | Unsubscribe from push |

### Users (`/api/users`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/users` | List team members |
| GET | `/api/users/me` | Get current user |
| PATCH | `/api/users/me` | Update profile |

### API Tokens (`/api/tokens`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/tokens` | List tokens |
| POST | `/api/tokens` | Create token |
| DELETE | `/api/tokens/{guid}` | Revoke token |

### Configuration (`/api/config`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/config` | Get all configuration |
| GET | `/api/config/{category}` | Get category config |
| PUT | `/api/config/{category}/{key}` | Set config value |
| DELETE | `/api/config/{category}/{key}` | Delete config value |
| POST | `/api/config/import` | Import from YAML |

### Admin - Teams (`/api/admin/teams`) - Super Admin Only

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/teams` | List all teams |
| POST | `/api/admin/teams` | Create team |
| GET | `/api/admin/teams/{guid}` | Get team details |
| PATCH | `/api/admin/teams/{guid}` | Update team |
| DELETE | `/api/admin/teams/{guid}` | Delete team |

### Admin - Release Manifests (`/api/admin/release-manifests`) - Super Admin Only

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/release-manifests` | List manifests |
| POST | `/api/admin/release-manifests` | Create manifest |
| GET | `/api/admin/release-manifests/{guid}` | Get manifest |
| DELETE | `/api/admin/release-manifests/{guid}` | Delete manifest |

### Agent API (`/api/agent/v1`) - Agent Authentication

See [Agent Protocol](agent-protocol.md) for detailed documentation.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/agent/v1/register` | Register agent (one-time token) |
| POST | `/api/agent/v1/heartbeat` | Agent heartbeat |
| GET | `/api/agent/v1/me` | Get agent info |
| POST | `/api/agent/v1/disconnect` | Disconnect agent |
| POST | `/api/agent/v1/jobs/claim` | Claim a queued job |
| POST | `/api/agent/v1/jobs/{guid}/progress` | Report job progress |
| POST | `/api/agent/v1/jobs/{guid}/complete` | Complete job with results |
| POST | `/api/agent/v1/jobs/{guid}/fail` | Report job failure |
| GET | `/api/agent/v1/jobs/{guid}/config` | Get job configuration |
| POST | `/api/agent/v1/jobs/{guid}/no-change` | Report no changes detected |
| GET | `/api/agent/v1/config` | Get team configuration |
| POST | `/api/agent/v1/jobs/{guid}/uploads/initiate` | Initiate chunked upload |
| PUT | `/api/agent/v1/uploads/{id}/{chunk}` | Upload chunk |
| GET | `/api/agent/v1/uploads/{id}/status` | Upload status |
| POST | `/api/agent/v1/uploads/{id}/finalize` | Finalize upload |
| DELETE | `/api/agent/v1/uploads/{id}` | Cancel upload |
