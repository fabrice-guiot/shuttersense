# Research: Pipeline Visual Graph Editor

**Branch**: `209-pipeline-visual-editor` | **Date**: 2026-02-15

## R-001: React Flow Integration with Existing Data Model

**Decision**: The existing `nodes_json` and `edges_json` JSONB format can be mapped to React Flow's node/edge format with a lightweight transformation layer.

**Rationale**:
- ShutterSense `PipelineNode`: `{id, type, properties}` — React Flow `Node`: `{id, type, position, data}`. The `properties` field maps to `data`, and `position` is a new optional field.
- ShutterSense `PipelineEdge`: `{from, to}` — React Flow `Edge`: `{id, source, target, type}`. The `from`/`to` fields map to `source`/`target`, and an `id` is generated as `${from}-${to}`.
- Position data (`{x, y}`) can be stored directly in `nodes_json` objects since JSONB is schema-flexible — no migration required.
- A `graph-transforms.ts` utility handles bidirectional conversion between API format and React Flow format.

**Alternatives considered**:
- Storing positions in a separate database column — rejected because it would require a migration and would split graph data across two columns.
- Using React Flow's internal storage format in the database — rejected because it couples the database to a specific library version.

## R-002: Dagre Layout Algorithm for Auto-Layout (Cyclic Graph Handling)

**Decision**: Use `@dagrejs/dagre` for automatic top-to-bottom layout when no saved positions exist. Pipeline graphs are **not acyclic** — they can contain cycles (back-edges). The layout algorithm handles this by computing an acyclic projection first.

**Rationale**:
- Dagre is purpose-built for directed graph layout, specifically DAGs.
- Official React Flow dagre example available at reactflow.dev.
- Configuration: `rankdir: 'TB'` (top-to-bottom), `nodesep: 80` (horizontal spacing), `ranksep: 100` (vertical spacing).
- Synchronous execution completes in <100ms for pipelines under 50 nodes.
- MIT license compatible with AGPL-3.0.

**Cyclic graph strategy** (important — pipelines are NOT acyclic):
1. **Compute acyclic projection**: Before running dagre, perform a forward traversal from the Capture node. Any edge whose target has already been visited in the current traversal is a "back-edge" (introduces a cycle). Collect these back-edges and exclude them from the dagre input.
2. **Run dagre on acyclic projection**: Dagre lays out nodes top-to-bottom using only the forward edges. This produces clean Capture→Termination flow positioning.
3. **Draw back-edges without moving nodes**: After layout, add the excluded back-edges to React Flow. These edges connect nodes that are already positioned — React Flow's smoothstep/bezier routing handles drawing them "as best as possible" without altering node positions.
4. **User may adjust**: The auto-layout positions may not produce ideal visual results for back-edges. This is the primary reason users would manually reposition nodes and save the layout — so that cycle-introducing edges display more clearly.

**Alternatives considered**:
- `elkjs` — More powerful (supports nested groups, ports, and has native cycle handling) but significantly heavier (~400KB vs ~20KB for dagre). Overkill given that the acyclic projection approach works well for pipeline-shaped graphs. Could be a future upgrade if sub-pipelines are added.
- `d3-dag` — Good for DAG-specific layouts but less React Flow integration documentation.
- No layout (freeform positioning only) — rejected because existing pipelines have no position data and need a reasonable default.
- Feeding cycles directly to dagre — dagre can technically handle cycles but produces unpredictable results. The acyclic projection + post-draw approach gives more predictable top-to-bottom flow.

## R-003: Custom Node Components and Visual Design

**Decision**: Create 6 custom React Flow node components, one per node type, following the existing ShutterSense design system (design tokens, Lucide icons, shadcn/ui patterns).

**Rationale**:
- React Flow supports plain React components as custom nodes — no framework-specific API to learn.
- Each node type has distinct visual requirements per the spec (icon, color, shape).
- Custom nodes can display inline information (ID, type, key properties) and validation error indicators.
- Nodes must be wrapped in `React.memo()` for performance per React Flow best practices.

**Node type visual mapping** (from spec FR-002):

