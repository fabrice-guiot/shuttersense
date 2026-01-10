/**
 * Results API service
 *
 * Handles all API calls related to analysis results
 */

import api from './api'
import { validateGuid } from '@/utils/guid'
import type {
  AnalysisResult,
  ResultListResponse,
  ResultListQueryParams,
  ResultStatsResponse,
  ResultDeleteResponse
} from '@/contracts/api/results-api'

/**
 * List analysis results with optional filters
 */
export const listResults = async (params: ResultListQueryParams = {}): Promise<ResultListResponse> => {
  const response = await api.get<ResultListResponse>('/results', { params })
  return response.data
}

/**
 * Get analysis result details
 * @param guid - External ID (res_xxx format)
 */
export const getResult = async (guid: string): Promise<AnalysisResult> => {
  // Validate GUID format and encode for URL safety
  const safeGuid = encodeURIComponent(validateGuid(guid, 'res'))
  const response = await api.get<AnalysisResult>(`/results/${safeGuid}`)
  return response.data
}

/**
 * Delete an analysis result
 * @param guid - External ID (res_xxx format)
 */
export const deleteResult = async (guid: string): Promise<ResultDeleteResponse> => {
  // Validate GUID format and encode for URL safety
  const safeGuid = encodeURIComponent(validateGuid(guid, 'res'))
  const response = await api.delete<ResultDeleteResponse>(`/results/${safeGuid}`)
  return response.data
}

/**
 * Get URL for downloading HTML report
 * Returns the full URL that can be used for downloading
 * @param guid - External ID (res_xxx format)
 */
export const getReportUrl = (guid: string): string => {
  // Validate GUID format and encode for URL safety
  const safeGuid = encodeURIComponent(validateGuid(guid, 'res'))
  const baseUrl = api.defaults.baseURL || 'http://localhost:8000/api'
  return `${baseUrl}/results/${safeGuid}/report`
}

/**
 * Download HTML report as blob with filename from Content-Disposition header
 * Returns both the blob and the server-provided filename
 * @param guid - External ID (res_xxx format)
 */
export const downloadReport = async (guid: string): Promise<{ blob: Blob; filename: string }> => {
  // Validate GUID format and encode for URL safety
  const safeGuid = encodeURIComponent(validateGuid(guid, 'res'))
  const response = await api.get(`/results/${safeGuid}/report`, {
    responseType: 'blob'
  })

  // Extract filename from Content-Disposition header
  // Format: attachment; filename="photostats_report_collection_1_2024-01-15_10-30-00.html"
  const contentDisposition = response.headers['content-disposition']
  let filename = `report_${guid}.html` // Fallback

  if (contentDisposition) {
    const filenameMatch = contentDisposition.match(/filename="?([^";\n]+)"?/)
    if (filenameMatch && filenameMatch[1]) {
      filename = filenameMatch[1]
    }
  }

  return { blob: response.data, filename }
}

/**
 * Get results statistics for KPIs
 */
export const getResultStats = async (): Promise<ResultStatsResponse> => {
  const response = await api.get<ResultStatsResponse>('/results/stats')
  return response.data
}
