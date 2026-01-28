# Quickstart: Cloud Storage Bucket Inventory Import

**Feature**: 107-bucket-inventory-import
**Date**: 2026-01-24

## Overview

This document provides a quick reference for implementing the bucket inventory import feature. It covers the key components, their interactions, and the implementation sequence.

---

## Implementation Sequence

### Phase 1: Core Infrastructure (~35 tasks)

```
Backend Models & Schemas
├── 1. Create InventoryFolder model with GuidMixin (fld_ prefix)
├── 2. Add inventory fields to Connector model
├── 3. Add FileInfo fields to Collection model
├── 4. Create database migration
├── 5. Create Pydantic schemas (S3InventoryConfig, GCSInventoryConfig, FileInfo, etc.)
└── 6. Unit tests for models and schemas

Backend Services
├── 7. Create InventoryService (job creation, folder storage, FileInfo updates)
├── 8. Extend ConnectorService (inventory config validation)
├── 9. Extend JobCoordinatorService (inventory job handling, chain scheduling)
└── 10. Unit tests for services

Backend API
├── 11. Create inventory routes (config, import, folders, status)
├── 12. Extend agent routes (folder report, FileInfo report, delta report)
├── 13. Integration tests for API endpoints
└── 14. OpenAPI documentation
```

### Phase 2: Agent Tool (~20 tasks)

```
Agent Infrastructure
├── 15. Register inventory_import tool in capabilities.py
├── 16. Add dispatch case in job_executor.py
└── 17. Create InventoryImportTool class

Inventory Parser
├── 18. Implement S3 manifest parser
├── 19. Implement GCS manifest parser
├── 20. Implement CSV parser with streaming
├── 21. Implement folder extraction algorithm
└── 22. Unit tests for parser

Pipeline Phases
├── 23. Phase A: Folder extraction and reporting
├── 24. Phase B: FileInfo population per collection
├── 25. Phase C: Delta detection and reporting
├── 26. Progress reporting integration
└── 27. Integration tests for pipeline
```

### Phase 3: Frontend (~25 tasks)

```
Types & Services
├── 28. Create inventory-api.ts types
├── 29. Create inventory.ts service
└── 30. Create useInventory.ts hook

Inventory Configuration
├── 31. Create InventoryConfigForm component
├── 32. Add inventory section to connector detail page
├── 33. Import button with job status display
└── 34. Component tests

Folder Selection
├── 35. Create FolderTreeNode component
├── 36. Create FolderTree component with virtualization
├── 37. Implement hierarchical selection constraints
├── 38. Implement search/filter
└── 39. Component tests

Collection Creation
├── 40. Create CreateCollectionsDialog (two-step wizard)
├── 41. Step 1: Folder selection UI
├── 42. Step 2: Review and configure UI
├── 43. Batch state action
└── 44. Integration with collections API
```

### Phase 4: Scheduling & Optimization (~20 tasks)

```
Scheduling
├── 45. Implement chain scheduling in job completion handler
├── 46. Add schedule options to inventory config form
├── 47. Display next scheduled import in UI
└── 48. Concurrent import prevention

Server-Side No-Change Detection
├── 49. Create input_state_hash_service.py
├── 50. Implement FileInfo hash computation
├── 51. Implement config hash computation
├── 52. Extend job claim for server-side detection
├── 53. Auto-complete "no_change" jobs
└── 54. Return next job after auto-completion

Polish
├── 55. Error handling and user feedback
├── 56. Loading states and progress indicators
├── 57. Empty states and edge cases
└── 58. End-to-end testing
```

---

## Key Files Reference

### Backend

| File | Purpose |
|------|---------|
| `backend/src/models/inventory_folder.py` | InventoryFolder SQLAlchemy model |
| `backend/src/schemas/inventory.py` | Pydantic schemas for inventory |
| `backend/src/services/inventory_service.py` | Business logic for inventory import |
| `backend/src/services/input_state_hash_service.py` | Server-side no-change detection via hashing |
| `backend/src/api/inventory/routes.py` | REST endpoints for inventory |
| `backend/src/api/agent/routes.py` | Agent endpoints (extend for inventory results) |

### Agent

| File | Purpose |
|------|---------|
| `agent/src/tools/inventory_import_tool.py` | Main tool implementation |
| `agent/src/analysis/inventory_parser.py` | Manifest and CSV parsing |
| `agent/src/capabilities.py` | Tool registration |
| `agent/src/job_executor.py` | Job dispatch |

### Frontend

| File | Purpose |
|------|---------|
| `frontend/src/contracts/api/inventory-api.ts` | TypeScript types |
| `frontend/src/services/inventory.ts` | API client |
| `frontend/src/hooks/useInventory.ts` | React hooks |
| `frontend/src/components/inventory/InventoryConfigForm.tsx` | Config form |
| `frontend/src/components/inventory/FolderTree.tsx` | Folder tree |
| `frontend/src/components/inventory/CreateCollectionsDialog.tsx` | Collection wizard |

---

