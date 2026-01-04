# Feature Specification: Remote Photo Collections Completion

**Feature Branch**: `007-remote-photos-completion`
**Created**: 2026-01-03
**Status**: Draft
**Input**: User description: "Complete the Remote Photo Collections feature per PRD 007 - Phases 4-8 covering tool execution, pipeline management, trend analysis, configuration migration, and production polish"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Execute Analysis Tools via Web Interface (Priority: P1)

As a photo collection manager, I want to run PhotoStats, Photo Pairing, and Pipeline Validation from the web interface so that I can analyze collections without using the command line and access results later.

**Why this priority**: This is the MVP core functionality. Without tool execution, the web application cannot deliver its primary value proposition. This story also enables the TopHeader KPIs from 006-ux-polish to display real data (storage used, file count, image count) by populating collection statistics after each tool run.

**Independent Test**: Run PhotoStats on a collection from the web UI, navigate away from the page, return later to view the stored results without re-running the analysis. Verify that TopHeader KPIs update with real data after execution.

**Acceptance Scenarios**:

1. **Given** a user with at least one configured collection, **When** they select a tool and click "Run", **Then** the tool begins executing and displays real-time progress (files scanned, issues found)

2. **Given** a tool is running, **When** it completes successfully, **Then** the results are stored in the database, the collection statistics are updated, and the user sees a summary with option to view the full HTML report

3. **Given** a user viewing the results list, **When** they click on a past execution, **Then** they see the detailed results and can download the HTML report

4. **Given** a tool execution fails mid-way, **When** the failure occurs, **Then** the user sees an error message, the partial results are not stored, and collection statistics remain unchanged

5. **Given** PhotoStats completes successfully, **When** the results are stored, **Then** the collection's storage_used and file_count statistics are updated and reflected in TopHeader KPIs

6. **Given** Photo Pairing or Pipeline Validation completes, **When** the results are stored, **Then** the collection's image_group_count and image_count statistics are updated

---

### User Story 2 - Configure Photo Processing Pipelines Through Forms (Priority: P2)

As a workflow-focused photographer, I want to create and edit pipelines through web forms instead of YAML so that I can avoid syntax errors and visualize expected filenames before running validation.

**Why this priority**: Pipeline management through forms significantly reduces user errors compared to manual YAML editing. However, users can still use CLI tools without this feature, making it less critical than tool execution.

**Independent Test**: Create a complete pipeline through the web forms, validate its structure, activate it, then verify that the Pipeline Validation tool uses this pipeline when analyzing a collection.

**Acceptance Scenarios**:

1. **Given** a user on the Pipelines page, **When** they click "Create Pipeline" and fill out the form with nodes (Capture, File, Process, Pairing, Branching, Termination), **Then** the pipeline is saved with valid structure

2. **Given** a pipeline with invalid structure (cycles, orphaned nodes, invalid references), **When** the user attempts to save, **Then** they see specific validation errors with guidance on how to fix them

3. **Given** a saved pipeline, **When** the user clicks "Preview Filenames", **Then** they see expected filename patterns generated from the pipeline definition

4. **Given** multiple pipelines exist, **When** the user activates one, **Then** only that pipeline is marked active and Pipeline Validation tool uses it

5. **Given** a pipeline with changes, **When** the user views version history, **Then** they see previous versions with change timestamps

---

### User Story 3 - Track Analysis Trends Over Time (Priority: P2)

As a photo archive manager, I want to view trend charts comparing metrics across multiple executions so that I can identify which collections are degrading and when issues started.

**Why this priority**: Trend analysis provides strategic value by enabling proactive archive management. It depends on having stored analysis results from User Story 1, making it naturally sequential.

**Independent Test**: Run PhotoStats 3+ times on the same collection over different dates (can be simulated), then view the trend chart showing orphaned file count over time.

**Acceptance Scenarios**:

1. **Given** multiple PhotoStats executions for a collection, **When** the user views the trends tab, **Then** they see a line chart showing orphaned files count over time

2. **Given** multiple Photo Pairing executions, **When** the user views camera usage trends, **Then** they see a multi-line chart showing usage per camera over time

3. **Given** multiple Pipeline Validation executions, **When** the user views consistency trends, **Then** they see a stacked area chart showing CONSISTENT/PARTIAL/INCONSISTENT ratios over time

4. **Given** a trend chart, **When** the user applies a date range filter, **Then** the chart updates to show only data within that range

5. **Given** multiple collections, **When** the user enables comparison mode, **Then** they see metrics from multiple collections overlaid on the same chart

---

### User Story 4 - Migrate Existing Configuration to Database (Priority: P3)

