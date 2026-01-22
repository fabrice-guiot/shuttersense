# PRD: Storage Optimization for Analysis Results

**Issue**: #92
**Status**: Draft
**Created**: 2026-01-22
**Last Updated**: 2026-01-22
**Related Documents**:
- [Domain Model](../domain-model.md)
- [021-distributed-agent-architecture.md](./021-distributed-agent-architecture.md) (Agent-based job processing)

---

## Executive Summary

This PRD defines a storage optimization strategy for analysis results that reduces database bloat while preserving historical trend functionality. The system introduces **Input State tracking** to detect when analysis results would be identical to previous runs, enabling **deduplication through reference linking** instead of storing redundant data.

### Key Design Decisions

1. **Input State Tracking**: Each result captures the key parameters that determine its reproducibility (collection state, pipeline version, configuration)
2. **No-Change Detection**: Before execution, agents compare Input State with the most recent successful result to skip unnecessary processing
3. **Reference Linking**: When input hasn't changed, results reference previous data instead of duplicating storage
4. **Configurable Retention**: Teams configure maximum job retention period; system automatically purges older jobs
5. **Trend Preservation**: First and latest results per Input State are always preserved; trend analysis shows transition points

---

## Background

### Current State

The analysis results system currently:
- Stores every job execution as a complete AnalysisResult record
- Includes full JSONB results and HTML reports (~50KB-500KB per result)
- Retains all historical results indefinitely
- Supports TTL-based auto-refresh that creates new results on schedule
- Has no deduplication mechanism for identical results

### Problem Statement

With scheduled auto-refresh (TTL) creating results hourly/daily for active collections, storage grows linearly regardless of whether the underlying data has changed. For a typical user with:
- 10 collections
- 3 tools per collection (photostats, photo_pairing, pipeline_validation)
- Hourly refresh on active collections

This generates **720 results per day** (10 × 3 × 24), most of which are identical to previous runs. Over a year, this produces **262,800 results** where perhaps only **1,000** represent actual changes.

### Strategic Context

Storage optimization is critical for:
- **Cost Efficiency**: Reducing database storage costs for SaaS deployment
- **Performance**: Faster queries with smaller result tables
- **Trend Integrity**: Maintaining meaningful trend analysis without noise from identical results
- **Scalability**: Supporting larger deployments without exponential storage growth

---

## Goals

### Primary Goals

1. **Storage Reduction**: Eliminate redundant result storage through Input State deduplication
2. **Execution Skip**: Skip tool execution when Input State matches previous successful run
3. **Retention Control**: Enable team-configurable retention policies for automatic cleanup
4. **Trend Preservation**: Maintain trend analysis capability with Input State transition visibility

### Secondary Goals

1. **Report Deduplication**: Share HTML reports between results with identical Input State
2. **Performance Metrics**: Track storage savings and execution skips for monitoring
3. **Backward Compatibility**: Existing results continue to work; optimization applies to new results

### Non-Goals (v1)

1. **Result Compression**: Compressing JSONB data (out of scope)
2. **Archive to Cold Storage**: Moving old results to cheaper storage tiers
3. **Result Merging**: Combining multiple similar results into summaries
4. **Cross-Collection Deduplication**: Deduplication only applies within a collection+tool pair

---

## User Personas

### Primary: System Administrator (Jordan)

- **Current Pain**: Database storage growing rapidly; costs increasing monthly
- **Desired Outcome**: Automatic cleanup of redundant data; predictable storage growth
- **This PRD Delivers**: Retention policies, Input State deduplication, storage metrics

### Secondary: Team Lead (Taylor)

- **Current Pain**: Trend charts cluttered with identical data points
- **Desired Outcome**: Trends show meaningful changes, not repeated identical results
- **This PRD Delivers**: Input State tracking, transition point visibility in trends

### Tertiary: Developer/API User (Alex)

- **Current Pain**: Unnecessary job executions consuming agent resources
- **Desired Outcome**: Jobs skip execution when nothing has changed
- **This PRD Delivers**: No-change detection, execution skip, efficient API response

---

## User Stories

### User Story 1: Retention Policy Configuration (Priority: P0 - Critical)

**As** a team administrator
**I want to** configure a maximum retention period for job results
**So that** old results are automatically cleaned up

**Acceptance Criteria:**
- Config Tab in Settings page includes "Storage" section with retention configuration
- Retention period configurable in days (1, 2, 5, 7, 14, 30, 90, 180, 365, or unlimited)
- Default retention for completed jobs: 2 days
- Default retention for completed results: unlimited
- Default retention for failed jobs: 7 days
- Retention applies to completed jobs separately from analysis results 
- Failed jobs/results have separate (shorter) retention period that applies to the pair (Job+result).
- Completed analysis results have a separate longer retention period than the job that procuded them (no CASCADE delete).
- Changes take effect on next job creation (cleanup runs then)

