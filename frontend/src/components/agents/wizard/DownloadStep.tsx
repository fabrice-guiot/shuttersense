/**
 * DownloadStep — Step 1: OS Detection & Binary Download.
 *
 * Phase 3 (placeholder): Detects platform, shows platform override dropdown,
 * fetches active release. Full download/signed URL logic added in Phase 4 (US2).
 *
 * Issue #136 - Agent Setup Wizard (FR-004 through FR-008)
 */

import { useEffect, useState } from 'react'
import { Download, AlertTriangle, Info } from 'lucide-react'
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
import { PLATFORM_LABELS, VALID_PLATFORMS, type ValidPlatform } from '@/contracts/api/release-manifests-api'
import type { ActiveReleaseResponse } from '@/contracts/api/agent-api'
import { getActiveRelease } from '@/services/agents'

interface DownloadStepProps {
  detectedPlatform: ValidPlatform
  selectedPlatform: ValidPlatform
  onPlatformChange: (platform: ValidPlatform) => void
  platformConfidence: string
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

  const isOverridden = selectedPlatform !== detectedPlatform

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    getActiveRelease()
      .then((release) => {
        if (!cancelled) setActiveRelease(release)
      })
      .catch(() => {
        if (!cancelled) setError('No release available. Contact your administrator for the agent binary.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => { cancelled = true }
  }, [])

  const matchingArtifact = activeRelease?.artifacts.find(
    (a) => a.platform === selectedPlatform
  )

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
            {VALID_PLATFORMS.map((p) => (
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

      {/* Release Info */}
      {loading && (
        <p className="text-sm text-muted-foreground">Loading release information...</p>
      )}

      {error && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {activeRelease && !loading && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Version <span className="font-medium text-foreground">{activeRelease.version}</span>
          </p>
          {matchingArtifact ? (
            <div className="space-y-2">
              <Button disabled variant="outline" className="gap-2">
                <Download className="h-4 w-4" />
                {matchingArtifact.filename}
                {matchingArtifact.file_size && (
                  <span className="text-muted-foreground">
                    ({(matchingArtifact.file_size / 1024 / 1024).toFixed(1)} MB)
                  </span>
                )}
              </Button>
              <p className="text-xs text-muted-foreground font-mono break-all">
                Checksum: {matchingArtifact.checksum}
              </p>
            </div>
          ) : (
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
