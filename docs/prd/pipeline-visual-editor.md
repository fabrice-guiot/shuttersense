# PRD: Pipeline Visual Graph Editor

**Issue**: TBD (to be filed after PRD review)
**Status**: Draft
**Created**: 2026-02-06
**Last Updated**: 2026-02-06
**Related Documents**:
- [Pipeline Validation PRD](./pipeline-validation/spec.md)
- [Domain Model](../domain-model.md)
- [Design System](../../frontend/docs/design-system.md)

---

## Executive Summary

This PRD defines the requirements for replacing the current form-based pipeline editor with an interactive visual graph editor built on React Flow (`@xyflow/react`). The feature addresses three complementary capabilities:

1. **Pipeline Graph View** -- A read-only visualization of pipeline structure rendered as a directed node graph, replacing the current flat list of nodes and edges.
2. **Pipeline Graph Editor** -- An interactive drag-and-drop editor for creating and modifying pipeline definitions, replacing the current form-based node/edge editor.
3. **Pipeline Flow Analytics** -- An overlay that visualizes analysis result data on pipeline edges, showing the volume and percentage of records flowing through each link.

The pipeline data model has been validated in production and the form-based editor is functional. This feature removes the "Beta" label by delivering the visual graph editor that has been promised in the UI since initial release.

---

## Background

### Current State

The pipeline feature currently uses a form-based editor (`PipelineEditorPage.tsx`, ~1,279 lines) where nodes and edges are managed as flat lists of cards. Users add nodes via an "Add Node" button, configure properties in form fields, then separately add edges by selecting source and target node IDs from dropdown menus.

Both `PipelinesPage.tsx` and `PipelineEditorPage.tsx` display a beta indicator:

> **Beta Feature:** Pipeline management is currently in beta. The visual graph editor will be available in a future release.

The underlying data model stores nodes and edges as JSONB arrays in the `Pipeline` model:
- `nodes_json`: Array of `{id, type, properties}` objects
- `edges_json`: Array of `{from, to}` objects

This structure maps directly to a directed graph suitable for visual rendering.

### Affected Files (Existing)

**Frontend (will be modified or replaced):**
- `frontend/src/pages/PipelineEditorPage.tsx` -- Form-based editor (create/edit/view modes)
- `frontend/src/pages/PipelinesPage.tsx` -- Pipeline list with beta indicator
- `frontend/src/contracts/api/pipelines-api.ts` -- TypeScript API contracts

**Backend (will be extended):**
- `backend/src/models/pipeline.py` -- Pipeline SQLAlchemy model
- `backend/src/models/pipeline_history.py` -- Version history model
- `backend/src/schemas/pipelines.py` -- Pydantic request/response schemas
- `backend/src/services/pipeline_service.py` -- Pipeline business logic
- `backend/src/api/pipelines.py` -- API routes

### Problem Statement

- **No spatial awareness**: Users cannot see the topological structure of their pipeline. Complex workflows with branching, pairing, and cycles are difficult to reason about as a flat list of nodes and edges.
- **Error-prone edge creation**: Selecting node IDs from dropdown menus requires users to mentally map which nodes should connect, without visual feedback on the resulting graph structure.
- **No analytics visualization**: Analysis results reference pipelines but there is no way to see how records flow through the pipeline graph. Users must interpret raw data without the context of the workflow topology.
- **Beta perception**: The "Beta Feature" label, visible on every pipeline page interaction, signals incompleteness and may reduce user confidence in the pipeline feature.

### Strategic Context

The pipeline is the central modeling concept in ShutterSense -- it defines how photo files relate to each other across the processing workflow. Every analysis tool (photostats, photo pairing, pipeline validation) operates within the context of a pipeline. Making the pipeline visually tangible transforms it from an abstract configuration object into an intuitive workflow diagram that users can design, understand, and analyze.

---

## Goals

### Primary Goals

