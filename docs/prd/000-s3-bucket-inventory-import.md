# PRD: Import S3 Collections from S3 Bucket Inventory File

**Issue**: #40
**Status**: Draft
**Created**: 2026-01-22
**Last Updated**: 2026-01-22 (v1.3)
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

**Architecture Note:** Per project constitution, all complex analysis and tool execution MUST run agent-side to avoid overloading the web server. The "Import Inventory" tool executes a sequential pipeline:

1. **Phase A (US2)**: Fetch manifest, download/decompress CSV, extract folders
2. **Phase B (US4)**: For each Collection using this Connector, populate FileInfo from inventory
3. **Phase C (US6)**: For each Collection, detect delta from previous inventory

The agent retains the parsed inventory data locally throughout the pipeline. On first run (before any Collections are mapped via US3), Phases B and C have no Collections to process and are skipped. Once Collections exist, Phases B and C iterate over each Collection bound to this Connector.

**Acceptance Criteria:**
- "Import Inventory" action available on S3 Connector
- Action creates a Job in the JobQueue (not executed server-side)
- Agent claims and executes the import job
- Agent fetches latest manifest.json from inventory location
- Agent downloads, decompresses (gzip), and parses CSV data files
- Agent retains parsed inventory in local storage for pipeline phases
- Agent extracts unique folder paths (entries ending with "/" or parent paths)
- Agent reports folder results back to server; folders stored on Connector record
- Agent proceeds to Phase B (US4) and Phase C (US6) sequentially
- UI shows job progress via standard job status polling
- Full pipeline completes within 10 minutes for 1 million objects

**Independent Test:** Trigger import, verify Job created in queue, agent executes full pipeline and reports folders

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

**As** a user with Collections mapped to inventory folders
**I want to** have file metadata automatically updated from inventory
**So that** tools can run without fetching metadata from S3

**Architecture Note:** This is Phase B of the Import Inventory pipeline (see US2). The agent executes this phase after folder extraction, using the locally-retained inventory data. For each Collection using this Connector, the agent filters inventory entries matching the Collection's folder path and reports FileInfo to the server.

**Acceptance Criteria:**
- Agent iterates over all Collections bound to this Connector
- For each Collection, agent filters inventory data by Collection's folder path
- Agent extracts FileInfo: key, size, last_modified, etag, storage_class
- Agent reports FileInfo array to server via collection update endpoint
- Server stores FileInfo on Collection record with `file_info_source: "inventory"`
- Server updates `file_info_updated_at` timestamp
- If no Collections exist yet, Phase B is skipped (no-op)
- Tools check for cached FileInfo before calling S3 list APIs
- "Last updated from inventory" timestamp visible in UI
- Option to refresh FileInfo from live S3 data if needed (separate action)

**Independent Test:** Create Collection from folder, trigger import, verify FileInfo populated without S3 list API calls

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

**Architecture Note:** This is Phase C of the Import Inventory pipeline (see US2). The agent executes this phase after FileInfo population, comparing current inventory data against each Collection's previously stored FileInfo. This requires no additional S3 API calls since both datasets are already available (current from Phase A, previous from Collection record).

**Acceptance Criteria:**
- Agent iterates over all Collections bound to this Connector
- For each Collection, agent compares current inventory entries against stored FileInfo
- Agent detects: new files (in current, not in previous), modified files (different ETag/size), deleted files (in previous, not in current)
- Agent reports delta summary to server: counts and optionally file lists
- Server stores delta on Collection or ImportSession record
- If no Collections exist yet, Phase C is skipped (no-op)
- If Collection has no previous FileInfo (first import after mapping), all files reported as "new"
- Delta summary visible in UI after import completes
- Summary statistics: X new, Y modified, Z deleted per Collection

**Independent Test:** Map Collection, run import (baseline), add/modify/delete files in S3, run next import, verify delta correctly detected

---

## Requirements

### Functional Requirements

#### Inventory Configuration

- **FR-001**: Add `inventory_config` field to S3 Connector configuration schema
- **FR-002**: Inventory config includes: destination_bucket, source_bucket, config_name
- **FR-003**: Validate inventory path accessibility during connector test
- **FR-004**: Store inventory settings encrypted with other credentials

#### Inventory Import Pipeline (Agent-Executed)

The Import Inventory tool executes three sequential phases in a single job:

