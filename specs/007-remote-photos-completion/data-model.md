# Data Model: Remote Photo Collections Completion

**Feature**: 007-remote-photos-completion
**Date**: 2026-01-03
**Status**: Complete

## Overview

This document defines the data models for Phases 4-8 of the Remote Photo Collections feature. Models extend the existing database schema from Phases 1-3.

---

## Existing Models (Reference)

### Collection (Enhanced)

Already exists from Phase 3; Phase 4 adds statistics fields.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PK, auto-increment | Unique identifier |
| connector_id | Integer | FK(connectors.id), nullable | Reference to remote connector |
| name | String(255) | unique, not null | Display name |
| type | Enum | not null | LOCAL, S3, GCS, SMB |
| location | String(1024) | not null | Path or bucket location |
| state | Enum | not null, default=LIVE | LIVE, CLOSED, ARCHIVED |
| cache_ttl | Integer | nullable | Override default cache TTL (seconds) |
| is_accessible | Boolean | not null, default=true | Connection status |
| last_error | Text | nullable | Most recent error message |
| metadata_json | JSONB | nullable | Additional metadata |
| storage_used | BigInteger | nullable | Total bytes (from PhotoStats) |
| file_count | Integer | nullable | Total file count (from PhotoStats) |
| image_group_count | Integer | nullable | Grouped images (from Photo Pairing/Pipeline) |
| image_count | Integer | nullable | Total images (from Photo Pairing/Pipeline) |
| last_stats_update | DateTime | nullable | When stats were last updated |
| created_at | DateTime | not null, default=now | Creation timestamp |
| updated_at | DateTime | not null, auto-update | Last modification timestamp |

**Indexes**:
- `idx_collections_name` on name
- `idx_collections_stats` on (storage_used, file_count, image_count) WHERE storage_used IS NOT NULL

---

## New Models

### AnalysisResult (Phase 4)

Stores execution history and results for all analysis tools.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PK, auto-increment | Unique identifier |
| collection_id | Integer | FK(collections.id), not null | Target collection |
| tool | String(50) | not null | Tool name: 'photostats', 'photo_pairing', 'pipeline_validation' |
| pipeline_id | Integer | FK(pipelines.id), nullable | For pipeline_validation tool |
| status | Enum | not null | COMPLETED, FAILED, CANCELLED |
| started_at | DateTime | not null | Execution start timestamp |
| completed_at | DateTime | not null | Execution end timestamp |
| duration_seconds | Float | not null | Execution duration |
| results_json | JSONB | not null | Structured results data |
| report_html | Text | nullable | Pre-rendered HTML report |
| error_message | Text | nullable | Error details if failed |
| files_scanned | Integer | nullable | Number of files processed |
| issues_found | Integer | nullable | Number of issues detected |
| created_at | DateTime | not null, default=now | Record creation timestamp |

**Relationships**:
- Many-to-one with Collection (CASCADE on delete)
- Many-to-one with Pipeline (SET NULL on delete)

**Indexes**:
- `idx_results_collection` on collection_id
- `idx_results_tool` on tool
- `idx_results_created` on created_at DESC
- `idx_results_collection_tool_date` on (collection_id, tool, created_at DESC)

**Status Enum Values**:
- `COMPLETED`: Tool finished successfully
- `FAILED`: Tool execution failed
- `CANCELLED`: User cancelled execution

---

### Pipeline (Phase 5)

Stores photo processing workflow definitions.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PK, auto-increment | Unique identifier |
| name | String(255) | unique, not null | Display name |
| description | Text | nullable | Purpose/usage description |
| nodes_json | JSONB | not null | Node definitions array |
| edges_json | JSONB | not null | Edge connections array |
| version | Integer | not null, default=1 | Current version number |
| is_active | Boolean | not null, default=false | Active for validation |
| is_valid | Boolean | not null, default=false | Structure validation passed |
| validation_errors | JSONB | nullable | Validation error messages |
| created_at | DateTime | not null, default=now | Creation timestamp |
| updated_at | DateTime | not null, auto-update | Last modification timestamp |

**Constraints**:
- Only one pipeline can have is_active=true (enforced at application level)

**Indexes**:
- `idx_pipelines_name` on name
- `idx_pipelines_active` on is_active WHERE is_active = true

**Node Structure (nodes_json)**:
```json
[
  {
    "id": "capture_1",
    "type": "capture",
    "properties": {
      "camera_id_pattern": "[A-Z0-9]{4}",
      "counter_pattern": "[0-9]{4}"
    }
  },
  {
    "id": "file_raw",
    "type": "file",
    "properties": {
      "extension": ".dng",
      "optional": false
    }
  },
  {
    "id": "process_hdr",
    "type": "process",
    "properties": {
      "suffix": "-HDR"
    }
  },
  {
    "id": "pairing_1",
    "type": "pairing",
    "properties": {
      "inputs": ["file_raw", "file_xmp"]
    }
  },
  {
    "id": "branch_1",
    "type": "branching",
    "properties": {
      "condition": "has_suffix",
      "value": "-HDR"
    }
  },
  {
    "id": "term_archive",
    "type": "termination",
    "properties": {
      "name": "Archive Ready",
      "classification": "CONSISTENT"
    }
  }
]
```

