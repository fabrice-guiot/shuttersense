import { describe, it, expect } from 'vitest'
import type { Node, Edge, Connection } from '@xyflow/react'
import type { PipelineNodeData } from '@/contracts/api/pipelines-api'
import { isValidConnection, getConnectionError } from '../connection-rules'

// ---------------------------------------------------------------------------
// Test fixtures
// ---------------------------------------------------------------------------

const mockNodes: Node<PipelineNodeData>[] = [
  {
    id: 'capture',
    type: 'capture',
    position: { x: 0, y: 0 },
    data: { nodeId: 'capture', type: 'capture', properties: {} },
  },
  {
    id: 'file_raw',
    type: 'file',
    position: { x: 0, y: 100 },
    data: { nodeId: 'file_raw', type: 'file', properties: { extension: '.dng' } },
  },
  {
    id: 'process_hdr',
    type: 'process',
    position: { x: 0, y: 200 },
    data: { nodeId: 'process_hdr', type: 'process', properties: { method_ids: ['HDR'] } },
  },
  {
    id: 'pairing_1',
    type: 'pairing',
    position: { x: 0, y: 300 },
    data: { nodeId: 'pairing_1', type: 'pairing', properties: {} },
  },
  {
    id: 'branching_1',
    type: 'branching',
    position: { x: 0, y: 400 },
    data: { nodeId: 'branching_1', type: 'branching', properties: {} },
  },
  {
    id: 'termination',
    type: 'termination',
    position: { x: 0, y: 500 },
    data: { nodeId: 'termination', type: 'termination', properties: { termination_type: 'Black Box Archive' } },
  },
]

const existingEdges: Edge[] = [
  { id: 'capture-file_raw', source: 'capture', target: 'file_raw' },
  { id: 'file_raw-process_hdr', source: 'file_raw', target: 'process_hdr' },
]

function makeConnection(source: string, target: string): Connection {
  return { source, target, sourceHandle: null, targetHandle: null }
}

// ---------------------------------------------------------------------------
// isValidConnection
// ---------------------------------------------------------------------------

describe('isValidConnection', () => {
  it('returns true for a valid connection between two standard nodes', () => {
    const conn = makeConnection('process_hdr', 'pairing_1')
    expect(isValidConnection(conn, mockNodes, existingEdges)).toBe(true)
  })

  it('returns false for a self-loop (same source and target)', () => {
    const conn = makeConnection('file_raw', 'file_raw')
    expect(isValidConnection(conn, mockNodes, existingEdges)).toBe(false)
  })

  it('returns false when the target is a capture node', () => {
    const conn = makeConnection('file_raw', 'capture')
    expect(isValidConnection(conn, mockNodes, existingEdges)).toBe(false)
  })

  it('returns false when the source is a termination node', () => {
    const conn = makeConnection('termination', 'file_raw')
    expect(isValidConnection(conn, mockNodes, existingEdges)).toBe(false)
  })

  it('returns false for a duplicate edge', () => {
    const conn = makeConnection('capture', 'file_raw')
    expect(isValidConnection(conn, mockNodes, existingEdges)).toBe(false)
  })

  it('returns true for a valid connection between compatible nodes', () => {
    const conn = makeConnection('branching_1', 'termination')
    expect(isValidConnection(conn, mockNodes, existingEdges)).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// getConnectionError
// ---------------------------------------------------------------------------

describe('getConnectionError', () => {
  it('returns error message for a self-loop', () => {
    const conn = makeConnection('process_hdr', 'process_hdr')
    expect(getConnectionError(conn, mockNodes, existingEdges)).toBe(
      'Cannot connect a node to itself',
    )
  })

  it('returns error message when the target is a capture node', () => {
    const conn = makeConnection('process_hdr', 'capture')
    expect(getConnectionError(conn, mockNodes, existingEdges)).toBe(
      'Capture nodes cannot receive incoming edges',
    )
  })

  it('returns error message when the source is a termination node', () => {
    const conn = makeConnection('termination', 'process_hdr')
    expect(getConnectionError(conn, mockNodes, existingEdges)).toBe(
      'Termination nodes cannot have outgoing edges',
    )
  })

  it('returns error message for a duplicate edge', () => {
    const conn = makeConnection('file_raw', 'process_hdr')
    expect(getConnectionError(conn, mockNodes, existingEdges)).toBe(
      'This connection already exists',
    )
  })

  it('returns null for a valid connection', () => {
    const conn = makeConnection('process_hdr', 'branching_1')
    expect(getConnectionError(conn, mockNodes, existingEdges)).toBeNull()
  })

  it('returns error when source is missing', () => {
    const conn: Connection = { source: null as unknown as string, target: 'file_raw', sourceHandle: null, targetHandle: null }
    expect(getConnectionError(conn, mockNodes, existingEdges)).toBe(
      'Connection must have a source and target',
    )
  })

  it('returns error when target is missing', () => {
    const conn: Connection = { source: 'file_raw', target: null as unknown as string, sourceHandle: null, targetHandle: null }
    expect(getConnectionError(conn, mockNodes, existingEdges)).toBe(
      'Connection must have a source and target',
    )
  })

  it('prioritises self-loop error over capture/termination rules', () => {
    // A capture node connecting to itself should report self-loop, not capture rule
    const conn = makeConnection('capture', 'capture')
    expect(getConnectionError(conn, mockNodes, existingEdges)).toBe(
      'Cannot connect a node to itself',
    )
  })

  it('allows cycles between non-capture/termination nodes', () => {
    // process_hdr -> file_raw is a back-edge creating a cycle but should be allowed
    const conn = makeConnection('process_hdr', 'file_raw')
    // This is not a duplicate (existing edge goes file_raw -> process_hdr)
    expect(getConnectionError(conn, mockNodes, existingEdges)).toBeNull()
  })

  it('returns null with empty edges list', () => {
    const conn = makeConnection('capture', 'file_raw')
    expect(getConnectionError(conn, mockNodes, [])).toBeNull()
  })
})
