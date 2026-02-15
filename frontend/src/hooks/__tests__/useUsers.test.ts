/**
 * Tests for useUsers hook
 *
 * Part of Issue #73 - User Story 3: User Pre-Provisioning
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useUsers, useUserStats } from '../useUsers'
import * as usersApi from '@/services/users-api'
import type { User, UserStatsResponse } from '@/services/users-api'

// Mock the service
vi.mock('@/services/users-api')

describe('useUsers', () => {
  const mockTeamInfo = {
    guid: 'ten_01hgw2bbg00000000000000001',
    name: 'Acme Corp',
    slug: 'acme-corp',
  }

  const mockUsers: User[] = [
    {
      guid: 'usr_01hgw2bbg00000000000000001',
      email: 'active@example.com',
      first_name: 'Active',
      last_name: 'User',
      display_name: 'Active User',
      picture_url: null,
      status: 'active',
      is_active: true,
      last_login_at: '2026-01-18T12:00:00Z',
      created_at: '2026-01-15T10:00:00Z',
      team: mockTeamInfo,
      audit: {
        created_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        created_at: '2026-01-15T10:00:00Z',
        updated_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        updated_at: '2026-01-15T10:00:00Z',
      },
    },
    {
      guid: 'usr_01hgw2bbg00000000000000002',
      email: 'pending@example.com',
      first_name: null,
      last_name: null,
      display_name: null,
      picture_url: null,
      status: 'pending',
      is_active: true,
      last_login_at: null,
      created_at: '2026-01-17T12:00:00Z',
      team: mockTeamInfo,
      audit: {
        created_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        created_at: '2026-01-17T12:00:00Z',
        updated_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        updated_at: '2026-01-17T12:00:00Z',
      },
    },
  ]

  const mockStats: UserStatsResponse = {
    total_users: 15,
    active_users: 10,
    pending_users: 3,
    deactivated_users: 2,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(usersApi.listUsers).mockResolvedValue({
      users: mockUsers,
      total: mockUsers.length,
    })
    vi.mocked(usersApi.getUserStats).mockResolvedValue(mockStats)
    vi.mocked(usersApi.inviteUser).mockImplementation(async (email) => ({
      guid: 'usr_new',
      email,
      first_name: null,
      last_name: null,
      display_name: null,
      picture_url: null,
      status: 'pending',
      is_active: true,
      last_login_at: null,
      created_at: new Date().toISOString(),
      team: mockTeamInfo,
    }))
    vi.mocked(usersApi.deletePendingUser).mockResolvedValue(undefined)
    vi.mocked(usersApi.deactivateUser).mockImplementation(async (guid) => ({
      ...mockUsers.find(u => u.guid === guid)!,
      is_active: false,
      status: 'deactivated',
    }))
    vi.mocked(usersApi.reactivateUser).mockImplementation(async (guid) => ({
      ...mockUsers.find(u => u.guid === guid)!,
      is_active: true,
      status: 'active',
    }))
  })

  it('should fetch users and stats on mount', async () => {
    const { result } = renderHook(() => useUsers())

    expect(result.current.loading).toBe(true)
    expect(result.current.users).toEqual([])

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.users).toHaveLength(2)
    expect(result.current.total).toBe(2)
    expect(result.current.stats).toEqual(mockStats)
    expect(result.current.error).toBe(null)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useUsers({ autoFetch: false }))

    expect(result.current.loading).toBe(false)
    expect(result.current.users).toEqual([])
    expect(usersApi.listUsers).not.toHaveBeenCalled()
    expect(usersApi.getUserStats).not.toHaveBeenCalled()
  })

  it('should fetch with initial status filter', async () => {
    const { result } = renderHook(() => useUsers({ initialStatus: 'pending' }))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(usersApi.listUsers).toHaveBeenCalledWith({
      status: 'pending',
      activeOnly: false,
    })
  })

  it('should fetch only active users when activeOnly is true', async () => {
    const { result } = renderHook(() => useUsers({ activeOnly: true }))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(usersApi.listUsers).toHaveBeenCalledWith({
      status: undefined,
      activeOnly: true,
    })
  })

  it('should invite a new user', async () => {
    const { result } = renderHook(() => useUsers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    let invitedUser: User | undefined

    await act(async () => {
      invitedUser = await result.current.invite('newuser@example.com')
    })

    expect(invitedUser?.email).toBe('newuser@example.com')
    expect(invitedUser?.status).toBe('pending')
    expect(usersApi.inviteUser).toHaveBeenCalledWith('newuser@example.com')
    expect(usersApi.listUsers).toHaveBeenCalledTimes(2) // Initial + refetch after invite
    expect(usersApi.getUserStats).toHaveBeenCalledTimes(2)
  })

  it('should delete a pending user', async () => {
    const { result } = renderHook(() => useUsers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.deletePending('usr_01hgw2bbg00000000000000002')
    })

    expect(usersApi.deletePendingUser).toHaveBeenCalledWith('usr_01hgw2bbg00000000000000002')
    expect(usersApi.listUsers).toHaveBeenCalledTimes(2) // Initial + refetch after delete
    expect(usersApi.getUserStats).toHaveBeenCalledTimes(2)
  })

  it('should deactivate a user', async () => {
    const { result } = renderHook(() => useUsers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.deactivate('usr_01hgw2bbg00000000000000001')
    })

    expect(usersApi.deactivateUser).toHaveBeenCalledWith('usr_01hgw2bbg00000000000000001')
    expect(usersApi.listUsers).toHaveBeenCalledTimes(2)
    expect(usersApi.getUserStats).toHaveBeenCalledTimes(2)
  })

  it('should reactivate a user', async () => {
    const { result } = renderHook(() => useUsers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.reactivate('usr_01hgw2bbg00000000000000001')
    })

    expect(usersApi.reactivateUser).toHaveBeenCalledWith('usr_01hgw2bbg00000000000000001')
    expect(usersApi.listUsers).toHaveBeenCalledTimes(2)
    expect(usersApi.getUserStats).toHaveBeenCalledTimes(2)
  })

  it('should refresh users', async () => {
    const { result } = renderHook(() => useUsers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    vi.mocked(usersApi.listUsers).mockResolvedValue({
      users: [...mockUsers, {
        guid: 'usr_new',
        email: 'newuser@example.com',
        first_name: 'New',
        last_name: 'User',
        display_name: 'New User',
        picture_url: null,
        status: 'active',
        is_active: true,
        last_login_at: null,
        created_at: '2026-01-18T12:00:00Z',
        team: mockTeamInfo,
      } as User],
      total: 3,
    })

    await act(async () => {
      await result.current.refresh()
    })

    await waitFor(() => {
      expect(result.current.users).toHaveLength(3)
      expect(result.current.total).toBe(3)
    })
  })

  it('should handle fetch error', async () => {
    const error = new Error('Network error')
    vi.mocked(usersApi.listUsers).mockRejectedValue(error)

    const { result } = renderHook(() => useUsers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Network error')
    expect(result.current.users).toEqual([])
  })

  it('should handle invite error', async () => {
    const error = new Error('Validation error')
    vi.mocked(usersApi.inviteUser).mockRejectedValue(error)

    const { result } = renderHook(() => useUsers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      try {
        await result.current.invite('invalid-email')
        expect.fail('Should have thrown')
      } catch (err) {
        // Expected
      }
    })

    expect(result.current.error).toBe('Validation error')
  })

  it('should handle delete error', async () => {
    const error = new Error('Not found')
    vi.mocked(usersApi.deletePendingUser).mockRejectedValue(error)

    const { result } = renderHook(() => useUsers())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      try {
        await result.current.deletePending('usr_invalid')
        expect.fail('Should have thrown')
      } catch (err) {
        // Expected
      }
    })

    expect(result.current.error).toBe('Not found')
  })
})

describe('useUserStats', () => {
  const mockStats: UserStatsResponse = {
    total_users: 25,
    active_users: 18,
    pending_users: 5,
    deactivated_users: 2,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(usersApi.getUserStats).mockResolvedValue(mockStats)
  })

  it('should fetch stats on mount', async () => {
    const { result } = renderHook(() => useUserStats())

    expect(result.current.loading).toBe(true)
    expect(result.current.stats).toBe(null)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats).toEqual(mockStats)
    expect(result.current.error).toBe(null)
  })

  it('should refetch stats', async () => {
    const { result } = renderHook(() => useUserStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    vi.mocked(usersApi.getUserStats).mockResolvedValue({
      ...mockStats,
      active_users: 20,
    })

    await act(async () => {
      await result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.stats?.active_users).toBe(20)
    })
  })

  it('should handle stats error', async () => {
    const error = new Error('Network error')
    vi.mocked(usersApi.getUserStats).mockRejectedValue(error)

    const { result } = renderHook(() => useUserStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Network error')
    expect(result.current.stats).toBe(null)
  })
})
