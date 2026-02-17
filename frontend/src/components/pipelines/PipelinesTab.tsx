/**
 * PipelinesTab component
 *
 * Extracted from PipelinesPage for use within the Resources page.
 * Preserves all Pipeline functionality: list, CRUD, activate/deactivate,
 * set/unset default, validate graph, import/export, confirmation modals.
 * Manages own TopHeader stats via usePipelineStats.
 */

import React, { useEffect, useCallback, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
  AlertDialogAction,
} from '@/components/ui/alert-dialog'
import { useHeaderStats } from '@/contexts/HeaderStatsContext'
import { PipelineList } from '@/components/pipelines/PipelineList'
import { usePipelines, usePipelineStats, usePipelineExport, usePipelineImport } from '@/hooks/usePipelines'
import { useTools } from '@/hooks/useTools'
import type { PipelineSummary } from '@/contracts/api/pipelines-api'

export const PipelinesTab: React.FC = () => {
  const navigate = useNavigate()
  const { setStats } = useHeaderStats()
  const fileInputRef = useRef<HTMLInputElement>(null)

  // State
  const [confirmDelete, setConfirmDelete] = useState<PipelineSummary | null>(null)
  const [confirmActivate, setConfirmActivate] = useState<PipelineSummary | null>(null)
  const [confirmDeactivate, setConfirmDeactivate] = useState<PipelineSummary | null>(null)
  const [confirmSetDefault, setConfirmSetDefault] = useState<PipelineSummary | null>(null)
  const [confirmUnsetDefault, setConfirmUnsetDefault] = useState<PipelineSummary | null>(null)
  const [actionLoading, setActionLoading] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  // Hooks
  const {
    pipelines,
    loading,
    error,
    deletePipeline,
    activatePipeline,
    deactivatePipeline,
    setDefaultPipeline,
    unsetDefaultPipeline,
    refetch,
  } = usePipelines({ autoFetch: true })

  const { stats, refetch: refetchStats } = usePipelineStats(true)
  const { downloadYaml, downloading } = usePipelineExport()
  const { importYaml, importing } = usePipelineImport()
  const { runTool } = useTools()

  // Set header stats (TopHeader KPI pattern)
  useEffect(() => {
    if (stats) {
      setStats([
        { label: 'Total Pipelines', value: stats.total_pipelines },
        { label: 'Active', value: stats.active_pipeline_count },
        {
          label: 'Default Pipeline',
          value: stats.default_pipeline_name || 'None',
        },
      ])
    }
    return () => setStats([])
  }, [stats, setStats])

  // Handlers
  const handleCreateNew = useCallback(() => {
    navigate('/pipelines/new')
  }, [navigate])

  const handleImport = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  const handleFileChange = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0]
      if (!file) return

      try {
        setActionLoading(true)
        setActionError(null)
        const pipeline = await importYaml(file)
        await refetch()
        await refetchStats()
        navigate(`/pipelines/${pipeline.guid}`)
      } catch (err: any) {
        setActionError(err.userMessage || 'Failed to import pipeline')
      } finally {
        setActionLoading(false)
        // Reset file input
        if (fileInputRef.current) {
          fileInputRef.current.value = ''
        }
      }
    },
    [importYaml, refetch, refetchStats, navigate]
  )

  const handleEdit = useCallback(
    (pipeline: PipelineSummary) => {
      navigate(`/pipelines/${pipeline.guid}/edit`)
    },
    [navigate]
  )

  const handleView = useCallback(
    (pipeline: PipelineSummary) => {
      navigate(`/pipelines/${pipeline.guid}`)
    },
    [navigate]
  )

  const handleDeleteClick = useCallback((pipeline: PipelineSummary) => {
    setConfirmDelete(pipeline)
  }, [])

  const handleDeleteConfirm = useCallback(async () => {
    if (!confirmDelete) return

    try {
      setActionLoading(true)
      setActionError(null)
      await deletePipeline(confirmDelete.guid)
      await refetchStats()
      setConfirmDelete(null)
    } catch (err: any) {
      setActionError(err.userMessage || 'Failed to delete pipeline')
    } finally {
      setActionLoading(false)
    }
  }, [confirmDelete, deletePipeline, refetchStats])

  const handleActivateClick = useCallback((pipeline: PipelineSummary) => {
    setConfirmActivate(pipeline)
  }, [])

  const handleActivateConfirm = useCallback(async () => {
    if (!confirmActivate) return

    try {
      setActionLoading(true)
      setActionError(null)
      await activatePipeline(confirmActivate.guid)
      await refetchStats()
      setConfirmActivate(null)
    } catch (err: any) {
      setActionError(err.userMessage || 'Failed to activate pipeline')
    } finally {
      setActionLoading(false)
    }
  }, [confirmActivate, activatePipeline, refetchStats])

  const handleDeactivateClick = useCallback((pipeline: PipelineSummary) => {
    setConfirmDeactivate(pipeline)
  }, [])

  const handleDeactivateConfirm = useCallback(async () => {
    if (!confirmDeactivate) return

    try {
      setActionLoading(true)
      setActionError(null)
      await deactivatePipeline(confirmDeactivate.guid)
      await refetchStats()
      setConfirmDeactivate(null)
    } catch (err: any) {
      setActionError(err.userMessage || 'Failed to deactivate pipeline')
    } finally {
      setActionLoading(false)
    }
  }, [confirmDeactivate, deactivatePipeline, refetchStats])

  const handleSetDefaultClick = useCallback((pipeline: PipelineSummary) => {
    setConfirmSetDefault(pipeline)
  }, [])

  const handleSetDefaultConfirm = useCallback(async () => {
    if (!confirmSetDefault) return

    try {
      setActionLoading(true)
      setActionError(null)
      await setDefaultPipeline(confirmSetDefault.guid)
      await refetchStats()
      setConfirmSetDefault(null)
    } catch (err: any) {
      setActionError(err.userMessage || 'Failed to set default pipeline')
    } finally {
      setActionLoading(false)
    }
  }, [confirmSetDefault, setDefaultPipeline, refetchStats])

  const handleUnsetDefaultClick = useCallback((pipeline: PipelineSummary) => {
    setConfirmUnsetDefault(pipeline)
  }, [])

  const handleUnsetDefaultConfirm = useCallback(async () => {
    if (!confirmUnsetDefault) return

    try {
      setActionLoading(true)
      setActionError(null)
      await unsetDefaultPipeline(confirmUnsetDefault.guid)
      await refetchStats()
      setConfirmUnsetDefault(null)
    } catch (err: any) {
      setActionError(err.userMessage || 'Failed to remove default status')
    } finally {
      setActionLoading(false)
    }
  }, [confirmUnsetDefault, unsetDefaultPipeline, refetchStats])

  const handleExport = useCallback(
    async (pipeline: PipelineSummary) => {
      try {
        await downloadYaml(pipeline.guid)
      } catch (err: any) {
        setActionError(err.userMessage || 'Failed to export pipeline')
      }
    },
    [downloadYaml]
  )

  const handleValidateGraph = useCallback(
    async (pipeline: PipelineSummary) => {
      try {
        setActionLoading(true)
        setActionError(null)
        await runTool({
          tool: 'pipeline_validation',
          mode: 'display_graph',
          pipeline_guid: pipeline.guid,
        })
      } catch (err: any) {
        setActionError(err.userMessage || 'Failed to start pipeline validation')
      } finally {
        setActionLoading(false)
      }
    },
    [runTool]
  )

  return (
    <>
      {/* Hidden file input for import */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".yaml,.yml"
        onChange={handleFileChange}
        className="hidden"
      />

      {/* Error Alert */}
      {actionError && (
        <Alert variant="destructive" className="mb-4">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>{actionError}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setActionError(null)}
              className="ml-4 h-auto px-2 py-1"
            >
              Dismiss
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Pipeline List */}
      <PipelineList
        pipelines={pipelines}
        loading={loading || actionLoading || importing}
        error={error}
        onCreateNew={handleCreateNew}
        onImport={handleImport}
        onEdit={handleEdit}
        onDelete={handleDeleteClick}
        onActivate={handleActivateClick}
        onDeactivate={handleDeactivateClick}
        onSetDefault={handleSetDefaultClick}
        onUnsetDefault={handleUnsetDefaultClick}
        onExport={handleExport}
        onView={handleView}
        onValidateGraph={handleValidateGraph}
      />

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!confirmDelete} onOpenChange={(open) => !open && setConfirmDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Pipeline</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <strong>{confirmDelete?.name}</strong>?
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={actionLoading}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              disabled={actionLoading}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {actionLoading ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Activate Confirmation Dialog */}
      <AlertDialog open={!!confirmActivate} onOpenChange={(open) => !open && setConfirmActivate(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Activate Pipeline</AlertDialogTitle>
            <AlertDialogDescription>
              Activating <strong>{confirmActivate?.name}</strong> will mark it as
              ready for use. To use this pipeline for tool execution, set it as the
              default pipeline after activation.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={actionLoading}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleActivateConfirm} disabled={actionLoading}>
              {actionLoading ? 'Activating...' : 'Activate'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Deactivate Confirmation Dialog */}
      <AlertDialog open={!!confirmDeactivate} onOpenChange={(open) => !open && setConfirmDeactivate(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Deactivate Pipeline</AlertDialogTitle>
            <AlertDialogDescription>
              Deactivating <strong>{confirmDeactivate?.name}</strong> will mark it as
              not ready for use.
              {confirmDeactivate?.is_default && (
                <span className="block mt-2 text-warning">
                  <strong>Note:</strong> This pipeline is currently the default.
                  Deactivating it will also remove the default status.
                </span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={actionLoading}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeactivateConfirm}
              disabled={actionLoading}
              className="bg-warning text-warning-foreground hover:bg-warning/90"
            >
              {actionLoading ? 'Deactivating...' : 'Deactivate'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Set Default Confirmation Dialog */}
      <AlertDialog open={!!confirmSetDefault} onOpenChange={(open) => !open && setConfirmSetDefault(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Set as Default Pipeline</AlertDialogTitle>
            <AlertDialogDescription>
              Setting <strong>{confirmSetDefault?.name}</strong> as default will
              use it for all pipeline validation tool runs.
              {stats?.default_pipeline_name && stats.default_pipeline_guid !== confirmSetDefault?.guid && (
                <span className="block mt-2 text-warning">
                  <strong>Note:</strong> The current default pipeline &quot;{stats.default_pipeline_name}&quot;
                  will lose its default status.
                </span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={actionLoading}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleSetDefaultConfirm}
              disabled={actionLoading}
              className="bg-warning text-warning-foreground hover:bg-warning/90"
            >
              {actionLoading ? 'Setting...' : 'Set as Default'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Unset Default Confirmation Dialog */}
      <AlertDialog open={!!confirmUnsetDefault} onOpenChange={(open) => !open && setConfirmUnsetDefault(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove Default Status</AlertDialogTitle>
            <AlertDialogDescription>
              Removing default status from <strong>{confirmUnsetDefault?.name}</strong> will
              leave no default pipeline. Pipeline validation tool will not run without
              a default pipeline configured.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={actionLoading}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleUnsetDefaultConfirm}
              disabled={actionLoading}
              className="bg-warning text-warning-foreground hover:bg-warning/90"
            >
              {actionLoading ? 'Removing...' : 'Remove Default'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

    </>
  )
}

export default PipelinesTab
