# Feature Specification: Pipeline-Driven Analysis Tools

**Feature Branch**: `217-pipeline-driven-tools`
**Created**: 2026-02-17
**Status**: Draft
**Input**: GitHub issue #217 — Improve PhotoStats and Photo_Pairing tools to use Pipeline content instead of Config. Full PRD: docs/prd/217-pipeline-driven-analysis-tools.md

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pipeline-Derived Extensions for PhotoStats (Priority: P1)

A team administrator has defined a Pipeline with File nodes specifying `.cr3`, `.dng`, `.tiff` (image), and `.xmp` (metadata) extensions. When they run PhotoStats on a Collection assigned to that Pipeline, the tool automatically recognizes those file types based on the Pipeline definition rather than requiring separate configuration entries. The administrator no longer needs to maintain extension lists in two places.

**Why this priority**: This is the foundational change that unifies the configuration source. Without Pipeline-derived extensions, the other stories (filename parsing, camera discovery, sidecar inference) have no common configuration extraction mechanism to build upon. PhotoStats is the simpler of the two tools, making it the right starting point.

**Independent Test**: Can be fully tested by running PhotoStats on a Collection with an assigned Pipeline that defines specific File nodes, then verifying the tool uses those extensions (and ignores the legacy Config extensions). Delivers value by eliminating Config/Pipeline duplication for extension management.

**Acceptance Scenarios**:

1. **Given** a Collection assigned to a Pipeline with File nodes for `.cr3`, `.dng`, and `.xmp`, **When** the user runs PhotoStats, **Then** the tool recognizes `.cr3` and `.dng` as image files and `.xmp` as metadata files, regardless of what the Config table contains.
2. **Given** a Collection with no Pipeline assigned and no team default Pipeline, **When** the user runs PhotoStats, **Then** the tool falls back to the Config-based extension lists and produces the same results as before this feature.
3. **Given** a Pipeline with File nodes for `.cr3`, `.dng`, `.heif`, and `.xmp`, **When** PhotoStats extracts the extension sets, **Then** `.heif` is categorized as an image extension (not metadata) because it is not in the recognized metadata formats set.
4. **Given** a Pipeline where sidecar relationships are defined (a Capture node outputs to both a `.cr3` File node and a non-optional `.xmp` File node), **When** PhotoStats runs, **Then** it infers that `.cr3` files require `.xmp` sidecars and reports orphaned images accordingly.

---

### User Story 2 - Pipeline-Driven Filename Parsing for Photo_Pairing (Priority: P2)

A photographer uses a non-standard camera naming convention (e.g., `IMG_0001` instead of `AB3D0001`). Their Pipeline's Capture node defines a custom `filename_regex` that matches this convention. When they run Photo_Pairing on a Collection assigned to that Pipeline, the tool parses filenames using the Pipeline's regex rather than the hardcoded pattern, correctly extracting camera IDs and counters.

**Why this priority**: This unlocks the primary differentiating capability of Pipeline-driven analysis: configurable filename parsing. Without it, Photo_Pairing remains locked to a single naming convention, which is the core limitation cited in the issue.

**Independent Test**: Can be tested by running Photo_Pairing on a Collection with a Pipeline whose Capture node defines a custom regex pattern, then verifying filenames are parsed correctly and image groups are formed based on the regex-extracted camera ID and counter.

**Acceptance Scenarios**:

1. **Given** a Pipeline with a Capture node defining `filename_regex: "^(IMG)_([0-9]{4})"` and `camera_id_group: 1`, **When** Photo_Pairing runs on files named `IMG_0001.cr3`, `IMG_0001-HDR.cr3`, **Then** the tool groups them correctly with camera ID `IMG` and counter `0001`.
2. **Given** a Pipeline with Process nodes named "HDR Merge" (method_ids: `["HDR"]`) and "Black & White" (method_ids: `["BW"]`), **When** Photo_Pairing encounters a file with suffix `-HDR`, **Then** the analytics report displays "HDR Merge" as the processing method name instead of "HDR".
3. **Given** a file with an all-numeric suffix like `-2`, **When** Photo_Pairing processes it, **Then** the tool treats it as a "separate image" indicator regardless of Pipeline configuration (hardcoded convention preserved).
4. **Given** no Pipeline is available for the Collection, **When** Photo_Pairing runs, **Then** it falls back to the hardcoded `FilenameParser` pattern and produces the same results as before.

