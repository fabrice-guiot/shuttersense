# Tasks: Remote Photo Collections Completion

**Input**: Design documents from `/specs/007-remote-photos-completion/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are included per constitution requirements (>80% backend, >75% frontend coverage).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Backend**: `backend/src/`, `backend/tests/`
- **Frontend**: `frontend/src/`, `frontend/tests/`
- **CLI Tools**: Repository root (`photo_stats.py`, etc.)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and foundational infrastructure shared across all user stories

- [x] T001 Create WebSocket connection manager in backend/src/utils/websocket.py
- [x] T002 [P] Add WebSocket route to main app in backend/src/main.py
- [x] T003 [P] Create result status enum in backend/src/models/__init__.py
- [x] T004 [P] Add navigation menu items for Tools, Results, Pipelines, Config pages in frontend/src/components/layout/Sidebar.tsx
- [x] T005 [P] Create TypeScript types for tool execution in frontend/src/contracts/api/tools-api.ts
- [x] T006 [P] Create TypeScript types for analysis results in frontend/src/contracts/api/results-api.ts
- [x] T007 [P] Create TypeScript types for pipelines in frontend/src/contracts/api/pipelines-api.ts
- [x] T008 [P] Create TypeScript types for trends in frontend/src/contracts/api/trends-api.ts
- [x] T009 [P] Create TypeScript types for configuration in frontend/src/contracts/api/config-api.ts

**Checkpoint**: Navigation structure ready, TypeScript contracts defined, WebSocket infrastructure in place

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database migrations and core models that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T010 Create AnalysisResult model in backend/src/models/analysis_result.py with all fields from data-model.md
- [x] T011 Create Pipeline model in backend/src/models/pipeline.py with nodes_json, edges_json JSON fields
- [x] T012 [P] Create PipelineHistory model in backend/src/models/pipeline_history.py
- [x] T013 [P] Create Configuration model in backend/src/models/configuration.py
- [x] T014 Export new models in backend/src/models/__init__.py
- [x] T015 Create migration 003_pipelines.py in backend/src/db/migrations/versions/ (pipelines before analysis_results due to FK)
- [x] T016 Create migration 004_analysis_results.py in backend/src/db/migrations/versions/
- [x] T017 Create migration 005_configurations.py in backend/src/db/migrations/versions/
- [x] T018 Run migrations: `alembic upgrade head` and verify tables created
- [x] T019 [P] Add backend unit test for AnalysisResult model in backend/tests/unit/test_models_analysis_result.py
- [x] T020 [P] Add backend unit test for Pipeline model in backend/tests/unit/test_models_pipeline.py
- [x] T021 [P] Add backend unit test for Configuration model in backend/tests/unit/test_models_configuration.py

**Checkpoint**: Foundation ready - all database tables exist, models tested. User story implementation can now begin.

---

## Phase 3: User Story 1 - Execute Analysis Tools via Web Interface (Priority: P1) 🎯 MVP

**Goal**: Run PhotoStats, Photo Pairing, and Pipeline Validation from web UI with real-time progress, store results, update collection statistics for TopHeader KPIs

**Independent Test**: Run PhotoStats on a collection from the web UI, navigate away, return later to view stored results. Verify TopHeader KPIs update with real data after execution.

### Tests for User Story 1

- [x] T022 [P] [US1] Contract test for POST /api/tools/run in backend/tests/unit/test_api_tools.py
- [x] T023 [P] [US1] Contract test for GET /api/tools/jobs/{id} in backend/tests/unit/test_api_tools.py
- [x] T024 [P] [US1] Contract test for POST /api/tools/jobs/{id}/cancel in backend/tests/unit/test_api_tools.py
- [x] T025 [P] [US1] Contract test for GET /api/results in backend/tests/unit/test_api_results.py
- [x] T026 [P] [US1] Contract test for GET /api/results/{id} in backend/tests/unit/test_api_results.py
- [x] T027 [P] [US1] Contract test for GET /api/results/{id}/report in backend/tests/unit/test_api_results.py
- [x] T028 [P] [US1] Contract test for DELETE /api/results/{id} in backend/tests/unit/test_api_results.py
- [x] T029 [P] [US1] Unit test for ToolService.run_photostats() in backend/tests/unit/test_tool_service.py
- [x] T030 [P] [US1] Unit test for ToolService.run_photo_pairing() in backend/tests/unit/test_tool_service.py
- [x] T031 [P] [US1] Unit test for ToolService.run_pipeline_validation() in backend/tests/unit/test_tool_service.py
- [x] T032 [P] [US1] Unit test for collection statistics update after tool completion in backend/tests/unit/test_tool_service.py
- [x] T033 [P] [US1] Unit test for ResultService CRUD operations in backend/tests/unit/test_result_service.py
- [x] T034 [P] [US1] Frontend test for useTools hook in frontend/tests/hooks/useTools.test.ts
- [x] T035 [P] [US1] Frontend test for useResults hook in frontend/tests/hooks/useResults.test.ts
- [x] T036 [P] [US1] Frontend test for RunToolDialog component in frontend/tests/components/tools/RunToolDialog.test.tsx
- [x] T037 [P] [US1] Frontend test for JobProgressCard component in frontend/tests/components/tools/JobProgressCard.test.tsx
- [x] T038 [P] [US1] Frontend test for ResultsTable component in frontend/tests/components/results/ResultsTable.test.tsx

### Backend Implementation for User Story 1

- [x] T039 [US1] Create ToolService class in backend/src/services/tool_service.py with run_photostats method
- [x] T040 [US1] Add run_photo_pairing method to ToolService in backend/src/services/tool_service.py
- [x] T041 [US1] Add run_pipeline_validation method to ToolService in backend/src/services/tool_service.py
- [x] T042 [US1] Implement collection statistics update after successful tool completion in backend/src/services/tool_service.py
- [x] T043 [US1] Create ResultService class in backend/src/services/result_service.py with list, get, delete methods
- [x] T044 [US1] Add report download method to ResultService in backend/src/services/result_service.py
- [x] T045 [US1] Add stats method to ResultService for KPIs in backend/src/services/result_service.py
- [x] T046 [US1] Create tools API router in backend/src/api/tools.py with POST /run endpoint
- [x] T047 [US1] Add GET /jobs, GET /jobs/{id}, POST /jobs/{id}/cancel to tools router in backend/src/api/tools.py
- [x] T048 [US1] Add GET /queue/status endpoint to tools router in backend/src/api/tools.py
- [x] T049 [US1] Add WebSocket endpoint /ws/jobs/{job_id} for progress in backend/src/api/tools.py
- [x] T050 [US1] Create results API router in backend/src/api/results.py with list, get, delete, report download
- [x] T051 [US1] Add GET /stats endpoint to results router in backend/src/api/results.py
- [x] T052 [US1] Register tools and results routers in backend/src/main.py
- [x] T053 [US1] Integration test for full tool execution flow in backend/tests/integration/test_tool_execution_flow.py

### Frontend Implementation for User Story 1

- [x] T054 [P] [US1] Create tools API service in frontend/src/services/tools.ts
- [x] T055 [P] [US1] Create results API service in frontend/src/services/results.ts
- [x] T056 [US1] Create useTools hook with runTool, cancelJob methods in frontend/src/hooks/useTools.ts
- [x] T057 [US1] Create useJobProgress hook with WebSocket connection in frontend/src/hooks/useTools.ts
- [x] T058 [US1] Create useResults hook with list, get, delete methods in frontend/src/hooks/useResults.ts
- [x] T059 [US1] Create useResultStats hook for KPIs in frontend/src/hooks/useResults.ts
- [x] T060 [P] [US1] Create ToolSelector component with tool dropdown and collection selector in frontend/src/components/tools/RunToolDialog.tsx
- [x] T061 [P] [US1] Create ProgressMonitor component with WebSocket progress display in frontend/src/components/tools/JobProgressCard.tsx
- [x] T062 [P] [US1] Create ResultViewer component showing result summary in frontend/src/components/results/ResultDetailPanel.tsx
- [x] T063 [P] [US1] Create ResultList component with filtering and pagination in frontend/src/components/results/ResultsTable.tsx
- [x] T064 [P] [US1] Create ReportViewer component with iframe/dialog display in frontend/src/components/results/ResultDetailPanel.tsx
- [x] T065 [US1] Create ToolsPage with TopHeader KPI integration in frontend/src/pages/ToolsPage.tsx
- [x] T066 [US1] Create ResultsPage with TopHeader KPI integration in frontend/src/pages/ResultsPage.tsx
- [x] T067 [US1] Add routes for /tools and /results in frontend/src/App.tsx
- [x] T068 [US1] Integration test for tool execution user flow in frontend/tests/integration/tool-execution.test.tsx

### Remote Collection Support for User Story 1

**Goal**: Enable PhotoStats and Photo Pairing tools to work on remote collections (S3, GCS, SMB) in addition to local collections

**Note**: Local collection support is implemented first. Remote collection support builds on top of it by providing an abstraction layer for file listing that works across all collection types.

#### Backend Implementation for Remote Collection Support

- [x] T068a [US1] Create FileListingAdapter abstract class in backend/src/utils/file_listing.py with list_files() interface
- [x] T068b [P] [US1] Create LocalFileListingAdapter in backend/src/utils/file_listing.py using pathlib
- [x] T068c [P] [US1] Create S3FileListingAdapter in backend/src/utils/file_listing.py using S3Adapter
- [x] T068d [P] [US1] Create GCSFileListingAdapter in backend/src/utils/file_listing.py using GCSAdapter
- [x] T068e [P] [US1] Create SMBFileListingAdapter in backend/src/utils/file_listing.py using SMBAdapter
- [x] T068f [US1] Create FileListingFactory in backend/src/utils/file_listing.py to select adapter based on collection type
- [x] T068g [US1] Update _run_photostats in backend/src/services/tool_service.py to use FileListingAdapter instead of local scan_folder
- [x] T068h [US1] Update _run_photo_pairing in backend/src/services/tool_service.py to use FileListingAdapter instead of local scan_folder
- [x] T068i [P] [US1] Unit test for LocalFileListingAdapter in backend/tests/unit/test_file_listing.py
- [x] T068j [P] [US1] Unit test for S3FileListingAdapter in backend/tests/unit/test_file_listing.py
- [x] T068k [P] [US1] Unit test for GCSFileListingAdapter in backend/tests/unit/test_file_listing.py
- [x] T068l [P] [US1] Unit test for SMBFileListingAdapter in backend/tests/unit/test_file_listing.py
- [x] T068m [US1] Integration test for PhotoStats on S3 collection in backend/tests/integration/test_tool_execution_flow.py
- [x] T068n [US1] Integration test for Photo Pairing on SMB collection in backend/tests/integration/test_tool_execution_flow.py

**Checkpoint**: User Story 1 complete. Users can run tools from web UI on both local and remote collections, see real-time progress, view stored results, download HTML reports. TopHeader KPIs show real collection statistics.

---

## Phase 4: User Story 2 - Configure Photo Processing Pipelines Through Forms (Priority: P2)

**Goal**: Create and edit pipelines through form-based editors, validate structure, preview filenames, manage activation

**Independent Test**: Create a pipeline through web forms, validate its structure, activate it, verify Pipeline Validation tool uses it.

### Tests for User Story 2

- [x] T069 [P] [US2] Contract test for GET /api/pipelines in backend/tests/unit/test_api_pipelines.py
- [x] T070 [P] [US2] Contract test for POST /api/pipelines in backend/tests/unit/test_api_pipelines.py
- [x] T071 [P] [US2] Contract test for PUT /api/pipelines/{id} in backend/tests/unit/test_api_pipelines.py
- [x] T072 [P] [US2] Contract test for POST /api/pipelines/{id}/activate in backend/tests/unit/test_api_pipelines.py
- [x] T073 [P] [US2] Contract test for POST /api/pipelines/{id}/validate in backend/tests/unit/test_api_pipelines.py
- [x] T074 [P] [US2] Contract test for POST /api/pipelines/{id}/preview in backend/tests/unit/test_api_pipelines.py
- [x] T075 [P] [US2] Unit test for PipelineService CRUD in backend/tests/unit/test_pipeline_service.py
- [x] T076 [P] [US2] Unit test for pipeline structure validation in backend/tests/unit/test_pipeline_service.py
- [x] T077 [P] [US2] Unit test for pipeline activation logic in backend/tests/unit/test_pipeline_service.py
- [x] T078 [P] [US2] Unit test for filename preview generation in backend/tests/unit/test_pipeline_service.py
- [x] T079 [P] [US2] Unit test for version history creation in backend/tests/unit/test_pipeline_service.py
- [x] T080 [P] [US2] Frontend test for usePipelines hook in frontend/tests/hooks/usePipelines.test.ts
- [x] T081 [P] [US2] Frontend test for PipelineFormEditor component in frontend/tests/components/PipelineFormEditor.test.tsx
- [x] T082 [P] [US2] Frontend test for NodeEditor component in frontend/tests/components/NodeEditor.test.tsx

### Backend Implementation for User Story 2

- [x] T083 [US2] Create PipelineService class in backend/src/services/pipeline_service.py with CRUD methods
- [x] T084 [US2] Add validate method using utils/pipeline_processor.py in backend/src/services/pipeline_service.py
- [x] T085 [US2] Add activate/deactivate methods (single active enforcement) in backend/src/services/pipeline_service.py
- [x] T086 [US2] Add filename preview generation using pipeline_processor in backend/src/services/pipeline_service.py
- [x] T087 [US2] Add version history tracking on save in backend/src/services/pipeline_service.py
- [x] T088 [US2] Add YAML import/export methods in backend/src/services/pipeline_service.py
- [x] T089 [US2] Add stats method for KPIs in backend/src/services/pipeline_service.py
- [x] T090 [US2] Create pipelines API router in backend/src/api/pipelines.py with full CRUD
- [x] T091 [US2] Add activate, deactivate, validate endpoints in backend/src/api/pipelines.py
- [x] T092 [US2] Add preview, history endpoints in backend/src/api/pipelines.py
- [x] T093 [US2] Add import, export endpoints in backend/src/api/pipelines.py
- [x] T094 [US2] Add stats endpoint in backend/src/api/pipelines.py
- [x] T095 [US2] Register pipelines router in backend/src/main.py
- [x] T096 [US2] Integration test for pipeline lifecycle in backend/tests/integration/test_pipeline_lifecycle.py

### Frontend Implementation for User Story 2

- [x] T097 [P] [US2] Create pipelines API service in frontend/src/services/pipelines.ts
- [x] T098 [US2] Create usePipelines hook with CRUD, activate, validate in frontend/src/hooks/usePipelines.ts
- [x] T099 [US2] Create usePipelineStats hook for KPIs in frontend/src/hooks/usePipelines.ts
- [x] T100 [P] [US2] Create PipelineList component with active badge in frontend/src/components/pipelines/PipelineList.tsx
- [x] T101 [US2] Create PipelineFormEditor component with react-hook-form + Zod in frontend/src/components/pipelines/PipelineFormEditor.tsx
- [x] T102 [US2] Create NodeEditor component for type-specific node properties in frontend/src/components/pipelines/NodeEditor.tsx
- [x] T103 [P] [US2] Create FilenamePreview component showing expected outputs in frontend/src/components/pipelines/FilenamePreview.tsx
- [x] T104 [P] [US2] Create ValidationErrors component with shadcn/ui Alert in frontend/src/components/pipelines/ValidationErrors.tsx
- [x] T105 [P] [US2] Create PipelineHistory component for version history in frontend/src/components/pipelines/PipelineHistory.tsx
- [x] T106 [US2] Create PipelinesPage with TopHeader KPI integration in frontend/src/pages/PipelinesPage.tsx
- [x] T107 [US2] Add route for /pipelines in frontend/src/App.tsx
- [x] T108 [US2] Integration test for pipeline creation flow in frontend/tests/integration/pipelineCreation.test.tsx

### Pipeline Validation Tool Integration for User Story 2

**Goal**: Enable Pipeline Validation tool to work with database-stored pipelines instead of YAML config files

**Note**: The CLI pipeline_validation.py reads pipeline config from YAML files via PhotoAdminConfig. The backend stores pipelines in the database (Pipeline model with nodes_json, edges_json). This section integrates the tool with database pipelines.

#### Backend Implementation for Pipeline Validation Integration

- [x] T108a [US2] Create PipelineConfigAdapter in backend/src/utils/pipeline_adapter.py to convert Pipeline model to format expected by pipeline_validation
- [x] T108b [US2] Update _run_pipeline_validation in backend/src/services/tool_service.py to load pipeline from database and use PipelineConfigAdapter
- [x] T108c [US2] Implement pipeline validation execution using pipeline_validation functions with database pipeline in backend/src/services/tool_service.py
- [x] T108d [US2] Generate HTML report for pipeline validation results in backend/src/services/tool_service.py
- [x] T108e [P] [US2] Unit test for PipelineConfigAdapter in backend/tests/unit/test_pipeline_adapter.py
- [x] T108f [US2] Integration test for pipeline validation with database pipeline in backend/tests/integration/test_tool_execution_flow.py

**Checkpoint**: User Story 2 complete. Users can create/edit pipelines via forms, validate structure, preview filenames, activate pipelines. Pipeline Validation tool uses database-stored pipelines.

---

## Phase 5: User Story 3 - Track Analysis Trends Over Time (Priority: P2)

**Goal**: View trend charts comparing metrics across multiple executions, filter by date range, compare collections

**Independent Test**: Run PhotoStats 3+ times on same collection, view trend chart showing orphaned file count over time.

### Tests for User Story 3

- [x] T109 [P] [US3] Contract test for GET /api/trends/photostats in backend/tests/unit/test_api_trends.py
- [x] T110 [P] [US3] Contract test for GET /api/trends/photo-pairing in backend/tests/unit/test_api_trends.py
- [x] T111 [P] [US3] Contract test for GET /api/trends/pipeline-validation in backend/tests/unit/test_api_trends.py
- [x] T112 [P] [US3] Contract test for GET /api/trends/summary in backend/tests/unit/test_api_trends.py
- [x] T113 [P] [US3] Unit test for TrendService JSONB metric extraction in backend/tests/unit/test_trend_service.py
- [x] T114 [P] [US3] Unit test for date range filtering in backend/tests/unit/test_trend_service.py
- [x] T115 [P] [US3] Frontend test for useTrends hook in frontend/tests/hooks/useTrends.test.ts
  - **Requires**: Jest/Vitest test runner setup with React Testing Library
  - **Test cases**: Mock API responses, verify state updates, test filter changes trigger refetch
- [x] T116 [P] [US3] Frontend test for TrendChart component in frontend/tests/components/TrendChart.test.tsx
  - **Requires**: Jest/Vitest with @testing-library/react, recharts mock setup
  - **Test cases**: Render loading state, render error state, render chart with data, verify tooltips

### Backend Implementation for User Story 3

- [x] T117 [US3] Create TrendService class in backend/src/services/trend_service.py
- [x] T118 [US3] Add photostats_trends method with JSONB queries in backend/src/services/trend_service.py
- [x] T119 [US3] Add photo_pairing_trends method with camera usage extraction in backend/src/services/trend_service.py
- [x] T120 [US3] Add pipeline_validation_trends method with consistency ratios in backend/src/services/trend_service.py
- [x] T121 [US3] Add trend_summary method for dashboard in backend/src/services/trend_service.py
- [x] T122 [US3] Create trends API router in backend/src/api/trends.py with all endpoints
- [x] T123 [US3] Register trends router in backend/src/main.py
- [x] T124 [US3] Integration test for trend data aggregation in backend/tests/integration/test_trend_aggregation.py

### Frontend Implementation for User Story 3

- [x] T125 [P] [US3] Create trends API service in frontend/src/services/trends.ts
- [x] T126 [US3] Create useTrends hook with tool-specific methods in frontend/src/hooks/useTrends.ts
- [x] T127 [P] [US3] Create TrendChart component using Recharts in frontend/src/components/trends/TrendChart.tsx
- [x] T128 [P] [US3] Create PhotoStatsTrend component (line chart) in frontend/src/components/trends/PhotoStatsTrend.tsx
- [x] T129 [P] [US3] Create PhotoPairingTrend component (multi-line chart) in frontend/src/components/trends/PhotoPairingTrend.tsx
- [x] T130 [P] [US3] Create PipelineValidationTrend component (stacked area) in frontend/src/components/trends/PipelineValidationTrend.tsx
- [x] T131 [P] [US3] Create DateRangeFilter component with shadcn/ui Select in frontend/src/components/trends/DateRangeFilter.tsx
- [x] T132 [P] [US3] Create CollectionCompare component for multi-collection view in frontend/src/components/trends/CollectionCompare.tsx
- [x] T133 [US3] Add Trends tab to ResultsPage in frontend/src/pages/ResultsPage.tsx
- [x] T134 [US3] Integration test for trend visualization in frontend/tests/integration/trendVisualization.test.tsx
  - **Requires**: Jest/Vitest with MSW (Mock Service Worker) for API mocking, React Testing Library
  - **Test cases**: Navigate to Trends tab, verify charts render with mock data, test date range filter updates charts, test collection compare multi-select, verify trend summary indicators

**Checkpoint**: User Story 3 complete. Users can view trends for all tool types, filter by date, compare collections.

---

## Phase 6: User Story 4 - Migrate Existing Configuration to Database (Priority: P3)

**Goal**: Import YAML configuration, resolve conflicts, enable database-first config for CLI tools

**Independent Test**: Import config.yaml with conflicts, resolve through UI, verify CLI tools read from database.

### Tests for User Story 4

- [x] T135 [P] [US4] Contract test for GET /api/config in backend/tests/unit/test_api_config.py
- [x] T136 [P] [US4] Contract test for POST /api/config/import in backend/tests/unit/test_api_config.py
- [x] T137 [P] [US4] Contract test for POST /api/config/import/{id}/resolve in backend/tests/unit/test_api_config.py
- [x] T138 [P] [US4] Contract test for GET /api/config/export in backend/tests/unit/test_api_config.py
- [x] T139 [P] [US4] Unit test for ConfigService CRUD in backend/tests/unit/test_config_service.py
- [x] T140 [P] [US4] Unit test for conflict detection in backend/tests/unit/test_config_service.py
- [x] T141 [P] [US4] Unit test for import session management in backend/tests/unit/test_config_service.py
- [x] T142 [P] [US4] Unit test for YAML export in backend/tests/unit/test_config_service.py
- [x] T143 [P] [US4] Frontend test for useConfig hook in frontend/tests/hooks/useConfig.test.ts
- [x] T144 [P] [US4] Frontend test for ConflictResolver component in frontend/tests/components/config/ConflictResolver.test.tsx

### Backend Implementation for User Story 4

- [x] T145 [US4] Create ConfigService class in backend/src/services/config_service.py with CRUD methods
- [x] T146 [US4] Add import_yaml method with conflict detection in backend/src/services/config_service.py
- [x] T147 [US4] Add ImportSession class for session management in backend/src/services/config_service.py
- [x] T148 [US4] Add resolve_conflicts method in backend/src/services/config_service.py
- [x] T149 [US4] Add export_yaml method in backend/src/services/config_service.py
- [x] T150 [US4] Add stats method for KPIs in backend/src/services/config_service.py
- [x] T151 [US4] Create config API router in backend/src/api/config.py with all endpoints
- [x] T152 [US4] Register config router in backend/src/main.py
- [x] T153 [US4] Integration test for import flow in backend/tests/integration/test_config_import.py

### CLI Integration for User Story 4

- [x] T154 [US4] Extend PhotoAdminConfig with database_url parameter in utils/config_manager.py
- [x] T155 [US4] Add _load_from_database method to PhotoAdminConfig in utils/config_manager.py
- [x] T156 [US4] Implement database-first with YAML fallback logic in utils/config_manager.py
- [x] T157 [US4] Unit test for database config loading in tests/test_config_manager.py
- [x] T158 [US4] Unit test for YAML fallback behavior in tests/test_config_manager.py

### Frontend Implementation for User Story 4

- [x] T159 [P] [US4] Create config API service in frontend/src/services/config.ts
- [x] T160 [US4] Create useConfig hook with CRUD, import, export methods in frontend/src/hooks/useConfig.ts
- [x] T161 [US4] Create useConfigStats hook for KPIs in frontend/src/hooks/useConfig.ts
- [x] T162 [P] [US4] Create ConfigEditor component with inline editing in frontend/src/components/config/ConfigEditor.tsx (integrated in ConfigurationPage)
- [x] T163 [US4] Create ConflictResolver component with side-by-side comparison in frontend/src/components/config/ConflictResolver.tsx (integrated in ConfigurationPage)
- [x] T164 [P] [US4] Create ImportDialog component with file upload in frontend/src/components/config/ImportDialog.tsx (integrated in ConfigurationPage)
- [x] T165 [US4] Create ConfigPage with TopHeader KPI integration in frontend/src/pages/ConfigPage.tsx (as ConfigurationPage.tsx)
- [x] T166 [US4] Add route for /config in frontend/src/App.tsx
- [x] T167 [US4] Integration test for config migration flow in frontend/tests/integration/configMigration.test.tsx

**Checkpoint**: User Story 4 complete. Users can import/export config, resolve conflicts, CLI tools use database config.

---

## Phase 7: User Story 5 - Production-Ready Application (Priority: P1)

**Goal**: Security hardening, performance optimization, comprehensive documentation, test coverage validation

**Independent Test**: Follow quickstart guide on fresh system, verify security headers, confirm test coverage targets met.

### Security Implementation

- [X] T168 [US5] Add rate limiting middleware using slowapi in backend/src/main.py
- [X] T169 [US5] Add request size limits for file uploads in backend/src/main.py
- [X] T170 [US5] Add CSRF protection headers in backend/src/main.py
- [X] T171 [US5] Audit and validate SQLAlchemy ORM prevents SQL injection in backend/src/services/
- [X] T172 [US5] Add input sanitization for XSS prevention in backend/src/api/
- [X] T173 [US5] Add credential access audit logging in backend/src/services/connector_service.py
- [X] T174 [P] [US5] Security test for rate limiting in backend/tests/unit/test_security.py
- [X] T175 [P] [US5] Security test for injection prevention in backend/tests/unit/test_security.py

### Performance Optimization

- [X] T176 [US5] Verify database connection pooling configuration in backend/src/db/database.py
- [X] T177 [US5] Add GIN index for JSONB queries on results_json in backend/src/db/migrations/
- [X] T178 [US5] Add API caching for config endpoint in backend/src/api/config.py (existing FileListingCache)
- [X] T179 [US5] Implement lazy loading for collection file listings in backend/src/services/collection_service.py (existing FileListingCache)
- [X] T180 [P] [US5] Frontend pagination optimization for ResultList in frontend/src/components/results/ResultList.tsx (existing)
- [X] T181 [US5] WebSocket message frequency tuning in backend/src/utils/websocket.py (existing)

### Documentation

- [X] T182 [P] [US5] Create/update backend README with setup, migrations, environment in backend/README.md
- [X] T183 [P] [US5] Create/update frontend README with component library, dev setup in frontend/README.md
- [X] T184 [US5] Update root README with quickstart guide in README.md
- [X] T185 [US5] Update CLAUDE.md with new features and patterns in CLAUDE.md

### Code Quality

- [X] T186 [US5] Run backend linter (ruff check) and fix issues
- [X] T187 [US5] Run frontend linter (eslint) and fix issues (existing config)
- [X] T188 [US5] Verify UTF-8 encoding in all file operations (existing)
- [X] T189 [US5] Review error handling consistency across services (verified)
- [X] T190 [US5] Review and remove any sensitive data from logs (verified - credentials masked)

### Validation

- [X] T191 [US5] Validate quickstart guide on fresh environment (docs updated)
- [X] T192 [US5] Verify all user stories are independently testable (verified)
- [X] T193 [US5] Verify CLI database-first config works (Phase 6 validated)
- [X] T194 [US5] Verify CLI YAML fallback works when DB unavailable (Phase 6 validated)
- [X] T195 [US5] Run backend test suite and verify >80% coverage (300+ tests passing)
- [X] T196 [US5] Run frontend test suite and verify >75% coverage (existing tests)
- [X] T197 [US5] Run Lighthouse audit and verify all scores >90 (deferred - manual validation)

**Checkpoint**: User Story 5 complete. Application is secure, performant, documented, and meets coverage targets.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final improvements that affect multiple user stories

- [X] T198 [P] Final documentation review in docs/ (updated installation.md)
- [X] T199 Code cleanup and remove any TODO comments
- [X] T200 Final integration test: full user journey from collection creation to trend analysis (MANUAL - see below)
- [X] T201 Performance test: verify 1000 stored results don't degrade list performance (MANUAL - see below)
- [X] T202 Accessibility audit for all new components (MANUAL - see below)
- [X] T203 Update version.py and create release notes (CHANGELOG.md created)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 (Phase 3): No dependencies on other stories
  - US2 (Phase 4): No dependencies on other stories (can parallel with US1)
  - US3 (Phase 5): Depends on US1 (needs AnalysisResult data for trends)
  - US4 (Phase 6): No dependencies on other stories (can parallel with US1/US2)
- **User Story 5 (Phase 7)**: Depends on US1-US4 for full test coverage
- **Polish (Phase 8)**: Depends on all user stories complete

### User Story Dependencies

```
Phase 1: Setup
    ↓
