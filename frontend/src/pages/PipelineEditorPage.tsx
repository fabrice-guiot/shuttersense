/**
 * PipelineEditorPage component
 *
 * View and edit photo processing pipelines
 * - View mode: /pipelines/:id (read-only)
 * - Edit mode: /pipelines/:id/edit or /pipelines/new
 */

import React, { useEffect, useState, useCallback, useRef } from 'react'
import { useNavigate, useParams, useLocation, useSearchParams } from 'react-router-dom'
import {
  GitBranch,
  Save,
  ArrowLeft,
  AlertTriangle,
  Pencil,
  CheckCircle,
  XCircle,
  Zap,
  Download,
  History,
  BarChart3,
} from 'lucide-react'
import { MainLayout } from '@/components/layout/MainLayout'
import { usePipeline, usePipelines, usePipelineExport } from '@/hooks/usePipelines'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type {
  PipelineNode,
  PipelineEdge,
  PipelineCreateRequest,
  PipelineUpdateRequest,
  ValidationResult,
} from '@/contracts/api/pipelines-api'
import { GuidBadge } from '@/components/GuidBadge'
import { AuditTrailSection } from '@/components/audit'
import { PipelineGraphView } from '@/components/pipelines/graph/PipelineGraphView'
import { PropertyPanel } from '@/components/pipelines/graph/PropertyPanel'
import { PipelineGraphEditor, type PipelineGraphEditorHandle } from '@/components/pipelines/graph/PipelineGraphEditor'
import { usePipelineAnalytics } from '@/hooks/usePipelineAnalytics'
import { ReactFlowProvider } from '@xyflow/react'

// ============================================================================
// Main Page Component
// ============================================================================

