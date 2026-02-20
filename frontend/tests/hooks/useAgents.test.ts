/**
 * Tests for useAgents hook
 *
 * Issue #90 - Distributed Agent Architecture (Phase 3)
 * Task: T047
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useAgents, useAgentStats, useRegistrationTokens } from '@/hooks/useAgents'
import * as agentService from '@/services/agents'
import type { Agent, AgentStatsResponse, RegistrationToken, RegistrationTokenListItem } from '@/contracts/api/agent-api'

// Mock the service
vi.mock('@/services/agents')

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('useAgents', () => {
  const mockAgents: Agent[] = [
    {
      guid: 'agt_01hgw2bbg00000000000000001',
      name: 'Studio Mac',
      hostname: 'studio-mac.local',
      os_info: 'macOS 14.0',
      status: 'online',
      error_message: null,
      last_heartbeat: '2026-01-18T12:00:00Z',
      capabilities: ['local_filesystem', 'tool:photostats:1.0.0'],
      authorized_roots: ['/Users/photographer/Photos', '/Volumes/External'],
      version: '1.0.0',
      is_outdated: false,
      is_verified: true,
      platform: 'darwin-arm64',
      created_at: '2026-01-15T10:00:00Z',
      team_guid: 'tea_01hgw2bbg00000000000000001',
      current_job_guid: null,
      running_jobs_count: 0,
    },
    {
      guid: 'agt_01hgw2bbg00000000000000002',
      name: 'Home Server',
      hostname: 'home-server.local',
      os_info: 'Ubuntu 22.04',
      status: 'offline',
      error_message: null,
      last_heartbeat: '2026-01-17T10:00:00Z',
      capabilities: ['local_filesystem'],
      authorized_roots: ['/home/photos'],
      version: '1.0.0',
      is_outdated: false,
      is_verified: true,
      platform: 'linux-amd64',
      created_at: '2026-01-10T08:00:00Z',
      team_guid: 'tea_01hgw2bbg00000000000000001',
      current_job_guid: null,
      running_jobs_count: 0,
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(agentService.listAgents).mockResolvedValue(mockAgents)
    vi.mocked(agentService.updateAgent).mockImplementation(async (guid, data) => ({
      ...mockAgents.find(a => a.guid === guid)!,
      ...data,
    }))
    vi.mocked(agentService.revokeAgent).mockResolvedValue(undefined)
  })

  it('should fetch agents on mount', async () => {
    const { result } = renderHook(() => useAgents())

    expect(result.current.loading).toBe(true)
    expect(result.current.agents).toEqual([])

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.agents).toHaveLength(2)
    expect(result.current.agents[0].name).toBe('Studio Mac')
    expect(result.current.error).toBe(null)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useAgents(false))

    expect(result.current.loading).toBe(false)
    expect(result.current.agents).toEqual([])
    expect(agentService.listAgents).not.toHaveBeenCalled()
  })

  it('should update an agent', async () => {
    const { result } = renderHook(() => useAgents())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.updateAgent('agt_01hgw2bbg00000000000000001', { name: 'Updated Studio Mac' })
    })

    await waitFor(() => {
      const updated = result.current.agents.find(a => a.guid === 'agt_01hgw2bbg00000000000000001')
      expect(updated?.name).toBe('Updated Studio Mac')
    })
  })

  it('should revoke an agent', async () => {
    const { result } = renderHook(() => useAgents())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const initialCount = result.current.agents.length

    await act(async () => {
      await result.current.revokeAgent('agt_01hgw2bbg00000000000000001')
    })

    await waitFor(() => {
      expect(result.current.agents).toHaveLength(initialCount - 1)
    })

    const revoked = result.current.agents.find(a => a.guid === 'agt_01hgw2bbg00000000000000001')
    expect(revoked).toBeUndefined()
  })

  it('should handle fetch error', async () => {
    const error = new Error('Network error')
    ;(error as any).userMessage = 'Network error'
    vi.mocked(agentService.listAgents).mockRejectedValue(error)

    const { result } = renderHook(() => useAgents())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Network error')
    expect(result.current.agents).toEqual([])
  })
})

describe('useAgentStats', () => {
  const mockStats: AgentStatsResponse = {
    total_agents: 5,
    online_agents: 3,
    offline_agents: 2,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(agentService.getAgentStats).mockResolvedValue(mockStats)
  })

  it('should fetch stats on mount', async () => {
    const { result } = renderHook(() => useAgentStats())

    expect(result.current.loading).toBe(true)
    expect(result.current.stats).toBe(null)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.stats).toEqual(mockStats)
    expect(result.current.error).toBe(null)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useAgentStats(false))

    expect(result.current.loading).toBe(false)
    expect(result.current.stats).toBe(null)
    expect(agentService.getAgentStats).not.toHaveBeenCalled()
  })

  it('should refetch stats', async () => {
    const { result } = renderHook(() => useAgentStats())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    vi.mocked(agentService.getAgentStats).mockResolvedValue({
      ...mockStats,
      online_agents: 4,
    })

    await act(async () => {
      await result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.stats?.online_agents).toBe(4)
    })
  })
})

describe('useRegistrationTokens', () => {
  const mockTokens: RegistrationTokenListItem[] = [
    {
      guid: 'art_01hgw2bbg00000000000000001',
      name: 'Studio Token',
      expires_at: '2026-01-20T12:00:00Z',
      is_valid: true,
      is_used: false,
      used_by_agent_guid: null,
      created_at: '2026-01-18T12:00:00Z',
      created_by_email: 'admin@example.com',
    },
  ]

  const mockCreatedToken: RegistrationToken = {
    guid: 'art_01hgw2bbg00000000000000002',
    token: 'art_secret_token_value',
    name: 'New Token',
    expires_at: '2026-01-21T12:00:00Z',
    is_valid: true,
    created_at: '2026-01-18T13:00:00Z',
    created_by_email: 'admin@example.com',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(agentService.listRegistrationTokens).mockResolvedValue(mockTokens)
    vi.mocked(agentService.createRegistrationToken).mockResolvedValue(mockCreatedToken)
    vi.mocked(agentService.deleteRegistrationToken).mockResolvedValue(undefined)
  })

  it('should fetch tokens on mount', async () => {
    const { result } = renderHook(() => useRegistrationTokens())

    expect(result.current.loading).toBe(true)
    expect(result.current.tokens).toEqual([])

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.tokens).toHaveLength(1)
    expect(result.current.tokens[0].name).toBe('Studio Token')
  })

  it('should create a new token', async () => {
    const { result } = renderHook(() => useRegistrationTokens())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    let createdToken: RegistrationToken | undefined

    await act(async () => {
      createdToken = await result.current.createToken({ name: 'New Token' })
    })

    expect(createdToken?.token).toBe('art_secret_token_value')
    expect(agentService.createRegistrationToken).toHaveBeenCalledWith({ name: 'New Token' })
  })

  it('should delete a token', async () => {
    const { result } = renderHook(() => useRegistrationTokens())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.deleteToken('art_01hgw2bbg00000000000000001')
    })

    await waitFor(() => {
      expect(result.current.tokens).toHaveLength(0)
    })

    expect(agentService.deleteRegistrationToken).toHaveBeenCalledWith('art_01hgw2bbg00000000000000001')
  })

  it('should handle token creation error', async () => {
    vi.mocked(agentService.createRegistrationToken).mockRejectedValue({ userMessage: 'Failed to create token' })

    const { result } = renderHook(() => useRegistrationTokens())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      try {
        await result.current.createToken({})
        expect.fail('Should have thrown')
      } catch (err) {
        // Expected
      }
    })

    expect(result.current.error).toBe('Failed to create token')
  })
})
