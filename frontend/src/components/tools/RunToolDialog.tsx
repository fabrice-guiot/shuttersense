/**
 * Run Tool Dialog Component
 *
 * Dialog for selecting and running analysis tools on collections or pipelines.
 * Supports two modes for Pipeline Validation:
 * - Collection mode: Validate files in a collection against a pipeline
 * - Display Graph mode: Validate pipeline definition only (no collection needed)
 */

import { useState, useEffect } from 'react'
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
import type { ToolType, ToolMode, ToolRunRequest } from '@/contracts/api/tools-api'
import type { Collection } from '@/contracts/api/collection-api'
import type { PipelineSummary } from '@/contracts/api/pipelines-api'

// ============================================================================
// Types
// ============================================================================

interface RunToolDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  collections: Collection[]
  pipelines: PipelineSummary[]
  onRunTool: (request: ToolRunRequest) => Promise<void>
  preSelectedCollectionId?: number
  preSelectedPipelineId?: number
  preSelectedMode?: ToolMode
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

// Mode display information
const MODE_INFO: Record<ToolMode, { label: string; description: string }> = {
  collection: {
    label: 'Validate Collection',
    description: 'Validate files in a collection against the pipeline'
  },
  display_graph: {
    label: 'Validate Pipeline Graph',
    description: 'Analyze pipeline definition and enumerate all paths (no collection needed)'
  }
}

// ============================================================================
// Component
// ============================================================================

