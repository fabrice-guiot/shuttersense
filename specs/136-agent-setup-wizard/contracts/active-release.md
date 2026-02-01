# API Contract: Active Release Manifest

**Endpoint**: `GET /api/agent/v1/releases/active`
**Authentication**: Required (session cookie or API token)
**Authorization**: Any authenticated user (not restricted to super admin)

## Purpose

Returns the currently active release manifest with per-platform artifact details, including download URLs. Used by the Agent Setup Wizard to determine which agent binaries are available for download.

## Request

```
GET /api/agent/v1/releases/active
```

No query parameters. No request body.

### Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Cookie` | Conditional | Session cookie (browser auth) |
| `Authorization` | Conditional | `Bearer <token>` (API token auth) |

One of `Cookie` or `Authorization` must be present.

## Response

### 200 OK — Active manifest found

```json
{
  "guid": "rel_01hgw2bbg0000000000000001",
  "version": "1.0.0",
  "artifacts": [
    {
      "platform": "darwin-arm64",
      "filename": "shuttersense-agent-darwin-arm64",
      "checksum": "sha256:a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
      "file_size": 52428800,
      "download_url": "/api/agent/v1/releases/rel_01hgw2bbg.../download/darwin-arm64",
      "signed_url": "/api/agent/v1/releases/rel_01hgw2bbg.../download/darwin-arm64?expires=1706832000&signature=abc123..."
    },
    {
      "platform": "linux-amd64",
      "filename": "shuttersense-agent-linux-amd64",
      "checksum": "sha256:b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3",
      "file_size": 48234496,
      "download_url": "/api/agent/v1/releases/rel_01hgw2bbg.../download/linux-amd64",
      "signed_url": "/api/agent/v1/releases/rel_01hgw2bbg.../download/linux-amd64?expires=1706832000&signature=def456..."
    }
  ],
  "notes": "Initial stable release",
  "dev_mode": false
}
```

### Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `guid` | string | Release manifest GUID (`rel_` prefix) |
| `version` | string | Semantic version of this release |
| `artifacts` | array | Per-platform artifact entries |
| `artifacts[].platform` | string | Platform identifier (e.g., `darwin-arm64`) |
| `artifacts[].filename` | string | Binary filename |
| `artifacts[].checksum` | string | `sha256:`-prefixed hex checksum |
| `artifacts[].file_size` | number \| null | File size in bytes, null if unknown |
| `artifacts[].download_url` | string \| null | Relative URL for session-authenticated download. Null if binary distribution is not configured. |
| `artifacts[].signed_url` | string \| null | Time-limited signed URL (default 1 hour expiry). Null if binary distribution is not configured. |
| `notes` | string \| null | Optional release notes |
| `dev_mode` | boolean | `true` if the server's binary distribution directory is not configured (signals the wizard to show all platforms) |

### 404 Not Found — No active manifest

```json
{
  "detail": "No active release manifest found"
}
```

Returned when no release manifest with `is_active=true` exists. The wizard handles this by showing the warning banner per FR-008/FR-200.9.

### 401 Unauthorized

```json
{
  "detail": "Authentication required"
}
```

### Behavior Notes

1. **Active manifest selection**: If multiple manifests have `is_active=true`, the endpoint returns the one with the highest version (semantic version sorting) or the most recently created one.
2. **Download URLs**: Built by the backend using the application's own URL. They are relative paths (e.g., `/api/agent/v1/releases/.../download/...`) to work regardless of proxy configuration.
3. **Signed URLs**: Generated at response time with a 1-hour expiry using HMAC-SHA256. Each call to this endpoint generates fresh signed URLs.
4. **dev_mode flag**: Set to `true` when `SHUSAI_AGENT_DIST_DIR` is not configured. The frontend uses this to show all 5 platforms regardless of which artifacts exist.
5. **Empty artifacts**: If the active manifest has no `ReleaseArtifact` rows, the `artifacts` array is empty (not omitted).

## Backend Schema (Pydantic)

```python
class ReleaseArtifactResponse(BaseModel):
    platform: str
    filename: str
    checksum: str
    file_size: Optional[int] = None
    download_url: Optional[str] = None
    signed_url: Optional[str] = None

class ActiveReleaseResponse(BaseModel):
    guid: str
    version: str
    artifacts: List[ReleaseArtifactResponse]
    notes: Optional[str] = None
    dev_mode: bool = False
```

## Frontend Service Function

```typescript
// In frontend/src/services/agents.ts
export async function getActiveRelease(): Promise<ActiveReleaseResponse> {
  const response = await api.get<ActiveReleaseResponse>(
    `${AGENT_API_PATH}/releases/active`
  )
  return response.data
}
```
