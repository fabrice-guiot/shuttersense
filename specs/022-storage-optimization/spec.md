# Feature Specification: Storage Optimization for Analysis Results

**Feature Branch**: `022-storage-optimization`
**Created**: 2026-01-22
**Status**: Draft
**Input**: User description: "Github issue #92, taking into account all the functional requirements documented in docs/prd/022-storage-optimization-analysis-results.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Configure Retention Policy (Priority: P1)

As a team administrator, I want to configure retention periods for jobs and results so that old data is automatically cleaned up and storage costs are controlled.

**Why this priority**: Retention configuration is the foundational setting that enables automatic cleanup. Without this, the system cannot manage storage growth. This story provides immediate value by allowing administrators to control data lifecycle.

**Independent Test**: Can be fully tested by accessing Settings > Config Tab > Storage section, setting retention values, and verifying the values persist. Delivers value by establishing the policy framework for automatic cleanup.

**Acceptance Scenarios**:

1. **Given** a team administrator on the Settings page, **When** they navigate to the Config Tab > Storage section, **Then** they see retention configuration options for completed jobs, completed results, and failed jobs.

2. **Given** retention settings displayed, **When** the administrator selects a retention period from the dropdown (options: 1, 2, 5, 7, 14, 30, 90, 180, 365 days, or unlimited), **Then** the selection is saved and takes effect on next job creation.

3. **Given** default settings for a new team, **When** viewing retention configuration, **Then** completed jobs default to 2 days, completed results default to unlimited, and failed jobs default to 7 days.

4. **Given** a team with configured retention settings, **When** a job is created, **Then** the cleanup process runs using the team's configured retention values.

---

### User Story 2 - Skip Execution When Input Unchanged (Priority: P1)

As a system user running scheduled or manual analysis jobs, I want the system to skip execution when the collection hasn't changed since the last successful run so that system resources are conserved and results appear faster.

**Why this priority**: This is the core optimization that reduces unnecessary processing. Collections that haven't changed shouldn't require full re-analysis. This directly addresses the problem of 262,800 annual results where only ~1,000 represent actual changes.

**Independent Test**: Can be tested by running the same analysis tool twice on an unchanged collection. The second run should complete almost instantly with a "no change" indication instead of performing full analysis.

**Acceptance Scenarios**:

1. **Given** a collection with a previous successful analysis result, **When** the same analysis tool runs and the collection files, pipeline configuration, and tool configuration are unchanged, **Then** the system reports completion with "No Change" status without executing the full analysis.

2. **Given** a "No Change" result, **When** viewing the result in the UI, **Then** the result displays the same metrics (files scanned, issues found) as the referenced previous result.

3. **Given** a collection that has changed since the last analysis (new files, modified configuration, or different pipeline version), **When** the analysis tool runs, **Then** the system performs full execution and stores complete results.

4. **Given** no previous successful result exists for a collection+tool combination, **When** analysis runs, **Then** the system performs full execution regardless of Input State.

---

### User Story 3 - Download Reports from Optimized Results (Priority: P1)

As a user viewing analysis results, I want to download HTML reports for any result including "No Change" results so that I can view detailed analysis information regardless of storage optimization.

**Why this priority**: Users must be able to access reports for all results. Without this, the optimization would degrade the user experience by making reports unavailable for deduplicated results.

**Independent Test**: Can be tested by creating a "No Change" result and then downloading its report. The report should be served correctly from the referenced source result.

**Acceptance Scenarios**:

1. **Given** a "No Change" result that references a previous result, **When** the user requests to download the HTML report, **Then** the system retrieves and serves the report from the referenced source result.

2. **Given** a regular completed result with its own report, **When** the user requests to download the report, **Then** the system serves the report directly from that result.

3. **Given** a "No Change" result whose referenced source result has been deleted, **When** the user requests the report, **Then** the system returns an appropriate error message indicating the report is no longer available.

---

### User Story 4 - Automatic Cleanup of Old Data (Priority: P2)

As the system, I want to automatically clean up old jobs and results according to retention policy so that storage is managed without manual intervention.

**Why this priority**: Automatic cleanup operationalizes the retention policy. While administrators can configure retention (Story 1), this story implements the actual cleanup mechanism. It's P2 because manual cleanup could serve as a temporary workaround.

**Independent Test**: Can be tested by setting a short retention period, creating jobs, advancing time (or using test utilities), and verifying that old jobs are automatically deleted while the minimum preserved results remain.

**Acceptance Scenarios**:

1. **Given** a team with completed jobs older than their `job_completed_days` setting, **When** a new job is created, **Then** old completed jobs are deleted (without cascading to results).

2. **Given** a team with completed results older than their `result_completed_days` setting, **When** cleanup runs, **Then** old completed results are deleted.

3. **Given** a team with failed jobs older than their `job_failed_days` setting, **When** cleanup runs, **Then** old failed jobs and their associated results are deleted.

4. **Given** retention configured with `preserve_per_collection` set to 1, **When** cleanup runs, **Then** at least the most recent result per (collection, tool) combination is preserved regardless of age or status.

5. **Given** unlimited retention (0 days) configured, **When** job creation occurs, **Then** cleanup is skipped and all data is preserved.

---

### User Story 5 - Clean Up Redundant No-Change Copies (Priority: P2)

As the system, I want to remove intermediate "No Change" copy results when a new "No Change" result is created referencing the same source so that storage is minimized while preserving trend visibility.

**Why this priority**: This prevents accumulation of redundant copy records. If a collection stays unchanged for 30 days, we only need the first result (with actual data) and the latest result (showing when it was last checked), not 30 intermediate copies.

**Independent Test**: Can be tested by running three consecutive unchanged analyses on the same collection. After the third run, only two results should exist: the original with data and the latest copy (the middle copy should be deleted).

**Acceptance Scenarios**:

1. **Given** a result A (original) referenced by result B (copy with `no_change_copy=true`), **When** a new "No Change" result C is created also referencing A, **Then** result B is deleted and only A and C remain.

2. **Given** a result A (original) referenced by result B (copy), **When** a new "Completed" result D is created with new data, **Then** result B is preserved (no deletion) and the trend shows: A → B → D transition.

3. **Given** the first result in a stable period and the latest result, **When** viewing trends, **Then** the trend correctly displays the duration of the stable period between these two points.

---

### User Story 6 - View Input State Transitions in Trends (Priority: P3)

As a user analyzing collection trends, I want to see meaningful transitions in the trend visualization so that I understand when actual changes occurred versus stable periods.

**Why this priority**: This enhances trend analysis by distinguishing between genuine changes and stable periods. It's P3 because the core functionality works without this visualization enhancement.

**Independent Test**: Can be tested by creating a series of results with Input State changes interspersed with "No Change" results, then viewing the trend chart to verify transition points are visually distinguished.

**Acceptance Scenarios**:

1. **Given** a collection with multiple analysis results over time, **When** viewing the trend chart, **Then** Input State transition points (where `no_change_copy=false` after a `no_change_copy=true` period) are visually distinguished using a different symbol (not color).

2. **Given** two results with the same Input State separated by more than a day, **When** viewing trends, **Then** the chart displays the period as a "stable period" indicator.

3. **Given** a transition from one Input State to another, **When** viewing trends, **Then** three consecutive points are visible: first result with previous state, last result with previous state, and new result with new state.

---

### User Story 7 - View Storage Metrics (Priority: P3)

As a team administrator, I want to view storage metrics and deduplication effectiveness so that I can understand the impact of storage optimization and retention policies.

**Why this priority**: This provides visibility into the optimization's effectiveness. It's P3 because the core optimization works without metrics visibility; this is observability enhancement.

**Independent Test**: Can be tested by navigating to Analytics > Report Storage tab and verifying KPI cards display cumulative metrics that increment after cleanup runs.

**Acceptance Scenarios**:

1. **Given** a team with storage optimization enabled, **When** viewing Analytics > Report Storage tab, **Then** the user sees KPI cards showing total reports generated, reports retained, and storage sizes.

2. **Given** cleanup operations have run, **When** viewing Report Storage tab, **Then** the purged counts (jobs and results) reflect cumulative totals across all cleanup runs.

3. **Given** NO_CHANGE results have been created and some purged, **When** viewing Report Storage tab, **Then** the purged counts distinguish between original results and copy results.

4. **Given** the preserve_per_collection setting is configured, **When** viewing Report Storage tab, **Then** the preserved results count reflects the real-time count of protected results.

---

### Edge Cases

- What happens when a referenced result is deleted by retention cleanup? The system returns a 404 with an appropriate message when attempting to download the report.
- How does the system handle results created before this optimization? Pre-migration results have null `input_state_hash` and are treated as regular results (backward compatible).
- What happens during concurrent job creation and cleanup? Cleanup is idempotent and safe for concurrent execution, using batch processing.
- How does the system handle very large collections (100K+ files)? File list hash computation completes within acceptable time, with potential caching of collection file list hash.
- What happens if an agent doesn't support Input State (older agent version)? Jobs complete normally without optimization; results have null Input State.

