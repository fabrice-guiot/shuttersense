/**
 * Unit tests for usePerformers hook.
 *
 * Tests CRUD operations, category filtering, and statistics.
 * Issue #39 - Calendar Events feature (Phase 11)
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { act } from 'react'
import { usePerformers, usePerformerStats, usePerformersByCategory } from '@/hooks/usePerformers'
import { resetMockData } from '../mocks/handlers'

describe('usePerformers', () => {
  beforeEach(() => {
    resetMockData()
  })

  it('should fetch performers on mount', async () => {
    const { result } = renderHook(() => usePerformers())

    // Initially loading
    expect(result.current.loading).toBe(true)
    expect(result.current.performers).toEqual([])

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.performers).toHaveLength(3)
    expect(result.current.performers[0].name).toBe('Blue Angels')
    expect(result.current.error).toBe(null)
  })

  it('should return total count', async () => {
    const { result } = renderHook(() => usePerformers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.total).toBe(3)
  })

  it('should create a performer successfully', async () => {
    const { result } = renderHook(() => usePerformers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const newPerformer = {
      name: 'Snowbirds',
      category_guid: 'cat_01hgw2bbg00000000000000001',
      website: 'https://rcaf-arc.forces.gc.ca/snowbirds',
      instagram_handle: '@cfsnowbirds',
    }

    await act(async () => {
      await result.current.createPerformer(newPerformer)
    })

    await waitFor(() => {
      expect(result.current.performers).toHaveLength(4)
    })

    const created = result.current.performers.find(
      (p) => p.name === 'Snowbirds'
    )
    expect(created).toBeDefined()
    expect(created?.instagram_handle).toBe('cfsnowbirds') // @ stripped
    expect(created?.category.guid).toBe('cat_01hgw2bbg00000000000000001')
  })

  it('should create a performer with minimal data', async () => {
    const { result } = renderHook(() => usePerformers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const newPerformer = {
      name: 'Solo Pilot',
      category_guid: 'cat_01hgw2bbg00000000000000001',
    }

    await act(async () => {
      await result.current.createPerformer(newPerformer)
    })

    await waitFor(() => {
      const created = result.current.performers.find(
        (p) => p.name === 'Solo Pilot'
      )
      expect(created).toBeDefined()
      expect(created?.website).toBe(null)
      expect(created?.instagram_handle).toBe(null)
    })
  })

  it('should fail to create performer with invalid category', async () => {
    const { result } = renderHook(() => usePerformers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const newPerformer = {
      name: 'Invalid Category Performer',
      category_guid: 'cat_00000000000000000000000000', // Non-existent
    }

    await act(async () => {
      try {
        await result.current.createPerformer(newPerformer)
        expect.fail('Should have thrown 404 error')
      } catch (error: any) {
        expect(error.response?.status).toBe(404)
      }
    })
  })

  it('should update a performer successfully', async () => {
    const { result } = renderHook(() => usePerformers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const performerGuid = result.current.performers[0].guid

    await act(async () => {
      await result.current.updatePerformer(performerGuid, {
        name: 'Updated Blue Angels',
        website: 'https://updated-website.com',
      })
    })

    await waitFor(() => {
      const updated = result.current.performers.find((p) => p.guid === performerGuid)
      expect(updated?.name).toBe('Updated Blue Angels')
      expect(updated?.website).toBe('https://updated-website.com')
    })
  })

  it('should update performer instagram handle', async () => {
    const { result } = renderHook(() => usePerformers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const performerGuid = result.current.performers[0].guid

    await act(async () => {
      await result.current.updatePerformer(performerGuid, {
        instagram_handle: '@newhandle',
      })
    })

    await waitFor(() => {
      const updated = result.current.performers.find((p) => p.guid === performerGuid)
      expect(updated?.instagram_handle).toBe('newhandle') // @ stripped
    })
  })

  it('should delete a performer successfully', async () => {
    const { result } = renderHook(() => usePerformers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const initialCount = result.current.performers.length
    const performerGuid = result.current.performers[0].guid

    await act(async () => {
      await result.current.deletePerformer(performerGuid)
    })

    await waitFor(() => {
      expect(result.current.performers).toHaveLength(initialCount - 1)
    })

    const deleted = result.current.performers.find((p) => p.guid === performerGuid)
    expect(deleted).toBeUndefined()
  })

  it('should handle delete of non-existent performer', async () => {
    const { result } = renderHook(() => usePerformers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      try {
        await result.current.deletePerformer('prf_00000000000000000000000000')
        expect.fail('Should have thrown 404 error')
      } catch (error: any) {
        expect(error.response?.status).toBe(404)
      }
    })
  })

  it('should fetch performers with search filter', async () => {
    const { result } = renderHook(() => usePerformers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.fetchPerformers({ search: 'Angels' })
    })

    await waitFor(() => {
      expect(result.current.performers.length).toBeGreaterThanOrEqual(1)
      expect(result.current.performers[0].name).toContain('Angels')
    })
  })

  it('should fetch performers filtered by category', async () => {
    const { result } = renderHook(() => usePerformers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.fetchPerformers({
        category_guid: 'cat_01hgw2bbg00000000000000001'
      })
    })

    await waitFor(() => {
      // All returned performers should have the specified category
      result.current.performers.forEach((p) => {
        expect(p.category.guid).toBe('cat_01hgw2bbg00000000000000001')
      })
    })
  })

  it('should not auto-fetch when autoFetch is false', async () => {
    const { result } = renderHook(() => usePerformers(false))

    // Should not be loading since autoFetch is false
    expect(result.current.loading).toBe(false)
    expect(result.current.performers).toEqual([])

    // Manually fetch
    await act(async () => {
      await result.current.fetchPerformers({})
    })

    await waitFor(() => {
      expect(result.current.performers).toHaveLength(3)
    })
  })
})

describe('usePerformerStats', () => {
  beforeEach(() => {
    resetMockData()
  })

  it('should fetch performer stats on mount', async () => {
    const { result } = renderHook(() => usePerformerStats())

    // Initially loading
    expect(result.current.loading).toBe(true)
    expect(result.current.stats).toBe(null)

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats).not.toBe(null)
    expect(result.current.stats?.total_count).toBe(3)
    expect(result.current.stats?.with_instagram_count).toBe(2)
    expect(result.current.stats?.with_website_count).toBe(2)
    expect(result.current.error).toBe(null)
  })

  it('should allow manual refetch of stats', async () => {
    const { result } = renderHook(() => usePerformerStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const initialStats = result.current.stats

    await act(async () => {
      await result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.stats).not.toBe(null)
    })

    // Stats should still be valid after refetch
    expect(result.current.stats?.total_count).toBe(initialStats?.total_count)
  })

  it('should not auto-fetch when autoFetch is false', async () => {
    const { result } = renderHook(() => usePerformerStats(false))

    expect(result.current.loading).toBe(false)
    expect(result.current.stats).toBe(null)
  })
})

describe('usePerformersByCategory', () => {
  beforeEach(() => {
    resetMockData()
  })

  it('should fetch performers for a category', async () => {
    const { result } = renderHook(() =>
      usePerformersByCategory('cat_01hgw2bbg00000000000000001')
    )

    // Initially loading
    expect(result.current.loading).toBe(true)
    expect(result.current.performers).toEqual([])

    // Wait for data to load
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Should have performers for Airshow category
    expect(result.current.performers.length).toBeGreaterThan(0)
    result.current.performers.forEach((p) => {
      expect(p.category.guid).toBe('cat_01hgw2bbg00000000000000001')
    })
  })

  it('should return empty array when category is null', async () => {
    const { result } = renderHook(() => usePerformersByCategory(null))

    // Should not be loading since no category
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.performers).toEqual([])
  })

  it('should refetch when category changes', async () => {
    const { result, rerender } = renderHook(
      ({ categoryGuid }) => usePerformersByCategory(categoryGuid),
      { initialProps: { categoryGuid: 'cat_01hgw2bbg00000000000000001' } }
    )

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Should have airshow performers
    expect(result.current.performers.length).toBe(2)

    // Change to different category (wildlife)
    rerender({ categoryGuid: 'cat_01hgw2bbg00000000000000002' })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Should have wildlife performers now
    result.current.performers.forEach((p) => {
      expect(p.category.guid).toBe('cat_01hgw2bbg00000000000000002')
    })
  })

  it('should allow manual refetch with search', async () => {
    const { result } = renderHook(() =>
      usePerformersByCategory('cat_01hgw2bbg00000000000000001')
    )

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.refetch('Angels')
    })

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Should filter to just Blue Angels
    expect(result.current.performers.length).toBe(1)
    expect(result.current.performers[0].name).toBe('Blue Angels')
  })
})
