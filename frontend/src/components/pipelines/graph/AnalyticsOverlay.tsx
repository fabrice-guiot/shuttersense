import { Activity } from 'lucide-react'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

interface AnalyticsOverlayProps {
  enabled: boolean
  showFlow: boolean
  onShowFlowChange: (show: boolean) => void
  totalRecords?: number
}

export function AnalyticsOverlay({
  enabled,
  showFlow,
  onShowFlowChange,
  totalRecords,
}: AnalyticsOverlayProps) {
  return (
    <div className="absolute top-3 right-3 z-10 flex items-center gap-3 rounded-lg bg-background/95 border px-3 py-2 shadow-sm backdrop-blur-sm">
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <Label htmlFor="show-flow" className="text-sm cursor-pointer select-none">
                Show Flow
              </Label>
              <Switch
                id="show-flow"
                checked={showFlow}
                onCheckedChange={onShowFlowChange}
                disabled={!enabled}
              />
            </div>
          </TooltipTrigger>
          {!enabled && (
            <TooltipContent side="bottom">
              No analysis results available. Run pipeline validation to see flow data.
            </TooltipContent>
          )}
        </Tooltip>
      </TooltipProvider>
      {showFlow && totalRecords != null && (
        <span className="text-xs text-muted-foreground border-l pl-3">
          {totalRecords.toLocaleString()} records
        </span>
      )}
    </div>
  )
}

export default AnalyticsOverlay