---

### User Story 3 - Camera Auto-Discovery During Analysis (Priority: P3)

An analyst runs Photo_Pairing on a large Collection containing images from cameras with IDs `AB3D`, `XYZW`, and `QR5T`. Only `AB3D` has been previously registered. During analysis, the system automatically creates Camera records for `XYZW` and `QR5T` with a "temporary" status and uses the raw camera ID as a placeholder name. The analyst sees "AB3D" resolved to "Canon EOS R5" in the report, while the new cameras appear by their raw IDs. Later, the administrator can confirm and rename the temporary cameras.

**Why this priority**: Camera auto-discovery enriches analysis results with human-readable names and builds a living equipment registry. However, it depends on the Pipeline-driven parsing (P2) to extract camera IDs correctly, making it naturally the third priority.

**Independent Test**: Can be tested by running Photo_Pairing (online mode) on a Collection with known and unknown camera IDs, then verifying that new Camera records are created in the database and the report resolves known camera names while showing raw IDs for newly discovered cameras.

**Acceptance Scenarios**:

1. **Given** a team has one confirmed Camera record (camera_id: `AB3D`, display_name: "Canon EOS R5"), **When** Photo_Pairing encounters files from `AB3D` and `XYZW`, **Then** a new Camera record is created for `XYZW` with `status: "temporary"` and `display_name: "XYZW"`, and the report shows "Canon EOS R5" for `AB3D` and "XYZW" for the new camera.
2. **Given** two analysis jobs discover the same new camera ID `XYZW` concurrently, **When** both attempt to create a Camera record, **Then** exactly one record is created (no duplicates), and both jobs proceed without error.
3. **Given** the agent is running in offline mode (no server connectivity), **When** Photo_Pairing encounters unknown camera IDs, **Then** camera discovery is skipped, the analysis completes successfully using raw camera IDs as display names, and no error is raised.
4. **Given** the server's camera discovery endpoint is unreachable or times out, **When** Photo_Pairing attempts camera discovery, **Then** the analysis falls back to using raw camera IDs and logs a warning, without failing the entire analysis.

---

### User Story 4 - Camera Management in the Resources Page (Priority: P4)

A team administrator navigates to the "Resources" page in the web application. They see two tabs: "Cameras" and "Pipelines". Under the Cameras tab, they view a list of auto-discovered cameras, filter by status (temporary/confirmed), and edit a temporary camera to add its make, model, and display name, changing its status to "confirmed". The Pipelines tab contains all existing Pipeline functionality (list, create, edit, delete, activate, validate, import/export) unchanged.

**Why this priority**: The frontend Camera management UI provides the user-facing experience for the Camera entity and consolidates the navigation. However, it depends on the Camera entity (P3) and backend API being in place, and the backend analysis improvements (P1-P3) deliver value even without a dedicated Camera management UI.

**Independent Test**: Can be tested by navigating to `/resources`, verifying both tabs render correctly, creating/editing/deleting cameras via the UI, and confirming that the `/pipelines` URL redirects to `/resources?tab=pipelines`.

**Acceptance Scenarios**:

