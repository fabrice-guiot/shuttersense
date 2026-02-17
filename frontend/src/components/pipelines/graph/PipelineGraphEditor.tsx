import { useCallback, useEffect, useImperativeHandle, useRef, useState, forwardRef, type DragEvent } from 'react'
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  BackgroundVariant,
  type NodeMouseHandler,
  type ReactFlowInstance,
  type Node,
  type Edge,
} from '@xyflow/react'
import type { PipelineNodeData } from '@/contracts/api/pipelines-api'
import type {
  PipelineNode,
  PipelineEdge,
  NodeType,
} from '@/contracts/api/pipelines-api'
import { PipelineEditorProvider } from './PipelineEditorContext'
import { nodeTypes } from './nodes'
import MiniMapNode from './nodes/MiniMapNode'
import { edgeTypes } from './edges'
import { NodePalette } from './NodePalette'
import { EditorToolbar } from './EditorToolbar'
import { PropertyPanel } from './PropertyPanel'
import { usePipelineGraph } from '@/hooks/usePipelineGraph'
import { toApiNodes } from './utils/graph-transforms'

export interface PipelineGraphEditorHandle {
  save: () => { nodes: PipelineNode[]; edges: PipelineEdge[] }
  isDirty: boolean
  isValid: boolean
}

interface PipelineGraphEditorProps {
  initialNodes: PipelineNode[]
  initialEdges: PipelineEdge[]
  onDirtyChange?: (isDirty: boolean) => void
}

