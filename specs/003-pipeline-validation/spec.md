# Feature Specification: Photo Processing Pipeline Validation Tool

**Feature Branch**: `003-pipeline-validation`
**Created**: 2025-12-26
**Status**: Draft
**Input**: User description: "Issue #18. The PRD and the entire set of related documents are stored in docs/prd/pipeline-validation/"

## Clarifications

### Session 2025-12-26

- Q: When an ImageGroup contains extra files not defined in any pipeline path (e.g., unexpected PSD file alongside required CR3, XMP, DNG, TIF), how should the validator report these to the user? → A: Option C - Warning flag - Extra files trigger WARNING status, shown prominently in report summary statistics

- Q: When path traversal encounters a looping Process node (e.g., Photoshop edits looping back for iterative processing) and exceeds the maximum iterations limit, what should the validator do? → A: Option B with limit of 5 - Truncate path gracefully at iteration 5, validate collected File nodes, mark result with truncation note

- Q: When a Specific Image is classified as CONSISTENT-WITH-WARNING (all required files present plus extra files), should it be marked as archival ready? → A: Option A - Yes, archival ready - Extra files don't affect completeness of required pipeline files

- Q: When deduplicating File nodes that appear multiple times in the same path (e.g., `raw_image_1 (.CR3)` and `raw_image_2 (.CR3)` representing the same physical file), what matching strategy should the validator use? → A: Option A - Exact filename match - Deduplicate by comparing generated filenames exactly

- Q: When a Specific Image matches multiple termination paths simultaneously (e.g., matches both `termination_blackbox` with 100% completion AND `termination_browsable` with 100% completion), how should archival readiness statistics be reported? → A: Option B - Count in all matched - Count image in each termination type it satisfies (image can appear in both Black Box and Browsable counts)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Validate Photo Collection Against Processing Pipeline (Priority: P1)

A photographer has processed hundreds of photos through their workflow (camera capture → DNG conversion → tone mapping → export) and wants to verify that all photos in their collection are complete and ready for archival. They want to identify which photos are missing processing steps and which are ready for Black Box or Browsable Archive.

**Why this priority**: This is the core value proposition - validating collections against defined workflows. Without this, users cannot assess archival readiness or identify incomplete processing.

**Independent Test**: Can be fully tested by running the tool against a test folder with known complete and incomplete image groups, verifying that the HTML report correctly classifies groups as CONSISTENT, PARTIAL, or INCONSISTENT and identifies missing files.

**Acceptance Scenarios**:

1. **Given** a folder with 100 photo groups where 70 have complete Black Box Archive paths (CR3+XMP+DNG+TIF), 20 are missing TIF files, and 10 are missing XMP metadata, **When** the user runs `python3 pipeline_validation.py /path/to/photos`, **Then** the tool generates an HTML report showing 70 CONSISTENT groups (archival ready), 20 PARTIAL groups with specific missing TIF files identified, and 10 INCONSISTENT groups with missing XMP metadata highlighted.

2. **Given** a photo group AB3D0001 with files [CR3, XMP, DNG, TIF, lowres.JPG, hires.JPG] matching the complete Browsable Archive path, **When** validation runs, **Then** the group is classified as CONSISTENT with 100% completion for the browsable_termination path and marked as archival ready for Browsable Archive.

3. **Given** a photo group AB3D0042 with only a CR3 file and no XMP metadata, **When** validation runs, **Then** the group is classified as INCONSISTENT with a clear message indicating "Missing required XMP sidecar at import stage" and specific file expected: "AB3D0042.XMP".

4. **Given** a photo group AB3D0055 with complete Black Box Archive files [CR3, XMP, DNG, TIF] plus an unexpected PSD file not defined in any pipeline path, **When** validation runs, **Then** the group is classified as CONSISTENT-WITH-WARNING, marked as archival ready, with the extra file "AB3D0055.PSD" listed in the validation result and shown prominently in the HTML report's WARNING section.

---

### User Story 2 - Configure Custom Processing Pipelines (Priority: P2)

A photographer wants to define their specific processing workflow in a configuration file, including custom processing methods (DxO DeepPRIME, Topaz AI, Photoshop edits) and multiple archival endpoints (Black Box vs Browsable). They want the validation tool to check against their exact workflow, not a generic template.

