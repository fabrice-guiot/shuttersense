# Quickstart: Storage Optimization for Analysis Results

**Feature**: 022-storage-optimization
**Date**: 2026-01-22

## Overview

This feature implements storage optimization for analysis results through:

1. **Input State Tracking**: Detect when collections haven't changed since last analysis
2. **No-Change Detection**: Skip redundant analysis, reference previous results
3. **Retention Policy**: Automatic cleanup of old jobs and results
4. **Report Reference**: Serve reports from source results for NO_CHANGE results

## Key Concepts

### Input State

The **Input State** is a set of parameters that determine if an analysis result is reproducible:

| Tool | Input State Components |
|------|----------------------|
| PhotoStats | collection_guid, file_list_hash, configuration_hash |
| Photo Pairing | collection_guid, file_list_hash, configuration_hash |
| Pipeline Validation | collection_guid, pipeline_guid, pipeline_version, file_list_hash, configuration_hash |

A SHA-256 hash of these components is stored as `input_state_hash` on each result.

### NO_CHANGE Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. Job Created                                                       │
│    └─► Server queues job for execution                               │
│                                                                      │
│ 2. Agent Claims Job                                                  │
│    └─► Response includes previous_result with input_state_hash       │
│                                                                      │
│ 3. Agent Computes Current Input State                                │
│    └─► file_list_hash = SHA256(sorted file paths)                    │
│    └─► configuration_hash = SHA256(relevant config)                  │
│    └─► input_state_hash = SHA256(all components)                     │
│                                                                      │
│ 4. Agent Compares Hashes                                             │
│    ├─► If MATCH: Complete job with status=NO_CHANGE                  │
│    └─► If DIFFERENT: Execute tool, complete with status=COMPLETED    │
│                                                                      │
│ 5. Server Creates Result                                             │
│    ├─► NO_CHANGE: no_change_copy=true, download_report_from=source   │
│    └─► COMPLETED: no_change_copy=false, report_html=<actual report>  │
└─────────────────────────────────────────────────────────────────────┘
```

### Report Reference Following

When downloading a report for a NO_CHANGE result:

```python
# Simplified logic
def get_report(result_guid):
    result = get_result_by_guid(result_guid)

    if result.download_report_from:
        # Follow reference to source
        source = get_result_by_guid(result.download_report_from)
        if source is None:
            raise NotFoundError("Report no longer available")
        return source.report_html

    return result.report_html
```

## Implementation Steps

### Phase 1: Backend Model Changes

1. Add columns to `analysis_results` table:
   - `input_state_hash` (String, nullable)
   - `input_state_json` (JSONB, nullable)
   - `no_change_copy` (Boolean, default False)
   - `download_report_from` (String, nullable)

2. Add `NO_CHANGE` to `ResultStatus` enum

3. Create database migration

### Phase 2: Retention Configuration

1. Add retention settings endpoints:
   - `GET /api/config/retention`
   - `PUT /api/config/retention`

2. Use Configuration model with category `result_retention`

3. Default settings:
   - `job_completed_days`: 2
   - `job_failed_days`: 7
   - `result_completed_days`: 0 (unlimited)
   - `preserve_per_collection`: 1

### Phase 3: Agent Changes

1. Extend job claim response with `previous_result`

2. Implement Input State computation in agent:
   - File list enumeration and hashing
   - Configuration extraction and hashing
   - Composite hash computation

3. Add NO_CHANGE completion path:
   - Compare hashes
   - Submit NO_CHANGE completion if match

### Phase 4: Cleanup Service

1. Create `CleanupService` with methods:
   - `cleanup_old_jobs(team_id)`
   - `cleanup_old_results(team_id)`
   - `cleanup_intermediate_copies(source_guid, new_copy_guid, team_id)`

2. Trigger cleanup during job creation

3. Batch deletions (100 per transaction)

### Phase 5: Frontend Changes

1. Add `ResultRetentionSection` to Settings > Config Tab

2. Update result list to show NO_CHANGE status badge

3. Handle report download for NO_CHANGE results (no change needed, backend handles)

## Testing Strategy

### Unit Tests

```python
# test_input_state.py
def test_compute_input_state_hash():
    """Hash is deterministic and consistent."""

def test_file_list_hash_ignores_order():
    """Same files in different order produce same hash."""

def test_configuration_hash_only_relevant_keys():
    """Irrelevant config changes don't affect hash."""
```

```python
# test_cleanup_service.py
def test_cleanup_respects_retention_days():
    """Only deletes items older than retention period."""

def test_cleanup_preserves_minimum_results():
    """Keeps at least preserve_per_collection results."""

def test_cleanup_skips_unlimited_retention():
    """No deletion when retention is 0 (unlimited)."""
```

### Integration Tests

```python
# test_no_change_flow.py
def test_no_change_detection_skips_execution():
    """Agent reports NO_CHANGE when input state matches."""

def test_no_change_result_references_source():
    """NO_CHANGE result has download_report_from set."""

def test_report_download_follows_reference():
    """Report download serves source report for NO_CHANGE."""
```

## Configuration Reference

### Retention Settings

| Setting | Type | Default | Options |
|---------|------|---------|---------|
| `job_completed_days` | int | 2 | 0, 1, 2, 5, 7, 14, 30, 90, 180, 365 |
| `job_failed_days` | int | 7 | 0, 1, 2, 5, 7, 14, 30, 90, 180, 365 |
| `result_completed_days` | int | 0 | 0, 1, 2, 5, 7, 14, 30, 90, 180, 365 |
| `preserve_per_collection` | int | 1 | 1, 2, 3, 5, 10 |

Note: 0 = unlimited (no automatic deletion)

### Input State JSON Structure

```json
{
  "collection_guid": "col_01abc...",
  "pipeline_guid": "pip_01xyz...",  // Pipeline Validation only
  "pipeline_version": 3,            // Pipeline Validation only
  "file_list_hash": "sha256hex...",
  "configuration_hash": "sha256hex..."
}
```

## API Quick Reference

### Retention Configuration

```bash
# Get retention settings
GET /api/config/retention

# Update retention settings
PUT /api/config/retention
{
  "job_completed_days": 7,
  "result_completed_days": 30
}
```

### Job Claim (Agent)

```bash
# Claim job (includes previous_result)
POST /api/agent/v1/jobs/claim

# Response includes:
{
  "guid": "job_01...",
  "previous_result": {
    "guid": "res_01...",
    "input_state_hash": "abc123..."
  }
}
```

### Job Complete (Agent)

```bash
# NO_CHANGE completion
POST /api/agent/v1/jobs/{guid}/complete
{
  "status": "NO_CHANGE",
  "previous_result_guid": "res_01...",
  "input_state_hash": "abc123...",
  "signature": "hmac..."
}
```

## Troubleshooting

### Report "No Longer Available"

This occurs when a NO_CHANGE result's source result has been deleted by retention cleanup.

**Resolution**: Re-run the analysis to generate a fresh result with the actual report.

### Input State Mismatch When Nothing Changed

Check:
1. File list is sorted consistently (case-sensitive, Unix path separators)
2. Configuration hash includes only relevant keys
3. JSON serialization is canonical (sorted keys, no whitespace)

### Cleanup Not Running

Cleanup only triggers on job creation. If no jobs are created, no cleanup runs.

**Manual cleanup**: Currently not exposed via API. Consider adding if needed.
