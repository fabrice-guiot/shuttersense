/**
 * DownloadStep — Step 1: OS Detection & Binary Download.
 *
 * Phase 4 (US2): Full download experience with session-authenticated download,
 * signed URL for remote use, checksum display, dev/QA mode, and graceful
 * degradation for all error cases.
 *
 * Issue #136 - Agent Setup Wizard (FR-004, FR-007 through FR-009, FR-033 through FR-040)
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AlertTriangle, Check, Copy, Download, Info, Loader2, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Label } from '@/components/ui/label'
import { CopyableCodeBlock } from '@/components/agents/wizard/CopyableCodeBlock'
import { useClipboard } from '@/hooks/useClipboard'
import { PLATFORM_LABELS, VALID_PLATFORMS, type ValidPlatform } from '@/contracts/api/release-manifests-api'
import type { ActiveReleaseResponse, ReleaseArtifact } from '@/contracts/api/agent-api'
import { getActiveRelease } from '@/services/agents'

interface DownloadStepProps {
  detectedPlatform: ValidPlatform
  selectedPlatform: ValidPlatform
  onPlatformChange: (platform: ValidPlatform) => void
  platformConfidence: string
}

/** Check whether the current page is served securely (HTTPS or localhost). */
function isSecureContext(): boolean {
  const { protocol, hostname } = window.location
  if (protocol === 'https:') return true
  if (hostname === 'localhost' || hostname === '127.0.0.1') return true
  return false
}

/** Format bytes into a human-readable size string. */
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

/** Parse the `expires` query parameter (Unix timestamp) from a signed URL. */
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

/** Build the full absolute URL for a signed URL (for curl examples). */
function buildFullSignedUrl(signedUrl: string): string {
  const prefix = signedUrl.startsWith('/') ? '' : '/'
  return `${window.location.origin}${prefix}${signedUrl}`
}

