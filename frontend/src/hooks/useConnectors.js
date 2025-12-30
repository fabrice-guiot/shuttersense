/**
 * useConnectors React hook
 *
 * Manages connector state with fetch, create, update, delete operations
 */

import { useState, useEffect, useCallback } from 'react';
import * as connectorService from '../services/connectors';

export const useConnectors = (autoFetch = true) => {
  const [connectors, setConnectors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Fetch connectors with optional filters
   */
  const fetchConnectors = useCallback(async (filters = {}) => {
    setLoading(true);
    setError(null);
    try {
      const data = await connectorService.listConnectors(filters);
      setConnectors(data);
      return data;
    } catch (err) {
      const errorMessage = err.userMessage || 'Failed to load connectors';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Create a new connector
   */
  const createConnector = useCallback(async (connectorData) => {
    setLoading(true);
    setError(null);
    try {
      const newConnector = await connectorService.createConnector(connectorData);
      setConnectors(prev => [...prev, newConnector]);
      return newConnector;
    } catch (err) {
      const errorMessage = err.userMessage || 'Failed to create connector';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Update an existing connector
   */
  const updateConnector = useCallback(async (id, updates) => {
    setLoading(true);
    setError(null);
    try {
      const updated = await connectorService.updateConnector(id, updates);
      setConnectors(prev =>
        prev.map(c => c.id === id ? updated : c)
      );
      return updated;
    } catch (err) {
      const errorMessage = err.userMessage || 'Failed to update connector';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Delete a connector
   */
  const deleteConnector = useCallback(async (id) => {
    setLoading(true);
    setError(null);
    try {
      await connectorService.deleteConnector(id);
      setConnectors(prev => prev.filter(c => c.id !== id));
    } catch (err) {
      const errorMessage = err.userMessage || 'Failed to delete connector';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Test connector connection
   */
  const testConnector = useCallback(async (id) => {
    try {
      const result = await connectorService.testConnector(id);
      return result;
    } catch (err) {
      const errorMessage = err.userMessage || 'Connection test failed';
      throw new Error(errorMessage);
    }
  }, []);

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (autoFetch) {
      fetchConnectors();
    }
  }, [autoFetch, fetchConnectors]);

  return {
    connectors,
    loading,
    error,
    fetchConnectors,
    createConnector,
    updateConnector,
    deleteConnector,
    testConnector,
  };
};
