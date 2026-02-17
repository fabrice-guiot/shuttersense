import type { Node, Edge, Connection } from '@xyflow/react'
import type { PipelineNodeData } from '@/contracts/api/pipelines-api'

/**
 * Validates whether a connection between two nodes is allowed.
 *
 * Rules:
 * - Capture nodes cannot receive incoming edges (source-only)
 * - Termination nodes cannot have outgoing edges (sink-only)
 * - Duplicate edges (same source+target) are not allowed
 * - Cycles are allowed (the pipeline analyzer handles loop limits at runtime)
 */
export function isValidConnection(
  connection: Connection,
  nodes: Node<PipelineNodeData>[],
  edges: Edge[],
): boolean {
  return getConnectionError(connection, nodes, edges) === null
}

/**
 * Returns a human-readable error message if the connection is invalid,
 * or null if the connection is valid.
 */
export function getConnectionError(
  connection: Connection,
  nodes: Node<PipelineNodeData>[],
  edges: Edge[],
): string | null {
  const { source, target } = connection
  if (!source || !target) return 'Connection must have a source and target'

  if (source === target) return 'Cannot connect a node to itself'

  const targetNode = nodes.find((n) => n.id === target)
  if (targetNode?.type === 'capture') {
    return 'Capture nodes cannot receive incoming edges'
  }

  const sourceNode = nodes.find((n) => n.id === source)
  if (sourceNode?.type === 'termination') {
    return 'Termination nodes cannot have outgoing edges'
  }

  const isDuplicate = edges.some((e) => e.source === source && e.target === target)
  if (isDuplicate) {
    return 'This connection already exists'
  }

  return null
}