**Technical Notes:**
- Store as team-level Configuration entry (category: `result_retention`). Requires seeding when a new team is created.
- Cleanup runs during job creation to avoid background job complexity
- Preserve at least one result per (collection, tool) pair regardless of age and result (success or failure)

---

### User Story 2: Input State Tracking (Priority: P0 - Critical)

**As** the system
**I want to** capture the Input State for each analysis result
**So that** I can determine if a new execution would produce identical results

**Acceptance Criteria:**
- Each AnalysisResult stores Input State hash and component values
- Input State components vary by tool type:
  - **PhotoStats/Photo Pairing**: collection_guid, file_list_hash, configuration_hash
  - **Pipeline Validation**: collection_guid, pipeline_guid, pipeline_version, file_list_hash, configuration_hash
  - **Display-Graph mode**: pipeline_guid, pipeline_version only (no collection)
- Input State hash is SHA-256 of sorted component values (file_list should also be sorted)
- Input State stored as JSONB for debugging/audit purposes. Only if DEBUG mode is enabled, as the file_list will be very long (will most likely require chunk upload of the JSON data from the agent-side job).

**Technical Notes:**
- Add `input_state_hash` (varchar 64) and `input_state_json` (JSONB) to AnalysisResult
- File list hash = SHA-256 of sorted file paths within collection
- Configuration hash = SHA-256 of tool-relevant configuration values
- Agent computes hashes during job execution phase

---

### User Story 3: Pre-Job State Retrieval (Priority: P0 - Critical)

**As** an agent
**I want to** receive the previous successful result's Input State before execution
**So that** I can determine if re-execution is necessary

**Acceptance Criteria:**
- Job claim response includes `previous_result` object when available
- Previous result contains: guid, input_state_hash, input_state_json (optional)
- Only most recent successfully COMPLETED result for same (collection, tool, pipeline GUID and pipeline version, depending on what is relevant to the tool) is returned
- Returns null if no previous successful result exists
- Agent can compare current Input State against previous (especially the hashes that cannot be compared server side)

**Technical Notes:**
- Modify `/api/jobs/claim` response schema
- Query: most recent AnalysisResult WHERE collection_id=X AND tool=Y AND status=COMPLETED ORDER BY created_at DESC LIMIT 1 (this example query applies to a tool that depends only on collection)
- Agent computes current Input State before tool execution

---

### User Story 4: No-Change Result Handling (Priority: P1)

**As** an agent
**I want to** report "No Change" when Input State matches previous result
**So that** tool execution is skipped and storage is optimized

**Acceptance Criteria:**
- Agent can complete job with status "NO_CHANGE" (new status)
- Server creates AnalysisResult copying previous result's data
- New result has `no_change_copy=true` flag
- New result has `download_report_from` pointing to source result GUID
- No HTML report stored in the new result (references source)
- Results JSON is copied 
- Created/completed timestamps reflect actual job timing
- Previous result's record is deleted IF it has `no_change_copy=true` flag (it was itself a copy pointing to an earlier record).

**Technical Notes:**
- Add NO_CHANGE to ResultStatus enum
- Add `no_change_copy` boolean (default false) to AnalysisResult
- Add `download_report_from` (varchar, nullable) to AnalysisResult - stores source result GUID unless source result also has `download_report_from`: in that case, keep the `download_report_from` from source.
- On complete with NO_CHANGE: create minimal result record with reference

---

### User Story 5: Standard Completion Processing (Priority: P0 - Critical)

**As** an agent
**I want to** complete jobs normally when Input State has changed
**So that** new results are properly stored

**Acceptance Criteria:**
- Normal completion creates AnalysisResult with `no_change_copy=false`
- Input State captured and stored with result
- HTML report generated and stored in result
- Results JSON stored normally
- `download_report_from` is null (self-contained result)
- Trend analysis can identify this as a state transition point

**Technical Notes:**
- Existing completion flow continues for COMPLETED status
- Add Input State population to result creation
- Input State computed by agent and passed in completion payload

---

### User Story 6: UI Report Retrieval (Priority: P1)

**As** a user
**I want to** download HTML reports for any result
**So that** I can view analysis details regardless of storage optimization

**Acceptance Criteria:**
- Report download checks `download_report_from` before serving
- If `download_report_from` is set, retrieve report from referenced result
- If referenced result is deleted, return appropriate error
- Report filename reflects the referenced result's metadata (not requested)
- Chain following limited to 1 level (no transitive references)

