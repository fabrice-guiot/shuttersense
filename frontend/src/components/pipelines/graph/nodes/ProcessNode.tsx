import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { Settings } from 'lucide-react'
import { memo } from 'react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import type { PipelineNodeData } from '@/contracts/api/pipelines-api'

type ProcessNodeType = Node<PipelineNodeData, 'process'>

const ProcessNode = memo(({ data }: NodeProps<ProcessNodeType>) => (
  <div
    className={cn(
      'w-48 rounded-md border-2 bg-card px-3 py-2 shadow-sm',
      data.hasError ? 'border-destructive' : 'border-purple-500/60',
    )}
  >
    <Handle type="target" position={Position.Top} />
    <div className="flex items-center gap-2">
      <Settings className="h-4 w-4 text-purple-500" />
      <span className="text-sm font-medium">{data.nodeId}</span>
      {data.analyticsCount != null && (
        <Badge variant="secondary" className="ml-auto text-xs">
          {data.analyticsCount.toLocaleString()}
        </Badge>
      )}
    </div>
    {Array.isArray(data.properties.method_ids) && data.properties.method_ids.length > 0 && (
      <div className="mt-1 text-xs text-muted-foreground truncate">
        {(data.properties.method_ids as string[]).join(', ')}
      </div>
    )}
    <Handle type="source" position={Position.Bottom} />
  </div>
))

ProcessNode.displayName = 'ProcessNode'

export default ProcessNode
