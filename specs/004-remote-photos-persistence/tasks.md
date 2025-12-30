# Tasks: Remote Photo Collections and Analysis Persistence

**Branch**: `004-remote-photos-persistence`
**Input**: Design documents from `/specs/004-remote-photos-persistence/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story (US1-US5 from spec.md) to enable independent implementation and testing.

**Tests**: NO test tasks included (Constitution: tests optional, spec doesn't explicitly request TDD)

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

**Independent Test**: Create collection, refresh browser, verify collection persists and shows accessibility status

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

### Backend - API Endpoints for Collections

- [ ] T095 Create backend/src/api/collections.py with FastAPI router
- [ ] T096 [P] [US1] In backend/src/api/collections.py, implement GET /collections with filters (state, type, accessible_only) returning CollectionResponse list
- [ ] T097 [P] [US1] In backend/src/api/collections.py, implement POST /collections with CollectionCreate, accessibility test, return 201 with CollectionResponse or 409 if name exists
- [ ] T098 [P] [US1] In backend/src/api/collections.py, implement GET /collections/{id} returning CollectionResponse or 404
- [ ] T099 [P] [US1] In backend/src/api/collections.py, implement PUT /collections/{id} with CollectionUpdate, cache invalidation, return 200 or 404/409
- [ ] T100 [US1] In backend/src/api/collections.py, implement DELETE /collections/{id} with force query param, check for results/jobs, return 204 or 409 with confirmation prompt
- [ ] T101 [P] [US1] In backend/src/api/collections.py, implement POST /collections/{id}/test returning accessibility status and file_count
- [ ] T102 [P] [US1] In backend/src/api/collections.py, implement POST /collections/{id}/refresh with confirm query param, file count warning, cache invalidation
- [ ] T103 [US1] In backend/src/main.py, register collections router with /api prefix

### Database Migration for Collections

- [ ] T104 [US1] Create Alembic migration backend/src/db/migrations/versions/001_initial_collections.py with connectors, collections tables, enums, indexes, foreign keys

### Frontend - Collection Components

- [ ] T105 [P] [US1] Create frontend/src/services/api.js with Axios instance configured for http://localhost:8000/api
- [ ] T106 [P] [US1] Create frontend/src/services/collections.js with API calls (listCollections, createCollection, getCollection, updateCollection, deleteCollection, testCollection, refreshCollection)
- [ ] T107 [P] [US1] Create frontend/src/hooks/useCollections.js with React hook for collection state (fetch, create, update, delete)
- [ ] T108 Create frontend/src/components/collections/CollectionList.jsx displaying collections with state badges, accessibility status, action buttons
- [ ] T109 In frontend/src/components/collections/CollectionList.jsx, add filters for state, type, accessible_only with URL query params
- [ ] T110 In frontend/src/components/collections/CollectionList.jsx, add delete confirmation dialog showing result/job counts if exists
- [ ] T111 Create frontend/src/components/collections/CollectionForm.jsx with fields (name, type, location, state, connector_id, cache_ttl, metadata)
- [ ] T112 In frontend/src/components/collections/CollectionForm.jsx, add connector selection dropdown (local = no connector, remote = select existing connector)
- [ ] T113 In frontend/src/components/collections/CollectionForm.jsx, add credential input fields based on selected type (S3/GCS/SMB)
- [ ] T114 In frontend/src/components/collections/CollectionForm.jsx, add test connection button calling POST /collections/{id}/test
- [ ] T115 [P] [US1] Create frontend/src/components/collections/CollectionStatus.jsx showing accessibility status with actionable error messages
- [ ] T116 Create frontend/src/pages/CollectionsPage.jsx with CollectionList, create/edit modals using CollectionForm
- [ ] T117 In frontend/src/pages/CollectionsPage.jsx, add manual refresh button with confirmation dialog if file count > threshold
- [ ] T118 In frontend/src/App.jsx, add route /collections → CollectionsPage

**Checkpoint**: User Story 1 complete - users can manage collections through web UI with credential encryption and cache management

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

**Checkpoint**: User Story 2 complete - users can run analysis tools, monitor progress via WebSocket, and view stored results with HTML reports

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

**Checkpoint**: User Story 3 complete - users can create/edit pipelines through forms with validation, preview, activation

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

**Checkpoint**: User Story 4 complete - users can view trend analysis across multiple executions

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

**Checkpoint**: User Story 5 complete - users can import YAML config with conflict resolution, CLI tools read from database with YAML fallback

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, security, performance improvements affecting multiple user stories

### Documentation

- [ ] T303 [P] Create backend/README.md with setup instructions (PostgreSQL, Python env, environment variables, Alembic migrations)
- [ ] T304 [P] Create frontend/README.md with setup instructions (Node.js, npm install, npm start, environment variables)
- [ ] T305 [P] Update root README.md with web application overview, quickstart guide, feature list
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
3. Complete Phase 3: User Story 1 (66 tasks)
4. Complete Phase 4: User Story 2 (74 tasks)
5. **STOP and VALIDATE**: Test collection management + tool execution independently
6. Deploy/demo MVP (186 total tasks)

### Incremental Delivery

1. MVP (US1 + US2): 186 tasks → Collection management + tool execution
2. Add US3: 56 tasks → Pipeline forms editor
3. Add US4: 13 tasks → Trend analysis
4. Add US5: 41 tasks → YAML migration
5. Polish: 33 tasks → Documentation, security, performance

Total: 329 tasks

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
- NO test tasks included (Constitution: tests optional, spec doesn't request TDD)
- **Pipeline Processor (utils/pipeline_processor.py)** is CRITICAL shared infrastructure used by US2 and US3
- **Master Key Setup (setup_master_key.py)** is required one-time setup before web server starts
- **Database-first with YAML fallback** enables seamless CLI tool integration