**Technical Notes:**
- Modify `ResultService.get_report()` to check `download_report_from`
- Query referenced result if needed
- Consider caching strategy for frequently accessed reports

---

### User Story 7: Automatic Retention Cleanup (Priority: P1)

**As** the system
**I want to** automatically clean up old jobs and results
**So that** storage is managed according to team policy

**Acceptance Criteria:**
- Cleanup runs during job creation (before creating new job)
- Jobs older than retention period are deleted (with CASCADE to results)
- Failed jobs cleaned up based on failed_retention_days setting
- At least one successful result per (collection, tool) always preserved
- Results with `download_report_from` pointing to deleted results are handled
- Cleanup is idempotent and safe for concurrent execution

**Technical Notes:**
- Add cleanup step to JobCoordinatorService.create_job()
- Batch deletion to avoid long-running transactions
- Consider orphaned reference handling (update reference or delete)

---

### User Story 8: Trend Visualization Enhancement (Priority: P2)

**As** a user
**I want to** see meaningful trends in analysis history
**So that** I can track collection changes over time

**Acceptance Criteria:**
- Trend charts display Input State transition points (use different symbol, not color)
- Trend shows "stable period" between 2 results with same Input state separated by more than a day
- No Input State information displayed in the "Trends" graph
- (Optionally) Storage savings indicator shows deduplication effectiveness

**Technical Notes:**
- Frontend enhancement to results history view
- Add `input_state_changed` derived boolean for display (derived from `no_change_copy=false`)
- Consider aggregation for long time ranges (Series per week, per month instead of per Day)

---

## Key Entities

### AnalysisResult (Enhanced)

Add the following fields to the existing AnalysisResult model:

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `input_state_hash` | String(64) | nullable | SHA-256 hash of Input State components |
| `input_state_json` | JSONB | nullable | Full Input State for debugging |
| `no_change_copy` | Boolean | not null, default=false | True if result references another |
| `download_report_from` | String(35) | nullable | Source result GUID for report |

**Design Notes:**
- `input_state_hash` indexed for efficient comparison queries
- Null `input_state_hash` indicates pre-optimization result (backward compatible)
- `download_report_from` stores full GUID (e.g., `res_01hgw2bbg0000000000000003`). Consider also storing the target result ID for Database FK.

---

### Input State Components

The Input State captures parameters that determine result reproducibility:

| Component | PhotoStats | Photo Pairing | Pipeline Validation | Display-Graph |
|-----------|------------|---------------|---------------------|---------------|
| collection_guid | Yes | Yes | Yes | No |
| file_list_hash | Yes | Yes | Yes | No |
| pipeline_guid | No | No | Yes | Yes |
| pipeline_version | No | No | Yes | Yes |
| configuration_hash | Yes | Yes | Yes | No |

**File List Hash Computation:**
```python
def compute_file_list_hash(file_paths: list[str]) -> str:
    """Hash of sorted file paths within collection."""
    sorted_paths = sorted(file_paths)
    content = "\n".join(sorted_paths)
    return hashlib.sha256(content.encode()).hexdigest()
```

**Configuration Hash Computation:**
```python
def compute_config_hash(config: dict, tool: str) -> str:
    """Hash of tool-relevant configuration values."""
    relevant_keys = TOOL_CONFIG_KEYS[tool]  # Defined per tool
    filtered = {k: v for k, v in config.items() if k in relevant_keys}
    content = json.dumps(filtered, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()
```

---

### Configuration Entries

New team-level configuration entries:

| Category | Key | Type | Default | Description |
|----------|-----|------|---------|-------------|
| `result_retention` | `job_completed_days` | Integer | 7 | Days to retain completed jobs |
| `result_retention` | `job_failed_days` | Integer | 7 | Days to retain failed jobs (and their associated results) |
| `result_retention` | `result_completed_days` | Integer | 0 | Days to retain successful results (default to 'unlimited' represented by 0) |
| `result_retention` | `preserve_per_collection` | Integer | 1 | Minimum results to keep per (collection, tool) |

---

### Job Completion Payload (Enhanced)

Add to agent completion payload:

```json
{
  "status": "COMPLETED|NO_CHANGE|FAILED",
  "input_state": {
    "hash": "sha256...",
    "components": {
      "collection_guid": "col_...",
      "file_list_hash": "sha256...",
      "pipeline_guid": "pip_...",
      "pipeline_version": 3,
      "configuration_hash": "sha256..."
    }
  },
  "referenced_result_guid": "res_...",  // Only for NO_CHANGE
  "results": {...},  // Only for COMPLETED
  "report_html": "...",  // Only for COMPLETED
  "files_scanned": 1234,
  "issues_found": 5
}
```

