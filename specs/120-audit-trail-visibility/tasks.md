# Tasks: Audit Trail Visibility

**Input**: Design documents from `/specs/120-audit-trail-visibility/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story. US2 (backend attribution) and US4 (API schemas) are foundational — they must complete before US1 (list views) and US3 (detail dialogs) can be implemented.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths included in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the AuditMixin, audit schemas, and database migration that all user stories depend on.

- [ ] T001 Create AuditMixin class in backend/src/models/mixins/audit.py with created_by_user_id and updated_by_user_id columns (Integer FK to users.id, nullable, SET NULL on delete, indexed) and created_by_user/updated_by_user relationships (lazy="joined" to User, foreign_keys specified)
- [ ] T002 Create AuditInfo and AuditUserSummary Pydantic schemas in backend/src/schemas/audit.py with from_attributes=True config; AuditUserSummary has guid/display_name/email fields; AuditInfo has created_at/created_by/updated_at/updated_by fields
- [ ] T003 Create Alembic migration backend/src/db/migrations/versions/058_add_audit_user_columns.py — add created_by_user_id + updated_by_user_id to 14 Group A tables (collections, connectors, pipelines, jobs, analysis_results, events, event_series, categories, locations, organizers, performers, configurations, push_subscriptions, notifications) and updated_by_user_id only to 3 Group B tables (agents, api_tokens, agent_registration_tokens); add indexes for all columns; use dialect-aware code for PostgreSQL CONCURRENTLY on large tables vs SQLite standard indexes
- [ ] T004 [P] Create AuditInfo and AuditUserSummary TypeScript types in frontend/src/contracts/api/audit-api.ts matching the backend schema (guid, display_name, email for user summary; created_at, created_by, updated_at, updated_by for audit info)

### Tests — Verify AuditMixin and audit schemas (NFR-400.1, NFR-400.3)

- [ ] T004a Create backend/tests/unit/test_audit_mixin.py with tests for: AuditMixin columns exist on a model (created_by_user_id, updated_by_user_id); FK constraint targets users table; SET NULL behavior when referenced user is deleted; columns are nullable (historical data compatibility); lazy="joined" relationships resolve to User instances
- [ ] T004b [P] Create backend/tests/unit/test_audit_schemas.py with tests for: AuditUserSummary serialization from User model (guid, display_name, email); AuditInfo serialization with full data (both users present); AuditInfo serialization with null users (historical records); AuditInfo with mixed null (created_by present, updated_by null); the build_audit_info helper function from T049 returns correct AuditInfo from a model instance

**Checkpoint**: AuditMixin, schemas, migration, frontend types, and foundational tests are ready. No models or services modified yet.

---

## Phase 2: User Story 2 — Track User Attribution on Record Changes (Priority: P1) 🎯 Foundational

**Goal**: Every create and update operation on tenant-scoped entities records the acting user. This is the backend data foundation that all other stories depend on.

**Independent Test**: Create or update a record via API and verify the database stores the acting user's ID in created_by_user_id / updated_by_user_id.

### Models — Apply AuditMixin to Group A entities (14 models)

- [ ] T005 [P] [US2] Add AuditMixin to Collection model class in backend/src/models/collection.py (add to class inheritance, import AuditMixin from mixins)
- [ ] T006 [P] [US2] Add AuditMixin to Connector model class in backend/src/models/connector.py
- [ ] T007 [P] [US2] Add AuditMixin to Pipeline model class in backend/src/models/pipeline.py
- [ ] T008 [P] [US2] Add AuditMixin to Job model class in backend/src/models/job.py
- [ ] T009 [P] [US2] Add AuditMixin to AnalysisResult model class in backend/src/models/analysis_result.py
- [ ] T010 [P] [US2] Add AuditMixin to Event model class in backend/src/models/event.py
- [ ] T011 [P] [US2] Add AuditMixin to EventSeries model class in backend/src/models/event_series.py
- [ ] T012 [P] [US2] Add AuditMixin to Category model class in backend/src/models/category.py
- [ ] T013 [P] [US2] Add AuditMixin to Location model class in backend/src/models/location.py
- [ ] T014 [P] [US2] Add AuditMixin to Organizer model class in backend/src/models/organizer.py
- [ ] T015 [P] [US2] Add AuditMixin to Performer model class in backend/src/models/performer.py
- [ ] T016 [P] [US2] Add AuditMixin to Configuration model class in backend/src/models/configuration.py
- [ ] T017 [P] [US2] Add AuditMixin to PushSubscription model class in backend/src/models/push_subscription.py
- [ ] T018 [P] [US2] Add AuditMixin to Notification model class in backend/src/models/notification.py

### Models — Add updated_by_user_id to Group B entities (3 models)

- [ ] T019 [P] [US2] Add updated_by_user_id column (Integer FK to users.id, nullable, SET NULL) and updated_by_user relationship (lazy="joined") to Agent model in backend/src/models/agent.py — do NOT use AuditMixin since it already has created_by_user_id with a different relationship name (created_by)
- [ ] T020 [P] [US2] Add updated_by_user_id column and updated_by_user relationship to ApiToken model in backend/src/models/api_token.py — same pattern as T019
- [ ] T021 [P] [US2] Add updated_by_user_id column and updated_by_user relationship to AgentRegistrationToken model in backend/src/models/agent_registration_token.py — same pattern as T019

### Services — Add user_id parameter to create/update methods

- [ ] T022 [US2] Add user_id: Optional[int] = None parameter to CollectionService.create_collection() and update_collection() in backend/src/services/collection_service.py — set created_by_user_id and updated_by_user_id on create; set updated_by_user_id on update
- [ ] T023 [P] [US2] Add user_id parameter to ConnectorService.create_connector() and update_connector() in backend/src/services/connector_service.py — same pattern as T022
- [ ] T024 [P] [US2] Add user_id parameter to PipelineService.create(), update(), activate(), deactivate(), set_default() in backend/src/services/pipeline_service.py — same pattern
- [ ] T025 [P] [US2] Add user_id parameter to EventService.create(), create_series(), update(), update_series(), soft_delete(), restore() in backend/src/services/event_service.py — same pattern
- [ ] T026 [P] [US2] Add user_id parameter to CategoryService.create() and update() in backend/src/services/category_service.py — same pattern
- [ ] T027 [P] [US2] Add user_id parameter to LocationService.create() and update() in backend/src/services/location_service.py — same pattern
- [ ] T028 [P] [US2] Add user_id parameter to OrganizerService.create() and update() in backend/src/services/organizer_service.py — same pattern
- [ ] T029 [P] [US2] Add user_id parameter to PerformerService.create() and update() in backend/src/services/performer_service.py — same pattern
- [ ] T030 [P] [US2] Add user_id parameter to ResultService.create_result() and update_result() in backend/src/services/result_service.py — same pattern
- [ ] T031 [P] [US2] Add user_id parameter to JobCoordinatorService.create_job() and relevant state-change methods in backend/src/services/job_coordinator_service.py — same pattern
- [ ] T032 [P] [US2] Add user_id parameter to NotificationService.create_notification() in backend/src/services/notification_service.py — set created_by_user_id and updated_by_user_id
- [ ] T033 [P] [US2] Add user_id parameter to ConfigService create/update methods in backend/src/services/config_service.py — same pattern

### Route Handlers — Pass ctx.user_id to service methods

- [ ] T034 [US2] Update collection route handlers in backend/src/api/collections.py to pass user_id=ctx.user_id to all CollectionService create/update calls
- [ ] T035 [P] [US2] Update connector route handlers in backend/src/api/connectors.py to pass user_id=ctx.user_id to all ConnectorService create/update calls
- [ ] T036 [P] [US2] Update pipeline route handlers in backend/src/api/pipelines.py to pass user_id=ctx.user_id to all PipelineService create/update calls
- [ ] T037 [P] [US2] Update event route handlers in backend/src/api/events.py to pass user_id=ctx.user_id to all EventService create/update calls
- [ ] T038 [P] [US2] Update category route handlers in backend/src/api/categories.py to pass user_id=ctx.user_id
- [ ] T039 [P] [US2] Update location route handlers in backend/src/api/locations.py to pass user_id=ctx.user_id
- [ ] T040 [P] [US2] Update organizer route handlers in backend/src/api/organizers.py to pass user_id=ctx.user_id
- [ ] T041 [P] [US2] Update performer route handlers in backend/src/api/performers.py to pass user_id=ctx.user_id
- [ ] T042 [P] [US2] Update result route handlers in backend/src/api/results.py to pass user_id=ctx.user_id
- [ ] T043 [P] [US2] Update tool/job route handlers in backend/src/api/tools.py to pass user_id=ctx.user_id to JobCoordinatorService calls
- [ ] T044 [P] [US2] Update notification route handlers in backend/src/api/notifications.py to pass user_id=ctx.user_id
- [ ] T045 [P] [US2] Update config route handlers in backend/src/api/config.py to pass user_id=ctx.user_id
- [ ] T046 [P] [US2] Update token route handlers in backend/src/api/tokens.py to pass user_id=ctx.user_id for token creation
- [ ] T047 [US2] Update agent-facing route handlers in backend/src/api/agent/routes.py to pass user_id=agent.system_user_id to service methods (job completion, result creation) — access agent.system_user_id from the authenticated agent object
- [ ] T048 [P] [US2] Update admin team/agent route handlers in backend/src/api/admin/teams.py to pass user_id=ctx.user_id for agent and token management

### Tests — Verify service user attribution (NFR-400.1, NFR-400.2)

- [ ] T048a [US2] Create backend/tests/unit/test_audit_attribution.py with tests covering: CollectionService sets created_by_user_id and updated_by_user_id on create; CollectionService updates updated_by_user_id on update while preserving created_by_user_id; at least 2 additional representative services (EventService, PipelineService) follow the same create/update/preserve pattern; service methods work correctly with user_id=None (backward compatibility, no crash); agent attribution via system_user_id is stored correctly

**Checkpoint**: All backend create/update operations now record the acting user, with test coverage for attribution logic. Verify by creating a record and checking the database columns directly.

---

## Phase 3: User Story 4 — Receive Audit Data in API Responses (Priority: P2) 🎯 API Layer

**Goal**: All entity API responses include the structured `audit` field with user attribution data. This is required before the frontend can display audit info.

**Independent Test**: Make a GET request to any entity list/detail endpoint and verify the response includes the `audit` object with created_by/updated_by user summaries.

### Schema Updates — Add audit field to all entity response schemas

- [ ] T049 [US4] Add a helper function to build AuditInfo from a model instance in backend/src/schemas/audit.py — accepts a model with created_at, updated_at, created_by_user, updated_by_user attributes and returns an AuditInfo object; handle null users gracefully
- [ ] T050 [P] [US4] Add audit: Optional[AuditInfo] = None field to CollectionResponse in backend/src/schemas/collection.py and update the route handler or serialization to populate it using the helper from T049
- [ ] T051 [P] [US4] Add audit field to ConnectorResponse in backend/src/schemas/collection.py (connectors are in the same schema file) and populate it
- [ ] T052 [P] [US4] Add audit field to PipelineResponse and related schemas in backend/src/schemas/pipelines.py
- [ ] T053 [P] [US4] Add audit field to JobResponse and related schemas in backend/src/schemas/tools.py
- [ ] T054 [P] [US4] Add audit field to AnalysisResultSummary and AnalysisResultResponse in backend/src/schemas/results.py
- [ ] T055 [P] [US4] Add audit field to EventResponse and EventDetailResponse in backend/src/schemas/event.py
- [ ] T056 [P] [US4] Add audit field to EventSeriesResponse in backend/src/schemas/event_series.py
- [ ] T057 [P] [US4] Add audit field to CategoryResponse in backend/src/schemas/category.py
- [ ] T058 [P] [US4] Add audit field to LocationResponse in backend/src/schemas/location.py
- [ ] T059 [P] [US4] Add audit field to OrganizerResponse in backend/src/schemas/organizer.py
- [ ] T060 [P] [US4] Add audit field to PerformerResponse in backend/src/schemas/performer.py
- [ ] T061 [P] [US4] Add audit field to NotificationResponse and PushSubscriptionResponse in backend/src/schemas/notifications.py
- [ ] T062 [P] [US4] Add audit field to ConfigurationResponse in backend/src/schemas/config.py
- [ ] T063 [P] [US4] Add audit field to AgentResponse, ApiTokenResponse, AgentRegistrationTokenResponse in backend/src/schemas/team.py (or wherever these response schemas live)
- [ ] T064 [US4] Export AuditInfo and AuditUserSummary from backend/src/schemas/__init__.py

### Tests — Verify audit field in API responses (NFR-400.3)

- [ ] T064a [US4] Create backend/tests/unit/test_audit_responses.py (or add to existing integration tests) with tests covering: entity API response includes audit field with created_by/updated_by user summaries (test at least CollectionResponse and one other); historical entity response has audit.created_by = null and audit.updated_by = null without error; audit field coexists with existing top-level created_at/updated_at fields (backward compatibility); AuditUserSummary contains guid (not internal id), display_name, and email

**Checkpoint**: All API responses now include the `audit` field with test coverage. Verify with curl/httpie requests to list and detail endpoints.

---

## Phase 4: User Story 1 — View Who Last Modified a Record in List Views (Priority: P1) 🎯 Primary Frontend

**Goal**: All 11 list views show a "Modified" column with relative time and a hover popover revealing full audit details (created by, modified by, timestamps).

**Independent Test**: Navigate to any list view page, verify the "Modified" column shows relative time, hover to see the popover with creator/modifier details.

### Frontend Components

- [ ] T065 [US1] Create AuditTrailPopover component in frontend/src/components/ui/audit-trail-popover.tsx — trigger shows formatRelativeTime(updated_at) with dotted underline; popover content shows created date/by and modified date/by; handle null users with "—"; skip modified section when created_at === updated_at; use Radix Popover from shadcn/ui
- [ ] T066 [US1] Create AuditTrailSection component (exported from same file frontend/src/components/ui/audit-trail-popover.tsx) — inline display for detail dialogs with border-t separator; shows created/modified rows with formatDateTime and user display_name || email; null users show "—"

### Tests — Verify frontend audit components (NFR-400.4)

- [ ] T066a [US1] Create frontend tests for AuditTrailPopover covering: renders relative time trigger text; popover displays created date/time and user display_name; popover displays modified date/time and user display_name; handles null created_by/updated_by by displaying "—"; hides modified section when created_at === updated_at (unmodified record); falls back to email when display_name is null
- [ ] T066b [P] [US1] Create frontend tests for AuditTrailSection covering: renders created and modified rows with full formatted timestamps; shows user display_name with fallback to email; handles null users by displaying "—"; handles same created_at/updated_at timestamps correctly

### Entity Type Updates — Add audit field to frontend API types

- [ ] T067 [P] [US1] Add audit?: AuditInfo | null field to Collection type in frontend/src/contracts/api/collection-api.ts (import AuditInfo from audit-api.ts)
- [ ] T068 [P] [US1] Add audit field to Connector type in frontend/src/contracts/api/collection-api.ts (or wherever ConnectorResponse type is defined)
- [ ] T069 [P] [US1] Add audit field to Pipeline type in the relevant contract file
- [ ] T070 [P] [US1] Add audit field to Job type in the relevant contract file
- [ ] T071 [P] [US1] Add audit field to AnalysisResult type in the relevant contract file
- [ ] T072 [P] [US1] Add audit field to Event and EventDetail types in frontend/src/contracts/api/event-api.ts
- [ ] T073 [P] [US1] Add audit field to EventSeries type in the relevant contract file
- [ ] T074 [P] [US1] Add audit field to Category, Location, Organizer, Performer types in their respective contract files
- [ ] T075 [P] [US1] Add audit field to Notification, PushSubscription types in the relevant contract file
- [ ] T076 [P] [US1] Add audit field to Agent, ApiToken, AgentRegistrationToken types in the relevant contract files

### List View Integration — Add/replace Modified column in all 11 list views

- [ ] T077 [US1] Add "Modified" column to CollectionList in frontend/src/components/collections/CollectionList.tsx — position before Actions column; cell renders AuditTrailPopover if item.audit exists, fallback to formatRelativeTime(item.updated_at); cardRole='detail'
- [ ] T078 [P] [US1] Replace "Created" column with "Modified" column in ConnectorList in frontend/src/components/connectors/ConnectorList.tsx — same pattern as T077
- [ ] T079 [P] [US1] Add "Modified" column to ResultsTable in frontend/src/components/results/ResultsTable.tsx — same pattern
- [ ] T080 [P] [US1] Replace "Created" column with "Modified" column in LocationsTab in frontend/src/components/settings/LocationsTab.tsx — same pattern
- [ ] T081 [P] [US1] Replace "Created" column with "Modified" column in OrganizersTab in frontend/src/components/settings/OrganizersTab.tsx — same pattern
- [ ] T082 [P] [US1] Replace "Created" column with "Modified" column in PerformersTab in frontend/src/components/settings/PerformersTab.tsx — same pattern
- [ ] T083 [P] [US1] Add "Modified" column to AgentsPage in frontend/src/pages/AgentsPage.tsx — same pattern
- [ ] T084 [P] [US1] Replace "Created" column with "Modified" column in CategoriesTab in frontend/src/components/settings/CategoriesTab.tsx — same pattern
- [ ] T085 [P] [US1] Replace "Created" column with "Modified" column in TokensTab in frontend/src/components/admin/TokensTab.tsx — same pattern
- [ ] T086 [P] [US1] Add "Modified" column to TeamsTab in frontend/src/components/admin/TeamsTab.tsx — same pattern
- [ ] T087 [P] [US1] Add "Modified" column to ReleaseManifestsTab in frontend/src/components/admin/ReleaseManifestsTab.tsx — same pattern

**Checkpoint**: All 11 list views show the "Modified" column with hover popover. Historical records show "—" for attribution.

---

## Phase 5: User Story 3 — View Full Audit Details in Detail Views (Priority: P2)

**Goal**: All detail dialogs show an audit trail section at the bottom with created/modified timestamps and user names inline.

**Independent Test**: Open any record's detail dialog, verify the bottom section shows "Created [date] by [user]" and "Modified [date] by [user]".

- [ ] T088 [US3] Add AuditTrailSection to AgentDetailsDialog in frontend/src/components/agents/AgentDetailsDialog.tsx — render at the bottom of the dialog content, passing the agent's audit data; conditionally render only when audit data exists
- [ ] T089 [P] [US3] Add AuditTrailSection to NotificationDetailDialog in frontend/src/components/notifications/NotificationDetailDialog.tsx — same pattern as T088

**Checkpoint**: Detail dialogs show complete audit trail inline. All user stories are functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Run full test suites (including new audit tests from T004a/T004b/T048a/T064a/T066a/T066b), verify builds, and validate migration.

- [ ] T090 Run full backend test suite (python3 -m pytest backend/tests/ -v) including new audit tests (test_audit_mixin.py, test_audit_schemas.py, test_audit_attribution.py, test_audit_responses.py) and fix any failures caused by the new user_id parameters or AuditMixin additions — service tests may need updated fixtures/mocks for the new parameter
- [ ] T091 Run frontend build and tests (npm run build && npm run test in frontend/) to verify TypeScript compilation succeeds and all frontend audit component tests (T066a/T066b) pass
- [ ] T092 Verify the Alembic migration applies cleanly by running it against a test database and checking all 17 tables have the expected columns and indexes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (US2 — Backend Attribution)**: Depends on Phase 1 (AuditMixin, migration)
- **Phase 3 (US4 — API Schemas)**: Depends on Phase 2 (models must have audit columns/relationships)
- **Phase 4 (US1 — List Views)**: Depends on Phase 3 (API must return audit field) and Phase 1 (frontend types)
- **Phase 5 (US3 — Detail Dialogs)**: Depends on Phase 4 (AuditTrailSection component created in Phase 4)
- **Phase 6 (Polish)**: Depends on all previous phases

### User Story Dependencies

```
Phase 1 (Setup: Mixin + Schema + Migration + TS Types + Mixin/Schema Tests)
    │
    ▼
