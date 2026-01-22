# PRD: Import S3 Collections from S3 Bucket Inventory File

**Issue**: #40
**Status**: Draft
**Created**: 2026-01-22
**Last Updated**: 2026-01-22 (v1.2)
**Related Features**:
- 004-remote-photos-persistence (Connector architecture)
- 007-remote-photos-completion (Tool execution)
- 021-distributed-agent-architecture (Agent-based processing)

---

## Executive Summary

This PRD proposes a new feature to reduce AWS S3 API consumption for remote collections by leveraging AWS S3's automated inventory reports. Instead of making continuous API calls to list objects in S3 buckets, the system will parse CSV-formatted inventory files that AWS generates automatically and stores in a designated S3 bucket.

### Current State

**Existing S3 Integration:**
- S3Adapter queries S3 directly via `list_objects_v2()` API calls
- Every collection scan triggers paginated API requests
- Large buckets (millions of objects) result in high API costs and latency
- No caching of file metadata between scans

**Pain Points:**
- High API costs for buckets with millions of objects
- Slow listing times for large collections
- Repeated API calls for unchanged data
- No efficient way to track bucket-wide changes

### What This PRD Delivers

- **S3 Inventory Integration**: Parse AWS S3 Inventory reports to discover bucket contents
- **Folder Extraction**: Automatically identify folder structures from inventory data
- **Collection Mapping**: Allow users to map inventory folders to Collections with intelligent naming
- **FileInfo Caching**: Store file metadata from inventory to avoid redundant API calls
- **Scheduled Sync**: Periodic inventory import matching AWS inventory generation frequency

---

## Background

### Problem Statement

AWS S3 buckets used for photo storage often contain millions of objects organized in folder hierarchies (e.g., `2020/Event-Name/`, `2021/Another-Event/`). Currently, each tool execution requires:

1. Calling `list_objects_v2()` with pagination (1,000 objects per request)
2. Filtering results to identify folders and files
3. Building file metadata structures for analysis

For a bucket with 1 million objects, this requires 1,000+ API calls, taking several minutes and incurring significant costs.

AWS S3 Inventory provides an alternative approach:
- Generates CSV/ORC/Parquet reports of all objects automatically
- Runs daily or weekly on a schedule defined by the user
- Includes metadata (size, last modified, storage class, ETag, checksums)
- Stored in a destination bucket at predictable paths

### Strategic Value

Implementing S3 Inventory import:
- **Reduces API costs** by 90%+ for large buckets
- **Improves performance** by eliminating pagination delays
- **Enables bulk operations** with complete bucket visibility
- **Supports offline analysis** (inventory can be downloaded once)
- **Aligns with AWS best practices** for large-scale bucket management

### Technical Background

**AWS S3 Inventory Concepts:**

| Concept | Description |
|---------|-------------|
| **Source Bucket** | The bucket being inventoried (contains photos) |
| **Destination Bucket** | Where inventory reports are stored |
| **Inventory Configuration** | Defines schedule, format, and fields to include |
| **Manifest File** | JSON file listing all inventory data files |
| **Data Files** | CSV/ORC/Parquet files containing object listings |

**Inventory File Location Pattern:**
```
s3://{destination-bucket}/{source-bucket}/{config-name}/{timestamp}/manifest.json
```

**Example:**
```
s3://my-inventory-bucket/photo-bucket/weekly-inventory/2026-01-20T00-00Z/manifest.json
```

---

## Goals

### Primary Goals

1. **Parse S3 Inventory Reports**: Read CSV-format inventory files from S3
2. **Extract Folder Structure**: Identify unique folder paths from object keys
3. **Store Folder Metadata**: Persist discovered folders on Connector records
4. **Enable Collection Mapping**: UI workflow for mapping folders to Collections
5. **Cache FileInfo**: Store file metadata to reduce subsequent API calls
6. **Support Scheduled Sync**: Periodic import matching inventory frequency

