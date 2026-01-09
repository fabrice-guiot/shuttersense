/**
 * Pipelines API service
 *
 * Handles all API calls related to pipeline management
 */

import api from './api'
import type {
  Pipeline,
  PipelineSummary,
  PipelineListResponse,
  PipelineCreateRequest,
  PipelineUpdateRequest,
  PipelineStatsResponse,
  PipelineDeleteResponse,
  PipelineListQueryParams,
  ValidationResult,
  FilenamePreviewRequest,
  FilenamePreviewResponse,
  PipelineHistoryEntry,
} from '@/contracts/api/pipelines-api'

/**
 * List all pipelines with optional filters
 */
export const listPipelines = async (params: PipelineListQueryParams = {}): Promise<PipelineSummary[]> => {
  const response = await api.get<PipelineListResponse>('/pipelines', { params })
  return response.data.items
}

/**
 * Get pipeline details by ID
 */
export const getPipeline = async (pipelineId: number): Promise<Pipeline> => {
  const response = await api.get<Pipeline>(`/pipelines/${pipelineId}`)
  return response.data
}

/**
 * Create a new pipeline
 */
export const createPipeline = async (data: PipelineCreateRequest): Promise<Pipeline> => {
  const response = await api.post<Pipeline>('/pipelines', data)
  return response.data
}

/**
 * Update an existing pipeline
 */
export const updatePipeline = async (pipelineId: number, data: PipelineUpdateRequest): Promise<Pipeline> => {
  const response = await api.put<Pipeline>(`/pipelines/${pipelineId}`, data)
  return response.data
}

/**
 * Delete a pipeline
 */
export const deletePipeline = async (pipelineId: number): Promise<PipelineDeleteResponse> => {
  const response = await api.delete<PipelineDeleteResponse>(`/pipelines/${pipelineId}`)
  return response.data
}

/**
 * Activate a pipeline for validation runs
 */
export const activatePipeline = async (pipelineId: number): Promise<Pipeline> => {
  const response = await api.post<Pipeline>(`/pipelines/${pipelineId}/activate`)
  return response.data
}

/**
 * Deactivate a pipeline
 */
export const deactivatePipeline = async (pipelineId: number): Promise<Pipeline> => {
  const response = await api.post<Pipeline>(`/pipelines/${pipelineId}/deactivate`)
  return response.data
}

/**
 * Set a pipeline as the default for tool execution
 */
export const setDefaultPipeline = async (pipelineId: number): Promise<Pipeline> => {
  const response = await api.post<Pipeline>(`/pipelines/${pipelineId}/set-default`)
  return response.data
}

/**
 * Remove default status from a pipeline
 */
export const unsetDefaultPipeline = async (pipelineId: number): Promise<Pipeline> => {
  const response = await api.post<Pipeline>(`/pipelines/${pipelineId}/unset-default`)
  return response.data
}

/**
 * Validate pipeline structure
 */
export const validatePipeline = async (pipelineId: number): Promise<ValidationResult> => {
  const response = await api.post<ValidationResult>(`/pipelines/${pipelineId}/validate`)
  return response.data
}

/**
 * Preview expected filenames for a pipeline
 */
export const previewFilenames = async (
  pipelineId: number,
  data: FilenamePreviewRequest = {}
): Promise<FilenamePreviewResponse> => {
  const response = await api.post<FilenamePreviewResponse>(`/pipelines/${pipelineId}/preview`, data)
  return response.data
}

/**
 * Get pipeline version history
 */
export const getPipelineHistory = async (pipelineId: number): Promise<PipelineHistoryEntry[]> => {
  const response = await api.get<PipelineHistoryEntry[]>(`/pipelines/${pipelineId}/history`)
  return response.data
}

/**
 * Get a specific version of a pipeline
 */
export const getPipelineVersion = async (pipelineId: number, version: number): Promise<Pipeline> => {
  const response = await api.get<Pipeline>(`/pipelines/${pipelineId}/versions/${version}`)
  return response.data
}

/**
 * Get pipeline statistics for KPIs
 */
export const getPipelineStats = async (): Promise<PipelineStatsResponse> => {
  const response = await api.get<PipelineStatsResponse>('/pipelines/stats')
  return response.data
}

/**
 * Import pipeline from YAML file
 */
export const importPipeline = async (file: File): Promise<Pipeline> => {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post<Pipeline>('/pipelines/import', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

/**
 * Get URL for downloading pipeline as YAML
 */
export const getExportUrl = (pipelineId: number): string => {
  const baseUrl = api.defaults.baseURL || 'http://localhost:8000/api'
  return `${baseUrl}/pipelines/${pipelineId}/export`
}

/**
 * Download pipeline as YAML file
 */
export const downloadPipelineYaml = async (pipelineId: number): Promise<{ blob: Blob; filename: string }> => {
  const response = await api.get(`/pipelines/${pipelineId}/export`, {
    responseType: 'blob',
  })

  // Extract filename from Content-Disposition header
  const contentDisposition = response.headers['content-disposition']
  let filename = `pipeline_${pipelineId}.yaml` // Fallback

  if (contentDisposition) {
    const filenameMatch = contentDisposition.match(/filename="?([^";\n]+)"?/)
    if (filenameMatch && filenameMatch[1]) {
      filename = filenameMatch[1]
    }
  }

  return { blob: response.data, filename }
}

/**
 * Download a specific version of a pipeline as YAML file
 */
export const downloadPipelineVersionYaml = async (
  pipelineId: number,
  version: number
): Promise<{ blob: Blob; filename: string }> => {
  const response = await api.get(`/pipelines/${pipelineId}/versions/${version}/export`, {
    responseType: 'blob',
  })

  // Extract filename from Content-Disposition header
  const contentDisposition = response.headers['content-disposition']
  let filename = `pipeline_${pipelineId}_v${version}.yaml` // Fallback

  if (contentDisposition) {
    const filenameMatch = contentDisposition.match(/filename="?([^";\n]+)"?/)
    if (filenameMatch && filenameMatch[1]) {
      filename = filenameMatch[1]
    }
  }

  return { blob: response.data, filename }
}
