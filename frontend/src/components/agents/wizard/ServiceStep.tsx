/**
 * ServiceStep — Step 5: Background Service Setup.
 *
 * Generates platform-specific service configuration files with user-provided
 * binary path. macOS: launchd plist, Linux: systemd unit, Windows: unsupported.
 * Step is always skippable via the wizard's "Next" button.
 *
 * Issue #136 - Agent Setup Wizard (FR-018 through FR-022)
 */

import { useCallback, useState, useMemo } from 'react'
import { Download, Info } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { CopyableCodeBlock } from '@/components/agents/wizard/CopyableCodeBlock'
import {
  generateLaunchdPlist,
  generateNewsyslogConfig,
  generateSystemdUnit,
} from '@/lib/service-file-generator'
import type { ValidPlatform } from '@/contracts/api/release-manifests-api'

interface ServiceStepProps {
  selectedPlatform: ValidPlatform
}

/** Return OS-appropriate default binary path. */
function getDefaultBinaryPath(platform: ValidPlatform): string {
  if (platform.startsWith('windows')) {
    return 'C:\\Program Files\\ShutterSense\\shuttersense-agent.exe'
  }
  return '/usr/local/bin/shuttersense-agent'
}

/** Validate that the binary path is absolute and well-formed for the platform. */
function validateBinaryPath(
  path: string,
  platform: ValidPlatform
): { valid: boolean; error?: string; warning?: string } {
  const trimmed = path.trim()
  if (!trimmed) return { valid: false }

  const isUnixLike = platform.startsWith('darwin') || platform.startsWith('linux')

  if (isUnixLike) {
    if (!trimmed.startsWith('/')) {
      return { valid: false, error: 'Path must be absolute (start with /)' }
    }
  } else {
    if (!/^[a-zA-Z]:\\/.test(trimmed)) {
      return { valid: false, error: 'Path must be absolute (e.g., C:\\Program Files\\...)' }
    }
  }

  const warning = trimmed.includes(' ')
    ? 'Path contains spaces — this may cause issues with some service managers.'
    : undefined

  return { valid: true, warning }
}

export function ServiceStep({ selectedPlatform }: ServiceStepProps) {
  const isWindows = selectedPlatform.startsWith('windows')
  const isMacOS = selectedPlatform.startsWith('darwin')
  const isLinux = selectedPlatform.startsWith('linux')

  const [binaryPath, setBinaryPath] = useState(() => getDefaultBinaryPath(selectedPlatform))
  const [serviceUser, setServiceUser] = useState('shuttersense')

  const pathValidation = useMemo(
    () => validateBinaryPath(binaryPath, selectedPlatform),
    [binaryPath, selectedPlatform]
  )

  // Windows: unsupported message (T043)
  if (isWindows) {
    return (
      <div className="space-y-6">
        <p className="text-sm text-muted-foreground">
          Configure the agent to run automatically as a background service on startup.
        </p>

        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            Automatic background service setup for Windows is not yet supported. You can run the agent manually or use Windows Task Scheduler.
          </AlertDescription>
        </Alert>

        <p className="text-sm text-muted-foreground">
          Click <span className="font-medium">Next</span> to continue to the summary.
        </p>
      </div>
    )
  }

  // macOS / Linux
  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Configure the agent to run automatically as a background service on startup.
        This step is optional — click <span className="font-medium">Next</span> to skip.
      </p>

      {/* Binary path input (T039, T040) */}
      <div className="space-y-2">
        <Label htmlFor="binary-path">Agent Binary Path</Label>
        <Input
          id="binary-path"
          value={binaryPath}
          onChange={(e) => setBinaryPath(e.target.value)}
          placeholder={getDefaultBinaryPath(selectedPlatform)}
        />
        {pathValidation.error && (
          <p className="text-xs text-destructive">{pathValidation.error}</p>
        )}
        {pathValidation.warning && (
          <p className="text-xs text-amber-600">{pathValidation.warning}</p>
        )}
        <p className="text-xs text-muted-foreground">
          Full path to the installed agent binary on the target machine.
        </p>
      </div>

      {/* Service user input for Linux (T042) */}
      {isLinux && (
        <div className="space-y-2">
          <Label htmlFor="service-user">Service User</Label>
          <Input
            id="service-user"
            value={serviceUser}
            onChange={(e) => setServiceUser(e.target.value)}
            placeholder="shuttersense"
            className="w-48"
          />
          <p className="text-xs text-muted-foreground">
            The Linux user the service will run as. Create it with:
          </p>
          <CopyableCodeBlock label="create service user" language="bash" alwaysShowCopy>
            {`sudo useradd --system --no-create-home ${serviceUser || 'shuttersense'}`}
          </CopyableCodeBlock>
        </div>
      )}

      {/* Generated service file + installation commands */}
      {pathValidation.valid && (
        <>
          {isMacOS && <MacOSServiceConfig binaryPath={binaryPath.trim()} />}
          {isLinux && (
            <LinuxServiceConfig
              binaryPath={binaryPath.trim()}
              serviceUser={serviceUser.trim() || 'shuttersense'}
            />
          )}
        </>
      )}
    </div>
  )
}

