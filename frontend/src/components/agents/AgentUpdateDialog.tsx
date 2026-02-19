/**
 * AgentUpdateDialog Component — 4-step update wizard.
 *
 * Guides the user through: Download → Stop Agent → Replace Binary → Start Agent.
 * Steps 2 & 4 offer "Background Service" vs "Manual" tabs so users can
 * pick the variant matching their setup.
 *
 * The Download step reuses the same OS-detection / platform-override pattern
 * as the setup wizard's DownloadStep: when the agent has reported its platform
 * we use that, otherwise we fall back to browser user-agent detection.  The
 * user can always override the target platform (useful when downloading via
 * signed URL onto the agent machine from a different browser).
 *
 * Issue #236 - Agent Update Wizard & Version Sort Fix
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  AlertTriangle,
  ArrowRight,
  Check,
  ChevronLeft,
  ChevronRight,
  Copy,
  Download,
  Info,
  Loader2,
  RefreshCw,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { CopyableCodeBlock } from '@/components/agents/wizard/CopyableCodeBlock'
import { useClipboard } from '@/hooks/useClipboard'
import { cn } from '@/lib/utils'
import { detectPlatform } from '@/lib/os-detection'
import {
  PLATFORM_LABELS,
  VALID_PLATFORMS,
  type ValidPlatform,
} from '@/contracts/api/release-manifests-api'
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

const UPDATE_STEPS = [
  { number: 1, title: 'Download' },
  { number: 2, title: 'Stop Agent' },
  { number: 3, title: 'Replace Binary' },
  { number: 4, title: 'Start Agent' },
] as const

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

function isSecureContext(): boolean {
  const { protocol, hostname } = window.location
  if (protocol === 'https:') return true
  if (hostname === 'localhost' || hostname === '127.0.0.1') return true
  return false
}

function agentPlatformToValidPlatform(platform: string | null): ValidPlatform | null {
  if (!platform) return null
  const knownPlatforms: ValidPlatform[] = [
    'darwin-arm64',
    'darwin-amd64',
    'linux-amd64',
    'linux-arm64',
    'windows-amd64',
  ]
  return knownPlatforms.find((p) => p === platform) ?? null
}

function getPlatformFamily(platform: ValidPlatform): PlatformFamily {
  if (platform.startsWith('darwin')) return 'macos'
  if (platform.startsWith('linux')) return 'linux'
  if (platform.startsWith('windows')) return 'windows'
  return 'generic'
}

/**
 * Determine the initial platform for the wizard.
 * If the agent reported a known platform, use that.  Otherwise detect from
 * the browser user-agent (same as the setup wizard).
 */
function resolveInitialPlatform(agent: Agent | null): {
  platform: ValidPlatform
  source: 'agent' | 'browser'
  confidence: 'high' | 'low'
} {
  const agentPlatform = agentPlatformToValidPlatform(agent?.platform ?? null)
  if (agentPlatform) {
    return { platform: agentPlatform, source: 'agent', confidence: 'high' }
  }
  const detected = detectPlatform()
  return {
    platform: detected.platform,
    source: 'browser',
    confidence: detected.confidence,
  }
}

// ============================================================================
// Step Indicator (inline 4-step variant)
// ============================================================================

function UpdateStepIndicator({ currentStep }: { currentStep: number }) {
  return (
    <nav aria-label="Update progress" className="flex items-center gap-1 overflow-x-auto py-2">
      {UPDATE_STEPS.map((step, index) => {
        const isActive = step.number === currentStep
        const isCompleted = step.number < currentStep

        return (
          <div key={step.number} className="flex items-center">
            {index > 0 && (
              <div
                className={cn(
                  'h-px w-4 sm:w-6 flex-shrink-0',
                  isCompleted ? 'bg-primary' : 'bg-border'
                )}
              />
            )}
            <div
              className="flex items-center gap-1.5 flex-shrink-0"
              aria-current={isActive ? 'step' : undefined}
            >
              <div
                className={cn(
                  'flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium',
                  isActive && 'bg-primary text-primary-foreground',
                  isCompleted && 'bg-primary/20 text-primary',
                  !isActive && !isCompleted && 'bg-muted text-muted-foreground'
                )}
              >
                {isCompleted ? <Check className="h-3 w-3" /> : step.number}
              </div>
              <span
                className={cn(
                  'text-xs hidden sm:inline whitespace-nowrap',
                  isActive && 'font-medium text-foreground',
                  !isActive && 'text-muted-foreground'
                )}
              >
                {step.title}
              </span>
            </div>
          </div>
        )
      })}
    </nav>
  )
}

