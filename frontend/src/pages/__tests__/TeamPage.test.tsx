import { describe, test, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import TeamPage from '../TeamPage'

vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn().mockReturnValue({
    user: {
      user_guid: 'usr_01hgw2bbg00000000000000001',
      email: 'admin@example.com',
      display_name: 'Admin User',
    },
  }),
}))

vi.mock('@/hooks/useUsers', () => ({
  useUsers: vi.fn().mockReturnValue({
    users: [],
    loading: false,
    error: null,
    invite: vi.fn(),
    deletePending: vi.fn(),
    deactivate: vi.fn(),
    reactivate: vi.fn(),
  }),
  useUserStats: vi.fn().mockReturnValue({
    stats: null,
    refetch: vi.fn(),
  }),
}))

vi.mock('@/contexts/HeaderStatsContext', () => ({
  useHeaderStats: vi.fn().mockReturnValue({
    stats: [],
    setStats: vi.fn(),
    clearStats: vi.fn(),
  }),
}))

vi.mock('@/components/GuidBadge', () => ({
  GuidBadge: () => <span data-testid="guid-badge" />,
}))

vi.mock('@/components/audit', () => ({
  AuditTrailPopover: () => <span data-testid="audit-trail-popover" />,
}))

vi.mock('@/utils/dateFormat', () => ({
  formatRelativeTime: vi.fn().mockReturnValue('2 days ago'),
}))

describe('TeamPage', () => {
  test('renders without error', () => {
    render(
      <MemoryRouter>
        <TeamPage />
      </MemoryRouter>,
    )

    expect(
      screen.getByText(
        'Manage your team members, invite new users, and control access.',
      ),
    ).toBeInTheDocument()
  })

  test('renders invite user button', () => {
    render(
      <MemoryRouter>
        <TeamPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Invite User')).toBeInTheDocument()
  })

  test('renders empty state when no users', () => {
    render(
      <MemoryRouter>
        <TeamPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('No team members yet')).toBeInTheDocument()
  })

  test('renders user list with users', async () => {
    const { useUsers } = await import('@/hooks/useUsers')
    vi.mocked(useUsers).mockReturnValue({
      users: [
        {
          guid: 'usr_01hgw2bbg00000000000000002',
          email: 'member@example.com',
          display_name: 'Team Member',
          picture_url: null,
          status: 'active' as const,
          is_active: true,
          last_login_at: '2026-02-10T00:00:00Z',
          created_at: '2026-01-01T00:00:00Z',
          updated_at: null,
          audit: null,
        },
      ],
      loading: false,
      error: null,
      invite: vi.fn(),
      deletePending: vi.fn(),
      deactivate: vi.fn(),
      reactivate: vi.fn(),
    })

    render(
      <MemoryRouter>
        <TeamPage />
      </MemoryRouter>,
    )

    // ResponsiveTable renders both desktop and mobile views, so multiple matches expected
    const members = screen.getAllByText('Team Member')
    expect(members.length).toBeGreaterThanOrEqual(1)
    const emails = screen.getAllByText('member@example.com')
    expect(emails.length).toBeGreaterThanOrEqual(1)
  })

  test('renders loading state', async () => {
    const { useUsers } = await import('@/hooks/useUsers')
    vi.mocked(useUsers).mockReturnValue({
      users: [],
      loading: true,
      error: null,
      invite: vi.fn(),
      deletePending: vi.fn(),
      deactivate: vi.fn(),
      reactivate: vi.fn(),
    })

    render(
      <MemoryRouter>
        <TeamPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Loading team members...')).toBeInTheDocument()
  })

  test('renders error state', async () => {
    const { useUsers } = await import('@/hooks/useUsers')
    vi.mocked(useUsers).mockReturnValue({
      users: [],
      loading: false,
      error: 'Failed to load team members',
      invite: vi.fn(),
      deletePending: vi.fn(),
      deactivate: vi.fn(),
      reactivate: vi.fn(),
    })

    render(
      <MemoryRouter>
        <TeamPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Failed to load team members')).toBeInTheDocument()
  })
})
