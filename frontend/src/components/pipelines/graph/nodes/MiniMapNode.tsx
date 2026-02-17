import { useReactFlow, type MiniMapNodeProps } from '@xyflow/react'

const nodeStyle = {
  fill: 'var(--xy-minimap-node-background-color)',
  stroke: 'var(--xy-minimap-node-stroke-color)',
}

/**
 * Custom minimap node that renders diamond shapes for pairing/branching nodes
 * and default rectangles for all other node types.
 */
function MiniMapNode({
  id,
  x,
  y,
  width,
  height,
  strokeWidth,
  shapeRendering,
  selected,
  onClick,
}: MiniMapNodeProps) {
  const { getNode } = useReactFlow()
  const nodeType = getNode(id)?.type
  const isDiamond = nodeType === 'pairing' || nodeType === 'branching'

  if (isDiamond) {
    const cx = x + width / 2
    const cy = y + height / 2
    const hw = width / 2
    const hh = height / 2

    return (
      <polygon
        points={`${cx},${cy - hh} ${cx + hw},${cy} ${cx},${cy + hh} ${cx - hw},${cy}`}
        style={nodeStyle}
        strokeWidth={strokeWidth}
        shapeRendering={shapeRendering}
        className={selected ? 'selected' : ''}
        onClick={onClick ? (e) => onClick(e, id) : undefined}
      />
    )
  }

  return (
    <rect
      x={x}
      y={y}
      width={width}
      height={height}
      rx={5}
      ry={5}
      style={nodeStyle}
      strokeWidth={strokeWidth}
      shapeRendering={shapeRendering}
      className={selected ? 'selected' : ''}
      onClick={onClick ? (e) => onClick(e, id) : undefined}
    />
  )
}

export default MiniMapNode
