/**
 * Organizers Tab Component
 *
 * Manage event organizers with CRUD operations.
 * Part of DirectoryPage tabs for Issue #39 - Calendar Events feature (Phase 9).
 */

import { useState, useEffect, useCallback } from 'react'
import { Plus, Edit, Trash2, Users, Star, Globe, Ticket, Instagram } from 'lucide-react'
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
import { ResponsiveTable, type ColumnDef } from '@/components/ui/responsive-table'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useOrganizers, useOrganizerStats } from '@/hooks/useOrganizers'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { OrganizerForm } from './OrganizerForm'
import { DirectoryPagination } from './DirectoryPagination'
import { GuidBadge } from '@/components/GuidBadge'
import type { Organizer } from '@/contracts/api/organizer-api'
import type { Category } from '@/contracts/api/category-api'
import { cn } from '@/lib/utils'
import { AuditTrailPopover } from '@/components/audit'

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

  const organizerColumns: ColumnDef<Organizer>[] = [
    {
      header: 'Name',
      cell: (organizer) => (
        <div className="flex flex-col">
          <span>{organizer.name}</span>
          {organizer.notes && (
            <span className="text-xs text-muted-foreground line-clamp-1">
              {organizer.notes}
            </span>
          )}
        </div>
      ),
      cellClassName: 'font-medium',
      cardRole: 'title',
    },
    {
      header: 'Category',
      cell: (organizer) => <CategoryBadge category={organizer.category} />,
      cardRole: 'badge',
    },
    {
      header: 'Rating',
      cell: (organizer) => <RatingDisplay rating={organizer.rating} size="sm" />,
      cardRole: 'detail',
    },
    {
      header: 'Ticket Default',
      cell: (organizer) => organizer.ticket_required_default ? (
        <Badge variant="default" className="gap-1">
          <Ticket className="h-3 w-3" />
          Required
        </Badge>
      ) : (
        <span className="text-muted-foreground">-</span>
      ),
      cardRole: 'detail',
    },
    {
      header: 'Website',
      cell: (organizer) => {
        if (!organizer.website) {
          return <span className="text-muted-foreground">-</span>
        }
        let hostname: string | null = null
        try {
          hostname = new URL(organizer.website).hostname
        } catch {
          // malformed URL — fall back to raw value
        }
        return (
          <a
            href={organizer.website}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-primary hover:underline"
            title={organizer.website}
          >
            <Globe className="h-3 w-3" />
            <span className="max-w-[120px] truncate">
              {hostname ?? organizer.website}
            </span>
          </a>
        )
      },
      cardRole: 'detail',
    },
    {
      header: 'Instagram',
      cell: (organizer) => organizer.instagram_handle ? (
        <a
          href={organizer.instagram_url || '#'}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-primary hover:underline"
        >
          <Instagram className="h-3 w-3" />
          <span>@{organizer.instagram_handle}</span>
        </a>
      ) : (
        <span className="text-muted-foreground">-</span>
      ),
      cardRole: 'detail',
    },
    {
      header: 'Modified',
      cell: (organizer) => (
        <AuditTrailPopover audit={organizer.audit} fallbackTimestamp={organizer.updated_at} />
      ),
      cellClassName: 'text-muted-foreground',
      cardRole: 'hidden',
    },
    {
      header: 'Actions',
      headerClassName: 'text-right',
      cell: (organizer) => (
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
      ),
      cardRole: 'action',
    },
  ]

  return (
    <>
      <ResponsiveTable
        data={organizers}
        columns={organizerColumns}
        keyField="guid"
      />

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
  } = useOrganizers(false)

  // KPI Stats for header
  const { stats, refetch: refetchStats } = useOrganizerStats()
  const { setStats } = useHeaderStats()

  // Search state
  const [search, setSearch] = useState('')

  // Pagination state
  const [page, setPage] = useState(1)
  const [limit, setLimit] = useState(20)

  // Category filter state
  const [categoryFilter, setCategoryFilter] = useState<string>('all')

  // Fetch with current filters and pagination
  const doFetch = useCallback(() => {
    fetchOrganizers({
      search: search || undefined,
      category_guid: categoryFilter !== 'all' ? categoryFilter : undefined,
      limit,
      offset: (page - 1) * limit,
    })
  }, [fetchOrganizers, search, categoryFilter, limit, page])

  useEffect(() => {
    doFetch()
  }, [doFetch])

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
      doFetch()
    } catch (err: any) {
      setFormError(err.userMessage || 'Operation failed')
    }
  }

  const handleDelete = (organizer: Organizer) => {
    deleteOrganizer(organizer.guid)
      .then(() => {
        refetchStats()
        doFetch()
      })
      .catch(() => {
        // Error handled by hook
      })
  }

  // Handle search
  const handleSearch = () => {
    setPage(1)
  }

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const handleClearSearch = () => {
    setSearch('')
    setPage(1)
  }

  const handleCategoryFilterChange = (value: string) => {
    setCategoryFilter(value)
    setPage(1)
  }

  const handlePageChange = (newPage: number) => {
    setPage(newPage)
  }

  const handleLimitChange = (newLimit: number) => {
    setLimit(newLimit)
    setPage(1)
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Search + Filter + Action Row */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2">
          <Input
            placeholder="Search organizers..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={handleSearchKeyDown}
            className="max-w-sm"
          />
          <Select value={categoryFilter} onValueChange={handleCategoryFilterChange}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="All Categories" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              {categories.map((cat) => (
                <SelectItem key={cat.guid} value={cat.guid}>
                  {cat.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={handleSearch}>
            Search
          </Button>
          {(search || categoryFilter !== 'all') && (
            <Button variant="ghost" onClick={() => { setSearch(''); setCategoryFilter('all'); setPage(1) }}>
              Clear
            </Button>
          )}
        </div>
        <Button onClick={() => handleOpen()} className="gap-2">
          <Plus className="h-4 w-4" />
          New Organizer
        </Button>
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

      {/* Pagination */}
      {total > 0 && (
        <DirectoryPagination
          page={page}
          limit={limit}
          total={total}
          onPageChange={handlePageChange}
          onLimitChange={handleLimitChange}
        />
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