| Node Type | Lucide Icon | Design Token Color | Shape |
|-----------|-------------|--------------------|-------|
| Capture | `Camera` | `primary` (blue) | Rounded rectangle, larger (w-56 h-20) |
| File | `FileText` | `muted` (gray) | Rectangle (w-48 h-16) |
| Process | `Settings` | `accent`/purple | Rectangle (w-48 h-16) |
| Pairing | `Merge` | `info` (teal) | Diamond-rotated or hexagonal (w-44 h-16) |
| Branching | `GitBranch` | `warning` (amber) | Diamond-rotated or hexagonal (w-44 h-16) |
| Termination | `Archive` | `success` (green) | Rounded rectangle, double-border (w-48 h-16) |

**Handle placement**:
- Capture: Output handle only (bottom)
- Termination: Input handle only (top)
- All others: Input (top) + Output (bottom)

## R-004: Connection Validation Rules

**Decision**: Implement connection validation in a `connection-rules.ts` utility that integrates with React Flow's `isValidConnection` callback.

**Rationale**:
- React Flow provides `isValidConnection` prop on `<ReactFlow>` that prevents edges from being created if the callback returns false.
- Rules match existing backend validation (pipeline_service.py `_validate_structure`):
  1. Termination nodes cannot be edge sources (no outgoing edges)
  2. Capture nodes cannot be edge targets (no incoming edges)
  3. Duplicate edges (same from/to) rejected
- Visual feedback: Valid targets highlight green during drag; invalid connections snap back with a brief toast.
- Pairing node 2-input constraint is a validation hint, not a connection blocker (the edge itself is valid; the pipeline becomes invalid).

## R-005: Undo/Redo Architecture

**Decision**: Implement undo/redo as a custom hook (`usePipelineGraph.ts`) using an action history stack pattern, separate from React Flow's internal state.

**Rationale**:
- React Flow does not provide built-in undo/redo.
- A stack of state snapshots (nodes + edges) enables Ctrl+Z / Ctrl+Shift+Z.
- Each undoable action pushes the pre-action state to the undo stack and clears the redo stack.
- Supported actions: node add/delete/move, edge add/delete, property changes.
- Stack depth: 50 actions (sufficient for pipeline editing sessions).
- Debounced node drag positions (push state on drag start, not every pixel moved).

**Alternatives considered**:
- Command pattern (storing action objects with invert operations) — more memory-efficient but significantly more complex to implement for graph operations. Snapshot approach is simpler and memory cost is negligible for pipelines under 50 nodes.
- Third-party undo library — no established React Flow undo library exists.

## R-006: Flow Analytics Data — Path-Based Counting

**Decision**: Per-node and per-edge traversal counts are **not currently stored** by the pipeline_validation tool. Phase 3 requires extending the agent-side pipeline analyzer to record **per-path image counts**, from which edge and node statistics are derived.

**Rationale**:
- Current `pipeline_analyzer.py` output includes:
  - `status_counts` (overall: consistent, partial, inconsistent)
  - `by_termination` (per-termination-type counts)
  - `validation_results` (per-image details)
- Missing: Which paths through the pipeline were actually used, and how many image groups traversed each path.

**Path-based approach** (optimized for real-world usage patterns):

Image processing through a pipeline is highly repetitive — in 99% of cases, many image groups follow the same path through the pipeline. The analyzer should exploit this:

1. **Path identification**: When validating an image group, the analyzer determines which path (sequence of nodes from Capture to Termination) produced it. A "path" is the ordered list of node IDs traversed.
2. **Path caching**: Once a path has been identified for one image group, subsequent groups should be tested against **already-known paths first**. Since most groups follow the same path, this is a significant optimization — the common case is a cache hit rather than a fresh traversal.
3. **Per-path counting**: The output stores each distinct path with its image group count.
4. **Edge/node derivation**: Per-edge and per-node counts are derived by summing across all paths that include each edge/node. One edge can belong to multiple paths — its count is the sum of all contributing path counts. Edges not part of any used path stay at 0.

