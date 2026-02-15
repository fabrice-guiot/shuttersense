/**
 * Tests for useTokens hook
 *
 * Phase 10: User Story 7 - API Token Authentication
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useTokens, useTokenStats } from '../useTokens'
import * as tokenService from '@/services/tokens'
import type { ApiToken, ApiTokenCreated, CreateTokenRequest, TokenStatsResponse } from '@/contracts/api/tokens-api'

// Mock the service
vi.mock('@/services/tokens')

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('useTokens', () => {
  const mockTokens: ApiToken[] = [
    {
      guid: 'tok_01hgw2bbg00000000000000001',
      name: 'Production API',
      token_prefix: 'shusai_p',
      scopes: [],
      expires_at: '2026-04-15T10:00:00Z',
      last_used_at: '2026-01-18T12:00:00Z',
      is_active: true,
      created_at: '2026-01-15T10:00:00Z',
      created_by_guid: 'usr_01hgw2bbg00000000000000001',
      created_by_email: 'admin@example.com',
      audit: {
        created_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        created_at: '2026-01-15T10:00:00Z',
        updated_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        updated_at: '2026-01-15T10:00:00Z',
      },
    },
    {
      guid: 'tok_01hgw2bbg00000000000000002',
      name: 'Testing Token',
      token_prefix: 'shusai_t',
      scopes: [],
      expires_at: '2026-04-10T08:00:00Z',
      last_used_at: null,
      is_active: false,
      created_at: '2026-01-10T08:00:00Z',
      created_by_guid: 'usr_01hgw2bbg00000000000000001',
      created_by_email: 'admin@example.com',
      audit: {
        created_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        created_at: '2026-01-10T08:00:00Z',
        updated_by: { guid: 'usr_01hgw2bbg00000000000000001', display_name: 'Admin User', email: 'admin@example.com' },
        updated_at: '2026-01-17T09:00:00Z',
      },
    },
  ]

  const mockCreatedToken: ApiTokenCreated = {
    guid: 'tok_01hgw2bbg00000000000000003',
    name: 'New Token',
    token_prefix: 'shusai_n',
    scopes: [],
    expires_at: '2026-04-18T13:00:00Z',
    last_used_at: null,
    token: 'shusai_secret_token_value',
    is_active: true,
    created_at: '2026-01-18T13:00:00Z',
    created_by_guid: 'usr_01hgw2bbg00000000000000001',
    created_by_email: 'admin@example.com',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(tokenService.listTokens).mockResolvedValue(mockTokens)
    vi.mocked(tokenService.createToken).mockResolvedValue(mockCreatedToken)
    vi.mocked(tokenService.revokeToken).mockResolvedValue(undefined)
  })

  it('should fetch tokens on mount', async () => {
    const { result } = renderHook(() => useTokens())

    expect(result.current.loading).toBe(true)
    expect(result.current.tokens).toEqual([])

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.tokens).toHaveLength(2)
    expect(result.current.tokens[0].name).toBe('Production API')
    expect(result.current.error).toBe(null)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useTokens(false))

    expect(result.current.loading).toBe(false)
    expect(result.current.tokens).toEqual([])
    expect(tokenService.listTokens).not.toHaveBeenCalled()
  })

  it('should fetch tokens with filters', async () => {
    const { result } = renderHook(() => useTokens(false))

    await act(async () => {
      await result.current.fetchTokens({ active_only: true })
    })

    expect(tokenService.listTokens).toHaveBeenCalledWith({ active_only: true })
    expect(result.current.tokens).toHaveLength(2)
  })

  it('should create a new token', async () => {
    const { result } = renderHook(() => useTokens())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const createRequest: CreateTokenRequest = {
      name: 'New Token',
    }

    let createdToken: ApiTokenCreated | undefined

    await act(async () => {
      createdToken = await result.current.createToken(createRequest)
    })

    expect(createdToken?.token).toBe('shusai_secret_token_value')
    expect(createdToken?.name).toBe('New Token')
    expect(tokenService.createToken).toHaveBeenCalledWith(createRequest)
    expect(tokenService.listTokens).toHaveBeenCalledTimes(2) // Initial + refetch after create
  })

  it('should revoke a token', async () => {
    const { result } = renderHook(() => useTokens())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.tokens[0].is_active).toBe(true)

    await act(async () => {
      await result.current.revokeToken('tok_01hgw2bbg00000000000000001')
    })

    await waitFor(() => {
      const revoked = result.current.tokens.find(t => t.guid === 'tok_01hgw2bbg00000000000000001')
      expect(revoked?.is_active).toBe(false)
    })

    expect(tokenService.revokeToken).toHaveBeenCalledWith('tok_01hgw2bbg00000000000000001')
  })

  it('should handle fetch error', async () => {
    const error = new Error('Network error')
    ;(error as any).userMessage = 'Failed to load tokens'
    vi.mocked(tokenService.listTokens).mockRejectedValue(error)

    // Use autoFetch=false to avoid unhandled rejection from useEffect
    // (fetchTokens re-throws after setting error state)
    const { result } = renderHook(() => useTokens(false))

    await act(async () => {
      try {
        await result.current.fetchTokens()
      } catch {
        // Expected — fetchTokens re-throws after setting error state
      }
    })

    expect(result.current.error).toBe('Failed to load tokens')
    expect(result.current.tokens).toEqual([])
  })

  it('should handle create error', async () => {
    const error = new Error('Validation error')
    ;(error as any).userMessage = 'Token name already exists'
    vi.mocked(tokenService.createToken).mockRejectedValue(error)

    const { result } = renderHook(() => useTokens())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      try {
        await result.current.createToken({ name: 'Duplicate Token' })
        expect.fail('Should have thrown')
      } catch (err) {
        // Expected
      }
    })

    expect(result.current.error).toBe('Token name already exists')
  })

  it('should handle revoke error', async () => {
    const error = new Error('Not found')
    ;(error as any).userMessage = 'Token not found'
    vi.mocked(tokenService.revokeToken).mockRejectedValue(error)

    const { result } = renderHook(() => useTokens())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      try {
        await result.current.revokeToken('tok_invalid')
        expect.fail('Should have thrown')
      } catch (err) {
        // Expected
      }
    })

    expect(result.current.error).toBe('Token not found')
  })
})

describe('useTokenStats', () => {
  const mockStats: TokenStatsResponse = {
    total_count: 10,
    active_count: 7,
    revoked_count: 3,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(tokenService.getTokenStats).mockResolvedValue(mockStats)
  })

  it('should fetch stats on mount', async () => {
    const { result } = renderHook(() => useTokenStats())

    expect(result.current.loading).toBe(true)
    expect(result.current.stats).toBe(null)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats).toEqual(mockStats)
    expect(result.current.error).toBe(null)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useTokenStats(false))

    expect(result.current.loading).toBe(false)
    expect(result.current.stats).toBe(null)
    expect(tokenService.getTokenStats).not.toHaveBeenCalled()
  })

  it('should refetch stats', async () => {
    const { result } = renderHook(() => useTokenStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    vi.mocked(tokenService.getTokenStats).mockResolvedValue({
      ...mockStats,
      active_count: 8,
    })

    await act(async () => {
      await result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.stats?.active_count).toBe(8)
    })
  })

  it('should handle stats error', async () => {
    const error = new Error('Network error')
    ;(error as any).userMessage = 'Failed to load statistics'
    vi.mocked(tokenService.getTokenStats).mockRejectedValue(error)

    const { result } = renderHook(() => useTokenStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to load statistics')
    expect(result.current.stats).toBe(null)
  })
})
