/**
 * Tests for useInventory hooks
 *
 * Issue #107: Cloud Storage Bucket Inventory Import
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import {
  useInventoryConfig,
  useInventoryValidation,
  useInventoryStatus,
  useInventoryFolders,
  useAllInventoryFolders,
  useInventoryImport,
} from '../useInventory'
import * as inventoryService from '@/services/inventory'
import type {
  InventoryConfig,
  InventoryStatus,
  InventoryFolder,
} from '@/contracts/api/inventory-api'

// Mock the service
vi.mock('@/services/inventory')

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}))

describe('useInventoryConfig', () => {
  const mockConfig: InventoryConfig = {
    provider: 's3',
    destination_bucket: 'inventory-bucket',
    source_bucket: 'photos-bucket',
    config_name: 'daily-inventory',
    format: 'CSV',
  }

  const mockSetResponse: inventoryService.SetInventoryConfigResponse = {
    message: 'Inventory configuration saved',
    validation_status: 'pending',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(inventoryService.setInventoryConfig).mockResolvedValue(mockSetResponse)
    vi.mocked(inventoryService.clearInventoryConfig).mockResolvedValue(undefined)
  })

  it('should set inventory config', async () => {
    const { result } = renderHook(() => useInventoryConfig())

    let response: inventoryService.SetInventoryConfigResponse | undefined

    await act(async () => {
      response = await result.current.setConfig('con_123', mockConfig, 'daily')
    })

    expect(response).toEqual(mockSetResponse)
    expect(inventoryService.setInventoryConfig).toHaveBeenCalledWith('con_123', {
      config: mockConfig,
      schedule: 'daily',
    })
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBe(null)
  })

  it('should clear inventory config', async () => {
    const { result } = renderHook(() => useInventoryConfig())

    await act(async () => {
      await result.current.clearConfig('con_123')
    })

    expect(inventoryService.clearInventoryConfig).toHaveBeenCalledWith('con_123')
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBe(null)
  })

  it('should handle set config error', async () => {
    const error = new Error('Validation error')
    ;(error as any).userMessage = 'Invalid bucket name'
    vi.mocked(inventoryService.setInventoryConfig).mockRejectedValue(error)

    const { result } = renderHook(() => useInventoryConfig())

    await act(async () => {
      try {
        await result.current.setConfig('con_123', mockConfig, 'daily')
        expect.unreachable('Should have thrown')
      } catch (err) {
        // Expected
      }
    })

    expect(result.current.error).toBe('Invalid bucket name')
  })

  it('should handle clear config error', async () => {
    const error = new Error('Not found')
    ;(error as any).userMessage = 'Connector not found'
    vi.mocked(inventoryService.clearInventoryConfig).mockRejectedValue(error)

    const { result } = renderHook(() => useInventoryConfig())

    await act(async () => {
      try {
        await result.current.clearConfig('con_invalid')
        expect.unreachable('Should have thrown')
      } catch (err) {
        // Expected
      }
    })

    expect(result.current.error).toBe('Connector not found')
  })
})

describe('useInventoryValidation', () => {
  const mockValidationSuccess: inventoryService.ValidateInventoryResponse = {
    success: true,
    message: 'Inventory configuration is valid',
    validation_status: 'validated',
  }

  const mockValidationJobCreated: inventoryService.ValidateInventoryResponse = {
    success: true,
    message: 'Validation job created',
    validation_status: 'validating',
    job_guid: 'job_123',
  }

  const mockValidationFailure: inventoryService.ValidateInventoryResponse = {
    success: false,
    message: 'manifest.json not found',
    validation_status: 'failed',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should validate successfully (server-side)', async () => {
    vi.mocked(inventoryService.validateInventoryConfig).mockResolvedValue(mockValidationSuccess)

    const { result } = renderHook(() => useInventoryValidation())

    let response: inventoryService.ValidateInventoryResponse | undefined

    await act(async () => {
      response = await result.current.validate('con_123')
    })

    expect(response).toEqual(mockValidationSuccess)
    expect(inventoryService.validateInventoryConfig).toHaveBeenCalledWith('con_123')
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBe(null)
  })

  it('should validate successfully (agent job created)', async () => {
    vi.mocked(inventoryService.validateInventoryConfig).mockResolvedValue(mockValidationJobCreated)

    const { result } = renderHook(() => useInventoryValidation())

    let response: inventoryService.ValidateInventoryResponse | undefined

    await act(async () => {
      response = await result.current.validate('con_123')
    })

    expect(response).toEqual(mockValidationJobCreated)
    expect(response?.job_guid).toBe('job_123')
  })

  it('should handle validation failure', async () => {
    vi.mocked(inventoryService.validateInventoryConfig).mockResolvedValue(mockValidationFailure)

    const { result } = renderHook(() => useInventoryValidation())

    let response: inventoryService.ValidateInventoryResponse | undefined

    await act(async () => {
      response = await result.current.validate('con_123')
    })

    expect(response).toEqual(mockValidationFailure)
    expect(response?.success).toBe(false)
  })

  it('should handle validation error', async () => {
    const error = new Error('Network error')
    ;(error as any).userMessage = 'Failed to validate'
    vi.mocked(inventoryService.validateInventoryConfig).mockRejectedValue(error)

    const { result } = renderHook(() => useInventoryValidation())

    await act(async () => {
      try {
        await result.current.validate('con_123')
        expect.unreachable('Should have thrown')
      } catch (err) {
        // Expected
      }
    })

    expect(result.current.error).toBe('Failed to validate')
  })
})

describe('useInventoryStatus', () => {
  const mockStatus: InventoryStatus = {
    validation_status: 'validated',
    validation_error: null,
    latest_manifest: null,
    last_import_at: null,
    next_scheduled_at: null,
    folder_count: 150,
    mapped_folder_count: 125,
    mappable_folder_count: 25,
    current_job: null,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(inventoryService.getInventoryStatus).mockResolvedValue(mockStatus)
  })

  it('should fetch status on mount', async () => {
    const { result } = renderHook(() => useInventoryStatus('con_123'))

    expect(result.current.loading).toBe(true)
    expect(result.current.status).toBe(null)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.status).toEqual(mockStatus)
    expect(result.current.error).toBe(null)
    expect(inventoryService.getInventoryStatus).toHaveBeenCalledWith('con_123')
  })

  it('should not fetch when connectorGuid is null', async () => {
    const { result } = renderHook(() => useInventoryStatus(null))

    expect(result.current.loading).toBe(false)
    expect(result.current.status).toBe(null)
    expect(inventoryService.getInventoryStatus).not.toHaveBeenCalled()
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useInventoryStatus('con_123', { autoFetch: false }))

    expect(result.current.loading).toBe(false)
    expect(result.current.status).toBe(null)
    expect(inventoryService.getInventoryStatus).not.toHaveBeenCalled()
  })

  it('should refetch status', async () => {
    const { result } = renderHook(() => useInventoryStatus('con_123'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    vi.clearAllMocks()

    await act(async () => {
      await result.current.refetch()
    })

    expect(inventoryService.getInventoryStatus).toHaveBeenCalledWith('con_123')
  })

  it('should handle fetch error', async () => {
    const error = new Error('Network error')
    ;(error as any).userMessage = 'Failed to fetch status'
    vi.mocked(inventoryService.getInventoryStatus).mockRejectedValue(error)

    const { result } = renderHook(() => useInventoryStatus('con_123'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to fetch status')
    expect(result.current.status).toBe(null)
  })
})

/** Helper to create an InventoryFolder with sensible defaults */
function makeInventoryFolder(overrides: Partial<InventoryFolder> & { path: string }): InventoryFolder {
  return {
    guid: overrides.guid ?? `fld_${overrides.path.replace(/\//g, '_')}`,
    path: overrides.path,
    object_count: overrides.object_count ?? 0,
    total_size_bytes: overrides.total_size_bytes ?? 0,
    deepest_modified: overrides.deepest_modified ?? null,
    discovered_at: overrides.discovered_at ?? '2026-01-15T10:00:00Z',
    collection_guid: overrides.collection_guid ?? null,
    suggested_name: overrides.suggested_name ?? null,
    is_mappable: overrides.is_mappable ?? true,
  }
}

