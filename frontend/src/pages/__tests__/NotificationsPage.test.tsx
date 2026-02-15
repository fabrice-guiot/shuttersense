import { describe, test, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import NotificationsPage from '../NotificationsPage'

vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn().mockReturnValue({
    isAuthenticated: true,
    user: {
      user_guid: 'usr_01hgw2bbg00000000000000001',
      email: 'test@example.com',
    },
  }),
}))

vi.mock('@/hooks/useNotifications', () => ({
  useNotifications: vi.fn().mockReturnValue({
    notifications: [],
    total: 0,
    unreadCount: 0,
    loading: false,
    error: null,
    fetchNotifications: vi.fn(),
    markAsRead: vi.fn(),
    markAllAsRead: vi.fn(),
    refreshUnreadCount: vi.fn(),
  }),
  useNotificationStats: vi.fn().mockReturnValue({
    stats: null,
    loading: false,
    error: null,
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

vi.mock('@/components/notifications/NotificationDetailDialog', () => ({
  NotificationDetailDialog: () => (
    <div data-testid="notification-detail-dialog" />
  ),
}))

vi.mock('@/components/ui/responsive-table', () => ({
  ResponsiveTable: ({
    emptyState,
  }: {
    emptyState?: React.ReactNode
    data: unknown[]
    columns: unknown[]
    keyField: string
    onRowClick?: unknown
  }) => <div data-testid="responsive-table">{emptyState}</div>,
}))

vi.mock('@/components/ui/date-picker', () => ({
  DatePicker: () => <div data-testid="date-picker" />,
}))

vi.mock('@/utils/dateFormat', () => ({
  formatRelativeTime: vi.fn().mockReturnValue('1 hour ago'),
}))

describe('NotificationsPage', () => {
  test('renders without error', () => {
    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('responsive-table')).toBeDefined()
  })

  test('renders search input', () => {
    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>,
    )

    expect(
      screen.getByPlaceholderText('Search notifications...'),
    ).toBeDefined()
  })

  test('renders filter controls', () => {
    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>,
    )

    // Category and read status selects render trigger text
    expect(screen.getByText('All categories')).toBeDefined()
    expect(screen.getByText('All')).toBeDefined()
    expect(screen.getByText('All time')).toBeDefined()
  })

  test('renders empty state when no notifications', () => {
    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('No notifications found')).toBeDefined()
    expect(
      screen.getByText('Try adjusting your filters or check back later'),
    ).toBeDefined()
  })

  test('renders loading state', async () => {
    const { useNotifications } = await import('@/hooks/useNotifications')
    vi.mocked(useNotifications).mockReturnValue({
      notifications: [],
      total: 0,
      unreadCount: 0,
      loading: true,
      error: null,
      fetchNotifications: vi.fn(),
      markAsRead: vi.fn(),
      markAllAsRead: vi.fn(),
      refreshUnreadCount: vi.fn(),
    })

    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Loading notifications...')).toBeDefined()
  })

  test('renders error state with retry button', async () => {
    const { useNotifications } = await import('@/hooks/useNotifications')
    vi.mocked(useNotifications).mockReturnValue({
      notifications: [],
      total: 0,
      unreadCount: 0,
      loading: false,
      error: 'Failed to load notifications',
      fetchNotifications: vi.fn(),
      markAsRead: vi.fn(),
      markAllAsRead: vi.fn(),
      refreshUnreadCount: vi.fn(),
    })

    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Failed to load notifications')).toBeDefined()
    expect(screen.getByText('Retry')).toBeDefined()
  })

  test('does not render pagination when no results', () => {
    render(
      <MemoryRouter>
        <NotificationsPage />
      </MemoryRouter>,
    )

    expect(screen.queryByText('Rows per page:')).toBeNull()
  })
})