export const PipelineEditorPage: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { id } = useParams<{ id: string }>()

  // Determine mode from URL
  const isNew = id === 'new'
  const isEditMode = isNew || location.pathname.endsWith('/edit')
  const isViewMode = !isEditMode && id && id !== 'new'
  // Use string identifier directly (supports both numeric IDs and external IDs like pip_xxx)
  const pipelineId = !isNew && id ? id : null

  // Hooks
  const {
    pipeline,
    loading: loadingPipeline,
    currentVersion,
    latestVersion,
    history,
    loadVersion,
  } = usePipeline(pipelineId)
  const { createPipeline, updatePipeline, loading: saving } = usePipelines({ autoFetch: false })
  const { downloadYaml, downloading } = usePipelineExport()

  // Flow analytics: only loaded when navigating from a result detail (?result=res_xxx)
  const [searchParams, setSearchParams] = useSearchParams()
  const resultGuid = searchParams.get('result')
  const {
    analytics,
    loading: analyticsLoading,
    enabled: analyticsEnabled,
    error: analyticsError,
  } = usePipelineAnalytics(
    isViewMode && resultGuid ? pipelineId : null,
    resultGuid,
  )
  const showFlow = !!resultGuid && !!analytics
  // Analytics were requested but the result has no path_stats data
  const analyticsUnavailable = !!resultGuid && !analyticsLoading && !analyticsEnabled && !analyticsError

  // Determine if viewing a historical version
  const isHistoricalVersion = currentVersion !== null && latestVersion !== null && currentVersion < latestVersion

  // Form state (name, description, change summary are outside the graph editor)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [changeSummary, setChangeSummary] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)

  // Graph editor ref
  const editorRef = useRef<PipelineGraphEditorHandle>(null)

  // Graph view selection state (view mode only)
  const [selectedNode, setSelectedNode] = useState<PipelineNode | null>(null)
  const [selectedEdge, setSelectedEdge] = useState<PipelineEdge | null>(null)

  // Load existing pipeline data
  useEffect(() => {
    if (pipeline) {
      setName(pipeline.name)
      setDescription(pipeline.description || '')
    }
  }, [pipeline])

  // Save handler
  const handleSave = async () => {
    setError(null)
    setValidationResult(null)

    if (!name.trim()) {
      setError('Pipeline name is required')
      return
    }

    if (!editorRef.current) {
      setError('Editor not ready')
      return
    }

    const { nodes, edges } = editorRef.current.save()

    if (nodes.length === 0) {
      setError('Pipeline must have at least one node')
      return
    }

    try {
      if (pipelineId) {
        const updateData: PipelineUpdateRequest = {
          name,
          description: description || undefined,
          nodes,
          edges,
          change_summary: changeSummary || undefined,
        }
        await updatePipeline(pipelineId, updateData)
      } else {
        const createData: PipelineCreateRequest = {
          name,
          description: description || undefined,
          nodes,
          edges,
        }
        await createPipeline(createData)
      }
      navigate('/pipelines')
    } catch (err: any) {
      setError(err.userMessage || 'Failed to save pipeline')
    }
  }

  // Graph click handlers for view mode
  const handleGraphNodeClick = useCallback((nodeId: string) => {
    const node = pipeline?.nodes.find((n) => n.id === nodeId) ?? null
    setSelectedNode(node)
    setSelectedEdge(null)
  }, [pipeline])

  const handleGraphEdgeClick = useCallback((edgeId: string) => {
    const edge = pipeline?.edges.find((e) => `${e.from}-${e.to}` === edgeId) ?? null
    setSelectedEdge(edge)
    setSelectedNode(null)
  }, [pipeline])

  const handleClosePropertyPanel = useCallback(() => {
    setSelectedNode(null)
    setSelectedEdge(null)
  }, [])

  // Determine page title
  const pageTitle = isNew
    ? 'Create Pipeline'
    : isEditMode
    ? 'Edit Pipeline'
    : 'Pipeline Details'

  if (loadingPipeline && pipelineId) {
    return (
      <MainLayout pageTitle={pageTitle} pageIcon={GitBranch}>
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      </MainLayout>
    )
  }

  // ============================================================================
  // VIEW MODE
  // ============================================================================
  if (isViewMode && pipeline) {
    return (
      <MainLayout pageTitle="Pipeline Details" pageIcon={GitBranch}>
        {/* Historical version warning */}
        {isHistoricalVersion && latestVersion && (
          <Alert className="mb-4 border-amber-500/50 bg-amber-500/10">
            <History className="h-4 w-4 text-amber-500" />
            <AlertDescription className="text-amber-600 dark:text-amber-400">
              <strong>Viewing historical version {currentVersion}</strong> — The latest version is v{latestVersion}.{' '}
              <button
                className="underline font-medium hover:no-underline"
                onClick={() => loadVersion(latestVersion)}
              >
                View latest
              </button>
            </AlertDescription>
          </Alert>
        )}

        <div className="space-y-6">
          {/* Pipeline Header */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-foreground">{pipeline.name}</h2>
                  {pipeline.description && (
                    <p className="text-muted-foreground mt-1">{pipeline.description}</p>
                  )}
                  <div className="flex items-center gap-2 mt-3">
                    {pipeline.guid && (
                      <GuidBadge guid={pipeline.guid} />
                    )}
                    {pipeline.is_active && !isHistoricalVersion && (
                      <Badge variant="default" className="gap-1">
                        <Zap className="h-3 w-3" />
                        Active
                      </Badge>
                    )}
                    {pipeline.is_valid ? (
                      <Badge variant="outline" className="gap-1 border-green-500/50 text-green-600 dark:text-green-400">
                        <CheckCircle className="h-3 w-3" />
                        Valid
                      </Badge>
                    ) : (
                      <Badge variant="destructive" className="gap-1">
                        <XCircle className="h-3 w-3" />
                        Invalid
                      </Badge>
                    )}
                    {/* Version picker */}
                    {latestVersion && (
                      <div className="flex items-center gap-2">
                        <History className="h-4 w-4 text-muted-foreground" />
                        <Select
                          value={String(currentVersion)}
                          onValueChange={(v) => loadVersion(Number(v))}
                        >
                          <SelectTrigger className="w-32 h-7 text-sm">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {/* Always include current/latest version first */}
                            <SelectItem value={String(latestVersion)}>
                              v{latestVersion} (latest)
                            </SelectItem>
                            {/* Add historical versions from history */}
                            {history
                              .filter((h) => h.version < latestVersion)
                              .map((h) => (
                                <SelectItem key={h.version} value={String(h.version)}>
                                  v{h.version}
                                  {h.change_summary && (
                                    <span className="text-muted-foreground ml-1">
                                      - {h.change_summary.slice(0, 20)}
                                      {h.change_summary.length > 20 ? '...' : ''}
                                    </span>
                                  )}
                                </SelectItem>
                              ))}
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    onClick={() => pipelineId && currentVersion && downloadYaml(pipelineId, currentVersion)}
                    disabled={downloading}
                  >
                    <Download className="h-4 w-4 mr-2" />
                    {downloading ? 'Exporting...' : `Export YAML${isHistoricalVersion ? ` (v${currentVersion})` : ''}`}
                  </Button>
                  {!isHistoricalVersion && (
                    <Button onClick={() => navigate(`/pipelines/${id}/edit`)}>
                      <Pencil className="h-4 w-4 mr-2" />
                      Edit Pipeline
                    </Button>
                  )}
                </div>
              </div>

              {/* Audit Trail (Issue #120) */}
              <AuditTrailSection audit={pipeline.audit} />

              {/* Flow Analytics Context (shown when navigated from a result) */}
              {showFlow && analytics && (
                <>
                  <Separator className="my-4" />
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <BarChart3 className="h-4 w-4 text-muted-foreground" />
                      Flow Analytics
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-1 text-sm">
                      <div>
                        <span className="text-muted-foreground">Collection: </span>
                        <span className="font-medium">{analytics.collection_name || 'Unknown'}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Status: </span>
                        <span className="font-medium">
                          {analytics.result_status === 'COMPLETED' ? '● Completed' :
                           analytics.result_status === 'NO_CHANGE' ? '● No Change' :
                           analytics.result_status}
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Analyzed: </span>
                        <span className="font-medium">
                          {analytics.completed_at
                            ? new Date(analytics.completed_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
                            : new Date(analytics.result_created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                        </span>
                      </div>
                      <div className="flex gap-4">
                        <span>
                          <span className="text-muted-foreground">Records: </span>
                          <span className="font-medium">{analytics.total_records.toLocaleString()}</span>
                        </span>
                        {analytics.files_scanned != null && (
                          <span>
                            <span className="text-muted-foreground">Files: </span>
                            <span className="font-medium">{analytics.files_scanned.toLocaleString()}</span>
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* Validation Errors (View mode only) */}
          {!pipeline.is_valid && pipeline.validation_errors && pipeline.validation_errors.length > 0 && (
            <div className="bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 p-4 rounded-lg">
              <div className="flex items-center gap-2 font-medium mb-2 text-red-700 dark:text-red-400">
                <AlertTriangle className="h-4 w-4" />
                Validation Errors
              </div>
              <ul className="list-disc list-inside space-y-1 text-sm text-red-600 dark:text-red-300">
                {pipeline.validation_errors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          )}

          {analyticsLoading && resultGuid && (
            <div className="flex items-center gap-2 rounded-lg border bg-muted/50 px-4 py-2 text-sm text-muted-foreground">
              <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-primary" />
              Loading flow analytics...
            </div>
          )}
          {analyticsUnavailable && (
            <Alert className="border-amber-500/50 bg-amber-500/10">
              <AlertTriangle className="h-4 w-4 text-amber-500" />
              <AlertDescription className="flex items-center justify-between text-amber-600 dark:text-amber-400">
                <span>
                  No flow analytics available for result{' '}
                  <code className="rounded bg-amber-100 dark:bg-amber-900 px-1 py-0.5 text-xs font-mono">{resultGuid}</code>
                  {' '}&mdash; the result does not contain path statistics.
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto px-2 py-1 text-xs shrink-0"
                  onClick={() => {
                    searchParams.delete('result')
                    setSearchParams(searchParams)
                  }}
                >
                  Dismiss
                </Button>
              </AlertDescription>
            </Alert>
          )}
          {analyticsError && resultGuid && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription className="flex items-center justify-between">
                <span>Failed to load flow analytics: {analyticsError}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-auto px-2 py-1 text-xs shrink-0"
                  onClick={() => {
                    searchParams.delete('result')
                    setSearchParams(searchParams)
                  }}
                >
                  Dismiss
                </Button>
              </AlertDescription>
            </Alert>
          )}

          {/* Pipeline Graph + Property Panel */}
          <div className="flex h-[600px] border rounded-lg overflow-hidden bg-background">
            <div className="relative flex-1 min-w-0">
              <PipelineGraphView
                nodes={pipeline.nodes}
                edges={pipeline.edges}
                validationErrors={pipeline.is_valid ? null : pipeline.validation_errors}
                onNodeClick={handleGraphNodeClick}
                onEdgeClick={handleGraphEdgeClick}
                analytics={showFlow ? analytics : undefined}
                showFlow={showFlow}
              />
            </div>
            {(selectedNode || selectedEdge) && (
              <PropertyPanel
                node={selectedNode}
                edge={selectedEdge}
                nodes={pipeline.nodes}
                mode="view"
                onClose={handleClosePropertyPanel}
              />
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center justify-between py-4">
            <Button variant="outline" onClick={() => navigate('/pipelines')}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Pipelines
            </Button>
            {!isHistoricalVersion && (
              <Button onClick={() => navigate(`/pipelines/${id}/edit`)}>
                <Pencil className="h-4 w-4 mr-2" />
                Edit Pipeline
              </Button>
            )}
          </div>
        </div>
      </MainLayout>
    )
  }

  // ============================================================================
  // EDIT/CREATE MODE
  // ============================================================================

  // Initial graph data for the editor
  const initialNodes = pipeline?.nodes ?? []
  const initialEdges = pipeline?.edges ?? []

  return (
    <MainLayout pageTitle={pageTitle} pageIcon={GitBranch}>
      {/* Error Alert */}
      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>{error}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setError(null)}
              className="h-auto p-1"
            >
              Dismiss
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Validation Result */}
      {validationResult && !validationResult.is_valid && (
        <Alert className="mb-4 border-orange-500/50 bg-orange-500/10">
          <AlertTriangle className="h-4 w-4 text-orange-500" />
          <AlertDescription>
            <div className="font-medium text-orange-600 dark:text-orange-400 mb-2">
              Validation Errors
            </div>
            <ul className="list-disc list-inside space-y-1 text-sm">
              {validationResult.errors.map((err, i) => (
                <li key={i}>{err.message}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      <div className="flex flex-col gap-4 h-[calc(100vh-8rem)]">
        {/* Basic Info + Actions Bar */}
        <Card className="shrink-0">
          <CardContent className="py-3">
            <div className="flex items-end gap-4">
              <div className="flex-1 space-y-1">
                <Label htmlFor="name" className="text-xs">
                  Name <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Standard RAW Pipeline"
                  className="h-8"
                />
              </div>
              <div className="flex-1 space-y-1">
                <Label htmlFor="description" className="text-xs">Description</Label>
                <Input
                  id="description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional description"
                  className="h-8"
                />
              </div>
              {pipelineId && (
                <div className="flex-1 space-y-1">
                  <Label htmlFor="changeSummary" className="text-xs">Change Summary</Label>
                  <Input
                    id="changeSummary"
                    value={changeSummary}
                    onChange={(e) => setChangeSummary(e.target.value)}
                    placeholder="Describe what changed"
                    className="h-8"
                  />
                </div>
              )}
              {pipeline?.guid && (
                <GuidBadge guid={pipeline.guid} />
              )}
              <div className="flex items-center gap-2 shrink-0">
                <Button variant="outline" size="sm" onClick={() => navigate('/pipelines')}>
                  <ArrowLeft className="h-4 w-4 mr-1" />
                  Cancel
                </Button>
                <Button size="sm" onClick={handleSave} disabled={saving}>
                  {saving ? (
                    <>
                      <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-primary-foreground mr-1.5" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4 mr-1" />
                      {pipelineId ? 'Save' : 'Create'}
                    </>
                  )}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Graph Editor */}
        <div className="flex-1 min-h-0 border rounded-lg overflow-hidden bg-background">
          <ReactFlowProvider>
            <PipelineGraphEditor
              ref={editorRef}
              initialNodes={initialNodes}
              initialEdges={initialEdges}
              onDirtyChange={() => {}}
            />
          </ReactFlowProvider>
        </div>
      </div>
    </MainLayout>
  )
}

export default PipelineEditorPage
