# Feature Specification: Pipeline Visual Graph Editor

**Feature Branch**: `209-pipeline-visual-editor`
**Created**: 2026-02-15
**Status**: Draft
**Input**: GitHub issue #171, based on PRD: docs/prd/pipeline-visual-editor.md
**Issue**: [#171 - Pipeline Visual Graph Editor (React Flow)](https://github.com/fabrice-guiot/shuttersense/issues/171)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Pipeline as a Visual Graph (Priority: P1)

A team member opens a pipeline to understand its structure. Instead of reading a flat list of nodes and edges, they see an interactive directed graph: a Capture node at the top flows downward through File, Process, Pairing, and Branching nodes to Termination nodes at the bottom. Each node type has a distinct icon, color, and shape. The user pans, zooms, and clicks nodes to inspect their properties. For larger pipelines, a minimap provides orientation.

**Why this priority**: This is the foundational capability. Without visual rendering, no other graph feature has value. It also addresses the primary pain point: users cannot reason about complex pipeline topologies from flat lists.

**Independent Test**: Can be fully tested by navigating to any existing pipeline's view page and verifying the graph renders correctly with proper node types, edges, pan/zoom, and node inspection.

**Acceptance Scenarios**:

1. **Given** a pipeline with 5+ nodes and multiple edges, **When** the user opens the pipeline view page, **Then** the pipeline is rendered as a directed graph with nodes positioned top-to-bottom (Capture at top, Termination at bottom).
2. **Given** a pipeline graph is displayed, **When** the user scrolls or pinches, **Then** the graph zooms in/out smoothly.
3. **Given** a pipeline graph is displayed, **When** the user clicks and drags the canvas, **Then** the view pans.
4. **Given** a pipeline graph is displayed, **When** the user clicks a node, **Then** a panel or popover shows all properties for that node in read-only mode.
5. **Given** a pipeline with 10+ nodes, **When** the graph is rendered, **Then** a minimap is visible showing the overall graph structure.
6. **Given** a pipeline with validation errors, **When** the graph is displayed, **Then** affected nodes show a visual error indicator (e.g., red border, error icon).
7. **Given** a pipeline with version history, **When** the user selects a historical version from the version picker, **Then** the graph renders that version's structure and layout.
8. **Given** each node type (Capture, File, Process, Pairing, Branching, Termination), **When** the graph renders, **Then** each type has a visually distinct icon, color, and shape.

---

### User Story 2 - Edit Pipeline Visually (Priority: P2)

A team member opens an existing pipeline for editing. The graph becomes interactive: they can drag nodes to rearrange the layout, drag connections between node handles to create edges, click nodes to edit properties in a side panel, and delete nodes or edges. Real-time validation feedback shows whether the pipeline is valid. Undo/redo allows safe experimentation. When satisfied, they save the pipeline.

**Why this priority**: This replaces the error-prone form-based editor. Visual edge creation (handle-to-handle dragging) eliminates the mental mapping required by dropdown-based edge creation, which is the second most significant user pain point.

**Independent Test**: Can be tested by opening any pipeline in edit mode, making structural changes (add/remove nodes, create/delete edges, edit properties), verifying validation feedback, and saving successfully.

**Acceptance Scenarios**:

1. **Given** the user is in edit mode, **When** they drag a node type from the palette onto the canvas, **Then** a new node of that type is added to the graph.
2. **Given** a Capture node already exists, **When** the user attempts to add a second Capture node, **Then** the system prevents it and shows a validation message.
3. **Given** two nodes on the canvas, **When** the user drags from a source node's output handle to a target node's input handle, **Then** a directed edge is created between them.
4. **Given** the user drags an edge toward a Capture node's input, **Then** the connection is rejected (Capture nodes cannot be edge targets).
5. **Given** the user drags an edge from a Termination node, **Then** the connection is rejected (Termination nodes cannot be edge sources).
6. **Given** a node is selected, **When** the user presses Delete/Backspace, **Then** the node and all its connected edges are removed.
7. **Given** the user has made changes, **When** they press Ctrl+Z, **Then** the last change is undone; Ctrl+Shift+Z redoes it.
8. **Given** the user selects a node, **When** the property panel opens, **Then** they can edit type-specific properties with inline validation.
9. **Given** the pipeline is missing a required Termination node, **Then** a validation hint is displayed contextually on the canvas.
10. **Given** the user has unsaved changes and clicks Cancel, **Then** a confirmation dialog appears before discarding changes.
11. **Given** the user clicks Save, **Then** the current graph state (nodes, edges, and positions) is persisted.

---

### User Story 3 - Create Pipeline Visually (Priority: P2)

A team member creates a new pipeline. They see an empty canvas with a helpful prompt guiding them to start by adding a Capture node. After placing the Capture node, contextual hints guide them to connect File nodes. They build the pipeline graph visually, configure node properties, and save.

**Why this priority**: Same priority as editing since it uses the same visual editor. The onboarding guidance makes pipeline creation intuitive for new users.

**Independent Test**: Can be tested by navigating to "Create Pipeline," following the onboarding prompts, building a simple pipeline (Capture -> File -> Termination), and saving.

**Acceptance Scenarios**:

1. **Given** the user navigates to create a new pipeline, **When** the editor loads, **Then** an empty canvas is shown with a prompt: "Drag a Capture node from the palette to start building your pipeline."
2. **Given** the palette is visible, **Then** the Capture node type is visually highlighted as the recommended first step.
3. **Given** the user has placed a Capture node, **Then** a contextual hint suggests connecting it to File nodes.
4. **Given** the user builds a valid pipeline and clicks Save, **Then** the pipeline is created and the user is navigated to the view page.

---

### User Story 4 - Persistent Visual Layout (Priority: P2)

A team member carefully arranges their pipeline graph layout so that the visual structure is easy to understand. When they save and later reopen the pipeline, the layout is exactly as they left it. Other team members see the same layout. An "Auto Layout" button lets anyone reset to an automatic arrangement.

**Why this priority**: Layout persistence ensures the visual editor is practical for repeated use. Without it, users would need to rearrange nodes every time they open a pipeline.

**Independent Test**: Can be tested by arranging nodes, saving, reopening the pipeline, and verifying positions match. Also test the Auto Layout button resets positions.

**Acceptance Scenarios**:

1. **Given** the user drags nodes to custom positions and saves, **When** they reopen the pipeline, **Then** nodes appear at the saved positions.
2. **Given** a pipeline was created before the visual editor existed (no saved layout), **When** the user opens it, **Then** nodes are automatically arranged top-to-bottom by an auto-layout algorithm.
3. **Given** the user clicks "Auto Layout" in edit mode, **Then** all nodes are repositioned using the automatic layout algorithm. This change is unsaved until explicitly saved.
4. **Given** a pipeline with saved layout is exported to YAML, **Then** the exported file includes position data. Importing a YAML file with positions restores them.
5. **Given** the pipeline has version history with layouts, **When** viewing a historical version, **Then** the layout from that version is displayed.

---

### User Story 5 - Visualize Record Flow Through Pipeline (Priority: P3)

After running a pipeline validation analysis, a team member wants to understand how records flowed through the pipeline. They toggle "Show Flow" in the view toolbar. Edge thickness changes to reflect how many records traversed each link, and labels show counts and percentages. Node badges show record counts. A legend explains the visual encoding. Hovering reveals detailed statistics.

**Why this priority**: This extends the graph view with analytics data. It requires analysis results to exist and a new data endpoint, making it a natural Phase 3 capability.

**Independent Test**: Can be tested by running pipeline_validation on a pipeline, then opening the pipeline view and toggling the analytics overlay to verify flow data is visualized correctly.

**Acceptance Scenarios**:

1. **Given** analysis results exist for a pipeline, **When** the user toggles "Show Flow," **Then** edges display thickness proportional to record volume and labels showing count/percentage.
2. **Given** analytics mode is active, **When** the user hovers over an edge, **Then** a tooltip shows detailed flow statistics (count, percentage, source node, target node).
3. **Given** analytics mode is active, **Then** each node displays a badge showing how many records reached it.
4. **Given** analytics mode is active, **Then** a legend explains the edge thickness and color mapping.
5. **Given** an edge with zero records flowing through it, **Then** it is rendered as a dashed line with reduced opacity.
6. **Given** no analysis results exist for the pipeline, **Then** the "Show Flow" toggle is disabled with a tooltip explaining that analysis must be run first.
7. **Given** analytics mode is active, **Then** the graph background dims slightly to increase contrast of the flow visualization.

---

### User Story 6 - Mobile/Tablet Pipeline Viewing (Priority: P3)

A team member views a pipeline graph on a tablet or mobile device. They can pan with a finger, pinch to zoom, and tap nodes to inspect properties. Editing is not available on small screens.

**Why this priority**: Read-only viewing on touch devices is a nice-to-have that extends accessibility without the complexity of touch-based editing.

**Independent Test**: Can be tested by opening a pipeline view on a tablet/mobile viewport and verifying pan, zoom, and node inspection work via touch.

**Acceptance Scenarios**:

1. **Given** a screen width below 768px, **When** the user opens a pipeline view, **Then** the graph is displayed in read-only mode with pan and zoom only.
2. **Given** a touch device, **When** the user uses single-finger drag, **Then** the view pans. Pinch-to-zoom works for zooming.
3. **Given** a touch device, **When** the user taps a node, **Then** a bottom sheet or overlay shows node properties.
4. **Given** a screen width below 768px, **Then** the edit button is hidden or disabled with a message that editing requires a desktop browser.

---

### User Story 7 - Beta Label Removal (Priority: P1)

When viewing the pipeline list or opening a pipeline, the "Beta Feature" banners are no longer displayed. This signals to users that the pipeline feature is mature and fully supported.

**Why this priority**: P1 because it is trivially simple and directly tied to delivering the graph view. Once the visual editor replaces the placeholder, the beta label is misleading.

**Independent Test**: Navigate to the pipeline list and pipeline editor pages and verify no beta banners or "Coming Soon" placeholders appear.

**Acceptance Scenarios**:

1. **Given** the user opens the pipelines list page, **Then** no "Beta Feature" banner is displayed.
2. **Given** the user opens a pipeline view or editor, **Then** no "Beta Feature" banner or "Coming Soon" graph placeholder is displayed.

---

### Edge Cases

- What happens when a pipeline has no nodes? The graph displays the empty canvas with an onboarding prompt (User Story 3).
- What happens when two users edit the same pipeline simultaneously? Last-save-wins (no real-time collaboration). The save operation uses existing version conflict handling.
- What happens when a pipeline has cycles? Cycles are allowed. The graph renders them with a visual indicator (e.g., a subtle badge on back-edges).
- What happens when a Pairing node has fewer or more than 2 incoming edges? A visual indicator warns about the constraint violation.
- What happens when a very large pipeline (30+ nodes) is displayed? The minimap and fit-to-view controls help with navigation. Performance remains smooth for up to 50 nodes.
- What happens when a YAML file is imported without position data? Auto-layout is applied. Position data is optional in YAML format.
- What happens when analytics results are from a different pipeline version than the current? The system uses the most recent analysis result; a visual indicator shows if the result is from an older version.

## Requirements *(mandatory)*

### Functional Requirements

#### Graph Visualization (View Mode)

- **FR-001**: System MUST render pipelines as directed graphs with nodes positioned according to saved layout or auto-layout when no saved layout exists.
- **FR-002**: System MUST display each node type with a distinct visual treatment (icon, color, shape) — Capture (camera icon, blue, larger rounded rectangle), File (document icon, gray, rectangle), Process (gear icon, purple, rectangle), Pairing (merge icon, teal, diamond/hexagon), Branching (branch icon, amber, diamond/hexagon), Termination (archive icon, green, double-border rounded rectangle).
- **FR-003**: Nodes MUST display their ID, type label, and key properties (e.g., extension for File nodes).
- **FR-004**: Edges MUST be rendered as directed arrows flowing generally top-to-bottom.
- **FR-005**: The graph canvas MUST support pan (drag), zoom (scroll/pinch), and fit-to-view (button).
- **FR-006**: A minimap MUST be displayed for orientation in larger pipelines.
- **FR-007**: Zoom controls (zoom in, zoom out, fit view) MUST be available.
- **FR-008**: Clicking a node MUST open a read-only panel showing all node properties.
- **FR-009**: Validation errors MUST be indicated visually on affected nodes (e.g., red border, error icon).
- **FR-010**: The version picker MUST continue to work — selecting a historical version renders that version's graph.
- **FR-011**: In view mode, the graph MUST be non-interactive beyond pan, zoom, and node inspection.

#### Graph Editor (Edit/Create Mode)

- **FR-012**: Users MUST be able to add nodes via a palette/toolbar listing available node types, using drag-to-canvas or click-to-add interaction.
- **FR-013**: System MUST enforce that only one Capture node exists per pipeline. The palette disables the Capture option when one exists.
- **FR-014**: Users MUST be able to reposition nodes by dragging on the canvas.
- **FR-015**: Selecting a node MUST open a side panel for configuring type-specific node properties with real-time inline validation.
- **FR-016**: Users MUST be able to delete nodes via context menu, keyboard shortcut (Delete/Backspace), or delete button in the property panel. Deleting a node removes all connected edges.
- **FR-017**: Each node MUST be assigned a unique ID with a suggested default based on type (e.g., `file_1`, `process_2`) that the user can rename.
- **FR-018**: Edges MUST be created by dragging from a source node's output handle to a target node's input handle.
- **FR-019**: Connection validation MUST prevent invalid edges at creation time: Termination nodes cannot be sources, Capture nodes cannot be targets, duplicate edges are rejected.
- **FR-020**: Pairing nodes MUST show a visual indicator when they have fewer or more than exactly 2 incoming edges.
- **FR-021**: Edges MUST be deletable by selecting and pressing Delete/Backspace or via context menu.
- **FR-022**: Cycles MUST be allowed (consistent with existing pipeline validation rules). The graph SHOULD visually indicate when a cycle exists.
- **FR-023**: An "Auto Layout" button MUST apply automatic layout to all nodes.
- **FR-024**: Undo/Redo (Ctrl+Z / Ctrl+Shift+Z) MUST be supported for node operations, edge operations, moves, and property changes.
- **FR-025**: Multi-select (Shift+click or lasso) MUST allow bulk deletion of nodes and edges.
- **FR-026**: Snap-to-grid MUST be toggleable for precise node placement.
- **FR-027**: Pipeline metadata fields (name, description, change summary) MUST remain as form inputs alongside the graph canvas.
- **FR-028**: Save MUST persist the current graph state (nodes, edges, positions). Cancel MUST discard unsaved changes with a confirmation dialog if changes exist.
- **FR-029**: Live validation indicators MUST show the current pipeline validity state (Valid/Invalid) as the user edits.
- **FR-030**: Validation hints (e.g., "At least one Termination node required") MUST be displayed contextually.

#### Layout Persistence

- **FR-031**: Each node's position (x, y coordinates) MUST be stored as part of the pipeline data.
- **FR-032**: Layout data MUST be included in pipeline version history snapshots.
- **FR-033**: YAML import/export MUST include position data when present and omit it when absent (backward-compatible).
- **FR-034**: Pre-existing pipelines without position data MUST use auto-layout. Users can save the generated layout by editing and saving the pipeline.

#### Flow Analytics Overlay

- **FR-035**: In view mode, a "Show Flow" toggle MUST enable flow visualization on the pipeline graph.
- **FR-036**: When analytics mode is active, edges MUST display thickness proportional to record volume and labels with count and/or percentage.
- **FR-037**: Nodes in analytics mode MUST display a count badge showing records that reached that node.
- **FR-038**: Analytics data MUST be derived from the most recent completed analysis result for the pipeline.
- **FR-039**: If no analysis results exist, the analytics toggle MUST be disabled with an explanatory tooltip.
- **FR-040**: A legend MUST explain edge thickness and color mapping.
- **FR-041**: Edge thickness MUST be bounded (minimum and maximum) to maintain readability.
- **FR-042**: Hovering over edges or nodes in analytics mode MUST display tooltips with detailed flow statistics.
- **FR-043**: Edges with zero flow MUST be rendered as dashed lines with reduced opacity.

#### Beta Label Removal

- **FR-044**: The "Beta Feature" banners MUST be removed from the pipeline list page and pipeline editor page.
- **FR-045**: The "Coming Soon" graph placeholder MUST be removed from the pipeline editor page.

### Key Entities

- **Pipeline**: Existing entity representing a photo processing workflow. Contains an ordered graph of nodes and edges. Extended with per-node position data for visual layout.
- **Pipeline Node**: A step in the pipeline (Capture, File, Process, Pairing, Branching, or Termination). Extended with optional x/y canvas position.
- **Pipeline Edge**: A directed connection between two pipeline nodes, representing record flow from source to target.
- **Pipeline Version History**: Snapshot of a pipeline at a point in time. Now includes node positions in the snapshot.
- **Flow Analytics Data**: Per-node and per-edge traversal statistics derived from pipeline validation analysis results. Includes record counts and percentages.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can understand a pipeline's topological structure within 10 seconds of opening the view page (compared to manually tracing node/edge lists).
- **SC-002**: Users can create a new pipeline with 5 nodes and appropriate edges in under 3 minutes using the visual editor.
- **SC-003**: Users can add a new edge between existing nodes in under 5 seconds (drag handle-to-handle), compared to the current multi-step dropdown workflow.
- **SC-004**: The graph view comfortably renders pipelines with up to 50 nodes without noticeable lag or jank.
- **SC-005**: Pipeline layouts persist across sessions — reopening a saved pipeline shows nodes in the exact positions where the user placed them.
- **SC-006**: 90% of pipeline editing tasks (add node, connect edge, delete node, edit properties) can be completed without referring to documentation.
- **SC-007**: Users can identify record flow bottlenecks in a pipeline within 15 seconds of enabling the analytics overlay.
- **SC-008**: The visual editor is accessible via keyboard — all node and edge operations can be performed without a mouse.
- **SC-009**: The "Beta Feature" banners are no longer visible anywhere in the pipeline feature.
- **SC-010**: Existing pipelines (created before the visual editor) display correctly using automatic layout with no data loss or behavior changes.

## Assumptions

- **Edge labels in normal view mode**: Directional arrows are sufficient without text labels in non-analytics mode. The arrow direction and node type icons provide enough context about the relationship between nodes.
- **Side-by-side version comparison**: Not included in this feature scope. The existing version picker (switching between versions one at a time) provides sufficient version review capability. Side-by-side comparison may be considered as a separate future enhancement.
- **Dark mode**: The visual editor follows the existing design system theming approach. If the application already supports dark mode via design tokens, the graph editor inherits that support. No additional dark-mode-specific work is scoped.
- **Analytics data availability**: The flow analytics overlay depends on per-node and per-edge traversal data being available in pipeline validation analysis results. If this data is not currently captured by the pipeline_validation tool, the tool output format will need to be extended as a prerequisite for the analytics overlay phase.
- **Performance**: Typical pipelines have 5-15 nodes. The graph must handle up to 50 nodes smoothly, which is well within standard graph visualization library capabilities.
- **No real-time collaboration**: Pipeline editing is single-user. Concurrent edits use last-save-wins semantics with existing version conflict handling.

## Phased Delivery

This feature is recommended for phased delivery to reduce risk and enable incremental user feedback:

### Phase 1: Graph View + Layout Persistence + Beta Label Removal
- User Stories 1 (View Graph), 4 (Layout Persistence), 7 (Beta Label Removal)
- FR-001 through FR-011, FR-031 through FR-034, FR-044, FR-045
- **Outcome**: Users see pipelines as graphs with persistent layouts. Form editor remains for editing. Beta labels removed.

### Phase 2: Graph Editor
- User Stories 2 (Edit Pipeline), 3 (Create Pipeline)
- FR-012 through FR-030
- **Outcome**: Users create and edit pipelines visually. Form editor deprecated and removed.

### Phase 3: Flow Analytics + Mobile View
- User Stories 5 (Flow Analytics), 6 (Mobile/Tablet)
- FR-035 through FR-043
- **Outcome**: Users visualize record flow through pipelines. Touch device support for viewing.
