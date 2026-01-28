# Tasks: Remove CLI Direct Usage

**Input**: Design documents from `/specs/108-remove-cli-direct-usage/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Included. The constitution requires "Testing & Quality" and the plan specifies unit + integration test files.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. US4 is ordered before US3 because US3's offline mode depends on the collection cache from US4.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Agent**: `agent/cli/`, `agent/src/`, `agent/tests/`
- **Backend**: `backend/src/api/agent/`, `backend/src/services/`
- **Docs**: `docs/`, `.specify/memory/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create cache module directory structure and extend agent config with cache paths.

- [ ] T001 Create cache module directory and init file at agent/src/cache/__init__.py
- [ ] T002 Add cache directory path constants (data_dir, test-cache, collection-cache, results) to agent/src/config.py using platformdirs.user_data_dir()
- [ ] T003 [P] Add Pydantic models for TestCacheEntry, CachedCollection, CollectionCache, and OfflineResult in agent/src/cache/__init__.py (shared types used across cache modules)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend schemas and API client methods that multiple user stories depend on.

**CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T004 Add AgentCreateCollectionRequest, AgentCreateCollectionResponse, AgentCollectionItem, AgentCollectionListResponse schemas to backend/src/api/agent/schemas.py
- [ ] T005 [P] Add AgentCollectionTestRequest, AgentCollectionTestResponse schemas to backend/src/api/agent/schemas.py
- [ ] T006 [P] Add AgentUploadResultRequest, AgentUploadResultResponse schemas to backend/src/api/agent/schemas.py
- [ ] T007 Add create_collection(), list_collections(), test_collection(), upload_result() method stubs to agent/src/api_client.py (raise NotImplementedError, filled in per story)

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Test Local Path Before Collection Creation (Priority: P0) MVP

**Goal**: Users can validate a local directory for accessibility and run analysis tools before creating a Collection. No server communication required.

**Independent Test**: Run `shuttersense-agent test /path/to/photos` against a directory with known files and verify output shows file counts and analysis results. Run with `--check-only` to verify accessibility-only mode. Run with `--output report.html` to verify HTML report generation.

### Implementation for User Story 1

- [ ] T008 [US1] Implement TestCacheEntry save/load/is_valid/cleanup methods in agent/src/cache/test_cache.py using Pydantic models from cache __init__ and JSON file storage at {data_dir}/test-cache/{path_hash}.json
- [ ] T009 [US1] Implement `test` Click command in agent/cli/test.py with <path> argument and --tool, --check-only, --output options. Command validates path accessibility, lists and categorizes files using LocalAdapter, optionally runs analysis modules (photostats, photo_pairing, pipeline_validation), displays summary, and caches results via test_cache
- [ ] T010 [US1] Register `test` command in agent/cli/main.py via cli.add_command(test)
- [ ] T011 [P] [US1] Write unit tests for test_cache save/load/expiry/cleanup in agent/tests/unit/test_test_cache.py
- [ ] T012 [P] [US1] Write unit tests for test CLI command (path validation, check-only mode, tool filter, output flag, error messages) in agent/tests/unit/test_test_command.py

**Checkpoint**: `shuttersense-agent test /path` works end-to-end. User can test local paths, see file counts and analysis results, save HTML reports, and results are cached for 24 hours.

---

## Phase 4: User Story 2 - Create Collection from Tested Path (Priority: P0)

**Goal**: Users can create a server-side Collection from a local path that was previously tested. Collection is automatically bound to the creating agent.

**Independent Test**: Run `shuttersense-agent test /path/to/photos` then `shuttersense-agent collection create /path/to/photos --name "Test"`. Verify Collection appears on the server with correct name, type=LOCAL, and bound_agent.

### Implementation for User Story 2