---

### ResultStatus Enum (Enhanced)

Add new status:

```python
class ResultStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    NO_CHANGE = "no_change"  # New
```

---

## Requirements

### Functional Requirements

#### FR-100: Retention Policy Configuration

- **FR-100.1**: Store retention settings as team Configuration entries
- **FR-100.2**: Support `job_completed_days` setting (1, 2, 5, 7, 14, 30, 90, 180, 365, 0=unlimited, default 2)
- **FR-100.3**: Support `job_failed_days` setting (independent from `job_completed_days`, default 7)
- **FR-100.4**: Support `result_completed_days` setting (independent from `job_completed_days`, default 0)
- **FR-100.5**: Support `preserve_per_collection` minimum (default 1)
- **FR-100.6**: Display retention settings in Settings > Config Tab > Storage section
- **FR-100.7**: Validate settings on save (`job_failed_days` <= `job_completed_days` <= `result_completed_days` when more than one set)

#### FR-200: Input State Tracking

- **FR-200.1**: Compute Input State hash for each tool execution
- **FR-200.2**: Store `input_state_hash` and `input_state_json` (if provided) on AnalysisResult
- **FR-200.3**: Agent computes file_list_hash after listing collection files
- **FR-200.4**: Agent computes configuration_hash from tool-relevant config
- **FR-200.5**: Input State components vary by tool type (see entity definition)
- **FR-200.6**: Null Input State for pre-migration results (backward compatible)

#### FR-300: Pre-Job State Retrieval

- **FR-300.1**: Job claim response includes `previous_result` when available
- **FR-300.2**: Previous result contains guid, input_state_hash, input_state_json
- **FR-300.3**: Query returns most recent COMPLETED result for (collection, tool, and potentially pipeline and pipeline version)
- **FR-300.4**: Returns null previous_result if no prior result exists
- **FR-300.5**: Pipeline validation includes pipeline_guid in matching criteria

#### FR-400: No-Change Detection and Handling

- **FR-400.1**: Agent compares current Input State hash with previous
- **FR-400.2**: If match, agent completes job with status NO_CHANGE
- **FR-400.3**: NO_CHANGE completion requires `referenced_result_guid`
- **FR-400.4**: Server creates AnalysisResult with `no_change_copy=true`
- **FR-400.5**: New result stores reference GUID in `download_report_from`
- **FR-400.6**: No report_html stored for NO_CHANGE results
- **FR-400.7**: results_json and metrics (files_scanned, issues_found) copied from referenced result

#### FR-500: Report Retrieval with References

- **FR-500.1**: ResultService checks `download_report_from` before serving
- **FR-500.2**: If set, fetch report from referenced result
- **FR-500.3**: Return 404 if referenced result deleted (with appropriate message)
- **FR-500.4**: No transitive reference following (max 1 level)
- **FR-500.5**: Report filename uses requesting result's metadata

#### FR-600: Automatic Cleanup

- **FR-600.1**: Cleanup triggered during job creation
- **FR-600.2**: Delete jobs older than team's `job_completed_days` setting. Does not delete linked results.
- **FR-600.3**: Delete results older than team's `result_completed_days` setting. 
- **FR-600.4**: Delete failed jobs older than team's `job_failed_days` setting. Deletes linked results.
- **FR-600.5**: Preserve minimum results per (collection, tool) regardless of age and status
- **FR-600.6**: Handle orphaned references (result points to deleted source)
- **FR-600.7**: Batch deletions to limit transaction size
- **FR-600.8**: Skip cleanup if retention is unlimited (0 days)
- **FR-600.9**: Cleanup redundant `no_change_copy` results (by deleting previous result if itself is a copy)

#### FR-700: API and UI Updates

- **FR-700.1**: Results list API returns `input_state_hash` and `no_change_copy`
- **FR-700.2**: Results list supports filter by `no_change_copy` (show/hide duplicates)
- **FR-700.3**: Result detail shows Input State transition indicator
- **FR-700.4**: Trend charts can optionally collapse NO_CHANGE results
- **FR-700.5**: Storage stats endpoint shows deduplication metrics

---

### Non-Functional Requirements

#### NFR-100: Performance

- **NFR-100.1**: Index on `input_state_hash` for efficient comparison
- **NFR-100.2**: Cleanup query limits batch size to 1000 records
- **NFR-100.3**: No-change detection adds < 50ms to job completion
- **NFR-100.4**: File list hash computation < 1s for 10,000 files

#### NFR-200: Storage

