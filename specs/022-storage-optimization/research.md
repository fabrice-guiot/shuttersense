# Research: Storage Optimization for Analysis Results

**Feature**: 022-storage-optimization
**Date**: 2026-01-22

## 1. Input State Hash Computation

### Decision: SHA-256 for deterministic hashing

**Rationale**: SHA-256 provides:
- 256-bit output sufficient for collision resistance (birthday attack requires 2^128 operations)
- Available in Python's `hashlib` standard library (used by both backend and agent)
- Fast computation: ~500MB/s on modern hardware
- Deterministic when input is normalized (sorted keys, canonical JSON)

**Alternatives Considered**:
- **MD5**: Faster but cryptographically broken, not suitable for integrity verification
- **SHA-1**: Deprecated, collision attacks demonstrated
- **BLAKE2**: Faster than SHA-256 but less ubiquitous library support

### Implementation Pattern

```python
# Python (agent and backend)
import hashlib
import json

def compute_input_state_hash(components: dict) -> str:
    """Compute deterministic hash from sorted, canonical JSON."""
    canonical = json.dumps(components, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
```

**Key Insight**: JSON serialization must be canonical (sorted keys, no whitespace) to ensure identical hashes. Python's `json.dumps(sort_keys=True)` provides this determinism.

---

## 2. File List Hash Computation

### Decision: Hash of sorted relative file paths

