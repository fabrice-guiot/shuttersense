# Implementation Plan: Pipeline Visual Graph Editor

**Branch**: `209-pipeline-visual-editor` | **Date**: 2026-02-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/209-pipeline-visual-editor/spec.md`
**Issue**: [#171 - Pipeline Visual Graph Editor (React Flow)](https://github.com/fabrice-guiot/shuttersense/issues/171)
**PRD**: [docs/prd/pipeline-visual-editor.md](../../docs/prd/pipeline-visual-editor.md)

## Summary

Replace the form-based pipeline editor with an interactive visual graph editor using React Flow (`@xyflow/react`). The feature is delivered in three phases: (1) read-only graph view with auto-layout and layout persistence, (2) interactive drag-and-drop editor with connection validation and undo/redo, and (3) flow analytics overlay showing record volume on edges derived from pipeline validation results. The backend requires a schema extension for node position data (no migration — JSONB is schema-flexible) and a new flow analytics endpoint. The existing pipeline data model (nodes_json, edges_json) maps directly to React Flow's node/edge graph format.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript 5.9.3 (frontend)
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0+, Pydantic v2 (backend); React 18.3.1, shadcn/ui, Tailwind CSS 4.x, Lucide React (frontend); **NEW**: `@xyflow/react`, `@dagrejs/dagre`
**Storage**: PostgreSQL JSONB (`nodes_json`, `edges_json`) — no DB migration required; position data is added as an optional field within existing JSONB objects
**Testing**: pytest (backend), vitest + React Testing Library (frontend)
**Target Platform**: Web application (desktop primary; mobile/tablet read-only view)
**Project Type**: Web application (backend + frontend)
**Performance Goals**: 50-60 FPS at 50 nodes with memoization; dagre auto-layout <100ms for 50 nodes
**Constraints**: Typical pipelines 5-15 nodes; max supported ~50 nodes; mobile screens read-only
**Scale/Scope**: ~20 new/modified files, 3 phases of delivery

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Agent-Only Tool Execution**: N/A — this feature is a UI/API enhancement, not a tool. Pipeline validation (which generates analytics data) continues to execute via agents only.
- [x] **Testing & Quality**: Tests planned for all phases — custom node components, edge validation logic, dagre layout integration, graph state serialization, undo/redo state, backend schema validation, flow analytics endpoint.
- [x] **User-Centric Design**:
  - Not an analysis tool — no HTML report generation required.
  - Error messages: Validation errors shown visually on nodes (red border, error icon). Contextual validation hints guide the user.
  - Simplicity: Uses React Flow (MIT, 35K+ stars, 2.7M weekly downloads) rather than a custom graph rendering solution. YAGNI observed — no sub-pipelines, real-time collaboration, or animated replay.
  - Structured logging: N/A for frontend; backend endpoint uses existing FastAPI logging.
- [x] **Shared Infrastructure**: N/A — web application feature, no PhotoAdminConfig or CLI. Uses existing pipeline schemas and YAML import/export.
- [x] **Simplicity**: React Flow is the simplest approach — it provides custom React node/edge components, built-in accessibility, dagre layout integration, and handles all pan/zoom/interaction out of the box. Custom canvas rendering would be vastly more complex.
- [x] **GUIDs**: Pipeline already uses `pip_` prefix GUIDs. New flow-analytics endpoint uses pipeline GUID in path. No new entities requiring GUID prefixes.
- [x] **Multi-Tenancy & Authentication**: All existing pipeline endpoints enforce tenant isolation via `TenantContext`. The new flow-analytics endpoint will follow the same pattern with `get_tenant_context` dependency.
- [x] **Audit Trail**: Pipeline model already has `AuditMixin`. No new database entities introduced. Pipeline list already displays `AuditTrailPopover`.
- [x] **Agent-Only Execution**: Flow analytics data comes from pipeline_validation results executed by agents. The new endpoint reads existing result data — no server-side execution.
- [x] **Single Title Pattern**: Pipeline pages already follow TopHeader pattern. PipelineEditorPage sets dynamic titles based on mode.
- [x] **TopHeader KPI Display**: PipelinesPage already implements KPI stats (Total Pipelines, Active, Default).

**Violations/Exceptions**: None. All principles satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/209-pipeline-visual-editor/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── backend-api.md   # New/modified API endpoints
│   └── frontend-api.md  # New/modified TypeScript contracts
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── schemas/
│   │   └── pipelines.py          # MODIFY: Add NodePosition, flow analytics schemas
│   ├── services/
│   │   └── pipeline_service.py   # MODIFY: Add get_flow_analytics() method
│   └── api/
│       └── pipelines.py          # MODIFY: Add flow-analytics endpoint
└── tests/
    └── unit/
        ├── test_pipeline_schemas.py     # ADD: NodePosition schema tests
        └── test_flow_analytics.py       # ADD: Flow analytics endpoint tests

frontend/
├── src/
│   ├── components/
│   │   └── pipelines/
│   │       └── graph/                   # ADD: New directory
│   │           ├── PipelineGraphView.tsx     # Read-only graph canvas
│   │           ├── PipelineGraphEditor.tsx   # Interactive editor canvas
│   │           ├── NodePalette.tsx           # Drag-to-add node palette
│   │           ├── PropertyPanel.tsx         # Node/edge property panel
│   │           ├── EditorToolbar.tsx         # Zoom, undo/redo, layout controls
│   │           ├── AnalyticsOverlay.tsx      # Flow analytics toggle/legend
│   │           ├── nodes/                    # Custom node components
│   │           │   ├── CaptureNode.tsx
│   │           │   ├── FileNode.tsx
│   │           │   ├── ProcessNode.tsx
│   │           │   ├── PairingNode.tsx
│   │           │   ├── BranchingNode.tsx
│   │           │   ├── TerminationNode.tsx
│   │           │   └── index.ts
│   │           ├── edges/                    # Custom edge components
│   │           │   ├── PipelineEdge.tsx
│   │           │   ├── AnalyticsEdge.tsx
│   │           │   └── index.ts
│   │           └── utils/                    # Graph utilities
│   │               ├── graph-transforms.ts   # API ↔ React Flow format conversion
│   │               ├── dagre-layout.ts       # Auto-layout with dagre
│   │               ├── connection-rules.ts   # Edge validation rules
│   │               └── node-defaults.ts      # Default ID generation, node config
│   ├── contracts/
│   │   └── api/
│   │       └── pipelines-api.ts         # MODIFY: Add position, flow analytics types
│   ├── hooks/
│   │   ├── usePipelineGraph.ts          # ADD: React Flow state + undo/redo
│   │   ├── usePipelineAnalytics.ts      # ADD: Flow analytics data fetching
│   │   └── usePipelines.ts             # EXISTING: No changes expected
│   ├── pages/
│   │   ├── PipelineEditorPage.tsx       # REWRITE: Use graph view/editor
│   │   └── PipelinesPage.tsx            # MODIFY: Remove beta banner
│   └── services/
│       └── pipelines.ts                 # MODIFY: Add getFlowAnalytics()
└── tests/
    └── unit/
        └── components/
            └── pipelines/
                └── graph/                    # ADD: Graph component tests
                    ├── graph-transforms.test.ts
                    ├── dagre-layout.test.ts
                    ├── connection-rules.test.ts
                    └── node-components.test.ts
```

**Structure Decision**: Web application structure with backend API extension and significant frontend rewrite. The graph components are organized under `components/pipelines/graph/` to colocate all React Flow related code while keeping it namespaced within the existing pipeline domain.

## Complexity Tracking

No violations to document. All complexity is justified by the feature requirements and uses well-maintained third-party libraries rather than custom solutions.
