# Research: Cloud Storage Bucket Inventory Import

**Feature**: 107-bucket-inventory-import
**Date**: 2026-01-24
**Status**: Complete

## Research Questions

This document captures research findings for technical decisions required by the bucket inventory import feature.

---

## 1. AWS S3 Inventory Format

**Question**: What is the structure of S3 Inventory reports and how should we parse them?

### Decision: Use CSV format with gzip decompression and streaming parsing

### Rationale

AWS S3 Inventory generates reports with a manifest file at a known location:

```
s3://{destination-bucket}/{source-bucket}/{config-name}/{timestamp}/manifest.json
```

**IMPORTANT**: The data files are NOT stored in a subfolder relative to the manifest. The manifest.json contains the full S3 keys for each data file, which may be stored in a completely different folder structure (typically branching from a parent folder). The implementation MUST use the exact keys from the manifest's `files` array to locate data files.

**Manifest Structure**:
```json
{
  "sourceBucket": "photo-bucket",
  "destinationBucket": "inventory-bucket",
  "version": "2016-11-30",
  "creationTimestamp": "1705708800000",
  "fileFormat": "CSV",
  "fileSchema": "Bucket, Key, Size, LastModifiedDate, ETag, StorageClass",
  "files": [
    {
      "key": "source-bucket/config-name/data/abc123-def456.csv.gz",
      "size": 12345678,
      "MD5checksum": "abc123..."
    }
  ]
}
```

**Key Point**: The `files[].key` values are full S3 object keys within the destination bucket. Do NOT assume any relative path relationship between the manifest location and data file locations.

**CSV Fields** (configurable by user in AWS console):
- Required: `Bucket`, `Key`, `Size`, `LastModifiedDate`
- Optional: `ETag`, `StorageClass`, `IsMultipartUploaded`, `ReplicationStatus`, `ChecksumAlgorithm`

**Parsing Strategy**:
1. Fetch `manifest.json` from the known inventory location to get file list and schema
2. For each entry in `files` array, use the exact `key` value to download the data file from the destination bucket
3. Decompress gzip in streaming fashion (avoid loading entire file in memory)
4. Parse CSV rows using schema from manifest's `fileSchema`
5. Extract folders by identifying keys ending with "/" or deriving parent paths

### Alternatives Considered

| Format | Pros | Cons | Decision |
|--------|------|------|----------|
| CSV | Simple parsing, Python stdlib support | Larger file size | **Selected** - Most common, supported everywhere |
| ORC | Columnar, smaller size | Requires pyarrow/fastparquet | Future enhancement |
| Parquet | Columnar, good compression | Additional dependency | Future enhancement (needed for GCS) |

---

## 2. GCS Storage Insights Format

**Question**: What is the structure of GCS inventory reports and how do they differ from S3?

### Decision: Support both CSV and Parquet formats, uncompressed

### Rationale

GCS Storage Insights has a similar but distinct structure:

```
gs://{destination-bucket}/{source-bucket}/{config-name}/{snapshot-date}/
├── manifest.json
└── shard_0.csv (or shard_0.parquet)
└── shard_1.csv
└── ...
```

**Manifest Structure**:
```json
{
  "report_config": { "display_name": "inventory-config", ... },
  "records_processed": 1500000,
  "snapshot_time": "2026-01-20T00:00:00Z",
  "shard_count": 2,
  "report_shards_file_names": ["shard_0.csv", "shard_1.csv"]
}
```

**Key Differences from S3**:

| Aspect | AWS S3 | GCS |
|--------|--------|-----|
| Compression | gzip (always) | Uncompressed |
| Object key field | `Key` | `name` |
| Size field | `Size` | `size` |
| Modified field | `LastModifiedDate` | `updated` |
| ETag field | `ETag` | `etag` |
| Manifest structure | `files` array | `report_shards_file_names` array |

**Implementation Approach**:
- Create unified internal format: `InventoryEntry(key, size, last_modified, etag, storage_class)`
- Provider-specific parsers map to unified format
- Agent auto-detects provider from connector type

---

## 3. Folder Extraction Algorithm

**Question**: How to efficiently extract unique folder paths from millions of object keys?

### Decision: Single-pass extraction with set deduplication

### Rationale

Object keys like `2020/Milledgeville, GA/IMG_0001.CR3` must produce folders:
- `2020/`
- `2020/Milledgeville, GA/`