## Requirements *(mandatory)*

### Functional Requirements

#### Retention Policy Configuration

- **FR-001**: System MUST store retention settings as team-level Configuration entries in category `result_retention`.
- **FR-002**: System MUST support `job_completed_days` setting with options: 1, 2, 5, 7, 14, 30, 90, 180, 365, or 0 (unlimited), defaulting to 2.
- **FR-003**: System MUST support `job_failed_days` setting (independent from completed jobs), defaulting to 7.
- **FR-004**: System MUST support `result_completed_days` setting (independent from job retention), defaulting to 0 (unlimited).
- **FR-005**: System MUST support `preserve_per_collection` minimum count, defaulting to 1.
- **FR-006**: System MUST display retention settings in Settings > Config Tab > Storage section.
- **FR-007**: System MUST seed default retention settings when a new team is created.

#### Input State Tracking

- **FR-008**: System MUST compute and store an Input State hash (SHA-256) for each analysis result.
- **FR-009**: System MUST store Input State components that vary by tool type:
  - PhotoStats/Photo Pairing: collection_guid, file_list_hash, configuration_hash
  - Pipeline Validation: collection_guid, pipeline_guid, pipeline_version, file_list_hash, configuration_hash
  - Display-Graph mode: pipeline_guid, pipeline_version only
- **FR-010**: System MUST compute file_list_hash as SHA-256 of sorted file paths within the collection.
- **FR-011**: System MUST compute configuration_hash as SHA-256 of tool-relevant configuration values.
- **FR-012**: System MUST optionally store full Input State JSON when DEBUG mode is enabled.
- **FR-013**: System MUST treat null Input State (pre-migration results) as backward compatible regular results.

#### Pre-Job State Retrieval

- **FR-014**: System MUST include `previous_result` object in job claim response when a prior successful result exists.
- **FR-015**: System MUST return the most recent COMPLETED result for the same (collection, tool) combination, including pipeline_guid and pipeline_version for Pipeline Validation.
- **FR-016**: System MUST return null `previous_result` if no prior successful result exists.

#### No-Change Detection and Handling

- **FR-017**: Agent MUST compare current Input State hash with previous result's hash before tool execution.
- **FR-018**: Agent MUST complete job with status "NO_CHANGE" when Input State hashes match.
- **FR-019**: NO_CHANGE completion MUST include the referenced previous result's GUID.
- **FR-020**: System MUST create an AnalysisResult with `no_change_copy=true` for NO_CHANGE completions.
- **FR-021**: System MUST set `download_report_from` to reference the source result's GUID (or the source's `download_report_from` if it exists).
- **FR-022**: System MUST NOT store HTML report for NO_CHANGE results (only reference).
- **FR-023**: System MUST copy results_json and metrics (files_scanned, issues_found) from the referenced result.
- **FR-024**: System MUST delete the previously referenced result IF it has `no_change_copy=true` (cleanup of intermediate copies).

#### Report Retrieval

- **FR-025**: System MUST check `download_report_from` field before serving a report.
- **FR-026**: System MUST fetch report from the referenced result if `download_report_from` is set.
- **FR-027**: System MUST return 404 with appropriate message if the referenced result has been deleted.
- **FR-028**: System MUST NOT follow transitive references (maximum 1 level of reference following).

#### Automatic Cleanup

- **FR-029**: System MUST trigger cleanup during job creation (before creating new job).
- **FR-030**: System MUST delete completed jobs older than team's `job_completed_days` setting without cascading to results.
- **FR-031**: System MUST delete completed results older than team's `result_completed_days` setting.
- **FR-032**: System MUST delete failed jobs older than team's `job_failed_days` setting with cascade to associated results.
- **FR-033**: System MUST preserve minimum results per (collection, tool) as specified by `preserve_per_collection`, regardless of age or status.
- **FR-034**: System MUST skip cleanup if retention is unlimited (0 days).
- **FR-035**: System MUST process deletions in batches to limit transaction size.
- **FR-036**: Cleanup failures MUST NOT block job creation.

#### API and UI Updates

- **FR-037**: Results list API MUST return `input_state_hash` and `no_change_copy` fields.
- **FR-038**: Results list MUST support filtering by `no_change_copy` to show/hide duplicate results.
- **FR-039**: Result detail view MUST show Input State transition indicator.
- **FR-040**: Trend charts MUST visually distinguish Input State transition points using different symbols (not colors).

