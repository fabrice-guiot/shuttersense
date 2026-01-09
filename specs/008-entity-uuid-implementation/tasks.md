# Tasks: Entity UUID Implementation

**Input**: Design documents from `/specs/008-entity-uuid-implementation/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are included as they were planned in the Constitution Check (Testing & Quality).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/src/`, `backend/tests/`
- **Frontend**: `frontend/src/`, `frontend/tests/`
- **Migrations**: `backend/alembic/versions/`

---

## Phase 1: Setup (Dependencies & Configuration)

**Purpose**: Install dependencies and configure project for UUID support

- [x] T001 Add `uuid7` and `base32-crockford` to backend/requirements.txt
- [x] T002 [P] Create mixins directory at backend/src/models/mixins/__init__.py
- [x] T003 [P] Create utils directory at frontend/src/utils/ (if not exists)

---

## Phase 2: Foundational (Core UUID Infrastructure)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Backend Core

- [ ] T004 Implement ExternalIdMixin class in backend/src/models/mixins/external_id.py
- [ ] T005 Implement ExternalIdService with generation/encoding logic in backend/src/services/external_id.py
- [ ] T006 [P] Create Pydantic schemas for external ID validation in backend/src/schemas/external_id.py
- [ ] T007 [P] Write unit tests for ExternalIdService in backend/tests/unit/test_external_id_service.py

### Model Updates (add UUID column to each entity)

- [ ] T008 [P] Add ExternalIdMixin to Collection model in backend/src/models/collection.py
- [ ] T009 [P] Add ExternalIdMixin to Connector model in backend/src/models/connector.py
- [ ] T010 [P] Add ExternalIdMixin to Pipeline model in backend/src/models/pipeline.py
- [ ] T011 [P] Add ExternalIdMixin to AnalysisResult model in backend/src/models/analysis_result.py

### Database Migration

- [ ] T012 Create Alembic migration to add nullable UUID columns to all entities in backend/alembic/versions/
- [ ] T013 Add UUID population logic to migration: generate UUIDv7 for all existing records in backend/alembic/versions/
- [ ] T014 Update migration to make UUID columns non-nullable and create unique indexes in backend/alembic/versions/
- [ ] T015 Write migration tests to verify zero data loss in backend/tests/integration/test_external_id_migration.py

### Schema Updates (add external_id to response schemas)

- [ ] T016 [P] Add external_id field to CollectionResponse in backend/src/schemas/collection.py
- [ ] T017 [P] Add external_id field to ConnectorResponse in backend/src/schemas/collection.py
- [ ] T018 [P] Add external_id field to PipelineResponse in backend/src/schemas/pipelines.py
- [ ] T019 [P] Add external_id field to AnalysisResultResponse in backend/src/schemas/results.py

### Frontend Core

- [ ] T020 Create external ID utilities in frontend/src/utils/externalId.ts
- [ ] T021 [P] Write tests for external ID utilities in frontend/src/utils/externalId.test.ts
- [ ] T022 [P] Add external_id field to Collection type in frontend/src/types/collection.ts
- [ ] T023 [P] Add external_id field to Connector type in frontend/src/types/connector.ts
- [ ] T024 [P] Add external_id field to Pipeline type in frontend/src/contracts/api/pipelines-api.ts

**Checkpoint**: Foundation ready - UUID columns exist, external_id in all responses - user story implementation can now begin

---

## Phase 3: User Story 1 - Access Entity via External ID (Priority: P1) 🎯 MVP

**Goal**: Users can access any entity using external ID in URLs (bookmarking, sharing)

**Independent Test**: Navigate to `/collections/col_xxx` and verify the correct collection loads

### Tests for User Story 1

- [ ] T025 [P] [US1] Write API tests for GET /collections/{external_id} in backend/tests/unit/test_api_external_ids.py
- [ ] T026 [P] [US1] Write API tests for GET /connectors/{external_id} in backend/tests/unit/test_api_external_ids.py
- [ ] T027 [P] [US1] Write API tests for GET /pipelines/{external_id} in backend/tests/unit/test_api_external_ids.py

### Implementation for User Story 1

