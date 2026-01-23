/**
 * Storage Stats Hook
 *
 * Provides functionality to fetch storage metrics and optimization statistics.
 * Part of Issue #92: Storage Optimization for Analysis Results.
 */

import { useState, useCallback, useEffect } from 'react'
import axios from 'axios'
import type { StorageStatsResponse } from '@/contracts/api/analytics-api'

// ============================================================================
// Types
// ============================================================================

interface UseStorageStatsReturn {
  /** Current storage statistics */
  stats: StorageStatsResponse | null
  /** Loading state */
  loading: boolean
  /** Error message */
  error: string | null
  /** Fetch current storage statistics */
  fetchStats: () => Promise<void>
  /** Refetch alias */
  refetch: () => Promise<void>
  /** Clear error state */
  clearError: () => void
}

// ============================================================================
// Hook
// ============================================================================

/**
 * Hook for fetching storage statistics.
 *
 * @param autoFetch - Whether to fetch stats automatically on mount (default: true)
 * @returns Storage stats state and actions
 *
 * @example
 * ```tsx
 * const { stats, loading, refetch } = useStorageStats()
 *
 * if (stats) {
 *   console.log(`Deduplication ratio: ${stats.deduplication_ratio}%`)
 * }
 * ```
 */
export function useStorageStats(autoFetch = true): UseStorageStatsReturn {
  const [stats, setStats] = useState<StorageStatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchStats = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await axios.get<StorageStatsResponse>('/api/analytics/storage')
      setStats(response.data)
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string }
      const message = axiosErr.response?.data?.detail || axiosErr.message || 'Failed to fetch storage statistics'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (autoFetch) {
      fetchStats()
    }
  }, [autoFetch, fetchStats])

  return {
    stats,
    loading,
    error,
    fetchStats,
    refetch: fetchStats,
    clearError
  }
}

export default useStorageStats
