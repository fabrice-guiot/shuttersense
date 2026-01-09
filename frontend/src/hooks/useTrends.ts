/**
 * useTrends React hook
 *
 * Manages trend data state for PhotoStats, Photo Pairing, and Pipeline Validation
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import * as trendsService from '../services/trends'
import type {
  PhotoStatsTrendResponse,
  PhotoPairingTrendResponse,
  PipelineValidationTrendResponse,
  DisplayGraphTrendResponse,
  TrendSummaryResponse,
  TrendQueryParams,
  PipelineValidationTrendQueryParams,
  TrendSummaryQueryParams
} from '@/contracts/api/trends-api'
import type { DisplayGraphTrendQueryParams } from '@/services/trends'

// Debounce delay for filter changes
const FILTER_DEBOUNCE_MS = 300

// ============================================================================
// PhotoStats Trends Hook
// ============================================================================

interface UsePhotoStatsTrendsOptions {
  autoFetch?: boolean
  debounceMs?: number
}

interface UsePhotoStatsTrendsReturn {
  data: PhotoStatsTrendResponse | null
  loading: boolean
  error: string | null
  filters: TrendQueryParams
  setFilters: (filters: TrendQueryParams) => void
  refetch: () => Promise<void>
}

export const usePhotoStatsTrends = (
  options: UsePhotoStatsTrendsOptions = {}
): UsePhotoStatsTrendsReturn => {
  const { autoFetch = false, debounceMs = FILTER_DEBOUNCE_MS } = options

  const [data, setData] = useState<PhotoStatsTrendResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFiltersState] = useState<TrendQueryParams>({})

  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const fetchTrends = useCallback(async (params: TrendQueryParams = {}) => {
    setLoading(true)
    setError(null)
    try {
      const response = await trendsService.getPhotoStatsTrends(params)
      setData(response)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load PhotoStats trends'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const setFilters = useCallback((newFilters: TrendQueryParams) => {
    setFiltersState(newFilters)
  }, [])

  const refetch = useCallback(async () => {
    await fetchTrends(filters)
  }, [filters, fetchTrends])

  // Debounced filter effect
  useEffect(() => {
    if (!autoFetch && Object.keys(filters).length === 0) {
      return
    }

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }

    debounceTimerRef.current = setTimeout(() => {
      fetchTrends(filters)
    }, debounceMs)

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, [filters, debounceMs, fetchTrends, autoFetch])

  return {
    data,
    loading,
    error,
    filters,
    setFilters,
    refetch
  }
}

// ============================================================================
// Photo Pairing Trends Hook
// ============================================================================

interface UsePhotoPairingTrendsOptions {
  autoFetch?: boolean
  debounceMs?: number
}

interface UsePhotoPairingTrendsReturn {
  data: PhotoPairingTrendResponse | null
  loading: boolean
  error: string | null
  filters: TrendQueryParams
  setFilters: (filters: TrendQueryParams) => void
  refetch: () => Promise<void>
}

export const usePhotoPairingTrends = (
  options: UsePhotoPairingTrendsOptions = {}
): UsePhotoPairingTrendsReturn => {
  const { autoFetch = false, debounceMs = FILTER_DEBOUNCE_MS } = options

  const [data, setData] = useState<PhotoPairingTrendResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFiltersState] = useState<TrendQueryParams>({})

  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const fetchTrends = useCallback(async (params: TrendQueryParams = {}) => {
    setLoading(true)
    setError(null)
    try {
      const response = await trendsService.getPhotoPairingTrends(params)
      setData(response)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load Photo Pairing trends'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const setFilters = useCallback((newFilters: TrendQueryParams) => {
    setFiltersState(newFilters)
  }, [])

  const refetch = useCallback(async () => {
    await fetchTrends(filters)
  }, [filters, fetchTrends])

  // Debounced filter effect
  useEffect(() => {
    if (!autoFetch && Object.keys(filters).length === 0) {
      return
    }

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }

    debounceTimerRef.current = setTimeout(() => {
      fetchTrends(filters)
    }, debounceMs)

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, [filters, debounceMs, fetchTrends, autoFetch])

  return {
    data,
    loading,
    error,
    filters,
    setFilters,
    refetch
  }
}

// ============================================================================
// Pipeline Validation Trends Hook
// ============================================================================

interface UsePipelineValidationTrendsOptions {
  autoFetch?: boolean
  debounceMs?: number
}

interface UsePipelineValidationTrendsReturn {
  data: PipelineValidationTrendResponse | null
  loading: boolean
  error: string | null
  filters: PipelineValidationTrendQueryParams
  setFilters: (filters: PipelineValidationTrendQueryParams) => void
  refetch: () => Promise<void>
}

export const usePipelineValidationTrends = (
  options: UsePipelineValidationTrendsOptions = {}
): UsePipelineValidationTrendsReturn => {
  const { autoFetch = false, debounceMs = FILTER_DEBOUNCE_MS } = options

  const [data, setData] = useState<PipelineValidationTrendResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFiltersState] = useState<PipelineValidationTrendQueryParams>({})

  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const fetchTrends = useCallback(async (params: PipelineValidationTrendQueryParams = {}) => {
    setLoading(true)
    setError(null)
    try {
      const response = await trendsService.getPipelineValidationTrends(params)
      setData(response)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load Pipeline Validation trends'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const setFilters = useCallback((newFilters: PipelineValidationTrendQueryParams) => {
    setFiltersState(newFilters)
  }, [])

  const refetch = useCallback(async () => {
    await fetchTrends(filters)
  }, [filters, fetchTrends])

  // Debounced filter effect
  useEffect(() => {
    if (!autoFetch && Object.keys(filters).length === 0) {
      return
    }

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }

    debounceTimerRef.current = setTimeout(() => {
      fetchTrends(filters)
    }, debounceMs)

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, [filters, debounceMs, fetchTrends, autoFetch])

  return {
    data,
    loading,
    error,
    filters,
    setFilters,
    refetch
  }
}

// ============================================================================
// Display Graph Trends Hook
// ============================================================================

interface UseDisplayGraphTrendsOptions {
  autoFetch?: boolean
  debounceMs?: number
}

interface UseDisplayGraphTrendsReturn {
  data: DisplayGraphTrendResponse | null
  loading: boolean
  error: string | null
  filters: DisplayGraphTrendQueryParams
  setFilters: (filters: DisplayGraphTrendQueryParams) => void
  refetch: () => Promise<void>
}

export const useDisplayGraphTrends = (
  options: UseDisplayGraphTrendsOptions = {}
): UseDisplayGraphTrendsReturn => {
  const { autoFetch = false, debounceMs = FILTER_DEBOUNCE_MS } = options

  const [data, setData] = useState<DisplayGraphTrendResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFiltersState] = useState<DisplayGraphTrendQueryParams>({})

  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const fetchTrends = useCallback(async (params: DisplayGraphTrendQueryParams = {}) => {
    setLoading(true)
    setError(null)
    try {
      const response = await trendsService.getDisplayGraphTrends(params)
      setData(response)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load Display Graph trends'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const setFilters = useCallback((newFilters: DisplayGraphTrendQueryParams) => {
    setFiltersState(newFilters)
  }, [])

  const refetch = useCallback(async () => {
    await fetchTrends(filters)
  }, [filters, fetchTrends])

  // Debounced filter effect
  useEffect(() => {
    if (!autoFetch && Object.keys(filters).length === 0) {
      return
    }

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }

    debounceTimerRef.current = setTimeout(() => {
      fetchTrends(filters)
    }, debounceMs)

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, [filters, debounceMs, fetchTrends, autoFetch])

  return {
    data,
    loading,
    error,
    filters,
    setFilters,
    refetch
  }
}

// ============================================================================
// Trend Summary Hook
// ============================================================================

interface UseTrendSummaryOptions {
  collectionId?: number
  autoFetch?: boolean
}

interface UseTrendSummaryReturn {
  summary: TrendSummaryResponse | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

export const useTrendSummary = (options: UseTrendSummaryOptions = {}): UseTrendSummaryReturn => {
  const { collectionId, autoFetch = true } = options

  const [summary, setSummary] = useState<TrendSummaryResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params: TrendSummaryQueryParams = {}
      if (collectionId !== undefined) {
        params.collection_id = collectionId
      }
      const response = await trendsService.getTrendSummary(params)
      setSummary(response)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load trend summary'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [collectionId])

  useEffect(() => {
    if (autoFetch) {
      refetch()
    }
  }, [autoFetch, refetch])

  return {
    summary,
    loading,
    error,
    refetch
  }
}

// ============================================================================
// Combined Trends Hook (for main trends view)
// ============================================================================

interface UseTrendsOptions {
  collectionIds?: number[]
  fromDate?: string
  toDate?: string
  limit?: number
  pipelineId?: number
  autoFetch?: boolean
}

interface UseTrendsReturn {
  photoStats: UsePhotoStatsTrendsReturn
  photoPairing: UsePhotoPairingTrendsReturn
  pipelineValidation: UsePipelineValidationTrendsReturn
  summary: UseTrendSummaryReturn
  isLoading: boolean
  hasError: boolean
  fetchAll: () => Promise<void>
}

export const useTrends = (options: UseTrendsOptions = {}): UseTrendsReturn => {
  const { collectionIds, fromDate, toDate, limit, pipelineId, autoFetch = false } = options

  const photoStats = usePhotoStatsTrends({ autoFetch: false })
  const photoPairing = usePhotoPairingTrends({ autoFetch: false })
  const pipelineValidation = usePipelineValidationTrends({ autoFetch: false })
  const summary = useTrendSummary({
    collectionId: collectionIds?.[0],
    autoFetch: false
  })

  const buildBaseFilters = useCallback((): TrendQueryParams => {
    const filters: TrendQueryParams = {}
    if (collectionIds && collectionIds.length > 0) {
      filters.collection_ids = collectionIds.join(',')
    }
    if (fromDate) {
      filters.from_date = fromDate
    }
    if (toDate) {
      filters.to_date = toDate
    }
    if (limit) {
      filters.limit = limit
    }
    return filters
  }, [collectionIds, fromDate, toDate, limit])

  const fetchAll = useCallback(async () => {
    const baseFilters = buildBaseFilters()

    // Fetch all trends in parallel
    await Promise.all([
      photoStats.setFilters(baseFilters),
      photoPairing.setFilters(baseFilters),
      pipelineValidation.setFilters({
        ...baseFilters,
        pipeline_id: pipelineId
      }),
      summary.refetch()
    ])
  }, [buildBaseFilters, photoStats, photoPairing, pipelineValidation, pipelineId, summary])

  // Apply filters when they change
  useEffect(() => {
    if (autoFetch) {
      const baseFilters = buildBaseFilters()
      photoStats.setFilters(baseFilters)
      photoPairing.setFilters(baseFilters)
      pipelineValidation.setFilters({
        ...baseFilters,
        pipeline_id: pipelineId
      })
      summary.refetch()
    }
  }, [collectionIds, fromDate, toDate, limit, pipelineId, autoFetch, buildBaseFilters])

  const isLoading =
    photoStats.loading || photoPairing.loading || pipelineValidation.loading || summary.loading

  const hasError = !!(
    photoStats.error ||
    photoPairing.error ||
    pipelineValidation.error ||
    summary.error
  )

  return {
    photoStats,
    photoPairing,
    pipelineValidation,
    summary,
    isLoading,
    hasError,
    fetchAll
  }
}
