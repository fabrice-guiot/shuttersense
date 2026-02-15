# Frontend API Contracts: Pipeline Visual Graph Editor

**Branch**: `209-pipeline-visual-editor` | **Date**: 2026-02-15

## Modified Contracts

### pipelines-api.ts (Extended)

**File**: `frontend/src/contracts/api/pipelines-api.ts`

#### New Types

```typescript
/** Canvas position for visual graph editor */
export interface NodePosition {
  x: number
  y: number
}
```

#### Modified Types

```typescript
/** Extended PipelineNode with optional position */
export interface PipelineNode {
  id: string
  type: NodeType
  properties: Record<string, unknown>
  position?: NodePosition  // NEW: optional canvas position
}
```

#### New Types (Phase 3 — Flow Analytics)

```typescript
/** Per-node flow statistics from pipeline validation results */
export interface NodeFlowStats {
  node_id: string
  record_count: number
  percentage: number
}

/** Per-edge flow statistics from pipeline validation results */
export interface EdgeFlowStats {
  from_node: string
  to_node: string
  record_count: number
  percentage: number
}

/** Response from GET /api/pipelines/{guid}/flow-analytics */
export interface PipelineFlowAnalyticsResponse {
  pipeline_guid: string
  pipeline_version: number
  result_guid: string
  result_created_at: string
  total_records: number
  nodes: NodeFlowStats[]
  edges: EdgeFlowStats[]
}
```

## New Service Functions

### pipelines.ts (Extended)

**File**: `frontend/src/services/pipelines.ts`

```typescript
/** Phase 3: Fetch flow analytics for a pipeline */
export async function getFlowAnalytics(
  guid: string,
  resultGuid?: string
): Promise<PipelineFlowAnalyticsResponse> {
  validateGuid(guid, 'pip')
  const params = resultGuid ? { result_guid: resultGuid } : {}
  const response = await api.get(
    `/pipelines/${encodeURIComponent(guid)}/flow-analytics`,
    { params }
  )
  return response.data
}
```

## New Hooks

### usePipelineGraph.ts

**File**: `frontend/src/hooks/usePipelineGraph.ts`

```typescript
interface UsePipelineGraphReturn {
  // React Flow state
  nodes: Node[]
  edges: Edge[]
  onNodesChange: OnNodesChange
  onEdgesChange: OnEdgesChange
  onConnect: OnConnect

  // Node operations
  addNode: (type: NodeType, position?: { x: number; y: number }) => void
  removeNode: (nodeId: string) => void
  updateNodeProperties: (nodeId: string, properties: Record<string, unknown>) => void

  // Edge operations
  removeEdge: (edgeId: string) => void

  // Layout
  applyAutoLayout: () => void

  // Undo/Redo
  undo: () => void
  redo: () => void
  canUndo: boolean
  canRedo: boolean

  // Serialization
  toApiFormat: () => { nodes: PipelineNode[]; edges: PipelineEdge[] }
  fromApiFormat: (nodes: PipelineNode[], edges: PipelineEdge[]) => void

  // Validation
  validationHints: string[]
  isValid: boolean

  // Dirty state
  isDirty: boolean
  resetDirty: () => void

  // Selection
  selectedNodeId: string | null
  selectedEdgeId: string | null
}
```

### usePipelineAnalytics.ts (Phase 3)

**File**: `frontend/src/hooks/usePipelineAnalytics.ts`

```typescript
interface UsePipelineAnalyticsReturn {
  analytics: PipelineFlowAnalyticsResponse | null
  loading: boolean
  error: string | null
  enabled: boolean        // Whether analytics data is available
  showFlow: boolean       // Toggle state
  setShowFlow: (show: boolean) => void
  refetch: () => Promise<void>
}
```

## New Components

### Graph Components

**Directory**: `frontend/src/components/pipelines/graph/`

#### PipelineGraphView.tsx (Phase 1)

```typescript
interface PipelineGraphViewProps {
  nodes: PipelineNode[]
  edges: PipelineEdge[]
  validationErrors?: string[] | null
  onNodeClick?: (nodeId: string) => void
  analytics?: PipelineFlowAnalyticsResponse | null  // Phase 3
  showFlow?: boolean                                 // Phase 3
}
```

Read-only graph visualization. Renders pipeline as directed graph with:
- Custom node components per type
- Minimap, zoom controls, fit-to-view
- Auto-layout when no positions saved
- Node click opens read-only property panel/popover
- Validation error indicators on affected nodes
- Analytics overlay when showFlow=true (Phase 3)

#### PipelineGraphEditor.tsx (Phase 2)

```typescript
interface PipelineGraphEditorProps {
  initialNodes: PipelineNode[]
  initialEdges: PipelineEdge[]
  onSave: (nodes: PipelineNode[], edges: PipelineEdge[]) => void
  onCancel: () => void
  onDirtyChange?: (isDirty: boolean) => void
}
```

Interactive graph editor. Wraps PipelineGraphView and adds:
- Node palette (drag-to-add)
- Handle-to-handle edge creation
- Property panel sidebar
- Undo/redo, auto-layout, snap-to-grid
- Connection validation
- Real-time validation hints

#### NodePalette.tsx (Phase 2)

```typescript
interface NodePaletteProps {
  existingNodeTypes: NodeType[]  // To disable Capture if one exists
  onAddNode: (type: NodeType) => void
}
```

#### PropertyPanel.tsx (Phase 2)

