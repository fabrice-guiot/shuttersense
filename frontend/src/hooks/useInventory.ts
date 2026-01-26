/**
 * useInventory React hooks
 *
 * Provides hooks for managing inventory configuration and status:
 * - useInventoryConfig: Set/clear inventory configuration
 * - useInventoryStatus: Poll inventory status with auto-refresh
 * - useInventoryFolders: List and paginate inventory folders
 *
 * Issue #107: Cloud Storage Bucket Inventory Import
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { toast } from 'sonner'
import * as inventoryService from '@/services/inventory'
import type {
  InventoryConfig,
  InventorySchedule,
  InventoryStatus,
  InventoryFolder,
  InventoryFolderQueryParams
} from '@/contracts/api/inventory-api'

// ============================================================================
// useInventoryConfig Hook
// ============================================================================

interface UseInventoryConfigReturn {
  /** Set inventory configuration on a connector */
  setConfig: (
    connectorGuid: string,
    config: InventoryConfig,
    schedule: InventorySchedule
  ) => Promise<inventoryService.SetInventoryConfigResponse>
  /** Clear inventory configuration from a connector */
  clearConfig: (connectorGuid: string) => Promise<void>
  /** Whether an operation is in progress */
  loading: boolean
  /** Last error message, if any */
  error: string | null
}

/**
 * Hook for managing inventory configuration on connectors.
 *
 * @example
 * ```tsx
 * const { setConfig, clearConfig, loading } = useInventoryConfig()
 *
 * const handleSave = async () => {
 *   await setConfig(connectorGuid, {
 *     provider: 's3',
 *     destination_bucket: 'inventory-bucket',
 *     source_bucket: 'photos-bucket',
 *     config_name: 'daily-inventory',
 *     format: 'CSV'
 *   }, 'weekly')
 * }
 * ```
 */
