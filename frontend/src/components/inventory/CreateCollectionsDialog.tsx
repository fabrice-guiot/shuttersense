/**
 * CreateCollectionsDialog Component
 *
 * Two-step wizard for creating collections from inventory folders:
 * - Step 1: Select folders from tree (with hierarchy constraints)
 * - Step 2: Review and configure (names, states, batch actions)
 *
 * Issue #107: Cloud Storage Bucket Inventory Import
 * Task: T050, T051, T052, T053, T054, T055
 */

import { useState, useMemo, useCallback } from 'react'
import { Plus, ArrowLeft, ArrowRight, Loader2, CheckCircle2, AlertCircle } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import type {
  InventoryFolder,
  CollectionState,
  DraftCollection,
  FolderToCollectionMapping,
  CreateCollectionsFromInventoryResponse
} from '@/contracts/api/inventory-api'
import { createCollectionsFromInventory } from '@/services/inventory'
import { FolderTree } from './FolderTree'
import { suggestCollectionName, formatPathForDisplay, validateCollectionName } from '@/utils/name-suggestion'

// ============================================================================
// Types
// ============================================================================

export interface CreateCollectionsDialogProps {
  /** Connector GUID */
  connectorGuid: string
  /** Available folders from inventory */
  folders: InventoryFolder[]
  /** Whether folders are loading */
  foldersLoading?: boolean
  /** Called when collections are created */
  onCreated?: (result: CreateCollectionsFromInventoryResponse) => void
  /** Function to create collections (injected for flexibility) */
  createCollections?: (
    connectorGuid: string,
    mappings: FolderToCollectionMapping[]
  ) => Promise<CreateCollectionsFromInventoryResponse>
  /** Trigger element (defaults to "Create Collections" button) */
  trigger?: React.ReactNode
  /** Controlled mode: dialog open state */
  open?: boolean
  /** Controlled mode: callback when open state changes */
  onOpenChange?: (open: boolean) => void
}

type WizardStep = 'select' | 'review'

const COLLECTION_STATES: { value: CollectionState; label: string; description: string }[] = [
  { value: 'live', label: 'Live', description: 'Active collection for analysis' },
  { value: 'archived', label: 'Archived', description: 'Preserved but inactive' },
  { value: 'closed', label: 'Closed', description: 'Subject to retention policy' }
]

// ============================================================================
// Component
// ============================================================================