**Edge Structure (edges_json)**:
```json
[
  {"from": "capture_1", "to": "file_raw"},
  {"from": "file_raw", "to": "process_hdr"},
  {"from": "process_hdr", "to": "term_archive"}
]
```

---

### PipelineHistory (Phase 5)

Tracks version history for pipeline changes.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PK, auto-increment | Unique identifier |
| pipeline_id | Integer | FK(pipelines.id), not null | Parent pipeline |
| version | Integer | not null | Version number |
| nodes_json | JSONB | not null | Node snapshot at this version |
| edges_json | JSONB | not null | Edge snapshot at this version |
| change_summary | String(500) | nullable | Description of changes |
| changed_by | String(100) | nullable | Who made the change (for future multi-user) |
| created_at | DateTime | not null, default=now | Version creation timestamp |

**Relationships**:
- Many-to-one with Pipeline (CASCADE on delete)

**Indexes**:
- `idx_history_pipeline` on pipeline_id
- `idx_history_version` on (pipeline_id, version DESC)

---

### Configuration (Phase 7)

Stores application configuration as key-value pairs.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PK, auto-increment | Unique identifier |
| category | String(100) | not null | Category: 'extensions', 'cameras', 'processing_methods' |
| key | String(255) | not null | Configuration key |
| value_json | JSONB | not null | Configuration value |
| description | Text | nullable | Human-readable description |
| source | String(20) | not null, default='database' | 'database' or 'yaml_import' |
| created_at | DateTime | not null, default=now | Creation timestamp |
| updated_at | DateTime | not null, auto-update | Last modification timestamp |

**Constraints**:
- Unique constraint on (category, key)

**Indexes**:
- `idx_config_category` on category
- `idx_config_category_key` on (category, key)

**Configuration Categories**:

| Category | Key Pattern | Value Type | Example |
|----------|-------------|------------|---------|
| extensions | photo_extensions | Array[String] | [".dng", ".cr3", ".tiff"] |
| extensions | metadata_extensions | Array[String] | [".xmp"] |
| extensions | require_sidecar | Array[String] | [".cr3"] |
| cameras | {camera_id} | Object | {"name": "Canon EOS R5", "serial_number": "12345"} |
| processing_methods | {method_code} | String | "High Dynamic Range" |

---

## Entity Relationship Diagram

```
┌─────────────────┐
│   Connector     │
│ (existing)      │
└────────┬────────┘
         │ 1
         │
         │ *
┌────────▼────────┐       ┌─────────────────┐
│   Collection    │──────*│ AnalysisResult  │
│ (enhanced)      │       └────────┬────────┘
└─────────────────┘                │ *
                                   │
                                   │ 0..1
┌─────────────────┐       ┌────────▼────────┐
│ PipelineHistory │*──────│    Pipeline     │
└─────────────────┘       └─────────────────┘
                                   │ 1
                                   │
                                   │ 0..1 (active)
                          ┌────────▼────────┐
                          │ (used by tools) │
                          └─────────────────┘

┌─────────────────┐
│  Configuration  │
│  (standalone)   │
└─────────────────┘
```

---

## Validation Rules

### AnalysisResult

- `collection_id` must reference existing collection
- `tool` must be one of: 'photostats', 'photo_pairing', 'pipeline_validation'
- `pipeline_id` required when tool='pipeline_validation', null otherwise
- `completed_at` must be >= `started_at`
- `duration_seconds` must be >= 0
- `results_json` must be valid JSON

### Pipeline

- `name` must be 1-255 characters, unique
- `nodes_json` must contain at least one node
- `edges_json` can be empty (single-node pipeline)
- `version` must be >= 1
- Only one pipeline can have `is_active=true`

### PipelineHistory

- `version` must match pipeline version at time of creation
- `pipeline_id` must reference existing pipeline
- Records are immutable (no updates)

### Configuration

- `category` must be one of: 'extensions', 'cameras', 'processing_methods'
- `key` must be 1-255 characters
- `value_json` must be valid JSON appropriate for category
- (category, key) combination must be unique

---

## State Transitions

### AnalysisResult Status

```
[none] ──(create job)──> RUNNING ──(success)──> COMPLETED
                              │
                              ├──(error)───> FAILED
                              │
                              └──(cancel)──> CANCELLED
```

Note: RUNNING is job queue state, not stored in database. Only terminal states are persisted.

### Pipeline Activation

