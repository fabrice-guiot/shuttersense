import { useState, useEffect } from 'react'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useCollections, useCollectionStats } from '../hooks/useCollections'
import { useConnectors } from '../hooks/useConnectors'
import { usePipelines } from '../hooks/usePipelines'
import { useTools } from '../hooks/useTools'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { CollectionList } from '../components/collections/CollectionList'
import { FiltersSection } from '../components/collections/FiltersSection'
import CollectionForm from '../components/collections/CollectionForm'
import type { Collection, CollectionState, CollectionType } from '@/contracts/api/collection-api'

export default function CollectionsPage() {
  const {
    collections,
    loading,
    error,
    search,
    setSearch,
    filters,
    setFilters,
    createCollection,
    updateCollection,
    deleteCollection,
    testCollection
  } = useCollections()

  // Tools hook for running analysis on collections
  const { runAllTools } = useTools({ autoFetch: false })

  // Filter UI state (for select components)
  const [selectedState, setSelectedState] = useState<CollectionState | 'ALL' | ''>('ALL')
  const [selectedType, setSelectedType] = useState<CollectionType | 'ALL' | ''>('ALL')
  const [accessibleOnly, setAccessibleOnly] = useState(false)

  // Update filters when UI state changes
  useEffect(() => {
    setFilters({
      state: selectedState === 'ALL' || selectedState === '' ? undefined : selectedState,
      type: selectedType === 'ALL' || selectedType === '' ? undefined : selectedType,
      accessible_only: accessibleOnly || undefined
    })
  }, [selectedState, selectedType, accessibleOnly, setFilters])

  const { connectors } = useConnectors()
  const { pipelines } = usePipelines()

  // KPI Stats for header (Issue #37)
  const { stats, refetch: refetchStats } = useCollectionStats()
  const { setStats } = useHeaderStats()

  // Update header stats when data changes
  useEffect(() => {
    if (stats) {
      setStats([
        { label: 'Total Collections', value: stats.total_collections },
        { label: 'Storage Used', value: stats.storage_used_formatted },
        { label: 'Total Files', value: stats.file_count.toLocaleString() },
        { label: 'Total Images', value: stats.image_count.toLocaleString() },
      ])
    }
    return () => setStats([]) // Clear stats on unmount
  }, [stats, setStats])

  const [open, setOpen] = useState(false)
  const [editingCollection, setEditingCollection] = useState<Collection | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  const handleOpen = (collection: Collection | null = null) => {
    setEditingCollection(collection)
    setFormError(null)
    setOpen(true)
  }

  const handleClose = () => {
    setOpen(false)
    setEditingCollection(null)
    setFormError(null)
  }

  const handleSubmit = async (formData: any) => {
    setFormError(null)
    try {
      if (editingCollection) {
        await updateCollection(editingCollection.id, formData)
      } else {
        await createCollection(formData)
        // Refresh KPI stats after creating a new collection
        refetchStats()
      }
      handleClose()
    } catch (err: any) {
      setFormError(err.userMessage || 'Operation failed')
    }
  }

  const handleDelete = (collection: Collection) => {
    deleteCollection(collection.id, false)
      .then(() => {
        // Refresh KPI stats after deleting a collection
        refetchStats()
      })
      .catch(() => {
        // Error handled by hook
      })
  }

  const handleInfo = (collection: Collection) => {
    testCollection(collection.id).catch(() => {
      // Error handled by hook
    })
  }

  const handleRefresh = (collection: Collection) => {
    runAllTools(collection.id).catch(() => {
      // Error handled by hook with toast notifications
    })
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Photo Collections</h1>
        <Button onClick={() => handleOpen()} className="gap-2">
          <Plus className="h-4 w-4" />
          New Collection
        </Button>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Filters Section with Search (Issue #38) */}
      <FiltersSection
        selectedState={selectedState}
        setSelectedState={setSelectedState}
        selectedType={selectedType}
        setSelectedType={setSelectedType}
        accessibleOnly={accessibleOnly}
        setAccessibleOnly={setAccessibleOnly}
        search={search}
        onSearchChange={setSearch}
      />

      {/* Collection List */}
      <CollectionList
        collections={collections}
        loading={loading}
        onEdit={handleOpen}
        onDelete={handleDelete}
        onInfo={handleInfo}
        onRefresh={handleRefresh}
        search={search}
      />

      {/* Create/Edit Dialog */}
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editingCollection ? 'Edit Collection' : 'New Collection'}
            </DialogTitle>
          </DialogHeader>
          <div className="mt-4">
            {formError && (
              <Alert variant="destructive" className="mb-4">
                <AlertDescription>{formError}</AlertDescription>
              </Alert>
            )}
            <CollectionForm
              collection={editingCollection}
              connectors={connectors}
              pipelines={pipelines}
              onSubmit={handleSubmit}
              onCancel={handleClose}
            />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
