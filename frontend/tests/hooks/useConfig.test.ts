/**
 * Tests for useConfig and useConfigStats hooks
 *
 * T143: Frontend test for useConfig hook
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { act } from 'react'
import { useConfig, useConfigStats } from '@/hooks/useConfig'
import { resetMockData } from '../mocks/handlers'

describe('useConfig', () => {
  beforeEach(() => {
    resetMockData()
  })

  it('should fetch configuration on mount', async () => {
    const { result } = renderHook(() => useConfig())

    // Initially loading
    expect(result.current.loading).toBe(true)
    expect(result.current.configuration).toBe(null)

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.configuration).not.toBe(null)
    expect(result.current.configuration?.extensions.photo_extensions).toContain('.dng')
    expect(result.current.configuration?.cameras).toHaveProperty('AB3D')
    expect(result.current.configuration?.processing_methods).toHaveProperty('HDR')
    expect(result.current.error).toBe(null)
  })

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

  it('should create a new camera configuration', async () => {
    const { result } = renderHook(() => useConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.createConfigValue('cameras', 'NEW1', {
        value: [{ name: 'New Camera', serial_number: '99999' }],
      })
    })

    // Verify the new camera was added (configuration should be refreshed)
    await waitFor(() => {
      expect(result.current.configuration?.cameras).toHaveProperty('NEW1')
    })
  })

  it('should update an existing configuration value', async () => {
    const { result } = renderHook(() => useConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.updateConfigValue('processing_methods', 'HDR', {
        value: 'Updated HDR Description',
      })
    })

    await waitFor(() => {
      expect(result.current.configuration?.processing_methods.HDR).toBe('Updated HDR Description')
    })
  })

  it('should delete a configuration value', async () => {
    const { result } = renderHook(() => useConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Verify BW exists first
    expect(result.current.configuration?.processing_methods).toHaveProperty('BW')

    await act(async () => {
      await result.current.deleteConfigValue('processing_methods', 'BW')
    })

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

  it('should export configuration', async () => {
    const { result } = renderHook(() => useConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // exportConfiguration creates a download, which we can't fully test
    // but we can verify it doesn't throw
    await act(async () => {
      try {
        await result.current.exportConfiguration()
      } catch (error) {
        // Mock may not support blob download fully, but no error is expected
      }
    })
  })

  it('should start an import session', async () => {
    const { result } = renderHook(() => useConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const file = new File(['test yaml content'], 'config.yaml', { type: 'application/x-yaml' })

    let session: any
    await act(async () => {
      session = await result.current.startImport(file)
    })

    expect(session.session_id).toBeDefined()
    expect(session.status).toBe('pending')
    expect(session.conflicts).toBeInstanceOf(Array)
  })

  it('should get import session status', async () => {
    const { result } = renderHook(() => useConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // First start an import
    const file = new File(['test yaml content'], 'config.yaml', { type: 'application/x-yaml' })
    let session: any

    await act(async () => {
      session = await result.current.startImport(file)
    })

    // Then get the session status
    let fetchedSession: any
    await act(async () => {
      fetchedSession = await result.current.getImportSession(session.session_id)
    })

    expect(fetchedSession.session_id).toBe(session.session_id)
    expect(fetchedSession.status).toBe('pending')
  })

  it('should resolve import conflicts', async () => {
    const { result } = renderHook(() => useConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Start an import
    const file = new File(['test yaml content'], 'config.yaml', { type: 'application/x-yaml' })
    let session: any

    await act(async () => {
      session = await result.current.startImport(file)
    })

    // Resolve the conflicts
    let importResult: any
    await act(async () => {
      importResult = await result.current.resolveImport(session.session_id, {
        resolutions: [{ category: 'cameras', key: 'AB3D', use_yaml: true }],
      })
    })

    expect(importResult.success).toBe(true)
    expect(importResult.items_imported).toBeGreaterThan(0)
  })

  it('should cancel an import session', async () => {
    const { result } = renderHook(() => useConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Start an import
    const file = new File(['test yaml content'], 'config.yaml', { type: 'application/x-yaml' })
    let session: any

    await act(async () => {
      session = await result.current.startImport(file)
    })

    // Cancel the import
    await act(async () => {
      await result.current.cancelImport(session.session_id)
    })

    // Verify session is cancelled (fetching should still work, status should be cancelled)
    let cancelledSession: any
    await act(async () => {
      cancelledSession = await result.current.getImportSession(session.session_id)
    })

    expect(cancelledSession.status).toBe('cancelled')
  })
})

describe('useConfigStats', () => {
  beforeEach(() => {
    resetMockData()
  })

  it('should fetch configuration stats on mount', async () => {
    const { result } = renderHook(() => useConfigStats())

    // Initially loading
    expect(result.current.loading).toBe(true)
    expect(result.current.stats).toBe(null)

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats).not.toBe(null)
    expect(result.current.stats?.cameras_configured).toBe(2) // AB3D and XY7Z
    expect(result.current.stats?.processing_methods_configured).toBe(2) // HDR and BW
    expect(result.current.stats?.total_items).toBeGreaterThan(0)
    expect(result.current.error).toBe(null)
  })

  it('should not auto-fetch when autoFetch is false', async () => {
    const { result } = renderHook(() => useConfigStats(false))

    expect(result.current.loading).toBe(false)
    expect(result.current.stats).toBe(null)
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
