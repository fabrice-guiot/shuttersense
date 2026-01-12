/**
 * Locations Tab Component
 *
 * Manage event locations with CRUD operations.
 * Part of DirectoryPage tabs for Issue #39 - Calendar Events feature (Phase 8).
 */

import { useState, useEffect } from 'react'
import { Plus, Edit, Trash2, MapPin, Star } from 'lucide-react'
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
import { useLocations, useLocationStats } from '@/hooks/useLocations'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { LocationForm } from './LocationForm'
import { GuidBadge } from '@/components/GuidBadge'
import type { Location } from '@/contracts/api/location-api'
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
// Location Address Display
// ============================================================================

interface AddressDisplayProps {
  location: Location
}

function AddressDisplay({ location }: AddressDisplayProps) {
  const parts = [location.city, location.state, location.country].filter(Boolean)
  if (parts.length === 0) return <span className="text-muted-foreground">No address</span>

  return (
    <span className="text-muted-foreground">{parts.join(', ')}</span>
  )
}

// ============================================================================
// Location List Component
// ============================================================================

interface LocationListProps {
  locations: Location[]
  loading: boolean
  onEdit: (location: Location) => void
  onDelete: (location: Location) => void
}

function LocationList({ locations, loading, onEdit, onDelete }: LocationListProps) {
  const [deleteDialog, setDeleteDialog] = useState<{
    open: boolean
    location: Location | null
  }>({ open: false, location: null })

  const handleDeleteClick = (location: Location) => {
    setDeleteDialog({ open: true, location })
  }

  const handleDeleteConfirm = () => {
    if (deleteDialog.location) {
      onDelete(deleteDialog.location)
      setDeleteDialog({ open: false, location: null })
    }
  }

  if (loading && locations.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-muted-foreground">Loading locations...</div>
      </div>
    )
  }

  if (locations.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <MapPin className="h-12 w-12 text-muted-foreground/30 mb-4" />
        <div className="text-muted-foreground mb-2">No locations found</div>
        <p className="text-sm text-muted-foreground">
          Create your first location to get started
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
            <TableHead>Location</TableHead>
            <TableHead>Category</TableHead>
            <TableHead>Rating</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Created</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {locations.map((location) => (
            <TableRow key={location.guid}>
              <TableCell className="font-medium">
                <div className="flex flex-col">
                  <span>{location.name}</span>
                  {location.timezone && (
                    <span className="text-xs text-muted-foreground">{location.timezone}</span>
                  )}
                </div>
              </TableCell>
              <TableCell>
                <AddressDisplay location={location} />
              </TableCell>
              <TableCell>
                <CategoryBadge category={location.category} />
              </TableCell>
              <TableCell>
                <RatingDisplay rating={location.rating} size="sm" />
              </TableCell>
              <TableCell>
                <Badge variant={location.is_known ? 'default' : 'secondary'}>
                  {location.is_known ? 'Known' : 'One-time'}
                </Badge>
              </TableCell>
              <TableCell className="text-muted-foreground">
                {formatRelativeTime(location.created_at)}
              </TableCell>
              <TableCell className="text-right">
                <div className="flex justify-end gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onEdit(location)}
                    title="Edit location"
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDeleteClick(location)}
                    title="Delete location"
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
          if (!open) setDeleteDialog({ open: false, location: null })
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Location</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the location "{deleteDialog.location?.name}"?
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialog({ open: false, location: null })}
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

interface LocationsTabProps {
  categories: Category[]
}

export function LocationsTab({ categories }: LocationsTabProps) {
  const {
    locations,
    total,
    loading,
    error,
    fetchLocations,
    createLocation,
    updateLocation,
    deleteLocation,
    geocodeAddress
  } = useLocations()

  // KPI Stats for header
  const { stats, refetch: refetchStats } = useLocationStats()
  const { setStats } = useHeaderStats()

  // Search state
  const [search, setSearch] = useState('')

  // Update header stats when data changes
  useEffect(() => {
    if (stats) {
      setStats([
        { label: 'Known Locations', value: stats.known_count },
        { label: 'Total Locations', value: stats.total_count },
        { label: 'With Coordinates', value: stats.with_coordinates_count },
      ])
    }
    return () => setStats([]) // Clear stats on unmount
  }, [stats, setStats])

  const [open, setOpen] = useState(false)
  const [editingLocation, setEditingLocation] = useState<Location | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  const handleOpen = (location: Location | null = null) => {
    setEditingLocation(location)
    setFormError(null)
    setOpen(true)
  }

  const handleClose = () => {
    setOpen(false)
    setEditingLocation(null)
    setFormError(null)
  }

  const handleSubmit = async (formData: any) => {
    setFormError(null)
    try {
      if (editingLocation) {
        await updateLocation(editingLocation.guid, formData)
      } else {
        await createLocation(formData)
        refetchStats()
      }
      handleClose()
    } catch (err: any) {
      setFormError(err.userMessage || 'Operation failed')
    }
  }

  const handleDelete = (location: Location) => {
    deleteLocation(location.guid)
      .then(() => {
        refetchStats()
      })
      .catch(() => {
        // Error handled by hook
      })
  }

  // Handle search
  const handleSearch = () => {
    fetchLocations({ search: search || undefined })
  }

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const handleClearSearch = () => {
    setSearch('')
    fetchLocations({})
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Event Locations</h2>
          <p className="text-sm text-muted-foreground">
            Manage venues and locations for your events
          </p>
        </div>
        <Button onClick={() => handleOpen()} className="gap-2">
          <Plus className="h-4 w-4" />
          New Location
        </Button>
      </div>

      {/* Search */}
      <div className="flex gap-2">
        <Input
          placeholder="Search locations..."
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

      {/* Location List */}
      <LocationList
        locations={locations}
        loading={loading}
        onEdit={handleOpen}
        onDelete={handleDelete}
      />

      {/* Pagination info */}
      {total > 0 && (
        <div className="text-sm text-muted-foreground">
          Showing {locations.length} of {total} locations
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="max-w-lg max-h-[90vh] flex flex-col">
          <DialogHeader className="flex-shrink-0">
            <DialogTitle>
              {editingLocation ? 'Edit Location' : 'New Location'}
            </DialogTitle>
            {editingLocation && (
              <DialogDescription asChild>
                <div className="pt-1">
                  <GuidBadge guid={editingLocation.guid} />
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
            <LocationForm
              location={editingLocation}
              categories={categories}
              onSubmit={handleSubmit}
              onCancel={handleClose}
              onGeocode={geocodeAddress}
            />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default LocationsTab
