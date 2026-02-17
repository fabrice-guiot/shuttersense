import { useCallback, useMemo, useRef } from 'react'
import { BaseEdge, useReactFlow, type EdgeProps } from '@xyflow/react'
import { usePipelineEditor } from '../PipelineEditorContext'

const BORDER_RADIUS = 5
const HANDLE_RADIUS = 7
const SNAP_THRESHOLD = 5
const LOOPBACK_PAD = 30
const LOOPBACK_X_OFFSET = 80

type Point = { x: number; y: number }

export type EdgeConfig = '1-seg' | '3-seg' | '5-seg'

export interface EdgeConfigResult {
  config: EdgeConfig
  points: Point[]
  /** Effective waypoints to persist (0, 2, or 4 items). undefined = clear stored. */
  effectiveWaypoints: Point[] | undefined
}

/**
 * Pure function: compute the edge configuration from endpoint positions and stored waypoints.
 *
 * Rules:
 * - Loopback (sy >= ty): always 5-seg
 * - Co-aligned (|sx-tx| < SNAP) + no stored offsets: 1-seg
 * - Otherwise: 3-seg
 * - Stored 4 waypoints on non-loopback can snap back to 1-seg
 * - Stored 2 waypoints on co-aligned can snap back to 1-seg
 */
export function computeEdgeConfig(
  sx: number,
  sy: number,
  tx: number,
  ty: number,
  storedWaypoints?: Point[],
): EdgeConfigResult {
  const isLoopback = sy >= ty

  if (isLoopback) {
    if (storedWaypoints && storedWaypoints.length === 4) {
      const wp = storedWaypoints
      const points: Point[] = [
        { x: sx, y: sy },
        { x: sx, y: wp[0].y },
        { x: wp[1].x, y: wp[0].y },
        { x: wp[2].x, y: wp[3].y },
        { x: tx, y: wp[3].y },
        { x: tx, y: ty },
      ]
      return {
        config: '5-seg',
        points,
        effectiveWaypoints: [
          { x: sx, y: wp[0].y },
          { x: wp[1].x, y: wp[0].y },
          { x: wp[2].x, y: wp[3].y },
          { x: tx, y: wp[3].y },
        ],
      }
    }
    // Default loopback geometry
    const h1Y = sy + LOOPBACK_PAD
    const h2Y = ty - LOOPBACK_PAD
    const vX = Math.max(sx, tx) + LOOPBACK_X_OFFSET
    const points: Point[] = [
      { x: sx, y: sy },
      { x: sx, y: h1Y },
      { x: vX, y: h1Y },
      { x: vX, y: h2Y },
      { x: tx, y: h2Y },
      { x: tx, y: ty },
    ]
    return { config: '5-seg', points, effectiveWaypoints: undefined }
  }

  // Normal (non-loopback) edge
  const coAligned = Math.abs(sx - tx) < SNAP_THRESHOLD

  if (storedWaypoints && storedWaypoints.length === 4) {
    const wp = storedWaypoints
    const middleVX = wp[1].x
    if (coAligned && Math.abs(middleVX - sx) < SNAP_THRESHOLD) {
      // Snap back to 1-seg
      return {
        config: '1-seg',
        points: [{ x: sx, y: sy }, { x: tx, y: ty }],
        effectiveWaypoints: undefined,
      }
    }
    const points: Point[] = [
      { x: sx, y: sy },
      { x: sx, y: wp[0].y },
      { x: wp[1].x, y: wp[0].y },
      { x: wp[2].x, y: wp[3].y },
      { x: tx, y: wp[3].y },
      { x: tx, y: ty },
    ]
    return {
      config: '5-seg',
      points,
      effectiveWaypoints: [
        { x: sx, y: wp[0].y },
        { x: wp[1].x, y: wp[0].y },
        { x: wp[2].x, y: wp[3].y },
        { x: tx, y: wp[3].y },
      ],
    }
  }

  if (storedWaypoints && storedWaypoints.length === 2) {
    if (coAligned) {
      // Snap back to 1-seg
      return {
        config: '1-seg',
        points: [{ x: sx, y: sy }, { x: tx, y: ty }],
        effectiveWaypoints: undefined,
      }
    }
    const hY = storedWaypoints[0].y
    return {
      config: '3-seg',
      points: [{ x: sx, y: sy }, { x: sx, y: hY }, { x: tx, y: hY }, { x: tx, y: ty }],
      effectiveWaypoints: [{ x: sx, y: hY }, { x: tx, y: hY }],
    }
  }

  // No stored waypoints
  if (coAligned) {
    return {
      config: '1-seg',
      points: [{ x: sx, y: sy }, { x: tx, y: ty }],
      effectiveWaypoints: undefined,
    }
  }

  // Default 3-seg
  const hY = (sy + ty) / 2
  return {
    config: '3-seg',
    points: [{ x: sx, y: sy }, { x: sx, y: hY }, { x: tx, y: hY }, { x: tx, y: ty }],
    effectiveWaypoints: undefined,
  }
}