1. **Visual pipeline authoring** -- Users can create and edit pipelines by dragging nodes onto a canvas, connecting them with edges, and configuring node properties through in-context panels.
2. **Topological visualization** -- Pipelines are rendered as directed graphs flowing from a single Capture node toward Termination nodes, with automatic layout and user-adjustable positions.
3. **Layout persistence** -- Node positions set by the user are saved and restored, so the visual layout remains consistent across sessions and for other team members.
4. **Remove Beta label** -- The beta indicators are removed from `PipelinesPage.tsx` and `PipelineEditorPage.tsx`.

### Secondary Goals

5. **Flow analytics overlay** -- When analysis results exist for a pipeline, edge thickness and labels indicate the volume/percentage of records flowing through each link.
6. **Accessible interaction** -- The graph editor supports keyboard navigation and screen reader announcements for node and edge operations, consistent with React Flow's built-in accessibility.
7. **Mobile/tablet read-only view** -- The graph visualization is viewable (pan, zoom) on touch devices, with editing reserved for desktop.

### Non-Goals (this PRD)

- **Pipeline execution engine** -- The frontend does not execute pipelines; agents handle tool execution.
- **Real-time collaboration** -- Multiple users cannot edit the same pipeline simultaneously.
- **Animated execution replay** -- Showing analysis execution progressing through nodes in real time.
- **Sub-pipelines / nested groups** -- Hierarchical pipeline composition (potential future enhancement).
- **Pipeline templates / marketplace** -- Sharing or importing pipeline templates across teams.

---

## Technology Selection

### Recommended Library: React Flow (`@xyflow/react`)

After evaluating six libraries (React Flow, Rete.js, Flume, React Diagrams, Butterfly, Drawflow), React Flow is recommended for the following reasons:

| Criterion | React Flow | Nearest Alternative (Rete.js) |
|-----------|-----------|-------------------------------|
| **Stack alignment** | Official Tailwind CSS 4 + shadcn/ui support | Possible but no official guide |
| **Maintenance** | Actively maintained (frequent commits as of Feb 2026), 35K+ GitHub stars, ~2.7M weekly npm downloads | Last pushed Nov 2025, 12K stars, ~15K weekly downloads |
| **Accessibility** | Tab navigation, ARIA attributes, configurable labels, keyboard movement | Minimal (no built-in a11y) |
| **Custom nodes/edges** | Plain React components | Framework plugin components |
| **Edge routing** | 4 built-in types (bezier, straight, step, smoothstep) | 2 types (default, linear) |
| **Layout integration** | Official examples for dagre, elkjs, d3-dag | elkjs only via plugin |
| **Performance** | Documented 50-60 FPS at 100 nodes with memoization | No published benchmarks |
| **License** | MIT (compatible with AGPL-3.0) | MIT |
| **Pro tier** | Core library fully featured; Pro is support/examples only | N/A |

**Layout algorithm**: `@dagrejs/dagre` for automatic top-to-bottom layout. It handles DAG structures well and is the simplest integration for pipeline-shaped graphs. `elkjs` is available as a future upgrade if nested groups are needed.

**Flow analytics**: Custom React Flow edges with variable stroke width proportional to throughput data, avoiding a separate Sankey library.

### Dependencies to Add

```text
@xyflow/react          # Core library (MIT)
@dagrejs/dagre         # Automatic layout (MIT)
```

No paid tier or Pro subscription is required.

---

## Detailed Requirements

### FR-001: Pipeline Graph Visualization (View Mode)

**Description**: When viewing a pipeline (`/pipelines/{guid}`), the node/edge list is replaced with an interactive graph visualization.

**Requirements**:
- FR-001.1: The pipeline is rendered as a directed graph using React Flow, with nodes positioned according to saved layout data or auto-layout.
- FR-001.2: Each node type has a distinct visual treatment:

  | Node Type | Icon | Color | Shape |
  |-----------|------|-------|-------|
  | Capture | Camera | Primary (blue) | Rounded rectangle, larger |
  | File | FileText | Neutral (gray) | Rectangle |
  | Process | Cog/Settings | Accent (purple) | Rectangle |
  | Pairing | Merge | Info (teal) | Diamond or hexagon |
  | Branching | GitBranch | Warning (amber) | Diamond or hexagon |
  | Termination | Archive | Success (green) | Rounded rectangle, double-border |

