import type { DragEvent } from 'react'
import type { NodeType } from '@/contracts/api/pipelines-api'
import { NODE_TYPE_DEFINITIONS } from '@/contracts/api/pipelines-api'
import { getNodeConfig } from './utils/node-defaults'
import { cn } from '@/lib/utils'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

interface NodePaletteProps {
  existingNodeTypes: NodeType[]
  onAddNode: (type: NodeType) => void
}

export function NodePalette({ existingNodeTypes, onAddNode }: NodePaletteProps) {
  const hasCaptureNode = existingNodeTypes.includes('capture')

  const handleDragStart = (event: DragEvent, type: NodeType) => {
    event.dataTransfer.setData('application/pipeline-node-type', type)
    event.dataTransfer.effectAllowed = 'move'
  }

  return (
    <TooltipProvider delayDuration={300}>
      <div
        className="flex items-center gap-1 px-3 py-2 border-b bg-card"
        data-testid="node-palette"
      >
        <span className="text-xs text-muted-foreground mr-2 shrink-0">Add node:</span>
        {NODE_TYPE_DEFINITIONS.map((def) => {
          const config = getNodeConfig(def.type)
          const Icon = config.icon
          const isDisabled = def.type === 'capture' && hasCaptureNode

          return (
            <Tooltip key={def.type}>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  draggable={!isDisabled}
                  onDragStart={(e) => handleDragStart(e, def.type)}
                  onClick={() => !isDisabled && onAddNode(def.type)}
                  disabled={isDisabled}
                  className={cn(
                    'flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors',
                    'border border-transparent',
                    isDisabled
                      ? 'opacity-40 cursor-not-allowed'
                      : 'hover:bg-accent hover:border-border cursor-grab active:cursor-grabbing',
                  )}
                  data-testid={`palette-${def.type}`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {def.label}
                </button>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                <p className="text-xs">
                  {isDisabled
                    ? 'Only one Capture node allowed per pipeline'
                    : def.description}
                </p>
              </TooltipContent>
            </Tooltip>
          )
        })}
      </div>
    </TooltipProvider>
  )
}

export default NodePalette
