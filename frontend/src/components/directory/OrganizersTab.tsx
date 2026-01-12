/**
 * Organizers Tab Component
 *
 * Manage event organizers with CRUD operations.
 * Part of DirectoryPage tabs for Issue #39 - Calendar Events feature (Phase 9).
 */

import { useState, useEffect } from 'react'
import { Plus, Edit, Trash2, Users, Star, Globe, Ticket } from 'lucide-react'
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
import { useOrganizers, useOrganizerStats } from '@/hooks/useOrganizers'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { OrganizerForm } from './OrganizerForm'
import { GuidBadge } from '@/components/GuidBadge'
import type { Organizer } from '@/contracts/api/organizer-api'
import type { Category } from '@/contracts/api/category-api'
import { cn } from '@/lib/utils'
import { formatRelativeTime } from '@/utils/dateFormat'

// ============================================================================
// Rating Display Component
// ============================================================================

interface RatingDisplayProps {
  rating: number | null
  size?: 'sm' | 'md'
}

function RatingDisplay({ rating, size = 'md' }: RatingDisplayProps) {
  if (rating === null) return <span className="text-muted-foreground">-</span>

  const starSize = size === 'sm' ? 'h-3 w-3' : 'h-4 w-4'

  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          className={cn(
            starSize,
            i < rating
              ? 'fill-yellow-400 text-yellow-400'
              : 'text-muted-foreground/30'
          )}
        />
      ))}
    </div>
  )
}

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
// Organizer List Component
// ============================================================================

interface OrganizerListProps {
  organizers: Organizer[]
  loading: boolean
  onEdit: (organizer: Organizer) => void
  onDelete: (organizer: Organizer) => void
}