- [ ] T013 [US2] Add agent_create_collection() method to backend/src/services/collection_service.py that accepts agent_id, team_id, name, location, and optional test_results. Creates Collection with type=LOCAL, bound_agent_id=agent, team_id from agent context
- [ ] T014 [US2] Add POST /api/agent/v1/collections endpoint in backend/src/api/agent/routes.py. Authenticate agent, resolve team_id, call collection_service.agent_create_collection(), return GUID and web_url. Handle 409 if path already registered
- [ ] T015 [US2] Implement create_collection() method body in agent/src/api_client.py to call POST /api/agent/v1/collections with name, location, and optional test_results
- [ ] T016 [US2] Implement `collection` Click group and `create` subcommand in agent/cli/collection.py with <path> argument and --name, --skip-test, --analyze options. Load test cache, auto-run test if no valid cache (unless --skip-test), prompt for name if not provided (suggest folder name), call API client, display GUID and web URL. If --analyze, create job via existing API
- [ ] T017 [US2] Register `collection` group in agent/cli/main.py via cli.add_command(collection)
- [ ] T018 [P] [US2] Write unit tests for collection create CLI command (cache lookup, auto-test, name prompt, skip-test, analyze flag) in agent/tests/unit/test_collection_command.py
- [ ] T019 [P] [US2] Write unit tests for agent collection creation endpoint (auth, team scoping, duplicate path 409, bound agent) in backend/tests/test_agent_collection_api.py

**Checkpoint**: `shuttersense-agent collection create /path --name "Name"` creates a Collection on the server. Test-then-create workflow works end-to-end.

---

## Phase 5: User Story 4 - List and Manage Bound Collections (Priority: P1)

**Goal**: Users can list Collections bound to their agent, refresh the local cache, and re-test Collection accessibility. Supports offline listing via cached data.

**Note**: Ordered before US3 because US3's offline mode depends on the collection cache implemented here.

**Independent Test**: Run `shuttersense-agent collection list` and verify all bound Collections appear in tabular format with correct metadata. Run `shuttersense-agent collection list --offline` to verify cached data. Run `shuttersense-agent collection sync` to verify cache refresh. Run `shuttersense-agent collection test <guid>` to verify accessibility update.

### Implementation for User Story 4

- [ ] T020 [US4] Implement CollectionCache save/load/is_valid/is_expired methods in agent/src/cache/collection_cache.py using Pydantic models from cache __init__ and JSON file storage at {data_dir}/collection-cache.json with 7-day TTL
- [ ] T021 [US4] Add GET /api/agent/v1/collections endpoint in backend/src/api/agent/routes.py. Authenticate agent, return all Collections where bound_agent_id matches or agent has connector credentials. Support ?type and ?status query filters
- [ ] T022 [US4] Add POST /api/agent/v1/collections/{guid}/test endpoint in backend/src/api/agent/routes.py. Authenticate agent, verify Collection is bound to this agent, update is_accessible and last_error fields
- [ ] T023 [US4] Implement list_collections() method body in agent/src/api_client.py to call GET /api/agent/v1/collections with optional type/status filters
- [ ] T024 [US4] Implement test_collection() method body in agent/src/api_client.py to call POST /api/agent/v1/collections/{guid}/test with accessibility result
- [ ] T025 [US4] Add `list` subcommand to collection group in agent/cli/collection.py with --type, --status, --offline options. Online mode: fetch from server and update cache. Offline mode: load from cache, show sync timestamp, warn if expired. Display tabular output with GUID, type, name, location, status, last analysis, offline capability
- [ ] T026 [US4] Add `sync` subcommand to collection group in agent/cli/collection.py. Fetch all bound Collections from server, update local cache, display summary
- [ ] T027 [US4] Add `test` subcommand to collection group in agent/cli/collection.py with <guid> argument. Check path accessibility via LocalAdapter, update status on server via API client, display result
- [ ] T028 [P] [US4] Write unit tests for collection_cache save/load/expiry/warning in agent/tests/unit/test_collection_cache.py
- [ ] T029 [P] [US4] Write unit tests for collection list/sync/test CLI commands (online mode, offline mode, type filter, stale cache warning) in agent/tests/unit/test_collection_command.py (extend existing file from US2)