**Phase A: Folder Extraction (US2)**
- **FR-010**: "Import Inventory" action creates a Job in JobQueue (never executes server-side)
- **FR-011**: Create `InventoryImportTool` as an agent-executable tool type
- **FR-012**: Agent fetches and parses `manifest.json` from inventory location
- **FR-013**: Agent downloads and decompresses (gzip) data files referenced in manifest
- **FR-014**: Agent parses CSV format with configurable field mapping
- **FR-015**: Agent retains parsed inventory data in local storage for pipeline duration
- **FR-016**: Agent extracts unique folder paths from object keys
- **FR-017**: Agent reports folder results to server; server stores as `InventoryFolder` records

**Phase B: FileInfo Population (US4)**
- **FR-020**: Agent queries server for all Collections bound to this Connector
- **FR-021**: For each Collection, agent filters inventory data by Collection's folder path
- **FR-022**: Agent extracts FileInfo: key, size, last_modified, etag, storage_class
- **FR-023**: Agent reports FileInfo array to server per Collection
- **FR-024**: Server stores FileInfo on Collection with `file_info_source: "inventory"`
- **FR-025**: Server updates `file_info_updated_at` timestamp
- **FR-026**: If no Collections exist, Phase B is skipped (no-op)

**Phase C: Delta Detection (US6)**
- **FR-030**: Agent compares current inventory data against each Collection's stored FileInfo
- **FR-031**: Agent detects: new files, modified files (ETag/size changed), deleted files
- **FR-032**: Agent reports delta summary per Collection: counts of new/modified/deleted
- **FR-033**: Server stores delta on Collection or ImportSession record
- **FR-034**: If no Collections exist or no previous FileInfo, Phase C is skipped or reports all as new
- **FR-035**: Support streaming/chunked processing for large inventories

#### Folder-to-Collection Mapping (Server-Side)

- **FR-040**: Create UI component for folder tree visualization
- **FR-041**: Implement intelligent name suggestion algorithm
- **FR-042**: Name suggestion rules: replace "/" with " - ", strip trailing slash, title case
- **FR-043**: Create Collection linked to Connector with folder path as location
- **FR-044**: Support batch Collection creation from multiple folders

#### FileInfo Usage

- **FR-050**: FileInfo schema: key, size (bytes), last_modified (ISO8601), etag, storage_class
- **FR-051**: Tools MUST check Collection.file_info before calling S3 list API
- **FR-052**: Provide "Refresh from S3" action to update FileInfo via direct API (separate job)
- **FR-053**: Track `file_info_updated_at` and `file_info_source` on Collection

#### Scheduling (Chain-Based)

- **FR-060**: Add `inventory_schedule` field to Connector configuration
- **FR-061**: Schedule options: manual only, daily, weekly (no cron - simple intervals)
- **FR-062**: When schedule enabled, create first scheduled Job with future `scheduled_at`
- **FR-063**: Upon job completion (all phases), automatically create next scheduled Job
- **FR-064**: Next job's `scheduled_at` = completion time + configured interval
- **FR-065**: Prevent concurrent imports for same Connector
- **FR-066**: Disabling schedule cancels pending scheduled jobs
- **FR-067**: "Import Now" creates immediate job independent of schedule

### Non-Functional Requirements

#### Performance

- **NFR-001**: Full pipeline (Phases A+B+C) completes within 10 minutes for 1 million objects
- **NFR-002**: Manifest fetch and parse within 10 seconds
- **NFR-003**: Folder tree render with 10,000 folders within 2 seconds
- **NFR-004**: Agent memory usage under 1GB during pipeline execution

#### Reliability

- **NFR-010**: Resume interrupted imports from checkpoint (per phase)
- **NFR-011**: Handle malformed inventory rows gracefully (skip, log)
- **NFR-012**: Retry transient S3 errors with exponential backoff
- **NFR-013**: Validate manifest schema before processing
- **NFR-014**: Phase B/C failures do not invalidate Phase A results (folders still stored)

#### Security

- **NFR-020**: Inventory bucket access via existing Connector credentials
- **NFR-021**: Agent retains inventory data only for pipeline duration, deletes after completion
- **NFR-022**: Audit log for import operations (all phases)

#### Testing

- **NFR-030**: Unit tests for CSV parsing logic (>90% coverage)
- **NFR-031**: Integration tests with mock S3 inventory data
- **NFR-032**: Performance tests with 1M+ object inventory

---

