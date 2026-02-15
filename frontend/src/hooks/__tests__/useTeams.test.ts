/**
 * Tests for useTeams hook
 *
 * Part of Issue #73 - User Story 5: Team Management
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useTeams, useTeamStats } from '../useTeams'
import * as teamsApi from '@/services/teams-api'
import type { Team, TeamStatsResponse, TeamWithAdmin } from '@/services/teams-api'

// Mock the service
vi.mock('@/services/teams-api')

describe('useTeams', () => {
  const mockTeams: Team[] = [
    {
      guid: 'ten_01hgw2bbg00000000000000001',
      name: 'Acme Corp',
      slug: 'acme-corp',
      is_active: true,
      user_count: 5,
      created_at: '2026-01-15T10:00:00Z',
      updated_at: '2026-01-15T10:00:00Z',
      audit: {
        created_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Super Admin', email: 'superadmin@example.com' },
        created_at: '2026-01-15T10:00:00Z',
        updated_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Super Admin', email: 'superadmin@example.com' },
        updated_at: '2026-01-15T10:00:00Z',
      },
    },
    {
      guid: 'ten_01hgw2bbg00000000000000002',
      name: 'Beta Inc',
      slug: 'beta-inc',
      is_active: false,
      user_count: 3,
      created_at: '2026-01-10T08:00:00Z',
      updated_at: '2026-01-17T09:00:00Z',
      audit: {
        created_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Super Admin', email: 'superadmin@example.com' },
        created_at: '2026-01-10T08:00:00Z',
        updated_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Super Admin', email: 'superadmin@example.com' },
        updated_at: '2026-01-17T09:00:00Z',
      },
    },
  ]

  const mockStats: TeamStatsResponse = {
    total_teams: 5,
    active_teams: 4,
    inactive_teams: 1,
  }

  const mockTeamWithAdmin: TeamWithAdmin = {
    team: mockTeams[0],
    admin_email: 'admin@acme.com',
    admin_guid: 'usr_01hgw2bbg00000000000000002',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(teamsApi.listTeams).mockResolvedValue({
      teams: mockTeams,
      total: mockTeams.length,
    })
    vi.mocked(teamsApi.getTeamStats).mockResolvedValue(mockStats)
    vi.mocked(teamsApi.createTeam).mockResolvedValue(mockTeamWithAdmin)
    vi.mocked(teamsApi.deactivateTeam).mockImplementation(async (guid) => ({
      ...mockTeams.find(t => t.guid === guid)!,
      is_active: false,
    }))
    vi.mocked(teamsApi.reactivateTeam).mockImplementation(async (guid) => ({
      ...mockTeams.find(t => t.guid === guid)!,
      is_active: true,
    }))
  })

  it('should fetch teams and stats on mount', async () => {
    const { result } = renderHook(() => useTeams())

    expect(result.current.loading).toBe(true)
    expect(result.current.teams).toEqual([])

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.teams).toHaveLength(2)
    expect(result.current.total).toBe(2)
    expect(result.current.stats).toEqual(mockStats)
    expect(result.current.error).toBe(null)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useTeams({ autoFetch: false }))

    expect(result.current.loading).toBe(false)
    expect(result.current.teams).toEqual([])
    expect(teamsApi.listTeams).not.toHaveBeenCalled()
    expect(teamsApi.getTeamStats).not.toHaveBeenCalled()
  })

  it('should fetch only active teams when activeOnly is true', async () => {
    const { result } = renderHook(() => useTeams({ activeOnly: true }))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(teamsApi.listTeams).toHaveBeenCalledWith({ activeOnly: true })
  })

  it('should create a new team', async () => {
    const { result } = renderHook(() => useTeams())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    let createdTeamWithAdmin: TeamWithAdmin | undefined

    await act(async () => {
      createdTeamWithAdmin = await result.current.createTeam('New Team', 'admin@newteam.com')
    })

    expect(createdTeamWithAdmin?.team.name).toBe('Acme Corp')
    expect(teamsApi.createTeam).toHaveBeenCalledWith('New Team', 'admin@newteam.com')
    expect(teamsApi.listTeams).toHaveBeenCalledTimes(2) // Initial + refetch after create
    expect(teamsApi.getTeamStats).toHaveBeenCalledTimes(2) // Initial + refetch after create
  })

  it('should deactivate a team', async () => {
    const { result } = renderHook(() => useTeams())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.deactivate('ten_01hgw2bbg00000000000000001')
    })

    expect(teamsApi.deactivateTeam).toHaveBeenCalledWith('ten_01hgw2bbg00000000000000001')
    expect(teamsApi.listTeams).toHaveBeenCalledTimes(2) // Initial + refetch after deactivate
    expect(teamsApi.getTeamStats).toHaveBeenCalledTimes(2)
  })

  it('should reactivate a team', async () => {
    const { result } = renderHook(() => useTeams())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.reactivate('ten_01hgw2bbg00000000000000002')
    })

    expect(teamsApi.reactivateTeam).toHaveBeenCalledWith('ten_01hgw2bbg00000000000000002')
    expect(teamsApi.listTeams).toHaveBeenCalledTimes(2)
    expect(teamsApi.getTeamStats).toHaveBeenCalledTimes(2)
  })

  it('should refresh teams', async () => {
    const { result } = renderHook(() => useTeams())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    vi.mocked(teamsApi.listTeams).mockResolvedValue({
      teams: [...mockTeams, {
        guid: 'ten_new',
        name: 'New Team',
        slug: 'new-team',
        is_active: true,
        user_count: 1,
        created_at: '2026-01-18T12:00:00Z',
        updated_at: '2026-01-18T12:00:00Z',
      } as Team],
      total: 3,
    })

    await act(async () => {
      await result.current.refresh()
    })

    await waitFor(() => {
      expect(result.current.teams).toHaveLength(3)
      expect(result.current.total).toBe(3)
    })
  })

  it('should handle fetch error', async () => {
    const error = new Error('Network error')
    vi.mocked(teamsApi.listTeams).mockRejectedValue(error)

    const { result } = renderHook(() => useTeams())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Network error')
    expect(result.current.teams).toEqual([])
  })

  it('should handle create error', async () => {
    const error = new Error('Validation error')
    vi.mocked(teamsApi.createTeam).mockRejectedValue(error)

    const { result } = renderHook(() => useTeams())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      try {
        await result.current.createTeam('Duplicate Team', 'admin@duplicate.com')
        expect.fail('Should have thrown')
      } catch (err) {
        // Expected
      }
    })

    expect(result.current.error).toBe('Validation error')
  })
})

describe('useTeamStats', () => {
  const mockStats: TeamStatsResponse = {
    total_teams: 10,
    active_teams: 8,
    inactive_teams: 2,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(teamsApi.getTeamStats).mockResolvedValue(mockStats)
  })

  it('should fetch stats on mount', async () => {
    const { result } = renderHook(() => useTeamStats())

    expect(result.current.loading).toBe(true)
    expect(result.current.stats).toBe(null)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats).toEqual(mockStats)
    expect(result.current.error).toBe(null)
  })

  it('should refetch stats', async () => {
    const { result } = renderHook(() => useTeamStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    vi.mocked(teamsApi.getTeamStats).mockResolvedValue({
      ...mockStats,
      active_teams: 9,
    })

    await act(async () => {
      await result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.stats?.active_teams).toBe(9)
    })
  })

  it('should handle stats error', async () => {
    const error = new Error('Network error')
    vi.mocked(teamsApi.getTeamStats).mockRejectedValue(error)

    const { result } = renderHook(() => useTeamStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Network error')
    expect(result.current.stats).toBe(null)
  })
})