### Secondary Goals

1. **Intelligent Naming**: Suggest Collection names from folder paths
2. **Delta Detection**: Identify new/modified files since last inventory
3. **Multi-Format Support**: Support CSV, ORC, and Parquet inventory formats
4. **Progress Reporting**: Show inventory import progress in UI

### Non-Goals (v1)

1. **Inventory Configuration**: Creating/managing S3 Inventory configurations (users set this up in AWS)
2. **Real-Time Updates**: This is batch-oriented, not real-time
3. **Cross-Account Inventory**: Single AWS account only

**Note on Gzip Decompression**: AWS S3 Inventory data files are always gzip-compressed. The agent will handle decompression when executing the Connector tool that refreshes the inventory. This is an implementation detail, not a non-goal.

---

## User Personas

### Primary: Professional Photo Archiver (Alex)

- **Storage**: 5+ million photos across 500+ events in a single S3 bucket
- **Current Pain**: Listing takes 10+ minutes and costs $50+/month in API calls
- **Desired Outcome**: Import inventory weekly, analyze collections without API overhead
- **This PRD Delivers**: Inventory-based collection discovery and cached metadata

### Secondary: Photo Studio Manager (Morgan)

- **Storage**: Multi-terabyte bucket organized by year/client/shoot
- **Current Pain**: Cannot easily see all folders without expensive full scan
- **Desired Outcome**: See complete folder structure, selectively create collections
- **This PRD Delivers**: Folder extraction with intelligent naming suggestions

### Tertiary: Enterprise IT Administrator (Jordan)

- **Storage**: Centralized photo archive for organization
- **Current Pain**: Multiple users running redundant scans against same bucket
- **Desired Outcome**: Single inventory import serves all users' collection needs
- **This PRD Delivers**: Shared folder discovery with per-user collection mapping

---

## User Stories

### User Story 1: Configure Inventory Source (Priority: P1)

**As** an administrator with S3 inventory configured
**I want to** specify where my inventory reports are stored
**So that** the system can parse them instead of calling list APIs

**Acceptance Criteria:**
- Connector configuration includes inventory settings section
- User provides: inventory bucket, source bucket name, inventory config name
- System validates inventory path exists and is accessible
- Configuration saved securely on Connector record

**Independent Test:** Configure inventory source, verify system can locate manifest.json

---

### User Story 2: Import Inventory and Extract Folders (Priority: P1)

**As** a user with configured inventory source
**I want to** trigger an inventory import
**So that** I can see all folders in my bucket without API calls

**Architecture Note:** Per project constitution, all complex analysis and tool execution MUST run agent-side to avoid overloading the web server. The "Import Inventory" tool is designed from the start as an agent-executed tool using the JobQueue system.

**Acceptance Criteria:**
- "Import Inventory" action available on S3 Connector
- Action creates a Job in the JobQueue (not executed server-side)
- Agent claims and executes the import job
- Agent fetches latest manifest.json from inventory location
- Agent downloads, decompresses (gzip), and parses CSV data files
- Agent extracts unique folder paths (entries ending with "/" or parent paths)
- Agent reports results back to server; folders stored on Connector record
- UI shows job progress via standard job status polling
- Import completes within 5 minutes for 1 million objects

**Independent Test:** Trigger import, verify Job created in queue, agent executes and reports folders

---

### User Story 3: Map Folders to Collections (Priority: P1)

**As** a user with imported inventory
**I want to** select folders and create Collections from them
**So that** I can organize and analyze specific subsets

**Acceptance Criteria:**
- UI displays hierarchical folder tree from inventory
- User can select one or more folders
- System suggests Collection name from folder path (e.g., "2020/Milledgeville, GA/" → "2020 - Milledgeville - GA")
- User can accept or modify suggested name
- Collection created with folder path as location
- FileInfo populated from inventory data (no API calls needed)

