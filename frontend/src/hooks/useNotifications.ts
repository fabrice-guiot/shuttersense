/**
 * useNotifications React hook
 *
 * Manages notification history state:
 * - Fetch paginated notification list (GET /notifications)
 * - Fetch and auto-refresh unread count (GET /unread-count) every 30s
 * - Mark individual notifications as read (POST /{guid}/read)
 * - Loading and error states
 *
 * Issue #114 - PWA with Push Notifications (US9)
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import * as notificationService from '@/services/notifications'
import type {
  NotificationResponse,
  NotificationListParams,
} from '@/contracts/api/notification-api'

// ============================================================================
// Types
// ============================================================================

const UNREAD_POLL_INTERVAL = 30_000 // 30 seconds

interface UseNotificationsReturn {
  /** Notification list (most recent first) */
  notifications: NotificationResponse[]
  /** Total notifications matching current filters */
  total: number
  /** Unread notification count (for badge) */
  unreadCount: number
  /** Loading state for list operations */
  loading: boolean
  /** Error message from the last failed operation */
  error: string | null
  /** Fetch notification list with optional filters */
  fetchNotifications: (params?: NotificationListParams) => Promise<void>
  /** Refresh unread count from the server */
  refreshUnreadCount: () => Promise<void>
  /** Mark a notification as read and update local state */
  markAsRead: (guid: string) => Promise<void>
}

// ============================================================================
// Hook
// ============================================================================

export const useNotifications = (
  autoFetch = true
): UseNotificationsReturn => {
  const [notifications, setNotifications] = useState<NotificationResponse[]>(
    []
  )
  const [total, setTotal] = useState(0)
  const [unreadCount, setUnreadCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const mountedRef = useRef(true)
  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  /**
   * Fetch notification list with optional filtering/pagination
   */
  const fetchNotifications = useCallback(
    async (params: NotificationListParams = {}) => {
      setLoading(true)
      setError(null)
      try {
        const data = await notificationService.listNotifications(params)
        if (mountedRef.current) {
          setNotifications(data.items)
          setTotal(data.total)
        }
      } catch (err: unknown) {
        if (mountedRef.current) {
          const errorMessage =
            (err as { userMessage?: string }).userMessage ||
            'Failed to load notifications'
          setError(errorMessage)
        }
      } finally {
        if (mountedRef.current) {
          setLoading(false)
        }
      }
    },
    []
  )

  /**
   * Fetch unread count (lightweight — used for badge polling)
   */
  const refreshUnreadCount = useCallback(async () => {
    try {
      const data = await notificationService.getUnreadCount()
      if (mountedRef.current) {
        setUnreadCount(data.unread_count)
      }
    } catch {
      // Silently fail for background poll — don't disrupt UI
    }
  }, [])

  /**
   * Mark a notification as read and update local state
   */
  const markAsRead = useCallback(
    async (guid: string) => {
      try {
        const updated = await notificationService.markAsRead(guid)
        if (mountedRef.current) {
          // Update the notification in the list
          setNotifications((prev) =>
            prev.map((n) => (n.guid === guid ? updated : n))
          )
          // Decrement unread count if it was previously unread
          setUnreadCount((prev) => Math.max(0, prev - 1))
        }
      } catch (err: unknown) {
        if (mountedRef.current) {
          const errorMessage =
            (err as { userMessage?: string }).userMessage ||
            'Failed to mark notification as read'
          setError(errorMessage)
        }
      }
    },
    []
  )

  // Auto-fetch on mount
  useEffect(() => {
    if (autoFetch) {
      refreshUnreadCount()
    }
  }, [autoFetch, refreshUnreadCount])

  // Poll unread count every 30 seconds
  useEffect(() => {
    if (!autoFetch) return

    const interval = setInterval(refreshUnreadCount, UNREAD_POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [autoFetch, refreshUnreadCount])

  return {
    notifications,
    total,
    unreadCount,
    loading,
    error,
    fetchNotifications,
    refreshUnreadCount,
    markAsRead,
  }
}
