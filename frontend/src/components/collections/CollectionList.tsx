import { useState, useMemo } from 'react'
import { FolderCheck, FolderSync, Edit, Trash2, Search } from 'lucide-react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table'
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { CollectionStatus } from './CollectionStatus'
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
  search,
  className
}: CollectionListProps) {
  const [deleteDialog, setDeleteDialog] = useState<{
    open: boolean
    collection: Collection | null
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

  const handleDeleteConfirm = () => {
    if (deleteDialog.collection) {
      onDelete(deleteDialog.collection)
      setDeleteDialog({ open: false, collection: null })
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

  const renderTable = (tabCollections: Collection[]) => {
    if (tabCollections.length === 0) {
      return (
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
    }

    return (
      <div className="rounded-md border border-border overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>State</TableHead>
              <TableHead>Pipeline</TableHead>
              <TableHead>Location</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tabCollections.map((collection) => (
              <TableRow key={collection.guid}>
                <TableCell className="font-medium">{collection.name}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">
                      {COLLECTION_TYPE_LABELS[collection.type]}
                    </Badge>
                    {isBetaCollectionType(collection.type) && <BetaChip />}
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant={COLLECTION_STATE_BADGE_VARIANT[collection.state]}>
                    {COLLECTION_STATE_LABELS[collection.state]}
                  </Badge>
                </TableCell>
                <TableCell>
                  {collection.pipeline_name ? (
                    <span className="text-sm" title={`v${collection.pipeline_version}`}>
                      {collection.pipeline_name}
                      <span className="text-muted-foreground text-xs ml-1">
                        v{collection.pipeline_version}
                      </span>
                    </span>
                  ) : (
                    <span className="text-muted-foreground text-sm">Using default</span>
                  )}
                </TableCell>
                <TableCell className="max-w-xs truncate" title={collection.location}>
                  {collection.location}
                </TableCell>
                <TableCell>
                  <CollectionStatus collection={collection} />
                </TableCell>
                <TableCell>
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
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    )
  }

  return (
    <>
      <div className={cn('flex flex-col gap-4', className)}>
        {/* Tabs and Table */}
        <Tabs defaultValue="all" className="w-full">
          <TabsList>
            {COLLECTION_TABS.map((tab) => (
              <TabsTrigger key={tab.id} value={tab.id}>
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>

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
            <DialogTitle>Delete Collection</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{deleteDialog.collection?.name}"?
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={handleDeleteCancel}>
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
