# Photo-Admin Domain Model

**Version:** 1.2.0
**Last Updated:** 2026-01-12
**Status:** Living Document

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Application Vision](#application-vision)
3. [Technical Standards](#technical-standards)
4. [Entity Classification](#entity-classification)
5. [Implemented Entities](#implemented-entities)
6. [Planned Entities](#planned-entities)
7. [Entity Relationships](#entity-relationships)
8. [Data Architecture Principles](#data-architecture-principles)
9. [Appendices](#appendices)

---

## Executive Summary

This document defines the domain model for the Photo-Admin application, a comprehensive toolbox designed to help photographers manage their daily workflows, organize photo collections, and gain insights through analytics. It serves as the authoritative reference for all current and future development efforts.

The domain model is divided into two categories:
- **Implemented Entities**: Currently available in the codebase (Branch: `007-remote-photos-completion`)
- **Planned Entities**: Future entities that will be implemented in upcoming epics

---

## Application Vision

### Primary Goals

1. **Operational Support**: Help photographers run upcoming events smoothly through calendar management, logistics tracking, and workflow automation.

2. **Historical Organization**: Provide tools to record, catalog, and organize historical photo collections (events that occurred before adopting the application).

### Secondary Goals

3. **Analytics & Insights**: Aggregate data from activities and photos to generate actionable analytics:
   - Camera usage trends and maintenance scheduling
   - Event scheduling conflict detection
   - Workflow efficiency metrics
   - Equipment utilization patterns

### Target Users

- **Professional Photographers**: Studio owners, event photographers, sports/wildlife photographers
- **Hobbyist Photographers**: Enthusiasts managing personal photo collections
- **Photography Teams**: Organizations with multiple photographers sharing resources

---

## Technical Standards

### Global Unique Identifiers (GUIDs) (Issue #42)

All user-facing entities MUST use Global Unique Identifiers (GUIDs) as their **primary external identifier** in all presentation layers (APIs, URLs, UI). Numeric IDs are internal-only.

| Aspect | Specification |
|--------|---------------|
| **UUID Version** | UUIDv7 (time-ordered for database efficiency) |
| **GUID Format** | Crockford's Base32 with entity-type prefix |
| **Property Name** | `.guid` on all models and API responses |
| **Database Storage** | Binary UUID (16 bytes) indexed column |
| **Database PKs** | Auto-increment integers (internal joins only) |

**GUID Format:** `{prefix}_{26-char Crockford Base32}`

Example: `col_01hgw2bbg0000000000000001`

**Entity Prefixes:**

| Entity Type | Prefix | Example GUID | Status |
|-------------|--------|--------------|--------|
| Collection | `col_` | `col_01hgw2bbg0000000000000000` | Implemented |
| Connector | `con_` | `con_01hgw2bbg0000000000000001` | Implemented |
| Pipeline | `pip_` | `pip_01hgw2bbg0000000000000002` | Implemented |
| Result | `res_` | `res_01hgw2bbg0000000000000003` | Implemented |
| Job | `job_` | `job_01hgw2bbg0000000000000004` | Implemented (in-memory) |
| ImportSession | `imp_` | `imp_01hgw2bbg0000000000000005` | Implemented (in-memory) |
| Event | `evt_` | `evt_01hgw2bbg0000000000000006` | Implemented (Issue #39) |
| EventSeries | `ser_` | `ser_01hgw2bbg0000000000000007` | Implemented (Issue #39) |
| Category | `cat_` | `cat_01hgw2bbg0000000000000008` | Implemented (Issue #39) |
| Location | `loc_` | `loc_01hgw2bbg0000000000000009` | Implemented (Issue #39) |
| Organizer | `org_` | `org_01hgw2bbg000000000000000a` | Implemented (Issue #39) |
| Performer | `prf_` | `prf_01hgw2bbg000000000000000b` | Implemented (Issue #39) |
| User | `usr_` | `usr_01hgw2bbg000000000000000c` | Planned |
| Team | `ten_` | `ten_01hgw2bbg000000000000000d` | Planned |
| Camera | `cam_` | `cam_01hgw2bbg000000000000000e` | Planned |
| Album | `alb_` | `alb_01hgw2bbg000000000000000f` | Planned |
| Image | `img_` | `img_01hgw2bbg0000000000000010` | Planned |
| File | `fil_` | `fil_01hgw2bbg0000000000000011` | Planned |
| Workflow | `wfl_` | `wfl_01hgw2bbg0000000000000012` | Planned |
| Agent | `agt_` | `agt_01hgw2bbg0000000000000013` | Planned |

**Key Implementation Files:**
- `backend/src/services/guid.py` - GuidService for generation, encoding, validation
- `backend/src/models/mixins/external_id.py` - ExternalIdMixin for database entities
- `frontend/src/utils/guid.ts` - Frontend GUID utilities

### Multi-Tenancy Model

The application implements team-based data isolation:

- Users belong to exactly one Team (with a default personal team for solo users)
- All data queries are automatically scoped to the user's Team
- Cross-team data sharing is explicitly prohibited at the database level

---

## Entity Classification

### Implementation Status Legend

| Status | Icon | Description |
|--------|------|-------------|
| Implemented | :white_check_mark: | Available in current codebase |
| Planned | :construction: | Designed, awaiting implementation |
| Conceptual | :thought_balloon: | Early design phase |

### Entity Overview

| Entity | Status | Category | Priority |
|--------|--------|----------|----------|
| [Collection](#collection) | :white_check_mark: | Storage | - |
| [Connector](#connector) | :white_check_mark: | Storage | - |
| [Pipeline](#pipeline) | :white_check_mark: | Workflow | - |
| [PipelineHistory](#pipelinehistory) | :white_check_mark: | Workflow | - |
| [AnalysisResult](#analysisresult) | :white_check_mark: | Workflow | - |
| [Configuration](#configuration) | :white_check_mark: | System | - |
| [Event](#event) | :white_check_mark: | Calendar | Completed (#39) |
| [EventSeries](#eventseries) | :white_check_mark: | Calendar | Completed (#39) |
| [Category](#category-1) | :white_check_mark: | Reference | Completed (#39) |
| [Location](#location) | :white_check_mark: | Reference | Completed (#39) |
| [Organizer](#organizer-1) | :white_check_mark: | Reference | Completed (#39) |
| [Performer](#performer-1) | :white_check_mark: | Reference | Completed (#39) |
| [EventPerformer](#eventperformer-junction-table) | :white_check_mark: | Junction | Completed (#39) |
| [User](#user) | :construction: | Identity | High |
| [Team](#team) | :construction: | Identity | High |
| [Camera](#camera) | :construction: | Equipment | Medium |
| [Album](#album) | :construction: | Content | Medium |
| [Image](#image) | :construction: | Content | Medium |
| [File](#file) | :construction: | Content | Medium |
| [Workflow](#workflow) | :construction: | Workflow | Medium |
| [WorkflowCollection](#workflowcollection-junction-table) | :construction: | Junction | Medium |
| [ImageWorkflowProgress](#imageworkflowprogress) | :construction: | Junction | Medium |
| [ImagePerformer](#imageperformer-junction-table) | :construction: | Junction | Medium |
| [Agent](#agent) | :thought_balloon: | Infrastructure | Future |

---

## Implemented Entities

### Collection

**Purpose:** Represents a physical storage location containing photo files.

**Current Location:** `backend/src/models/collection.py`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `external_id` | UUID | unique, not null | UUIDv7 for GUID generation |
| `connector_id` | Integer | FK(connectors.id), nullable | Reference to remote connector |
| `pipeline_id` | Integer | FK(pipelines.id), nullable | Assigned pipeline (SET NULL on delete) |
| `pipeline_version` | Integer | nullable | Pinned pipeline version |
| `name` | String(255) | unique, not null | User-friendly display name |
| `type` | Enum | not null | `LOCAL`, `S3`, `GCS`, `SMB` |
| `location` | String(1024) | not null | Path or bucket location |
| `state` | Enum | not null, default=LIVE | `LIVE`, `CLOSED`, `ARCHIVED` |
| `cache_ttl` | Integer | nullable | Override default cache TTL (seconds) |
| `is_accessible` | Boolean | not null, default=true | Connection status |
| `last_error` | Text | nullable | Most recent error message |
| `metadata_json` | Text | nullable | User-defined metadata (JSON) |
| `storage_bytes` | BigInteger | nullable | Total storage in bytes |
| `file_count` | Integer | nullable | Total number of files |
| `image_count` | Integer | nullable | Number of images after grouping |
| `created_at` | DateTime | not null | Creation timestamp |
| `updated_at` | DateTime | not null, auto-update | Last modification timestamp |

**GUID Property:** `.guid` returns `col_{crockford_base32}` format (e.g., `col_01hgw2bbg0000000000000001`)

**State-Based Cache TTL Defaults:**

| State | Default TTL | Rationale |
|-------|-------------|-----------|
| `LIVE` | 3,600s (1 hour) | Active work, frequent changes |
| `CLOSED` | 86,400s (24 hours) | Finished work, infrequent changes |
| `ARCHIVED` | 604,800s (7 days) | Long-term storage, infrastructure monitoring |

**Location Format by Type:**

| Type | Format | Example |
|------|--------|---------|
| `LOCAL` | Absolute filesystem path | `/photos/2026/january` |
| `S3` | bucket-name/optional/prefix | `my-photos-bucket/raw/2026` |
| `GCS` | bucket-name/optional/prefix | `my-gcs-bucket/collections` |
| `SMB` | /share-path/optional/prefix | `/photos-share/archive` |

**Relationships:**
- Many-to-one with Connector (RESTRICT on delete)
- Many-to-one with Pipeline (SET NULL on delete)
- One-to-many with AnalysisResult (CASCADE delete)
- One-to-many with File (RESTRICT delete - Files must be moved/deleted first)
- Many-to-many with Workflow (via WorkflowCollection junction)

**Collection vs Image vs File:**

Collections contain **Files**, not Images directly. A Collection is a storage location; an Image is a logical concept that may span multiple Collections through its Files:

```
┌──────────────────────────────────────────────────────────────────────┐
│                     WORKFLOW: "Airshow Processing"                    │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Collection A              Collection B              Collection C     │
│  "Card1-Import"           "Selects"                 "Exports"         │
│  (role: SOURCE)           (role: WORKING)           (role: OUTPUT)    │
│  ┌─────────────┐          ┌─────────────┐          ┌─────────────┐   │
│  │AB3D0001.CR3 │          │AB3D0001.DNG │          │AB3D0001.TIF │   │
│  │AB3D0001.XMP │──────────│             │──────────│             │   │
│  │             │  Image   │             │  Image   │             │   │
│  │AB3D0002.CR3 │ AB3D0001 │AB3D0002.DNG │ AB3D0001 │AB3D0002.TIF │   │
│  │AB3D0002.XMP │──────────│             │──────────│             │   │
│  └─────────────┘          └─────────────┘          └─────────────┘   │
│                                                                       │
│  All 6 files shown belong to 2 Images, spread across 3 Collections   │
└──────────────────────────────────────────────────────────────────────┘
```

---

### Connector

**Purpose:** Stores encrypted authentication credentials for remote storage systems.

**Current Location:** `backend/src/models/connector.py`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `external_id` | UUID | unique, not null | UUIDv7 for GUID generation |
| `name` | String(255) | unique, not null | User-friendly name |
| `type` | Enum | not null | `S3`, `GCS`, `SMB` |
| `credentials` | Text | not null | Encrypted JSON credentials |
| `metadata_json` | Text | nullable | User-defined metadata |
| `is_active` | Boolean | not null, default=true | Active status |
| `last_validated` | DateTime | nullable | Last successful connection test |
| `last_error` | Text | nullable | Last connection error |
| `created_at` | DateTime | not null | Creation timestamp |
| `updated_at` | DateTime | not null, auto-update | Last modification timestamp |

**GUID Property:** `.guid` returns `con_{crockford_base32}` format (e.g., `con_01hgw2bbg0000000000000001`)

**Credentials Format (Decrypted JSON):**

```json
// S3
{
  "aws_access_key_id": "AKIA...",
  "aws_secret_access_key": "...",
  "region": "us-west-2",
  "endpoint_url": null  // Optional for S3-compatible storage
}

// GCS
{
  "service_account_json": "{...}"  // Full service account JSON
}

// SMB
{
  "server": "192.168.1.100",
  "share": "photos",
  "username": "photographer",
  "password": "...",
  "domain": null  // Optional
}
```

**Design Rationale:**
- **Credential Reuse:** Multiple collections share one connector (e.g., 50 S3 buckets)
- **Key Rotation:** Master key rotation only re-encrypts Connector table
- **Future-Proof:** Enables connector-level access control for multi-user support

---

### Pipeline

**Purpose:** Defines photo processing workflow as a directed graph of nodes and edges.

**Current Location:** `backend/src/models/pipeline.py`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `external_id` | UUID | unique, not null | UUIDv7 for GUID generation |
| `name` | String(255) | unique, not null | Display name |
| `description` | Text | nullable | Purpose/usage description |
| `nodes_json` | JSONB | not null | Node definitions array |
| `edges_json` | JSONB | not null | Edge connections array |
| `version` | Integer | not null, default=1 | Current version number |
| `is_active` | Boolean | not null, default=false | Available for use |
| `is_default` | Boolean | not null, default=false | Default for tool execution |
| `is_valid` | Boolean | not null, default=false | Structure validation passed |
| `validation_errors` | JSONB | nullable | Validation error messages |
| `created_at` | DateTime | not null | Creation timestamp |
| `updated_at` | DateTime | not null, auto-update | Last modification timestamp |

**GUID Property:** `.guid` returns `pip_{crockford_base32}` format (e.g., `pip_01hgw2bbg0000000000000001`)

**Node Types:**

| Type | Purpose | Key Properties |
|------|---------|----------------|
| `capture` | Entry point for camera captures | `camera_id_pattern`, `counter_pattern` |
| `file` | Represents a file extension stage | `extension`, `optional` |
| `process` | Processing step (HDR, BW, etc.) | `suffix`, `description` |
| `pairing` | Groups related files | `inputs` (array of node IDs) |
| `branching` | Conditional path selection | `condition`, `value` |
| `termination` | End state classification | `name`, `classification` |

**Node Structure Example:**
```json
[
  {"id": "capture_1", "type": "capture", "properties": {"camera_id_pattern": "[A-Z0-9]{4}"}},
  {"id": "file_raw", "type": "file", "properties": {"extension": ".dng", "optional": false}},
  {"id": "file_xmp", "type": "file", "properties": {"extension": ".xmp", "optional": false}},
  {"id": "process_hdr", "type": "process", "properties": {"suffix": "-HDR"}},
  {"id": "done", "type": "termination", "properties": {"classification": "CONSISTENT"}}
]
```

**Edge Structure Example:**
```json
[
  {"from": "capture_1", "to": "file_raw"},
  {"from": "file_raw", "to": "process_hdr"},
  {"from": "process_hdr", "to": "done"}
]
```

**Constraints:**
- Only ONE pipeline can have `is_default=true` (application-enforced)
- Default pipeline MUST be active (`is_default` implies `is_active`)

---

### PipelineHistory

**Purpose:** Immutable audit trail of pipeline version changes.

**Current Location:** `backend/src/models/pipeline_history.py`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `pipeline_id` | Integer | FK(pipelines.id), not null | Parent pipeline |
| `version` | Integer | not null | Version number snapshot |
| `nodes_json` | JSONB | not null | Node state at this version |
| `edges_json` | JSONB | not null | Edge state at this version |
| `change_summary` | String(500) | nullable | Description of changes |
| `changed_by` | String(255) | nullable | User who made the change |
| `created_at` | DateTime | not null | Version creation timestamp |

**Constraints:**
- `(pipeline_id, version)` is unique
- Records are NEVER modified after creation
- CASCADE delete when parent pipeline is deleted

---

### AnalysisResult

**Purpose:** Stores execution history and results for asynchronous analysis jobs run against any domain entity.

**Current Location:** `backend/src/models/analysis_result.py`

AnalysisResult is a **polymorphic results store** designed to capture the output of complex analysis jobs executed through the async Job Queue. While the current implementation supports only Collections and Pipelines as targets, the future vision expands this to any analyzable domain entity.

#### Current Implementation

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `external_id` | UUID | unique, not null | UUIDv7 for GUID generation |
| `collection_id` | Integer | FK(collections.id), nullable | Target collection |
| `tool` | String(50) | not null | Tool name |
| `pipeline_id` | Integer | FK(pipelines.id), nullable | Pipeline used |
| `pipeline_version` | Integer | nullable | Pipeline version at execution |
| `status` | Enum | not null | `COMPLETED`, `FAILED`, `CANCELLED` |
| `started_at` | DateTime | not null | Execution start |
| `completed_at` | DateTime | not null | Execution end |
| `duration_seconds` | Float | not null | Execution duration |
| `results_json` | JSONB | not null | Structured results data |
| `report_html` | Text | nullable | Pre-rendered HTML report |
| `error_message` | Text | nullable | Error details if failed |
| `files_scanned` | Integer | nullable | Files processed count |
| `issues_found` | Integer | nullable | Issues detected count |
| `created_at` | DateTime | not null | Record creation timestamp |

**GUID Property:** `.guid` returns `res_{crockford_base32}` format (e.g., `res_01hgw2bbg0000000000000001`)

**Current Tool Types:**

| Tool | Description | Target Entity |
|------|-------------|---------------|
| `photostats` | File statistics and orphan detection | Collection |
| `photo_pairing` | Filename pattern analysis | Collection |
| `pipeline_validation` | Pipeline structure validation | Pipeline (or Collection+Pipeline) |

#### Future Vision: Polymorphic Target Entity

As the domain model expands, AnalysisResult will support analysis on any entity type. This requires a **polymorphic foreign key pattern**:

**Proposed Schema Evolution:**

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `target_entity_type` | Enum | not null | Type of entity being analyzed |
| `target_entity_id` | Integer | not null | ID of the target entity |
| `tool` | String(50) | not null | Analysis tool name |
| `tool_version` | String(20) | nullable | Tool version for reproducibility |

**Target Entity Types:**

| Entity Type | Current | Future Tools |
|-------------|---------|--------------|
| `COLLECTION` | :white_check_mark: | photostats, photo_pairing, storage_analysis |
| `PIPELINE` | :white_check_mark: | pipeline_validation, complexity_analysis |
| `ALBUM` | :construction: | completeness_check, coverage_analysis, duplicate_detection |
| `IMAGE` | :construction: | ai_subject_detection, quality_assessment, metadata_extraction |
| `WORKFLOW` | :construction: | progress_analysis, bottleneck_detection, eta_estimation |
| `CAMERA` | :construction: | health_analysis, maintenance_prediction, usage_statistics |
| `EVENT` | :construction: | logistics_validation, scheduling_conflicts |
| `PERFORMER` | :construction: | appearance_frequency, coverage_across_events |

**Future Analysis Tools by Category:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ANALYSIS TOOL CATEGORIES                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  STORAGE ANALYSIS (Target: Collection)                                       │
│  ├── photostats          - File counts, sizes, orphan detection             │
│  ├── photo_pairing       - Filename pattern analysis, grouping              │
│  ├── storage_health      - Accessibility, latency, capacity trends          │
│  └── deduplication       - Cross-collection duplicate detection             │
│                                                                              │
│  PIPELINE ANALYSIS (Target: Pipeline)                                        │
│  ├── pipeline_validation - Structure validation, node connectivity          │
│  ├── complexity_metrics  - Path analysis, branching factor                  │
│  └── usage_statistics    - Which workflows use this pipeline                │
│                                                                              │
│  CONTENT ANALYSIS (Target: Album, Image)                                     │
│  ├── album_completeness  - Expected vs actual file coverage                 │
│  ├── ai_subject_detect   - ML-based performer identification                │
│  ├── quality_assessment  - Sharpness, exposure, composition scoring         │
│  ├── metadata_extract    - Batch EXIF/XMP extraction                        │
│  └── duplicate_finder    - Perceptual hash-based duplicate detection        │
│                                                                              │
│  WORKFLOW ANALYSIS (Target: Workflow)                                        │
│  ├── progress_report     - Per-node completion statistics                   │
│  ├── bottleneck_detect   - Identify slow processing stages                  │
│  ├── eta_estimation      - Predict completion time                          │
│  └── stalled_detection   - Find images stuck in processing                  │
│                                                                              │
│  EQUIPMENT ANALYSIS (Target: Camera)                                         │
│  ├── health_check        - Actuation tracking, maintenance alerts           │
│  ├── usage_patterns      - Shooting frequency, event correlation            │
│  └── lens_statistics     - Per-lens usage across cameras                    │
│                                                                              │
│  EVENT ANALYSIS (Target: Event)                                              │
│  ├── logistics_check     - Verify ticket/lodging/travel status              │
│  ├── schedule_conflicts  - Overlapping event detection                      │
│  └── coverage_analysis   - Performer appearance vs scheduled                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Polymorphic Query Pattern:**

```python
# Future: Query results for any entity
def get_results_for_entity(entity_type: str, entity_id: int):
    return db.query(AnalysisResult).filter(
        AnalysisResult.target_entity_type == entity_type,
        AnalysisResult.target_entity_id == entity_id
    ).order_by(AnalysisResult.created_at.desc())

# Usage examples:
get_results_for_entity("ALBUM", album_id)
get_results_for_entity("CAMERA", camera_id)
get_results_for_entity("WORKFLOW", workflow_id)
```

**Migration Strategy:**

The transition from current FK-based to polymorphic pattern:

1. **Phase 1 (Current):** Specific FKs (`collection_id`, `pipeline_id`)
2. **Phase 2:** Add `target_entity_type` + `target_entity_id`, backfill existing data
3. **Phase 3:** Deprecate specific FKs, use polymorphic pattern for new tools
4. **Phase 4:** Remove deprecated FKs after migration

**Relationships (Future):**
- Polymorphic many-to-one with target entity (Collection, Pipeline, Album, Image, Workflow, Camera, Event, Performer)
- Many-to-one with User (who triggered the analysis)
- Many-to-one with Team (tenant isolation)

---

### Configuration

**Purpose:** Persistent application settings as key-value pairs.

**Current Location:** `backend/src/models/configuration.py`

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `category` | String(50) | not null | Configuration category |
| `key` | String(255) | not null | Configuration key |
| `value_json` | JSONB | not null | Configuration value |
| `description` | Text | nullable | Human-readable description |
| `source` | Enum | not null, default=DATABASE | `DATABASE`, `YAML_IMPORT` |
| `created_at` | DateTime | not null | Creation timestamp |
| `updated_at` | DateTime | not null, auto-update | Last modification timestamp |

**Configuration Categories:**

| Category | Example Keys | Value Type |
|----------|--------------|------------|
| `extensions` | `photo_extensions`, `metadata_extensions`, `require_sidecar` | Array[String] |
| `cameras` | Camera ID (e.g., `AB3D`) | Object with `name`, `serial_number` |
| `processing_methods` | Method code (e.g., `HDR`) | String description |
| `event_statuses` | Status key (e.g., `future`, `confirmed`) | Object with `label`, `display_order` |

---

### Event (Implemented - Issue #39)

**Status:** Implemented
**Implementation:** `backend/src/models/event.py`

**Purpose:** Calendar-based photography event management with logistics tracking.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `external_id` | UUID | unique, not null | UUIDv7 for GUID generation |
| `title` | String(255) | not null | Event title |
| `description` | Text | nullable | Event description |
| `event_date` | Date | not null | Event date (timezone-independent) |
| `start_time` | Time | nullable | Start time (null for all-day) |
| `end_time` | Time | nullable | End time (null for all-day) |
| `is_all_day` | Boolean | not null, default=false | All-day event flag |
| `input_timezone` | String(50) | nullable | User's input timezone |
| `category_id` | Integer | FK(categories.id), not null | Event category |
| `location_id` | Integer | FK(locations.id), nullable | Event venue |
| `organizer_id` | Integer | FK(organizers.id), nullable | Event organizer |
| `series_id` | Integer | FK(event_series.id), nullable | Parent series |
| `status` | String(50) | not null, default='future' | Event status (configurable) |
| `attendance` | Enum | not null, default='planned' | `planned`, `attended`, `skipped` |
| `ticket_required` | Boolean | nullable | Ticket required |
| `ticket_status` | String(50) | nullable | `not_purchased`, `purchased`, `ready` |
| `ticket_purchase_date` | Date | nullable | Ticket purchase date |
| `timeoff_required` | Boolean | nullable | Time off required |
| `timeoff_status` | String(50) | nullable | `planned`, `booked`, `approved` |
| `timeoff_booking_date` | Date | nullable | Time off booking date |
| `travel_required` | Boolean | nullable | Travel required |
| `travel_status` | String(50) | nullable | `planned`, `booked` |
| `travel_booking_date` | Date | nullable | Travel booking date |
| `deadline_date` | Date | nullable | Workflow deadline |
| `created_at` | DateTime | not null | Creation timestamp |
| `updated_at` | DateTime | not null | Last modification |

**GUID Property:** `.guid` returns `evt_{crockford_base32}` format (e.g., `evt_01hgw2bbg0000000000000001`)

**Status Values (Configurable via Settings > Config):**

| Status | Description | Color Hint |
|--------|-------------|------------|
| `future` | Upcoming event | Blue |
| `confirmed` | Event confirmed | Green |
| `completed` | Event finished | Gray |
| `cancelled` | Event cancelled | Red |

**Attendance Values:**

| Value | Description | Calendar Color |
|-------|-------------|----------------|
| `planned` | Intend to attend | Default |
| `attended` | Actually attended | Success/Green |
| `skipped` | Decided not to attend | Muted/Gray |

**Logistics Tracking:**
Events support three logistics categories (ticket, timeoff, travel), each with:
- Required flag (nullable tri-state: null=unknown, true=required, false=not required)
- Status progression
- Booking/purchase date tracking

**Relationships:**
- Many-to-one with Category (required)
- Many-to-one with Location (optional, SET NULL on delete)
- Many-to-one with Organizer (optional, SET NULL on delete)
- Many-to-one with EventSeries (optional, CASCADE on delete)
- Many-to-many with Performer (via EventPerformer junction)

---

### EventSeries (Implemented - Issue #39)

**Status:** Implemented
**Implementation:** `backend/src/models/event_series.py`

**Purpose:** Groups related events created from multi-day calendar selections.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `external_id` | UUID | unique, not null | UUIDv7 for GUID generation |
| `title` | String(255) | not null | Series title |
| `created_at` | DateTime | not null | Creation timestamp |
| `updated_at` | DateTime | not null | Last modification |

**GUID Property:** `.guid` returns `ser_{crockford_base32}` format (e.g., `ser_01hgw2bbg0000000000000001`)

**Series Behavior:**
- Multi-day calendar selections auto-generate individual Event records linked to a Series
- Series updates can apply to: single event, this event and future, or all events
- Performer additions/removals sync across all series events
- Location and organizer changes can be synced across series
- Individual event status/attendance can differ within a series

**Relationships:**
- One-to-many with Event (CASCADE delete)

---

### Category (Implemented - Issue #39)

**Status:** Implemented
**Implementation:** `backend/src/models/category.py`

**Purpose:** Photography categories for classification of events, locations, organizers, and performers.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `external_id` | UUID | unique, not null | UUIDv7 for GUID generation |
| `name` | String(100) | unique, not null | Category name |
| `icon` | String(50) | nullable | Icon identifier |
| `color` | String(7) | nullable | Hex color code |
| `display_order` | Integer | not null, default=0 | Order in UI lists |
| `is_active` | Boolean | not null, default=true | Active status |
| `created_at` | DateTime | not null | Creation timestamp |
| `updated_at` | DateTime | not null | Last modification |

**GUID Property:** `.guid` returns `cat_{crockford_base32}` format (e.g., `cat_01hgw2bbg0000000000000001`)

**Category Matching:**
Events, Locations, Organizers, and Performers are category-scoped. When assigning entities to events, the system validates that the entity's category matches the event's category.

**Relationships:**
- One-to-many with Event (RESTRICT delete)
- One-to-many with Location (RESTRICT delete)
- One-to-many with Organizer (RESTRICT delete)
- One-to-many with Performer (RESTRICT delete)

---

### Location (Implemented - Issue #39)

**Status:** Implemented
**Implementation:** `backend/src/models/location.py`

**Purpose:** Event venues and shooting locations with rating system.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `external_id` | UUID | unique, not null | UUIDv7 for GUID generation |
| `name` | String(255) | not null | Location name |
| `category_id` | Integer | FK(categories.id), not null | Location category |
| `address` | Text | nullable | Street address |
| `city` | String(100) | nullable | City |
| `state` | String(100) | nullable | State/Province |
| `country` | String(100) | nullable | Country |
| `postal_code` | String(20) | nullable | Postal/ZIP code |
| `timezone` | String(50) | nullable | Location timezone (IANA format) |
| `latitude` | Decimal(10,7) | nullable | GPS latitude |
| `longitude` | Decimal(10,7) | nullable | GPS longitude |
| `is_known` | Boolean | not null, default=false | Known/visited location flag |
| `website` | String(1024) | nullable | Website URL |
| `additional_info` | Text | nullable | Additional notes |
| `default_ticket_required` | Boolean | nullable | Default logistics |
| `default_timeoff_required` | Boolean | nullable | Default logistics |
| `default_travel_required` | Boolean | nullable | Default logistics |
| `created_at` | DateTime | not null | Creation timestamp |
| `updated_at` | DateTime | not null | Last modification |

**GUID Property:** `.guid` returns `loc_{crockford_base32}` format (e.g., `loc_01hgw2bbg0000000000000001`)

**Known Locations:**
Locations can be marked as "known" after visiting, enabling rating and review features. Known locations can have photo ratings displayed as camera icons.

**Default Logistics:**
Locations can define default logistics requirements (ticket, timeoff, travel) that auto-populate when assigning the location to an event.

**Relationships:**
- Many-to-one with Category (required, RESTRICT delete)
- One-to-many with Event (SET NULL on delete)

---

### Organizer (Implemented - Issue #39)

**Status:** Implemented
**Implementation:** `backend/src/models/organizer.py`

**Purpose:** Event organizers for relationship management.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `external_id` | UUID | unique, not null | UUIDv7 for GUID generation |
| `name` | String(255) | not null | Organizer name |
| `category_id` | Integer | FK(categories.id), not null | Organizer category |
| `website` | String(1024) | nullable | Website URL |
| `additional_info` | Text | nullable | Additional notes |
| `default_ticket_required` | Boolean | nullable | Default logistics |
| `default_timeoff_required` | Boolean | nullable | Default logistics |
| `default_travel_required` | Boolean | nullable | Default logistics |
| `created_at` | DateTime | not null | Creation timestamp |
| `updated_at` | DateTime | not null | Last modification |

**GUID Property:** `.guid` returns `org_{crockford_base32}` format (e.g., `org_01hgw2bbg0000000000000001`)

**Default Logistics:**
Organizers can define default logistics requirements that auto-populate when assigning the organizer to an event.

**Relationships:**
- Many-to-one with Category (required, RESTRICT delete)
- One-to-many with Event (SET NULL on delete)

---

### Performer (Implemented - Issue #39)

**Status:** Implemented
**Implementation:** `backend/src/models/performer.py`

**Purpose:** Photo subjects (models, demo teams, wildlife species, etc.).

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `external_id` | UUID | unique, not null | UUIDv7 for GUID generation |
| `name` | String(255) | not null | Performer name |
| `category_id` | Integer | FK(categories.id), not null | Performer category |
| `website` | String(1024) | nullable | Website URL |
| `instagram_handle` | String(255) | nullable | Instagram handle (without @) |
| `additional_info` | Text | nullable | Additional notes |
| `created_at` | DateTime | not null | Creation timestamp |
| `updated_at` | DateTime | not null | Last modification |

**GUID Property:** `.guid` returns `prf_{crockford_base32}` format (e.g., `prf_01hgw2bbg0000000000000001`)

**Relationships:**
- Many-to-one with Category (required, RESTRICT delete)
- Many-to-many with Event (via EventPerformer junction)

---

### EventPerformer (Junction Table - Implemented)

**Status:** Implemented
**Implementation:** `backend/src/models/event_performer.py`

**Purpose:** Links Events to Performers with attendance status.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `event_id` | Integer | FK(events.id), not null | Parent event |
| `performer_id` | Integer | FK(performers.id), not null | The performer |
| `status` | Enum | not null, default='announced' | `announced`, `confirmed`, `cancelled` |
| `created_at` | DateTime | not null | Record creation |

**Performer Status Values:**

| Status | Description |
|--------|-------------|
| `announced` | Performer announced but not yet confirmed (default) |
| `confirmed` | Performer attendance confirmed |
| `cancelled` | Performer cancelled |

**Constraints:**
- `(event_id, performer_id)` is unique
- CASCADE delete when Event or Performer is deleted

**Series Sync Behavior:**
- Adding/removing performers syncs across all events in a series
- Performer status can be set independently per event

---

## Planned Entities

### User

**Priority:** High
**Target Epic:** 008 or 009

**Purpose:** Individual photographer identity and authentication.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `uuid` | UUID | unique, not null | External identifier |
| `team_id` | Integer | FK(teams.id), not null | Primary team membership |
| `email` | String(255) | unique, not null | Login email |
| `display_name` | String(255) | not null | Display name |
| `avatar_url` | String(1024) | nullable | Profile image URL |
| `is_active` | Boolean | not null, default=true | Account active |
| `preferences_json` | JSONB | nullable | User preferences |
| `created_at` | DateTime | not null | Creation timestamp |
| `updated_at` | DateTime | not null | Last modification |

---

### Team

**Priority:** High
**Target Epic:** 008 or 009

**Purpose:** Multi-tenancy boundary for data isolation.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `uuid` | UUID | unique, not null | External identifier |
| `name` | String(255) | unique, not null | Team name |
| `slug` | String(100) | unique, not null | URL-safe identifier |
| `is_personal` | Boolean | not null, default=false | Personal team (solo user) |
| `settings_json` | JSONB | nullable | Team-level settings |
| `created_at` | DateTime | not null | Creation timestamp |
| `updated_at` | DateTime | not null | Last modification |

**Design Notes:**
- Every user has a personal team created automatically at registration
- Personal teams are hidden from team-switching UI
- All entities are scoped to exactly one team

---

### Camera

**Priority:** Medium
**Target Epic:** 009 or later

**Purpose:** Physical camera equipment tracking and usage analytics.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `uuid` | UUID | unique, not null | External identifier |
| `team_id` | Integer | FK(teams.id), not null | Owning team |
| `camera_id` | String(4) | not null | 4-character camera ID from files |
| `serial_number` | String(100) | nullable | Manufacturer serial number |
| `make` | String(100) | nullable | Manufacturer (Canon, Sony, etc.) |
| `model` | String(100) | nullable | Model name (EOS R5, A7R IV, etc.) |
| `nickname` | String(100) | nullable | User-assigned name |
| `purchase_date` | Date | nullable | When acquired |
| `total_actuations` | Integer | nullable | Estimated shutter count |
| `maintenance_threshold` | Integer | nullable | Actuations before service |
| `notes` | Text | nullable | Equipment notes |
| `metadata_json` | JSONB | nullable | Custom metadata |
| `created_at` | DateTime | not null | Creation timestamp |
| `updated_at` | DateTime | not null | Last modification |

**Usage Tracking:**
- Actuation counts estimated from image counters and gaps
- Maintenance alerts when approaching threshold
- Historical usage correlated with events

**Disambiguation:**
- Same `camera_id` may appear in multiple events with different physical cameras
- Combination of `camera_id` + Event + Photographer identifies physical camera
- Serial number (from EXIF when available) provides definitive identification

---

### Album

**Priority:** Medium
**Target Epic:** 009 or later

**Purpose:** Logical grouping of Images from an Event or session, serving as the container for workflow processing.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `uuid` | UUID | unique, not null | External identifier |
| `team_id` | Integer | FK(teams.id), not null | Owning team |
| `event_id` | Integer | FK(events.id), nullable | Source event |
| `name` | String(255) | not null | Album name |
| `description` | Text | nullable | Album description |
| `cover_image_id` | Integer | FK(images.id), nullable | Cover thumbnail |
| `image_count` | Integer | nullable | Cached image count |
| `created_at` | DateTime | not null | Creation timestamp |
| `updated_at` | DateTime | not null | Last modification |

**Relationships:**
- Many-to-one with Event (optional - historical albums may not have events)
- One-to-many with Image (Images belong to one Album)
- One-to-many with Workflow (can have multiple workflow executions over time)

**Workflow Integration:**
When a photographer creates an Album:
1. Selects a Pipeline to define expected processing path
2. System creates a Workflow to track execution
3. As Files are added to Collections, they are linked to Images in the Album
4. Progress is tracked per-Image through the Pipeline nodes

---

### Image

**Priority:** Medium
**Target Epic:** 009 or later

**Purpose:** Logical representation of a photograph, independent of its physical file artifacts.

An Image is the **conceptual entity** representing a single photograph. It may be persisted as multiple Files across multiple Collections as it moves through processing stages. The Image is identified by its origin (camera + counter + timestamp) and tracks its journey through the workflow.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `uuid` | UUID | unique, not null | External identifier |
| `team_id` | Integer | FK(teams.id), not null | Owning team |
| `album_id` | Integer | FK(albums.id), not null | Parent album |
| `camera_id` | String(4) | not null | Source camera ID (from filename) |
| `counter` | String(4) | not null | Image counter (from filename) |
| `capture_timestamp` | DateTime | nullable | When photo was taken (from EXIF) |
| `original_filename` | String(255) | not null | Original capture filename |
| `exif_json` | JSONB | nullable | Extracted EXIF metadata (shared across Files) |
| `rating` | Integer | nullable | User rating (1-5 stars) |
| `label_color` | String(20) | nullable | Color label (red, yellow, green, etc.) |
| `is_pick` | Boolean | nullable | Flagged as picked/selected |
| `is_rejected` | Boolean | not null, default=false | Marked as rejected |
| `notes` | Text | nullable | User notes about this image |
| `metadata_json` | JSONB | nullable | Additional user metadata |
| `created_at` | DateTime | not null | Record creation |
| `updated_at` | DateTime | not null | Last modification |

**Unique Image Identification:**
- Natural key: `album_id` + `camera_id` + `counter`
- `capture_timestamp` provides additional disambiguation when counters reset
- The same physical photo (same camera_id + counter + timestamp) appearing in different Albums creates separate Image records

**Relationships:**
- Many-to-one with Album (required)
- One-to-many with File (Image has multiple file artifacts)
- Many-to-many with Performer (via ImagePerformer junction)
- One-to-many with ImageWorkflowProgress (tracks position in each Workflow)

**Key Distinction: Image vs File**
```
┌─────────────────────────────────────────────────────────────────┐
│                         IMAGE (Logical)                         │
│  "The photograph I took of the Blue Angels at 2:35 PM"          │
│  Identified by: AB3D0001, captured 2026-01-07T14:35:22          │
├─────────────────────────────────────────────────────────────────┤
│                        FILES (Physical)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ AB3D0001.CR3 │  │ AB3D0001.XMP │  │AB3D0001-s.DNG│          │
│  │ (RAW capture)│  │ (sidecar)    │  │ (denoised)   │          │
│  │ Collection A │  │ Collection A │  │ Collection B │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │AB3D0001-s.TIF│  │AB3D0001-w.JPG│                             │
│  │ (exported)   │  │ (web export) │                             │
│  │ Collection C │  │ Collection D │                             │
│  └──────────────┘  └──────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

---

### File

**Priority:** Medium
**Target Epic:** 009 or later

**Purpose:** Physical artifact persisting an Image in a specific format at a specific storage location.

A File represents a single physical file on storage. Multiple Files may represent the same Image (different formats, processing stages, or copies). Files are the actual artifacts that exist in Collections.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `uuid` | UUID | unique, not null | External identifier |
| `team_id` | Integer | FK(teams.id), not null | Owning team |
| `image_id` | Integer | FK(images.id), not null | Parent Image |
| `collection_id` | Integer | FK(collections.id), not null | Storage location |
| `filename` | String(255) | not null | Filename (without path) |
| `relative_path` | String(1024) | not null | Path within Collection |
| `extension` | String(20) | not null | File extension (lowercase, with dot) |
| `file_size` | BigInteger | nullable | Size in bytes |
| `file_hash` | String(64) | nullable | SHA-256 hash for integrity |
| `format_type` | Enum | not null | `RAW`, `SIDECAR`, `PROCESSED`, `EXPORT` |
| `pipeline_node_id` | String(100) | nullable | Pipeline node that produced this file |
| `is_primary` | Boolean | not null, default=false | Primary representation of Image |
| `sidecar_for_id` | Integer | FK(files.id), nullable | Parent file (for XMP sidecars) |
| `discovered_at` | DateTime | not null | When file was discovered/imported |
| `file_modified_at` | DateTime | nullable | File system modification time |
| `metadata_json` | JSONB | nullable | File-specific metadata |
| `created_at` | DateTime | not null | Record creation |
| `updated_at` | DateTime | not null | Last modification |

**Format Types:**

| Type | Description | Examples |
|------|-------------|----------|
| `RAW` | Original camera capture | .CR3, .NEF, .ARW, .DNG (camera) |
| `SIDECAR` | Metadata file accompanying another file | .XMP |
| `PROCESSED` | Intermediate processing output | .DNG (denoised), .PSD |
| `EXPORT` | Final export artifact | .TIFF, .JPG, .PNG |

**Constraints:**
- `(collection_id, relative_path)` is unique (one file per path per collection)
- CASCADE delete when Image is deleted
- RESTRICT delete on Collection if Files exist

**Relationships:**
- Many-to-one with Image (required)
- Many-to-one with Collection (required)
- Self-referential: Sidecar files reference their parent file

**Sidecar Relationship:**
XMP sidecars and similar metadata files link to their parent:
```
┌─────────────────┐         ┌─────────────────┐
│  AB3D0001.CR3   │◄────────│  AB3D0001.XMP   │
│  format: RAW    │         │  format: SIDECAR│
│  is_primary: T  │         │  sidecar_for_id │
└─────────────────┘         └─────────────────┘
```

---

### Workflow

**Priority:** Medium
**Target Epic:** 009 or later

**Purpose:** Tracks the execution of a Pipeline against an Album, monitoring progress of each Image through processing stages.

A Workflow is the **runtime instance** of applying a Pipeline to an Album. It tracks which Images have reached which Pipeline nodes, which Collections are being used, and overall completion status.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `uuid` | UUID | unique, not null | External identifier |
| `team_id` | Integer | FK(teams.id), not null | Owning team |
| `album_id` | Integer | FK(albums.id), not null | Target album |
| `pipeline_id` | Integer | FK(pipelines.id), not null | Blueprint pipeline |
| `pipeline_version` | Integer | not null | Pinned pipeline version |
| `name` | String(255) | nullable | Optional workflow name |
| `status` | Enum | not null | Workflow status |
| `started_at` | DateTime | nullable | When processing began |
| `completed_at` | DateTime | nullable | When processing finished |
| `deadline` | DateTime | nullable | Target completion date |
| `progress_json` | JSONB | nullable | Cached aggregate progress |
| `settings_json` | JSONB | nullable | Workflow-specific settings |
| `notes` | Text | nullable | Workflow notes |
| `created_at` | DateTime | not null | Record creation |
| `updated_at` | DateTime | not null | Last modification |

**Status Values:**

| Status | Description |
|--------|-------------|
| `CREATED` | Workflow created, not started |
| `IN_PROGRESS` | Actively processing images |
| `PAUSED` | Processing paused by user |
| `COMPLETED` | All images reached termination |
| `CANCELLED` | Workflow cancelled |

**Progress JSON Structure:**
```json
{
  "total_images": 500,
  "by_node": {
    "capture": {"count": 500, "percentage": 100.0},
    "raw_file": {"count": 500, "percentage": 100.0},
    "selection": {"count": 450, "percentage": 90.0},
    "denoise": {"count": 400, "percentage": 80.0},
    "export_tiff": {"count": 350, "percentage": 70.0},
    "termination_archive": {"count": 300, "percentage": 60.0}
  },
  "by_path": {
    "archive_ready": {"count": 300, "percentage": 60.0},
    "rejected": {"count": 50, "percentage": 10.0},
    "in_progress": {"count": 150, "percentage": 30.0}
  },
  "last_updated": "2026-01-07T15:30:00Z"
}
```

**Relationships:**
- Many-to-one with Album (required)
- Many-to-one with Pipeline (required, pinned version)
- One-to-many with WorkflowCollection (storage locations used)
- One-to-many with ImageWorkflowProgress (per-image tracking)

**User Story Example:**

```
1. Photographer creates Album for "Blue Angels Airshow Day 1"
2. Selects "Standard RAW Workflow" Pipeline → Workflow created
3. Imports camera cards:
   - Memory card 1 → Collection "BA-Day1-Card1" (attached to Workflow)
   - Memory card 2 → Collection "BA-Day1-Card2" (attached to Workflow)
4. System discovers Files → creates Images in Album
5. Processing begins:
   - Selection: Picks moved to Collection "BA-Day1-Selects"
   - Denoise: DNG files added to "BA-Day1-Selects"
   - Export: TIFFs to Collection "BA-Day1-Exports"
6. Progress tracked: 60% at archive_ready termination
```

---

### WorkflowCollection (Junction Table)

**Priority:** Medium
**Target Epic:** 009 or later

**Purpose:** Links Workflows to the Collections used during processing.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `workflow_id` | Integer | FK(workflows.id), not null | Parent workflow |
| `collection_id` | Integer | FK(collections.id), not null | Attached collection |
| `role` | Enum | not null | Collection's role in workflow |
| `pipeline_node_id` | String(100) | nullable | Associated pipeline node |
| `attached_at` | DateTime | not null | When collection was attached |
| `created_at` | DateTime | not null | Record creation |

**Role Values:**

| Role | Description |
|------|-------------|
| `SOURCE` | Initial capture files (input) |
| `WORKING` | Intermediate processing storage |
| `OUTPUT` | Final export destination |
| `ARCHIVE` | Long-term archive location |

**Constraints:**
- `(workflow_id, collection_id)` may appear multiple times with different roles
- CASCADE delete when Workflow is deleted

---

### ImageWorkflowProgress

**Priority:** Medium
**Target Epic:** 009 or later

**Purpose:** Tracks each Image's progress through a specific Workflow's Pipeline.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `image_id` | Integer | FK(images.id), not null | The image |
| `workflow_id` | Integer | FK(workflows.id), not null | The workflow |
| `current_node_id` | String(100) | not null | Furthest reached node |
| `path_taken` | JSONB | not null | Ordered list of nodes traversed |
| `status` | Enum | not null | Image's workflow status |
| `entered_at` | DateTime | not null | When image entered current node |
| `files_json` | JSONB | nullable | Files produced at each node |
| `created_at` | DateTime | not null | Record creation |
| `updated_at` | DateTime | not null | Last modification |

**Status Values:**

| Status | Description |
|--------|-------------|
| `PENDING` | Not yet started processing |
| `IN_PROGRESS` | Currently being processed |
| `COMPLETED` | Reached termination node |
| `REJECTED` | Rejected during selection |
| `ERROR` | Processing error occurred |

**Path Taken Structure:**
```json
["capture", "raw_file", "xmp_sidecar", "selection", "denoise", "export_tiff"]
```

**Files JSON Structure:**
```json
{
  "capture": {"file_id": 1001, "collection_id": 5},
  "raw_file": {"file_id": 1001, "collection_id": 5},
  "xmp_sidecar": {"file_id": 1002, "collection_id": 5},
  "selection": {"file_id": 1003, "collection_id": 6},
  "denoise": {"file_id": 1004, "collection_id": 6},
  "export_tiff": {"file_id": 1005, "collection_id": 7}
}
```

**Constraints:**
- `(image_id, workflow_id)` is unique
- CASCADE delete when Image or Workflow is deleted

---

### ImagePerformer (Junction Table)

**Priority:** Medium
**Target Epic:** 009 or later

**Purpose:** Links Images to Performers they contain, supporting both manual tagging and AI identification.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `image_id` | Integer | FK(images.id), not null | The image |
| `performer_id` | Integer | FK(performers.id), not null | The performer in the image |
| `identification_method` | Enum | not null | `MANUAL`, `AI_DETECTED`, `AI_CONFIRMED` |
| `confidence_score` | Float | nullable | AI confidence (0.0-1.0), null for manual |
| `bounding_box_json` | JSONB | nullable | Face/subject location in image |
| `identified_by` | Integer | FK(users.id), nullable | User who tagged (manual) |
| `identified_at` | DateTime | not null | When identification was made |
| `verified` | Boolean | not null, default=false | Human-verified AI detection |
| `verified_by` | Integer | FK(users.id), nullable | User who verified |
| `verified_at` | DateTime | nullable | When verification occurred |
| `created_at` | DateTime | not null | Record creation timestamp |

**Constraints:**
- `(image_id, performer_id)` is unique (one entry per performer per image)
- CASCADE delete when Image or Performer is deleted

**Identification Methods:**

| Method | Description | Confidence | Verified |
|--------|-------------|------------|----------|
| `MANUAL` | User-tagged | null | true (implicit) |
| `AI_DETECTED` | ML model identified | 0.0-1.0 | false |
| `AI_CONFIRMED` | AI detection verified by user | 0.0-1.0 | true |

**Bounding Box Format:**
```json
{
  "x": 0.25,      // Relative position (0-1) from left
  "y": 0.15,      // Relative position (0-1) from top
  "width": 0.20,  // Relative width (0-1)
  "height": 0.30, // Relative height (0-1)
  "type": "face"  // "face", "full_body", "partial"
}
```

**Use Cases:**
- Manual workflow: User browses images, tags performers for identification
- AI workflow: ML model processes images, suggests performers with confidence scores
- Verification workflow: User reviews AI detections, confirms or rejects
- Search: "Find all images containing [Performer]" across entire collection
- Analytics: Track which performers are photographed most frequently

---

### Agent

**Priority:** Future
**Target Epic:** 010+

**Purpose:** Local workers for accessing physical storage and offloading computation.

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal identifier |
| `uuid` | UUID | unique, not null | External identifier |
| `team_id` | Integer | FK(teams.id), not null | Owning team |
| `name` | String(255) | not null | Agent name |
| `hostname` | String(255) | nullable | Machine hostname |
| `status` | Enum | not null | `ONLINE`, `OFFLINE`, `ERROR` |
| `last_heartbeat` | DateTime | nullable | Last check-in |
| `capabilities_json` | JSONB | nullable | Supported operations |
| `api_key_hash` | String(255) | not null | Authentication key hash |
| `created_at` | DateTime | not null | Creation timestamp |
| `updated_at` | DateTime | not null | Last modification |

**Use Cases:**
- Access local filesystem Collections without cloud upload
- Access SMB shares from local network
- Offload expensive async jobs (image analysis, EXIF extraction)
- Enable hybrid cloud/local architecture

---

## Entity Relationships

### Current State (Implemented)

```
                                    ┌─────────────────┐
                                    │  Configuration  │
                                    │  (standalone)   │
                                    └─────────────────┘

┌─────────────────┐     1:*        ┌─────────────────┐
│    Connector    │◄───────────────│   Collection    │
│  (credentials)  │                │   (storage)     │
└─────────────────┘                └────────┬────────┘
                                            │
                                     CASCADE│ 1:*
                                            ▼
┌─────────────────┐     1:*        ┌─────────────────┐
│    Pipeline     │◄───────────────│ AnalysisResult  │
│   (workflow)    │    SET NULL    │   (results)     │
└────────┬────────┘                └─────────────────┘
         │
  CASCADE│ 1:*
         ▼
┌─────────────────┐
│ PipelineHistory │
│   (versions)    │
└─────────────────┘
```

### Future State (Full Domain)

The complete domain model centers around three key subsystems:
1. **Events & Planning** - Calendar, scheduling, logistics
2. **Content & Storage** - Albums, Images, Files, Collections
3. **Processing & Workflow** - Pipelines, Workflows, progress tracking

```
                              ┌─────────────┐
                              │    Team     │ (Multi-tenancy root)
                              └──────┬──────┘
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
        ▼                            ▼                            ▼
┌──────────────┐            ┌──────────────┐            ┌──────────────┐
│     User     │◄──────────►│    Event     │            │   Pipeline   │
└──────────────┘  attendees └──────┬───────┘            └──────┬───────┘
                                   │                           │
                    ┌──────────────┼──────────────┐            │
                    │              │              │            │
                    ▼              ▼              ▼            │
            ┌──────────┐  ┌──────────┐  ┌──────────┐          │
            │ Location │  │ Category │  │Organizer │          │
            └──────────┘  └──────────┘  └──────────┘          │
                                   │                           │
┌──────────────┐    *:*           │                           │
│  Performer   │◄─────────────────┤                           │
└──────┬───────┘   (scheduled)    │                           │
       │                          ▼                           │
       │ *:*              ┌──────────────┐                    │
       │ (in images)      │    Album     │◄───────────────────┤
       │                  └──────┬───────┘                    │
       │                         │                            │
       │                         │ 1:*                        │
       │                         ▼                            ▼
       │                  ┌──────────────┐            ┌──────────────┐
       └─────────────────►│    Image     │◄───────────│   Workflow   │
         ImagePerformer   └──────┬───────┘            └──────┬───────┘
                                 │                           │
                                 │ 1:*                       │ *:*
                                 ▼                           │WorkflowCollection
                          ┌──────────────┐                   │
                          │    File      │                   │
                          └──────┬───────┘                   │
                                 │                           │
                                 │ *:1                       │
                                 ▼                           ▼
┌──────────────┐    1:*   ┌──────────────┐            (attached to)
│  Connector   │─────────►│  Collection  │◄───────────────────┘
└──────────────┘          └──────────────┘
```

**Core Processing Model: Pipeline → Workflow → Album → Image → File → Collection**

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           PROCESSING HIERARCHY                              │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PIPELINE (Blueprint)           WORKFLOW (Execution)                        │
│  ┌─────────────────┐           ┌─────────────────────────────────────────┐ │
│  │ "Standard RAW"  │           │ Workflow for "Airshow Day 1" Album      │ │
│  │                 │──────────►│                                         │ │
│  │ Nodes:          │  applies  │ Status: IN_PROGRESS                     │ │
│  │ - capture       │  to       │ Progress: 60% at termination            │ │
│  │ - raw_file      │           │                                         │ │
│  │ - selection     │           │ Attached Collections:                   │ │
│  │ - denoise       │           │ - Card1-Import (SOURCE)                 │ │
│  │ - export_tiff   │           │ - Selects (WORKING)                     │ │
│  │ - termination   │           │ - Exports (OUTPUT)                      │ │
│  └─────────────────┘           └─────────────────────────────────────────┘ │
│                                              │                              │
│                                              │ tracks progress of           │
│                                              ▼                              │
│  ALBUM                         ┌─────────────────────────────────────────┐ │
│  ┌─────────────────┐          │ ImageWorkflowProgress (per Image)        │ │
│  │"Airshow Day 1"  │          │                                          │ │
│  │                 │          │ Image AB3D0001:                          │ │
│  │ Contains:       │          │   current_node: export_tiff              │ │
│  │ - 500 Images    │          │   path: [capture→raw→select→denoise→exp]│ │
│  │                 │          │   status: IN_PROGRESS                    │ │
│  └────────┬────────┘          │                                          │ │
│           │                   │ Image AB3D0002:                          │ │
│           │ 1:*               │   current_node: termination              │ │
│           ▼                   │   status: COMPLETED                      │ │
│  ┌─────────────────┐          └─────────────────────────────────────────┘ │
│  │     IMAGE       │                                                       │
│  │   (Logical)     │                                                       │
│  │                 │                                                       │
│  │ AB3D0001        │──────┐                                                │
│  │ camera+counter  │      │ 1:* (one Image, many Files)                   │
│  └─────────────────┘      │                                                │
│                           ▼                                                │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐              │
│  │ FILE (Physical) │ │ FILE (Physical) │ │ FILE (Physical) │              │
│  │                 │ │                 │ │                 │              │
│  │ AB3D0001.CR3    │ │ AB3D0001.DNG    │ │ AB3D0001.TIF    │              │
│  │ format: RAW     │ │ format:PROCESSED│ │ format: EXPORT  │              │
│  │ node: capture   │ │ node: denoise   │ │ node: export    │              │
│  │                 │ │                 │ │                 │              │
│  │ Collection:     │ │ Collection:     │ │ Collection:     │              │
│  │ "Card1-Import"  │ │ "Selects"       │ │ "Exports"       │              │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘              │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

**Key Relationship: Performer ↔ Image**

```
┌──────────────┐                              ┌──────────────┐
│  Performer   │                              │    Image     │
│              │         *:*                  │              │
│  - name      │◄────────────────────────────►│  - camera_id │
│  - type      │      ImagePerformer          │  - album_id  │
│  - ref_imgs  │      (junction table)        │  - counter   │
└──────────────┘                              └──────────────┘
                           │
                           ▼
              ┌─────────────────────────┐
              │     ImagePerformer      │
              │                         │
              │  - identification_method│
              │  - confidence_score     │
              │  - bounding_box_json    │
              │  - verified             │
              └─────────────────────────┘
```

**Legend:**
- `──────►` One-to-many (arrow points to "many" side)
- `◄──────►` Many-to-many
- `(text)` Relationship context/junction table

---

## Data Architecture Principles

### 1. Tenant Isolation

Every user-created entity belongs to exactly one Team. Database queries MUST include team filtering:

```python
# Correct: Always filter by team
collections = db.query(Collection).filter(Collection.team_id == current_user.team_id)

# Incorrect: Missing team filter (security vulnerability)
collections = db.query(Collection).all()
```

### 2. Soft Delete vs. Hard Delete

| Entity Type | Delete Strategy | Rationale |
|-------------|-----------------|-----------|
| Configuration | Hard delete | No historical value |
| Collection | Hard delete + CASCADE results | Storage management |
| Connector | RESTRICT if collections exist | Prevent orphans |
| Pipeline | Soft delete (is_active=false) | Preserve historical results |
| Event | Soft delete | Historical record |
| User | Soft delete (is_active=false) | Audit trail |

### 3. Timestamp Management

All entities include:
- `created_at`: Set once at creation (server-side default)
- `updated_at`: Auto-updated on modification (database trigger)

### 4. JSONB Usage Guidelines

Use JSONB for:
- User-defined metadata (`metadata_json`)
- Flexible structures that evolve (`settings_json`, `preferences_json`)
- Extracted data (`exif_json`, `xmp_json`)

Avoid JSONB for:
- Core business attributes (use proper columns)
- Frequently queried fields (use indexed columns)
- Relationship data (use proper foreign keys)

### 5. External Integration Points

| Integration | Entity | Purpose |
|-------------|--------|---------|
| TripIt | Trip (future) | Travel planning for non-local events |
| S3/GCS/SMB | Connector | Remote storage access |
| ML/AI Services | Image | Subject identification, quality assessment |

---

## Appendices

### A. Migration Roadmap

| Phase | Entities | Dependencies | Description |
|-------|----------|--------------|-------------|
| Current | Collection, Connector, Pipeline, PipelineHistory, AnalysisResult, Configuration | - | Storage, tools, and analysis |
| Phase 1 | Team, User | Auth system | Multi-tenancy foundation |
| Phase 2 | Event, Category, Location, Organizer | Team, User | Calendar and planning |
| Phase 3 | Album, Image, File | Team, Collection | Content management core |
| Phase 4 | Workflow, WorkflowCollection, ImageWorkflowProgress | Album, Pipeline | Processing orchestration |
| Phase 5 | Performer, ImagePerformer | Team, Image | Subject tracking |
| Phase 6 | Camera | Team | Equipment tracking |
| Phase 7 | Agent | Team, Infrastructure | Distributed processing |

**Critical Path:**
1. Team/User must precede all user-facing entities
2. Album/Image/File must precede Workflow (content before processing)
3. Workflow enables tracking; can be added after Albums are in use

### B. API Endpoint Conventions

All entities follow RESTful conventions:

```
GET    /api/{entity}s          - List (with pagination, filtering)
POST   /api/{entity}s          - Create
GET    /api/{entity}s/{id}     - Read
PUT    /api/{entity}s/{id}     - Update
DELETE /api/{entity}s/{id}     - Delete
GET    /api/{entity}s/stats    - KPI statistics for TopHeader
```

### C. Related Issues

| Issue | Title | Relevance |
|-------|-------|-----------|
| #39 | Add Events repo with React Calendar | Event entity detailed requirements |
| #42 | Add UUID to every relevant object | UUID standard (UUIDv7 + Crockford Base32) |
| #24 | Remote Photo collections persistence | Collection and AnalysisResult foundation |
| #40 | Import S3 Collections from inventory | Collection bulk import |
| #52 | Auto-trigger Collection refresh | Collection state management |

### D. Glossary

| Term | Definition |
|------|------------|
| **Actuation** | Single shutter activation (camera usage metric) |
| **Album** | Logical grouping of Images from an Event or session |
| **Collection** | Physical storage location containing Files |
| **Connector** | Authentication credentials for remote storage |
| **File** | Physical artifact persisting an Image in a specific format |
| **GUID** | Global Unique Identifier: `{prefix}_{crockford_base32}` format used in APIs, URLs, and UI |
| **Image** | Logical representation of a photograph (may have multiple Files) |
| **Image Group** | Set of Files representing the same Image across Collections |
| **Pipeline** | Directed graph defining expected photo processing workflow (blueprint) |
| **Sidecar** | Metadata file (.xmp) accompanying another file |
| **Tenant** | Isolated data boundary (Team) |
| **Termination** | Pipeline end state (classification of image processing outcome) |
| **Workflow** | Runtime execution of a Pipeline against an Album (tracks progress) |

---

*This document is maintained as a living reference. Updates should be made when:*
- *New entities are implemented*
- *Entity attributes change significantly*
- *New issues affect domain design*
