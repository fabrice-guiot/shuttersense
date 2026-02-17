import { useCallback, useMemo, useRef, useState } from 'react'
import {
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
  type Connection,
  MarkerType,
  addEdge,
} from '@xyflow/react'
import type {
  PipelineNode,
  PipelineEdge,
  PipelineNodeData,
  NodeType,
} from '@/contracts/api/pipelines-api'
import { NODE_TYPE_DEFINITIONS } from '@/contracts/api/pipelines-api'
import { toReactFlowNodes, toReactFlowEdges, toApiNodes, toApiEdges, hasPositions } from '@/components/pipelines/graph/utils/graph-transforms'
import { applyDagreLayout } from '@/components/pipelines/graph/utils/dagre-layout'
import { isValidConnection, getConnectionError } from '@/components/pipelines/graph/utils/connection-rules'
import { generateNodeId, getNodeConfig, getDefaultProperties } from '@/components/pipelines/graph/utils/node-defaults'

const MAX_UNDO_STACK = 50

interface Snapshot {
  nodes: Node<PipelineNodeData>[]
  edges: Edge[]
}

interface UsePipelineGraphReturn {
  // React Flow state
  nodes: Node<PipelineNodeData>[]
  edges: Edge[]
  onNodesChange: OnNodesChange<Node<PipelineNodeData>>
  onEdgesChange: OnEdgesChange
  onConnect: (connection: Connection) => void

  // Node operations
  addNode: (type: NodeType, position?: { x: number; y: number }) => void
  removeNode: (nodeId: string) => void
  updateNodeProperties: (nodeId: string, properties: Record<string, unknown>) => void
  updateNodeId: (oldId: string, newId: string) => void

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

  // Edit-mode callbacks (for PipelineEditorContext)
  pushUndoSnapshot: () => void
  markDirty: () => void

  // Dirty tracking
  isDirty: boolean
  resetDirty: () => void

  // Selection
  selectedNodeId: string | null
  selectedEdgeId: string | null
  setSelectedNodeId: (id: string | null) => void
  setSelectedEdgeId: (id: string | null) => void

  // Connection validation (for React Flow isValidConnection prop)
  checkConnection: (edgeOrConnection: Edge | Connection) => boolean
  getConnectionErrorMessage: (connection: Connection) => string | null

  // Node types present (for NodePalette)
  existingNodeTypes: NodeType[]
}