**Checkpoint**: `shuttersense-agent collection list` shows all bound Collections. Cache sync and offline listing work. Accessibility re-test updates server status.

---

## Phase 6: User Story 3 - Run Analysis Offline and Sync Results Later (Priority: P1)

**Goal**: Users can run analysis tools against Collections identified by GUID. Online mode creates a server job; offline mode runs locally and stores results for later sync.

**Independent Test**: Run `shuttersense-agent run <guid> --tool photostats` in online mode and verify job appears on server. Run with `--offline` against a LOCAL collection and verify local result file created. Run `shuttersense-agent sync --dry-run` to verify pending results listed. Run `shuttersense-agent sync` to verify upload and cleanup.

### Implementation for User Story 3

- [ ] T030 [US3] Implement OfflineResult save/load/list_pending/mark_synced/delete methods in agent/src/cache/result_store.py using Pydantic models from cache __init__ and JSON file storage at {data_dir}/results/{result_id}.json
- [ ] T031 [US3] Add agent_upload_offline_result() method to backend/src/services/tool_service.py that creates both a Job record (status=COMPLETED) and an AnalysisResult in a single transaction. Set job timestamps from offline execution data, agent_id from agent context
- [ ] T032 [US3] Add POST /api/agent/v1/results/upload endpoint in backend/src/api/agent/routes.py. Authenticate agent, validate collection_guid belongs to agent, call tool_service.agent_upload_offline_result(), return job_guid and result_guid. Support idempotent upload via result_id (409 if already uploaded)
- [ ] T033 [US3] Implement upload_result() method body in agent/src/api_client.py to call POST /api/agent/v1/results/upload with OfflineResult data
- [ ] T034 [US3] Implement `run` Click command in agent/cli/run.py with <collection-guid> argument and --tool (required), --offline, --output options. Online mode: create job on server, execute locally using analysis modules and LocalAdapter (reuse patterns from job_executor.py), report results. Offline mode: load collection from cache, reject if remote type, execute locally, save OfflineResult via result_store
- [ ] T035 [US3] Implement `sync` Click command in agent/cli/sync_results.py with --dry-run option. Scan result_store for pending results, display list. If not dry-run: upload each result via API client, mark synced, delete local files. Handle partial failure with resume support
- [ ] T036 [US3] Register `run` and `sync` commands in agent/cli/main.py via cli.add_command()
- [ ] T037 [P] [US3] Write unit tests for result_store save/load/list_pending/mark_synced/delete in agent/tests/unit/test_result_store.py
- [ ] T038 [P] [US3] Write unit tests for run CLI command (online mode, offline mode, remote rejection, tool validation) in agent/tests/unit/test_run_command.py
- [ ] T039 [P] [US3] Write unit tests for sync CLI command (dry-run, upload, cleanup, partial failure resume) in agent/tests/unit/test_sync_command.py

**Checkpoint**: `shuttersense-agent run <guid> --tool photostats` works in both online and offline modes. `shuttersense-agent sync` uploads offline results. Results appear identically to online job results in the web UI.

---

## Phase 7: User Story 5 - Remove Standalone CLI Tools and Update Constitution (Priority: P2)

**Goal**: Remove standalone CLI tools from the repository, replace the "Independent CLI Tools" constitution principle with "Agent-Only Tool Execution", and update all documentation to reference agent-based workflows.

**Independent Test**: Verify deleted files no longer exist. Verify constitution reflects agent-only principles. Verify all documentation references agent commands. Verify analysis modules still work via agent (run existing agent tests).

### Implementation for User Story 5

