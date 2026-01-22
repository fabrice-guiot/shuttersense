/**
 * RegistrationTokenDialog Component
 *
 * Dialog for generating and displaying agent registration tokens.
 * The token is only shown once at creation time.
 *
 * Issue #90 - Distributed Agent Architecture (Phase 3)
 * Task: T049
 */

import { useState } from 'react'
import { Copy, Check, Key, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useClipboard } from '@/hooks/useClipboard'
import type { RegistrationToken, RegistrationTokenCreateRequest } from '@/contracts/api/agent-api'

interface RegistrationTokenDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreateToken: (data: RegistrationTokenCreateRequest) => Promise<RegistrationToken>
}

/**
 * RegistrationTokenDialog handles token creation with a two-step flow:
 * 1. Form to input optional token name and expiration
 * 2. Display the generated token with copy functionality
 */
export function RegistrationTokenDialog({
  open,
  onOpenChange,
  onCreateToken,
}: RegistrationTokenDialogProps) {
  const [step, setStep] = useState<'form' | 'token'>('form')
  const [name, setName] = useState('')
  const [expiresInHours, setExpiresInHours] = useState(24)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [createdToken, setCreatedToken] = useState<RegistrationToken | null>(null)

  const { copied, copy } = useClipboard()

  const handleCreate = async () => {
    setLoading(true)
    setError(null)
    try {
      const token = await onCreateToken({
        name: name.trim() || undefined,
        expires_in_hours: expiresInHours,
      })
      setCreatedToken(token)
      setStep('token')
    } catch (err: any) {
      setError(err.userMessage || 'Failed to create registration token')
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    // Reset state when dialog closes
    setStep('form')
    setName('')
    setExpiresInHours(24)
    setError(null)
    setCreatedToken(null)
    onOpenChange(false)
  }

  const handleCopy = () => {
    if (createdToken?.token) {
      copy(createdToken.token)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        {step === 'form' ? (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Key className="h-5 w-5" />
                Create Registration Token
              </DialogTitle>
              <DialogDescription>
                Generate a one-time token to register a new agent. The token can only be used once
                and will expire after the specified time.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="token-name">Token Name (optional)</Label>
                <Input
                  id="token-name"
                  placeholder="e.g., For Studio Mac"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  disabled={loading}
                />
                <p className="text-xs text-muted-foreground">
                  A descriptive name to help identify which machine this token is for.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="expires-hours">Expires In (hours)</Label>
                <Input
                  id="expires-hours"
                  type="number"
                  min={1}
                  max={168}
                  value={expiresInHours}
                  onChange={e => setExpiresInHours(parseInt(e.target.value) || 24)}
                  disabled={loading}
                />
                <p className="text-xs text-muted-foreground">
                  Token will expire after this many hours (max 168 hours / 1 week).
                </p>
              </div>

              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={handleClose} disabled={loading}>
                Cancel
              </Button>
              <Button onClick={handleCreate} disabled={loading}>
                {loading ? 'Creating...' : 'Create Token'}
              </Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Check className="h-5 w-5 text-green-500" />
                Token Created
              </DialogTitle>
              <DialogDescription>
                Copy this token now - it cannot be retrieved later.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <Alert className="border-amber-500/50 bg-amber-500/10">
                <AlertTriangle className="h-4 w-4 text-amber-500" />
                <AlertDescription className="text-amber-500">
                  This token will only be shown once. Make sure to copy it before closing this
                  dialog.
                </AlertDescription>
              </Alert>

              <div className="space-y-2">
                <Label>Registration Token</Label>
                <div className="flex gap-2">
                  <Input
                    value={createdToken?.token || ''}
                    readOnly
                    className="font-mono text-sm"
                  />
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={handleCopy}
                    title={copied ? 'Copied!' : 'Copy to clipboard'}
                  >
                    {copied ? (
                      <Check className="h-4 w-4 text-green-500" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>

              <div className="rounded-lg bg-muted p-4 text-sm space-y-2">
                <p className="font-medium">Next steps:</p>
                <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
                  <li>Copy the token above</li>
                  <li>On the target machine, run the agent CLI</li>
                  <li>
                    Use the register command:
                    <pre className="mt-1 p-2 bg-background rounded text-xs overflow-x-auto">
                      shuttersense-agent register --token &lt;TOKEN&gt;
                    </pre>
                  </li>
                </ol>
              </div>
            </div>

            <DialogFooter>
              <Button onClick={handleClose}>Done</Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

export default RegistrationTokenDialog
