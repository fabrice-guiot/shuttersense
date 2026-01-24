# Feature Specification: Cloud Storage Bucket Inventory Import

**Feature Branch**: `107-bucket-inventory-import`
**Created**: 2026-01-24
**Status**: Draft
**Related Issue**: #40
**Related PRD**: `docs/prd/107-bucket-inventory-import.md`
**Input**: User description: "Import S3 Collections from S3 bucket inventory file"

---

## Overview

This feature enables ShutterSense to import cloud storage collection metadata from automated inventory reports (AWS S3 Inventory, Google Cloud Storage Insights) instead of making expensive API calls. The system parses inventory files to discover folder structures, map folders to Collections, cache file metadata, and detect changes between inventory snapshots.

**Supported Connectors**: S3 and GCS only (SMB has no inventory feature)

---

## User Scenarios & Testing

### User Story 1 - Configure Inventory Source (Priority: P1)

As an administrator with S3 or GCS inventory already configured in my cloud provider, I want to specify where my inventory reports are stored so that the system can parse them instead of making repeated list API calls.

**Why this priority**: Without inventory source configuration, no other functionality in this feature can work. This is the foundational capability that enables all subsequent user stories.

**Independent Test**: Configure an S3 connector with inventory settings, trigger a validation check, and verify the system can locate and read the manifest.json file.

**Acceptance Scenarios**:

1. **Given** an S3 connector exists, **When** I navigate to the connector's inventory configuration section, **Then** I see fields for destination bucket, source bucket name, inventory configuration name, and format selection.

2. **Given** a connector with server-stored credentials and valid inventory configuration details, **When** I save the configuration, **Then** the system validates that the inventory path exists and is accessible immediately using the stored credentials.

3. **Given** a connector with agent-side credentials and inventory configuration details, **When** I save the configuration, **Then** the system saves the configuration and creates a validation job for an agent with access to perform the accessibility check.

4. **Given** a validation job completes for agent-side credentials, **When** the agent reports validation results, **Then** the connector's inventory configuration status is updated to reflect whether the path is accessible or not.

5. **Given** inventory path validation fails (either immediately for server-stored credentials or via agent job), **When** I view the connector, **Then** I see a clear error message indicating the inventory path could not be validated with guidance on how to resolve.

6. **Given** a GCS connector exists, **When** I navigate to the connector's inventory configuration section, **Then** I see fields for destination bucket, report configuration name, and format selection (CSV or Parquet).

7. **Given** an SMB connector exists, **When** I view the connector, **Then** I do not see any inventory configuration options (inventory is not available for SMB).

8. **Given** a connector with agent-side credentials and no available agent, **When** I save inventory configuration, **Then** the configuration is saved with a "pending validation" status and the UI indicates validation requires an agent.

---

### User Story 2 - Import Inventory and Extract Folders (Priority: P1)

As a user with a configured inventory source, I want to trigger an inventory import so that I can see all folders in my bucket without making expensive API calls.

**Why this priority**: Folder extraction is the core value proposition of inventory import - it enables users to discover their bucket structure efficiently and is required before Collections can be mapped.

**Independent Test**: Trigger an import on a configured connector, verify a job is created in the queue, an agent executes the pipeline, and discovered folders appear on the connector record.

**Acceptance Scenarios**:

1. **Given** an S3 connector with valid inventory configuration, **When** I click "Import Inventory", **Then** a job is created in the JobQueue (not executed server-side).

2. **Given** an import job is queued, **When** an agent claims the job, **Then** the agent fetches the latest manifest.json from the configured inventory location.

3. **Given** the agent has fetched the S3 manifest, **When** processing data files, **Then** the agent downloads and decompresses gzip-compressed CSV files.

4. **Given** the agent has fetched the GCS manifest, **When** processing data files, **Then** the agent reads CSV or Parquet files directly (uncompressed).

5. **Given** inventory data is parsed, **When** the agent extracts folders, **Then** unique folder paths (entries ending with "/" or derived parent paths) are identified.