**Why this priority**: Custom pipeline configuration makes the tool adaptable to different workflows. While a default pipeline is useful, photographers have unique processes requiring configuration flexibility.

**Independent Test**: Can be tested independently by creating a custom pipeline configuration YAML, running validation, and verifying that the tool correctly validates against the custom-defined nodes, processing methods, and termination points.

**Acceptance Scenarios**:

1. **Given** the user has a custom pipeline configuration defining a node-based graph with Capture → File (CR3) → Process (DxO_DeepPRIME_XD2s) → File (DNG) → Process (tone mapping) → File (TIF) → Termination (Black Box), **When** the tool loads the configuration, **Then** it successfully parses all 6 node types (Capture, File, Process, Pairing, Branching, Termination) and constructs the directed graph.

2. **Given** a pipeline configuration with branching at the denoise stage (Option 1: DNG conversion with DxO, Option 2: skip to tone mapping), **When** validation traverses the graph, **Then** it enumerates all possible paths through both branches and validates image groups against each possible path.

3. **Given** a pipeline configuration with processing method "DxO_DeepPRIME_XD2s" defined in the processing_methods section, **When** a Process node references this method_id, **Then** the validator generates expected filename "AB3D0001-DxO_DeepPRIME_XD2s.DNG" and checks for its existence.

4. **Given** a pipeline configuration is missing or has validation errors (e.g., invalid node references, circular dependencies), **When** the tool starts, **Then** it displays a clear error message identifying the specific issue and offers to generate a default pipeline configuration.

---

### User Story 3 - Handle Counter Looping and Multiple Captures (Priority: P2)

A photographer's camera counter has looped (reset to 0001 after reaching 9999), resulting in multiple captures with the same camera ID and counter. When exported to the same folder, these files have numerical suffixes (AB3D0001.CR3, AB3D0001-2.CR3, AB3D0001-3.CR3). They want each capture validated independently as separate Specific Images.

**Why this priority**: Counter looping is a real-world scenario for active photographers. Without handling this, the tool would incorrectly group separate captures together and produce invalid validation results.

**Independent Test**: Can be tested independently by creating an ImageGroup with multiple separate_images entries (suffix '', '2', '3'), running validation, and verifying that each Specific Image is validated independently with its own status and missing files list.

**Acceptance Scenarios**:

1. **Given** an ImageGroup AB3D0001 with two Specific Images: suffix='' with files [CR3, XMP, DNG, TIF] and suffix='2' with files [CR3-2, XMP-2, DNG-2], **When** validation runs, **Then** the first Specific Image is classified as CONSISTENT (complete Black Box path) and the second as PARTIAL (missing TIF-2 file).

2. **Given** a Specific Image with base_filename "AB3D0001-2" (suffix='2'), **When** generating expected filenames for File nodes, **Then** the validator correctly produces "AB3D0001-2.CR3", "AB3D0001-2.XMP", "AB3D0001-2.DNG", etc., using the suffix throughout the filename pattern.

3. **Given** a Specific Image "AB3D0001-2-HDR.TIF" where '-HDR' is a processing property and '-2' is the counter loop suffix, **When** parsing the filename, **Then** the tool correctly identifies suffix='2', processing_property='HDR', base_filename='AB3D0001-2', and extension='.TIF'.

---

### User Story 4 - Smart Caching for Performance and Iteration (Priority: P3)

A photographer is iterating on their pipeline configuration, adding new processing methods and termination points. They want to update the pipeline definition and re-run validation without waiting for the Photo Pairing Tool to re-scan thousands of files. The tool should reuse cached Photo Pairing results and only regenerate pipeline validation.

**Why this priority**: Large photo collections (10,000+ files) can take minutes to scan. Intelligent caching enables fast iteration on pipeline definitions and improves the user experience for subsequent runs.

**Independent Test**: Can be tested independently by running validation with initial pipeline configuration (creates cache), modifying only the pipeline definition, re-running validation, and verifying that Photo Pairing results are reused while pipeline validation is regenerated with updated logic.

**Acceptance Scenarios**:

1. **Given** a folder previously analyzed with cached Photo Pairing results (.photo_pairing_cache.json) and pipeline validation results (.pipeline_validation_cache.json), **When** the user runs validation again with unchanged folder contents and pipeline configuration, **Then** the tool displays "✓ Using cached pipeline validation results" and returns results instantly without re-scanning files.