```
[inactive] ──(activate)──> [active]
    ▲                          │
    │                          │
    └───(deactivate)───────────┘
           or
    └───(another activated)────┘
```

Only one pipeline can be active. Activating a pipeline deactivates any previously active pipeline.

---

## Migration Strategy

### Phase 4 Migration (003_analysis_results.py)

```python
def upgrade():
    # Create analysis_results table
    op.create_table('analysis_results',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('collection_id', sa.Integer(), sa.ForeignKey('collections.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tool', sa.String(50), nullable=False),
        sa.Column('pipeline_id', sa.Integer(), sa.ForeignKey('pipelines.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.Enum('COMPLETED', 'FAILED', 'CANCELLED', name='result_status'), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=False),
        sa.Column('results_json', sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column('report_html', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('files_scanned', sa.Integer(), nullable=True),
        sa.Column('issues_found', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # Create indexes
    op.create_index('idx_results_collection', 'analysis_results', ['collection_id'])
    op.create_index('idx_results_tool', 'analysis_results', ['tool'])
    op.create_index('idx_results_created', 'analysis_results', ['created_at'])
```

### Phase 5 Migration (004_pipelines.py)

```python
def upgrade():
    # Create pipelines table
    op.create_table('pipelines',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(255), unique=True, nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('nodes_json', sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column('edges_json', sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column('version', sa.Integer(), default=1, nullable=False),
        sa.Column('is_active', sa.Boolean(), default=False, nullable=False),
        sa.Column('is_valid', sa.Boolean(), default=False, nullable=False),
        sa.Column('validation_errors', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=False),
    )

    # Create pipeline_history table
    op.create_table('pipeline_history',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('pipeline_id', sa.Integer(), sa.ForeignKey('pipelines.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('nodes_json', sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column('edges_json', sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column('change_summary', sa.String(500), nullable=True),
        sa.Column('changed_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    # Create indexes
    op.create_index('idx_pipelines_name', 'pipelines', ['name'])
    op.create_index('idx_pipelines_active', 'pipelines', ['is_active'], postgresql_where='is_active = true')
    op.create_index('idx_history_pipeline', 'pipeline_history', ['pipeline_id'])
```

### Phase 7 Migration (005_configurations.py)

```python
def upgrade():
    # Create configurations table
    op.create_table('configurations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('key', sa.String(255), nullable=False),
        sa.Column('value_json', sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source', sa.String(20), default='database', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now(), nullable=False),
    )

    # Create unique constraint
    op.create_unique_constraint('uq_config_category_key', 'configurations', ['category', 'key'])

    # Create indexes
    op.create_index('idx_config_category', 'configurations', ['category'])
```

---

## Data Examples

### AnalysisResult (PhotoStats)

```json
{
  "id": 1,
  "collection_id": 5,
  "tool": "photostats",
  "pipeline_id": null,
  "status": "COMPLETED",
  "started_at": "2026-01-03T10:00:00Z",
  "completed_at": "2026-01-03T10:02:30Z",
  "duration_seconds": 150.0,
  "results_json": {
    "total_size": 52428800000,
    "total_files": 1250,
    "file_counts": {
      ".dng": 500,
      ".cr3": 300,
      ".xmp": 950
    },
    "orphaned_images": ["IMG_0001.dng", "IMG_0002.cr3"],
    "orphaned_xmp": ["IMG_9999.xmp"]
  },
  "files_scanned": 1250,
  "issues_found": 3
}
```

### Pipeline (Photo Workflow)

```json
{
  "id": 1,
  "name": "Standard RAW Workflow",
  "description": "RAW capture to processed TIFF export",
  "nodes_json": [
    {"id": "capture", "type": "capture", "properties": {"camera_id_pattern": "[A-Z0-9]{4}"}},
    {"id": "raw", "type": "file", "properties": {"extension": ".dng"}},
    {"id": "xmp", "type": "file", "properties": {"extension": ".xmp"}},
    {"id": "pair", "type": "pairing", "properties": {"inputs": ["raw", "xmp"]}},
    {"id": "export", "type": "file", "properties": {"extension": ".tiff"}},
    {"id": "done", "type": "termination", "properties": {"classification": "CONSISTENT"}}
  ],
  "edges_json": [
    {"from": "capture", "to": "raw"},
    {"from": "raw", "to": "pair"},
    {"from": "xmp", "to": "pair"},
    {"from": "pair", "to": "export"},
    {"from": "export", "to": "done"}
  ],
  "version": 3,
  "is_active": true,
  "is_valid": true
}
```

### Configuration (Extensions)

```json
{
  "id": 1,
  "category": "extensions",
  "key": "photo_extensions",
  "value_json": [".dng", ".cr3", ".tiff", ".jpg"],
  "description": "Recognized photo file extensions",
  "source": "yaml_import"
}
```
