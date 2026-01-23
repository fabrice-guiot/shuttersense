# Data Model: Storage Optimization for Analysis Results

**Feature**: 022-storage-optimization
**Date**: 2026-01-22

## Entity Changes

### 1. AnalysisResult (Enhanced)

**File**: `backend/src/models/analysis_result.py`

#### New Fields

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `input_state_hash` | String(64) | Yes | NULL | SHA-256 hash of Input State components |
| `input_state_json` | JSONB | Yes | NULL | Full Input State for debugging (DEBUG mode only) |
| `no_change_copy` | Boolean | No | False | True if this result references another |
| `download_report_from` | String(50) | Yes | NULL | GUID of source result for report download |

#### Updated Indexes

```sql
-- Existing indexes retained
CREATE INDEX idx_results_collection ON analysis_results(collection_id);
CREATE INDEX idx_results_tool ON analysis_results(tool);
CREATE INDEX idx_results_created ON analysis_results(created_at);
CREATE INDEX idx_results_collection_tool_date ON analysis_results(collection_id, tool, created_at DESC);

-- New indexes for optimization queries
CREATE INDEX idx_results_input_state ON analysis_results(collection_id, tool, input_state_hash)
    WHERE input_state_hash IS NOT NULL;
CREATE INDEX idx_results_no_change_source ON analysis_results(download_report_from)
    WHERE download_report_from IS NOT NULL;
CREATE INDEX idx_results_cleanup ON analysis_results(team_id, status, created_at);
```

#### Validation Rules

- `input_state_hash`: Must be exactly 64 characters (SHA-256 hex) or NULL
- `download_report_from`: Must be valid GUID format (res_xxx) or NULL
- If `no_change_copy=True`, then `download_report_from` must not be NULL
- If `no_change_copy=True`, then `report_html` must be NULL

---

### 2. ResultStatus (Enhanced Enum)

**File**: `backend/src/models/__init__.py`

```python
class ResultStatus(enum.Enum):
    """Status of an analysis result after tool execution."""
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    NO_CHANGE = "NO_CHANGE"  # NEW: Result references previous, no new data
```

---

### 3. Configuration (result_retention category)

**File**: `backend/src/models/configuration.py` (no changes, uses existing model)

#### Retention Settings Keys

| Key | Type | Default | Valid Values | Description |
|-----|------|---------|--------------|-------------|
| `job_completed_days` | int | 2 | 1, 2, 5, 7, 14, 30, 90, 180, 365, 0 | Days to retain completed jobs |
| `job_failed_days` | int | 7 | 1, 2, 5, 7, 14, 30, 90, 180, 365, 0 | Days to retain failed jobs |
| `result_completed_days` | int | 0 | 1, 2, 5, 7, 14, 30, 90, 180, 365, 0 | Days to retain completed results |
| `preserve_per_collection` | int | 1 | 1, 2, 3, 5, 10 | Minimum results per (collection, tool) |

Note: 0 means "unlimited" (no automatic deletion)

---

### 4. StorageMetrics (New Entity)

**File**: `backend/src/models/storage_metrics.py`

#### Fields

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | Integer | No | Auto | Primary key |
| `team_id` | FK (teams) | No | - | Team scope (one row per team) |
| `total_reports_generated` | BigInteger | No | 0 | Cumulative count of all job completions (COMPLETED, NO_CHANGE, FAILED) |
| `completed_jobs_purged` | BigInteger | No | 0 | Cumulative count of completed jobs deleted by cleanup |
| `failed_jobs_purged` | BigInteger | No | 0 | Cumulative count of failed jobs deleted by cleanup |
| `completed_results_purged_original` | BigInteger | No | 0 | Cumulative count of original results purged (no_change_copy=false) |
| `completed_results_purged_copy` | BigInteger | No | 0 | Cumulative count of copy results purged (no_change_copy=true) |
| `estimated_bytes_purged` | BigInteger | No | 0 | Cumulative estimated bytes freed from DB (JSON + HTML sizes) |
| `updated_at` | DateTime | No | Auto | Last update timestamp |

#### Computed Fields (Real-time Queries, Not Stored)

| Field | Description |
|-------|-------------|
| `reports_retained_count` | Current count of retained results (matches header KPI) |
| `reports_retained_json_bytes` | Current total JSON size of retained results |
| `reports_retained_html_bytes` | Current total HTML size of retained results |
| `preserved_results_count` | Count of results protected by preserve_per_collection setting |

#### Constraints

- Unique constraint on `team_id` (one metrics row per team)
- All counter fields use BigInteger to handle large cumulative values

#### Migration

```python
"""Add storage_metrics table.

Revision ID: 022b_storage_metrics
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'storage_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('total_reports_generated', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('completed_jobs_purged', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('failed_jobs_purged', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('completed_results_purged_original', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('completed_results_purged_copy', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('estimated_bytes_purged', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id', name='uq_storage_metrics_team')
    )
    op.create_index('idx_storage_metrics_team', 'storage_metrics', ['team_id'])


def downgrade():
    op.drop_index('idx_storage_metrics_team', table_name='storage_metrics')
    op.drop_table('storage_metrics')
```

---

