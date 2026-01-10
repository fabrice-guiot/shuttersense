/**
 * useConnectors React hook
 *
 * Manages connector state with fetch, create, update, delete operations
 */

import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import * as connectorService from '../services/connectors'
import type {
  Connector,
  ConnectorCreateRequest,
  ConnectorUpdateRequest,
  ConnectorTestResponse,
  ConnectorStatsResponse
} from '@/contracts/api/connector-api'

interface UseConnectorsReturn {
  connectors: Connector[]
  loading: boolean
  error: string | null
  fetchConnectors: (filters?: Record<string, any>) => Promise<Connector[]>
  createConnector: (connectorData: ConnectorCreateRequest) => Promise<Connector>
  updateConnector: (guid: string, updates: ConnectorUpdateRequest) => Promise<Connector>
  deleteConnector: (guid: string) => Promise<void>
  testConnector: (guid: string) => Promise<ConnectorTestResponse>
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
      toast.success('Connector created successfully')
      return newConnector
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to create connector'
      setError(errorMessage)
      toast.error('Failed to create connector', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Update an existing connector
   */
  const updateConnector = useCallback(async (guid: string, updates: ConnectorUpdateRequest) => {
    setLoading(true)
    setError(null)
    try {
      const updated = await connectorService.updateConnector(guid, updates)
      setConnectors(prev =>
        prev.map(c => c.guid === guid ? updated : c)
      )
      toast.success('Connector updated successfully')
      return updated
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to update connector'
      setError(errorMessage)
      toast.error('Failed to update connector', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Delete a connector
   */
  const deleteConnector = useCallback(async (guid: string) => {
    setLoading(true)
    setError(null)
    try {
      await connectorService.deleteConnector(guid)
      setConnectors(prev => prev.filter(c => c.guid !== guid))
      toast.success('Connector deleted successfully')
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to delete connector'
      setError(errorMessage)
      toast.error('Failed to delete connector', {
        description: errorMessage
      })
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Test connector connection
   */
  const testConnector = useCallback(async (guid: string) => {
    try {
      const result = await connectorService.testConnector(guid)
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

// ============================================================================
// Connector Stats Hook (Issue #37)
// ============================================================================

interface UseConnectorStatsReturn {
  stats: ConnectorStatsResponse | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * Hook for fetching connector KPI statistics
 * Returns total and active connector counts
 */
export const useConnectorStats = (autoFetch = true): UseConnectorStatsReturn => {
  const [stats, setStats] = useState<ConnectorStatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await connectorService.getConnectorStats()
      setStats(data)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load connector statistics'
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