6. **Given** folder extraction completes, **When** the agent reports results, **Then** discovered folders are stored on the Connector record.

7. **Given** an import is in progress, **When** I view the connector in the UI, **Then** I see job progress via standard job status polling showing the current pipeline phase.

8. **Given** a bucket with 1 million objects, **When** I run the full import pipeline, **Then** the pipeline completes within 10 minutes.

---

### User Story 3 - Map Folders to Collections (Priority: P1)

As a user with imported inventory data, I want to select folders and create Collections from them so that I can organize and analyze specific subsets of my photo archive with appropriate lifecycle states.

**Why this priority**: Mapping folders to Collections is essential for users to actually use the discovered folder structure. Without this, discovered folders have no actionable purpose. The state assignment (Live, Archived, Closed) is critical as it drives the TTL (Time To Live) behavior for each Collection.

**Independent Test**: View the folder tree for a connector with imported inventory, select multiple folders respecting hierarchy constraints, proceed to review step, adjust names and states, and verify Collections are created with correct attributes.

**Workflow**: This is a two-step process:
1. **Step 1 - Folder Selection**: Browse the folder tree and select which folders should become Collections (with hierarchical constraints enforced).
2. **Step 2 - Review & Configure**: Review the draft collection list, adjust individual names and states, or batch-set state for all drafts, then confirm creation.

**Acceptance Scenarios**:

*Step 1 - Folder Selection:*

1. **Given** inventory folders have been imported, **When** I view the connector's inventory section and initiate "Create Collections", **Then** I see a hierarchical folder tree with expand/collapse functionality.

2. **Given** I am viewing the folder tree, **When** I select a folder node, **Then** that folder is marked for Collection creation.

3. **Given** I have selected a folder node, **When** I attempt to select an ancestor folder (upstream in hierarchy), **Then** the selection is prevented and I see an indication that overlapping selections are not allowed.

4. **Given** I have selected a folder node, **When** I attempt to select a descendant folder (downstream in hierarchy), **Then** the selection is prevented and I see an indication that overlapping selections are not allowed.

5. **Given** I have selected a folder node, **When** I select another folder on a parallel branch (sibling or cousin), **Then** the selection is allowed and both folders are marked for Collection creation.

6. **Given** a folder is already mapped to an existing Collection, **When** I view the folder tree, **Then** that folder shows an indicator that it is already mapped and cannot be selected again.

7. **Given** I have selected one or more folders, **When** I click "Continue" or "Review", **Then** I proceed to the review step with my selections.

*Step 2 - Review & Configure:*

8. **Given** I am in the review step, **When** the draft collection list is displayed, **Then** I see each selected folder with: proposed Collection name, current state (defaulting to a reasonable value), and folder path.

9. **Given** I am viewing the draft collection list, **When** I edit an individual draft's name, **Then** I can customize the Collection name for that specific folder.

10. **Given** I am viewing the draft collection list, **When** I change an individual draft's state, **Then** I can select from Live, Archived, or Closed for that specific Collection.

11. **Given** I am viewing the draft collection list, **When** I use the "Set all states" batch action and select a state, **Then** all draft Collections in the list are updated to that state.

12. **Given** I have reviewed and configured all draft Collections, **When** I confirm creation, **Then** all Collections are created with their configured names, states, and linked to the Connector with their respective folder paths.

13. **Given** I am in the review step, **When** I click "Back" or "Edit Selection", **Then** I return to the folder selection step with my previous selections preserved.

---

### User Story 4 - Automatic FileInfo Population (Priority: P1)

As a user with Collections mapped to inventory folders, I want file metadata to be automatically updated from inventory data so that analysis tools can run without making additional API calls.

**Why this priority**: FileInfo caching is the key performance optimization that justifies the entire feature - it eliminates redundant API calls for subsequent tool executions.

**Independent Test**: Create a Collection from an inventory folder, trigger an inventory import, verify FileInfo is populated on the Collection without any S3/GCS list API calls being made.

