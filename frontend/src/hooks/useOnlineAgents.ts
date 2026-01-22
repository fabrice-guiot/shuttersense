/**
 * useOnlineAgents React hook
 *
 * Provides a filtered list of online agents for binding to LOCAL collections.
 *
 * Issue #90 - Distributed Agent Architecture (Phase 6)
 * Task T116: Add useOnlineAgents hook
 */

import { useState, useEffect, useCallback, useMemo } from 'react'
import * as agentService from '../services/agents'
import type { Agent } from '@/contracts/api/agent-api'

// ============================================================================
// Types
// ============================================================================

export interface OnlineAgent {
  guid: string
  name: string
  hostname: string
  version: string
}

interface UseOnlineAgentsReturn {
  /** List of online agents available for binding */
  onlineAgents: OnlineAgent[]
  /** Loading state */
  loading: boolean
  /** Error message if fetch failed */
  error: string | null
  /** Refetch agents */
  refetch: () => Promise<void>
}

// ============================================================================
// Hook Implementation
// ============================================================================

/**
 * Hook to fetch and filter online agents for LOCAL collection binding.
 *
 * @param autoFetch - Whether to fetch on mount (default: true)
 * @returns Online agents list with loading/error state
 *
 * @example
 * ```tsx
 * const { onlineAgents, loading, error } = useOnlineAgents()
 *
 * return (
 *   <Select>
 *     {onlineAgents.map(agent => (
 *       <SelectItem key={agent.guid} value={agent.guid}>
 *         {agent.name} ({agent.hostname})
 *       </SelectItem>
 *     ))}
 *   </Select>
 * )
 * ```
 */
export const useOnlineAgents = (autoFetch = true): UseOnlineAgentsReturn => {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /**
   * Fetch all agents from API
   */
  const fetchAgents = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      // Fetch non-revoked agents only
      const data = await agentService.listAgents(false)
      setAgents(data)
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load agents'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Filter agents to only online status
   */
  const onlineAgents: OnlineAgent[] = useMemo(() => {
    return agents
      .filter((agent) => agent.status === 'online')
      .map((agent) => ({
        guid: agent.guid,
        name: agent.name,
        hostname: agent.hostname,
        version: agent.version,
      }))
  }, [agents])

  /**
   * Refetch handler for manual refresh
   */
  const refetch = useCallback(async () => {
    await fetchAgents()
  }, [fetchAgents])

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (autoFetch) {
      fetchAgents()
    }
  }, [autoFetch, fetchAgents])

  return {
    onlineAgents,
    loading,
    error,
    refetch,
  }
}

export default useOnlineAgents