**Algorithm**:
```python
def extract_folders(keys: Iterable[str]) -> Set[str]:
    folders = set()
    for key in keys:
        # Skip folder entries themselves
        if key.endswith("/"):
            folders.add(key)
            continue

        # Extract all parent folders
        parts = key.split("/")
        for i in range(1, len(parts)):
            folder = "/".join(parts[:i]) + "/"
            folders.add(folder)

    return folders
```

**Memory Optimization**:
- Process in streaming chunks of 100k keys
- Use set for O(1) deduplication
- For 5M objects with 10k unique folders: ~500KB memory for folder set

### Alternatives Considered

| Approach | Memory | Speed | Decision |
|----------|--------|-------|----------|
| Two-pass (count, then extract) | Higher | Slower | Rejected - unnecessary complexity |
| Streaming with set | Low | Fast | **Selected** |
| Sort-based dedup | Higher | Similar | Rejected - sorting 5M items expensive |

---

## 4. Collection State and TTL

**Question**: What are the valid Collection states and their implications?

### Decision: Use existing state enum (Live, Archived, Closed) with TTL mapping

### Rationale

From existing Collection model analysis, states drive cache TTL behavior:

| State | Description | TTL Behavior |
|-------|-------------|--------------|
| `live` | Active collection being updated | Short TTL, frequent refresh |
| `archived` | Complete collection, rarely changes | Medium TTL, occasional refresh |
| `closed` | Finished collection, never changes | Long TTL, minimal refresh |

**For Inventory Import**:
- Default state should be configurable (typically `archived` for historical buckets)
- Batch "Set all states" action allows quick assignment
- State affects how often FileInfo gets refreshed from subsequent inventory imports

---

## 5. Hierarchical Selection Constraint

**Question**: How to implement the constraint that prevents ancestor/descendant selection overlap?

### Decision: Maintain selection state with path-based constraint checking

### Rationale

When user selects folder `2020/Event/`, we must disable:
- Ancestors: `2020/` (parent)
- Descendants: `2020/Event/Subfolder/` (children)

**Implementation**:
```typescript
function isSelectable(path: string, selectedPaths: Set<string>): boolean {
  for (const selected of selectedPaths) {
    // Check if path is ancestor of selected
    if (selected.startsWith(path)) return false
    // Check if path is descendant of selected
    if (path.startsWith(selected)) return false
  }
  return true
}
```

**UI Behavior**:
- Disabled nodes show grayed styling with tooltip explaining why
- Parallel branches remain fully selectable
- Already-mapped folders shown with "linked" indicator and disabled

---

## 6. Name Suggestion Algorithm

**Question**: How to generate readable Collection names from folder paths?

### Decision: Path component transformation with URL decoding

### Rationale

Transform `2020/Milledgeville%2C%20GA/Picked/` into `2020 - Milledgeville GA`:

**Algorithm**:
```typescript
function suggestCollectionName(folderPath: string, ignorePatterns: string[] = []): string {
  // Remove trailing slash
  let path = folderPath.replace(/\/$/, '')

  // Remove ignored patterns
  for (const pattern of ignorePatterns) {
    path = path.replace(pattern, '')
  }

  // Split into parts
  const parts = path.split('/').filter(Boolean)

  // Transform each part
  const cleaned = parts.map(part => {
    // URL decode
    let decoded = decodeURIComponent(part)
    // Replace common separators
    decoded = decoded.replace(/[_-]/g, ' ')
    // Remove special characters
    decoded = decoded.replace(/[,]/g, '')
    // Title case
    return decoded.split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ')
  })

  return cleaned.join(' - ')
}
```

**Examples**:
| Input | Output |
|-------|--------|
| `2020/Milledgeville, GA/` | `2020 - Milledgeville GA` |
| `2021/Wedding/Smith-Jones/` | `2021 - Wedding - Smith Jones` |
| `archive/2019-06-15_concert/` | `Archive - 2019 06 15 Concert` |

---

## 7. Validation Flow for Agent-Side Credentials

**Question**: How to validate inventory accessibility when credentials are on the agent?

### Decision: Create validation job type with lightweight agent execution

### Rationale

