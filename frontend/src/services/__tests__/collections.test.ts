import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'
import { validateGuid } from '@/utils/guid'
import {
  listCollections,
  getCollection,
  createCollection,
  updateCollection,
  deleteCollection,
  testCollection,
  refreshCollection,
  getCollectionStats,
  assignPipeline,
  clearPipeline,
  clearInventoryCache,
} from '@/services/collections'
import type {
  Collection,
  CollectionCreateRequest,
  CollectionUpdateRequest,
  CollectionListQueryParams,
  CollectionTestResponse,
  CollectionDeleteResponse,
  CollectionStatsResponse,
} from '@/contracts/api/collection-api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

vi.mock('@/utils/guid', () => ({
  validateGuid: vi.fn((guid: string) => guid),
}))

describe('Collections API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const mockCollection: Collection = {
    guid: 'col_01hgw2bbg00000000000000001',
    name: 'Test Collection',
    type: 'local',
    state: 'live',
    location: '/path/to/photos',
    connector_guid: null,
    pipeline_guid: null,
    pipeline_version: null,
    pipeline_name: null,
    is_accessible: true,
    accessibility_message: null,
    cache_ttl: null,
    bound_agent: null,
    file_info: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    last_scanned_at: null,
  }

  describe('listCollections', () => {
    test('lists collections without filters', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [mockCollection] })

      const result = await listCollections()

      expect(api.get).toHaveBeenCalledWith('/collections', { params: {} })
      expect(result).toEqual([mockCollection])
    })

    test('lists collections with state filter', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await listCollections({ state: 'live' })

      expect(api.get).toHaveBeenCalledWith('/collections', {
        params: { state: 'live' },
      })
    })

    test('lists collections with type filter', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await listCollections({ type: 's3' })

      expect(api.get).toHaveBeenCalledWith('/collections', {
        params: { type: 's3' },
      })
    })

    test('lists collections with accessible_only filter', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await listCollections({ accessible_only: true })

      expect(api.get).toHaveBeenCalledWith('/collections', {
        params: { accessible_only: true },
      })
    })

    test('lists collections with search filter', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await listCollections({ search: 'test' })

      expect(api.get).toHaveBeenCalledWith('/collections', {
        params: { search: 'test' },
      })
    })

    test('lists collections with pagination', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await listCollections({ limit: 50, offset: 100 })

      expect(api.get).toHaveBeenCalledWith('/collections', {
        params: { limit: 50, offset: 100 },
      })
    })

    test('lists collections with multiple filters', async () => {
      const filters: CollectionListQueryParams = {
        state: 'live',
        type: 'local',
        accessible_only: true,
        search: 'photos',
        limit: 25,
        offset: 50,
      }

      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await listCollections(filters)

      expect(api.get).toHaveBeenCalledWith('/collections', { params: filters })
    })
  })

  describe('getCollection', () => {
    test('retrieves a single collection by GUID', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockCollection })

      const result = await getCollection('col_01hgw2bbg00000000000000001')

      expect(validateGuid).toHaveBeenCalledWith('col_01hgw2bbg00000000000000001', 'col')
      expect(api.get).toHaveBeenCalledWith('/collections/col_01hgw2bbg00000000000000001')
      expect(result).toEqual(mockCollection)
    })
  })

  describe('createCollection', () => {
    test('creates a local collection', async () => {
      const request: CollectionCreateRequest = {
        name: 'New Collection',
        type: 'local',
        state: 'live',
        location: '/path/to/photos',
        connector_guid: null,
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockCollection })

      const result = await createCollection(request)

      expect(api.post).toHaveBeenCalledWith('/collections', request)
      expect(result).toEqual(mockCollection)
    })

    test('creates an S3 collection with connector', async () => {
      const request: CollectionCreateRequest = {
        name: 'S3 Collection',
        type: 's3',
        state: 'live',
        location: 's3://bucket/path',
        connector_guid: 'con_01hgw2bbg00000000000000001',
      }

      vi.mocked(api.post).mockResolvedValue({
        data: { ...mockCollection, type: 's3', connector_guid: 'con_01hgw2bbg00000000000000001' },
      })

      await createCollection(request)

      expect(api.post).toHaveBeenCalledWith('/collections', request)
    })

    test('creates a collection with pipeline assignment', async () => {
      const request: CollectionCreateRequest = {
        name: 'New Collection',
        type: 'local',
        state: 'live',
        location: '/path/to/photos',
        connector_guid: null,
        pipeline_guid: 'pip_01hgw2bbg00000000000000001',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockCollection })

      await createCollection(request)

      expect(api.post).toHaveBeenCalledWith('/collections', request)
    })

    test('creates a collection with bound agent', async () => {
      const request: CollectionCreateRequest = {
        name: 'New Collection',
        type: 'local',
        state: 'live',
        location: '/path/to/photos',
        connector_guid: null,
        bound_agent_guid: 'agt_01hgw2bbg00000000000000001',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockCollection })

      await createCollection(request)

      expect(api.post).toHaveBeenCalledWith('/collections', request)
    })
  })

  describe('updateCollection', () => {
    test('updates a collection with partial data', async () => {
      const updateData: CollectionUpdateRequest = {
        name: 'Updated Name',
      }

      vi.mocked(api.put).mockResolvedValue({ data: { ...mockCollection, name: 'Updated Name' } })

      const result = await updateCollection('col_01hgw2bbg00000000000000001', updateData)

      expect(validateGuid).toHaveBeenCalledWith('col_01hgw2bbg00000000000000001', 'col')
      expect(api.put).toHaveBeenCalledWith('/collections/col_01hgw2bbg00000000000000001', updateData)
      expect(result.name).toBe('Updated Name')
    })

    test('updates a collection with multiple fields', async () => {
      const updateData: CollectionUpdateRequest = {
        name: 'Updated Name',
        state: 'archived',
        location: '/new/path',
      }

      vi.mocked(api.put).mockResolvedValue({ data: mockCollection })

      await updateCollection('col_01hgw2bbg00000000000000001', updateData)

      expect(api.put).toHaveBeenCalledWith('/collections/col_01hgw2bbg00000000000000001', updateData)
    })
  })

  describe('deleteCollection', () => {
    test('deletes a collection successfully (204)', async () => {
      vi.mocked(api.delete).mockResolvedValue({ status: 204, data: undefined })

      const result = await deleteCollection('col_01hgw2bbg00000000000000001')

      expect(validateGuid).toHaveBeenCalledWith('col_01hgw2bbg00000000000000001', 'col')
      expect(api.delete).toHaveBeenCalledWith('/collections/col_01hgw2bbg00000000000000001', { params: {} })
      expect(result).toBeUndefined()
    })

    test('deletes a collection with force parameter', async () => {
      vi.mocked(api.delete).mockResolvedValue({ status: 204, data: undefined })

      await deleteCollection('col_01hgw2bbg00000000000000001', true)

      expect(api.delete).toHaveBeenCalledWith('/collections/col_01hgw2bbg00000000000000001', {
        params: { force: true },
      })
    })

    test('returns data when collection has dependencies (200)', async () => {
      const deleteResponse: CollectionDeleteResponse = {
        success: true,
        message: 'Collection has data',
      }

      vi.mocked(api.delete).mockResolvedValue({ status: 200, data: deleteResponse })

      const result = await deleteCollection('col_01hgw2bbg00000000000000001')

      expect(result).toEqual(deleteResponse)
    })
  })

  describe('testCollection', () => {
    test('tests collection accessibility successfully', async () => {
      const testResponse: CollectionTestResponse = {
        success: true,
        message: 'Collection is accessible',
        collection: mockCollection,
      }

      vi.mocked(api.post).mockResolvedValue({ data: testResponse })

      const result = await testCollection('col_01hgw2bbg00000000000000001')

      expect(validateGuid).toHaveBeenCalledWith('col_01hgw2bbg00000000000000001', 'col')
      expect(api.post).toHaveBeenCalledWith('/collections/col_01hgw2bbg00000000000000001/test')
      expect(result).toEqual(testResponse)
    })

    test('tests collection accessibility with failure', async () => {
      const testResponse: CollectionTestResponse = {
        success: false,
        message: 'Path not found',
        collection: { ...mockCollection, is_accessible: false },
      }

      vi.mocked(api.post).mockResolvedValue({ data: testResponse })

      const result = await testCollection('col_01hgw2bbg00000000000000001')

      expect(result.success).toBe(false)
    })
  })

  describe('refreshCollection', () => {
    test('refreshes collection cache without confirm', async () => {
      vi.mocked(api.post).mockResolvedValue({ data: { success: true } })

      await refreshCollection('col_01hgw2bbg00000000000000001')

      expect(validateGuid).toHaveBeenCalledWith('col_01hgw2bbg00000000000000001', 'col')
      expect(api.post).toHaveBeenCalledWith('/collections/col_01hgw2bbg00000000000000001/refresh', null, {
        params: {},
      })
    })

    test('refreshes collection cache with confirm', async () => {
      vi.mocked(api.post).mockResolvedValue({ data: { success: true } })

      await refreshCollection('col_01hgw2bbg00000000000000001', true)

      expect(api.post).toHaveBeenCalledWith('/collections/col_01hgw2bbg00000000000000001/refresh', null, {
        params: { confirm: true },
      })
    })
  })

  describe('getCollectionStats', () => {
    test('retrieves collection statistics', async () => {
      const mockStats: CollectionStatsResponse = {
        total_collections: 50,
        storage_used_bytes: 1024000000000,
        storage_used_formatted: '1 TB',
        file_count: 100000,
        image_count: 50000,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockStats })

      const result = await getCollectionStats()

      expect(api.get).toHaveBeenCalledWith('/collections/stats')
      expect(result).toEqual(mockStats)
    })
  })

  describe('assignPipeline', () => {
    test('assigns a pipeline to a collection', async () => {
      const updatedCollection: Collection = {
        ...mockCollection,
        pipeline_guid: 'pip_01hgw2bbg00000000000000001',
        pipeline_version: 1,
        pipeline_name: 'Test Pipeline',
      }

      vi.mocked(api.post).mockResolvedValue({ data: updatedCollection })

      const result = await assignPipeline('col_01hgw2bbg00000000000000001', 'pip_01hgw2bbg00000000000000001')

      expect(validateGuid).toHaveBeenCalledWith('col_01hgw2bbg00000000000000001', 'col')
      expect(validateGuid).toHaveBeenCalledWith('pip_01hgw2bbg00000000000000001', 'pip')
      expect(api.post).toHaveBeenCalledWith(
        '/collections/col_01hgw2bbg00000000000000001/assign-pipeline',
        null,
        { params: { pipeline_guid: 'pip_01hgw2bbg00000000000000001' } }
      )
      expect(result.pipeline_guid).toBe('pip_01hgw2bbg00000000000000001')
    })
  })

  describe('clearPipeline', () => {
    test('clears pipeline assignment from a collection', async () => {
      const updatedCollection: Collection = {
        ...mockCollection,
        pipeline_guid: null,
        pipeline_version: null,
        pipeline_name: null,
      }

      vi.mocked(api.post).mockResolvedValue({ data: updatedCollection })

      const result = await clearPipeline('col_01hgw2bbg00000000000000001')

      expect(validateGuid).toHaveBeenCalledWith('col_01hgw2bbg00000000000000001', 'col')
      expect(api.post).toHaveBeenCalledWith('/collections/col_01hgw2bbg00000000000000001/clear-pipeline')
      expect(result.pipeline_guid).toBeNull()
    })
  })

  describe('clearInventoryCache', () => {
    test('clears inventory cache successfully', async () => {
      const mockResponse = {
        success: true,
        message: 'Cache cleared',
        cleared_count: 1000,
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockResponse })

      const result = await clearInventoryCache('col_01hgw2bbg00000000000000001')

      expect(validateGuid).toHaveBeenCalledWith('col_01hgw2bbg00000000000000001', 'col')
      expect(api.post).toHaveBeenCalledWith('/collections/col_01hgw2bbg00000000000000001/clear-inventory-cache')
      expect(result).toEqual(mockResponse)
      expect(result.cleared_count).toBe(1000)
    })
  })
})