- FR-001.3: Nodes display their `id`, `type` label, and key properties (e.g., extension for File nodes, method_ids for Process nodes).
- FR-001.4: Edges are rendered as directed arrows (smoothstep routing for orthogonal clarity) flowing generally top-to-bottom.
- FR-001.5: The graph canvas supports pan (drag), zoom (scroll/pinch), and fit-to-view (button).
- FR-001.6: A minimap component is displayed for orientation in larger pipelines.
- FR-001.7: Zoom controls (zoom in, zoom out, fit view, lock) are displayed.
- FR-001.8: If no saved layout exists, dagre auto-layout positions nodes top-to-bottom with the Capture node at the top and Termination nodes at the bottom.
- FR-001.9: If saved layout exists, nodes are positioned according to saved coordinates.
- FR-001.10: In view mode, the graph is non-interactive (no dragging, no connection creation) beyond pan/zoom.
- FR-001.11: Clicking a node opens a read-only side panel or popover showing all node properties (equivalent information to the current `NodeViewer` component).
- FR-001.12: Validation errors, if present, are indicated visually on the affected nodes (e.g., red border, error icon).
- FR-001.13: The version picker (existing feature) continues to work -- selecting a historical version renders that version's graph.

### FR-002: Pipeline Graph Editor (Edit/Create Mode)

**Description**: When editing or creating a pipeline, the graph visualization becomes an interactive editor.

**Requirements**:

#### Node Operations
- FR-002.1: Nodes can be added via a toolbar/palette panel that lists available node types (Capture, File, Process, Pairing, Branching, Termination) with drag-to-canvas or click-to-add interaction.
- FR-002.2: Only one Capture node is allowed. The toolbar disables/hides the Capture option when one exists. Attempting to add a second Capture node shows a validation message.
- FR-002.3: Nodes can be repositioned by dragging on the canvas.
- FR-002.4: Selecting a node opens a side panel or inline editor for configuring node properties (type-specific fields as defined in `NODE_TYPE_DEFINITIONS`).
- FR-002.5: Node property changes are validated in real time with inline error messages (same validation rules as the current form editor).
- FR-002.6: Nodes can be deleted via a context menu, keyboard shortcut (Delete/Backspace), or a delete button in the property panel. Deleting a node also removes all connected edges.
- FR-002.7: Each node is assigned a unique `id`. For user-created nodes, suggest a default based on type (e.g., `file_1`, `process_2`) that the user can rename.
- FR-002.8: The Capture node's regex extraction preview (showing camera ID and counter groups extracted from the sample filename) is displayed within the Capture node's property panel.

#### Edge Operations
- FR-002.9: Edges are created by dragging from a source node's output handle to a target node's input handle.
- FR-002.10: Connection validation prevents invalid edges at creation time:
  - Termination nodes cannot be edge sources (no outgoing edges).
  - Capture nodes cannot be edge targets (no incoming edges).
  - Duplicate edges (same from/to pair) are rejected.
- FR-002.11: Pairing nodes enforce exactly 2 incoming edges. A visual indicator shows when a Pairing node has fewer or more than 2 inputs.
- FR-002.12: Edges can be deleted by selecting them and pressing Delete/Backspace, or via a context menu.
- FR-002.13: Cycles are allowed (consistent with current pipeline validation rules). No cycle-prevention logic is applied during edge creation. The UI should visually indicate when a cycle exists (e.g., a subtle badge or highlight on back-edges).

#### Canvas Operations
- FR-002.14: An "Auto Layout" button applies dagre layout to all nodes, useful after significant structural changes.
- FR-002.15: Undo/Redo support (Ctrl+Z / Ctrl+Shift+Z) for node additions, deletions, moves, edge additions, edge deletions, and property changes.
- FR-002.16: Multi-select (Shift+click or lasso) allows deleting multiple nodes/edges at once.
- FR-002.17: Snap-to-grid can be toggled for precise node placement.
- FR-002.18: The pipeline name, description, and change summary fields remain as form inputs above or beside the graph canvas (consistent with the current editor layout).

