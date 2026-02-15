import { describe, it, expect } from 'vitest'
import type { PipelineNode, PipelineEdge } from '@/contracts/api/pipelines-api'
import {
  toReactFlowNodes,
  toReactFlowEdges,
  toApiNodes,
  toApiEdges,
  hasPositions,
} from '../graph-transforms'

const sampleNodes: PipelineNode[] = [
  {
    id: 'capture_1',
    type: 'capture',
    properties: { sample_filename: 'AB3D0001', filename_regex: '([A-Z0-9]{4})([0-9]{4})', camera_id_group: '1' },
    position: { x: 100, y: 50 },
  },
  {
    id: 'file_raw',
    type: 'file',
    properties: { extension: '.dng', optional: false },
    position: { x: 100, y: 200 },
  },
  {
    id: 'process_hdr',
    type: 'process',
    properties: { method_ids: ['HDR'] },
  },
  {
    id: 'termination_archive',
    type: 'termination',
    properties: { termination_type: 'Black Box Archive' },
  },
]

const sampleEdges: PipelineEdge[] = [
  { from: 'capture_1', to: 'file_raw' },
  { from: 'file_raw', to: 'process_hdr' },
  { from: 'process_hdr', to: 'termination_archive' },
  { from: 'process_hdr', to: 'file_raw' }, // back-edge (cycle)
]

describe('toReactFlowNodes', () => {
  it('converts PipelineNode[] to React Flow nodes preserving id/type/properties', () => {
    const rfNodes = toReactFlowNodes(sampleNodes)
    expect(rfNodes).toHaveLength(4)

    const capture = rfNodes.find((n) => n.id === 'capture_1')!
    expect(capture.type).toBe('capture')
    expect(capture.data.nodeId).toBe('capture_1')
    expect(capture.data.type).toBe('capture')
    expect(capture.data.properties.sample_filename).toBe('AB3D0001')
  })

  it('passes through position data when present', () => {
    const rfNodes = toReactFlowNodes(sampleNodes)
    const capture = rfNodes.find((n) => n.id === 'capture_1')!
    expect(capture.position).toEqual({ x: 100, y: 50 })
  })

  it('defaults position to {x: 0, y: 0} when absent', () => {
    const rfNodes = toReactFlowNodes(sampleNodes)
    const process = rfNodes.find((n) => n.id === 'process_hdr')!
    expect(process.position).toEqual({ x: 0, y: 0 })
  })

  it('sets hasError when validationErrors reference the node id', () => {
    const errors = ['Node "file_raw" has invalid extension', 'Missing required node']
    const rfNodes = toReactFlowNodes(sampleNodes, errors)

    const fileNode = rfNodes.find((n) => n.id === 'file_raw')!
    expect(fileNode.data.hasError).toBe(true)

    const capture = rfNodes.find((n) => n.id === 'capture_1')!
    expect(capture.data.hasError).toBe(false)
  })

  it('sets hasError to false for all nodes when no validationErrors', () => {
    const rfNodes = toReactFlowNodes(sampleNodes)
    for (const node of rfNodes) {
      expect(node.data.hasError).toBe(false)
    }
  })
})

describe('toReactFlowEdges', () => {
  it('generates edge id as from-to and maps source/target', () => {
    const rfEdges = toReactFlowEdges(sampleEdges)
    expect(rfEdges).toHaveLength(4)

    const first = rfEdges[0]
    expect(first.id).toBe('capture_1-file_raw')
    expect(first.source).toBe('capture_1')
    expect(first.target).toBe('file_raw')
  })

  it('sets smoothstep edge type', () => {
    const rfEdges = toReactFlowEdges(sampleEdges)
    expect(rfEdges[0].type).toBe('pipelineEdge')
  })

  it('includes arrow marker', () => {
    const rfEdges = toReactFlowEdges(sampleEdges)
    expect(rfEdges[0].markerEnd).toBeDefined()
  })
})

describe('toApiNodes', () => {
  it('roundtrips nodes preserving all data including positions', () => {
    const rfNodes = toReactFlowNodes(sampleNodes)
    const apiNodes = toApiNodes(rfNodes)

    expect(apiNodes).toHaveLength(4)
    const capture = apiNodes.find((n) => n.id === 'capture_1')!
    expect(capture.type).toBe('capture')
    expect(capture.properties.sample_filename).toBe('AB3D0001')
    expect(capture.position).toEqual({ x: 100, y: 50 })
  })
})

describe('toApiEdges', () => {
  it('maps source→from and target→to', () => {
    const rfEdges = toReactFlowEdges(sampleEdges)
    const apiEdges = toApiEdges(rfEdges)

    expect(apiEdges).toHaveLength(4)
    expect(apiEdges[0]).toEqual({ from: 'capture_1', to: 'file_raw' })
  })
})

describe('hasPositions', () => {
  it('returns false when no nodes have position', () => {
    const noPos: PipelineNode[] = [
      { id: 'a', type: 'capture', properties: {} },
      { id: 'b', type: 'file', properties: {} },
    ]
    expect(hasPositions(noPos)).toBe(false)
  })

  it('returns true when at least one node has position', () => {
    expect(hasPositions(sampleNodes)).toBe(true)
  })

  it('returns false for empty array', () => {
    expect(hasPositions([])).toBe(false)
  })
})
