/**
 * Tests for useCategories hook
 *
 * Issue #39 - Calendar Events feature (Phase 3)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useCategories, useCategoryStats } from '../useCategories'
import * as categoryService from '@/services/categories'
import type {
  Category,
  CategoryCreateRequest,
  CategoryUpdateRequest,
  CategoryStatsResponse,
} from '@/contracts/api/category-api'

// Mock the service
vi.mock('@/services/categories')

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}))

describe('useCategories', () => {
  const mockCategories: Category[] = [
    {
      guid: 'cat_01hgw2bbg00000000000000001',
      name: 'Sports',
      color: '#FF5733',
      icon: 'trophy',
      is_active: true,
      display_order: 1,
      created_at: '2026-01-15T10:00:00Z',
      updated_at: '2026-01-15T10:00:00Z',
      audit: {
        created_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        created_at: '2026-01-15T10:00:00Z',
        updated_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        updated_at: '2026-01-15T10:00:00Z',
      },
    },
    {
      guid: 'cat_01hgw2bbg00000000000000002',
      name: 'Music',
      color: '#3498DB',
      icon: 'music',
      is_active: true,
      display_order: 2,
      created_at: '2026-01-10T08:00:00Z',
      updated_at: '2026-01-10T08:00:00Z',
      audit: {
        created_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        created_at: '2026-01-10T08:00:00Z',
        updated_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        updated_at: '2026-01-10T08:00:00Z',
      },
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(categoryService.listCategories).mockResolvedValue(mockCategories)
    vi.mocked(categoryService.createCategory).mockImplementation(async (data) => ({
      guid: 'cat_new',
      name: data.name,
      icon: data.icon ?? null,
      color: data.color ?? null,
      is_active: data.is_active ?? true,
      display_order: data.display_order ?? 999,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      audit: {
        created_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        created_at: new Date().toISOString(),
        updated_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        updated_at: new Date().toISOString(),
      },
    }))
    vi.mocked(categoryService.updateCategory).mockImplementation(async (guid, updates) => ({
      ...mockCategories.find(c => c.guid === guid)!,
      ...updates,
    }))
    vi.mocked(categoryService.deleteCategory).mockResolvedValue(undefined)
    vi.mocked(categoryService.reorderCategories).mockImplementation(async (guids) => {
      return guids.map((guid, index) => ({
        ...mockCategories.find(c => c.guid === guid)!,
        display_order: index + 1,
      }))
    })
    vi.mocked(categoryService.seedDefaultCategories).mockResolvedValue({
      categories: mockCategories,
      categories_created: 0,
    })
  })

  it('should fetch categories on mount', async () => {
    const { result } = renderHook(() => useCategories())

    expect(result.current.loading).toBe(true)
    expect(result.current.categories).toEqual([])

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.categories).toHaveLength(2)
    expect(result.current.categories[0].name).toBe('Sports')
    expect(result.current.error).toBe(null)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useCategories(false))

    expect(result.current.loading).toBe(false)
    expect(result.current.categories).toEqual([])
    expect(categoryService.listCategories).not.toHaveBeenCalled()
  })

  it('should fetch categories with filters', async () => {
    const { result } = renderHook(() => useCategories(false))

    await act(async () => {
      await result.current.fetchCategories({ is_active: true })
    })

    expect(categoryService.listCategories).toHaveBeenCalledWith({ is_active: true })
    expect(result.current.categories).toHaveLength(2)
  })

  it('should create a new category', async () => {
    const { result } = renderHook(() => useCategories())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const createRequest: CategoryCreateRequest = {
      name: 'Theater',
      color: '#9B59B6',
      icon: 'theater-masks',
      is_active: true,
    }

    await act(async () => {
      await result.current.createCategory(createRequest)
    })

    expect(categoryService.createCategory).toHaveBeenCalledWith(createRequest)
    expect(result.current.categories).toHaveLength(3)
    expect(result.current.categories[2].name).toBe('Theater')
  })

  it('should update a category', async () => {
    const { result } = renderHook(() => useCategories())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const updateRequest: CategoryUpdateRequest = {
      name: 'Sports Updated',
      color: '#E74C3C',
    }

    await act(async () => {
      await result.current.updateCategory('cat_01hgw2bbg00000000000000001', updateRequest)
    })

    expect(categoryService.updateCategory).toHaveBeenCalledWith(
      'cat_01hgw2bbg00000000000000001',
      updateRequest
    )

    const updated = result.current.categories.find(c => c.guid === 'cat_01hgw2bbg00000000000000001')
    expect(updated?.name).toBe('Sports Updated')
    expect(updated?.color).toBe('#E74C3C')
  })

  it('should delete a category', async () => {
    const { result } = renderHook(() => useCategories())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.categories).toHaveLength(2)

    await act(async () => {
      await result.current.deleteCategory('cat_01hgw2bbg00000000000000001')
    })

    expect(categoryService.deleteCategory).toHaveBeenCalledWith('cat_01hgw2bbg00000000000000001')
    expect(result.current.categories).toHaveLength(1)
    expect(result.current.categories[0].guid).toBe('cat_01hgw2bbg00000000000000002')
  })

  it('should reorder categories', async () => {
    const { result } = renderHook(() => useCategories())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const newOrder = [
      'cat_01hgw2bbg00000000000000002',
      'cat_01hgw2bbg00000000000000001',
    ]

    await act(async () => {
      await result.current.reorderCategories(newOrder)
    })

    expect(categoryService.reorderCategories).toHaveBeenCalledWith(newOrder)
    expect(result.current.categories[0].guid).toBe('cat_01hgw2bbg00000000000000002')
    expect(result.current.categories[0].display_order).toBe(1)
    expect(result.current.categories[1].guid).toBe('cat_01hgw2bbg00000000000000001')
    expect(result.current.categories[1].display_order).toBe(2)
  })

  it('should seed default categories', async () => {
    vi.mocked(categoryService.seedDefaultCategories).mockResolvedValue({
      categories: [...mockCategories, {
        guid: 'cat_new_default',
        name: 'Dance',
        color: '#1ABC9C',
        icon: 'dance',
        is_active: true,
        display_order: 3,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      } as Category],
      categories_created: 1,
    })

    const { result } = renderHook(() => useCategories())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      const createdCount = await result.current.seedDefaults()
      expect(createdCount).toBe(1)
    })

    expect(categoryService.seedDefaultCategories).toHaveBeenCalled()
    expect(result.current.categories).toHaveLength(3)
  })

  it('should seed defaults with skipLoading option', async () => {
    const { result } = renderHook(() => useCategories())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.seedDefaults({ skipLoading: true })
    })

    // Loading should not be triggered
    expect(result.current.loading).toBe(false)
  })

  it('should handle fetch error', async () => {
    const error = new Error('Network error')
    ;(error as any).userMessage = 'Failed to load categories'
    vi.mocked(categoryService.listCategories).mockRejectedValue(error)

    // Use autoFetch=false to avoid unhandled rejection from useEffect
    // (fetchCategories re-throws after setting error state)
    const { result } = renderHook(() => useCategories(false))

    await act(async () => {
      try {
        await result.current.fetchCategories()
      } catch {
        // Expected — fetchCategories re-throws after setting error state
      }
    })

    expect(result.current.error).toBe('Failed to load categories')
    expect(result.current.categories).toEqual([])
  })

  it('should handle create error', async () => {
    const error = new Error('Validation error')
    ;(error as any).userMessage = 'Category name already exists'
    vi.mocked(categoryService.createCategory).mockRejectedValue(error)

    const { result } = renderHook(() => useCategories())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      try {
        await result.current.createCategory({ name: 'Duplicate', color: '#000', icon: 'icon' })
        expect.fail('Should have thrown')
      } catch (err) {
        // Expected
      }
    })

    expect(result.current.error).toBe('Category name already exists')
  })
})

describe('useCategoryStats', () => {
  const mockStats: CategoryStatsResponse = {
    total_count: 15,
    active_count: 12,
    inactive_count: 3,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(categoryService.getCategoryStats).mockResolvedValue(mockStats)
  })

  it('should fetch stats on mount', async () => {
    const { result } = renderHook(() => useCategoryStats())

    expect(result.current.loading).toBe(true)
    expect(result.current.stats).toBe(null)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats).toEqual(mockStats)
    expect(result.current.error).toBe(null)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useCategoryStats(false))

    expect(result.current.loading).toBe(false)
    expect(result.current.stats).toBe(null)
    expect(categoryService.getCategoryStats).not.toHaveBeenCalled()
  })

  it('should refetch stats', async () => {
    const { result } = renderHook(() => useCategoryStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    vi.mocked(categoryService.getCategoryStats).mockResolvedValue({
      ...mockStats,
      active_count: 13,
    })

    await act(async () => {
      await result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.stats?.active_count).toBe(13)
    })
  })

  it('should handle stats error', async () => {
    const error = new Error('Network error')
    ;(error as any).userMessage = 'Failed to load statistics'
    vi.mocked(categoryService.getCategoryStats).mockRejectedValue(error)

    const { result } = renderHook(() => useCategoryStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to load statistics')
    expect(result.current.stats).toBe(null)
  })
})
