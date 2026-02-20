/**
 * Tests for useAgentDetail hooks
 *
 * Issue #90 - Distributed Agent Architecture (Phase 11)
 * Task: T173
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useAgentDetail, useAgentJobHistory } from '@/hooks/useAgentDetail'
import * as agentService from '@/services/agents'
import type { AgentDetailResponse, AgentJobHistoryResponse } from '@/contracts/api/agent-api'

// Mock the service
vi.mock('@/services/agents')

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  readyState = MockWebSocket.CONNECTING
  onopen: (() => void) | null = null
  onclose: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: (() => void) | null = null

  constructor(_url: string) {
    // Simulate connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      this.onopen?.()
    }, 10)
  }

  send(_data: string) {
    // Mock send
  }

  close() {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.()
  }
}

// Use vi.stubGlobal for WebSocket mock
vi.stubGlobal('WebSocket', MockWebSocket)

describe('useAgentDetail', () => {
  const mockAgentDetail: AgentDetailResponse = {
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
    is_verified: true,
    matched_manifest: null,
    platform: 'darwin-arm64',
    created_at: '2026-01-15T10:00:00Z',
    team_guid: 'tea_01hgw2bbg00000000000000001',
    current_job_guid: null,
    metrics: {
      cpu_percent: 45.5,
      memory_percent: 62.3,
      disk_free_gb: 128.7,
    },
    bound_collections_count: 3,
    total_jobs_completed: 15,
    total_jobs_failed: 2,
    recent_jobs: [
      {
        guid: 'job_01hgw2bbg00000000000000001',
        tool: 'photostats',
        status: 'completed',
        collection_guid: 'col_01hgw2bbg00000000000000001',
        collection_name: 'Holiday Photos',
        started_at: '2026-01-18T10:00:00Z',
        completed_at: '2026-01-18T10:05:00Z',
        error_message: null,
      },
    ],
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(agentService.getAgentDetail).mockResolvedValue(mockAgentDetail)
    vi.mocked(agentService.getPoolStatusWebSocketUrl).mockReturnValue('ws://localhost:8000/ws/pool-status')
  })

  it('should fetch agent detail on mount', async () => {
    const { result } = renderHook(() => useAgentDetail('agt_01hgw2bbg00000000000000001'))

    expect(result.current.loading).toBe(true)
    expect(result.current.agent).toBe(null)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.agent).toEqual(mockAgentDetail)
    expect(result.current.error).toBe(null)
    expect(agentService.getAgentDetail).toHaveBeenCalledWith('agt_01hgw2bbg00000000000000001')
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useAgentDetail('agt_01hgw2bbg00000000000000001', false))

    expect(result.current.loading).toBe(false)
    expect(result.current.agent).toBe(null)
    expect(agentService.getAgentDetail).not.toHaveBeenCalled()
  })

  it('should not fetch when guid is empty', async () => {
    renderHook(() => useAgentDetail(''))

    // The hook sets loading=true initially but does not call the API with empty guid
    await waitFor(() => {
      expect(agentService.getAgentDetail).not.toHaveBeenCalled()
    })
  })

  it('should handle fetch error', async () => {
    vi.mocked(agentService.getAgentDetail).mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useAgentDetail('agt_01hgw2bbg00000000000000001'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Network error')
    expect(result.current.agent).toBe(null)
  })

  it('should handle fetch error without Error instance', async () => {
    vi.mocked(agentService.getAgentDetail).mockRejectedValue('Some error string')

    const { result } = renderHook(() => useAgentDetail('agt_01hgw2bbg00000000000000001'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to fetch agent details')
  })

  it('should refetch when refetch is called', async () => {
    const { result } = renderHook(() => useAgentDetail('agt_01hgw2bbg00000000000000001'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Clear mocks to check refetch
    vi.mocked(agentService.getAgentDetail).mockClear()

    // Update mock response for refetch
    vi.mocked(agentService.getAgentDetail).mockResolvedValue({
      ...mockAgentDetail,
      status: 'offline',
    })

    await act(async () => {
      await result.current.refetch()
    })

    expect(agentService.getAgentDetail).toHaveBeenCalledTimes(1)
    expect(result.current.agent?.status).toBe('offline')
  })

  it('should connect to WebSocket when enableRealtime is true', async () => {
    const { result } = renderHook(() => useAgentDetail('agt_01hgw2bbg00000000000000001', true, true))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Wait for WebSocket to connect
    await waitFor(() => {
      expect(result.current.wsConnected).toBe(true)
    })
  })

  it('should not connect to WebSocket when enableRealtime is false', async () => {
    const { result } = renderHook(() => useAgentDetail('agt_01hgw2bbg00000000000000001', true, false))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // WebSocket should not be connected
    expect(result.current.wsConnected).toBe(false)
  })

  it('should include metrics in response', async () => {
    const { result } = renderHook(() => useAgentDetail('agt_01hgw2bbg00000000000000001'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.agent?.metrics).toEqual({
      cpu_percent: 45.5,
      memory_percent: 62.3,
      disk_free_gb: 128.7,
    })
  })

  it('should include job statistics in response', async () => {
    const { result } = renderHook(() => useAgentDetail('agt_01hgw2bbg00000000000000001'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.agent?.total_jobs_completed).toBe(15)
    expect(result.current.agent?.total_jobs_failed).toBe(2)
    expect(result.current.agent?.bound_collections_count).toBe(3)
  })
})

describe('useAgentJobHistory', () => {
  const mockJobHistory: AgentJobHistoryResponse = {
    jobs: [
      {
        guid: 'job_01hgw2bbg00000000000000001',
        tool: 'photostats',
        status: 'completed',
        collection_guid: 'col_01hgw2bbg00000000000000001',
        collection_name: 'Holiday Photos',
        started_at: '2026-01-18T10:00:00Z',
        completed_at: '2026-01-18T10:05:00Z',
        error_message: null,
      },
      {
        guid: 'job_01hgw2bbg00000000000000002',
        tool: 'photopairing',
        status: 'failed',
        collection_guid: 'col_01hgw2bbg00000000000000002',
        collection_name: 'Wedding Photos',
        started_at: '2026-01-18T11:00:00Z',
        completed_at: '2026-01-18T11:02:00Z',
        error_message: 'Connection timeout',
      },
    ],
    total_count: 25,
    offset: 0,
    limit: 20,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(agentService.getAgentJobHistory).mockResolvedValue(mockJobHistory)
  })

  it('should fetch job history on mount', async () => {
    const { result } = renderHook(() => useAgentJobHistory('agt_01hgw2bbg00000000000000001'))

    expect(result.current.loading).toBe(true)
    expect(result.current.jobs).toEqual([])

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.jobs).toHaveLength(2)
    expect(result.current.totalCount).toBe(25)
    expect(result.current.offset).toBe(0)
    expect(result.current.limit).toBe(20)
    expect(agentService.getAgentJobHistory).toHaveBeenCalledWith('agt_01hgw2bbg00000000000000001', 0, 20)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => useAgentJobHistory('agt_01hgw2bbg00000000000000001', 20, false))

    expect(result.current.loading).toBe(false)
    expect(result.current.jobs).toEqual([])
    expect(agentService.getAgentJobHistory).not.toHaveBeenCalled()
  })

  it('should not fetch when guid is empty', async () => {
    renderHook(() => useAgentJobHistory(''))

    // The hook sets loading=true initially but does not call the API with empty guid
    await waitFor(() => {
      expect(agentService.getAgentJobHistory).not.toHaveBeenCalled()
    })
  })

  it('should use custom limit', async () => {
    const { result } = renderHook(() => useAgentJobHistory('agt_01hgw2bbg00000000000000001', 10))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.limit).toBe(10)
    expect(agentService.getAgentJobHistory).toHaveBeenCalledWith('agt_01hgw2bbg00000000000000001', 0, 10)
  })

  it('should handle pagination with fetchPage', async () => {
    const { result } = renderHook(() => useAgentJobHistory('agt_01hgw2bbg00000000000000001'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Clear mocks
    vi.mocked(agentService.getAgentJobHistory).mockClear()

    // Mock second page
    vi.mocked(agentService.getAgentJobHistory).mockResolvedValue({
      ...mockJobHistory,
      offset: 20,
    })

    await act(async () => {
      await result.current.fetchPage(20)
    })

    expect(agentService.getAgentJobHistory).toHaveBeenCalledWith('agt_01hgw2bbg00000000000000001', 20, 20)
    expect(result.current.offset).toBe(20)
  })

  it('should handle fetch error', async () => {
    vi.mocked(agentService.getAgentJobHistory).mockRejectedValue(new Error('Failed to load jobs'))

    const { result } = renderHook(() => useAgentJobHistory('agt_01hgw2bbg00000000000000001'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to load jobs')
    expect(result.current.jobs).toEqual([])
  })

  it('should handle fetch error without Error instance', async () => {
    vi.mocked(agentService.getAgentJobHistory).mockRejectedValue('Some error')

    const { result } = renderHook(() => useAgentJobHistory('agt_01hgw2bbg00000000000000001'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to fetch job history')
  })
})