As a current photo-admin CLI user, I want to import my existing YAML configuration into the database so that I can use the web interface without losing my custom settings.

**Why this priority**: Configuration migration is essential for existing users but not blocking for new users. The system maintains YAML fallback for CLI tools, reducing urgency.

**Independent Test**: Import a config.yaml file with conflicting values (some keys exist in database with different values), resolve conflicts through the UI choosing specific values for each conflict, then verify CLI tools read from the database.

**Acceptance Scenarios**:

1. **Given** a user with an existing config.yaml, **When** they click "Import Configuration" and select the file, **Then** the system analyzes the file and shows detected settings

2. **Given** conflicting values between YAML and database, **When** the import wizard displays them, **Then** the user sees a side-by-side comparison for each conflict and can choose which value to keep

3. **Given** a completed import, **When** the user runs a CLI tool, **Then** the tool reads configuration from the database instead of YAML

4. **Given** the database is unavailable, **When** a CLI tool runs, **Then** it gracefully falls back to reading from YAML configuration

5. **Given** configuration in the database, **When** the user clicks "Export to YAML", **Then** a valid config.yaml file is downloaded with all current settings

---

### User Story 5 - Production-Ready Application (Priority: P1)

As a developer or user deploying photo-admin, I want the application to be secure, performant, and well-documented so that I can confidently use it in production.

**Why this priority**: Security and documentation are critical for any production deployment. While feature-wise this comes last, it's P1 because shipping without these would be irresponsible.

**Independent Test**: Follow the quickstart guide on a fresh system, verify the application starts correctly, run through all main features, and confirm security headers are present in API responses.

**Acceptance Scenarios**:

1. **Given** the root README, **When** a new user follows the quickstart guide, **Then** they can set up and run the application successfully within 30 minutes

2. **Given** API endpoints, **When** inspected for security, **Then** rate limiting is enforced, CSRF headers are present, and SQL injection attempts are rejected

3. **Given** a running application, **When** tested with Lighthouse, **Then** all scores (performance, accessibility, best practices) exceed 90

4. **Given** the codebase, **When** running test suites, **Then** backend coverage exceeds 80% and frontend coverage exceeds 75%

---

### Edge Cases

- What happens when a tool execution is cancelled mid-way? (Partial results discarded, collection stats unchanged)
- How does the system handle concurrent tool executions on the same collection? (Queue or block based on job system)
- What happens when WebSocket connection drops during execution? (Reconnect and resume progress updates)
- How does the system handle very large collections (100k+ files)? (Progress updates batched, results paginated)
- What happens when a pipeline references a deleted node? (Validation catches orphaned references)
- How does conflict resolution handle deeply nested YAML structures? (Flatten to key-value pairs for comparison)
- What happens when the database becomes unavailable during tool execution? (Fail gracefully, preserve CLI fallback)
- How does the system handle collections with NULL statistics in TopHeader? (Display "–" or "N/A" until first tool run)

## Requirements *(mandatory)*

### Functional Requirements

#### Tool Execution (Phase 4)

- **FR-001**: System MUST allow users to run PhotoStats, Photo Pairing, or Pipeline Validation on any configured collection from the web interface
- **FR-002**: System MUST display real-time execution progress via WebSocket showing files scanned and issues found
- **FR-003**: System MUST store analysis results in the database with timestamp, tool type, collection reference, and results data
- **FR-004**: System MUST store the generated HTML report alongside analysis results for later retrieval
- **FR-005**: System MUST provide a results list showing all past executions with filtering by tool, collection, and date range
- **FR-006**: Users MUST be able to download HTML reports for offline viewing
- **FR-007**: System MUST update collection statistics (storage_used, file_count) after successful PhotoStats execution
- **FR-008**: System MUST update collection statistics (image_group_count, image_count) after successful Photo Pairing or Pipeline Validation execution
- **FR-009**: System MUST NOT update collection statistics if tool execution fails or is cancelled
- **FR-010**: TopHeader KPIs MUST aggregate statistics from all collections with non-NULL values
- **FR-011**: Tool execution UI MUST use shadcn/ui components matching the design system from 005-ui-migration

#### Pipeline Management (Phase 5)

- **FR-012**: System MUST allow users to create pipelines through form-based editors with node types: Capture, File, Process, Pairing, Branching, Termination
- **FR-013**: System MUST validate pipeline structure detecting cycles, orphaned nodes, and invalid references
- **FR-014**: System MUST display validation errors with actionable guidance using alert components
- **FR-015**: System MUST allow users to preview expected filenames based on pipeline configuration
- **FR-016**: System MUST support pipeline activation where only one pipeline can be active at a time
- **FR-017**: System MUST maintain version history for pipeline changes with timestamps
- **FR-018**: Pipeline Validation tool MUST use the currently active pipeline from the database
- **FR-019**: Users MUST be able to import and export pipelines as YAML format