## Technical Approach

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    S3 Inventory Import Pipeline (Single Job)             │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│   User   │     │   Server     │     │   Agent     │     │     S3       │
│   (UI)   │     │   (API)      │     │  (Worker)   │     │ (Inventory)  │
└────┬─────┘     └──────┬───────┘     └──────┬──────┘     └──────┬───────┘
     │                  │                    │                   │
     │ 1. Trigger Import│                    │                   │
     │─────────────────►│                    │                   │
     │                  │ 2. Create Job      │                   │
     │                  │───────────────────►│                   │
     │                  │                    │                   │
     │                  │         ┌──────────┴──────────┐        │
     │                  │         │  PHASE A: Extract   │        │
     │                  │         └──────────┬──────────┘        │
     │                  │                    │ 3. Fetch manifest │
     │                  │                    │──────────────────►│
     │                  │                    │◄──────────────────│
     │                  │                    │ 4. Download CSV   │
     │                  │                    │──────────────────►│
     │                  │                    │◄──────────────────│
     │                  │                    │ 5. Parse & store locally
     │                  │ 6. Report folders  │                   │
     │                  │◄───────────────────│                   │
     │                  │                    │                   │
     │                  │         ┌──────────┴──────────┐        │
     │                  │         │ PHASE B: FileInfo   │        │
     │                  │         └──────────┬──────────┘        │
     │                  │ 7. Get Collections │                   │
     │                  │◄───────────────────│                   │
     │                  │───────────────────►│                   │
     │                  │                    │ 8. Filter inventory per Collection
     │                  │ 9. Report FileInfo │                   │
     │                  │◄───────────────────│ (per Collection)  │
     │                  │                    │                   │
     │                  │         ┌──────────┴──────────┐        │
     │                  │         │  PHASE C: Delta     │        │
     │                  │         └──────────┬──────────┘        │
     │                  │                    │ 10. Compare vs stored FileInfo
     │                  │ 11. Report delta   │                   │
     │                  │◄───────────────────│ (per Collection)  │
     │                  │                    │                   │
     │                  │                    │ 12. Cleanup local storage
     │                  │ 13. Job complete   │                   │
     │                  │◄───────────────────│                   │
     │ 14. Display results                   │                   │
     │◄─────────────────│                    │                   │
