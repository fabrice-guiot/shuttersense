# Tasks: UX Polish Epic

**Input**: Design documents from `/specs/006-ux-polish/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Backend tests are included (pytest exists in project). Frontend tests are minimal (focus on critical collapse behavior).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and schema changes required for KPIs

- [x] T001 Create Alembic migration for Collection stats columns (storage_bytes, file_count, image_count) in backend/src/db/migrations/versions/
- [x] T002 Run migration to add new columns: `alembic upgrade head`
- [x] T003 [P] Add new columns to Collection model in backend/src/models/collection.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend schemas and response types that all user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Add CollectionStatsResponse schema in backend/src/schemas/collection.py
- [x] T005 [P] Add ConnectorStatsResponse schema in backend/src/schemas/collection.py
- [x] T006 [P] Add format_storage_bytes utility function in backend/src/utils/ (bytes → human-readable)
- [x] T007 [P] Add CollectionStatsResponse TypeScript type in frontend/src/contracts/api/collection-api.ts
- [x] T008 [P] Add ConnectorStatsResponse TypeScript type in frontend/src/contracts/api/connector-api.ts

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - View Dashboard KPI Metrics (Priority: P1) 🎯 MVP

**Goal**: Display aggregated KPI statistics on Collections and Connectors pages

**Independent Test**: Navigate to Collections/Connectors pages and verify KPI values match database aggregations

**Relates to**: Issue #37

### Backend Implementation for User Story 1

- [x] T009 [US1] Add get_collection_stats() method to CollectionService in backend/src/services/collection_service.py
- [x] T010 [US1] Add GET /collections/stats endpoint in backend/src/api/collections.py
- [x] T011 [P] [US1] Add get_connector_stats() method to ConnectorService in backend/src/services/connector_service.py
- [x] T012 [P] [US1] Add GET /connectors/stats endpoint in backend/src/api/connectors.py
- [x] T013 [US1] Add pytest tests for collection stats endpoint in backend/tests/unit/test_api_collections.py
- [x] T014 [P] [US1] Add pytest tests for connector stats endpoint in backend/tests/unit/test_api_connectors.py

### Frontend Implementation for User Story 1

- [x] T015 [P] [US1] Create HeaderStatsContext for dynamic topbar stats in frontend/src/contexts/HeaderStatsContext.tsx
- [x] T016 [P] [US1] Update MainLayout to use HeaderStatsContext (replaces static route stats)
- [x] T017 [US1] Add useCollectionStats hook in frontend/src/hooks/useCollections.ts
- [x] T018 [P] [US1] Add useConnectorStats hook in frontend/src/hooks/useConnectors.ts
- [x] T019 [US1] Integrate KPI stats into CollectionsPage topbar (4 stats: Total Collections, Storage Used, Files, Images)
- [x] T020 [US1] Integrate KPI stats into ConnectorsPage topbar (2 stats: Active Connectors, Total Connectors)
- [x] T021 [US1] Remove static placeholder stats from App.tsx routes
- [x] T022 [US1] Stats auto-clear on page unmount (prevents stale data)

**Checkpoint**: KPI metrics visible on both pages - User Story 1 complete

---

## Phase 4: User Story 2 - Search Collections by Name (Priority: P2)

**Goal**: Allow filtering collections by name with case-insensitive partial matching

**Independent Test**: Type in search field and verify collection list filters correctly

**Relates to**: Issue #38

### Backend Implementation for User Story 2

- [x] T023 [US2] Add search parameter to list_collections() in backend/src/services/collection_service.py
- [x] T024 [US2] Add search query parameter to GET /collections endpoint in backend/src/api/collections.py
- [x] T025 [US2] Add pytest tests for search functionality in backend/tests/unit/test_api_collections.py
- [x] T026 [US2] Test SQL injection protection (parameterized queries) in backend/tests/unit/test_api_collections.py

### Frontend Implementation for User Story 2

- [x] T027 [US2] Add search state and debounce logic to useCollections hook in frontend/src/hooks/useCollections.ts
- [x] T028 [US2] Add search input component to FiltersSection in frontend/src/components/collections/FiltersSection.tsx
- [x] T029 [US2] Wire search input to useCollections hook in CollectionsPage in frontend/src/pages/CollectionsPage.tsx
- [x] T030 [US2] Update empty state message when no collections match search in frontend/src/components/collections/CollectionList.tsx
- [x] T031 [US2] Add input maxLength (100 chars) to prevent excessive queries

**Checkpoint**: Search filters collections by name - User Story 2 complete

---

## Phase 5: User Story 3 - Collapse Sidebar on Tablet (Priority: P3)

**Goal**: Allow users on tablet-sized screens to manually collapse sidebar for more content space

**Independent Test**: Click collapse arrow on tablet viewport, verify sidebar transitions to hamburger mode; click Pin to restore

**Relates to**: Issue #41

### Frontend Implementation for User Story 3

- [x] T032 [P] [US3] Create useSidebarCollapse hook with localStorage persistence in frontend/src/hooks/useSidebarCollapse.ts
- [x] T033 [US3] Add collapse arrow button (ChevronLeft) to Sidebar right edge in frontend/src/components/layout/Sidebar.tsx
- [x] T034 [US3] Add Pin button to hamburger menu header in frontend/src/components/layout/Sidebar.tsx
- [x] T035 [US3] Update MainLayout to use useSidebarCollapse hook in frontend/src/components/layout/MainLayout.tsx
- [x] T036 [US3] Add CSS transitions for collapse animation (300ms duration) in frontend/src/components/layout/Sidebar.tsx
- [x] T037 [US3] Hide collapse arrow when viewport < 768px (already hamburger mode)
- [x] T038 [US3] Add vitest test for collapse state persistence in frontend/tests/components/layout/Sidebar.test.tsx

**Checkpoint**: Sidebar collapse/expand working on tablet - User Story 3 complete

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and improvements across all features

- [x] T039 [P] Verify KPIs refresh when collections/connectors are created/deleted (fixed: added refetchStats() calls)
- [x] T040 [P] Test search + filters combination (state, type, accessible_only) (verified: backend properly chains all filters)
- [x] T041 [P] Test collapse state persistence across page navigation (10+ navigations) (verified: test exists in useSidebarCollapse.test.ts)
- [x] T042 Run all backend tests: `pytest backend/tests/ -v` (344 passed, 2 skipped)
- [x] T043 Run frontend build: `npm run build` (in frontend/) (build successful)
- [ ] T044 Manual E2E validation per quickstart.md testing checklist
- [x] T045 Update CLAUDE.md if any new patterns introduced (no new patterns needed)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on T001-T003 (migration + model update)
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1 - KPIs)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P2 - Search)**: Can start after Foundational - No dependencies on US1
- **User Story 3 (P3 - Collapse)**: Can start after Foundational - No dependencies on US1/US2 (frontend-only)

### Within Each User Story

- Backend implementation before frontend integration
- Schemas before services before endpoints
- Tests after implementation (not strict TDD for this epic)

### Parallel Opportunities

**Phase 1 (Setup)**:
- T003 can run parallel with T001/T002 completion

**Phase 2 (Foundational)**:
- T004, T005, T006 can run in parallel (different files)
- T007, T008 can run in parallel (different files)

**Phase 3 (US1 - KPIs)**:
- T011, T012 can run parallel with T009, T010 (connectors vs collections)
- T013, T014 can run in parallel (different test files)
- T015, T016 can run in parallel (UI components)
- T017, T018 can run in parallel (different hooks)

**Phase 4 (US2 - Search)**:
- T023-T026 must be sequential (service → API → tests)
- T027-T031 must be sequential (hook → UI integration)

**Phase 5 (US3 - Collapse)**:
- T032 can start immediately (new file, no dependencies)
- T033-T037 are sequential (modifying same files)

**User Stories Can Run in Parallel**:
- US1, US2, US3 can be worked on simultaneously by different developers
- US3 is frontend-only and has no backend dependencies

---

## Parallel Example: User Story 1

```bash
# Backend - can run in parallel:
Task T011: "Add get_connector_stats() method in backend/src/services/connector_service.py"
Task T012: "Add GET /connectors/stats endpoint in backend/src/api/connectors.py"

