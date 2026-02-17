import { useMemo } from 'react'
import { BaseEdge, type EdgeProps } from '@xyflow/react'
import { computeEdgeConfig } from './PipelineEdge'

const MIN_STROKE_WIDTH = 2
const MAX_STROKE_WIDTH = 10
const BORDER_RADIUS = 5

type Point = { x: number; y: number }

function buildRoundedPath(points: Point[]): string {
  if (points.length < 2) return ''
  if (points.length === 2) {
    return `M ${points[0].x},${points[0].y} L ${points[1].x},${points[1].y}`
  }

  let d = `M ${points[0].x},${points[0].y}`
  for (let i = 1; i < points.length - 1; i++) {
    const prev = points[i - 1]
    const curr = points[i]
    const next = points[i + 1]

    const dxIn = curr.x - prev.x
    const dyIn = curr.y - prev.y
    const lenIn = Math.sqrt(dxIn * dxIn + dyIn * dyIn)
    const dxOut = next.x - curr.x
    const dyOut = next.y - curr.y
    const lenOut = Math.sqrt(dxOut * dxOut + dyOut * dyOut)

    const r = Math.min(BORDER_RADIUS, lenIn / 2, lenOut / 2)

    const uxIn = lenIn > 0 ? dxIn / lenIn : 0
    const uyIn = lenIn > 0 ? dyIn / lenIn : 0
    const uxOut = lenOut > 0 ? dxOut / lenOut : 0
    const uyOut = lenOut > 0 ? dyOut / lenOut : 0

    const startX = curr.x - uxIn * r
    const startY = curr.y - uyIn * r
    const endX = curr.x + uxOut * r
    const endY = curr.y + uyOut * r

    d += ` L ${startX},${startY}`
    d += ` Q ${curr.x},${curr.y} ${endX},${endY}`
  }

  const last = points[points.length - 1]
  d += ` L ${last.x},${last.y}`
  return d
}

function AnalyticsEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  data,
  markerEnd,
  style,
}: EdgeProps) {
  const recordCount = (data?.record_count as number) ?? 0
  const percentage = (data?.percentage as number) ?? 0
  const maxCount = (data?.maxCount as number) ?? 1
  const waypoints = data?.waypoints as Point[] | undefined

  const { path, labelX, labelY, strokeWidth } = useMemo(() => {
    const { points } = computeEdgeConfig(
      sourceX, sourceY, targetX, targetY, waypoints,
    )
    const d = buildRoundedPath(points)

    // Compute label position at the midpoint of the path
    const midIdx = Math.floor(points.length / 2)
    const lx = midIdx > 0
      ? (points[midIdx - 1].x + points[midIdx].x) / 2
      : points[0].x
    const ly = midIdx > 0
      ? (points[midIdx - 1].y + points[midIdx].y) / 2
      : points[0].y

    // Proportional stroke width
    const ratio = maxCount > 0 ? recordCount / maxCount : 0
    const sw = MIN_STROKE_WIDTH + ratio * (MAX_STROKE_WIDTH - MIN_STROKE_WIDTH)

    return { path: d, labelX: lx, labelY: ly, strokeWidth: sw }
  }, [sourceX, sourceY, targetX, targetY, waypoints, recordCount, maxCount])

  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        markerEnd={markerEnd}
        style={{
          ...style,
          strokeWidth,
          opacity: 0.8,
        }}
      />
      {recordCount > 0 && (
        <foreignObject
          x={labelX - 28}
          y={labelY - 12}
          width={56}
          height={24}
          requiredExtensions="http://www.w3.org/1999/xhtml"
        >
          <div
            className="flex items-center justify-center rounded bg-background/90 px-1.5 py-0.5 text-[10px] font-medium text-foreground shadow-sm border"
            title={`${recordCount} records (${percentage.toFixed(1)}%)`}
          >
            {recordCount.toLocaleString()}
          </div>
        </foreignObject>
      )}
    </>
  )
}

export default AnalyticsEdge
