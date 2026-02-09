/**
 * RegisterStep — Step 3: Agent Installation & Registration Instructions.
 *
 * Guides the user through moving/renaming the downloaded binary to its
 * recommended location, clearing macOS quarantine, making it executable,
 * and running the registration command.
 *
 * Issue #136 - Agent Setup Wizard (FR-014 through FR-016)
 */

import { Alert, AlertDescription } from '@/components/ui/alert'
import { CopyableCodeBlock } from '@/components/agents/wizard/CopyableCodeBlock'
import { CheckCircle2, Info } from 'lucide-react'
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

/** Return the downloaded filename based on platform (matches build script output). */
function getDownloadedFilename(platform: ValidPlatform): string {
  if (platform.startsWith('windows')) {
    return `shuttersense-agent-${platform}.exe`
  }
  return `shuttersense-agent-${platform}`
}

/** Return OS-appropriate recommended install path (matches ServiceStep defaults). */
function getInstallPath(platform: ValidPlatform): string {
  if (platform.startsWith('windows')) {
    return 'C:\\Program Files\\ShutterSense\\shuttersense-agent.exe'
  }
  return '/usr/local/bin/shuttersense-agent'
}

export { getServerUrl }

export function RegisterStep({ token, serverUrl, selectedPlatform }: RegisterStepProps) {
  const isMacOS = selectedPlatform.startsWith('darwin')
  const isUnixLike = isMacOS || selectedPlatform.startsWith('linux')
  const isWindows = selectedPlatform.startsWith('windows')

  const downloadedFilename = getDownloadedFilename(selectedPlatform)
  const installPath = getInstallPath(selectedPlatform)

  const registerCommand = `${installPath} register --server ${serverUrl} --token ${token}`

  let stepNumber = 1

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Open a terminal on the target machine and run the following commands to install and register the agent.
      </p>

      {/* Step: Move and rename the binary */}
      {isUnixLike && (
        <div className="space-y-2">
          <p className="text-sm font-medium">{stepNumber++}. Move the binary to the recommended location</p>
          <p className="text-xs text-muted-foreground">
            The downloaded binary includes a platform suffix and needs to be renamed.
            The recommended location is <code className="font-mono bg-muted px-1 py-0.5 rounded">/usr/local/bin/</code> so
            it is available system-wide.
          </p>
          <CopyableCodeBlock label="move and rename" language="bash" alwaysShowCopy>
            {`sudo mv ~/Downloads/${downloadedFilename} ${installPath}`}
          </CopyableCodeBlock>
        </div>
      )}
      {isWindows && (
        <div className="space-y-2">
          <p className="text-sm font-medium">{stepNumber++}. Move the binary to the recommended location</p>
          <p className="text-xs text-muted-foreground">
            The downloaded binary includes a platform suffix and needs to be renamed.
            Move it to a permanent location using an <strong>Administrator</strong> command prompt.
          </p>
          <CopyableCodeBlock label="move and rename" language="powershell" alwaysShowCopy>
            {`mkdir "C:\\Program Files\\ShutterSense"\nmove "%USERPROFILE%\\Downloads\\${downloadedFilename}" "${installPath}"`}
          </CopyableCodeBlock>
        </div>
      )}

      {/* Step: Remove macOS quarantine attribute */}
      {isMacOS && (
        <div className="space-y-2">
          <p className="text-sm font-medium">{stepNumber++}. Remove macOS quarantine attribute</p>
          <p className="text-xs text-muted-foreground">
            macOS blocks downloaded binaries that are not code-signed. This command removes the quarantine flag
            so the agent can run.
          </p>
          <CopyableCodeBlock label="remove quarantine" language="bash" alwaysShowCopy>
            {`sudo xattr -d com.apple.quarantine ${installPath}`}
          </CopyableCodeBlock>
        </div>
      )}

      {/* Step: chmod for Unix-like */}
      {isUnixLike && (
        <div className="space-y-2">
          <p className="text-sm font-medium">{stepNumber++}. Make the binary executable</p>
          <CopyableCodeBlock label="chmod command" language="bash" alwaysShowCopy>
            {`sudo chmod +x ${installPath}`}
          </CopyableCodeBlock>
        </div>
      )}

      {/* Step: Register command */}
      <div className="space-y-2">
        <p className="text-sm font-medium">
          {stepNumber++}. Register the agent
        </p>
        <CopyableCodeBlock label="registration command" language="bash" alwaysShowCopy>
          {registerCommand}
        </CopyableCodeBlock>
      </div>

      {/* Tip about the install path */}
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription className="text-xs">
          The install path <code className="font-mono bg-muted px-1 py-0.5 rounded">{installPath}</code> matches
          the default used in the background service configuration (Step 5). If you install the binary elsewhere,
          adjust the service configuration accordingly.
        </AlertDescription>
      </Alert>

      {/* Expected output */}
      <Alert className="border-success/30 bg-success/10">
        <CheckCircle2 className="h-4 w-4 text-success" />
        <AlertDescription className="text-success-foreground">
          <p className="font-medium">Expected output:</p>
          <code className="text-xs">
            Agent registered successfully. Run &apos;shuttersense-agent start&apos; to begin.
          </code>
        </AlertDescription>
      </Alert>
    </div>
  )
}
