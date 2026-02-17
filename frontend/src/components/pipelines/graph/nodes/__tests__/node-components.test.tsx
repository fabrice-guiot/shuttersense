import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { PipelineNodeData } from '@/contracts/api/pipelines-api'

// Mock @xyflow/react
vi.mock('@xyflow/react', () => ({
  Handle: ({ type, position }: { type: string; position: string }) => (
    <div data-testid={`handle-${type}-${position}`} />
  ),
  Position: { Top: 'top', Bottom: 'bottom' },
  Node: {},
}))

import CaptureNode from '../CaptureNode'
import FileNode from '../FileNode'
import ProcessNode from '../ProcessNode'
import PairingNode from '../PairingNode'
import BranchingNode from '../BranchingNode'
import TerminationNode from '../TerminationNode'

function makeNodeProps(data: PipelineNodeData) {
  return {
    id: data.nodeId,
    data,
    type: data.type,
    positionAbsoluteX: 0,
    positionAbsoluteY: 0,
    zIndex: 0,
    isConnectable: true,
    dragging: false,
    dragHandle: undefined,
    selected: false,
    sourcePosition: undefined,
    targetPosition: undefined,
    parentId: undefined,
    width: 200,
    height: 60,
    deletable: true,
    selectable: true,
  } as any
}

function baseData(overrides: Partial<PipelineNodeData> = {}): PipelineNodeData {
  return {
    nodeId: 'test_1',
    type: 'file',
    properties: {},
    ...overrides,
  }
}

describe('CaptureNode', () => {
  it('renders without crashing', () => {
    const props = makeNodeProps(baseData({ nodeId: 'capture_1', type: 'capture', properties: { sample_filename: 'AB3D0001' } }))
    const { container } = render(<CaptureNode {...props} />)
    expect(container.firstChild).toBeTruthy()
  })

  it('displays the node ID', () => {
    const props = makeNodeProps(baseData({ nodeId: 'capture_1', type: 'capture', properties: {} }))
    render(<CaptureNode {...props} />)
    expect(screen.getByText('capture_1')).toBeTruthy()
  })

  it('shows error indicator when hasError is true', () => {
    const props = makeNodeProps(baseData({ nodeId: 'capture_1', type: 'capture', hasError: true, properties: {} }))
    const { container } = render(<CaptureNode {...props} />)
    expect(container.querySelector('.border-destructive')).toBeTruthy()
  })

  it('has output handle only (bottom, no top)', () => {
    const props = makeNodeProps(baseData({ nodeId: 'capture_1', type: 'capture', properties: {} }))
    render(<CaptureNode {...props} />)
    expect(screen.getByTestId('handle-source-bottom')).toBeTruthy()
    expect(screen.queryByTestId('handle-target-top')).toBeNull()
  })

  it('shows analytics badge when analyticsCount is set', () => {
    const props = makeNodeProps(baseData({ nodeId: 'capture_1', type: 'capture', analyticsCount: 1500, properties: {} }))
    render(<CaptureNode {...props} />)
    expect(screen.getByText('1,500')).toBeTruthy()
  })
})

describe('TerminationNode', () => {
  it('renders without crashing', () => {
    const props = makeNodeProps(baseData({ nodeId: 'term_1', type: 'termination', properties: { termination_type: 'Black Box Archive' } }))
    const { container } = render(<TerminationNode {...props} />)
    expect(container.firstChild).toBeTruthy()
  })

  it('displays the node ID', () => {
    const props = makeNodeProps(baseData({ nodeId: 'term_1', type: 'termination', properties: {} }))
    render(<TerminationNode {...props} />)
    expect(screen.getByText('term_1')).toBeTruthy()
  })

  it('has input handle only (top, no bottom)', () => {
    const props = makeNodeProps(baseData({ nodeId: 'term_1', type: 'termination', properties: {} }))
    render(<TerminationNode {...props} />)
    expect(screen.getByTestId('handle-target-top')).toBeTruthy()
    expect(screen.queryByTestId('handle-source-bottom')).toBeNull()
  })

  it('shows error indicator when hasError is true', () => {
    const props = makeNodeProps(baseData({ nodeId: 'term_1', type: 'termination', hasError: true, properties: {} }))
    const { container } = render(<TerminationNode {...props} />)
    expect(container.querySelector('.border-destructive')).toBeTruthy()
  })
})

