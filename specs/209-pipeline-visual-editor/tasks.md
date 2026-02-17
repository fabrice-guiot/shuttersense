# Tasks: Pipeline Visual Graph Editor

**Input**: Design documents from `/specs/209-pipeline-visual-editor/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks grouped by user story per the phased delivery plan. US1+US4(read)+US7 form the MVP. US2+US3+US4(write) form the editor phase. US5 and US6 are independent enhancements.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Install new dependencies and create directory structure for React Flow graph components

- [x] T001 Install `@xyflow/react` and `@dagrejs/dagre` via npm in `frontend/`. Run `npm install @xyflow/react @dagrejs/dagre` and `npm install -D @types/dagre`
- [x] T002 Import React Flow base CSS by adding `@import '@xyflow/react/dist/style.css';` to `frontend/src/globals.css`
- [x] T003 Create the graph component directory structure under `frontend/src/components/pipelines/graph/` with subdirectories: `nodes/`, `edges/`, `utils/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend schema extension, frontend graph utilities, and their tests — ALL user stories depend on this phase

**CRITICAL**: No user story work can begin until this phase is complete

### Implementation

- [x] T004 Add `NodePosition` schema and extend `PipelineNode` with optional `position` field in `backend/src/schemas/pipelines.py`. Add `class NodePosition(BaseModel)` with `x: float` and `y: float` fields. Add `position: Optional[NodePosition] = Field(None)` to the existing `PipelineNode` class. Verify existing pipeline validation (`_validate_structure`) naturally ignores the position field (it only checks id, type, properties — no code change needed)
- [x] T005 [P] Add `NodePosition` interface and extend `PipelineNode` interface with optional `position?: NodePosition` field in `frontend/src/contracts/api/pipelines-api.ts`. Also add the `PipelineNodeData` interface (nodeId, type, properties, hasError, isSelected, analyticsCount) that all custom node components will use
- [x] T006 [P] Create `frontend/src/components/pipelines/graph/utils/node-defaults.ts` with: `generateNodeId(type, existingIds)` → generates unique IDs like `file_1`, `process_2`; `getNodeConfig(type)` → returns `{icon, colorClass, shapeClass, defaultWidth, defaultHeight}` per the visual mapping in research.md R-003 (Capture=Camera/primary/w-56, File=FileText/muted/w-48, Process=Settings/purple/w-48, Pairing=Merge/info/w-44, Branching=GitBranch/warning/w-44, Termination=Archive/success/w-48); `getDefaultProperties(type)` → returns default properties for each node type based on NODE_TYPE_DEFINITIONS in pipelines-api.ts
- [x] T007 [P] Create `frontend/src/components/pipelines/graph/utils/graph-transforms.ts` with: `toReactFlowNodes(apiNodes, validationErrors?)` → converts PipelineNode[] to React Flow Node<PipelineNodeData>[] (maps properties→data, position→position, sets hasError from validation errors); `toReactFlowEdges(apiEdges, analytics?)` → converts PipelineEdge[] to React Flow Edge[] (generates id as `${from}-${to}`, maps from→source, to→target, uses smoothstep type); `toApiNodes(rfNodes)` → converts back to PipelineNode[] (preserves positions); `toApiEdges(rfEdges)` → converts back to PipelineEdge[]; `hasPositions(nodes)` → returns true if any node has non-null position
- [x] T008 [P] Create `frontend/src/components/pipelines/graph/utils/dagre-layout.ts` with: `findBackEdges(nodes, edges, captureNodeId)` → performs forward traversal from Capture node, returns edges whose target was already visited (cycle-introducing back-edges); `applyDagreLayout(nodes, edges, options?)` → computes acyclic projection by excluding back-edges, runs dagre with `rankdir:'TB'`, `nodesep:80`, `ranksep:100` on forward edges only, returns nodes with computed positions. Import dagre from `@dagrejs/dagre`
- [x] T009 [P] Create custom node components `CaptureNode.tsx` and `TerminationNode.tsx` in `frontend/src/components/pipelines/graph/nodes/`. Both wrapped in `React.memo()`. CaptureNode: Camera icon, primary color, larger rounded rect (w-56), displays node ID and sample_filename property, output Handle only (Position.Bottom). TerminationNode: Archive icon, success color, double-border rounded rect, displays node ID and termination_type property, input Handle only (Position.Top). Both show red border ring when `data.hasError` is true. Both show analytics count badge when `data.analyticsCount` is set
- [x] T010 [P] Create custom node components `FileNode.tsx`, `ProcessNode.tsx`, `PairingNode.tsx`, `BranchingNode.tsx` in `frontend/src/components/pipelines/graph/nodes/`. All wrapped in `React.memo()` with input Handle (Position.Top) and output Handle (Position.Bottom). FileNode: FileText icon, muted color, displays extension property. ProcessNode: Settings icon, purple/accent color, displays method_ids. PairingNode: Merge icon, info/teal color, diamond-shaped via rotate-45 transform. BranchingNode: GitBranch icon, warning/amber color, diamond-shaped. All show error indicator and analytics badge like T009
- [x] T011 [P] Create `PipelineEdge.tsx` custom edge component in `frontend/src/components/pipelines/graph/edges/`. Use `SmoothStepEdge` from `@xyflow/react` with an arrowhead marker (`MarkerType.ArrowClosed`). Standard styling using design system colors. This is the default edge for non-analytics view
- [x] T012 Create barrel exports: `frontend/src/components/pipelines/graph/nodes/index.ts` exporting all 6 node components and the `nodeTypes` mapping object (keyed by NodeType values); `frontend/src/components/pipelines/graph/edges/index.ts` exporting PipelineEdge and the `edgeTypes` mapping object

