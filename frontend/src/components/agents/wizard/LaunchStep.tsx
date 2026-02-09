/**
 * LaunchStep — Step 4: Agent Launch Instructions.
 *
 * Displays start and self-test commands with a collapsible "Previous Commands" section.
 * Commands reference the installed binary path from Step 3.
 *
 * Issue #136 - Agent Setup Wizard (FR-017)
 */

import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { CopyableCodeBlock } from '@/components/agents/wizard/CopyableCodeBlock'
import type { ValidPlatform } from '@/contracts/api/release-manifests-api'

interface LaunchStepProps {
  token: string
  serverUrl: string
  selectedPlatform: ValidPlatform
}

/** Return OS-appropriate recommended install path (matches RegisterStep/ServiceStep). */
function getInstallPath(platform: ValidPlatform): string {
  if (platform.startsWith('windows')) {
    return 'C:\\Program Files\\ShutterSense\\shuttersense-agent.exe'
  }
  return '/usr/local/bin/shuttersense-agent'
}

export function LaunchStep({ token, serverUrl, selectedPlatform }: LaunchStepProps) {
  const [showPrevious, setShowPrevious] = useState(false)
  const isMacOS = selectedPlatform.startsWith('darwin')
  const isUnixLike = isMacOS || selectedPlatform.startsWith('linux')

  const installPath = getInstallPath(selectedPlatform)

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Start the agent and verify it can connect to the server.
      </p>

      {/* Start command */}
      <div className="space-y-2">
        <p className="text-sm font-medium">1. Start the agent</p>
        <CopyableCodeBlock label="start command" language="bash" alwaysShowCopy>
          {`${installPath} start`}
        </CopyableCodeBlock>
        <p className="text-xs text-muted-foreground">
          The agent will connect to the server and begin listening for jobs. Keep the terminal open or continue to Step 5 to configure a background service.
        </p>
      </div>

      {/* Self-test command */}
      <div className="space-y-2">
        <p className="text-sm font-medium">2. Verify the agent (optional)</p>
        <CopyableCodeBlock label="self-test command" language="bash" alwaysShowCopy>
          {`${installPath} self-test`}
        </CopyableCodeBlock>
        <p className="text-xs text-muted-foreground">
          Runs a connectivity check to confirm the agent can reach the server and is properly registered.
        </p>
      </div>

      {/* Collapsible previous commands */}
      <div className="border-t pt-4">
        <Button
          variant="ghost"
          size="sm"
          className="gap-1 text-muted-foreground"
          onClick={() => setShowPrevious(!showPrevious)}
        >
          {showPrevious ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
          Previous Commands
        </Button>
        {showPrevious && (
          <div className="mt-3 space-y-3 pl-2 border-l-2 border-muted">
            {isUnixLike && (
              <CopyableCodeBlock label="chmod command" language="bash" alwaysShowCopy>
                {`sudo chmod +x ${installPath}`}
              </CopyableCodeBlock>
            )}
            <CopyableCodeBlock label="registration command" language="bash" alwaysShowCopy>
              {`${installPath} register --server ${serverUrl} --token ${token}`}
            </CopyableCodeBlock>
          </div>
        )}
      </div>
    </div>
  )
}