1. **Given** the user navigates to `/resources`, **When** the page loads, **Then** the "Cameras" tab is active by default and displays a list of Camera records with columns for Camera ID, Display Name, Make, Model, Status, and Modified.
2. **Given** several cameras with mixed statuses, **When** the user filters by "Temporary", **Then** only cameras with `status: "temporary"` are shown.
3. **Given** a temporary camera, **When** the user edits it to set a display name, make, model, and changes status to "confirmed", **Then** the Camera record is updated and the list reflects the changes.
4. **Given** the user navigates to `/pipelines` (old URL), **When** the page loads, **Then** the browser redirects to `/resources?tab=pipelines` and all Pipeline functionality is preserved.
5. **Given** the Cameras tab is active, **When** the TopHeader area is rendered, **Then** it displays Camera KPI stats (total cameras, confirmed count, temporary count). When the user switches to the Pipelines tab, the stats update to show Pipeline KPIs.

---

### User Story 5 - Pipeline Resolution per Collection (Priority: P5)

A team has a default Pipeline configured. One specific Collection is assigned a different Pipeline (with different file extensions and filename regex). When the user runs PhotoStats or Photo_Pairing on that Collection, the tool uses the Collection-specific Pipeline rather than the team default. When they run the same tools on a Collection with no specific Pipeline assignment, the team default Pipeline is used.

**Why this priority**: Pipeline resolution is the glue that connects Collections to the correct Pipeline configuration. It depends on all previous stories being functional and adds the collection-specific override behavior.

**Independent Test**: Can be tested by configuring two Collections (one with an assigned Pipeline, one without), running analysis tools on each, and verifying the correct Pipeline is used in each case.

**Acceptance Scenarios**:

1. **Given** a Collection with `pipeline_id` set to a specific Pipeline, **When** PhotoStats or Photo_Pairing runs, **Then** the tool uses that specific Pipeline's configuration.
2. **Given** a Collection with `pipeline_id` set to NULL and the team has a default Pipeline, **When** a tool runs, **Then** the tool uses the team's default Pipeline.
3. **Given** a Collection with `pipeline_id` set to NULL and no team default Pipeline exists, **When** a tool runs, **Then** the tool falls back to Config-based parameters.
4. **Given** a Collection assigned to a Pipeline that is structurally invalid (e.g., missing Capture node), **When** the agent attempts to extract tool config, **Then** the agent logs a warning, falls back to Config-based parameters, and the analysis completes successfully.
5. **Given** offline mode with cached Pipeline data, **When** the agent runs a tool, **Then** the cached Pipeline is used for configuration extraction without requiring server connectivity.

---

### Edge Cases

