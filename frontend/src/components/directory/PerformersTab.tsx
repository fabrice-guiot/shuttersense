/**
 * Performers Tab Component
 *
 * Manage event performers with CRUD operations.
 * Part of DirectoryPage tabs for Issue #39 - Calendar Events feature (Phase 11).
 */

import { useState, useEffect } from 'react'
import { Plus, Edit, Trash2, Users, Globe, Instagram } from 'lucide-react'
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
import { usePerformers, usePerformerStats } from '@/hooks/usePerformers'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { PerformerForm } from './PerformerForm'
import { GuidBadge } from '@/components/GuidBadge'
import type { Performer } from '@/contracts/api/performer-api'
import type { Category } from '@/contracts/api/category-api'
import { formatRelativeTime } from '@/utils/dateFormat'

// ============================================================================
// Category Badge Component
// ============================================================================

interface CategoryBadgeProps {
  category: {
    name: string
    color: string | null
    icon: string | null
  }
}

function CategoryBadge({ category }: CategoryBadgeProps) {
  return (
    <Badge
      variant="secondary"
      className="gap-1"
      style={{
        backgroundColor: category.color ? `${category.color}20` : undefined,
        borderColor: category.color || undefined,
        color: category.color || undefined
      }}
    >
      {category.name}
    </Badge>
  )
}

// ============================================================================
// Performer List Component
// ============================================================================

interface PerformerListProps {
  performers: Performer[]
  loading: boolean
  onEdit: (performer: Performer) => void
  onDelete: (performer: Performer) => void
}