function OrganizerList({ organizers, loading, onEdit, onDelete }: OrganizerListProps) {
  const [deleteDialog, setDeleteDialog] = useState<{
    open: boolean
    organizer: Organizer | null
  }>({ open: false, organizer: null })

  const handleDeleteClick = (organizer: Organizer) => {
    setDeleteDialog({ open: true, organizer })
  }

  const handleDeleteConfirm = () => {
    if (deleteDialog.organizer) {
      onDelete(deleteDialog.organizer)
      setDeleteDialog({ open: false, organizer: null })
    }
  }

  if (loading && organizers.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-muted-foreground">Loading organizers...</div>
      </div>
    )
  }

  if (organizers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Users className="h-12 w-12 text-muted-foreground/30 mb-4" />
        <div className="text-muted-foreground mb-2">No organizers found</div>
        <p className="text-sm text-muted-foreground">
          Create your first organizer to get started
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
            <TableHead>Rating</TableHead>
            <TableHead>Ticket Default</TableHead>
            <TableHead>Website</TableHead>
            <TableHead>Created</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {organizers.map((organizer) => (
            <TableRow key={organizer.guid}>
              <TableCell className="font-medium">
                <div className="flex flex-col">
                  <span>{organizer.name}</span>
                  {organizer.notes && (
                    <span className="text-xs text-muted-foreground line-clamp-1">
                      {organizer.notes}
                    </span>
                  )}
                </div>
              </TableCell>
              <TableCell>
                <CategoryBadge category={organizer.category} />
              </TableCell>
              <TableCell>
                <RatingDisplay rating={organizer.rating} size="sm" />
              </TableCell>
              <TableCell>
                {organizer.ticket_required_default ? (
                  <Badge variant="default" className="gap-1">
                    <Ticket className="h-3 w-3" />
                    Required
                  </Badge>
                ) : (
                  <span className="text-muted-foreground">-</span>
                )}
              </TableCell>
              <TableCell>
                {organizer.website ? (
                  <a
                    href={organizer.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-primary hover:underline"
                    title={organizer.website}
                  >
                    <Globe className="h-3 w-3" />
                    <span className="max-w-[120px] truncate">
                      {new URL(organizer.website).hostname}
                    </span>
                  </a>
                ) : (
                  <span className="text-muted-foreground">-</span>
                )}
              </TableCell>
              <TableCell className="text-muted-foreground">
                {formatRelativeTime(organizer.created_at)}
              </TableCell>
              <TableCell className="text-right">
                <div className="flex justify-end gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onEdit(organizer)}
                    title="Edit organizer"
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDeleteClick(organizer)}
                    title="Delete organizer"
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
          if (!open) setDeleteDialog({ open: false, organizer: null })
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Organizer</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the organizer "{deleteDialog.organizer?.name}"?
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialog({ open: false, organizer: null })}
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

interface OrganizersTabProps {
  categories: Category[]
}

export function OrganizersTab({ categories }: OrganizersTabProps) {
  const {
    organizers,
    total,
    loading,
    error,
    fetchOrganizers,
    createOrganizer,
    updateOrganizer,
    deleteOrganizer
  } = useOrganizers()

  // KPI Stats for header
  const { stats, refetch: refetchStats } = useOrganizerStats()
  const { setStats } = useHeaderStats()

  // Search state
  const [search, setSearch] = useState('')

  // Update header stats when data changes
  useEffect(() => {
    if (stats) {
      const avgRatingDisplay = stats.avg_rating !== null
        ? stats.avg_rating.toFixed(1)
        : '-'

      setStats([
        { label: 'Total Organizers', value: stats.total_count },
        { label: 'With Rating', value: stats.with_rating_count },
        { label: 'Avg Rating', value: avgRatingDisplay },
      ])
    }
    return () => setStats([]) // Clear stats on unmount
  }, [stats, setStats])

  const [open, setOpen] = useState(false)
  const [editingOrganizer, setEditingOrganizer] = useState<Organizer | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  const handleOpen = (organizer: Organizer | null = null) => {
    setEditingOrganizer(organizer)
    setFormError(null)
    setOpen(true)
  }

  const handleClose = () => {
    setOpen(false)
    setEditingOrganizer(null)
    setFormError(null)
  }

  const handleSubmit = async (formData: any) => {
    setFormError(null)
    try {
      if (editingOrganizer) {
        await updateOrganizer(editingOrganizer.guid, formData)
      } else {
        await createOrganizer(formData)
        refetchStats()
      }
      handleClose()
    } catch (err: any) {
      setFormError(err.userMessage || 'Operation failed')
    }
  }

  const handleDelete = (organizer: Organizer) => {
    deleteOrganizer(organizer.guid)
      .then(() => {
        refetchStats()
      })
      .catch(() => {
        // Error handled by hook
      })
  }

  // Handle search
  const handleSearch = () => {
    fetchOrganizers({ search: search || undefined })
  }

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const handleClearSearch = () => {
    setSearch('')
    fetchOrganizers({})
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Event Organizers</h2>
          <p className="text-sm text-muted-foreground">
            Manage organizers and promoters for your events
          </p>
        </div>
        <Button onClick={() => handleOpen()} className="gap-2">
          <Plus className="h-4 w-4" />
          New Organizer
        </Button>
      </div>

      {/* Search */}
      <div className="flex gap-2">
        <Input
          placeholder="Search organizers..."
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

      {/* Organizer List */}
      <OrganizerList
        organizers={organizers}
        loading={loading}
        onEdit={handleOpen}
        onDelete={handleDelete}
      />

      {/* Pagination info */}
      {total > 0 && (
        <div className="text-sm text-muted-foreground">
          Showing {organizers.length} of {total} organizers
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="max-w-lg max-h-[90vh] flex flex-col">
          <DialogHeader className="flex-shrink-0">
            <DialogTitle>
              {editingOrganizer ? 'Edit Organizer' : 'New Organizer'}
            </DialogTitle>
            {editingOrganizer && (
              <DialogDescription asChild>
                <div className="pt-1">
                  <GuidBadge guid={editingOrganizer.guid} />
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
            <OrganizerForm
              organizer={editingOrganizer}
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

export default OrganizersTab
