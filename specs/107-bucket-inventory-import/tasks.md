# Tasks: Cloud Storage Bucket Inventory Import

**Input**: Design documents from `/specs/107-bucket-inventory-import/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Database schema, base models, and project structure

### Implementation

- [x] T001 Create `backend/src/models/inventory_folder.py` with InventoryFolder model (GuidMixin, fld_ prefix)
- [x] T002 [P] Add inventory fields to `backend/src/models/connector.py` (inventory_config JSONB, validation_status, schedule)
- [x] T003 [P] Add FileInfo fields to `backend/src/models/collection.py` (file_info JSONB, file_info_updated_at, file_info_source, file_info_delta)
- [x] T004 Create database migration for inventory tables and column extensions
- [x] T005 [P] Create `backend/src/schemas/inventory.py` (S3InventoryConfig, GCSInventoryConfig, FileInfo, InventoryFolder schemas)
- [x] T006 [P] Extend `backend/src/schemas/collection.py` with FileInfo and delta summary response fields
- [x] T007 [P] Create `frontend/src/contracts/api/inventory-api.ts` TypeScript types (copy from contracts/inventory-types.ts)

### Tests for Phase 1

- [x] T008 [P] Unit tests for InventoryFolder model in `backend/tests/unit/models/test_inventory_folder.py`
- [x] T008a [P] Unit tests for Connector model inventory extensions in `backend/tests/unit/models/test_connector_inventory.py`
- [x] T008b [P] Unit tests for Collection model FileInfo extensions in `backend/tests/unit/models/test_collection_fileinfo.py`
- [x] T008c [P] Unit tests for Pydantic schemas (S3InventoryConfig, GCSInventoryConfig, FileInfo validation) in `backend/tests/unit/schemas/test_inventory_schemas.py`

**Checkpoint**: Database schema ready, models and types available for all user stories

---

## Phase 2: User Story 1 - Configure Inventory Source (Priority: P1) 🎯 MVP

**Goal**: Allow administrators to configure inventory source location on S3/GCS connectors with validation for both server-stored and agent-side credentials

**Independent Test**: Configure an S3 connector with inventory settings, trigger validation, verify manifest.json accessibility check completes

### Backend Implementation

- [x] T009 [US1] Create `backend/src/services/inventory_service.py` with config validation methods (server-side credential path)
- [x] T010 [US1] Add `create_validation_job()` method to InventoryService for agent-side credential path
- [x] T011 [US1] Extend `backend/src/services/connector_service.py` with inventory config CRUD operations
- [x] T012 [US1] Create `backend/src/api/inventory/routes.py` with PUT/DELETE config endpoints
- [x] T013 [US1] Add GET status endpoint to inventory routes (validation_status, last_import_at, folder counts)
- [x] T014 [US1] Add agent endpoint `POST /api/agent/v1/jobs/{guid}/inventory/validate` for validation results

### Frontend Implementation

- [x] T017 [P] [US1] Create `frontend/src/services/inventory.ts` API client (config CRUD, status polling)
- [x] T018 [P] [US1] Create `frontend/src/hooks/useInventory.ts` React hooks (useInventoryConfig, useInventoryStatus)
- [x] T019 [US1] Create `frontend/src/components/inventory/InventoryConfigForm.tsx` (provider-specific fields, schedule selection)
- [x] T020 [US1] Add inventory configuration section to connector detail page
- [x] T021 [US1] Implement validation status display (pending, validating, validated, failed states)
- [x] T022 [US1] Add error message display for validation failures with guidance

### Tests for US1

- [x] T015 [P] [US1] Unit tests for server-side credential validation path in `backend/tests/unit/services/test_inventory_service.py`
- [x] T015a [P] [US1] Unit tests for agent-side credential validation job creation in `backend/tests/unit/services/test_inventory_service.py`
- [x] T016 [US1] Integration tests for config endpoints in `backend/tests/integration/api/test_inventory_api.py`
- [x] T016a [US1] Integration test for agent-side credential validation flow (job creation → agent report → status update) in `backend/tests/integration/api/test_inventory_validation_flow.py`
- [x] T016b [US1] Integration test for SMB connector inventory exclusion (verify 404/hidden) in `backend/tests/integration/api/test_inventory_api.py`
- [x] T023 [US1] Component tests for InventoryConfigForm in `frontend/tests/components/inventory/InventoryConfigForm.test.tsx`

**Checkpoint**: Users can configure inventory sources on S3/GCS connectors with proper validation feedback

---

## Phase 3: User Story 2 - Import Inventory and Extract Folders (Priority: P1) 🎯 MVP

**Goal**: Agent-executed pipeline that fetches inventory data, parses manifests, and extracts unique folder paths

**Independent Test**: Trigger import on configured connector, verify job queued, agent claims and executes, folders stored on connector

### Agent Tool Implementation

- [ ] T024 [US2] Create `agent/src/analysis/inventory_parser.py` with S3 manifest parser (manifest.json → files array)
- [ ] T025 [P] [US2] Add GCS manifest parser to inventory_parser.py (manifest.json → report_shards_file_names)
- [ ] T026 [US2] Implement CSV parser with streaming/chunked processing in inventory_parser.py
- [ ] T026a [P] [US2] Implement Parquet parser with streaming/chunked processing in inventory_parser.py (handle GCS manifest.json → report_shards_file_names, parse Parquet files into same record stream as CSV parser)
- [ ] T027 [US2] Implement folder extraction algorithm (single-pass with set deduplication)
- [ ] T028 [US2] Create `agent/src/tools/inventory_import_tool.py` with InventoryImportTool class
- [ ] T028a [US2] Update InventoryImportTool to detect Parquet format from manifest and route to Parquet parser (reference T026, T026a for parser implementations)
- [ ] T029 [US2] Implement Phase A (Folder Extraction) in inventory_import_tool.py
- [ ] T030 [US2] Register inventory_import tool in `agent/src/capabilities.py`
- [ ] T031 [US2] Add dispatch case in `agent/src/job_executor.py` for inventory_import
- [ ] T032 [US2] Add progress reporting integration to inventory_import_tool.py

### Backend API for Agent Results

- [ ] T035 [US2] Add POST endpoint `/api/agent/v1/jobs/{guid}/inventory/folders` to report discovered folders
- [ ] T036 [US2] Implement folder storage in InventoryService (upsert InventoryFolder records)
- [ ] T037 [US2] Add GET endpoint `/api/connectors/{guid}/inventory/folders` (list with path_prefix filter)

### Backend Job Trigger

- [ ] T038 [US2] Create POST endpoint `/api/connectors/{guid}/inventory/import` to trigger import job
- [ ] T039 [US2] Add concurrent import prevention (409 if job already running for connector)
- [ ] T040 [US2] Extend JobCoordinatorService for inventory job handling

### Frontend Import UI

- [ ] T041 [P] [US2] Add "Import Inventory" button to connector inventory section (disabled if not validated)
- [ ] T042 [US2] Implement job status polling and progress display during import
- [ ] T043 [US2] Display folder count after import completes

### Tests for US2

- [ ] T033 [P] [US2] Unit tests for S3 manifest parser in `agent/tests/unit/test_inventory_parser.py`
- [ ] T033a [P] [US2] Unit tests for GCS manifest parser (report_shards_file_names array) in `agent/tests/unit/test_inventory_parser.py`
- [ ] T033b [P] [US2] Unit tests for folder extraction algorithm (edge cases: deep nesting, URL-encoded paths, trailing slashes) in `agent/tests/unit/test_inventory_parser.py`
- [ ] T033c [P] [US2] Unit tests for streaming CSV parser (chunked processing, memory efficiency) in `agent/tests/unit/test_inventory_parser.py`
- [ ] T033d [P] [US2] Unit tests for streaming Parquet parser (chunked processing, memory efficiency, same record stream output as CSV) in `agent/tests/unit/test_inventory_parser.py`
- [ ] T033e [P] [US2] Unit tests for InventoryImportTool Parquet format detection and routing in `agent/tests/unit/test_inventory_import_tool.py`
- [ ] T034 [US2] Integration tests for InventoryImportTool in `agent/tests/integration/test_inventory_import_tool.py`
- [ ] T034a [US2] Integration tests for InventoryImportTool with Parquet manifests in `agent/tests/integration/test_inventory_import_tool.py`
- [ ] T040a [US2] Integration test for folder storage endpoint (upsert behavior, duplicate handling) in `backend/tests/integration/api/test_inventory_api.py`
- [ ] T040b [US2] Integration test for concurrent import prevention (409 response) in `backend/tests/integration/api/test_inventory_api.py`

**Checkpoint**: Users can trigger inventory imports, agents process data, folders are discovered and stored

---

## Phase 4: User Story 3 - Map Folders to Collections (Priority: P1) 🎯 MVP

**Goal**: Two-step wizard UI for selecting folders (with hierarchy constraints) and creating Collections with mandatory state assignment

**Independent Test**: View folder tree, select multiple non-overlapping folders, proceed to review, adjust names/states, create Collections

### Frontend Folder Tree Components

- [ ] T044 [US3] Create `frontend/src/components/inventory/FolderTreeNode.tsx` (expand/collapse, selection, mapping indicator)
- [ ] T045 [US3] Create `frontend/src/components/inventory/FolderTree.tsx` with virtualization (tanstack-virtual)
- [ ] T046 [US3] Implement hierarchical selection constraint logic (disable ancestors/descendants when selected)
- [ ] T047 [US3] Add visual indicators for mapped folders (linked icon, disabled state)
- [ ] T048 [US3] Implement folder search/filter functionality

### Frontend Create Collections Wizard

- [ ] T050 [US3] Create `frontend/src/components/inventory/CreateCollectionsDialog.tsx` (two-step wizard container)
- [ ] T051 [US3] Implement Step 1: Folder Selection UI (tree + continue button)
- [ ] T052 [US3] Implement Step 2: Review & Configure UI (draft list, name/state editors)
- [ ] T053 [US3] Implement name suggestion algorithm (path transformation, URL decode, title case)
- [ ] T054 [US3] Add batch "Set all states" action in review step
- [ ] T055 [US3] Add "Back to Selection" navigation with state preservation

### Backend Collection Creation

- [ ] T057 [US3] Create POST endpoint `/api/collections/from-inventory` for batch collection creation
- [ ] T058 [US3] Implement FolderToCollectionMapping validation (no overlapping paths, valid states)
- [ ] T059 [US3] Link created Collections to Connector with folder path as location
- [ ] T060 [US3] Update InventoryFolder.collection_guid when mapped
- [ ] T061 [US3] Add unmapped_only filter to GET folders endpoint

### Tests for US3

- [ ] T046a [P] [US3] Unit tests for hierarchical selection constraint logic in `frontend/tests/utils/test_folder_selection.ts`
- [ ] T049 [US3] Component tests for FolderTree in `frontend/tests/components/inventory/FolderTree.test.tsx`
- [ ] T053a [P] [US3] Unit tests for name suggestion algorithm (URL decode, title case, path transformation) in `frontend/tests/utils/test_name_suggestion.ts`
- [ ] T056 [US3] Component tests for wizard in `frontend/tests/components/inventory/CreateCollectionsDialog.test.tsx`
- [ ] T056a [US3] Component test for wizard state preservation (back navigation) in `frontend/tests/components/inventory/CreateCollectionsDialog.test.tsx`
- [ ] T058a [P] [US3] Unit tests for overlapping path validation in `backend/tests/unit/services/test_inventory_service.py`
- [ ] T058b [P] [US3] Unit tests for state validation (required, valid enum values) in `backend/tests/unit/services/test_inventory_service.py`
- [ ] T062 [US3] Integration tests for collection creation endpoint in `backend/tests/integration/api/test_inventory_api.py`
- [ ] T062a [US3] Integration test for batch collection creation (multiple folders, mixed states) in `backend/tests/integration/api/test_inventory_api.py`
- [ ] T062b [US3] Integration test for InventoryFolder.collection_guid update after mapping in `backend/tests/integration/api/test_inventory_api.py`

**Checkpoint**: Users can browse folders, select non-overlapping paths, configure draft Collections, and batch-create with states

---

## Phase 5: User Story 4 - Automatic FileInfo Population (Priority: P1) 🎯 MVP

**Goal**: Agent populates FileInfo on Collections from inventory data during import pipeline Phase B

**Independent Test**: Create Collection from inventory folder, trigger import, verify FileInfo populated without cloud API calls

### Agent Phase B Implementation

- [ ] T063 [US4] Implement Phase B (FileInfo Population) in `agent/src/tools/inventory_import_tool.py`
- [ ] T064 [US4] Add Collection query from server (GET collections for connector)
- [ ] T065 [US4] Implement inventory filtering by Collection folder path prefix
- [ ] T066 [US4] Extract FileInfo (key, size, last_modified, etag, storage_class) per Collection

### Backend FileInfo Storage

- [ ] T068 [US4] Add POST endpoint `/api/agent/v1/jobs/{guid}/inventory/file-info` for FileInfo results
- [ ] T069 [US4] Implement FileInfo storage on Collection (file_info JSONB, file_info_updated_at, file_info_source)
- [ ] T070 [US4] Add GET endpoint for Collection FileInfo status (last updated, source)

### Tool Integration

- [ ] T071 [US4] Update analysis tools to check Collection.file_info before calling cloud list APIs
- [ ] T072 [US4] Add "Refresh from Cloud" action that creates separate job for live file fetch

### Frontend FileInfo Display

- [ ] T074 [P] [US4] Display "Last updated from inventory" timestamp on Collection view
- [ ] T075 [US4] Add "Refresh from Cloud" button to Collection detail page

### Tests for US4

- [ ] T065a [P] [US4] Unit tests for inventory filtering by Collection folder path prefix in `agent/tests/unit/test_inventory_import_tool.py`
- [ ] T066a [P] [US4] Unit tests for FileInfo extraction (field mapping, missing optional fields) in `agent/tests/unit/test_inventory_import_tool.py`
- [ ] T067 [US4] Unit tests for Phase B pipeline in `agent/tests/unit/test_inventory_import_tool.py`
- [ ] T069a [US4] Unit tests for FileInfo storage service (source tracking, timestamp update) in `backend/tests/unit/services/test_inventory_service.py`
- [ ] T071a [US4] Integration test for analysis tool FileInfo check behavior in `backend/tests/integration/tools/test_fileinfo_integration.py`
- [ ] T073 [US4] Integration tests for FileInfo population endpoint in `backend/tests/integration/api/test_inventory_api.py`
- [ ] T073a [US4] Integration test for Phase B skip when no Collections exist in `backend/tests/integration/api/test_inventory_api.py`

**Checkpoint**: Collections receive FileInfo from inventory, analysis tools skip cloud API calls when cached data available

---

## Phase 6: User Story 5 - Scheduled Inventory Import (Priority: P2)

**Goal**: Automatic periodic imports via chain scheduling (next job created on completion)

**Independent Test**: Configure weekly schedule, complete import, verify next scheduled job created with correct timestamp

### Backend Scheduling

- [ ] T076 [US5] Add schedule field to inventory config schema (manual, daily, weekly)
- [ ] T077 [US5] Implement chain scheduling in job completion handler (create next job on completion)
- [ ] T078 [US5] Calculate next scheduled_at (next fixed schedule occurrence: daily at 00:00 UTC, weekly same weekday at 00:00 UTC)
- [ ] T079 [US5] Add schedule cancellation when schedule disabled (cancel pending jobs)
- [ ] T080 [US5] Handle "Import Now" as immediate job independent of schedule

### Frontend Schedule UI

- [ ] T082 [P] [US5] Add schedule options to InventoryConfigForm (manual, daily, weekly)
- [ ] T083 [US5] Display next scheduled import timestamp in connector inventory section
- [ ] T084 [US5] Update status display to show scheduled vs in-progress states

### Tests for US5

- [ ] T081 [P] [US5] Unit tests for chain scheduling logic in `backend/tests/unit/services/test_inventory_service.py`
- [ ] T081a [P] [US5] Unit tests for next scheduled_at calculation (fixed schedule occurrences: daily at 00:00 UTC, weekly same weekday at 00:00 UTC) in `backend/tests/unit/services/test_inventory_service.py`
- [ ] T081b [P] [US5] Unit tests for schedule cancellation (pending job cleanup) in `backend/tests/unit/services/test_inventory_service.py`
- [ ] T084a [US5] Integration test for complete scheduling workflow (enable → complete → next job created) in `backend/tests/integration/api/test_inventory_scheduling.py`

**Checkpoint**: Users can configure automatic import schedules, system creates chain of scheduled jobs

---

## Phase 7: User Story 7 - Server-Side No-Change Detection (Priority: P2)

**Goal**: Server detects "no change" situations during job claim for Collections with inventory-sourced FileInfo, auto-completing jobs without sending to agent

**Independent Test**: Create Collection with inventory-sourced FileInfo, run job successfully, trigger same job type again without file changes, verify server auto-completes with "no_change" status

**Background**: With FileInfo now stored server-side from inventory imports, the server can compute input state hashes and detect "no change" situations during job claim, saving network round-trips and agent processing time.

### Backend Implementation

- [ ] T120 [US7] Create input state hash computation service in `backend/src/services/input_state_hash_service.py`
- [ ] T121 [US7] Implement FileInfo hash computation (deterministic hash of file list)
- [ ] T122 [US7] Implement config hash computation (hash of relevant job config data)
- [ ] T123 [US7] Combine FileInfo hash + config hash into input_state_hash
- [ ] T124 [US7] Extend job claim endpoint to check for inventory-sourced FileInfo (`file_info_source: "inventory"`)
- [ ] T125 [US7] Add server-side hash comparison against previous execution's `input_state_hash`
- [ ] T126 [US7] Implement auto-completion with `termination_status: "no_change"` when hashes match
- [ ] T127 [US7] Return next available job to agent when current job is auto-completed
- [ ] T128 [US7] Add metadata to auto-completed jobs indicating server-side detection
- [ ] T129 [US7] Skip server-side detection when `file_info_source` is null or "api"
- [ ] T130 [US7] Skip server-side detection when no previous execution result exists

### Tests for US7

- [ ] T131 [P] [US7] Unit tests for FileInfo hash computation (deterministic, order-independent) in `backend/tests/unit/services/test_input_state_hash_service.py`
- [ ] T132 [P] [US7] Unit tests for config hash computation in `backend/tests/unit/services/test_input_state_hash_service.py`
- [ ] T133 [P] [US7] Unit tests for hash comparison logic in `backend/tests/unit/services/test_input_state_hash_service.py`
- [ ] T134 [US7] Integration test: no-change detected, job auto-completed in `backend/tests/integration/api/test_nochange_detection.py`
- [ ] T135 [US7] Integration test: change detected, job sent to agent in `backend/tests/integration/api/test_nochange_detection.py`
- [ ] T136 [US7] Integration test: non-inventory FileInfo, job sent to agent in `backend/tests/integration/api/test_nochange_detection.py`
- [ ] T137 [US7] Integration test: no previous execution, job sent to agent in `backend/tests/integration/api/test_nochange_detection.py`
- [ ] T138 [US7] Integration test: next job returned after auto-completion in `backend/tests/integration/api/test_nochange_detection.py`
- [ ] T139 [US7] Performance test: SC-011 - server-side detection adds <50ms latency in `backend/tests/performance/test_nochange_performance.py`

**Checkpoint**: Server auto-completes "no change" jobs for inventory-sourced Collections without agent involvement

---

## Phase 8: User Story 6 - Delta Detection Between Inventories (Priority: P3)

**Goal**: Agent detects changes (new/modified/deleted files) between inventory imports

**Independent Test**: Run import on Collection with FileInfo, modify source files, run next import, verify delta summary

### Agent Phase C Implementation

- [ ] T085 [US6] Implement Phase C (Delta Detection) in `agent/src/tools/inventory_import_tool.py`
- [ ] T086 [US6] Compare current inventory against stored FileInfo per Collection
- [ ] T087 [US6] Detect new files (in current, not in previous)
- [ ] T088 [US6] Detect modified files (different ETag or size)
- [ ] T089 [US6] Detect deleted files (in previous, not in current)

### Backend Delta Storage

- [ ] T091 [US6] Add POST endpoint `/api/agent/v1/jobs/{guid}/inventory/delta` for delta results
- [ ] T092 [US6] Store delta summary on Collection (file_info_delta JSONB)
- [ ] T093 [US6] Handle first import case (all files reported as new)

### Frontend Delta Display

- [ ] T094 [P] [US6] Display change statistics on Collection view (X new, Y modified, Z deleted)
- [ ] T095 [US6] Add delta summary to import completion notification

### Tests for US6

- [ ] T086a [P] [US6] Unit tests for new file detection in `agent/tests/unit/test_inventory_import_tool.py`
- [ ] T088a [P] [US6] Unit tests for modified file detection (ETag change, size change) in `agent/tests/unit/test_inventory_import_tool.py`
- [ ] T089a [P] [US6] Unit tests for deleted file detection in `agent/tests/unit/test_inventory_import_tool.py`
- [ ] T090 [US6] Unit tests for Phase C pipeline in `agent/tests/unit/test_inventory_import_tool.py`
- [ ] T093a [US6] Integration test for delta endpoint and storage in `backend/tests/integration/api/test_inventory_api.py`

**Checkpoint**: Users see what changed between inventory imports with per-Collection delta summaries

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Error handling, edge cases, performance optimization, documentation

### Error Handling Implementation

- [ ] T096 [P] Implement edge case: Empty inventory (complete with zero folders)
- [ ] T097 [P] Implement edge case: Malformed CSV rows (skip and log, continue processing)
- [ ] T098 [P] Implement edge case: Missing required fields (fail validation with clear message)
- [ ] T099 [P] Implement edge case: Inventory not yet generated (display appropriate message)
- [ ] T100 Implement edge case: Stale inventory warning (display generation timestamp)
- [ ] T108 Implement edge case: Deep folder hierarchies (10+ levels)
- [ ] T109 Implement edge case: URL-encoded folder names decoded in suggestions
- [ ] T110 Implement edge case: All folders mapped disables "Create Collections"
- [ ] T111 Implement edge case: No state selected prevents collection creation
- [ ] T112 Implement edge case: Large folder selections (100+) with virtualization

### Edge Case Tests

- [ ] T096a [P] Test: Empty inventory completes successfully with zero folders in `agent/tests/unit/test_inventory_parser.py`
- [ ] T097a [P] Test: Malformed CSV rows skipped with warning logged in `agent/tests/unit/test_inventory_parser.py`
- [ ] T098a [P] Test: Missing required fields fails validation with clear message in `agent/tests/unit/test_inventory_parser.py`
- [ ] T099a [P] Test: Inventory not yet generated displays appropriate message in `backend/tests/integration/api/test_inventory_api.py`
- [ ] T100a [P] Test: Stale inventory warning displayed when data > N days old in `frontend/tests/components/inventory/InventoryStatus.test.tsx`
- [ ] T108a [P] Test: Deep folder hierarchies (10+ levels) handled correctly in `agent/tests/unit/test_inventory_parser.py`
- [ ] T109a [P] Test: URL-encoded folder names decoded in name suggestions in `frontend/tests/utils/test_name_suggestion.ts`
- [ ] T110a [P] Test: All folders already mapped disables "Create Collections" action in `frontend/tests/components/inventory/FolderTree.test.tsx`
- [ ] T111a [P] Test: No state selected prevents collection creation in `frontend/tests/components/inventory/CreateCollectionsDialog.test.tsx`
- [ ] T112a [P] Test: Large folder selections (100+) handled with virtualization in `frontend/tests/components/inventory/FolderTree.test.tsx`

### Performance Verification

- [ ] T101 Verify streaming CSV processing for large inventories (1M+ objects)
- [ ] T102 Verify folder tree virtualization performance (10k+ folders in <2 seconds)
- [ ] T103 Verify agent memory usage <1GB for 5M object inventories

### Performance Tests (Success Criteria)

- [ ] T113 Performance test: SC-002 - Full pipeline completes <10 min for 1M objects in `agent/tests/performance/test_inventory_performance.py`
- [ ] T114 Performance test: SC-003 - Manifest fetch/parse <10 seconds in `agent/tests/performance/test_inventory_performance.py`
- [ ] T115 Performance test: SC-004 - Folder tree renders 10k folders <2 seconds in `frontend/tests/performance/test_folder_tree_performance.ts`
- [ ] T116 Performance test: SC-005 - Agent memory <1GB for 5M objects in `agent/tests/performance/test_inventory_performance.py`
- [ ] T117 [P] Test: SC-007 - Zero cloud API calls with cached FileInfo in `backend/tests/integration/tools/test_fileinfo_integration.py`
- [ ] T118 [P] Test: SC-009 - FileInfo accuracy matches direct cloud API results in `agent/tests/integration/test_inventory_import_tool.py`

### Documentation & Validation

- [ ] T104 [P] Update OpenAPI documentation for inventory endpoints
- [ ] T105 [P] Add inventory examples to API documentation
- [ ] T106 Run quickstart.md validation (full pipeline test)
- [ ] T107 End-to-end test: complete workflow from config to delta detection
- [ ] T119 E2E test: SC-001 - Complete configuration to first import workflow in `tests/e2e/test_inventory_workflow.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - can start immediately
- **Phase 2 (US1 - Config)**: Depends on Phase 1 - models and schemas must exist
- **Phase 3 (US2 - Import)**: Depends on Phase 1, Phase 2 - needs config validation
- **Phase 4 (US3 - Mapping)**: Depends on Phase 3 - needs folders discovered
- **Phase 5 (US4 - FileInfo)**: Depends on Phase 4 - needs Collections mapped
- **Phase 6 (US5 - Scheduling)**: Depends on Phase 3 - needs import job infrastructure
- **Phase 7 (US7 - No-Change Detection)**: Depends on Phase 5 - needs inventory-sourced FileInfo stored
- **Phase 8 (US6 - Delta)**: Depends on Phase 5 - needs FileInfo stored
- **Phase 9 (Polish)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (Config)**: Foundation only - can start after Phase 1
- **US2 (Import)**: Requires US1 (valid config needed to trigger import)
- **US3 (Mapping)**: Requires US2 (folders must be discovered first)
- **US4 (FileInfo)**: Requires US3 (Collections must exist to receive FileInfo)
- **US5 (Scheduling)**: Requires US2 (import job must work)
- **US6 (Delta)**: Requires US4 (previous FileInfo needed for comparison)
- **US7 (No-Change Detection)**: Requires US4 (needs inventory-sourced FileInfo on Collections)

