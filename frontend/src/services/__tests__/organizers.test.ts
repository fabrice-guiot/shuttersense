import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'
import { validateGuid } from '@/utils/guid'
import {
  listOrganizers,
  getOrganizer,
  createOrganizer,
  updateOrganizer,
  deleteOrganizer,
  getOrganizerStats,
  getOrganizersByCategory,
  validateCategoryMatch,
} from '@/services/organizers'
import type {
  Organizer,
  OrganizerCreateRequest,
  OrganizerUpdateRequest,
  OrganizerListResponse,
  OrganizerStatsResponse,
  CategoryMatchResponse,
} from '@/contracts/api/organizer-api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

vi.mock('@/utils/guid', () => ({
  validateGuid: vi.fn((guid: string) => guid),
}))

describe('Organizers API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const mockOrganizer: Organizer = {
    guid: 'org_01hgw2bbg00000000000000001',
    name: 'Test Organizer',
    website: 'https://example.com',
    instagram_handle: 'testorg',
    instagram_url: 'https://instagram.com/testorg',
    category: {
      guid: 'cat_01hgw2bbg00000000000000001',
      name: 'Music',
      icon: 'music',
      color: '#ff0000',
    },
    rating: 5,
    ticket_required_default: true,
    notes: 'Test notes',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }

  describe('listOrganizers', () => {
    test('lists organizers without filters', async () => {
      const mockResponse: OrganizerListResponse = {
        items: [mockOrganizer],
        total: 1,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await listOrganizers()

      expect(api.get).toHaveBeenCalledWith('/organizers', { params: {} })
      expect(result).toEqual(mockResponse)
    })

    test('lists organizers with category filter', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0 } })

      await listOrganizers({ category_guid: 'cat_01hgw2bbg00000000000000001' })

      expect(api.get).toHaveBeenCalledWith('/organizers', {
        params: { category_guid: 'cat_01hgw2bbg00000000000000001' },
      })
    })

    test('lists organizers with search filter', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0 } })

      await listOrganizers({ search: '  test query  ' })

      expect(api.get).toHaveBeenCalledWith('/organizers', {
        params: { search: 'test query' },
      })
    })

    test('lists organizers with pagination', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0 } })

      await listOrganizers({ limit: 50, offset: 100 })

      expect(api.get).toHaveBeenCalledWith('/organizers', {
        params: { limit: 50, offset: 100 },
      })
    })

    test('trims empty search string', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { items: [], total: 0 } })

      await listOrganizers({ search: '   ' })

      expect(api.get).toHaveBeenCalledWith('/organizers', { params: {} })
    })
  })

  describe('getOrganizer', () => {
    test('retrieves a single organizer by GUID', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockOrganizer })

      const result = await getOrganizer('org_01hgw2bbg00000000000000001')

      expect(validateGuid).toHaveBeenCalledWith('org_01hgw2bbg00000000000000001', 'org')
      expect(api.get).toHaveBeenCalledWith('/organizers/org_01hgw2bbg00000000000000001')
      expect(result).toEqual(mockOrganizer)
    })
  })

  describe('createOrganizer', () => {
    test('creates an organizer with required fields', async () => {
      const request: OrganizerCreateRequest = {
        name: 'New Organizer',
        category_guid: 'cat_01hgw2bbg00000000000000001',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockOrganizer })

      const result = await createOrganizer(request)

      expect(api.post).toHaveBeenCalledWith('/organizers', request)
      expect(result).toEqual(mockOrganizer)
    })

    test('creates an organizer with all optional fields', async () => {
      const request: OrganizerCreateRequest = {
        name: 'New Organizer',
        category_guid: 'cat_01hgw2bbg00000000000000001',
        website: 'https://example.com',
        instagram_handle: 'neworg',
        rating: 4,
        ticket_required_default: false,
        notes: 'Test organizer',
      }

      vi.mocked(api.post).mockResolvedValue({ data: mockOrganizer })

      await createOrganizer(request)

      expect(api.post).toHaveBeenCalledWith('/organizers', request)
    })
  })

  describe('updateOrganizer', () => {
    test('updates an organizer with partial data', async () => {
      const updateData: OrganizerUpdateRequest = {
        name: 'Updated Name',
      }

      vi.mocked(api.patch).mockResolvedValue({ data: { ...mockOrganizer, name: 'Updated Name' } })

      const result = await updateOrganizer('org_01hgw2bbg00000000000000001', updateData)

      expect(validateGuid).toHaveBeenCalledWith('org_01hgw2bbg00000000000000001', 'org')
      expect(api.patch).toHaveBeenCalledWith('/organizers/org_01hgw2bbg00000000000000001', updateData)
      expect(result.name).toBe('Updated Name')
    })

    test('updates an organizer with multiple fields', async () => {
      const updateData: OrganizerUpdateRequest = {
        name: 'Updated Name',
        rating: 3,
        notes: 'Updated notes',
      }

      vi.mocked(api.patch).mockResolvedValue({ data: mockOrganizer })

      await updateOrganizer('org_01hgw2bbg00000000000000001', updateData)

      expect(api.patch).toHaveBeenCalledWith('/organizers/org_01hgw2bbg00000000000000001', updateData)
    })
  })

  describe('deleteOrganizer', () => {
    test('deletes an organizer by GUID', async () => {
      vi.mocked(api.delete).mockResolvedValue({ data: undefined })

      await deleteOrganizer('org_01hgw2bbg00000000000000001')

      expect(validateGuid).toHaveBeenCalledWith('org_01hgw2bbg00000000000000001', 'org')
      expect(api.delete).toHaveBeenCalledWith('/organizers/org_01hgw2bbg00000000000000001')
    })
  })

  describe('getOrganizerStats', () => {
    test('retrieves organizer statistics', async () => {
      const mockStats: OrganizerStatsResponse = {
        total_count: 50,
        with_rating_count: 30,
        with_instagram_count: 25,
        avg_rating: 4.2,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockStats })

      const result = await getOrganizerStats()

      expect(api.get).toHaveBeenCalledWith('/organizers/stats')
      expect(result).toEqual(mockStats)
    })
  })

  describe('getOrganizersByCategory', () => {
    test('retrieves organizers for a specific category', async () => {
      const mockOrganizers: Organizer[] = [mockOrganizer]

      vi.mocked(api.get).mockResolvedValue({ data: mockOrganizers })

      const result = await getOrganizersByCategory('cat_01hgw2bbg00000000000000001')

      expect(validateGuid).toHaveBeenCalledWith('cat_01hgw2bbg00000000000000001', 'cat')
      expect(api.get).toHaveBeenCalledWith('/organizers/by-category/cat_01hgw2bbg00000000000000001')
      expect(result).toEqual(mockOrganizers)
    })
  })

  describe('validateCategoryMatch', () => {
    test('validates matching categories', async () => {
      const mockResponse: CategoryMatchResponse = {
        matches: true,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await validateCategoryMatch(
        'org_01hgw2bbg00000000000000001',
        'cat_01hgw2bbg00000000000000001'
      )

      expect(validateGuid).toHaveBeenCalledWith('org_01hgw2bbg00000000000000001', 'org')
      expect(validateGuid).toHaveBeenCalledWith('cat_01hgw2bbg00000000000000001', 'cat')
      expect(api.get).toHaveBeenCalledWith(
        '/organizers/org_01hgw2bbg00000000000000001/validate-category/cat_01hgw2bbg00000000000000001'
      )
      expect(result).toBe(true)
    })

    test('validates non-matching categories', async () => {
      const mockResponse: CategoryMatchResponse = {
        matches: false,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await validateCategoryMatch(
        'org_01hgw2bbg00000000000000001',
        'cat_01hgw2bbg00000000000000002'
      )

      expect(result).toBe(false)
    })
  })
})