Phase 2 (US2: Models + Services + Routes + Attribution Tests)  ← Backend attribution
    │
    ▼
Phase 3 (US4: Response schema integration + Response Tests) ← API audit field
    │
    ▼
Phase 4 (US1: Frontend components + Component Tests + 11 list views) ← UI display
    │
    ▼
Phase 5 (US3: Detail dialogs) ← Audit section in dialogs
    │
    ▼
Phase 6 (Polish: Full test suite + Build + Migration verify)
```

### Within Each Phase

- Phase 1: T004a/T004b (audit mixin/schema tests) can run in parallel [P] after T001-T003
- Models (T005-T021) can all run in parallel [P]
- Services (T022-T033) can run in parallel [P] after models
- Route handlers (T034-T048) can run in parallel [P] after their corresponding service
- Phase 2 test: T048a (attribution tests) runs after services and routes are complete
- Schema updates (T050-T063) can all run in parallel [P] after T049
- Phase 3 test: T064a (response tests) runs after schema updates are complete
- Frontend type updates (T067-T076) can all run in parallel [P]
- Frontend tests: T066a/T066b can run in parallel [P] after T065-T066
- List view updates (T077-T087) can all run in parallel [P] after T065

### Parallel Opportunities

Within Phase 2, the 14 model updates (T005-T018) can all run simultaneously since they modify different files. Similarly, all 12 service updates (T022-T033) are on different files and can run in parallel. Route handler updates (T034-T048) are also independent.

Within Phase 4, all 11 list view updates (T077-T087) can run in parallel after the AuditTrailPopover component (T065) is created.

---

## Parallel Example: Phase 2 Model Updates

```bash
# All 14 Group A model updates in parallel:
T005: Add AuditMixin to Collection in backend/src/models/collection.py
T006: Add AuditMixin to Connector in backend/src/models/connector.py
T007: Add AuditMixin to Pipeline in backend/src/models/pipeline.py
T008: Add AuditMixin to Job in backend/src/models/job.py
T009: Add AuditMixin to AnalysisResult in backend/src/models/analysis_result.py
T010: Add AuditMixin to Event in backend/src/models/event.py
T011: Add AuditMixin to EventSeries in backend/src/models/event_series.py
T012: Add AuditMixin to Category in backend/src/models/category.py
T013: Add AuditMixin to Location in backend/src/models/location.py
T014: Add AuditMixin to Organizer in backend/src/models/organizer.py
T015: Add AuditMixin to Performer in backend/src/models/performer.py
T016: Add AuditMixin to Configuration in backend/src/models/configuration.py
T017: Add AuditMixin to PushSubscription in backend/src/models/push_subscription.py
T018: Add AuditMixin to Notification in backend/src/models/notification.py
# Plus 3 Group B updates:
T019: Add updated_by_user_id to Agent in backend/src/models/agent.py
T020: Add updated_by_user_id to ApiToken in backend/src/models/api_token.py
T021: Add updated_by_user_id to AgentRegistrationToken in backend/src/models/agent_registration_token.py
```

---

## Implementation Strategy

### MVP First (Phases 1-3)

1. Complete Phase 1: Setup (AuditMixin, schemas, migration, types, mixin/schema tests)
2. Complete Phase 2: US2 (models, services, routes, attribution tests — backend attribution works)
3. Complete Phase 3: US4 (API responses include audit field, response tests)
4. **STOP and VALIDATE**: API returns audit data for all entities. Backend tests pass.
5. Backend is complete — can be deployed independently

### Full Delivery (Phases 4-6)

6. Complete Phase 4: US1 (frontend components, component tests, 11 list views)
7. Complete Phase 5: US3 (detail dialog audit sections)
8. Complete Phase 6: Polish (full test suite, build, migration verify)
9. **VALIDATE**: All 11 list views + all dialogs show audit info. All tests pass.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [US*] labels map tasks to user stories from spec.md
- Backend (US2 + US4) must complete before frontend (US1 + US3)
- The AuditMixin handles Group A entities; Group B entities get manual column/relationship additions
- Service method signatures use Optional[int] = None for backward compatibility
- Frontend falls back gracefully when audit field is missing (transitional state)
