# Data Model: Pipeline Visual Graph Editor

**Branch**: `209-pipeline-visual-editor` | **Date**: 2026-02-15

## Existing Entities (Modified)

### Pipeline

**Table**: `pipelines` (no schema change — JSONB is flexible)

The Pipeline entity is unchanged at the database level. The `nodes_json` JSONB column now stores an optional `position` field per node.

**nodes_json structure (extended)**:
```json
[
  {
    "id": "capture_1",
    "type": "capture",
    "properties": {
      "sample_filename": "AB3D0001",
      "filename_regex": "([A-Z0-9]{4})([0-9]{4})",
      "camera_id_group": "1"
    },
    "position": { "x": 250.0, "y": 50.0 }
  },
  {
    "id": "file_raw",
    "type": "file",
    "properties": {
      "extension": ".dng",
      "optional": false
    },
    "position": { "x": 150.0, "y": 200.0 }
  }
]
```

**Changes**:
- `position` field: Optional `{x: float, y: float}` object per node
- When absent (pre-existing pipelines): Frontend applies dagre auto-layout
- When present: Frontend uses saved coordinates
- Position is included in pipeline version history snapshots (stored in `pipeline_history.nodes_json`)

**Validation**:
- `position` field is ignored during pipeline structure validation
- `x` and `y` must be finite numbers when present

### Pipeline History

**Table**: `pipeline_history` (no schema change)

History snapshots capture `nodes_json` including position data when available. No change to the table schema — JSONB automatically includes any fields present in the source data.

### Analysis Result

**Table**: `analysis_results` (no schema change)

The `results_json` JSONB field for `pipeline_validation` tool results will be extended (Phase 3 prerequisite) to include **per-path image counts**. Per-node and per-edge statistics are derived from paths at query time.

**results_json structure (Phase 3 extension)**:
```json
{
  "total_images": 1500,
  "total_groups": 750,
  "status_counts": {
    "consistent": 1200,
    "consistent_with_warning": 50,
    "partial": 35,
    "inconsistent": 15
  },
  "by_termination": { ... },
  "path_stats": [
    {
      "path": ["capture_1", "file_raw", "process_hdr", "file_tiff", "termination_archive"],
      "image_count": 800
    },
    {
      "path": ["capture_1", "file_raw", "termination_archive"],
      "image_count": 650
    }
  ],
  "validation_results": [ ... ]
}
```

**Changes** (Phase 3 only):
- `path_stats`: Array of objects, each containing:
  - `path`: Ordered list of node IDs from Capture to Termination representing a distinct route through the pipeline
  - `image_count`: Number of image groups that traversed this exact path
- The analyzer uses **path caching** for performance: once a path is identified for one image group, subsequent groups are tested against known paths first (since 99% of images follow the same few paths)
- Per-edge and per-node counts are **derived at query time** by the flow-analytics endpoint (summing across all paths that include each edge/node), not stored directly
- Existing results without `path_stats` return 404 from the flow-analytics endpoint

**Terminology mapping**: The stored data uses `image_count` (counting image groups processed by the agent). The API response schemas use `record_count` (user-facing, domain-neutral term from the spec). The flow-analytics endpoint maps `image_count` → `record_count` when building the response. Both refer to the same quantity — the number of image groups that traversed a given path, edge, or node.

## New Schemas (Backend — Pydantic)

### NodePosition

```
NodePosition
├── x: float (required, canvas X coordinate)
└── y: float (required, canvas Y coordinate)
```

Added as an optional field on the existing `PipelineNode` schema.

### PipelineNode (Extended)

```
PipelineNode
├── id: str (1-100 chars, required)
├── type: NodeType (enum, required)
├── properties: Dict[str, Any] (default: {})
└── position: Optional[NodePosition] (default: None)
```

### Flow Analytics Response (Phase 3)

```
NodeFlowStats
├── node_id: str
├── record_count: int
└── percentage: float (% of total records from Capture node)

EdgeFlowStats
├── from_node: str
├── to_node: str
├── record_count: int
└── percentage: float (% of upstream node's records)

PipelineFlowAnalyticsResponse
├── pipeline_guid: str
├── pipeline_version: int
├── result_guid: str (analysis result used)
├── result_created_at: datetime
├── total_records: int (records at Capture node)
├── nodes: List[NodeFlowStats]
└── edges: List[EdgeFlowStats]
```

## New Types (Frontend — TypeScript)

### NodePosition

```typescript
interface NodePosition {
  x: number
  y: number
}
```

### PipelineNode (Extended)

```typescript
interface PipelineNode {
  id: string
  type: NodeType
  properties: Record<string, unknown>
  position?: NodePosition  // NEW: optional
}
```

### Flow Analytics Types (Phase 3)

```typescript
interface NodeFlowStats {
  node_id: string
  record_count: number
  percentage: number
}

interface EdgeFlowStats {
  from_node: string
  to_node: string
  record_count: number
  percentage: number
}

interface PipelineFlowAnalyticsResponse {
  pipeline_guid: string
  pipeline_version: number
  result_guid: string
  result_created_at: string
  total_records: number
  nodes: NodeFlowStats[]
  edges: EdgeFlowStats[]
}
```

## Entity Relationships

```
Pipeline (pip_)
├── has many → PipelineHistory (version snapshots)
├── has many → AnalysisResult (analysis runs)
├── has many → Collection (bound collections)
│
├── nodes_json [] → PipelineNode
│   ├── id (unique within pipeline)
│   ├── type (capture|file|process|pairing|branching|termination)
│   ├── properties (type-specific)
│   └── position? (x, y canvas coordinates) ← NEW
│
└── edges_json [] → PipelineEdge
    ├── from (source node ID)
    └── to (target node ID)

AnalysisResult (res_)
├── pipeline_id → Pipeline
├── pipeline_version (int)
├── results_json
│   ├── status_counts (existing)
│   ├── by_termination (existing)
│   └── path_stats (Phase 3) ← NEW
│       └── [{path: [node_ids], image_count: int}]
```

## State Transitions

No new entity state transitions are introduced. The existing Pipeline lifecycle remains unchanged:

```
Created (v1, inactive, may be valid/invalid)
  → Validated (is_valid=true/false)
  → Activated (is_active=true, requires is_valid=true)
  → Set Default (is_default=true, requires is_active=true)
  → Updated (version incremented, history saved, re-validated, auto-deactivated if invalid)
  → Deactivated (is_active=false, is_default=false)
  → Deleted (only if not active/default)
```

## Migration Impact

**No database migration required.** All changes are within existing JSONB columns:
- `pipelines.nodes_json`: Optional `position` field per node object
- `analysis_results.results_json`: Optional `node_stats` and `edge_stats` fields (Phase 3)
- Both are backward-compatible: absence of these fields is handled gracefully by the application layer
