/**
 * useConnectors React hook
 *
 * Manages connector state with fetch, create, update, delete operations
 */

import { useState, useEffect, useCallback } from 'react'
import * as connectorService from '../services/connectors'
import type {
  Connector,
  ConnectorCreateRequest,
  ConnectorUpdateRequest,
  ConnectorTestResponse
} from '@/contracts/api/connector-api'

interface UseConnectorsReturn {
  connectors: Connector[]
  loading: boolean
  error: string | null
  fetchConnectors: (filters?: Record<string, any>) => Promise<Connector[]>
  createConnector: (connectorData: ConnectorCreateRequest) => Promise<Connector>
  updateConnector: (id: number, updates: ConnectorUpdateRequest) => Promise<Connector>
  deleteConnector: (id: number) => Promise<void>
  testConnector: (id: number) => Promise<ConnectorTestResponse>
}

export const useConnectors = (autoFetch = true): UseConnectorsReturn => {
  const [connectors, setConnectors] = useState<Connector[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /**
   * Fetch connectors with optional filters
   */
  const fetchConnectors = useCallback(async (filters: Record<string, any> = {}) => {
    setLoading(true)
    setError(null)
    try {
      const data = await connectorService.listConnectors(filters)
      setConnectors(data)
      return data
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load connectors'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Create a new connector
   */
  const createConnector = useCallback(async (connectorData: ConnectorCreateRequest) => {
    setLoading(true)
    setError(null)
    try {
      const newConnector = await connectorService.createConnector(connectorData)
      setConnectors(prev => [...prev, newConnector])
      return newConnector
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to create connector'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Update an existing connector
   */
  const updateConnector = useCallback(async (id: number, updates: ConnectorUpdateRequest) => {
    setLoading(true)
    setError(null)
    try {
      const updated = await connectorService.updateConnector(id, updates)
      setConnectors(prev =>
        prev.map(c => c.id === id ? updated : c)
      )
      return updated
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to update connector'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Delete a connector
   */
  const deleteConnector = useCallback(async (id: number) => {
    setLoading(true)
    setError(null)
    try {
      await connectorService.deleteConnector(id)
      setConnectors(prev => prev.filter(c => c.id !== id))
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to delete connector'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Test connector connection
   */
  const testConnector = useCallback(async (id: number) => {
    try {
      const result = await connectorService.testConnector(id)
      return result
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Connection test failed'
      throw new Error(errorMessage)
    }
  }, [])

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (autoFetch) {
      fetchConnectors()
    }
  }, [autoFetch, fetchConnectors])

  return {
    connectors,
    loading,
    error,
    fetchConnectors,
    createConnector,
    updateConnector,
    deleteConnector,
    testConnector
  }
}