## API Quick Reference

### User-Facing Endpoints

```
PUT  /api/connectors/{guid}/inventory/config    # Configure inventory
DEL  /api/connectors/{guid}/inventory/config    # Remove config
POST /api/connectors/{guid}/inventory/import    # Trigger import
GET  /api/connectors/{guid}/inventory/folders   # List folders
GET  /api/connectors/{guid}/inventory/status    # Get status
POST /api/collections/from-inventory            # Create collections
```

### Agent Endpoints

```
POST /api/agent/v1/jobs/{guid}/inventory/folders    # Report folders (Phase A)
POST /api/agent/v1/jobs/{guid}/inventory/file-info  # Report FileInfo (Phase B)
POST /api/agent/v1/jobs/{guid}/inventory/delta      # Report delta (Phase C)
```

---

## Data Flow

### Import Pipeline

```
User clicks "Import Inventory"
        │
        ▼
Server creates Job (tool: inventory_import)
        │
        ▼
Agent claims Job
        │
        ▼
┌───────────────────────────────────────┐
│ PHASE A: Folder Extraction            │
│ 1. Fetch manifest.json                │
│ 2. Download data files (decompress)   │
│ 3. Parse CSV, extract folders         │
│ 4. Report folders to server           │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│ PHASE B: FileInfo Population          │
│ 1. Get Collections for Connector      │
│ 2. Filter inventory by Collection     │
│ 3. Report FileInfo per Collection     │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│ PHASE C: Delta Detection              │
│ 1. Compare vs stored FileInfo         │
│ 2. Calculate new/modified/deleted     │
│ 3. Report delta per Collection        │
└───────────────────────────────────────┘
        │
        ▼
Job marked COMPLETED
(If scheduled: create next job)
```

### Collection Creation

```
User clicks "Create Collections"
        │
        ▼
┌───────────────────────────────────────┐
│ STEP 1: Folder Selection              │
│ - Show folder tree                    │
│ - Enforce hierarchy constraints       │
│ - Allow multi-select                  │
└───────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│ STEP 2: Review & Configure            │
│ - Show draft list                     │
│ - Edit names individually             │
│ - Set states individually or batch    │
└───────────────────────────────────────┘
        │
        ▼
POST /api/collections/from-inventory
        │
        ▼
Collections created with folder paths as locations
```

---

## Testing Strategy

### Unit Tests

| Component | Test Focus |
|-----------|------------|
| InventoryFolder model | GUID generation, validation, relationships |
| InventoryParser | Manifest parsing, CSV parsing, folder extraction |
| InventoryService | Job creation, folder storage, FileInfo updates |
| FolderTree component | Selection constraints, expand/collapse, search |

### Integration Tests

| Scenario | Test Focus |
|----------|------------|
| Full import pipeline | End-to-end with mock S3/GCS data |
| Collection creation | Batch creation with state assignment |
| Scheduled imports | Chain scheduling verification |
| Credential validation | Server vs agent credential paths |

### Performance Tests

| Metric | Target |
|--------|--------|
| 1M object import | < 10 minutes |
| 10k folder tree render | < 2 seconds |
| Agent memory usage | < 1GB |

---

## Common Patterns

### Hierarchical Selection Check

```typescript
function isSelectable(path: string, selectedPaths: Set<string>): boolean {
  for (const selected of selectedPaths) {
    if (selected.startsWith(path) || path.startsWith(selected)) {
      return false
    }
  }
  return true
}
```

### Name Suggestion

```typescript
function suggestName(path: string): string {
  return path
    .replace(/\/$/, '')           // Remove trailing slash
    .split('/')                    // Split into parts
    .map(decodeURIComponent)       // URL decode
    .map(p => p.replace(/[_-]/g, ' ').replace(/,/g, ''))  // Clean
    .map(p => p.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' '))  // Title case
    .join(' - ')                   // Join with separator
}
```

### FileInfo Check in Tools

```python
# In analysis tool
if collection.file_info and collection.file_info_source == "inventory":
    files = [FileInfo(**f) for f in collection.file_info]
else:
    files = adapter.list_files_with_metadata(collection.location)
```

---

## Error Handling

### Validation Errors

| Error | User Message |
|-------|--------------|
| Invalid bucket name | "Bucket name must be 3-63 characters" |
| Inaccessible inventory | "Cannot access inventory at configured path" |
| Missing required fields | "Inventory is missing required fields: Size, LastModified" |

### Import Errors

| Error | User Message |
|-------|--------------|
| No manifest found | "No inventory found at configured path. AWS/GCS may not have generated the first report yet." |
| Malformed CSV | "Some inventory rows could not be parsed. X rows skipped." |
| Agent unavailable | "No agent available to process import. Start an agent with access to this connector." |

### Selection Errors

| Error | User Message |
|-------|--------------|
| Overlapping selection | "Cannot select: this folder overlaps with an already-selected folder" |
| Already mapped | "This folder is already mapped to collection 'X'" |
| No state selected | "Please select a state for each collection" |
