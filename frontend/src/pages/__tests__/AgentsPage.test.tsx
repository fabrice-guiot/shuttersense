import { describe, test, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import AgentsPage from '../AgentsPage'

vi.mock('@/contexts/HeaderStatsContext', () => ({
  useHeaderStats: vi.fn().mockReturnValue({ setStats: vi.fn() }),
}))

vi.mock('@/hooks/useAgents', () => ({
  useAgents: vi.fn().mockReturnValue({
    agents: [
      {
        guid: 'agt_01hgw2bbg00000000000000001',
        name: 'Test Agent',
        status: 'online',
        version: 'v1.2.3',
        hostname: 'test-host',
        last_heartbeat_at: '2026-02-14T10:00:00Z',
        created_at: '2026-01-01T00:00:00Z',
        audit: null,
      },
    ],
    loading: false,
    error: null,
    fetchAgents: vi.fn(),
    updateAgent: vi.fn(),
    revokeAgent: vi.fn(),
  }),
  useAgentStats: vi.fn().mockReturnValue({
    stats: { total_agents: 1, online_agents: 1 },
    loading: false,
    refetch: vi.fn(),
  }),
  useRegistrationTokens: vi.fn().mockReturnValue({
    createToken: vi.fn(),
    tokens: [],
    loading: false,
  }),
}))

vi.mock('@/components/agents/AgentStatusBadge', () => ({
  AgentStatusBadge: ({ status }: { status: string }) => (
    <span data-testid="agent-status-badge">{status}</span>
  ),
}))

vi.mock('@/components/agents/AgentDetailsDialog', () => ({
  AgentDetailsDialog: () => <div data-testid="agent-details-dialog" />,
}))

vi.mock('@/components/agents/RegistrationTokenDialog', () => ({
  RegistrationTokenDialog: () => <div data-testid="reg-token-dialog" />,
}))

vi.mock('@/components/agents/AgentSetupWizardDialog', () => ({
  AgentSetupWizardDialog: () => <div data-testid="setup-wizard-dialog" />,
}))

vi.mock('@/components/GuidBadge', () => ({
  GuidBadge: ({ guid }: { guid: string }) => <span>{guid}</span>,
}))

vi.mock('@/components/audit', () => ({
  AuditTrailPopover: () => <div data-testid="audit-popover" />,
}))

describe('AgentsPage', () => {
  test('renders without errors', () => {
    render(
      <MemoryRouter>
        <AgentsPage />
      </MemoryRouter>,
    )

    // Agent name may appear in both the table and mobile card view
    const matches = screen.getAllByText('Test Agent')
    expect(matches.length).toBeGreaterThanOrEqual(1)
  })

  test('renders agent in the list', () => {
    render(
      <MemoryRouter>
        <AgentsPage />
      </MemoryRouter>,
    )

    const matches = screen.getAllByText('Test Agent')
    expect(matches.length).toBeGreaterThanOrEqual(1)
  })

  test('renders action buttons', () => {
    render(
      <MemoryRouter>
        <AgentsPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('New Registration Token')).toBeDefined()
  })

  test('renders agent status badge', () => {
    render(
      <MemoryRouter>
        <AgentsPage />
      </MemoryRouter>,
    )

    const badges = screen.getAllByTestId('agent-status-badge')
    expect(badges.length).toBeGreaterThanOrEqual(1)
  })

  test('shows loading state', async () => {
    const { useAgents } = await import('@/hooks/useAgents')
    vi.mocked(useAgents).mockReturnValue({
      agents: [],
      loading: true,
      error: null,
      fetchAgents: vi.fn(),
      updateAgent: vi.fn(),
      revokeAgent: vi.fn(),
    } as any)

    render(
      <MemoryRouter>
        <AgentsPage />
      </MemoryRouter>,
    )

    expect(screen.queryByText('Test Agent')).toBeNull()
  })
})