describe('useInventoryFolders', () => {
  const mockFolders: InventoryFolder[] = [
    makeInventoryFolder({
      path: '/events/2024/soccer',
      object_count: 150,
      total_size_bytes: 524288000,
      collection_guid: null,
      is_mappable: true,
    }),
    makeInventoryFolder({
      path: '/events/2024/music',
      object_count: 200,
      total_size_bytes: 1048576000,
      collection_guid: 'col_123',
      is_mappable: false,
    }),
  ]

  const mockFoldersResponse = {
    folders: mockFolders,
    total_count: 50,
    has_more: true,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(inventoryService.listInventoryFolders).mockResolvedValue(mockFoldersResponse)
  })

  it('should fetch folders on mount', async () => {
    const { result } = renderHook(() => useInventoryFolders('con_123'))

    expect(result.current.loading).toBe(true)
    expect(result.current.folders).toEqual([])

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.folders).toHaveLength(2)
    expect(result.current.totalCount).toBe(50)
    expect(result.current.hasMore).toBe(true)
    expect(inventoryService.listInventoryFolders).toHaveBeenCalledWith('con_123', {
      limit: 50,
      offset: 0,
    })
  })

  it('should not fetch when connectorGuid is null', async () => {
    const { result } = renderHook(() => useInventoryFolders(null))

    expect(result.current.loading).toBe(false)
    expect(result.current.folders).toEqual([])
    expect(inventoryService.listInventoryFolders).not.toHaveBeenCalled()
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    // Using null because the hook's params-change effect bypasses autoFetch when connectorGuid is truthy
    const { result } = renderHook(() => useInventoryFolders(null, { autoFetch: false }))

    expect(result.current.loading).toBe(false)
    expect(result.current.folders).toEqual([])
    expect(inventoryService.listInventoryFolders).not.toHaveBeenCalled()
  })

  it('should fetch with custom page size and params', async () => {
    const { result } = renderHook(() =>
      useInventoryFolders('con_123', {
        pageSize: 100,
        params: { unmapped_only: true },
      })
    )

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(inventoryService.listInventoryFolders).toHaveBeenCalledWith('con_123', {
      limit: 100,
      offset: 0,
      unmapped_only: true,
    })
  })

  it('should load more folders', async () => {
    const { result } = renderHook(() => useInventoryFolders('con_123', { pageSize: 50 }))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.folders).toHaveLength(2)

    const moreFolders = {
      folders: [
        makeInventoryFolder({
          path: '/events/2024/theater',
          object_count: 75,
          total_size_bytes: 262144000,
          collection_guid: null,
          is_mappable: true,
        }),
      ],
      total_count: 50,
      has_more: false,
    }

    vi.mocked(inventoryService.listInventoryFolders).mockResolvedValue(moreFolders)

    await act(async () => {
      await result.current.loadMore()
    })

    expect(result.current.folders).toHaveLength(3)
    expect(result.current.hasMore).toBe(false)
    expect(inventoryService.listInventoryFolders).toHaveBeenCalledWith('con_123', {
      limit: 50,
      offset: 50,
    })
  })

  it('should not load more when hasMore is false', async () => {
    vi.mocked(inventoryService.listInventoryFolders).mockResolvedValue({
      ...mockFoldersResponse,
      has_more: false,
    })

    const { result } = renderHook(() => useInventoryFolders('con_123'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    vi.clearAllMocks()

    await act(async () => {
      await result.current.loadMore()
    })

    expect(inventoryService.listInventoryFolders).not.toHaveBeenCalled()
  })

  it('should update params and refetch', async () => {
    const { result } = renderHook(() => useInventoryFolders('con_123'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    vi.clearAllMocks()

    act(() => {
      result.current.setParams({ unmapped_only: true })
    })

    await waitFor(() => {
      expect(inventoryService.listInventoryFolders).toHaveBeenCalledWith('con_123', {
        limit: 50,
        offset: 0,
        unmapped_only: true,
      })
    })
  })
})

describe('useAllInventoryFolders', () => {
  const mockPage1: InventoryFolder[] = Array.from({ length: 100 }, (_, i) =>
    makeInventoryFolder({
      guid: `fld_${i}`,
      path: `/folder${i}`,
      object_count: 10,
      total_size_bytes: 1024000,
      collection_guid: null,
      is_mappable: true,
    })
  )

  const mockPage2: InventoryFolder[] = Array.from({ length: 50 }, (_, i) =>
    makeInventoryFolder({
      guid: `fld_${i + 100}`,
      path: `/folder${i + 100}`,
      object_count: 10,
      total_size_bytes: 1024000,
      collection_guid: null,
      is_mappable: true,
    })
  )

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should fetch all folders with auto-pagination', async () => {
    vi.mocked(inventoryService.listInventoryFolders)
      .mockResolvedValueOnce({
        folders: mockPage1,
        total_count: 150,
        has_more: true,
      })
      .mockResolvedValueOnce({
        folders: mockPage2,
        total_count: 150,
        has_more: false,
      })

    const { result } = renderHook(() =>
      useAllInventoryFolders('con_123', { autoFetch: true, pageSize: 100 })
    )

    expect(result.current.loading).toBe(true)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.folders).toHaveLength(150)
    expect(result.current.totalCount).toBe(150)
    expect(result.current.progress).toBe(100)
    expect(inventoryService.listInventoryFolders).toHaveBeenCalledTimes(2)
  })

  it('should handle empty folder list', async () => {
    vi.mocked(inventoryService.listInventoryFolders).mockResolvedValue({
      folders: [],
      total_count: 0,
      has_more: false,
    })

    const { result } = renderHook(() =>
      useAllInventoryFolders('con_123', { autoFetch: true })
    )

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.folders).toEqual([])
    expect(result.current.totalCount).toBe(0)
    expect(result.current.progress).toBe(100)
  })

  it('should update progress during pagination', async () => {
    vi.mocked(inventoryService.listInventoryFolders)
      .mockResolvedValueOnce({
        folders: mockPage1,
        total_count: 150,
        has_more: true,
      })
      .mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(
              () =>
                resolve({
                  folders: mockPage2,
                  total_count: 150,
                  has_more: false,
                }),
              100
            )
          )
      )

    const { result } = renderHook(() =>
      useAllInventoryFolders('con_123', { autoFetch: true, pageSize: 100 })
    )

    await waitFor(() => {
      expect(result.current.progress).toBeGreaterThan(0)
    })

    await waitFor(
      () => {
        expect(result.current.loading).toBe(false)
      },
      { timeout: 5000 }
    )

    expect(result.current.progress).toBe(100)
  })

  it('should handle fetch error', async () => {
    const error = new Error('Network error')
    ;(error as any).userMessage = 'Failed to fetch folders'
    vi.mocked(inventoryService.listInventoryFolders).mockRejectedValue(error)

    const { result } = renderHook(() =>
      useAllInventoryFolders('con_123', { autoFetch: true })
    )

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to fetch folders')
    expect(result.current.folders).toEqual([])
  })

  it('should not fetch when connectorGuid is null', async () => {
    const { result } = renderHook(() =>
      useAllInventoryFolders(null, { autoFetch: true })
    )

    expect(result.current.loading).toBe(false)
    expect(result.current.folders).toEqual([])
    expect(inventoryService.listInventoryFolders).not.toHaveBeenCalled()
  })
})

describe('useInventoryImport', () => {
  const mockImportResponse = {
    job_guid: 'job_123',
    message: 'Inventory import started',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(inventoryService.triggerInventoryImport).mockResolvedValue(mockImportResponse)
  })

  it('should trigger import', async () => {
    const { result } = renderHook(() => useInventoryImport())

    let jobGuid: string | undefined

    await act(async () => {
      jobGuid = await result.current.triggerImport('con_123')
    })

    expect(jobGuid).toBe('job_123')
    expect(inventoryService.triggerInventoryImport).toHaveBeenCalledWith('con_123')
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBe(null)
  })

  it('should handle import error', async () => {
    const error = new Error('Import failed')
    ;(error as any).userMessage = 'No agent available'
    vi.mocked(inventoryService.triggerInventoryImport).mockRejectedValue(error)

    const { result } = renderHook(() => useInventoryImport())

    await act(async () => {
      try {
        await result.current.triggerImport('con_123')
        expect.unreachable('Should have thrown')
      } catch (err) {
        // Expected
      }
    })

    expect(result.current.error).toBe('No agent available')
  })
})
