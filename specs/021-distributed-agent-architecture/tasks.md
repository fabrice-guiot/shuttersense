# Tasks: Distributed Agent Architecture

**Input**: Design documents from `/specs/021-distributed-agent-architecture/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required per constitution. Tests written alongside implementation per user story.

**Organization**: Tasks grouped by user story for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Exact file paths included in descriptions

## Path Conventions

- **Backend**: `backend/src/`, `backend/tests/`
- **Frontend**: `frontend/src/`, `frontend/tests/`
- **Agent**: `agent/src/`, `agent/cli/`, `agent/tests/`

---

## Phase 1: Setup (Shared Infrastructure) ✅

**Purpose**: Project initialization and database migrations

- [x] T001 Create `agent/` directory structure per plan.md project structure
- [x] T002 [P] Initialize agent Python package with `agent/pyproject.toml` and dependencies (httpx, websockets, pydantic, cryptography, click, pytest)
- [x] T003 [P] Create Alembic migration for Agent table in `backend/src/db/migrations/versions/032_create_agents_table.py`
- [x] T004 [P] Create Alembic migration for AgentRegistrationToken table in `backend/src/db/migrations/versions/033_create_agent_registration_tokens_table.py`
- [x] T005 [P] Create Alembic migration for Jobs table (persistent queue) in `backend/src/db/migrations/versions/034_create_jobs_table.py`
- [x] T006 [P] Create Alembic migration for Connector credential_location field in `backend/src/db/migrations/versions/035_add_connector_credential_location.py`
- [x] T007 [P] Create Alembic migration for Collection agent binding fields in `backend/src/db/migrations/versions/036_add_collection_agent_binding.py`
- [x] T008 [P] Create agent test configuration in `agent/tests/conftest.py` with pytest fixtures

**Checkpoint**: Database schema ready, agent package initialized with test infrastructure ✅

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Models

- [x] T009 Create Agent SQLAlchemy model in `backend/src/models/agent.py` with GuidMixin, AgentStatus enum
- [x] T010 [P] Create AgentRegistrationToken SQLAlchemy model in `backend/src/models/agent_registration_token.py` with GuidMixin
- [x] T011 Enhance Job model with agent routing fields in `backend/src/models/job.py` (bound_agent_id, agent_id, required_capabilities_json, scheduled_for, signing_secret_hash)
- [x] T012 Enhance JobStatus enum with SCHEDULED, ASSIGNED states in `backend/src/models/job.py`
- [x] T013 [P] Enhance Connector model with credential_location field in `backend/src/models/connector.py`
- [x] T014 [P] Enhance Collection model with agent binding fields in `backend/src/models/collection.py` (bound_agent_id, auto_refresh, refresh_interval_hours)

### Tests for Models

- [x] T015 [P] Unit tests for Agent model in `backend/tests/unit/models/test_agent.py` (GUID generation, status enum, validation)
- [x] T016 [P] Unit tests for AgentRegistrationToken model in `backend/tests/unit/models/test_agent_registration_token.py` (expiration, usage)
- [x] T017 [P] Unit tests for enhanced Job model in `backend/tests/unit/models/test_job_agent_fields.py` (new fields, status transitions)

### Core Services and API Infrastructure

- [x] T018 Create AgentService in `backend/src/services/agent_service.py` with registration, heartbeat, SYSTEM user creation
- [x] T019 [P] Add Agent Pydantic schemas in `backend/src/api/agent/schemas.py` (registration, heartbeat, responses)
- [x] T020 [P] Create agent API router mount in `backend/src/main.py` at `/api/agent/v1`
- [x] T021 Create agent authentication dependency in `backend/src/api/agent/dependencies.py` (API key validation from Bearer token)

### Tests for Core Services

- [x] T022 Unit tests for AgentService in `backend/tests/unit/test_agent_service.py` (registration, heartbeat, SYSTEM user creation, offline detection)
- [x] T023 [P] Unit tests for agent authentication dependency in `backend/tests/unit/test_agent_auth.py` (valid key, invalid key, revoked agent)

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 2 - Agent Registration and Setup (Priority: P0) ✅ MVP

**Goal**: Team administrators can register agents running on their local machines

**Independent Test**: Download agent binary, configure with server URL and registration token, verify agent appears in agent list UI

### Backend Tests for User Story 2

- [x] T024 [P] [US2] Unit tests for registration token service in `backend/tests/unit/services/test_registration_token.py` (creation, expiration, single-use)
- [x] T025 [P] [US2] Integration tests for POST `/api/agent/v1/register` in `backend/tests/integration/test_agent_registration.py` (success, invalid token, expired token)
- [x] T026 [P] [US2] Integration tests for POST `/api/agent/v1/heartbeat` in `backend/tests/integration/test_agent_heartbeat.py` (status update, capability refresh)
- [x] T027 [P] [US2] Integration tests for admin endpoints in `backend/tests/integration/test_agent_admin_api.py` (list, delete, rename, token generation)

### Backend Implementation for User Story 2

- [x] T028 [US2] Implement POST `/register` endpoint in `backend/src/api/agent/routes.py` (token validation, agent creation, SYSTEM user creation, API key generation)
- [x] T029 [US2] Implement POST `/heartbeat` endpoint in `backend/src/api/agent/routes.py` (status update, capability refresh)
- [x] T030 [US2] Implement token generation service method in `backend/src/services/agent_service.py` (create_registration_token)
- [x] T031 [US2] Create admin endpoint POST `/api/agents/tokens` in `backend/src/api/agents/routes.py` for token generation from UI
- [x] T032 [P] [US2] Create admin endpoint GET `/api/agents` in `backend/src/api/agents/routes.py` for agent list
- [x] T033 [P] [US2] Create admin endpoint DELETE `/api/agents/{guid}` in `backend/src/api/agents/routes.py` for agent deletion
- [x] T034 [P] [US2] Create admin endpoint PATCH `/api/agents/{guid}` in `backend/src/api/agents/routes.py` for agent rename

### Agent Tests for User Story 2

- [x] T035 [P] [US2] Unit tests for agent config module in `agent/tests/unit/test_config.py` (loading, saving, defaults)
- [x] T036 [P] [US2] Unit tests for agent API client in `agent/tests/unit/test_api_client.py` (register, heartbeat, error handling)
- [x] T037 [P] [US2] Unit tests for register CLI command in `agent/tests/unit/test_cli_register.py` (argument parsing, success flow, error handling)
- [x] T038 [US2] Integration tests for agent registration flow in `agent/tests/integration/test_registration.py` (end-to-end with mock server)

### Agent Implementation for User Story 2

- [x] T039 [US2] Create agent config module in `agent/src/config.py` (server URL, API key storage path, config file location)
- [x] T040 [US2] Create agent API client in `agent/src/api_client.py` (register, heartbeat methods)
- [x] T041 [US2] Create agent CLI entry point in `agent/cli/main.py` using click
- [x] T042 [US2] Implement `register` CLI command in `agent/cli/register.py` (--server, --token, --name flags)
- [x] T043 [US2] Implement agent main loop with heartbeat in `agent/src/main.py` (30-second heartbeat)

### Frontend Tests for User Story 2

- [x] T044 [P] [US2] Component tests for AgentListPage in `frontend/tests/components/agents/AgentsPage.test.tsx` (render, actions)
- [x] T045 [P] [US2] Component tests for RegistrationTokenDialog in `frontend/tests/components/agents/RegistrationTokenDialog.test.tsx` (generate, copy, close)
- [x] T046 [P] [US2] Component tests for AgentStatusBadge in `frontend/tests/components/agents/AgentStatusBadge.test.tsx` (all states)
- [x] T047 [P] [US2] Hook tests for useAgents in `frontend/tests/hooks/useAgents.test.ts` (fetch, error handling)

### Frontend Implementation for User Story 2

- [x] T048 [US2] Create AgentListPage component in `frontend/src/pages/AgentsPage.tsx` (agent list, status badges, delete/rename actions)
- [x] T049 [P] [US2] Create RegistrationTokenDialog component in `frontend/src/components/agents/RegistrationTokenDialog.tsx`
- [x] T050 [P] [US2] Create AgentStatusBadge component in `frontend/src/components/agents/AgentStatusBadge.tsx` (online/offline/error/revoked)
- [x] T051 [US2] Create useAgents hook in `frontend/src/hooks/useAgents.ts` for agent list fetching
- [x] T052 [US2] Add route for AgentsPage in `frontend/src/App.tsx` at `/agents` (NO sidebar entry per spec)

**Checkpoint**: Agents can register via CLI and appear in web UI ✅

---

## Phase 4: User Story 1 - Agent Pool Status in Header (Priority: P0) ✅

**Goal**: Users see agent pool status at a glance in top header, with real-time updates

**Independent Test**: Observe agent status icon in header, verify updates in real-time as agents come online/offline/start jobs

### Backend Tests for User Story 1

- [x] T053 [P] [US1] Unit tests for pool status service in `backend/tests/unit/services/test_agent_pool_service.py` (status calculation, broadcast triggers)
- [x] T054 [P] [US1] Integration tests for GET `/api/agent/v1/pool-status` in `backend/tests/integration/test_pool_status_api.py`
- [x] T055 [P] [US1] WebSocket tests for pool status broadcast in `backend/tests/integration/test_pool_status_ws.py` (connect, receive updates)

### Backend Implementation for User Story 1

- [x] T056 [US1] Create GET `/api/agent/v1/pool-status` endpoint in `backend/src/api/agent/routes.py` (online_count, idle_count, running_jobs_count)
- [x] T057 [US1] Create WebSocket handler for pool status at `/api/agent/v1/ws/pool-status` in `backend/src/api/agent/routes.py`
- [x] T058 [US1] Create pool status broadcast service in `backend/src/utils/websocket.py` (broadcast on status changes)
- [x] T059 [US1] Trigger pool status broadcast from heartbeat endpoint in `backend/src/api/agent/routes.py`
- [x] T060 [US1] Trigger pool status broadcast from job status changes in `backend/src/api/agent/routes.py` (claim, complete, fail)

### Frontend Tests for User Story 1

- [x] T061 [P] [US1] Component tests for AgentPoolStatus in `frontend/tests/components/layout/AgentPoolStatus.test.tsx` (all badge states, click navigation)
- [x] T062 [P] [US1] Hook tests for useAgentPoolStatus in `frontend/tests/hooks/useAgentPoolStatus.test.ts` (WebSocket connection, updates)
- [x] T063 [P] [US1] ~~Context tests for AgentPoolContext~~ N/A - Design simplified: hook manages state directly without separate context

### Frontend Implementation for User Story 1

- [x] T064 [US1] Create AgentPoolStatus component in `frontend/src/components/layout/AgentPoolStatus.tsx` (icon, badge, click handler)
- [x] T065 [US1] Create useAgentPoolStatus hook in `frontend/src/hooks/useAgentPoolStatus.ts` (WebSocket subscription)
- [x] T066 [US1] ~~Create AgentPoolContext~~ N/A - Design simplified: useAgentPoolStatus hook manages state directly
- [x] T067 [US1] Integrate AgentPoolStatus into TopHeader in `frontend/src/components/layout/TopHeader.tsx` (between bell and user card)
- [x] T068 [US1] Add navigation from AgentPoolStatus click to /agents route

**Checkpoint**: Header shows real-time agent pool status badge

---

## Phase 5: User Story 4 - Job Distribution and Execution (Priority: P0) ✅

**Goal**: Jobs are automatically distributed to capable agents and executed with real-time progress

**Independent Test**: Create a job, verify agent claims and executes it with results appearing in web UI

### Backend Tests for User Story 4

- [x] T069 [P] [US4] Unit tests for JobCoordinatorService in `backend/tests/unit/services/test_job_coordinator.py` (claim logic, capability matching, bound agent routing)
- [x] T070 [P] [US4] Unit tests for signing secret generation in `backend/tests/unit/services/test_job_coordinator.py` (TestSigningSecret class)
- [x] T071 [P] [US4] Unit tests for ConfigLoader protocol in `backend/tests/unit/services/test_config_loader.py` (interface compliance)
- [x] T072 [P] [US4] Integration tests for POST `/api/agent/v1/jobs/claim` in `backend/tests/integration/test_job_claim.py` (claim success, no jobs, capability mismatch)
- [x] T073 [P] [US4] Integration tests for POST `/api/agent/v1/jobs/{guid}/complete` in `backend/tests/integration/test_job_complete.py` (success, failed, HMAC verification)
- [x] T074 [P] [US4] Integration tests for job progress endpoints in `backend/tests/integration/test_job_progress.py` (REST fallback)
- [x] T075 [P] [US4] WebSocket tests for agent progress in `backend/tests/integration/test_agent_progress_ws.py` (connect, stream, proxy to frontend)
- [x] T076 [P] [US4] Integration tests for config API endpoints in `backend/tests/integration/test_config_api.py` (photo-extensions, camera-mappings, etc.)

### Backend Implementation for User Story 4

- [x] T077 [US4] Create JobCoordinatorService in `backend/src/services/job_coordinator_service.py` (claim_job with FOR UPDATE SKIP LOCKED)
- [x] T078 [US4] Implement POST `/jobs/claim` endpoint in `backend/src/api/agent/routes.py` (capability matching, bound agent routing)
- [x] T079 [US4] Create job signing secret generation in `backend/src/services/job_coordinator_service.py` (HMAC secret per job)
- [x] T080 [US4] Implement POST `/jobs/{jobGuid}/complete` endpoint in `backend/src/api/agent/routes.py` (status update, result storage)
- [x] T081 [US4] Implement POST `/jobs/{jobGuid}/progress` endpoint (REST fallback) in `backend/src/api/agent/routes.py`
- [x] T082 [US4] Create WebSocket handler for agent progress in `backend/src/utils/websocket.py` (broadcast_job_progress, broadcast_global_job_update)
- [x] T083 [US4] Implement server-to-frontend progress proxy in `backend/src/utils/websocket.py` (broadcast to global jobs channel)
- [x] T084 [US4] Verify HMAC signature in job completion handler in `backend/src/services/job_coordinator_service.py`
- [x] T085 [US4] Handle agent offline detection in AgentService (release jobs, increment retry_count) in `backend/src/services/agent_service.py`
- [x] T086 [US4] Create ConfigLoader protocol in `backend/src/services/config_loader.py` (interface definition)
- [x] T087 [P] [US4] Create FileConfigLoader in `backend/src/services/config_loader.py` (wraps PhotoAdminConfig)
- [x] T088 [P] [US4] Create DatabaseConfigLoader in `backend/src/services/config_loader.py` (fetches from Configuration model)
- [x] T089 [US4] Create job config endpoint GET `/api/agent/v1/jobs/{guid}/config` in `backend/src/api/agent/routes.py`
- [x] T090 [US4] ToolService updated to list/get both in-memory and DB-persisted jobs in `backend/src/services/tool_service.py`

### Agent Tests for User Story 4

- [x] T091 [P] [US4] Unit tests for polling loop in `agent/tests/unit/test_polling_loop.py` (poll interval, claim handling, error recovery)
- [x] T092 [P] [US4] Unit tests for job executor in `agent/tests/unit/test_job_executor.py` (tool dispatch, progress callbacks, error handling)
- [x] T093 [P] [US4] Unit tests for progress reporter in `agent/tests/unit/test_progress_reporter.py` (WebSocket, REST fallback)
- [x] T094 [P] [US4] Unit tests for result signer in `agent/tests/unit/test_result_signer.py` (HMAC generation)
- [x] T095 [P] [US4] Unit tests for ApiConfigLoader in `agent/tests/unit/test_config_loader.py` (fetch, cache, error handling)
- [x] T096 [US4] Integration tests for job execution flow in `agent/tests/integration/test_job_execution.py` (claim, execute, complete)

### Agent Implementation for User Story 4

- [x] T097 [US4] Create agent polling loop in `agent/src/polling_loop.py` (5-second poll interval, job claim)
- [x] T098 [US4] Create job executor in `agent/src/job_executor.py` (tool dispatch, progress callback)
- [x] T099 [US4] Create progress reporter in `agent/src/progress_reporter.py` (WebSocket with REST fallback)
- [x] T100 [US4] Implement HMAC result signing in `agent/src/result_signer.py`
- [x] T101 [US4] Create ApiConfigLoader in `agent/src/config_loader.py` (fetch from server API)
- [x] T102 [US4] Integrate ConfigLoader into tool execution in `agent/src/job_executor.py`

**Checkpoint**: Jobs can be claimed, executed, and results stored via agent ✅

---

## Phase 6: User Story 3 - Local Collection with Agent Binding (Priority: P0) ✅

**Goal**: Photographers can analyze local photo collections via bound agents

**Independent Test**: Create LOCAL collection bound to agent, run PhotoStats, verify results in web UI

### Backend Tests for User Story 3

- [x] T103 [P] [US3] Unit tests for collection binding validation in `backend/tests/unit/test_collection_service.py` (LOCAL requires agent, deletion blocking)
- [x] T104 [P] [US3] Integration tests for LOCAL collection creation in `backend/tests/integration/test_collection_binding.py` (binding required, agent validation)
- [x] T105 [P] [US3] Integration tests for bound job routing in `backend/tests/unit/services/test_job_coordinator.py` (only bound agent claims)

### Backend Implementation for User Story 3

- [x] T106 [US3] Update Collection create endpoint to require agent selection for LOCAL type in `backend/src/services/collection_service.py`
- [x] T107 [US3] Add agent binding validation in CollectionService in `backend/src/services/collection_service.py`
- [x] T108 [US3] Update job creation to set bound_agent_id from collection in `backend/src/services/job_coordinator_service.py`
- [x] T109 [US3] Update job claim query to prioritize bound jobs in `backend/src/services/job_coordinator_service.py`
- [x] T110 [US3] Block agent deletion if bound collections exist in `backend/src/services/agent_service.py`

### Agent Tests for User Story 3

- [x] T111 [P] [US3] Unit tests for local filesystem scanning in `agent/tests/unit/test_local_filesystem.py` (path validation, file enumeration)

### Agent Implementation for User Story 3

- [x] T112 [US3] Handle local filesystem scanning in agent in `agent/src/job_executor.py` (local_filesystem capability, collection_test tool)

### Frontend Tests for User Story 3

- [x] T113 [P] [US3] Component tests for CollectionForm with agent selector in `frontend/tests/components/CollectionForm.test.tsx` (LOCAL type shows selector)
- [x] T114 [P] [US3] Hook tests for useOnlineAgents in `frontend/tests/hooks/useOnlineAgents.test.ts` (fetch online agents)

### Frontend Implementation for User Story 3

- [x] T115 [US3] Update CollectionForm to show agent selector for LOCAL type in `frontend/src/components/collections/CollectionForm.tsx`
- [x] T116 [US3] Add useOnlineAgents hook for agent dropdown in `frontend/src/hooks/useOnlineAgents.ts`
- [x] T117 [US3] Display bound agent in collection list view in `frontend/src/components/collections/CollectionList.tsx`

**Checkpoint**: LOCAL collections work with bound agents ✅

---

## Phase 7: User Story 5 - Connector Credential Modes (Priority: P1) ✅

**Goal**: Administrators can choose where connector credentials are stored (server vs agent)

**Independent Test**: Create connectors with different credential locations, verify job routing based on credential availability

### Backend Tests for User Story 5

- [x] T118 [P] [US5] Unit tests for credential location validation in `backend/tests/unit/services/test_connector_service.py` (mode validation, existing tests updated)
- [x] T119 [P] [US5] Integration tests for connector creation with credential modes (covered by existing connector tests)
- [x] T120 [P] [US5] Integration tests for job routing with agent credentials - **Completed in Phase 8** (covered by existing job coordinator tests)

### Backend Implementation for User Story 5

- [x] T121 [US5] Add CredentialLocation enum to Connector model (verified from T013)
- [x] T122 [US5] Update Connector create/update endpoints to accept credential_location in `backend/src/api/connectors.py` (also added update_credentials flag for edit mode)
- [x] T123 [US5] Conditionally require credentials based on location in `backend/src/services/connector_service.py` (server requires credentials, pending/agent do not)
- [x] T124 [US5] Update job routing to check agent connector capabilities - **Completed in Phase 8** (implemented in job_coordinator_service.py)
- [x] T125 [US5] Report connector capability to server from agent - **Completed in Phase 8** (via heartbeat in agent/src/main.py)

### Frontend Tests for User Story 5

- [x] T126 [P] [US5] Component tests for ConnectorForm with credential_location in `frontend/tests/components/ConnectorForm.test.tsx` (existing tests updated)
- [x] T127 [P] [US5] Component tests for connector credential status display in `frontend/tests/components/ConnectorList.test.tsx` (existing tests updated)

### Frontend Implementation for User Story 5

- [x] T128 [US5] Update ConnectorForm to show credential_location selector in `frontend/src/components/connectors/ConnectorForm.tsx` (Server/Pending options for create, Agent only shown when editing existing agent connector)
- [x] T129 [US5] Display credential status (Server/Agent/Pending Config) in connector list in `frontend/src/components/connectors/ConnectorList.tsx` (moved from ConnectorsPage to ConnectorsTab in Settings)
- [x] T130 [US5] Show which agents have credentials for each connector - **Completed in Phase 8** (ConnectorList.tsx displays agent count with tooltip)

### Additional Implementation Notes (Phase 7)

- Added `update_credentials` flag to ConnectorUpdate schema for editing without re-entering credentials
- Connectors with pending credentials cannot be activated (enforced in backend and frontend)
- Test connection disabled for pending/agent credentials (graceful error messages)
- Deleted unused `ConnectorsPage.tsx` (connectors now in Settings tab)
- Fixed dialog scrolling and added toast notifications for test results
- Fixed Pydantic validation error handling in frontend API client

**Checkpoint**: Connectors support server, agent, and pending credential modes. All deferred tasks (T120, T124, T125, T130) completed in Phase 8 ✅

---

## Phase 8: User Story 6 - Agent Credential Configuration via CLI (Priority: P1) ✅

**Goal**: Agent operators can configure connector credentials locally via CLI

**Independent Test**: Run CLI commands to list pending connectors, configure credentials, verify capability reported to server

### Backend Tests for User Story 6

- [x] T131 [P] [US6] Integration tests for agent connector endpoints in `backend/tests/integration/test_agent_connector_api.py` (list, metadata, report-capability) - 16 tests

### Backend Implementation for User Story 6

- [x] T132 [US6] Create GET `/connectors` agent endpoint in `backend/src/api/agent/routes.py` (list with pending_only filter)
- [x] T133 [US6] Create GET `/connectors/{guid}/metadata` agent endpoint in `backend/src/api/agent/routes.py`
- [x] T134 [US6] Create POST `/connectors/{guid}/report-capability` agent endpoint in `backend/src/api/agent/routes.py`

### Agent Tests for User Story 6

- [x] T135 [P] [US6] Unit tests for credential store in `agent/tests/unit/test_credential_store.py` (encryption, storage, retrieval) - 26 tests
- [x] T136 [P] [US6] Unit tests for connectors CLI commands in `agent/tests/unit/test_cli_connectors.py` (list, show, remove, test) - 15 tests
- [x] T137 [P] [US6] Unit tests for capabilities CLI command in `agent/tests/unit/test_cli_capabilities.py` - 5 tests
- [x] T138 [US6] Integration tests for credential configuration flow in `agent/tests/integration/test_credential_config.py` - 12 tests

### Agent Implementation for User Story 6

- [x] T139 [US6] Create local credential store in `agent/src/credential_store.py` (Fernet encryption)
- [x] T140 [US6] Implement `connectors list` CLI command in `agent/cli/connectors.py` (--pending flag)
- [x] T141 [US6] Implement `connectors configure` CLI command in `agent/cli/connectors.py` (interactive prompts)
- [x] T142 [US6] Implement credential test before storage in `agent/cli/connectors.py` (S3, GCS, SMB tests)
- [x] T143 [US6] Implement `capabilities` CLI command in `agent/cli/capabilities.py`
- [x] T144 [US6] Report connector capabilities on heartbeat in `agent/src/main.py` (get_all_capabilities function)

### Additional Implementation Notes (Phase 8)

- Master key auto-generated on first credential storage (no explicit init command needed)
- Agents can configure credentials for both 'pending' AND 'agent' credential_location connectors
- When first agent reports capability for pending connector, server flips credential_location to 'agent'
- Frontend ConnectorList shows agent count with tooltip for connectors with agent-side credentials
- Frontend ConnectorList added tests for agent credential display (4 new tests)

**Checkpoint**: Agent CLI can configure and manage connector credentials ✅

---

## Phase 9: User Story 7 - SMB/Network Share via Agent (Priority: P1)

**Goal**: Photographers can analyze photos on local SMB shares via agents

**Independent Test**: Configure SMB credentials on agent, create SMB collection, run analysis

### Agent Tests for User Story 7

- [ ] T145 [P] [US7] Unit tests for SMB connection in `agent/tests/unit/test_smb_connector.py` (connect, list, download)
- [ ] T146 [US7] Integration tests for SMB access in `agent/tests/integration/test_smb_integration.py` (with mock SMB server)

### Implementation for User Story 7

- [ ] T147 [US7] Add SMB connector type support in `backend/src/models/connector.py` (verify exists)
- [ ] T148 [US7] Add SMB credential schema to connector metadata in `backend/src/api/agent/routes.py`
- [ ] T149 [US7] Implement SMB connection test in agent in `agent/src/connectors/smb.py`
- [ ] T150 [US7] Implement SMB filesystem access wrapper in `agent/src/connectors/smb.py`
- [ ] T151 [US7] Integrate SMB access in job executor in `agent/src/job_executor.py`

**Checkpoint**: SMB collections can be analyzed via agents

---

## Phase 10: User Story 8 - Job Queue Visibility and Management (Priority: P1)

**Goal**: Administrators can see all queued and running jobs across agents

**Independent Test**: Create multiple jobs, view job queue UI, perform cancel/retry actions

### Backend Tests for User Story 8

- [ ] T152 [P] [US8] Unit tests for job cancellation service in `backend/tests/unit/services/test_job_cancellation.py` (cancel, notify agent)
- [ ] T153 [P] [US8] Integration tests for job management endpoints in `backend/tests/integration/test_job_management.py` (cancel, retry, filters)

### Backend Implementation for User Story 8

- [ ] T154 [US8] Add agent_guid to job list response in `backend/src/api/jobs/routes.py`
- [ ] T155 [US8] Add filters (agent, status) to job list endpoint in `backend/src/api/jobs/routes.py`
- [ ] T156 [US8] Implement job cancel endpoint enhancement in `backend/src/api/jobs/routes.py` (notify agent via WebSocket)
- [ ] T157 [US8] Implement job retry endpoint in `backend/src/api/jobs/routes.py` (create new PENDING job)

### Agent Tests for User Story 8

- [ ] T158 [P] [US8] Unit tests for cancellation handling in `agent/tests/unit/test_cancellation.py` (receive cancel, graceful stop)

### Agent Implementation for User Story 8

- [ ] T159 [US8] Handle cancellation request in agent in `agent/src/polling_loop.py` (via WebSocket)

### Frontend Tests for User Story 8

- [ ] T160 [P] [US8] Component tests for JobsPage with agent column in `frontend/tests/pages/JobsPage.test.tsx` (render, filters, actions)

### Frontend Implementation for User Story 8

- [ ] T161 [US8] Update JobsPage with agent column in `frontend/src/pages/JobsPage.tsx`
- [ ] T162 [US8] Add job filters UI in `frontend/src/pages/JobsPage.tsx` (agent, status dropdowns)
- [ ] T163 [US8] Add cancel/retry action buttons in `frontend/src/pages/JobsPage.tsx`

**Checkpoint**: Full job queue visibility and management in UI

---

## Phase 11: User Story 9 - Agent Health Monitoring (Priority: P1)

**Goal**: Administrators can monitor agent health and resource usage

**Independent Test**: View agent dashboard, verify real-time status updates

### Backend Tests for User Story 9

- [ ] T164 [P] [US9] Unit tests for metrics storage in `backend/tests/unit/services/test_agent_metrics.py` (store, retrieve)
- [ ] T165 [P] [US9] Integration tests for agent detail endpoint in `backend/tests/integration/test_agent_detail.py` (metrics, job history)

### Backend Implementation for User Story 9

- [ ] T166 [US9] Add metrics to heartbeat request schema in `backend/src/api/agent/schemas.py` (cpu_percent, memory_percent, disk_free_gb)
- [ ] T167 [US9] Store agent metrics in Agent model in `backend/src/models/agent.py` (metrics_json field)
- [ ] T168 [US9] Create agent detail endpoint GET `/api/agents/{guid}` in `backend/src/api/agents/routes.py` (include recent jobs)
- [ ] T169 [US9] Create agent job history endpoint GET `/api/agents/{guid}/jobs` in `backend/src/api/agents/routes.py`

### Agent Tests for User Story 9

- [ ] T170 [P] [US9] Unit tests for metrics collection in `agent/tests/unit/test_metrics.py` (CPU, memory, disk)

### Agent Implementation for User Story 9

- [ ] T171 [US9] Collect and report system metrics in agent in `agent/src/metrics.py`

### Frontend Tests for User Story 9

- [ ] T172 [P] [US9] Component tests for AgentDetailPage in `frontend/tests/pages/AgentDetailPage.test.tsx` (metrics, job history)
- [ ] T173 [P] [US9] Hook tests for useAgentDetail in `frontend/tests/hooks/useAgentDetail.test.ts` (fetch, WebSocket updates)

### Frontend Implementation for User Story 9

- [ ] T174 [US9] Create AgentDetailPage in `frontend/src/pages/AgentDetailPage.tsx` (metrics, current job, history)
- [ ] T175 [US9] Add route for agent detail at `/agents/{guid}` in `frontend/src/App.tsx`
- [ ] T176 [US9] Create real-time agent status WebSocket subscription in `frontend/src/hooks/useAgentDetail.ts`

**Checkpoint**: Agent health monitoring with metrics and job history

---

## Phase 12: User Story 10 - Multi-Agent Job Distribution (Priority: P2)

**Goal**: Jobs are distributed across multiple capable agents

**Independent Test**: Register multiple agents, create multiple jobs, verify distribution

### Backend Tests for User Story 10

- [ ] T177 [P] [US10] Unit tests for load balancing in `backend/tests/unit/services/test_load_balancing.py` (prefer least busy agent)
- [ ] T178 [P] [US10] Integration tests for multi-agent distribution in `backend/tests/integration/test_multi_agent.py`

### Implementation for User Story 10

- [ ] T179 [US10] Implement simple load balancing in job claim (prefer agent with fewest recent jobs) in `backend/src/services/job_coordinator_service.py`
- [ ] T180 [US10] Track recent job count per agent in `backend/src/services/job_coordinator_service.py`
- [ ] T181 [US10] Display agent load in agent list in `frontend/src/pages/AgentsPage.tsx`

**Checkpoint**: Jobs distributed across multiple agents with basic load balancing

---

## Phase 13: User Story 11 - Automatic Collection Refresh Scheduling (Priority: P2)

**Goal**: Collection analysis automatically re-runs based on configurable TTL

**Independent Test**: Set collection TTL, wait for job completion, verify next job auto-scheduled

### Backend Tests for User Story 11

- [ ] T182 [P] [US11] Unit tests for scheduled job creation in `backend/tests/unit/services/test_scheduled_jobs.py` (auto-create, unique constraint)
- [ ] T183 [P] [US11] Integration tests for scheduling in `backend/tests/integration/test_collection_scheduling.py` (TTL, manual refresh cancels scheduled)

### Backend Implementation for User Story 11

- [ ] T184 [US11] Create scheduled job on completion if TTL configured in `backend/src/services/job_service.py`
- [ ] T185 [US11] Include SCHEDULED jobs in claim query (where scheduled_for <= NOW) in `backend/src/services/job_coordinator_service.py`
- [ ] T186 [US11] Enforce unique scheduled job per (collection, tool) in `backend/src/services/job_service.py`
- [ ] T187 [US11] Cancel scheduled job on manual refresh in `backend/src/services/job_service.py`
- [ ] T188 [US11] Cascade delete scheduled jobs on collection deletion in `backend/src/services/collection_service.py`

### Frontend Tests for User Story 11

- [ ] T189 [P] [US11] Component tests for collection refresh settings in `frontend/tests/components/collections/CollectionForm.test.tsx` (TTL fields)
- [ ] T190 [P] [US11] Component tests for upcoming jobs section in `frontend/tests/pages/JobsPage.test.tsx`

### Frontend Implementation for User Story 11

- [ ] T191 [US11] Add auto_refresh and refresh_interval_hours to collection form in `frontend/src/components/collections/CollectionForm.tsx`
- [ ] T192 [US11] Display "Upcoming" scheduled jobs section in `frontend/src/pages/JobsPage.tsx`

**Checkpoint**: Automatic collection refresh scheduling works end-to-end

---

## Phase 14: Agent Trust and Attestation (Cross-Cutting)

**Purpose**: Binary attestation and result signing

### Tests

- [ ] T193 [P] Unit tests for release manifest in `backend/tests/unit/models/test_release_manifest.py`
- [ ] T194 [P] Unit tests for binary attestation in `agent/tests/unit/test_attestation.py` (self-hash)
- [ ] T195 [P] Integration tests for attestation flow in `backend/tests/integration/test_agent_attestation.py`

### Implementation

- [ ] T196 Create release manifest model/storage for binary checksums in `backend/src/models/release_manifest.py`
- [ ] T197 Validate binary checksum during registration in `backend/src/services/agent_service.py`
- [ ] T198 Implement binary self-hash in agent in `agent/src/attestation.py`
- [ ] T199 Add admin endpoint to manage release manifests in `backend/src/api/admin/routes.py`

**Checkpoint**: Agent attestation ensures only trusted binaries can register

---

## Phase 15: Result Ingestion (Cross-Cutting)

**Purpose**: Chunked upload protocol for large results

### Tests

- [ ] T200 [P] Unit tests for ChunkedUploadService in `backend/tests/unit/services/test_chunked_upload.py` (chunking, checksum, expiration)
- [ ] T201 [P] Unit tests for agent chunked upload client in `agent/tests/unit/test_chunked_upload.py`
- [ ] T202 [P] Integration tests for chunked upload flow in `backend/tests/integration/test_chunked_upload.py`
- [ ] T203 [P] Unit tests for result validation in `backend/tests/unit/services/test_result_validation.py` (JSON schema, HTML security)

### Implementation

- [ ] T204 Create ChunkedUploadService in `backend/src/services/chunked_upload_service.py`
- [ ] T205 Implement PUT `/uploads/{uploadId}/{chunkIndex}` endpoint in `backend/src/api/agent/routes.py`
- [ ] T206 Implement POST `/uploads/{uploadId}/finalize` endpoint in `backend/src/api/agent/routes.py`
- [ ] T207 Implement chunked upload client in agent in `agent/src/chunked_upload.py`
- [ ] T208 Validate result JSON against tool schemas in `backend/src/services/job_service.py`
- [ ] T209 Validate HTML report security (no external scripts) in `backend/src/services/chunked_upload_service.py`

**Checkpoint**: Large results upload via chunked protocol

---

## Phase 16: Polish & Documentation

**Purpose**: Documentation updates and final polish

### Tests

- [ ] T210 [P] E2E test for complete agent workflow in `backend/tests/e2e/test_agent_workflow.py` (register, execute job, complete)

### Implementation

- [ ] T211 [P] Update `.specify/memory/constitution.md` with Agent-Only Execution principle
- [ ] T212 [P] Update `CLAUDE.md` with agent architecture, GUID prefixes, header pattern
- [ ] T213 [P] Update `README.md` with agent requirement section
- [ ] T214 Create `docs/agent-installation.md` (download, register, start, configure, troubleshoot)
- [ ] T215 [P] Add "No agents available" warning to job creation UI in `frontend/src/components/jobs/JobCreateForm.tsx`
- [ ] T216 Run quickstart.md validation (manual test)
- [ ] T217 Create agent packaging scripts in `agent/packaging/` (build_macos.sh, build_windows.sh, build_linux.sh)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion - **BLOCKS all user stories**
- **User Stories (Phase 3-13)**: All depend on Phase 2 completion
  - P0 stories proceed in order: US2 → US1 → US4 → US3
  - P1 stories can start after P0 complete
  - P2 stories can start after P1 complete
- **Cross-Cutting (Phase 14-15)**: Can run parallel with later user stories
- **Polish (Phase 16)**: Depends on all stories being complete

### User Story Dependencies

| Story | Depends On | Can Parallel With |
|-------|------------|-------------------|
| US2 (Registration) | Phase 2 only | - |
| US1 (Pool Status) | US2 (needs agents to display) | - |
| US4 (Job Execution) | US2 (needs agents) | US1 |
| US3 (Local Collections) | US2, US4 (needs job execution) | US1 |
| US5 (Credential Modes) | US4 | US6, US7 |
| US6 (CLI Credentials) | US5 | US7 |
| US7 (SMB) | US5, US6 | - |
| US8 (Job Queue UI) | US4 | US9 |
| US9 (Agent Monitoring) | US2 | US8 |
| US10 (Multi-Agent) | US4 | US11 |
| US11 (Scheduling) | US4 | US10 |

### Parallel Opportunities

```text
Phase 1 (all Setup tasks can run in parallel):
- T002, T003, T004, T005, T006, T007, T008

