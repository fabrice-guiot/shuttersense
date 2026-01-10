/**
 * useTools React hook
 *
 * Manages tool execution state with job tracking and WebSocket progress updates
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { toast } from 'sonner'
import * as toolsService from '../services/tools'
import type {
  Job,
  JobStatus,
  ToolType,
  ToolRunRequest,
  JobListQueryParams,
  QueueStatusResponse,
  ProgressData,
  WebSocketMessage,
  RunAllToolsResponse
} from '@/contracts/api/tools-api'

// ============================================================================
// Main Tools Hook
// ============================================================================

interface UseToolsOptions {
  autoFetch?: boolean
  /** @deprecated Use WebSocket updates instead. Polling is only used as fallback. */
  pollInterval?: number  // Poll interval in ms (0 to disable)
  /** Enable WebSocket for real-time job updates (default: true) */
  useWebSocket?: boolean
  /** Callback fired when a job transitions to a terminal state (completed, failed, cancelled) */
  onJobComplete?: (job: Job) => void
}

interface UseToolsReturn {
  jobs: Job[]
  loading: boolean
  error: string | null
  wsConnected: boolean
  fetchJobs: (params?: JobListQueryParams) => Promise<Job[]>
  runTool: (request: ToolRunRequest) => Promise<Job>
  runAllTools: (collectionGuid: string) => Promise<RunAllToolsResponse>
  cancelJob: (jobId: string) => Promise<Job>
  getJob: (jobId: string) => Promise<Job>
}