describe('FileNode', () => {
  it('renders without crashing and displays node ID', () => {
    const props = makeNodeProps(baseData({ nodeId: 'file_raw', type: 'file', properties: { extension: '.dng' } }))
    render(<FileNode {...props} />)
    expect(screen.getByText('file_raw')).toBeTruthy()
  })

  it('displays extension property', () => {
    const props = makeNodeProps(baseData({ nodeId: 'file_raw', type: 'file', properties: { extension: '.dng' } }))
    render(<FileNode {...props} />)
    expect(screen.getByText('.dng')).toBeTruthy()
  })

  it('has both input and output handles', () => {
    const props = makeNodeProps(baseData({ nodeId: 'file_1', type: 'file', properties: {} }))
    render(<FileNode {...props} />)
    expect(screen.getByTestId('handle-target-top')).toBeTruthy()
    expect(screen.getByTestId('handle-source-bottom')).toBeTruthy()
  })

  it('shows error indicator when hasError is true', () => {
    const props = makeNodeProps(baseData({ nodeId: 'file_1', type: 'file', hasError: true, properties: {} }))
    const { container } = render(<FileNode {...props} />)
    expect(container.querySelector('.border-destructive')).toBeTruthy()
  })
})

describe('ProcessNode', () => {
  it('renders and displays node ID', () => {
    const props = makeNodeProps(baseData({ nodeId: 'process_hdr', type: 'process', properties: { method_ids: ['HDR'] } }))
    render(<ProcessNode {...props} />)
    expect(screen.getByText('process_hdr')).toBeTruthy()
  })

  it('displays method_ids', () => {
    const props = makeNodeProps(baseData({ nodeId: 'process_1', type: 'process', properties: { method_ids: ['HDR', 'BW'] } }))
    render(<ProcessNode {...props} />)
    expect(screen.getByText('HDR, BW')).toBeTruthy()
  })

  it('has both input and output handles', () => {
    const props = makeNodeProps(baseData({ nodeId: 'process_1', type: 'process', properties: {} }))
    render(<ProcessNode {...props} />)
    expect(screen.getByTestId('handle-target-top')).toBeTruthy()
    expect(screen.getByTestId('handle-source-bottom')).toBeTruthy()
  })
})

describe('PairingNode', () => {
  it('renders and displays node ID', () => {
    const props = makeNodeProps(baseData({ nodeId: 'pairing_1', type: 'pairing', properties: {} }))
    render(<PairingNode {...props} />)
    expect(screen.getByText('pairing_1')).toBeTruthy()
  })

  it('has both input and output handles', () => {
    const props = makeNodeProps(baseData({ nodeId: 'pairing_1', type: 'pairing', properties: {} }))
    render(<PairingNode {...props} />)
    expect(screen.getByTestId('handle-target-top')).toBeTruthy()
    expect(screen.getByTestId('handle-source-bottom')).toBeTruthy()
  })
})

describe('BranchingNode', () => {
  it('renders and displays node ID', () => {
    const props = makeNodeProps(baseData({ nodeId: 'branching_1', type: 'branching', properties: {} }))
    render(<BranchingNode {...props} />)
    expect(screen.getByText('branching_1')).toBeTruthy()
  })

  it('has both input and output handles', () => {
    const props = makeNodeProps(baseData({ nodeId: 'branching_1', type: 'branching', properties: {} }))
    render(<BranchingNode {...props} />)
    expect(screen.getByTestId('handle-target-top')).toBeTruthy()
    expect(screen.getByTestId('handle-source-bottom')).toBeTruthy()
  })

  it('shows analytics badge when analyticsCount is set', () => {
    const props = makeNodeProps(baseData({ nodeId: 'branching_1', type: 'branching', analyticsCount: 500, properties: {} }))
    render(<BranchingNode {...props} />)
    expect(screen.getByText('500')).toBeTruthy()
  })
})
