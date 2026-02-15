import { describe, test, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AgentDetailPage from '../AgentDetailPage'

vi.mock('@/contexts/HeaderStatsContext', () => ({
  useHeaderStats: vi.fn().mockReturnValue({ setStats: vi.fn() }),
}))

vi.mock('@/hooks/useAgentDetail', () => ({
  useAgentDetail: vi.fn().mockReturnValue({
    agent: {
      guid: 'agt_01hgw2bbg00000000000000001',
      name: 'Test Agent',
      status: 'online',
      version: 'v1.2.3',
      hostname: 'test-host',
      os_info: 'Linux',
      arch: 'x86_64',
      last_heartbeat: '2026-02-14T10:00:00Z',
      created_at: '2026-01-01T00:00:00Z',
      capabilities: [],
      authorized_roots: [],
      team_guid: 'ten_01hgw2bbg00000000000000001',
      current_job_guid: null,
      error_message: null,
      metrics: {
        cpu_percent: 25.5,
        memory_percent: 60.0,
        disk_free_gb: 120.5,
      },
      bound_collections_count: 2,
      total_jobs_completed: 8,
      total_jobs_failed: 1,
      recent_jobs: [],
      audit: null,
    },
    loading: false,
    error: null,
    refetch: vi.fn(),
    wsConnected: false,
  }),
  useAgentJobHistory: vi.fn().mockReturnValue({
    jobs: [],
    loading: false,
    error: null,
    fetchJobs: vi.fn(),
  }),
}))

vi.mock('@/components/agents/AgentStatusBadge', () => ({
  AgentStatusBadge: ({ status }: { status: string }) => (
    <span data-testid="agent-status-badge">{status}</span>
  ),
}))

vi.mock('@/components/GuidBadge', () => ({
  GuidBadge: ({ guid }: { guid: string }) => <span>{guid}</span>,
}))

vi.mock('@/components/audit', () => ({
  AuditTrailSection: () => <div data-testid="audit-section" />,
}))

function renderWithRouter() {
  return render(
    <MemoryRouter initialEntries={['/agents/agt_01hgw2bbg00000000000000001']}>
      <Routes>
        <Route path="/agents/:guid" element={<AgentDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AgentDetailPage', () => {
  test('renders without errors', () => {
    renderWithRouter()

    expect(screen.getByText('Test Agent')).toBeDefined()
  })

  test('renders agent name', () => {
    renderWithRouter()

    expect(screen.getByText('Test Agent')).toBeDefined()
  })

  test('renders agent status badge', () => {
    renderWithRouter()

    expect(screen.getByTestId('agent-status-badge')).toBeDefined()
  })

  test('renders system metrics', () => {
    renderWithRouter()

    expect(screen.getByText('CPU Usage')).toBeDefined()
    expect(screen.getByText('Memory Usage')).toBeDefined()
    expect(screen.getByText('Disk Free')).toBeDefined()
  })

  test('renders agent version', () => {
    renderWithRouter()

    expect(screen.getByText('v1.2.3')).toBeDefined()
  })

  test('shows error state', async () => {
    const { useAgentDetail } = await import('@/hooks/useAgentDetail')
    vi.mocked(useAgentDetail).mockReturnValue({
      agent: null,
      loading: false,
      error: 'Agent not found',
      refetch: vi.fn(),
      wsConnected: false,
    } as any)

    renderWithRouter()

    expect(screen.getByText('Agent not found')).toBeDefined()
  })
})