**Independent Test:** Select folder from tree, accept suggested name, verify Collection created with cached FileInfo

---

### User Story 4: Automatic FileInfo Population (Priority: P1)

**As** a user creating Collections from inventory
**I want to** have file metadata pre-populated
**So that** tools can run without fetching metadata from S3

**Acceptance Criteria:**
- Collection records include FileInfo array from inventory
- FileInfo contains: path, size, last_modified, etag, storage_class
- Tools check for cached FileInfo before calling S3
- "Last updated from inventory" timestamp visible
- Option to refresh FileInfo from live S3 data if needed

**Independent Test:** Create Collection from inventory, run PhotoStats, verify zero list_objects API calls

---

### User Story 5: Scheduled Inventory Import (Priority: P2)

**As** an administrator
**I want to** schedule automatic inventory imports
**So that** Collections stay up-to-date without manual intervention

**Architecture Note:** Scheduling leverages the agent-executed Import Inventory tool from User Story 2. When a scheduled import job completes, the system automatically creates the next scheduled job based on the configured frequency. This "chain scheduling" approach ensures reliable periodic execution without requiring a separate scheduler service.

**Acceptance Criteria:**
- Connector configuration includes import schedule frequency
- Schedule options: manual only, daily, weekly, or matching inventory frequency
- When schedule is enabled, system creates first scheduled Job in JobQueue
- Upon job completion, system automatically creates next scheduled Job based on frequency
- Next job's scheduled_at timestamp calculated from completion time + frequency interval
- Last import timestamp and next scheduled import visible in UI
- Manual "Import Now" action available regardless of schedule (creates immediate job)
- Disabling schedule cancels any pending scheduled jobs

**Independent Test:** Configure weekly import, complete first job, verify next job auto-created with correct scheduled_at timestamp

---

### User Story 6: Delta Detection Between Inventories (Priority: P3)

**As** a user with periodic inventory imports
**I want to** see what changed since last import
**So that** I can identify new or modified photos

**Acceptance Criteria:**
- After import, system compares to previous inventory
- New files highlighted in UI
- Modified files (different ETag/size) highlighted
- Deleted files (present before, absent now) flagged
- Summary statistics: X new, Y modified, Z deleted

**Independent Test:** Run import, add files to bucket, run next import, verify changes detected

---

## Requirements

### Functional Requirements

#### Inventory Configuration

- **FR-001**: Add `inventory_config` field to S3 Connector configuration schema
- **FR-002**: Inventory config includes: destination_bucket, source_bucket, config_name
- **FR-003**: Validate inventory path accessibility during connector test
- **FR-004**: Store inventory settings encrypted with other credentials

#### Inventory Import (Agent-Executed)

- **FR-010**: "Import Inventory" action creates a Job in JobQueue (never executes server-side)
- **FR-011**: Create `InventoryImportTool` as an agent-executable tool type
- **FR-012**: Agent fetches and parses `manifest.json` from inventory location
- **FR-013**: Agent downloads and decompresses (gzip) data files referenced in manifest
- **FR-014**: Agent parses CSV format with configurable field mapping
- **FR-015**: Agent extracts unique folder paths from object keys
- **FR-016**: Agent reports results to server via job completion endpoint
- **FR-017**: Server stores folders as `InventoryFolder` records linked to Connector
- **FR-018**: Support streaming/chunked processing for large inventories

#### Folder-to-Collection Mapping

- **FR-020**: Create UI component for folder tree visualization
- **FR-021**: Implement intelligent name suggestion algorithm
- **FR-022**: Name suggestion rules: replace "/" with " - ", strip trailing slash, title case
- **FR-023**: Create Collection with pre-populated FileInfo from inventory
- **FR-024**: Support batch Collection creation from multiple folders

#### FileInfo Caching

