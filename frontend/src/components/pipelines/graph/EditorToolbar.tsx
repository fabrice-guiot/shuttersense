import {
  LayoutGrid,
  Undo2,
  Redo2,
  Grid3X3,
  CheckCircle,
  XCircle,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Toggle } from '@/components/ui/toggle'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Badge } from '@/components/ui/badge'

interface EditorToolbarProps {
  onAutoLayout: () => void
  onUndo: () => void
  onRedo: () => void
  canUndo: boolean
  canRedo: boolean
  snapToGrid: boolean
  onToggleSnapToGrid: () => void
  isValid: boolean
  validationHints: string[]
}

export function EditorToolbar({
  onAutoLayout,
  onUndo,
  onRedo,
  canUndo,
  canRedo,
  snapToGrid,
  onToggleSnapToGrid,
  isValid,
  validationHints,
}: EditorToolbarProps) {
  return (
    <TooltipProvider delayDuration={300}>
      <div
        className="flex items-center gap-1 px-3 py-1.5 border-b bg-card"
        data-testid="editor-toolbar"
      >
        {/* Auto Layout */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="ghost" size="sm" onClick={onAutoLayout} className="h-7 px-2 gap-1.5">
              <LayoutGrid className="h-3.5 w-3.5" />
              <span className="text-xs">Auto Layout</span>
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            <p className="text-xs">Automatically arrange nodes (dagre layout)</p>
          </TooltipContent>
        </Tooltip>

        <div className="w-px h-4 bg-border mx-1" />

        {/* Undo */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={onUndo}
              disabled={!canUndo}
              className="h-7 w-7"
            >
              <Undo2 className="h-3.5 w-3.5" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            <p className="text-xs">Undo (Ctrl+Z)</p>
          </TooltipContent>
        </Tooltip>

        {/* Redo */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={onRedo}
              disabled={!canRedo}
              className="h-7 w-7"
            >
              <Redo2 className="h-3.5 w-3.5" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            <p className="text-xs">Redo (Ctrl+Shift+Z)</p>
          </TooltipContent>
        </Tooltip>

        <div className="w-px h-4 bg-border mx-1" />

        {/* Snap to Grid */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Toggle
              pressed={snapToGrid}
              onPressedChange={onToggleSnapToGrid}
              size="sm"
              className="h-7 w-7 p-0"
              aria-label="Toggle snap to grid"
            >
              <Grid3X3 className="h-3.5 w-3.5" />
            </Toggle>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            <p className="text-xs">Snap to grid {snapToGrid ? '(on)' : '(off)'}</p>
          </TooltipContent>
        </Tooltip>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Validation Status */}
        {isValid ? (
          <Badge variant="outline" className="gap-1 border-green-500/50 text-green-600 dark:text-green-400 text-xs">
            <CheckCircle className="h-3 w-3" />
            Valid
          </Badge>
        ) : (
          <Popover>
            <PopoverTrigger asChild>
              <Badge
                variant="destructive"
                className="gap-1 text-xs cursor-pointer hover:bg-destructive/90"
              >
                <XCircle className="h-3 w-3" />
                {validationHints.length} issue{validationHints.length !== 1 ? 's' : ''}
              </Badge>
            </PopoverTrigger>
            <PopoverContent side="bottom" align="end" className="w-80">
              <div className="space-y-2">
                <p className="text-sm font-medium">Validation Issues</p>
                <ul className="space-y-1">
                  {validationHints.map((hint, i) => (
                    <li key={i} className="text-xs text-muted-foreground flex items-start gap-1.5">
                      <XCircle className="h-3 w-3 text-destructive shrink-0 mt-0.5" />
                      {hint}
                    </li>
                  ))}
                </ul>
              </div>
            </PopoverContent>
          </Popover>
        )}
      </div>
    </TooltipProvider>
  )
}

export default EditorToolbar