#### Storage Metrics Tracking

- **FR-041**: System MUST persist cumulative storage metrics in a team-scoped StorageMetrics table.
- **FR-042**: System MUST increment metrics during cleanup operations:
  - `completed_jobs_purged`: Count of completed job records deleted
  - `failed_jobs_purged`: Count of failed job records deleted
  - `completed_results_purged_original`: Count of completed result records deleted (no_change_copy=false)
  - `completed_results_purged_copy`: Count of completed result records deleted (no_change_copy=true)
  - `estimated_bytes_purged`: Estimated bytes removed from DB (JSON + HTML sizes)
- **FR-043**: System MUST increment `total_reports_generated` on each job completion (COMPLETED, NO_CHANGE, or FAILED).
- **FR-044**: System MUST provide storage stats API endpoint returning all cumulative metrics plus current counts.
- **FR-045**: System MUST display "Report Storage" tab in Analytics page (after "Runs" tab) with KPI cards showing:
  - Total reports generated (cumulative, including purged)
  - Reports retained (current count, matches header KPI)
  - Total size of retained reports (JSON bytes, HTML bytes separately)
  - Completed jobs purged (cumulative)
  - Failed jobs purged (cumulative)
  - Completed results purged (cumulative, split by no_change_copy flag)
  - Preserved results count (real-time, based on preserve_per_collection setting)
- **FR-046**: System MUST compute `preserved_results_count` as a real-time query based on preserve_per_collection setting.

### Key Entities

- **AnalysisResult (Enhanced)**: Existing entity enhanced with:
  - `input_state_hash`: SHA-256 hash identifying reproducibility parameters
  - `input_state_json`: Full Input State for debugging (optional, DEBUG mode only)
  - `no_change_copy`: Boolean indicating this result references another
  - `download_report_from`: GUID of the source result containing the HTML report

- **Configuration (result_retention category)**: Team-level settings controlling data lifecycle:
  - `job_completed_days`: Days to retain completed jobs
  - `job_failed_days`: Days to retain failed jobs (with cascade to results)
  - `result_completed_days`: Days to retain successful results
  - `preserve_per_collection`: Minimum results to keep per (collection, tool)

- **ResultStatus (Enhanced)**: Enum extended with NO_CHANGE status for optimized results

- **Input State Components**: Logical entity (computed, not stored separately) containing:
  - collection_guid, file_list_hash, configuration_hash (tool-specific)
  - pipeline_guid, pipeline_version (for Pipeline Validation and Display-Graph)

- **StorageMetrics (New)**: Team-level cumulative storage statistics:
  - `total_reports_generated`: Cumulative count of all job completions (including purged)
  - `reports_retained_json_bytes`: Current total JSON size of retained results
  - `reports_retained_html_bytes`: Current total HTML size of retained results
  - `completed_jobs_purged`: Cumulative count of completed jobs deleted
  - `failed_jobs_purged`: Cumulative count of failed jobs deleted
  - `completed_results_purged_original`: Cumulative count of original results purged (no_change_copy=false)
  - `completed_results_purged_copy`: Cumulative count of copy results purged (no_change_copy=true)
  - `estimated_bytes_purged`: Cumulative estimated bytes freed from DB

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Stable collections (unchanged between runs) achieve 80%+ storage reduction compared to storing full results.
- **SC-002**: "No Change" detection and completion adds less than 50ms overhead to job processing.
- **SC-003**: File list hash computation completes in under 1 second for collections with up to 10,000 files.
- **SC-004**: NO_CHANGE results use less than 1KB storage compared to 50-500KB for full results.
- **SC-005**: Administrators can configure retention policy in under 2 minutes.
- **SC-006**: Users can download reports for any result (including NO_CHANGE results) without errors when the source exists.
- **SC-007**: Trend visualization correctly displays stable periods and transition points.
- **SC-008**: System preserves at least one result per (collection, tool) regardless of retention settings.

## Assumptions

- Teams will configure retention settings appropriate to their storage and compliance needs.
- SHA-256 provides sufficient collision resistance for Input State hashing (collision probability negligible).
- File list hash computation scales linearly with file count (acceptable for typical collections).
- Existing results without Input State (pre-migration) will function normally without optimization benefits.
- Agents will be updated to support Input State computation to receive optimization benefits.
- Cleanup running during job creation provides sufficient frequency without requiring background jobs.