- **FR-030**: Store FileInfo array on Collection records from inventory data
- **FR-031**: FileInfo schema: path, size (bytes), last_modified (ISO8601), etag, storage_class
- **FR-032**: Tools MUST check Collection.file_info before calling S3 list API
- **FR-033**: Provide "Refresh from S3" action to update FileInfo via API
- **FR-034**: Track `file_info_updated_at` timestamp on Collection

#### Scheduling (Chain-Based)

- **FR-040**: Add `inventory_schedule` field to Connector configuration
- **FR-041**: Schedule options: manual only, daily, weekly (no cron - simple intervals)
- **FR-042**: When schedule enabled, create first scheduled Job with future `scheduled_at`
- **FR-043**: Upon job completion, automatically create next scheduled Job
- **FR-044**: Next job's `scheduled_at` = completion time + configured interval
- **FR-045**: Prevent concurrent imports for same Connector
- **FR-046**: Disabling schedule cancels pending scheduled jobs
- **FR-047**: "Import Now" creates immediate job independent of schedule

### Non-Functional Requirements

#### Performance

- **NFR-001**: Import 1 million objects within 5 minutes
- **NFR-002**: Manifest fetch and parse within 10 seconds
- **NFR-003**: Folder tree render with 10,000 folders within 2 seconds
- **NFR-004**: Memory usage under 500MB during import

#### Reliability

- **NFR-010**: Resume interrupted imports from checkpoint
- **NFR-011**: Handle malformed inventory rows gracefully (skip, log)
- **NFR-012**: Retry transient S3 errors with exponential backoff
- **NFR-013**: Validate manifest schema before processing

#### Security

- **NFR-020**: Inventory bucket access via existing Connector credentials
- **NFR-021**: No storage of raw inventory files (process in memory)
- **NFR-022**: Audit log for import operations

#### Testing

- **NFR-030**: Unit tests for CSV parsing logic (>90% coverage)
- **NFR-031**: Integration tests with mock S3 inventory data
- **NFR-032**: Performance tests with 1M+ object inventory

---

## Technical Approach

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            S3 Inventory Import Flow                      │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│   User   │     │   Backend    │     │   Agent     │     │     S3       │
│   (UI)   │     │   (API)      │     │  (Worker)   │     │ (Inventory)  │
└────┬─────┘     └──────┬───────┘     └──────┬──────┘     └──────┬───────┘
     │                  │                    │                   │
     │ 1. Trigger Import│                    │                   │
     │─────────────────►│                    │                   │
     │                  │                    │                   │
     │                  │ 2. Create Job      │                   │
     │                  │───────────────────►│                   │
     │                  │                    │                   │
     │                  │                    │ 3. Fetch manifest │
     │                  │                    │──────────────────►│
     │                  │                    │◄──────────────────│
     │                  │                    │                   │
     │                  │                    │ 4. Download CSV   │
     │                  │                    │──────────────────►│
     │                  │                    │◄──────────────────│
     │                  │                    │                   │
     │                  │ 5. Store results   │                   │
     │                  │◄───────────────────│                   │
     │                  │                    │                   │
     │ 6. Display folders                    │                   │
     │◄─────────────────│                    │                   │
     │                  │                    │                   │
     │ 7. Select folders for Collections     │                   │
     │─────────────────►│                    │                   │
     │                  │                    │                   │
     │ 8. Collections created with FileInfo  │                   │
     │◄─────────────────│                    │                   │
```

### Data Model

#### InventoryConfig (embedded in Connector credentials)

```python
class InventoryConfig(BaseModel):
    """S3 Inventory configuration for a connector."""
    destination_bucket: str = Field(..., description="Bucket where inventory is stored")
    source_bucket: str = Field(..., description="Bucket being inventoried")
    config_name: str = Field(..., description="Inventory configuration name")
    format: Literal["CSV", "ORC", "Parquet"] = Field(default="CSV")
    schedule: Literal["manual", "daily", "weekly"] = Field(default="manual")