**Rationale**:
- Relative paths ensure portability (same hash regardless of collection root location)
- Sorting ensures determinism regardless of filesystem enumeration order
- Includes only file paths, not metadata (modification time changes shouldn't trigger re-analysis)

**Performance Analysis**:
- 10,000 files × ~100 bytes avg path = 1MB data
- SHA-256 of 1MB: <5ms
- File enumeration is the bottleneck, not hashing

**Alternatives Considered**:
- **Include file sizes**: Rejected - file size changes should trigger re-analysis but this adds complexity for minimal benefit since content changes typically accompany size changes
- **Include modification times**: Rejected - backup/restore operations change mtime without changing content
- **Content hashing**: Rejected - too slow for large collections (would require reading all files)

### Implementation Pattern

```python
# Python (agent)
import hashlib
import os
from pathlib import Path
from typing import List

def compute_file_list_hash(root_path: str) -> str:
    """Compute SHA-256 hash of sorted relative file paths."""
    paths: List[str] = []
    root = Path(root_path)

    for file_path in root.rglob('*'):
        if file_path.is_file():
            # Use forward slashes for cross-platform consistency
            rel_path = file_path.relative_to(root).as_posix()
            paths.append(rel_path)

    paths.sort()  # Case-sensitive alphabetical sort
    joined = '\n'.join(paths)
    return hashlib.sha256(joined.encode('utf-8')).hexdigest()
```

---

## 3. Configuration Hash Computation

### Decision: Hash of tool-relevant configuration subset

**Rationale**: Only configuration values that affect analysis output should be included. Changes to UI preferences shouldn't invalidate cached results.

**Tool-Specific Configuration**:

| Tool | Configuration Keys |
|------|-------------------|
| PhotoStats | `photo_extensions`, `metadata_extensions` |
| Photo Pairing | `photo_extensions`, `camera_mappings`, `processing_methods` |
| Pipeline Validation | `photo_extensions`, `metadata_extensions`, `require_sidecar` |

**Alternatives Considered**:
- **Hash entire configuration**: Rejected - unrelated changes would invalidate all caches
- **No configuration hash**: Rejected - configuration changes should trigger re-analysis

---

## 4. Retention Policy Storage

### Decision: Use existing Configuration model with `result_retention` category

**Rationale**:
- Consistent with existing team-level configuration patterns (cameras, extensions, event_statuses)
- No schema migration needed for storage
- Leverages existing Configuration API endpoints

**Configuration Keys**:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `job_completed_days` | int | 2 | Days to retain completed jobs |
| `job_failed_days` | int | 7 | Days to retain failed jobs |
| `result_completed_days` | int | 0 | Days to retain completed results (0=unlimited) |
| `preserve_per_collection` | int | 1 | Minimum results to keep per (collection, tool) |

**Alternatives Considered**:
- **Dedicated RetentionPolicy model**: Rejected - over-engineering for 4 settings
- **Environment variables**: Rejected - needs to be team-specific

---

## 5. Cleanup Trigger Strategy

### Decision: Trigger cleanup during job creation (before creating new job)

**Rationale**:
- Natural trigger point: cleanup happens when new data is about to be added
- No background jobs needed: simpler operational model
- Self-throttling: cleanup frequency matches job creation frequency
- Failure isolation: cleanup failures don't block job creation (catch and log)

**Performance Considerations**:
- Cleanup uses batch deletes with `LIMIT` to bound transaction size
- Uses `created_at < (now - retention_days)` index for efficient selection
- Deletes in batches of 100 to limit lock duration

**Alternatives Considered**:
- **Scheduled background job**: Rejected - adds operational complexity (cron, Celery)
- **On-demand cleanup API**: Rejected - users would forget to run it
- **Cleanup on result creation**: Rejected - too late, storage already consumed

---

## 6. Reference Following for Reports

### Decision: Single-level reference following only

**Rationale**:
- Simplicity: `download_report_from` points directly to the result with the actual report
- No transitive chains: When creating NO_CHANGE result C referencing B (which references A), C.download_report_from = A.guid (B's source)
- Deletion safety: When B is deleted (intermediate copy cleanup), C still points to A

**Reference Resolution Logic**:

```python
def get_report_source(result: AnalysisResult) -> Optional[AnalysisResult]:
    """Get the result containing the actual report HTML."""
    if result.download_report_from:
        # Follow reference (single level only)
        return get_result_by_guid(result.download_report_from)
    elif result.has_report:
        return result
    else:
        return None
```

**Alternatives Considered**:
- **Transitive following**: Rejected - complex, prone to cycles, harder to debug
- **Denormalized report storage**: Rejected - defeats the storage optimization purpose

---

## 7. Intermediate Copy Cleanup

### Decision: Delete previous copy when new copy references same source

**Rationale**:
- Scenario: A (original) → B (copy at day 5) → C (copy at day 10)
- After C is created: Delete B, keep A and C
- Trend shows: "Stable period from A's date to C's date" based on timestamps

**Implementation**:

```python
def cleanup_intermediate_copies(source_guid: str, new_copy_guid: str, team_id: int):
    """Delete copies that reference the same source, except the new one."""
    intermediate = (
        db.query(AnalysisResult)
        .filter(
            AnalysisResult.team_id == team_id,
            AnalysisResult.download_report_from == source_guid,
            AnalysisResult.no_change_copy == True,
            AnalysisResult.guid != new_copy_guid
        )
        .all()
    )
    for result in intermediate:
        db.delete(result)
```

**Edge Cases**:
- New actual result (D) created: B is NOT deleted (trend needs A → B → D transition)
- Source (A) deleted by retention: C.download_report_from becomes orphaned (returns 404)

---

## 8. Agent API Changes

### Decision: Extend job claim response with previous_result

**Rationale**:
- Agent needs previous result's Input State hash to compare
- Also needs the GUID to reference in NO_CHANGE completion
- Minimal data transfer: only hash and guid, not full result

**JobClaimResponse Extension**:

```python
class PreviousResultInfo(BaseModel):
    guid: str  # res_xxx
    input_state_hash: str  # SHA-256 hex

class JobClaimResponse(BaseModel):
    # ... existing fields ...
    previous_result: Optional[PreviousResultInfo] = None
```

**Lookup Logic**:
- Find most recent COMPLETED result for same (collection, tool)
- For Pipeline Validation: also match (pipeline_guid, pipeline_version)
- Return null if no prior successful result

---

## 9. NO_CHANGE Job Completion

### Decision: New completion endpoint variant for NO_CHANGE

**Rationale**:
- Different payload: references previous result instead of providing results
- Different storage: no report_html, copies metrics from referenced result
- Same endpoint, different status detection

**Completion Payload**:

```python
class JobCompleteRequest(BaseModel):
    status: Literal["COMPLETED", "NO_CHANGE", "FAILED"]

    # For COMPLETED
    results_json: Optional[dict] = None
    report_html: Optional[str] = None
    files_scanned: Optional[int] = None
    issues_found: Optional[int] = None

    # For NO_CHANGE
    previous_result_guid: Optional[str] = None
    input_state_hash: Optional[str] = None

    signature: str
```

---

## 10. Frontend Retention Configuration

### Decision: Add Storage section to Settings > Config Tab

**Rationale**:
- Consistent with existing configuration UI patterns
- Uses same Card-based layout as cameras, extensions, event_statuses
- Dropdown selectors for predefined retention periods

**UI Components**:
- `ResultRetentionSection`: Card with 4 dropdowns
- Dropdown options: 1, 2, 5, 7, 14, 30, 90, 180, 365, Unlimited (0)
- Save on change (auto-save pattern, consistent with other sections)

**Alternatives Considered**:
- **Dedicated Settings page**: Rejected - storage is part of application configuration
- **Number input fields**: Rejected - constrained options prevent invalid values

---

## 11. Backward Compatibility

### Decision: Null Input State means legacy result (no optimization)

**Rationale**:
- Pre-migration results have `input_state_hash = NULL`
- These results are treated as regular results (not copies)
- Cannot be used as source for NO_CHANGE optimization
- Gradually replaced as collections are re-analyzed

**Migration Strategy**:
- Add columns with NULL defaults (no data migration needed)
- Existing results continue to work unchanged
- New results get Input State if agent supports it
- Agent version check not needed (null handling is sufficient)

---

## Summary of Key Decisions

| Topic | Decision | Key Rationale |
|-------|----------|---------------|
| Hash Algorithm | SHA-256 | Collision-resistant, standard library |
| File List | Sorted relative paths | Deterministic, portable |
| Retention Storage | Configuration model | Existing pattern, no migration |
| Cleanup Trigger | On job creation | Self-throttling, no background jobs |
| Reference Following | Single level only | Simple, deletion-safe |
| Intermediate Cleanup | Delete when new copy created | Preserves trend visibility |
| Agent API | Extend claim response | Minimal data, efficient |
| Backward Compat | Null = legacy | Gradual migration, no breaking changes |
