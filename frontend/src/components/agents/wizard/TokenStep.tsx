/**
 * TokenStep — Step 2: Registration Token Creation.
 *
 * Reuses the existing createToken API. Shows creation form on first visit,
 * read-only token display on subsequent visits (prevents duplicate creation).
 *
 * Issue #136 - Agent Setup Wizard (FR-010 through FR-013)
 */

import { useState } from 'react'
import { AlertTriangle, Loader2, Key } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { CopyableCodeBlock } from '@/components/agents/wizard/CopyableCodeBlock'
import type { RegistrationToken } from '@/contracts/api/agent-api'

interface TokenStepProps {
  createdToken: RegistrationToken | null
  onTokenCreated: (token: RegistrationToken) => void
  createToken: (data?: { name?: string; expires_in_hours?: number }) => Promise<RegistrationToken>
}

export function TokenStep({ createdToken, onTokenCreated, createToken }: TokenStepProps) {
  const [tokenName, setTokenName] = useState('')
  const [expiresInHours, setExpiresInHours] = useState(24)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // If token already created, show read-only display
  if (createdToken) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Key className="h-4 w-4" />
          <span>Registration token created{createdToken.name ? ` — ${createdToken.name}` : ''}</span>
        </div>

        <CopyableCodeBlock label="registration token" alwaysShowCopy>
          {createdToken.token}
        </CopyableCodeBlock>

        <Alert className="border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950">
          <AlertTriangle className="h-4 w-4 text-amber-600" />
          <AlertDescription className="text-amber-800 dark:text-amber-200">
            This token will only be shown once. Copy it now.
          </AlertDescription>
        </Alert>

        <p className="text-xs text-muted-foreground">
          Expires: {new Date(createdToken.expires_at).toLocaleString()}
        </p>
      </div>
    )
  }

  const handleCreate = async () => {
    setCreating(true)
    setError(null)
    try {
      const token = await createToken({
        name: tokenName.trim() || undefined,
        expires_in_hours: expiresInHours,
      })
      onTokenCreated(token)
    } catch (err: any) {
      setError(err.userMessage || 'Failed to create registration token')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Create a one-time registration token for the agent. This token will be used in the next step to register the agent with the server.
      </p>

      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="token-name">Token Name (optional)</Label>
          <Input
            id="token-name"
            placeholder="e.g., Studio Mac Agent"
            value={tokenName}
            onChange={(e) => setTokenName(e.target.value)}
            disabled={creating}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="token-expiry">Expiration (hours)</Label>
          <Input
            id="token-expiry"
            type="number"
            min={1}
            max={168}
            value={expiresInHours}
            onChange={(e) => setExpiresInHours(Math.min(168, Math.max(1, parseInt(e.target.value) || 24)))}
            disabled={creating}
            className="w-32"
          />
          <p className="text-xs text-muted-foreground">
            Between 1 and 168 hours (7 days). Default: 24 hours.
          </p>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Button onClick={handleCreate} disabled={creating}>
        {creating && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
        Create Registration Token
      </Button>
    </div>
  )
}
