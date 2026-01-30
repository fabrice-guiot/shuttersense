import { useState, useMemo } from 'react'
import { FolderCheck, FolderSync, Edit, Trash2, Search, Bot, CloudDownload, TrendingUp, TrendingDown, ArrowRight } from 'lucide-react'
import { ResponsiveTable, type ColumnDef } from '@/components/ui/responsive-table'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger
} from '@/components/ui/tooltip'
import { Tabs, TabsContent, TabsTrigger } from '@/components/ui/tabs'
import { ResponsiveTabsList, type TabOption } from '@/components/ui/responsive-tabs-list'
import { CollectionStatus } from './CollectionStatus'
import { formatRelativeTime } from '@/utils/dateFormat'
import type { CollectionListProps } from '@/contracts/components/collection-components'
import type { Collection, CollectionType } from '@/contracts/api/collection-api'
import {
  COLLECTION_TYPE_LABELS,
  COLLECTION_STATE_LABELS,
  COLLECTION_STATE_BADGE_VARIANT,
  COLLECTION_TABS
} from '@/contracts/components/collection-components'
import { cn } from '@/lib/utils'

// Collection types still in beta/QA - remove from this set once QA'd
const BETA_COLLECTION_TYPES: Set<CollectionType> = new Set(['gcs', 'smb'])

function isBetaCollectionType(type: CollectionType): boolean {
  return BETA_COLLECTION_TYPES.has(type)
}

// Beta chip component for consistent styling
function BetaChip() {
  return (
    <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
      Beta
    </span>
  )
}

/**
 * Collection list component
 * Displays collections in a table with actions and tab navigation
 * Filtering is now handled via API (server-side) through useCollections hook
 */
