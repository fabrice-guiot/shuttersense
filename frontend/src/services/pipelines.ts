/**
 * Pipelines API service
 *
 * Handles all API calls related to pipeline management
 */

import api from './api'
import { validateGuid } from '@/utils/guid'
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
 * Get pipeline details by GUID
 * @param guid - External ID (pip_xxx format)
 */
export const getPipeline = async (guid: string): Promise<Pipeline> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'pip'))
  const response = await api.get<Pipeline>(`/pipelines/${safeGuid}`)
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
 * @param guid - External ID (pip_xxx format)
 */
export const updatePipeline = async (guid: string, data: PipelineUpdateRequest): Promise<Pipeline> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'pip'))
  const response = await api.put<Pipeline>(`/pipelines/${safeGuid}`, data)
  return response.data
}

/**
 * Delete a pipeline
 * @param guid - External ID (pip_xxx format)
 */
export const deletePipeline = async (guid: string): Promise<PipelineDeleteResponse> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'pip'))
  const response = await api.delete<PipelineDeleteResponse>(`/pipelines/${safeGuid}`)
  return response.data
}

/**
 * Activate a pipeline for validation runs
 * @param guid - External ID (pip_xxx format)
 */
export const activatePipeline = async (guid: string): Promise<Pipeline> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'pip'))
  const response = await api.post<Pipeline>(`/pipelines/${safeGuid}/activate`)
  return response.data
}

/**
 * Deactivate a pipeline
 * @param guid - External ID (pip_xxx format)
 */
export const deactivatePipeline = async (guid: string): Promise<Pipeline> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'pip'))
  const response = await api.post<Pipeline>(`/pipelines/${safeGuid}/deactivate`)
  return response.data
}

/**
 * Set a pipeline as the default for tool execution
 * @param guid - External ID (pip_xxx format)
 */
export const setDefaultPipeline = async (guid: string): Promise<Pipeline> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'pip'))
  const response = await api.post<Pipeline>(`/pipelines/${safeGuid}/set-default`)
  return response.data
}

/**
 * Remove default status from a pipeline
 * @param guid - External ID (pip_xxx format)
 */
export const unsetDefaultPipeline = async (guid: string): Promise<Pipeline> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'pip'))
  const response = await api.post<Pipeline>(`/pipelines/${safeGuid}/unset-default`)
  return response.data
}

/**
 * Validate pipeline structure
 * @param guid - External ID (pip_xxx format)
 */
export const validatePipeline = async (guid: string): Promise<ValidationResult> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'pip'))
  const response = await api.post<ValidationResult>(`/pipelines/${safeGuid}/validate`)
  return response.data
}

/**
 * Preview expected filenames for a pipeline
 * @param guid - External ID (pip_xxx format)
 */
export const previewFilenames = async (
  guid: string,
  data: FilenamePreviewRequest = {}
): Promise<FilenamePreviewResponse> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'pip'))
  const response = await api.post<FilenamePreviewResponse>(`/pipelines/${safeGuid}/preview`, data)
  return response.data
}

/**
 * Get pipeline version history
 * @param guid - External ID (pip_xxx format)
 */
export const getPipelineHistory = async (guid: string): Promise<PipelineHistoryEntry[]> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'pip'))
  const response = await api.get<PipelineHistoryEntry[]>(`/pipelines/${safeGuid}/history`)
  return response.data
}

/**
 * Get a specific version of a pipeline
 * @param guid - External ID (pip_xxx format)
 */
export const getPipelineVersion = async (guid: string, version: number): Promise<Pipeline> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'pip'))
  const response = await api.get<Pipeline>(`/pipelines/${safeGuid}/versions/${version}`)
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
 * @param guid - External ID (pip_xxx format)
 */
export const getExportUrl = (guid: string): string => {
  // Validate GUID format and encode for URL safety
  const safeGuid = encodeURIComponent(validateGuid(guid, 'pip'))
  const baseUrl = api.defaults.baseURL || 'http://localhost:8000/api'
  return `${baseUrl}/pipelines/${safeGuid}/export`
}

/**
 * Download pipeline as YAML file
 * @param guid - External ID (pip_xxx format)
 */
export const downloadPipelineYaml = async (guid: string): Promise<{ blob: Blob; filename: string }> => {
  // Validate GUID format and encode for URL safety
  const safeGuid = encodeURIComponent(validateGuid(guid, 'pip'))
  const response = await api.get(`/pipelines/${safeGuid}/export`, {
    responseType: 'blob',
  })

  // Extract filename from Content-Disposition header
  const contentDisposition = response.headers['content-disposition']
  let filename = `pipeline_${guid}.yaml` // Fallback

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
 * @param guid - External ID (pip_xxx format)
 */
export const downloadPipelineVersionYaml = async (
  guid: string,
  version: number
): Promise<{ blob: Blob; filename: string }> => {
  // Validate GUID format and encode for URL safety
  const safeGuid = encodeURIComponent(validateGuid(guid, 'pip'))
  const response = await api.get(`/pipelines/${safeGuid}/versions/${version}/export`, {
    responseType: 'blob',
  })

  // Extract filename from Content-Disposition header
  const contentDisposition = response.headers['content-disposition']
  let filename = `pipeline_${guid}_v${version}.yaml` // Fallback

  if (contentDisposition) {
    const filenameMatch = contentDisposition.match(/filename="?([^";\n]+)"?/)
    if (filenameMatch && filenameMatch[1]) {
      filename = filenameMatch[1]
    }
  }

  return { blob: response.data, filename }
}
