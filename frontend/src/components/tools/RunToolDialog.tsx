/**
 * Run Tool Dialog Component
 *
 * Dialog for selecting and running analysis tools on collections
 */

import { useState } from 'react'
import { Play, AlertCircle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import type { ToolType, ToolRunRequest } from '@/contracts/api/tools-api'
import type { Collection } from '@/contracts/api/collection-api'

// ============================================================================
// Types
// ============================================================================

interface RunToolDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  collections: Collection[]
  onRunTool: (request: ToolRunRequest) => Promise<void>
  preSelectedCollectionId?: number
}

// Tool display information
const TOOL_INFO: Record<ToolType, { label: string; description: string }> = {
  photostats: {
    label: 'PhotoStats',
    description: 'Analyze photo collection for orphaned files and sidecar issues'
  },
  photo_pairing: {
    label: 'Photo Pairing',
    description: 'Analyze filename patterns, group files, and track camera usage'
  },
  pipeline_validation: {
    label: 'Pipeline Validation',
    description: 'Validate files against a defined pipeline'
  }
}

// ============================================================================
// Component
// ============================================================================

export function RunToolDialog({
  open,
  onOpenChange,
  collections,
  onRunTool,
  preSelectedCollectionId
}: RunToolDialogProps) {
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(
    preSelectedCollectionId ?? null
  )
  const [selectedTool, setSelectedTool] = useState<ToolType | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Reset state when dialog opens
  const handleOpenChange = (newOpen: boolean) => {
    if (newOpen) {
      setSelectedCollectionId(preSelectedCollectionId ?? null)
      setSelectedTool(null)
      setError(null)
    }
    onOpenChange(newOpen)
  }

  const handleRun = async () => {
    if (!selectedCollectionId || !selectedTool) {
      setError('Please select both a collection and a tool')
      return
    }

    // Pipeline validation requires pipeline_id (not implemented yet)
    if (selectedTool === 'pipeline_validation') {
      setError('Pipeline validation requires selecting a pipeline (coming soon)')
      return
    }

    setLoading(true)
    setError(null)

    try {
      await onRunTool({
        collection_id: selectedCollectionId,
        tool: selectedTool
      })
      onOpenChange(false)
    } catch (err: any) {
      setError(err.userMessage || err.message || 'Failed to start tool')
    } finally {
      setLoading(false)
    }
  }

  const selectedToolInfo = selectedTool ? TOOL_INFO[selectedTool] : null

  // Only show accessible collections - tools can only run on accessible collections
  const accessibleCollections = collections.filter((c) => c.is_accessible)
  const hasNoAccessibleCollections = accessibleCollections.length === 0 && collections.length > 0

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Play className="h-5 w-5" />
            Run Analysis Tool
          </DialogTitle>
          <DialogDescription>
            Select a collection and tool to analyze your photos
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          {/* Warning if no accessible collections */}
          {hasNoAccessibleCollections && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                No accessible collections available. Please verify your collection paths
                and use the "Test Connection" action on the Collections page to update their status.
              </AlertDescription>
            </Alert>
          )}

          {/* Collection Select */}
          <div className="grid gap-2">
            <Label htmlFor="collection">Collection</Label>
            <Select
              value={selectedCollectionId?.toString() ?? ''}
              onValueChange={(value) => setSelectedCollectionId(parseInt(value, 10))}
              disabled={accessibleCollections.length === 0}
            >
              <SelectTrigger id="collection">
                <SelectValue placeholder={
                  accessibleCollections.length === 0
                    ? "No accessible collections"
                    : "Select a collection"
                } />
              </SelectTrigger>
              <SelectContent>
                {accessibleCollections.map((collection) => (
                  <SelectItem key={collection.id} value={collection.id.toString()}>
                    {collection.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Tool Select */}
          <div className="grid gap-2">
            <Label htmlFor="tool">Tool</Label>
            <Select
              value={selectedTool ?? ''}
              onValueChange={(value) => setSelectedTool(value as ToolType)}
            >
              <SelectTrigger id="tool">
                <SelectValue placeholder="Select a tool" />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(TOOL_INFO).map(([key, info]) => (
                  <SelectItem key={key} value={key}>
                    {info.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selectedToolInfo && (
              <p className="text-sm text-muted-foreground">
                {selectedToolInfo.description}
              </p>
            )}
          </div>

          {/* Error Alert */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button
            onClick={handleRun}
            disabled={loading || !selectedCollectionId || !selectedTool}
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Run Tool
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
