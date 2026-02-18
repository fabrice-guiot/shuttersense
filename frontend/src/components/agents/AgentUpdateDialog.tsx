/**
 * AgentUpdateDialog Component
 *
 * Shows version comparison, platform-specific download button, and
 * step-by-step update instructions per platform (macOS launchd,
 * Linux systemd, Windows Task Scheduler, generic).
 *
 * Issue #242 - Outdated Agent Detection (Frontend)
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertTriangle,
  Check,
  Copy,
  Download,
  Info,
  Loader2,
  RefreshCw,
  ArrowRight,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { CopyableCodeBlock } from '@/components/agents/wizard/CopyableCodeBlock'
import { useClipboard } from '@/hooks/useClipboard'
import { PLATFORM_LABELS, type ValidPlatform } from '@/contracts/api/release-manifests-api'
import type { ActiveReleaseResponse, ReleaseArtifact, Agent } from '@/contracts/api/agent-api'
import { getActiveRelease } from '@/services/agents'

// ============================================================================
// Types
// ============================================================================

interface AgentUpdateDialogProps {
  agent: Agent | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

type PlatformFamily = 'macos' | 'linux' | 'windows' | 'generic'

// ============================================================================
// Helpers
// ============================================================================

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function parseSignedUrlExpiry(signedUrl: string): Date | null {
  try {
    const url = new URL(signedUrl, window.location.origin)
    const expires = url.searchParams.get('expires')
    if (!expires) return null
    const expiresMs = parseInt(expires, 10) * 1000
    if (isNaN(expiresMs)) return null
    return new Date(expiresMs)
  } catch {
    return null
  }
}

function buildFullSignedUrl(signedUrl: string): string {
  const prefix = signedUrl.startsWith('/') ? '' : '/'
  return `${window.location.origin}${prefix}${signedUrl}`
}

/** Map agent platform string to a ValidPlatform, or null if unrecognized. */
function agentPlatformToValidPlatform(platform: string | null): ValidPlatform | null {
  if (!platform) return null
  // The backend stores platform as e.g. "darwin-arm64", "linux-amd64", etc.
  const knownPlatforms: ValidPlatform[] = [
    'darwin-arm64',
    'darwin-amd64',
    'linux-amd64',
    'linux-arm64',
    'windows-amd64',
  ]
  return knownPlatforms.find((p) => p === platform) ?? null
}

/** Determine the platform family for instructions. */
function getPlatformFamily(platform: ValidPlatform | null): PlatformFamily {
  if (!platform) return 'generic'
  if (platform.startsWith('darwin')) return 'macos'
  if (platform.startsWith('linux')) return 'linux'
  if (platform.startsWith('windows')) return 'windows'
  return 'generic'
}

// ============================================================================
// Instructions per platform
// ============================================================================

function getMacOSInstructions(filename: string): string[] {
  return [
    'Stop the running agent service:',
    `  launchctl unload ~/Library/LaunchAgents/com.shuttersense.agent.plist`,
    `Replace the binary with the downloaded version:`,
    `  chmod +x ~/${filename}`,
    `  mv ~/${filename} /usr/local/bin/shuttersense-agent`,
    `Restart the agent service:`,
    `  launchctl load ~/Library/LaunchAgents/com.shuttersense.agent.plist`,
  ]
}

function getLinuxInstructions(filename: string): string[] {
  return [
    'Stop the running agent service:',
    `  sudo systemctl stop shuttersense-agent`,
    `Replace the binary with the downloaded version:`,
    `  chmod +x ~/${filename}`,
    `  sudo mv ~/${filename} /usr/local/bin/shuttersense-agent`,
    `Restart the agent service:`,
    `  sudo systemctl start shuttersense-agent`,
  ]
}

function getWindowsInstructions(filename: string): string[] {
  return [
    'Stop the running agent from Task Scheduler:',
    `  Open Task Scheduler, find "ShutterSense Agent", and click "End"`,
    `Replace the binary with the downloaded version:`,
    `  Move ${filename} to the agent installation directory (e.g., C:\\Program Files\\ShutterSense\\)`,
    `Restart the agent from Task Scheduler:`,
    `  Right-click "ShutterSense Agent" and click "Run"`,
  ]
}

function getGenericInstructions(filename: string): string[] {
  return [
    'Stop the currently running agent process.',
    `Replace the agent binary with the downloaded file (${filename}).`,
    'Ensure the binary is executable (chmod +x on Unix systems).',
    'Restart the agent process or service.',
  ]
}