interface HandleDescriptor {
  x: number
  y: number
  cursor: 'ns-resize' | 'ew-resize'
  /** Which handle index (0-based) in the config's handle list */
  handleIndex: number
}

/**
 * Derive drag handles from the edge config.
 * - 1-seg: 1 handle at midpoint (ew-resize)
 * - 3-seg: 1 handle at midpoint of H segment (ns-resize)
 * - 5-seg: 3 handles on segments 2, 3, 4 (ns, ew, ns)
 */
export function getHandles(config: EdgeConfig, points: Point[]): HandleDescriptor[] {
  switch (config) {
    case '1-seg': {
      const mid = { x: (points[0].x + points[1].x) / 2, y: (points[0].y + points[1].y) / 2 }
      return [{ ...mid, cursor: 'ew-resize', handleIndex: 0 }]
    }
    case '3-seg': {
      // Handle on H segment (points[1] to points[2])
      const mid = { x: (points[1].x + points[2].x) / 2, y: (points[1].y + points[2].y) / 2 }
      return [{ ...mid, cursor: 'ns-resize', handleIndex: 0 }]
    }
    case '5-seg': {
      // Segment 2: H (points[1]→points[2]) — ns-resize
      const mid1 = { x: (points[1].x + points[2].x) / 2, y: (points[1].y + points[2].y) / 2 }
      // Segment 3: V (points[2]→points[3]) — ew-resize
      const mid2 = { x: (points[2].x + points[3].x) / 2, y: (points[2].y + points[3].y) / 2 }
      // Segment 4: H (points[3]→points[4]) — ns-resize
      const mid3 = { x: (points[3].x + points[4].x) / 2, y: (points[3].y + points[4].y) / 2 }
      return [
        { ...mid1, cursor: 'ns-resize', handleIndex: 0 },
        { ...mid2, cursor: 'ew-resize', handleIndex: 1 },
        { ...mid3, cursor: 'ns-resize', handleIndex: 2 },
      ]
    }
  }
}

/**
 * Build an SVG path string from axis-aligned waypoints with rounded corners.
 */
function roundedOrthogonalPath(points: Point[], radius: number = BORDER_RADIUS): string {
  if (points.length < 2) return ''

  let d = `M ${points[0].x},${points[0].y}`

  for (let i = 1; i < points.length - 1; i++) {
    const prev = points[i - 1]
    const curr = points[i]
    const next = points[i + 1]

    const len1 = Math.abs(curr.x - prev.x) + Math.abs(curr.y - prev.y)
    const len2 = Math.abs(next.x - curr.x) + Math.abs(next.y - curr.y)
    const r = Math.max(0, Math.min(radius, len1 / 2, len2 / 2))

    if (r <= 0) {
      d += ` L ${curr.x},${curr.y}`
      continue
    }

    const ux1 = curr.x === prev.x ? 0 : Math.sign(curr.x - prev.x)
    const uy1 = curr.y === prev.y ? 0 : Math.sign(curr.y - prev.y)
    const ux2 = next.x === curr.x ? 0 : Math.sign(next.x - curr.x)
    const uy2 = next.y === curr.y ? 0 : Math.sign(next.y - curr.y)

    const bx = curr.x - ux1 * r
    const by = curr.y - uy1 * r
    const ax = curr.x + ux2 * r
    const ay = curr.y + uy2 * r

    d += ` L ${bx},${by} Q ${curr.x},${curr.y} ${ax},${ay}`
  }

  d += ` L ${points[points.length - 1].x},${points[points.length - 1].y}`
  return d
}

function PipelineEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  data,
  style,
  markerEnd,
}: EdgeProps) {
  const waypoints = data?.waypoints as Point[] | undefined
  const { pushUndo, markDirty, isEditable, selectedEdgeId } = usePipelineEditor()
  const { setEdges, screenToFlowPosition } = useReactFlow()
  const dragging = useRef(false)

  const { config, points } = useMemo(
    () => computeEdgeConfig(sourceX, sourceY, targetX, targetY, waypoints),
    [sourceX, sourceY, targetX, targetY, waypoints],
  )

  const path = useMemo(() => roundedOrthogonalPath(points), [points])

  const handles = useMemo(
    () => getHandles(config, points),
    [config, points],
  )

  const isLoopback = sourceY >= targetY

  const handleDrag = useCallback(
    (handleIndex: number, e: React.PointerEvent) => {
      if (!isEditable) return
      e.stopPropagation()
      e.preventDefault()
      dragging.current = true
      pushUndo()

      const onPointerMove = (ev: PointerEvent) => {
        if (!dragging.current) return
        const flowPos = screenToFlowPosition({ x: ev.clientX, y: ev.clientY })

        setEdges((edges) =>
          edges.map((edge) => {
            if (edge.id !== id) return edge

            const currentWp = edge.data?.waypoints as Point[] | undefined
            const edgeConfig = computeEdgeConfig(
              sourceX, sourceY, targetX, targetY, currentWp,
            )

            let wp: Point[]

            if (edgeConfig.config === '1-seg') {
              // Materialize 4 waypoints (V-H-V-H-V) from drag
              const h1Y = sourceY + (targetY - sourceY) * 0.33
              const h2Y = sourceY + (targetY - sourceY) * 0.67
              wp = [
                { x: sourceX, y: h1Y },
                { x: flowPos.x, y: h1Y },
                { x: flowPos.x, y: h2Y },
                { x: targetX, y: h2Y },
              ]
            } else if (edgeConfig.config === '3-seg') {
              // Update hY — stays 3-seg
              const existingWp = edgeConfig.effectiveWaypoints
              const hY = existingWp ? existingWp[0].y : (sourceY + targetY) / 2
              wp = [
                { x: sourceX, y: flowPos.y },
                { x: targetX, y: flowPos.y },
              ]
              // Only Y moves, ignore hY — directly use flowPos.y
              void hY
            } else {
              // 5-seg: update based on which handle
              const existingWp = currentWp && currentWp.length === 4
                ? currentWp.map((w) => ({ ...w }))
                : edgeConfig.effectiveWaypoints
                  ? edgeConfig.effectiveWaypoints.map((w) => ({ ...w }))
                  : (() => {
                      // Default 5-seg points (loopback default)
                      const h1Y = sourceY + LOOPBACK_PAD
                      const h2Y = targetY - LOOPBACK_PAD
                      const vX = Math.max(sourceX, targetX) + LOOPBACK_X_OFFSET
                      return [
                        { x: sourceX, y: h1Y },
                        { x: vX, y: h1Y },
                        { x: vX, y: h2Y },
                        { x: targetX, y: h2Y },
                      ]
                    })()

              wp = existingWp

              if (handleIndex === 0) {
                // H1 (ns-resize): move h1Y
                wp[0].y = flowPos.y
                wp[1].y = flowPos.y
              } else if (handleIndex === 1) {
                // V2 (ew-resize): move vX
                wp[1].x = flowPos.x
                wp[2].x = flowPos.x
              } else {
                // H2 (ns-resize): move h2Y
                wp[2].y = flowPos.y
                wp[3].y = flowPos.y
              }

              // Pin X endpoints
              wp[0].x = sourceX
              wp[3].x = targetX
            }

            return { ...edge, data: { ...edge.data, waypoints: wp, offset: 0 } }
          }),
        )
      }

      const onPointerUp = () => {
        dragging.current = false

        // Snap-back check on drag end
        if (!isLoopback) {
          setEdges((edges) =>
            edges.map((edge) => {
              if (edge.id !== id) return edge
              const wp = edge.data?.waypoints as Point[] | undefined
              if (!wp || wp.length === 0) return edge

              const coAligned = Math.abs(sourceX - targetX) < SNAP_THRESHOLD

              if (wp.length === 4) {
                const middleVX = wp[1].x
                if (coAligned && Math.abs(middleVX - sourceX) < SNAP_THRESHOLD) {
                  return { ...edge, data: { ...edge.data, waypoints: undefined } }
                }
              } else if (wp.length === 2) {
                if (coAligned) {
                  return { ...edge, data: { ...edge.data, waypoints: undefined } }
                }
              }

              return edge
            }),
          )
        }

        markDirty()
        window.removeEventListener('pointermove', onPointerMove)
        window.removeEventListener('pointerup', onPointerUp)
      }

      window.addEventListener('pointermove', onPointerMove)
      window.addEventListener('pointerup', onPointerUp)
    },
    [id, isEditable, isLoopback, pushUndo, markDirty, setEdges, screenToFlowPosition, sourceX, sourceY, targetX, targetY],
  )

  const isSelected = selectedEdgeId === id

  return (
    <>
      <BaseEdge id={id} path={path} style={style} markerEnd={markerEnd} />
      {isEditable && isSelected &&
        handles.map((h) => (
          <circle
            key={`handle-${h.handleIndex}`}
            cx={h.x}
            cy={h.y}
            r={HANDLE_RADIUS}
            fill="hsl(var(--primary))"
            stroke="hsl(var(--background))"
            strokeWidth={2}
            style={{
              cursor: h.cursor,
              pointerEvents: 'all',
            }}
            onPointerDown={(e) => handleDrag(h.handleIndex, e)}
            data-testid="edge-segment-handle"
          />
        ))}
    </>
  )
}

export default PipelineEdge