#### Save and Validation
- FR-002.19: The "Save" action serializes the current graph state (nodes, edges, and layout positions) and calls the existing `PUT /api/pipelines/{guid}` endpoint.
- FR-002.20: Live validation indicators show the current pipeline validity state (Valid/Invalid badge) as the user edits, matching the current behavior.
- FR-002.21: Validation hints (e.g., "At least one Termination node required") are displayed contextually, not as a separate section.
- FR-002.22: The "Cancel" action discards unsaved changes and returns to view mode, with a confirmation dialog if changes exist.

### FR-003: Node Layout Persistence

**Description**: Node positions are stored alongside the pipeline definition so that the visual layout is preserved across sessions and shared across team members.

**Requirements**:
- FR-003.1: Each node's position (`x`, `y` coordinates) is stored as part of the pipeline data.
- FR-003.2: Layout data is included in `nodes_json` by adding a `position` field to each node: `{id, type, properties, position: {x, y}}`.
- FR-003.3: Layout data is included in pipeline version history snapshots, so historical versions can be rendered with their original layout.
- FR-003.4: YAML import/export includes position data when present, and omits it when absent (backward-compatible).
- FR-003.5: Pipelines without position data (pre-existing pipelines) use dagre auto-layout. Users can save the auto-generated layout by editing and saving the pipeline.
- FR-003.6: The "Auto Layout" action (FR-002.14) replaces all current positions with dagre-computed positions. This change is part of the unsaved edit state and only persists on save.

### FR-004: Pipeline Flow Analytics Overlay

**Description**: When analysis results exist for a pipeline, edge annotations show how records flow through the graph.

**Requirements**:
- FR-004.1: In view mode, an "Analytics" toggle enables flow visualization on the pipeline graph.
- FR-004.2: When analytics mode is active, edges display flow data:
  - **Edge thickness**: Proportional to the number of records that traversed the edge (thicker = more records).
  - **Edge label**: Shows the count and/or percentage of records (e.g., "1,234 (87%)").
  - **Edge color**: Gradient from source node color to target node color, or a uniform color with opacity proportional to flow percentage.
- FR-004.3: Nodes in analytics mode display a count badge showing how many records reached that node.
- FR-004.4: The analytics data source is the most recent completed analysis result for the pipeline (specifically, `pipeline_validation` tool results which track per-node/per-edge traversal).
- FR-004.5: If no analysis results exist, the analytics toggle is disabled with a tooltip explaining that analysis must be run first.
- FR-004.6: A legend explains the edge thickness and color mapping.
- FR-004.7: The maximum and minimum edge thickness are bounded to maintain readability (e.g., 2px minimum, 20px maximum).

### FR-005: Remove Beta Labels

**Description**: The "Beta Feature" indicators are removed from pipeline pages.

**Requirements**:
- FR-005.1: ~~Remove the beta indicator from `PipelinesPage.tsx`.~~ **Done** -- removed in initial commit; `Beaker` import also removed from this file.
- FR-005.2: ~~Remove the beta indicator and "Coming Soon" graph placeholder from `PipelineEditorPage.tsx`.~~ **Done** -- both blocks removed in initial commit; `Beaker` import also removed (no remaining usages in this file).
- FR-005.3: ~~Remove the `Beaker` icon import if no longer used on these pages.~~ **Done** -- `Beaker` was removed from the lucide-react imports in both `PipelinesPage.tsx` and `PipelineEditorPage.tsx`.

---

## Backend Requirements

### BR-001: Layout Data in Pipeline Schema

**Description**: Extend the pipeline node schema to include optional position data.

**Changes**:
- BR-001.1: Add optional `position` field to `PipelineNode` schema in `backend/src/schemas/pipelines.py`:
  ```python
  class NodePosition(BaseModel):
      x: float = Field(..., description="X coordinate on canvas")
      y: float = Field(..., description="Y coordinate on canvas")

  class PipelineNode(BaseModel):
      id: str = Field(..., min_length=1, max_length=100)
      type: NodeType
      properties: Dict[str, Any] = Field(default_factory=dict)
      position: Optional[NodePosition] = Field(None, description="Canvas position for visual editor")
  ```