```

#### InventoryFolder (new table)

```python
class InventoryFolder(Base, ExternalIdMixin):
    """Folder discovered from S3 inventory."""
    __tablename__ = "inventory_folders"

    # GUID prefix: 'fld_'
    connector_id: int = Column(ForeignKey("connectors.id"), nullable=False)
    path: str = Column(String(1024), nullable=False)  # e.g., "2020/Milledgeville, GA/"
    object_count: int = Column(Integer, default=0)
    total_size_bytes: int = Column(BigInteger, default=0)
    last_modified: datetime = Column(DateTime)  # Most recent object in folder
    discovered_at: datetime = Column(DateTime, default=datetime.utcnow)

    # Relationship
    connector: Connector = relationship("Connector", back_populates="inventory_folders")
```

#### FileInfo (embedded in Collection)

```python
class FileInfo(BaseModel):
    """File metadata from S3 inventory."""
    key: str = Field(..., description="Full S3 object key")
    size: int = Field(..., description="Size in bytes")
    last_modified: datetime = Field(..., description="Last modified timestamp")
    etag: str = Field(..., description="S3 ETag (MD5 for non-multipart)")
    storage_class: str = Field(default="STANDARD")
    checksum_algorithm: Optional[str] = Field(default=None)
```

#### Collection Extension

```python
# Add to Collection model
file_info: List[FileInfo] = Column(JSONB, default=list)
file_info_updated_at: datetime = Column(DateTime, nullable=True)
file_info_source: Literal["api", "inventory"] = Column(String(20), nullable=True)
```

### S3 Inventory Manifest Schema

AWS generates `manifest.json` with this structure:

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
      "key": "photo-bucket/weekly-inventory/data/part-00000.csv.gz",
      "size": 12345678,
      "MD5checksum": "abc123..."
    }
  ]
}
```

### CSV Parsing Implementation

```python
class InventoryParser:
    """Parse S3 inventory CSV files."""

    REQUIRED_FIELDS = {"Key", "Size", "LastModifiedDate"}
    OPTIONAL_FIELDS = {"ETag", "StorageClass", "ChecksumAlgorithm"}

    def parse_manifest(self, manifest_data: bytes) -> InventoryManifest:
        """Parse manifest.json and return structured data."""
        data = json.loads(manifest_data)
        return InventoryManifest(
            source_bucket=data["sourceBucket"],
            file_format=data["fileFormat"],
            file_schema=data["fileSchema"].split(", "),
            data_files=[f["key"] for f in data["files"]]
        )

    def parse_csv_row(self, row: Dict[str, str], schema: List[str]) -> FileInfo:
        """Parse single CSV row into FileInfo."""
        return FileInfo(
            key=row["Key"],
            size=int(row["Size"]),
            last_modified=datetime.fromisoformat(row["LastModifiedDate"]),
            etag=row.get("ETag", "").strip('"'),
            storage_class=row.get("StorageClass", "STANDARD")
        )

    def extract_folders(self, keys: List[str]) -> Set[str]:
        """Extract unique folder paths from object keys."""
        folders = set()
        for key in keys:
            # Get parent folders
            parts = key.rsplit("/", 1)
            if len(parts) > 1:
                folder = parts[0] + "/"
                folders.add(folder)
                # Add ancestor folders
                while "/" in folder[:-1]:
                    folder = folder.rsplit("/", 2)[0] + "/"
                    folders.add(folder)
        return folders
```

### Name Suggestion Algorithm

