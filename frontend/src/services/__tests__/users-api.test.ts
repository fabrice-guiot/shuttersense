import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'
import {
  inviteUser,
  listUsers,
  getUserStats,
  getUser,
  deletePendingUser,
  deactivateUser,
  reactivateUser,
} from '@/services/users-api'
import type { User, UserListResponse, UserStatsResponse } from '@/services/users-api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

describe('Users API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const mockUser: User = {
    guid: 'usr_01hgw2bbg00000000000000001',
    email: 'user@example.com',
    first_name: 'John',
    last_name: 'Doe',
    display_name: 'John Doe',
    picture_url: 'https://example.com/photo.jpg',
    status: 'active',
    is_active: true,
    last_login_at: '2026-01-01T00:00:00Z',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    team: {
      guid: 'ten_01hgw2bbg00000000000000001',
      name: 'Test Team',
      slug: 'test-team',
    },
  }

  describe('inviteUser', () => {
    test('invites a new user with email', async () => {
      const pendingUser: User = {
        ...mockUser,
        guid: 'usr_01hgw2bbg00000000000000002',
        email: 'new@example.com',
        status: 'pending',
        first_name: null,
        last_name: null,
        display_name: null,
        picture_url: null,
        last_login_at: null,
      }

      vi.mocked(api.post).mockResolvedValue({ data: pendingUser })

      const result = await inviteUser('new@example.com')

      expect(api.post).toHaveBeenCalledWith('/users', { email: 'new@example.com' })
      expect(result).toEqual(pendingUser)
      expect(result.status).toBe('pending')
    })
  })

  describe('listUsers', () => {
    test('lists all users without filters', async () => {
      const mockResponse: UserListResponse = {
        users: [mockUser],
        total: 1,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockResponse })

      const result = await listUsers()

      expect(api.get).toHaveBeenCalledWith('/users', { params: expect.any(URLSearchParams) })
      const call = vi.mocked(api.get).mock.calls[0]
      const params = call[1]?.params as URLSearchParams
      expect(params.toString()).toBe('')
      expect(result).toEqual(mockResponse)
    })

    test('lists users with status filter', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { users: [], total: 0 } })

      await listUsers({ status: 'pending' })

      const call = vi.mocked(api.get).mock.calls[0]
      const params = call[1]?.params as URLSearchParams
      expect(params.get('status')).toBe('pending')
    })

    test('lists users with activeOnly filter', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { users: [], total: 0 } })

      await listUsers({ activeOnly: true })

      const call = vi.mocked(api.get).mock.calls[0]
      const params = call[1]?.params as URLSearchParams
      expect(params.get('active_only')).toBe('true')
    })

    test('lists users with multiple filters', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: { users: [], total: 0 } })

      await listUsers({ status: 'active', activeOnly: true })

      const call = vi.mocked(api.get).mock.calls[0]
      const params = call[1]?.params as URLSearchParams
      expect(params.get('status')).toBe('active')
      expect(params.get('active_only')).toBe('true')
    })
  })

  describe('getUserStats', () => {
    test('retrieves user statistics', async () => {
      const mockStats: UserStatsResponse = {
        total_users: 20,
        active_users: 15,
        pending_users: 3,
        deactivated_users: 2,
      }

      vi.mocked(api.get).mockResolvedValue({ data: mockStats })

      const result = await getUserStats()

      expect(api.get).toHaveBeenCalledWith('/users/stats')
      expect(result).toEqual(mockStats)
    })
  })

  describe('getUser', () => {
    test('retrieves a user by GUID', async () => {
      vi.mocked(api.get).mockResolvedValue({ data: mockUser })

      const result = await getUser('usr_01hgw2bbg00000000000000001')

      expect(api.get).toHaveBeenCalledWith('/users/usr_01hgw2bbg00000000000000001')
      expect(result).toEqual(mockUser)
    })
  })

  describe('deletePendingUser', () => {
    test('deletes a pending user invitation', async () => {
      vi.mocked(api.delete).mockResolvedValue({ data: undefined })

      await deletePendingUser('usr_01hgw2bbg00000000000000001')

      expect(api.delete).toHaveBeenCalledWith('/users/usr_01hgw2bbg00000000000000001')
    })
  })

  describe('deactivateUser', () => {
    test('deactivates a user', async () => {
      const deactivatedUser = { ...mockUser, status: 'deactivated' as const, is_active: false }
      vi.mocked(api.post).mockResolvedValue({ data: deactivatedUser })

      const result = await deactivateUser('usr_01hgw2bbg00000000000000001')

      expect(api.post).toHaveBeenCalledWith('/users/usr_01hgw2bbg00000000000000001/deactivate')
      expect(result.status).toBe('deactivated')
      expect(result.is_active).toBe(false)
    })
  })

  describe('reactivateUser', () => {
    test('reactivates a user', async () => {
      const reactivatedUser = { ...mockUser, status: 'active' as const, is_active: true }
      vi.mocked(api.post).mockResolvedValue({ data: reactivatedUser })

      const result = await reactivateUser('usr_01hgw2bbg00000000000000001')

      expect(api.post).toHaveBeenCalledWith('/users/usr_01hgw2bbg00000000000000001/reactivate')
      expect(result.status).toBe('active')
      expect(result.is_active).toBe(true)
    })
  })
})
