import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { act } from 'react'
import { useCollections } from '@/hooks/useCollections'
import { resetMockData } from '../mocks/handlers'

describe('useCollections', () => {
  beforeEach(() => {
    resetMockData()
  })

  it('should fetch collections on mount', async () => {
    const { result } = renderHook(() => useCollections())

    // Initially loading
    expect(result.current.loading).toBe(true)
    expect(result.current.collections).toEqual([])

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.collections).toHaveLength(2)
    expect(result.current.collections[0].name).toBe('Test Collection')
    expect(result.current.error).toBe(null)
  })

  it('should create a local collection successfully', async () => {
    const { result } = renderHook(() => useCollections())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const newCollection = {
      name: 'New Local Collection',
      type: 'local' as const,
      location: '/new/photos',
      state: 'live' as const,
      connector_guid: null,
      cache_ttl: null,
    }

    await act(async () => {
      await result.current.createCollection(newCollection)
    })

    await waitFor(() => {
      expect(result.current.collections).toHaveLength(3)
    })

    const created = result.current.collections.find(
      (c) => c.name === 'New Local Collection'
    )
    expect(created).toBeDefined()
    expect(created?.type).toBe('local')
    expect(created?.connector_guid).toBeNull()
  })

  it('should create a remote collection with connector', async () => {
    const { result } = renderHook(() => useCollections())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const newCollection = {
      name: 'New S3 Collection',
      type: 's3' as const,
      location: 'bucket/prefix',
      state: 'live' as const,
      connector_guid: 'con_01hgw2bbg00000000000000001',
      cache_ttl: 3600,
    }

    await act(async () => {
      await result.current.createCollection(newCollection)
    })

    await waitFor(() => {
      expect(result.current.collections).toHaveLength(3)
    })

    const created = result.current.collections.find(
      (c) => c.name === 'New S3 Collection'
    )
    expect(created).toBeDefined()
    expect(created?.connector_guid).toBe('con_01hgw2bbg00000000000000001')
  })

  it('should fail to create collection with invalid connector', async () => {
    const { result } = renderHook(() => useCollections())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const newCollection = {
      name: 'Invalid Collection',
      type: 's3' as const,
      location: 'bucket/prefix',
      state: 'live' as const,
      connector_guid: 'con_01hgw2bbg00000000000000999', // Non-existent connector
      cache_ttl: null,
    }

    await act(async () => {
      try {
        await result.current.createCollection(newCollection)
        expect.fail('Should have thrown 404 error')
      } catch (error: any) {
        expect(error.response?.status).toBe(404)
        expect(error.response?.data?.detail).toContain('Connector not found')
      }
    })
  })

  it('should update a collection successfully', async () => {
    const { result } = renderHook(() => useCollections())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const collectionGuid = result.current.collections[0].guid

    await act(async () => {
      await result.current.updateCollection(collectionGuid, {
        name: 'Updated Collection Name',
        state: 'archived' as const,
      })
    })

    await waitFor(() => {
      const updated = result.current.collections.find((c) => c.guid === collectionGuid)
      expect(updated?.name).toBe('Updated Collection Name')
      expect(updated?.state).toBe('archived')
    })
  })

  it('should delete collection without results successfully', async () => {
    const { result } = renderHook(() => useCollections())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const initialCount = result.current.collections.length
    const collectionGuid = result.current.collections[0].guid // No results

    await act(async () => {
      await result.current.deleteCollection(collectionGuid, false)
    })

    await waitFor(() => {
      expect(result.current.collections).toHaveLength(initialCount - 1)
    })

    const deleted = result.current.collections.find((c) => c.guid === collectionGuid)
    expect(deleted).toBeUndefined()
  })

  it('should return result/job info when deleting collection with data', async () => {
    const { result } = renderHook(() => useCollections())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Collection GUID 2 has results (per mock handler)
    const collectionGuid = 'col_01hgw2bbg00000000000000002'

    let response: any

    await act(async () => {
      response = await result.current.deleteCollection(collectionGuid, false)
      expect(response.has_results).toBe(true)
      expect(response.result_count).toBe(5)
      expect(response.has_jobs).toBe(false)
    })

    // Collection should still exist
    await waitFor(() => {
      const collection = result.current.collections.find((c) => c.guid === collectionGuid)
      expect(collection).toBeDefined()
    })
  })

  it('should force delete collection with results', async () => {
    const { result } = renderHook(() => useCollections())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const initialCount = result.current.collections.length
    const collectionGuid = 'col_01hgw2bbg00000000000000002' // Has results

    await act(async () => {
      await result.current.deleteCollection(collectionGuid, true)
    })

    await waitFor(() => {
      expect(result.current.collections).toHaveLength(initialCount - 1)
    })

    const deleted = result.current.collections.find((c) => c.guid === collectionGuid)
    expect(deleted).toBeUndefined()
  })

  it('should test a collection successfully', async () => {
    const { result } = renderHook(() => useCollections())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const collectionGuid = result.current.collections[0].guid

    await act(async () => {
      const response = await result.current.testCollection(collectionGuid)
      expect(response.success).toBe(true)
      expect(response.message).toBe('Collection is accessible')
    })
  })

  it('should refresh a collection', async () => {
    const { result } = renderHook(() => useCollections())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const collectionGuid = result.current.collections[0].guid

    await act(async () => {
      const response = await result.current.refreshCollection(collectionGuid, false)
      expect(response.message).toContain('Refresh initiated')
      expect(response.task_id).toBeTruthy()
    })
  })

  it('should force refresh a collection', async () => {
    const { result } = renderHook(() => useCollections())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const collectionGuid = result.current.collections[0].guid

    await act(async () => {
      const response = await result.current.refreshCollection(collectionGuid, true)
      expect(response.message).toContain('Force refresh initiated')
      expect(response.task_id).toBeTruthy()
    })
  })
})