2. **Given** cached results exist and the user modifies the pipeline configuration (adds a new Termination node), **When** validation runs, **Then** the tool displays "ℹ Pipeline definition has changed since last analysis" and offers to "Reuse Photo Pairing cache and regenerate validation (recommended)" or "Re-run Photo Pairing Tool from scratch".

3. **Given** the Photo Pairing cache file has been manually edited (hash mismatch detected), **When** validation runs, **Then** the tool prompts "⚠ Warning: Photo Pairing cache appears to have been manually edited" with options to "Trust edited cache and regenerate pipeline validation", "Discard edited cache and re-run Photo Pairing Tool", or "Cancel and review changes manually".

4. **Given** the user runs `python3 pipeline_validation.py /path/to/photos --force-regenerate`, **When** the tool starts, **Then** it ignores all cache files and regenerates both Photo Pairing results and pipeline validation from scratch.

5. **Given** the cache version format changes between tool versions (e.g., v1.0 cache vs v1.1 cache), **When** the tool detects a version mismatch, **Then** it automatically invalidates the old cache and regenerates results without prompting the user.

---

### User Story 5 - Generate Interactive HTML Reports (Priority: P3)

A photographer wants to review validation results in a visual, interactive HTML report with charts showing consistency distribution, pipeline path statistics, and detailed tables of incomplete groups. They want to open the report in a browser and quickly identify actionable next steps.

**Why this priority**: While critical for usability, the HTML report is secondary to core validation logic. A basic text output could suffice for initial testing, making this P3.

**Independent Test**: Can be tested independently by running validation and verifying that the generated HTML report uses the Jinja2 base template, includes Chart.js visualizations, displays summary statistics, and provides expandable tables of CONSISTENT/PARTIAL/INCONSISTENT groups.

**Acceptance Scenarios**:

1. **Given** validation completes for 1,247 image groups, **When** the HTML report is generated, **Then** it includes an executive summary section showing "✓ Consistent (Archival Ready): 892 groups (71.5%)", "⚠ Warning (Extra Files): 45 groups (3.6%)", "⚠ Partial Processing: 203 groups (16.3%)", "✗ Inconsistent (Missing Files): 152 groups (12.2%)".

2. **Given** the validation results include multiple termination paths (termination_blackbox, termination_browsable), **When** the HTML report renders, **Then** it displays archival readiness statistics: "Black Box Archive Ready: 654 groups (52.4%)" (includes both CONSISTENT and CONSISTENT-WITH-WARNING), "Browsable Archive Ready: 238 groups (19.1%)". Note: Counts can overlap - images matching both termination types are counted in both statistics.

3. **Given** the HTML report is generated, **When** the user opens it in a browser, **Then** it uses the shared base.html.j2 template with consistent styling, Chart.js theme, and includes a pie chart showing consistency status distribution and a bar chart showing groups per pipeline path.

4. **Given** a PARTIAL group is displayed in the report, **When** the user views the details, **Then** the report lists the specific missing files with expected filenames (e.g., "Missing: AB3D0001-WEB.jpg - Required for browsable_archive_path") and recommended actions.

---

### Edge Cases

- **What happens when a File node appears multiple times in the same path?**
  Example: `raw_image_1 (.CR3)` and `raw_image_2 (.CR3)` representing the same physical file before and after selection. The validator should deduplicate File nodes using exact filename matching when collecting expected files for a Specific Image (e.g., "AB3D0001.CR3" matches "AB3D0001.CR3", keeping only one entry).

- **How does the system handle looping Process nodes?**
  Example: Photoshop edits that loop back to `tiff_generation_branching` for iterative processing. The validator should limit loop traversal to max 5 iterations to prevent infinite path enumeration while still allowing valid iterative workflows. When the limit is exceeded, the path is truncated gracefully, collected File nodes are validated, and the result is marked with a truncation note.

- **What happens when an ImageGroup contains extra files not defined in any pipeline path?**
  Example: Group has [CR3, XMP, DNG, TIF, JPG] plus an unexpected PSD file. The validator should classify the group as CONSISTENT-WITH-WARNING if all required File nodes are present, triggering WARNING status shown prominently in report summary statistics with extra files listed. The group is marked as archival ready since all required pipeline files are complete.

