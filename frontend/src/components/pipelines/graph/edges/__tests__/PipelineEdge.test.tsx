import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'
import { computeEdgeConfig, getHandles } from '../PipelineEdge'

// Mock @xyflow/react
vi.mock('@xyflow/react', () => ({
  BaseEdge: ({ id, path }: { id: string; path: string }) => (
    <path data-testid={`edge-${id}`} d={path} />
  ),
  useReactFlow: () => ({
    setEdges: vi.fn(),
    screenToFlowPosition: vi.fn(() => ({ x: 0, y: 0 })),
  }),
}))

// Mock PipelineEditorContext
const mockContext = {
  pushUndo: vi.fn(),
  markDirty: vi.fn(),
  isEditable: false,
  selectedEdgeId: null as string | null,
}
vi.mock('../../PipelineEditorContext', () => ({
  usePipelineEditor: () => mockContext,
}))

import PipelineEdge from '../PipelineEdge'

function makeEdgeProps(overrides: Record<string, unknown> = {}) {
  return {
    id: 'a-b',
    source: 'a',
    target: 'b',
    sourceX: 100,
    sourceY: 0,
    targetX: 200,
    targetY: 200,
    sourcePosition: 'bottom' as const,
    targetPosition: 'top' as const,
    selected: false,
    data: {},
    style: {},
    markerEnd: undefined,
    ...overrides,
  } as any
}

// ── computeEdgeConfig (pure function) ──────────────────────────

describe('computeEdgeConfig', () => {
  describe('1-seg (co-aligned, non-loopback)', () => {
    it('returns 1-seg when endpoints are co-aligned', () => {
      const result = computeEdgeConfig(100, 0, 100, 200)
      expect(result.config).toBe('1-seg')
      expect(result.points).toHaveLength(2)
      expect(result.effectiveWaypoints).toBeUndefined()
    })

    it('returns 1-seg when endpoints are within snap threshold', () => {
      const result = computeEdgeConfig(100, 0, 103, 200)
      expect(result.config).toBe('1-seg')
    })

    it('does NOT return 1-seg when endpoints differ by more than threshold', () => {
      const result = computeEdgeConfig(100, 0, 110, 200)
      expect(result.config).toBe('3-seg')
    })
  })

  describe('3-seg (non-aligned, non-loopback)', () => {
    it('returns 3-seg with default midY when no stored waypoints', () => {
      const result = computeEdgeConfig(100, 0, 200, 200)
      expect(result.config).toBe('3-seg')
      expect(result.points).toHaveLength(4) // src, bend1, bend2, tgt
      expect(result.points[1].y).toBe(100) // midY = (0+200)/2
      expect(result.points[2].y).toBe(100)
      expect(result.effectiveWaypoints).toBeUndefined()
    })

    it('uses stored hY from 2 waypoints', () => {
      const wp = [{ x: 100, y: 80 }, { x: 200, y: 80 }]
      const result = computeEdgeConfig(100, 0, 200, 200, wp)
      expect(result.config).toBe('3-seg')
      expect(result.points[1].y).toBe(80)
      expect(result.points[2].y).toBe(80)
      expect(result.effectiveWaypoints).toHaveLength(2)
    })

    it('pins waypoint X to source/target X at render time', () => {
      // Stored waypoints have stale X values
      const wp = [{ x: 50, y: 80 }, { x: 150, y: 80 }]
      const result = computeEdgeConfig(100, 0, 200, 200, wp)
      expect(result.points[1].x).toBe(100) // pinned to sourceX
      expect(result.points[2].x).toBe(200) // pinned to targetX
    })
  })

  describe('5-seg (loopback)', () => {
    it('returns 5-seg when sourceY >= targetY (loopback)', () => {
      const result = computeEdgeConfig(100, 200, 200, 100)
      expect(result.config).toBe('5-seg')
      expect(result.points).toHaveLength(6) // src + 4 bends + tgt
    })

    it('returns 5-seg even when co-aligned in loopback', () => {
      const result = computeEdgeConfig(100, 200, 100, 100)
      expect(result.config).toBe('5-seg')
    })

    it('uses default loopback geometry without stored waypoints', () => {
      const result = computeEdgeConfig(100, 200, 200, 100)
      // h1Y = 200 + 30 = 230 (below source)
      expect(result.points[1].y).toBe(230)
      // h2Y = 100 - 30 = 70 (above target)
      expect(result.points[4].y).toBe(70)
      // vX = max(100, 200) + 80 = 280
      expect(result.points[2].x).toBe(280)
      expect(result.points[3].x).toBe(280)
    })

    it('uses stored 4 waypoints for loopback', () => {
      const wp = [
        { x: 100, y: 250 },
        { x: 300, y: 250 },
        { x: 300, y: 50 },
        { x: 200, y: 50 },
      ]
      const result = computeEdgeConfig(100, 200, 200, 100, wp)
      expect(result.config).toBe('5-seg')
      expect(result.effectiveWaypoints).toHaveLength(4)
    })
  })

  describe('5-seg (user detour from 1-seg)', () => {
    it('returns 5-seg for co-aligned with 4 stored waypoints (detour)', () => {
      const wp = [
        { x: 100, y: 66 },
        { x: 250, y: 66 },
        { x: 250, y: 134 },
        { x: 100, y: 134 },
      ]
      const result = computeEdgeConfig(100, 0, 100, 200, wp)
      // middleVX = 250, sourceX = 100 → |250-100| > SNAP → stays 5-seg
      expect(result.config).toBe('5-seg')
      expect(result.points).toHaveLength(6)
    })
  })

  describe('snap-back', () => {
    it('snaps 5-seg back to 1-seg when middle V returns to source X', () => {
      const wp = [
        { x: 100, y: 66 },
        { x: 102, y: 66 },  // middleVX ≈ sourceX
        { x: 102, y: 134 },
        { x: 100, y: 134 },
      ]
      const result = computeEdgeConfig(100, 0, 100, 200, wp)
      expect(result.config).toBe('1-seg')
      expect(result.effectiveWaypoints).toBeUndefined()
    })

    it('snaps 3-seg with 2 waypoints back to 1-seg when nodes become co-aligned', () => {
      const wp = [{ x: 100, y: 80 }, { x: 100, y: 80 }]
      // Nodes moved so they are now co-aligned (both at x=100)
      const result = computeEdgeConfig(100, 0, 100, 200, wp)
      expect(result.config).toBe('1-seg')
      expect(result.effectiveWaypoints).toBeUndefined()
    })

    it('does NOT snap back 5-seg on loopback even if middle V matches source', () => {
      const wp = [
        { x: 100, y: 230 },
        { x: 100, y: 230 },
        { x: 100, y: 70 },
        { x: 100, y: 70 },
      ]
      const result = computeEdgeConfig(100, 200, 100, 100, wp)
      expect(result.config).toBe('5-seg') // loopback never simplifies
    })
  })
})