- What happens when a Pipeline has multiple Capture nodes? The system uses the first Capture node found and extracts its `filename_regex` and `camera_id_group`.
- What happens when a Capture node's `filename_regex` is syntactically invalid? The regex parsing fails gracefully, the system falls back to the hardcoded `FilenameParser` pattern, and a warning is logged.
- What happens when a Pipeline has File nodes but no Process nodes? The `processing_suffixes` map is empty, and all filename suffixes that are non-numeric are treated as unrecognized.
- What happens when a File node has no `extension` property? That node is skipped during extension extraction.
- What happens when a Pipeline has an optional `.xmp` File node alongside a `.cr3` File node? No sidecar requirement is inferred for `.cr3` because the metadata node is optional.
- What happens when Camera discovery receives an empty list of camera IDs? The discover endpoint returns an empty list and no records are created.
- What happens when a Camera record is deleted but historical analysis results reference that camera ID? Historical results remain valid and viewable; they display whatever camera name was resolved at analysis time.
- What happens when the same camera ID exists in the discover request multiple times? The endpoint deduplicates and creates or returns only one Camera record per unique camera ID.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST extract tool-relevant configuration (file extensions, filename pattern, processing suffixes, sidecar requirements) from a Pipeline definition into a unified structure usable by all analysis tools.
- **FR-002**: Image extensions MUST be derived from Pipeline File nodes by exclusion: any File node extension that is not in the recognized metadata formats set (currently `{".xmp"}`) is treated as an image extension. The system MUST NOT rely on a hardcoded list of image extensions.
- **FR-003**: Metadata extensions MUST be derived from Pipeline File nodes whose extension matches the recognized metadata formats set.
- **FR-004**: Sidecar requirements MUST be inferred from Pipeline structure: when a non-optional image File node and a non-optional metadata File node share a common parent node, the image extension requires a sidecar. Optional metadata File nodes MUST NOT create sidecar requirements.
- **FR-005**: Processing suffixes MUST be derived from Pipeline Process nodes, mapping each Process node's `method_ids` to the node's display name for human-readable resolution.
- **FR-006**: The filename parsing pattern MUST be taken from the Pipeline Capture node's `filename_regex` property. The `filename_regex` property is required on Capture nodes; a missing value MUST raise an error. The `camera_id_group` MAY default to 1 if not explicitly set.
- **FR-007**: If the Pipeline has no Capture node, the configuration extraction (`extract_tool_config()`) MUST raise a clear error (e.g., `ValueError`). See FR-014 for how tools handle this error at the execution layer.
- **FR-008**: PhotoStats MUST use Pipeline-derived extensions (image, metadata) and sidecar requirements when a Pipeline is available for the target Collection.
- **FR-009**: Photo_Pairing MUST use the Pipeline Capture node's filename regex for camera ID and counter extraction when a Pipeline is available.
- **FR-010**: Photo_Pairing MUST use Pipeline-derived processing suffixes for method name resolution in analytics reports.
- **FR-011**: Photo_Pairing MUST use Pipeline-derived image extensions for file filtering when a Pipeline is available.
- **FR-012**: The all-numeric suffix detection for "separate image" grouping (e.g., `-2`, `-3`) MUST remain hardcoded and unchanged, not configurable through the Pipeline.
- **FR-013**: When no Pipeline is available for a Collection (no assigned Pipeline and no team default), all analysis tools MUST fall back to Config-based parameters, preserving existing behavior identically.
- **FR-014**: When an assigned Pipeline is structurally invalid (e.g., missing Capture node per FR-007, syntactically invalid `filename_regex`, or zero File nodes), the agent tool runner MUST catch the extraction error, log a warning, and fall back to Config-based parameters rather than failing the analysis.
- **FR-015**: A Camera entity MUST be created to represent physical camera equipment tracked per team, with attributes for camera ID, status (temporary/confirmed), display name, make, model, serial number, and notes.
- **FR-016**: Each Camera record MUST be unique per team and camera ID combination.
- **FR-017**: An agent-facing discovery endpoint MUST accept a batch of camera IDs discovered during analysis and idempotently create Camera records with `status: "temporary"` for any IDs not already registered. The endpoint MUST return all Camera records (existing and newly created) for the submitted IDs.
- **FR-018**: Camera auto-discovery MUST occur during Photo_Pairing analysis: after extracting unique camera IDs from image groups, the agent calls the discovery endpoint and uses the returned display names in analytics.
- **FR-019**: Camera auto-creation MUST be idempotent. Concurrent analysis jobs discovering the same camera ID MUST NOT create duplicate Camera records.
- **FR-020**: In offline mode or when the discovery endpoint is unreachable, camera discovery MUST fall back to using raw camera IDs as display names, logging a warning without failing the analysis.
- **FR-021**: A user-facing Camera management API MUST provide endpoints for listing (paginated, team-scoped), retrieving, updating, and deleting Camera records.
- **FR-022**: A Camera statistics endpoint MUST return KPI data (total cameras, confirmed count, temporary count).
- **FR-023**: The Pipeline used for analysis MUST be resolved in order: (1) Collection-specific Pipeline assignment, (2) team default Pipeline, (3) Config-based fallback.
- **FR-024**: Extension sets derived from the Pipeline MUST be case-insensitive (`.DNG` and `.dng` treated as equivalent).
- **FR-025**: The "Resources" page MUST consolidate Camera management and Pipeline management under a single tabbed interface, replacing the standalone Pipelines page.
- **FR-026**: The Resources page MUST have two tabs: "Cameras" (default) and "Pipelines", with URL-synced tab selection.
- **FR-027**: The sidebar MUST replace the "Pipelines" menu entry with "Resources".
- **FR-028**: The old `/pipelines` URL MUST redirect to `/resources?tab=pipelines` for backward compatibility.
- **FR-029**: The Pipelines tab MUST preserve all existing Pipeline functionality (list, create, edit, delete, activate, validate, import/export).
- **FR-030**: The Cameras tab MUST display a list of cameras with columns for Camera ID, Display Name, Make, Model, Status, and Modified, with filtering by status.
- **FR-031**: The Cameras tab MUST provide an edit dialog for confirming temporary cameras (updating status, display name, make, model, serial number, notes).
- **FR-032**: Each tab MUST show its own KPI stats in the TopHeader when active (Camera stats for Cameras tab, Pipeline stats for Pipelines tab).
- **FR-033**: File nodes marked as `optional: true` MUST still be included in the extension sets. Optionality affects validation, not recognition.
- **FR-034**: Pipeline configuration extraction MUST be deterministic: the same Pipeline definition MUST always produce the same configuration.