- **How does the tool handle shared XMP files between CR3 and DNG?**
  Example: `AB3D0001.xmp` used by both `AB3D0001.cr3` and `AB3D0001.dng`. The validator should allow XMP sharing by default and mark metadata_status as "SHARED" for the DNG file node.

- **How does the tool handle Pairing nodes with multiple upstream paths?**
  Example: `metadata_pairing` has 3 paths arriving from branch 1 (raw_image) and 2 paths from branch 2 (xmp_metadata). The validator generates all 6 combinations (3×2=6) by merging each pair. Merged paths have max depth from either branch, union of files (deduplicated), and max iteration counts per node. Pairing nodes are processed in topological order (upstream first) to handle nested pairing correctly.

- **How does the system handle invalid pipeline configurations?**
  Example: Orphaned nodes (not reachable from Capture), missing node references in outputs, or multiple Capture nodes. The tool should detect these issues during configuration validation and display specific error messages before attempting validation.

- **What happens when file extensions in the pipeline don't match the config's photo_extensions?**
  Example: Pipeline defines a File node with extension ".HEIC" but photo_extensions only includes [.cr3, .dng, .tif, .jpg]. The configuration validator should flag this as an error and refuse to load the pipeline.

- **How does the tool handle very large collections (10,000+ groups)?**
  The validator should provide progress indicators during scanning, use efficient data structures (sets for file lookups), and complete analysis in under 60 seconds for 10,000 groups as per success criteria.

- **What happens when a Specific Image matches multiple termination paths?**
  Example: Image has all files for both `termination_blackbox` (CR3, XMP, DNG, TIF) AND `termination_browsable` (adds lowres.JPG, hires.JPG). The validator should count this image in archival readiness statistics for BOTH Black Box Archive and Browsable Archive, providing accurate counts of images ready for each archival type.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST load pipeline configuration from YAML defining nodes (Capture, File, Process, Pairing, Branching, Termination) with directed graph structure

- **FR-002**: System MUST validate pipeline configuration detecting orphaned nodes, invalid node references, circular dependencies, missing Capture node, and File extensions not matching photo_extensions config

- **FR-003**: System MUST integrate with Photo Pairing Tool to obtain ImageGroups grouped by camera_id and counter, then flatten each ImageGroup into individual Specific Images for independent validation

- **FR-004**: System MUST traverse the pipeline graph from Capture node to each Termination node, enumerating all possible paths while handling branching (choose ONE output), looping (limit to 5 iterations with graceful truncation), and parallel outputs (execute ALL). When loop limit exceeded, validator collects File nodes from truncated path and marks result with truncation note.

- **FR-005**: System MUST collect File nodes encountered on each path from Capture to Termination, generating expected filenames based on base_filename (camera_id + counter + suffix), processing methods from Process nodes, and File node extensions

- **FR-006**: System MUST validate each Specific Image by comparing actual files against expected files from File nodes, classifying as CONSISTENT (100% match, archival ready), CONSISTENT-WITH-WARNING (100% match plus extra files not in pipeline, archival ready), PARTIAL (subset match, not archival ready), or INCONSISTENT (no valid path match, not archival ready)

- **FR-007**: System MUST handle counter looping where multiple captures share the same camera_id and counter, validating each Specific Image with suffix ('', '2', '3', etc.) independently using base_filename that includes the suffix

- **FR-008**: System MUST validate metadata sidecar files (XMP) using PhotoStats' linking logic, supporting shared XMP between CR3 and DNG, separate XMP per file type, and embedded metadata (XMP optional) for TIF files

- **FR-009**: System MUST support Pairing nodes that combine paths from exactly 2 upstream branches using Cartesian product logic (if branch 1 has 3 paths and branch 2 has 5 paths, generate 15 combined paths). Pairing nodes MUST be processed in topological order (upstream first) using longest-path algorithm. When merging paths: (a) merged depth = max(depth1, depth2), (b) merged files = union of both paths (deduplicated), (c) merged iterations = max per node across both paths. Pairing nodes CANNOT be in loops (MAX_ITERATIONS=1, truncate if encountered again during DFS). System uses hybrid iterative approach: DFS to pairing node → merge all combinations → continue DFS downstream

- **FR-010**: System MUST support Branching nodes where validation explores ALL possible branch outputs to enumerate complete set of valid paths

- **FR-011**: System MUST support Process nodes that can chain (Process → Process without File interface) and loop (output back to earlier node), with processing method_ids from processing_methods config appending to filenames

