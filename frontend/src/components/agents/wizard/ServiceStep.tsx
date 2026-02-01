/**
 * ServiceStep — Step 5: Background Service Setup (placeholder).
 *
 * Phase 3 placeholder — shows skip guidance. Full implementation in Phase 6 (US3).
 *
 * Issue #136 - Agent Setup Wizard (FR-022)
 */

import { Info } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'

export function ServiceStep() {
  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Configure the agent to run automatically as a background service on startup.
      </p>

      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          Background service configuration will be available in a future update. For now, you can run the agent manually with <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">./shuttersense-agent start</code> or skip this step.
        </AlertDescription>
      </Alert>

      <p className="text-sm text-muted-foreground">
        Click <span className="font-medium">Next</span> to continue to the summary, or go back to review previous steps.
      </p>
    </div>
  )
}
