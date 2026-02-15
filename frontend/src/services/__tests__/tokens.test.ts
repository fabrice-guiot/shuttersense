import { describe, test, expect, vi, beforeEach } from 'vitest'
import api from '@/services/api'
import {
  listTokens,
  getToken,
  createToken,
  revokeToken,
  getTokenStats,
} from '@/services/tokens'
import type { ApiToken, ApiTokenCreated, TokenStatsResponse } from '@/contracts/api/tokens-api'

vi.mock('@/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

const mockToken: ApiToken = {
  guid: 'tok_01hgw2bbg00000000000000001',
  name: 'Production Token',
  token_prefix: 'shsn_pro',
  scopes: [],
  expires_at: '2026-06-01T00:00:00Z',
  last_used_at: '2026-01-15T12:00:00Z',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  created_by_guid: 'usr_01hgw2bbg00000000000000001',
  created_by_email: 'admin@example.com',
}

describe('tokens service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('listTokens', () => {
    test('fetches tokens without filters', async () => {
      vi.mocked(api.get).mockResolvedValueOnce({ data: [mockToken] })

      const result = await listTokens()

      expect(api.get).toHaveBeenCalledWith('/tokens', { params: {} })
      expect(result).toEqual([mockToken])
    })

    test('fetches tokens with active_only filter', async () => {
      vi.mocked(api.get).mockResolvedValueOnce({ data: [mockToken] })

      const result = await listTokens({ active_only: true })

      expect(api.get).toHaveBeenCalledWith('/tokens', { params: { active_only: true } })
      expect(result).toEqual([mockToken])
    })
  })

  describe('getToken', () => {
    test('fetches token by guid', async () => {
      vi.mocked(api.get).mockResolvedValueOnce({ data: mockToken })

      const result = await getToken('tok_01hgw2bbg00000000000000001')

      expect(api.get).toHaveBeenCalledWith('/tokens/tok_01hgw2bbg00000000000000001')
      expect(result).toEqual(mockToken)
    })
  })

  describe('createToken', () => {
    test('creates new token and returns JWT', async () => {
      const mockCreated: ApiTokenCreated = {
        ...mockToken,
        guid: 'tok_01hgw2bbg00000000000000003',
        name: 'New Token',
        token: 'jwt_secret_value_here',
      }

      vi.mocked(api.post).mockResolvedValueOnce({ data: mockCreated })

      const result = await createToken({ name: 'New Token', expires_in_days: 90 })

      expect(api.post).toHaveBeenCalledWith('/tokens', { name: 'New Token', expires_in_days: 90 })
      expect(result.token).toBe('jwt_secret_value_here')
    })
  })

  describe('revokeToken', () => {
    test('revokes token', async () => {
      vi.mocked(api.delete).mockResolvedValueOnce({ data: undefined })

      await revokeToken('tok_01hgw2bbg00000000000000001')

      expect(api.delete).toHaveBeenCalledWith('/tokens/tok_01hgw2bbg00000000000000001')
    })
  })

  describe('getTokenStats', () => {
    test('fetches token statistics', async () => {
      const mockStats: TokenStatsResponse = {
        total_count: 10,
        active_count: 8,
        revoked_count: 2,
      }

      vi.mocked(api.get).mockResolvedValueOnce({ data: mockStats })

      const result = await getTokenStats()

      expect(api.get).toHaveBeenCalledWith('/tokens/stats')
      expect(result).toEqual(mockStats)
    })
  })
})