export function CreateCollectionsDialog({
  connectorGuid,
  folders,
  foldersLoading = false,
  onCreated,
  createCollections,
  trigger,
  open: controlledOpen,
  onOpenChange
}: CreateCollectionsDialogProps) {
  // Dialog state - support both controlled and uncontrolled modes
  const [internalOpen, setInternalOpen] = useState(false)
  const isControlled = controlledOpen !== undefined
  const open = isControlled ? controlledOpen : internalOpen
  const setOpen = isControlled ? (onOpenChange ?? (() => {})) : setInternalOpen
  const [step, setStep] = useState<WizardStep>('select')

  // Selection state (preserved across steps)
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set())

  // Draft collections for review step
  const [drafts, setDrafts] = useState<DraftCollection[]>([])

  // Batch state for "Set all states" action
  const [batchState, setBatchState] = useState<CollectionState | ''>('')

  // Submission state
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CreateCollectionsFromInventoryResponse | null>(null)

  // Get mapped paths for disabling in tree
  const mappedPaths = useMemo(() => {
    const paths = new Set<string>()
    for (const folder of folders) {
      if (folder.collection_guid) {
        paths.add(folder.path)
      }
    }
    return paths
  }, [folders])

  // Build folder lookup map
  const folderMap = useMemo(() => {
    const map = new Map<string, InventoryFolder>()
    for (const folder of folders) {
      map.set(folder.path, folder)
    }
    return map
  }, [folders])

  // Initialize drafts when moving to review step
  const initializeDrafts = useCallback(() => {
    const newDrafts: DraftCollection[] = []

    for (const path of selectedPaths) {
      const folder = folderMap.get(path)
      if (folder) {
        newDrafts.push({
          folder_guid: folder.guid,
          folder_path: path,
          name: suggestCollectionName(path),
          state: 'live', // Default state
          pipeline_guid: null
        })
      }
    }

    // Sort by path for consistent order
    newDrafts.sort((a, b) => a.folder_path.localeCompare(b.folder_path))
    setDrafts(newDrafts)
  }, [selectedPaths, folderMap])

  // Handle selection change
  const handleSelectionChange = useCallback((paths: Set<string>) => {
    setSelectedPaths(paths)
  }, [])

  // Navigate to review step
  const handleContinue = useCallback(() => {
    initializeDrafts()
    setStep('review')
    setError(null)
  }, [initializeDrafts])

  // Navigate back to selection step
  const handleBack = useCallback(() => {
    setStep('select')
    setError(null)
    // Note: drafts are preserved so user doesn't lose edits
  }, [])

  // Update a single draft
  const updateDraft = useCallback(
    (folderGuid: string, updates: Partial<DraftCollection>) => {
      setDrafts(prev =>
        prev.map(d => (d.folder_guid === folderGuid ? { ...d, ...updates } : d))
      )
    },
    []
  )

  // Apply batch state
  const applyBatchState = useCallback((state: CollectionState) => {
    setDrafts(prev => prev.map(d => ({ ...d, state })))
    setBatchState(state)
  }, [])

  // Validate all drafts
  const validationErrors = useMemo(() => {
    const errors: Map<string, string[]> = new Map()

    for (const draft of drafts) {
      const nameErrors = validateCollectionName(draft.name)
      if (nameErrors.length > 0) {
        errors.set(draft.folder_guid, nameErrors)
      }
    }

    return errors
  }, [drafts])

  const hasValidationErrors = validationErrors.size > 0
  const canSubmit = drafts.length > 0 && !hasValidationErrors

  // Submit collection creation
  const handleSubmit = useCallback(async () => {
    if (!canSubmit) return

    setSubmitting(true)
    setError(null)

    try {
      const mappings: FolderToCollectionMapping[] = drafts.map(d => ({
        folder_guid: d.folder_guid,
        name: d.name.trim(),
        state: d.state,
        pipeline_guid: d.pipeline_guid
      }))

      const createFn = createCollections ?? createCollectionsFromInventory
      const response = await createFn(connectorGuid, mappings)
      setResult(response)

      // If all succeeded, notify and close
      if (response.errors.length === 0) {
        onCreated?.(response)
        // Don't close immediately - show success state
      }
    } catch (err: any) {
      setError(err.userMessage || err.message || 'Failed to create collections')
    } finally {
      setSubmitting(false)
    }
  }, [canSubmit, drafts, connectorGuid, createCollections, onCreated])

  // Reset state when dialog closes
  const handleOpenChange = useCallback((isOpen: boolean) => {
    setOpen(isOpen)
    if (!isOpen) {
      // Reset all state
      setTimeout(() => {
        setStep('select')
        setSelectedPaths(new Set())
        setDrafts([])
        setBatchState('')
        setError(null)
        setResult(null)
      }, 200) // After close animation
    }
  }, [])

  // Close after success
  const handleDone = useCallback(() => {
    handleOpenChange(false)
  }, [handleOpenChange])

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      {/* Only render trigger in uncontrolled mode (when parent doesn't control open state) */}
      {!isControlled && (
        <DialogTrigger asChild>
          {trigger || (
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create Collections
            </Button>
          )}
        </DialogTrigger>
      )}

      <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>
            {result
              ? 'Collections Created'
              : step === 'select'
                ? 'Select Folders'
                : 'Configure Collections'}
          </DialogTitle>
          <DialogDescription>
            {result
              ? `${result.created.length} collection${result.created.length !== 1 ? 's' : ''} created successfully`
              : step === 'select'
                ? 'Choose folders to create as collections. Nested selections are not allowed.'
                : 'Review and customize collection names and states before creating.'}
          </DialogDescription>
        </DialogHeader>

        {/* Step Indicator */}
        {!result && (
          <div className="flex items-center gap-2 py-2">
            <Badge variant={step === 'select' ? 'default' : 'outline'}>
              1. Select Folders
            </Badge>
            <div className="h-px w-8 bg-border" />
            <Badge variant={step === 'review' ? 'default' : 'outline'}>
              2. Review & Configure
            </Badge>
          </div>
        )}

        <Separator />

        {/* Content */}
        <div className="flex-1 overflow-hidden py-4">
          {result ? (
            // Success/Result View
            <div className="space-y-4">
              {result.created.length > 0 && (
                <Alert>
                  <CheckCircle2 className="h-4 w-4 text-success" />
                  <AlertDescription>
                    Successfully created {result.created.length} collection
                    {result.created.length !== 1 ? 's' : ''}.
                  </AlertDescription>
                </Alert>
              )}

              {result.errors.length > 0 && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    {result.errors.length} collection
                    {result.errors.length !== 1 ? 's' : ''} failed to create:
                    <ul className="mt-2 list-disc list-inside">
                      {result.errors.map(e => (
                        <li key={e.folder_guid}>{e.error}</li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}

              {result.created.length > 0 && (
                <ScrollArea className="h-48">
                  <div className="space-y-2">
                    {result.created.map(c => (
                      <div
                        key={c.collection_guid}
                        className="flex items-center gap-2 p-2 bg-muted/50 rounded"
                      >
                        <CheckCircle2 className="h-4 w-4 text-success flex-shrink-0" />
                        <span className="font-medium">{c.name}</span>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              )}
            </div>
          ) : step === 'select' ? (
            // Step 1: Folder Selection
            <FolderTree
              folders={folders}
              loading={foldersLoading}
              mappedPaths={mappedPaths}
              onSelectionChange={handleSelectionChange}
              initialSelection={selectedPaths}
              maxHeight={350}
            />
          ) : (
            // Step 2: Review & Configure
            <div className="space-y-4">
              {/* Batch Actions */}
              <div className="flex items-center gap-4 p-3 bg-muted/50 rounded-md">
                <Label className="text-sm font-medium">Set all states:</Label>
                <Select
                  value={batchState}
                  onValueChange={value => applyBatchState(value as CollectionState)}
                >
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Select state" />
                  </SelectTrigger>
                  <SelectContent>
                    {COLLECTION_STATES.map(s => (
                      <SelectItem key={s.value} value={s.value}>
                        {s.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Error Display */}
              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {/* Draft List */}
              <ScrollArea className="h-[300px] pr-4">
                <div className="space-y-4">
                  {drafts.map(draft => {
                    const errors = validationErrors.get(draft.folder_guid)
                    return (
                      <div
                        key={draft.folder_guid}
                        className="p-4 border rounded-lg space-y-3"
                      >
                        {/* Path (readonly) */}
                        <div className="text-xs text-muted-foreground font-mono">
                          {formatPathForDisplay(draft.folder_path, 80)}
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          {/* Name Input */}
                          <div className="space-y-1.5">
                            <Label htmlFor={`name-${draft.folder_guid}`}>
                              Collection Name
                            </Label>
                            <Input
                              id={`name-${draft.folder_guid}`}
                              value={draft.name}
                              onChange={e =>
                                updateDraft(draft.folder_guid, { name: e.target.value })
                              }
                              className={errors ? 'border-destructive' : ''}
                            />
                            {errors && (
                              <p className="text-xs text-destructive">{errors[0]}</p>
                            )}
                          </div>

                          {/* State Select */}
                          <div className="space-y-1.5">
                            <Label htmlFor={`state-${draft.folder_guid}`}>
                              State
                            </Label>
                            <Select
                              value={draft.state}
                              onValueChange={value =>
                                updateDraft(draft.folder_guid, {
                                  state: value as CollectionState
                                })
                              }
                            >
                              <SelectTrigger id={`state-${draft.folder_guid}`}>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {COLLECTION_STATES.map(s => (
                                  <SelectItem key={s.value} value={s.value}>
                                    <div>
                                      <span>{s.label}</span>
                                      <span className="text-xs text-muted-foreground ml-2">
                                        {s.description}
                                      </span>
                                    </div>
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </ScrollArea>
            </div>
          )}
        </div>

        <Separator />

        {/* Footer Actions */}
        <DialogFooter>
          {result ? (
            <Button onClick={handleDone}>Done</Button>
          ) : step === 'select' ? (
            <>
              <Button variant="outline" onClick={() => handleOpenChange(false)}>
                Cancel
              </Button>
              <Button onClick={handleContinue} disabled={selectedPaths.size === 0}>
                Continue
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={handleBack}>
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
              <Button
                onClick={handleSubmit}
                disabled={!canSubmit || submitting}
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    Create {drafts.length} Collection
                    {drafts.length !== 1 ? 's' : ''}
                  </>
                )}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
