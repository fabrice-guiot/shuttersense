# Tasks: Fix Trend Aggregation for Storage-Optimized Results

**Input**: Design documents from `/specs/106-fix-trend-aggregation/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/trends-api.md
**Related Issue**: [#105](https://github.com/fabrice-guiot/shuttersense/issues/105)

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

This is a web application with `backend/` and `frontend/` structure per plan.md.

---

## Phase 1: Setup

**Purpose**: Verify environment and understand existing code

- [x] T001 Verify feature branch 106-fix-trend-aggregation is checked out
- [x] T002 [P] Review existing trend_service.py structure in backend/src/services/trend_service.py
- [x] T003 [P] Review existing trends.py schemas in backend/src/schemas/trends.py
- [x] T004 [P] Review existing trend tests in backend/tests/unit/test_trend_service.py

**Checkpoint**: Environment ready, existing code understood

---

## Phase 2: Foundational (Schema Updates)

**Purpose**: Add `calculated_count` field to response schemas (required by all user stories)

**⚠️ CRITICAL**: Schema changes must be complete before service layer changes

- [x] T005 Add `calculated_count` field to PhotoStatsAggregatedPoint in backend/src/schemas/trends.py
- [x] T006 Add `calculated_count` field to PhotoPairingAggregatedPoint in backend/src/schemas/trends.py
- [x] T007 Add `calculated_count` field to PipelineValidationAggregatedPoint in backend/src/schemas/trends.py
- [x] T008 Add `calculated_count` field to PhotoStatsAggregatedPoint in frontend/src/contracts/api/trends-api.ts
- [x] T009 Add `calculated_count` field to PhotoPairingAggregatedPoint in frontend/src/contracts/api/trends-api.ts
- [x] T010 Add `calculated_count` field to PipelineValidationAggregatedPoint in frontend/src/contracts/api/trends-api.ts

**Checkpoint**: Schema foundation ready - service layer can now be updated

---

## Phase 3: User Story 1 - Accurate Multi-Collection Trend Viewing (Priority: P1) 🎯 MVP

**Goal**: Fix the core bug - ensure aggregated trends correctly include all collections by filling forward missing values

**Independent Test**: Query `/api/trends/photostats` with 2 collections having staggered results, verify aggregation is mathematically correct (sequence 18→18→20→20 per Issue #105)

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T011 [P] [US1] Add unit test for _get_seed_values helper in backend/tests/unit/test_trend_service.py
- [x] T012 [P] [US1] Add unit test for _fill_forward_aggregation helper in backend/tests/unit/test_trend_service.py
- [x] T013 [P] [US1] Add unit test for fill-forward with gaps scenario in backend/tests/unit/test_trend_service.py
- [x] T014 [P] [US1] Add unit test for new collection mid-window scenario in backend/tests/unit/test_trend_service.py
- [x] T015 [P] [US1] Add integration test for Issue #105 exact scenario in backend/tests/integration/test_trend_aggregation.py

### Implementation for User Story 1

- [x] T016 [US1] Implement _get_seed_values helper method in backend/src/services/trend_service.py
- [x] T017 [US1] Implement _fill_forward_aggregation helper method in backend/src/services/trend_service.py
- [x] T018 [US1] Update get_photostats_trends aggregated mode to use fill-forward in backend/src/services/trend_service.py
- [x] T019 [US1] Verify tests pass for PhotoStats fill-forward implementation

**Checkpoint**: PhotoStats aggregation is now mathematically correct. US1 can be tested independently.

---

## Phase 4: User Story 3 - Consistent Behavior Across All Tools (Priority: P1)

**Goal**: Apply the same fill-forward fix to Photo Pairing, Pipeline Validation, and Trend Summary

**Independent Test**: Query each tool's trend endpoint with staggered collection results, verify all produce correct aggregations

**Note**: This is P1 priority because a partial fix (only PhotoStats) would be incomplete

### Tests for User Story 3

- [x] T020 [P] [US3] Add unit test for Photo Pairing fill-forward in backend/tests/unit/test_trend_service.py
- [x] T021 [P] [US3] Add unit test for Pipeline Validation fill-forward in backend/tests/unit/test_trend_service.py (includes collection mode AND display-graph mode by pipeline+version)
- [x] T022 [P] [US3] Add unit test for Trend Summary fill-forward in backend/tests/unit/test_trend_service.py
- [x] T023 [P] [US3] Add regression test for comparison mode (no fill-forward) in backend/tests/unit/test_trend_service.py

### Implementation for User Story 3

- [x] T024 [US3] Update get_photo_pairing_trends aggregated mode to use fill-forward in backend/src/services/trend_service.py
- [x] T025 [US3] Update get_pipeline_validation_trends aggregated mode to use fill-forward in backend/src/services/trend_service.py (includes display-graph mode with fill-forward by pipeline+version)
- [x] T026 [US3] Update get_trend_summary to use fill-forward for both orphaned and consistency trends in backend/src/services/trend_service.py (already implemented via PhotoStats aggregation logic)
- [x] T027 [US3] Verify all tool tests pass (37 unit tests + 12 integration tests pass)

**Checkpoint**: All tools now have correct aggregation. Core bug fix complete.

---

## Phase 5: User Story 2 - Visual Distinction of Calculated vs. Actual Data Points (Priority: P2)

**Goal**: Frontend displays calculated_count information so users can distinguish actual vs filled data points

**Independent Test**: View a trend chart with mixed actual/filled data, verify tooltip shows "X of Y collections have actual data"

### Implementation for User Story 2

- [x] T028 [US2] Identify trend chart components that need updating in frontend/src/components/charts/
  - TrendChart.tsx (BaseLineChart tooltip)
  - PhotoStatsTrend.tsx
  - PhotoPairingTrend.tsx
  - PipelineValidationTrend.tsx
- [x] T029 [US2] Update chart tooltip to show calculated vs actual count when calculated_count > 0
  - Created AggregatedTooltip component with "X of Y collections have actual data" warning
  - Shows warning badge with AlertCircle icon when calculated_count > 0
  - Footer shows total collections included with "(X filled forward)" suffix
- [x] T030 [US2] Optional: Add visual styling for data points with calculated_count > 0 (lighter opacity or different marker)
  - Skipped: Warning in tooltip is sufficient visual distinction
- [x] T031 [US2] Verify frontend displays calculated information correctly
  - TypeScript compiles without errors for trend components
  - Test mocks updated with calculated_count field

**Checkpoint**: Users can now see which data points include filled values.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, performance, and final validation

- [ ] T032 [P] Add unit test for all-NO_CHANGE-day scenario in backend/tests/unit/test_trend_service.py
- [ ] T033 [P] Add unit test for empty trend window scenario in backend/tests/unit/test_trend_service.py
- [ ] T034 [P] Add unit test for very large date range (performance) in backend/tests/unit/test_trend_service.py
- [ ] T035 Add logging for seed query and fill-forward operations in backend/src/services/trend_service.py
- [ ] T036 Run full test suite and verify no regressions
- [ ] T037 Validate quickstart.md scenarios work as documented

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 - schema changes block service changes
- **Phase 3 (US1)**: Depends on Phase 2 - core PhotoStats fix
- **Phase 4 (US3)**: Depends on Phase 3 - extends fix to other tools (reuses helper methods)
- **Phase 5 (US2)**: Depends on Phase 2 - can run parallel to Phase 3/4 (frontend only needs schema)
- **Phase 6 (Polish)**: Depends on all prior phases

### User Story Dependencies

- **US1 (P1)**: Core fix - must complete first for MVP
- **US3 (P1)**: Extends US1 to all tools - depends on US1 helper methods
- **US2 (P2)**: Frontend enhancement - can start once schemas (Phase 2) are done

### Parallel Opportunities

**Within Phase 1:**
- T002, T003, T004 can run in parallel (reading different files)

**Within Phase 2:**
- T005, T006, T007 can run in parallel (same file but different classes - careful merge)
- T008, T009, T010 can run in parallel (same file - careful merge)
- Backend and frontend schema updates can run in parallel

**Within Phase 3 (US1 Tests):**
- T011, T012, T013, T014, T015 can all run in parallel (different test cases)

**Within Phase 4 (US3 Tests):**
- T020, T021, T022, T023 can all run in parallel (different test cases)

**Cross-Phase:**
- Phase 5 (US2 Frontend) can start once Phase 2 completes (parallel to Phase 3/4)

---

## Parallel Example: Phase 3 Tests

```bash
# Launch all US1 tests together:
Task: "Add unit test for _get_seed_values helper in backend/tests/unit/test_trend_service.py"
Task: "Add unit test for _fill_forward_aggregation helper in backend/tests/unit/test_trend_service.py"
Task: "Add unit test for fill-forward with gaps scenario in backend/tests/unit/test_trend_service.py"
Task: "Add unit test for new collection mid-window scenario in backend/tests/unit/test_trend_service.py"
Task: "Add integration test for Issue #105 exact scenario in backend/tests/integration/test_trend_aggregation.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (schema changes)
3. Complete Phase 3: User Story 1 (PhotoStats fix)
4. **STOP and VALIDATE**: Test PhotoStats aggregation independently
5. The core bug is fixed for the most common use case