**Required addition to `results_json`**:
```json
{
  "path_stats": [
    {
      "path": ["capture_1", "file_raw", "process_hdr", "file_tiff", "termination_archive"],
      "image_count": 800
    },
    {
      "path": ["capture_1", "file_raw", "termination_archive"],
      "image_count": 650
    }
  ]
}
```

**Derived per-edge counts** (computed by flow-analytics endpoint, not stored):
- `capture_1→file_raw`: 800 + 650 = 1,450
- `file_raw→process_hdr`: 800
- `process_hdr→file_tiff`: 800
- `file_tiff→termination_archive`: 800
- `file_raw→termination_archive`: 650

**Derived per-node counts**:
- `capture_1`: 1,450 (entry point)
- `file_raw`: 1,450
- `process_hdr`: 800
- `file_tiff`: 800
- `termination_archive`: 1,450

This is an **agent-side change** (modifying `agent/src/analysis/pipeline_analyzer.py`), not a backend schema change. The backend flow-analytics endpoint reads `path_stats` from `results_json` and computes the per-edge/per-node aggregation on the fly.

**Alternatives considered**:
- Storing pre-computed per-edge/per-node counts directly — simpler to consume but loses path-level detail. The path-based approach preserves which exact routes were used, enabling richer analytics in the future (e.g., "show me which paths were used").
- Deriving counts from existing per-image `validation_results` array at query time — expensive re-aggregation on every analytics request. Pre-computing during analysis with path caching is more efficient.

## R-007: PipelineEditorPage Rewrite Strategy

**Decision**: Incrementally rewrite `PipelineEditorPage.tsx` across phases rather than a single big-bang rewrite.

**Rationale**:
- Current file is ~1,279 lines with significant logic (validation hints, regex extraction, node locking).
- Phase 1: Replace the flat node/edge list in **view mode only** with the graph canvas. Form editor remains for edit/create.
- Phase 2: Replace the form editor in **edit/create mode** with the interactive graph editor. Extract inline components (NodeEditor, EdgeEditor, NodeViewer, EdgeViewer) into the PropertyPanel.
- Phase 3: Add analytics overlay toggle to view mode.
- This minimizes risk — each phase is independently testable and deployable.

**Key logic to preserve**:
- `extractRegexGroups()` — Capture node regex preview (moves into PropertyPanel)
- `NODE_TYPE_DEFINITIONS` — Already in `pipelines-api.ts`, used by PropertyPanel
- Validation hints computation — Moves into `usePipelineGraph` hook
- Version history picker — Remains in page, feeds version data to graph view

## R-008: YAML Import/Export Backward Compatibility

**Decision**: Position data in YAML is optional. Import handles presence/absence gracefully.

**Rationale**:
- Existing YAML exports have no position data. Importing these uses auto-layout.
- New YAML exports include `position: {x: 100, y: 200}` per node when available.
- The `pipeline_service.py` YAML import already uses `PipelineNode` schema with `model_validate()` — adding an optional `position` field is backward-compatible.
- YAML export iterates `nodes_json` and includes all fields — position data passes through automatically.

## R-009: React Flow Styling with Tailwind CSS 4

**Decision**: Use React Flow's built-in Tailwind CSS support and extend with custom Tailwind classes from the design system.

**Rationale**:
- React Flow v12+ has official Tailwind CSS 4 integration.
- Custom node components use standard Tailwind classes and design tokens (same as all other ShutterSense components).
- React Flow's base CSS must be imported: `@xyflow/react/dist/style.css`.
- Canvas background, minimap, and controls are styled via React Flow's theme props, mapped to design tokens.

## R-010: Mobile/Tablet Responsive Behavior

**Decision**: Read-only graph view on screens < 768px. Editing disabled with informational message.

**Rationale**:
- React Flow supports touch gestures (pan, zoom, tap) natively.
- The property panel uses a bottom sheet overlay on mobile (< 768px) instead of side panel.
- Tablet landscape (>= 768px, < 1024px): Side panel collapses by default, toggleable.
- Desktop (>= 1024px): Two-panel layout (canvas + property panel).
- Edit button hidden on mobile with `hidden md:inline-flex` pattern.