Phase 2 (some Foundation tasks can run in parallel):
- T010, T013, T014, T015, T016, T017 (after T009)
- T019, T020, T023 (after T018)

Within User Stories:
- Tests can run in parallel within each story
- Frontend and backend tests can run in parallel
- Implementation follows tests
```

---

## Parallel Example: Phase 2 Tests

```bash
# Launch all model tests together:
Task: "Unit tests for Agent model in backend/tests/unit/models/test_agent.py"
Task: "Unit tests for AgentRegistrationToken model in backend/tests/unit/models/test_agent_registration_token.py"
Task: "Unit tests for enhanced Job model in backend/tests/unit/models/test_job_agent_fields.py"
```

---

## Implementation Strategy

### MVP First (User Story 2 + 1 + 4)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (**CRITICAL** - blocks all stories)
3. Complete Phase 3: User Story 2 (Agent Registration) - can register agents
4. Complete Phase 4: User Story 1 (Pool Status) - can see agent status in header
5. Complete Phase 5: User Story 4 (Job Execution) - can execute jobs
6. **STOP and VALIDATE**: End-to-end job execution via agent
7. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US2 → Agents can register → **MVP Milestone 1**
3. Add US1 → Pool status visible → **MVP Milestone 2**
4. Add US4 → Jobs execute → **MVP Milestone 3**
5. Add US3 → Local collections work → **Core Complete**
6. Add US5-US9 → Full P1 features
7. Add US10-US11 → Full P2 features
8. Polish + Documentation → **Release Ready**

### Task Count Summary

| Phase | Description | Tests | Implementation | Total |
|-------|-------------|-------|----------------|-------|
| 1 | Setup | 1 | 7 | 8 |
| 2 | Foundational | 9 | 14 | 23 |
| 3 | US2 - Registration | 12 | 17 | 29 |
| 4 | US1 - Pool Status | 6 | 8 | 14 |
| 5 | US4 - Job Execution | 14 | 20 | 34 |
| 6 | US3 - Local Collections | 5 | 10 | 15 |
| 7 | US5 - Credential Modes | 5 | 8 | 13 |
| 8 | US6 - CLI Credentials | 5 | 9 | 14 |
| 9 | US7 - SMB | 2 | 5 | 7 |
| 10 | US8 - Job Queue UI | 4 | 8 | 12 |
| 11 | US9 - Agent Monitoring | 5 | 8 | 13 |
| 12 | US10 - Multi-Agent | 2 | 3 | 5 |
| 13 | US11 - Scheduling | 4 | 7 | 11 |
| 14 | Attestation | 3 | 4 | 7 |
| 15 | Result Ingestion | 4 | 6 | 10 |
| 16 | Polish | 1 | 6 | 7 |
| **Total** | | **77** | **140** | **217** |

### Test Coverage Summary

| Component | Unit Tests | Integration Tests | Total |
|-----------|------------|-------------------|-------|
| Backend Models | 3 | - | 3 |
| Backend Services | 14 | - | 14 |
| Backend API | 2 | 20 | 22 |
| Backend WebSocket | - | 4 | 4 |
| Agent Core | 15 | 5 | 20 |
| Agent CLI | 4 | 1 | 5 |
| Frontend Components | 8 | - | 8 |
| Frontend Hooks | 6 | - | 6 |
| E2E | - | 1 | 1 |
| **Total** | **52** | **31** | **77** |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Each user story includes tests for backend, agent, and frontend as applicable
- Tests should be written to FAIL before implementation
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Per constitution: "All features MUST have test coverage. Tests SHOULD be written before or alongside implementation."
