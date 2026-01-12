/**
 * usePerformers React hook
 *
 * Manages performer state with fetch, create, update, delete operations
 * Issue #39 - Calendar Events feature (Phase 11)
 */

import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import * as performerService from '../services/performers'
import type {
  Performer,
  PerformerCreateRequest,
  PerformerUpdateRequest,
  PerformerListParams,
  PerformerStatsResponse
} from '@/contracts/api/performer-api'

// ============================================================================
// Main Performers Hook
// ============================================================================

interface UsePerformersReturn {
  performers: Performer[]
  total: number
  loading: boolean
  error: string | null
  fetchPerformers: (params?: PerformerListParams) => Promise<{ items: Performer[]; total: number }>
  createPerformer: (performerData: PerformerCreateRequest) => Promise<Performer>
  updatePerformer: (guid: string, updates: PerformerUpdateRequest) => Promise<Performer>
  deletePerformer: (guid: string) => Promise<void>
}

export const usePerformers = (autoFetch = true, initialParams?: PerformerListParams): UsePerformersReturn => {
  const [performers, setPerformers] = useState<Performer[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /**
   * Fetch performers with optional filters
   */
  const fetchPerformers = useCallback(async (params: PerformerListParams = {}) => {
    setLoading(true)
    setError(null)
    try {
      const data = await performerService.listPerformers(params)
      setPerformers(data.items)
      setTotal(data.total)
      return data
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load performers'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Create a new performer
   */
  const createPerformer = useCallback(async (performerData: PerformerCreateRequest) => {
    setLoading(true)
    setError(null)
    try {
      const newPerformer = await performerService.createPerformer(performerData)
      setPerformers(prev => [...prev, newPerformer])
      setTotal(prev => prev + 1)
      toast.success('Performer created successfully')
      return newPerformer
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to create performer'
      setError(errorMessage)
      toast.error('Failed to create performer', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Update an existing performer
   */
  const updatePerformer = useCallback(async (guid: string, updates: PerformerUpdateRequest) => {
    setLoading(true)
    setError(null)
    try {
      const updated = await performerService.updatePerformer(guid, updates)
      setPerformers(prev =>
        prev.map(p => p.guid === guid ? updated : p)
      )
      toast.success('Performer updated successfully')
      return updated
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to update performer'
      setError(errorMessage)
      toast.error('Failed to update performer', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Delete a performer
   */
  const deletePerformer = useCallback(async (guid: string) => {
    setLoading(true)
    setError(null)
    try {
      await performerService.deletePerformer(guid)
      setPerformers(prev => prev.filter(p => p.guid !== guid))
      setTotal(prev => prev - 1)
      toast.success('Performer deleted successfully')
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to delete performer'
      setError(errorMessage)
      toast.error('Failed to delete performer', {
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
      fetchPerformers(initialParams)
    }
  }, [autoFetch, fetchPerformers, initialParams])

  return {
    performers,
    total,
    loading,
    error,
    fetchPerformers,
    createPerformer,
    updatePerformer,
    deletePerformer
  }
}

// ============================================================================
// Performer Stats Hook
// ============================================================================

interface UsePerformerStatsReturn {
  stats: PerformerStatsResponse | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * Hook for fetching performer KPI statistics
 * Returns total count, instagram count, and website count
 */
export const usePerformerStats = (autoFetch = true): UsePerformerStatsReturn => {
  const [stats, setStats] = useState<PerformerStatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await performerService.getPerformerStats()
      setStats(data)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load performer statistics'
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
// Performers by Category Hook
// ============================================================================

interface UsePerformersByCategoryReturn {
  performers: Performer[]
  loading: boolean
  error: string | null
  refetch: (search?: string) => Promise<void>
}

/**
 * Hook for fetching performers filtered by category
 * Used when creating/editing events to show compatible performers
 *
 * @param categoryGuid - Category GUID to filter by (null disables fetching)
 */
export const usePerformersByCategory = (
  categoryGuid: string | null
): UsePerformersByCategoryReturn => {
  const [performers, setPerformers] = useState<Performer[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async (search?: string) => {
    if (!categoryGuid) {
      setPerformers([])
      return
    }

    setLoading(true)
    setError(null)
    try {
      const data = await performerService.getPerformersByCategory(categoryGuid, search)
      setPerformers(data)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load performers'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [categoryGuid])

  useEffect(() => {
    refetch()
  }, [refetch])

  return { performers, loading, error, refetch }
}
