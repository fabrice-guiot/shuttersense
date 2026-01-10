/**
 * useCollections React hook
 *
 * Manages collection state with fetch, create, update, delete operations
 * Includes search with debounce support (Issue #38)
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { toast } from 'sonner'
import * as collectionService from '../services/collections'
import type {
  Collection,
  CollectionCreateRequest,
  CollectionUpdateRequest,
  CollectionListQueryParams,
  CollectionTestResponse,
  CollectionDeleteResponse,
  CollectionStatsResponse
} from '@/contracts/api/collection-api'

// Debounce delay in milliseconds
const SEARCH_DEBOUNCE_MS = 300

interface UseCollectionsOptions {
  autoFetch?: boolean
  debounceMs?: number
}

interface UseCollectionsReturn {
  collections: Collection[]
  loading: boolean
  error: string | null
  search: string
  setSearch: (value: string) => void
  filters: CollectionListQueryParams
  setFilters: (filters: CollectionListQueryParams) => void
  fetchCollections: (filters?: CollectionListQueryParams) => Promise<Collection[]>
  createCollection: (collectionData: CollectionCreateRequest) => Promise<Collection>
  updateCollection: (guid: string, updates: CollectionUpdateRequest) => Promise<Collection>
  deleteCollection: (guid: string, force?: boolean) => Promise<CollectionDeleteResponse | void>
  testCollection: (guid: string) => Promise<CollectionTestResponse>
  refreshCollection: (guid: string, confirm?: boolean) => Promise<any>
  assignPipeline: (collectionGuid: string, pipelineGuid: string) => Promise<Collection>
  clearPipeline: (collectionGuid: string) => Promise<Collection>
}

export const useCollections = (
  options: UseCollectionsOptions | boolean = true
): UseCollectionsReturn => {
  // Handle legacy boolean parameter for backwards compatibility
  const opts = typeof options === 'boolean'
    ? { autoFetch: options, debounceMs: SEARCH_DEBOUNCE_MS }
    : { autoFetch: true, debounceMs: SEARCH_DEBOUNCE_MS, ...options }

  const [collections, setCollections] = useState<Collection[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearchState] = useState('')
  const [filters, setFilters] = useState<CollectionListQueryParams>({})

  // Debounce timer ref
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  /**
   * Fetch collections with optional filters
   */
  const fetchCollections = useCallback(async (queryFilters: CollectionListQueryParams = {}) => {
    setLoading(true)
    setError(null)
    try {
      const data = await collectionService.listCollections(queryFilters)
      setCollections(data)
      return data
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load collections'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Set search term with debounce
   */
  const setSearch = useCallback((value: string) => {
    setSearchState(value)
  }, [])

  /**
   * Create a new collection
   */
  const createCollection = useCallback(async (collectionData: CollectionCreateRequest) => {
    setLoading(true)
    setError(null)
    try {
      const newCollection = await collectionService.createCollection(collectionData)
      setCollections(prev => [...prev, newCollection])
      toast.success('Collection created successfully')
      return newCollection
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to create collection'
      setError(errorMessage)
      toast.error('Failed to create collection', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Update an existing collection
   */
  const updateCollection = useCallback(async (guid: string, updates: CollectionUpdateRequest) => {
    setLoading(true)
    setError(null)
    try {
      const updated = await collectionService.updateCollection(guid, updates)
      setCollections(prev =>
        prev.map(c => c.guid === guid ? updated : c)
      )
      toast.success('Collection updated successfully')
      return updated
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to update collection'
      setError(errorMessage)
      toast.error('Failed to update collection', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Delete a collection
   */
  const deleteCollection = useCallback(async (guid: string, force = false) => {
    setLoading(true)
    setError(null)
    try {
      const response = await collectionService.deleteCollection(guid, force)
      // If response exists, it means collection has results/jobs (status 200)
      if (response) {
        return response
      }
      // No response means deleted successfully (status 204)
      setCollections(prev => prev.filter(c => c.guid !== guid))
      toast.success('Collection deleted successfully')
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to delete collection'
      setError(errorMessage)
      toast.error('Failed to delete collection', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Test collection accessibility
   * Updates local collection state with the returned updated collection
   */
  const testCollection = useCallback(async (guid: string) => {
    try {
      const result = await collectionService.testCollection(guid)
      // Update local state with the updated collection from the response
      if (result.collection) {
        setCollections(prev =>
          prev.map(c => c.guid === guid ? result.collection : c)
        )
      }
      return result
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Accessibility test failed'
      throw new Error(errorMessage)
    }
  }, [])

  /**
   * Refresh collection cache
   */
  const refreshCollection = useCallback(async (guid: string, confirm = false) => {
    try {
      const result = await collectionService.refreshCollection(guid, confirm)
      // Refresh the collection in local state
      await fetchCollections()
      return result
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Cache refresh failed'
      throw new Error(errorMessage)
    }
  }, [fetchCollections])

  /**
   * Assign a pipeline to a collection
   * Stores the pipeline's current version as the pinned version
   */
  const assignPipeline = useCallback(async (collectionGuid: string, pipelineGuid: string) => {
    setLoading(true)
    setError(null)
    try {
      const updated = await collectionService.assignPipeline(collectionGuid, pipelineGuid)
      setCollections(prev =>
        prev.map(c => c.guid === collectionGuid ? updated : c)
      )
      toast.success('Pipeline assigned successfully')
      return updated
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to assign pipeline'
      setError(errorMessage)
      toast.error('Failed to assign pipeline', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Clear pipeline assignment from a collection
   * Collection will use default pipeline at runtime
   */
  const clearPipeline = useCallback(async (collectionGuid: string) => {
    setLoading(true)
    setError(null)
    try {
      const updated = await collectionService.clearPipeline(collectionGuid)
      setCollections(prev =>
        prev.map(c => c.guid === collectionGuid ? updated : c)
      )
      toast.success('Pipeline assignment cleared')
      return updated
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to clear pipeline'
      setError(errorMessage)
      toast.error('Failed to clear pipeline', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  // Debounced search effect
  useEffect(() => {
    // Clear any existing timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }

    // Set new timer for debounced fetch
    debounceTimerRef.current = setTimeout(() => {
      const queryFilters: CollectionListQueryParams = {
        ...filters,
        search: search || undefined  // Don't send empty string
      }
      fetchCollections(queryFilters)
    }, opts.debounceMs)

    // Cleanup on unmount or when dependencies change
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, [search, filters, opts.debounceMs, fetchCollections])

  // Auto-fetch on mount if enabled (initial load without debounce)
  useEffect(() => {
    if (opts.autoFetch) {
      fetchCollections(filters)
    }
    // Only run on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return {
    collections,
    loading,
    error,
    search,
    setSearch,
    filters,
    setFilters,
    fetchCollections,
    createCollection,
    updateCollection,
    deleteCollection,
    testCollection,
    refreshCollection,
    assignPipeline,
    clearPipeline
  }
}

// ============================================================================
// Collection Stats Hook (Issue #37)
// ============================================================================

interface UseCollectionStatsReturn {
  stats: CollectionStatsResponse | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * Hook for fetching collection KPI statistics
 * Stats are independent of any filters - always shows system-wide totals
 */
export const useCollectionStats = (autoFetch = true): UseCollectionStatsReturn => {
  const [stats, setStats] = useState<CollectionStatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await collectionService.getCollectionStats()
      setStats(data)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load collection statistics'
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