### Key Entities

- **Camera**: Represents a physical camera tracked per team. Key attributes: camera ID (4-character code from filenames), status (temporary or confirmed), display name, make, model, serial number, notes, custom metadata. Unique per team and camera ID. Identified externally by GUID with prefix `cam_`. Belongs to a team.
- **PipelineToolConfig**: A derived configuration structure extracted from a Pipeline definition. Not a persistent entity. Contains: filename regex, camera ID group, image extensions, metadata extensions, sidecar requirements, and processing suffix mappings. Serves as the bridge between the Pipeline graph structure and the simplified parameters needed by PhotoStats and Photo_Pairing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of PhotoStats and Photo_Pairing executions on Collections with an assigned Pipeline use Pipeline-derived configuration (extensions, regex, suffixes) instead of Config entries.
- **SC-002**: Photo_Pairing reports display human-readable camera names (from the Camera registry) for all cameras that have a display name, instead of showing raw 4-character codes.
- **SC-003**: Photo_Pairing reports display human-readable processing method names (from Pipeline Process node names) instead of raw method codes.
- **SC-004**: PhotoStats sidecar detection produces results consistent with Pipeline structure: inferred sidecar requirements match what Pipeline_Validation would detect for the same Pipeline.
- **SC-005**: Camera auto-discovery creates records for 100% of newly encountered camera IDs during online analysis, with zero manual pre-registration required.
- **SC-006**: No analysis failures occur when no Pipeline is available: Config-based fallback succeeds for 100% of no-Pipeline cases.
- **SC-007**: Analysis tool execution time does not increase by more than 5% compared to Config-based execution.
- **SC-008**: Users can navigate to the Resources page, view and manage cameras, and access all existing Pipeline functionality without loss of capability.
- **SC-009**: All previously bookmarked `/pipelines` URLs continue to work via redirect to `/resources?tab=pipelines`.

## Assumptions

- The `METADATA_EXTENSIONS` set (currently `{".xmp"}`) is sufficient for v1. New metadata formats will be rare and can be added to this single set when needed.
- Pipelines always have exactly one Capture node when valid. Multiple Capture nodes are not expected but are handled by using the first one found.
- The `filename_regex` property on Capture nodes is always present on valid Pipelines, as pipeline validation already enforces this.
- Camera IDs are short alphanumeric strings (typically 4 characters) extracted from filenames via regex capture groups.
- The Camera entity does not need EXIF-based enrichment in v1; camera details beyond the ID are entered manually by users.
- Existing analysis results stored in the database are self-contained and do not need migration when the configuration source changes.
- The `FilenameParser` utility remains available and unchanged for any non-Pipeline contexts.
- The agent's `TeamConfigCache` can be extended to include Pipeline data without breaking backward compatibility with older cache files.
- The `Box` icon from lucide-react is appropriate and available for the Resources page menu entry.
