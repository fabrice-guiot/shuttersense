/**
 * Categories Tab Component
 *
 * Manage event categories with CRUD operations.
 * Part of SettingsPage tabs for Issue #39 - Calendar Events feature.
 */

import { useState, useEffect } from 'react'
import { Plus, Edit, Trash2 } from 'lucide-react'
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
import { useCategories, useCategoryStats } from '@/hooks/useCategories'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { CategoryForm, ICON_MAP } from './CategoryForm'
import { GuidBadge } from '@/components/GuidBadge'
import type { Category } from '@/contracts/api/category-api'
import { cn } from '@/lib/utils'
import { formatRelativeTime } from '@/utils/dateFormat'

// ============================================================================
// Category Icon Component
// ============================================================================

interface CategoryIconProps {
  icon: string | null
  color: string | null
  size?: 'sm' | 'md'
}

function CategoryIcon({ icon, color, size = 'md' }: CategoryIconProps) {
  const iconSizeClass = size === 'sm' ? 'h-3.5 w-3.5' : 'h-4 w-4'
  const containerSize = size === 'sm' ? 'h-6 w-6' : 'h-8 w-8'

  // Look up the Lucide icon component
  const IconComponent = icon ? ICON_MAP[icon] : null

  return (
    <div
      className={cn(
        containerSize,
        'rounded-full flex items-center justify-center text-white',
        size === 'sm' ? 'text-xs' : 'text-sm'
      )}
      style={{ backgroundColor: color || '#6B7280' }}
    >
      {IconComponent ? (
        <IconComponent className={iconSizeClass} />
      ) : icon ? (
        // Fallback to first letter if icon name not in map
        <span className="font-medium">{icon.charAt(0).toUpperCase()}</span>
      ) : null}
    </div>
  )
}

// ============================================================================
// Category List Component
// ============================================================================

interface CategoryListProps {
  categories: Category[]
  loading: boolean
  onEdit: (category: Category) => void
  onDelete: (category: Category) => void
}

function CategoryList({ categories, loading, onEdit, onDelete }: CategoryListProps) {
  const [deleteDialog, setDeleteDialog] = useState<{
    open: boolean
    category: Category | null
  }>({ open: false, category: null })

  const handleDeleteClick = (category: Category) => {
    setDeleteDialog({ open: true, category })
  }

  const handleDeleteConfirm = () => {
    if (deleteDialog.category) {
      onDelete(deleteDialog.category)
      setDeleteDialog({ open: false, category: null })
    }
  }

  if (loading && categories.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-muted-foreground">Loading categories...</div>
      </div>
    )
  }

  if (categories.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <div className="text-muted-foreground mb-2">No categories found</div>
        <p className="text-sm text-muted-foreground">
          Create your first category to get started
        </p>
      </div>
    )
  }

  return (
    <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-12"></TableHead>
            <TableHead>Name</TableHead>
            <TableHead>Icon</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Created</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {categories.map((category) => (
            <TableRow key={category.guid}>
              <TableCell>
                <CategoryIcon icon={category.icon} color={category.color} size="sm" />
              </TableCell>
              <TableCell className="font-medium">{category.name}</TableCell>
              <TableCell className="text-muted-foreground">
                {category.icon || '-'}
              </TableCell>
              <TableCell>
                <Badge variant={category.is_active ? 'default' : 'secondary'}>
                  {category.is_active ? 'Active' : 'Inactive'}
                </Badge>
              </TableCell>
              <TableCell className="text-muted-foreground">
                {formatRelativeTime(category.created_at)}
              </TableCell>
              <TableCell className="text-right">
                <div className="flex justify-end gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onEdit(category)}
                    title="Edit category"
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleDeleteClick(category)}
                    title="Delete category"
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
          if (!open) setDeleteDialog({ open: false, category: null })
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Category</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the category "{deleteDialog.category?.name}"?
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialog({ open: false, category: null })}
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

export function CategoriesTab() {
  const {
    categories,
    loading,
    error,
    createCategory,
    updateCategory,
    deleteCategory
  } = useCategories()

  // KPI Stats for header
  const { stats, refetch: refetchStats } = useCategoryStats()
  const { setStats } = useHeaderStats()

  // Update header stats when data changes
  useEffect(() => {
    if (stats) {
      setStats([
        { label: 'Active Categories', value: stats.active_count },
        { label: 'Total Categories', value: stats.total_count },
      ])
    }
    return () => setStats([]) // Clear stats on unmount
  }, [stats, setStats])

  const [open, setOpen] = useState(false)
  const [editingCategory, setEditingCategory] = useState<Category | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  const handleOpen = (category: Category | null = null) => {
    setEditingCategory(category)
    setFormError(null)
    setOpen(true)
  }

  const handleClose = () => {
    setOpen(false)
    setEditingCategory(null)
    setFormError(null)
  }

  const handleSubmit = async (formData: any) => {
    setFormError(null)
    try {
      if (editingCategory) {
        await updateCategory(editingCategory.guid, formData)
      } else {
        await createCategory(formData)
        refetchStats()
      }
      handleClose()
    } catch (err: any) {
      setFormError(err.userMessage || 'Operation failed')
    }
  }

  const handleDelete = (category: Category) => {
    deleteCategory(category.guid)
      .then(() => {
        refetchStats()
      })
      .catch(() => {
        // Error handled by hook
      })
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Event Categories</h2>
          <p className="text-sm text-muted-foreground">
            Organize events by type (Airshow, Wildlife, Wedding, etc.)
          </p>
        </div>
        <Button onClick={() => handleOpen()} className="gap-2">
          <Plus className="h-4 w-4" />
          New Category
        </Button>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Category List */}
      <CategoryList
        categories={categories}
        loading={loading}
        onEdit={handleOpen}
        onDelete={handleDelete}
      />

      {/* Create/Edit Dialog */}
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {editingCategory ? 'Edit Category' : 'New Category'}
            </DialogTitle>
            {editingCategory && (
              <DialogDescription asChild>
                <div className="pt-1">
                  <GuidBadge guid={editingCategory.guid} />
                </div>
              </DialogDescription>
            )}
          </DialogHeader>
          <div className="mt-4">
            {formError && (
              <Alert variant="destructive" className="mb-4">
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            )}
            <CategoryForm
              category={editingCategory}
              onSubmit={handleSubmit}
              onCancel={handleClose}
            />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default CategoriesTab
