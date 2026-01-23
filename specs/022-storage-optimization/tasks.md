# Tasks: Storage Optimization for Analysis Results

**Input**: Design documents from `/specs/022-storage-optimization/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Database Schema Changes)

**Purpose**: Database migration and model changes that enable all user stories

- [X] T001 Add NO_CHANGE to ResultStatus enum in backend/src/models/__init__.py
- [X] T001b Add StorageMetrics model in backend/src/models/storage_metrics.py (team_id FK, cumulative counters for reports generated, purged counts, bytes)
- [X] T002 Add storage optimization fields to AnalysisResult model in backend/src/models/analysis_result.py (input_state_hash, input_state_json, no_change_copy, download_report_from)
- [X] T003 Create Alembic migration for analysis_results table changes in backend/alembic/versions/
- [X] T003b Create Alembic migration for storage_metrics table in backend/alembic/versions/
- [X] T004 [P] Create retention Pydantic schemas in backend/src/schemas/retention.py (RetentionSettingsResponse, RetentionSettingsUpdate)
- [X] T005 [P] Create frontend retention API types in frontend/src/contracts/api/retention-api.ts
- [X] T006 Run migration and verify schema changes apply correctly

---

## Phase 2: Foundational (Shared Services)

**Purpose**: Core services that multiple user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Create RetentionService in backend/src/services/retention_service.py (get_settings, update_settings with defaults)
- [X] T008 [P] Add retention API routes in backend/src/api/config.py (GET/PUT /api/config/retention)
- [X] T009 Seed default retention settings for existing teams in migration or service initialization
- [X] T009b Update team creation to seed default retention settings in backend/src/services/team_service.py (or admin_service.py)
- [X] T010 Update AnalysisResultSummary schema in backend/src/schemas/results.py (add input_state_hash, no_change_copy fields)
- [X] T011 Update AnalysisResultResponse schema in backend/src/schemas/results.py (add download_report_from, source_result_exists)
- [X] T011b [P] Create unit tests for RetentionService in backend/tests/unit/test_retention_service.py

**Checkpoint**: Foundation ready - user story implementation can now begin ✅

---

## Phase 3: User Story 1 - Configure Retention Policy (Priority: P1) 🎯 MVP

**Goal**: Team administrators can configure retention periods for jobs and results via Settings UI

**Independent Test**: Access Settings > Config Tab > Storage section, set retention values, verify values persist after page reload

### Implementation for User Story 1

- [X] T012 [US1] Create useRetention hook in frontend/src/hooks/useRetention.ts (fetch and update retention settings)
- [X] T013 [US1] Create ResultRetentionSection component in frontend/src/components/settings/ResultRetentionSection.tsx
- [X] T014 [US1] Add ResultRetentionSection to ConfigTab in frontend/src/components/settings/ConfigTab.tsx
- [X] T015 [US1] Add validation for retention values (allowed options only) in backend/src/services/retention_service.py
- [X] T016 [US1] Add structured logging for retention configuration changes

**Checkpoint**: User Story 1 complete - administrators can configure retention policy ✅

---

## Phase 4: User Story 2 - Skip Execution When Input Unchanged (Priority: P1)

**Goal**: Agent skips tool execution when collection hasn't changed since last successful run

**Independent Test**: Run same analysis tool twice on unchanged collection; second run completes instantly with "No Change" status

### Backend Implementation for User Story 2

- [X] T017 [US2] Create InputStateService in backend/src/services/input_state_service.py (compute_input_state_hash, compute_configuration_hash)
- [X] T018 [US2] Add PreviousResultInfo schema in backend/src/api/agent/schemas.py (PreviousResultData)
- [X] T019 [US2] Update JobClaimResponse schema to include previous_result in backend/src/api/agent/schemas.py
- [X] T020 [US2] Implement get_previous_result lookup in backend/src/services/job_coordinator_service.py (_find_previous_result method)
- [X] T021 [US2] Update job claim endpoint to include previous_result in backend/src/api/agent/routes.py
- [X] T022 [US2] Add NO_CHANGE completion handling in backend/src/services/job_coordinator_service.py (complete_job_no_change method):
  - Create AnalysisResult with status=NO_CHANGE and no_change_copy=true
  - Set download_report_from to source result's GUID (or source's download_report_from if it exists)
  - Copy results_json from referenced result
  - Copy files_scanned and issues_found from referenced result
  - Store input_state_hash from agent completion request
  - Store input_state_json if DEBUG mode is enabled (check settings.DEBUG or env var)
  - Ensure report_html is NOT stored (must be None/null)
  - Set started_at, completed_at, duration_seconds from job timestamps

### Agent Implementation for User Story 2

- [X] T024 [US2] Create input_state module in agent/src/input_state.py (compute_file_list_hash, compute_configuration_hash, compute_input_state_hash)
- [X] T025 [US2] Update job executor to check previous_result hash before execution in agent/src/job_executor.py
- [X] T026 [US2] Implement NO_CHANGE completion in agent/src/job_executor.py (submit NO_CHANGE status with previous_result_guid)
- [X] T027 [US2] Add structured logging for no-change detection decisions

### Tests for User Story 2

- [X] T027b [P] [US2] Create unit tests for InputStateService in backend/tests/unit/test_input_state_service.py (hash determinism, configuration hash)
- [X] T027c [P] [US2] Create unit tests for agent input_state module in agent/tests/unit/test_input_state.py (file list hash, configuration hash)
- [X] T027d [US2] Create integration test for NO_CHANGE flow in backend/tests/integration/test_no_change_flow.py (job claim with previous_result, NO_CHANGE completion, result creation)

**Checkpoint**: User Story 2 complete - unchanged collections skip full analysis ✅

---

## Phase 5: User Story 3 - Download Reports from Optimized Results (Priority: P1)

**Goal**: Users can download HTML reports for any result including NO_CHANGE results

**Independent Test**: Create NO_CHANGE result, download its report; report serves correctly from referenced source

### Implementation for User Story 3

- [X] T028 [US3] Update get_report method in backend/src/services/result_service.py to follow download_report_from reference
- [X] T029 [US3] Update report download endpoint in backend/src/api/results.py to handle reference following
- [X] T030 [US3] Return appropriate 404 error when source result has been deleted
- [X] T031 [US3] Update has_report computation for NO_CHANGE results (true if source exists and has report)
- [X] T032 [US3] Add source_result_exists field to result detail response
- [X] T032b [US3] Add Input State transition indicator to result detail view in frontend/src/components/results/ResultDetailPanel.tsx (show badge/icon when no_change_copy=true with link to source)

**Checkpoint**: User Story 3 complete - reports downloadable for all result types ✅

---

## Phase 6: User Story 4 - Automatic Cleanup of Old Data (Priority: P2)

**Goal**: System automatically cleans up old jobs and results according to retention policy

**Independent Test**: Set short retention period, create jobs, advance time or use test utilities, verify old items are deleted

### Implementation for User Story 4

- [X] T033 [US4] Create CleanupService in backend/src/services/cleanup_service.py with batch deletion methods
- [X] T034 [US4] Implement cleanup_old_jobs method (delete completed jobs older than retention, exclude results)
- [X] T035 [US4] Implement cleanup_old_results method (delete completed results older than retention)
- [X] T036 [US4] Implement cleanup_failed_jobs method (delete failed jobs with cascade to results)
- [X] T037 [US4] Implement preserve_per_collection logic (keep minimum results per collection+tool)
- [X] T038 [US4] Integrate cleanup trigger into job creation flow in backend/src/services/tool_service.py
- [X] T039 [US4] Add structured logging for cleanup operations (items deleted, items preserved, errors)
- [X] T039b [US4] Update CleanupService to return cleanup stats (records deleted by type, bytes freed estimates)
- [X] T039c [US4] Update CleanupService to persist cleanup stats to StorageMetrics table after each cleanup run
- [X] T039d [US4] Compute bytes freed estimate from deleted records (sum of JSONB column sizes + HTML sizes)
- [X] T040 [US4] Ensure cleanup failures don't block job creation (catch and log)

### Tests for User Story 4

- [X] T040b [P] [US4] Create unit tests for CleanupService in backend/tests/unit/test_cleanup_service.py (retention logic, preserve_per_collection, batch deletion)
- [X] T040c [US4] Create integration test for retention cleanup in backend/tests/integration/test_cleanup_integration.py (end-to-end cleanup trigger)

**Checkpoint**: User Story 4 complete - old data is automatically cleaned up ✅

---

## Phase 7: User Story 5 - Clean Up Redundant No-Change Copies (Priority: P2)

**Goal**: System removes intermediate NO_CHANGE copies when new copy references same source

**Independent Test**: Run three consecutive unchanged analyses; after third run, only original and latest copy exist (middle copy deleted)

### Implementation for User Story 5

- [X] T041 [US5] Implement cleanup_intermediate_copies in backend/src/services/job_coordinator_service.py
- [X] T042 [US5] Integrate intermediate cleanup into NO_CHANGE completion flow
- [X] T043 [US5] Preserve copies when new COMPLETED result is created (don't delete for trend visibility)
- [X] T044 [US5] Add logging for intermediate copy cleanup operations
- [X] T044b [US5] Update intermediate copy cleanup to increment completed_results_purged_copy in StorageMetrics

**Checkpoint**: User Story 5 complete - redundant copies are automatically removed ✅

---

## Phase 8: User Story 6 - View Input State Transitions in Trends (Priority: P3)

**Goal**: Trend visualization distinguishes between genuine changes and stable periods

**Independent Test**: Create series of results with Input State changes and NO_CHANGE results, verify trend chart shows transition points with different symbols

### Implementation for User Story 6

- [X] T045 [US6] Update trend data response to include no_change_copy flag in backend/src/schemas/trends.py
- [X] T046 [US6] Update frontend trend chart to render different symbols for transition points in frontend/src/components/trends/
- [X] T047 [US6] Add stable period indicator for consecutive NO_CHANGE results
- [X] T048 [US6] Update trend summary to account for NO_CHANGE results

**Checkpoint**: User Story 6 complete - trends visually distinguish state transitions ✅

---

## Phase 9: User Story 7 - View Storage Metrics (Priority: P3)

**Goal**: Users can view storage metrics and deduplication effectiveness in Analytics

**Independent Test**: Navigate to Analytics > Report Storage tab, verify KPI cards show cumulative metrics that increment after cleanup runs

### Implementation for User Story 7

- [X] T056 [US7] Create StorageMetricsService in backend/src/services/storage_metrics_service.py (get_metrics, increment_on_cleanup, increment_on_completion)
- [X] T057 [US7] Increment total_reports_generated on job completion in backend/src/services/job_coordinator_service.py
- [X] T058 [US7] Create storage stats API endpoint GET /api/analytics/storage in backend/src/api/analytics.py
- [X] T059 [US7] Implement preserved_results_count real-time query (count of most recent N per collection+tool based on preserve_per_collection)
- [X] T060 [US7] Implement reports_retained_json_bytes and reports_retained_html_bytes real-time queries
- [X] T061 [US7] Create ReportStorageTab component in frontend/src/components/analytics/ReportStorageTab.tsx
- [X] T062 [US7] Add "Report Storage" tab to Analytics page after "Runs" tab in frontend/src/pages/AnalyticsPage.tsx
- [X] T063 [US7] Create KPI cards for all storage metrics (total generated, retained counts, retained bytes, purged counts, preserved count)
- [X] T064 [P] [US7] Create unit tests for StorageMetricsService in backend/tests/unit/test_storage_metrics_service.py

**Checkpoint**: User Story 7 complete - storage metrics visible in Analytics ✅

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T049 [P] Update Results list API to support no_change_copy filter parameter in backend/src/api/results.py
- [X] T050 [P] Add NO_CHANGE status badge styling in frontend/src/components/results/
- [X] T051 [P] Update result list UI to show NO_CHANGE indicator (Copy icon with tooltip)
- [X] T052 Performance validation: verify <50ms overhead for no-change detection
- [X] T053 Performance validation: verify <1s file list hash for 10K files
- [X] T054 Verify backward compatibility with null input_state_hash (legacy results)
- [X] T055 Run quickstart.md validation scenarios (automated tests created in test_storage_optimization_performance.py)

**Checkpoint**: Phase 10 complete - storage optimization polish applied ✅

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-9)**: All depend on Foundational phase completion
  - US1 (P1): Can start after Foundational
  - US2 (P1): Can start after Foundational - Agent changes can parallel backend
  - US3 (P1): Depends on US2 completion (needs NO_CHANGE results to test)
  - US4 (P2): Can start after Foundational - independent of US2/US3
  - US5 (P2): Depends on US2 completion (needs intermediate copy creation)
  - US6 (P3): Can start after Foundational - independent but benefits from US2 data
  - US7 (P3): Depends on US4 and US5 completion (needs cleanup metrics to display)
- **Polish (Phase 10)**: Depends on all P1 stories being complete

### User Story Dependencies

```
Phase 1: Setup
    │
    ▼