- **FR-012**: System MUST deduplicate File nodes when the same file appears multiple times in a path using exact filename matching strategy (e.g., raw_image_1 and raw_image_2 both generate "AB3D0001.CR3", keep only one entry in expected files set)

- **FR-013**: System MUST cache Photo Pairing results and pipeline validation results in the analyzed folder (.photo_pairing_cache.json, .pipeline_validation_cache.json) with hash-based invalidation

- **FR-014**: System MUST detect cache invalidation triggers including pipeline definition changes (hash mismatch), folder content changes (file additions/removals/modifications), Photo Pairing cache manual edits, and pipeline validation results manual edits

- **FR-015**: System MUST prompt users when cache conflicts are detected (manual edits, multiple simultaneous changes) with options to trust, discard, or cancel the operation

- **FR-016**: System MUST support CLI flags: --force-regenerate (ignore cache), --cache-status (show cache state), --clear-cache (delete and regenerate), --config (custom config path), --output-format (html or json)

- **FR-017**: System MUST generate interactive HTML reports using Jinja2 templates extending base.html.j2 with sections for executive summary, pipeline path statistics, consistent groups table, warning groups table (with extra files listed), inconsistent groups table with missing files, and metadata validation status

- **FR-018**: System MUST include Chart.js visualizations in HTML reports showing consistency distribution (pie chart) and groups per pipeline path (bar chart)

- **FR-019**: System MUST provide comprehensive --help text showing usage examples, workflow steps, configuration guidance, and CLI options

- **FR-020**: System MUST display validation progress for long-running operations with status indicators during Photo Pairing scan, graph traversal, and report generation

- **FR-021**: System MUST mark Specific Images with status CONSISTENT-WITH-WARNING as archival ready since all required pipeline files are complete, while still prominently displaying the WARNING and extra files list to alert users of unexpected files

- **FR-022**: System MUST count each Specific Image in archival readiness statistics for ALL termination types it matches with 100% completion (image matching both termination_blackbox and termination_browsable is counted in both Black Box Archive Ready and Browsable Archive Ready statistics)

### Key Entities *(include if feature involves data)*

- **Pipeline Configuration**: Represents the complete processing workflow as a directed graph with nodes (6 types), processing methods mapping, and version metadata. Loaded from YAML config.

- **Node**: Abstract entity with types Capture (start), File (actual files), Process (transformations), Pairing (multi-branch merge with Cartesian product), Branching (conditional paths), Termination (endpoints). Each has id, name, output references. Pairing nodes must have exactly 2 inputs and cannot be in loops.

- **File Node**: Critical entity representing actual filesystem files. Attributes: file_type (Image/Metadata), extension (must match photo_extensions or metadata_extensions), generates expected filenames for validation.

- **Specific Image**: Unit of validation representing a single captured photo and all its processed derivatives. Attributes: camera_id, counter, suffix (for counter looping), base_filename, files list, unique_id. Distinct from ImageGroup which may contain multiple Specific Images.

- **ImageGroup**: Container from Photo Pairing Tool grouping files by camera_id + counter. Contains separate_images dictionary keyed by suffix ('', '2', '3'), where each entry is a Specific Image.

- **Validation Result**: Output entity for each Specific Image. Attributes: status (CONSISTENT/CONSISTENT-WITH-WARNING/PARTIAL/INCONSISTENT), matched_terminations list with completion percentages (can include multiple termination types), files with metadata_status, missing_files with reasons, extra_files list (for WARNING status), truncation_note (for paths exceeding loop limit), archival_ready_for map (termination_type → boolean, e.g., {'black_box': True, 'browsable': True}).

- **Path**: Sequence of nodes from Capture to Termination. Attributes: node_ids traversed, File nodes collected, processing methods accumulated, expected filenames generated.

- **Cache Metadata**: Tracking entity for cache invalidation. Attributes: pipeline_definition_hash, folder_content_hash, photo_pairing_cache_hash, results_hash, timestamps, version.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can analyze a collection of 10,000 image groups in under 60 seconds when using cached Photo Pairing results

- **SC-002**: Validation accuracy of 95% or higher when classifying image groups as CONSISTENT vs INCONSISTENT, verified against manually validated test dataset

- **SC-003**: Users can configure a custom pipeline with 5+ processing stages and 3+ termination points without reading full documentation, guided by inline YAML comments in pipeline-config-example.yaml