- **NFR-200.1**: NO_CHANGE results use < 1KB storage (vs 50-500KB for full)
- **NFR-200.2**: Target 80%+ storage reduction for stable collections
- **NFR-200.3**: Monitor storage savings via metrics

#### NFR-300: Reliability

- **NFR-300.1**: Cleanup failures don't block job creation
- **NFR-300.2**: Reference integrity maintained (orphan handling)
- **NFR-300.3**: Backward compatible with existing results

#### NFR-400: Testing

- **NFR-400.1**: Unit tests for Input State computation
- **NFR-400.2**: Integration tests for no-change detection flow
- **NFR-400.3**: Tests for reference following in report retrieval
- **NFR-400.4**: Tests for retention cleanup edge cases

---

## Technical Approach

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Agent (Binary)                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   Input State Computation                    ││
│  │  - List collection files → file_list_hash                   ││
│  │  - Get relevant config → configuration_hash                  ││
│  │  - Combine components → input_state_hash                    ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                    │
│                              ▼                                    │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   No-Change Detection                        ││
│  │  IF current_hash == previous_result.input_state_hash        ││
│  │     THEN complete(NO_CHANGE, ref=previous_guid)             ││
│  │     ELSE execute tool, complete(COMPLETED, results)         ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼ REST API
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │               JobCoordinatorService                          ││
│  │  claim_job():                                                ││
│  │    - Return previous_result with Input State                 ││
│  │  complete_job():                                             ││
│  │    - Handle COMPLETED: store full result                     ││
│  │    - Handle NO_CHANGE: store reference result                ││
│  │  create_job():                                               ││
│  │    - Run retention cleanup first                             ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                  ResultService                               ││
│  │  get_report():                                               ││
│  │    - Check download_report_from                              ││
│  │    - Follow reference if set                                 ││
│  │    - Return HTML content                                     ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │               RetentionService (New)                         ││
│  │  cleanup_old_results():                                      ││
│  │    - Query retention settings                                ││
│  │    - Delete expired jobs in batches                          ││
│  │    - Preserve minimum per (collection, tool)                 ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼ PostgreSQL
┌─────────────────────────────────────────────────────────────────┐
│                        Database                                  │
│  analysis_results:                                               │
│    + input_state_hash VARCHAR(64)                               │
│    + input_state_json JSONB                                     │
│    + no_change_copy BOOLEAN DEFAULT false                       │
│    + download_report_from VARCHAR(35)                           │
│                                                                  │
│  configurations:                                                 │
│    category='result_retention', key='completed_days'            │
│    category='result_retention', key='failed_days'               │
└─────────────────────────────────────────────────────────────────┘
```

### Job Claim Flow (Enhanced)

```
Agent                              Server
  │                                  │
  │  POST /api/jobs/claim            │
  │────────────────────────────────>│
  │                                  │
  │                                  │ Find available job
  │                                  │ Query previous result:
  │                                  │   SELECT * FROM analysis_results
  │                                  │   WHERE collection_id = job.collection_id
  │                                  │     AND tool = job.tool
  │                                  │     AND status = 'completed'
  │                                  │   ORDER BY created_at DESC
  │                                  │   LIMIT 1
  │                                  │
  │  200 OK                          │
  │  {                               │
  │    "job": {...},                 │
  │    "previous_result": {          │
  │      "guid": "res_...",          │
  │      "input_state_hash": "...",  │
  │      "input_state_json": {...}   │
  │    }                             │
  │  }                               │
  │<────────────────────────────────│
  │                                  │
```

### Job Completion Flow (No-Change)

```
Agent                              Server
  │                                  │
  │  Compute current Input State     │
  │  Compare with previous_result    │
  │  hash matches → skip execution   │
  │                                  │
  │  POST /api/jobs/{guid}/complete  │
  │  {                               │
  │    "status": "NO_CHANGE",        │
  │    "input_state": {              │
  │      "hash": "abc123...",        │
  │      "components": {...}         │
  │    },                            │
  │    "referenced_result_guid":     │
  │      "res_01hgw..."              │
  │  }                               │
  │────────────────────────────────>│
  │                                  │
  │                                  │ Validate referenced result exists
  │                                  │ Create AnalysisResult:
  │                                  │   status = 'no_change'
  │                                  │   no_change_copy = true
  │                                  │   download_report_from = ref_guid
  │                                  │   report_html = null
  │                                  │   Copy: results_json, files_scanned, issues_found
  │                                  │
  │  200 OK                          │
  │<────────────────────────────────│
```

### Database Migration

```sql
-- Migration: Add Input State and reference fields to analysis_results

ALTER TABLE analysis_results
ADD COLUMN input_state_hash VARCHAR(64);