# Frontend - can run in parallel:
Task T015: "Create KpiCard component in frontend/src/components/ui/kpi-card.tsx"
Task T016: "Create KpiCardGrid component in frontend/src/components/ui/kpi-card.tsx"

# Tests - can run in parallel:
Task T013: "Add pytest tests for collection stats in backend/tests/unit/test_api_collections.py"
Task T014: "Add pytest tests for connector stats in backend/tests/unit/test_api_connectors.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (migration + model)
2. Complete Phase 2: Foundational (schemas + types)
3. Complete Phase 3: User Story 1 (KPIs)
4. **STOP and VALIDATE**: Verify KPIs display correctly
5. Deploy if ready

### Incremental Delivery

1. Setup + Foundational → Schema ready
2. Add User Story 1 → KPIs visible → Deploy (MVP!)
3. Add User Story 2 → Search works → Deploy
4. Add User Story 3 → Collapse works → Deploy
5. Each story adds value independently

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Backend + Frontend KPIs)
   - Developer B: User Story 2 (Backend + Frontend Search)
   - Developer C: User Story 3 (Frontend Collapse)
3. All stories complete independently, integrate at end

---

## Summary

| Phase | Task Count | Description |
|-------|------------|-------------|
| Setup | 3 | Migration + model changes |
| Foundational | 5 | Schemas + types |
| User Story 1 (KPIs) | 14 | Backend stats endpoints + frontend KPI cards |
| User Story 2 (Search) | 9 | Backend search param + frontend search input |
| User Story 3 (Collapse) | 7 | Frontend sidebar collapse/pin |
| Polish | 7 | Validation + cross-cutting |
| **Total** | **45** | |

---

## Notes

- [P] tasks = different files, no dependencies on each other
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Issue references: #37 (KPIs), #38 (Search), #41 (Collapse)
