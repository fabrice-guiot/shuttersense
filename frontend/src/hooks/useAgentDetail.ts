/**
 * Hook for agent detail view with real-time updates
 *
 * Provides detailed agent information including metrics, job statistics,
 * and recent job history. Supports WebSocket subscription for real-time updates.
 *
 * Issue #90 - Distributed Agent Architecture (Phase 11)
 * Task: T176 - Create real-time agent status WebSocket subscription
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import { getAgentDetail, getAgentJobHistory, getPoolStatusWebSocketUrl } from '@/services/agents'
import type {
  AgentDetailResponse,
  AgentJobHistoryResponse,
  AgentStatus,
} from '@/contracts/api/agent-api'

// ============================================================================
// Types
// ============================================================================

interface UseAgentDetailReturn {
  /** Agent detail data */
  agent: AgentDetailResponse | null
  /** Whether data is currently loading */
  loading: boolean
  /** Error message if fetch failed */
  error: string | null
  /** Refetch agent detail */
  refetch: () => Promise<void>
  /** Whether WebSocket is connected */
  wsConnected: boolean
}

interface UseAgentJobHistoryReturn {
  /** Job history list */
  jobs: AgentJobHistoryResponse['jobs']
  /** Total number of jobs */
  totalCount: number
  /** Whether data is currently loading */
  loading: boolean
  /** Error message if fetch failed */
  error: string | null
  /** Current offset */
  offset: number
  /** Items per page */
  limit: number
  /** Fetch a specific page */
  fetchPage: (offset: number) => Promise<void>
}

// ============================================================================
// useAgentDetail Hook
// ============================================================================

/**
 * Hook for fetching and subscribing to agent detail updates.
 *
 * @param guid - Agent GUID to fetch details for
 * @param autoFetch - Whether to fetch on mount (default: true)
 * @param enableRealtime - Whether to enable WebSocket updates (default: true)
 * @returns Agent detail data, loading state, error, and refetch function
 */
export const useAgentDetail = (
  guid: string,
  autoFetch = true,
  enableRealtime = true
): UseAgentDetailReturn => {
  const [agent, setAgent] = useState<AgentDetailResponse | null>(null)
  const [loading, setLoading] = useState(autoFetch)
  const [error, setError] = useState<string | null>(null)
  const [wsConnected, setWsConnected] = useState(false)

  // WebSocket ref for cleanup
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const reconnectAttemptsRef = useRef(0)

  const MAX_RECONNECT_ATTEMPTS = 5
  const BASE_RECONNECT_DELAY = 1000

  /**
   * Fetch agent detail from API
   */
  const fetchAgent = useCallback(async () => {
    if (!guid) return

    setLoading(true)
    setError(null)

    try {
      const data = await getAgentDetail(guid)
      setAgent(data)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch agent details'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [guid])

  /**
   * Connect to WebSocket for real-time updates
   */
  const connectWebSocket = useCallback(() => {
    if (!enableRealtime || wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    const url = getPoolStatusWebSocketUrl()

    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setWsConnected(true)
        reconnectAttemptsRef.current = 0

        // Start ping interval to keep connection alive
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping')
          }
        }, 25000)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          // Handle pool status updates - refetch agent detail if our agent is affected
          if (data.type === 'agent_pool_status') {
            // Refetch agent detail to get updated status
            fetchAgent()
          }

          // Handle heartbeat messages (no action needed)
          if (data.type === 'heartbeat') {
            return
          }
        } catch {
          // Non-JSON messages (like 'pong') can be ignored
        }
      }

      ws.onclose = () => {
        setWsConnected(false)

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current)
          pingIntervalRef.current = null
        }

        // Attempt reconnection with exponential backoff
        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          const delay = BASE_RECONNECT_DELAY * Math.pow(2, reconnectAttemptsRef.current)
          reconnectAttemptsRef.current++

          reconnectTimeoutRef.current = setTimeout(() => {
            connectWebSocket()
          }, delay)
        }
      }

      ws.onerror = () => {
        // Error will trigger onclose, no additional handling needed
      }
    } catch {
      // WebSocket creation failed - will retry via reconnection logic
    }
  }, [enableRealtime, fetchAgent])

  /**
   * Cleanup WebSocket connection
   */
  const cleanupWebSocket = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current)
      pingIntervalRef.current = null
    }

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    setWsConnected(false)
    reconnectAttemptsRef.current = 0
  }, [])

  // Fetch on mount if autoFetch is enabled
  useEffect(() => {
    if (autoFetch && guid) {
      fetchAgent()
    }
  }, [autoFetch, guid, fetchAgent])

  // Setup WebSocket connection
  useEffect(() => {
    if (enableRealtime && guid) {
      connectWebSocket()
    }

    return () => {
      cleanupWebSocket()
    }
  }, [enableRealtime, guid, connectWebSocket, cleanupWebSocket])

  return {
    agent,
    loading,
    error,
    refetch: fetchAgent,
    wsConnected,
  }
}

// ============================================================================
// useAgentJobHistory Hook
// ============================================================================

/**
 * Hook for fetching paginated agent job history.
 *
 * @param guid - Agent GUID to fetch job history for
 * @param initialLimit - Items per page (default: 20)
 * @param autoFetch - Whether to fetch on mount (default: true)
 * @returns Job history data, loading state, pagination, and fetch function
 */
export const useAgentJobHistory = (
  guid: string,
  initialLimit = 20,
  autoFetch = true
): UseAgentJobHistoryReturn => {
  const [jobs, setJobs] = useState<AgentJobHistoryResponse['jobs']>([])
  const [totalCount, setTotalCount] = useState(0)
  const [loading, setLoading] = useState(autoFetch)
  const [error, setError] = useState<string | null>(null)
  const [offset, setOffset] = useState(0)
  const [limit] = useState(initialLimit)

  /**
   * Fetch a specific page of job history
   */
  const fetchPage = useCallback(
    async (pageOffset: number) => {
      if (!guid) return

      setLoading(true)
      setError(null)

      try {
        const data = await getAgentJobHistory(guid, pageOffset, limit)
        setJobs(data.jobs)
        setTotalCount(data.total_count)
        setOffset(pageOffset)
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Failed to fetch job history'
        setError(message)
      } finally {
        setLoading(false)
      }
    },
    [guid, limit]
  )

  // Fetch on mount if autoFetch is enabled
  useEffect(() => {
    if (autoFetch && guid) {
      fetchPage(0)
    }
  }, [autoFetch, guid, fetchPage])

  return {
    jobs,
    totalCount,
    loading,
    error,
    offset,
    limit,
    fetchPage,
  }
}

// Default export for convenience
export default useAgentDetail
