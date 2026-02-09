/**
 * useCategories React hook
 *
 * Manages category state with fetch, create, update, delete, and reorder operations
 * Issue #39 - Calendar Events feature (Phase 3)
 */

import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import * as categoryService from '../services/categories'
import type {
  Category,
  CategoryCreateRequest,
  CategoryUpdateRequest,
  CategoryStatsResponse
} from '@/contracts/api/category-api'

interface UseCategoriesReturn {
  categories: Category[]
  loading: boolean
  error: string | null
  fetchCategories: (filters?: { is_active?: boolean }) => Promise<Category[]>
  createCategory: (categoryData: CategoryCreateRequest) => Promise<Category>
  updateCategory: (guid: string, updates: CategoryUpdateRequest) => Promise<Category>
  deleteCategory: (guid: string) => Promise<void>
  reorderCategories: (orderedGuids: string[]) => Promise<Category[]>
  seedDefaults: (options?: { skipLoading?: boolean }) => Promise<number>
}

export const useCategories = (autoFetch = true): UseCategoriesReturn => {
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /**
   * Fetch categories with optional filters
   */
  const fetchCategories = useCallback(async (filters: { is_active?: boolean } = {}) => {
    setLoading(true)
    setError(null)
    try {
      const data = await categoryService.listCategories(filters)
      setCategories(data)
      return data
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load categories'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Create a new category
   */
  const createCategory = useCallback(async (categoryData: CategoryCreateRequest) => {
    setLoading(true)
    setError(null)
    try {
      const newCategory = await categoryService.createCategory(categoryData)
      setCategories(prev => [...prev, newCategory])
      toast.success('Category created successfully')
      return newCategory
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to create category'
      setError(errorMessage)
      toast.error('Failed to create category', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Update an existing category
   */
  const updateCategory = useCallback(async (guid: string, updates: CategoryUpdateRequest) => {
    setLoading(true)
    setError(null)
    try {
      const updated = await categoryService.updateCategory(guid, updates)
      setCategories(prev =>
        prev.map(c => c.guid === guid ? updated : c)
      )
      toast.success('Category updated successfully')
      return updated
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to update category'
      setError(errorMessage)
      toast.error('Failed to update category', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Delete a category
   */
  const deleteCategory = useCallback(async (guid: string) => {
    setLoading(true)
    setError(null)
    try {
      await categoryService.deleteCategory(guid)
      setCategories(prev => prev.filter(c => c.guid !== guid))
      toast.success('Category deleted successfully')
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to delete category'
      setError(errorMessage)
      toast.error('Failed to delete category', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Reorder categories
   */
  const reorderCategories = useCallback(async (orderedGuids: string[]) => {
    setLoading(true)
    setError(null)
    try {
      const reordered = await categoryService.reorderCategories(orderedGuids)
      setCategories(reordered)
      toast.success('Categories reordered successfully')
      return reordered
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to reorder categories'
      setError(errorMessage)
      toast.error('Failed to reorder categories', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Seed default categories (restore missing defaults)
   * Returns the number of categories created
   * @param options.skipLoading - If true, don't set the shared loading state (caller manages own loading state)
   */
  const seedDefaults = useCallback(async (options?: { skipLoading?: boolean }) => {
    const skipLoading = options?.skipLoading ?? false
    if (!skipLoading) {
      setLoading(true)
    }
    setError(null)
    try {
      const result = await categoryService.seedDefaultCategories()
      setCategories(result.categories)
      if (result.categories_created > 0) {
        toast.success(`Restored ${result.categories_created} default categor${result.categories_created === 1 ? 'y' : 'ies'}`)
      } else {
        toast.info('All default categories already exist')
      }
      return result.categories_created
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to restore default categories'
      setError(errorMessage)
      toast.error('Failed to restore default categories', {
        description: errorMessage
      })
      throw err
    } finally {
      if (!skipLoading) {
        setLoading(false)
      }
    }
  }, [])

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (autoFetch) {
      fetchCategories()
    }
  }, [autoFetch, fetchCategories])

  return {
    categories,
    loading,
    error,
    fetchCategories,
    createCategory,
    updateCategory,
    deleteCategory,
    reorderCategories,
    seedDefaults
  }
}

// ============================================================================
// Category Stats Hook
// ============================================================================

interface UseCategoryStatsReturn {
  stats: CategoryStatsResponse | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * Hook for fetching category KPI statistics
 * Returns total, active, and inactive category counts
 */
export const useCategoryStats = (autoFetch = true): UseCategoryStatsReturn => {
  const [stats, setStats] = useState<CategoryStatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await categoryService.getCategoryStats()
      setStats(data)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load category statistics'
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
