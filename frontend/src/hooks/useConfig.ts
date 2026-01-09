/**
 * useConfig React hook
 *
 * Manages configuration state with fetch, update, import/export operations
 */

import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import * as configService from '../services/config'
import type {
  ConfigurationResponse,
  CategoryConfigResponse,
  ConfigValueResponse,
  ConfigStatsResponse,
  ImportSessionResponse,
  ImportResultResponse,
  ConfigCategory,
  ConfigValueUpdateRequest,
  ConflictResolutionRequest
} from '@/contracts/api/config-api'

interface UseConfigReturn {
  configuration: ConfigurationResponse | null
  loading: boolean
  error: string | null
  fetchConfiguration: () => Promise<ConfigurationResponse>
  getCategoryConfig: (category: ConfigCategory) => Promise<CategoryConfigResponse>
  createConfigValue: (
    category: ConfigCategory,
    key: string,
    data: ConfigValueUpdateRequest
  ) => Promise<ConfigValueResponse>
  updateConfigValue: (
    category: ConfigCategory,
    key: string,
    data: ConfigValueUpdateRequest
  ) => Promise<ConfigValueResponse>
  deleteConfigValue: (category: ConfigCategory, key: string) => Promise<void>
  startImport: (file: File) => Promise<ImportSessionResponse>
  getImportSession: (sessionId: string) => Promise<ImportSessionResponse>
  resolveImport: (
    sessionId: string,
    request: ConflictResolutionRequest
  ) => Promise<ImportResultResponse>
  cancelImport: (sessionId: string) => Promise<void>
  exportConfiguration: () => Promise<void>
}

export const useConfig = (autoFetch = true): UseConfigReturn => {
  const [configuration, setConfiguration] = useState<ConfigurationResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /**
   * Fetch all configuration
   */
  const fetchConfiguration = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await configService.getConfiguration()
      setConfiguration(data)
      return data
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load configuration'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  /**
   * Get configuration for a specific category
   */
  const getCategoryConfig = useCallback(
    async (category: ConfigCategory) => {
      try {
        return await configService.getCategoryConfig(category)
      } catch (err: any) {
        const errorMessage = err.userMessage || 'Failed to load category configuration'
        throw new Error(errorMessage)
      }
    },
    []
  )

  /**
   * Create a configuration value
   */
  const createConfigValue = useCallback(
    async (category: ConfigCategory, key: string, data: ConfigValueUpdateRequest) => {
      setLoading(true)
      setError(null)
      try {
        const result = await configService.createConfigValue(category, key, data)
        toast.success('Configuration created successfully')
        // Refresh configuration
        await fetchConfiguration()
        return result
      } catch (err: any) {
        const errorMessage = err.userMessage || 'Failed to create configuration'
        setError(errorMessage)
        toast.error('Failed to create configuration', {
          description: errorMessage
        })
        throw err
      } finally {
        setLoading(false)
      }
    },
    [fetchConfiguration]
  )

  /**
   * Update a configuration value
   */
  const updateConfigValue = useCallback(
    async (category: ConfigCategory, key: string, data: ConfigValueUpdateRequest) => {
      setLoading(true)
      setError(null)
      try {
        const result = await configService.updateConfigValue(category, key, data)
        toast.success('Configuration updated successfully')
        // Refresh configuration
        await fetchConfiguration()
        return result
      } catch (err: any) {
        const errorMessage = err.userMessage || 'Failed to update configuration'
        setError(errorMessage)
        toast.error('Failed to update configuration', {
          description: errorMessage
        })
        throw err
      } finally {
        setLoading(false)
      }
    },
    [fetchConfiguration]
  )

  /**
   * Delete a configuration value
   */
  const deleteConfigValue = useCallback(
    async (category: ConfigCategory, key: string) => {
      setLoading(true)
      setError(null)
      try {
        await configService.deleteConfigValue(category, key)
        toast.success('Configuration deleted successfully')
        // Refresh configuration
        await fetchConfiguration()
      } catch (err: any) {
        const errorMessage = err.userMessage || 'Failed to delete configuration'
        setError(errorMessage)
        toast.error('Failed to delete configuration', {
          description: errorMessage
        })
        throw err
      } finally {
        setLoading(false)
      }
    },
    [fetchConfiguration]
  )

  /**
   * Start YAML import
   */
  const startImport = useCallback(async (file: File) => {
    try {
      const session = await configService.startImport(file)
      return session
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to start import'
      toast.error('Import failed', {
        description: errorMessage
      })
      throw err
    }
  }, [])

  /**
   * Get import session status
   */
  const getImportSession = useCallback(async (sessionId: string) => {
    try {
      return await configService.getImportSession(sessionId)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to get import session'
      throw new Error(errorMessage)
    }
  }, [])

  /**
   * Resolve conflicts and apply import
   */
  const resolveImport = useCallback(
    async (sessionId: string, request: ConflictResolutionRequest) => {
      try {
        const result = await configService.resolveImport(sessionId, request)
        toast.success('Import completed', {
          description: result.message
        })
        // Refresh configuration
        await fetchConfiguration()
        return result
      } catch (err: any) {
        const errorMessage = err.userMessage || 'Failed to apply import'
        toast.error('Import failed', {
          description: errorMessage
        })
        throw err
      }
    },
    [fetchConfiguration]
  )

  /**
   * Cancel import session
   */
  const cancelImport = useCallback(async (sessionId: string) => {
    try {
      await configService.cancelImport(sessionId)
      toast.info('Import cancelled')
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to cancel import'
      throw new Error(errorMessage)
    }
  }, [])

  /**
   * Export configuration as YAML file
   */
  const exportConfiguration = useCallback(async () => {
    try {
      const blob = await configService.exportConfiguration()
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `photo-admin-config-${new Date().toISOString().split('T')[0]}.yaml`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      toast.success('Configuration exported successfully')
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to export configuration'
      toast.error('Export failed', {
        description: errorMessage
      })
      throw err
    }
  }, [])

  // Auto-fetch on mount if enabled
  useEffect(() => {
    if (autoFetch) {
      fetchConfiguration()
    }
  }, [autoFetch, fetchConfiguration])

  return {
    configuration,
    loading,
    error,
    fetchConfiguration,
    getCategoryConfig,
    createConfigValue,
    updateConfigValue,
    deleteConfigValue,
    startImport,
    getImportSession,
    resolveImport,
    cancelImport,
    exportConfiguration
  }
}

/**
 * useConfigStats - Separate hook for configuration statistics
 */
interface UseConfigStatsReturn {
  stats: ConfigStatsResponse | null
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

export const useConfigStats = (autoFetch = true): UseConfigStatsReturn => {
  const [stats, setStats] = useState<ConfigStatsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchStats = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await configService.getConfigStats()
      setStats(data)
    } catch (err: any) {
      const errorMessage = err.userMessage || 'Failed to load statistics'
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (autoFetch) {
      fetchStats()
    }
  }, [autoFetch, fetchStats])

  return {
    stats,
    loading,
    error,
    refetch: fetchStats
  }
}
