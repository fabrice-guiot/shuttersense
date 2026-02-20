/**
 * Tests for AgentDetailPage component
 *
 * Issue #90 - Distributed Agent Architecture (Phase 11)
 * Task: T172
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '../../utils/test-utils'
import AgentDetailPage from '@/pages/AgentDetailPage'
import * as agentService from '@/services/agents'
import type { AgentDetailResponse, AgentJobHistoryResponse } from '@/contracts/api/agent-api'

// Mock the services
vi.mock('@/services/agents')

// Mock react-router-dom
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useParams: () => ({ guid: 'agt_01hgw2bbg00000000000000001' }),
    useNavigate: () => mockNavigate,
  }
})

// Mock HeaderStatsContext
vi.mock('@/contexts/HeaderStatsContext', () => ({
  useHeaderStats: () => ({
    setStats: vi.fn(),
  }),
}))

// Mock WebSocket
vi.stubGlobal('WebSocket', class {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3
  readyState = 0
  onopen: (() => void) | null = null
  onclose: (() => void) | null = null
  onmessage: (() => void) | null = null
  onerror: (() => void) | null = null
  send() {}
  close() {}
})

describe('AgentDetailPage', () => {
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
    total_count: 17,
    offset: 0,
    limit: 10,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockClear()
    vi.mocked(agentService.getAgentDetail).mockResolvedValue(mockAgentDetail)
    vi.mocked(agentService.getAgentJobHistory).mockResolvedValue(mockJobHistory)
    vi.mocked(agentService.getPoolStatusWebSocketUrl).mockReturnValue('ws://localhost:8000/ws/pool-status')
  })

  it('shows loading state initially', async () => {
    // Delay the response to catch loading state
    vi.mocked(agentService.getAgentDetail).mockImplementation(() =>
      new Promise(resolve => setTimeout(() => resolve(mockAgentDetail), 100))
    )

    render(<AgentDetailPage />)

    // Should show skeleton loading state
    expect(document.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('displays agent name and status after loading', async () => {
    render(<AgentDetailPage />)

    await waitFor(() => {
      expect(screen.getByText('Studio Mac')).toBeInTheDocument()
    })

    expect(screen.getByText('Online')).toBeInTheDocument()
  })

  it('displays agent hostname', async () => {
    render(<AgentDetailPage />)

    await waitFor(() => {
      expect(screen.getByText('studio-mac.local')).toBeInTheDocument()
    })
  })

  it('displays system metrics', async () => {
    render(<AgentDetailPage />)

    await waitFor(() => {
      expect(screen.getByText('CPU Usage')).toBeInTheDocument()
    })

    expect(screen.getByText('45.5')).toBeInTheDocument()
    expect(screen.getByText('Memory Usage')).toBeInTheDocument()
    expect(screen.getByText('62.3')).toBeInTheDocument()
    expect(screen.getByText('Disk Free')).toBeInTheDocument()
    expect(screen.getByText('128.7')).toBeInTheDocument()
  })

  it('displays job statistics', async () => {
    render(<AgentDetailPage />)

    await waitFor(() => {
      expect(screen.getByText('Jobs Completed')).toBeInTheDocument()
    })

    expect(screen.getByText('15')).toBeInTheDocument()
    expect(screen.getByText('Jobs Failed')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('Bound Collections')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('displays agent information', async () => {
    render(<AgentDetailPage />)

    await waitFor(() => {
      expect(screen.getByText('Agent Information')).toBeInTheDocument()
    })

    expect(screen.getByText('macOS 14.0')).toBeInTheDocument()
    expect(screen.getByText('1.0.0')).toBeInTheDocument()
  })

  it('displays capabilities', async () => {
    render(<AgentDetailPage />)

    await waitFor(() => {
      expect(screen.getByText('Capabilities')).toBeInTheDocument()
    })

    expect(screen.getByText('local_filesystem')).toBeInTheDocument()
    expect(screen.getByText('tool:photostats:1.0.0')).toBeInTheDocument()
  })

  it('displays authorized roots', async () => {
    render(<AgentDetailPage />)

    await waitFor(() => {
      expect(screen.getByText('Authorized Roots')).toBeInTheDocument()
    })

    expect(screen.getByText('/Users/photographer/Photos')).toBeInTheDocument()
  })

  it('displays recent jobs table', async () => {
    render(<AgentDetailPage />)

    await waitFor(() => {
      expect(screen.getByText('Recent Jobs')).toBeInTheDocument()
    })

    expect(screen.getAllByText('photostats')[0]).toBeInTheDocument()
    expect(screen.getAllByText('Holiday Photos')[0]).toBeInTheDocument()
  })

  it('displays job history with pagination info', async () => {
    render(<AgentDetailPage />)

    await waitFor(() => {
      expect(screen.getByText(/17 total/)).toBeInTheDocument()
    })
  })

  it('navigates back when back button is clicked', async () => {
    const user = userEvent.setup()
    render(<AgentDetailPage />)

    await waitFor(() => {
      expect(screen.getByText('Studio Mac')).toBeInTheDocument()
    })

    // Find the back button (icon button with ArrowLeft)
    const backButton = screen.getByRole('button', { name: '' })
    await user.click(backButton)

    expect(mockNavigate).toHaveBeenCalledWith('/agents')
  })

  it('shows refresh button', async () => {
    render(<AgentDetailPage />)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Refresh/i })).toBeInTheDocument()
    })
  })

  it('refetches data when refresh is clicked', async () => {
    const user = userEvent.setup()
    render(<AgentDetailPage />)

    await waitFor(() => {
      expect(screen.getByText('Studio Mac')).toBeInTheDocument()
    })

    // Clear mock calls
    vi.mocked(agentService.getAgentDetail).mockClear()

    const refreshButton = screen.getByRole('button', { name: /Refresh/i })
    await user.click(refreshButton)

    await waitFor(() => {
      expect(agentService.getAgentDetail).toHaveBeenCalled()
    })
  })

  it('displays error state when fetch fails', async () => {
    vi.mocked(agentService.getAgentDetail).mockRejectedValue(new Error('Network error'))

    render(<AgentDetailPage />)

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument()
    })

    // Should show back to agents button
    expect(screen.getByRole('button', { name: /Back to Agents/i })).toBeInTheDocument()
  })

  it('displays error message when agent has error status', async () => {
    vi.mocked(agentService.getAgentDetail).mockResolvedValue({
      ...mockAgentDetail,
      status: 'error',
      error_message: 'Connection timeout',
    })

    render(<AgentDetailPage />)

    await waitFor(() => {
      expect(screen.getByText('Connection timeout')).toBeInTheDocument()
    })
  })

  it('displays "No data" when metrics are null', async () => {
    vi.mocked(agentService.getAgentDetail).mockResolvedValue({
      ...mockAgentDetail,
      metrics: null,
    })

    render(<AgentDetailPage />)

    await waitFor(() => {
      expect(screen.getByText('CPU Usage')).toBeInTheDocument()
    })

    // Should show "No data" for each metric
    expect(screen.getAllByText('No data')).toHaveLength(3)
  })

  it('displays empty jobs message when no jobs', async () => {
    vi.mocked(agentService.getAgentJobHistory).mockResolvedValue({
      jobs: [],
      total_count: 0,
      offset: 0,
      limit: 10,
    })

    render(<AgentDetailPage />)

    await waitFor(() => {
      expect(screen.getByText('No jobs have been executed by this agent')).toBeInTheDocument()
    })
  })

  it('displays current job when agent is running a job', async () => {
    vi.mocked(agentService.getAgentDetail).mockResolvedValue({
      ...mockAgentDetail,
      current_job_guid: 'job_current123',
    })

    render(<AgentDetailPage />)

    await waitFor(() => {
      expect(screen.getByText('Currently Running')).toBeInTheDocument()
    })

    expect(screen.getByText('job_current123')).toBeInTheDocument()
  })

  it('displays no capabilities message when empty', async () => {
    vi.mocked(agentService.getAgentDetail).mockResolvedValue({
      ...mockAgentDetail,
      capabilities: [],
    })

    render(<AgentDetailPage />)

    await waitFor(() => {
      expect(screen.getByText('No capabilities reported')).toBeInTheDocument()
    })
  })

  it('handles pagination controls', async () => {
    const user = userEvent.setup()
    render(<AgentDetailPage />)

    await waitFor(() => {
      expect(screen.getByText(/Showing 1 - 10 of 17/)).toBeInTheDocument()
    })

    // Next button should be enabled
    const nextButton = screen.getByRole('button', { name: /Next/i })
    expect(nextButton).not.toBeDisabled()

    // Previous button should be disabled on first page
    const prevButton = screen.getByRole('button', { name: /Previous/i })
    expect(prevButton).toBeDisabled()

    // Click next
    vi.mocked(agentService.getAgentJobHistory).mockClear()
    vi.mocked(agentService.getAgentJobHistory).mockResolvedValue({
      ...mockJobHistory,
      offset: 10,
    })

    await user.click(nextButton)

    await waitFor(() => {
      expect(agentService.getAgentJobHistory).toHaveBeenCalledWith(
        'agt_01hgw2bbg00000000000000001',
        10,
        10
      )
    })
  })
})