function getInstructions(family: PlatformFamily, filename: string): string[] {
  switch (family) {
    case 'macos':
      return getMacOSInstructions(filename)
    case 'linux':
      return getLinuxInstructions(filename)
    case 'windows':
      return getWindowsInstructions(filename)
    default:
      return getGenericInstructions(filename)
  }
}

function getFamilyLabel(family: PlatformFamily): string {
  switch (family) {
    case 'macos':
      return 'macOS (launchd)'
    case 'linux':
      return 'Linux (systemd)'
    case 'windows':
      return 'Windows (Task Scheduler)'
    default:
      return 'Manual Update'
  }
}

// ============================================================================
// Component
// ============================================================================

export function AgentUpdateDialog({
  agent,
  open,
  onOpenChange,
}: AgentUpdateDialogProps) {
  const [activeRelease, setActiveRelease] = useState<ActiveReleaseResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [downloadError, setDownloadError] = useState<string | null>(null)
  const [isDownloading, setIsDownloading] = useState(false)
  const [nearExpiry, setNearExpiry] = useState(false)
  const fetchedAtRef = useRef<number>(0)
  const { copy, copied } = useClipboard()

  const validPlatform = useMemo(
    () => agentPlatformToValidPlatform(agent?.platform ?? null),
    [agent?.platform]
  )

  const platformFamily = useMemo(
    () => getPlatformFamily(validPlatform),
    [validPlatform]
  )

  const matchingArtifact: ReleaseArtifact | undefined = useMemo(
    () =>
      validPlatform
        ? activeRelease?.artifacts.find((a) => a.platform === validPlatform)
        : undefined,
    [activeRelease, validPlatform]
  )

  const fetchRelease = useCallback(() => {
    setLoading(true)
    setError(null)
    setNearExpiry(false)
    fetchedAtRef.current = Date.now()

    getActiveRelease()
      .then((release) => setActiveRelease(release))
      .catch(() =>
        setError('No release available. Contact your administrator for the agent binary.')
      )
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (open) {
      fetchRelease()
    }
  }, [open, fetchRelease])

  // Check for near-expiry signed URLs (> 50 minutes since fetch)
  useEffect(() => {
    if (!matchingArtifact?.signed_url) return

    const checkExpiry = () => {
      const elapsed = Date.now() - fetchedAtRef.current
      if (elapsed > 50 * 60 * 1000) {
        setNearExpiry(true)
      }
    }

    const interval = setInterval(checkExpiry, 60_000)
    checkExpiry()
    return () => clearInterval(interval)
  }, [matchingArtifact?.signed_url])

  const handleDownload = useCallback(
    (artifact: ReleaseArtifact) => {
      if (!artifact.download_url) return
      setDownloadError(null)
      setIsDownloading(true)

      try {
        const link = document.createElement('a')
        link.href = artifact.download_url
        link.download = artifact.filename
        link.style.display = 'none'
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        setTimeout(() => setIsDownloading(false), 2000)
      } catch {
        setDownloadError(
          'Failed to start download. Try the signed URL below to download manually.'
        )
        setIsDownloading(false)
      }
    },
    []
  )

  const signedUrlExpiry = matchingArtifact?.signed_url
    ? parseSignedUrlExpiry(matchingArtifact.signed_url)
    : null
  const fullSignedUrl = matchingArtifact?.signed_url
    ? buildFullSignedUrl(matchingArtifact.signed_url)
    : null

  if (!agent) return null

  const instructions = matchingArtifact
    ? getInstructions(platformFamily, matchingArtifact.filename)
    : []

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Update Agent</DialogTitle>
          <DialogDescription>
            Update &quot;{agent.name}&quot; to the latest version.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5">
          {/* Version comparison */}
          <div className="flex items-center gap-3 flex-wrap">
            <div className="text-sm">
              <span className="text-muted-foreground">Current:</span>{' '}
              <Badge variant="outline" className="font-mono">
                {agent.version}
              </Badge>
            </div>
            <ArrowRight className="h-4 w-4 text-muted-foreground" />
            <div className="text-sm">
              <span className="text-muted-foreground">Latest:</span>{' '}
              {loading ? (
                <Loader2 className="inline h-3 w-3 animate-spin" />
              ) : activeRelease ? (
                <Badge variant="success" className="font-mono">
                  {activeRelease.version}
                </Badge>
              ) : (
                <span className="text-muted-foreground">&mdash;</span>
              )}
            </div>
          </div>

          {/* Platform info */}
          {validPlatform && (
            <p className="text-sm text-muted-foreground">
              Platform: {PLATFORM_LABELS[validPlatform]}
            </p>
          )}
          {!validPlatform && agent.platform && (
            <p className="text-sm text-muted-foreground">
              Platform: {agent.platform} (unrecognized)
            </p>
          )}
          {!agent.platform && (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                This agent has not reported its platform. Update the agent manually
                or wait for the next heartbeat.
              </AlertDescription>
            </Alert>
          )}

          {/* Fetch error */}
          {error && !loading && (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Download section */}
          {activeRelease && !loading && matchingArtifact && (
            <div className="space-y-4">
              {/* Download button */}
              <div className="space-y-2">
                {matchingArtifact.download_url ? (
                  <Button
                    className="gap-2"
                    onClick={() => handleDownload(matchingArtifact)}
                    disabled={isDownloading}
                  >
                    {isDownloading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Download className="h-4 w-4" />
                    )}
                    Download {matchingArtifact.filename}
                    {matchingArtifact.file_size != null && (
                      <span className="opacity-70">
                        ({formatFileSize(matchingArtifact.file_size)})
                      </span>
                    )}
                  </Button>
                ) : (
                  <Button variant="outline" className="gap-2" disabled>
                    <Download className="h-4 w-4" />
                    {matchingArtifact.filename}
                  </Button>
                )}

                {downloadError && (
                  <Alert variant="destructive">
                    <AlertDescription className="flex items-center gap-2">
                      <span>{downloadError}</span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDownload(matchingArtifact)}
                      >
                        Retry
                      </Button>
                    </AlertDescription>
                  </Alert>
                )}
              </div>

              {/* Checksum */}
              <p className="text-xs text-muted-foreground font-mono break-all">
                Checksum: {matchingArtifact.checksum}
              </p>

              {/* Signed URL section */}
              {matchingArtifact.signed_url && fullSignedUrl && (
                <div className="space-y-3 border-t pt-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">Remote Download Link</span>
                      {signedUrlExpiry && (
                        <span className="text-xs text-muted-foreground">
                          valid until {signedUrlExpiry.toLocaleTimeString()}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Use this link to download the updated binary directly on the agent machine.
                    </p>
                  </div>

                  {nearExpiry && (
                    <Alert className="border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950">
                      <AlertTriangle className="h-4 w-4 text-amber-600" />
                      <AlertDescription className="flex items-center justify-between text-amber-800 dark:text-amber-200">
                        <span>This link will expire soon.</span>
                        <Button
                          variant="outline"
                          size="sm"
                          className="gap-1 ml-2"
                          onClick={fetchRelease}
                        >
                          <RefreshCw className="h-3 w-3" />
                          Refresh
                        </Button>
                      </AlertDescription>
                    </Alert>
                  )}

                  <CopyableCodeBlock label="curl download command" language="bash" alwaysShowCopy>
                    {`curl -fLo ${matchingArtifact.filename} "${fullSignedUrl}"`}
                  </CopyableCodeBlock>

                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1"
                    onClick={() => copy(fullSignedUrl)}
                    aria-label="Copy signed download link"
                  >
                    {copied ? (
                      <Check className="h-3 w-3 text-green-600" />
                    ) : (
                      <Copy className="h-3 w-3" />
                    )}
                    {copied ? 'Copied!' : 'Copy Link'}
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* No matching artifact */}
          {activeRelease && !loading && !matchingArtifact && validPlatform && (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                No build available for {PLATFORM_LABELS[validPlatform]}. Contact your
                administrator to upload the binary for this platform.
              </AlertDescription>
            </Alert>
          )}

          {/* Update instructions */}
          {matchingArtifact && instructions.length > 0 && (
            <div className="space-y-2 border-t pt-4">
              <p className="text-sm font-medium">
                Update Instructions ({getFamilyLabel(platformFamily)})
              </p>
              <ol className="space-y-1 text-sm text-muted-foreground list-decimal list-inside">
                {instructions.map((step, i) => (
                  <li
                    key={i}
                    className={step.startsWith('  ') ? 'ml-4 list-none' : ''}
                  >
                    {step.startsWith('  ') ? (
                      <code className="text-xs font-mono bg-muted px-1 py-0.5 rounded">
                        {step.trim()}
                      </code>
                    ) : (
                      step
                    )}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

export default AgentUpdateDialog
