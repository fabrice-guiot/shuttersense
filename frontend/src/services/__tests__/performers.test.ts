import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'
import { validateGuid } from '@/utils/guid'
import {
  listPerformers,
  getPerformer,
  createPerformer,
  updatePerformer,
  deletePerformer,
  getPerformerStats,
  getPerformersByCategory,
  validatePerformerCategoryMatch,
} from '@/services/performers'
import type {
  Performer,
  PerformerCreateRequest,
  PerformerUpdateRequest,
  PerformerListResponse,
  PerformerStatsResponse,
  CategoryMatchResponse,
} from '@/contracts/api/performer-api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

vi.mock('@/utils/guid', () => ({
  validateGuid: vi.fn((guid: string) => guid),
}))

describe('Performers API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const mockPerformer: Performer = {
    guid: 'prf_01hgw2bbg00000000000000001',
    name: 'Test Performer',
    website: 'https://example.com',
    instagram_handle: 'testperformer',
    instagram_url: 'https://instagram.com/testperformer',
    category: {
      guid: 'cat_01hgw2bbg00000000000000001',
      name: 'Music',
      icon: 'music',
      color: '#ff0000',
    },
    additional_info: 'Test info',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }

  describe('listPerformers', () => {
    test('lists performers without filters', async () => {
      const mockResponse: PerformerListResponse = {
        items: [mockPerformer],
        total: 1,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await listPerformers()

      expect(api.get).toHaveBeenCalledWith('/performers', { params: {} })
      expect(result).toEqual(mockResponse)
    })

    test('lists performers with category filter', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0 } })

      await listPerformers({ category_guid: 'cat_01hgw2bbg00000000000000001' })

      expect(api.get).toHaveBeenCalledWith('/performers', {
        params: { category_guid: 'cat_01hgw2bbg00000000000000001' },
      })
    })

    test('lists performers with search filter', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0 } })

      await listPerformers({ search: '  test query  ' })

      expect(api.get).toHaveBeenCalledWith('/performers', {
        params: { search: 'test query' },
      })
    })

    test('lists performers with pagination', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0 } })

      await listPerformers({ limit: 50, offset: 100 })

      expect(api.get).toHaveBeenCalledWith('/performers', {
        params: { limit: 50, offset: 100 },
      })
    })

    test('trims empty search string', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0 } })

      await listPerformers({ search: '   ' })

      expect(api.get).toHaveBeenCalledWith('/performers', { params: {} })
    })
  })

  describe('getPerformer', () => {
    test('retrieves a single performer by GUID', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockPerformer })

      const result = await getPerformer('prf_01hgw2bbg00000000000000001')

      expect(validateGuid).toHaveBeenCalledWith('prf_01hgw2bbg00000000000000001', 'prf')
      expect(api.get).toHaveBeenCalledWith('/performers/prf_01hgw2bbg00000000000000001')
      expect(result).toEqual(mockPerformer)
    })
  })

  describe('createPerformer', () => {
    test('creates a performer with required fields', async () => {
      const request: PerformerCreateRequest = {
        name: 'New Performer',
        category_guid: 'cat_01hgw2bbg00000000000000001',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockPerformer })

      const result = await createPerformer(request)

      expect(api.post).toHaveBeenCalledWith('/performers', request)
      expect(result).toEqual(mockPerformer)
    })

    test('creates a performer with all optional fields', async () => {
      const request: PerformerCreateRequest = {
        name: 'New Performer',
        category_guid: 'cat_01hgw2bbg00000000000000001',
        website: 'https://example.com',
        instagram_handle: 'newperformer',
        additional_info: 'Additional details',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockPerformer })

      await createPerformer(request)

      expect(api.post).toHaveBeenCalledWith('/performers', request)
    })
  })

  describe('updatePerformer', () => {
    test('updates a performer with partial data', async () => {
      const updateData: PerformerUpdateRequest = {
        name: 'Updated Name',
      }

      vi.mocked(api.patch).mockResolvedValue({ data: { ...mockPerformer, name: 'Updated Name' } })

      const result = await updatePerformer('prf_01hgw2bbg00000000000000001', updateData)

      expect(validateGuid).toHaveBeenCalledWith('prf_01hgw2bbg00000000000000001', 'prf')
      expect(api.patch).toHaveBeenCalledWith('/performers/prf_01hgw2bbg00000000000000001', updateData)
      expect(result.name).toBe('Updated Name')
    })

    test('updates a performer with multiple fields', async () => {
      const updateData: PerformerUpdateRequest = {
        name: 'Updated Name',
        website: 'https://newsite.com',
        additional_info: 'Updated info',
      }

      vi.mocked(api.patch).mockResolvedValue({ data: mockPerformer })

      await updatePerformer('prf_01hgw2bbg00000000000000001', updateData)

      expect(api.patch).toHaveBeenCalledWith('/performers/prf_01hgw2bbg00000000000000001', updateData)
    })
  })

  describe('deletePerformer', () => {
    test('deletes a performer by GUID', async () => {
      vi.mocked(api.delete).mockResolvedValue({ data: undefined })

      await deletePerformer('prf_01hgw2bbg00000000000000001')

      expect(validateGuid).toHaveBeenCalledWith('prf_01hgw2bbg00000000000000001', 'prf')
      expect(api.delete).toHaveBeenCalledWith('/performers/prf_01hgw2bbg00000000000000001')
    })
  })

  describe('getPerformerStats', () => {
    test('retrieves performer statistics', async () => {
      const mockStats: PerformerStatsResponse = {
        total_count: 100,
        with_instagram_count: 75,
        with_website_count: 60,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockStats })

      const result = await getPerformerStats()

      expect(api.get).toHaveBeenCalledWith('/performers/stats')
      expect(result).toEqual(mockStats)
    })
  })

  describe('getPerformersByCategory', () => {
    test('retrieves performers for a category without search', async () => {
      const mockPerformers: Performer[] = [mockPerformer]

      vi.mocked(api.get).mockResolvedValue({ data: mockPerformers })

      const result = await getPerformersByCategory('cat_01hgw2bbg00000000000000001')

      expect(validateGuid).toHaveBeenCalledWith('cat_01hgw2bbg00000000000000001', 'cat')
      expect(api.get).toHaveBeenCalledWith('/performers/by-category/cat_01hgw2bbg00000000000000001', {
        params: {},
      })
      expect(result).toEqual(mockPerformers)
    })

    test('retrieves performers for a category with search', async () => {
      const mockPerformers: Performer[] = [mockPerformer]

      vi.mocked(api.get).mockResolvedValue({ data: mockPerformers })

      const result = await getPerformersByCategory('cat_01hgw2bbg00000000000000001', 'test')

      expect(validateGuid).toHaveBeenCalledWith('cat_01hgw2bbg00000000000000001', 'cat')
      expect(api.get).toHaveBeenCalledWith('/performers/by-category/cat_01hgw2bbg00000000000000001', {
        params: { search: 'test' },
      })
      expect(result).toEqual(mockPerformers)
    })

    test('trims whitespace from search parameter', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await getPerformersByCategory('cat_01hgw2bbg00000000000000001', '  test  ')

      expect(api.get).toHaveBeenCalledWith('/performers/by-category/cat_01hgw2bbg00000000000000001', {
        params: { search: 'test' },
      })
    })

    test('ignores empty search parameter', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: [] })

      await getPerformersByCategory('cat_01hgw2bbg00000000000000001', '   ')

      expect(api.get).toHaveBeenCalledWith('/performers/by-category/cat_01hgw2bbg00000000000000001', {
        params: {},
      })
    })
  })

  describe('validatePerformerCategoryMatch', () => {
    test('validates matching categories', async () => {
      const mockResponse: CategoryMatchResponse = {
        matches: true,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await validatePerformerCategoryMatch(
        'prf_01hgw2bbg00000000000000001',
        'cat_01hgw2bbg00000000000000001'
      )

      expect(validateGuid).toHaveBeenCalledWith('prf_01hgw2bbg00000000000000001', 'prf')
      expect(validateGuid).toHaveBeenCalledWith('cat_01hgw2bbg00000000000000001', 'cat')
      expect(api.get).toHaveBeenCalledWith(
        '/performers/prf_01hgw2bbg00000000000000001/validate-category/cat_01hgw2bbg00000000000000001'
      )
      expect(result).toBe(true)
    })

    test('validates non-matching categories', async () => {
      const mockResponse: CategoryMatchResponse = {
        matches: false,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await validatePerformerCategoryMatch(
        'prf_01hgw2bbg00000000000000001',
        'cat_01hgw2bbg00000000000000002'
      )

      expect(result).toBe(false)
    })
  })
})