// ── getHandles ─────────────────────────────────────────────────

describe('getHandles', () => {
  it('returns 1 handle with ew-resize for 1-seg', () => {
    const points = [{ x: 100, y: 0 }, { x: 100, y: 200 }]
    const handles = getHandles('1-seg', points)
    expect(handles).toHaveLength(1)
    expect(handles[0].cursor).toBe('ew-resize')
    expect(handles[0].x).toBe(100)
    expect(handles[0].y).toBe(100) // midpoint
  })

  it('returns 1 handle with ns-resize for 3-seg', () => {
    const points = [
      { x: 100, y: 0 },
      { x: 100, y: 100 },
      { x: 200, y: 100 },
      { x: 200, y: 200 },
    ]
    const handles = getHandles('3-seg', points)
    expect(handles).toHaveLength(1)
    expect(handles[0].cursor).toBe('ns-resize')
    expect(handles[0].y).toBe(100) // midpoint of H segment
  })

  it('returns 3 handles (ns, ew, ns) for 5-seg', () => {
    const points = [
      { x: 100, y: 0 },
      { x: 100, y: 66 },
      { x: 250, y: 66 },
      { x: 250, y: 134 },
      { x: 200, y: 134 },
      { x: 200, y: 200 },
    ]
    const handles = getHandles('5-seg', points)
    expect(handles).toHaveLength(3)
    expect(handles[0].cursor).toBe('ns-resize')
    expect(handles[1].cursor).toBe('ew-resize')
    expect(handles[2].cursor).toBe('ns-resize')
  })
})

// ── Component rendering ────────────────────────────────────────

