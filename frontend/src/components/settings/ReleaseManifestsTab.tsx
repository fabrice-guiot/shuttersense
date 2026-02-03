/**
 * Release Manifests Tab Component (Super Admin Only)
 *
 * Manage release manifests for agent binary attestation.
 * Only visible to super admin users.
 *
 * Part of Issue #90 - Distributed Agent Architecture
 */

import { useState, useEffect } from 'react'
import {
  Plus,
  Package,
  Pencil,
  Trash2,
  Copy,
  Check,
  Power,
  PowerOff,
  FileDown,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { ResponsiveTable, type ColumnDef } from '@/components/ui/responsive-table'
import { Badge } from '@/components/ui/badge'
import {
  useReleaseManifests,
  useReleaseManifestStats,
} from '@/hooks/useReleaseManifests'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { GuidBadge } from '@/components/GuidBadge'
import { AuditTrailPopover } from '@/components/audit'
import type {
  ReleaseManifest,
  ReleaseManifestCreateRequest,
  ValidPlatform,
} from '@/contracts/api/release-manifests-api'
import {
  VALID_PLATFORMS,
  PLATFORM_LABELS,
} from '@/contracts/api/release-manifests-api'

/**
 * Truncate a checksum for display (first 8 + last 4 chars).
 */
function truncateChecksum(checksum: string): string {
  if (checksum.length <= 16) return checksum
  return `${checksum.slice(0, 8)}...${checksum.slice(-4)}`
}

export function ReleaseManifestsTab() {
  const {
    manifests,
    loading,
    error,
    createManifest,
    updateManifest,
    deleteManifest,
  } = useReleaseManifests()

  // KPI Stats for header
  const { stats, refetch: refetchStats } = useReleaseManifestStats()
  const { setStats } = useHeaderStats()

  // Update header stats when data changes
  useEffect(() => {
    if (stats) {
      setStats([
        { label: 'Active', value: stats.active_count },
        { label: 'Total', value: stats.total_count },
      ])
    }
    return () => setStats([]) // Clear stats on unmount
  }, [stats, setStats])

  // Clipboard state for checksum copy
  const [copiedGuid, setCopiedGuid] = useState<string | null>(null)

  // Create dialog state
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Create form state
  const [newVersion, setNewVersion] = useState('')
  const [newPlatform, setNewPlatform] = useState<ValidPlatform | ''>('')
  const [newChecksum, setNewChecksum] = useState('')
  const [newNotes, setNewNotes] = useState('')
  const [newIsActive, setNewIsActive] = useState(true)
  const [newFilename, setNewFilename] = useState('')

  // Edit dialog state
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [editingManifest, setEditingManifest] = useState<ReleaseManifest | null>(
    null
  )
  const [editNotes, setEditNotes] = useState('')

  // Delete dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deletingManifest, setDeletingManifest] =
    useState<ReleaseManifest | null>(null)

  // Create dialog handlers
  const handleOpenCreateDialog = () => {
    setNewVersion('')
    setNewPlatform('')
    setNewChecksum('')
    setNewNotes('')
    setNewIsActive(true)
    setNewFilename('')
    setFormError(null)
    setCreateDialogOpen(true)
  }

  const handleCloseCreateDialog = () => {
    setCreateDialogOpen(false)
  }

  const handleCreateManifest = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    // Validate
    if (!newPlatform) {
      setFormError('Please select a platform')
      return
    }
    if (newChecksum.length !== 64) {
      setFormError('Checksum must be exactly 64 hexadecimal characters')
      return
    }
    if (!/^[0-9a-fA-F]{64}$/.test(newChecksum)) {
      setFormError('Checksum must contain only hexadecimal characters')
      return
    }
    if (!newFilename.trim()) {
      setFormError('Please enter the binary filename')
      return
    }

    setIsSubmitting(true)

    try {
      const data: ReleaseManifestCreateRequest = {
        version: newVersion.trim(),
        platforms: [newPlatform],
        checksum: newChecksum.toLowerCase(),
        is_active: newIsActive,
        artifacts: [{
          platform: newPlatform,
          filename: newFilename.trim(),
          checksum: `sha256:${newChecksum.toLowerCase()}`,
        }],
      }
      if (newNotes.trim()) {
        data.notes = newNotes.trim()
      }

      await createManifest(data)
      handleCloseCreateDialog()
      refetchStats()
    } catch (err: any) {
      setFormError(err.message || 'Failed to create release manifest')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Edit dialog handlers
  const handleOpenEditDialog = (manifest: ReleaseManifest) => {
    setEditingManifest(manifest)
    setEditNotes(manifest.notes || '')
    setFormError(null)
    setEditDialogOpen(true)
  }

  const handleCloseEditDialog = () => {
    setEditDialogOpen(false)
    setEditingManifest(null)
  }

  const handleToggleActive = async (manifest: ReleaseManifest) => {
    try {
      await updateManifest(manifest.guid, { is_active: !manifest.is_active })
      refetchStats()
    } catch (err) {
      // Error displayed via hook
    }
  }

  const handleUpdateNotes = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!editingManifest) return

    setFormError(null)
    setIsSubmitting(true)

    try {
      await updateManifest(editingManifest.guid, { notes: editNotes.trim() || undefined })
      handleCloseEditDialog()
      refetchStats()
    } catch (err: any) {
      setFormError(err.message || 'Failed to update release manifest')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Delete dialog handlers
  const handleOpenDeleteDialog = (manifest: ReleaseManifest) => {
    setDeletingManifest(manifest)
    setDeleteDialogOpen(true)
  }

  const handleConfirmDelete = async () => {
    if (!deletingManifest) return

    try {
      await deleteManifest(deletingManifest.guid)
      setDeleteDialogOpen(false)
      setDeletingManifest(null)
      refetchStats()
    } catch (err) {
      // Error displayed via hook
    }
  }

  // Copy checksum to clipboard
  const handleCopyChecksum = async (manifest: ReleaseManifest) => {
    try {
      await navigator.clipboard.writeText(manifest.checksum)
      setCopiedGuid(manifest.guid)
      setTimeout(() => setCopiedGuid(null), 2000)
    } catch (err) {
      console.error('Failed to copy checksum:', err)
    }
  }

  const manifestColumns: ColumnDef<ReleaseManifest>[] = [
    {
      header: 'Version',
      cell: (manifest) => (
        <div className="flex flex-col gap-1">
          <span className="font-medium">{manifest.version}</span>
          <GuidBadge guid={manifest.guid} />
        </div>
      ),
      cardRole: 'title',
    },
    {
      header: 'Platforms',
      cell: (manifest) => (
        <div className="flex flex-wrap gap-1">
          {manifest.platforms.map(platform => {
            const artifact = manifest.artifacts?.find(a => a.platform === platform)
            return (
              <Badge
                key={platform}
                variant="outline"
                className="text-xs"
                title={artifact ? `${artifact.filename} (${artifact.checksum})` : undefined}
              >
                {platform}
                {artifact && <FileDown className="h-3 w-3 ml-0.5" />}
              </Badge>
            )
          })}
        </div>
      ),
      cardRole: 'detail',
    },
    {
      header: 'Artifacts',
      cell: (manifest) => {
        const count = manifest.artifacts?.length ?? 0
        return count > 0 ? (
          <span className="text-sm">{count} {count === 1 ? 'file' : 'files'}</span>
        ) : (
          <span className="text-muted-foreground text-sm">—</span>
        )
      },
      cardRole: 'detail',
    },
    {
      header: 'Checksum',
      cell: (manifest) => (
        <div className="flex items-center gap-2">
          <code className="text-xs bg-muted px-1.5 py-0.5 rounded font-mono">
            {truncateChecksum(manifest.checksum)}
          </code>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => handleCopyChecksum(manifest)}
            title="Copy full checksum"
            aria-label="Copy full checksum"
          >
            {copiedGuid === manifest.guid ? (
              <Check className="h-3 w-3 text-success" />
            ) : (
              <Copy className="h-3 w-3" />
            )}
          </Button>
        </div>
      ),
      cardRole: 'detail',
    },
    {
      header: 'Status',
      cell: (manifest) => manifest.is_active ? (
        <Badge variant="success">
          Active
        </Badge>
      ) : (
        <Badge variant="muted">Inactive</Badge>
      ),
      cardRole: 'badge',
    },
    {
      header: 'Notes',
      cell: (manifest) => manifest.notes || (
        <span className="text-muted-foreground">—</span>
      ),
      cellClassName: 'max-w-[200px] truncate',
      cardRole: 'detail',
    },
    {
      header: 'Modified',
      cell: (manifest) => (
        <AuditTrailPopover audit={manifest.audit} fallbackTimestamp={manifest.updated_at} />
      ),
      cellClassName: 'text-muted-foreground',
      cardRole: 'hidden',
    },
    {
      header: 'Actions',
      headerClassName: 'text-right',
      cell: (manifest) => (
        <div className="flex justify-end gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => handleToggleActive(manifest)}
            title={manifest.is_active ? 'Deactivate' : 'Activate'}
            aria-label={manifest.is_active ? 'Deactivate manifest' : 'Activate manifest'}
            aria-pressed={manifest.is_active}
          >
            {manifest.is_active ? (
              <PowerOff className="h-4 w-4 text-destructive" />
            ) : (
              <Power className="h-4 w-4" />
            )}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => handleOpenEditDialog(manifest)}
            title="Edit notes"
            aria-label="Edit notes"
          >
            <Pencil className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-destructive hover:text-destructive"
            onClick={() => handleOpenDeleteDialog(manifest)}
            title="Delete"
            aria-label="Delete manifest"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ),
      cardRole: 'action',
    },
  ]

  return (
    <div className="flex flex-col gap-6">
      {/* Action Row */}
      <div className="flex justify-end">
        <Button onClick={handleOpenCreateDialog} className="gap-2">
          <Plus className="h-4 w-4" />
          New Manifest
        </Button>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Manifests Table */}
      {loading ? (
        <div className="flex items-center justify-center py-8">
          <div className="text-muted-foreground">Loading release manifests...</div>
        </div>
      ) : (
        <ResponsiveTable
          data={manifests}
          columns={manifestColumns}
          keyField="guid"
          emptyState={
            <div className="text-center py-8 text-muted-foreground">
              <Package className="h-8 w-8 mx-auto mb-2 opacity-50" />
              No release manifests found
            </div>
          }
        />
      )}

      {/* Create Manifest Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Create Release Manifest</DialogTitle>
            <DialogDescription>
              Add a known-good binary checksum to allow agent registration.
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreateManifest}>
            <div className="grid gap-4 py-4">
              {formError && (
                <Alert variant="destructive">
                  <AlertDescription>{formError}</AlertDescription>
                </Alert>
              )}

              <div className="grid gap-2">
                <Label htmlFor="version">Version</Label>
                <Input
                  id="version"
                  value={newVersion}
                  onChange={e => setNewVersion(e.target.value)}
                  placeholder="1.0.0"
                  required
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="platform">Platform</Label>
                <Select
                  value={newPlatform}
                  onValueChange={(value) => setNewPlatform(value as ValidPlatform)}
                >
                  <SelectTrigger id="platform">
                    <SelectValue placeholder="Select platform" />
                  </SelectTrigger>
                  <SelectContent>
                    {VALID_PLATFORMS.map(platform => (
                      <SelectItem key={platform} value={platform}>
                        {PLATFORM_LABELS[platform]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="checksum">SHA-256 Checksum</Label>
                <Input
                  id="checksum"
                  value={newChecksum}
                  onChange={e => setNewChecksum(e.target.value)}
                  placeholder="64 hexadecimal characters"
                  className="font-mono text-sm"
                  maxLength={64}
                  required
                />
                <p className="text-xs text-muted-foreground">
                  {newChecksum.length}/64 characters
                </p>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="notes">Notes (optional)</Label>
                <Textarea
                  id="notes"
                  value={newNotes}
                  onChange={e => setNewNotes(e.target.value)}
                  placeholder="e.g., Initial release for macOS"
                  rows={2}
                />
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="is-active"
                  checked={newIsActive}
                  onCheckedChange={checked => setNewIsActive(!!checked)}
                />
                <Label htmlFor="is-active" className="font-normal cursor-pointer">
                  Active (allow agent registration)
                </Label>
              </div>

              {/* Binary filename */}
              {newPlatform && (
                <div className="grid gap-2">
                  <Label htmlFor="filename">Binary Filename</Label>
                  <Input
                    id="filename"
                    placeholder={`e.g., shuttersense-agent-${newPlatform}`}
                    value={newFilename}
                    onChange={e => setNewFilename(e.target.value)}
                    className="font-mono text-sm"
                    required
                  />
                  <p className="text-xs text-muted-foreground">
                    The filename in <code>{`{SHUSAI_AGENT_DIST_DIR}/${newVersion || 'version'}/`}</code>
                  </p>
                </div>
              )}
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={handleCloseCreateDialog}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Creating...' : 'Create Manifest'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Notes Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Notes</DialogTitle>
            <DialogDescription>
              Update the notes for{' '}
              {editingManifest && (
                <span className="font-medium">
                  v{editingManifest.version}
                </span>
              )}
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleUpdateNotes}>
            <div className="grid gap-4 py-4">
              {formError && (
                <Alert variant="destructive">
                  <AlertDescription>{formError}</AlertDescription>
                </Alert>
              )}

              <div className="grid gap-2">
                <Label htmlFor="edit-notes">Notes</Label>
                <Textarea
                  id="edit-notes"
                  value={editNotes}
                  onChange={e => setEditNotes(e.target.value)}
                  placeholder="Optional notes about this release"
                  rows={3}
                />
              </div>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={handleCloseEditDialog}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Saving...' : 'Save Changes'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Release Manifest?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete the manifest for{' '}
              <span className="font-medium">
                v{deletingManifest?.version}
              </span>{' '}
              ({deletingManifest?.platforms.join(', ')}). Consider deactivating
              instead to preserve the record.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              className="bg-destructive text-white hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

export default ReleaseManifestsTab
