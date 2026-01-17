/**
 * useTokens React Hook
 *
 * Manages API token state with list, create, and revoke operations.
 * Phase 10: User Story 7 - API Token Authentication
 */

import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import * as tokenService from '@/services/tokens'
import type { ApiToken, ApiTokenCreated, CreateTokenRequest, TokenStatsResponse } from '@/contracts/api/tokens-api'

interface UseTokensReturn {
  tokens: ApiToken[]
  loading: boolean
  error: string | null
  fetchTokens: (filters?: { active_only?: boolean }) => Promise<ApiToken[]>
  createToken: (data: CreateTokenRequest) => Promise<ApiTokenCreated>
  revokeToken: (guid: string) => Promise<void>
}

/**
 * Hook for managing API tokens
 *
 * @param autoFetch - Whether to automatically fetch tokens on mount
 */
export const useTokens = (autoFetch = true): UseTokensReturn => {
  const [tokens, setTokens] = useState<ApiToken[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /**
   * Fetch tokens with optional filters
   */
  const fetchTokens = useCallback(async (filters: { active_only?: boolean } = {}) => {
    setLoading(true)
    setError(null)
    try {
      const data = await tokenService.listTokens(filters)
      setTokens(data)
      return data
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load API tokens'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Create a new API token
   *
   * Returns the created token including the actual JWT value.
   * This is the only time the token value is available!
   */
  const createToken = useCallback(async (data: CreateTokenRequest) => {
    setLoading(true)
    setError(null)
    try {
      const newToken = await tokenService.createToken(data)
      // Refetch the list to get complete token data with audit info
      await fetchTokens()
      toast.success('API token created successfully')
      return newToken
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to create API token'
      setError(errorMessage)
      toast.error('Failed to create API token', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [fetchTokens])

  /**
   * Revoke (deactivate) an API token
   */
  const revokeToken = useCallback(async (guid: string) => {
    setLoading(true)
    setError(null)
    try {
      await tokenService.revokeToken(guid)
      // Update local state - mark as inactive
      setTokens(prev =>
        prev.map(t => t.guid === guid ? { ...t, is_active: false } : t)
      )
      toast.success('API token revoked')
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to revoke API token'
      setError(errorMessage)
      toast.error('Failed to revoke token', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (autoFetch) {
      fetchTokens()
    }
  }, [autoFetch, fetchTokens])

  return {
    tokens,
    loading,
    error,
    fetchTokens,
    createToken,
    revokeToken,
  }
}

// ============================================================================
// Token Stats Hook
// ============================================================================

interface UseTokenStatsReturn {
  stats: TokenStatsResponse | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * Hook for fetching token KPI statistics
 * Returns total, active, and revoked token counts
 */
export const useTokenStats = (autoFetch = true): UseTokenStatsReturn => {
  const [stats, setStats] = useState<TokenStatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await tokenService.getTokenStats()
      setStats(data)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load token statistics'
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
