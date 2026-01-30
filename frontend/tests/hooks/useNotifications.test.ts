/**
 * Tests for useNotifications hook.
 *
 * Issue #114 - PWA with Push Notifications (Phase 13 — T053)
 * Tests notification list fetch, unread count, mark-as-read,
 * auto-refresh interval, and loading/error states.
 */

import { renderHook, waitFor, act } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../mocks/server'
import { useNotifications } from '@/hooks/useNotifications'

// ============================================================================
// Test Data
// ============================================================================

const mockNotification = {
  guid: 'ntf_01hgw2bbg0000000000000001',
  category: 'job_failure' as const,
  title: 'Analysis Failed',
  body: 'PhotoStats analysis failed',
  data: { url: '/tools', job_guid: 'job_01hgw2bbg0000000000000001' },
  read_at: null,
  created_at: '2026-01-20T10:00:00Z',
}

const mockReadNotification = {
  ...mockNotification,
  guid: 'ntf_01hgw2bbg0000000000000002',
  read_at: '2026-01-20T11:00:00Z',
}

// ============================================================================
// Test: Fetch notification list
// ============================================================================

describe('useNotifications', () => {
  describe('fetchNotifications', () => {
    it('should fetch notification list', async () => {
      server.use(
        http.get('*/notifications', () =>
          HttpResponse.json({
            items: [mockNotification],
            total: 1,
            limit: 20,
            offset: 0,
          })
        )
      )

      const { result } = renderHook(() => useNotifications(false))

      await act(async () => {
        await result.current.fetchNotifications()
      })

      await waitFor(() => {
        expect(result.current.notifications).toHaveLength(1)
        expect(result.current.total).toBe(1)
        expect(result.current.notifications[0].guid).toBe(mockNotification.guid)
      })
    })

    it('should set error on fetch failure', async () => {
      server.use(
        http.get('*/notifications', () =>
          HttpResponse.json({ error: 'Server error' }, { status: 500 })
        )
      )

      const { result } = renderHook(() => useNotifications(false))

      await act(async () => {
        await result.current.fetchNotifications()
      })

      await waitFor(() => {
        expect(result.current.error).toBeTruthy()
      })
    })

    it('should set loading state during fetch', async () => {
      server.use(
        http.get('*/notifications', async () => {
          await new Promise((r) => setTimeout(r, 50))
          return HttpResponse.json({
            items: [],
            total: 0,
            limit: 20,
            offset: 0,
          })
        })
      )

      const { result } = renderHook(() => useNotifications(false))

      act(() => {
        result.current.fetchNotifications()
      })

      // Should be loading
      expect(result.current.loading).toBe(true)

      await waitFor(() => {
        expect(result.current.loading).toBe(false)
      })
    })
  })

  // ============================================================================
  // Test: Unread count
  // ============================================================================

  describe('refreshUnreadCount', () => {
    it('should fetch unread count', async () => {
      server.use(
        http.get('*/notifications/unread-count', () =>
          HttpResponse.json({ unread_count: 5 })
        )
      )

      const { result } = renderHook(() => useNotifications(false))

      await act(async () => {
        await result.current.refreshUnreadCount()
      })

      await waitFor(() => {
        expect(result.current.unreadCount).toBe(5)
      })
    })

    it('should auto-fetch unread count on mount when autoFetch=true', async () => {
      server.use(
        http.get('*/notifications/unread-count', () =>
          HttpResponse.json({ unread_count: 3 })
        )
      )

      const { result } = renderHook(() => useNotifications(true))

      await waitFor(() => {
        expect(result.current.unreadCount).toBe(3)
      })
    })
  })

  // ============================================================================
  // Test: Mark as read
  // ============================================================================

  describe('markAsRead', () => {
    it('should mark notification as read and update state', async () => {
      const updatedNotification = {
        ...mockNotification,
        read_at: '2026-01-20T12:00:00Z',
      }

      server.use(
        http.get('*/notifications', () =>
          HttpResponse.json({
            items: [mockNotification],
            total: 1,
            limit: 20,
            offset: 0,
          })
        ),
        http.get('*/notifications/unread-count', () =>
          HttpResponse.json({ unread_count: 1 })
        ),
        http.post('*/notifications/:guid/read', () =>
          HttpResponse.json(updatedNotification)
        )
      )

      const { result } = renderHook(() => useNotifications(false))

      // First fetch the list
      await act(async () => {
        await result.current.fetchNotifications()
        await result.current.refreshUnreadCount()
      })

      await waitFor(() => {
        expect(result.current.notifications).toHaveLength(1)
        expect(result.current.unreadCount).toBe(1)
      })

      // Mark as read
      await act(async () => {
        await result.current.markAsRead(mockNotification.guid)
      })

      await waitFor(() => {
        // Notification should be updated in the list
        expect(result.current.notifications[0].read_at).toBeTruthy()
        // Unread count should be decremented
        expect(result.current.unreadCount).toBe(0)
      })
    })

    it('should set error on mark-as-read failure', async () => {
      server.use(
        http.post('*/notifications/:guid/read', () =>
          HttpResponse.json({ error: 'Not found' }, { status: 404 })
        )
      )

      const { result } = renderHook(() => useNotifications(false))

      await act(async () => {
        await result.current.markAsRead('ntf_nonexistent')
      })

      await waitFor(() => {
        expect(result.current.error).toBeTruthy()
      })
    })
  })
})
