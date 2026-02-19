/**
 * Event Statuses Section Component
 *
 * Manages event status configuration options.
 * Displays status list with CRUD operations and reordering.
 *
 * Issue #39 - Calendar Events feature (Phase 12)
 * Issue #238 - Configurable forces_skip behavior
 */

import { useState, useEffect } from 'react'
import { Plus, Trash2, Pencil, GripVertical, Flag, Loader2, SkipForward } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import type { EventStatusConfig } from '@/contracts/api/config-api'

// ============================================================================
// Types
// ============================================================================

interface EventStatusesProps {
  /** Event statuses from configuration */
  statuses: Record<string, EventStatusConfig>
  /** Loading state */
  loading?: boolean
  /** Called when a status is created */
  onCreate: (key: string, value: { label: string; display_order: number; forces_skip?: boolean }) => Promise<void>
  /** Called when a status is updated */
  onUpdate: (key: string, value: { label: string; display_order: number; forces_skip?: boolean }) => Promise<void>
  /** Called when a status is deleted */
  onDelete: (key: string) => Promise<void>
}

// ============================================================================
// Component
// ============================================================================

export function EventStatusesSection({
  statuses,
  loading = false,
  onCreate,
  onUpdate,
  onDelete
}: EventStatusesProps) {
  // Dialog states
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Edit form state
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [formData, setFormData] = useState({ key: '', label: '', forces_skip: false })

  // Convert to sorted array
  const statusList = Object.entries(statuses)
    .map(([key, value]) => ({
      key,
      label: value.label,
      display_order: value.display_order,
      forces_skip: value.forces_skip ?? false
    }))
    .sort((a, b) => a.display_order - b.display_order)

  // Open add dialog
  const handleAdd = () => {
    setEditingKey(null)
    setFormData({ key: '', label: '', forces_skip: false })
    setFormError(null)
    setEditDialogOpen(true)
  }

  // Open edit dialog
  const handleEdit = (key: string) => {
    const status = statuses[key]
    setEditingKey(key)
    setFormData({ key, label: status.label, forces_skip: status.forces_skip ?? false })
    setFormError(null)
    setEditDialogOpen(true)
  }

  // Open delete dialog
  const handleDeleteClick = (key: string) => {
    setEditingKey(key)
    setDeleteDialogOpen(true)
  }

  // Handle save
  const handleSave = async () => {
    if (!formData.key.trim()) {
      setFormError('Status key is required')
      return
    }
    if (!formData.label.trim()) {
      setFormError('Status label is required')
      return
    }

    // Validate key format (lowercase, alphanumeric with underscores)
    const keyPattern = /^[a-z][a-z0-9_]*$/
    if (!keyPattern.test(formData.key)) {
      setFormError('Key must start with a letter and contain only lowercase letters, numbers, and underscores')
      return
    }

    // Check for duplicate key on create
    if (!editingKey && statuses[formData.key]) {
      setFormError(`Status with key "${formData.key}" already exists`)
      return
    }

    setIsSubmitting(true)
    setFormError(null)

    try {
      if (editingKey) {
        // Update existing
        await onUpdate(editingKey, {
          label: formData.label.trim(),
          display_order: statuses[editingKey].display_order,
          forces_skip: formData.forces_skip,
        })
      } else {
        // Create new - add at the end
        const maxOrder = statusList.length > 0
          ? Math.max(...statusList.map(s => s.display_order))
          : -1
        await onCreate(formData.key.trim(), {
          label: formData.label.trim(),
          display_order: maxOrder + 1,
          forces_skip: formData.forces_skip,
        })
      }
      setEditDialogOpen(false)
    } catch (err: any) {
      setFormError(err.userMessage || 'Operation failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Handle delete confirm
  const handleDeleteConfirm = async () => {
    if (!editingKey) return

    setIsSubmitting(true)
    try {
      await onDelete(editingKey)
      setDeleteDialogOpen(false)
    } catch (err: any) {
      setFormError(err.userMessage || 'Delete failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center gap-2">
          <Flag className="h-5 w-5 text-muted-foreground" />
          <div>
            <CardTitle className="text-lg">Event Statuses</CardTitle>
            <CardDescription>Configure event status options for calendar events</CardDescription>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleAdd}
          className="gap-1"
        >
          <Plus className="h-4 w-4" />
          Add
        </Button>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-2">
            <div className="h-8 w-full bg-muted animate-pulse rounded" />
            <div className="h-8 w-full bg-muted animate-pulse rounded" />
          </div>
        ) : statusList.length === 0 ? (
          <p className="text-sm text-muted-foreground">No statuses configured</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-10">#</TableHead>
                <TableHead>Key</TableHead>
                <TableHead>Label</TableHead>
                <TableHead className="w-24">Forces Skip</TableHead>
                <TableHead className="w-24">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {statusList.map((status, index) => (
                <TableRow key={status.key}>
                  <TableCell className="text-muted-foreground">
                    {index + 1}
                  </TableCell>
                  <TableCell>
                    <Badge variant="secondary" className="font-mono">
                      {status.key}
                    </Badge>
                  </TableCell>
                  <TableCell>{status.label}</TableCell>
                  <TableCell>
                    {status.forces_skip && (
                      <Badge variant="outline" className="text-xs gap-1">
                        <SkipForward className="h-3 w-3" />
                        Skip
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleEdit(status.key)}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDeleteClick(status.key)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={() => setEditDialogOpen(false)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingKey ? 'Edit Status' : 'Add Status'}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="statusKey">Key</Label>
              <Input
                id="statusKey"
                value={formData.key}
                onChange={e => setFormData(prev => ({ ...prev, key: e.target.value.toLowerCase() }))}
                placeholder="e.g., in_progress"
                disabled={!!editingKey}
              />
              <p className="text-xs text-muted-foreground">
                Unique identifier used in code. Cannot be changed after creation.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="statusLabel">Label</Label>
              <Input
                id="statusLabel"
                value={formData.label}
                onChange={e => setFormData(prev => ({ ...prev, label: e.target.value }))}
                placeholder="e.g., In Progress"
              />
              <p className="text-xs text-muted-foreground">
                Display name shown in dropdowns and forms.
              </p>
            </div>

            <div className="flex items-center justify-between rounded-lg border p-3">
              <div className="space-y-0.5">
                <Label htmlFor="forcesSkip" className="text-sm font-medium">
                  Forces Skip
                </Label>
                <p className="text-xs text-muted-foreground">
                  Automatically set attendance to "Skipped" for events with this status.
                </p>
              </div>
              <Switch
                id="forcesSkip"
                checked={formData.forces_skip}
                onCheckedChange={(checked) => setFormData(prev => ({ ...prev, forces_skip: checked }))}
              />
            </div>

            {formError && (
              <Alert variant="destructive">
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={() => setDeleteDialogOpen(false)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Status</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the status "{editingKey}"?
              Events using this status will still retain the value.
            </DialogDescription>
          </DialogHeader>
          {formError && (
            <Alert variant="destructive">
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteConfirm} disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}

export default EventStatusesSection
