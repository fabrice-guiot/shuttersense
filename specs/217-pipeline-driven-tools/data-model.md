# Data Model: Pipeline-Driven Analysis Tools

**Feature Branch**: `217-pipeline-driven-tools`
**Date**: 2026-02-17

## New Entities

### Camera

Physical camera equipment tracked per team. Auto-discovered during analysis or manually created by users.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | Integer | PK, auto-increment | Internal ID (never exposed) |
| `uuid` | UUID (v7) | Unique, not null | External identifier base |
| `team_id` | Integer | FK→teams.id, not null | Tenant scope |
| `camera_id` | String(10) | Not null | Short alphanumeric ID from filenames (e.g., `AB3D`) |
| `status` | String(20) | Not null, default `"temporary"` | `"temporary"` or `"confirmed"` |
| `display_name` | String(100) | Nullable | User-assigned friendly name (e.g., `"Canon EOS R5"`) |
| `make` | String(100) | Nullable | Camera manufacturer |
| `model` | String(100) | Nullable | Camera model name |
| `serial_number` | String(100) | Nullable | Camera serial number |
| `notes` | Text | Nullable | Free-form notes |
| `metadata_json` | JSONB | Nullable | Custom metadata |
| `created_by_user_id` | Integer | FK→users.id, nullable, SET NULL | Audit: creator |
| `updated_by_user_id` | Integer | FK→users.id, nullable, SET NULL | Audit: last modifier |
| `created_at` | DateTime | Not null, server default | Creation timestamp |
| `updated_at` | DateTime | Not null, server default, on update | Last update timestamp |

**Constraints**:
- `uq_cameras_team_camera_id`: UNIQUE(`team_id`, `camera_id`)

**GUID**: Prefix `cam_` → e.g., `cam_01hgw2bbg0000000000000001`

**Mixins**: `GuidMixin` (GUID), `AuditMixin` (created_by/updated_by)

**Relationships**:
- `Camera.team` → `Team` (many-to-one)
- `Team.cameras` → `Camera[]` (one-to-many, reciprocal)

**Status transitions**:
```text
[auto-discover] → temporary
[user edit]     → confirmed
[user edit]     → temporary (can revert)
```

---

## Derived Structures (Not Persisted)

### PipelineToolConfig

Extracted from Pipeline `nodes_json` + `edges_json` at analysis time. Not stored in DB.

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `filename_regex` | `str` | Capture node `properties.filename_regex` | Regex for filename parsing (2 capture groups) |
| `camera_id_group` | `int` | Capture node `properties.camera_id_group` (default: 1) | Which capture group is the camera ID |
| `photo_extensions` | `Set[str]` | File nodes where `extension ∉ METADATA_EXTENSIONS` | Image file extensions (lowercase) |
| `metadata_extensions` | `Set[str]` | File nodes where `extension ∈ METADATA_EXTENSIONS` | Metadata file extensions (lowercase) |
| `require_sidecar` | `Set[str]` | Inferred from sibling File nodes | Image extensions requiring metadata sidecar |
| `processing_suffixes` | `Dict[str, str]` | Process node `method_ids` → `name` | method_id → human-readable display name |

**Constants**:
- `METADATA_EXTENSIONS = {".xmp"}` — recognized metadata formats (extensible)

**Extraction rules**:
1. **Extension categorization**: `ext ∈ METADATA_EXTENSIONS` → metadata; else → image (by exclusion)
2. **Sidecar inference**: If a parent node (Capture or Process) has edges to both a non-optional image File node and a non-optional metadata File node, the image extension requires a sidecar
3. **Processing suffixes**: Each Process node's `method_ids[]` mapped to the node's `name`
4. **Regex**: Required on Capture node. Missing raises `ValueError`.

---

## Modified Entities

### Collection (existing — no schema change)

Already has `pipeline_id` (FK→Pipeline) and `pipeline_version` (Integer). These fields are used for Pipeline resolution:
1. `Collection.pipeline_id` set → use that Pipeline
2. `Collection.pipeline_id` NULL → use team default Pipeline
3. No default Pipeline → Config fallback

### Team (existing — relationship only)

Add reciprocal relationship:
```python
cameras = relationship("Camera", back_populates="team")
```

### TeamConfigCache (existing — no schema change)

Already has `default_pipeline: Optional[CachedPipeline]` with `nodes` and `edges`. No structural change needed — `extract_tool_config()` can consume `CachedPipeline.nodes` and `.edges` directly.

---

## Entity Relationship Diagram

```text
Team (1) ──── (*) Camera
  │                 │
  │                 └── cam_ GUID
  │
  ├── (*) Pipeline
  │         │
  │         └── pip_ GUID
  │         │
  │         └── nodes_json ──→ [extract_tool_config()] ──→ PipelineToolConfig
  │
  └── (*) Collection
            │
            ├── pipeline_id ──→ Pipeline (optional, specific assignment)
            └── (fallback) ──→ Team default Pipeline ──→ Config fallback
```

---

## Migration Plan

### Alembic Migration: `add_cameras_table`

```python
# Alembic migration — DB-agnostic (works on both PostgreSQL and SQLite)
def upgrade():
    op.create_table(
        'cameras',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', UUIDType(), nullable=False),  # UUIDType from guid.py
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('camera_id', sa.String(10), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='temporary'),
        sa.Column('display_name', sa.String(100), nullable=True),
        sa.Column('make', sa.String(100), nullable=True),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('serial_number', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('updated_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('uuid'),
        sa.UniqueConstraint('team_id', 'camera_id', name='uq_cameras_team_camera_id'),
    )
    op.create_index('ix_cameras_uuid', 'cameras', ['uuid'])
    op.create_index('ix_cameras_team_id', 'cameras', ['team_id'])
    op.create_index('ix_cameras_status', 'cameras', ['status'])

def downgrade():
    op.drop_table('cameras')
```

> **Note**: Uses `sa.JSON()` (maps to JSONB on PostgreSQL, TEXT on SQLite), `UUIDType()` (from the existing `guid.py` pattern, handles PostgreSQL UUID vs SQLite LargeBinary), and `sa.func.now()` (dialect-aware) to ensure cross-dialect compatibility. See existing migrations for the established pattern.

**Reversible**: `DROP TABLE cameras` (no FK references from other tables).
