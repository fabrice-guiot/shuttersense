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

// Demo mode: use mock data when backend is not running
const DEMO_MODE = true

const MOCK_COLLECTIONS: Collection[] = [
  {
    guid: 'col-001-wedding-2024',
    name: 'Wedding Photos 2024',
    description: 'Sarah & John wedding ceremony and reception',
    connector_guid: 'conn-s3-001',
    connector_name: 'AWS S3 Production',
    type: 'S3',
    state: 'LIVE',
    is_accessible: true,
    accessibility_error: null,
    last_accessibility_check: '2024-03-15T10:30:00Z',
    bound_agent_guid: null,
    bound_agent_name: null,
    pipeline_guid: 'pipe-001',
    pipeline_name: 'Wedding Photo Pipeline',
    pipeline_version: 3,
    created_at: '2024-01-15T08:00:00Z',
    updated_at: '2024-03-15T10:30:00Z',
    config: { bucket: 'wedding-photos-2024', prefix: 'ceremony/' },
    path: 's3://wedding-photos-2024/ceremony/',
    file_count: 2450,
    folder_count: 12,
    total_bytes: 45678901234,
    image_count: 2380,
    video_count: 70,
    min_date: '2024-03-10',
    max_date: '2024-03-15',
    last_analysis_at: '2024-03-15T09:00:00Z'
  },
  {
    guid: 'col-002-studio-portraits',
    name: 'Studio Portraits',
    description: 'Professional headshots and portrait sessions',
    connector_guid: 'conn-local-001',
    connector_name: 'Local Storage',
    type: 'LOCAL',
    state: 'LIVE',
    is_accessible: true,
    accessibility_error: null,
    last_accessibility_check: '2024-03-14T16:00:00Z',
    bound_agent_guid: 'agent-001',
    bound_agent_name: 'Studio Workstation',
    pipeline_guid: null,
    pipeline_name: null,
    pipeline_version: null,
    created_at: '2024-02-01T10:00:00Z',
    updated_at: '2024-03-14T16:00:00Z',
    config: { path: '/data/portraits' },
    path: '/data/portraits',
    file_count: 890,
    folder_count: 45,
    total_bytes: 12345678901,
    image_count: 890,
    video_count: 0,
    min_date: '2024-02-01',
    max_date: '2024-03-14',
    last_analysis_at: '2024-03-14T15:30:00Z'
  },
  {
    guid: 'col-003-event-archive',
    name: 'Event Photography Archive',
    description: 'Corporate events and conferences 2023',
    connector_guid: 'conn-gcs-001',
    connector_name: 'Google Cloud Storage',
    type: 'GCS_BETA',
    state: 'ARCHIVED',
    is_accessible: false,
    accessibility_error: 'Storage bucket access revoked',
    last_accessibility_check: '2024-02-28T12:00:00Z',
    bound_agent_guid: null,
    bound_agent_name: null,
    pipeline_guid: 'pipe-002',
    pipeline_name: 'Event Processing',
    pipeline_version: 1,
    created_at: '2023-06-01T09:00:00Z',
    updated_at: '2024-02-28T12:00:00Z',
    config: { bucket: 'events-archive-2023' },
    path: 'gs://events-archive-2023/',
    file_count: 15000,
    folder_count: 120,
    total_bytes: 234567890123,
    image_count: 14500,
    video_count: 500,
    min_date: '2023-01-15',
    max_date: '2023-12-20',
    last_analysis_at: '2024-01-15T08:00:00Z'
  },
  {
    guid: 'col-004-corporate-headshots',
    name: 'Corporate Headshots',
    description: 'Executive portraits for company website',
    connector_guid: 'conn-smb-001',
    connector_name: 'Office NAS',
    type: 'SMB_BETA',
    state: 'CLOSED',
    is_accessible: null,
    accessibility_error: null,
    last_accessibility_check: null,
    bound_agent_guid: null,
    bound_agent_name: null,
    pipeline_guid: null,
    pipeline_name: null,
    pipeline_version: null,
    created_at: '2024-03-01T14:00:00Z',
    updated_at: '2024-03-01T14:00:00Z',
    config: { share: '//nas/headshots' },
    path: '//nas/headshots',
    file_count: null,
    folder_count: null,
    total_bytes: null,
    image_count: null,
    video_count: null,
    min_date: null,
    max_date: null,
    last_analysis_at: null
  },
  {
    guid: 'col-005-nature-photography',
    name: 'Nature Photography',
    description: 'Wildlife and landscape shots from 2024 expeditions',
    connector_guid: 'conn-s3-002',
    connector_name: 'AWS S3 Archive',
    type: 'S3',
    state: 'LIVE',
    is_accessible: true,
    accessibility_error: null,
    last_accessibility_check: '2024-03-15T08:00:00Z',
    bound_agent_guid: null,
    bound_agent_name: null,
    pipeline_guid: 'pipe-003',
    pipeline_name: 'Nature Analysis',
    pipeline_version: 2,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-03-15T08:00:00Z',
    config: { bucket: 'nature-photos-2024', prefix: 'expeditions/' },
    path: 's3://nature-photos-2024/expeditions/',
    file_count: 5670,
    folder_count: 89,
    total_bytes: 98765432109,
    image_count: 5500,
    video_count: 170,
    min_date: '2024-01-05',
    max_date: '2024-03-10',
    last_analysis_at: '2024-03-15T07:30:00Z'
  }
]

const MOCK_STATS: CollectionStatsResponse = {
  total_collections: 5,
  storage_used: 391358802367,
  storage_used_formatted: '364.5 GB',
  file_count: 24010,
  image_count: 23270
}

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
      // In demo mode, filter mock data locally
      if (DEMO_MODE) {
        let filtered = [...MOCK_COLLECTIONS]
        if (queryFilters.search) {
          const searchLower = queryFilters.search.toLowerCase()
          filtered = filtered.filter(c =>
            c.name.toLowerCase().includes(searchLower) ||
            c.description?.toLowerCase().includes(searchLower)
          )
        }
        if (queryFilters.state) {
          filtered = filtered.filter(c => c.state === queryFilters.state)
        }
        if (queryFilters.type) {
          filtered = filtered.filter(c => c.type === queryFilters.type)
        }
        if (queryFilters.accessible_only) {
          filtered = filtered.filter(c => c.is_accessible === true)
        }
        setCollections(filtered)
        return filtered
      }

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
   * @param guid - Collection GUID
   * @param force - If true, force delete even with existing results/jobs
   * @throws Error if collection has data and force=false (caller should handle to show force-delete dialog)
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

      // Don't show toast for "collection has data" errors - let caller handle with force-delete dialog
      const isHasDataError = errorMessage.includes('analysis result(s)') || errorMessage.includes('active job(s)')
      if (!isHasDataError) {
        toast.error('Failed to delete collection', {
          description: errorMessage
        })
      }
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
  const [stats, setStats] = useState<CollectionStatsResponse | null>(DEMO_MODE ? MOCK_STATS : null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    if (DEMO_MODE) {
      setStats(MOCK_STATS)
      return
    }
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
