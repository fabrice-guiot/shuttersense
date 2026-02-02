/**
 * SummaryStep — Step 6: Setup Summary.
 *
 * Recaps platform, token name, registration command, and OS-dependent config paths.
 *
 * Issue #136 - Agent Setup Wizard (FR-023, PRD FR-700.2, FR-700.3)
 */

import { CheckCircle2, FolderOpen, Monitor } from 'lucide-react'
import { PLATFORM_LABELS, type ValidPlatform } from '@/contracts/api/release-manifests-api'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface SummaryStepProps {
  selectedPlatform: ValidPlatform
  tokenName: string | null
  serverUrl: string
}

function getConfigPath(platform: ValidPlatform): string {
  if (platform.startsWith('darwin')) {
    return '~/Library/Application Support/shuttersense/'
  }
  if (platform.startsWith('linux')) {
    return '~/.config/shuttersense/'
  }
  return '%APPDATA%\\shuttersense\\'
}

export function SummaryStep({ selectedPlatform, tokenName, serverUrl }: SummaryStepProps) {
  const configPath = getConfigPath(selectedPlatform)

  return (
    <div className="space-y-6">
      <Alert className="border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950">
        <CheckCircle2 className="h-4 w-4 text-green-600" />
        <AlertDescription className="text-green-800 dark:text-green-200">
          Agent setup is complete. The agent should now appear on the Agents page once it connects.
        </AlertDescription>
      </Alert>

      {/* Setup recap */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium">Setup Summary</h3>
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
          <dt className="text-muted-foreground">Platform</dt>
          <dd>{PLATFORM_LABELS[selectedPlatform]}</dd>

          <dt className="text-muted-foreground">Token</dt>
          <dd>{tokenName || 'Unnamed token'}</dd>

          <dt className="text-muted-foreground">Server</dt>
          <dd className="font-mono text-xs break-all">{serverUrl}</dd>
        </dl>
      </div>

      {/* Config file paths */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-sm font-medium">
          <FolderOpen className="h-4 w-4" />
          Configuration &amp; Data Files
        </div>
        <p className="text-sm text-muted-foreground">
          The agent stores its configuration and cached data in:
        </p>
        <code className="block text-xs font-mono bg-muted p-2 rounded-md break-all">
          {configPath}
        </code>
      </div>

      {/* Monitoring reminder */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Monitor className="h-4 w-4" />
          Next Steps
        </div>
        <p className="text-sm text-muted-foreground">
          Monitor your agent from the <span className="font-medium">Agents</span> page. Once the agent connects, it will appear as &quot;online&quot; and begin accepting analysis jobs.
        </p>
      </div>
    </div>
  )
}