export function RunToolDialog({
  open,
  onOpenChange,
  collections,
  pipelines,
  onRunTool,
  preSelectedCollectionId,
  preSelectedPipelineId,
  preSelectedMode
}: RunToolDialogProps) {
  // Form state - Tool selection comes first
  const [selectedTool, setSelectedTool] = useState<ToolType | null>(null)
  const [selectedMode, setSelectedMode] = useState<ToolMode | null>(null)
  const [selectedCollectionId, setSelectedCollectionId] = useState<number | null>(null)
  const [selectedPipelineId, setSelectedPipelineId] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Reset state when dialog opens with pre-selected values
  useEffect(() => {
    if (open) {
      // If pipeline is pre-selected, default to pipeline_validation with display_graph mode
      if (preSelectedPipelineId) {
        setSelectedTool('pipeline_validation')
        setSelectedMode(preSelectedMode ?? 'display_graph')
        setSelectedPipelineId(preSelectedPipelineId)
        setSelectedCollectionId(null)
      } else if (preSelectedCollectionId) {
        setSelectedTool(null)
        setSelectedMode(null)
        setSelectedCollectionId(preSelectedCollectionId)
        setSelectedPipelineId(null)
      } else {
        setSelectedTool(null)
        setSelectedMode(null)
        setSelectedCollectionId(null)
        setSelectedPipelineId(null)
      }
      setError(null)
    }
  }, [open, preSelectedCollectionId, preSelectedPipelineId, preSelectedMode])

  // When tool changes, reset mode and related selections
  const handleToolChange = (tool: ToolType) => {
    setSelectedTool(tool)
    setError(null)

    if (tool === 'pipeline_validation') {
      // Default to display_graph mode for pipeline validation
      setSelectedMode('display_graph')
    } else {
      setSelectedMode(null)
    }
  }

  // When mode changes, clear the appropriate selector
  const handleModeChange = (mode: ToolMode) => {
    setSelectedMode(mode)
    setError(null)

    if (mode === 'display_graph') {
      setSelectedCollectionId(null)
    } else {
      setSelectedPipelineId(null)
    }
  }

  const handleRun = async () => {
    if (!selectedTool) {
      setError('Please select a tool')
      return
    }

    // Validate based on tool and mode
    if (selectedTool === 'pipeline_validation') {
      if (selectedMode === 'display_graph') {
        if (!selectedPipelineId) {
          setError('Please select a pipeline')
          return
        }
      } else {
        // Collection mode
        if (!selectedCollectionId) {
          setError('Please select a collection')
          return
        }
      }
    } else {
      // PhotoStats and Photo Pairing require collection
      if (!selectedCollectionId) {
        setError('Please select a collection')
        return
      }
    }

    setLoading(true)
    setError(null)

    try {
      const request: ToolRunRequest = {
        tool: selectedTool
      }

      if (selectedTool === 'pipeline_validation' && selectedMode === 'display_graph') {
        request.mode = 'display_graph'
        request.pipeline_id = selectedPipelineId!
      } else {
        request.collection_id = selectedCollectionId!
        if (selectedTool === 'pipeline_validation') {
          request.mode = 'collection'
        }
      }

      await onRunTool(request)
      onOpenChange(false)
    } catch (err: any) {
      setError(err.userMessage || err.message || 'Failed to start tool')
    } finally {
      setLoading(false)
    }
  }

  const selectedToolInfo = selectedTool ? TOOL_INFO[selectedTool] : null
  const selectedModeInfo = selectedMode ? MODE_INFO[selectedMode] : null

  // Only show accessible collections - tools can only run on accessible collections
  const accessibleCollections = collections.filter((c) => c.is_accessible)
  const hasNoAccessibleCollections = accessibleCollections.length === 0 && collections.length > 0

  // Only show active and valid pipelines for display_graph mode
  const validPipelines = pipelines.filter((p) => p.is_active && p.is_valid)
  const hasNoValidPipelines = validPipelines.length === 0 && pipelines.length > 0

  // Determine if mode selector should be shown
  const showModeSelector = selectedTool === 'pipeline_validation'

  // Determine if collection or pipeline selector should be shown
  const showCollectionSelector = selectedTool && (
    selectedTool !== 'pipeline_validation' ||
    selectedMode === 'collection'
  )
  const showPipelineSelector = selectedTool === 'pipeline_validation' && selectedMode === 'display_graph'

  // Determine if Run button should be enabled
  const canRun = selectedTool && (
    (showPipelineSelector && selectedPipelineId) ||
    (showCollectionSelector && selectedCollectionId)
  )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Play className="h-5 w-5" />
            Run Analysis Tool
          </DialogTitle>
          <DialogDescription>
            Select a tool and target to analyze your photos
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          {/* Tool Select (First) */}
          <div className="grid gap-2">
            <Label htmlFor="tool">Tool</Label>
            <Select
              value={selectedTool ?? ''}
              onValueChange={(value) => handleToolChange(value as ToolType)}
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

          {/* Mode Select (Only for Pipeline Validation) */}
          {showModeSelector && (
            <div className="grid gap-2">
              <Label htmlFor="mode">Mode</Label>
              <Select
                value={selectedMode ?? ''}
                onValueChange={(value) => handleModeChange(value as ToolMode)}
              >
                <SelectTrigger id="mode">
                  <SelectValue placeholder="Select a mode" />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(MODE_INFO).map(([key, info]) => (
                    <SelectItem key={key} value={key}>
                      {info.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedModeInfo && (
                <p className="text-sm text-muted-foreground">
                  {selectedModeInfo.description}
                </p>
              )}
            </div>
          )}

          {/* Collection Select (for PhotoStats, Photo Pairing, and Pipeline Validation collection mode) */}
          {showCollectionSelector && (
            <div className="grid gap-2">
              <Label htmlFor="collection">Collection</Label>
              {hasNoAccessibleCollections && (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    No accessible collections available. Please verify your collection paths.
                  </AlertDescription>
                </Alert>
              )}
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
          )}

          {/* Pipeline Select (for Pipeline Validation display_graph mode) */}
          {showPipelineSelector && (
            <div className="grid gap-2">
              <Label htmlFor="pipeline">Pipeline</Label>
              {hasNoValidPipelines && (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    No valid and active pipelines available. Please create or activate a pipeline first.
                  </AlertDescription>
                </Alert>
              )}
              <Select
                value={selectedPipelineId?.toString() ?? ''}
                onValueChange={(value) => setSelectedPipelineId(parseInt(value, 10))}
                disabled={validPipelines.length === 0}
              >
                <SelectTrigger id="pipeline">
                  <SelectValue placeholder={
                    validPipelines.length === 0
                      ? "No valid pipelines"
                      : "Select a pipeline"
                  } />
                </SelectTrigger>
                <SelectContent>
                  {validPipelines.map((pipeline) => (
                    <SelectItem key={pipeline.id} value={pipeline.id.toString()}>
                      {pipeline.name} (v{pipeline.version})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

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
            disabled={loading || !canRun}
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
