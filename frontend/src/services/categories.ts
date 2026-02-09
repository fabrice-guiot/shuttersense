/**
 * Category API service
 *
 * Handles all API calls related to event categories
 * Issue #39 - Calendar Events feature (Phase 3)
 */

import api from './api'
import { validateGuid } from '@/utils/guid'
import type {
  Category,
  CategoryCreateRequest,
  CategoryUpdateRequest,
  CategoryReorderRequest,
  CategorySeedResponse,
  CategoryStatsResponse
} from '@/contracts/api/category-api'

/**
 * List all categories with optional filters
 */
export const listCategories = async (filters: { is_active?: boolean } = {}): Promise<Category[]> => {
  const params: Record<string, string | boolean> = {}
  if (filters.is_active !== undefined) params.is_active = filters.is_active

  const response = await api.get<Category[]>('/categories', { params })
  return response.data
}

/**
 * Get a single category by GUID
 * @param guid - External ID (cat_xxx format)
 */
export const getCategory = async (guid: string): Promise<Category> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'cat'))
  const response = await api.get<Category>(`/categories/${safeGuid}`)
  return response.data
}

/**
 * Create a new category
 */
export const createCategory = async (data: CategoryCreateRequest): Promise<Category> => {
  const response = await api.post<Category>('/categories', data)
  return response.data
}

/**
 * Update an existing category
 * @param guid - External ID (cat_xxx format)
 */
export const updateCategory = async (guid: string, data: CategoryUpdateRequest): Promise<Category> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'cat'))
  const response = await api.patch<Category>(`/categories/${safeGuid}`, data)
  return response.data
}

/**
 * Delete a category
 * @param guid - External ID (cat_xxx format)
 * @throws Error 409 if events, locations, etc. reference this category
 */
export const deleteCategory = async (guid: string): Promise<void> => {
  const safeGuid = encodeURIComponent(validateGuid(guid, 'cat'))
  await api.delete(`/categories/${safeGuid}`)
}

/**
 * Reorder categories
 * Updates display_order based on the provided order
 */
export const reorderCategories = async (orderedGuids: string[]): Promise<Category[]> => {
  const data: CategoryReorderRequest = { ordered_guids: orderedGuids }
  const response = await api.post<Category[]>('/categories/reorder', data)
  return response.data
}

/**
 * Seed default categories (idempotent)
 * Restores any missing default categories without affecting existing ones
 */
export const seedDefaultCategories = async (): Promise<CategorySeedResponse> => {
  const response = await api.post<CategorySeedResponse>('/categories/seed-defaults')
  return response.data
}

/**
 * Get category statistics (KPIs)
 * Returns aggregated stats for all categories
 */
export const getCategoryStats = async (): Promise<CategoryStatsResponse> => {
  const response = await api.get<CategoryStatsResponse>('/categories/stats')
  return response.data
}