**Acceptance Scenarios**:

1. **Given** the import pipeline reaches Phase B, **When** processing begins, **Then** the agent queries the server for all Collections bound to this Connector.

2. **Given** Collections exist for this Connector, **When** the agent processes each Collection, **Then** inventory data is filtered by each Collection's folder path prefix.

3. **Given** filtered inventory data exists, **When** extracting FileInfo, **Then** the agent extracts key, size, last_modified, etag, and storage_class for each file.

4. **Given** FileInfo is extracted, **When** the agent reports results, **Then** the server stores FileInfo on the Collection record with `file_info_source: "inventory"`.

5. **Given** FileInfo is stored, **When** I view the Collection, **Then** I see "Last updated from inventory" timestamp displayed.

6. **Given** no Collections are mapped to the Connector, **When** Phase B executes, **Then** it is skipped (no-op).

7. **Given** a Collection has inventory-sourced FileInfo, **When** a tool runs on that Collection, **Then** the tool uses cached FileInfo instead of calling cloud list APIs.

8. **Given** I want fresh data from the cloud provider, **When** I click "Refresh from Cloud", **Then** a separate job is created to fetch live file metadata via API.

---

### User Story 5 - Scheduled Inventory Import (Priority: P2)

As an administrator, I want to schedule automatic inventory imports so that Collections stay up-to-date without manual intervention.

**Why this priority**: Scheduling is an efficiency improvement over manual imports but is not required for core functionality. Users can still manually trigger imports.

**Independent Test**: Configure a weekly import schedule on a connector, complete an import, verify the next scheduled job is automatically created with the correct scheduled_at timestamp.

**Acceptance Scenarios**:

1. **Given** a connector with inventory configured, **When** I view the inventory settings, **Then** I see schedule options: manual only, daily, or weekly.

2. **Given** I select a daily or weekly schedule, **When** I save the configuration, **Then** the system creates the first scheduled Job in the JobQueue with a future scheduled_at timestamp.

3. **Given** a scheduled import job completes, **When** the job finishes all phases, **Then** the system automatically creates the next scheduled Job based on the configured frequency.

4. **Given** scheduled imports are configured, **When** I view the connector, **Then** I see both the last import timestamp and the next scheduled import time.

5. **Given** a schedule is configured, **When** I click "Import Now", **Then** an immediate job is created independent of the schedule.

6. **Given** a scheduled job is pending, **When** I disable the schedule, **Then** the pending scheduled job is cancelled.

7. **Given** an import is already running for a Connector, **When** another import is triggered, **Then** the system prevents concurrent imports for the same Connector.

---

### User Story 6 - Delta Detection Between Inventories (Priority: P3)

As a user with periodic inventory imports, I want to see what changed since the last import so that I can identify new or modified photos in my archive.

**Why this priority**: Delta detection is valuable for monitoring but not essential for core import and caching functionality. Users can still use the feature without change tracking.

**Independent Test**: Run an import on a Collection with existing FileInfo, add/modify/delete files in the source bucket, run the next inventory import, verify delta summary correctly shows new/modified/deleted counts.

**Acceptance Scenarios**:

1. **Given** the import pipeline reaches Phase C, **When** processing begins, **Then** the agent compares current inventory data against each Collection's stored FileInfo.

2. **Given** comparison is performed, **When** changes are detected, **Then** the agent identifies new files (in current but not previous), modified files (different ETag or size), and deleted files (in previous but not current).

3. **Given** delta is calculated, **When** the agent reports results, **Then** delta summary (counts of new/modified/deleted) is stored per Collection.

4. **Given** an import completes, **When** I view the Collection, **Then** I see change statistics: X new, Y modified, Z deleted files.

5. **Given** a Collection has no previous FileInfo (first import after mapping), **When** Phase C executes, **Then** all files are reported as "new".

6. **Given** no Collections exist for the Connector, **When** Phase C executes, **Then** it is skipped (no-op).