export function usePipelineGraph(): UsePipelineGraphReturn {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<PipelineNodeData>>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  // Undo/redo stacks
  const undoStack = useRef<Snapshot[]>([])
  const redoStack = useRef<Snapshot[]>([])
  const [undoCount, setUndoCount] = useState(0) // trigger re-render on stack changes
  const [redoCount, setRedoCount] = useState(0)

  // Dirty tracking
  const [isDirty, setIsDirty] = useState(false)
  const cleanSnapshot = useRef<string>('')

  // Selection
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)

  // Deep-clone edge data including waypoints array
  const cloneEdgeData = useCallback((data: Record<string, unknown> | undefined) => {
    if (!data) return data
    const cloned = { ...data }
    if (Array.isArray(cloned.waypoints)) {
      cloned.waypoints = cloned.waypoints.map((w: { x: number; y: number }) => ({ ...w }))
    }
    return cloned
  }, [])

  // Push current state to undo stack
  const pushUndo = useCallback(() => {
    setNodes((currentNodes) => {
      setEdges((currentEdges) => {
        undoStack.current.push({
          nodes: currentNodes.map((n) => ({ ...n, data: { ...n.data } })),
          edges: currentEdges.map((e) => ({ ...e, data: cloneEdgeData(e.data) })),
        })
        if (undoStack.current.length > MAX_UNDO_STACK) {
          undoStack.current.shift()
        }
        redoStack.current = []
        setUndoCount((c) => c + 1)
        setRedoCount(0)
        return currentEdges
      })
      return currentNodes
    })
  }, [setNodes, setEdges, cloneEdgeData])

  // Mark dirty
  const markDirty = useCallback(() => {
    setIsDirty(true)
  }, [])

  // Initialize from API data
  const fromApiFormat = useCallback((apiNodes: PipelineNode[], apiEdges: PipelineEdge[]) => {
    let rfNodes = toReactFlowNodes(apiNodes)
    const rfEdges = toReactFlowEdges(apiEdges)

    if (!hasPositions(apiNodes)) {
      rfNodes = applyDagreLayout(rfNodes, rfEdges)
    }

    setNodes(rfNodes)
    setEdges(rfEdges)

    // Reset undo/redo and dirty state
    undoStack.current = []
    redoStack.current = []
    setUndoCount(0)
    setRedoCount(0)
    setIsDirty(false)
    cleanSnapshot.current = JSON.stringify({ nodes: apiNodes, edges: apiEdges })
  }, [setNodes, setEdges])

  // Serialize to API format
  const toApiFormat = useCallback(() => {
    let currentNodes: Node<PipelineNodeData>[] = []
    let currentEdges: Edge[] = []
    // Read current state synchronously via setState callback
    setNodes((n) => { currentNodes = n; return n })
    setEdges((e) => { currentEdges = e; return e })
    return {
      nodes: toApiNodes(currentNodes),
      edges: toApiEdges(currentEdges, currentNodes),
    }
  }, [setNodes, setEdges])

  // Add node
  const addNode = useCallback((type: NodeType, position?: { x: number; y: number }) => {
    pushUndo()
    const config = getNodeConfig(type)
    const defaultProps = getDefaultProperties(type)

    setNodes((currentNodes) => {
      const existingIds = currentNodes.map((n) => n.id)
      const nodeId = generateNodeId(type, existingIds)

      const newNode: Node<PipelineNodeData> = {
        id: nodeId,
        type,
        position: position ?? { x: 250, y: 250 },
        data: {
          nodeId,
          type,
          properties: defaultProps,
        },
        width: config.defaultWidth,
        height: config.defaultHeight,
      }
      return [...currentNodes, newNode]
    })
    markDirty()
  }, [pushUndo, setNodes, markDirty])

  // Remove node (and connected edges)
  const removeNode = useCallback((nodeId: string) => {
    pushUndo()
    setNodes((prev) => prev.filter((n) => n.id !== nodeId))
    setEdges((prev) => prev.filter((e) => e.source !== nodeId && e.target !== nodeId))
    setSelectedNodeId((prev) => prev === nodeId ? null : prev)
    markDirty()
  }, [pushUndo, setNodes, setEdges, markDirty])

  // Update node properties
  const updateNodeProperties = useCallback((nodeId: string, properties: Record<string, unknown>) => {
    pushUndo()
    setNodes((prev) =>
      prev.map((n) =>
        n.id === nodeId
          ? { ...n, data: { ...n.data, properties } }
          : n,
      ),
    )
    markDirty()
  }, [pushUndo, setNodes, markDirty])

  // Update node ID
  const updateNodeId = useCallback((oldId: string, newId: string) => {
    if (oldId === newId || !newId.trim()) return

    // Prevent duplicate IDs
    let idExists = false
    setNodes((prev) => {
      idExists = prev.some((n) => n.id === newId)
      return prev
    })
    if (idExists) return

    pushUndo()

    setNodes((prev) =>
      prev.map((n) =>
        n.id === oldId
          ? { ...n, id: newId, data: { ...n.data, nodeId: newId } }
          : n,
      ),
    )
    // Update edge references
    setEdges((prev) =>
      prev.map((e) => {
        let updated = e
        if (e.source === oldId) {
          updated = { ...updated, source: newId, id: `${newId}-${updated.target}` }
        }
        if (e.target === oldId) {
          updated = { ...updated, target: newId, id: `${updated.source}-${newId}` }
        }
        return updated
      }),
    )
    setSelectedNodeId((prev) => prev === oldId ? newId : prev)
    markDirty()
  }, [pushUndo, setNodes, setEdges, markDirty])

  // Remove edge
  const removeEdge = useCallback((edgeId: string) => {
    pushUndo()
    setEdges((prev) => prev.filter((e) => e.id !== edgeId))
    setSelectedEdgeId((prev) => prev === edgeId ? null : prev)
    markDirty()
  }, [pushUndo, setEdges, markDirty])

  // Connect handler (for new edges via handle dragging)
  const onConnect = useCallback((connection: Connection) => {
    setNodes((currentNodes) => {
      setEdges((currentEdges) => {
        if (!isValidConnection(connection, currentNodes, currentEdges)) {
          return currentEdges
        }
        // Push undo before modification
        undoStack.current.push({
          nodes: currentNodes.map((n) => ({ ...n, data: { ...n.data } })),
          edges: currentEdges.map((e) => ({ ...e, data: cloneEdgeData(e.data) })),
        })
        if (undoStack.current.length > MAX_UNDO_STACK) {
          undoStack.current.shift()
        }
        redoStack.current = []
        setUndoCount((c) => c + 1)
        setRedoCount(0)
        setIsDirty(true)
        return addEdge(
          { ...connection, type: 'pipelineEdge', markerEnd: { type: MarkerType.ArrowClosed }, data: { offset: 0 } },
          currentEdges,
        )
      })
      return currentNodes
    })
  }, [setNodes, setEdges])

  // Auto layout
  const applyAutoLayout = useCallback(() => {
    pushUndo()
    setNodes((currentNodes) => {
      let result: Node<PipelineNodeData>[] = currentNodes
      setEdges((currentEdges) => {
        result = applyDagreLayout(currentNodes, currentEdges)
        // Reset edge routing when auto-laying out
        return currentEdges.map((e) =>
          (e.data?.offset || e.data?.waypoints)
            ? { ...e, data: { ...e.data, offset: 0, waypoints: undefined } }
            : e,
        )
      })
      return result
    })
    markDirty()
  }, [pushUndo, setNodes, setEdges, markDirty])

  // Undo
  const undo = useCallback(() => {
    const snapshot = undoStack.current.pop()
    if (!snapshot) return

    // Save current state to redo stack
    setNodes((currentNodes) => {
      setEdges((currentEdges) => {
        redoStack.current.push({
          nodes: currentNodes.map((n) => ({ ...n, data: { ...n.data } })),
          edges: currentEdges.map((e) => ({ ...e, data: cloneEdgeData(e.data) })),
        })
        setRedoCount((c) => c + 1)
        return snapshot.edges
      })
      return snapshot.nodes
    })
    setUndoCount((c) => c - 1)
    markDirty()
  }, [setNodes, setEdges, markDirty, cloneEdgeData])

  // Redo
  const redo = useCallback(() => {
    const snapshot = redoStack.current.pop()
    if (!snapshot) return

    // Save current state to undo stack
    setNodes((currentNodes) => {
      setEdges((currentEdges) => {
        undoStack.current.push({
          nodes: currentNodes.map((n) => ({ ...n, data: { ...n.data } })),
          edges: currentEdges.map((e) => ({ ...e, data: cloneEdgeData(e.data) })),
        })
        setUndoCount((c) => c + 1)
        return snapshot.edges
      })
      return snapshot.nodes
    })
    setRedoCount((c) => c - 1)
    markDirty()
  }, [setNodes, setEdges, markDirty, cloneEdgeData])

  // Reset dirty
  const resetDirty = useCallback(() => {
    setIsDirty(false)
  }, [])

  // Connection validation (for React Flow isValidConnection prop)
  // Accepts Edge | Connection to satisfy React Flow's IsValidConnection type
  const checkConnection = useCallback((edgeOrConnection: Edge | Connection) => {
    const connection: Connection = {
      source: edgeOrConnection.source,
      target: edgeOrConnection.target,
      sourceHandle: edgeOrConnection.sourceHandle ?? null,
      targetHandle: edgeOrConnection.targetHandle ?? null,
    }
    let valid = false
    setNodes((currentNodes) => {
      setEdges((currentEdges) => {
        valid = isValidConnection(connection, currentNodes, currentEdges)
        return currentEdges
      })
      return currentNodes
    })
    return valid
  }, [setNodes, setEdges])

  const getConnectionErrorMessage = useCallback((connection: Connection) => {
    let error: string | null = null
    setNodes((currentNodes) => {
      setEdges((currentEdges) => {
        error = getConnectionError(connection, currentNodes, currentEdges)
        return currentEdges
      })
      return currentNodes
    })
    return error
  }, [setNodes, setEdges])

  // Validation hints (computed from current node/edge state)
  const validationHints = useMemo(() => {
    const hints: string[] = []

    const typedNodes = nodes.filter(
      (n) => n.type && NODE_TYPE_DEFINITIONS.some((d) => d.type === n.type),
    )

    if (!typedNodes.some((n) => n.type === 'capture')) {
      hints.push('A Capture node is required to define camera patterns.')
    }

    if (!typedNodes.some((n) => n.type === 'file' && !n.data.properties.optional)) {
      hints.push('At least one non-optional File node is required.')
    }

    if (!typedNodes.some((n) => n.type === 'termination')) {
      hints.push('A Termination node is required to define end states.')
    }

    // Check orphaned nodes
    const nodesInEdges = new Set<string>()
    edges.forEach((e) => {
      nodesInEdges.add(e.source)
      nodesInEdges.add(e.target)
    })
    const orphaned = typedNodes.filter((n) => !nodesInEdges.has(n.id) && n.type !== 'termination')
    if (orphaned.length > 0 && typedNodes.length > 1) {
      hints.push(`Orphaned nodes: ${orphaned.map((n) => n.id).join(', ')}`)
    }

    // Check pairing nodes have exactly 2 inputs
    typedNodes.filter((n) => n.type === 'pairing').forEach((pNode) => {
      const inputCount = edges.filter((e) => e.target === pNode.id).length
      if (inputCount !== 2) {
        hints.push(`Pairing node "${pNode.id}" must have exactly 2 inputs (has ${inputCount})`)
      }
    })

    // Check duplicate node IDs
    const idCounts = new Map<string, number>()
    typedNodes.forEach((n) => {
      const nid = n.data.nodeId
      idCounts.set(nid, (idCounts.get(nid) ?? 0) + 1)
    })
    for (const [nid, count] of idCounts) {
      if (count > 1) {
        hints.push(`Duplicate node ID: "${nid}" appears ${count} times`)
      }
    }

    return hints
  }, [nodes, edges])

  const isValid = validationHints.length === 0 && nodes.length > 0

  // Existing node types (for NodePalette)
  const existingNodeTypes = useMemo(
    () => nodes.map((n) => n.type).filter(Boolean) as NodeType[],
    [nodes],
  )

  return {
    nodes,
    edges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    removeNode,
    updateNodeProperties,
    updateNodeId,
    removeEdge,
    applyAutoLayout,
    undo,
    redo,
    canUndo: undoCount > 0,
    canRedo: redoCount > 0,
    toApiFormat,
    fromApiFormat,
    validationHints,
    isValid,
    pushUndoSnapshot: pushUndo,
    markDirty,
    isDirty,
    resetDirty,
    selectedNodeId,
    selectedEdgeId,
    setSelectedNodeId,
    setSelectedEdgeId,
    checkConnection,
    getConnectionErrorMessage,
    existingNodeTypes,
  }
}
