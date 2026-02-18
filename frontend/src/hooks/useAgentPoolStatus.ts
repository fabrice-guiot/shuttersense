/**
 * useAgentPoolStatus React hook
 *
 * Provides real-time agent pool status for the header badge.
 * Uses WebSocket for real-time updates with automatic reconnection.
 *
 * Issue #90 - Distributed Agent Architecture (Phase 4)
 * Task: T065
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { getPoolStatus, getPoolStatusWebSocketUrl } from '../services/agents'
import type { AgentPoolStatusResponse } from '@/contracts/api/agent-api'

// ============================================================================
// Types
// ============================================================================

export type PoolStatus = 'offline' | 'idle' | 'running' | 'outdated'

export interface UseAgentPoolStatusReturn {
  poolStatus: AgentPoolStatusResponse | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

// ============================================================================
// Constants
// ============================================================================

const RECONNECT_DELAY_MS = 3000
const MAX_RECONNECT_ATTEMPTS = 5
const PING_INTERVAL_MS = 25000

// ============================================================================
// Hook
// ============================================================================

/**
 * Hook for fetching and maintaining agent pool status via WebSocket.
 *
 * @param autoConnect - Whether to connect on mount (default: true)
 */
export const useAgentPoolStatus = (
  autoConnect = true
): UseAgentPoolStatusReturn => {
  const { isAuthenticated } = useAuth()
  const [poolStatus, setPoolStatus] = useState<AgentPoolStatusResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Use refs for WebSocket state
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const hasConnectedRef = useRef(false)
  const serverRequestedReconnectRef = useRef(false)

  // Manual refetch via REST API (fallback)
  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getPoolStatus()
      setPoolStatus(data)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load agent pool status'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  // Single effect for WebSocket lifecycle - runs once on mount
  useEffect(() => {
    if (!autoConnect || !isAuthenticated) {
      return
    }

    // Prevent duplicate connections (React StrictMode protection)
    if (hasConnectedRef.current) {
      return
    }
    hasConnectedRef.current = true

    const connect = () => {
      // Don't connect if already connected or connecting
      if (wsRef.current?.readyState === WebSocket.OPEN ||
          wsRef.current?.readyState === WebSocket.CONNECTING) {
        return
      }

      setLoading(true)
      setError(null)

      const wsUrl = getPoolStatusWebSocketUrl()

      try {
        const ws = new WebSocket(wsUrl)

        ws.onopen = () => {
          reconnectAttemptsRef.current = 0
          setError(null)

          // Start ping interval to keep connection alive
          pingIntervalRef.current = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send('ping')
            }
          }, PING_INTERVAL_MS)
        }

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (data.type === 'agent_pool_status' && data.pool_status) {
              setPoolStatus(data.pool_status)
              setLoading(false)
            } else if (data.type === 'notification_created') {
              window.dispatchEvent(new Event('notification-created'))
            } else if (data.type === 'reconnect') {
              // Server requests reconnection (connection lifecycle management)
              console.log('[useAgentPoolStatus] Server requested reconnect')
              serverRequestedReconnectRef.current = true
              reconnectAttemptsRef.current = 0 // Reset attempts for clean reconnect
              ws.close()
            }
            // Ignore heartbeat messages
          } catch {
            // Ignore parse errors (e.g., "pong" text responses)
          }
        }

        ws.onerror = () => {
          setError('WebSocket connection error')
        }

        ws.onclose = (event) => {
          // Clean up ping interval
          if (pingIntervalRef.current) {
            clearInterval(pingIntervalRef.current)
            pingIntervalRef.current = null
          }

          wsRef.current = null

          // Check if server requested reconnection (connection lifecycle)
          const shouldReconnectImmediately = serverRequestedReconnectRef.current
          serverRequestedReconnectRef.current = false

          if (shouldReconnectImmediately) {
            // Server requested reconnect - do it immediately
            reconnectTimeoutRef.current = setTimeout(() => {
              connect()
            }, 100) // Small delay to allow socket cleanup
            return
          }

          // Don't reconnect if closed normally or max attempts reached
          if (event.code === 1000 || reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
            if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
              setError('Failed to connect after multiple attempts')
            }
            setLoading(false)
            return
          }

          // Attempt reconnection with exponential backoff
          reconnectAttemptsRef.current++
          const delay = RECONNECT_DELAY_MS * Math.pow(1.5, reconnectAttemptsRef.current - 1)

          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, delay)
        }

        wsRef.current = ws
      } catch {
        setError('Failed to create WebSocket connection')
        setLoading(false)
      }
    }

    connect()

    // Cleanup on unmount only
    return () => {
      hasConnectedRef.current = false

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
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Empty deps - only run on mount/unmount

  return {
    poolStatus,
    loading,
    error,
    refetch,
  }
}

export default useAgentPoolStatus
