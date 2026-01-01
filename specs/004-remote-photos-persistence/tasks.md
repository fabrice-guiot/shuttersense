# Tasks: Remote Photo Collections and Analysis Persistence

**Branch**: `004-remote-photos-persistence`
**Input**: Design documents from `/specs/004-remote-photos-persistence/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story (US1-US5 from spec.md) to enable independent implementation and testing.

**Testing Strategy**: Comprehensive test coverage (>80% backend, >75% frontend) for constitution compliance. Testing tasks integrated throughout:
- Phase 3.5: Backend testing Phase 2-3 (31 tasks) - Core infrastructure, services, models, API
- Phase 3: Frontend testing (11 tasks) - Hooks, components, connector-collection flow
- Phase 4: Backend testing (10 tasks) + Frontend testing (7 tasks) = 17 tasks - Tools, WebSocket, results
- Phase 5: Backend testing (8 tasks) + Frontend testing (6 tasks) = 14 tasks - Pipelines, validation, activation
- Phase 6: Backend testing (3 tasks) + Frontend testing (3 tasks) = 6 tasks - Trend analysis, charts
- Phase 7: Backend testing (7 tasks) + Frontend testing (4 tasks) = 11 tasks - Config, YAML migration
- **Total**: 90 testing tasks (59 backend + 31 frontend) ensuring comprehensive coverage

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US5)
- All file paths are absolute from repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 [P] Create backend directory structure: backend/src/{models,services,api,db,schemas,utils}, backend/tests/{unit,integration,e2e}
- [X] T002 [P] Create frontend directory structure: frontend/src/{components,pages,services,hooks,utils}, frontend/tests/components
- [X] T003 [P] Initialize backend/requirements.txt with dependencies: FastAPI, SQLAlchemy, Alembic, boto3, google-cloud-storage, smbprotocol, pydantic, cryptography, uvicorn, psycopg2-binary, pytest
- [X] T004 [P] Initialize frontend/package.json with dependencies: React, React Router, Axios, Recharts, Material-UI or Ant Design, WebSocket client
- [X] T005 [P] Add backend/.env.example with PHOTO_ADMIN_DB_URL, PHOTO_ADMIN_MASTER_KEY placeholders
- [X] T006 [P] Update root .gitignore to exclude backend/.env, frontend/node_modules, __pycache__, *.pyc

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Database Setup

- [X] T007 Create backend/src/db/database.py with SQLAlchemy engine configuration (PostgreSQL, connection pooling)
- [X] T008 Setup Alembic in backend/ with alembic.ini configuration pointing to backend/src/db/migrations/
- [X] T009 Create backend/src/models/__init__.py with Base declarative base class

### Master Key Management (NEW from research.md)

- [X] T010 Create setup_master_key.py (repository root) with interactive key generation using Fernet.generate_key()
- [X] T011 In setup_master_key.py, add platform-specific environment variable instructions (macOS/Linux/Windows)
- [X] T012 In setup_master_key.py, add key validation function to check Fernet format
- [X] T013 In setup_master_key.py, add option to save key to ~/.photo_admin_master_key.txt with chmod 600
- [X] T014 In setup_master_key.py, add warnings about key loss consequences

### Encryption Infrastructure (from research.md Task 2)

- [X] T015 Create backend/src/utils/crypto.py with CredentialEncryptor class (Fernet encryption/decryption)
- [X] T016 In backend/src/utils/crypto.py, implement encrypt() and decrypt() methods using PHOTO_ADMIN_MASTER_KEY env var
- [X] T017 In backend/src/utils/crypto.py, add master key validation on CredentialEncryptor initialization (fail fast if missing/invalid)

### File Listing Cache (from research.md Task 3)

- [X] T018 Create backend/src/utils/cache.py with CachedFileListing dataclass (files, cached_at, ttl_seconds)
- [X] T019 In backend/src/utils/cache.py, create FileListingCache class with in-memory dict storage and threading.Lock
- [X] T020 In backend/src/utils/cache.py, implement get(), set(), invalidate(), clear() methods with TTL expiry logic
- [X] T021 In backend/src/utils/cache.py, define COLLECTION_STATE_TTL constants (Live: 3600, Closed: 86400, Archived: 604800)

### Job Queue (from research.md Task 4)

- [X] T022 Create backend/src/utils/job_queue.py with JobStatus enum (QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED)
- [X] T023 In backend/src/utils/job_queue.py, create AnalysisJob dataclass (id, collection_id, tool, pipeline_id, status, created_at, started_at, completed_at, progress, error_message)
- [X] T024 In backend/src/utils/job_queue.py, create JobQueue class with in-memory dict storage, FIFO queue list, threading.Lock
- [X] T025 In backend/src/utils/job_queue.py, implement enqueue(), dequeue(), get_position(), cancel(), get_job() methods

### Pipeline Processor (CRITICAL - from data-model.md and research.md Task 7)

- [X] T026 [P] Create utils/pipeline_processor.py with Node and Edge dataclasses
- [X] T027 [P] In utils/pipeline_processor.py, create PipelineGraph class with __init__(config), _parse_config(), get_children(), get_parents(), get_nodes_by_type()
- [X] T028 In utils/pipeline_processor.py, implement PipelineGraph.topological_sort() using Kahn's algorithm for cycle detection
- [X] T029 In utils/pipeline_processor.py, implement PipelineGraph.dfs_from_nodes() for orphaned node detection
- [X] T030 [P] In utils/pipeline_processor.py, create ValidationError dataclass (error_type, message, node_ids, guidance)
- [X] T031 In utils/pipeline_processor.py, create StructureValidator class with validate(), detect_cycles(), find_orphaned_nodes(), find_dead_ends()
- [X] T032 In utils/pipeline_processor.py, implement StructureValidator.validate_nodes() for node-specific constraints (Capture, File, Process, Pairing, Branching, Termination)
- [X] T033 In utils/pipeline_processor.py, implement StructureValidator.validate_property_references() to check processing_methods exist in config
- [X] T034 [P] In utils/pipeline_processor.py, create FilenamePreviewGenerator class with generate_preview(camera_id, counter)
- [X] T035 In utils/pipeline_processor.py, implement FilenamePreviewGenerator._find_all_paths() using DFS to find Capture → Termination paths
- [X] T036 In utils/pipeline_processor.py, implement FilenamePreviewGenerator._apply_path_transformations() to build filename from node properties
- [X] T037 [P] In utils/pipeline_processor.py, create ImageGroupStatus enum (CONSISTENT, PARTIAL, INCONSISTENT)
- [X] T038 [P] In utils/pipeline_processor.py, create ImageGroup dataclass (base, files, status, completed_nodes, missing_files)
- [X] T039 In utils/pipeline_processor.py, create CollectionValidator class with validate(), _group_files(), _validate_group()
- [X] T040 In utils/pipeline_processor.py, implement CollectionValidator._get_expected_files_for_base() using FilenamePreviewGenerator logic
- [X] T041 [P] In utils/pipeline_processor.py, create ReadinessCalculator class with calculate(), _count_groups_reaching_node()

### Logging Infrastructure

- [X] T042 Create backend/src/utils/logging_config.py with structured logging setup (JSON format, log levels per environment)
- [X] T043 In backend/src/utils/logging_config.py, configure loggers for api, services, tools, db with file rotation

### FastAPI Application Bootstrap

- [X] T044 Create backend/src/main.py with FastAPI app initialization
- [X] T045 In backend/src/main.py, add app.state.file_cache = FileListingCache() singleton
- [X] T046 In backend/src/main.py, add app.state.job_queue = JobQueue() singleton
- [X] T047 In backend/src/main.py, add startup event handler to validate PHOTO_ADMIN_MASTER_KEY env var (exit with error if missing)
- [X] T048 In backend/src/main.py, configure CORS middleware for localhost:3000 (frontend dev server)
- [X] T049 In backend/src/main.py, add exception handlers for validation errors, database errors, generic errors

### CLI Tool Entry Point

- [X] T050 Create web_server.py (repository root) as CLI entry point to start FastAPI with uvicorn
- [X] T051 In web_server.py, add PHOTO_ADMIN_MASTER_KEY validation on startup (print error pointing to setup_master_key.py if missing)
- [X] T052 In web_server.py, add --host, --port, --reload CLI arguments using argparse

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Manage Multiple Collections Through Web Interface (Priority: P1) 🎯 MVP

**Goal**: Enable users to create, view, edit, and delete photo collections (local and remote) with credential management through web UI

**Independent Test**: Create connector, create collection referencing connector, refresh browser, verify both persist and collection shows accessibility status

**Architecture Note**: Connectors (T053-T094l) are separate from Collections to enable credential reuse - one S3 connector can service multiple bucket collections. Delete protection prevents orphaned collections.

### Backend - Connector Model (NEW from data-model.md)

- [X] T053 [P] [US1] Create backend/src/models/connector.py with ConnectorType enum (S3, GCS, SMB)
- [X] T054 [US1] In backend/src/models/connector.py, create Connector model (id, name, type, credentials, metadata_json, is_active, last_validated, last_error, created_at, updated_at)
- [X] T055 [US1] In backend/src/models/connector.py, add unique constraint on name, indexes on type and is_active
- [X] T056 [US1] In backend/src/models/connector.py, add relationship to Collection (one-to-many, RESTRICT delete)

### Backend - Collection Model

- [X] T057 [P] [US1] Create backend/src/models/collection.py with CollectionType enum (LOCAL, S3, GCS, SMB)
- [X] T058 [P] [US1] In backend/src/models/collection.py, create CollectionState enum (LIVE, CLOSED, ARCHIVED)
- [X] T059 [US1] In backend/src/models/collection.py, create Collection model (id, connector_id, name, type, location, state, cache_ttl, is_accessible, last_error, metadata_json, created_at, updated_at)
- [X] T060 [US1] In backend/src/models/collection.py, add unique constraint on name, foreign key to connectors(id) with RESTRICT delete
- [X] T061 [US1] In backend/src/models/collection.py, add indexes on state, type, is_accessible
- [X] T062 [US1] In backend/src/models/collection.py, add relationship to Connector (many-to-one)
- [X] T063 [US1] In backend/src/models/collection.py, implement get_effective_cache_ttl() method (user override or state default)

### Backend - Remote Storage Adapters (from research.md Tasks 1-3)

- [X] T064 [P] [US1] Create backend/src/services/remote/base.py with abstract StorageAdapter class (list_files, test_connection)
- [X] T065 [P] [US1] Create backend/src/services/remote/s3_adapter.py with S3Adapter class using boto3
- [X] T066 [US1] In backend/src/services/remote/s3_adapter.py, implement list_files() with exponential backoff retry (3 retries per FR-012)
- [X] T067 [US1] In backend/src/services/remote/s3_adapter.py, implement test_connection() to validate credentials
- [X] T068 [P] [US1] Create backend/src/services/remote/gcs_adapter.py with GCSAdapter class using google-cloud-storage
- [X] T069 [US1] In backend/src/services/remote/gcs_adapter.py, implement list_files() with exponential backoff retry
- [X] T070 [US1] In backend/src/services/remote/gcs_adapter.py, implement test_connection() to validate service account JSON
- [X] T071 [P] [US1] Create backend/src/services/remote/smb_adapter.py with SMBAdapter class using smbprotocol
- [X] T072 [US1] In backend/src/services/remote/smb_adapter.py, implement list_files() with retry logic
- [X] T073 [US1] In backend/src/services/remote/smb_adapter.py, implement test_connection() to validate SMB credentials

### Backend - Connector Service (NEW from data-model.md)

- [X] T074 Create backend/src/services/connector_service.py with ConnectorService class
- [X] T075 In backend/src/services/connector_service.py, implement create_connector(name, type, credentials, metadata) with credential encryption using CredentialEncryptor
- [X] T076 In backend/src/services/connector_service.py, implement get_connector(id) with credential decryption
- [X] T077 In backend/src/services/connector_service.py, implement list_connectors(type_filter, active_only)
- [X] T078 In backend/src/services/connector_service.py, implement update_connector(id, name, credentials, metadata) with re-encryption
- [X] T079 In backend/src/services/connector_service.py, implement delete_connector(id) with check for referenced collections (raise error if collections exist per RESTRICT)
- [X] T080 In backend/src/services/connector_service.py, implement test_connector(id) to validate connection using appropriate adapter
- [X] T081 In backend/src/services/connector_service.py, implement last_validated and last_error fields on test_connector() results

### Backend - Collection Service

- [X] T082 Create backend/src/services/collection_service.py with CollectionService class
- [X] T083 In backend/src/services/collection_service.py, implement create_collection(name, type, location, state, connector_id, cache_ttl, metadata) with accessibility test
- [X] T084 In backend/src/services/collection_service.py, implement get_collection(id) returning Collection with connector details
- [X] T085 In backend/src/services/collection_service.py, implement list_collections(state_filter, type_filter, accessible_only) sorted by created_at DESC
- [X] T086 In backend/src/services/collection_service.py, implement update_collection(id, name, location, state, cache_ttl, metadata) with cache invalidation on state change
- [X] T087 In backend/src/services/collection_service.py, implement delete_collection(id, force) with check for analysis_results and active jobs (FR-005)
- [X] T088 In backend/src/services/collection_service.py, implement test_collection_accessibility(id) using appropriate adapter (local filesystem or remote)
- [X] T089 In backend/src/services/collection_service.py, implement get_collection_files(id, cache) with cache hit/miss logic using FileListingCache
- [X] T090 In backend/src/services/collection_service.py, implement refresh_collection_cache(id, confirm, threshold) with file count warning logic (FR-013a, default 100K threshold)

### Backend - Pydantic Schemas for Collections

- [x] T091 [P] [US1] Create backend/src/schemas/collection.py with S3Credentials, GCSCredentials, SMBCredentials schemas
- [x] T092 [P] [US1] In backend/src/schemas/collection.py, create CollectionCreate schema (name, type, location, state, connector_id, cache_ttl, metadata) with validation
- [x] T093 [P] [US1] In backend/src/schemas/collection.py, create CollectionUpdate schema (name, location, state, cache_ttl, metadata)
- [x] T094 [P] [US1] In backend/src/schemas/collection.py, create CollectionResponse schema (id, name, type, location, state, connector_id, cache_ttl, is_accessible, last_error, metadata, created_at, updated_at)

### Backend - Pydantic Schemas for Connectors

- [x] T094a [P] [US1] In backend/src/schemas/collection.py, create ConnectorCreate schema (name, type, credentials, metadata) with credential validation
- [x] T094b [P] [US1] In backend/src/schemas/collection.py, create ConnectorUpdate schema (name, credentials, metadata, is_active)
- [x] T094c [P] [US1] In backend/src/schemas/collection.py, create ConnectorResponse schema (id, name, type, metadata, is_active, last_validated, last_error, created_at, updated_at) - credentials NEVER exposed
- [x] T094d [P] [US1] In backend/src/schemas/collection.py, create ConnectorTestResponse schema (success, message)

### Backend - API Endpoints for Connectors (NEW - addresses architectural gap)

- [x] T094e Create backend/src/api/connectors.py with FastAPI router
- [x] T094f [P] [US1] In backend/src/api/connectors.py, implement GET /connectors with filters (type, active_only) returning ConnectorResponse list
- [x] T094g [P] [US1] In backend/src/api/connectors.py, implement POST /connectors with ConnectorCreate, credential validation, encryption, return 201 with ConnectorResponse or 409 if name exists
- [x] T094h [P] [US1] In backend/src/api/connectors.py, implement GET /connectors/{id} returning ConnectorResponse (credentials not included) or 404
- [x] T094i [P] [US1] In backend/src/api/connectors.py, implement PUT /connectors/{id} with ConnectorUpdate, credential re-encryption if provided, return 200 or 404/409
- [x] T094j [US1] In backend/src/api/connectors.py, implement DELETE /connectors/{id} with PROTECTION - return 409 Conflict if collections reference connector, 204 if successful
- [x] T094k [P] [US1] In backend/src/api/connectors.py, implement POST /connectors/{id}/test with connection test using appropriate adapter, update last_validated/last_error
- [x] T094l [US1] In backend/src/main.py, register connectors router with /api prefix

### Backend - API Endpoints for Collections

- [x] T095 Create backend/src/api/collections.py with FastAPI router
- [x] T096 [P] [US1] In backend/src/api/collections.py, implement GET /collections with filters (state, type, accessible_only) returning CollectionResponse list
- [x] T097 [P] [US1] In backend/src/api/collections.py, implement POST /collections with CollectionCreate, accessibility test, return 201 with CollectionResponse or 409 if name exists
- [x] T098 [P] [US1] In backend/src/api/collections.py, implement GET /collections/{id} returning CollectionResponse or 404
- [x] T099 [P] [US1] In backend/src/api/collections.py, implement PUT /collections/{id} with CollectionUpdate, cache invalidation, return 200 or 404/409
- [x] T100 [US1] In backend/src/api/collections.py, implement DELETE /collections/{id} with force query param, check for results/jobs, return 204 or 409 with confirmation prompt
- [x] T101 [P] [US1] In backend/src/api/collections.py, implement POST /collections/{id}/test returning accessibility status and file_count
- [x] T102 [P] [US1] In backend/src/api/collections.py, implement POST /collections/{id}/refresh with confirm query param, file count warning, cache invalidation
- [x] T103 [US1] In backend/src/main.py, register collections router with /api prefix

### Database Migration for Collections

- [x] T104 [US1] Create Alembic migration backend/src/db/migrations/versions/001_initial_collections.py with connectors, collections tables, enums, indexes, foreign keys

### Frontend - Connector Components (NEW - addresses architectural gap)

- [x] T105 [P] [US1] Create frontend/src/services/api.js with Axios instance configured for http://localhost:8000/api
- [x] T106 [P] [US1] Create frontend/src/services/connectors.js with API calls (listConnectors, createConnector, getConnector, updateConnector, deleteConnector, testConnector)
- [x] T107 [P] [US1] Create frontend/src/hooks/useConnectors.js with React hook for connector state (fetch, create, update, delete)
- [x] T108 Create frontend/src/components/connectors/ConnectorList.jsx displaying connectors with type badges, active status, last_validated timestamp, action buttons
- [x] T109 In frontend/src/components/connectors/ConnectorList.jsx, add filters for type (S3, GCS, SMB) and active_only with URL query params
- [x] T110 In frontend/src/components/connectors/ConnectorList.jsx, add delete confirmation dialog with warning if collections reference connector
- [x] T111 Create frontend/src/components/connectors/ConnectorForm.jsx with fields (name, type, credentials based on type, metadata)
- [x] T112 In frontend/src/components/connectors/ConnectorForm.jsx, add dynamic credential input fields based on connector type (S3: access_key_id/secret_access_key/region, GCS: service_account_json, SMB: server/share/username/password)
- [x] T113 In frontend/src/components/connectors/ConnectorForm.jsx, add test connection button calling POST /connectors/{id}/test with real-time feedback
- [x] T114 In frontend/src/components/connectors/ConnectorForm.jsx, add credential validation with helpful error messages (minimum lengths, required fields)
- [x] T115 Create frontend/src/pages/ConnectorsPage.jsx with ConnectorList, create/edit modals using ConnectorForm
- [x] T116 In frontend/src/pages/ConnectorsPage.jsx, add active/inactive toggle with confirmation for collections in use
- [x] T117 In frontend/src/App.jsx, add route /connectors → ConnectorsPage
- [x] T118 In frontend/src/App.jsx, add navigation link to Connectors page in sidebar/header

### Frontend - Collection Components

- [x] T118a [P] [US1] Create frontend/src/services/collections.js with API calls (listCollections, createCollection, getCollection, updateCollection, deleteCollection, testCollection, refreshCollection)
- [x] T118b [P] [US1] Create frontend/src/hooks/useCollections.js with React hook for collection state (fetch, create, update, delete)
- [x] T118c Create frontend/src/components/collections/CollectionList.jsx displaying collections with state badges, accessibility status, action buttons
- [x] T118d In frontend/src/components/collections/CollectionList.jsx, add filters for state, type, accessible_only with URL query params
- [x] T118e In frontend/src/components/collections/CollectionList.jsx, add delete confirmation dialog showing result/job counts if exists
- [x] T118f Create frontend/src/components/collections/CollectionForm.jsx with fields (name, type, location, state, connector_id, cache_ttl, metadata)
- [x] T118g In frontend/src/components/collections/CollectionForm.jsx, add connector selection dropdown - local collections = no connector, remote collections = select from existing connectors (from useConnectors hook)
- [x] T118h In frontend/src/components/collections/CollectionForm.jsx, add "Create New Connector" button that opens ConnectorForm modal inline for convenience
- [x] T118i In frontend/src/components/collections/CollectionForm.jsx, add test connection button calling POST /collections/{id}/test
- [x] T118j [P] [US1] Create frontend/src/components/collections/CollectionStatus.jsx showing accessibility status with actionable error messages
- [x] T118k Create frontend/src/pages/CollectionsPage.jsx with CollectionList, create/edit modals using CollectionForm
- [x] T118l In frontend/src/pages/CollectorsPage.jsx, add manual refresh button with confirmation dialog if file count > threshold
- [x] T118m In frontend/src/App.jsx, add route /collections → CollectionsPage

### Phase 3 Frontend Testing (Constitution Compliance)

- [x] T118n [P] Create frontend/tests/setup.js with Jest configuration, React Testing Library setup, MSW server configuration, jest-dom matchers
- [x] T118o [P] Update frontend/package.json with test dependencies (jest ^29.0.0, @testing-library/react ^14.0.0, @testing-library/jest-dom ^6.0.0, @testing-library/user-event ^14.0.0, msw ^2.0.0)
- [x] T118p [P] Create frontend/tests/mocks/handlers.js with MSW API mocks (GET/POST/PUT/DELETE /connectors, GET/POST/PUT/DELETE /collections, POST /connectors/{id}/test)
- [x] T118q [P] Create frontend/tests/mocks/server.js with MSW server setup (setupServer, handlers export, beforeAll/afterEach/afterAll hooks)
- [x] T118r Create frontend/tests/hooks/useConnectors.test.js with hook tests (fetch on mount, createConnector success, updateConnector, deleteConnector, error handling for 409 delete protection)
- [x] T118s Create frontend/tests/hooks/useCollections.test.js with hook tests (fetch with filters, createCollection with connector validation, deleteCollection with result/job checks)
- [x] T118t Create frontend/tests/components/ConnectorForm.test.js with component tests (render, type selection shows correct credential fields S3/GCS/SMB, credential validation min lengths, test connection button click)
- [x] T118u In frontend/tests/components/ConnectorForm.test.js, add integration test (fill form → submit → verify MSW API call → verify success callback)
- [x] T118v Create frontend/tests/components/CollectionForm.test.js with component tests (connector dropdown for remote types, LOCAL type hides connector field, test connection button, cache TTL validation)
- [x] T118w Create frontend/tests/components/ConnectorList.test.js with component tests (render list, type filter, active_only filter, delete button shows confirmation, delete protection error message display)
- [x] T118x Create frontend/tests/integration/connector-collection-flow.test.js testing full user flow (create connector → verify in list → create collection referencing connector → attempt delete connector → see 409 error message → delete collection → delete connector succeeds)

**Checkpoint**: User Story 1 complete - users can manage connectors and collections through web UI with credential encryption, delete protection, and cache management. Frontend test coverage >75%.

**Note**: Tasks T094a-T094l (Connector schemas/API) and T106-T118x (Connector/Collection frontend + testing) were added to address critical architectural gap - Connector CRUD endpoints and frontend were missing from initial design

---

## Phase 3.5: Testing Phase 2-3 Implementation (CRITICAL - Constitution Compliance)

**Purpose**: Achieve >80% test coverage for all code implemented in Phase 2 (Foundational) and Phase 3 (User Story 1) to comply with project constitution

**Rationale**: Constitution requires "comprehensive test coverage (target >80% for core logic)" with tests written "alongside implementation". This phase addresses the gap before proceeding with Phase 4.

**Independent Test**: Run pytest with coverage report, verify >80% coverage for services, utils, models, API endpoints

### Core Infrastructure Tests (Phase 2)

- [x] T104a [P] Create backend/tests/unit/test_crypto.py with CredentialEncryptor tests (encrypt/decrypt roundtrip, master key validation, invalid key handling, UTF-8 support)
- [x] T104b [P] Create backend/tests/unit/test_cache.py with FileListingCache tests (get/set/invalidate/clear, TTL expiry logic, concurrent access with threading, state-based TTL defaults)
- [x] T104c [P] Create backend/tests/unit/test_job_queue.py with JobQueue tests (enqueue/dequeue FIFO, get_position, cancel, concurrent access, job status transitions)
- [ ] T104d [P] **DEFERRED TO PHASE 4** Create backend/tests/unit/test_pipeline_processor.py with StructureValidator tests (cycle detection, orphaned nodes, dead ends, node-specific constraints, processing_method validation) - *Blocked by: Phase 4 CLI Tool Database Integration - need unified YAML/database config handling*
- [ ] T104e [P] **DEFERRED TO PHASE 4** In backend/tests/unit/test_pipeline_processor.py, add FilenamePreviewGenerator tests (all paths generation, property transformations, multiple branches, pairing separators) - *Blocked by: Phase 4 CLI Tool Database Integration*
- [ ] T104f [P] **DEFERRED TO PHASE 4** In backend/tests/unit/test_pipeline_processor.py, add CollectionValidator tests (file grouping, expected files, status determination: CONSISTENT/PARTIAL/INCONSISTENT) - *Blocked by: Phase 4 CLI Tool Database Integration*

### Storage Adapter Tests

- [x] T104g [P] Create backend/tests/unit/test_s3_adapter.py with S3Adapter tests using mocked boto3 (list_files with pagination, test_connection success/failure, retry logic, credential validation)
- [x] T104h [P] Create backend/tests/unit/test_gcs_adapter.py with GCSAdapter tests using mocked google-cloud-storage (list_files, test_connection, service account validation, error handling)
- [x] T104i [P] Create backend/tests/unit/test_smb_adapter.py with SMBAdapter tests using mocked smbprotocol (list_files, test_connection, credential validation, network error handling)

### Service Layer Tests

- [x] T104j Create backend/tests/unit/test_connector_service.py with ConnectorService tests (create with encryption, get with decryption, list with filters, update with re-encryption)
- [x] T104k In backend/tests/unit/test_connector_service.py, add delete_connector tests (success when no collections, ValueError when collections exist, collection count check)
- [x] T104l In backend/tests/unit/test_connector_service.py, add test_connector tests (adapter selection by type, last_validated update on success, last_error update on failure)
- [x] T104m Create backend/tests/unit/test_collection_service.py with CollectionService tests (create with accessibility test, get with connector details, list with filters, update with cache invalidation)
- [x] T104n In backend/tests/unit/test_collection_service.py, add delete_collection tests (check for analysis_results, check for active jobs, force flag behavior)
- [x] T104o In backend/tests/unit/test_collection_service.py, add get_collection_files tests (cache hit/miss logic, TTL expiry, state-based TTL selection)

### Model Validation Tests

- [x] T104p [P] Create backend/tests/unit/test_models.py with Connector model tests (unique name constraint, type enum validation, is_active default, relationship to collections)
- [x] T104q [P] In backend/tests/unit/test_models.py, add Collection model tests (connector_id validation by type, state enum, get_effective_cache_ttl with user override and defaults)
- [x] T104r [P] In backend/tests/unit/test_models.py, add schema validation tests for CollectionCreate (LOCAL rejects connector_id, remote types require connector_id, connector_id >= 1)

### API Endpoint Tests

- [x] T104s Create backend/tests/unit/test_api_connectors.py with Connector API tests (POST creates and returns 201, GET list with type filter, GET by ID returns 404 if not found)
- [x] T104t In backend/tests/unit/test_api_connectors.py, add PUT tests (update name/metadata, 409 on duplicate name, credential re-encryption)
- [x] T104u In backend/tests/unit/test_api_connectors.py, add DELETE tests (204 when no collections, 409 when collections exist with descriptive message, protection logic)
- [x] T104v In backend/tests/unit/test_api_connectors.py, add POST /test tests (success/failure responses, last_validated/last_error updates)
- [x] T104w Create backend/tests/unit/test_api_collections.py with Collection API tests (POST creates with accessibility test, GET list with state/type/accessible filters, DELETE with result/job checks)
- [x] T104x In backend/tests/unit/test_api_collections.py, add POST /test and /refresh tests (accessibility status, file count warnings, cache invalidation on refresh)

### Integration Tests

- [x] T104y Create backend/tests/integration/test_connector_collection_flow.py testing full flow (create connector → create collection → delete connector fails with 409 → delete collection → delete connector succeeds)
- [x] T104z In backend/tests/integration/test_connector_collection_flow.py, add remote collection accessibility test (create S3 connector with invalid creds → create collection → verify is_accessible=false and last_error populated)

### Test Infrastructure

- [x] T104aa [P] Create backend/tests/conftest.py with pytest fixtures (test database session, in-memory cache, mock encryptor with test key, sample connector/collection factories)
- [x] T104ab [P] In backend/tests/conftest.py, add fixtures for mocked storage adapters (mock_s3_client, mock_gcs_client, mock_smb_connection)
- [x] T104ac [P] Update backend/requirements.txt with test dependencies (pytest-cov, pytest-mock, pytest-asyncio, freezegun for time-based tests)
- [x] T104ad Create backend/.coveragerc with coverage configuration (exclude migrations, __init__.py, target 80% minimum)
- [ ] T104ae Update backend/README.md with testing instructions (pytest commands, coverage reporting, test organization)

**Checkpoint**: Comprehensive test coverage achieved (>80%) for Phase 2-3 code - safe to proceed with Phase 4

**Constitution Compliance**: This phase satisfies "comprehensive test coverage (target >80% for core logic)" requirement from Architecture Principles section 2

---

## Phase 4: User Story 2 - Execute Analysis Tools and Store Results (Priority: P1)

**Goal**: Run PhotoStats, Photo Pairing, and Pipeline Validation on collections with persistent storage of results and HTML reports

**Independent Test**: Run PhotoStats on a collection, navigate away, return to view stored results without re-running

### Backend - AnalysisResult Model

- [ ] T119 [P] [US2] Create backend/src/models/analysis_result.py with ToolType enum (PHOTOSTATS, PHOTO_PAIRING, PIPELINE_VALIDATION)
- [ ] T120 [P] [US2] In backend/src/models/analysis_result.py, create AnalysisStatus enum (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
- [ ] T121 [US2] In backend/src/models/analysis_result.py, create AnalysisResult model (id, collection_id, pipeline_id, tool, job_id, status, executed_at, started_at, completed_at, results, schema_version, report_html, error_message, progress)
- [ ] T122 [US2] In backend/src/models/analysis_result.py, add foreign keys to collections(id) CASCADE, pipelines(id) SET NULL
- [ ] T123 [US2] In backend/src/models/analysis_result.py, add indexes on collection_id, tool, status, job_id, executed_at DESC, GIN index on results JSONB
- [ ] T124 [US2] In backend/src/models/analysis_result.py, add relationships to Collection and Pipeline

### Backend - Tool Execution Service

- [ ] T125 Create backend/src/services/tool_service.py with ToolService class
- [ ] T126 In backend/src/services/tool_service.py, implement enqueue_analysis(collection_id, tool, pipeline_id) creating AnalysisJob and calling JobQueue.enqueue()
- [ ] T127 In backend/src/services/tool_service.py, implement process_job_queue() async worker function dequeuing jobs and calling run_analysis_tool()
- [ ] T128 In backend/src/services/tool_service.py, implement run_analysis_tool(job) dispatching to PhotoStats, Photo Pairing, or Pipeline Validation
- [ ] T129 In backend/src/services/tool_service.py, implement run_photostats(job) calling existing photo_stats.py logic, updating job.progress, storing results
- [ ] T130 In backend/src/services/tool_service.py, implement run_photo_pairing(job) calling existing photo_pairing.py logic, updating job.progress, storing results
- [ ] T131 In backend/src/services/tool_service.py, implement run_pipeline_validation(job) using CollectionValidator and ReadinessCalculator from utils/pipeline_processor.py
- [ ] T132 In backend/src/services/tool_service.py, implement store_analysis_result(job, results) creating AnalysisResult with JSONB results and pre-generated report_html
- [ ] T133 In backend/src/services/tool_service.py, implement generate_html_report(tool, results) using existing Jinja2 templates (templates/photostats.html.j2, photo_pairing.html.j2)
- [ ] T134 In backend/src/services/tool_service.py, implement get_job_status(job_id) returning job progress and status
- [ ] T135 In backend/src/services/tool_service.py, add error handling for network failures, collection inaccessibility, partial progress discard (FR-040)

### Backend - Results Service

- [ ] T136 Create backend/src/services/result_service.py with ResultService class
- [ ] T137 In backend/src/services/result_service.py, implement list_results(collection_id, tool, status, date_from, date_to, limit, offset) with pagination
- [ ] T138 In backend/src/services/result_service.py, implement get_result(id) returning AnalysisResult with full details
- [ ] T139 In backend/src/services/result_service.py, implement delete_result(id)
- [ ] T140 In backend/src/services/result_service.py, implement get_result_report(id) returning pre-generated report_html from database

### Backend - Pydantic Schemas for Tools

- [ ] T141 [P] [US2] Create backend/src/schemas/analysis.py with AnalysisRequest schema (collection_id, pipeline_id)
- [ ] T142 [P] [US2] In backend/src/schemas/analysis.py, create JobResponse schema (message, job_id, position, estimated_start_minutes)
- [ ] T143 [P] [US2] In backend/src/schemas/analysis.py, create JobStatusResponse schema (job_id, status, progress, result_id, error_message)
- [ ] T144 [P] [US2] In backend/src/schemas/analysis.py, create AnalysisResultResponse schema (id, collection_id, collection_name, pipeline_id, pipeline_name, tool, job_id, status, executed_at, started_at, completed_at, results, schema_version, error_message)

### Backend - API Endpoints for Tools

- [ ] T145 Create backend/src/api/tools.py with FastAPI router
- [ ] T146 [P] [US2] In backend/src/api/tools.py, implement POST /tools/photostats with AnalysisRequest, enqueue job, return 202 with JobResponse
- [ ] T147 [P] [US2] In backend/src/api/tools.py, implement POST /tools/photo_pairing with AnalysisRequest, enqueue job, return 202 with JobResponse
- [ ] T148 [P] [US2] In backend/src/api/tools.py, implement POST /tools/pipeline_validation with AnalysisRequest (with pipeline_id), enqueue job, return 202 with JobResponse
- [ ] T149 [P] [US2] In backend/src/api/tools.py, implement GET /tools/status/{job_id} returning JobStatusResponse
- [ ] T150 [US2] In backend/src/api/tools.py, add BackgroundTasks dependency to start process_job_queue() worker on first job enqueue
- [ ] T151 [US2] In backend/src/main.py, register tools router with /api prefix

### Backend - WebSocket for Progress Updates (from research.md Task 6)

- [ ] T152 In backend/src/api/tools.py, implement WebSocket endpoint /tools/progress/{job_id}
- [ ] T153 In backend/src/api/tools.py, send initial status event on WebSocket connect (job_id, status, position)
- [ ] T154 In backend/src/api/tools.py, implement progress polling loop (1 second interval) sending progress events while job running
- [ ] T155 In backend/src/api/tools.py, send complete event with result_id on job completion, close WebSocket
- [ ] T156 In backend/src/api/tools.py, send error event with error_message on job failure, close WebSocket
- [ ] T157 In backend/src/api/tools.py, send cancelled event on job cancellation, close WebSocket
- [ ] T158 In backend/src/api/tools.py, handle WebSocket disconnect gracefully (job continues in background)

### Backend - API Endpoints for Results

- [ ] T159 Create backend/src/api/results.py with FastAPI router
- [ ] T160 [P] [US2] In backend/src/api/results.py, implement GET /results with filters (collection_id, tool, status, date_from, date_to, limit, offset) returning paginated AnalysisResultResponse list
- [ ] T161 [P] [US2] In backend/src/api/results.py, implement GET /results/{id} returning AnalysisResultResponse or 404
- [ ] T162 [P] [US2] In backend/src/api/results.py, implement DELETE /results/{id} returning 204 or 404
- [ ] T163 [P] [US2] In backend/src/api/results.py, implement GET /results/{id}/report returning HTML report with download option (Content-Disposition header)
- [ ] T164 [US2] In backend/src/main.py, register results router with /api prefix

### Database Migration for Analysis Results

- [ ] T165 [US2] Create Alembic migration backend/src/db/migrations/versions/002_analysis_results.py with analysis_results table, enums, indexes, foreign keys

### Frontend - Tool Execution Components

- [ ] T166 [P] [US2] Create frontend/src/services/tools.js with API calls (runPhotoStats, runPhotoPairing, runPipelineValidation, getJobStatus)
- [ ] T167 [P] [US2] Create frontend/src/services/websocket.js with WebSocket client class for progress monitoring
- [ ] T168 [P] [US2] Create frontend/src/hooks/useAnalysisProgress.js with React hook for WebSocket progress updates (status, progress, error handling)
- [ ] T169 Create frontend/src/components/tools/ToolSelector.jsx with buttons for PhotoStats, Photo Pairing, Pipeline Validation (per collection)
- [ ] T170 In frontend/src/components/tools/ToolSelector.jsx, add pipeline selection dropdown for Pipeline Validation (show active pipeline by default)
- [ ] T171 Create frontend/src/components/tools/ProgressMonitor.jsx displaying real-time progress (files_scanned, issues_found, stage, percent_complete) using useAnalysisProgress hook
- [ ] T172 In frontend/src/components/tools/ProgressMonitor.jsx, add queue position display for pending jobs ("Position: 2. Estimated start: 10 minutes")
- [ ] T173 In frontend/src/components/tools/ProgressMonitor.jsx, add completion notification with "View Report" link to /results/{result_id}
- [ ] T174 In frontend/src/components/tools/ProgressMonitor.jsx, add error display with actionable guidance and retry button
- [ ] T175 Create frontend/src/pages/ToolsPage.jsx with collection selector, ToolSelector, ProgressMonitor
- [ ] T176 In frontend/src/App.jsx, add route /tools → ToolsPage

### Frontend - Results Components

- [ ] T177 [P] [US2] Create frontend/src/services/results.js with API calls (listResults, getResult, deleteResult, getReport)
- [ ] T178 Create frontend/src/components/results/ResultList.jsx displaying results with filters (collection, tool, status, date range)
- [ ] T179 In frontend/src/components/results/ResultList.jsx, add sort by executed_at DESC, pagination (limit 50, offset controls)
- [ ] T180 In frontend/src/components/results/ResultList.jsx, add quick summary display (tool type, status, timestamp, collection name)
- [ ] T181 Create frontend/src/components/results/ReportViewer.jsx displaying HTML report in iframe with download button
- [ ] T182 Create frontend/src/pages/ResultsPage.jsx with ResultList, result detail view, ReportViewer
- [ ] T183 In frontend/src/App.jsx, add route /results → ResultsPage
- [ ] T184 In frontend/src/App.jsx, add route /results/{id} → ResultsPage with detail view

### CLI Tool Database Integration (from research.md Task 8)

- [ ] T185 Extend utils/config_manager.py PhotoAdminConfig with database connection support (db_url parameter or PHOTO_ADMIN_DB_URL env var)
- [ ] T186 In utils/config_manager.py, implement _load_from_database(db_url) using SQLAlchemy NullPool to fetch Configuration rows
- [ ] T187 In utils/config_manager.py, add fallback logic: try database first, fall back to YAML if unavailable, print warning on fallback
- [ ] T188 In utils/config_manager.py, add config_source property returning "database" or "yaml" for debugging
- [ ] T189 In utils/config_manager.py, update ensure_camera_mapping() to save to database if source=database, else YAML
- [ ] T190 In utils/config_manager.py, update ensure_processing_method() to save to database if source=database, else YAML
- [ ] T191 Update photo_stats.py to use PhotoAdminConfig() with automatic database-first fallback (no code changes needed)
- [ ] T192 Update photo_pairing.py to use PhotoAdminConfig() with automatic database-first fallback (no code changes needed)

### Phase 4 Testing (Constitution Compliance)

- [ ] T192a [P] Create backend/tests/unit/test_tool_service.py with ToolService tests (enqueue_analysis, process_job_queue, run_analysis_tool dispatch, progress updates, error handling)
- [ ] T192b [P] Create backend/tests/unit/test_result_service.py with ResultService tests (list_results with pagination/filters, get_result, delete_result, get_result_report)
- [ ] T192c [P] Create backend/tests/unit/test_api_tools.py with Tools API tests (POST /photostats enqueue, POST /photo_pairing enqueue, GET /status/{job_id}, WebSocket connection/disconnect)
- [ ] T192d [P] Create backend/tests/unit/test_api_results.py with Results API tests (GET /results with filters, GET /results/{id}, DELETE /results/{id}, GET /results/{id}/report HTML download)
- [ ] T192e [P] Create backend/tests/unit/test_analysis_result_model.py with AnalysisResult model tests (tool enum, status enum, JSONB results validation, schema_version, relationships)
- [ ] T192f [P] In backend/tests/unit/test_tool_service.py, add HTML report generation tests (generate_html_report using Jinja2 templates, pre-generated report_html storage)
- [ ] T192g Create backend/tests/integration/test_tool_execution_flow.py testing full flow (create collection → enqueue PhotoStats → monitor progress → job completes → result stored → HTML report accessible)
- [ ] T192h In backend/tests/integration/test_tool_execution_flow.py, add WebSocket progress monitoring test (connect → receive queued event → receive running events → receive complete event)
- [ ] T192i In backend/tests/integration/test_tool_execution_flow.py, add error handling test (network failure during tool run → partial progress discarded → error_message stored)
- [ ] T192j [P] Update backend/.coveragerc to include new Phase 4 modules (tool_service, result_service, api/tools, api/results, models/analysis_result)

### Phase 4 Frontend Testing (Constitution Compliance)

- [ ] T192k [P] Create frontend/tests/hooks/useAnalysisProgress.test.js with WebSocket hook tests (connection establishment, progress event updates, completion event, error event, disconnect handling, reconnect logic)
- [ ] T192l [P] Create frontend/tests/components/ToolSelector.test.js with component tests (PhotoStats button click, Photo Pairing button click, Pipeline Validation with pipeline dropdown, disabled state when no collection selected)
- [ ] T192m Create frontend/tests/components/ProgressMonitor.test.js with component tests (display progress percentage, files_scanned count, queue position display, completion notification with View Report link, error display with retry button)
- [ ] T192n Create frontend/tests/components/ResultList.test.js with component tests (render results list, collection filter, tool filter, status filter, date range filter, pagination controls, sort by executed_at DESC)
- [ ] T192o [P] Create frontend/tests/components/ReportViewer.test.js with component tests (iframe src set to report URL, download button click, HTML report content display)
- [ ] T192p Create frontend/tests/integration/tool-execution-flow.test.js testing full user flow (select collection → click PhotoStats → WebSocket connection established → receive progress updates → job completes → navigate to results → view HTML report)
- [ ] T192q [P] Update frontend/tests/mocks/handlers.js with Phase 4 API mocks (POST /tools/photostats, POST /tools/photo_pairing, GET /tools/status/{job_id}, GET /results, GET /results/{id}, GET /results/{id}/report, WebSocket mock)

**Checkpoint**: User Story 2 complete - users can run analysis tools, monitor progress via WebSocket, and view stored results with HTML reports. Backend test coverage >80%, frontend test coverage >75%.

---

## Phase 5: User Story 3 - Configure Photo Processing Pipelines Through Forms (Priority: P2)

**Goal**: Create and edit pipelines through web forms with validation, filename preview, and activation management

**Independent Test**: Create pipeline through forms, validate structure, activate it, verify Pipeline Validation tool uses it

### Backend - Pipeline Model

- [ ] T193 Create backend/src/models/pipeline.py with Pipeline model (id, name, description, config, is_active, version, created_at, updated_at)
- [ ] T194 In backend/src/models/pipeline.py, create PipelineHistory model (id, pipeline_id, version, config, changed_at, change_notes)
- [ ] T195 In backend/src/models/pipeline.py, add unique constraint on name, index on is_active
- [ ] T196 In backend/src/models/pipeline.py, add relationship to PipelineHistory (one-to-many, cascade delete)
- [ ] T197 In backend/src/models/pipeline.py, add relationship to AnalysisResult (one-to-many, nullable foreign key)

### Backend - Pipeline Service

- [ ] T198 Create backend/src/services/pipeline_service.py with PipelineService class
- [ ] T199 In backend/src/services/pipeline_service.py, implement create_pipeline(name, description, config) with structure validation using StructureValidator
- [ ] T200 In backend/src/services/pipeline_service.py, implement get_pipeline(id) returning Pipeline with config
- [ ] T201 In backend/src/services/pipeline_service.py, implement list_pipelines() sorted by updated_at DESC
- [ ] T202 In backend/src/services/pipeline_service.py, implement update_pipeline(id, name, description, config, change_notes) creating PipelineHistory entry, incrementing version
- [ ] T203 In backend/src/services/pipeline_service.py, implement delete_pipeline(id)
- [ ] T204 In backend/src/services/pipeline_service.py, implement validate_pipeline_structure(config) using StructureValidator, return errors list
- [ ] T205 In backend/src/services/pipeline_service.py, implement activate_pipeline(id) setting is_active=True, deactivating others (only one active per FR-030)
- [ ] T206 In backend/src/services/pipeline_service.py, implement get_active_pipeline() returning currently active pipeline or None
- [ ] T207 In backend/src/services/pipeline_service.py, implement preview_filenames(id, camera_id, start_counter) using FilenamePreviewGenerator
- [ ] T208 In backend/src/services/pipeline_service.py, implement get_pipeline_history(id) returning PipelineHistory entries sorted by version DESC
- [ ] T209 In backend/src/services/pipeline_service.py, implement import_pipeline_yaml(yaml_file) parsing YAML and creating Pipeline
- [ ] T210 In backend/src/services/pipeline_service.py, implement export_pipeline_yaml(id) returning YAML string matching existing schema

### Backend - Pydantic Schemas for Pipelines

- [ ] T211 [P] [US3] Create backend/src/schemas/pipeline.py with PipelineNode schema (type, properties) with enum [Capture, File, Process, Pairing, Branching, Termination]
- [ ] T212 [P] [US3] In backend/src/schemas/pipeline.py, create PipelineEdge schema (source, target)
- [ ] T213 [P] [US3] In backend/src/schemas/pipeline.py, create PipelineConfig schema (nodes: Dict[str, PipelineNode], edges: List[PipelineEdge])
- [ ] T214 [P] [US3] In backend/src/schemas/pipeline.py, create PipelineCreate schema (name, description, config) with validation
- [ ] T215 [P] [US3] In backend/src/schemas/pipeline.py, create PipelineUpdate schema (name, description, config, change_notes)
- [ ] T216 [P] [US3] In backend/src/schemas/pipeline.py, create PipelineResponse schema (id, name, description, config, is_active, version, created_at, updated_at)
- [ ] T217 [P] [US3] In backend/src/schemas/pipeline.py, create ValidationErrorResponse schema (node_id, error_type, message, guidance)

### Backend - API Endpoints for Pipelines

- [ ] T218 Create backend/src/api/pipelines.py with FastAPI router
- [ ] T219 [P] [US3] In backend/src/api/pipelines.py, implement GET /pipelines returning PipelineResponse list sorted by updated_at DESC
- [ ] T220 [P] [US3] In backend/src/api/pipelines.py, implement POST /pipelines with PipelineCreate, validation, return 201 with PipelineResponse or 400 with validation errors
- [ ] T221 [P] [US3] In backend/src/api/pipelines.py, implement GET /pipelines/{id} returning PipelineResponse or 404
- [ ] T222 [P] [US3] In backend/src/api/pipelines.py, implement PUT /pipelines/{id} with PipelineUpdate, validation, version increment, return 200 or 400/404
- [ ] T223 [P] [US3] In backend/src/api/pipelines.py, implement DELETE /pipelines/{id} returning 204 or 404
- [ ] T224 [P] [US3] In backend/src/api/pipelines.py, implement POST /pipelines/{id}/validate returning validation result (valid: bool, errors: List[ValidationErrorResponse])
- [ ] T225 [P] [US3] In backend/src/api/pipelines.py, implement POST /pipelines/{id}/activate setting is_active=True, deactivating others, return 200 with previous_active_id
- [ ] T226 [P] [US3] In backend/src/api/pipelines.py, implement GET /pipelines/{id}/preview with query params (camera_id, start_counter) returning filename list
- [ ] T227 [P] [US3] In backend/src/api/pipelines.py, implement GET /pipelines/{id}/history returning PipelineHistoryEntry list
- [ ] T228 [P] [US3] In backend/src/api/pipelines.py, implement GET /pipelines/{id}/export returning YAML file (Content-Type: application/x-yaml)
- [ ] T229 [P] [US3] In backend/src/api/pipelines.py, implement POST /pipelines/import with multipart file upload, return 201 with PipelineResponse or 400
- [ ] T230 [US3] In backend/src/main.py, register pipelines router with /api prefix

### Database Migration for Pipelines

- [ ] T231 [US3] Create Alembic migration backend/src/db/migrations/versions/003_pipelines.py with pipelines, pipeline_history tables, indexes, unique constraints

### Frontend - Pipeline Components

- [ ] T232 [P] [US3] Create frontend/src/services/pipelines.js with API calls (listPipelines, createPipeline, getPipeline, updatePipeline, deletePipeline, validatePipeline, activatePipeline, previewFilenames, getHistory, exportPipeline, importPipeline)
- [ ] T233 Create frontend/src/components/pipelines/PipelineList.jsx displaying pipelines with active badge, version, action buttons (edit, activate, export, delete)
- [ ] T234 In frontend/src/components/pipelines/PipelineList.jsx, add activate button calling POST /pipelines/{id}/activate with confirmation dialog
- [ ] T235 Create frontend/src/components/pipelines/PipelineFormEditor.jsx with form fields (name, description)
- [ ] T236 In frontend/src/components/pipelines/PipelineFormEditor.jsx, add node management UI (add/remove nodes by type with properties)
- [ ] T237 In frontend/src/components/pipelines/PipelineFormEditor.jsx, add edge management UI (connect nodes with source/target selectors)
- [ ] T238 In frontend/src/components/pipelines/PipelineFormEditor.jsx, integrate with NodeEditor component for property editing
- [ ] T239 Create frontend/src/components/pipelines/NodeEditor.jsx with type-specific property forms (Capture: none, File: extension, Process: processing_method, Pairing: separator, Branching: branch_type, Termination: termination_type)
- [ ] T240 In frontend/src/components/pipelines/NodeEditor.jsx, add processing_method validation against database configuration (interactive prompt if unknown)
- [ ] T241 In frontend/src/components/pipelines/PipelineFormEditor.jsx, add validate button calling POST /pipelines/{id}/validate, display errors with node highlighting and guidance
- [ ] T242 In frontend/src/components/pipelines/PipelineFormEditor.jsx, add preview button calling GET /pipelines/{id}/preview with camera_id input, display expected filenames
- [ ] T243 In frontend/src/components/pipelines/PipelineFormEditor.jsx, add save button with automatic version increment and change notes input
- [ ] T244 In frontend/src/components/pipelines/PipelineFormEditor.jsx, add export button downloading YAML file
- [ ] T245 Create frontend/src/pages/PipelinesPage.jsx with PipelineList, create/edit modals using PipelineFormEditor
- [ ] T246 In frontend/src/pages/PipelinesPage.jsx, add import button with file upload dialog calling POST /pipelines/import
- [ ] T247 In frontend/src/pages/PipelinesPage.jsx, add version history view showing PipelineHistoryEntry list with change notes
- [ ] T248 In frontend/src/App.jsx, add route /pipelines → PipelinesPage

### Phase 5 Testing (Constitution Compliance)

- [ ] T248a [P] Create backend/tests/unit/test_pipeline_service.py with PipelineService tests (create with structure validation, get, list, update with version increment, delete)
- [ ] T248b [P] In backend/tests/unit/test_pipeline_service.py, add validate_pipeline_structure tests (StructureValidator integration, error list return)
- [ ] T248c [P] In backend/tests/unit/test_pipeline_service.py, add activate_pipeline tests (single active constraint, deactivate others, get_active_pipeline)
- [ ] T248d [P] In backend/tests/unit/test_pipeline_service.py, add preview_filenames tests (FilenamePreviewGenerator integration, camera_id/counter input)
- [ ] T248e [P] In backend/tests/unit/test_pipeline_service.py, add pipeline history tests (get_pipeline_history, PipelineHistory creation on update)
- [ ] T248f [P] In backend/tests/unit/test_pipeline_service.py, add import/export YAML tests (import_pipeline_yaml, export_pipeline_yaml, format compatibility)
- [ ] T248g [P] Create backend/tests/unit/test_api_pipelines.py with Pipeline API tests (POST with validation, GET list, PUT with version increment, DELETE, POST /validate, POST /activate)
- [ ] T248h Create backend/tests/integration/test_pipeline_activation_flow.py testing activation constraint (create pipeline1 → activate → create pipeline2 → activate → verify pipeline1.is_active=false)

### Phase 5 Frontend Testing (Constitution Compliance)

- [ ] T248i [P] Create frontend/tests/components/PipelineFormEditor.test.js with component tests (render, add/remove nodes, add/remove edges, validate button click, error display with node highlighting)
- [ ] T248j [P] Create frontend/tests/components/NodeEditor.test.js with component tests (type selection shows correct property fields, Capture has no properties, File has extension, Process has processing_method, validation against config)
- [ ] T248k Create frontend/tests/components/PipelineList.test.js with component tests (render list, active badge display, activate button with confirmation, export button download, delete button)
- [ ] T248l Create frontend/tests/integration/pipeline-preview-flow.test.js testing preview feature (create pipeline → add nodes/edges → click preview → enter camera_id → see expected filenames list)
- [ ] T248m Create frontend/tests/integration/pipeline-activation-flow.test.js testing activation constraint (create pipeline1 → activate → create pipeline2 → activate → verify only pipeline2 shows active badge)
- [ ] T248n [P] Update frontend/tests/mocks/handlers.js with Phase 5 API mocks (GET/POST/PUT/DELETE /pipelines, POST /pipelines/{id}/validate, POST /pipelines/{id}/activate, GET /pipelines/{id}/preview, GET/POST /pipelines/import)

**Checkpoint**: User Story 3 complete - users can create/edit pipelines through forms with validation, preview, activation. Backend test coverage >80%, frontend test coverage >75%.

---

## Phase 6: User Story 4 - Track Analysis Trends Over Time (Priority: P2)

**Goal**: Display trend charts comparing metrics across multiple analysis executions (orphaned files, camera usage, pipeline validation ratios)

**Independent Test**: Run PhotoStats 3+ times on same collection, view trend chart showing orphaned files over time

### Backend - Trend Analysis Endpoint

- [ ] T249 In backend/src/api/results.py, implement GET /results/trends with query params (collection_id, tool, metric, limit)
- [ ] T250 In backend/src/api/results.py, implement trend data extraction for PhotoStats (orphaned_files_count from results JSONB summary)
- [ ] T251 In backend/src/api/results.py, implement trend data extraction for Photo Pairing (camera_usage from results JSONB camera_groups)
- [ ] T252 In backend/src/api/results.py, implement trend data extraction for Pipeline Validation (CONSISTENT/PARTIAL/INCONSISTENT ratios from results JSONB validation_details)
- [ ] T253 In backend/src/api/results.py, return trend data as array of {executed_at, metric_value, result_id} sorted by executed_at ASC

### Frontend - Trend Visualization Components

- [ ] T254 [P] [US4] Create frontend/src/components/results/TrendChart.jsx with Recharts LineChart component
- [ ] T255 In frontend/src/components/results/TrendChart.jsx, add chart for PhotoStats orphaned files count over time (X: executed_at, Y: orphaned_files_count)
- [ ] T256 In frontend/src/components/results/TrendChart.jsx, add chart for Photo Pairing camera usage distribution (multi-line chart per camera)
- [ ] T257 In frontend/src/components/results/TrendChart.jsx, add chart for Pipeline Validation consistency ratios (stacked area chart: CONSISTENT/PARTIAL/INCONSISTENT)
- [ ] T258 In frontend/src/components/results/TrendChart.jsx, add tooltip on hover showing execution date, metric value, link to full report
- [ ] T259 In frontend/src/components/results/TrendChart.jsx, add date range filter with start/end date pickers
- [ ] T260 In frontend/src/components/results/TrendChart.jsx, add collection comparison mode (multiple collections on same chart with legend)
- [ ] T261 In frontend/src/pages/ResultsPage.jsx, add "Trends" tab with TrendChart component and collection/tool/metric selectors

### Phase 6 Testing (Constitution Compliance)

- [ ] T261a [P] Create backend/tests/unit/test_api_results_trends.py with trend endpoint tests (GET /results/trends with metric extraction for PhotoStats, Photo Pairing, Pipeline Validation)
- [ ] T261b [P] In backend/tests/unit/test_api_results_trends.py, add JSONB query tests (verify GIN index usage, metric extraction from results.summary, results.camera_groups, results.validation_details)
- [ ] T261c Create backend/tests/integration/test_trend_data_flow.py testing multi-execution trend (run PhotoStats 3 times → query trends → verify chronological data with executed_at/metric_value pairs)

### Phase 6 Frontend Testing (Constitution Compliance)

- [ ] T261d [P] Create frontend/tests/components/TrendChart.test.js with component tests (render chart, PhotoStats orphaned files line chart, Photo Pairing multi-line camera usage, Pipeline Validation stacked area chart)
- [ ] T261e In frontend/tests/components/TrendChart.test.js, add interaction tests (tooltip on hover shows date/value, date range filter updates chart, collection comparison shows legend)
- [ ] T261f [P] Update frontend/tests/mocks/handlers.js with Phase 6 API mocks (GET /results/trends with query params collection_id/tool/metric/limit)

**Checkpoint**: User Story 4 complete - users can view trend analysis across multiple executions. Backend test coverage >80%, frontend test coverage >75%.

---

## Phase 7: User Story 5 - Migrate Existing Configuration to Database (Priority: P3)

**Goal**: Import existing YAML configuration (config/config.yaml) into database with conflict resolution UI

**Independent Test**: Import config.yaml with conflicting keys, resolve conflicts through UI, verify CLI tools read from database

### Backend - Configuration Model

- [ ] T262 Create backend/src/models/configuration.py with Configuration model (id, key, value, description, updated_at)
- [ ] T263 In backend/src/models/configuration.py, add unique constraint on key

### Backend - Configuration Service

- [ ] T264 Create backend/src/services/config_service.py with ConfigService class
- [ ] T265 In backend/src/services/config_service.py, implement get_config() returning all Configuration rows as dict (key → value)
- [ ] T266 In backend/src/services/config_service.py, implement update_config(updates) upserting Configuration rows for each key
- [ ] T267 In backend/src/services/config_service.py, implement import_yaml_config(yaml_file) detecting conflicts with existing database config
- [ ] T268 In backend/src/services/config_service.py, implement detect_conflicts(db_config, yaml_config) comparing keys recursively for nested objects (camera_mappings)
- [ ] T269 In backend/src/services/config_service.py, create ConfigConflict dataclass (key, db_value, yaml_value, type) for conflict resolution
- [ ] T270 In backend/src/services/config_service.py, implement store_pending_import(session_id, yaml_config, conflicts) in-memory session storage with 1-hour expiry
- [ ] T271 In backend/src/services/config_service.py, implement apply_yaml_config_with_resolution(session_id, selections) merging based on user selections
- [ ] T272 In backend/src/services/config_service.py, implement export_yaml_config() returning YAML string matching original config.yaml format

### Backend - Pydantic Schemas for Configuration

- [ ] T273 [P] [US5] Create backend/src/schemas/config.py with ConfigConflict schema (key, db_value, yaml_value, type)
- [ ] T274 [P] [US5] In backend/src/schemas/config.py, create ConfigImportResponse schema (status, session_id, conflicts) for oneOf (success | conflicts)
- [ ] T275 [P] [US5] In backend/src/schemas/config.py, create ConflictResolution schema (session_id, selections: Dict[str, Literal["database", "yaml"]])

### Backend - API Endpoints for Configuration

- [ ] T276 Create backend/src/api/config.py with FastAPI router
- [ ] T277 [P] [US5] In backend/src/api/config.py, implement GET /config returning configuration dict (photo_extensions, metadata_extensions, camera_mappings, processing_methods)
- [ ] T278 [P] [US5] In backend/src/api/config.py, implement PUT /config with updates dict, return 200 with updated_keys list
- [ ] T279 [P] [US5] In backend/src/api/config.py, implement POST /config/import with multipart file upload (YAML), detect conflicts, return ConfigImportResponse
- [ ] T280 [US5] In backend/src/api/config.py, implement POST /config/resolve with ConflictResolution, apply selections, delete session, return 200 or 404 if session expired
- [ ] T281 [P] [US5] In backend/src/api/config.py, implement GET /config/export returning YAML file (Content-Type: application/x-yaml, Content-Disposition: attachment)
- [ ] T282 [US5] In backend/src/main.py, register config router with /api prefix

### Database Migration for Configuration

- [ ] T283 [US5] Create Alembic migration backend/src/db/migrations/versions/004_configuration.py with configurations table, unique constraint on key

### Frontend - Configuration Components

- [ ] T284 [P] [US5] Create frontend/src/services/config.js with API calls (getConfig, updateConfig, importConfig, resolveConflicts, exportConfig)
- [ ] T285 Create frontend/src/components/config/ConflictResolver.jsx with side-by-side comparison UI for database vs YAML values
- [ ] T286 In frontend/src/components/config/ConflictResolver.jsx, add ConflictRow component showing key, db_value (left), yaml_value (right) with selection radio buttons
- [ ] T287 In frontend/src/components/config/ConflictResolver.jsx, require selection for ALL conflicts before enabling "Resolve" button
- [ ] T288 In frontend/src/components/config/ConflictResolver.jsx, handle nested object conflicts (camera_mappings) with flattened dot notation keys
- [ ] T289 In frontend/src/components/config/ConflictResolver.jsx, add JSON pretty-print display with diff highlighting (red = removed, green = added)
- [ ] T290 Create frontend/src/pages/ConfigPage.jsx with configuration editor (photo_extensions, metadata_extensions, camera_mappings, processing_methods)
- [ ] T291 In frontend/src/pages/ConfigPage.jsx, add import button with file upload dialog calling POST /config/import
- [ ] T292 In frontend/src/pages/ConfigPage.jsx, show ConflictResolver modal if conflicts detected in import response
- [ ] T293 In frontend/src/pages/ConfigPage.jsx, call POST /config/resolve with user selections after conflict resolution
- [ ] T294 In frontend/src/pages/ConfigPage.jsx, add export button downloading YAML file
- [ ] T295 In frontend/src/pages/ConfigPage.jsx, add inline editing for photo_extensions, metadata_extensions (add/remove items)
- [ ] T296 In frontend/src/pages/ConfigPage.jsx, add camera mapping editor (add/edit/delete camera IDs with name and serial_number)
- [ ] T297 In frontend/src/pages/ConfigPage.jsx, add processing method editor (add/edit/delete methods with descriptions)
- [ ] T298 In frontend/src/App.jsx, add route /config → ConfigPage

### First-Run Import Prompt

- [ ] T299 In frontend/src/App.jsx, add useEffect hook to check if database config empty on first load
- [ ] T300 In frontend/src/App.jsx, detect existing config/config.yaml file (check via API endpoint)
- [ ] T301 In frontend/src/App.jsx, show modal prompt "Existing config.yaml detected. Import to database?" with "Import" and "Skip" buttons
- [ ] T302 In frontend/src/App.jsx, call POST /config/import automatically if user clicks "Import", show ConflictResolver if conflicts

### Phase 7 Testing (Constitution Compliance)

- [ ] T302a [P] Create backend/tests/unit/test_config_service.py with ConfigService tests (get_config, update_config upsert, import_yaml_config with conflict detection)
- [ ] T302b [P] In backend/tests/unit/test_config_service.py, add detect_conflicts tests (compare db vs YAML, nested object handling for camera_mappings, ConfigConflict dataclass creation)
- [ ] T302c [P] In backend/tests/unit/test_config_service.py, add session management tests (store_pending_import with 1-hour expiry, apply_yaml_config_with_resolution, session cleanup)
- [ ] T302d [P] In backend/tests/unit/test_config_service.py, add export_yaml_config tests (format compatibility with original config.yaml schema, nested structure preservation)
- [ ] T302e [P] Create backend/tests/unit/test_api_config.py with Config API tests (GET /config, PUT /config upsert, POST /import with conflict detection, POST /resolve with session validation)
- [ ] T302f Create backend/tests/integration/test_config_migration_flow.py testing full flow (seed database config → import YAML with conflicts → resolve conflicts → verify merged config → verify CLI tools use database)
- [ ] T302g In backend/tests/integration/test_config_migration_flow.py, add YAML fallback test (unset PHOTO_ADMIN_DB_URL → verify CLI tools load from YAML → verify warning message)

### Phase 7 Frontend Testing (Constitution Compliance)

- [ ] T302h [P] Create frontend/tests/components/ConflictResolver.test.js with component tests (render conflict list, db_value vs yaml_value side-by-side, radio button selection, resolve button disabled until all conflicts resolved, nested object conflicts with dot notation)
- [ ] T302i Create frontend/tests/components/ConfigPage.test.js with component tests (render config editor, inline editing for photo_extensions/metadata_extensions add/remove, camera mapping editor, processing method editor)
- [ ] T302j Create frontend/tests/integration/config-import-flow.test.js testing full user flow (upload YAML → conflicts detected → select resolutions for each conflict → submit → verify merged config in display)
- [ ] T302k [P] Update frontend/tests/mocks/handlers.js with Phase 7 API mocks (GET /config, PUT /config, POST /config/import returning ConfigImportResponse, POST /config/resolve, GET /config/export)

**Checkpoint**: User Story 5 complete - users can import YAML config with conflict resolution, CLI tools read from database with YAML fallback. Backend test coverage >80%, frontend test coverage >75%.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, security, performance improvements affecting multiple user stories

### Documentation

- [ ] T303 [P] Create backend/README.md with setup instructions (PostgreSQL, Python env, environment variables, Alembic migrations)
- [ ] T304 [P] Create frontend/README.md with setup instructions (Node.js, npm install, npm start, environment variables)
- [ ] T305 [P] Update root README.md with web application overview, quickstart guide, feature list
- [ ] T305a [P] Update root CLAUDE.md with web application overview, quickstart guide, feature list. Check for outdated information which also need to be updated (list of tools, project structure, test strategy and coverage, technologies, etc.)
- [ ] T306 [P] Create specs/004-remote-photos-persistence/quickstart.md with developer setup guide (database creation, master key setup, first-time user flow)
- [ ] T307 [P] In quickstart.md, add section on running setup_master_key.py and setting PHOTO_ADMIN_MASTER_KEY
- [ ] T308 [P] In quickstart.md, add section on database migrations (alembic upgrade head)
- [ ] T309 [P] In quickstart.md, add section on starting backend (python web_server.py) and frontend (npm start)
- [ ] T310 [P] In quickstart.md, add first-time user workflow (import YAML config, create first collection, run first analysis)

### Security Hardening

- [ ] T311 [P] Add rate limiting to API endpoints using slowapi or custom middleware (100 requests/minute per IP)
- [ ] T312 [P] Add request size limits to file upload endpoints (10MB for YAML, 5MB for pipeline JSON)
- [ ] T313 [P] Add CSRF protection headers for state-changing endpoints (even though localhost-only for v1)
- [ ] T314 [P] Add SQL injection protection validation in all service layer inputs (SQLAlchemy ORM provides this, verify usage)
- [ ] T315 [P] Add input sanitization for user-provided metadata fields (prevent XSS in frontend display)
- [ ] T316 [P] Verify all database credentials (connectors table) use encrypted storage (CredentialEncryptor)
- [ ] T317 [P] Add logging for all credential access operations (encrypt/decrypt events) for audit trail

### Performance Optimization

- [ ] T318 [P] Add database connection pooling configuration in backend/src/db/database.py (pool_size=20, max_overflow=10)
- [ ] T319 [P] Add query optimization for GET /results endpoint with pagination (verify indexes on executed_at, collection_id, tool)
- [ ] T320 [P] Add JSONB query optimization for trend analysis (verify GIN index on analysis_results.results)
- [ ] T321 [P] Add caching for GET /config endpoint (in-memory cache with 5-minute TTL)
- [ ] T322 [P] Add lazy loading for collection file listings (only fetch when user expands collection details)
- [ ] T323 [P] Add frontend pagination for collection list, result list (50 items per page)
- [ ] T324 [P] Optimize WebSocket message frequency (increase to 2-second interval if performance issues)

### Code Quality

- [ ] T325 [P] Run backend linter (ruff check backend/) and fix errors
- [ ] T326 [P] Run frontend linter (eslint frontend/src/) and fix errors
- [ ] T327 [P] Add UTF-8 encoding validation to all file operations (verify open() calls use encoding='utf-8')
- [ ] T328 [P] Add error handling validation for all API endpoints (verify 400/404/500 responses consistent)
- [ ] T329 [P] Review all logging statements for sensitive data (ensure no decrypted credentials logged)

### Validation

- [ ] T330 Run quickstart.md validation: fresh database, master key setup, import config, create collection, run analysis
- [ ] T331 Verify all 5 user stories work independently (US1 without US2, US2 without US3, etc.)
- [ ] T332 Verify CLI tools work with database-first configuration (PHOTO_ADMIN_DB_URL set)
- [ ] T333 Verify CLI tools fall back to YAML when database unavailable (PHOTO_ADMIN_DB_URL unset)
- [ ] T334 Verify performance targets: collection listing <2s (100 collections), result queries <1s (1000+ results), report generation <500ms
- [ ] T335 Verify cache effectiveness: 80% API call reduction for remote collections with proper TTL

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - Can proceed in parallel (if team capacity) or sequentially by priority (P1 → P2 → P3)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational - Depends on Collection model from US1 for collection_id foreign key
- **User Story 3 (P2)**: Can start after Foundational - Depends on Pipeline model, used by US2 for Pipeline Validation
- **User Story 4 (P2)**: Depends on US2 (AnalysisResult model) for trend data
- **User Story 5 (P3)**: Can start after Foundational - Independent of other stories

### Critical Path

1. Phase 1: Setup (T001-T006)
2. Phase 2: Foundational (T007-T052) - **CRITICAL BLOCKER**
   - Master Key Management (T010-T014)
   - Encryption (T015-T017)
   - Cache (T018-T021)
   - Job Queue (T022-T025)
   - Pipeline Processor (T026-T041) - **SHARED INFRASTRUCTURE**
3. Phase 3: US1 Collections (T053-T118) - **MVP FOUNDATION**
4. Phase 4: US2 Tool Execution (T119-T192) - **MVP CORE VALUE**
5. Phase 5: US3 Pipeline Forms (T193-T248)
6. Phase 6: US4 Trends (T249-T261)
7. Phase 7: US5 Migration (T262-T302)
8. Phase 8: Polish (T303-T335)

### Parallel Opportunities

Within each phase, tasks marked [P] can run in parallel:
- Phase 1: All 6 tasks parallel
- Phase 2: Encryption, Cache, Job Queue can be built in parallel after database setup
- Phase 3: Model files, service files, API files, frontend files can be built in parallel
- Phase 4: Similar parallelization opportunities
- Phase 8: All documentation and code quality tasks can run in parallel

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup (6 tasks)
2. Complete Phase 2: Foundational (46 tasks) - **CRITICAL**
3. Complete Phase 3: User Story 1 (91 implementation + 11 frontend testing = 102 tasks)
4. **Complete Phase 3.5: Testing Phase 2-3 (31 backend testing tasks)** - **CONSTITUTION COMPLIANCE**
5. Complete Phase 4: User Story 2 (74 implementation + 10 backend + 7 frontend testing = 91 tasks)
6. **STOP and VALIDATE**: Test connector/collection management + tool execution independently with >80% backend, >75% frontend coverage
7. Deploy/demo MVP (276 total tasks)

### Incremental Delivery

1. **MVP (US1 + US2)**: 276 tasks → Connector + collection management + tool execution **with comprehensive test coverage (backend >80%, frontend >75%)**
2. **Add US3**: 56 implementation + 8 backend + 6 frontend testing = 70 tasks → Pipeline forms editor
3. **Add US4**: 13 implementation + 3 backend + 3 frontend testing = 19 tasks → Trend analysis
4. **Add US5**: 41 implementation + 7 backend + 4 frontend testing = 52 tasks → YAML migration
5. **Polish**: 33 tasks → Documentation, security, performance

**Total: 450 tasks** (360 implementation + 90 testing for constitution compliance)

**Testing Breakdown**: 59 backend + 31 frontend = 90 testing tasks total
**Coverage Targets**: Backend >80%, Frontend >75%, Overall project >75%

**Task Numbering Note**:
- Frontend Collection Components use T118a-T118m notation to avoid collision with Phase 4 (T119+)
- Testing tasks use letter suffixes (e.g., T104a-ae, T192a-q, T118n-x) to maintain phase association

### Parallel Team Strategy

With multiple developers after Foundational phase:
- Developer A: User Story 1 (Collections)
- Developer B: User Story 2 (Tool Execution)
- Developer C: User Story 3 (Pipelines)
- Developer D: User Story 5 (Configuration)

Then converge for US4 (Trends - depends on US2) and Polish.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label (US1-US5) maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All file paths are absolute from repository root
- **Test tasks included for constitution compliance**: Backend >80%, Frontend >75%, written alongside implementation (flexible approach)
- **Testing stack**: Backend (pytest, pytest-cov, mocked adapters), Frontend (Jest, React Testing Library, MSW for API mocking)
- **Testing phases** ensure comprehensive coverage: Phase 3.5 (backend Phase 2-3), each phase includes backend + frontend testing tasks
- **90 testing tasks total**: 59 backend (unit, integration, coverage) + 31 frontend (hooks, components, user flows)
- **Pipeline Processor (utils/pipeline_processor.py)** is CRITICAL shared infrastructure used by US2 and US3
- **Master Key Setup (setup_master_key.py)** is required one-time setup before web server starts
- **Database-first with YAML fallback** enables seamless CLI tool integration