// ============================================================================
// Step 1: Download
// ============================================================================

interface UpdateDownloadStepProps {
  agent: Agent
  activeRelease: ActiveReleaseResponse | null
  loading: boolean
  error: string | null
  selectedPlatform: ValidPlatform
  onPlatformChange: (platform: ValidPlatform) => void
  platformSource: 'agent' | 'browser'
  platformConfidence: 'high' | 'low'
  nearExpiry: boolean
  fetchRelease: () => void
}

function UpdateDownloadStep({
  agent,
  activeRelease,
  loading,
  error,
  selectedPlatform,
  onPlatformChange,
  platformSource,
  platformConfidence,
  nearExpiry,
  fetchRelease,
}: UpdateDownloadStepProps) {
  const { copy, copied } = useClipboard()
  const [downloadError, setDownloadError] = useState<string | null>(null)
  const [isDownloading, setIsDownloading] = useState(false)

  const isDevMode = import.meta.env.DEV || (activeRelease?.dev_mode ?? false)
  const secure = isSecureContext()

  // Resolve the initial platform label for display
  const initialPlatform = useMemo(
    () => agentPlatformToValidPlatform(agent.platform ?? null),
    [agent.platform]
  )

  // Determine available platforms for the dropdown
  const availablePlatforms = useMemo(() => {
    if (isDevMode) return [...VALID_PLATFORMS]
    if (!activeRelease) return [...VALID_PLATFORMS]
    const artifactPlatforms = new Set(activeRelease.artifacts.map((a) => a.platform))
    // Always include the selected + initial platforms so dropdown is never empty
    artifactPlatforms.add(selectedPlatform)
    if (initialPlatform) artifactPlatforms.add(initialPlatform)
    return VALID_PLATFORMS.filter((p) => artifactPlatforms.has(p))
  }, [activeRelease, isDevMode, selectedPlatform, initialPlatform])

  const isOverridden = initialPlatform
    ? selectedPlatform !== initialPlatform
    : selectedPlatform !== resolveInitialPlatform(agent).platform

  const matchingArtifact = activeRelease?.artifacts.find(
    (a) => a.platform === selectedPlatform
  )

  const signedUrlExpiry = matchingArtifact?.signed_url
    ? parseSignedUrlExpiry(matchingArtifact.signed_url)
    : null
  const fullSignedUrl = matchingArtifact?.signed_url
    ? buildFullSignedUrl(matchingArtifact.signed_url)
    : null

  const handleDownload = useCallback((artifact: ReleaseArtifact) => {
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
  }, [])

  return (
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
          <span className="text-muted-foreground">Target:</span>{' '}
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

      {/* Platform source info */}
      <div className="space-y-2">
        <Label>
          {platformSource === 'agent' ? 'Agent Platform' : 'Detected Platform'}
        </Label>
        <p className="text-sm text-muted-foreground">
          {PLATFORM_LABELS[platformSource === 'agent' && initialPlatform
            ? initialPlatform
            : selectedPlatform]}
          {platformSource === 'agent' && (
            <span className="ml-2 text-xs">(reported by agent)</span>
          )}
          {platformSource === 'browser' && platformConfidence === 'low' && (
            <span className="text-amber-600 ml-2">(low confidence — please verify)</span>
          )}
        </p>
      </div>

      {/* Platform Override Selector */}
      <div className="space-y-2">
        <Label htmlFor="update-platform-select">Target Platform</Label>
        <Select
          value={selectedPlatform}
          onValueChange={(val) => onPlatformChange(val as ValidPlatform)}
        >
          <SelectTrigger id="update-platform-select" className="w-full sm:w-72">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {availablePlatforms.map((p) => (
              <SelectItem key={p} value={p}>
                {PLATFORM_LABELS[p]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {isOverridden && (
          <Alert>
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              You selected a different platform than {platformSource === 'agent' ? 'the agent\'s' : 'detected'}.
              Make sure this matches the machine where the agent is installed.
            </AlertDescription>
          </Alert>
        )}
      </div>

      {/* Loading state */}
      {loading && (
        <p className="text-sm text-muted-foreground">Loading release information...</p>
      )}

      {/* Fetch error */}
      {error && !loading && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Release info + download */}
      {activeRelease && !loading && (
        <div className="space-y-4">
          {/* HTTPS warning */}
          {!secure && matchingArtifact?.download_url && (
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                This page is not served over HTTPS. The download may not be secure.
                Consider using the signed URL on a secure connection.
              </AlertDescription>
            </Alert>
          )}

          {/* Dev/QA mode banner */}
          {isDevMode && (
            <Alert className="border-blue-200 bg-blue-50 dark:border-blue-900 dark:bg-blue-950">
              <Info className="h-4 w-4 text-blue-600" />
              <AlertDescription className="text-blue-800 dark:text-blue-200">
                Development/QA mode — all platforms are shown. Downloads may not be available.
              </AlertDescription>
            </Alert>
          )}

          {matchingArtifact ? (
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
                    {matchingArtifact.file_size != null && (
                      <span className="text-muted-foreground">
                        ({formatFileSize(matchingArtifact.file_size)})
                      </span>
                    )}
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
                <div className={`space-y-3 border-t pt-4 ${isOverridden ? 'rounded-md border border-blue-200 bg-blue-50/30 p-4 dark:border-blue-900 dark:bg-blue-950/30' : ''}`}>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <Label>Remote Download Link</Label>
                      {signedUrlExpiry && (
                        <span className="text-xs text-muted-foreground">
                          — valid until {signedUrlExpiry.toLocaleTimeString()}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {isOverridden
                        ? 'Since you selected a different platform, use this link to download the binary directly on the agent machine.'
                        : 'Use this link to download the updated binary directly on the agent machine.'}
                    </p>
                  </div>

                  {/* Near-expiry warning */}
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
          ) : isDevMode ? (
            <div className="space-y-2">
              <Button variant="outline" className="gap-2" disabled>
                <Download className="h-4 w-4" />
                Download Agent — {PLATFORM_LABELS[selectedPlatform]}
              </Button>
              <p className="text-sm text-muted-foreground">
                Agent binary for {PLATFORM_LABELS[selectedPlatform]} is not available in this environment.
                This is expected in development/QA — the wizard flow can still be tested without downloading.
              </p>
            </div>
          ) : (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                No build available for {PLATFORM_LABELS[selectedPlatform]}. Contact your
                administrator to upload the binary for this platform.
              </AlertDescription>
            </Alert>
          )}
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Step 2: Stop Agent
// ============================================================================

function StopAgentStep({ family }: { family: PlatformFamily }) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Stop the currently running agent before replacing the binary.
      </p>

      <Tabs defaultValue="service">
        <TabsList>
          <TabsTrigger value="service">Background Service</TabsTrigger>
          <TabsTrigger value="manual">Manual</TabsTrigger>
        </TabsList>

        <TabsContent value="service" className="space-y-3 mt-3">
          {family === 'macos' && (
            <>
              <p className="text-sm font-medium">macOS (LaunchDaemon)</p>
              <CopyableCodeBlock label="stop launchd service" language="bash" alwaysShowCopy>
                {`sudo launchctl unload /Library/LaunchDaemons/ai.shuttersense.agent.plist`}
              </CopyableCodeBlock>
              <p className="text-xs text-muted-foreground">
                If you installed the agent as a user-level LaunchAgent instead:
              </p>
              <CopyableCodeBlock label="stop launchd user agent" language="bash" alwaysShowCopy>
                {`launchctl unload ~/Library/LaunchAgents/ai.shuttersense.agent.plist`}
              </CopyableCodeBlock>
            </>
          )}
          {family === 'linux' && (
            <>
              <p className="text-sm font-medium">Linux (systemd)</p>
              <CopyableCodeBlock label="stop systemd service" language="bash" alwaysShowCopy>
                {`sudo systemctl stop shuttersense-agent`}
              </CopyableCodeBlock>
            </>
          )}
          {family === 'windows' && (
            <>
              <p className="text-sm font-medium">Windows (Task Scheduler)</p>
              <p className="text-sm text-muted-foreground">
                Open <span className="font-medium">Task Scheduler</span>, find{' '}
                <span className="font-mono text-xs">&quot;ShutterSense Agent&quot;</span>, right-click and
                select <span className="font-medium">End</span>.
              </p>
            </>
          )}
          {family === 'generic' && (
            <p className="text-sm text-muted-foreground">
              Stop the agent background service using your platform&apos;s service manager.
            </p>
          )}
        </TabsContent>

        <TabsContent value="manual" className="space-y-3 mt-3">
          <p className="text-sm text-muted-foreground">
            If you started the agent manually in a terminal, press{' '}
            <kbd className="rounded border bg-muted px-1.5 py-0.5 text-xs font-mono">Ctrl+C</kbd>{' '}
            in that terminal to stop it.
          </p>
          {family !== 'windows' && (
            <>
              <p className="text-xs text-muted-foreground">
                Or find and kill the process:
              </p>
              <CopyableCodeBlock label="kill agent process" language="bash" alwaysShowCopy>
                {`pkill -f shuttersense-agent`}
              </CopyableCodeBlock>
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}

// ============================================================================
// Step 3: Replace Binary
// ============================================================================

function ReplaceBinaryStep({
  family,
  filename,
}: {
  family: PlatformFamily
  filename: string
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Replace the existing agent binary with the downloaded version.
      </p>

      {(family === 'macos' || family === 'linux' || family === 'generic') && (
        <div className="space-y-3">
          <CopyableCodeBlock label="replace binary" language="bash" alwaysShowCopy>
            {`chmod +x ~/${filename}\nsudo mv ~/${filename} /usr/local/bin/shuttersense-agent`}
          </CopyableCodeBlock>
          <p className="text-xs text-muted-foreground">
            Adjust the paths if you downloaded the binary to a different location or
            installed the agent elsewhere.
          </p>
        </div>
      )}

      {family === 'windows' && (
        <div className="space-y-3">
          <CopyableCodeBlock label="replace binary" language="powershell" alwaysShowCopy>
            {`Move-Item -Force ~\\Downloads\\${filename} "C:\\Program Files\\ShutterSense\\shuttersense-agent.exe"`}
          </CopyableCodeBlock>
          <p className="text-xs text-muted-foreground">
            Adjust the paths if you downloaded the binary to a different location or
            installed the agent elsewhere.
          </p>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Step 4: Start Agent
// ============================================================================

function StartAgentStep({ family }: { family: PlatformFamily }) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Start the updated agent and verify it connects to the server.
      </p>

      <Tabs defaultValue="service">
        <TabsList>
          <TabsTrigger value="service">Background Service</TabsTrigger>
          <TabsTrigger value="manual">Manual</TabsTrigger>
        </TabsList>

        <TabsContent value="service" className="space-y-3 mt-3">
          {family === 'macos' && (
            <>
              <p className="text-sm font-medium">macOS (LaunchDaemon)</p>
              <CopyableCodeBlock label="start launchd service" language="bash" alwaysShowCopy>
                {`sudo launchctl load /Library/LaunchDaemons/ai.shuttersense.agent.plist`}
              </CopyableCodeBlock>
              <p className="text-xs text-muted-foreground">
                If you use a user-level LaunchAgent instead:
              </p>
              <CopyableCodeBlock label="start launchd user agent" language="bash" alwaysShowCopy>
                {`launchctl load ~/Library/LaunchAgents/ai.shuttersense.agent.plist`}
              </CopyableCodeBlock>
            </>
          )}
          {family === 'linux' && (
            <>
              <p className="text-sm font-medium">Linux (systemd)</p>
              <CopyableCodeBlock label="start systemd service" language="bash" alwaysShowCopy>
                {`sudo systemctl start shuttersense-agent`}
              </CopyableCodeBlock>
            </>
          )}
          {family === 'windows' && (
            <>
              <p className="text-sm font-medium">Windows (Task Scheduler)</p>
              <p className="text-sm text-muted-foreground">
                Open <span className="font-medium">Task Scheduler</span>, find{' '}
                <span className="font-mono text-xs">&quot;ShutterSense Agent&quot;</span>, right-click and
                select <span className="font-medium">Run</span>.
              </p>
            </>
          )}
          {family === 'generic' && (
            <p className="text-sm text-muted-foreground">
              Restart the agent background service using your platform&apos;s service manager.
            </p>
          )}
        </TabsContent>

        <TabsContent value="manual" className="space-y-3 mt-3">
          {family === 'windows' ? (
            <CopyableCodeBlock label="start agent" language="powershell" alwaysShowCopy>
              {`& "C:\\Program Files\\ShutterSense\\shuttersense-agent.exe" start`}
            </CopyableCodeBlock>
          ) : (
            <CopyableCodeBlock label="start agent" language="bash" alwaysShowCopy>
              {`/usr/local/bin/shuttersense-agent start`}
            </CopyableCodeBlock>
          )}
          <p className="text-xs text-muted-foreground">
            Keep the terminal open while the agent is running. Use{' '}
            <kbd className="rounded border bg-muted px-1.5 py-0.5 text-xs font-mono">Ctrl+C</kbd>{' '}
            to stop it later.
          </p>
        </TabsContent>
      </Tabs>

      {/* Verification */}
      <div className="space-y-2 border-t pt-4">
        <p className="text-sm font-medium">Verify the update</p>
        <p className="text-xs text-muted-foreground">
          Run the self-test command to confirm the agent connects and reports the new version:
        </p>
        {family === 'windows' ? (
          <CopyableCodeBlock label="self-test command" language="powershell" alwaysShowCopy>
            {`& "C:\\Program Files\\ShutterSense\\shuttersense-agent.exe" self-test`}
          </CopyableCodeBlock>
        ) : (
          <CopyableCodeBlock label="self-test command" language="bash" alwaysShowCopy>
            {`/usr/local/bin/shuttersense-agent self-test`}
          </CopyableCodeBlock>
        )}
      </div>
    </div>
  )
}

// ============================================================================
// Main Dialog Component
// ============================================================================

export function AgentUpdateDialog({
  agent,
  open,
  onOpenChange,
}: AgentUpdateDialogProps) {
  const [currentStep, setCurrentStep] = useState(1)
  const [activeRelease, setActiveRelease] = useState<ActiveReleaseResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [nearExpiry, setNearExpiry] = useState(false)
  const fetchedAtRef = useRef<number>(0)

  // Platform state: resolved once on open, user can override via dropdown
  const [initialPlatformInfo, setInitialPlatformInfo] = useState<ReturnType<typeof resolveInitialPlatform>>(() =>
    resolveInitialPlatform(agent)
  )
  const [selectedPlatform, setSelectedPlatform] = useState<ValidPlatform>(
    initialPlatformInfo.platform
  )

  // Derive platform family from selectedPlatform (used by steps 2-4)
  const platformFamily = useMemo(
    () => getPlatformFamily(selectedPlatform),
    [selectedPlatform]
  )

  // Find artifact for selected platform
  const matchingArtifact = useMemo(
    () => activeRelease?.artifacts.find((a) => a.platform === selectedPlatform),
    [activeRelease, selectedPlatform]
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

  // Reset state when dialog opens
  useEffect(() => {
    if (open) {
      const info = resolveInitialPlatform(agent)
      setInitialPlatformInfo(info)
      setSelectedPlatform(info.platform)
      setCurrentStep(1)
      fetchRelease()
    }
  }, [open, agent, fetchRelease])

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

  if (!agent) return null

  const isFirstStep = currentStep === 1
  const isLastStep = currentStep === UPDATE_STEPS.length
  const canProceed = currentStep === 1 ? !loading && !error : true
  const filename = matchingArtifact?.filename ?? 'shuttersense-agent'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col p-4 sm:p-6">
        <DialogHeader>
          <DialogTitle>Update Agent</DialogTitle>
          <DialogDescription>
            Update &quot;{agent.name}&quot; to the latest version.
          </DialogDescription>
        </DialogHeader>

        <UpdateStepIndicator currentStep={currentStep} />

        {/* Scrollable step content */}
        <div className="flex-1 overflow-y-auto min-h-0 pr-1">
          {currentStep === 1 && (
            <UpdateDownloadStep
              agent={agent}
              activeRelease={activeRelease}
              loading={loading}
              error={error}
              selectedPlatform={selectedPlatform}
              onPlatformChange={setSelectedPlatform}
              platformSource={initialPlatformInfo.source}
              platformConfidence={initialPlatformInfo.confidence}
              nearExpiry={nearExpiry}
              fetchRelease={fetchRelease}
            />
          )}
          {currentStep === 2 && <StopAgentStep family={platformFamily} />}
          {currentStep === 3 && (
            <ReplaceBinaryStep family={platformFamily} filename={filename} />
          )}
          {currentStep === 4 && <StartAgentStep family={platformFamily} />}
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between border-t pt-4">
          <Button
            variant="outline"
            size="sm"
            className="gap-1"
            onClick={() => setCurrentStep((s) => s - 1)}
            disabled={isFirstStep}
          >
            <ChevronLeft className="h-4 w-4" />
            Back
          </Button>

          {isLastStep ? (
            <Button size="sm" onClick={() => onOpenChange(false)}>
              Done
            </Button>
          ) : (
            <Button
              size="sm"
              className="gap-1"
              onClick={() => setCurrentStep((s) => s + 1)}
              disabled={!canProceed}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

export default AgentUpdateDialog
