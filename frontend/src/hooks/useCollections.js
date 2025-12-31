/**
 * useCollections React hook
 *
 * Manages collection state with fetch, create, update, delete operations
 */

import { useState, useEffect, useCallback } from 'react';
import * as collectionService from '../services/collections';

export const useCollections = (autoFetch = true) => {
  const [collections, setCollections] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Fetch collections with optional filters
   */
  const fetchCollections = useCallback(async (filters = {}) => {
    setLoading(true);
    setError(null);
    try {
      const data = await collectionService.listCollections(filters);
      setCollections(data);
      return data;
    } catch (err) {
      const errorMessage = err.userMessage || 'Failed to load collections';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Create a new collection
   */
  const createCollection = useCallback(async (collectionData) => {
    setLoading(true);
    setError(null);
    try {
      const newCollection = await collectionService.createCollection(collectionData);
      setCollections(prev => [...prev, newCollection]);
      return newCollection;
    } catch (err) {
      const errorMessage = err.userMessage || 'Failed to create collection';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Update an existing collection
   */
  const updateCollection = useCallback(async (id, updates) => {
    setLoading(true);
    setError(null);
    try {
      const updated = await collectionService.updateCollection(id, updates);
      setCollections(prev =>
        prev.map(c => c.id === id ? updated : c)
      );
      return updated;
    } catch (err) {
      const errorMessage = err.userMessage || 'Failed to update collection';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Delete a collection
   */
  const deleteCollection = useCallback(async (id, force = false) => {
    setLoading(true);
    setError(null);
    try {
      const response = await collectionService.deleteCollection(id, force);
      // If response exists, it means collection has results/jobs (status 200)
      if (response) {
        return response;
      }
      // No response means deleted successfully (status 204)
      setCollections(prev => prev.filter(c => c.id !== id));
    } catch (err) {
      const errorMessage = err.userMessage || 'Failed to delete collection';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Test collection accessibility
   */
  const testCollection = useCallback(async (id) => {
    try {
      const result = await collectionService.testCollection(id);
      return result;
    } catch (err) {
      const errorMessage = err.userMessage || 'Accessibility test failed';
      throw new Error(errorMessage);
    }
  }, []);

  /**
   * Refresh collection cache
   */
  const refreshCollection = useCallback(async (id, confirm = false) => {
    try {
      const result = await collectionService.refreshCollection(id, confirm);
      // Refresh the collection in local state
      await fetchCollections();
      return result;
    } catch (err) {
      const errorMessage = err.userMessage || 'Cache refresh failed';
      throw new Error(errorMessage);
    }
  }, [fetchCollections]);

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (autoFetch) {
      fetchCollections();
    }
  }, [autoFetch, fetchCollections]);

  return {
    collections,
    loading,
    error,
    fetchCollections,
    createCollection,
    updateCollection,
    deleteCollection,
    testCollection,
    refreshCollection,
  };
};