/** Trigger a browser download of a text file. */
function downloadTextFile(content: string, filename: string) {
  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/** macOS launchd plist + installation commands (T041). */
function MacOSServiceConfig({ binaryPath }: { binaryPath: string }) {
  const plist = generateLaunchdPlist(binaryPath)
  const plistFilename = 'ai.shuttersense.agent.plist'
  const newsyslogConfig = generateNewsyslogConfig()
  const newsyslogFilename = 'shuttersense.conf'

  const handleDownloadPlist = useCallback(
    () => downloadTextFile(plist, plistFilename),
    [plist]
  )

  const handleDownloadNewsyslog = useCallback(
    () => downloadTextFile(newsyslogConfig, newsyslogFilename),
    [newsyslogConfig]
  )

  return (
    <div className="space-y-4 border-t pt-4">
      <div className="space-y-2">
        <p className="text-sm font-medium">1. Download the service configuration file</p>
        <p className="text-xs text-muted-foreground">
          This file must be placed in <code className="font-mono bg-muted px-1 py-0.5 rounded">/Library/LaunchDaemons/</code> (see step 2).
        </p>
        <Button variant="outline" className="gap-2" onClick={handleDownloadPlist}>
          <Download className="h-4 w-4" />
          Download {plistFilename}
        </Button>
        <details className="text-xs">
          <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
            View file contents
          </summary>
          <div className="mt-2">
            <CopyableCodeBlock label="launchd plist" language="xml" alwaysShowCopy>
              {plist}
            </CopyableCodeBlock>
          </div>
        </details>
      </div>

      <div className="space-y-2">
        <p className="text-sm font-medium">2. Install and start the service</p>
        <CopyableCodeBlock label="macOS install commands" language="bash" alwaysShowCopy>
          {`sudo mkdir -p /var/log/shuttersense\nsudo cp ~/Downloads/${plistFilename} /Library/LaunchDaemons/\nsudo launchctl load /Library/LaunchDaemons/${plistFilename}`}
        </CopyableCodeBlock>
      </div>

      <div className="space-y-2">
        <p className="text-sm font-medium">3. Manage the service</p>
        <CopyableCodeBlock label="macOS manage commands" language="bash" alwaysShowCopy>
          {`# Check status\nsudo launchctl list | grep shuttersense\n\n# Stop the service\nsudo launchctl unload /Library/LaunchDaemons/${plistFilename}\n\n# View logs\ntail -f /var/log/shuttersense/shuttersense-agent.stdout.log`}
        </CopyableCodeBlock>
      </div>

      <div className="space-y-2">
        <p className="text-sm font-medium">4. Configure log rotation (recommended)</p>
        <p className="text-xs text-muted-foreground">
          Without log rotation, log files will grow indefinitely. This configuration rotates logs at 1 MB and keeps 7 compressed backups.
        </p>
        <Button variant="outline" className="gap-2" onClick={handleDownloadNewsyslog}>
          <Download className="h-4 w-4" />
          Download {newsyslogFilename}
        </Button>
        <details className="text-xs">
          <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
            View file contents
          </summary>
          <div className="mt-2">
            <CopyableCodeBlock label="newsyslog config" language="text" alwaysShowCopy>
              {newsyslogConfig}
            </CopyableCodeBlock>
          </div>
        </details>
        <CopyableCodeBlock label="install log rotation" language="bash" alwaysShowCopy>
          {`sudo cp ~/Downloads/${newsyslogFilename} /etc/newsyslog.d/\n\n# Verify configuration is valid\nsudo newsyslog -vn`}
        </CopyableCodeBlock>
      </div>
    </div>
  )
}

/** Linux systemd unit + installation commands (T042). */
function LinuxServiceConfig({
  binaryPath,
  serviceUser,
}: {
  binaryPath: string
  serviceUser: string
}) {
  const unit = generateSystemdUnit(binaryPath, serviceUser)
  const unitFilename = 'shuttersense-agent.service'

  const handleDownload = useCallback(
    () => downloadTextFile(unit, unitFilename),
    [unit]
  )

  return (
    <div className="space-y-4 border-t pt-4">
      <div className="space-y-2">
        <p className="text-sm font-medium">1. Download the service configuration file</p>
        <p className="text-xs text-muted-foreground">
          This file must be placed in <code className="font-mono bg-muted px-1 py-0.5 rounded">/etc/systemd/system/</code> (see step 2).
        </p>
        <Button variant="outline" className="gap-2" onClick={handleDownload}>
          <Download className="h-4 w-4" />
          Download {unitFilename}
        </Button>
        <details className="text-xs">
          <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
            View file contents
          </summary>
          <div className="mt-2">
            <CopyableCodeBlock label="systemd unit file" language="ini" alwaysShowCopy>
              {unit}
            </CopyableCodeBlock>
          </div>
        </details>
      </div>

      <div className="space-y-2">
        <p className="text-sm font-medium">2. Install and start the service</p>
        <CopyableCodeBlock label="Linux install commands" language="bash" alwaysShowCopy>
          {`sudo cp ~/Downloads/${unitFilename} /etc/systemd/system/\nsudo systemctl daemon-reload\nsudo systemctl enable shuttersense-agent\nsudo systemctl start shuttersense-agent`}
        </CopyableCodeBlock>
      </div>

      <div className="space-y-2">
        <p className="text-sm font-medium">3. Manage the service</p>
        <CopyableCodeBlock label="Linux manage commands" language="bash" alwaysShowCopy>
          {`# Check status\nsudo systemctl status shuttersense-agent\n\n# View logs\nsudo journalctl -u shuttersense-agent -f\n\n# Stop the service\nsudo systemctl stop shuttersense-agent`}
        </CopyableCodeBlock>
      </div>
    </div>
  )
}
