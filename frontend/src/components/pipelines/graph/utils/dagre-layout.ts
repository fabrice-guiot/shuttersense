import dagre from '@dagrejs/dagre'
import type { Node, Edge } from '@xyflow/react'

interface LayoutOptions {
  direction?: 'TB' | 'LR'
  nodeSep?: number
  rankSep?: number
}

/**
 * Identify back-edges that introduce cycles in the pipeline graph.
 *
 * Performs a forward traversal (DFS) from the Capture node.
 * Any edge whose target is already on the current DFS path is a back-edge.
 */
export function findBackEdges(
  nodes: Node[],
  edges: Edge[],
  captureNodeId?: string,
): Edge[] {
  if (!captureNodeId || nodes.length === 0) return []

  const adjacency = new Map<string, Edge[]>()
  for (const edge of edges) {
    const list = adjacency.get(edge.source) ?? []
    list.push(edge)
    adjacency.set(edge.source, list)
  }

  const visited = new Set<string>()
  const inStack = new Set<string>()
  const backEdges: Edge[] = []

  function dfs(nodeId: string) {
    visited.add(nodeId)
    inStack.add(nodeId)

    for (const edge of adjacency.get(nodeId) ?? []) {
      if (inStack.has(edge.target)) {
        backEdges.push(edge)
      } else if (!visited.has(edge.target)) {
        dfs(edge.target)
      }
    }

    inStack.delete(nodeId)
  }

  dfs(captureNodeId)

  // Also visit any nodes not reachable from capture (disconnected subgraphs)
  for (const node of nodes) {
    if (!visited.has(node.id)) {
      dfs(node.id)
    }
  }

  return backEdges
}

/**
 * Apply dagre auto-layout to nodes and edges.
 *
 * Pipeline graphs can contain cycles. The layout algorithm handles this by:
 * 1. Computing an acyclic projection (forward traversal from Capture node;
 *    edges whose target is already visited are "back-edges" and excluded)
 * 2. Running dagre on the acyclic projection (produces clean top-to-bottom flow)
 * 3. Returning positioned nodes — back-edges are drawn by React Flow using
 *    the existing node positions without further adjustment
 */
export function applyDagreLayout(
  nodes: Node[],
  edges: Edge[],
  options?: LayoutOptions,
): Node[] {
  if (nodes.length === 0) return []

  const direction = options?.direction ?? 'TB'
  const nodeSep = options?.nodeSep ?? 80
  const rankSep = options?.rankSep ?? 100

  // Find the Capture node as the entry point
  const captureNode = nodes.find((n) => n.type === 'capture')

  // Compute acyclic projection — exclude back-edges
  const backEdges = findBackEdges(nodes, edges, captureNode?.id)
  const backEdgeIds = new Set(backEdges.map((e) => e.id))
  const forwardEdges = edges.filter((e) => !backEdgeIds.has(e.id))

  // Create dagre graph
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: direction, nodesep: nodeSep, ranksep: rankSep })

  // Add all nodes with their dimensions
  for (const node of nodes) {
    g.setNode(node.id, {
      width: node.width ?? 200,
      height: node.height ?? 60,
    })
  }

  // Add only forward edges
  for (const edge of forwardEdges) {
    g.setEdge(edge.source, edge.target)
  }

  // Run dagre layout
  dagre.layout(g)

  // Apply computed positions to nodes
  return nodes.map((node) => {
    const pos = g.node(node.id)
    const width = node.width ?? 200
    const height = node.height ?? 60
    return {
      ...node,
      position: {
        x: pos.x - width / 2,
        y: pos.y - height / 2,
      },
    }
  })
}