### Parallel Opportunities

Within each phase, tasks marked [P] can run in parallel:
- Phase 1: T002, T003, T005, T006, T007, T008, T008a, T008b, T008c can all run in parallel
- Phase 2: T015, T015a, T017, T018 can run in parallel
- Phase 3: T024, T025, T026a, T033, T033a, T033b, T033c, T033d, T033e can run in parallel
- Phase 4: T046a, T053a, T058a, T058b can run in parallel
- Phase 5: T065a, T066a, T074 can run in parallel
- Phase 6: T081, T081a, T081b, T082 can run in parallel
- Phase 7: T131, T132, T133 can run in parallel
- Phase 8: T086a, T088a, T089a, T094 can run in parallel
- Phase 9: All edge case tests can run in parallel

Across phases (with team capacity):
- US5 (Scheduling) can start in parallel with US4 (FileInfo) since they share dependencies on US2
- US6 (Delta) and US7 (No-Change Detection) both depend on US4 and can run in parallel with each other

---

## Parallel Example: Phase 1 Setup

```bash
# Launch all parallel model/schema tasks together:
Task: "Add inventory fields to backend/src/models/connector.py"
Task: "Add FileInfo fields to backend/src/models/collection.py"
Task: "Create backend/src/schemas/inventory.py"
Task: "Extend backend/src/schemas/collection.py"
Task: "Create frontend/src/contracts/api/inventory-api.ts"

# Launch all parallel test tasks together:
Task: "Unit tests for InventoryFolder model"
Task: "Unit tests for Connector model inventory extensions"
Task: "Unit tests for Collection model FileInfo extensions"
Task: "Unit tests for Pydantic schemas"
```