For connectors with `credential_location = "agent"`:
1. Server cannot directly validate inventory path
2. Must create a validation job for agent to execute
3. Agent fetches manifest.json only (lightweight check)
4. Reports success/failure back to server
5. Server updates connector inventory validation status

**Job Type**: `inventory_validate` (distinct from `inventory_import`)

**Flow**:
```
User saves config → Server creates validation job → Agent claims job
→ Agent fetches manifest.json → Agent reports result → Server updates status
```

**Status Enum**:
- `pending` - Validation not yet attempted (no agent available)
- `validating` - Validation job in progress
- `validated` - Successfully validated
- `failed` - Validation failed (with error message)

---

## 8. Chain Scheduling Implementation

**Question**: How to implement automatic rescheduling after job completion?

### Decision: Job completion handler creates next scheduled job

### Rationale

Unlike TTL-based scheduling (which uses `next_scheduled_at` on Collection), inventory import uses chain scheduling:

1. User enables schedule (daily/weekly) on Connector
2. System creates first scheduled Job with future `scheduled_at`
3. When job completes (all phases), job coordinator creates next Job
4. Next job's `scheduled_at` = current completion time + interval

**Implementation in job_coordinator_service.py**:
```python
async def complete_inventory_import(job: Job, results: Dict) -> None:
    # Store results...

    # Check if scheduling enabled
    connector = await get_connector(job.connector_id)
    if connector.inventory_schedule != "manual":
        interval = timedelta(days=1) if connector.inventory_schedule == "daily" else timedelta(weeks=1)
        next_scheduled = datetime.utcnow() + interval

        # Create next job
        await create_inventory_import_job(
            connector_id=connector.id,
            scheduled_at=next_scheduled
        )
```

**Concurrency Prevention**:
- Before creating import job, check for existing PENDING/RUNNING jobs for same connector
- If exists, reject with "Import already in progress" message

---

## 9. FileInfo Storage Strategy

**Question**: How to store FileInfo on Collection efficiently?

### Decision: JSONB array on Collection model with metadata fields

### Rationale

**Schema**:
```python
class Collection(Base):
    # ... existing fields ...

    # FileInfo cache
    file_info = Column(JSONB, nullable=True)  # List[FileInfo]
    file_info_updated_at = Column(DateTime, nullable=True)
    file_info_source = Column(String(20), nullable=True)  # "api" | "inventory"
```

**FileInfo Structure**:
```json
[
  {
    "key": "2020/Event/IMG_0001.CR3",
    "size": 24831445,
    "last_modified": "2022-11-25T13:30:49.000Z",
    "etag": "371e1101d4248ef2609e269697bb0221-2",
    "storage_class": "GLACIER_IR"
  }
]
```

**Size Considerations**:
- 1M files × ~150 bytes/entry ≈ 150MB JSONB
- PostgreSQL handles this efficiently with TOAST compression
- For extreme cases (>5M files), consider pagination or external storage

**Tool Integration**:
- Tools check `file_info` before calling `list_files_with_metadata()`
- If `file_info` present and fresh, use directly
- Otherwise, fetch via storage adapter (existing behavior)

---

## 10. Tree View Performance

**Question**: How to render 10k+ folders efficiently in the UI?

### Decision: Virtual scrolling with lazy loading

### Rationale

**Strategy**:
1. **Virtualization**: Only render visible nodes (~50-100 at a time)
2. **Lazy expand**: Load children only when parent expanded
3. **Incremental search**: Filter tree as user types

**Implementation Options**:

| Library | Pros | Cons | Decision |
|---------|------|------|----------|
| react-window | Small, fast | Basic API | Fallback option |
| tanstack-virtual | Flexible, well-maintained | Learning curve | **Selected** |
| react-virtualized | Feature-rich | Large bundle | Rejected - overkill |

**Tree Data Structure**:
```typescript
interface FolderNode {
  path: string
  name: string
  objectCount: number
  totalSize: number
  children?: FolderNode[]
  isExpanded?: boolean
  isSelected?: boolean
  isMapped?: boolean  // Already has Collection
}
```

**API Design**:
- `GET /connectors/{guid}/inventory/folders` - Returns flat list with parent references
- Frontend builds tree structure from flat list
- Supports filtering by path prefix for search

---

## Summary

All research questions have been resolved with clear decisions and rationale. No NEEDS CLARIFICATION items remain. The implementation can proceed to Phase 1 (data model and contracts).
