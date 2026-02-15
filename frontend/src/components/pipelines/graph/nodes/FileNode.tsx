import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { FileText } from 'lucide-react'
import { memo } from 'react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import type { PipelineNodeData } from '@/contracts/api/pipelines-api'

type FileNodeType = Node<PipelineNodeData, 'file'>

const FileNode = memo(({ data }: NodeProps<FileNodeType>) => (
  <div
    className={cn(
      'w-48 rounded-md border-2 bg-card px-3 py-2 shadow-sm',
      data.hasError ? 'border-destructive' : 'border-muted-foreground/40',
    )}
  >
    <Handle type="target" position={Position.Top} />
    <div className="flex items-center gap-2">
      <FileText className="h-4 w-4 text-muted-foreground" />
      <span className="text-sm font-medium">{data.nodeId}</span>
      {data.analyticsCount != null && (
        <Badge variant="secondary" className="ml-auto text-xs">
          {data.analyticsCount.toLocaleString()}
        </Badge>
      )}
    </div>
    {data.properties.extension && (
      <div className="mt-1 text-xs text-muted-foreground">
        {String(data.properties.extension)}
        {data.properties.optional === true && ' (optional)'}
      </div>
    )}
    <Handle type="source" position={Position.Bottom} />
  </div>
))

FileNode.displayName = 'FileNode'

export default FileNode