### Tests

- [x] T013 [P] Create tests for graph-transforms utilities in `frontend/src/components/pipelines/graph/utils/__tests__/graph-transforms.test.ts`. Using vitest. Test cases: `toReactFlowNodes` converts PipelineNode[] to React Flow Node<PipelineNodeData>[] preserving id/type/properties mapping; position data is passed through when present; `hasError` is set when validationErrors contain an error referencing the node id; `toReactFlowEdges` generates edge id as `${from}-${to}`, maps from→source and to→target, sets smoothstep type; `toApiNodes` roundtrip preserves all data including positions; `toApiEdges` maps source→from and target→to; `hasPositions` returns false when no nodes have position, true when at least one does. Test with representative pipeline data: 3+ nodes of different types, edges including a cycle
- [x] T014 [P] Create tests for dagre layout and cycle detection in `frontend/src/components/pipelines/graph/utils/__tests__/dagre-layout.test.ts`. Using vitest. Test cases for `findBackEdges`: simple DAG (Capture→File→Termination) returns empty array; single cycle (Capture→File→Process→File — the Process→File edge is a back-edge); multiple cycles returns all back-edges; graph with no Capture node handles gracefully; disconnected nodes are handled. Test cases for `applyDagreLayout`: positions are assigned to all nodes; Capture node is positioned above Termination nodes (y-coordinate check); nodes have non-overlapping positions; cyclic graph produces valid layout (back-edges excluded, all nodes still positioned); empty graph returns empty array; respects `options` parameter (direction, nodeSep, rankSep)
- [x] T015 [P] Create tests for node defaults utilities in `frontend/src/components/pipelines/graph/utils/__tests__/node-defaults.test.ts`. Using vitest. Test cases: `generateNodeId` produces expected format (`file_1` for type `file` with no existing IDs); increments counter when ID exists (`file_2` when `file_1` exists); handles gaps in numbering; handles all 6 node types. `getNodeConfig` returns correct icon component, colorClass, shapeClass, defaultWidth, defaultHeight for each of the 6 node types per R-003 mapping. `getDefaultProperties` returns appropriate default properties for each node type matching NODE_TYPE_DEFINITIONS
- [x] T016 [P] Create tests for the NodePosition schema extension in `backend/tests/unit/schemas/test_pipeline_schemas.py`. Using pytest. Test cases: NodePosition accepts valid x/y floats; PipelineNode accepts optional position field; PipelineNode without position field validates successfully (backward compat); PipelineNode with `position={x: 100.0, y: 200.0}` validates and round-trips correctly via `model_dump()`/`model_validate()`; PipelineCreateRequest with nodes containing positions validates; existing pipeline structure validation ignores position field — a valid pipeline with positions passes validation unchanged. Import NodePosition and PipelineNode from `backend.src.schemas.pipelines`
- [x] T017 Create tests for all 6 custom node components in `frontend/src/components/pipelines/graph/nodes/__tests__/node-components.test.tsx`. Using vitest + @testing-library/react. Mock `@xyflow/react` Handle component (render as a div with data-testid including position). For each node type (CaptureNode, FileNode, ProcessNode, PairingNode, BranchingNode, TerminationNode): renders without crashing; displays the node ID from `data.nodeId`; shows error indicator when `data.hasError` is true; hides error indicator when `data.hasError` is false. Type-specific handle tests: CaptureNode has output Handle only (Position.Bottom, no Position.Top); TerminationNode has input Handle only (Position.Top, no Position.Bottom); all other nodes have both input and output Handles. Analytics badge: when `data.analyticsCount` is set, a badge with the count is visible

**Checkpoint**: Foundation ready — all graph utilities, custom components, schema extensions, and their tests are in place. User story implementation can now begin.

---

## Phase 3: User Story 1 + User Story 4 (Read) + User Story 7 — Graph View + Beta Removal (Priority: P1) MVP

**Goal**: Replace flat node/edge lists with an interactive directed graph visualization. Auto-layout positions nodes when no saved layout exists. Remove beta banners.

**Independent Test**: Navigate to any existing pipeline's view page → graph renders with correct node types, pan/zoom works, clicking a node shows properties, minimap visible, version picker loads historical versions as graph. Pipeline list and editor pages show no beta banners.

### Implementation