export function CollectionList({
  collections,
  loading,
  onEdit,
  onDelete,
  onRefresh,
  onInfo,
  onRefreshFromCloud,
  search,
  className
}: CollectionListProps) {
  const [activeTab, setActiveTab] = useState('all')
  const [deleteDialog, setDeleteDialog] = useState<{
    open: boolean
    collection: Collection | null
    forceDelete?: boolean
    resultCount?: number
    jobCount?: number
  }>({ open: false, collection: null })

  // Filter collections by tab (client-side tab filtering only)
  const filteredCollections = useMemo(() => {
    return {
      all: collections,
      recent: [...collections]
        .filter((c) => c.last_scanned_at !== null)
        .sort((a, b) => {
          const dateA = new Date(a.last_scanned_at!).getTime()
          const dateB = new Date(b.last_scanned_at!).getTime()
          return dateB - dateA
        }),
      archived: collections.filter((c) => c.state === 'archived')
    }
  }, [collections])

  const handleDeleteClick = (collection: Collection) => {
    setDeleteDialog({ open: true, collection })
  }

  const handleDeleteConfirm = async () => {
    if (!deleteDialog.collection) return

    try {
      // If force delete is already requested, pass true
      await onDelete(deleteDialog.collection, deleteDialog.forceDelete)
      setDeleteDialog({ open: false, collection: null })
    } catch (err: any) {
      // Check if error is about existing results/jobs
      const errorMessage = err?.userMessage || err?.message || ''
      const resultMatch = errorMessage.match(/(\d+) analysis result\(s\)/)
      const jobMatch = errorMessage.match(/(\d+) active job\(s\)/)

      if (resultMatch || jobMatch) {
        // Show force-delete confirmation dialog
        setDeleteDialog({
          ...deleteDialog,
          forceDelete: true,
          resultCount: resultMatch ? parseInt(resultMatch[1], 10) : 0,
          jobCount: jobMatch ? parseInt(jobMatch[1], 10) : 0
        })
      }
      // If it's a different error, the hook will show a toast
    }
  }

  const handleDeleteCancel = () => {
    setDeleteDialog({ open: false, collection: null })
  }

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <div
          role="status"
          className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"
        />
      </div>
    )
  }

  const emptyState = (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      {search ? (
        <>
          <Search className="h-10 w-10 text-muted-foreground mb-3" />
          <p className="text-muted-foreground">
            No collections matching "{search}"
          </p>
          <p className="text-sm text-muted-foreground mt-1">
            Try a different search term or clear the search
          </p>
        </>
      ) : (
        <p className="text-muted-foreground">No collections found</p>
      )}
    </div>
  )

  const columns: ColumnDef<Collection>[] = [
    {
      header: 'Name',
      cell: (collection) => collection.name,
      cellClassName: 'font-medium',
      cardRole: 'title',
    },
    {
      header: 'Type',
      cell: (collection) => (
        <div className="flex items-center gap-2">
          <Badge variant="secondary">
            {COLLECTION_TYPE_LABELS[collection.type]}
          </Badge>
          {isBetaCollectionType(collection.type) && <BetaChip />}
        </div>
      ),
      cardRole: 'badge',
    },
    {
      header: 'Agent',
      cell: (collection) =>
        collection.bound_agent ? (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex items-center gap-1.5">
                  <Bot className="h-3.5 w-3.5 text-muted-foreground" />
                  <span
                    className={cn(
                      'h-2 w-2 rounded-full',
                      collection.bound_agent.status === 'online'
                        ? 'bg-green-500'
                        : collection.bound_agent.status === 'offline'
                          ? 'bg-gray-400'
                          : 'bg-red-500'
                    )}
                  />
                  <span className="text-sm truncate max-w-[100px]">
                    {collection.bound_agent.name}
                  </span>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <div className="text-xs">
                  <div className="font-medium">{collection.bound_agent.name}</div>
                  <div className="text-muted-foreground capitalize">
                    Status: {collection.bound_agent.status}
                  </div>
                </div>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ) : collection.type === 'local' ? (
          <span className="text-muted-foreground text-sm">Any agent</span>
        ) : (
          <span className="text-muted-foreground text-sm">-</span>
        ),
      cardRole: 'detail',
    },
    {
      header: 'State',
      cell: (collection) => (
        <Badge variant={COLLECTION_STATE_BADGE_VARIANT[collection.state]}>
          {COLLECTION_STATE_LABELS[collection.state]}
        </Badge>
      ),
      cardRole: 'badge',
    },
    {
      header: 'Pipeline',
      cell: (collection) =>
        collection.pipeline_name ? (
          <span className="text-sm" title={`v${collection.pipeline_version}`}>
            {collection.pipeline_name}
            <span className="text-muted-foreground text-xs ml-1">
              v{collection.pipeline_version}
            </span>
          </span>
        ) : (
          <span className="text-muted-foreground text-sm">Using default</span>
        ),
      cardRole: 'detail',
    },
    {
      header: 'Location',
      cell: (collection) => (
        <span className="max-w-xs truncate" title={collection.location}>
          {collection.location}
        </span>
      ),
      cellClassName: 'max-w-xs truncate',
      cardRole: 'subtitle',
    },
    {
      header: 'Inventory',
      cell: (collection) =>
        collection.type === 'local' ? (
          <span className="text-muted-foreground text-sm">-</span>
        ) : collection.file_info?.updated_at ? (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="text-sm cursor-default inline-flex items-center gap-1">
                  {formatRelativeTime(collection.file_info.updated_at)}
                  {collection.file_info.delta && (
                    (() => {
                      const delta = collection.file_info.delta
                      const netChange = delta.new_count - delta.deleted_count
                      if (delta.is_first_import || netChange > 0) {
                        return <TrendingUp className="h-3.5 w-3.5 text-success" />
                      } else if (netChange < 0) {
                        return <TrendingDown className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
                      } else {
                        return <ArrowRight className="h-3.5 w-3.5 text-info" />
                      }
                    })()
                  )}
                </span>
              </TooltipTrigger>
              <TooltipContent>
                <div className="text-xs space-y-1">
                  <div>
                    {collection.file_info.count.toLocaleString()} files cached
                  </div>
                  <div className="text-muted-foreground">
                    Source: {collection.file_info.source === 'inventory' ? 'Bucket Inventory' : 'Cloud API'}
                  </div>
                  {collection.file_info.delta && (
                    <div className="border-t border-border pt-1 mt-1">
                      <div className="font-medium">Last import changes:</div>
                      {collection.file_info.delta.is_first_import ? (
                        <div className="text-success">
                          First import ({collection.file_info.delta.new_count.toLocaleString()} files)
                        </div>
                      ) : collection.file_info.delta.total_changes > 0 ? (
                        <div className="space-y-0.5">
                          {collection.file_info.delta.new_count > 0 && (
                            <div className="text-success">
                              +{collection.file_info.delta.new_count.toLocaleString()} new
                            </div>
                          )}
                          {collection.file_info.delta.modified_count > 0 && (
                            <div className="text-amber-600 dark:text-amber-400">
                              ~{collection.file_info.delta.modified_count.toLocaleString()} modified
                            </div>
                          )}
                          {collection.file_info.delta.deleted_count > 0 && (
                            <div className="text-destructive">
                              -{collection.file_info.delta.deleted_count.toLocaleString()} deleted
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="text-muted-foreground">No changes detected</div>
                      )}
                    </div>
                  )}
                </div>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ) : (
          <span className="text-muted-foreground text-sm">Not imported</span>
        ),
      cardRole: 'detail',
    },
    {
      header: 'Status',
      cell: (collection) => <CollectionStatus collection={collection} />,
      cardRole: 'detail',
    },
    {
      header: 'Actions',
      headerClassName: 'text-right',
      cell: (collection) => (
        <div className="flex justify-end gap-1">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => onInfo(collection)}
                  aria-label="Test Accessibility"
                >
                  <FolderCheck className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Test Accessibility</TooltipContent>
            </Tooltip>
          </TooltipProvider>

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => onRefresh(collection)}
                  aria-label="Refresh Collection"
                >
                  <FolderSync className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Refresh Collection</TooltipContent>
            </Tooltip>
          </TooltipProvider>

          {collection.type !== 'local' && onRefreshFromCloud && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => onRefreshFromCloud(collection)}
                    aria-label="Refresh from Cloud Storage"
                  >
                    <CloudDownload className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Refresh from Cloud Storage</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => onEdit(collection)}
                  aria-label="Edit Collection"
                >
                  <Edit className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Edit Collection</TooltipContent>
            </Tooltip>
          </TooltipProvider>

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handleDeleteClick(collection)}
                  aria-label="Delete Collection"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Delete Collection</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      ),
      cardRole: 'action',
    },
  ]

  const renderTable = (tabCollections: Collection[]) => (
    <ResponsiveTable
      data={tabCollections}
      columns={columns}
      keyField="guid"
      emptyState={emptyState}
    />
  )

  return (
    <>
      <div className={cn('flex flex-col gap-4', className)}>
        {/* Tabs and Table */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <ResponsiveTabsList
            tabs={COLLECTION_TABS.map((tab): TabOption => ({ value: tab.id, label: tab.label }))}
            value={activeTab}
            onValueChange={setActiveTab}
          >
            {COLLECTION_TABS.map((tab) => (
              <TabsTrigger key={tab.id} value={tab.id}>
                {tab.label}
              </TabsTrigger>
            ))}
          </ResponsiveTabsList>

          <TabsContent value="all" className="mt-4">
            {renderTable(filteredCollections.all)}
          </TabsContent>

          <TabsContent value="recent" className="mt-4">
            {renderTable(filteredCollections.recent)}
          </TabsContent>

          <TabsContent value="archived" className="mt-4">
            {renderTable(filteredCollections.archived)}
          </TabsContent>
        </Tabs>
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialog.open} onOpenChange={handleDeleteCancel}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {deleteDialog.forceDelete ? 'Confirm Deletion with Data' : 'Delete Collection'}
            </DialogTitle>
            <DialogDescription>
              {deleteDialog.forceDelete ? (
                <>
                  <span className="font-medium text-destructive">
                    "{deleteDialog.collection?.name}" has existing data:
                  </span>
                  <ul className="mt-2 list-disc list-inside text-sm">
                    {(deleteDialog.resultCount ?? 0) > 0 && (
                      <li>{deleteDialog.resultCount} analysis result(s)</li>
                    )}
                    {(deleteDialog.jobCount ?? 0) > 0 && (
                      <li>{deleteDialog.jobCount} active job(s)</li>
                    )}
                  </ul>
                  <p className="mt-2">
                    Deleting this collection will permanently remove all associated data.
                    This action cannot be undone.
                  </p>
                </>
              ) : (
                <>
                  Are you sure you want to delete "{deleteDialog.collection?.name}"?
                  This action cannot be undone.
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={handleDeleteCancel}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteConfirm}>
              {deleteDialog.forceDelete ? 'Delete Everything' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