### Incremental Delivery

1. **Schema + PhotoStats fix (US1)** → Core bug fixed for one tool
2. **Add US3** → Fix extended to all tools → Full backend fix complete
3. **Add US2** → Frontend shows calculated info → Enhanced user experience
4. **Add Polish** → Edge cases, performance → Production ready

### Parallel Team Strategy

With multiple developers:
1. Team completes Setup + Foundational together
2. Once schemas are done:
   - Developer A: US1 (PhotoStats fix)
   - Developer B: US2 (Frontend enhancement) - can start immediately
3. Once US1 complete:
   - Developer A: US3 (Other tools)
   - Developer B: Continues US2

---

## Task Summary

| Phase | Tasks | Parallel Opportunities |
|-------|-------|------------------------|
| Phase 1: Setup | 4 | 3 parallel |
| Phase 2: Foundational | 6 | Backend(3) + Frontend(3) parallel |
| Phase 3: US1 | 9 | 5 tests parallel, then 4 sequential |
| Phase 4: US3 | 8 | 4 tests parallel, then 4 sequential |
| Phase 5: US2 | 4 | Sequential (same components) |
| Phase 6: Polish | 6 | 3 tests parallel |
| **Total** | **37** | |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Tests should FAIL before implementation (TDD approach per plan.md Testing Strategy)
- Schema changes (Phase 2) are backward compatible - no breaking changes
- US1 provides immediate value - can deploy after Phase 3 completion
- Commit after each task or logical group