- BR-001.2: No database migration required -- `nodes_json` is JSONB and already accepts arbitrary node fields. The `position` field is simply a new property within existing JSONB objects.
- BR-001.3: Pipeline validation (`pipeline_service.py`) ignores the `position` field -- it is not relevant to structural validity.
- BR-001.4: YAML export/import handles the `position` field: present in export if set, optional on import.
- BR-001.5: Pipeline history snapshots (`PipelineHistory.nodes_json`) automatically include position data since they store the full `nodes_json` blob.

### BR-002: Flow Analytics Data Endpoint

**Description**: Provide an API endpoint that returns per-node and per-edge flow statistics derived from analysis results.

**Changes**:
- BR-002.1: New endpoint `GET /api/pipelines/{guid}/flow-analytics`:
  ```python
  @router.get("/{guid}/flow-analytics")
  async def get_flow_analytics(
      guid: str,
      result_guid: Optional[str] = None,  # Specific result, or latest if omitted
      ctx: TenantContext = Depends(get_tenant_context),
  ) -> PipelineFlowAnalyticsResponse
  ```
- BR-002.2: Response schema:
  ```python
  class NodeFlowStats(BaseModel):
      node_id: str
      record_count: int  # Records that reached this node
      percentage: float  # Percentage of total records from Capture node

  class EdgeFlowStats(BaseModel):
      from_node: str
      to_node: str
      record_count: int  # Records that traversed this edge
      percentage: float  # Percentage of upstream node's records

  class PipelineFlowAnalyticsResponse(BaseModel):
      pipeline_guid: str
      pipeline_version: int
      result_guid: str  # The analysis result used
      result_created_at: datetime
      total_records: int  # Total records at Capture node
      nodes: List[NodeFlowStats]
      edges: List[EdgeFlowStats]
  ```
- BR-002.3: The endpoint extracts flow data from the `report_json` field of `AnalysisResult` entries where `tool = 'pipeline_validation'`. The specific JSON structure depends on how the pipeline_validation tool stores per-node traversal counts.
- BR-002.4: If no analysis results exist for the pipeline, return 404 with a descriptive message.
- BR-002.5: If `result_guid` is provided, use that specific result. Otherwise, use the most recent completed result for the pipeline.

### BR-003: Pipeline Stats Update

**Description**: Update the pipeline stats endpoint to include data useful for the visual editor.

**Changes**:
- BR-003.1: No immediate changes required to `GET /api/pipelines/stats`. The existing stats (total, valid, active, default) remain sufficient for the TopHeader KPIs.
- BR-003.2: Future consideration: Add `pipelines_with_layout` count if tracking layout adoption is desired.

---

## UX Requirements

### UX-001: Visual Hierarchy and Node Design

- UX-001.1: The Capture node is visually prominent (larger, primary color) as the entry point. It should appear at the top of the auto-layout.
- UX-001.2: Termination nodes are visually distinct (double border or terminal icon) as endpoints. They appear at the bottom.
- UX-001.3: The topological flow direction is top-to-bottom (vertical), matching the mental model of a pipeline progressing from capture to archive.
- UX-001.4: Node type icons match the existing domain icon conventions from the design system.
- UX-001.5: The node color palette uses existing design tokens (`primary`, `success`, `warning`, `muted`, `info`, `destructive`) -- no new colors introduced.

### UX-002: Editor Layout

- UX-002.1: The editor page has a two-panel layout:
  - **Left**: Graph canvas (takes majority of horizontal space)
  - **Right**: Property panel (collapsible sidebar, ~320px) for selected node/edge configuration
- UX-002.2: Above the canvas: pipeline metadata fields (name, description, change summary) in a collapsible header.
- UX-002.3: The node palette (for adding new nodes) can be:
  - A dockable panel on the left edge, or
  - A toolbar above the canvas with draggable node type buttons
