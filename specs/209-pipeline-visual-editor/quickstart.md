# Quickstart: Pipeline Visual Graph Editor

**Branch**: `209-pipeline-visual-editor` | **Date**: 2026-02-15

## Prerequisites

- Node.js 18+ and npm
- Python 3.11+ with venv
- PostgreSQL 12+ (or SQLite for tests)
- Existing ShutterSense development environment

## Setup

### 1. Install New Frontend Dependencies

```bash
cd frontend
npm install @xyflow/react @dagrejs/dagre
npm install -D @types/dagre  # Type definitions for dagre
```

### 2. Import React Flow Styles

Add to `frontend/src/index.css` (or equivalent global CSS entry):

```css
@import '@xyflow/react/dist/style.css';
```

### 3. Backend — No Setup Required

No database migration needed. The `position` field is added to `PipelineNode` Pydantic schema only. JSONB columns accept any structure.

## Development Workflow

### Phase 1: Graph View + Layout Persistence

**Start with**:
1. Backend schema extension (`NodePosition` in `pipelines.py`)
2. Graph transform utilities (`graph-transforms.ts`, `dagre-layout.ts`)
3. Custom node components (6 types in `nodes/`)
4. `PipelineGraphView` component
5. Integrate into `PipelineEditorPage` view mode
6. Remove beta banners

**Verify**:
```bash
# Backend schema tests
venv/bin/python -m pytest backend/tests/unit/test_pipeline_schemas.py -v

# Frontend type check
cd frontend && npx tsc --noEmit

# Frontend unit tests
cd frontend && npx vitest run --reporter=verbose
```

### Phase 2: Graph Editor

**Start with**:
1. `usePipelineGraph` hook (state management + undo/redo)
2. Connection validation rules (`connection-rules.ts`)
3. `NodePalette` component
4. `PropertyPanel` component (extract from PipelineEditorPage)
5. `EditorToolbar` component
6. `PipelineGraphEditor` component
7. Integrate into `PipelineEditorPage` edit/create modes
8. Remove form-based editor components

**Verify**:
```bash
cd frontend && npx vitest run --reporter=verbose
cd frontend && npx tsc --noEmit
```

### Phase 3: Flow Analytics

**Start with**:
1. Agent-side: Extend `pipeline_analyzer.py` to emit `path_stats`
2. Backend: Add flow analytics endpoint and schemas
3. Frontend: `usePipelineAnalytics` hook
4. Frontend: `AnalyticsEdge` custom edge component
5. Frontend: `AnalyticsOverlay` component (toggle, legend)
6. Integrate into `PipelineGraphView`

**Verify**:
```bash
# Backend tests
venv/bin/python -m pytest backend/tests/unit/test_flow_analytics.py -v

# Frontend
cd frontend && npx vitest run --reporter=verbose
cd frontend && npx tsc --noEmit
```

## Key Files Reference

| File | Purpose | Phase |
|------|---------|-------|
| `backend/src/schemas/pipelines.py` | NodePosition schema | 1 |
| `frontend/src/components/pipelines/graph/utils/graph-transforms.ts` | API ↔ React Flow conversion | 1 |
| `frontend/src/components/pipelines/graph/utils/dagre-layout.ts` | Auto-layout | 1 |
| `frontend/src/components/pipelines/graph/nodes/*.tsx` | Custom node components | 1 |
| `frontend/src/components/pipelines/graph/PipelineGraphView.tsx` | Read-only graph | 1 |
| `frontend/src/pages/PipelineEditorPage.tsx` | Main page (rewrite) | 1-2 |
| `frontend/src/pages/PipelinesPage.tsx` | Remove beta banner | 1 |
| `frontend/src/hooks/usePipelineGraph.ts` | Graph state + undo/redo | 2 |
| `frontend/src/components/pipelines/graph/utils/connection-rules.ts` | Edge validation | 2 |
| `frontend/src/components/pipelines/graph/PipelineGraphEditor.tsx` | Interactive editor | 2 |
| `frontend/src/components/pipelines/graph/NodePalette.tsx` | Node palette | 2 |
| `frontend/src/components/pipelines/graph/PropertyPanel.tsx` | Property editing | 2 |
| `agent/src/analysis/pipeline_analyzer.py` | Add node/edge stats | 3 |
| `backend/src/api/pipelines.py` | Flow analytics endpoint | 3 |
| `frontend/src/hooks/usePipelineAnalytics.ts` | Analytics data hook | 3 |
| `frontend/src/components/pipelines/graph/edges/AnalyticsEdge.tsx` | Variable-thickness edges | 3 |

## React Flow Key Patterns

### Custom Node Component

```tsx
import { Handle, Position, type NodeProps } from '@xyflow/react'
import { memo } from 'react'

const FileNode = memo(({ data }: NodeProps<PipelineNodeData>) => (
  <div className={cn(
    'rounded border-2 bg-card px-3 py-2 shadow-sm',
    data.hasError ? 'border-destructive' : 'border-muted'
  )}>
    <Handle type="target" position={Position.Top} />
    <div className="flex items-center gap-2">
      <FileText className="h-4 w-4 text-muted-foreground" />
      <span className="text-sm font-medium">{data.nodeId}</span>
    </div>
    <Handle type="source" position={Position.Bottom} />
  </div>
))
```

### ReactFlow Canvas Setup

```tsx
import { ReactFlow, MiniMap, Controls, Background } from '@xyflow/react'

<ReactFlow
  nodes={nodes}
  edges={edges}
  nodeTypes={nodeTypes}  // Custom node component mapping
  edgeTypes={edgeTypes}  // Custom edge component mapping
  onNodesChange={onNodesChange}
  onEdgesChange={onEdgesChange}
  onConnect={onConnect}
  isValidConnection={isValidConnection}
  fitView
  minZoom={0.1}
  maxZoom={2}
>
  <MiniMap />
  <Controls />
  <Background variant="dots" gap={16} />
</ReactFlow>
```

### Dagre Layout (with cycle handling)

Pipeline graphs can contain cycles. The layout uses an acyclic projection:

```tsx
import dagre from '@dagrejs/dagre'

function applyDagreLayout(nodes, edges) {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'TB', nodesep: 80, ranksep: 100 })

  // Step 1: Find the Capture node (entry point)
  const captureNode = nodes.find(n => n.data.type === 'capture')

  // Step 2: Compute acyclic projection — exclude back-edges
  const backEdges = findBackEdges(nodes, edges, captureNode?.id)
  const forwardEdges = edges.filter(e => !backEdges.includes(e))

  // Step 3: Run dagre on forward edges only
  nodes.forEach(node => g.setNode(node.id, { width: 200, height: 60 }))
  forwardEdges.forEach(edge => g.setEdge(edge.source, edge.target))
  dagre.layout(g)

  // Step 4: Position nodes — back-edges drawn by React Flow as-is
  return nodes.map(node => {
    const pos = g.node(node.id)
    return { ...node, position: { x: pos.x - 100, y: pos.y - 30 } }
  })
}
```

## Testing Approach

- **Unit tests**: Graph transforms, dagre layout, connection rules, node defaults
- **Component tests**: Custom node rendering per type, property panel, toolbar
- **Integration tests** (backend): NodePosition schema validation, flow analytics endpoint
- **Manual testing**: Drag-and-drop interactions, keyboard shortcuts, touch gestures
