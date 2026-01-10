/**
 * usePipelines React hook
 *
 * Manages pipeline state with fetch, create, update, delete, and activation operations
 */

import { useState, useEffect, useCallback } from 'react'
import * as pipelinesService from '../services/pipelines'
import type {
  Pipeline,
  PipelineSummary,
  PipelineCreateRequest,
  PipelineUpdateRequest,
  PipelineListQueryParams,
  PipelineStatsResponse,
  ValidationResult,
  FilenamePreviewRequest,
  FilenamePreviewResponse,
  PipelineHistoryEntry,
} from '@/contracts/api/pipelines-api'

// ============================================================================
// Main Pipelines Hook
// ============================================================================

interface UsePipelinesOptions {
  autoFetch?: boolean
}

interface UsePipelinesReturn {
  pipelines: PipelineSummary[]
  loading: boolean
  error: string | null
  fetchPipelines: (params?: PipelineListQueryParams) => Promise<void>
  createPipeline: (data: PipelineCreateRequest) => Promise<Pipeline>
  updatePipeline: (guid: string, data: PipelineUpdateRequest) => Promise<Pipeline>
  deletePipeline: (guid: string) => Promise<void>
  activatePipeline: (guid: string) => Promise<Pipeline>
  deactivatePipeline: (guid: string) => Promise<Pipeline>
  setDefaultPipeline: (guid: string) => Promise<Pipeline>
  unsetDefaultPipeline: (guid: string) => Promise<Pipeline>
  refetch: () => Promise<void>
}