```python
def suggest_collection_name(folder_path: str) -> str:
    """Generate human-readable name from folder path.

    Examples:
        "2020/Milledgeville, GA/" → "2020 - Milledgeville GA"
        "2021/Wedding/Smith-Jones/" → "2021 - Wedding - Smith Jones"
        "archive/2019-06-15_concert/" → "Archive - 2019 06 15 Concert"
    """
    # Remove trailing slash
    path = folder_path.rstrip("/")

    # Split into parts
    parts = path.split("/")

    # Clean each part
    cleaned = []
    for part in parts:
        # Replace common separators with spaces
        name = part.replace("_", " ").replace("-", " ").replace(",", "")
        # Title case
        name = name.title()
        cleaned.append(name)

    # Join with " - "
    return " - ".join(cleaned)
```

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/connectors/{guid}/inventory/config` | PUT | Configure inventory settings |
| `/api/connectors/{guid}/inventory/import` | POST | Trigger inventory import |
| `/api/connectors/{guid}/inventory/folders` | GET | List discovered folders |
| `/api/connectors/{guid}/inventory/status` | GET | Get import status/progress |
| `/api/collections/from-inventory` | POST | Create Collection from inventory folder |

### New Files

```
backend/src/
├── services/
│   ├── inventory_service.py          # InventoryImportService
│   └── inventory_parser.py           # CSV/manifest parsing
├── schemas/
│   └── inventory.py                  # Inventory-related schemas
├── models/
│   └── inventory_folder.py           # InventoryFolder model
└── api/
    └── inventory.py                  # Inventory endpoints

frontend/src/
├── components/
│   └── inventory/
│       ├── InventoryConfigForm.tsx   # Inventory settings form
│       ├── FolderTree.tsx            # Hierarchical folder display
│       └── FolderToCollectionDialog.tsx  # Collection creation dialog
├── hooks/
│   └── useInventory.ts               # Inventory API hooks
└── pages/
    └── connectors/
        └── InventoryTab.tsx          # Connector inventory tab
