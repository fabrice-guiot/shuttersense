import { useState, useEffect, useCallback } from 'react'
import { Plus, AlertTriangle } from 'lucide-react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useCollections, useCollectionStats } from '../hooks/useCollections'
import { useConnectors } from '../hooks/useConnectors'
import { usePipelines } from '../hooks/usePipelines'
import { useTools } from '../hooks/useTools'
import { useAgentPoolStatus } from '../hooks/useAgentPoolStatus'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { CollectionList } from '../components/collections/CollectionList'
import { FiltersSection } from '../components/collections/FiltersSection'
import CollectionForm from '../components/collections/CollectionForm'
import { GuidBadge } from '@/components/GuidBadge'
import { clearInventoryCache } from '@/services/collections'
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
    fetchCollections,
    createCollection,
    updateCollection,
    deleteCollection,
    testCollection
  } = useCollections()

  const { connectors } = useConnectors()
  const { pipelines } = usePipelines()

  // KPI Stats for header (Issue #37)
  const { stats, refetch: refetchStats } = useCollectionStats()
  const { setStats } = useHeaderStats()

  // Callback to refresh collections when a collection_test job completes
  const handleJobComplete = useCallback((job: { tool: string }) => {
    if (job.tool === 'collection_test') {
      // Refresh collections list to show updated accessibility status
      fetchCollections(filters)
      refetchStats()
    }
  }, [fetchCollections, filters, refetchStats])

  // Tools hook for running analysis on collections
  // Enable WebSocket to receive job completion events
  const { runAllTools } = useTools({
    autoFetch: false,
    useWebSocket: true,
    onJobComplete: handleJobComplete
  })

  // Agent pool status for warning banner
  const { poolStatus } = useAgentPoolStatus()
  const noAgentsAvailable = poolStatus?.online_count === 0

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
        await updateCollection(editingCollection.guid, formData)
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

  const handleDelete = async (collection: Collection, force = false) => {
    await deleteCollection(collection.guid, force)
    // Refresh KPI stats after deleting a collection
    refetchStats()
  }

  const handleInfo = (collection: Collection) => {
    const toastId = toast.loading('Testing accessibility...', {
      description: collection.name,
    })
    testCollection(collection.guid)
      .then(() => {
        toast.success('Accessibility test complete', { id: toastId, description: collection.name })
      })
      .catch(() => {
        toast.error('Accessibility test failed', { id: toastId, description: collection.name })
      })
  }

  const handleRefresh = (collection: Collection) => {
    const toastId = toast.loading('Starting analysis...', {
      description: collection.name,
    })
    runAllTools(collection.guid, toastId).catch(() => {
      // Error toast already shown by runAllTools via toastId
    })
  }

  // T075: Refresh from Cloud - clear inventory cache then run all tools
  const handleRefreshFromCloud = async (collection: Collection) => {
    const toastId = toast.loading('Refreshing from cloud storage...', {
      description: collection.name,
    })
    try {
      // First, clear the inventory cache
      const result = await clearInventoryCache(collection.guid)
      if (result.cleared_count > 0) {
        toast.loading('Cache cleared, starting analysis...', {
          id: toastId,
          description: `${result.cleared_count.toLocaleString()} cached entries removed`,
        })
      }

      // Then run all tools (they will fetch fresh listings from cloud)
      await runAllTools(collection.guid, toastId)
    } catch (err: any) {
      const errorMessage = err.userMessage || err?.response?.data?.detail || 'Failed to refresh from cloud'
      toast.error('Refresh from Cloud failed', { id: toastId, description: errorMessage })
    }
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Action Row (Issue #67 - Single Title Pattern) */}
      <div className="flex justify-end">
        <Button onClick={() => handleOpen()} className="gap-2">
          <Plus className="h-4 w-4" />
          New Collection
        </Button>
      </div>

      {/* No Agents Warning (Issue #90 - T215) */}
      {noAgentsAvailable && (
        <Alert variant="warning">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>No agents available</AlertTitle>
          <AlertDescription>
            Analysis jobs require at least one agent to process. Jobs will remain queued until an agent becomes available.{' '}
            <Link to="/agents" className="underline hover:no-underline">
              Manage agents
            </Link>
          </AlertDescription>
        </Alert>
      )}

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
        onRefreshFromCloud={handleRefreshFromCloud}
        search={search}
      />

      {/* Create/Edit Dialog */}
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {editingCollection ? 'Edit Collection' : 'New Collection'}
            </DialogTitle>
            {editingCollection && (
              <DialogDescription asChild>
                <div className="pt-1">
                  <GuidBadge guid={editingCollection.guid} />
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