ALTER TABLE analysis_results
ADD COLUMN input_state_json JSONB;

ALTER TABLE analysis_results
ADD COLUMN no_change_copy BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE analysis_results
ADD COLUMN download_report_from VARCHAR(35);

-- Index for efficient Input State comparison
CREATE INDEX idx_results_input_state_hash
ON analysis_results(input_state_hash)
WHERE input_state_hash IS NOT NULL;

-- Index for finding reference sources
CREATE INDEX idx_results_download_from
ON analysis_results(download_report_from)
WHERE download_report_from IS NOT NULL;

-- Update ResultStatus enum to include NO_CHANGE
-- (Handled via Alembic enum migration)
```

### Retention Cleanup Query

```python
def cleanup_old_results(
    db: Session,
    team_id: int,
    job_completed_days: int,
    result_completed_days: int,
    job_failed_days: int,
    preserve_count: int = 1
):
    """Delete old results while preserving minimum per collection+tool."""

    cutoff_job_completed = datetime.utcnow() - timedelta(days=job_completed_days)
    cutoff_result_completed = datetime.utcnow() - timedelta(days=result_completed_days)
    cutoff_job_failed = datetime.utcnow() - timedelta(days=job_failed_days)

    # Subquery: results to preserve (most recent N per collection+tool)
    # Consider alternative approach for performance: 
    # select the most recent N per (collection_id, tool) using a window function
    # (e.g., row_number() OVER (PARTITION BY AnalysisResult.collection_id,
    # AnalysisResult.tool ORDER BY AnalysisResult.created_at DESC)) and filter
    # row_number <= preserve_count, then delete AnalysisResult rows where id NOT IN
    # that preserve_subq (i.e., exclude preserved IDs)
    preserve_subq = (
        db.query(AnalysisResult.id)
        .filter(AnalysisResult.team_id == team_id)
        .filter(AnalysisResult.status == ResultStatus.COMPLETED)
        .order_by(
            AnalysisResult.collection_id,
            AnalysisResult.tool,
            AnalysisResult.created_at.desc()
        )
        .distinct(AnalysisResult.collection_id, AnalysisResult.tool)
        .limit(preserve_count)
        .subquery()
    )

    # Delete old completed jobs
    # Make sure no CASCADE delete of Results
    if job_completed_days > 0:
        db.query(Job).filter(
            Job.team_id == team_id,
            Job.status == JobStatus.COMPLETED,
            Job.completed_at < cutoff_job_completed,
        ).delete(synchronize_session=False)

    # Delete old completed results (except preserved)
    if result_completed_days > 0:
        db.query(AnalysisResult).filter(
            AnalysisResult.team_id == team_id,
            AnalysisResult.status == ResultStatus.COMPLETED,
            AnalysisResult.created_at < cutoff_result_completed,
            AnalysisResult.id.in_(preserve_subq)
        ).delete(synchronize_session=False)

    # Delete old failed results
    # Make sure CASCADE delete of Results
    if job_failed_days > 0:
        db.query(Job).filter(
            Job.team_id == team_id,
            Job.status == JobStatus.FAILED,
            Job.completed_at < cutoff_job_failed
        ).delete(synchronize_session=False)

    db.commit()