export const useTools = (options: UseToolsOptions = {}): UseToolsReturn => {
  const { autoFetch = true, pollInterval = 0, useWebSocket = true, onJobComplete } = options

  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [wsConnected, setWsConnected] = useState(false)

  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 5

  /**
   * Fetch jobs with optional filters
   */
  const fetchJobs = useCallback(async (params: JobListQueryParams = {}) => {
    setLoading(true)
    setError(null)
    try {
      const data = await toolsService.listJobs(params)
      setJobs(data)
      return data
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load jobs'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Run a tool on a collection
   */
  const runTool = useCallback(async (request: ToolRunRequest) => {
    setLoading(true)
    setError(null)
    try {
      const job = await toolsService.runTool(request)
      // Check if job already exists (WebSocket may have added it first due to race condition)
      setJobs(prev => {
        const existingIndex = prev.findIndex(j => j.id === job.id)
        if (existingIndex >= 0) {
          // Job already exists (from WebSocket), update it with API response
          // Keep the existing job since WebSocket may have more up-to-date status
          return prev
        }
        return [job, ...prev]
      })
      toast.success('Tool started successfully', {
        description: `Job ${job.id.slice(0, 8)} is now running`
      })
      return job
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to start tool'
      setError(errorMessage)
      toast.error('Failed to start tool', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Run all analysis tools on a collection
   */
  const runAllTools = useCallback(async (collectionGuid: string) => {
    setLoading(true)
    setError(null)
    try {
      const result = await toolsService.runAllTools(collectionGuid)
      // Add new jobs to state, checking for duplicates (WebSocket race condition)
      if (result.jobs.length > 0) {
        setJobs(prev => {
          const existingIds = new Set(prev.map(j => j.id))
          const newJobs = result.jobs.filter(job => !existingIds.has(job.id))
          return [...newJobs, ...prev]
        })
      }
      toast.success('Analysis started', {
        description: result.message
      })
      return result
    } catch (err: any) {
      // Handle inaccessible collection error (422)
      const detail = err.response?.data?.detail
      if (detail?.message) {
        toast.warning('Cannot run analysis', {
          description: detail.message
        })
      } else {
        const errorMessage = err.userMessage || 'Failed to start analysis'
        setError(errorMessage)
        toast.error('Failed to start analysis', {
          description: errorMessage
        })
      }
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Cancel a job
   */
  const cancelJob = useCallback(async (jobId: string) => {
    setLoading(true)
    setError(null)
    try {
      const cancelledJob = await toolsService.cancelJob(jobId)
      setJobs(prev => prev.map(j => j.id === jobId ? cancelledJob : j))
      toast.success('Job cancelled')
      return cancelledJob
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to cancel job'
      setError(errorMessage)
      toast.error('Failed to cancel job', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Get a specific job
   */
  const getJob = useCallback(async (jobId: string) => {
    try {
      const job = await toolsService.getJob(jobId)
      setJobs(prev => {
        const exists = prev.find(j => j.id === jobId)
        if (exists) {
          return prev.map(j => j.id === jobId ? job : j)
        }
        return [job, ...prev]
      })
      return job
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to get job'
      throw new Error(errorMessage)
    }
  }, [])

  // Auto-fetch on mount
  useEffect(() => {
    if (autoFetch) {
      fetchJobs()
    }
  }, [autoFetch, fetchJobs])

  // WebSocket connection for real-time job updates
  const connectWebSocket = useCallback(() => {
    if (!useWebSocket || wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    const wsUrl = toolsService.getGlobalJobsWebSocketUrl()
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      setWsConnected(true)
      reconnectAttempts.current = 0
      console.log('[useTools] WebSocket connected to global jobs channel')
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)

        if (message.type === 'job_update' && message.job) {
          const updatedJob = message.job as Job
          const terminalStatuses: JobStatus[] = ['completed', 'failed', 'cancelled']
          const isTerminal = terminalStatuses.includes(updatedJob.status)

          setJobs(prev => {
            const existingIndex = prev.findIndex(j => j.id === updatedJob.id)
            if (existingIndex >= 0) {
              const existingJob = prev[existingIndex]
              // Check if this is a transition to terminal state
              const wasTerminal = terminalStatuses.includes(existingJob.status)
              if (isTerminal && !wasTerminal && onJobComplete) {
                // Defer callback to avoid state update during render
                setTimeout(() => onJobComplete(updatedJob), 0)
              }
              // Update existing job
              const newJobs = [...prev]
              newJobs[existingIndex] = updatedJob
              return newJobs
            } else {
              // New job - add to front
              // If it's already terminal (e.g., fast completion), still notify
              if (isTerminal && onJobComplete) {
                setTimeout(() => onJobComplete(updatedJob), 0)
              }
              return [updatedJob, ...prev]
            }
          })
        }
        // Ignore heartbeat messages
      } catch (err) {
        console.error('[useTools] Failed to parse WebSocket message:', err)
      }
    }

    ws.onerror = (event) => {
      console.error('[useTools] WebSocket error:', event)
    }

    ws.onclose = () => {
      setWsConnected(false)
      wsRef.current = null

      // Attempt reconnection with exponential backoff
      if (reconnectAttempts.current < maxReconnectAttempts) {
        reconnectAttempts.current++
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
        console.log(`[useTools] WebSocket closed, reconnecting in ${delay}ms (attempt ${reconnectAttempts.current})`)
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, delay)
      }
    }

    wsRef.current = ws
  }, [useWebSocket, onJobComplete])

  // Initialize WebSocket connection
  useEffect(() => {
    if (useWebSocket) {
      connectWebSocket()
    }

    return () => {
      // Cleanup WebSocket
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [useWebSocket, connectWebSocket])

  // Fallback polling (only if WebSocket is disabled or as backup)
  useEffect(() => {
    // Only poll if WebSocket is disabled AND pollInterval is set
    if (!useWebSocket && pollInterval > 0) {
      pollTimerRef.current = setInterval(() => {
        fetchJobs()
      }, pollInterval)
    }

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
      }
    }
  }, [pollInterval, fetchJobs, useWebSocket])

  return {
    jobs,
    loading,
    error,
    wsConnected,
    fetchJobs,
    runTool,
    runAllTools,
    cancelJob,
    getJob
  }
}

// ============================================================================
// Job Progress Hook (WebSocket)
// ============================================================================

interface UseJobProgressOptions {
  onProgress?: (progress: ProgressData) => void
  onStatusChange?: (status: JobStatus, resultGuid?: string, errorMessage?: string) => void
  onError?: (error: string) => void
}

interface UseJobProgressReturn {
  progress: ProgressData | null
  status: JobStatus | null
  connected: boolean
  error: string | null
  connect: () => void
  disconnect: () => void
}

export const useJobProgress = (
  jobId: string | null,
  options: UseJobProgressOptions = {}
): UseJobProgressReturn => {
  const { onProgress, onStatusChange, onError } = options

  const [progress, setProgress] = useState<ProgressData | null>(null)
  const [status, setStatus] = useState<JobStatus | null>(null)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 3

  const connect = useCallback(() => {
    if (!jobId || wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    const wsUrl = toolsService.getJobWebSocketUrl(jobId)
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      setConnected(true)
      setError(null)
      reconnectAttempts.current = 0
    }

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data)

        if (message.type === 'progress') {
          setProgress(message.data)
          onProgress?.(message.data)
        } else if (message.type === 'status') {
          setStatus(message.status)
          onStatusChange?.(message.status, message.result_guid, message.error_message)
        } else if (message.type === 'closed') {
          ws.close()
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err)
      }
    }

    ws.onerror = () => {
      setError('WebSocket connection error')
      onError?.('WebSocket connection error')
    }

    ws.onclose = () => {
      setConnected(false)
      wsRef.current = null

      // Attempt reconnection for non-terminal statuses
      if (
        reconnectAttempts.current < maxReconnectAttempts &&
        status !== 'completed' &&
        status !== 'failed' &&
        status !== 'cancelled'
      ) {
        reconnectAttempts.current++
        setTimeout(connect, 1000 * reconnectAttempts.current)
      }
    }

    wsRef.current = ws
  }, [jobId, status, onProgress, onStatusChange, onError])

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setConnected(false)
  }, [])

  // Auto-connect when jobId changes
  useEffect(() => {
    if (jobId) {
      connect()
    }
    return () => {
      disconnect()
    }
  }, [jobId, connect, disconnect])

  return {
    progress,
    status,
    connected,
    error,
    connect,
    disconnect
  }
}

// ============================================================================
// Queue Status Hook
// ============================================================================

interface UseQueueStatusOptions {
  autoFetch?: boolean
  pollInterval?: number
}

interface UseQueueStatusReturn {
  queueStatus: QueueStatusResponse | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

export const useQueueStatus = (options: UseQueueStatusOptions = {}): UseQueueStatusReturn => {
  const { autoFetch = true, pollInterval = 0 } = options  // No polling by default

  const [queueStatus, setQueueStatus] = useState<QueueStatusResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await toolsService.getQueueStatus()
      setQueueStatus(data)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load queue status'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  // Auto-fetch on mount
  useEffect(() => {
    if (autoFetch) {
      refetch()
    }
  }, [autoFetch, refetch])

  // Polling
  useEffect(() => {
    if (pollInterval > 0) {
      pollTimerRef.current = setInterval(refetch, pollInterval)
    }

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
      }
    }
  }, [pollInterval, refetch])

  return {
    queueStatus,
    loading,
    error,
    refetch
  }
}
