/**
 * useDashboard React hook
 *
 * Provides dashboard-specific data fetching, including recent analysis results.
 */

import { useState, useEffect, useCallback } from 'react'
import * as resultsService from '../services/results'
import type { AnalysisResultSummary } from '@/contracts/api/results-api'

// ============================================================================
// Recent Results Hook
// ============================================================================

const RECENT_RESULTS_LIMIT = 5

interface UseRecentResultsReturn {
  results: AnalysisResultSummary[]
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * Fetches the most recent analysis results for the dashboard.
 * Returns the latest 5 results sorted by creation date (newest first).
 */
export const useRecentResults = (autoFetch = true): UseRecentResultsReturn => {
  const [results, setResults] = useState<AnalysisResultSummary[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await resultsService.listResults({
        limit: RECENT_RESULTS_LIMIT,
        offset: 0,
        sort_by: 'created_at',
        sort_order: 'desc',
      })
      setResults(response.items)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load recent results'
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

  return { results, loading, error, refetch }
}