- [x] T018 [US1] Create `PipelineGraphView.tsx` in `frontend/src/components/pipelines/graph/`. This is the read-only graph canvas component. Props: `nodes: PipelineNode[]`, `edges: PipelineEdge[]`, `validationErrors?: string[] | null`, `onNodeClick?: (nodeId: string) => void`. Implementation: convert API data to React Flow format via `toReactFlowNodes`/`toReactFlowEdges`; if `!hasPositions(nodes)`, apply `applyDagreLayout`; render `<ReactFlow>` with `nodeTypes`, `edgeTypes`, `fitView`, `minZoom={0.1}`, `maxZoom={2}`, disable node dragging (`nodesDraggable={false}`), disable edge connection; include `<MiniMap>`, `<Controls>` (zoom in/out/fit), `<Background variant="dots" gap={16}>`; wire `onNodeClick` to node click events
- [x] T019 [P] [US1] Create `PropertyPanel.tsx` in `frontend/src/components/pipelines/graph/`. Initial implementation supports view mode only (edit mode added in Phase 4). Props: `node: PipelineNode | null`, `edge: PipelineEdge | null`, `mode: 'view' | 'edit'`, `onClose: () => void`. In view mode: displays all node properties read-only (same information as current NodeViewer inline component), including special handling for Capture node regex preview (`extractRegexGroups` logic from current PipelineEditorPage). Collapsible sidebar (~320px) on right side of canvas. Shows edge info (from → to with node types) when an edge is selected
- [x] T020 [US1] [US4] Integrate `PipelineGraphView` into `PipelineEditorPage.tsx` view mode. Replace the current flat node list (`NodeViewer` cards) and edge list (`EdgeViewer` cards) with the `PipelineGraphView` component. Also remove the blue "Coming Soon: Visual pipeline graph" alert placeholder. Wire node click to open `PropertyPanel` in view mode. The graph uses saved positions when present (US4 read-side) or auto-layout when absent. Keep the existing pipeline header (name, description, GUID, status badges, version picker, export/edit buttons) above the graph canvas. The graph canvas should fill available vertical space
- [x] T021 [US7] Remove beta banners from `frontend/src/pages/PipelinesPage.tsx` (the warning div with Beaker icon and "Beta Feature: Pipeline management is currently in beta" text) and from `frontend/src/pages/PipelineEditorPage.tsx` (the amber Alert with "Beta Feature: Pipeline editor is currently in beta" text). Remove the `Beaker` icon import from both files if no longer used after removal
- [x] T022 [US1] Wire the existing version history picker in `PipelineEditorPage.tsx` view mode to feed historical version data into `PipelineGraphView`. When the user selects a historical version (via `loadVersion(version)`), the graph should re-render with that version's nodes, edges, and positions (if saved). Show the existing "historical version" warning banner. The "Edit Pipeline" button should remain disabled for historical versions

### Tests

- [x] T023 [P] [US7] Update `frontend/src/pages/__tests__/PipelinesPage.test.tsx` after beta banner removal. Remove the `renders beta feature indicator` test that asserts `screen.getByText('Beta Feature:', { exact: false })` — this element no longer exists after T021. Add a replacement test: `does not show beta banner` that asserts `screen.queryByText('Beta Feature:', { exact: false })` returns null. Verify the remaining tests still pass (renders pipeline list, create button, loading state, no error alert)
- [x] T024 [P] [US1] Update `frontend/src/pages/__tests__/PipelineEditorPage.test.tsx` after graph view integration. The existing tests mock `usePipeline` with `nodes: []` and `edges: []`. After T020 integrates PipelineGraphView, the view mode rendering changes. Add `vi.mock` for the new `PipelineGraphView` component (mock as a simple div with `data-testid="pipeline-graph-view"`). Add `vi.mock` for `PropertyPanel`. Update `renders in view mode without errors` test to verify the graph view mock renders. Update mock pipeline data to include sample nodes (at least one Capture node) and edges to better represent real usage. Verify `renders edit button in view mode` and `shows loading state` tests still pass

**Checkpoint**: MVP complete — pipelines render as visual directed graphs with auto-layout, minimap, zoom controls, node property inspection, version history, and no beta banners. Tests updated to reflect new graph-based rendering.

---

## Phase 4: User Story 2 + User Story 3 + User Story 4 (Write) — Graph Editor + Create Pipeline (Priority: P2)

**Goal**: Replace the form-based editor with an interactive drag-and-drop graph editor. Support creating new pipelines with onboarding guidance. Persist node positions when saving.

**Independent Test**: Open a pipeline in edit mode → drag nodes from palette, connect via handles, edit properties in side panel, undo/redo works, validation hints shown, save persists graph with positions. Create new pipeline → empty canvas with onboarding prompt, build and save successfully.

### Implementation