function PerformerList({ performers, loading, onEdit, onDelete }: PerformerListProps) {
  const [deleteDialog, setDeleteDialog] = useState<{
    open: boolean
    performer: Performer | null
  }>({ open: false, performer: null })

  const handleDeleteClick = (performer: Performer) => {
    setDeleteDialog({ open: true, performer })
  }

  const handleDeleteConfirm = () => {
    if (deleteDialog.performer) {
      onDelete(deleteDialog.performer)
      setDeleteDialog({ open: false, performer: null })
    }
  }

  if (loading && performers.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-muted-foreground">Loading performers...</div>
      </div>
    )
  }

  if (performers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Users className="h-12 w-12 text-muted-foreground/30 mb-4" />
        <div className="text-muted-foreground mb-2">No performers found</div>
        <p className="text-sm text-muted-foreground">
          Create your first performer to get started
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
            <TableHead>Category</TableHead>
            <TableHead>Instagram</TableHead>
            <TableHead>Website</TableHead>
            <TableHead>Created</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {performers.map((performer) => (
            <TableRow key={performer.guid}>
              <TableCell className="font-medium">
                <div className="flex flex-col">
                  <span>{performer.name}</span>
                  {performer.additional_info && (
                    <span className="text-xs text-muted-foreground line-clamp-1">
                      {performer.additional_info}
                    </span>
                  )}
                </div>
              </TableCell>
              <TableCell>
                <CategoryBadge category={performer.category} />
              </TableCell>
              <TableCell>
                {performer.instagram_handle ? (
                  <a
                    href={performer.instagram_url || '#'}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-primary hover:underline"
                  >
                    <Instagram className="h-3 w-3" />
                    <span>@{performer.instagram_handle}</span>
                  </a>
                ) : (
                  <span className="text-muted-foreground">-</span>
                )}
              </TableCell>
              <TableCell>
                {performer.website ? (
                  <a
                    href={performer.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-primary hover:underline"
                    title={performer.website}
                  >
                    <Globe className="h-3 w-3" />
                    <span className="max-w-[120px] truncate">
                      {new URL(performer.website).hostname}
                    </span>
                  </a>
                ) : (
                  <span className="text-muted-foreground">-</span>
                )}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {formatRelativeTime(performer.created_at)}
              </TableCell>
              <TableCell className="text-right">
                <div className="flex justify-end gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onEdit(performer)}
                    title="Edit performer"
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDeleteClick(performer)}
                    title="Delete performer"
                    className="text-destructive hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialog.open}
        onOpenChange={(open) => {
          if (!open) setDeleteDialog({ open: false, performer: null })
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Performer</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the performer "{deleteDialog.performer?.name}"?
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialog({ open: false, performer: null })}
            >
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteConfirm}>
              Delete
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

interface PerformersTabProps {
  categories: Category[]
}

export function PerformersTab({ categories }: PerformersTabProps) {
  const {
    performers,
    total,
    loading,
    error,
    fetchPerformers,
    createPerformer,
    updatePerformer,
    deletePerformer
  } = usePerformers()

  // KPI Stats for header
  const { stats, refetch: refetchStats } = usePerformerStats()
  const { setStats } = useHeaderStats()

  // Search state
  const [search, setSearch] = useState('')

  // Update header stats when data changes
  useEffect(() => {
    if (stats) {
      setStats([
        { label: 'Total Performers', value: stats.total_count },
        { label: 'With Instagram', value: stats.with_instagram_count },
        { label: 'With Website', value: stats.with_website_count },
      ])
    }
    return () => setStats([]) // Clear stats on unmount
  }, [stats, setStats])

  const [open, setOpen] = useState(false)
  const [editingPerformer, setEditingPerformer] = useState<Performer | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  const handleOpen = (performer: Performer | null = null) => {
    setEditingPerformer(performer)
    setFormError(null)
    setOpen(true)
  }

  const handleClose = () => {
    setOpen(false)
    setEditingPerformer(null)
    setFormError(null)
  }

  const handleSubmit = async (formData: any) => {
    setFormError(null)
    try {
      if (editingPerformer) {
        await updatePerformer(editingPerformer.guid, formData)
      } else {
        await createPerformer(formData)
        refetchStats()
      }
      handleClose()
    } catch (err: any) {
      setFormError(err.userMessage || 'Operation failed')
    }
  }

  const handleDelete = (performer: Performer) => {
    deletePerformer(performer.guid)
      .then(() => {
        refetchStats()
      })
      .catch(() => {
        // Error handled by hook
      })
  }

  // Handle search
  const handleSearch = () => {
    fetchPerformers({ search: search || undefined })
  }

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const handleClearSearch = () => {
    setSearch('')
    fetchPerformers({})
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Event Performers</h2>
          <p className="text-sm text-muted-foreground">
            Manage performers and artists for your events
          </p>
        </div>
        <Button onClick={() => handleOpen()} className="gap-2">
          <Plus className="h-4 w-4" />
          New Performer
        </Button>
      </div>

      {/* Search */}
      <div className="flex gap-2">
        <Input
          placeholder="Search performers..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={handleSearchKeyDown}
          className="max-w-sm"
        />
        <Button variant="outline" onClick={handleSearch}>
          Search
        </Button>
        {search && (
          <Button variant="ghost" onClick={handleClearSearch}>
            Clear
          </Button>
        )}
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Performer List */}
      <PerformerList
        performers={performers}
        loading={loading}
        onEdit={handleOpen}
        onDelete={handleDelete}
      />

      {/* Pagination info */}
      {total > 0 && (
        <div className="text-sm text-muted-foreground">
          Showing {performers.length} of {total} performers
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="max-w-lg max-h-[90vh] flex flex-col">
          <DialogHeader className="flex-shrink-0">
            <DialogTitle>
              {editingPerformer ? 'Edit Performer' : 'New Performer'}
            </DialogTitle>
            {editingPerformer && (
              <DialogDescription asChild>
                <div className="pt-1">
                  <GuidBadge guid={editingPerformer.guid} />
                </div>
              </DialogDescription>
            )}
          </DialogHeader>
          <div className="flex-1 overflow-y-auto mt-4 pr-2">
            {formError && (
              <Alert variant="destructive" className="mb-4">
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            )}
            <PerformerForm
              performer={editingPerformer}
              categories={categories}
              onSubmit={handleSubmit}
              onCancel={handleClose}
            />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default PerformersTab
