/**
 * Tests for AgentPoolStatus component
 *
 * Issue #90 - Distributed Agent Architecture (Phase 4)
 * Task: T061
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent } from '@testing-library/react'
import { render } from '../../utils/test-utils'
import { AgentPoolStatus } from '@/components/layout/AgentPoolStatus'
import * as useAgentPoolStatusHook from '@/hooks/useAgentPoolStatus'
import type { AgentPoolStatusResponse } from '@/contracts/api/agent-api'

// Mock the hook
vi.mock('@/hooks/useAgentPoolStatus')

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

describe('AgentPoolStatus', () => {
  const mockRefetch = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Running status', () => {
    const runningStatus: AgentPoolStatusResponse = {
      online_count: 3,
      offline_count: 1,
      idle_count: 2,
      running_jobs_count: 5,
      status: 'running',
    }

    beforeEach(() => {
      vi.mocked(useAgentPoolStatusHook.useAgentPoolStatus).mockReturnValue({
        poolStatus: runningStatus,
        loading: false,
        error: null,
        refetch: mockRefetch,
      })
    })

    it('renders green "Running" badge with job count', () => {
      render(<AgentPoolStatus />)

      expect(screen.getByText('Running')).toBeInTheDocument()
      expect(screen.getByText('(5)')).toBeInTheDocument()
    })

    it('uses success (green) color for running status', () => {
      const { container } = render(<AgentPoolStatus />)

      const badge = container.querySelector('.bg-success')
      expect(badge).toBeInTheDocument()
    })
  })

  describe('Idle status', () => {
    const idleStatus: AgentPoolStatusResponse = {
      online_count: 3,
      offline_count: 0,
      idle_count: 3,
      running_jobs_count: 0,
      status: 'idle',
    }

    beforeEach(() => {
      vi.mocked(useAgentPoolStatusHook.useAgentPoolStatus).mockReturnValue({
        poolStatus: idleStatus,
        loading: false,
        error: null,
        refetch: mockRefetch,
      })
    })

    it('renders blue "Idle" badge with online agent count', () => {
      render(<AgentPoolStatus />)

      expect(screen.getByText('Idle')).toBeInTheDocument()
      expect(screen.getByText('(3)')).toBeInTheDocument()
    })

    it('uses info (blue) color for idle status', () => {
      const { container } = render(<AgentPoolStatus />)

      const badge = container.querySelector('.bg-info')
      expect(badge).toBeInTheDocument()
    })
  })

  describe('Offline status', () => {
    const offlineStatus: AgentPoolStatusResponse = {
      online_count: 0,
      offline_count: 2,
      idle_count: 0,
      running_jobs_count: 0,
      status: 'offline',
    }

    beforeEach(() => {
      vi.mocked(useAgentPoolStatusHook.useAgentPoolStatus).mockReturnValue({
        poolStatus: offlineStatus,
        loading: false,
        error: null,
        refetch: mockRefetch,
      })
    })

    it('renders red "Offline" badge with total registered agent count', () => {
      render(<AgentPoolStatus />)

      expect(screen.getByText('Offline')).toBeInTheDocument()
      expect(screen.getByText('(2)')).toBeInTheDocument()
    })

    it('uses destructive (red) color for offline status', () => {
      const { container } = render(<AgentPoolStatus />)

      const badge = container.querySelector('.bg-destructive')
      expect(badge).toBeInTheDocument()
    })
  })

  describe('No agents registered', () => {
    const emptyStatus: AgentPoolStatusResponse = {
      online_count: 0,
      offline_count: 0,
      idle_count: 0,
      running_jobs_count: 0,
      status: 'offline',
    }

    beforeEach(() => {
      vi.mocked(useAgentPoolStatusHook.useAgentPoolStatus).mockReturnValue({
        poolStatus: emptyStatus,
        loading: false,
        error: null,
        refetch: mockRefetch,
      })
    })

    it('renders "Offline (0)" when no agents registered', () => {
      render(<AgentPoolStatus />)

      expect(screen.getByText('Offline')).toBeInTheDocument()
      expect(screen.getByText('(0)')).toBeInTheDocument()
    })
  })

  describe('Navigation', () => {
    beforeEach(() => {
      vi.mocked(useAgentPoolStatusHook.useAgentPoolStatus).mockReturnValue({
        poolStatus: {
          online_count: 1,
          offline_count: 0,
          idle_count: 1,
          running_jobs_count: 0,
          status: 'idle',
        },
        loading: false,
        error: null,
        refetch: mockRefetch,
      })
    })

    it('navigates to /agents on click', () => {
      render(<AgentPoolStatus />)

      const button = screen.getByRole('button', { name: /agent pool status/i })
      fireEvent.click(button)

      expect(mockNavigate).toHaveBeenCalledWith('/agents')
    })
  })

  describe('Loading and error states', () => {
    it('does not render while loading initial data', () => {
      vi.mocked(useAgentPoolStatusHook.useAgentPoolStatus).mockReturnValue({
        poolStatus: null,
        loading: true,
        error: null,
        refetch: mockRefetch,
      })

      const { container } = render(<AgentPoolStatus />)

      expect(container.firstChild).toBeNull()
    })

    it('does not render when error and no data', () => {
      vi.mocked(useAgentPoolStatusHook.useAgentPoolStatus).mockReturnValue({
        poolStatus: null,
        loading: false,
        error: 'Failed to load',
        refetch: mockRefetch,
      })

      const { container } = render(<AgentPoolStatus />)

      expect(container.firstChild).toBeNull()
    })

    it('renders with stale data during loading', () => {
      vi.mocked(useAgentPoolStatusHook.useAgentPoolStatus).mockReturnValue({
        poolStatus: {
          online_count: 3,
          offline_count: 0,
          idle_count: 3,
          running_jobs_count: 0,
          status: 'idle',
        },
        loading: true,
        error: null,
        refetch: mockRefetch,
      })

      render(<AgentPoolStatus />)

      expect(screen.getByText('Idle')).toBeInTheDocument()
      expect(screen.getByText('(3)')).toBeInTheDocument()
    })

    it('renders with cached data despite error', () => {
      vi.mocked(useAgentPoolStatusHook.useAgentPoolStatus).mockReturnValue({
        poolStatus: {
          online_count: 2,
          offline_count: 1,
          idle_count: 0,
          running_jobs_count: 2,
          status: 'running',
        },
        loading: false,
        error: 'Network error',
        refetch: mockRefetch,
      })

      render(<AgentPoolStatus />)

      expect(screen.getByText('Running')).toBeInTheDocument()
      expect(screen.getByText('(2)')).toBeInTheDocument()
    })
  })

  describe('Bot icon', () => {
    it('shows Bot icon in badge', () => {
      vi.mocked(useAgentPoolStatusHook.useAgentPoolStatus).mockReturnValue({
        poolStatus: {
          online_count: 1,
          offline_count: 0,
          idle_count: 1,
          running_jobs_count: 0,
          status: 'idle',
        },
        loading: false,
        error: null,
        refetch: mockRefetch,
      })

      const { container } = render(<AgentPoolStatus />)

      // Lucide icons render as SVG
      const svg = container.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })
  })

  describe('Custom className', () => {
    it('applies custom className', () => {
      vi.mocked(useAgentPoolStatusHook.useAgentPoolStatus).mockReturnValue({
        poolStatus: {
          online_count: 1,
          offline_count: 0,
          idle_count: 1,
          running_jobs_count: 0,
          status: 'idle',
        },
        loading: false,
        error: null,
        refetch: mockRefetch,
      })

      render(<AgentPoolStatus className="custom-class" />)

      const button = screen.getByRole('button', { name: /agent pool status/i })
      expect(button).toHaveClass('custom-class')
    })
  })
})