export const usePipelines = (options: UsePipelinesOptions = {}): UsePipelinesReturn => {
  const { autoFetch = true } = options

  const [pipelines, setPipelines] = useState<PipelineSummary[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastParams, setLastParams] = useState<PipelineListQueryParams>({})

  /**
   * Fetch pipelines with given parameters
   */
  const fetchPipelines = useCallback(async (params: PipelineListQueryParams = {}) => {
    setLoading(true)
    setError(null)
    setLastParams(params)
    try {
      const data = await pipelinesService.listPipelines(params)
      setPipelines(data)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load pipelines'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Create a new pipeline
   */
  const createPipeline = useCallback(async (data: PipelineCreateRequest): Promise<Pipeline> => {
    setLoading(true)
    setError(null)
    try {
      const pipeline = await pipelinesService.createPipeline(data)
      return pipeline
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to create pipeline'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Update an existing pipeline
   */
  const updatePipeline = useCallback(async (
    guid: string,
    data: PipelineUpdateRequest
  ): Promise<Pipeline> => {
    setLoading(true)
    setError(null)
    try {
      const pipeline = await pipelinesService.updatePipeline(guid, data)
      return pipeline
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to update pipeline'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Delete a pipeline
   */
  const deletePipeline = useCallback(async (guid: string) => {
    setLoading(true)
    setError(null)
    try {
      await pipelinesService.deletePipeline(guid)
      setPipelines((prev) => prev.filter((p) => p.guid !== guid))
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to delete pipeline'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Activate a pipeline (multiple can be active)
   */
  const activatePipeline = useCallback(async (guid: string): Promise<Pipeline> => {
    setLoading(true)
    setError(null)
    try {
      const pipeline = await pipelinesService.activatePipeline(guid)
      // Update local state to reflect activation (only this pipeline changes)
      setPipelines((prev) =>
        prev.map((p) => p.guid === guid ? { ...p, is_active: true } : p)
      )
      return pipeline
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to activate pipeline'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Deactivate a pipeline (also clears default status if it was default)
   */
  const deactivatePipeline = useCallback(async (guid: string): Promise<Pipeline> => {
    setLoading(true)
    setError(null)
    try {
      const pipeline = await pipelinesService.deactivatePipeline(guid)
      // Update local state to reflect deactivation (also clears default)
      setPipelines((prev) =>
        prev.map((p) => p.guid === guid ? { ...p, is_active: false, is_default: false } : p)
      )
      return pipeline
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to deactivate pipeline'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Set a pipeline as the default (only one can be default)
   */
  const setDefaultPipeline = useCallback(async (guid: string): Promise<Pipeline> => {
    setLoading(true)
    setError(null)
    try {
      const pipeline = await pipelinesService.setDefaultPipeline(guid)
      // Update local state - unset previous default, set new default
      setPipelines((prev) =>
        prev.map((p) => ({ ...p, is_default: p.guid === guid }))
      )
      return pipeline
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to set default pipeline'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Remove default status from a pipeline
   */
  const unsetDefaultPipeline = useCallback(async (guid: string): Promise<Pipeline> => {
    setLoading(true)
    setError(null)
    try {
      const pipeline = await pipelinesService.unsetDefaultPipeline(guid)
      // Update local state to reflect removal of default status
      setPipelines((prev) =>
        prev.map((p) => p.guid === guid ? { ...p, is_default: false } : p)
      )
      return pipeline
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to remove default status'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Refetch with last parameters
   */
  const refetch = useCallback(async () => {
    await fetchPipelines(lastParams)
  }, [fetchPipelines, lastParams])

  // Initial fetch
  useEffect(() => {
    if (autoFetch) {
      fetchPipelines()
    }
  }, [autoFetch, fetchPipelines])

  return {
    pipelines,
    loading,
    error,
    fetchPipelines,
    createPipeline,
    updatePipeline,
    deletePipeline,
    activatePipeline,
    deactivatePipeline,
    setDefaultPipeline,
    unsetDefaultPipeline,
    refetch,
  }
}

// ============================================================================
// Single Pipeline Hook
// ============================================================================

interface UsePipelineReturn {
  pipeline: Pipeline | null
  loading: boolean
  error: string | null
  currentVersion: number | null
  latestVersion: number | null
  history: PipelineHistoryEntry[]
  historyLoading: boolean
  refetch: () => Promise<void>
  validate: () => Promise<ValidationResult>
  preview: (data?: FilenamePreviewRequest) => Promise<FilenamePreviewResponse>
  getHistory: () => Promise<PipelineHistoryEntry[]>
  loadVersion: (version: number) => Promise<void>
}

export const usePipeline = (pipelineId: string | null): UsePipelineReturn => {
  const [pipeline, setPipeline] = useState<Pipeline | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentVersion, setCurrentVersion] = useState<number | null>(null)
  const [latestVersion, setLatestVersion] = useState<number | null>(null)
  const [history, setHistory] = useState<PipelineHistoryEntry[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)

  const refetch = useCallback(async () => {
    if (!pipelineId) {
      setPipeline(null)
      setCurrentVersion(null)
      setLatestVersion(null)
      return
    }

    setLoading(true)
    setError(null)
    try {
      const data = await pipelinesService.getPipeline(pipelineId)
      setPipeline(data)
      setCurrentVersion(data.version)
      setLatestVersion(data.version)  // Track latest version separately
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load pipeline'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [pipelineId])

  const validate = useCallback(async (): Promise<ValidationResult> => {
    if (!pipelineId) {
      throw new Error('No pipeline ID')
    }
    return pipelinesService.validatePipeline(pipelineId)
  }, [pipelineId])

  const preview = useCallback(
    async (data: FilenamePreviewRequest = {}): Promise<FilenamePreviewResponse> => {
      if (!pipelineId) {
        throw new Error('No pipeline ID')
      }
      return pipelinesService.previewFilenames(pipelineId, data)
    },
    [pipelineId]
  )

  const getHistory = useCallback(async (): Promise<PipelineHistoryEntry[]> => {
    if (!pipelineId) {
      throw new Error('No pipeline ID')
    }
    setHistoryLoading(true)
    try {
      const historyData = await pipelinesService.getPipelineHistory(pipelineId)
      setHistory(historyData)
      return historyData
    } finally {
      setHistoryLoading(false)
    }
  }, [pipelineId])

  const loadVersion = useCallback(async (version: number) => {
    if (!pipelineId) {
      throw new Error('No pipeline ID')
    }
    setLoading(true)
    setError(null)
    try {
      const data = await pipelinesService.getPipelineVersion(pipelineId, version)
      setPipeline(data)
      setCurrentVersion(version)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load pipeline version'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [pipelineId])

  useEffect(() => {
    refetch()
  }, [refetch])

  // Load history when pipeline loads
  useEffect(() => {
    if (pipelineId && pipeline) {
      getHistory()
    }
  }, [pipelineId, pipeline, getHistory])

  return {
    pipeline,
    loading,
    error,
    currentVersion,
    latestVersion,
    history,
    historyLoading,
    refetch,
    validate,
    preview,
    getHistory,
    loadVersion,
  }
}

// ============================================================================
// Pipeline Stats Hook (for KPIs)
// ============================================================================

interface UsePipelineStatsReturn {
  stats: PipelineStatsResponse | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

export const usePipelineStats = (autoFetch = true): UsePipelineStatsReturn => {
  const [stats, setStats] = useState<PipelineStatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await pipelinesService.getPipelineStats()
      setStats(data)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load pipeline statistics'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (autoFetch) {
      refetch()
    }
  }, [autoFetch, refetch])

  return { stats, loading, error, refetch }
}

// ============================================================================
// Pipeline YAML Export Hook
// ============================================================================

interface UsePipelineExportReturn {
  downloading: boolean
  error: string | null
  downloadYaml: (guid: string, version?: number) => Promise<void>
  getExportUrl: (guid: string) => string
}

export const usePipelineExport = (): UsePipelineExportReturn => {
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const downloadYaml = useCallback(async (guid: string, version?: number) => {
    setDownloading(true)
    setError(null)
    try {
      // Use version-specific download if version is provided
      const { blob, filename } = version !== undefined
        ? await pipelinesService.downloadPipelineVersionYaml(guid, version)
        : await pipelinesService.downloadPipelineYaml(guid)

      // Create download link
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()

      // Cleanup
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to download pipeline'
      setError(errorMessage)
      throw err
    } finally {
      setDownloading(false)
    }
  }, [])

  const getExportUrl = useCallback((guid: string) => {
    return pipelinesService.getExportUrl(guid)
  }, [])

  return {
    downloading,
    error,
    downloadYaml,
    getExportUrl,
  }
}

// ============================================================================
// Pipeline Import Hook
// ============================================================================

interface UsePipelineImportReturn {
  importing: boolean
  error: string | null
  importYaml: (file: File) => Promise<Pipeline>
}

export const usePipelineImport = (): UsePipelineImportReturn => {
  const [importing, setImporting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const importYaml = useCallback(async (file: File): Promise<Pipeline> => {
    setImporting(true)
    setError(null)
    try {
      const pipeline = await pipelinesService.importPipeline(file)
      return pipeline
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to import pipeline'
      setError(errorMessage)
      throw err
    } finally {
      setImporting(false)
    }
  }, [])

  return {
    importing,
    error,
    importYaml,
  }
}
