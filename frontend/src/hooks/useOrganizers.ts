/**
 * useOrganizers React hook
 *
 * Manages organizer state with fetch, create, update, delete operations
 * Issue #39 - Calendar Events feature (Phase 9)
 */

import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import * as organizerService from '../services/organizers'
import type {
  Organizer,
  OrganizerCreateRequest,
  OrganizerUpdateRequest,
  OrganizerListParams,
  OrganizerStatsResponse
} from '@/contracts/api/organizer-api'

// ============================================================================
// Main Organizers Hook
// ============================================================================

interface UseOrganizersReturn {
  organizers: Organizer[]
  total: number
  loading: boolean
  error: string | null
  fetchOrganizers: (params?: OrganizerListParams) => Promise<{ items: Organizer[]; total: number }>
  createOrganizer: (organizerData: OrganizerCreateRequest) => Promise<Organizer>
  updateOrganizer: (guid: string, updates: OrganizerUpdateRequest) => Promise<Organizer>
  deleteOrganizer: (guid: string) => Promise<void>
}

export const useOrganizers = (autoFetch = true, initialParams?: OrganizerListParams): UseOrganizersReturn => {
  const [organizers, setOrganizers] = useState<Organizer[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /**
   * Fetch organizers with optional filters
   */
  const fetchOrganizers = useCallback(async (params: OrganizerListParams = {}) => {
    setLoading(true)
    setError(null)
    try {
      const data = await organizerService.listOrganizers(params)
      setOrganizers(data.items)
      setTotal(data.total)
      return data
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load organizers'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Create a new organizer
   */
  const createOrganizer = useCallback(async (organizerData: OrganizerCreateRequest) => {
    setLoading(true)
    setError(null)
    try {
      const newOrganizer = await organizerService.createOrganizer(organizerData)
      setOrganizers(prev => [...prev, newOrganizer])
      setTotal(prev => prev + 1)
      toast.success('Organizer created successfully')
      return newOrganizer
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to create organizer'
      setError(errorMessage)
      toast.error('Failed to create organizer', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Update an existing organizer
   */
  const updateOrganizer = useCallback(async (guid: string, updates: OrganizerUpdateRequest) => {
    setLoading(true)
    setError(null)
    try {
      const updated = await organizerService.updateOrganizer(guid, updates)
      setOrganizers(prev =>
        prev.map(o => o.guid === guid ? updated : o)
      )
      toast.success('Organizer updated successfully')
      return updated
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to update organizer'
      setError(errorMessage)
      toast.error('Failed to update organizer', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Delete an organizer
   */
  const deleteOrganizer = useCallback(async (guid: string) => {
    setLoading(true)
    setError(null)
    try {
      await organizerService.deleteOrganizer(guid)
      setOrganizers(prev => prev.filter(o => o.guid !== guid))
      setTotal(prev => prev - 1)
      toast.success('Organizer deleted successfully')
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to delete organizer'
      setError(errorMessage)
      toast.error('Failed to delete organizer', {
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
      fetchOrganizers(initialParams)
    }
  }, [autoFetch, fetchOrganizers, initialParams])

  return {
    organizers,
    total,
    loading,
    error,
    fetchOrganizers,
    createOrganizer,
    updateOrganizer,
    deleteOrganizer
  }
}

// ============================================================================
// Organizer Stats Hook
// ============================================================================

interface UseOrganizerStatsReturn {
  stats: OrganizerStatsResponse | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * Hook for fetching organizer KPI statistics
 * Returns total count, rated count, and average rating
 */
export const useOrganizerStats = (autoFetch = true): UseOrganizerStatsReturn => {
  const [stats, setStats] = useState<OrganizerStatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await organizerService.getOrganizerStats()
      setStats(data)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load organizer statistics'
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
// Organizers by Category Hook
// ============================================================================

interface UseOrganizersByCategoryReturn {
  organizers: Organizer[]
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * Hook for fetching organizers filtered by category
 * Used when creating/editing events to show compatible organizers
 *
 * @param categoryGuid - Category GUID to filter by (null disables fetching)
 */
export const useOrganizersByCategory = (
  categoryGuid: string | null
): UseOrganizersByCategoryReturn => {
  const [organizers, setOrganizers] = useState<Organizer[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    if (!categoryGuid) {
      setOrganizers([])
      return
    }

    setLoading(true)
    setError(null)
    try {
      const data = await organizerService.getOrganizersByCategory(categoryGuid)
      setOrganizers(data)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load organizers'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [categoryGuid])

  useEffect(() => {
    refetch()
  }, [refetch])

  return { organizers, loading, error, refetch }
}