export function DownloadStep({
  detectedPlatform,
  selectedPlatform,
  onPlatformChange,
  platformConfidence,
}: DownloadStepProps) {
  const [activeRelease, setActiveRelease] = useState<ActiveReleaseResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [downloadError, setDownloadError] = useState<string | null>(null)
  const [isDownloading, setIsDownloading] = useState(false)
  const [nearExpiry, setNearExpiry] = useState(false)
  const fetchedAtRef = useRef<number>(0)
  const { copy, copied } = useClipboard()

  const isOverridden = selectedPlatform !== detectedPlatform
  const isDevMode = import.meta.env.DEV || (activeRelease?.dev_mode ?? false)
  const secure = isSecureContext()

  // Determine available platforms for the dropdown (T033)
  const availablePlatforms = useMemo(() => {
    if (isDevMode) return [...VALID_PLATFORMS]
    if (!activeRelease) return [...VALID_PLATFORMS]
    const artifactPlatforms = new Set(activeRelease.artifacts.map((a) => a.platform))
    // Always include detected + selected platforms so the dropdown is never empty
    artifactPlatforms.add(detectedPlatform)
    artifactPlatforms.add(selectedPlatform)
    return VALID_PLATFORMS.filter((p) => artifactPlatforms.has(p))
  }, [activeRelease, isDevMode, detectedPlatform, selectedPlatform])

  const matchingArtifact = activeRelease?.artifacts.find(
    (a) => a.platform === selectedPlatform
  )

  // Fetch active release
  const fetchRelease = useCallback(() => {
    setLoading(true)
    setError(null)
    setNearExpiry(false)
    fetchedAtRef.current = Date.now()

    getActiveRelease()
      .then((release) => {
        setActiveRelease(release)
      })
      .catch(() => {
        setError('No release available. Contact your administrator for the agent binary.')
      })
      .finally(() => {
        setLoading(false)
      })
  }, [])

  useEffect(() => {
    fetchRelease()
  }, [fetchRelease])

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

  // Trigger in-browser download via hidden <a> element (T034)
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
      // Browser handles the download asynchronously
      setTimeout(() => setIsDownloading(false), 2000)
    } catch {
      setDownloadError('Failed to start download. Try the signed URL below to download manually.')
      setIsDownloading(false)
    }
  }, [])

  const signedUrlExpiry = matchingArtifact?.signed_url
    ? parseSignedUrlExpiry(matchingArtifact.signed_url)
    : null
  const fullSignedUrl = matchingArtifact?.signed_url
    ? buildFullSignedUrl(matchingArtifact.signed_url)
    : null

  return (
    <div className="space-y-6">
      {/* Detected Platform */}
      <div className="space-y-2">
        <Label>Detected Platform</Label>
        <p className="text-sm text-muted-foreground">
          {PLATFORM_LABELS[detectedPlatform]}
          {platformConfidence === 'low' && (
            <span className="text-amber-600 ml-2">(low confidence — please verify)</span>
          )}
        </p>
      </div>

      {/* Platform Override */}
      <div className="space-y-2">
        <Label htmlFor="platform-select">Target Platform</Label>
        <Select
          value={selectedPlatform}
          onValueChange={(val) => onPlatformChange(val as ValidPlatform)}
        >
          <SelectTrigger id="platform-select" className="w-full sm:w-72">
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
              You selected a different platform than detected. Make sure this matches the machine where you will install the agent.
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
          <p className="text-sm text-muted-foreground">
            Version <span className="font-medium text-foreground">{activeRelease.version}</span>
          </p>

          {/* HTTPS warning (T031) */}
          {!secure && matchingArtifact?.download_url && (
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                This page is not served over HTTPS. The download may not be secure. Consider accessing this page over HTTPS or using the signed URL on a secure connection.
              </AlertDescription>
            </Alert>
          )}

          {/* Dev/QA mode banner (T033) */}
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
              {/* Download button (T031, T034) */}
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

                {/* Download error with retry (T031 - FR-009) */}
                {downloadError && (
                  <Alert variant="destructive">
                    <AlertDescription className="flex items-center gap-2">
                      <span>{downloadError}</span>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDownload(matchingArtifact)}
                      >
                        Retry Download
                      </Button>
                    </AlertDescription>
                  </Alert>
                )}
              </div>

              {/* Checksum (T031) */}
              <p className="text-xs text-muted-foreground font-mono break-all">
                Checksum: {matchingArtifact.checksum}
              </p>

              {/* Signed URL section (T032) */}
              {matchingArtifact.signed_url && fullSignedUrl && (
                <div className="space-y-3 border-t pt-4">
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
                      Use this link to download the agent on a remote or headless machine.
                    </p>
                  </div>

                  {/* Near-expiry warning (T032) */}
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
                          Refresh Link
                        </Button>
                      </AlertDescription>
                    </Alert>
                  )}

                  {/* curl example */}
                  <CopyableCodeBlock label="curl download command" language="bash" alwaysShowCopy>
                    {`curl -fLo ${matchingArtifact.filename} "${fullSignedUrl}"`}
                  </CopyableCodeBlock>

                  {/* Copy link button */}
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
            /* Dev/QA mode — no artifact for this platform (T033 - FR-034) */
            <div className="space-y-2">
              <Button variant="outline" className="gap-2" disabled>
                <Download className="h-4 w-4" />
                Download Agent — {PLATFORM_LABELS[selectedPlatform]}
              </Button>
              <p className="text-sm text-muted-foreground">
                Agent binary for {PLATFORM_LABELS[selectedPlatform]} is not available in this environment. This is expected in development/QA — the wizard flow can still be tested without downloading.
              </p>
            </div>
          ) : (
            /* Production mode — no artifact for selected platform (FR-008) */
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                No build available for {PLATFORM_LABELS[selectedPlatform]}. You can still continue with the setup if you already have the agent binary.
              </AlertDescription>
            </Alert>
          )}
        </div>
      )}
    </div>
  )
}