- [ ] T040 [US5] Delete photo_stats.py from repository root
- [ ] T041 [P] [US5] Delete photo_pairing.py from repository root
- [ ] T042 [P] [US5] Delete pipeline_validation.py from repository root
- [ ] T043 [US5] Delete CLI-specific test files: tests/test_photo_stats.py and tests/test_photo_pairing.py (preserve agent/tests/ analysis module tests)
- [ ] T044 [US5] Update .specify/memory/constitution.md: Replace "I. Independent CLI Tools" principle with "I. Agent-Only Tool Execution" principle. New principle mandates all tool execution through authenticated agents, references agent/src/analysis/ as shared libraries, prohibits standalone execution scripts
- [ ] T045 [US5] Update CLAUDE.md: Remove CLI tool references from Project Structure, Running Tools, Commands sections. Replace with agent command examples. Update project structure to reflect agent-only architecture
- [ ] T046 [P] [US5] Update README.md: Remove CLI tool usage examples, add agent quick-start with test/create/run workflow
- [ ] T047 [P] [US5] Update docs/installation.md: Focus on agent binary installation only, remove standalone Python script setup
- [ ] T048 [P] [US5] Update docs/configuration.md: Remove CLI-specific YAML config sections, reference agent config
- [ ] T049 [P] [US5] Update docs/photostats.md: Add archive notice, redirect users to `shuttersense-agent test --tool photostats` and `shuttersense-agent run --tool photostats`
- [ ] T050 [P] [US5] Update docs/photo-pairing.md: Add archive notice, redirect users to `shuttersense-agent test --tool photo_pairing` and `shuttersense-agent run --tool photo_pairing`
- [ ] T051 [US5] Run existing agent analysis module tests (agent/tests/unit/test_photostats_analyzer.py, test_photo_pairing_analyzer.py, test_pipeline_analyzer.py) to verify shared modules still function after CLI tool removal

**Checkpoint**: CLI tools removed. Constitution updated. All documentation references agent commands. Analysis modules verified working via agent test suite.

---

## Phase 8: User Story 6 - Agent Self-Test Command (Priority: P2)

**Goal**: Users can verify their agent is correctly configured and can communicate with the server.

**Independent Test**: Run `shuttersense-agent self-test` on a correctly configured agent and verify all checks pass. Simulate failures (invalid API key, unreachable server, inaccessible root) and verify each produces the expected failure message with remediation advice.

### Implementation for User Story 6

- [ ] T052 [US6] Implement `self-test` Click command in agent/cli/self_test.py. Check: server connectivity (URL reachable, measure latency), agent registration (API key valid via heartbeat), tool availability (import each analysis module), authorized roots accessibility (check each configured root path). Display pass/fail/warn per check with formatted output. Include remediation suggestions for failures
- [ ] T053 [US6] Register `self-test` command in agent/cli/main.py via cli.add_command(self_test)
- [ ] T054 [P] [US6] Write unit tests for self-test command (all pass, connectivity failure, invalid API key, inaccessible root, warn summary) in agent/tests/unit/test_self_test.py

**Checkpoint**: `shuttersense-agent self-test` validates the full agent configuration with clear pass/fail/warn output and actionable remediation advice.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Integration tests, documentation consistency, and final validation.

- [ ] T055 [P] Write integration test for test-then-create workflow (test path → create collection → verify on server) in agent/tests/integration/test_test_create_flow.py
- [ ] T056 [P] Write integration test for offline-sync workflow (sync cache → run offline → sync results → verify on server) in agent/tests/integration/test_offline_sync_flow.py
- [ ] T057 Run all agent tests (pytest agent/tests/) to verify no regressions across all new and existing tests
- [ ] T058 Run all backend tests (pytest backend/tests/) to verify no regressions with new agent endpoints
- [ ] T059 Run quickstart.md validation: execute each verification command from quickstart.md and confirm expected output

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 - No dependencies on other stories
- **US2 (Phase 4)**: Depends on Phase 2 - Reads test cache from US1 (but auto-runs test if cache missing, so US1 is not a strict blocker)
- **US4 (Phase 5)**: Depends on Phase 2 - No dependencies on US1 or US2
- **US3 (Phase 6)**: Depends on Phase 2 + US4 (offline mode needs collection cache from US4)
- **US5 (Phase 7)**: Depends on US1, US2, US3, US4 being complete (all CLI replacements must exist before removal)
- **US6 (Phase 8)**: Depends on Phase 2 - No dependencies on other stories
- **Polish (Phase 9)**: Depends on all user stories being complete