---

### User Story 7 - Server-Side No-Change Detection (Priority: P2)

As a system optimization, when a Collection has inventory-sourced FileInfo stored server-side, the server should detect "no change" situations during job claim rather than sending the job to an agent, saving network round-trips and agent processing time.

**Why this priority**: This is a performance optimization that leverages the server-side FileInfo storage from US4. It's not required for core functionality but significantly improves system efficiency by avoiding unnecessary agent work.

**Background**: Currently, agents detect "no change" situations by computing a hash of the input state (file list + config) and comparing it to the previous execution's stored hash. This requires the agent to fetch the file list first. With inventory-sourced FileInfo now stored server-side, the server can perform this comparison during job claim.

**Independent Test**: Create a Collection with inventory-sourced FileInfo, run a job that completes successfully, trigger the same job type again without any file changes, verify the server auto-completes with "no_change" status without sending to agent.

**Acceptance Scenarios**:

1. **Given** a Collection has inventory-sourced FileInfo (`file_info_source: "inventory"`), **When** an agent claims a job for that Collection, **Then** the server computes an input state hash from the stored FileInfo and relevant job config.

2. **Given** the server has computed the input state hash, **When** a previous execution result exists with an `input_state_hash`, **Then** the server compares the two hashes.

3. **Given** the hashes match (no change detected), **When** the job claim is processed, **Then** the server auto-completes the job with `termination_status: "no_change"` without sending it to the agent.

4. **Given** the server auto-completes a job as "no_change", **When** the agent's claim response is returned, **Then** the server returns the next available job for that agent (if any) instead.

5. **Given** the hashes do not match (change detected), **When** the job claim is processed, **Then** the job is sent to the agent for normal execution.

6. **Given** a Collection does NOT have inventory-sourced FileInfo (`file_info_source` is null or "api"), **When** an agent claims a job, **Then** the server does NOT perform server-side no-change detection and sends the job to the agent.

7. **Given** no previous execution result exists for this job type on this Collection, **When** an agent claims the job, **Then** the server sends the job to the agent for normal execution.

8. **Given** a job is auto-completed as "no_change", **When** I view the job history, **Then** I see the job recorded with appropriate metadata indicating server-side auto-completion.

---

### Edge Cases

- **Empty inventory**: What happens when the inventory file exists but contains zero objects? The system should complete successfully with zero folders discovered.

- **Malformed inventory rows**: What happens when individual CSV rows are corrupted or malformed? The system should skip malformed rows, log warnings, and continue processing.

- **Missing required fields**: What happens when the inventory CSV is missing required fields (Size, LastModifiedDate)? The system should fail validation with a clear error message indicating which required fields are missing.

- **URL-encoded folder names**: What happens when folder paths contain URL-encoded characters (e.g., "Milledgeville%2C%20GA")? The system should decode URL-encoded characters when displaying and suggesting Collection names.

- **Inventory file not yet generated**: What happens when inventory is configured but AWS/GCS hasn't generated the first report yet? The system should display a clear message that no inventory data is available yet.

- **Stale inventory data**: What happens when inventory data is several days old? The system should display the inventory generation timestamp and warn users when data may be stale.

- **Very deep folder hierarchies**: What happens when folders are nested 10+ levels deep? The system should handle arbitrary nesting depth, though UI may need scrolling or truncation for display.

- **Concurrent imports**: What happens when a user triggers an import while another is running? The system should prevent concurrent imports for the same Connector with an appropriate message.

- **Agent unavailable**: What happens when no agent is available to process the import job? The job remains queued and the UI indicates no agents are available (per existing agent architecture).

- **Cross-bucket inventory**: What happens when the inventory destination bucket requires different credentials? The system should validate access during configuration and provide clear error if destination bucket is inaccessible.

- **Large inventory (millions of objects)**: What happens with inventories containing millions of objects? The agent should use streaming/chunked processing to stay under 1GB memory usage.