- [ ] T028 [US1] Add identifier parsing helper (numeric vs external) in backend/src/services/external_id.py
- [ ] T029 [US1] Update CollectionService.get_by_identifier() to support external IDs in backend/src/services/collection_service.py
- [ ] T030 [P] [US1] Update ConnectorService.get_by_identifier() to support external IDs in backend/src/services/connector_service.py
- [ ] T031 [P] [US1] Update PipelineService.get_by_identifier() to support external IDs in backend/src/services/pipeline_service.py
- [ ] T032 [US1] Update GET /collections/{id} endpoint to accept external IDs in backend/src/api/collections.py
- [ ] T033 [P] [US1] Update GET /connectors/{id} endpoint to accept external IDs in backend/src/api/connectors.py
- [ ] T034 [P] [US1] Update GET /pipelines/{id} endpoint to accept external IDs in backend/src/api/pipelines.py
- [ ] T035 [US1] Add error handling for invalid external ID format (400 response) in backend/src/api/collections.py
- [ ] T036 [US1] Add error handling for prefix mismatch (e.g., con_ at /collections/) in backend/src/services/external_id.py

**Checkpoint**: User Story 1 complete - entities accessible via external ID URLs

---

## Phase 4: User Story 2 - API External ID Support (Priority: P1)

**Goal**: All API responses include external IDs, create operations return them

**Independent Test**: Call `GET /api/collections` and verify each entity has `external_id` field

### Tests for User Story 2

- [ ] T037 [P] [US2] Write test for external_id in list responses in backend/tests/unit/test_api_external_ids.py
- [ ] T038 [P] [US2] Write test for external_id in create responses in backend/tests/unit/test_api_external_ids.py

### Implementation for User Story 2

- [ ] T039 [US2] Verify list endpoints return external_id (should work via schema update) in backend/src/api/collections.py
- [ ] T040 [US2] Verify create endpoints return external_id in response in backend/src/api/collections.py
- [ ] T041 [P] [US2] Update frontend API services to expect external_id in responses in frontend/src/services/collections.ts
- [ ] T042 [P] [US2] Update frontend hooks to handle external_id in frontend/src/hooks/useCollections.ts

**Checkpoint**: User Story 2 complete - all API responses include external_id

---

## Phase 5: User Story 3 - Display External ID in UI (Priority: P2)

**Goal**: Users can see and copy external IDs from entity detail pages

**Independent Test**: Open collection detail page, verify external ID displayed with copy button

### Tests for User Story 3

- [ ] T043 [P] [US3] Write test for ExternalIdBadge component in frontend/src/components/ExternalIdBadge.test.tsx

### Implementation for User Story 3

- [ ] T044 [US3] Create useClipboard hook for copy functionality in frontend/src/hooks/useClipboard.ts
- [ ] T045 [US3] Create ExternalIdBadge component with copy button in frontend/src/components/ExternalIdBadge.tsx
- [ ] T046 [US3] Add ExternalIdBadge to Collection detail/dialog in frontend/src/pages/CollectionsPage.tsx
- [ ] T047 [P] [US3] Add ExternalIdBadge to Connector detail/dialog in frontend/src/pages/ConnectorsPage.tsx
- [ ] T048 [P] [US3] Add ExternalIdBadge to Pipeline detail view in frontend/src/pages/PipelineEditorPage.tsx
- [ ] T049 [US3] Add visual feedback for copy action (toast/tooltip) in frontend/src/components/ExternalIdBadge.tsx

**Checkpoint**: User Story 3 complete - external IDs visible and copyable in UI

---

## Phase 6: User Story 4 - Backward Compatibility (Priority: P2)

**Goal**: Existing numeric ID URLs and API calls continue to work

**Independent Test**: Access `/collections/5` (numeric) and verify it works or redirects

### Tests for User Story 4

- [ ] T050 [P] [US4] Write test for numeric ID backward compatibility in backend/tests/unit/test_api_external_ids.py
- [ ] T051 [P] [US4] Write test for deprecation warning header in backend/tests/unit/test_api_external_ids.py

### Implementation for User Story 4

