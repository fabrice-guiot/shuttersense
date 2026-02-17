import { useMemo } from 'react'
import { BaseEdge, type EdgeProps } from '@xyflow/react'
import { computeEdgeConfig, roundedOrthogonalPath } from './PipelineEdge'

const MIN_STROKE_WIDTH = 2
const MAX_STROKE_WIDTH = 10

type Point = { x: number; y: number }

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
    const d = roundedOrthogonalPath(points)

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