- **Agent-side credentials with no agent available**: What happens when a connector uses agent-side credentials but no agent is online? The configuration should be saved with "pending validation" status, and the UI should indicate validation will occur when an agent becomes available.

- **Validation job timeout**: What happens when an agent-side credential validation job takes too long or the agent disconnects? The system should mark validation as failed with a timeout error and allow the user to retry.

- **Overlapping folder selection attempt**: What happens when a user tries to select a folder that is an ancestor or descendant of an already-selected folder? The UI should prevent the selection and provide a clear explanation that overlapping Collections are not allowed.

- **All folders already mapped**: What happens when all folders in the inventory are already mapped to Collections? The UI should indicate that no unmapped folders are available and disable the "Create Collections" action.

- **No state selected during review**: What happens if a user tries to create Collections without setting a state? The system should require a state for each Collection before allowing creation, as state drives TTL behavior.

- **Large number of folder selections**: What happens when a user selects 100+ folders to create Collections? The review step should handle large lists with pagination or virtualization to maintain UI performance.

- **Server-side no-change with stale FileInfo**: What happens when FileInfo is very old but unchanged? The system should still detect "no change" based on hash comparison, not FileInfo age.

- **Server-side no-change with config change**: What happens when the job config has changed but FileInfo hasn't? The hash will differ (includes config), so the job should be sent to the agent.

- **Server-side no-change with no previous execution**: What happens on the first execution of a job type? No previous hash exists, so the job should be sent to the agent.

- **Multiple jobs auto-completed in sequence**: What happens when an agent claims a job, it's auto-completed, and the next job is also "no change"? The server should continue returning next jobs until one requires agent execution or queue is empty.

- **Server-side no-change for non-inventory FileInfo**: What happens when FileInfo was populated via API (not inventory)? Server-side detection should NOT be performed; job goes to agent who will fetch fresh file list.

---

## Requirements

### Functional Requirements

#### Inventory Configuration

- **FR-001**: System MUST add an `inventory_config` field to S3 and GCS Connector configuration schemas.
- **FR-002**: S3 inventory configuration MUST include: destination_bucket, source_bucket, config_name, and format selection.
- **FR-003**: GCS inventory configuration MUST include: destination_bucket, report_config_name, and format selection.
- **FR-004**: System MUST validate inventory path accessibility based on credential storage model:
  - For server-stored credentials: validation MUST occur immediately during configuration save.
  - For agent-side credentials: system MUST create a validation job for an agent to perform the check asynchronously.
- **FR-005**: Inventory settings MUST be stored encrypted with other connector credentials.
- **FR-006**: "Import Inventory" action MUST only be visible for S3 and GCS connectors (not SMB).
- **FR-007**: System MUST track inventory configuration validation status (pending, validated, failed) for connectors with agent-side credentials.
- **FR-008**: "Import Inventory" action MUST only be enabled when inventory configuration has been validated successfully.

#### Inventory Import Pipeline (Agent-Executed)

**Phase A: Folder Extraction**

- **FR-010**: "Import Inventory" action MUST create a Job in the JobQueue (never execute server-side).
- **FR-011**: System MUST register `InventoryImportTool` as an agent-executable tool type.
- **FR-012**: Agent MUST fetch and parse manifest file from the inventory location (S3: `manifest.json` with `files` array; GCS: `manifest.json` with `report_shards_file_names` array).
- **FR-013**: Agent MUST download data files referenced in the manifest (S3: decompress gzip-compressed files; GCS: read uncompressed CSV or Parquet).
- **FR-014**: Agent MUST parse inventory format with provider-specific field mapping (S3: Key, Size, LastModifiedDate, ETag, StorageClass; GCS: name, size, updated, etag, storageClass).
- **FR-015**: Agent MUST retain parsed inventory data locally for the duration of the pipeline execution.
- **FR-016**: Agent MUST extract unique folder paths from object keys/names.
- **FR-017**: Agent MUST report folder results to the server; server MUST store folders as `InventoryFolder` records.