```

**First Run (No Collections):** Phases B and C are no-ops since no Collections exist yet.

**Subsequent Runs:** All three phases execute, updating FileInfo and detecting changes for each mapped Collection.

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

### Phase 1: Full Import Pipeline - Agent Implementation (Priority: P1)

**Estimated Tasks: ~45**

The Import Inventory tool executes three phases (A, B, C) sequentially in a single agent job. This phase implements the complete pipeline.

**Backend/Server (18 tasks):**
1. Create `InventoryConfig` schema for connector settings
2. Add inventory config to S3 connector credential schema
3. Create `InventoryFolder` model and migration
4. Add `file_info`, `file_info_updated_at`, `file_info_source` fields to Collection model
5. Create `InventoryImportTool` job type registration
6. Add "Import Inventory" endpoint that creates Job in queue
7. Add endpoint to receive Phase A results (folders) from agent
8. Add endpoint to receive Phase B results (FileInfo per Collection) from agent
9. Add endpoint to receive Phase C results (delta per Collection) from agent
10. Store discovered folders as `InventoryFolder` records
11. Store FileInfo on Collection records from agent results
12. Store delta summary on Collection or ImportSession record
13. Add API to list Collections bound to a Connector (for agent query)
14. Add inventory status/folders API endpoints
15. Unit tests for job creation and result handling
16. Integration tests with mock agent responses

**Agent (20 tasks):**
1. Implement `InventoryImportTool` in agent tool registry
2. Implement manifest.json fetching and parsing
3. Implement gzip decompression for data files
4. Implement CSV parsing with streaming for large files
5. Implement local storage of parsed inventory data for pipeline duration
6. **Phase A**: Implement folder extraction algorithm
7. **Phase A**: Report folder results to server
8. **Phase B**: Query server for Collections bound to this Connector
9. **Phase B**: Filter inventory data by each Collection's folder path
10. **Phase B**: Extract FileInfo per Collection
11. **Phase B**: Report FileInfo results to server per Collection
12. **Phase B**: Skip if no Collections exist
13. **Phase C**: Compare current inventory against stored FileInfo per Collection
14. **Phase C**: Detect new, modified, deleted files
15. **Phase C**: Report delta summary to server per Collection
16. **Phase C**: Skip if no Collections or no previous FileInfo
17. Clean up local inventory storage after pipeline completion
18. Unit tests for parsing and extraction logic
19. Unit tests for FileInfo population and delta detection
20. Integration tests with mock S3 data

**Frontend (10 tasks):**
1. Add inventory configuration section to S3 connector form
2. Implement "Import Inventory" action button (creates job)
3. Display job progress via standard job status polling (shows current phase)
4. Show discovered folder count on connector card
5. Show last import timestamp
6. Component tests

**Checkpoint:** User triggers import, agent executes full pipeline (A→B→C), folders discovered, FileInfo populated on existing Collections, delta detected.

---

### Phase 2: Folder-to-Collection Mapping UI (Priority: P1)

**Estimated Tasks: ~20**

**Backend (5 tasks):**
1. Create collection-from-inventory endpoint (links Collection to Connector + folder path)
2. Implement name suggestion algorithm
3. Support batch Collection creation from multiple folders
4. Tests for collection creation flow

**Frontend (15 tasks):**
1. Create `FolderTree` component with expand/collapse
2. Implement folder selection (single and multi)
3. Create `FolderToCollectionDialog` with name suggestions
4. Allow editing suggested names
5. Show folder metadata (object count, size from inventory)
6. Implement batch collection creation
7. Show which folders are already mapped to Collections
8. Component tests

**Checkpoint:** User can browse folder tree, select folders, and create Collections. Next import will populate FileInfo for new Collections.

---

### Phase 3: Tool Integration with Cached FileInfo (Priority: P1)

**Estimated Tasks: ~15**

**Backend/Agent (15 tasks):**
1. Update S3Adapter to check Collection.file_info first
2. Skip `list_objects` when FileInfo present and fresh
3. Add "Refresh from S3" action (creates separate job to fetch live data)
4. Tools receive FileInfo without additional S3 API calls
5. Update PhotoStats to use cached metadata
6. Update Photo Pairing to use cached metadata
7. Show `file_info_source` and `file_info_updated_at` in Collection details
8. Tests verifying zero S3 list API calls with cached FileInfo

**Checkpoint:** Running tools on Collections with inventory-sourced FileInfo makes zero S3 list API calls.

---

### Phase 4: Scheduled Import (Priority: P2)

**Estimated Tasks: ~17**

**Backend (12 tasks):**
1. Add `inventory_schedule` field to Connector configuration schema
2. Add schedule options: manual, daily, weekly
3. Create first scheduled Job when schedule is enabled
4. Implement chain scheduling: create next Job on pipeline completion
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

### Phase 5: Delta UI and Notifications (Priority: P3)

**Estimated Tasks: ~12**

Delta detection runs in Phase 1's pipeline; this phase adds UI visibility.

**Backend (4 tasks):**
1. Add endpoint to retrieve delta history per Collection
2. Store delta details (file lists) if configured
3. Optional: webhook/notification on significant changes
4. Tests for delta retrieval

**Frontend (8 tasks):**
1. Display delta summary on Collection card after import
2. Show change statistics: X new, Y modified, Z deleted
3. Delta detail view listing changed files
4. Filter by change type (new/modified/deleted)
5. Link to file details where applicable
6. Component tests

**Checkpoint:** Users see what changed between inventory imports per Collection.

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

- **2026-01-22 (v1.3)**: Sequential pipeline architecture (US2 → US4 → US6)
  - Import Inventory tool now executes three phases in sequence: A (folder extraction), B (FileInfo population), C (delta detection)
  - US4 (FileInfo Population): Now agent-executed as Phase B, iterates over Collections bound to Connector
  - US6 (Delta Detection): Now agent-executed as Phase C, compares current inventory vs stored FileInfo
  - Agent retains parsed inventory locally for pipeline duration, cleans up after completion
  - First run skips Phases B/C when no Collections exist; subsequent runs process all mapped Collections
  - Reorganized Functional Requirements into pipeline phases (FR-010 to FR-035)
  - Reorganized Implementation Plan: Phase 1 now includes full pipeline, Phase 5 for Delta UI only
  - Updated Architecture Overview diagram to show three-phase pipeline flow

- **2026-01-22 (v1.2)**: Agent-first architecture and chain scheduling
  - User Story 2: Emphasized Import Inventory is agent-executed via JobQueue from day one
  - User Story 5: Defined chain scheduling (next job created on completion)
  - Updated Functional Requirements for agent-executed import
  - Updated Scheduling requirements for chain-based approach
  - Revised Implementation Plan to split Backend/Agent tasks clearly

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
