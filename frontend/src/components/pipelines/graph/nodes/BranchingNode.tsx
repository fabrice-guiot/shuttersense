import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { GitBranch } from 'lucide-react'
import { memo } from 'react'
import { Badge } from '@/components/ui/badge'
import type { PipelineNodeData } from '@/contracts/api/pipelines-api'

type BranchingNodeType = Node<PipelineNodeData, 'branching'>

const BranchingNode = memo(({ data }: NodeProps<BranchingNodeType>) => (
  <div className="relative w-52 h-20">
    <svg
      className="absolute inset-0 w-full h-full"
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
    >
      <polygon
        points="50,2 98,50 50,98 2,50"
        className={data.hasError ? 'fill-card stroke-destructive' : 'fill-card stroke-warning/60'}
        strokeWidth="2"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
    <div className="relative z-10 flex items-center justify-center gap-2 h-full px-6">
      <GitBranch className="h-4 w-4 text-warning shrink-0" />
      <span className="text-sm font-medium truncate">
        {(typeof data.properties.name === 'string' && data.properties.name) || data.nodeId}
      </span>
      {data.analyticsCount != null && (
        <Badge variant="secondary" className="ml-auto text-xs shrink-0">
          {data.analyticsCount.toLocaleString()}
        </Badge>
      )}
    </div>
    <Handle type="target" position={Position.Top} className="!left-1/2" />
    <Handle type="source" position={Position.Bottom} className="!left-1/2" />
  </div>
))

BranchingNode.displayName = 'BranchingNode'

export default BranchingNode
