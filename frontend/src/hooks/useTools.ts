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
  WebSocketMessage
} from '@/contracts/api/tools-api'

// ============================================================================
// Main Tools Hook
// ============================================================================

interface UseToolsOptions {
  autoFetch?: boolean
  pollInterval?: number  // Poll interval in ms (0 to disable)
}

interface UseToolsReturn {
  jobs: Job[]
  loading: boolean
  error: string | null
  fetchJobs: (params?: JobListQueryParams) => Promise<Job[]>
  runTool: (request: ToolRunRequest) => Promise<Job>
  cancelJob: (jobId: string) => Promise<Job>
  getJob: (jobId: string) => Promise<Job>
}

export const useTools = (options: UseToolsOptions = {}): UseToolsReturn => {
  const { autoFetch = true, pollInterval = 0 } = options

  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

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
      setJobs(prev => [job, ...prev])
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

  // Polling for job updates
  useEffect(() => {
    if (pollInterval > 0) {
      pollTimerRef.current = setInterval(() => {
        fetchJobs()
      }, pollInterval)
    }

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
      }
    }
  }, [pollInterval, fetchJobs])

  return {
    jobs,
    loading,
    error,
    fetchJobs,
    runTool,
    cancelJob,
    getJob
  }
}

// ============================================================================
// Job Progress Hook (WebSocket)
// ============================================================================

interface UseJobProgressOptions {
  onProgress?: (progress: ProgressData) => void
  onStatusChange?: (status: JobStatus, resultId?: number, errorMessage?: string) => void
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
          onStatusChange?.(message.status, message.result_id, message.error_message)
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
  const { autoFetch = true, pollInterval = 5000 } = options

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