- [ ] T052 [US4] Verify numeric IDs still work in GET endpoints (should already work from T028-T034)
- [ ] T053 [US4] Add X-Deprecation-Warning header for numeric ID requests in backend/src/api/collections.py
- [ ] T054 [P] [US4] Add X-Deprecation-Warning header to connector endpoints in backend/src/api/connectors.py
- [ ] T055 [P] [US4] Add X-Deprecation-Warning header to pipeline endpoints in backend/src/api/pipelines.py
- [ ] T056 [US4] Update PUT/DELETE endpoints to accept external IDs in backend/src/api/collections.py
- [ ] T057 [P] [US4] Update PUT/DELETE endpoints for connectors in backend/src/api/connectors.py
- [ ] T058 [P] [US4] Update PUT/DELETE endpoints for pipelines in backend/src/api/pipelines.py

**Checkpoint**: User Story 4 complete - backward compatibility maintained with deprecation warnings

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements affecting multiple user stories

- [ ] T059 [P] Update frontend routes to prefer external IDs in URLs in frontend/src/App.tsx
- [ ] T060 [P] Add structured logging for external ID operations in backend/src/services/external_id.py
- [ ] T061 Run all tests and fix any failures
- [ ] T062 [P] Update API documentation in OpenAPI spec to reflect external ID support
- [ ] T063 Run quickstart.md validation scenarios
- [ ] T064 Performance test: verify external ID lookups are within 10% of numeric ID lookups

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 and US2 are both P1 priority but can be done in parallel
  - US3 and US4 are P2 priority and can be done after US1/US2 or in parallel
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Phase 2 - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Phase 2 - No dependencies on other stories
- **User Story 3 (P2)**: Can start after Phase 2 - Requires external_id in API responses (US2 helpful but not blocking)
- **User Story 4 (P2)**: Can start after Phase 2 - Builds on US1 API endpoint changes

### Within Each User Story

- Tests written first (if included)
- Service layer before API endpoints
- Backend before frontend (for data availability)
- Core implementation before error handling refinements

### Parallel Opportunities

**Phase 2 (Foundational)**:
```
# These can run in parallel (different files):
T006, T007 (schema, tests)
T008, T009, T010, T011 (model updates - different files)
T016, T017, T018, T019 (schema updates - different files)
T020, T021, T022, T023, T024 (frontend - different files)
```

**Phase 3 (US1)**:
```
# Tests can run in parallel:
T025, T026, T027 (API tests - different endpoints)

# Service updates can run in parallel:
T030, T031 (after T029 pattern established)

# Endpoint updates can run in parallel:
T033, T034 (after T032 pattern established)
```

---

## Parallel Example: Phase 2 Foundational

```bash
# Launch model updates in parallel (different files):
Task: "Add ExternalIdMixin to Collection model in backend/src/models/collection.py"
Task: "Add ExternalIdMixin to Connector model in backend/src/models/connector.py"
Task: "Add ExternalIdMixin to Pipeline model in backend/src/models/pipeline.py"
Task: "Add ExternalIdMixin to AnalysisResult model in backend/src/models/analysis_result.py"

# Launch schema updates in parallel (different files):
Task: "Add external_id field to CollectionResponse in backend/src/schemas/collection.py"
Task: "Add external_id field to ConnectorResponse in backend/src/schemas/collection.py"
Task: "Add external_id field to PipelineResponse in backend/src/schemas/pipelines.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 & 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (URL access)
4. Complete Phase 4: User Story 2 (API responses)
5. **STOP and VALIDATE**: Test external ID access via URL and API
6. Deploy/demo if ready - core functionality complete

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 + 2 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 3 → Test independently → Deploy/Demo (UI polish)
4. Add User Story 4 → Test independently → Deploy/Demo (full backward compat)
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (backend focus)
   - Developer B: User Story 2 (API responses)
   - Developer C: User Story 3 (frontend focus)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- External ID format: `{prefix}_{crockford_base32_uuid}` (e.g., `col_01HGW2BBG...`)
- Entity prefixes: col (Collection), con (Connector), pip (Pipeline), res (AnalysisResult)
