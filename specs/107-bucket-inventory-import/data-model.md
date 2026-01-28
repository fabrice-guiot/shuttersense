# Data Model: Cloud Storage Bucket Inventory Import

**Feature**: 107-bucket-inventory-import
**Date**: 2026-01-24
**Status**: Complete

## Entity Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Bucket Inventory Import                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐      1:N       ┌──────────────────┐
│  Connector   │───────────────>│  InventoryFolder │
│  (Extended)  │                │  (NEW)           │
│              │                │  prefix: fld_    │
└──────┬───────┘                └──────────────────┘
       │
       │ 1:N
       ▼
┌──────────────┐
│  Collection  │
│  (Extended)  │
│              │
│  +file_info  │
│  +file_info_ │
│   updated_at │
│  +file_info_ │
│   source     │
└──────────────┘
```

---

## New Entity: InventoryFolder

Represents a folder discovered from cloud inventory data.

**GUID Prefix**: `fld_`

### Fields

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | Integer | No | Internal primary key |
| `guid` | String(30) | No | External identifier (fld_xxx) |
| `connector_id` | Integer (FK) | No | Reference to parent Connector |
| `path` | String(1024) | No | Full folder path (e.g., "2020/Event/") |
| `object_count` | Integer | No | Number of objects in folder (direct children) |
| `total_size_bytes` | BigInteger | No | Sum of object sizes in folder |
| `deepest_modified` | DateTime | Yes | Most recent object modification in folder |
| `discovered_at` | DateTime | No | When folder was first discovered |
| `collection_guid` | String(30) | Yes | GUID of mapped Collection (if any) |

### Indexes

- Unique: `(connector_id, path)`
- Index: `connector_id` (for folder listing)
- Index: `collection_guid` (for mapping lookup)

### Relationships

- **Connector** (many-to-one): Each folder belongs to one connector
- **Collection** (one-to-one, optional): A folder may be mapped to a collection

### SQLAlchemy Model

```python
class InventoryFolder(Base, GuidMixin):
    """Folder discovered from cloud inventory."""
    __tablename__ = "inventory_folders"

    GUID_PREFIX = "fld"

    id: Mapped[int] = mapped_column(primary_key=True)
    connector_id: Mapped[int] = mapped_column(ForeignKey("connectors.id"), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    object_count: Mapped[int] = mapped_column(Integer, default=0)
    total_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    deepest_modified: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    collection_guid: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Relationships
    connector: Mapped["Connector"] = relationship("Connector", back_populates="inventory_folders")

    __table_args__ = (
        UniqueConstraint("connector_id", "path", name="uq_inventory_folder_path"),
        Index("ix_inventory_folder_connector", "connector_id"),
        Index("ix_inventory_folder_collection", "collection_guid"),
    )
```

---

## Extended Entity: Connector

Add inventory configuration as embedded JSONB.

### New Fields

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `inventory_config` | JSONB | Yes | Inventory source configuration |
| `inventory_validation_status` | String(20) | Yes | "pending" / "validating" / "validated" / "failed" |
| `inventory_validation_error` | String(500) | Yes | Error message if validation failed |
| `inventory_last_import_at` | DateTime | Yes | Timestamp of last successful import |
| `inventory_schedule` | String(20) | Yes | "manual" / "daily" / "weekly" |

### InventoryConfig Schema (S3)

```python
class S3InventoryConfig(BaseModel):
    """AWS S3 Inventory configuration."""
    destination_bucket: str = Field(..., description="Bucket where inventory is stored")
    source_bucket: str = Field(..., description="Bucket being inventoried")
    config_name: str = Field(..., description="Inventory configuration name")
    format: Literal["CSV", "ORC", "Parquet"] = Field(default="CSV")

    class Config:
        extra = "forbid"
```

### InventoryConfig Schema (GCS)

```python
class GCSInventoryConfig(BaseModel):
    """Google Cloud Storage Insights configuration."""
    destination_bucket: str = Field(..., description="Bucket where inventory is stored")
    report_config_name: str = Field(..., description="Report configuration name")
    format: Literal["CSV", "Parquet"] = Field(default="CSV")

    class Config:
        extra = "forbid"
```

---

## Extended Entity: Collection

Add FileInfo caching fields.

### New Fields

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `file_info` | JSONB | Yes | Array of FileInfo objects |
| `file_info_updated_at` | DateTime | Yes | When FileInfo was last updated |
| `file_info_source` | String(20) | Yes | "api" / "inventory" |
| `file_info_delta` | JSONB | Yes | Last delta summary (new/modified/deleted counts) |

### FileInfo Schema

```python
class FileInfo(BaseModel):
    """File metadata from inventory or API."""
    key: str = Field(..., description="Full object key/path")
    size: int = Field(..., description="Size in bytes")
    last_modified: str = Field(..., description="ISO8601 timestamp")
    etag: Optional[str] = Field(default=None, description="Object ETag")
    storage_class: Optional[str] = Field(default=None, description="Storage class")
```

### DeltaSummary Schema

```python
class DeltaSummary(BaseModel):
    """Summary of changes between inventory imports."""
    new_count: int = Field(default=0)
    modified_count: int = Field(default=0)
    deleted_count: int = Field(default=0)
    computed_at: str = Field(..., description="ISO8601 timestamp")
```

---

## State Transitions

### InventoryFolder Lifecycle

```
[Discovered] ──> [Unmapped] ──> [Mapped to Collection]
      │               │                  │
      │               │                  │
      └───────────────┴──────────────────┘
                      │
                      ▼
                  [Deleted]
                (on reimport if
                 folder no longer
                 exists in inventory)
```

### Inventory Validation Status

```
[pending] ──> [validating] ──> [validated]
                   │
                   └──> [failed]
```

### Collection FileInfo Source

```
[null] ──> [inventory] ──> [api]
              │               │
              └───────────────┘
              (can switch between
               sources as needed)
```

---

## Database Migration

### Up Migration

```sql
-- Create inventory_folders table
CREATE TABLE inventory_folders (
    id SERIAL PRIMARY KEY,
    guid VARCHAR(30) NOT NULL UNIQUE,
    connector_id INTEGER NOT NULL REFERENCES connectors(id) ON DELETE CASCADE,
    path VARCHAR(1024) NOT NULL,
    object_count INTEGER NOT NULL DEFAULT 0,
    total_size_bytes BIGINT NOT NULL DEFAULT 0,
    deepest_modified TIMESTAMP,
    discovered_at TIMESTAMP NOT NULL DEFAULT NOW(),
    collection_guid VARCHAR(30),
    CONSTRAINT uq_inventory_folder_path UNIQUE (connector_id, path)
);

CREATE INDEX ix_inventory_folder_connector ON inventory_folders(connector_id);
CREATE INDEX ix_inventory_folder_collection ON inventory_folders(collection_guid);

-- Extend connectors table
ALTER TABLE connectors
    ADD COLUMN inventory_config JSONB,
    ADD COLUMN inventory_validation_status VARCHAR(20),
    ADD COLUMN inventory_validation_error VARCHAR(500),
    ADD COLUMN inventory_last_import_at TIMESTAMP,
    ADD COLUMN inventory_schedule VARCHAR(20) DEFAULT 'manual';

-- Extend collections table
ALTER TABLE collections
    ADD COLUMN file_info JSONB,
    ADD COLUMN file_info_updated_at TIMESTAMP,
    ADD COLUMN file_info_source VARCHAR(20),
    ADD COLUMN file_info_delta JSONB;
```

### Down Migration

```sql
DROP TABLE IF EXISTS inventory_folders;

ALTER TABLE connectors
    DROP COLUMN IF EXISTS inventory_config,
    DROP COLUMN IF EXISTS inventory_validation_status,
    DROP COLUMN IF EXISTS inventory_validation_error,
    DROP COLUMN IF EXISTS inventory_last_import_at,
    DROP COLUMN IF EXISTS inventory_schedule;

ALTER TABLE collections
    DROP COLUMN IF EXISTS file_info,
    DROP COLUMN IF EXISTS file_info_updated_at,
    DROP COLUMN IF EXISTS file_info_source,
    DROP COLUMN IF EXISTS file_info_delta;
```

---

## Validation Rules

### InventoryFolder

- `path` must end with "/" (folder convention)
- `path` must not contain consecutive slashes
- `object_count` must be >= 0
- `total_size_bytes` must be >= 0

### InventoryConfig (S3)

- `destination_bucket` must be valid S3 bucket name (3-63 chars, no dots for best compatibility)
- `source_bucket` must be valid S3 bucket name
- `config_name` must match AWS inventory config naming rules (alphanumeric, hyphens, 1-64 chars)
- `format` must be one of: CSV, ORC, Parquet

### InventoryConfig (GCS)

- `destination_bucket` must be valid GCS bucket name (3-63 chars)
- `report_config_name` must match GCS naming rules
- `format` must be one of: CSV, Parquet

### FileInfo

- `key` must be non-empty
- `size` must be >= 0
- `last_modified` must be valid ISO8601 timestamp
