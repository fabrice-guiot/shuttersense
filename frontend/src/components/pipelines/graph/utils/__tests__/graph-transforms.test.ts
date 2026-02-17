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

  it('defaults offset to 0 in edge data when absent', () => {
    const rfEdges = toReactFlowEdges(sampleEdges)
    expect(rfEdges[0].data?.offset).toBe(0)
  })

  it('reads offset from API edge into data', () => {
    const edgesWithOffset: PipelineEdge[] = [
      { from: 'a', to: 'b', offset: 42 },
    ]
    const rfEdges = toReactFlowEdges(edgesWithOffset)
    expect(rfEdges[0].data?.offset).toBe(42)
  })

  it('reads waypoints from API edge into data', () => {
    const edgesWithWaypoints: PipelineEdge[] = [
      { from: 'a', to: 'b', waypoints: [{ x: 100, y: 50 }, { x: 200, y: 50 }] },
    ]
    const rfEdges = toReactFlowEdges(edgesWithWaypoints)
    expect(rfEdges[0].data?.waypoints).toEqual([{ x: 100, y: 50 }, { x: 200, y: 50 }])
  })

  it('sets waypoints to undefined in data when absent', () => {
    const rfEdges = toReactFlowEdges(sampleEdges)
    expect(rfEdges[0].data?.waypoints).toBeUndefined()
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

  it('omits offset when zero', () => {
    const rfEdges = toReactFlowEdges(sampleEdges)
    const apiEdges = toApiEdges(rfEdges)
    expect(apiEdges[0]).not.toHaveProperty('offset')
  })

  it('drops legacy offset when converting back to API (offset is deprecated)', () => {
    const edgesWithOffset: PipelineEdge[] = [
      { from: 'a', to: 'b', offset: -30 },
    ]
    const rfEdges = toReactFlowEdges(edgesWithOffset)
    const apiEdges = toApiEdges(rfEdges)
    // Legacy offset is no longer preserved — edges are normalized via computeEdgeConfig
    expect(apiEdges[0]).toEqual({ from: 'a', to: 'b' })
    expect(apiEdges[0]).not.toHaveProperty('offset')
  })

  it('preserves non-empty waypoints in round-trip', () => {
    const wp = [{ x: 100, y: 50 }, { x: 200, y: 50 }]
    const edgesWithWaypoints: PipelineEdge[] = [
      { from: 'a', to: 'b', waypoints: wp },
    ]
    const rfEdges = toReactFlowEdges(edgesWithWaypoints)
    const apiEdges = toApiEdges(rfEdges)
    expect(apiEdges[0]).toEqual({ from: 'a', to: 'b', waypoints: wp })
  })

  it('omits waypoints when empty array', () => {
    const edgesEmptyWp: PipelineEdge[] = [
      { from: 'a', to: 'b', waypoints: [] },
    ]
    const rfEdges = toReactFlowEdges(edgesEmptyWp)
    const apiEdges = toApiEdges(rfEdges)
    expect(apiEdges[0]).not.toHaveProperty('waypoints')
  })

  it('omits offset when waypoints are present', () => {
    const edgesWithBoth: PipelineEdge[] = [
      { from: 'a', to: 'b', offset: 42, waypoints: [{ x: 100, y: 50 }, { x: 200, y: 50 }] },
    ]
    const rfEdges = toReactFlowEdges(edgesWithBoth)
    const apiEdges = toApiEdges(rfEdges)
    expect(apiEdges[0]).toHaveProperty('waypoints')
    expect(apiEdges[0]).not.toHaveProperty('offset')
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

describe('toApiEdges normalization', () => {
  // Helper: create RF nodes with positions and dimensions for normalization tests
  function makeRfNodes() {
    return toReactFlowNodes([
      { id: 'a', type: 'capture', properties: {}, position: { x: 0, y: 0 } },
      { id: 'b', type: 'file', properties: {}, position: { x: 0, y: 200 } },
      { id: 'c', type: 'file', properties: {}, position: { x: 200, y: 200 } },
    ])
  }

  it('clears waypoints for 1-seg edge (co-aligned nodes)', () => {
    // Use same-type nodes at same X for true co-alignment
    const coAlignedNodes = toReactFlowNodes([
      { id: 'a', type: 'file', properties: {}, position: { x: 0, y: 0 } },
      { id: 'b', type: 'file', properties: {}, position: { x: 0, y: 200 } },
    ])
    // Stale waypoints that should be cleared (nodes are co-aligned)
    const rfEdges = toReactFlowEdges([
      { from: 'a', to: 'b', waypoints: [{ x: 96, y: 80 }, { x: 96, y: 80 }] },
    ])
    const apiEdges = toApiEdges(rfEdges, coAlignedNodes)
    expect(apiEdges[0]).not.toHaveProperty('waypoints')
  })

  it('preserves adjusted waypoints for 3-seg edge', () => {
    const nodes = makeRfNodes()
    // a → c: different X positions → 3-seg
    // a (capture: w=224) → sourceX=112, sourceY=80
    // c (file: w=192) at x=200 → targetX=296, targetY=200
    const rfEdges = toReactFlowEdges([
      { from: 'a', to: 'c', waypoints: [{ x: 112, y: 120 }, { x: 296, y: 120 }] },
    ])
    const apiEdges = toApiEdges(rfEdges, nodes)
    expect(apiEdges[0].waypoints).toBeDefined()
    expect(apiEdges[0].waypoints).toHaveLength(2)
    // Y value should be preserved from stored waypoints
    expect(apiEdges[0].waypoints![0].y).toBe(120)
  })

  it('preserves waypoints for 5-seg edge', () => {
    const nodes = makeRfNodes()
    // 4 waypoints that produce a valid 5-seg
    const wp = [
      { x: 112, y: 50 },
      { x: 300, y: 50 },
      { x: 300, y: 150 },
      { x: 296, y: 150 },
    ]
    const rfEdges = toReactFlowEdges([
      { from: 'a', to: 'c', waypoints: wp },
    ])
    const apiEdges = toApiEdges(rfEdges, nodes)
    expect(apiEdges[0].waypoints).toBeDefined()
    expect(apiEdges[0].waypoints).toHaveLength(4)
  })

  it('falls back to passthrough when nodes not provided', () => {
    const wp = [{ x: 100, y: 50 }, { x: 200, y: 50 }]
    const rfEdges = toReactFlowEdges([{ from: 'a', to: 'b', waypoints: wp }])
    const apiEdges = toApiEdges(rfEdges) // no nodes
    expect(apiEdges[0].waypoints).toEqual(wp)
  })

  it('omits offset field (legacy) even when present in RF edge', () => {
    const nodes = makeRfNodes()
    const rfEdges = toReactFlowEdges([{ from: 'a', to: 'b', offset: 42 }])
    const apiEdges = toApiEdges(rfEdges, nodes)
    expect(apiEdges[0]).not.toHaveProperty('offset')
  })
})
