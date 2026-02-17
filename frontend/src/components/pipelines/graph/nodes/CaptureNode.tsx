import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { Camera } from 'lucide-react'
import { memo } from 'react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import type { PipelineNodeData } from '@/contracts/api/pipelines-api'

type CaptureNodeType = Node<PipelineNodeData, 'capture'>

const CaptureNode = memo(({ data }: NodeProps<CaptureNodeType>) => (
  <div
    className={cn(
      'w-56 min-h-20 rounded-lg border-2 bg-card px-4 py-3 shadow-sm',
      data.hasError ? 'border-destructive' : 'border-primary',
    )}
  >
    <div className="flex items-center gap-2 min-w-0">
      <Camera className="h-5 w-5 text-primary shrink-0" />
      <span className="text-sm font-semibold truncate">
        {(typeof data.properties.name === 'string' && data.properties.name) || data.nodeId}
      </span>
      {data.analyticsCount != null && (
        <Badge variant="secondary" className="ml-auto text-xs shrink-0">
          {data.analyticsCount.toLocaleString()}
        </Badge>
      )}
    </div>
    {data.properties.sample_filename && (
      <div className="mt-1 text-xs text-muted-foreground truncate">
        {String(data.properties.sample_filename)}
      </div>
    )}
    <Handle type="source" position={Position.Bottom} />
  </div>
))

CaptureNode.displayName = 'CaptureNode'

export default CaptureNode