- UX-002.4: The canvas toolbar (bottom or top) contains: Auto Layout, Zoom In, Zoom Out, Fit View, Snap Grid toggle, Undo, Redo.
- UX-002.5: Save and Cancel buttons are positioned consistently with the current editor (bottom action bar or top-right).

### UX-003: Interaction Feedback

- UX-003.1: Dragging a new edge shows a preview line from the source handle to the cursor.
- UX-003.2: Valid drop targets (compatible node handles) are highlighted during edge dragging.
- UX-003.3: Invalid edge attempts (e.g., connecting to a Capture node's input) show a brief error toast or the edge snaps back.
- UX-003.4: Node selection is indicated by a highlight ring matching the node's type color.
- UX-003.5: Edge selection is indicated by a thicker stroke and/or color change.
- UX-003.6: The validation state (Valid/Invalid) is visible at all times during editing, updating live as the graph changes.

### UX-004: Empty State and Onboarding

- UX-004.1: Creating a new pipeline shows an empty canvas with a centered prompt: "Drag a Capture node from the palette to start building your pipeline."
- UX-004.2: The Capture node is pre-highlighted or visually distinguished in the palette as the required first step.
- UX-004.3: After adding the Capture node, a contextual hint suggests: "Connect the Capture node to File nodes to define expected file types."

### UX-005: Responsive Behavior

- UX-005.1: On screens < 768px (mobile/tablet), the graph view is read-only with pan/zoom only. The property panel overlays as a bottom sheet.
- UX-005.2: On screens >= 768px and < 1024px (tablet landscape), the property panel collapses by default and can be toggled open.
- UX-005.3: On screens >= 1024px (desktop), the two-panel layout is the default.
- UX-005.4: Touch gestures are supported: single-finger pan, pinch-to-zoom, tap to select node.

### UX-006: Analytics Overlay UX

- UX-006.1: The analytics toggle is a switch in the view mode toolbar, labeled "Show Flow".
- UX-006.2: When analytics mode is active, the graph background dims slightly to increase contrast of the flow visualization.
- UX-006.3: Hovering over an edge in analytics mode shows a tooltip with detailed flow statistics (count, percentage, upstream node, downstream node).
- UX-006.4: Hovering over a node in analytics mode shows a tooltip with that node's total record count and percentage.
- UX-006.5: Edges with zero flow are rendered as dashed lines with reduced opacity.
- UX-006.6: The analytics overlay does not interfere with pan/zoom navigation.

---

## Migration and Compatibility

### MC-001: Backward Compatibility

- MC-001.1: Existing pipelines without `position` data in `nodes_json` continue to work. The frontend applies auto-layout when positions are absent.
- MC-001.2: No database migration is required (JSONB storage is schema-flexible).
- MC-001.3: The YAML export format remains backward-compatible. Position data is an optional addition.
- MC-001.4: The API contract (`PipelineNode`) adds the optional `position` field. Existing API consumers that do not send `position` continue to work.

### MC-002: Form Editor Deprecation

- MC-002.1: The existing form-based editor components (`NodeEditor`, `EdgeEditor`, `NodeViewer`, `EdgeViewer`) are replaced by the graph editor and property panel. They should be removed once the graph editor is fully functional.
- MC-002.2: The current `PipelineEditorPage.tsx` is rewritten. The view mode, edit mode, and create mode remain as URL-driven states but render the graph editor instead of forms.

---

## Performance Considerations

- PC-001: Custom node components must be wrapped in `React.memo()` to prevent unnecessary re-renders.
- PC-002: Callback props on `<ReactFlow>` must use `useCallback()`.
- PC-003: The graph should comfortably handle pipelines with up to 50 nodes (typical pipelines have 5-15 nodes). This is well within React Flow's documented performance envelope.
- PC-004: Auto-layout (dagre) runs synchronously and should complete in <100ms for pipelines under 50 nodes.
- PC-005: Analytics overlay edge thickness calculations should be memoized to avoid recalculation on pan/zoom.

---

## Testing Requirements

- TR-001: Unit tests for custom node components (render correctly for each node type).
- TR-002: Unit tests for edge validation logic (prevent invalid connections).
- TR-003: Unit tests for dagre layout integration (nodes positioned correctly for known graph structures).
- TR-004: Unit tests for serialization/deserialization of graph state to/from API format.
- TR-005: Unit tests for undo/redo state management.
- TR-006: Backend unit tests for `NodePosition` schema validation.
- TR-007: Backend unit tests for flow analytics endpoint (mock analysis result data).
- TR-008: Integration test: create pipeline via graph editor, verify saved nodes/edges/positions match expected structure.
- TR-009: Accessibility test: verify keyboard navigation through nodes and edges.

---

## Phased Delivery

This feature is recommended for phased delivery:

### Phase 1: Graph View + Beta Label Removal
- FR-001 (Graph Visualization in view mode)
- FR-003 (Layout Persistence)
- FR-005 (Remove Beta Labels)
- BR-001 (Layout data in schema)
- UX-001, UX-005
- **Outcome**: Users see pipelines as graphs. Existing form editor remains for editing. Beta label removed.

### Phase 2: Graph Editor
- FR-002 (Interactive graph editor)
- MC-002 (Form editor deprecation)
- UX-002, UX-003, UX-004
- **Outcome**: Users create and edit pipelines visually. Form editor removed.

### Phase 3: Flow Analytics
- FR-004 (Analytics overlay)
- BR-002 (Flow analytics endpoint)
- UX-006
- **Outcome**: Users visualize record flow through pipelines.

---

## Library Evaluation Summary

The following libraries were evaluated:

| Library | Stars | License | Active | TS | React 18 | A11y | Tailwind | Verdict |
|---------|-------|---------|--------|-----|----------|------|----------|---------|
| **React Flow** | 35,124 | MIT | Yes (daily) | Native | Yes | Strong | Official | **Selected** |
| Rete.js | 11,842 | MIT | Yes (Nov 2025) | Native | Plugin | Minimal | No guide | Runner-up |
| React Diagrams | 9,377 | MIT | Stalled (2yr) | Native | Yes | None | No | Not recommended |
| Drawflow | 5,954 | MIT | Stale (Oct 2024) | @types | No React | None | No | Not recommended |
| Butterfly | 4,651 | MIT | Dead (React) | JS only | Unmaintained | None | No | Not recommended |
| Flume | 1,607 | MIT | Low adoption | Community | ^18.2 | None | No | Not recommended |

React Flow is the clear choice: largest community (2.7M weekly npm downloads), official Tailwind CSS 4 and shadcn/ui support matching the ShutterSense stack, strong built-in accessibility (keyboard nav, ARIA), MIT license compatible with AGPL-3.0, and a fully featured core with no feature gating behind a paid tier.

---

## Open Questions

1. **Analytics data granularity**: Does the pipeline_validation tool currently store per-node and per-edge traversal counts in `report_json`? If not, the tool output format needs to be extended (agent-side change) before FR-004 can be implemented.
2. **Edge labels for non-analytics mode**: Should edges display labels in normal view mode (e.g., showing the edge's semantic meaning), or are directional arrows sufficient?
3. **Pipeline comparison**: Should the graph view support side-by-side comparison of two pipeline versions? This would be valuable for reviewing changes but adds scope.
4. **Dark mode**: React Flow supports theming. Should the graph editor be styled for both light and dark modes from the start?

---

## References

- [React Flow Documentation](https://reactflow.dev)
- [React Flow GitHub (xyflow/xyflow)](https://github.com/xyflow/xyflow)
- [React Flow Tailwind CSS Example](https://reactflow.dev/examples/styling/tailwind)
- [React Flow Dagre Layout Example](https://reactflow.dev/examples/layout/dagre)
- [React Flow Accessibility Guide](https://reactflow.dev/learn/advanced-use/accessibility)
- [React Flow Performance Guide](https://reactflow.dev/learn/advanced-use/performance)
- [dagre Layout Library](https://github.com/dagrejs/dagre)
- [Awesome Node-Based UIs](https://github.com/xyflow/awesome-node-based-uis)
