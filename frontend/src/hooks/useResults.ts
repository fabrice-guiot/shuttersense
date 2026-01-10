/**
 * useResults React hook
 *
 * Manages analysis results state with fetch, delete, and pagination operations
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import * as resultsService from '../services/results'
import type {
  AnalysisResult,
  AnalysisResultSummary,
  ResultListQueryParams,
  ResultStatsResponse,
  ResultFilters,
  toApiQueryParams
} from '@/contracts/api/results-api'

// Debounce delay for filter changes
const FILTER_DEBOUNCE_MS = 300

// ============================================================================
// Main Results Hook
// ============================================================================

interface UseResultsOptions {
  autoFetch?: boolean
  debounceMs?: number
  defaultLimit?: number
}

interface UseResultsReturn {
  results: AnalysisResultSummary[]
  total: number
  loading: boolean
  error: string | null
  filters: ResultListQueryParams
  setFilters: (filters: ResultListQueryParams) => void
  page: number
  setPage: (page: number) => void
  limit: number
  setLimit: (limit: number) => void
  fetchResults: (params?: ResultListQueryParams) => Promise<void>
  deleteResult: (identifier: string) => Promise<void>
  refetch: () => Promise<void>
}

export const useResults = (options: UseResultsOptions = {}): UseResultsReturn => {
  const { autoFetch = true, debounceMs = FILTER_DEBOUNCE_MS, defaultLimit = 20 } = options

  const [results, setResults] = useState<AnalysisResultSummary[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFiltersState] = useState<ResultListQueryParams>({})
  const [page, setPage] = useState(1)
  const [limit, setLimit] = useState(defaultLimit)

  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  /**
   * Fetch results with given parameters
   */
  const fetchResults = useCallback(async (params: ResultListQueryParams = {}) => {
    setLoading(true)
    setError(null)
    try {
      const response = await resultsService.listResults(params)
      setResults(response.items)
      setTotal(response.total)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load results'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Set filters with state update
   */
  const setFilters = useCallback((newFilters: ResultListQueryParams) => {
    setFiltersState(newFilters)
    setPage(1) // Reset to first page when filters change
  }, [])

  /**
   * Delete a result by external ID
   */
  const deleteResult = useCallback(async (identifier: string) => {
    setLoading(true)
    setError(null)
    try {
      await resultsService.deleteResult(identifier)
      setResults(prev => prev.filter(r => r.guid !== identifier))
      setTotal(prev => Math.max(0, prev - 1))
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to delete result'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Refetch with current filters and pagination
   */
  const refetch = useCallback(async () => {
    const offset = (page - 1) * limit
    await fetchResults({
      ...filters,
      limit,
      offset
    })
  }, [filters, page, limit, fetchResults])

  // Debounced filter effect
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }

    debounceTimerRef.current = setTimeout(() => {
      const offset = (page - 1) * limit
      fetchResults({
        ...filters,
        limit,
        offset
      })
    }, debounceMs)

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, [filters, page, limit, debounceMs, fetchResults])

  // Initial fetch
  useEffect(() => {
    if (autoFetch) {
      fetchResults({ limit, offset: 0 })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return {
    results,
    total,
    loading,
    error,
    filters,
    setFilters,
    page,
    setPage,
    limit,
    setLimit,
    fetchResults,
    deleteResult,
    refetch
  }
}

// ============================================================================
// Single Result Hook
// ============================================================================

interface UseResultReturn {
  result: AnalysisResult | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

export const useResult = (identifier: string | null): UseResultReturn => {
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    if (!identifier) {
      setResult(null)
      return
    }

    setLoading(true)
    setError(null)
    try {
      const data = await resultsService.getResult(identifier)
      setResult(data)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load result'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [identifier])

  useEffect(() => {
    refetch()
  }, [refetch])

  return {
    result,
    loading,
    error,
    refetch
  }
}

// ============================================================================
// Result Stats Hook (for KPIs)
// ============================================================================

interface UseResultStatsReturn {
  stats: ResultStatsResponse | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

export const useResultStats = (autoFetch = true): UseResultStatsReturn => {
  const [stats, setStats] = useState<ResultStatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await resultsService.getResultStats()
      setStats(data)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load result statistics'
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
// Report Download Hook
// ============================================================================

interface UseReportDownloadReturn {
  downloading: boolean
  error: string | null
  downloadReport: (identifier: string) => Promise<void>
  getReportUrl: (identifier: string) => string
}

export const useReportDownload = (): UseReportDownloadReturn => {
  const [downloading, setDownloading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const downloadReport = useCallback(async (identifier: string) => {
    setDownloading(true)
    setError(null)
    try {
      const { blob, filename } = await resultsService.downloadReport(identifier)

      // Create download link
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()

      // Cleanup
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to download report'
      setError(errorMessage)
      throw err
    } finally {
      setDownloading(false)
    }
  }, [])

  const getReportUrl = useCallback((identifier: string) => {
    return resultsService.getReportUrl(identifier)
  }, [])

  return {
    downloading,
    error,
    downloadReport,
    getReportUrl
  }
}
