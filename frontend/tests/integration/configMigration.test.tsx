/**
 * Integration tests for configuration migration - T167
 *
 * Tests the complete workflow of configuration management including:
 * - Loading configuration from database
 * - CRUD operations on configuration items
 * - YAML import with conflict detection and resolution
 * - YAML export functionality
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useConfig, useConfigStats } from '@/hooks/useConfig'
import { resetMockData } from '../mocks/handlers'

describe('Configuration Migration Integration', () => {
  beforeEach(() => {
    resetMockData()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Full Configuration Data Flow - T167', () => {
    it('should load all configuration on mount', async () => {
      const { result } = renderHook(() => useConfig())

      // Initially loading
      expect(result.current.loading).toBe(true)

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Configuration should be loaded
      expect(result.current.configuration).not.toBe(null)
      expect(result.current.configuration?.cameras).toBeDefined()
      expect(result.current.configuration?.processing_methods).toBeDefined()
      expect(result.current.configuration?.extensions).toBeDefined()
    })

    it('should load cameras from database', async () => {
      const { result } = renderHook(() => useConfig())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Verify camera data
      expect(result.current.configuration?.cameras).toHaveProperty('AB3D')
      expect(result.current.configuration?.cameras.AB3D.name).toBe('Canon EOS R5')
      expect(result.current.configuration?.cameras.AB3D.serial_number).toBe('12345')

      expect(result.current.configuration?.cameras).toHaveProperty('XY7Z')
      expect(result.current.configuration?.cameras.XY7Z.name).toBe('Sony A7R IV')
    })

    it('should load processing methods from database', async () => {
      const { result } = renderHook(() => useConfig())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Verify processing methods
      expect(result.current.configuration?.processing_methods).toHaveProperty('HDR')
      expect(result.current.configuration?.processing_methods.HDR).toBe('High Dynamic Range')
      expect(result.current.configuration?.processing_methods).toHaveProperty('BW')
      expect(result.current.configuration?.processing_methods.BW).toBe('Black and White')
    })

    it('should load extensions from database', async () => {
      const { result } = renderHook(() => useConfig())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Verify extensions
      const extensions = result.current.configuration?.extensions
      expect(extensions?.photo_extensions).toContain('.dng')
      expect(extensions?.photo_extensions).toContain('.cr3')
      expect(extensions?.metadata_extensions).toContain('.xmp')
      expect(extensions?.require_sidecar).toContain('.cr3')
    })
  })

  describe('CRUD Operations - T167', () => {
    it('should create new camera configuration', async () => {
      const { result } = renderHook(() => useConfig())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Create new camera
      await act(async () => {
        await result.current.createConfigValue('cameras', 'NEW1', {
          value: [{ name: 'New Camera', serial_number: '99999' }],
        })
      })

      // Verify camera was created
      await waitFor(() => {
        expect(result.current.configuration?.cameras).toHaveProperty('NEW1')
      })
    })

    it('should update existing configuration', async () => {
      const { result } = renderHook(() => useConfig())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Update existing processing method
      await act(async () => {
        await result.current.updateConfigValue('processing_methods', 'HDR', {
          value: 'Updated HDR Description',
        })
      })

      // Verify update
      await waitFor(() => {
        expect(result.current.configuration?.processing_methods.HDR).toBe(
          'Updated HDR Description'
        )
      })
    })

    it('should delete configuration value', async () => {
      const { result } = renderHook(() => useConfig())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Verify BW exists
      expect(result.current.configuration?.processing_methods).toHaveProperty('BW')

      // Delete BW processing method
      await act(async () => {
        await result.current.deleteConfigValue('processing_methods', 'BW')
      })

      // Verify deletion
      await waitFor(() => {
        expect(result.current.configuration?.processing_methods).not.toHaveProperty('BW')
      })
    })

    it('should get category configuration', async () => {
      const { result } = renderHook(() => useConfig())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      let categoryConfig: any
      await act(async () => {
        categoryConfig = await result.current.getCategoryConfig('cameras')
      })

      expect(categoryConfig.category).toBe('cameras')
      expect(categoryConfig.items).toBeInstanceOf(Array)
      expect(categoryConfig.items.length).toBeGreaterThan(0)
    })
  })

  describe('Import Flow - T167', () => {
    it('should start import session and detect conflicts', async () => {
      const { result } = renderHook(() => useConfig())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Start import
      const file = new File(['test yaml content'], 'config.yaml', {
        type: 'application/x-yaml',
      })

      let session: any
      await act(async () => {
        session = await result.current.startImport(file)
      })

      // Verify session created
      expect(session.session_id).toBeDefined()
      expect(session.status).toBe('pending')
      expect(session.conflicts).toBeInstanceOf(Array)
    })

    it('should resolve import conflicts', async () => {
      const { result } = renderHook(() => useConfig())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Start import
      const file = new File(['test yaml content'], 'config.yaml', {
        type: 'application/x-yaml',
      })

      let session: any
      await act(async () => {
        session = await result.current.startImport(file)
      })

      // Resolve conflicts
      let importResult: any
      await act(async () => {
        importResult = await result.current.resolveImport(session.session_id, {
          resolutions: [{ category: 'cameras', key: 'AB3D', use_yaml: true }],
        })
      })

      expect(importResult.success).toBe(true)
      expect(importResult.items_imported).toBeGreaterThan(0)
    })

    it('should cancel import session', async () => {
      const { result } = renderHook(() => useConfig())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Start import
      const file = new File(['test yaml content'], 'config.yaml', {
        type: 'application/x-yaml',
      })

      let session: any
      await act(async () => {
        session = await result.current.startImport(file)
      })

      // Cancel import
      await act(async () => {
        await result.current.cancelImport(session.session_id)
      })

      // Verify session is cancelled
      let cancelledSession: any
      await act(async () => {
        cancelledSession = await result.current.getImportSession(session.session_id)
      })

      expect(cancelledSession.status).toBe('cancelled')
    })

    it('should retrieve import session status', async () => {
      const { result } = renderHook(() => useConfig())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Start import
      const file = new File(['test yaml content'], 'config.yaml', {
        type: 'application/x-yaml',
      })

      let session: any
      await act(async () => {
        session = await result.current.startImport(file)
      })

      // Get session status
      let fetchedSession: any
      await act(async () => {
        fetchedSession = await result.current.getImportSession(session.session_id)
      })

      expect(fetchedSession.session_id).toBe(session.session_id)
      expect(fetchedSession.status).toBe('pending')
    })
  })

  describe('Export Flow - T167', () => {
    it('should export configuration to YAML', async () => {
      const { result } = renderHook(() => useConfig())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Export should not throw
      // Note: exportConfiguration triggers a download, which we can't fully test
      // but we can verify the method exists and doesn't throw
      let exportError: Error | null = null
      await act(async () => {
        try {
          await result.current.exportConfiguration()
        } catch (error) {
          exportError = error as Error
        }
      })

      // No error means the export request was made successfully
      // The actual download may fail in test environment, but the API call should succeed
      expect(exportError).toBe(null)
    })
  })

  describe('Configuration Statistics - T167', () => {
    it('should fetch configuration stats', async () => {
      const { result } = renderHook(() => useConfigStats())

      // Initially loading
      expect(result.current.loading).toBe(true)

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Stats should be loaded
      expect(result.current.stats).not.toBe(null)
      expect(result.current.stats?.cameras_configured).toBe(2)
      expect(result.current.stats?.processing_methods_configured).toBe(2)
    })

    it('should refetch stats', async () => {
      const { result } = renderHook(() => useConfigStats())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      const initialCamerasCount = result.current.stats?.cameras_configured

      await act(async () => {
        await result.current.refetch()
      })

      expect(result.current.stats?.cameras_configured).toBe(initialCamerasCount)
    })
  })

  describe('Configuration and Stats Together - T167', () => {
    it('should keep config and stats in sync after create', async () => {
      const { result: configResult } = renderHook(() => useConfig())
      const { result: statsResult } = renderHook(() => useConfigStats())

      await waitFor(() => {
        expect(configResult.current.loading).toBe(false)
        expect(statsResult.current.loading).toBe(false)
      })

      const initialCameraCount = statsResult.current.stats?.cameras_configured

      // Create new camera
      await act(async () => {
        await configResult.current.createConfigValue('cameras', 'SYNC1', {
          value: [{ name: 'Sync Test Camera', serial_number: '11111' }],
        })
      })

      // Refetch stats
      await act(async () => {
        await statsResult.current.refetch()
      })

      // Stats should reflect new camera
      expect(statsResult.current.stats?.cameras_configured).toBe(
        (initialCameraCount || 0) + 1
      )
    })

    it('should keep config and stats in sync after delete', async () => {
      const { result: configResult } = renderHook(() => useConfig())
      const { result: statsResult } = renderHook(() => useConfigStats())

      await waitFor(() => {
        expect(configResult.current.loading).toBe(false)
        expect(statsResult.current.loading).toBe(false)
      })

      const initialMethodCount = statsResult.current.stats?.processing_methods_configured

      // Delete processing method
      await act(async () => {
        await configResult.current.deleteConfigValue('processing_methods', 'BW')
      })

      // Refetch stats
      await act(async () => {
        await statsResult.current.refetch()
      })

      // Stats should reflect deletion
      expect(statsResult.current.stats?.processing_methods_configured).toBe(
        (initialMethodCount || 0) - 1
      )
    })
  })

  describe('Error Handling - T167', () => {
    it('should handle missing import session gracefully', async () => {
      const { result } = renderHook(() => useConfig())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Try to get a non-existent session
      let sessionError: Error | null = null
      await act(async () => {
        try {
          await result.current.getImportSession('non-existent-session-id')
        } catch (error) {
          sessionError = error as Error
        }
      })

      // Should have caught an error for missing session
      expect(sessionError).not.toBe(null)
    })

    it('should handle load error gracefully', async () => {
      const { result } = renderHook(() => useConfig())

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })

      // Even with potential errors, the hook should not crash
      expect(result.current.error).toBe(null)
    })
  })

  describe('Manual Fetch Control - T167', () => {
    it('should not auto-fetch when autoFetch is false', async () => {
      const { result } = renderHook(() => useConfig(false))

      // Should not be loading
      expect(result.current.loading).toBe(false)
      expect(result.current.configuration).toBe(null)
    })

    it('should manually fetch configuration', async () => {
      const { result } = renderHook(() => useConfig(false))

      expect(result.current.configuration).toBe(null)

      await act(async () => {
        await result.current.fetchConfiguration()
      })

      expect(result.current.configuration).not.toBe(null)
      expect(result.current.configuration?.cameras).toHaveProperty('AB3D')
    })

    it('should manually fetch stats when autoFetch is false', async () => {
      const { result } = renderHook(() => useConfigStats(false))

      expect(result.current.stats).toBe(null)

      await act(async () => {
        await result.current.refetch()
      })

      expect(result.current.stats).not.toBe(null)
      expect(result.current.stats?.cameras_configured).toBeGreaterThanOrEqual(0)
    })
  })
})
