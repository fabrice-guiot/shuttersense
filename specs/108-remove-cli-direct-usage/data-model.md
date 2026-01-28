# Data Model: Remove CLI Direct Usage

**Feature Branch**: `108-remove-cli-direct-usage`
**Created**: 2026-01-28

## Overview

This feature introduces three new local data entities (agent-side only) and extends two existing server-side entities. No new database tables are created on the server - all new data lives as JSON files on the agent's local filesystem.

---

## New Entities (Agent Local Storage)

### TestCacheEntry

Cached result of a local path test, used to avoid redundant testing during the test-then-create workflow. Stored as individual JSON files keyed by path hash.

**Storage**: `{data_dir}/test-cache/{path_hash}.json`
**TTL**: 24 hours from `tested_at`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| path | string | Yes | Absolute path that was tested |
| path_hash | string | Yes | SHA-256 hash of normalized path (filename key) |
| tested_at | datetime | Yes | When the test was executed |
| expires_at | datetime | Yes | `tested_at` + 24 hours |
| accessible | boolean | Yes | Whether path was accessible |
| file_count | integer | Yes | Total files found |
| photo_count | integer | Yes | Files matching photo extensions |
| sidecar_count | integer | Yes | Files matching metadata extensions |
| tools_tested | list[string] | Yes | Tools that were run (empty if `--check-only`) |
| issues_found | dict | No | Summary of issues per tool |
| agent_id | string | Yes | GUID of the agent that ran the test |
| agent_version | string | Yes | Version of the agent binary |

**Validation Rules**:
- `path` must be an absolute path
- `file_count` >= `photo_count` + `sidecar_count`
- `tools_tested` values must be in `["photostats", "photo_pairing", "pipeline_validation"]`
- `expires_at` must be exactly 24 hours after `tested_at`

**Lifecycle**: Created by `test` command. Read by `collection create` command. Expired entries cleaned up on next `test` run.

---

### CollectionCache

Local snapshot of all Collections bound to the agent, enabling offline listing and offline tool execution.

**Storage**: `{data_dir}/collection-cache.json`
**TTL**: 7 days from `synced_at`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| agent_guid | string | Yes | GUID of this agent |
| synced_at | datetime | Yes | When cache was last refreshed from server |
| expires_at | datetime | Yes | `synced_at` + 7 days |
| collections | list[CachedCollection] | Yes | All bound collections |

#### CachedCollection (embedded)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| guid | string | Yes | Collection GUID (e.g., `col_01hgw2bbg...`) |
| name | string | Yes | Collection display name |
| type | string | Yes | `LOCAL`, `S3`, `GCS`, or `SMB` |
| location | string | Yes | Path (LOCAL) or bucket/prefix (remote) |
| bound_agent_guid | string | No | Agent GUID for LOCAL collections |
| connector_guid | string | No | Connector GUID for remote collections |
| connector_name | string | No | Connector display name |
| is_accessible | boolean | No | Last known accessibility status |
| last_analysis_at | datetime | No | When last analysis completed |
| supports_offline | boolean | Yes | `true` only for LOCAL type |

**Validation Rules**:
- `type` must be one of `LOCAL`, `S3`, `GCS`, `SMB`
- `supports_offline` must be `true` if and only if `type == "LOCAL"`
- LOCAL collections must have `bound_agent_guid`
- Remote collections must have `connector_guid`

**Lifecycle**: Created/updated by `collections sync` and `collections list` (online mode). Read by `run --offline` and `collections list --offline`. Warning displayed when expired (>7 days).

---

### OfflineResult

Analysis result produced during offline execution, pending upload to the server.

**Storage**: `{data_dir}/results/{result_id}.json`
**TTL**: None (persists until synced or manually deleted)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| result_id | string | Yes | Locally generated UUID (not a server GUID) |
| collection_guid | string | Yes | GUID of the collection analyzed |
| collection_name | string | Yes | Display name (for sync preview) |
| tool | string | Yes | Tool used: `photostats`, `photo_pairing`, `pipeline_validation` |
| executed_at | datetime | Yes | When the analysis ran |
| agent_guid | string | Yes | GUID of the executing agent |
| agent_version | string | Yes | Agent binary version |
| analysis_data | dict | Yes | Full analysis output (tool-specific JSON) |
| html_report_path | string | No | Path to locally saved HTML report |
| synced | boolean | Yes | Whether this result has been uploaded (default: false) |

**Validation Rules**:
- `collection_guid` must match a known collection (from cache)
- `tool` must be one of `["photostats", "photo_pairing", "pipeline_validation"]`
- `synced` is `false` on creation, set to `true` after successful upload
- `result_id` is a UUID v4 generated locally

**Lifecycle**: Created by `run --offline`. Read by `sync` command. Marked `synced=true` and optionally deleted after successful upload.

---

## Existing Entities (Server-Side - Extensions)

### Collection (existing - no schema changes)

The existing `Collection` model already has all fields needed:
- `bound_agent_id`: FK to Agent (used for LOCAL collections)
- `type`: CollectionType enum (`LOCAL`, `S3`, `GCS`, `SMB`)
- `is_accessible`: Boolean for accessibility status
- `last_error`: String for error details

**New behavior**: Agent-initiated creation sets `bound_agent_id` to the creating agent and inherits the agent's `team_id`.

### Job (existing - no schema changes)

The existing `Job` model already supports all needed states:
- `status`: Includes `COMPLETED` for offline result uploads
- `agent_id`: Set to the uploading agent
- `completed_at`: Set from the offline result's `executed_at`

**New behavior**: Offline result upload creates a Job record with `status=COMPLETED` directly (never goes through PENDING/ASSIGNED/RUNNING).

### AnalysisResult (existing - no schema changes)

The existing `AnalysisResult` model stores analysis output:
- `analysis_data`: JSONB column for full results
- `report_html`: Text column for HTML report
- `collection_id`: FK to Collection

**New behavior**: Offline result upload creates an AnalysisResult with the same structure as online results.

---

## Entity Relationships

```
Agent (server)
  │
  ├── bound_collections: Collection[] (1:N)
  │     └── analysis_results: AnalysisResult[] (1:N)
  │           └── job: Job (1:1)
  │
  └── [local filesystem]
        ├── TestCacheEntry[] (keyed by path_hash)
        ├── CollectionCache (single file)
        │     └── CachedCollection[] (mirrors server Collections)
        └── OfflineResult[] (keyed by result_id)
```

**Data flow**:
1. `test` command → creates TestCacheEntry (local only)
2. `collection create` → reads TestCacheEntry, calls server API → creates Collection (server)
3. `collections sync` → reads server Collections → updates CollectionCache (local)
4. `run --offline` → reads CollectionCache, runs analysis → creates OfflineResult (local)
5. `sync` → reads OfflineResults, uploads to server → creates Job + AnalysisResult (server)

---

## State Transitions

### OfflineResult States

```
[Created] → synced=false
    │
    ├── sync command succeeds → synced=true → [Deleted]
    │
    └── sync command fails → synced=false (retry later)
```

### TestCacheEntry Lifecycle

```
[Created] → valid (within 24h)
    │
    ├── collection create reads it → consumed (still valid for re-reads)
    │
    └── 24h elapsed → expired → [Cleaned up on next test run]
```
