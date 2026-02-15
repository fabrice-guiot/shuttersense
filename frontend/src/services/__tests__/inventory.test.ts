import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'
import {
  setInventoryConfig,
  clearInventoryConfig,
  getInventoryStatus,
  listInventoryFolders,
  getInventoryFolder,
  validateInventoryConfig,
  triggerInventoryImport,
  createCollectionsFromInventory,
} from '@/services/inventory'
import type {
  InventoryConfig,
  InventorySchedule,
  InventoryStatus,
  InventoryFolder,
  InventoryFolderList,
  InventoryFolderQueryParams,
  FolderToCollectionMapping,
  CreateCollectionsFromInventoryResponse,
} from '@/contracts/api/inventory-api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

describe('Inventory Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('setInventoryConfig', () => {
    test('sets S3 inventory configuration', async () => {
      const connectorGuid = 'con_01hgw2bbg00000000000000001'
      const config: InventoryConfig = {
        provider: 's3',
        destination_bucket: 'my-inventory-bucket',
        destination_prefix: 'inventories/',
        source_bucket: 'my-photos-bucket',
        config_name: 'daily-inventory',
        format: 'Parquet',
      }
      const schedule: InventorySchedule = 'daily'

      const mockResponse = {
        message: 'Inventory configuration saved',
        validation_status: 'pending',
        job_guid: 'job_123',
      }

      vi.mocked(api.put).mockResolvedValue({ data: mockResponse })

      const result = await setInventoryConfig(connectorGuid, { config, schedule })

      expect(api.put).toHaveBeenCalledWith(
        `/connectors/${encodeURIComponent(connectorGuid)}/inventory/config`,
        { config, schedule }
      )
      expect(result).toEqual(mockResponse)
    })

    test('sets GCS inventory configuration', async () => {
      const connectorGuid = 'con_01hgw2bbg00000000000000001'
      const config: InventoryConfig = {
        provider: 'gcs',
        destination_bucket: 'my-inventory-bucket',
        report_config_name: 'daily-report',
        format: 'CSV',
      }
      const schedule: InventorySchedule = 'weekly'

      const mockResponse = {
        message: 'Inventory configuration saved',
        validation_status: 'pending',
      }

      vi.mocked(api.put).mockResolvedValue({ data: mockResponse })

      const result = await setInventoryConfig(connectorGuid, { config, schedule })

      expect(api.put).toHaveBeenCalledWith(
        `/connectors/${encodeURIComponent(connectorGuid)}/inventory/config`,
        { config, schedule }
      )
      expect(result).toEqual(mockResponse)
    })

    test('throws error for invalid connector GUID', async () => {
      const config: InventoryConfig = {
        provider: 's3',
        destination_bucket: 'bucket',
        source_bucket: 'bucket2',
        config_name: 'config',
        format: 'CSV',
      }

      await expect(
        setInventoryConfig('invalid_guid', { config, schedule: 'manual' })
      ).rejects.toThrow('Invalid GUID format')
    })
  })

  describe('clearInventoryConfig', () => {
    test('clears inventory configuration', async () => {
      const connectorGuid = 'con_01hgw2bbg00000000000000001'

      vi.mocked(api.delete).mockResolvedValue({ data: null })

      await clearInventoryConfig(connectorGuid)

      expect(api.delete).toHaveBeenCalledWith(
        `/connectors/${encodeURIComponent(connectorGuid)}/inventory/config`
      )
    })
  })

  describe('getInventoryStatus', () => {
    test('fetches inventory status', async () => {
      const connectorGuid = 'con_01hgw2bbg00000000000000001'

      const mockResponse: InventoryStatus = {
        validation_status: 'validated',
        validation_error: null,
        latest_manifest: '2026-01-01/manifest.json',
        last_import_at: '2026-01-01T12:00:00Z',
        next_scheduled_at: '2026-01-02T00:00:00Z',
        folder_count: 42,
        mapped_folder_count: 10,
        mappable_folder_count: 32,
        current_job: null,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await getInventoryStatus(connectorGuid)

      expect(api.get).toHaveBeenCalledWith(
        `/connectors/${encodeURIComponent(connectorGuid)}/inventory/status`
      )
      expect(result).toEqual(mockResponse)
    })
  })

  describe('listInventoryFolders', () => {
    test('lists folders without filters', async () => {
      const connectorGuid = 'con_01hgw2bbg00000000000000001'

      const mockResponse: InventoryFolderList = {
        folders: [
          {
            guid: 'fld_01hgw2bbg00000000000000001',
            path: 'events/2026/',
            object_count: 100,
            total_size_bytes: 1024000,
            deepest_modified: '2026-01-01T00:00:00Z',
            discovered_at: '2026-01-01T00:00:00Z',
            collection_guid: null,
            suggested_name: 'Events 2026',
            is_mappable: true,
          },
        ],
        total_count: 1,
        has_more: false,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await listInventoryFolders(connectorGuid)

      expect(api.get).toHaveBeenCalledWith(
        `/connectors/${encodeURIComponent(connectorGuid)}/inventory/folders`,
        { params: {} }
      )
      expect(result).toEqual(mockResponse)
    })

    test('lists folders with all query parameters', async () => {
      const connectorGuid = 'con_01hgw2bbg00000000000000001'
      const params: InventoryFolderQueryParams = {
        path_prefix: 'events/',
        unmapped_only: true,
        limit: 50,
        offset: 10,
      }

      const mockResponse: InventoryFolderList = {
        folders: [],
        total_count: 0,
        has_more: false,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await listInventoryFolders(connectorGuid, params)

      expect(api.get).toHaveBeenCalledWith(
        `/connectors/${encodeURIComponent(connectorGuid)}/inventory/folders`,
        {
          params: {
            path_prefix: 'events/',
            unmapped_only: true,
            limit: 50,
            offset: 10,
          },
        }
      )
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getInventoryFolder', () => {
    test('fetches a single folder by GUID', async () => {
      const folderGuid = 'fld_01hgw2bbg00000000000000001'

      const mockResponse: InventoryFolder = {
        guid: folderGuid,
        path: 'events/2026/01/',
        object_count: 50,
        total_size_bytes: 512000,
        deepest_modified: '2026-01-15T00:00:00Z',
        discovered_at: '2026-01-01T00:00:00Z',
        collection_guid: null,
        suggested_name: 'Events January 2026',
        is_mappable: true,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await getInventoryFolder(folderGuid)

      expect(api.get).toHaveBeenCalledWith(`/inventory/folders/${encodeURIComponent(folderGuid)}`)
      expect(result).toEqual(mockResponse)
    })

    test('throws error for invalid folder GUID', async () => {
      await expect(getInventoryFolder('invalid_guid')).rejects.toThrow('Invalid GUID format')
    })
  })

  describe('validateInventoryConfig', () => {
    test('validates inventory configuration', async () => {
      const connectorGuid = 'con_01hgw2bbg00000000000000001'

      const mockResponse = {
        success: true,
        message: 'Validation successful',
        validation_status: 'validated',
        job_guid: 'job_123',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await validateInventoryConfig(connectorGuid)

      expect(api.post).toHaveBeenCalledWith(
        `/connectors/${encodeURIComponent(connectorGuid)}/inventory/validate`
      )
      expect(result).toEqual(mockResponse)
    })

    test('returns failure response on validation error', async () => {
      const connectorGuid = 'con_01hgw2bbg00000000000000001'

      const mockResponse = {
        success: false,
        message: 'Manifest not found',
        validation_status: 'failed',
        job_guid: null,
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await validateInventoryConfig(connectorGuid)

      expect(result.success).toBe(false)
      expect(result.message).toBe('Manifest not found')
    })
  })

  describe('triggerInventoryImport', () => {
    test('triggers inventory import', async () => {
      const connectorGuid = 'con_01hgw2bbg00000000000000001'

      const mockResponse = {
        job_guid: 'job_01hgw2bbg00000000000000123',
        message: 'Import job started',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await triggerInventoryImport(connectorGuid)

      expect(api.post).toHaveBeenCalledWith(
        `/connectors/${encodeURIComponent(connectorGuid)}/inventory/import`
      )
      expect(result).toEqual(mockResponse)
    })
  })

  describe('createCollectionsFromInventory', () => {
    test('creates collections from inventory folders', async () => {
      const connectorGuid = 'con_01hgw2bbg00000000000000001'
      const folders: FolderToCollectionMapping[] = [
        {
          folder_guid: 'fld_01hgw2bbg00000000000000001',
          name: 'Events 2026',
          state: 'live',
          pipeline_guid: 'pip_01hgw2bbg00000000000000001',
        },
        {
          folder_guid: 'fld_01hgw2bbg00000000000000002',
          name: 'Archived Photos',
          state: 'archived',
          pipeline_guid: null,
        },
      ]

      const mockResponse: CreateCollectionsFromInventoryResponse = {
        created: [
          {
            collection_guid: 'col_01hgw2bbg00000000000000001',
            folder_guid: 'fld_01hgw2bbg00000000000000001',
            name: 'Events 2026',
          },
        ],
        errors: [
          {
            folder_guid: 'fld_01hgw2bbg00000000000000002',
            error: 'Pipeline not found',
          },
        ],
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await createCollectionsFromInventory(connectorGuid, folders)

      expect(api.post).toHaveBeenCalledWith('/collections/from-inventory', {
        connector_guid: connectorGuid,
        folders,
      })
      expect(result).toEqual(mockResponse)
    })

    test('throws error for invalid connector GUID', async () => {
      await expect(
        createCollectionsFromInventory('invalid_guid', [])
      ).rejects.toThrow('Invalid GUID format')
    })
  })
})