**Phase B: FileInfo Population**

- **FR-020**: Agent MUST query the server for all Collections bound to the Connector.
- **FR-021**: For each Collection, agent MUST filter inventory data by the Collection's folder path prefix.
- **FR-022**: Agent MUST extract FileInfo containing: key, size, last_modified, etag, storage_class.
- **FR-023**: Agent MUST report FileInfo array to the server per Collection.
- **FR-024**: Server MUST store FileInfo on Collection with `file_info_source: "inventory"`.
- **FR-025**: Server MUST update `file_info_updated_at` timestamp when FileInfo is stored.
- **FR-026**: Phase B MUST be skipped (no-op) if no Collections exist for the Connector.

**Phase C: Delta Detection**

- **FR-030**: Agent MUST compare current inventory data against each Collection's stored FileInfo.
- **FR-031**: Agent MUST detect: new files, modified files (ETag or size changed), and deleted files.
- **FR-032**: Agent MUST report delta summary per Collection: counts of new, modified, and deleted files.
- **FR-033**: Server MUST store delta summary on the Collection or ImportSession record.
- **FR-034**: Phase C MUST be skipped (no-op) if no Collections exist or no previous FileInfo is available.
- **FR-035**: Agent MUST support streaming/chunked processing for inventories with millions of objects.

#### Folder-to-Collection Mapping

**Step 1 - Folder Selection:**

- **FR-040**: System MUST provide a UI component for hierarchical folder tree visualization with expand/collapse.
- **FR-041**: System MUST enforce hierarchical selection constraints: when a folder is selected, all ancestor and descendant folders MUST be disabled for selection.
- **FR-042**: System MUST allow selection of folders on parallel branches (siblings, cousins) without restriction.
- **FR-043**: System MUST visually indicate folders that are already mapped to existing Collections and prevent their re-selection.
- **FR-044**: System MUST allow users to proceed to review step only when at least one folder is selected.

**Step 2 - Review & Configure:**

- **FR-045**: System MUST display a draft collection list showing: proposed name, state, and source folder path for each selection.
- **FR-046**: System MUST implement an intelligent name suggestion algorithm for Collection names.
- **FR-047**: Name suggestion MUST follow rules: replace "/" with " - ", strip trailing slash, decode URL-encoded characters, apply title case.
- **FR-048**: System MUST allow individual editing of each draft Collection's name.
- **FR-049**: System MUST require a state (Live, Archived, Closed) for each Collection, as state drives TTL behavior.
- **FR-050**: System MUST allow individual editing of each draft Collection's state.
- **FR-051**: System MUST provide a batch action to set state for all draft Collections at once.
- **FR-052**: System MUST allow users to return to the selection step with previous selections preserved.

**Collection Creation:**

- **FR-053**: Collection creation MUST link the Collection to the Connector with the folder path as location.
- **FR-054**: Collection creation MUST set the specified state (Live, Archived, Closed) on each Collection.
- **FR-055**: System MUST support batch Collection creation from multiple selected folders in a single operation.

#### FileInfo Usage by Tools

- **FR-056**: FileInfo schema MUST include: key, size (bytes), last_modified (ISO8601), etag, storage_class.
- **FR-057**: Analysis tools MUST check Collection.file_info before calling cloud list APIs.
- **FR-058**: System MUST provide a "Refresh from Cloud" action that fetches live file metadata via separate job.
- **FR-059**: System MUST track `file_info_updated_at` and `file_info_source` on each Collection.

#### Scheduling

- **FR-060**: System MUST add `inventory_schedule` field to Connector configuration.
- **FR-061**: Schedule options MUST include: manual only, daily, weekly.
- **FR-062**: When schedule is enabled, system MUST create the first scheduled Job with a future `scheduled_at` timestamp.
- **FR-063**: Upon job completion (all phases), system MUST automatically create the next scheduled Job.
- **FR-064**: Next job's `scheduled_at` MUST be calculated as: completion time + configured interval.
- **FR-065**: System MUST prevent concurrent imports for the same Connector.
- **FR-066**: Disabling the schedule MUST cancel any pending scheduled jobs.
- **FR-067**: "Import Now" action MUST create an immediate job independent of any configured schedule.