- **SC-004**: 90% of users successfully identify missing files for incomplete image groups on their first report review, measured by actionable next steps taken

- **SC-005**: Cache reuse reduces re-analysis time by 80% or more when only pipeline configuration changes (folder content unchanged)

- **SC-006**: HTML reports load in under 2 seconds in modern browsers for collections up to 5,000 image groups

- **SC-007**: Tool correctly handles counter looping scenarios with 100% accuracy, validating each Specific Image independently without cross-contamination

- **SC-008**: Users can identify which photos are ready for Black Box Archive vs Browsable Archive with a single report review, no manual file inspection required

## Assumptions *(auto-generated)*

- **A-001**: Pipeline configuration will be stored in the existing config/config.yaml under a new `processing_pipelines` section, maintaining backward compatibility with existing PhotoStats and Photo Pairing tools

- **A-002**: Default pipeline configuration will support the most common workflow: Camera (CR3) → Import (XMP) → DNG Conversion → Tone Mapping (TIF) → Web Export (JPG) → Black Box/Browsable Archive

- **A-003**: Processing method names will use standard naming conventions (DxO_DeepPRIME_XD2s, topaz, Edit, HDR, BW, lowres, hires) consistent with existing processing_methods config

- **A-004**: Photo Pairing Tool's ImageGroup structure with separate_images dictionary will remain stable and is the authoritative source for file grouping

- **A-005**: Metadata linking logic from PhotoStats (base filename matching for CR3→XMP) will be reused without modification

- **A-006**: HTML report filenames will follow the established pattern: pipeline_validation_report_YYYY-MM-DD_HH-MM-SS.html

- **A-007**: Maximum loop iteration depth will be 5 to prevent infinite path enumeration while supporting common iterative workflows (e.g., multiple Photoshop edit passes). When exceeded, paths are truncated gracefully with a truncation note in validation results.

- **A-008**: Chart.js will be loaded via CDN (not bundled) consistent with existing PhotoStats and Photo Pairing report templates

- **A-009**: File extensions in pipeline configuration will be case-insensitive for matching (.CR3 = .cr3)

- **A-010**: Shared XMP files between CR3 and DNG will be allowed by default without requiring separate XMP files unless explicitly named (e.g., AB3D0001-DNG.xmp)

- **A-011**: Cache files will use JSON format for human readability and manual editing capability, consistent with Photo Pairing Tool's .photo_pairing_cache.json

- **A-012**: Photographers will typically have 1-2 primary pipeline paths (80% of photos) with occasional variations, making path enumeration tractable

## Dependencies & Constraints *(auto-generated)*

### Dependencies

- **D-001**: Requires Photo Pairing Tool to generate ImageGroup structures with camera_id, counter, and separate_images dictionary

- **D-002**: Requires PhotoStats' metadata linking logic for CR3→XMP pairing validation

- **D-003**: Requires PhotoAdminConfig for YAML configuration loading and photo_extensions/metadata_extensions schema

- **D-004**: Requires Jinja2 (>=3.1.0) for HTML template rendering, reusing existing base.html.j2 template

- **D-005**: Requires Chart.js (via CDN) for report visualizations

- **D-006**: Requires Python 3.10+ for match/case syntax and modern type hinting

- **D-007**: Requires pytest for comprehensive test coverage (target >70% overall, >85% for validation engine)

### Constraints

- **C-001**: Pipeline configuration must be defined in YAML - no GUI editor in v1.0 (deferred to v2.0)

- **C-002**: Local filesystem analysis only - no cloud storage integration in v1.0 (S3, Google Drive deferred to v2.0)

- **C-003**: 1:1 file evolution only - multi-image workflows (HDR merging N:1, panorama stitching) deferred to v2.0

- **C-004**: Batch analysis mode only - real-time folder monitoring and webhook notifications deferred to v2.0

- **C-005**: Tool will NOT create, move, or delete files - validation only, no automated remediation in v1.0

- **C-006**: Maximum supported nodes per pipeline: 100 (reasonable limit to prevent performance degradation)

- **C-007**: Maximum ImageGroups per folder: 50,000 (practical limit for single-folder analysis)

## Open Questions *(pending clarification)*

[No critical open questions remain - all design decisions have been documented in the comprehensive PRD at docs/prd/pipeline-validation/]
