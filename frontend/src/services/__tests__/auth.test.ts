import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'
import {
  getProviders,
  getMe,
  getLoginUrl,
  logout,
  checkAuthStatus,
} from '@/services/auth'
import type { ProvidersResponse, AuthStatusResponse } from '@/contracts/api/auth-api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

describe('auth service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getProviders', () => {
    test('fetches auth providers', async () => {
      const mockResponse: ProvidersResponse = {
        providers: [
          { name: 'google', display_name: 'Google', icon: 'google' },
          { name: 'microsoft', display_name: 'Microsoft', icon: 'microsoft' },
        ],
      }

      vi.mocked(api.get).mockResolvedValueOnce({ data: mockResponse })

      const result = await getProviders()

      expect(api.get).toHaveBeenCalledWith('/auth/providers')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getMe', () => {
    test('fetches current auth status', async () => {
      const mockResponse: AuthStatusResponse = {
        authenticated: true,
        user: {
          user_guid: 'usr_01hgw2bbg00000000000000001',
          email: 'user@example.com',
          team_guid: 'tea_01hgw2bbg00000000000000001',
          team_name: 'Test Team',
          display_name: 'Test User',
          picture_url: null,
          is_super_admin: false,
          first_name: 'Test',
          last_name: 'User',
        },
      }

      vi.mocked(api.get).mockResolvedValueOnce({ data: mockResponse })

      const result = await getMe()

      expect(api.get).toHaveBeenCalledWith('/auth/me')
      expect(result).toEqual(mockResponse)
    })
  })

  describe('getLoginUrl', () => {
    test('returns login URL for provider', () => {
      const result = getLoginUrl('google')
      expect(result).toBe('/api/auth/login/google')
    })

    test('encodes provider name', () => {
      const result = getLoginUrl('my provider')
      expect(result).toBe('/api/auth/login/my%20provider')
    })
  })

  describe('logout', () => {
    test('logs out user', async () => {
      vi.mocked(api.post).mockResolvedValueOnce({ data: { success: true, message: 'Logged out' } })

      const result = await logout()

      expect(api.post).toHaveBeenCalledWith('/auth/logout')
      expect(result.success).toBe(true)
    })
  })

  describe('checkAuthStatus', () => {
    test('returns true when authenticated', async () => {
      vi.mocked(api.get).mockResolvedValueOnce({
        data: { authenticated: true, user: { user_guid: 'usr_01hgw2bbg00000000000000001' } },
      })

      const result = await checkAuthStatus()
      expect(result).toBe(true)
    })

    test('returns false when not authenticated', async () => {
      vi.mocked(api.get).mockRejectedValueOnce(new Error('Unauthorized'))

      const result = await checkAuthStatus()
      expect(result).toBe(false)
    })
  })
})
