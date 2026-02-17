import { useCallback, useEffect, useMemo } from 'react'
import { useMediaQuery } from '@/hooks/useMediaQuery'
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  type NodeMouseHandler,
} from '@xyflow/react'
import type {
  PipelineNode,
  PipelineEdge,
  PipelineFlowAnalyticsResponse,
} from '@/contracts/api/pipelines-api'
import { nodeTypes } from './nodes'
import MiniMapNode from './nodes/MiniMapNode'
import { edgeTypes } from './edges'
import { toReactFlowNodes, toReactFlowEdges, hasPositions } from './utils/graph-transforms'
import { applyDagreLayout } from './utils/dagre-layout'

interface PipelineGraphViewProps {
  nodes: PipelineNode[]
  edges: PipelineEdge[]
  validationErrors?: string[] | null
  onNodeClick?: (nodeId: string) => void
  onEdgeClick?: (edgeId: string) => void
  analytics?: PipelineFlowAnalyticsResponse | null
  showFlow?: boolean
}

export function PipelineGraphView({
  nodes: apiNodes,
  edges: apiEdges,
  validationErrors,
  onNodeClick,
  onEdgeClick,
  analytics,
  showFlow,
}: PipelineGraphViewProps) {
  const { initialNodes, initialEdges } = useMemo(() => {
    let rfNodes = toReactFlowNodes(apiNodes, validationErrors)
    let rfEdges = toReactFlowEdges(apiEdges, analytics)

    // Apply auto-layout if no saved positions
    if (!hasPositions(apiNodes)) {
      rfNodes = applyDagreLayout(rfNodes, rfEdges)
    }

    // Switch edge type to analyticsEdge when showing flow data
    if (showFlow && analytics) {
      rfEdges = rfEdges.map((e) => ({
        ...e,
        type: 'analyticsEdge',
      }))
    }

    return { initialNodes: rfNodes, initialEdges: rfEdges }
  }, [apiNodes, apiEdges, validationErrors, analytics, showFlow])

  const [nodes, setNodes] = useNodesState(initialNodes)
  const [edges, setEdges] = useEdgesState(initialEdges)

  // Sync React Flow state when API data changes (e.g., version switch)
  useEffect(() => {
    setNodes(initialNodes)
  }, [initialNodes, setNodes])

  useEffect(() => {
    setEdges(initialEdges)
  }, [initialEdges, setEdges])

  const handleNodeClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      onNodeClick?.(node.id)
    },
    [onNodeClick],
  )

  const isDesktop = useMediaQuery('(min-width: 768px)')

  const handleEdgeClick = useCallback(
    (_event: React.MouseEvent, edge: { id: string }) => {
      onEdgeClick?.(edge.id)
    },
    [onEdgeClick],
  )

  return (
    <div className="h-full w-full" data-testid="pipeline-graph-view">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodeClick={handleNodeClick}
        onEdgeClick={handleEdgeClick}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={true}
        fitView
        minZoom={0.1}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        {isDesktop && <MiniMap nodeComponent={MiniMapNode} />}
        <Controls />
        <Background variant={BackgroundVariant.Dots} gap={16} />
      </ReactFlow>
    </div>
  )
}

export default PipelineGraphView
