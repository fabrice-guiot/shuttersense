/**
 * Tools API service
 *
 * Handles all API calls related to tool execution and job management
 */

import api from './api'
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
  const response = await api.get<Job>(`/tools/jobs/${jobId}`)
  return response.data
}

/**
 * Cancel a queued job
 */
export const cancelJob = async (jobId: string): Promise<Job> => {
  const response = await api.post<Job>(`/tools/jobs/${jobId}/cancel`)
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
 * Create WebSocket connection for job progress updates
 * Returns the WebSocket URL for the given job
 */
export const getJobWebSocketUrl = (jobId: string): string => {
  const baseUrl = api.defaults.baseURL || 'http://localhost:8000/api'
  // Convert HTTP URL to WebSocket URL
  const wsUrl = baseUrl.replace(/^http/, 'ws')
  return `${wsUrl}/tools/ws/jobs/${jobId}`
}

/**
 * Get WebSocket URL for global job updates
 * Returns the WebSocket URL for the global jobs channel
 */
export const getGlobalJobsWebSocketUrl = (): string => {
  const baseUrl = api.defaults.baseURL || 'http://localhost:8000/api'
  // Convert HTTP URL to WebSocket URL
  const wsUrl = baseUrl.replace(/^http/, 'ws')
  return `${wsUrl}/tools/ws/jobs/all`
}

/**
 * Run all analysis tools on a collection
 * Queues photostats and photo_pairing tools for execution
 */
export const runAllTools = async (collectionId: number): Promise<RunAllToolsResponse> => {
  const response = await api.post<RunAllToolsResponse>(`/tools/run-all/${collectionId}`)
  return response.data
}
