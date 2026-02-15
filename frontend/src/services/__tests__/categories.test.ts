import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'
import {
  listCategories,
  getCategory,
  createCategory,
  updateCategory,
  deleteCategory,
  reorderCategories,
  seedDefaultCategories,
  getCategoryStats,
} from '@/services/categories'
import type { Category, CategoryStatsResponse, CategorySeedResponse } from '@/contracts/api/category-api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

const mockCategory: Category = {
  guid: 'cat_01hgw2bbg00000000000000001',
  name: 'Wedding',
  icon: 'heart',
  color: '#FF69B4',
  is_active: true,
  display_order: 1,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

describe('categories service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listCategories', () => {
    test('fetches categories without filters', async () => {
      vi.mocked(api.get).mockResolvedValueOnce({ data: [mockCategory] })

      const result = await listCategories()

      expect(api.get).toHaveBeenCalledWith('/categories', { params: {} })
      expect(result).toEqual([mockCategory])
    })

    test('fetches categories with active filter', async () => {
      vi.mocked(api.get).mockResolvedValueOnce({ data: [mockCategory] })

      const result = await listCategories({ is_active: true })

      expect(api.get).toHaveBeenCalledWith('/categories', { params: { is_active: true } })
      expect(result).toEqual([mockCategory])
    })
  })

  describe('getCategory', () => {
    test('fetches category by guid', async () => {
      vi.mocked(api.get).mockResolvedValueOnce({ data: mockCategory })

      const result = await getCategory('cat_01hgw2bbg00000000000000001')

      expect(api.get).toHaveBeenCalledWith('/categories/cat_01hgw2bbg00000000000000001')
      expect(result).toEqual(mockCategory)
    })
  })

  describe('createCategory', () => {
    test('creates new category', async () => {
      vi.mocked(api.post).mockResolvedValueOnce({ data: mockCategory })

      const result = await createCategory({ name: 'Wedding', icon: 'heart', color: '#FF69B4' })

      expect(api.post).toHaveBeenCalledWith('/categories', { name: 'Wedding', icon: 'heart', color: '#FF69B4' })
      expect(result).toEqual(mockCategory)
    })
  })

  describe('updateCategory', () => {
    test('updates category via PATCH', async () => {
      vi.mocked(api.patch).mockResolvedValueOnce({ data: { ...mockCategory, name: 'Updated' } })

      const result = await updateCategory('cat_01hgw2bbg00000000000000001', { name: 'Updated' })

      expect(api.patch).toHaveBeenCalledWith('/categories/cat_01hgw2bbg00000000000000001', { name: 'Updated' })
      expect(result.name).toBe('Updated')
    })
  })

  describe('deleteCategory', () => {
    test('deletes category', async () => {
      vi.mocked(api.delete).mockResolvedValueOnce({ data: undefined })

      await deleteCategory('cat_01hgw2bbg00000000000000001')

      expect(api.delete).toHaveBeenCalledWith('/categories/cat_01hgw2bbg00000000000000001')
    })
  })

  describe('reorderCategories', () => {
    test('reorders categories via POST', async () => {
      const orderedGuids = ['cat_01hgw2bbg00000000000000003', 'cat_01hgw2bbg00000000000000001']
      vi.mocked(api.post).mockResolvedValueOnce({ data: [mockCategory] })

      const result = await reorderCategories(orderedGuids)

      expect(api.post).toHaveBeenCalledWith('/categories/reorder', { ordered_guids: orderedGuids })
      expect(result).toEqual([mockCategory])
    })
  })

  describe('seedDefaultCategories', () => {
    test('seeds default categories', async () => {
      const mockResponse: CategorySeedResponse = { categories_created: 5, categories: [mockCategory] }

      vi.mocked(api.post).mockResolvedValueOnce({ data: mockResponse })

      const result = await seedDefaultCategories()

      expect(api.post).toHaveBeenCalledWith('/categories/seed-defaults')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getCategoryStats', () => {
    test('fetches category statistics', async () => {
      const mockStats: CategoryStatsResponse = {
        total_count: 12,
        active_count: 10,
        inactive_count: 2,
      }

      vi.mocked(api.get).mockResolvedValueOnce({ data: mockStats })

      const result = await getCategoryStats()

      expect(api.get).toHaveBeenCalledWith('/categories/stats')
      expect(result).toEqual(mockStats)
    })
  })
})
