import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { Archive } from 'lucide-react'
import { memo } from 'react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import type { PipelineNodeData } from '@/contracts/api/pipelines-api'

type TerminationNodeType = Node<PipelineNodeData, 'termination'>

const TerminationNode = memo(({ data }: NodeProps<TerminationNodeType>) => (
  <div
    className={cn(
      'w-48 min-h-16 rounded-lg border-2 bg-card px-3 py-2 shadow-sm ring-2 ring-offset-1 ring-offset-card',
      data.hasError
        ? 'border-destructive ring-destructive/30'
        : 'border-success ring-success/30',
    )}
    aria-label={`Termination node: ${(typeof data.properties.name === 'string' && data.properties.name) || data.nodeId}`}
  >
    <Handle type="target" position={Position.Top} />
    <div className="flex items-center gap-2 min-w-0">
      <Archive className="h-4 w-4 text-success shrink-0" />
      <span className="text-sm font-medium truncate">
        {(typeof data.properties.name === 'string' && data.properties.name) || data.nodeId}
      </span>
      {data.analyticsCount != null && (
        <Badge variant="secondary" className="ml-auto text-xs shrink-0">
          {data.analyticsCount.toLocaleString()}
        </Badge>
      )}
    </div>
    {data.properties.termination_type && (
      <div className="mt-1 text-xs text-muted-foreground truncate">
        {String(data.properties.termination_type)}
      </div>
    )}
  </div>
))

TerminationNode.displayName = 'TerminationNode'

export default TerminationNode
