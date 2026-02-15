/**
 * Tests for useOrganizers hook
 *
 * Issue #39 - Calendar Events feature (Phase 9)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useOrganizers, useOrganizerStats, useOrganizersByCategory } from '../useOrganizers'
import * as organizerService from '@/services/organizers'
import type {
  Organizer,
  OrganizerCreateRequest,
  OrganizerUpdateRequest,
  OrganizerListParams,
  OrganizerStatsResponse,
} from '@/contracts/api/organizer-api'

// Mock the service
vi.mock('@/services/organizers')

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('useOrganizers', () => {
  const mockOrganizers: Organizer[] = [
    {
      guid: 'org_01hgw2bbg00000000000000001',
      name: 'Elite Sports Club',
      website: null,
      instagram_handle: null,
      instagram_url: null,
      category: { guid: 'cat_sports', name: 'Sports', icon: 'trophy', color: '#FF5733' },
      rating: 5,
      ticket_required_default: false,
      notes: 'Excellent venue',
      created_at: '2026-01-15T10:00:00Z',
      updated_at: '2026-01-15T10:00:00Z',
      audit: {
        created_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        created_at: '2026-01-15T10:00:00Z',
        updated_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        updated_at: '2026-01-15T10:00:00Z',
      },
    },
    {
      guid: 'org_01hgw2bbg00000000000000002',
      name: 'City Music Hall',
      website: null,
      instagram_handle: null,
      instagram_url: null,
      category: { guid: 'cat_music', name: 'Music', icon: 'music', color: '#3498DB' },
      rating: null,
      ticket_required_default: false,
      notes: null,
      created_at: '2026-01-10T08:00:00Z',
      updated_at: '2026-01-10T08:00:00Z',
      audit: {
        created_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        created_at: '2026-01-10T08:00:00Z',
        updated_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        updated_at: '2026-01-10T08:00:00Z',
      },
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(organizerService.listOrganizers).mockResolvedValue({
      items: mockOrganizers,
      total: mockOrganizers.length,
    })
    vi.mocked(organizerService.createOrganizer).mockImplementation(async (data) => ({
      guid: 'org_new',
      name: data.name,
      website: data.website ?? null,
      instagram_handle: data.instagram_handle ?? null,
      instagram_url: null,
      category: { guid: data.category_guid, name: 'Category', icon: null, color: null },
      rating: data.rating ?? null,
      ticket_required_default: data.ticket_required_default ?? false,
      notes: data.notes ?? null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      audit: {
        created_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        created_at: new Date().toISOString(),
        updated_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        updated_at: new Date().toISOString(),
      },
    }))
    vi.mocked(organizerService.updateOrganizer).mockImplementation(async (guid, updates) => ({
      ...mockOrganizers.find(o => o.guid === guid)!,
      ...updates,
    }))
    vi.mocked(organizerService.deleteOrganizer).mockResolvedValue(undefined)
  })

  it('should fetch organizers on mount', async () => {
    const { result } = renderHook(() => useOrganizers())

    expect(result.current.loading).toBe(true)
    expect(result.current.organizers).toEqual([])

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.organizers).toHaveLength(2)
    expect(result.current.total).toBe(2)
    expect(result.current.organizers[0].name).toBe('Elite Sports Club')
    expect(result.current.error).toBe(null)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useOrganizers(false))

    expect(result.current.loading).toBe(false)
    expect(result.current.organizers).toEqual([])
    expect(organizerService.listOrganizers).not.toHaveBeenCalled()
  })

  it('should fetch organizers with filters', async () => {
    const { result } = renderHook(() => useOrganizers(false))

    const params: OrganizerListParams = {
      category_guid: 'cat_sports',
    }

    await act(async () => {
      await result.current.fetchOrganizers(params)
    })

    expect(organizerService.listOrganizers).toHaveBeenCalledWith(params)
    expect(result.current.organizers).toHaveLength(2)
  })

  it('should fetch with initial params', async () => {
    const initialParams: OrganizerListParams = { category_guid: 'cat_sports' }
    const { result } = renderHook(() => useOrganizers(true, initialParams))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(organizerService.listOrganizers).toHaveBeenCalledWith(initialParams)
  })

  it('should create a new organizer', async () => {
    const { result } = renderHook(() => useOrganizers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const createRequest: OrganizerCreateRequest = {
      name: 'New Venue',
      category_guid: 'cat_theater',
      rating: 4,
      notes: 'Good location',
    }

    await act(async () => {
      await result.current.createOrganizer(createRequest)
    })

    expect(organizerService.createOrganizer).toHaveBeenCalledWith(createRequest)
    expect(result.current.organizers).toHaveLength(3)
    expect(result.current.total).toBe(3)
    expect(result.current.organizers[2].name).toBe('New Venue')
  })

  it('should update an organizer', async () => {
    const { result } = renderHook(() => useOrganizers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const updateRequest: OrganizerUpdateRequest = {
      name: 'Elite Sports Club Updated',
      rating: 4,
    }

    await act(async () => {
      await result.current.updateOrganizer('org_01hgw2bbg00000000000000001', updateRequest)
    })

    expect(organizerService.updateOrganizer).toHaveBeenCalledWith(
      'org_01hgw2bbg00000000000000001',
      updateRequest
    )

    const updated = result.current.organizers.find(o => o.guid === 'org_01hgw2bbg00000000000000001')
    expect(updated?.name).toBe('Elite Sports Club Updated')
    expect(updated?.rating).toBe(4)
  })

  it('should delete an organizer', async () => {
    const { result } = renderHook(() => useOrganizers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.organizers).toHaveLength(2)
    expect(result.current.total).toBe(2)

    await act(async () => {
      await result.current.deleteOrganizer('org_01hgw2bbg00000000000000001')
    })

    expect(organizerService.deleteOrganizer).toHaveBeenCalledWith('org_01hgw2bbg00000000000000001')
    expect(result.current.organizers).toHaveLength(1)
    expect(result.current.total).toBe(1)
    expect(result.current.organizers[0].guid).toBe('org_01hgw2bbg00000000000000002')
  })

  it('should handle fetch error', async () => {
    const error = new Error('Network error')
    ;(error as any).userMessage = 'Failed to load organizers'
    vi.mocked(organizerService.listOrganizers).mockRejectedValue(error)

    const { result } = renderHook(() => useOrganizers(false))

    await act(async () => {
      try {
        await result.current.fetchOrganizers()
      } catch {
        // Expected — fetchOrganizers re-throws after setting error state
      }
    })

    expect(result.current.error).toBe('Failed to load organizers')
    expect(result.current.organizers).toEqual([])
  })

  it('should handle create error', async () => {
    const error = new Error('Validation error')
    ;(error as any).userMessage = 'Organizer name already exists'
    vi.mocked(organizerService.createOrganizer).mockRejectedValue(error)

    const { result } = renderHook(() => useOrganizers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      try {
        await result.current.createOrganizer({ name: 'Duplicate', category_guid: 'cat_sports' })
        expect.fail('Should have thrown')
      } catch (err) {
        // Expected
      }
    })

    expect(result.current.error).toBe('Organizer name already exists')
  })
})

describe('useOrganizerStats', () => {
  const mockStats: OrganizerStatsResponse = {
    total_count: 50,
    with_rating_count: 35,
    with_instagram_count: 10,
    avg_rating: 4.2,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(organizerService.getOrganizerStats).mockResolvedValue(mockStats)
  })

  it('should fetch stats on mount', async () => {
    const { result } = renderHook(() => useOrganizerStats())

    expect(result.current.loading).toBe(true)
    expect(result.current.stats).toBe(null)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats).toEqual(mockStats)
    expect(result.current.error).toBe(null)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useOrganizerStats(false))

    expect(result.current.loading).toBe(false)
    expect(result.current.stats).toBe(null)
    expect(organizerService.getOrganizerStats).not.toHaveBeenCalled()
  })

  it('should refetch stats', async () => {
    const { result } = renderHook(() => useOrganizerStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    vi.mocked(organizerService.getOrganizerStats).mockResolvedValue({
      ...mockStats,
      with_rating_count: 40,
      avg_rating: 4.5,
    })

    await act(async () => {
      await result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.stats?.with_rating_count).toBe(40)
      expect(result.current.stats?.avg_rating).toBe(4.5)
    })
  })

  it('should handle stats error', async () => {
    const error = new Error('Network error')
    ;(error as any).userMessage = 'Failed to load statistics'
    vi.mocked(organizerService.getOrganizerStats).mockRejectedValue(error)

    const { result } = renderHook(() => useOrganizerStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to load statistics')
    expect(result.current.stats).toBe(null)
  })
})

describe('useOrganizersByCategory', () => {
  const mockOrganizers: Organizer[] = [
    {
      guid: 'org_01hgw2bbg00000000000000001',
      name: 'Elite Sports Club',
      website: null,
      instagram_handle: null,
      instagram_url: null,
      category: { guid: 'cat_sports', name: 'Sports', icon: 'trophy', color: '#FF5733' },
      rating: 5,
      ticket_required_default: false,
      notes: 'Excellent venue',
      created_at: '2026-01-15T10:00:00Z',
      updated_at: '2026-01-15T10:00:00Z',
      audit: {
        created_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        created_at: '2026-01-15T10:00:00Z',
        updated_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        updated_at: '2026-01-15T10:00:00Z',
      },
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(organizerService.getOrganizersByCategory).mockResolvedValue(mockOrganizers)
  })

  it('should fetch organizers by category', async () => {
    const { result } = renderHook(() => useOrganizersByCategory('cat_sports'))

    expect(result.current.loading).toBe(true)
    expect(result.current.organizers).toEqual([])

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.organizers).toHaveLength(1)
    expect(result.current.organizers[0].name).toBe('Elite Sports Club')
    expect(result.current.error).toBe(null)
    expect(organizerService.getOrganizersByCategory).toHaveBeenCalledWith('cat_sports')
  })

  it('should not fetch when categoryGuid is null', async () => {
    const { result } = renderHook(() => useOrganizersByCategory(null))

    expect(result.current.loading).toBe(false)
    expect(result.current.organizers).toEqual([])
    expect(organizerService.getOrganizersByCategory).not.toHaveBeenCalled()
  })

  it('should refetch when categoryGuid changes', async () => {
    const { result, rerender } = renderHook(
      ({ categoryGuid }) => useOrganizersByCategory(categoryGuid),
      { initialProps: { categoryGuid: 'cat_sports' } }
    )

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(organizerService.getOrganizersByCategory).toHaveBeenCalledWith('cat_sports')
    expect(organizerService.getOrganizersByCategory).toHaveBeenCalledTimes(1)

    // Change category
    rerender({ categoryGuid: 'cat_music' })

    await waitFor(() => {
      expect(organizerService.getOrganizersByCategory).toHaveBeenCalledWith('cat_music')
    })

    expect(organizerService.getOrganizersByCategory).toHaveBeenCalledTimes(2)
  })

  it('should clear organizers when categoryGuid becomes null', async () => {
    const { result, rerender } = renderHook(
      ({ categoryGuid }) => useOrganizersByCategory(categoryGuid),
      { initialProps: { categoryGuid: 'cat_sports' as string | null } }
    )

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.organizers).toHaveLength(1)

    // Change to null
    rerender({ categoryGuid: null })

    expect(result.current.organizers).toEqual([])
  })

  it('should handle fetch error', async () => {
    const error = new Error('Network error')
    ;(error as any).userMessage = 'Failed to load organizers'
    vi.mocked(organizerService.getOrganizersByCategory).mockRejectedValue(error)

    const { result } = renderHook(() => useOrganizersByCategory('cat_sports'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to load organizers')
    expect(result.current.organizers).toEqual([])
  })
})
