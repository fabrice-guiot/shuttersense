/**
 * Tools API service
 *
 * Handles all API calls related to tool execution and job management
 */

import api from './api'
import { validateGuid } from '@/utils/guid'
import type {
  ToolRunRequest,
  Job,
  JobListQueryParams,
  QueueStatusResponse,
  RunAllToolsResponse
} from '@/contracts/api/tools-api'

/**
 * Start tool execution on a collection
 */
export const runTool = async (request: ToolRunRequest): Promise<Job> => {
  const response = await api.post<Job>('/tools/run', request)
  return response.data
}

/**
 * List all jobs with optional filters
 */
export const listJobs = async (params: JobListQueryParams = {}): Promise<Job[]> => {
  const response = await api.get<Job[]>('/tools/jobs', { params })
  return response.data
}

/**
 * Get job status and details
 */
export const getJob = async (jobId: string): Promise<Job> => {
  // Job IDs use 'job' prefix
  const safeJobId = encodeURIComponent(validateGuid(jobId, 'job'))
  const response = await api.get<Job>(`/tools/jobs/${safeJobId}`)
  return response.data
}

/**
 * Cancel a queued job
 */
export const cancelJob = async (jobId: string): Promise<Job> => {
  // Job IDs use 'job' prefix
  const safeJobId = encodeURIComponent(validateGuid(jobId, 'job'))
  const response = await api.post<Job>(`/tools/jobs/${safeJobId}/cancel`)
  return response.data
}

/**
 * Get queue statistics
 */
export const getQueueStatus = async (): Promise<QueueStatusResponse> => {
  const response = await api.get<QueueStatusResponse>('/tools/queue/status')
  return response.data
}

/**
 * Build WebSocket URL from API base URL
 * Handles both relative URLs (/api) and absolute URLs (http://...)
 */
const buildWebSocketUrl = (path: string): string => {
  const baseUrl = api.defaults.baseURL || '/api'

  // If baseUrl is relative, construct absolute WebSocket URL from current location
  if (baseUrl.startsWith('/')) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}${baseUrl}${path}`
  }

  // If baseUrl is absolute, convert HTTP to WS
  const wsUrl = baseUrl.replace(/^http/, 'ws')
  return `${wsUrl}${path}`
}

/**
 * Create WebSocket connection for job progress updates
 * Returns the WebSocket URL for the given job
 */
export const getJobWebSocketUrl = (jobId: string): string => {
  // Job IDs use 'job' prefix
  const safeJobId = encodeURIComponent(validateGuid(jobId, 'job'))
  return buildWebSocketUrl(`/tools/ws/jobs/${safeJobId}`)
}

/**
 * Get WebSocket URL for global job updates
 * Returns the WebSocket URL for the global jobs channel
 */
export const getGlobalJobsWebSocketUrl = (): string => {
  return buildWebSocketUrl('/tools/ws/jobs/all')
}

/**
 * Run all analysis tools on a collection
 * Queues photostats and photo_pairing tools for execution
 * @param collectionGuid - External ID (col_xxx format)
 */
export const runAllTools = async (collectionGuid: string): Promise<RunAllToolsResponse> => {
  const safeGuid = encodeURIComponent(validateGuid(collectionGuid, 'col'))
  const response = await api.post<RunAllToolsResponse>(`/tools/run-all/${safeGuid}`)
  return response.data
}
