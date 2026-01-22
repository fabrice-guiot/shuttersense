/**
 * Tests for useAgentPoolStatus hook
 *
 * Issue #90 - Distributed Agent Architecture (Phase 4)
 * Task: T062
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useAgentPoolStatus } from '@/hooks/useAgentPoolStatus'
import * as agentService from '@/services/agents'
import type { AgentPoolStatusResponse } from '@/contracts/api/agent-api'

// Mock the service
vi.mock('@/services/agents', () => ({
  getPoolStatus: vi.fn(),
  getPoolStatusWebSocketUrl: vi.fn(() => 'ws://localhost:3000/api/agent/v1/ws/pool-status'),
}))

// Mock useAuth
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    isAuthenticated: true,
  }),
}))

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3
  static instances: MockWebSocket[] = []

  onopen: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: ((event: { code: number }) => void) | null = null
  readyState: number = MockWebSocket.CONNECTING

  constructor(public url: string) {
    MockWebSocket.instances.push(this)
    // Simulate async connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      this.onopen?.()
    }, 0)
  }

  send = vi.fn()
  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.({ code: 1000 })
  })

  // Helper to simulate receiving a message
  simulateMessage(data: any) {
    this.onmessage?.({ data: JSON.stringify(data) })
  }
}

describe('useAgentPoolStatus', () => {
  const mockPoolStatus: AgentPoolStatusResponse = {
    online_count: 3,
    offline_count: 1,
    idle_count: 2,
    running_jobs_count: 1,
    status: 'running',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    MockWebSocket.instances = []
    vi.stubGlobal('WebSocket', MockWebSocket)
    vi.mocked(agentService.getPoolStatus).mockResolvedValue(mockPoolStatus)
    vi.mocked(agentService.getPoolStatusWebSocketUrl).mockReturnValue(
      'ws://localhost:3000/api/agent/v1/ws/pool-status'
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('should connect to WebSocket on mount', async () => {
    renderHook(() => useAgentPoolStatus())

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1)
    })

    expect(MockWebSocket.instances[0].url).toContain('/api/agent/v1/ws/pool-status')
    // No team_guid in URL - authentication is session-based
    expect(MockWebSocket.instances[0].url).not.toContain('team_guid')
  })

  it('should not connect when autoConnect is false', () => {
    renderHook(() => useAgentPoolStatus(false))

    expect(MockWebSocket.instances).toHaveLength(0)
  })

  it('should update poolStatus on WebSocket message', async () => {
    const { result } = renderHook(() => useAgentPoolStatus())

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1)
    })

    // Simulate receiving pool status message
    act(() => {
      MockWebSocket.instances[0].simulateMessage({
        type: 'agent_pool_status',
        pool_status: mockPoolStatus,
      })
    })

    await waitFor(() => {
      expect(result.current.poolStatus).toEqual(mockPoolStatus)
      expect(result.current.loading).toBe(false)
    })
  })

  it('should close WebSocket on unmount', async () => {
    const { unmount } = renderHook(() => useAgentPoolStatus())

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1)
    })

    const ws = MockWebSocket.instances[0]

    unmount()

    expect(ws.close).toHaveBeenCalled()
  })

  it('should allow manual refetch via REST API', async () => {
    const { result } = renderHook(() => useAgentPoolStatus())

    await act(async () => {
      await result.current.refetch()
    })

    expect(agentService.getPoolStatus).toHaveBeenCalled()

    await waitFor(() => {
      expect(result.current.poolStatus).toEqual(mockPoolStatus)
    })
  })

  it('should handle refetch error', async () => {
    const error = new Error('Network error')
    ;(error as any).userMessage = 'Network error'
    vi.mocked(agentService.getPoolStatus).mockRejectedValue(error)

    const { result } = renderHook(() => useAgentPoolStatus())

    await act(async () => {
      await result.current.refetch()
    })

    await waitFor(() => {
      expect(result.current.error).toBe('Network error')
    })
  })

  it('should ignore heartbeat messages', async () => {
    const { result } = renderHook(() => useAgentPoolStatus())

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1)
    })

    // Simulate receiving heartbeat message
    act(() => {
      MockWebSocket.instances[0].simulateMessage({
        type: 'heartbeat',
      })
    })

    // poolStatus should still be null (no update)
    expect(result.current.poolStatus).toBe(null)
  })

  it('should update status when receiving new pool status', async () => {
    const { result } = renderHook(() => useAgentPoolStatus())

    await waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1)
    })

    // First status update
    act(() => {
      MockWebSocket.instances[0].simulateMessage({
        type: 'agent_pool_status',
        pool_status: mockPoolStatus,
      })
    })

    await waitFor(() => {
      expect(result.current.poolStatus?.status).toBe('running')
    })

    // Second status update (agent goes idle)
    const idleStatus: AgentPoolStatusResponse = {
      ...mockPoolStatus,
      status: 'idle',
      running_jobs_count: 0,
    }

    act(() => {
      MockWebSocket.instances[0].simulateMessage({
        type: 'agent_pool_status',
        pool_status: idleStatus,
      })
    })

    await waitFor(() => {
      expect(result.current.poolStatus?.status).toBe('idle')
    })
  })
})