---

## Summary

| Phase | User Story | Priority | Tasks | Test Tasks | Total |
|-------|------------|----------|-------|------------|-------|
| 1 | Setup | - | 7 | 4 | 11 |
| 2 | US1 - Configure Inventory Source | P1 | 12 | 6 | 18 |
| 3 | US2 - Import and Extract Folders | P1 | 18 | 11 | 29 |
| 4 | US3 - Map Folders to Collections | P1 | 11 | 10 | 21 |
| 5 | US4 - FileInfo Population | P1 | 8 | 7 | 15 |
| 6 | US5 - Scheduled Import | P2 | 6 | 4 | 10 |
| 7 | US7 - Server-Side No-Change Detection | P2 | 11 | 9 | 20 |
| 8 | US6 - Delta Detection | P3 | 8 | 5 | 13 |
| 9 | Polish | - | 17 | 17 | 34 |
| **Total** | | | **98** | **73** | **171** |

**Test Coverage**: 73 test tasks / 171 total = **43%** test task ratio

---

## Test File Structure

```text
backend/tests/
├── unit/
│   ├── models/
│   │   ├── test_inventory_folder.py      # T008
│   │   ├── test_connector.py             # T008a
│   │   └── test_collection.py            # T008b
│   ├── schemas/
│   │   └── test_inventory_schemas.py     # T008c
│   └── services/
│       ├── test_inventory_service.py     # T015, T015a, T058a, T058b, T069a, T081, T081a, T081b
│       └── test_input_state_hash_service.py  # T131, T132, T133
├── integration/
│   ├── api/
│   │   ├── test_inventory_api.py         # T016, T016b, T040a, T040b, T062, T062a, T062b, T073, T073a, T093a, T099a
│   │   ├── test_inventory_validation_flow.py  # T016a
│   │   ├── test_inventory_scheduling.py  # T084a
│   │   └── test_nochange_detection.py    # T134, T135, T136, T137, T138
│   └── tools/
│       └── test_fileinfo_integration.py  # T071a, T117
├── performance/
│   └── test_nochange_performance.py      # T139
└── e2e/
    └── test_inventory_workflow.py        # T119

agent/tests/
├── unit/
│   ├── test_inventory_parser.py          # T033, T033a, T033b, T033c, T033d, T096a, T097a, T098a, T108a
│   └── test_inventory_import_tool.py     # T033e, T065a, T066a, T067, T086a, T088a, T089a, T090
├── integration/
│   └── test_inventory_import_tool.py     # T034, T034a, T118
└── performance/
    └── test_inventory_performance.py     # T113, T114, T116

frontend/tests/
├── components/
│   └── inventory/
│       ├── InventoryConfigForm.test.tsx  # T023
│       ├── FolderTree.test.tsx           # T049, T110a, T112a
│       ├── CreateCollectionsDialog.test.tsx  # T056, T056a, T111a
│       └── InventoryStatus.test.tsx      # T100a
├── utils/
│   ├── test_folder_selection.ts          # T046a
│   └── test_name_suggestion.ts           # T053a, T109a
└── performance/
    └── test_folder_tree_performance.ts   # T115
```

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Agent tool implementation (Phase 3) is the most complex - consider allocating extra time
- Frontend folder tree (Phase 4) requires careful attention to virtualization for 10k+ folders
- **Tests are organized within each phase** to enable test-first development when desired
