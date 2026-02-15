import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import ProfilePage from '../ProfilePage'

vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn().mockReturnValue({
    user: {
      user_guid: 'usr_01hgw2bbg00000000000000001',
      email: 'test@example.com',
      team_guid: 'ten_01hgw2bbg00000000000000001',
      team_name: 'Test Team',
      display_name: 'Test User',
      picture_url: null,
      is_super_admin: false,
      first_name: 'Test',
      last_name: 'User',
    },
  }),
}))

vi.mock('@/services/users-api', () => ({
  getUser: vi.fn().mockResolvedValue({
    guid: 'usr_01hgw2bbg00000000000000001',
    email: 'test@example.com',
    first_name: 'Test',
    last_name: 'User',
    display_name: 'Test User',
    picture_url: null,
    status: 'active' as const,
    is_active: true,
    last_login_at: '2026-02-01T00:00:00Z',
    created_at: '2026-01-01T00:00:00Z',
    team: { guid: 'ten_01hgw2bbg00000000000000001', name: 'Test Team', slug: 'test-team' },
    audit: null,
  }),
}))

vi.mock('@/components/profile/NotificationPreferences', () => ({
  NotificationPreferences: () => <div data-testid="notification-preferences" />,
}))

vi.mock('@/components/audit', () => ({
  AuditTrailSection: () => <div data-testid="audit-section" />,
}))

describe('ProfilePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('renders user display name in header', async () => {
    render(<ProfilePage />)

    await waitFor(() => {
      // displayName and fullName are both "Test User" — appears multiple times
      const matches = screen.getAllByText('Test User')
      expect(matches.length).toBeGreaterThanOrEqual(1)
    })
  })

  test('renders user email', () => {
    render(<ProfilePage />)

    // Email appears in both header description and profile details
    const emails = screen.getAllByText('test@example.com')
    expect(emails.length).toBeGreaterThanOrEqual(1)
  })

  test('renders team name', () => {
    render(<ProfilePage />)

    expect(screen.getByText('Test Team')).toBeDefined()
  })

  test('renders full name in profile details section', () => {
    render(<ProfilePage />)

    // "Test User" appears as both displayName (header) and fullName (details)
    const matches = screen.getAllByText('Test User')
    expect(matches.length).toBeGreaterThanOrEqual(2)
  })

  test('renders notification preferences', () => {
    render(<ProfilePage />)

    expect(screen.getByTestId('notification-preferences')).toBeDefined()
  })

  test('renders profile details section', () => {
    render(<ProfilePage />)

    expect(screen.getByText('Profile Details')).toBeDefined()
  })

  test('does not show Super Admin badge for non-admin', () => {
    render(<ProfilePage />)

    expect(screen.queryByText('Super Admin')).toBeNull()
  })
})