### User Story Dependencies

```
Phase 1 (Setup)
    │
    ▼
Phase 2 (Foundational)
    │
    ├──────────┬──────────┬──────────┐
    ▼          ▼          ▼          ▼
  US1 (P0)  US2 (P0)  US4 (P1)  US6 (P2)
    │          │          │
    │          │          ▼
    │          │        US3 (P1)
    │          │          │
    ▼          ▼          ▼
    └──────────┴──────────┘
               │
               ▼
            US5 (P2)
               │
               ▼
         Phase 9 (Polish)
```

### Within Each User Story

- Cache/model modules before CLI commands
- API client methods before CLI commands that call them
- Backend endpoints before agent commands that call them
- CLI commands before unit tests (tests need implementation to mock)
- Core implementation before integration

### Parallel Opportunities

- T003 can run in parallel with T001/T002 (different files)
- T004, T005, T006 can all run in parallel (different schemas in same file but no conflicts)
- After Phase 2: US1, US2, US4, US6 can start in parallel (different files, no dependencies)
- Within US4: T028, T029 can run in parallel with each other (different test files)
- Within US3: T037, T038, T039 can run in parallel (different test files)
- Within US5: T040-T042 parallel (file deletions), T046-T050 parallel (doc updates)

---

## Parallel Example: User Story 1

```bash
# After T009 completes (test command implemented):
# Launch test tasks in parallel:
Task: "T011 - Write unit tests for test_cache in agent/tests/unit/test_test_cache.py"
Task: "T012 - Write unit tests for test command in agent/tests/unit/test_test_command.py"
```

## Parallel Example: User Story 5

```bash
# After T040-T043 completes (files deleted):
# Launch doc updates in parallel:
Task: "T046 - Update README.md"
Task: "T047 - Update docs/installation.md"
Task: "T048 - Update docs/configuration.md"
Task: "T049 - Update docs/photostats.md"
Task: "T050 - Update docs/photo-pairing.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T007)
3. Complete Phase 3: US1 - Test Command (T008-T012)
4. **STOP and VALIDATE**: Run `shuttersense-agent test /path/to/photos` and verify output
5. This delivers immediate value: users can validate paths without any server interaction

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. **US1**: Test command → Users can validate local paths (MVP!)
3. **US2**: Collection create → Users can create Collections from tested paths
4. **US4**: Collection management → Users can list, sync, and re-test Collections
5. **US3**: Run + sync → Users can run tools online/offline and sync results
6. **US5**: CLI removal → Production-ready security posture
7. **US6**: Self-test → Improved setup experience
8. Polish → Integration tests and final validation

### Parallel Team Strategy

With multiple developers after Phase 2 completes:
- **Developer A**: US1 (test command) → US3 (run + sync)
- **Developer B**: US2 (collection create) → US5 (CLI removal)
- **Developer C**: US4 (collection management) → US6 (self-test)

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks in same phase
- [Story] label maps task to specific user story for traceability
- US4 is ordered before US3 because US3 offline mode depends on collection cache from US4
- US5 (CLI removal) must be last functional phase since it removes the tools being replaced
- No new Python dependencies needed - all libraries already in agent/backend dependency trees
- Analysis modules in agent/src/analysis/ are NOT modified - they are consumed as-is
- Backend model changes are NOT needed - existing Collection, Job, AnalysisResult models have all required fields
