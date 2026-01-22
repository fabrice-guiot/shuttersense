/**
 * useAgents React hook
 *
 * Manages agent state with fetch, update, revoke, and token operations
 *
 * Issue #90 - Distributed Agent Architecture (Phase 3)
 * Task: T051
 */

import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import * as agentService from '../services/agents'
import type {
  Agent,
  AgentUpdateRequest,
  AgentStatsResponse,
  RegistrationToken,
  RegistrationTokenCreateRequest,
  RegistrationTokenListItem,
} from '@/contracts/api/agent-api'

// ============================================================================
// Main useAgents Hook
// ============================================================================

interface UseAgentsReturn {
  agents: Agent[]
  loading: boolean
  error: string | null
  fetchAgents: (includeRevoked?: boolean) => Promise<Agent[]>
  updateAgent: (guid: string, data: AgentUpdateRequest) => Promise<Agent>
  revokeAgent: (guid: string, reason?: string) => Promise<void>
}

export const useAgents = (autoFetch = true): UseAgentsReturn => {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /**
   * Fetch agents
   */
  const fetchAgents = useCallback(async (includeRevoked = false) => {
    setLoading(true)
    setError(null)
    try {
      const data = await agentService.listAgents(includeRevoked)
      setAgents(data)
      return data
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load agents'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Update an agent (rename)
   */
  const updateAgent = useCallback(async (guid: string, data: AgentUpdateRequest) => {
    setLoading(true)
    setError(null)
    try {
      const updated = await agentService.updateAgent(guid, data)
      setAgents(prev => prev.map(a => (a.guid === guid ? updated : a)))
      toast.success('Agent updated successfully')
      return updated
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to update agent'
      setError(errorMessage)
      toast.error('Failed to update agent', {
        description: errorMessage,
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Revoke an agent's access
   */
  const revokeAgent = useCallback(async (guid: string, reason?: string) => {
    setLoading(true)
    setError(null)
    try {
      await agentService.revokeAgent(guid, reason)
      setAgents(prev => prev.filter(a => a.guid !== guid))
      toast.success('Agent revoked successfully')
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to revoke agent'
      setError(errorMessage)
      toast.error('Failed to revoke agent', {
        description: errorMessage,
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (autoFetch) {
      fetchAgents().catch(() => {
        // Error already handled in fetchAgents, just suppress unhandled rejection
      })
    }
  }, [autoFetch, fetchAgents])

  return {
    agents,
    loading,
    error,
    fetchAgents,
    updateAgent,
    revokeAgent,
  }
}

// ============================================================================
// Agent Stats Hook (for header KPIs)
// ============================================================================

interface UseAgentStatsReturn {
  stats: AgentStatsResponse | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * Hook for fetching agent KPI statistics
 */
export const useAgentStats = (autoFetch = true): UseAgentStatsReturn => {
  const [stats, setStats] = useState<AgentStatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await agentService.getAgentStats()
      setStats(data)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load agent statistics'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (autoFetch) {
      refetch()
    }
  }, [autoFetch, refetch])

  return { stats, loading, error, refetch }
}

// ============================================================================
// Registration Token Hook
// ============================================================================

interface UseRegistrationTokensReturn {
  tokens: RegistrationTokenListItem[]
  loading: boolean
  error: string | null
  fetchTokens: (includeUsed?: boolean) => Promise<RegistrationTokenListItem[]>
  createToken: (data?: RegistrationTokenCreateRequest) => Promise<RegistrationToken>
  deleteToken: (guid: string) => Promise<void>
}

export const useRegistrationTokens = (autoFetch = true): UseRegistrationTokensReturn => {
  const [tokens, setTokens] = useState<RegistrationTokenListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /**
   * Fetch registration tokens
   */
  const fetchTokens = useCallback(async (includeUsed = false) => {
    setLoading(true)
    setError(null)
    try {
      const data = await agentService.listRegistrationTokens(includeUsed)
      setTokens(data)
      return data
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load registration tokens'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Create a new registration token
   */
  const createToken = useCallback(async (data: RegistrationTokenCreateRequest = {}) => {
    setLoading(true)
    setError(null)
    try {
      const newToken = await agentService.createRegistrationToken(data)
      // Token list doesn't include the actual token value, so we just refetch
      await fetchTokens()
      toast.success('Registration token created')
      return newToken
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to create registration token'
      setError(errorMessage)
      toast.error('Failed to create token', {
        description: errorMessage,
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [fetchTokens])

  /**
   * Delete a registration token
   */
  const deleteToken = useCallback(async (guid: string) => {
    setLoading(true)
    setError(null)
    try {
      await agentService.deleteRegistrationToken(guid)
      setTokens(prev => prev.filter(t => t.guid !== guid))
      toast.success('Registration token deleted')
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to delete registration token'
      setError(errorMessage)
      toast.error('Failed to delete token', {
        description: errorMessage,
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (autoFetch) {
      fetchTokens().catch(() => {
        // Error already handled in fetchTokens, just suppress unhandled rejection
      })
    }
  }, [autoFetch, fetchTokens])

  return {
    tokens,
    loading,
    error,
    fetchTokens,
    createToken,
    deleteToken,
  }
}
