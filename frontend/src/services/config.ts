/**
 * Configuration API service
 *
 * Handles all API calls related to configuration management including
 * CRUD operations, YAML import/export, and statistics.
 */

import api from './api'
import type {
  ConfigurationResponse,
  CategoryConfigResponse,
  ConfigValueResponse,
  ConfigStatsResponse,
  ImportSessionResponse,
  ImportResultResponse,
  ConfigCategory,
  ConfigValueUpdateRequest,
  ConflictResolutionRequest
} from '@/contracts/api/config-api'

/**
 * Get all configuration
 */
export const getConfiguration = async (): Promise<ConfigurationResponse> => {
  const response = await api.get<ConfigurationResponse>('/config')
  return response.data
}

/**
 * Get configuration for a specific category
 */
export const getCategoryConfig = async (
  category: ConfigCategory
): Promise<CategoryConfigResponse> => {
  const response = await api.get<CategoryConfigResponse>(`/config/${category}`)
  return response.data
}

/**
 * Get a specific configuration value
 */
export const getConfigValue = async (
  category: ConfigCategory,
  key: string
): Promise<ConfigValueResponse> => {
  const response = await api.get<ConfigValueResponse>(`/config/${category}/${key}`)
  return response.data
}

/**
 * Create a configuration value
 */
export const createConfigValue = async (
  category: ConfigCategory,
  key: string,
  data: ConfigValueUpdateRequest
): Promise<ConfigValueResponse> => {
  const response = await api.post<ConfigValueResponse>(
    `/config/${category}/${key}`,
    data
  )
  return response.data
}

/**
 * Update a configuration value
 */
export const updateConfigValue = async (
  category: ConfigCategory,
  key: string,
  data: ConfigValueUpdateRequest
): Promise<ConfigValueResponse> => {
  const response = await api.put<ConfigValueResponse>(
    `/config/${category}/${key}`,
    data
  )
  return response.data
}

/**
 * Delete a configuration value
 */
export const deleteConfigValue = async (
  category: ConfigCategory,
  key: string
): Promise<void> => {
  await api.delete(`/config/${category}/${key}`)
}

/**
 * Get configuration statistics (KPIs)
 */
export const getConfigStats = async (): Promise<ConfigStatsResponse> => {
  const response = await api.get<ConfigStatsResponse>('/config/stats')
  return response.data
}

/**
 * Start YAML import with conflict detection
 */
export const startImport = async (file: File): Promise<ImportSessionResponse> => {
  const formData = new FormData()
  formData.append('file', file)
  const response = await api.post<ImportSessionResponse>('/config/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return response.data
}

/**
 * Get import session status
 */
export const getImportSession = async (
  sessionId: string
): Promise<ImportSessionResponse> => {
  const response = await api.get<ImportSessionResponse>(`/config/import/${sessionId}`)
  return response.data
}

/**
 * Resolve conflicts and apply import
 */
export const resolveImport = async (
  sessionId: string,
  request: ConflictResolutionRequest
): Promise<ImportResultResponse> => {
  const response = await api.post<ImportResultResponse>(
    `/config/import/${sessionId}/resolve`,
    request
  )
  return response.data
}

/**
 * Cancel an import session
 */
export const cancelImport = async (sessionId: string): Promise<void> => {
  await api.post(`/config/import/${sessionId}/cancel`)
}

/**
 * Export configuration as YAML file
 */
export const exportConfiguration = async (): Promise<Blob> => {
  const response = await api.get('/config/export', {
    responseType: 'blob'
  })
  return response.data
}