describe('PipelineEdge component', () => {
  it('renders a path element', () => {
    const { container } = render(
      <svg>
        <PipelineEdge {...makeEdgeProps()} />
      </svg>,
    )
    const path = container.querySelector('[data-testid="edge-a-b"]')
    expect(path).toBeTruthy()
  })

  it('renders 1-seg (co-aligned) with no Q-curves (straight line)', () => {
    const { container } = render(
      <svg>
        <PipelineEdge {...makeEdgeProps({ sourceX: 100, targetX: 100 })} />
      </svg>,
    )
    const path = container.querySelector('[data-testid="edge-a-b"]')
    const d = path?.getAttribute('d') ?? ''
    // 1-seg: M + L only, no Q curves
    expect(d).toContain('M 100,0')
    expect(d).toContain('L 100,200')
    expect(d).not.toContain('Q')
  })

  it('renders 3-seg (non-aligned) with Q-curves', () => {
    const { container } = render(
      <svg>
        <PipelineEdge {...makeEdgeProps({ sourceX: 100, targetX: 200 })} />
      </svg>,
    )
    const path = container.querySelector('[data-testid="edge-a-b"]')
    const d = path?.getAttribute('d') ?? ''
    // 3-seg has 2 bends → Q curves
    expect(d).toContain('Q')
  })

  it('renders 5-seg from waypoints with Q-curves', () => {
    const waypoints = [
      { x: 100, y: 66 },
      { x: 250, y: 66 },
      { x: 250, y: 134 },
      { x: 200, y: 134 },
    ]
    const { container } = render(
      <svg>
        <PipelineEdge {...makeEdgeProps({ data: { waypoints } })} />
      </svg>,
    )
    const path = container.querySelector('[data-testid="edge-a-b"]')
    const d = path?.getAttribute('d') ?? ''
    expect(d).toContain('Q')
    expect(d).toMatch(/^M 100,0/)
  })

  it('does not show drag handles when not editable', () => {
    mockContext.selectedEdgeId = 'a-b'
    const { container } = render(
      <svg>
        <PipelineEdge {...makeEdgeProps()} />
      </svg>,
    )
    expect(container.querySelector('[data-testid="edge-segment-handle"]')).toBeNull()
    mockContext.selectedEdgeId = null
  })

  it('does not show drag handles when edge is not selected', () => {
    mockContext.isEditable = true
    mockContext.selectedEdgeId = 'other-edge'
    const { container } = render(
      <svg>
        <PipelineEdge {...makeEdgeProps()} />
      </svg>,
    )
    expect(container.querySelector('[data-testid="edge-segment-handle"]')).toBeNull()
    mockContext.isEditable = false
    mockContext.selectedEdgeId = null
  })

  it('shows 1 handle with ns-resize for 3-seg (non-aligned) edge', () => {
    mockContext.isEditable = true
    mockContext.selectedEdgeId = 'a-b'
    const { container } = render(
      <svg>
        <PipelineEdge {...makeEdgeProps({ sourceX: 100, targetX: 200 })} />
      </svg>,
    )
    const handles = container.querySelectorAll('[data-testid="edge-segment-handle"]')
    expect(handles).toHaveLength(1)
    expect(handles[0]?.getAttribute('style')).toContain('ns-resize')
    mockContext.isEditable = false
    mockContext.selectedEdgeId = null
  })

  it('shows 1 handle with ew-resize for 1-seg (co-aligned) edge', () => {
    mockContext.isEditable = true
    mockContext.selectedEdgeId = 'a-b'
    const { container } = render(
      <svg>
        <PipelineEdge {...makeEdgeProps({ sourceX: 100, targetX: 100 })} />
      </svg>,
    )
    const handles = container.querySelectorAll('[data-testid="edge-segment-handle"]')
    expect(handles).toHaveLength(1)
    expect(handles[0]?.getAttribute('style')).toContain('ew-resize')
    mockContext.isEditable = false
    mockContext.selectedEdgeId = null
  })

  it('shows 3 handles for 5-seg (waypoints) edge', () => {
    mockContext.isEditable = true
    mockContext.selectedEdgeId = 'a-b'
    const waypoints = [
      { x: 100, y: 66 },
      { x: 250, y: 66 },
      { x: 250, y: 134 },
      { x: 200, y: 134 },
    ]
    const { container } = render(
      <svg>
        <PipelineEdge {...makeEdgeProps({ data: { waypoints } })} />
      </svg>,
    )
    const handles = container.querySelectorAll('[data-testid="edge-segment-handle"]')
    expect(handles).toHaveLength(3)
    // Verify cursors: ns, ew, ns
    expect(handles[0]?.getAttribute('style')).toContain('ns-resize')
    expect(handles[1]?.getAttribute('style')).toContain('ew-resize')
    expect(handles[2]?.getAttribute('style')).toContain('ns-resize')
    mockContext.isEditable = false
    mockContext.selectedEdgeId = null
  })

  it('shows 3 handles for loopback edge (auto 5-seg)', () => {
    mockContext.isEditable = true
    mockContext.selectedEdgeId = 'a-b'
    const { container } = render(
      <svg>
        <PipelineEdge {...makeEdgeProps({ sourceY: 200, targetY: 100 })} />
      </svg>,
    )
    const handles = container.querySelectorAll('[data-testid="edge-segment-handle"]')
    expect(handles).toHaveLength(3)
    mockContext.isEditable = false
    mockContext.selectedEdgeId = null
  })

  it('handle fill and radius match design spec', () => {
    mockContext.isEditable = true
    mockContext.selectedEdgeId = 'a-b'
    const { container } = render(
      <svg>
        <PipelineEdge {...makeEdgeProps({ sourceX: 100, targetX: 200 })} />
      </svg>,
    )
    const handle = container.querySelector('[data-testid="edge-segment-handle"]')
    expect(handle?.getAttribute('fill')).toBe('hsl(var(--primary))')
    expect(handle?.getAttribute('r')).toBe('7')
    expect(handle?.getAttribute('style')).toContain('pointer-events: all')
    mockContext.isEditable = false
    mockContext.selectedEdgeId = null
  })
})