```

---

## Implementation Plan

### Phase 1: Database Schema (Priority: P0)

**Tasks:**

1. **Add Input State Fields**
   - Add `input_state_hash` to AnalysisResult model
   - Add `input_state_json` to AnalysisResult model
   - Create database migration
   - Add index on `input_state_hash`

2. **Add Reference Fields**
   - Add `no_change_copy` to AnalysisResult model
   - Add `download_report_from` to AnalysisResult model
   - Create database migration
   - Add index on `download_report_from`

3. **Update ResultStatus Enum**
   - Add NO_CHANGE to ResultStatus
   - Create Alembic enum migration
   - Update schema validators

**Checkpoint**: Database schema supports all new fields

---

### Phase 2: Agent Input State Computation (Priority: P0)

**Tasks:**

1. **File List Hash Computation**
   - Implement file listing for collection path
   - Compute SHA-256 of sorted file paths
   - Handle large collections efficiently

2. **Configuration Hash Computation**
   - Define tool-relevant configuration keys
   - Filter and hash configuration values
   - Handle missing configuration gracefully

3. **Input State Assembly**
   - Combine components per tool type
   - Compute overall Input State hash
   - Serialize to JSON for storage

**Checkpoint**: Agent can compute Input State for any job

---

### Phase 3: Pre-Job State Retrieval (Priority: P0)

**Tasks:**

1. **Backend Query Enhancement**
   - Query most recent completed result for (collection, tool)
   - Include Input State in job claim response
   - Handle null case (no previous result)

2. **API Schema Updates**
   - Add `previous_result` to job claim response schema
   - Define PreviousResultResponse schema
   - Update OpenAPI documentation

3. **Agent Claim Processing**
   - Parse previous_result from claim response
   - Store for comparison during execution
   - Handle null previous_result

**Checkpoint**: Agent receives previous Input State with claimed job

---

### Phase 4: No-Change Detection (Priority: P1)

**Tasks:**

1. **Agent Comparison Logic**
   - Compare current vs previous Input State hash
   - Decision: execute if different, skip if same
   - Handle edge cases (no previous, null hash)

2. **NO_CHANGE Completion**
   - Complete job with NO_CHANGE status
   - Include referenced result GUID
   - Include computed Input State

3. **Backend NO_CHANGE Handling**
   - Validate referenced result exists and accessible
   - Create minimal AnalysisResult record
   - Copy metrics from referenced result
   - Set reference fields appropriately
   - Check cleanup requirements for referenced result
   - Update storage savings calculation (if referenced result gets deleted)

**Checkpoint**: Agent skips execution when Input State unchanged

---

### Phase 5: Report Retrieval (Priority: P1)

**Tasks:**

1. **Reference Following**
   - Check `download_report_from` in ResultService
   - Fetch report from referenced result
   - Handle deleted reference gracefully

2. **Error Handling**
   - Return 404 with message if reference broken
   - Log orphaned references for monitoring
   - Consider reference repair mechanism

3. **Frontend Updates**
   - Handle NO_CHANGE status display
   - Show "identical to previous" indicator
   - Link to source result in UI

**Checkpoint**: Reports served correctly for NO_CHANGE results

---

### Phase 6: Retention Configuration (Priority: P1)

**Tasks:**

1. **Configuration Schema**
   - Add result_retention configuration category
   - Define completed_days, failed_days, preserve_per_collection
   - Set defaults and validation rules

2. **Settings UI**
   - Add Storage section to Settings page
   - Retention period dropdown/input
   - Separate failed retention setting
   - Save confirmation with impact estimate

3. **Backend ConfigService Updates**
   - CRUD for retention settings
   - Default value handling
   - Team-scoped storage

**Checkpoint**: Teams can configure retention policies

---

### Phase 7: Automatic Cleanup (Priority: P1)

**Tasks:**

1. **RetentionService Implementation**
   - Cleanup query with preservation logic
   - Batch processing for large deletions
   - Orphan reference handling

2. **Integration with Job Creation**
   - Trigger cleanup at job creation
   - Non-blocking (catch and log errors)
   - Skip if unlimited retention

3. **Monitoring and Metrics**
   - Track cleanup runs and deletions
   - Storage savings calculation
   - Admin visibility into cleanup status

**Checkpoint**: Old results automatically cleaned up

---

### Phase 8: UI Enhancements (Priority: P2)

**Tasks:**

1. **Results List Updates**
   - Show/hide NO_CHANGE filter
   - Input State changed indicator
   - Reference link for NO_CHANGE results

2. **Trend Visualization**
   - Collapse consecutive NO_CHANGE results
   - Show transition points prominently
   - Storage savings metric display

3. **Storage Dashboard**
   - Total storage used
   - Deduplication effectiveness
   - Results by status breakdown

**Checkpoint**: UI fully supports optimized results

---

## Risks and Mitigation

### Risk 1: Reference Integrity

- **Impact**: High - Broken references cause missing reports
- **Probability**: Medium - Deletion and reference timing
- **Mitigation**:
  - Mark references as orphaned rather than failing
  - Consider reference pinning (don't delete referenced results)
  - Graceful degradation in UI

### Risk 2: Hash Collisions

- **Impact**: Low - False no-change detection
- **Probability**: Very Low - SHA-256 collision probability negligible
- **Mitigation**:
  - Store full Input State JSON for verification
  - Manual re-run option in UI

### Risk 3: File List Performance

- **Impact**: Medium - Slow job execution for large collections
- **Probability**: Medium - Collections can have 100K+ files
- **Mitigation**:
  - Async file listing
  - Cache file list hash with collection
  - Skip hash if collection modified_at unchanged

### Risk 4: Cleanup Impact

- **Impact**: Medium - Accidental data loss
- **Probability**: Low - With preserve_per_collection safeguard
- **Mitigation**:
  - Always preserve minimum results
  - Dry-run mode for testing
  - Audit log of deletions

### Risk 5: Agent Compatibility

- **Impact**: High - Old agents don't support Input State
- **Probability**: Certain during rollout
- **Mitigation**:
  - Graceful handling of missing Input State
  - Agent version check in claim
  - Force agent update for optimization benefits

---

## Open Questions

1. **Reference Pinning**: Should results referenced by `download_report_from` be exempt from retention cleanup? This would offer additional protection regarding data loss.

2. **Cascading References**: If result A references result B, and B references C, should we follow the chain or flatten to direct reference? This should never happen: would be an indication of data corruption, or failure in the "No Change" tool result report handling.

3. **Partial Changes**: What if only some Input State components change? Should we store delta or full results? This applies only to the DEBUG mode, so it's not relevant for the normal use case.

4. **Configuration Change Detection**: Should configuration changes be detected separately from file changes? This would be interesting for the Trend charts to only display transition points for actual Collection changes.

5. **Manual Override**: Should users be able to force full execution even if Input State matches? This will need to be implemented at some point.

6. **Storage Quota**: Should teams have storage quotas in addition to retention periods? Consider for a future Epic.

7. **Archive Option**: Should old results be archived (downloadable) rather than deleted? Consider for a future Epic.

8. **Notification**: Should cleanup notify team admins of deleted result counts? Consider keeping a metric for Deleted Jobs and Deleted Results as part of the Storage Savings metrics.

---

## Testing Strategy

### Unit Tests

- Input State hash computation (all tools)
- File list hash with various path formats
- Configuration hash with missing/extra keys
- NO_CHANGE completion validation
- Reference following logic
- Retention cleanup query correctness

### Integration Tests

- Complete no-change detection flow (agent → server → result)
- Report retrieval with reference following
- Cleanup with preservation rules
- Concurrent job creation and cleanup
- Migration of existing results

### Security Tests

- Cross-team reference access (should fail)
- Reference manipulation attempts
- Cleanup doesn't affect other teams

### Performance Tests

- File list hash for 100K files
- Cleanup query for 1M results
- Reference lookup latency

---

## Dependencies

### External Dependencies

- None (uses existing stack)

### Internal Dependencies

- Agent binary updates for Input State computation
- Database migration infrastructure
- Existing ResultService and JobCoordinatorService

---

## Appendix

### A. Input State Examples

**PhotoStats Example:**
```json
{
  "hash": "abc123def456...",
  "components": {
    "collection_guid": "col_01hgw2bbg0000000000000001",
    "file_list_hash": "789xyz...",
    "configuration_hash": "111aaa..."
  }
}
```

**Pipeline Validation Example:**
```json
{
  "hash": "def789abc123...",
  "components": {
    "collection_guid": "col_01hgw2bbg0000000000000001",
    "pipeline_guid": "pip_01hgw2bbg0000000000000002",
    "pipeline_version": 5,
    "file_list_hash": "789xyz...",
    "configuration_hash": "111aaa..."
  }
}
```

**Display-Graph Example (no collection):**
```json
{
  "hash": "ghi012jkl345...",
  "components": {
    "pipeline_guid": "pip_01hgw2bbg0000000000000002",
    "pipeline_version": 5
  }
}
```

### B. Configuration Defaults

```yaml
result_retention:
  job_completed_days: 2      # 2 days
  result_completed_days: 0      # unlimited
  job_failed_days: 7         # 1 week
  preserve_per_collection: 1  # Always keep latest
