# Implementation Plan: Cloud Storage Bucket Inventory Import

**Branch**: `107-bucket-inventory-import` | **Date**: 2026-01-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/107-bucket-inventory-import/spec.md`
**Related PRD**: `docs/prd/107-bucket-inventory-import.md`

## Summary

This feature enables ShutterSense to import cloud storage collection metadata from automated inventory reports (AWS S3 Inventory, Google Cloud Storage Insights) instead of making expensive API calls. The implementation adds:

1. **Inventory Configuration** on S3/GCS Connectors (with dual validation path for server vs agent credentials)
2. **InventoryImportTool** as a new agent-executable tool with 3-phase pipeline (Folder Extraction → FileInfo Population → Delta Detection)
3. **InventoryFolder** entity to store discovered folders with GUID prefix `fld_`
4. **Collection FileInfo caching** via JSONB on Collection model
5. **Two-step folder-to-collection mapping UI** with hierarchical selection constraints and mandatory state assignment
6. **Chain-based scheduling** for automated periodic imports

## Technical Context

**Language/Version**: Python 3.10+ (Backend/Agent), TypeScript 5.9.3 (Frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0+, Pydantic v2, boto3, google-cloud-storage, React 18.3.1, shadcn/ui, Tailwind CSS 4.x
**Storage**: PostgreSQL 12+ (JSONB columns for FileInfo, InventoryConfig embedded in credentials)
**Testing**: pytest (backend/agent), Vitest (frontend)
**Target Platform**: Linux server (backend), user machines (agent), modern browsers (frontend)
**Project Type**: Web application (backend + frontend + agent)
**Performance Goals**:
- Full import pipeline completes in <10 minutes for 1M objects (SC-002)
- Manifest fetch/parse <10 seconds (SC-003)
- Folder tree renders 10k folders in <2 seconds (SC-004)
**Constraints**:
- Agent memory <1GB for inventories up to 5M objects (SC-005)
- Streaming/chunked processing for large inventories
- Zero cloud list API calls with cached FileInfo (SC-007)
**Scale/Scope**: Buckets with millions of objects, 10k+ folders in tree UI

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with `.specify/memory/constitution.md`:

- [x] **Independent CLI Tools**: N/A - This is a web application feature with agent-side tool. The InventoryImportTool follows existing tool patterns in `agent/src/analysis/`.
- [x] **Testing & Quality**: Tests planned for backend (pytest), agent (pytest), frontend (Vitest). Coverage targets aligned with existing patterns.
- [x] **User-Centric Design**:
  - For analysis tools: This imports data rather than generates reports; Collections with inventory-sourced FileInfo will generate reports via existing tools.
  - Error messages: Clear validation errors for inventory configuration, path accessibility, missing required fields.
  - YAGNI: Implementation follows existing patterns (Connector config extension, new tool type, Collection extensions).
  - Structured logging: All phases will log progress for observability.
- [x] **Global Unique Identifiers (GUIDs)**: New InventoryFolder entity uses `fld_` prefix per spec. All API responses use GUIDs.
- [x] **Multi-Tenancy and Authentication**: All endpoints use TenantContext for team isolation. InventoryFolder scoped via Connector's team_id.
- [x] **Agent-Only Execution**: All import processing runs on agents via JobQueue. Server acts as coordinator only.
- [x] **Shared Infrastructure**: Uses existing Connector credential encryption, JobQueue infrastructure, Collection model extensions.
- [x] **Simplicity**: Follows existing patterns - no new frameworks, reuses storage adapters, extends existing models.
- [x] **Single Title Pattern**: UI components follow TopHeader KPI pattern, no inline h1 elements.

**Violations/Exceptions**: None - all principles satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/107-bucket-inventory-import/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (API schemas)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── models/
│   │   ├── inventory_folder.py          # NEW: InventoryFolder model
│   │   └── collection.py                # EXTEND: file_info, file_info_updated_at, file_info_source
│   ├── schemas/
│   │   ├── inventory.py                 # NEW: S3InventoryConfig, GCSInventoryConfig, InventoryFolder schemas
│   │   └── collection.py                # EXTEND: FileInfo schema, Collection response with file_info
│   ├── services/
│   │   ├── inventory_service.py         # NEW: Inventory import job creation, folder storage, FileInfo updates
│   │   ├── input_state_hash_service.py  # NEW: Server-side no-change detection via input state hashing
│   │   └── connector_service.py         # EXTEND: Inventory config validation (server-side for server credentials)
│   └── api/
│       ├── inventory/                   # NEW: Inventory endpoints
│       │   ├── routes.py               # Inventory config, import trigger, folders list, status
│       │   └── schemas.py              # Request/response models
│       └── agent/
│           ├── routes.py               # EXTEND: Inventory result endpoints
│           └── schemas.py              # EXTEND: Inventory result schemas
└── tests/
    ├── unit/
    │   └── services/
    │       ├── test_inventory_service.py
    │       └── test_input_state_hash_service.py
    ├── integration/
    │   └── api/
    │       ├── test_inventory_api.py
    │       └── test_nochange_detection.py
    └── performance/
        └── test_nochange_performance.py

agent/
├── src/
│   ├── tools/
│   │   └── inventory_import_tool.py    # NEW: InventoryImportTool (3-phase pipeline)
│   ├── analysis/
│   │   └── inventory_parser.py         # NEW: Manifest parsing, CSV extraction, folder extraction
│   ├── capabilities.py                 # EXTEND: Register inventory_import tool
│   └── job_executor.py                 # EXTEND: Dispatch to inventory_import_tool
└── tests/
    ├── unit/
    │   └── test_inventory_parser.py
    └── integration/
        └── test_inventory_import_tool.py

frontend/
├── src/
│   ├── components/
│   │   └── inventory/                   # NEW: Inventory UI components
│   │       ├── InventoryConfigForm.tsx  # Inventory settings form (destination bucket, config name, schedule)
│   │       ├── FolderTree.tsx          # Hierarchical folder tree with selection constraints
│   │       ├── FolderTreeNode.tsx      # Individual tree node with expand/collapse
│   │       └── CreateCollectionsDialog.tsx  # Two-step wizard (selection → review)
│   ├── hooks/
│   │   └── useInventory.ts             # NEW: Inventory API hooks
│   ├── services/
│   │   └── inventory.ts                # NEW: Inventory API calls
│   └── contracts/
│       └── api/
│           └── inventory-api.ts        # NEW: Inventory type definitions
└── tests/
    └── components/
        └── inventory/
            └── FolderTree.test.tsx
```

**Structure Decision**: Web application with backend, frontend, and agent components. Follows existing patterns established by Connector, Collection, and Job implementations.

## Complexity Tracking

> **No violations - all principles satisfied**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
