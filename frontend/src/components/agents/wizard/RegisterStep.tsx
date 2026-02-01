/**
 * RegisterStep — Step 3: Agent Registration Instructions.
 *
 * Displays the chmod + register commands with pre-populated server URL and token.
 *
 * Issue #136 - Agent Setup Wizard (FR-014 through FR-016)
 */

import { Alert, AlertDescription } from '@/components/ui/alert'
import { CopyableCodeBlock } from '@/components/agents/wizard/CopyableCodeBlock'
import { CheckCircle2 } from 'lucide-react'
import type { ValidPlatform } from '@/contracts/api/release-manifests-api'

interface RegisterStepProps {
  token: string
  serverUrl: string
  selectedPlatform: ValidPlatform
}

function getServerUrl(): string {
  // Use VITE_API_BASE_URL if set, otherwise derive from current origin
  const envUrl = import.meta.env.VITE_API_BASE_URL
  if (envUrl && envUrl !== '/api') {
    // Absolute URL configured — extract the origin
    try {
      const parsed = new URL(envUrl)
      return parsed.origin
    } catch {
      // Fall through to window.location.origin
    }
  }
  return window.location.origin
}

export { getServerUrl }

export function RegisterStep({ token, serverUrl, selectedPlatform }: RegisterStepProps) {
  const isUnixLike = selectedPlatform.startsWith('darwin') || selectedPlatform.startsWith('linux')
  const chmodCommand = 'chmod +x ./shuttersense-agent'
  const registerCommand = `./shuttersense-agent register --server ${serverUrl} --token ${token}`

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Open a terminal on the target machine and run the following commands to register the agent with the server.
      </p>

      {/* chmod step for macOS/Linux */}
      {isUnixLike && (
        <div className="space-y-2">
          <p className="text-sm font-medium">1. Make the binary executable</p>
          <CopyableCodeBlock label="chmod command" language="bash" alwaysShowCopy>
            {chmodCommand}
          </CopyableCodeBlock>
        </div>
      )}

      {/* Register command */}
      <div className="space-y-2">
        <p className="text-sm font-medium">
          {isUnixLike ? '2. Register the agent' : '1. Register the agent'}
        </p>
        <CopyableCodeBlock label="registration command" language="bash" alwaysShowCopy>
          {registerCommand}
        </CopyableCodeBlock>
      </div>

      {/* Expected output */}
      <Alert className="border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950">
        <CheckCircle2 className="h-4 w-4 text-green-600" />
        <AlertDescription className="text-green-800 dark:text-green-200">
          <p className="font-medium">Expected output:</p>
          <code className="text-xs">
            Agent registered successfully. Run &apos;shuttersense-agent start&apos; to begin.
          </code>
        </AlertDescription>
      </Alert>
    </div>
  )
}