```

---

## Implementation Plan

### Phase 1: Inventory Configuration and Import (Priority: P1)

**Estimated Tasks: ~35**

**Backend/Server (15 tasks):**
1. Create `InventoryConfig` schema for connector settings
2. Add inventory config to S3 connector credential schema
3. Create `InventoryFolder` model and migration
4. Create `InventoryImportTool` job type registration
5. Add "Import Inventory" endpoint that creates Job in queue
6. Add endpoint to receive import results from agent
7. Store discovered folders to database from agent results
8. Add inventory status/folders API endpoints
9. Unit tests for job creation and result handling
10. Integration tests with mock agent responses

**Agent (10 tasks):**
1. Implement `InventoryImportTool` in agent tool registry
2. Implement manifest.json fetching and parsing
3. Implement gzip decompression for data files
4. Implement CSV parsing with streaming for large files
5. Implement folder extraction algorithm
6. Report results back to server via job completion
7. Unit tests for parsing logic
8. Integration tests with mock S3 data

**Frontend (10 tasks):**
1. Add inventory configuration section to S3 connector form
2. Implement "Import Inventory" action button (creates job)
3. Display job progress via standard job status polling
4. Show discovered folder count on connector card
5. Component tests

**Checkpoint:** User triggers import, Job created in queue, agent executes and reports folders.

---

### Phase 2: Folder-to-Collection Mapping (Priority: P1)

**Estimated Tasks: ~25**

**Backend (10 tasks):**
1. Create collection-from-inventory endpoint
2. Implement name suggestion algorithm
3. Implement FileInfo population from inventory
4. Add `file_info` and related fields to Collection model
5. Update Collection service to use cached FileInfo
6. Tests for collection creation flow

**Frontend (15 tasks):**
1. Create `FolderTree` component with expand/collapse
2. Implement folder selection (single and multi)
3. Create `FolderToCollectionDialog` with name suggestions
4. Allow editing suggested names
5. Show folder metadata (object count, size)
6. Implement batch collection creation
7. Component tests

**Checkpoint:** User can browse folder tree, select folders, and create Collections with pre-populated FileInfo.

---

### Phase 3: FileInfo Integration with Tools (Priority: P1)

**Estimated Tasks: ~15**

**Backend/Agent (15 tasks):**
1. Update S3Adapter to check Collection.file_info first
2. Skip `list_objects` when FileInfo present and fresh
3. Add "Refresh from S3" endpoint
4. Track `file_info_updated_at` timestamp
5. Tools receive FileInfo without additional API calls
6. Update PhotoStats to use cached metadata
7. Update Photo Pairing to use cached metadata
8. Tests verifying zero API calls with cached FileInfo

**Checkpoint:** Running tools on inventory-created Collections makes zero S3 list API calls.

---

### Phase 4: Scheduled Import (Priority: P2)

**Estimated Tasks: ~15**

**Backend (12 tasks):**
1. Add `inventory_schedule` field to Connector configuration schema
2. Add schedule options: manual, daily, weekly
3. Create first scheduled Job when schedule is enabled
4. Implement chain scheduling: create next Job on completion
5. Calculate next `scheduled_at` from completion time + interval
6. Cancel pending scheduled jobs when schedule disabled
7. Prevent concurrent imports for same Connector
8. Ensure "Import Now" works independently of schedule
9. Store last import timestamp on Connector
10. Tests for chain scheduling logic

**Frontend (5 tasks):**
1. Schedule frequency selector in inventory configuration
2. Display next scheduled import time (from pending Job)
3. Display last import timestamp
4. "Import Now" button available regardless of schedule

**Checkpoint:** Complete import, verify next scheduled job auto-created with correct timestamp.

---

### Phase 5: Delta Detection (Priority: P3)

**Estimated Tasks: ~15**

**Backend (10 tasks):**
1. Store previous inventory snapshot reference
2. Implement delta comparison algorithm
3. Identify new, modified, deleted files
4. Store delta summary on import record
5. Tests for delta detection

**Frontend (5 tasks):**
1. Display delta summary after import
2. Highlight new files in folder tree
3. Show change statistics

**Checkpoint:** Users see what changed between inventory imports.

---

## Risks and Mitigation

### Risk 1: Large Inventory Files

- **Impact**: High - Memory exhaustion, timeout during import
- **Probability**: Medium (some users have millions of objects)
- **Mitigation**: Stream CSV parsing; process in chunks; checkpoint progress; agent-based execution with generous resources

### Risk 2: Inventory Not Configured in AWS

- **Impact**: Medium - Feature unusable without AWS-side setup
- **Probability**: High (many users won't have inventory configured)
- **Mitigation**: Clear documentation; setup wizard link; fallback to direct API listing

### Risk 3: Inventory Staleness

- **Impact**: Low - FileInfo may be out of date
- **Probability**: Medium (daily/weekly inventory has inherent lag)
- **Mitigation**: Display "last updated" timestamp; provide "Refresh from S3" option; warn on old data

### Risk 4: Large Compressed Inventory Files

- **Impact**: Low - Agent must decompress before parsing
- **Probability**: Certain (AWS inventory files are always gzip-compressed)
- **Mitigation**: Agent handles gzip decompression as part of the Connector tool; stream decompression to avoid memory spikes

### Risk 5: Different Inventory Formats

- **Impact**: Low - Only CSV supported initially
- **Probability**: Low (CSV is most common)
- **Mitigation**: Start with CSV; add ORC/Parquet support in Phase 5+

---

## Security Considerations

### Access Control

- Inventory bucket access uses existing S3 connector credentials
- No additional IAM permissions required if same bucket
- Cross-bucket inventory requires `s3:GetObject` on destination bucket

### Data Handling

- Inventory data processed in memory, not persisted as raw files
- Only extracted folder paths and FileInfo stored in database
- Sensitive object keys may be visible in logs (sanitize)

### Audit

- Log all inventory import operations
- Track who triggered import and when
- Record number of objects processed

---

## Open Questions

1. **Partial Import**: If import fails midway, should we keep partial results?
2. **Folder Depth Limit**: Should we limit folder tree depth to prevent UI performance issues?
3. **Multi-Tenant Inventory**: Can multiple teams share inventory from same bucket?
4. **Cost Display**: Should we show estimated API cost savings from using inventory?

---

## Success Metrics

### Adoption Metrics
- **M1**: 30% of S3 connectors have inventory configured within 3 months
- **M2**: 70% of inventory-configured connectors use scheduled imports

### Performance Metrics
- **M3**: 90% reduction in S3 list API calls for inventory-enabled collections
- **M4**: Import of 1M objects completes in under 5 minutes
- **M5**: Tool execution time reduced by 80% with cached FileInfo

### Reliability Metrics
- **M6**: 99% of inventory imports complete successfully
- **M7**: Zero data corruption from inventory parsing
- **M8**: FileInfo accuracy matches direct S3 API (same data)

---

## Dependencies

### External Dependencies
- AWS S3 Inventory configured by user in AWS Console
- S3 bucket permissions for reading inventory destination bucket

### Internal Dependencies
- Connector architecture (004-remote-photos-persistence)
- Agent-based job execution (021-distributed-agent-architecture)
- Collection model with JSONB support

### New Dependencies (to add to requirements.txt)
```
# No new dependencies - uses existing boto3
```

---

## Appendix

### A. AWS S3 Inventory Configuration Guide

To enable S3 Inventory for a bucket:

1. Open AWS S3 Console
2. Navigate to source bucket → Management → Inventory configurations
3. Create inventory configuration:
   - Name: `shuttersense-inventory` (or similar)
   - Destination bucket: Can be same or different bucket
   - Frequency: Daily or Weekly
   - Output format: CSV
   - Status: Enabled
4. Required fields for ShutterSense:
   - Size
   - Last modified date
   - ETag (optional but recommended)
   - Storage class (optional)

### B. Example Inventory CSV

```csv
"photo-bucket","2020/Milledgeville, GA/IMG_0001.CR3",12345678,"2020-05-15T10:30:00.000Z","abc123","STANDARD"
"photo-bucket","2020/Milledgeville, GA/IMG_0001.xmp",4567,"2020-05-15T10:30:01.000Z","def456","STANDARD"
"photo-bucket","2020/Milledgeville, GA/IMG_0002.CR3",13456789,"2020-05-15T10:35:00.000Z","ghi789","STANDARD"
```

### C. Folder Extraction Example

Given objects:
```
2020/Milledgeville, GA/IMG_0001.CR3
2020/Milledgeville, GA/IMG_0002.CR3
2020/Atlanta/Wedding/IMG_0001.CR3
2021/Nashville/IMG_0001.CR3
```

Extracted folders:
```
2020/
2020/Milledgeville, GA/
2020/Atlanta/
2020/Atlanta/Wedding/
2021/
2021/Nashville/
```

### D. GUID Prefix

| Entity | Prefix |
|--------|--------|
| InventoryFolder | `fld_` |

---

## Revision History

- **2026-01-22 (v1.2)**: Agent-first architecture and chain scheduling
  - User Story 2: Emphasized Import Inventory is agent-executed via JobQueue from day one
  - User Story 5: Defined chain scheduling (next job created on completion)
  - Updated Functional Requirements for agent-executed import (FR-010 to FR-018)
  - Updated Scheduling requirements for chain-based approach (FR-040 to FR-047)
  - Revised Phase 1 to split Backend/Agent tasks clearly
  - Revised Phase 4 for chain scheduling implementation

- **2026-01-22 (v1.1)**: Clarified gzip decompression handling
  - Removed gzip decompression from Non-Goals (AWS inventory is always compressed)
  - Agent handles decompression as part of Connector tool execution
  - Updated Risk 4 to reflect certain compression requirement
  - Removed resolved open question about gzip handling

- **2026-01-22 (v1.0)**: Initial draft
  - Defined S3 Inventory import requirements
  - Designed folder extraction and collection mapping workflow
  - Specified FileInfo caching mechanism
  - Created phased implementation plan