- [x] T025 [US2] Create `frontend/src/components/pipelines/graph/utils/connection-rules.ts` with: `isValidConnection(connection, nodes, edges)` → returns false if: target node is type 'capture' (no incoming edges), source node is type 'termination' (no outgoing edges), or duplicate edge (same source/target) already exists; `getConnectionError(connection, nodes, edges)` → returns human-readable error message for invalid connections (e.g., "Capture nodes cannot receive incoming edges"), or null if valid
- [x] T026 [US2] Create `usePipelineGraph` hook in `frontend/src/hooks/usePipelineGraph.ts`. This is the core state management hook for the graph editor. Must provide: React Flow state (`nodes`, `edges`, `onNodesChange`, `onEdgesChange`, `onConnect`); node operations (`addNode(type, position?)`, `removeNode(nodeId)`, `updateNodeProperties(nodeId, props)`); edge operations (`removeEdge(edgeId)`); layout (`applyAutoLayout()` using dagre-layout.ts); undo/redo (snapshot stack of max 50, `undo()`, `redo()`, `canUndo`, `canRedo` — push state on node add/delete, edge add/delete, property change, drag start); serialization (`toApiFormat()`, `fromApiFormat(nodes, edges)`); validation hints (compute: capture required, non-optional file required, termination required, orphaned nodes, pairing 2-input check); dirty tracking (`isDirty`, `resetDirty`); selection (`selectedNodeId`, `selectedEdgeId`). Use `isValidConnection` from connection-rules.ts in `onConnect`. Integrate node ID generation from node-defaults.ts
- [x] T027 [P] [US2] Create `NodePalette.tsx` in `frontend/src/components/pipelines/graph/`. Displays all 6 node types with their icons and labels. Supports drag-to-canvas (using React Flow's drag-and-drop pattern with `onDragStart` setting transfer data) and click-to-add (calls `onAddNode`). Props: `existingNodeTypes: NodeType[]`, `onAddNode: (type: NodeType) => void`. Disable/gray-out Capture option when `existingNodeTypes` includes 'capture'. Visually highlight Capture as the recommended first node (when no nodes exist). Styled as a horizontal toolbar above the canvas or a vertical dockable panel on the left edge
- [x] T028 [US2] Extend `PropertyPanel.tsx` (created in T019) with edit mode functionality. When `mode='edit'`: show editable form fields for node properties based on NODE_TYPE_DEFINITIONS from pipelines-api.ts (same field types as current NodeEditor — text, select, boolean checkbox, array). Include node ID field (editable, calls `onUpdateNodeId`). Include delete node/edge button (calls `onDeleteNode`/`onDeleteEdge`). For Capture nodes: show regex extraction preview (Camera ID Group dropdown populated from regex match groups — port `extractRegexGroups` logic). Inline validation with error messages. Add props: `onUpdateProperties`, `onUpdateNodeId`, `onDeleteNode`, `onDeleteEdge`
- [x] T029 [P] [US2] Create `EditorToolbar.tsx` in `frontend/src/components/pipelines/graph/`. Toolbar positioned above or below the canvas with buttons: Auto Layout (calls `onAutoLayout`), Undo (Ctrl+Z, calls `onUndo`, disabled when `!canUndo`), Redo (Ctrl+Shift+Z, calls `onRedo`, disabled when `!canRedo`), Snap-to-Grid toggle (calls `onToggleSnapToGrid`), validation status badge (green checkmark when `isValid`, red X when invalid with popover listing `validationHints`). Props per `EditorToolbarProps` from contracts/frontend-api.md
- [x] T030 [US2] Create `PipelineGraphEditor.tsx` in `frontend/src/components/pipelines/graph/`. This is the interactive editor component wrapping PipelineGraphView. Uses `usePipelineGraph` hook for state. Two-panel layout: left=graph canvas (majority width), right=PropertyPanel (collapsible ~320px sidebar). Above canvas: NodePalette. Below/above canvas: EditorToolbar. Enable node dragging, handle-to-handle edge creation via `onConnect`, multi-select (shift+click/lasso), keyboard delete (Delete/Backspace removes selected nodes/edges). React Flow config: `nodesDraggable={true}`, `connectOnClick={false}`, `snapToGrid` from toolbar toggle. Support React Flow's `onDrop` for palette drag-and-drop. Props per `PipelineGraphEditorProps` from contracts/frontend-api.md. Register keyboard shortcuts for undo/redo (Ctrl+Z/Ctrl+Shift+Z)
- [x] T031 [US2] [US3] [US4] Integrate `PipelineGraphEditor` into `PipelineEditorPage.tsx` for edit and create modes. Replace the current form-based node/edge editing (the "Add Node"/"Add Edge" buttons, NodeEditor cards, EdgeEditor cards) with `PipelineGraphEditor`. Keep pipeline metadata fields (name, description, change summary) as form inputs above the graph — in a collapsible header section. Wire `onSave` to serialize graph state via `toApiFormat()` (which includes node positions — US4 write-side) and call existing `updatePipeline`/`createPipeline`. Wire `onCancel` to show confirmation dialog if `isDirty`, then navigate back. Wire `onDirtyChange` to track unsaved state for the cancel confirmation. For create mode: pass empty initial nodes/edges. For edit mode: pass current pipeline's nodes/edges
- [x] T032 [US3] Add empty canvas onboarding to `PipelineGraphEditor.tsx`. When `nodes` array is empty (create mode), display a centered overlay on the canvas: "Drag a Capture node from the palette to start building your pipeline." with an arrow/highlight pointing to the Capture option in NodePalette. After the first Capture node is placed, show a brief contextual hint toast: "Connect the Capture node to File nodes to define expected file types." Hint dismisses after 5 seconds or on user interaction
- [x] T033 [US2] Remove deprecated form editor inline components from `PipelineEditorPage.tsx`. Delete the `NodeEditor`, `EdgeEditor`, `NodeViewer`, and `EdgeViewer` inline component definitions (these were replaced by PipelineGraphView + PropertyPanel + PipelineGraphEditor). Remove the "Add Node" button, "Add Edge" button, and their associated handler functions that are no longer used. Clean up unused imports and state variables (e.g., `lockedNodeIndices`). The page should now only contain: metadata form + PipelineGraphView (view mode) or PipelineGraphEditor (edit/create mode)

### Tests

- [x] T034 [P] [US2] Create tests for connection validation rules in `frontend/src/components/pipelines/graph/utils/__tests__/connection-rules.test.ts`. Using vitest. Test `isValidConnection`: returns true for valid File→Process connection; returns false when target is a Capture node (no incoming edges); returns false when source is a Termination node (no outgoing edges); returns false for duplicate edge (same source+target already exists); returns true for creating a cycle (cycles are allowed per FR-022). Test `getConnectionError`: returns null for valid connections; returns descriptive message when target is Capture; returns descriptive message when source is Termination; returns descriptive message for duplicate edges. Set up test fixtures with mock `Node<PipelineNodeData>[]` and `Edge[]` arrays
- [x] T035 [US2] Create tests for the usePipelineGraph hook in `frontend/src/hooks/__tests__/usePipelineGraph.test.ts`. Using vitest + `renderHook` from @testing-library/react. Mock graph utility imports (dagre-layout, graph-transforms, connection-rules, node-defaults). Test cases: (1) `fromApiFormat` initializes nodes and edges correctly; (2) `addNode` adds a node with generated ID and default properties; (3) `addNode` for Capture type when one exists triggers validation hint; (4) `removeNode` removes the node and all connected edges; (5) `updateNodeProperties` updates properties on the target node; (6) `undo` reverts the last action (add/remove/property change); (7) `redo` re-applies after undo; (8) `canUndo` is false initially, true after a change; `canRedo` is false initially, true after undo; (9) `toApiFormat` produces valid PipelineNode[] and PipelineEdge[]; (10) `isDirty` is false initially, true after any change, false after `resetDirty`; (11) `validationHints` includes "Pipeline requires a Capture node" when no capture exists; (12) `isValid` reflects whether validation hints are empty. Use `act()` wrapper for state changes

**Checkpoint**: Full visual pipeline editing is functional with tests. Users can create, edit, and save pipelines using drag-and-drop with undo/redo, connection validation, and layout persistence. Form editor components have been removed.

---

## Phase 5: User Story 5 — Flow Analytics Overlay (Priority: P3)

**Goal**: Visualize record flow through pipelines by showing edge thickness and count labels derived from pipeline validation analysis results.

**Independent Test**: Run pipeline_validation on a pipeline with a collection → open pipeline view → toggle "Show Flow" → edges show variable thickness and count/percentage labels, nodes show record count badges, legend is visible, hovering shows tooltips. Toggle off restores normal view.

**Dependency**: Requires extending the agent-side pipeline_analyzer.py to emit `path_stats` data.

### Implementation

- [x] T036 [US5] Extend `agent/src/analysis/pipeline_analyzer.py` to emit `path_stats` in the validation results. During image group validation, track which path (ordered sequence of node IDs from Capture to Termination) each image group traverses. Implement path caching: maintain a list of already-identified paths; for each new image group, test against known paths first before doing a fresh traversal (optimization — 99% of groups follow the same few paths). Add to the returned results dict: `"path_stats": [{"path": ["node_id_1", "node_id_2", ...], "image_count": N}, ...]`. Each entry is a distinct path with its image group count. Existing output fields (`status_counts`, `by_termination`, `validation_results`) remain unchanged
- [x] T037 [P] [US5] Add flow analytics response schemas to `backend/src/schemas/pipelines.py`: `NodeFlowStats(BaseModel)` with `node_id: str`, `record_count: int`, `percentage: float`; `EdgeFlowStats(BaseModel)` with `from_node: str`, `to_node: str`, `record_count: int`, `percentage: float`; `PipelineFlowAnalyticsResponse(BaseModel)` with `pipeline_guid: str`, `pipeline_version: int`, `result_guid: str`, `result_created_at: datetime`, `total_records: int`, `nodes: List[NodeFlowStats]`, `edges: List[EdgeFlowStats]`
- [x] T038 [US5] Implement `get_flow_analytics(pipeline_id, team_id, result_guid=None)` method in `backend/src/services/pipeline_service.py`. Steps: (1) find target AnalysisResult — if `result_guid` provided, look up that specific result; otherwise find most recent COMPLETED result where `tool='pipeline_validation'` and `pipeline_id` matches; (2) extract `path_stats` from `results_json` — if absent, raise 404; (3) derive per-edge counts by iterating each path and summing `image_count` for every consecutive node pair (edge) in the path; (4) derive per-node counts by summing `image_count` for every node in every path; (5) calculate percentages — node percentages relative to Capture node total (global), edge percentages relative to upstream node total (shows branching behavior); (6) return `PipelineFlowAnalyticsResponse`
- [x] T039 [US5] Add `GET /api/pipelines/{guid}/flow-analytics` endpoint to `backend/src/api/pipelines.py`. Accept optional `result_guid` query parameter. Use `require_auth` and `get_tenant_context` dependencies (same as other pipeline endpoints). Resolve pipeline by GUID with team_id filtering. Call `get_flow_analytics` service method. Return 404 if pipeline not found or no results with path_stats exist. Return 400 for invalid GUID format
- [x] T040 [P] [US5] Add `getFlowAnalytics(guid, resultGuid?)` function to `frontend/src/services/pipelines.ts`. Validate GUID with `validateGuid(guid, 'pip')`. Call `GET /api/pipelines/${guid}/flow-analytics` with optional `result_guid` query param. Return typed `PipelineFlowAnalyticsResponse`
- [x] T041 [P] [US5] Add flow analytics TypeScript types to `frontend/src/contracts/api/pipelines-api.ts`: `NodeFlowStats`, `EdgeFlowStats`, `PipelineFlowAnalyticsResponse` interfaces per contracts/frontend-api.md
- [x] T042 [US5] Create `usePipelineAnalytics` hook in `frontend/src/hooks/usePipelineAnalytics.ts`. Props: `pipelineGuid: string | null`. Returns: `analytics` (PipelineFlowAnalyticsResponse | null), `loading`, `error`, `enabled` (true when analytics data is available — false when no results exist), `showFlow` (toggle state, default false), `setShowFlow(show)`, `refetch()`. Fetches flow analytics on mount when pipelineGuid is provided. Catches 404 gracefully (sets `enabled=false`)
- [x] T043 [P] [US5] Create `AnalyticsEdge.tsx` custom edge component in `frontend/src/components/pipelines/graph/edges/`. Extends the base edge with variable stroke width proportional to `record_count` (min 2px, max 20px, linear interpolation normalized against `maxCount` in edge data). Displays a label with count and percentage (e.g., "1,234 (87%)"). Zero-flow edges rendered as dashed lines with reduced opacity. Hover shows tooltip with detailed stats (count, percentage, source node, target node). Add to `edgeTypes` mapping in `edges/index.ts`
- [x] T044 [P] [US5] Create `AnalyticsOverlay.tsx` in `frontend/src/components/pipelines/graph/`. Contains: "Show Flow" toggle switch (labeled, with disabled state + tooltip when `!enabled`), flow legend (explains edge thickness mapping, min/max reference), background dimming class applied to graph container when active. Props per `AnalyticsOverlayProps` from contracts/frontend-api.md
- [x] T045 [US5] Integrate analytics into `PipelineGraphView.tsx` and `PipelineEditorPage.tsx`. In PipelineGraphView: accept optional `analytics` and `showFlow` props; when `showFlow=true`, pass analytics data to `toReactFlowEdges` to switch edge type to 'analytics' with flow data; add analytics count badges to node data. In PipelineEditorPage view mode: add `usePipelineAnalytics` hook; render `AnalyticsOverlay` in the view mode toolbar area; pass analytics data and showFlow to PipelineGraphView

### Tests

- [x] T046 [P] [US5] Create tests for the pipeline analyzer path_stats extension in `agent/tests/unit/test_pipeline_analyzer_paths.py`. Using pytest. Test cases: (1) analyzer output includes `path_stats` array when processing a collection; (2) simple Capture→File→Termination pipeline with 10 image groups all following the same path produces one entry with `image_count: 10`; (3) branching pipeline (Capture→Branch→FileA→TermA / →FileB→TermB) produces multiple path entries with correct counts per branch; (4) existing output fields (`status_counts`, `by_termination`, `validation_results`) remain unchanged after adding path_stats; (5) empty collection produces `path_stats: []`. Mock filesystem and pipeline data per existing `pipeline_analyzer` test patterns
- [x] T047 [P] [US5] Create tests for the flow analytics service and endpoint in `backend/tests/unit/test_flow_analytics.py`. Using pytest with the existing test database session fixture. Test `get_flow_analytics` service: (1) returns correct per-node and per-edge counts derived from path_stats — for paths `[A,B,C]` with count 100 and `[A,B,D]` with count 50, node A should have `record_count=150`, edge A→B should have `record_count=150`, edge B→C should have `record_count=100`, edge B→D should have `record_count=50`; (2) returns 404 when no analysis results exist for the pipeline; (3) returns 404 when results exist but have no `path_stats` key; (4) node percentages are calculated relative to Capture node total, edge percentages are calculated relative to upstream (source) node total — e.g., if A has 150 records and edge A→B has 100, then A→B percentage is 66.67%; (5) specific `result_guid` parameter selects the correct result. Test the endpoint: (6) GET returns 200 with valid data; (7) returns 404 for non-existent pipeline; (8) returns 400 for malformed GUID; (9) enforces tenant isolation (cross-team returns 404). Use existing conftest fixtures
- [x] T048 [P] [US5] Create tests for the usePipelineAnalytics hook in `frontend/src/hooks/__tests__/usePipelineAnalytics.test.ts`. Using vitest + `renderHook` + `vi.mock`. Mock the pipelines service (`getFlowAnalytics`). Test cases: (1) fetches analytics on mount when `pipelineGuid` is provided; (2) does not fetch when `pipelineGuid` is null; (3) sets `enabled=true` and populates `analytics` when fetch succeeds; (4) sets `enabled=false` when fetch returns 404 (no results); (5) `showFlow` defaults to false; `setShowFlow(true)` updates state; (6) `loading` is true during fetch, false after; (7) `error` is set when fetch fails with non-404 error; (8) `refetch` re-triggers the API call

**Checkpoint**: Flow analytics overlay is fully functional with tests. Users can visualize record flow through pipelines with proportional edge thickness, count labels, and tooltips.

---

## Phase 6: User Story 6 — Mobile/Tablet Pipeline Viewing (Priority: P3)

**Goal**: Support read-only pipeline graph viewing on touch devices with pan, zoom, and node inspection. Editing is disabled on small screens.

**Independent Test**: Open a pipeline view page on a mobile viewport (<768px) → graph renders in read-only mode, single-finger pan works, pinch-to-zoom works, tapping a node opens a bottom sheet with properties, edit button is hidden.

### Implementation

- [x] T049 [US6] Add responsive breakpoint handling to `PipelineGraphView.tsx` and `PipelineEditorPage.tsx`. Use a `useMediaQuery` or `window.matchMedia` hook to detect screen width. On screens <768px: ensure graph is read-only (already default in view mode), enable touch pan/zoom via React Flow's built-in touch support. On screens >=768px and <1024px: PropertyPanel collapses by default with a toggle button. On screens >=1024px: two-panel layout (default)
- [x] T050 [US6] Add mobile PropertyPanel variant to `PropertyPanel.tsx`. On screens <768px, render as a bottom sheet overlay (slide-up panel from bottom of screen) instead of a side panel. Use existing Radix UI Dialog/Sheet component from shadcn/ui. Triggered by tapping a node in the graph. Dismiss by swiping down or tapping outside
- [x] T051 [US6] Hide or disable edit controls on mobile in `PipelineEditorPage.tsx`. On screens <768px: hide the "Edit Pipeline" button with `hidden md:inline-flex` class. If user navigates directly to `/pipelines/{id}/edit` on mobile, show an informational message: "Pipeline editing requires a desktop browser" and display the read-only graph view instead

**Checkpoint**: Pipeline graphs are viewable on mobile and tablet devices with touch gesture support. Editing is desktop-only.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Performance optimization, accessibility, and final validation

- [x] T052 Verify all custom node components in `frontend/src/components/pipelines/graph/nodes/` are wrapped in `React.memo()`. Verify all callback props passed to `<ReactFlow>` use `useCallback()`. Verify analytics edge thickness calculations are memoized with `useMemo()`. Profile with React DevTools to confirm no unnecessary re-renders during pan/zoom
- [x] T053 Keyboard accessibility audit for the graph editor. Verify: Tab navigates between nodes and edges (React Flow built-in), Delete/Backspace removes selected items, Ctrl+Z/Ctrl+Shift+Z triggers undo/redo, Enter or Space on a node opens PropertyPanel, Escape closes PropertyPanel. Add `aria-label` attributes to custom nodes describing their type and ID. Verify screen reader announcements for node/edge operations
- [x] T054 Run all quickstart.md validation steps: backend schema tests (`venv/bin/python -m pytest backend/tests/unit/test_pipeline_schemas.py backend/tests/unit/test_flow_analytics.py -v`), frontend type check (`cd frontend && npx tsc --noEmit`), frontend unit tests (`cd frontend && npx vitest run --reporter=verbose`). Manually verify all phases against their checkpoint criteria

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1+US4(Read)+US7 (Phase 3)**: Depends on Foundational — this is the MVP
- **US2+US3+US4(Write) (Phase 4)**: Depends on Phase 3 (extends PipelineGraphView with editing)
- **US5 (Phase 5)**: Depends on Phase 3 (extends PipelineGraphView with analytics). Agent-side task T036 can start after Phase 1 (independent of frontend)
- **US6 (Phase 6)**: Depends on Phase 3 (adds responsive behavior to PipelineGraphView)
- **Polish (Phase 7)**: Depends on all desired phases being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational (Phase 2) — no dependencies on other stories
- **US7 (P1)**: Can start after Foundational (Phase 2) — independent, parallelizable with US1
- **US4 (P2)**: Split across US1 (read-side: auto-layout) and US2 (write-side: save positions)
- **US2 (P2)**: Depends on US1 (extends the graph view with editing capabilities)
- **US3 (P2)**: Depends on US2 (uses the same graph editor with onboarding additions)
- **US5 (P3)**: Depends on US1 (extends the graph view). Agent work (T036) is independent
- **US6 (P3)**: Depends on US1 (adds responsive behavior). Can run in parallel with US5

### Within Each Phase

```
Foundational:   T004 ──┐
                T005 ──┤ (all [P] impl tasks in parallel)
                T006 ──┤
                T007 ──┤
                T008 ──┤
                T009 ──┤
                T010 ──┤
                T011 ──┘──→ T012 (barrel exports need all components)
                T013 ──┐
                T014 ──┤ (test tasks [P], after their impl deps)
                T015 ──┤
                T016 ──┤
                T017 ──┘ (after T012)

Phase 3 (MVP):  T018 ──┐
                T019 ──┘──→ T020 (integration needs both) ──→ T022
                T021 (parallel with T018-T020, independent)
                T023 (after T021)
                T024 (after T020)

Phase 4 (Edit): T025 ──→ T026 ──→ T030 ──→ T031 ──→ T033
                T027 ──┘ (parallel)       ↗
                T029 ──────────────────────
                T028 (extends T019, can start after T026)
                T032 (after T031)
                T034 (after T025)
                T035 (after T026)

Phase 5 (Flow): T036 (agent, independent — can start early)
                T037 ──→ T038 ──→ T039
                T040 ──┐
                T041 ──┘(parallel)──→ T045
                T042 ──┘
                T043 ──┘
                T044 ──┘
                T046 (after T036)
                T047 (after T038-T039)
                T048 (after T042)

Phase 6 (Mobile): T049 ──→ T050 ──→ T051
```

### Parallel Opportunities

**Within Foundational (Phase 2)**: T005-T011 can all run in parallel (different files, no interdependencies). Only T012 (barrel exports) must wait for T009-T011. Test tasks T013-T016 can run in parallel once their implementation dependency is ready; T017 waits for T012.

**Across Phases**: T036 (agent-side pipeline analyzer) can start as early as Phase 1 since it's in a completely different codebase (`agent/`). Backend flow analytics (T037-T039) can start once T036 is designed but don't need T036 complete — they can use mock data.

**Within Phase 4**: T027 and T029 are parallelizable with T026. T025 can run in parallel with T026 start. Test tasks T034 and T035 can run in parallel with later impl tasks once their deps are ready.

**Within Phase 5**: T046 (agent test) is independent of frontend. T047 and T048 are parallelizable with each other after their impl deps complete.

---

## Parallel Example: Foundational Phase

```
# Launch all foundational impl tasks in parallel (different files):
T004: "Add NodePosition to backend/src/schemas/pipelines.py"
T005: "Add NodePosition to frontend/src/contracts/api/pipelines-api.ts"
T006: "Create node-defaults.ts"
T007: "Create graph-transforms.ts"
T008: "Create dagre-layout.ts"
T009: "Create CaptureNode + TerminationNode"
T010: "Create FileNode + ProcessNode + PairingNode + BranchingNode"
T011: "Create PipelineEdge edge component"

# Then barrel exports:
T012: "Create barrel exports" (needs T009-T011 complete)

# Then test tasks in parallel:
T013: "Test graph-transforms" (needs T007)
T014: "Test dagre-layout" (needs T008)
T015: "Test node-defaults" (needs T006)
T016: "Test NodePosition schema" (needs T004)
T017: "Test custom node components" (needs T012)
```

## Parallel Example: Phase 5 (Flow Analytics)

```
# Agent work can start independently:
T036: "Extend pipeline_analyzer.py" (agent codebase, independent)

# Backend in sequence:
T037 → T038 → T039 (schemas → service → endpoint)

# Frontend in parallel (after T041 types are added):
T040: "Add getFlowAnalytics service function"
T042: "Create usePipelineAnalytics hook"
T043: "Create AnalyticsEdge component"
T044: "Create AnalyticsOverlay component"

# Integration last:
T045: "Integrate analytics into PipelineGraphView"

# Tests in parallel (after their impl deps):
T046: "Test pipeline_analyzer path_stats" (after T036)
T047: "Test flow analytics backend" (after T038-T039)
T048: "Test usePipelineAnalytics hook" (after T042)
```

---

## Implementation Strategy

### MVP First (Phase 1-3: US1 + US4 Read + US7)

1. Complete Phase 1: Setup (install deps, create dirs)
2. Complete Phase 2: Foundational (schema, utilities, node components, tests)
3. Complete Phase 3: US1 + US7 (graph view integration, beta removal, test updates)
4. **STOP and VALIDATE**: Run all tests, then test against US1 acceptance scenarios (8 scenarios) and US7 (2 scenarios)
5. Deploy/demo — pipelines now render as visual graphs

### Incremental Delivery

1. Setup + Foundational → Foundation ready (with passing tests)
2. Phase 3 (US1+US7) → Visual graph view + beta removal → **Deploy (MVP!)**
3. Phase 4 (US2+US3+US4) → Full visual editor → **Deploy**
4. Phase 5 (US5) → Flow analytics → **Deploy**
5. Phase 6 (US6) → Mobile support → **Deploy**
6. Phase 7 → Polish → **Final release**

Each phase adds value independently. The form editor remains functional until Phase 4 replaces it, so there is no gap in editing capability.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- US4 (Layout Persistence) is split: read-side in Phase 3, write-side in Phase 4
- No database migration required in any phase — all changes within existing JSONB columns
- The existing form editor remains functional through Phase 3; it is only removed in Phase 4 (T033) after the graph editor is proven
- Agent work (T036) is in a separate codebase and can proceed in parallel with frontend phases
- Frontend tests follow co-located convention per `frontend/docs/testing.md`: `src/<path>/__tests__/<Name>.test.{ts,tsx}`
- Total: 54 tasks across 7 phases (42 implementation + 12 test tasks)