#### Server-Side No-Change Detection

- **FR-070**: During job claim, server MUST compute input state hash for Collections with `file_info_source: "inventory"`.
- **FR-071**: Input state hash MUST include: hash of stored FileInfo array + relevant job configuration data.
- **FR-072**: Server MUST compare computed hash against `input_state_hash` from the most recent execution result for the same job type on the same Collection.
- **FR-073**: If hashes match, server MUST auto-complete the job with `termination_status: "no_change"` without sending to agent.
- **FR-074**: If hashes match, server MUST return the next available job to the claiming agent (if any exists).
- **FR-075**: Server MUST NOT perform server-side no-change detection for Collections where `file_info_source` is null or "api".
- **FR-076**: Auto-completed "no_change" jobs MUST be recorded in job history with metadata indicating server-side auto-completion.
- **FR-077**: If no previous execution result exists, server MUST send the job to the agent for normal execution.
- **FR-078**: Server-side no-change detection MUST NOT block or delay the job claim response.

### Key Entities

- **InventoryConfig**: Configuration for inventory source location, embedded within Connector credentials. Contains destination bucket, source/config identifiers, format, and schedule settings. Separate schemas for S3 (S3InventoryConfig) and GCS (GCSInventoryConfig).

- **InventoryFolder**: A discovered folder path from inventory data. GUID prefix: `fld_`. Contains connector reference, path string, object count, total size, last modified timestamp, and discovery timestamp. Relationship to Connector (many-to-one).

- **FileInfo**: Cached file metadata from inventory, stored as JSONB array on Collection. Contains key, size, last_modified, etag, storage_class. Used by analysis tools to avoid cloud API calls.

- **Collection Extensions**: Existing Collection entity extended with: file_info (JSONB array), file_info_updated_at (timestamp), file_info_source (enum: "api" or "inventory").

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can complete inventory configuration and trigger their first import within 5 minutes of starting.

- **SC-002**: Full import pipeline (all three phases) completes within 10 minutes for buckets containing 1 million objects.

- **SC-003**: Manifest fetch and parse completes within 10 seconds for any inventory size.

- **SC-004**: Folder tree renders with 10,000 folders within 2 seconds in the UI.

- **SC-005**: Agent memory usage stays under 1GB during pipeline execution for inventories up to 5 million objects.

- **SC-006**: 90% reduction in cloud list API calls achieved when analysis tools run on Collections with inventory-sourced FileInfo.

- **SC-007**: Zero cloud list API calls made when running analysis tools on Collections with valid cached FileInfo.

- **SC-008**: 99% of inventory imports complete successfully without errors.

- **SC-009**: FileInfo accuracy matches direct cloud API results (same data values for key, size, last_modified, etag).

- **SC-010**: Users can browse and select from a folder tree of 10,000+ folders without UI performance degradation.

- **SC-011**: Server-side no-change detection adds less than 50ms latency to job claim response.

- **SC-012**: 100% of "no change" situations for inventory-sourced Collections are detected server-side without agent involvement.

---

## Assumptions

- Users have already configured S3 Inventory or GCS Storage Insights in their cloud provider console before using this feature.
- Inventory destination buckets are accessible using the same credentials configured on the Connector.
- CSV is the primary inventory format; ORC and Parquet support may be added in future iterations.
- Inventory generation frequency (daily/weekly) is configured in the cloud provider, not in ShutterSense.
- The agent architecture from feature 021 (distributed agents) is already implemented and operational.
- Job queue infrastructure from existing features is available for scheduling import jobs.
- Existing Connector credential encryption mechanisms will be reused for inventory settings.
- Connectors may use either server-stored credentials or agent-side credentials; this feature supports both models with appropriate validation flows.