## Entity Relationships

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AnalysisResult                               │
├─────────────────────────────────────────────────────────────────────┤
│ id (PK)                                                              │
│ uuid / guid (res_xxx)                                                │
│ team_id (FK → teams)                                                 │
│ collection_id (FK → collections, nullable)                           │
│ pipeline_id (FK → pipelines, nullable)                               │
│ pipeline_version                                                     │
│ tool                                                                 │
│ status (COMPLETED | FAILED | CANCELLED | NO_CHANGE)                  │
│ started_at, completed_at, duration_seconds                           │
│ results_json (JSONB)                                                 │
│ report_html (nullable)                                               │
│ error_message (nullable)                                             │
│ files_scanned, issues_found                                          │
│ input_state_hash (nullable) ←────────────────┐ NEW                   │
│ input_state_json (nullable)                   │ NEW                   │
│ no_change_copy (default: false)               │ NEW                   │
│ download_report_from (nullable) ──────────────┘ NEW                   │
│ created_at                                                           │
└─────────────────────────────────────────────────────────────────────┘
         │
         │ download_report_from references another AnalysisResult.guid
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    AnalysisResult (Source)                           │
│                                                                      │
│ guid = "res_01abc..."                                                │
│ report_html = "<html>..." (actual report content)                    │
│ no_change_copy = false                                               │
└─────────────────────────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│                         StorageMetrics                               │
├─────────────────────────────────────────────────────────────────────┤
│ id (PK)                                                              │
│ team_id (FK → teams, UNIQUE)                                         │
│ total_reports_generated (BigInt, cumulative)                         │
│ completed_jobs_purged (BigInt, cumulative)                           │
│ failed_jobs_purged (BigInt, cumulative)                              │
│ completed_results_purged_original (BigInt, cumulative)               │
│ completed_results_purged_copy (BigInt, cumulative)                   │
│ estimated_bytes_purged (BigInt, cumulative)                          │
│ updated_at                                                           │
└─────────────────────────────────────────────────────────────────────┘
         │
         │ One row per team (created on first cleanup or job completion)
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                            Team                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Input State Structure (Computed, Not Stored as Entity)

The Input State is a logical structure computed by the agent. Only the hash is stored in the database.

### PhotoStats / Photo Pairing

```json
{
  "collection_guid": "col_01abc...",
  "file_list_hash": "abc123...",
  "configuration_hash": "def456..."
}
```

### Pipeline Validation (Collection Mode)

```json
{
  "collection_guid": "col_01abc...",
  "pipeline_guid": "pip_01xyz...",
  "pipeline_version": 3,
  "file_list_hash": "abc123...",
  "configuration_hash": "def456..."
}
```

### Pipeline Validation (Display-Graph Mode)

```json
{
  "pipeline_guid": "pip_01xyz...",
  "pipeline_version": 3
}
```

---

## Database Migration

### Migration Script

```python
"""Add storage optimization fields to analysis_results.

Revision ID: 022_storage_optimization
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Add new columns to analysis_results
    op.add_column('analysis_results', sa.Column(
        'input_state_hash',
        sa.String(64),
        nullable=True,
        comment='SHA-256 hash of Input State components'
    ))
    op.add_column('analysis_results', sa.Column(
        'input_state_json',
        postgresql.JSONB().with_variant(sa.JSON(), 'sqlite'),
        nullable=True,
        comment='Full Input State for debugging'
    ))
    op.add_column('analysis_results', sa.Column(
        'no_change_copy',
        sa.Boolean(),
        server_default='false',
        nullable=False,
        comment='True if this result references another'
    ))
    op.add_column('analysis_results', sa.Column(
        'download_report_from',
        sa.String(50),
        nullable=True,
        comment='GUID of source result for report download'
    ))

    # Add new indexes
    op.create_index(
        'idx_results_input_state',
        'analysis_results',
        ['collection_id', 'tool', 'input_state_hash'],
        postgresql_where=sa.text('input_state_hash IS NOT NULL')
    )
    op.create_index(
        'idx_results_no_change_source',
        'analysis_results',
        ['download_report_from'],
        postgresql_where=sa.text('download_report_from IS NOT NULL')
    )
    op.create_index(
        'idx_results_cleanup',
        'analysis_results',
        ['team_id', 'status', 'created_at']
    )


def downgrade():
    op.drop_index('idx_results_cleanup', table_name='analysis_results')
    op.drop_index('idx_results_no_change_source', table_name='analysis_results')
    op.drop_index('idx_results_input_state', table_name='analysis_results')
    op.drop_column('analysis_results', 'download_report_from')
    op.drop_column('analysis_results', 'no_change_copy')
    op.drop_column('analysis_results', 'input_state_json')
    op.drop_column('analysis_results', 'input_state_hash')
```

---

## State Transitions

### Result Status Flow

```
            ┌──────────────────────────────────────────────────────────┐
            │                                                          │
Agent Runs  ▼                                                          │
Tool     ───┬──► COMPLETED (new results, has report_html)              │
            │                                                          │
            ├──► NO_CHANGE (references previous, no report_html)  ─────┘
            │         │                                           (may become
            ├──► FAILED (has error_message)                        COMPLETED
            │                                                      on next run)
            └──► CANCELLED (user/system cancellation)
```

### Retention Cleanup Flow

```
On Job Creation:
1. Check team retention settings
2. If unlimited (0 days), skip cleanup
3. For each retention category:
   a. Query old items (created_at < now - retention_days)
   b. Exclude items protected by preserve_per_collection
   c. Delete in batches of 100
   d. Log deletions
4. Proceed with job creation (regardless of cleanup success)
```

---

## Seed Data

### Default Retention Settings (for new teams)

```python
DEFAULT_RETENTION_SETTINGS = {
    "job_completed_days": 2,
    "job_failed_days": 7,
    "result_completed_days": 0,  # Unlimited by default
    "preserve_per_collection": 1,
}
```

These settings are created in the `result_retention` category when a new team is created or when retention settings are first accessed.
