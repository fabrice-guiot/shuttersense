/**
 * React hook for release manifest management (super admin only).
 *
 * Provides state management and API integration for creating,
 * listing, updating, and deleting release manifests.
 *
 * Part of Issue #90 - Distributed Agent Architecture
 */

import { useState, useCallback, useEffect } from 'react'
import type {
  ReleaseManifest,
  ReleaseManifestCreateRequest,
  ReleaseManifestUpdateRequest,
  ReleaseManifestStatsResponse,
  ReleaseManifestListOptions,
} from '@/contracts/api/release-manifests-api'
import {
  listManifests as apiListManifests,
  getManifestStats as apiGetManifestStats,
  createManifest as apiCreateManifest,
  updateManifest as apiUpdateManifest,
  deleteManifest as apiDeleteManifest,
} from '@/services/release-manifests-api'

// ============================================================================
// Types
// ============================================================================

interface UseReleaseManifestsOptions {
  /** Whether to only show active manifests */
  activeOnly?: boolean
  /** Filter by platform */
  platform?: string
  /** Filter by version */
  version?: string
  /** Only return the most recent manifest per version (default: true) */
  latestOnly?: boolean
  /** Whether to auto-fetch manifests on mount */
  autoFetch?: boolean
}

interface UseReleaseManifestsReturn {
  /** List of release manifests */
  manifests: ReleaseManifest[]
  /** Total number of manifests (matching filters) */
  totalCount: number
  /** Number of active manifests (matching filters) */
  activeCount: number
  /** Manifest statistics */
  stats: ReleaseManifestStatsResponse | null
  /** Loading state */
  loading: boolean
  /** Error message if any */
  error: string | null
  /** Refresh manifests list */
  refresh: () => Promise<void>
  /** Create a new manifest */
  createManifest: (data: ReleaseManifestCreateRequest) => Promise<ReleaseManifest>
  /** Update an existing manifest */
  updateManifest: (guid: string, data: ReleaseManifestUpdateRequest) => Promise<ReleaseManifest>
  /** Delete a manifest */
  deleteManifest: (guid: string) => Promise<void>
  /** Fetch manifest stats */
  fetchStats: () => Promise<void>
}

// ============================================================================
// Hook Implementation
// ============================================================================

export function useReleaseManifests(
  options: UseReleaseManifestsOptions = {}
): UseReleaseManifestsReturn {
  const { activeOnly = false, platform, version, latestOnly = true, autoFetch = true } = options

  const [manifests, setManifests] = useState<ReleaseManifest[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [activeCount, setActiveCount] = useState(0)
  const [stats, setStats] = useState<ReleaseManifestStatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /**
   * Build filter options from hook options.
   */
  const buildFilterOptions = useCallback((): ReleaseManifestListOptions => {
    const filterOptions: ReleaseManifestListOptions = {}
    if (activeOnly) filterOptions.active_only = true
    if (platform) filterOptions.platform = platform
    if (version) filterOptions.version = version
    if (latestOnly) filterOptions.latest_only = true
    return filterOptions
  }, [activeOnly, platform, version, latestOnly])

  /**
   * Fetch manifests list from API.
   */
  const fetchManifests = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await apiListManifests(buildFilterOptions())
      setManifests(response.manifests)
      setTotalCount(response.total_count)
      setActiveCount(response.active_count)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch release manifests'
      setError(message)
      console.error('[useReleaseManifests] Failed to fetch manifests:', err)
    } finally {
      setLoading(false)
    }
  }, [buildFilterOptions])

  /**
   * Fetch manifest statistics from API.
   */
  const fetchStats = useCallback(async () => {
    try {
      const response = await apiGetManifestStats()
      setStats(response)
    } catch (err) {
      console.error('[useReleaseManifests] Failed to fetch stats:', err)
    }
  }, [])

  /**
   * Create a new manifest.
   */
  const createManifest = useCallback(
    async (data: ReleaseManifestCreateRequest): Promise<ReleaseManifest> => {
      setError(null)

      try {
        const result = await apiCreateManifest(data)
        // Refresh the list after creating
        await fetchManifests()
        await fetchStats()
        return result
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to create release manifest'
        setError(message)
        throw err
      }
    },
    [fetchManifests, fetchStats]
  )

  /**
   * Update an existing manifest.
   */
  const updateManifest = useCallback(
    async (guid: string, data: ReleaseManifestUpdateRequest): Promise<ReleaseManifest> => {
      setError(null)

      try {
        const result = await apiUpdateManifest(guid, data)
        // Refresh the list after updating
        await fetchManifests()
        await fetchStats()
        return result
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to update release manifest'
        setError(message)
        throw err
      }
    },
    [fetchManifests, fetchStats]
  )

  /**
   * Delete a manifest.
   */
  const deleteManifest = useCallback(
    async (guid: string): Promise<void> => {
      setError(null)

      try {
        await apiDeleteManifest(guid)
        // Refresh the list after deleting
        await fetchManifests()
        await fetchStats()
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to delete release manifest'
        setError(message)
        throw err
      }
    },
    [fetchManifests, fetchStats]
  )

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (autoFetch) {
      fetchManifests()
      fetchStats()
    }
  }, [autoFetch, fetchManifests, fetchStats])

  return {
    manifests,
    totalCount,
    activeCount,
    stats,
    loading,
    error,
    refresh: fetchManifests,
    createManifest,
    updateManifest,
    deleteManifest,
    fetchStats,
  }
}

// ============================================================================
// Stats-only Hook
// ============================================================================

/**
 * Hook for fetching release manifest statistics only.
 * Useful for TopHeader KPIs without loading full manifest list.
 */
export function useReleaseManifestStats() {
  const [stats, setStats] = useState<ReleaseManifestStatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchStats = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await apiGetManifestStats()
      setStats(response)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to fetch release manifest stats'
      setError(message)
      console.error('[useReleaseManifestStats] Failed to fetch stats:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  return { stats, loading, error, refetch: fetchStats }
}