export const PipelineGraphEditor = forwardRef<PipelineGraphEditorHandle, PipelineGraphEditorProps>(
  function PipelineGraphEditor({ initialNodes, initialEdges, onDirtyChange }, ref) {
    const graph = usePipelineGraph()
    const reactFlowWrapper = useRef<HTMLDivElement>(null)
    const reactFlowInstance = useRef<ReactFlowInstance<Node<PipelineNodeData>, Edge> | null>(null)
    const [snapToGrid, setSnapToGrid] = useToggle(false)

    // Expose imperative methods to parent
    useImperativeHandle(ref, () => ({
      save: () => graph.toApiFormat(),
      isDirty: graph.isDirty,
      isValid: graph.isValid,
    }), [graph])

    // Initialize graph from API data on mount
    useEffect(() => {
      graph.fromApiFormat(initialNodes, initialEdges)
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []) // intentionally run once

    // Notify parent of dirty state changes
    useEffect(() => {
      onDirtyChange?.(graph.isDirty)
    }, [graph.isDirty, onDirtyChange])

    // Keyboard shortcuts
    useEffect(() => {
      const handler = (e: KeyboardEvent) => {
        // Undo: Ctrl+Z (without Shift)
        if (e.key === 'z' && (e.ctrlKey || e.metaKey) && !e.shiftKey) {
          e.preventDefault()
          graph.undo()
        }
        // Redo: Ctrl+Shift+Z
        if (e.key === 'z' && (e.ctrlKey || e.metaKey) && e.shiftKey) {
          e.preventDefault()
          graph.redo()
        }
        // Delete selected
        if (e.key === 'Delete' || e.key === 'Backspace') {
          // Don't delete if focus is in an input/textarea
          const tag = (e.target as HTMLElement)?.tagName
          if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return

          if (graph.selectedNodeId) {
            graph.removeNode(graph.selectedNodeId)
          } else if (graph.selectedEdgeId) {
            graph.removeEdge(graph.selectedEdgeId)
          }
        }
        // Escape closes property panel
        if (e.key === 'Escape') {
          graph.setSelectedNodeId(null)
          graph.setSelectedEdgeId(null)
        }
      }
      window.addEventListener('keydown', handler)
      return () => window.removeEventListener('keydown', handler)
    }, [graph])

    // Node click
    const handleNodeClick: NodeMouseHandler = useCallback(
      (_event, node) => {
        graph.setSelectedNodeId(node.id)
        graph.setSelectedEdgeId(null)
      },
      [graph],
    )

    // Edge click
    const handleEdgeClick = useCallback(
      (_event: React.MouseEvent, edge: { id: string }) => {
        graph.setSelectedEdgeId(edge.id)
        graph.setSelectedNodeId(null)
      },
      [graph],
    )

    // Pane click (deselect)
    const handlePaneClick = useCallback(() => {
      graph.setSelectedNodeId(null)
      graph.setSelectedEdgeId(null)
    }, [graph])

    // Add node from palette
    const handleAddNode = useCallback(
      (type: NodeType) => {
        graph.addNode(type)
      },
      [graph],
    )

    // Drag & drop from palette
    const handleDragOver = useCallback((event: DragEvent) => {
      event.preventDefault()
      event.dataTransfer.dropEffect = 'move'
    }, [])

    const handleDrop = useCallback(
      (event: DragEvent) => {
        event.preventDefault()
        const type = event.dataTransfer.getData('application/pipeline-node-type') as NodeType
        if (!type) return

        const bounds = reactFlowWrapper.current?.getBoundingClientRect()
        if (!bounds || !reactFlowInstance.current) return

        const position = reactFlowInstance.current.screenToFlowPosition({
          x: event.clientX,
          y: event.clientY,
        })

        graph.addNode(type, position)
      },
      [graph],
    )

    // Build selected node/edge for PropertyPanel
    const selectedNode: PipelineNode | null = graph.selectedNodeId
      ? (() => {
          const rfNode = graph.nodes.find((n) => n.id === graph.selectedNodeId)
          if (!rfNode) return null
          return {
            id: rfNode.data.nodeId,
            type: rfNode.data.type,
            properties: rfNode.data.properties,
            position: rfNode.position,
          }
        })()
      : null

    const selectedEdge: PipelineEdge | null = graph.selectedEdgeId
      ? (() => {
          const rfEdge = graph.edges.find((e) => e.id === graph.selectedEdgeId)
          if (!rfEdge) return null
          return { from: rfEdge.source, to: rfEdge.target }
        })()
      : null

    // All nodes as API format for PropertyPanel edge display
    const allApiNodes = toApiNodes(graph.nodes)

    return (
      <div className="flex flex-col h-full" data-testid="pipeline-graph-editor">
        {/* Node Palette */}
        <NodePalette
          existingNodeTypes={graph.existingNodeTypes}
          onAddNode={handleAddNode}
        />

        {/* Editor Toolbar */}
        <EditorToolbar
          onAutoLayout={graph.applyAutoLayout}
          onUndo={graph.undo}
          onRedo={graph.redo}
          canUndo={graph.canUndo}
          canRedo={graph.canRedo}
          snapToGrid={snapToGrid}
          onToggleSnapToGrid={() => setSnapToGrid()}
          isValid={graph.isValid}
          validationHints={graph.validationHints}
        />

        {/* Graph + Property Panel */}
        <div className="flex flex-1 min-h-0">
          <div className="flex-1 min-w-0 relative" ref={reactFlowWrapper}>
            {/* Onboarding overlay for empty canvas */}
            {graph.nodes.length === 0 && (
              <div
                className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none"
                data-testid="onboarding-overlay"
              >
                <div className="text-center space-y-3 max-w-sm">
                  <div className="text-4xl">🔧</div>
                  <h3 className="text-lg font-semibold text-foreground">Build Your Pipeline</h3>
                  <p className="text-sm text-muted-foreground">
                    Drag nodes from the palette above onto the canvas, or click a node type to add it.
                    Connect nodes by dragging from one handle to another.
                  </p>
                  <div className="flex flex-wrap justify-center gap-2 text-xs text-muted-foreground pt-1">
                    <span className="px-2 py-1 rounded-md bg-muted">1. Add a Capture node</span>
                    <span className="px-2 py-1 rounded-md bg-muted">2. Add File nodes</span>
                    <span className="px-2 py-1 rounded-md bg-muted">3. Add a Termination node</span>
                    <span className="px-2 py-1 rounded-md bg-muted">4. Connect them</span>
                  </div>
                </div>
              </div>
            )}
            <PipelineEditorProvider
              pushUndo={graph.pushUndoSnapshot}
              markDirty={graph.markDirty}
              isEditable
              selectedEdgeId={graph.selectedEdgeId}
            >
            <ReactFlow
              nodes={graph.nodes}
              edges={graph.edges}
              onNodesChange={graph.onNodesChange}
              onEdgesChange={graph.onEdgesChange}
              onConnect={graph.onConnect}
              isValidConnection={graph.checkConnection}
              nodeTypes={nodeTypes}
              edgeTypes={edgeTypes}
              onNodeClick={handleNodeClick}
              onEdgeClick={handleEdgeClick}
              onPaneClick={handlePaneClick}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              onInit={(instance) => { reactFlowInstance.current = instance }}
              nodesDraggable
              nodesConnectable
              connectOnClick={false}
              elementsSelectable
              snapToGrid={snapToGrid}
              snapGrid={[16, 16]}
              fitView
              minZoom={0.1}
              maxZoom={2}
              proOptions={{ hideAttribution: true }}
            >
              <MiniMap nodeComponent={MiniMapNode} />
              <Controls />
              <Background variant={BackgroundVariant.Dots} gap={16} />
            </ReactFlow>
            </PipelineEditorProvider>
          </div>

          {/* Property Panel */}
          {(selectedNode || selectedEdge) && (
            <PropertyPanel
              node={selectedNode}
              edge={selectedEdge}
              nodes={allApiNodes}
              mode="edit"
              onUpdateProperties={graph.updateNodeProperties}
              onUpdateNodeId={graph.updateNodeId}
              onDeleteNode={graph.removeNode}
              onDeleteEdge={graph.removeEdge}
              onClose={() => {
                graph.setSelectedNodeId(null)
                graph.setSelectedEdgeId(null)
              }}
            />
          )}
        </div>
      </div>
    )
  },
)

/** Simple toggle hook */
function useToggle(initial: boolean): [boolean, () => void] {
  const [value, setValue] = useState(initial)
  const toggle = useCallback(() => setValue((v) => !v), [])
  return [value, toggle]
}

export default PipelineGraphEditor
