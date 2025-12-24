# Tasks: Photo Pairing Tool

**Input**: Design documents from `/specs/001-photo-pairing-tool/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are included based on Testing & Quality constitution principle (flexible approach - tests alongside implementation).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Single project structure: Files at repository root
- Tests in `tests/` directory
- Config in `config/` directory

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Update config template with camera_mappings and processing_methods schema in config/template-config.yaml
- [ ] T002 [P] Extend PhotoAdminConfig class with methods to access camera_mappings and processing_methods in config_manager.py

**Checkpoint**: Configuration infrastructure ready for photo pairing tool

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Create main script file photo_pairing.py with argument parsing for folder path
- [ ] T004 [P] Implement filename validation regex and validation function in photo_pairing.py
- [ ] T005 [P] Implement filename parsing logic to extract camera_id, counter, and properties in photo_pairing.py
- [ ] T006 [P] Implement property type detection (numeric vs alphanumeric) in photo_pairing.py
- [ ] T007 Implement file scanning function using pathlib.rglob with extension filtering in photo_pairing.py
- [ ] T008 Implement ImageGroup builder that organizes files by 8-char prefix with separate_images structure in photo_pairing.py
- [ ] T009 Implement invalid file tracking with validation failure reasons in photo_pairing.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - First Run Analysis (Priority: P1) 🎯 MVP

**Goal**: Enable photographers to analyze their photo collection for the first time, with interactive prompts for camera IDs and processing methods, generating comprehensive HTML reports.

**Independent Test**: Run tool on sample folder with photos from 2+ cameras and 2+ processing methods. Verify prompts appear, configuration is saved, and complete HTML report is generated.

### Implementation for User Story 1

- [ ] T010 [US1] Implement camera mapping lookup and prompt logic in photo_pairing.py
- [ ] T011 [US1] Implement processing method lookup and prompt logic in photo_pairing.py
- [ ] T012 [US1] Implement placeholder generation for empty user input (FR-017) in photo_pairing.py
- [ ] T013 [US1] Implement config file update function for camera_mappings (as list structure) in photo_pairing.py
- [ ] T014 [US1] Implement config file update function for processing_methods in photo_pairing.py
- [ ] T015 [US1] Implement CameraUsage analytics aggregation in photo_pairing.py
- [ ] T016 [US1] Implement MethodUsage analytics aggregation in photo_pairing.py
- [ ] T017 [US1] Implement ReportStatistics calculation in photo_pairing.py
- [ ] T018 [US1] Implement HTML report generation with summary statistics in photo_pairing.py
- [ ] T019 [US1] Implement HTML tables for camera usage breakdown in photo_pairing.py
- [ ] T020 [US1] Implement HTML tables for processing method breakdown in photo_pairing.py
- [ ] T021 [US1] Add Chart.js integration for camera usage visualization in photo_pairing.py
- [ ] T022 [US1] Add Chart.js integration for processing method visualization in photo_pairing.py
- [ ] T023 [US1] Implement timestamped HTML report filename generation in photo_pairing.py
- [ ] T024 [US1] Add progress indicators and status messages for user feedback in photo_pairing.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently - photographers can analyze folders and get complete reports with prompts.

---

## Phase 4: User Story 2 - Cached Analysis & Fast Regeneration (Priority: P2)

**Goal**: Enable instant report regeneration when folder content hasn't changed, using cached ImageGroup data. Perfect for updating camera/method descriptions.

**Independent Test**: Run tool twice on same folder. First run creates cache. Second run uses cache and completes in under 2 seconds.

### Implementation for User Story 2

- [ ] T025 [US2] Implement file list hash calculation (SHA256 of sorted relative paths) in photo_pairing.py
- [ ] T026 [US2] Implement ImageGroup structure hash calculation in photo_pairing.py
- [ ] T027 [US2] Implement JSON cache file writer for ImageGroup structure in photo_pairing.py
- [ ] T028 [US2] Implement cache file metadata generation (timestamps, hashes, statistics) in photo_pairing.py
- [ ] T029 [US2] Implement cache file loader and JSON parser in photo_pairing.py
- [ ] T030 [US2] Implement cache validation logic (hash comparison) in photo_pairing.py
- [ ] T031 [US2] Implement user prompt for stale cache handling (options a/b) in photo_pairing.py
- [ ] T032 [US2] Integrate cache check at tool startup in photo_pairing.py
- [ ] T033 [US2] Implement report generation from cached data (skip analysis path) in photo_pairing.py
- [ ] T034 [US2] Add cache file save after successful analysis completion (not on Ctrl+C) in photo_pairing.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - first run analyzes and caches, subsequent runs use cache when valid.

---

## Phase 5: User Story 3 - Invalid Filename Detection (Priority: P3)

**Goal**: Help photographers identify non-compliant filenames with clear explanations so they can rename or organize files.

**Independent Test**: Analyze folder with mix of valid and invalid filenames. Verify invalid files listed in report with specific reasons.

### Implementation for User Story 3

- [ ] T035 [US3] Implement detailed validation error message generation in photo_pairing.py
- [ ] T036 [US3] Add invalid files table to HTML report with filename and reason columns in photo_pairing.py
- [ ] T037 [US3] Implement validation rule documentation display in report in photo_pairing.py
- [ ] T038 [US3] Add invalid file count to summary statistics in photo_pairing.py

**Checkpoint**: All user stories should now be independently functional - complete analysis with validation feedback.

---

## Phase 6: Error Handling & Edge Cases

**Purpose**: Handle interruptions and edge cases gracefully

- [ ] T039 [P] Implement Ctrl+C handler for graceful exit (FR-016) in photo_pairing.py
- [ ] T040 [P] Add error handling for corrupted cache files with graceful degradation in photo_pairing.py
- [ ] T041 [P] Add error handling for folder permission errors in photo_pairing.py
- [ ] T042 [P] Implement cache file path handling for .photo_pairing_imagegroups in photo_pairing.py

---

## Phase 7: Testing

**Purpose**: Comprehensive test coverage for reliability

- [ ] T043 [P] Create test fixtures for sample filenames and ImageGroups in tests/test_photo_pairing.py
- [ ] T044 [P] Write tests for filename validation (valid/invalid patterns) in tests/test_photo_pairing.py
- [ ] T045 [P] Write tests for filename parsing (camera_id, counter, properties) in tests/test_photo_pairing.py
- [ ] T046 [P] Write tests for property type detection (numeric vs alphanumeric) in tests/test_photo_pairing.py
- [ ] T047 [P] Write tests for file grouping by 8-char prefix in tests/test_photo_pairing.py
- [ ] T048 [P] Write tests for separate_images structure building in tests/test_photo_pairing.py
- [ ] T049 [P] Write tests for duplicate property deduplication in tests/test_photo_pairing.py
- [ ] T050 [P] Write tests for empty property detection in tests/test_photo_pairing.py
- [ ] T051 [P] Write tests for config update functions (camera_mappings) in tests/test_photo_pairing.py
- [ ] T052 [P] Write tests for config update functions (processing_methods) in tests/test_photo_pairing.py
- [ ] T053 [P] Write tests for placeholder generation on empty input in tests/test_photo_pairing.py
- [ ] T054 [P] Write tests for hash calculations (file list and ImageGroup) in tests/test_photo_pairing.py
- [ ] T055 [P] Write tests for cache validation logic in tests/test_photo_pairing.py
- [ ] T056 [P] Write tests for cache save/load roundtrip in tests/test_photo_pairing.py
- [ ] T057 [P] Write tests for analytics calculations (CameraUsage, MethodUsage, ReportStatistics) in tests/test_photo_pairing.py
- [ ] T058 [P] Write tests for HTML report generation (structure validation) in tests/test_photo_pairing.py
- [ ] T059 Write integration test for complete first-run workflow in tests/test_photo_pairing.py
- [ ] T060 Write integration test for cached analysis workflow in tests/test_photo_pairing.py
- [ ] T061 Write integration test for stale cache handling in tests/test_photo_pairing.py

---

## Phase 8: Documentation & Polish

**Purpose**: Finalize documentation and user experience

- [ ] T062 [P] Add module-level docstring and function docstrings to photo_pairing.py
- [ ] T063 [P] Add usage examples to photo_pairing.py --help output
- [ ] T064 [P] Create user documentation in docs/photo-pairing.md
- [ ] T065 Update README.md with Photo Pairing Tool section and usage example
- [ ] T066 Run full test suite and ensure >80% coverage
- [ ] T067 Test tool end-to-end on real photo collection
- [ ] T068 Verify constitution compliance (all checkboxes in plan.md)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories CAN proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Error Handling (Phase 6)**: Can be done in parallel with user stories
- **Testing (Phase 7)**: Can start after foundational; tests can be written alongside implementation
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Builds on US1 but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Independent of US1/US2

### Within Each User Story

- Models before services before endpoints (if applicable)
- Core implementation before integration
- Tests can be written alongside (flexible TDD approach per constitution)
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All test tasks marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Core implementation tasks that can run in parallel:
Task T010: Implement camera mapping lookup (modifies photo_pairing.py section A)
Task T011: Implement processing method lookup (modifies photo_pairing.py section B)
Task T015: Implement CameraUsage analytics (modifies photo_pairing.py section C)
Task T016: Implement MethodUsage analytics (modifies photo_pairing.py section D)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Run on real photo collection
6. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo (caching feature)
4. Add User Story 3 → Test independently → Deploy/Demo (validation feature)
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (T010-T024)
   - Developer B: User Story 2 (T025-T034)
   - Developer C: User Story 3 (T035-T038)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different sections of code, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tests use flexible approach per constitution (alongside implementation)
- Commit after logical groups of related tasks
- Stop at any checkpoint to validate story independently
- File: photo_pairing.py contains all logic (single CLI tool per constitution)
- Config updates save camera_mappings as list (future-compatible)
- Cache file (.photo_pairing_imagegroups) only saved on successful completion

---

## Constitution Compliance

✅ **Independent CLI Tools**: photo_pairing.py is standalone, uses PhotoAdminConfig
✅ **Testing & Quality**: Comprehensive test suite (Phase 7) with flexible approach
✅ **User-Centric Design**: HTML reports, clear error messages, observability, simplicity
✅ **Shared Infrastructure**: Uses PhotoAdminConfig, extends shared config schema
✅ **Simplicity**: Direct implementation, no premature abstractions

---

## Task Summary

**Total Tasks**: 68
**Setup**: 2 tasks
**Foundational**: 7 tasks (blocking)
**User Story 1 (P1 - MVP)**: 15 tasks
**User Story 2 (P2)**: 10 tasks
**User Story 3 (P3)**: 4 tasks
**Error Handling**: 4 tasks
**Testing**: 19 tasks
**Documentation**: 7 tasks

**Parallel Opportunities**: 45+ tasks marked [P]
**Independent Stories**: All 3 user stories are independently testable
**MVP Scope**: Phases 1-3 (24 tasks) delivers working photo analysis tool