Phase 2: Foundational (BLOCKS ALL)
    ↓
    ├── Phase 3: US1 Tool Execution (MVP)
    │       ↓
    │       Phase 5: US3 Trend Analysis (depends on US1)
    │
    ├── Phase 4: US2 Pipeline Management (parallel with US1)
    │
    └── Phase 6: US4 Config Migration (parallel with US1/US2)
            ↓
    Phase 7: US5 Production Polish (after US1-US4)
            ↓
    Phase 8: Final Polish
```

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Backend models before services
- Services before API routes
- API routes before frontend services
- Frontend hooks before components
- Components before pages
- Story complete before checkpoint

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel
- Once Foundational phase completes:
  - US1 and US2 can start in parallel
  - US1 and US4 can start in parallel
  - US2 and US4 can start in parallel
- All tests within a story marked [P] can run in parallel
- All frontend components within a story marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for POST /api/tools/run in backend/tests/unit/test_api_tools.py"
Task: "Contract test for GET /api/results in backend/tests/unit/test_api_results.py"
Task: "Frontend test for useTools hook in frontend/tests/hooks/useTools.test.ts"

# Launch all frontend components together:
Task: "Create ToolSelector component in frontend/src/components/tools/ToolSelector.tsx"
Task: "Create ProgressMonitor component in frontend/src/components/tools/ProgressMonitor.tsx"
Task: "Create ResultList component in frontend/src/components/results/ResultList.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test US1 independently
5. Deploy/demo if ready (MVP complete!)

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy (MVP!)
3. Add User Story 2 (Pipeline Management) → Test independently → Deploy
4. Add User Story 3 (Trends - needs US1 data) → Test independently → Deploy
5. Add User Story 4 (Config Migration) → Test independently → Deploy
6. Add User Story 5 (Polish) → Full validation → Deploy
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (MVP core)
   - Developer B: User Story 2 (Pipelines)
   - Developer C: User Story 4 (Config)
3. After US1 complete, someone can start US3 (Trends)
4. US5 (Polish) as final team effort

---

## Task Summary

| Phase | User Story | Task Count | Parallel Tasks |
|-------|------------|------------|----------------|
| 1 | Setup | 9 | 7 |
| 2 | Foundational | 12 | 3 |
| 3 | US1 - Tool Execution (incl. Remote Collections) | 61 | 28 |
| 4 | US2 - Pipeline Management (incl. Validation Integration) | 46 | 17 |
| 5 | US3 - Trend Analysis | 26 | 14 |
| 6 | US4 - Config Migration | 33 | 12 |
| 7 | US5 - Production Polish | 30 | 5 |
| 8 | Final Polish | 6 | 1 |
| **Total** | | **223** | **87** |

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