Phase 2: Foundational
    │
    ├──────────────────────────────────────────────┐
    │                                              │
    ▼                                              ▼
Phase 3: US1 (Retention Config)     Phase 4: US2 (Skip Execution)
    │                                              │
    │                               ┌──────────────┤
    │                               │              │
    │                               ▼              ▼
    │                    Phase 5: US3 (Reports)  Phase 7: US5 (Copy Cleanup)
    │                               │                         │
    │                               │                         │
    ▼                               │                         │
Phase 6: US4 (Auto Cleanup)         │                         │
    │                               │                         │
    └──────────────┬────────────────┴─────────────────────────┘
                   │
                   ▼
           Phase 8: US6 (Trends)
                   │
                   ▼
           Phase 9: US7 (Storage Metrics)
                   │
                   ▼
           Phase 10: Polish
```

### Parallel Opportunities

**Within Phase 1 (Setup)**:
- T004 and T005 can run in parallel (backend and frontend schemas)

**Within Phase 2 (Foundational)**:
- T007 and T010-T011 can run in parallel after T007

**Within Phase 4 (US2)**:
- T017-T021 (backend) can run in parallel with T024-T027 (agent) after T017 is complete

**Cross-Phase Parallelism**:
- US1, US4, and US6 can run in parallel after Foundational
- US2 backend and agent work can be parallelized

---

## Parallel Example: User Story 2

```bash
# Launch backend and agent work in parallel after T017:

# Backend track:
Task: "Add PreviousResultInfo schema in backend/src/schemas/jobs.py"
Task: "Update JobClaimResponse schema in backend/src/schemas/jobs.py"
Task: "Implement get_previous_result lookup in backend/src/services/job_service.py"

# Agent track (parallel):
Task: "Create input_state module in agent/src/input_state.py"
Task: "Update job executor to check previous_result hash in agent/src/job_executor.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1-3)

1. Complete Phase 1: Setup (migrations, schemas)
2. Complete Phase 2: Foundational (retention service, API updates)
3. Complete Phase 3: User Story 1 (retention UI)
4. Complete Phase 4: User Story 2 (skip execution)
5. Complete Phase 5: User Story 3 (report download)
6. **STOP and VALIDATE**: Test all P1 stories independently
7. Deploy/demo if ready - core optimization is functional

### Incremental Delivery

1. **MVP**: US1-3 → Core storage optimization working
2. **Enhancement 1**: US4 → Automatic cleanup operational
3. **Enhancement 2**: US5 → Intermediate copy cleanup
4. **Enhancement 3**: US6 → Improved trend visualization
5. **Enhancement 4**: US7 → Storage metrics dashboard
6. **Final**: Polish → Performance validation, UI polish

### Suggested MVP Scope

**User Stories 1-3 (all P1)** deliver the core value:
- Administrators can configure retention policy
- Collections skip re-analysis when unchanged (80% storage savings)
- Reports downloadable for all result types

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Backend and agent changes for US2 can be developed in parallel
