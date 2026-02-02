# Data Model: Agent Setup Wizard

**Feature Branch**: `136-agent-setup-wizard`
**Date**: 2026-02-01

## Entity Overview

```text
┌──────────────────────┐       ┌──────────────────────┐
│   ReleaseManifest    │       │   ReleaseArtifact     │
│   (existing)         │1    * │   (NEW)               │
│──────────────────────│───────│───────────────────────│
│ id (PK)              │       │ id (PK)               │
│ uuid / guid (rel_)   │       │ manifest_id (FK)      │
│ version              │       │ platform              │
│ platforms_json       │       │ filename              │
│ checksum             │       │ checksum              │
│ is_active            │       │ file_size             │
│ notes                │       │ created_at            │
│ created_at           │       │ updated_at            │
│ updated_at           │       └───────────────────────┘
│ created_by_user_id   │
│ updated_by_user_id   │
└──────────────────────┘
```

## New Entity: ReleaseArtifact

Represents a single downloadable agent binary for a specific platform within a release manifest.

### Fields

| Field         | Type        | Constraints                                              | Description                                                                      |
|---------------|-------------|----------------------------------------------------------|----------------------------------------------------------------------------------|
| `id`          | Integer     | PK, auto-increment                                       | Internal primary key                                                             |
| `manifest_id` | Integer     | FK → `release_manifests.id`, NOT NULL, ON DELETE CASCADE  | Parent release manifest                                                          |
| `platform`    | String(50)  | NOT NULL                                                 | Platform identifier (e.g., `darwin-arm64`)                                       |
| `filename`    | String(255) | NOT NULL                                                 | Binary filename (e.g., `shuttersense-agent-darwin-arm64`)                        |
| `checksum`    | String(73)  | NOT NULL                                                 | Prefixed checksum (e.g., `sha256:a1b2c3d4...`)                                  |
| `file_size`   | BigInteger  | Nullable                                                 | File size in bytes (for display; nullable because not always known at creation)   |
| `created_at`  | DateTime    | NOT NULL, server default                                 | Creation timestamp                                                               |
| `updated_at`  | DateTime    | NOT NULL, server default, on update                      | Last update timestamp                                                            |

### Constraints

- **Unique**: `(manifest_id, platform)` — one artifact per platform per manifest
- **Foreign Key**: `manifest_id` → `release_manifests.id` with `ON DELETE CASCADE`
- **Platform validation**: Must be one of `darwin-arm64`, `darwin-amd64`, `linux-amd64`, `linux-arm64`, `windows-amd64`
- **Checksum format**: Must match `^(sha256:)?[0-9a-fA-F]{64}$` (prefixed or bare hex)
- **Filename validation**: Must not contain path separators (`/`, `\`) — filename only, not a path

### Relationships

- **Parent**: `ReleaseManifest` (many-to-one) — accessed via `artifact.manifest`
- **From parent**: `manifest.artifacts` — one-to-many collection, lazy loaded

### Design Notes

- **No GUID**: Artifacts are always accessed through their parent manifest. No use case requires independent GUID-based references.
- **No AuditMixin**: Artifacts inherit audit context from the parent manifest. The manifest's `created_by_user_id` and `updated_by_user_id` cover who manages the release.
- **No team_id**: Release manifests (and their artifacts) are global — not tenant-scoped. All teams see the same agent binaries. This is consistent with the existing `ReleaseManifest` model.
- **CASCADE delete**: If a manifest is deleted, all its artifacts are removed. Artifacts have no meaning without their parent.
- **Checksum prefix**: Using `sha256:` prefix (e.g., `sha256:a1b2c3d4...`) to be explicit about the hash algorithm, matching the PRD format. The prefix is optional in validation to accept bare hex values.

## Modified Entity: ReleaseManifest

### Changes

No column changes. The following additions are made:

1. **New relationship**: `artifacts` — one-to-many to `ReleaseArtifact`, cascade all/delete-orphan
2. **New property**: `artifact_platforms` — returns the set of platforms that have artifacts (as distinct from `platforms` which lists all supported platforms for attestation)

### Backward Compatibility

- The existing `checksum` field remains as the binary attestation checksum (used during agent registration).
- The existing `platforms_json` field remains as the list of platforms this version supports for registration.
- The new `release_artifacts` is purely additive — manifests without artifacts continue to function exactly as before.
- The admin API `POST /api/admin/release-manifests` continues to accept the existing request body. An optional `artifacts` array is added.

## Migration Plan

### Migration: `0XX_add_release_artifacts`

```sql
CREATE TABLE release_artifacts (
    id SERIAL PRIMARY KEY,
    manifest_id INTEGER NOT NULL REFERENCES release_manifests(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    checksum VARCHAR(73) NOT NULL,
    file_size BIGINT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (manifest_id, platform)
);

CREATE INDEX ix_release_artifacts_manifest_id ON release_artifacts(manifest_id);
CREATE INDEX ix_release_artifacts_platform ON release_artifacts(platform);
```

### SQLite Compatibility (Tests)

The migration must handle SQLite differences:
- `SERIAL` → `INTEGER PRIMARY KEY AUTOINCREMENT`
- `NOW()` → `CURRENT_TIMESTAMP`
- Standard Alembic dialect-aware pattern used in existing migrations

### Data Migration

No data migration needed. Existing manifests simply have zero artifacts, which the wizard handles via graceful degradation (FR-008).

## Frontend Type Additions

### New Types (in `agent-api.ts`)

```typescript
interface ReleaseArtifact {
  platform: string          // e.g., "darwin-arm64"
  filename: string          // e.g., "shuttersense-agent-darwin-arm64"
  checksum: string          // e.g., "sha256:a1b2c3d4..."
  file_size: number | null  // bytes, or null if unknown
  download_url: string | null  // constructed by backend, null if dist dir not configured
  signed_url: string | null    // time-limited signed URL, null if dist dir not configured
}

interface ActiveReleaseResponse {
  guid: string              // rel_xxx format
  version: string           // semantic version
  artifacts: ReleaseArtifact[]  // per-platform artifacts
  notes: string | null
  dev_mode: boolean         // true if server is in dev/QA mode (no dist dir configured)
}
```

### Modified Types

The existing `ReleaseManifest` interface in `release-manifests-api.ts` gains an optional `artifacts` field for the admin UI:

```typescript
interface ReleaseManifest {
  // ... existing fields unchanged ...
  artifacts?: ReleaseArtifactAdmin[]  // optional, included when fetching single manifest
}

interface ReleaseArtifactAdmin {
  platform: string
  filename: string
  checksum: string
  file_size: number | null
}
```
