/**
 * useCollections React hook
 *
 * Manages collection state with fetch, create, update, delete operations
 */

import { useState, useEffect, useCallback } from 'react'
import * as collectionService from '../services/collections'
import type {
  Collection,
  CollectionCreateRequest,
  CollectionUpdateRequest,
  CollectionListQueryParams,
  CollectionTestResponse,
  CollectionDeleteResponse
} from '@/contracts/api/collection-api'

interface UseCollectionsReturn {
  collections: Collection[]
  loading: boolean
  error: string | null
  fetchCollections: (filters?: CollectionListQueryParams) => Promise<Collection[]>
  createCollection: (collectionData: CollectionCreateRequest) => Promise<Collection>
  updateCollection: (id: number, updates: CollectionUpdateRequest) => Promise<Collection>
  deleteCollection: (id: number, force?: boolean) => Promise<CollectionDeleteResponse | void>
  testCollection: (id: number) => Promise<CollectionTestResponse>
  refreshCollection: (id: number, confirm?: boolean) => Promise<any>
}

export const useCollections = (autoFetch = true): UseCollectionsReturn => {
  const [collections, setCollections] = useState<Collection[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /**
   * Fetch collections with optional filters
   */
  const fetchCollections = useCallback(async (filters: CollectionListQueryParams = {}) => {
    setLoading(true)
    setError(null)
    try {
      const data = await collectionService.listCollections(filters)
      setCollections(data)
      return data
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load collections'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Create a new collection
   */
  const createCollection = useCallback(async (collectionData: CollectionCreateRequest) => {
    setLoading(true)
    setError(null)
    try {
      const newCollection = await collectionService.createCollection(collectionData)
      setCollections(prev => [...prev, newCollection])
      return newCollection
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to create collection'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Update an existing collection
   */
  const updateCollection = useCallback(async (id: number, updates: CollectionUpdateRequest) => {
    setLoading(true)
    setError(null)
    try {
      const updated = await collectionService.updateCollection(id, updates)
      setCollections(prev =>
        prev.map(c => c.id === id ? updated : c)
      )
      return updated
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to update collection'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Delete a collection
   */
  const deleteCollection = useCallback(async (id: number, force = false) => {
    setLoading(true)
    setError(null)
    try {
      const response = await collectionService.deleteCollection(id, force)
      // If response exists, it means collection has results/jobs (status 200)
      if (response) {
        return response
      }
      // No response means deleted successfully (status 204)
      setCollections(prev => prev.filter(c => c.id !== id))
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to delete collection'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Test collection accessibility
   */
  const testCollection = useCallback(async (id: number) => {
    try {
      const result = await collectionService.testCollection(id)
      return result
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Accessibility test failed'
      throw new Error(errorMessage)
    }
  }, [])

  /**
   * Refresh collection cache
   */
  const refreshCollection = useCallback(async (id: number, confirm = false) => {
    try {
      const result = await collectionService.refreshCollection(id, confirm)
      // Refresh the collection in local state
      await fetchCollections()
      return result
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Cache refresh failed'
      throw new Error(errorMessage)
    }
  }, [fetchCollections])

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (autoFetch) {
      fetchCollections()
    }
  }, [autoFetch, fetchCollections])

  return {
    collections,
    loading,
    error,
    fetchCollections,
    createCollection,
    updateCollection,
    deleteCollection,
    testCollection,
    refreshCollection
  }
}