export const useInventoryConfig = (): UseInventoryConfigReturn => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const setConfig = useCallback(async (
    connectorGuid: string,
    config: InventoryConfig,
    schedule: InventorySchedule
  ) => {
    setLoading(true)
    setError(null)
    try {
      const result = await inventoryService.setInventoryConfig(connectorGuid, {
        config,
        schedule
      })
      toast.success('Inventory configuration saved')
      return result
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to save inventory configuration'
      setError(errorMessage)
      toast.error('Failed to save inventory configuration', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const clearConfig = useCallback(async (connectorGuid: string) => {
    setLoading(true)
    setError(null)
    try {
      await inventoryService.clearInventoryConfig(connectorGuid)
      toast.success('Inventory configuration cleared')
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to clear inventory configuration'
      setError(errorMessage)
      toast.error('Failed to clear inventory configuration', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return { setConfig, clearConfig, loading, error }
}

// ============================================================================
// useInventoryValidation Hook
// ============================================================================

interface UseInventoryValidationReturn {
  /** Validate inventory configuration */
  validate: (connectorGuid: string) => Promise<inventoryService.ValidateInventoryResponse>
  /** Whether validation is in progress */
  loading: boolean
  /** Last error message, if any */
  error: string | null
}

/**
 * Hook for validating inventory configuration.
 *
 * Triggers manifest.json accessibility check for the configured inventory.
 *
 * @example
 * ```tsx
 * const { validate, loading } = useInventoryValidation()
 *
 * const handleValidate = async () => {
 *   const result = await validate(connectorGuid)
 *   if (result.success) {
 *     console.log('Validation passed:', result.message)
 *   }
 * }
 * ```
 */
export const useInventoryValidation = (): UseInventoryValidationReturn => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const validate = useCallback(async (
    connectorGuid: string
  ): Promise<inventoryService.ValidateInventoryResponse> => {
    setLoading(true)
    setError(null)
    try {
      const result = await inventoryService.validateInventoryConfig(connectorGuid)
      if (result.success) {
        if (result.job_guid) {
          // Agent-side validation - job created
          toast.success('Validation job created', {
            description: 'An agent will validate the inventory configuration'
          })
        } else {
          // Server-side validation succeeded
          toast.success('Inventory configuration validated', {
            description: result.message
          })
        }
      } else {
        // Validation failed
        toast.error('Inventory validation failed', {
          description: result.message
        })
      }
      return result
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to validate inventory configuration'
      setError(errorMessage)
      toast.error('Failed to validate inventory configuration', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return { validate, loading, error }
}

// ============================================================================
// useInventoryStatus Hook
// ============================================================================

interface UseInventoryStatusOptions {
  /** Auto-refresh interval in ms (0 to disable) */
  pollInterval?: number
  /** Whether to start fetching immediately */
  autoFetch?: boolean
}

interface UseInventoryStatusReturn {
  /** Current inventory status */
  status: InventoryStatus | null
  /** Whether status is being fetched */
  loading: boolean
  /** Last error message, if any */
  error: string | null
  /** Manually refresh status */
  refetch: () => Promise<void>
  /** Start polling (if not already started) */
  startPolling: () => void
  /** Stop polling */
  stopPolling: () => void
}

/**
 * Hook for fetching and polling inventory status.
 *
 * Automatically polls while a job is running (validating or importing).
 *
 * @param connectorGuid - Connector GUID to fetch status for
 * @param options - Configuration options
 *
 * @example
 * ```tsx
 * const { status, loading, refetch } = useInventoryStatus(connectorGuid, {
 *   pollInterval: 5000, // Poll every 5s while job is running
 *   autoFetch: true
 * })
 *
 * if (status?.validation_status === 'validated') {
 *   // Show "Import" button
 * }
 * ```
 */
export const useInventoryStatus = (
  connectorGuid: string | null,
  options: UseInventoryStatusOptions = {}
): UseInventoryStatusReturn => {
  const { pollInterval = 5000, autoFetch = true } = options

  const [status, setStatus] = useState<InventoryStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isPolling, setIsPolling] = useState(false)

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const refetch = useCallback(async () => {
    if (!connectorGuid) return

    setLoading(true)
    setError(null)
    try {
      const data = await inventoryService.getInventoryStatus(connectorGuid)
      setStatus(data)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to fetch inventory status'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [connectorGuid])

  const startPolling = useCallback(() => {
    if (pollInterval <= 0 || pollingRef.current) return
    setIsPolling(true)
  }, [pollInterval])

  const stopPolling = useCallback(() => {
    setIsPolling(false)
    if (pollingRef.current) {
      clearInterval(pollingRef.current)
      pollingRef.current = null
    }
  }, [])

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (autoFetch && connectorGuid) {
      refetch()
    }
  }, [autoFetch, connectorGuid, refetch])

  // Poll while validation is pending/validating or job is running
  useEffect(() => {
    const shouldPoll = isPolling ||
      status?.validation_status === 'pending' ||
      status?.validation_status === 'validating' ||
      status?.current_job !== null

    if (shouldPoll && pollInterval > 0 && connectorGuid) {
      pollingRef.current = setInterval(refetch, pollInterval)
      return () => {
        if (pollingRef.current) {
          clearInterval(pollingRef.current)
          pollingRef.current = null
        }
      }
    }
  }, [isPolling, status?.validation_status, status?.current_job, pollInterval, connectorGuid, refetch])

  // Cleanup on unmount
  useEffect(() => {
    return () => stopPolling()
  }, [stopPolling])

  return { status, loading, error, refetch, startPolling, stopPolling }
}

// ============================================================================
// useInventoryFolders Hook
// ============================================================================

interface UseInventoryFoldersOptions {
  /** Initial page size */
  pageSize?: number
  /** Whether to fetch immediately */
  autoFetch?: boolean
  /** Filter params */
  params?: InventoryFolderQueryParams
}

interface UseInventoryFoldersReturn {
  /** List of folders */
  folders: InventoryFolder[]
  /** Total count of folders matching query */
  totalCount: number
  /** Whether more pages exist */
  hasMore: boolean
  /** Whether folders are being fetched */
  loading: boolean
  /** Last error message, if any */
  error: string | null
  /** Manually refresh folder list */
  refetch: () => Promise<void>
  /** Load next page */
  loadMore: () => Promise<void>
  /** Update filter params */
  setParams: (params: InventoryFolderQueryParams) => void
}

/**
 * Hook for listing and paginating inventory folders.
 *
 * @param connectorGuid - Connector GUID to list folders for
 * @param options - Configuration options
 *
 * @example
 * ```tsx
 * const { folders, hasMore, loadMore } = useInventoryFolders(connectorGuid, {
 *   pageSize: 50,
 *   params: { unmapped_only: true }
 * })
 *
 * return (
 *   <FolderList folders={folders} />
 *   {hasMore && <Button onClick={loadMore}>Load More</Button>}
 * )
 * ```
 */
export const useInventoryFolders = (
  connectorGuid: string | null,
  options: UseInventoryFoldersOptions = {}
): UseInventoryFoldersReturn => {
  const { pageSize = 50, autoFetch = true, params: initialParams = {} } = options

  const [folders, setFolders] = useState<InventoryFolder[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [params, setParams] = useState<InventoryFolderQueryParams>(initialParams)
  const [offset, setOffset] = useState(0)

  const refetch = useCallback(async () => {
    if (!connectorGuid) return

    setLoading(true)
    setError(null)
    setOffset(0)
    try {
      const data = await inventoryService.listInventoryFolders(connectorGuid, {
        ...params,
        limit: pageSize,
        offset: 0
      })
      setFolders(data.folders)
      setTotalCount(data.total_count)
      setHasMore(data.has_more)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to fetch inventory folders'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [connectorGuid, params, pageSize])

  const loadMore = useCallback(async () => {
    if (!connectorGuid || !hasMore || loading) return

    setLoading(true)
    setError(null)
    const newOffset = offset + pageSize
    try {
      const data = await inventoryService.listInventoryFolders(connectorGuid, {
        ...params,
        limit: pageSize,
        offset: newOffset
      })
      setFolders(prev => [...prev, ...data.folders])
      setOffset(newOffset)
      setHasMore(data.has_more)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load more folders'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [connectorGuid, hasMore, loading, offset, params, pageSize])

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (autoFetch && connectorGuid) {
      refetch()
    }
  }, [autoFetch, connectorGuid, refetch])

  // Refetch when params change
  useEffect(() => {
    if (connectorGuid) {
      refetch()
    }
  }, [params]) // eslint-disable-line react-hooks/exhaustive-deps

  return {
    folders,
    totalCount,
    hasMore,
    loading,
    error,
    refetch,
    loadMore,
    setParams
  }
}

// ============================================================================
// useInventoryImport Hook
// ============================================================================

interface UseInventoryImportReturn {
  /** Trigger inventory import */
  triggerImport: (connectorGuid: string) => Promise<string>
  /** Whether import is being triggered */
  loading: boolean
  /** Last error message, if any */
  error: string | null
}

/**
 * Hook for triggering inventory imports.
 *
 * @example
 * ```tsx
 * const { triggerImport, loading } = useInventoryImport()
 *
 * const handleImport = async () => {
 *   const jobGuid = await triggerImport(connectorGuid)
 *   console.log('Import started:', jobGuid)
 * }
 * ```
 */
export const useInventoryImport = (): UseInventoryImportReturn => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const triggerImport = useCallback(async (connectorGuid: string): Promise<string> => {
    setLoading(true)
    setError(null)
    try {
      const result = await inventoryService.triggerInventoryImport(connectorGuid)
      toast.success('Inventory import started', {
        description: result.message
      })
      return result.job_guid
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to start inventory import'
      setError(errorMessage)
      toast.error('Failed to start inventory import', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return { triggerImport, loading, error }
}
