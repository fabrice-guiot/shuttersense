import type { Node, Edge } from '@xyflow/react'
import { MarkerType } from '@xyflow/react'
import type {
  PipelineNode,
  PipelineEdge,
  PipelineNodeData,
  PipelineFlowAnalyticsResponse,
} from '@/contracts/api/pipelines-api'
import { getNodeConfig } from './node-defaults'
import { computeEdgeConfig } from '../edges/PipelineEdge'

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
      data: {
        offset: edge.offset ?? 0,
        waypoints: edge.waypoints,
      },
    }

    if (analytics) {
      const edgeStats = analytics.edges.find(
        (e) => e.from_node === edge.from && e.to_node === edge.to,
      )
      if (edgeStats) {
        rfEdge.data = {
          ...rfEdge.data,
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
 * Compute handle positions for a node (source handle = bottom center, target handle = top center).
 */
function getHandlePositions(node: Node<PipelineNodeData>) {
  const config = getNodeConfig(node.data.type)
  const w = node.measured?.width ?? node.width ?? config.defaultWidth
  const h = node.measured?.height ?? node.height ?? config.defaultHeight
  return {
    sourceX: node.position.x + w / 2,
    sourceY: node.position.y + h,
    targetX: node.position.x + w / 2,
    targetY: node.position.y,
  }
}

/**
 * Convert React Flow edges back to API pipeline edges.
 * Accepts nodes to normalize waypoints: runs computeEdgeConfig to produce
 * effective waypoints (clearing stale data for 1-seg edges).
 */
export function toApiEdges(rfEdges: Edge[], rfNodes?: Node<PipelineNodeData>[]): PipelineEdge[] {
  const nodeMap = new Map<string, Node<PipelineNodeData>>()
  if (rfNodes) {
    for (const n of rfNodes) nodeMap.set(n.id, n)
  }

  return rfEdges.map((edge) => {
    const apiEdge: PipelineEdge = {
      from: edge.source,
      to: edge.target,
    }

    const storedWp = edge.data?.waypoints as Array<{ x: number; y: number }> | undefined
    const sourceNode = nodeMap.get(edge.source)
    const targetNode = nodeMap.get(edge.target)

    if (sourceNode && targetNode) {
      const src = getHandlePositions(sourceNode)
      const tgt = getHandlePositions(targetNode)
      const result = computeEdgeConfig(
        src.sourceX, src.sourceY, tgt.targetX, tgt.targetY, storedWp,
      )
      if (result.effectiveWaypoints && result.effectiveWaypoints.length > 0) {
        apiEdge.waypoints = result.effectiveWaypoints
      }
    } else {
      // Fallback: no node data available, pass waypoints through
      if (storedWp && storedWp.length > 0) {
        apiEdge.waypoints = storedWp
      }
    }

    return apiEdge
  })
}

/**
 * Check if any node in the pipeline has a saved position.
 */
export function hasPositions(nodes: PipelineNode[]): boolean {
  return nodes.some((node) => node.position != null)
}
