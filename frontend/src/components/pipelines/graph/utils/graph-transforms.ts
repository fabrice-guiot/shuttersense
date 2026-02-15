import type { Node, Edge } from '@xyflow/react'
import { MarkerType } from '@xyflow/react'
import type {
  PipelineNode,
  PipelineEdge,
  PipelineNodeData,
  PipelineFlowAnalyticsResponse,
} from '@/contracts/api/pipelines-api'
import { getNodeConfig } from './node-defaults'

/**
 * Convert API pipeline nodes to React Flow nodes.
 */
export function toReactFlowNodes(
  apiNodes: PipelineNode[],
  validationErrors?: string[] | null,
): Node<PipelineNodeData>[] {
  return apiNodes.map((node) => {
    const hasError = validationErrors
      ? validationErrors.some((err) => err.toLowerCase().includes(node.id.toLowerCase()))
      : false

    const config = getNodeConfig(node.type)

    return {
      id: node.id,
      type: node.type,
      position: node.position ?? { x: 0, y: 0 },
      data: {
        nodeId: node.id,
        type: node.type,
        properties: node.properties,
        hasError,
      },
      width: config.defaultWidth,
      height: config.defaultHeight,
    }
  })
}

/**
 * Convert API pipeline edges to React Flow edges.
 */
export function toReactFlowEdges(
  apiEdges: PipelineEdge[],
  analytics?: PipelineFlowAnalyticsResponse | null,
): Edge[] {
  return apiEdges.map((edge) => {
    const rfEdge: Edge = {
      id: `${edge.from}-${edge.to}`,
      source: edge.from,
      target: edge.to,
      type: 'pipelineEdge',
      markerEnd: { type: MarkerType.ArrowClosed },
    }

    if (analytics) {
      const edgeStats = analytics.edges.find(
        (e) => e.from_node === edge.from && e.to_node === edge.to,
      )
      if (edgeStats) {
        rfEdge.data = {
          record_count: edgeStats.record_count,
          percentage: edgeStats.percentage,
          maxCount: Math.max(...analytics.edges.map((e) => e.record_count)),
        }
      }
    }

    return rfEdge
  })
}

/**
 * Convert React Flow nodes back to API pipeline nodes (preserves positions).
 */
export function toApiNodes(rfNodes: Node<PipelineNodeData>[]): PipelineNode[] {
  return rfNodes.map((node) => ({
    id: node.data.nodeId,
    type: node.data.type,
    properties: node.data.properties,
    position: node.position,
  }))
}

/**
 * Convert React Flow edges back to API pipeline edges.
 */
export function toApiEdges(rfEdges: Edge[]): PipelineEdge[] {
  return rfEdges.map((edge) => ({
    from: edge.source,
    to: edge.target,
  }))
}

/**
 * Check if any node in the pipeline has a saved position.
 */
export function hasPositions(nodes: PipelineNode[]): boolean {
  return nodes.some((node) => node.position != null)
}
