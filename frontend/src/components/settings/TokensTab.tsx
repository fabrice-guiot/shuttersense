/**
 * Tokens Tab Component
 *
 * Manage API tokens with create, list, and revoke operations.
 * Phase 10: User Story 7 - API Token Authentication
 */

import { useState, useEffect } from 'react'
import { Plus, Key, Trash2, Copy, Check, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useTokens, useTokenStats } from '@/hooks/useTokens'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { formatRelativeTime } from '@/utils/dateFormat'
import type { ApiToken, ApiTokenCreated, CreateTokenRequest } from '@/contracts/api/tokens-api'

// ============================================================================
// Create Token Dialog
// ============================================================================

interface CreateTokenDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: CreateTokenRequest) => Promise<ApiTokenCreated>
}

function CreateTokenDialog({ open, onOpenChange, onSubmit }: CreateTokenDialogProps) {
  const [name, setName] = useState('')
  const [expiresInDays, setExpiresInDays] = useState('90')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [createdToken, setCreatedToken] = useState<ApiTokenCreated | null>(null)
  const [copied, setCopied] = useState(false)

  const handleClose = () => {
    setName('')
    setExpiresInDays('90')
    setError(null)
    setCreatedToken(null)
    setCopied(false)
    onOpenChange(false)
  }

  const handleCreate = async () => {
    if (!name.trim()) {
      setError('Name is required')
      return
    }

    const days = parseInt(expiresInDays, 10)
    if (isNaN(days) || days < 1 || days > 365) {
      setError('Expiration must be between 1 and 365 days')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const token = await onSubmit({
        name: name.trim(),
        expires_in_days: days
      })
      setCreatedToken(token)
    } catch (err: any) {
      setError(err.userMessage || 'Failed to create token')
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = async () => {
    if (createdToken) {
      await navigator.clipboard.writeText(createdToken.token)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            {createdToken ? 'Token Created' : 'Create API Token'}
          </DialogTitle>
          <DialogDescription>
            {createdToken
              ? 'Copy your token now. It will not be shown again.'
              : 'Create a new API token for programmatic access.'}
          </DialogDescription>
        </DialogHeader>

        {createdToken ? (
          // Show created token
          <div className="space-y-4 py-4">
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Make sure to copy your token now. You will not be able to see it again!
              </AlertDescription>
            </Alert>

            <div className="space-y-2">
              <Label>Your API Token</Label>
              <div className="flex gap-2">
                <Input
                  value={createdToken.token}
                  readOnly
                  className="font-mono text-sm"
                />
                <Button variant="outline" size="icon" onClick={handleCopy}>
                  {copied ? (
                    <Check className="h-4 w-4 text-green-500" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
              </div>
              <p className="text-sm text-muted-foreground">
                Token prefix: <code className="bg-muted px-1 rounded">{createdToken.token_prefix}</code>
              </p>
            </div>

            <DialogFooter>
              <Button onClick={handleClose}>Done</Button>
            </DialogFooter>
          </div>
        ) : (
          // Create form
          <div className="space-y-4 py-4">
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="token-name">Name</Label>
              <Input
                id="token-name"
                placeholder="e.g., CI/CD Pipeline"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <p className="text-sm text-muted-foreground">
                A descriptive name to identify this token
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="expires-in">Expires In (days)</Label>
              <Input
                id="expires-in"
                type="number"
                min={1}
                max={365}
                value={expiresInDays}
                onChange={(e) => setExpiresInDays(e.target.value)}
              />
              <p className="text-sm text-muted-foreground">
                Token will expire after this many days (1-365)
              </p>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={handleClose} disabled={loading}>
                Cancel
              </Button>
              <Button onClick={handleCreate} disabled={loading}>
                {loading ? 'Creating...' : 'Create Token'}
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

// ============================================================================
// Token List Component
// ============================================================================

interface TokenListProps {
  tokens: ApiToken[]
  loading: boolean
  onRevoke: (token: ApiToken) => void
}

function TokenList({ tokens, loading, onRevoke }: TokenListProps) {
  const [revokeDialog, setRevokeDialog] = useState<{
    open: boolean
    token: ApiToken | null
  }>({ open: false, token: null })

  const handleRevokeClick = (token: ApiToken) => {
    setRevokeDialog({ open: true, token })
  }

  const handleRevokeConfirm = () => {
    if (revokeDialog.token) {
      onRevoke(revokeDialog.token)
      setRevokeDialog({ open: false, token: null })
    }
  }

  if (loading && tokens.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-muted-foreground">Loading tokens...</div>
      </div>
    )
  }

  if (tokens.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Key className="h-12 w-12 text-muted-foreground mb-4" />
        <div className="text-muted-foreground mb-2">No API tokens</div>
        <p className="text-sm text-muted-foreground">
          Create an API token to access the API programmatically
        </p>
      </div>
    )
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Token</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Created</TableHead>
            <TableHead>Expires</TableHead>
            <TableHead>Last Used</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {tokens.map((token) => (
            <TableRow key={token.guid}>
              <TableCell className="font-medium">{token.name}</TableCell>
              <TableCell>
                <code className="bg-muted px-2 py-1 rounded text-sm">
                  {token.token_prefix}...
                </code>
              </TableCell>
              <TableCell>
                <Badge variant={token.is_active ? 'default' : 'secondary'}>
                  {token.is_active ? 'Active' : 'Revoked'}
                </Badge>
              </TableCell>
              <TableCell className="text-muted-foreground">
                <div>{formatRelativeTime(token.created_at)}</div>
                {token.created_by_email && (
                  <div className="text-xs">by {token.created_by_email}</div>
                )}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {formatRelativeTime(token.expires_at)}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {token.last_used_at
                  ? formatRelativeTime(token.last_used_at)
                  : 'Never'}
              </TableCell>
              <TableCell className="text-right">
                {token.is_active && (
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleRevokeClick(token)}
                    title="Revoke token"
                    className="text-destructive hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {/* Revoke Confirmation Dialog */}
      <Dialog
        open={revokeDialog.open}
        onOpenChange={(open) => {
          if (!open) setRevokeDialog({ open: false, token: null })
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Revoke API Token</DialogTitle>
            <DialogDescription>
              Are you sure you want to revoke the token "{revokeDialog.token?.name}"?
              This will immediately invalidate the token and cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setRevokeDialog({ open: false, token: null })}
            >
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleRevokeConfirm}>
              Revoke Token
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

// ============================================================================
// Main Component
// ============================================================================

export function TokensTab() {
  const { tokens, loading, error, createToken, revokeToken } = useTokens()
  const { stats, refetch: refetchStats } = useTokenStats()
  const { setStats } = useHeaderStats()
  const [createDialogOpen, setCreateDialogOpen] = useState(false)

  // Update header stats when data changes
  useEffect(() => {
    if (stats) {
      setStats([
        { label: 'Active Tokens', value: stats.active_count },
        { label: 'Total Tokens', value: stats.total_count },
      ])
    }
    return () => setStats([]) // Clear stats on unmount
  }, [stats, setStats])

  const handleRevoke = (token: ApiToken) => {
    revokeToken(token.guid).then(() => refetchStats())
  }

  const handleCreate = async (data: CreateTokenRequest) => {
    const result = await createToken(data)
    refetchStats()
    return result
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Action Row */}
      <div className="flex justify-end">
        <Button onClick={() => setCreateDialogOpen(true)} className="gap-2">
          <Plus className="h-4 w-4" />
          New Token
        </Button>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Token List */}
      <TokenList
        tokens={tokens}
        loading={loading}
        onRevoke={handleRevoke}
      />

      {/* Create Token Dialog */}
      <CreateTokenDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onSubmit={handleCreate}
      />
    </div>
  )
}

export default TokensTab