```typescript
interface PropertyPanelProps {
  node: PipelineNode | null
  edge: PipelineEdge | null
  mode: 'view' | 'edit'
  onUpdateProperties?: (nodeId: string, properties: Record<string, unknown>) => void
  onUpdateNodeId?: (oldId: string, newId: string) => void
  onDeleteNode?: (nodeId: string) => void
  onDeleteEdge?: (edgeId: string) => void
  onClose: () => void
}
```

#### EditorToolbar.tsx (Phase 2)

```typescript
interface EditorToolbarProps {
  onAutoLayout: () => void
  onUndo: () => void
  onRedo: () => void
  canUndo: boolean
  canRedo: boolean
  snapToGrid: boolean
  onToggleSnapToGrid: () => void
  isValid: boolean
  validationHints: string[]
}
```

#### AnalyticsOverlay.tsx (Phase 3)

```typescript
interface AnalyticsOverlayProps {
  analytics: PipelineFlowAnalyticsResponse
  showFlow: boolean
  onToggleFlow: (show: boolean) => void
}
```

### Custom Node Components

**Directory**: `frontend/src/components/pipelines/graph/nodes/`

All custom nodes follow the same pattern:

```typescript
interface PipelineNodeData {
  nodeId: string
  type: NodeType
  properties: Record<string, unknown>
  hasError?: boolean           // Validation error indicator
  isSelected?: boolean         // Selection highlight
  analyticsCount?: number      // Phase 3: record count badge
}

// Each node component:
interface CustomNodeProps extends NodeProps<PipelineNodeData> {}
```

| Component | Node Type | Visual |
|-----------|-----------|--------|
| `CaptureNode.tsx` | capture | Camera icon, blue, larger rounded rect, output handle only |
| `FileNode.tsx` | file | FileText icon, gray, rectangle, input + output handles |
| `ProcessNode.tsx` | process | Settings icon, purple, rectangle, input + output handles |
| `PairingNode.tsx` | pairing | Merge icon, teal, diamond shape, input + output handles |
| `BranchingNode.tsx` | branching | GitBranch icon, amber, diamond shape, input + output handles |
| `TerminationNode.tsx` | termination | Archive icon, green, double-border rounded rect, input handle only |

### Custom Edge Components

**Directory**: `frontend/src/components/pipelines/graph/edges/`

```typescript
// Standard pipeline edge (Phase 1)
// Uses smoothstep routing with arrow marker

// Analytics edge (Phase 3)
interface AnalyticsEdgeData {
  record_count: number
  percentage: number
  maxCount: number      // For thickness normalization
}
// Variable stroke width (2px-20px), count/percentage label, dashed if zero flow
```

### Graph Utilities

**Directory**: `frontend/src/components/pipelines/graph/utils/`

#### graph-transforms.ts

```typescript
/** Convert API pipeline data to React Flow format */
export function toReactFlowNodes(
  apiNodes: PipelineNode[],
  validationErrors?: string[] | null
): Node<PipelineNodeData>[]

/** Convert API edges to React Flow format */
export function toReactFlowEdges(
  apiEdges: PipelineEdge[],
  analytics?: PipelineFlowAnalyticsResponse | null
): Edge[]

/** Convert React Flow state back to API format */
export function toApiNodes(rfNodes: Node<PipelineNodeData>[]): PipelineNode[]
export function toApiEdges(rfEdges: Edge[]): PipelineEdge[]

/** Check if pipeline has saved positions */
export function hasPositions(nodes: PipelineNode[]): boolean
```

#### dagre-layout.ts

```typescript
/**
 * Apply dagre auto-layout to nodes and edges.
 *
 * Pipeline graphs can contain cycles. The layout algorithm handles this by:
 * 1. Computing an acyclic projection (forward traversal from Capture node;
 *    edges whose target is already visited are "back-edges" and excluded)
 * 2. Running dagre on the acyclic projection (produces clean top-to-bottom flow)
 * 3. Returning positioned nodes — back-edges are drawn by React Flow using
 *    the existing node positions without further adjustment
 *
 * Users may manually reposition nodes after auto-layout to improve the
 * visual clarity of back-edges (cycle-introducing edges).
 */
export function applyDagreLayout(
  nodes: Node[],
  edges: Edge[],
  options?: {
    direction?: 'TB' | 'LR'   // Default: 'TB'
    nodeSep?: number           // Default: 80
    rankSep?: number           // Default: 100
  }
): Node[]

/** Identify back-edges that introduce cycles in the pipeline graph */
export function findBackEdges(
  nodes: Node[],
  edges: Edge[],
  captureNodeId: string
): Edge[]
```

#### connection-rules.ts

```typescript
/** Validate whether a connection is allowed */
export function isValidConnection(
  connection: Connection,
  nodes: Node<PipelineNodeData>[],
  edges: Edge[]
): boolean

/** Get connection validation error message */
export function getConnectionError(
  connection: Connection,
  nodes: Node<PipelineNodeData>[],
  edges: Edge[]
): string | null
```

#### node-defaults.ts

```typescript
/** Generate a unique node ID for a given type */
export function generateNodeId(type: NodeType, existingIds: string[]): string

/** Get the node visual config (icon, color, shape) for a type */
export function getNodeConfig(type: NodeType): {
  icon: LucideIcon
  colorClass: string
  shapeClass: string
  defaultWidth: number
  defaultHeight: number
}

/** Get default properties for a node type */
export function getDefaultProperties(type: NodeType): Record<string, unknown>
```