```

### C. Related Issues

| Issue | Title | Relevance |
|-------|-------|-----------|
| #90 | Distributed Agent Architecture | Agents compute Input State |
| #24 | Remote Photo Collections | Collection file listing |
| #42 | Entity UUID Implementation | GUID format for references |

### D. Glossary

| Term | Definition |
|------|------------|
| **Input State** | The set of parameters that determine analysis reproducibility |
| **No-Change** | Result status when Input State matches previous execution |
| **Reference Linking** | Storing pointer to source result instead of duplicating data |
| **Retention Policy** | Team configuration for automatic result cleanup |
| **Deduplication** | Eliminating redundant storage through Input State matching |

---

## Revision History

- **2026-01-22 (v1.2)**: CodeRabbit.ai review
  - Fixed consistency of new Settings definition
  - Fixed sample Python code for Cleanup based on Settings
  - Added a comment in that code for alternative Query for preserving Analysis Results

- **2026-01-22 (v1.1)**: Stakeholder review
  - Refined Settings and their default values
  - Added JSON Result copy
  - Added intermediate Copied results cleanup

- **2026-01-22 (v1.0)**: Initial draft
  - Defined Input State tracking concept
  - Specified no-change detection flow
  - Detailed retention policy configuration
  - Created implementation plan with 8 phases
  - Identified risks and open questions
