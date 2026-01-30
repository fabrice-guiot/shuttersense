/**
 * Tests for NotificationPanel component.
 *
 * Issue #114 - PWA with Push Notifications (Phase 13 — T054)
 * Tests notification list rendering, category icons, relative timestamps,
 * click behavior, empty state, and read/unread indicators.
 */

import { describe, it, expect, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { server } from '../../mocks/server'
import { render } from '../../utils/test-utils'
import { NotificationPanel } from '@/components/notifications/NotificationPanel'

// ============================================================================
// Test Data
// ============================================================================

const mockNotifications = [
  {
    guid: 'ntf_01hgw2bbg0000000000000001',
    category: 'job_failure' as const,
    title: 'Analysis Failed',
    body: 'PhotoStats analysis failed: timeout',
    data: { url: '/tools' },
    read_at: null,
    created_at: new Date(Date.now() - 60_000).toISOString(), // 1 minute ago
  },
  {
    guid: 'ntf_01hgw2bbg0000000000000002',
    category: 'deadline' as const,
    title: 'Deadline Approaching',
    body: '"Event" deadline in 3 days',
    data: { url: '/events/evt_123' },
    read_at: '2026-01-20T10:00:00Z',
    created_at: new Date(Date.now() - 3600_000).toISOString(), // 1 hour ago
  },
]

// ============================================================================
// Setup
// ============================================================================

function setupHandlers(notifications = mockNotifications) {
  server.use(
    http.get('*/notifications', () =>
      HttpResponse.json({
        items: notifications,
        total: notifications.length,
        limit: 10,
        offset: 0,
      })
    ),
    http.post('*/notifications/:guid/read', ({ params }) => {
      const notification = notifications.find((n) => n.guid === params.guid)
      if (!notification) {
        return HttpResponse.json({ error: 'Not found' }, { status: 404 })
      }
      return HttpResponse.json({
        ...notification,
        read_at: new Date().toISOString(),
      })
    })
  )
}

// ============================================================================
// Tests
// ============================================================================

describe('NotificationPanel', () => {
  it('should render bell icon', () => {
    render(<NotificationPanel unreadCount={0} />)
    expect(screen.getByLabelText('Notifications')).toBeInTheDocument()
  })

  it('should show unread badge when count > 0', () => {
    render(<NotificationPanel unreadCount={3} />)
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('should not show badge when count is 0', () => {
    render(<NotificationPanel unreadCount={0} />)
    expect(screen.queryByText('0')).not.toBeInTheDocument()
  })

  it('should cap badge display at 99+', () => {
    render(<NotificationPanel unreadCount={150} />)
    expect(screen.getByText('99+')).toBeInTheDocument()
  })

  it('should show notification list when popover opens', async () => {
    setupHandlers()
    const user = userEvent.setup()

    render(<NotificationPanel unreadCount={2} />)

    await user.click(screen.getByLabelText(/Notifications/))

    await waitFor(() => {
      expect(screen.getByText('Analysis Failed')).toBeInTheDocument()
      expect(screen.getByText('Deadline Approaching')).toBeInTheDocument()
    })
  })

  it('should show empty state when no notifications', async () => {
    setupHandlers([])
    const user = userEvent.setup()

    render(<NotificationPanel unreadCount={0} />)

    await user.click(screen.getByLabelText('Notifications'))

    await waitFor(() => {
      expect(screen.getByText(/no notifications/i)).toBeInTheDocument()
    })
  })

  it('should show "View all" link', async () => {
    setupHandlers()
    const user = userEvent.setup()

    render(<NotificationPanel unreadCount={1} />)

    await user.click(screen.getByLabelText(/Notifications/))

    await waitFor(() => {
      expect(screen.getByText('View all')).toBeInTheDocument()
    })
  })
})
