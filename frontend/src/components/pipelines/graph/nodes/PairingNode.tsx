import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { Merge } from 'lucide-react'
import { memo } from 'react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import type { PipelineNodeData } from '@/contracts/api/pipelines-api'

type PairingNodeType = Node<PipelineNodeData, 'pairing'>

const PairingNode = memo(({ data }: NodeProps<PairingNodeType>) => (
  <div
    className={cn(
      'w-44 border-2 bg-card px-3 py-2 shadow-sm rotate-45',
      data.hasError ? 'border-destructive' : 'border-info/60',
    )}
  >
    <Handle type="target" position={Position.Top} />
    <div className="flex items-center gap-2 -rotate-45">
      <Merge className="h-4 w-4 text-info" />
      <span className="text-sm font-medium">{data.nodeId}</span>
      {data.analyticsCount != null && (
        <Badge variant="secondary" className="ml-auto text-xs">
          {data.analyticsCount.toLocaleString()}
        </Badge>
      )}
    </div>
    <Handle type="source" position={Position.Bottom} />
  </div>
))

PairingNode.displayName = 'PairingNode'

export default PairingNode
