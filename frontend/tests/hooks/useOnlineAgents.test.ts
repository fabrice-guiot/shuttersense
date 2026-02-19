/**
 * Tests for useOnlineAgents hook
 *
 * Issue #90 - Distributed Agent Architecture (Phase 6)
 * Task T114: Hook tests for useOnlineAgents
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useOnlineAgents } from '@/hooks/useOnlineAgents'
import * as agentService from '@/services/agents'
import type { Agent } from '@/contracts/api/agent-api'

// Mock the service
vi.mock('@/services/agents')

describe('useOnlineAgents', () => {
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
      authorized_roots: ['/Users/photographer/Photos'],
      version: '1.0.0',
      is_outdated: false,
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
      platform: 'linux-amd64',
      created_at: '2026-01-10T08:00:00Z',
      team_guid: 'tea_01hgw2bbg00000000000000001',
      current_job_guid: null,
      running_jobs_count: 0,
    },
    {
      guid: 'agt_01hgw2bbg00000000000000003',
      name: 'Office Workstation',
      hostname: 'office-ws.local',
      os_info: 'Windows 11',
      status: 'online',
      error_message: null,
      last_heartbeat: '2026-01-18T12:00:00Z',
      capabilities: ['local_filesystem', 'tool:photostats:1.0.0', 'tool:photo_pairing:1.0.0'],
      authorized_roots: ['C:\\Photos', 'D:\\Archive'],
      version: '1.0.0',
      is_outdated: false,
      platform: 'windows-amd64',
      created_at: '2026-01-12T09:00:00Z',
      team_guid: 'tea_01hgw2bbg00000000000000001',
      current_job_guid: 'job_01hgw2bbg00000000000000001',
      running_jobs_count: 1,
    },
    {
      guid: 'agt_01hgw2bbg00000000000000004',
      name: 'Error Agent',
      hostname: 'error-agent.local',
      os_info: 'Linux',
      status: 'error',
      error_message: 'Connection timeout',
      last_heartbeat: '2026-01-17T08:00:00Z',
      capabilities: ['local_filesystem'],
      authorized_roots: [],
      version: '1.0.0',
      is_outdated: false,
      platform: 'linux-amd64',
      created_at: '2026-01-08T07:00:00Z',
      team_guid: 'tea_01hgw2bbg00000000000000001',
      current_job_guid: null,
      running_jobs_count: 0,
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(agentService.listAgents).mockResolvedValue(mockAgents)
  })

  it('should fetch agents on mount', async () => {
    const { result } = renderHook(() => useOnlineAgents())

    expect(result.current.loading).toBe(true)
    expect(result.current.onlineAgents).toEqual([])

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe(null)
    expect(agentService.listAgents).toHaveBeenCalledWith(false) // Only non-revoked
  })

  it('should filter to only online agents', async () => {
    const { result } = renderHook(() => useOnlineAgents())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Should only include agents with status 'online'
    expect(result.current.onlineAgents).toHaveLength(2)

    const guids = result.current.onlineAgents.map(a => a.guid)
    expect(guids).toContain('agt_01hgw2bbg00000000000000001') // Studio Mac - online
    expect(guids).toContain('agt_01hgw2bbg00000000000000003') // Office Workstation - online
    expect(guids).not.toContain('agt_01hgw2bbg00000000000000002') // Home Server - offline
    expect(guids).not.toContain('agt_01hgw2bbg00000000000000004') // Error Agent - error
  })

  it('should return simplified agent objects', async () => {
    const { result } = renderHook(() => useOnlineAgents())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const agent = result.current.onlineAgents[0]

    // Should have simplified fields
    expect(agent).toHaveProperty('guid')
    expect(agent).toHaveProperty('name')
    expect(agent).toHaveProperty('hostname')
    expect(agent).toHaveProperty('version')

    // Should NOT have full agent fields
    expect(agent).not.toHaveProperty('status')
    expect(agent).not.toHaveProperty('capabilities')
    expect(agent).not.toHaveProperty('os_info')
    expect(agent).not.toHaveProperty('last_heartbeat')
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useOnlineAgents(false))

    expect(result.current.loading).toBe(false)
    expect(result.current.onlineAgents).toEqual([])
    expect(agentService.listAgents).not.toHaveBeenCalled()
  })

  it('should refetch agents', async () => {
    const { result } = renderHook(() => useOnlineAgents())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Add a new online agent
    const newAgents = [
      ...mockAgents,
      {
        guid: 'agt_01hgw2bbg00000000000000005',
        name: 'New Agent',
        hostname: 'new-agent.local',
        os_info: 'Linux',
        status: 'online' as const,
        error_message: null,
        last_heartbeat: '2026-01-18T13:00:00Z',
        capabilities: ['local_filesystem'],
        authorized_roots: ['/data/photos'],
        version: '1.0.0',
        is_outdated: false,
        platform: 'linux-amd64',
        created_at: '2026-01-18T12:00:00Z',
        team_guid: 'tea_01hgw2bbg00000000000000001',
        current_job_guid: null,
      running_jobs_count: 0,
      },
    ]
    vi.mocked(agentService.listAgents).mockResolvedValue(newAgents)

    await act(async () => {
      await result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.onlineAgents).toHaveLength(3)
    })

    const guids = result.current.onlineAgents.map(a => a.guid)
    expect(guids).toContain('agt_01hgw2bbg00000000000000005')
  })

  it('should handle fetch error', async () => {
    const error = new Error('Network error')
    vi.mocked(agentService.listAgents).mockRejectedValue(error)

    const { result } = renderHook(() => useOnlineAgents())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Network error')
    expect(result.current.onlineAgents).toEqual([])
  })

  it('should return empty array when no agents are online', async () => {
    const offlineAgents = mockAgents.map(a => ({ ...a, status: 'offline' as const }))
    vi.mocked(agentService.listAgents).mockResolvedValue(offlineAgents)

    const { result } = renderHook(() => useOnlineAgents())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.onlineAgents).toEqual([])
    expect(result.current.error).toBe(null)
  })

  it('should return empty array when no agents exist', async () => {
    vi.mocked(agentService.listAgents).mockResolvedValue([])

    const { result } = renderHook(() => useOnlineAgents())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.onlineAgents).toEqual([])
    expect(result.current.error).toBe(null)
  })
})