#### Trend Analysis (Phase 6)

- **FR-020**: System MUST provide trend visualization showing metrics over time for each tool type
- **FR-021**: PhotoStats trends MUST show orphaned file count as a line chart over executions
- **FR-022**: Photo Pairing trends MUST show camera usage distribution as a multi-line chart
- **FR-023**: Pipeline Validation trends MUST show consistency ratios (CONSISTENT/PARTIAL/INCONSISTENT) as a stacked area chart
- **FR-024**: Users MUST be able to filter trends by date range
- **FR-025**: Users MUST be able to compare multiple collections on the same trend chart
- **FR-026**: Trend charts MUST use the established Recharts integration with Tailwind CSS theming

#### Configuration Migration (Phase 7)

- **FR-027**: System MUST allow users to import existing YAML configuration files
- **FR-028**: System MUST detect conflicts between database and YAML configuration values
- **FR-029**: System MUST provide a side-by-side conflict resolution interface
- **FR-030**: CLI tools MUST read configuration from database as primary source
- **FR-031**: CLI tools MUST fall back to YAML configuration when database is unavailable
- **FR-032**: Users MUST be able to export database configuration to YAML format
- **FR-033**: Configuration editor MUST support inline editing with real-time validation

#### Production Polish (Phase 8)

- **FR-034**: Application MUST implement rate limiting on API endpoints
- **FR-035**: Application MUST enforce request size limits for file uploads
- **FR-036**: Application MUST include CSRF protection headers
- **FR-037**: Application MUST validate and sanitize all user inputs to prevent injection attacks
- **FR-038**: Backend README MUST document setup, migrations, and environment configuration
- **FR-039**: Frontend README MUST document component library and development setup
- **FR-040**: Root README MUST include quickstart guide for new users

### Key Entities

- **AnalysisResult**: Stores execution history - tool type, collection reference, timestamp, results (JSONB), HTML report content, execution duration, status
- **Pipeline**: Processing workflow definition - nodes configuration (JSONB), edges configuration (JSONB), version number, is_active flag, name, description
- **PipelineHistory**: Version tracking - pipeline reference, change timestamp, previous configuration snapshot, change description
- **Configuration**: Database-backed settings - category (extensions, cameras, methods), key-value pairs (JSONB), last updated timestamp
- **Collection Statistics Cache** (extension to existing Collection entity): storage_used (bytes), file_count (integer), image_group_count (integer), image_count (integer), last_stats_update (timestamp)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete a full tool execution cycle (select, run, view results) in under 5 minutes for collections up to 10,000 files
- **SC-002**: 95% of real-time progress updates are delivered within 500ms via WebSocket
- **SC-003**: Trend charts render completely within 1 second for datasets with up to 100 data points
- **SC-004**: Pipeline validation feedback appears within 2 seconds of form submission
- **SC-005**: Backend test coverage exceeds 80% across all new services and endpoints
- **SC-006**: Frontend test coverage exceeds 75% across all new components and hooks
- **SC-007**: New users can complete the quickstart guide and run their first tool within 30 minutes
- **SC-008**: Application achieves Lighthouse scores above 90 for performance, accessibility, and best practices
- **SC-009**: Configuration conflicts are resolved in under 5 minutes for typical config.yaml files (50 settings)
- **SC-010**: System handles 1000 stored analysis results without noticeable performance degradation in result list
- **SC-011**: TopHeader KPIs display real aggregate statistics within 1 second of page load after collections have been analyzed

## Assumptions

- PostgreSQL 12+ database is already configured and accessible (established in Phases 1-3)
- The shadcn/ui design system from 005-ui-migration is the authoritative UI pattern
- WebSocket infrastructure from FastAPI is available for real-time progress updates
- Existing CLI tools (photo_stats.py, photo_pairing.py, pipeline_validation.py) can be invoked programmatically
- Users primarily operate in a localhost environment (single user, no authentication required)
- The PHOTO_ADMIN_MASTER_KEY environment variable is configured for credential encryption
- Recharts dependency is already integrated and available for trend visualization
- The TopHeader KPI pattern from 006-ux-polish is fully implemented and waiting for real data

## Constraints

- All new frontend code must be TypeScript with strict type checking
- All new UI components must use shadcn/ui and Tailwind CSS (no CSS-in-JS)
- Visual pipeline graph editor is explicitly out of scope (deferred to v2)
- User authentication is out of scope (localhost single-user assumption)
- Mobile application is out of scope (responsive web UI only)
- Pipeline Validation values take precedence over Photo Pairing for image statistics
