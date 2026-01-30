/**
 * Notification Panel Component
 *
 * Popover panel triggered by the bell icon in TopHeader.
 * Shows recent notifications (capped at 10) with category icon, title, body,
 * relative timestamp, and read/unread indicator.
 * Clicking a notification opens a detail dialog with the full content.
 * "View all" link navigates to the full /notifications page.
 *
 * Issue #114 - PWA with Push Notifications (US9)
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, BellOff } from 'lucide-react'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { formatRelativeTime } from '@/utils/dateFormat'
import { useNotifications } from '@/hooks/useNotifications'
import { NotificationDetailDialog } from '@/components/notifications/NotificationDetailDialog'
import type { NotificationResponse } from '@/contracts/api/notification-api'
import {
  NOTIFICATION_CATEGORY_ICONS,
  NOTIFICATION_CATEGORY_LABELS,
} from '@/contracts/domain-labels'

// ============================================================================
// Sub-components
// ============================================================================

function NotificationItem({
  notification,
  onClick,
}: {
  notification: NotificationResponse
  onClick: (notification: NotificationResponse) => void
}) {
  const isUnread = notification.read_at === null
  const Icon = NOTIFICATION_CATEGORY_ICONS[notification.category]
  const categoryLabel = NOTIFICATION_CATEGORY_LABELS[notification.category]

  return (
    <button
      onClick={() => onClick(notification)}
      className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-accent transition-colors border-b border-border last:border-0"
    >
      {/* Category icon */}
      <div className="mt-0.5 shrink-0">
        {Icon ? (
          <Icon className="h-4 w-4 text-muted-foreground" />
        ) : (
          <Bell className="h-4 w-4 text-muted-foreground" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 space-y-0.5">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium truncate">{notification.title}</p>
          {isUnread && (
            <span className="h-2 w-2 shrink-0 rounded-full bg-primary" />
          )}
        </div>
        <p className="text-xs text-muted-foreground line-clamp-2">
          {notification.body}
        </p>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>{categoryLabel}</span>
          <span>&middot;</span>
          <span>{formatRelativeTime(notification.created_at)}</span>
        </div>
      </div>
    </button>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      <BellOff className="h-8 w-8 text-muted-foreground/50 mb-2" />
      <p className="text-sm font-medium text-muted-foreground">
        No notifications
      </p>
      <p className="text-xs text-muted-foreground">
        You&apos;re all caught up
      </p>
    </div>
  )
}

// ============================================================================
// Main Component
// ============================================================================

interface NotificationPanelProps {
  /** Unread count for the badge */
  unreadCount: number
}

export function NotificationPanel({ unreadCount }: NotificationPanelProps) {
  const navigate = useNavigate()
  const {
    notifications,
    loading,
    fetchNotifications,
    markAsRead,
  } = useNotifications(false) // Don't auto-fetch — fetch on open

  const [selected, setSelected] = useState<NotificationResponse | null>(null)
  const [popoverOpen, setPopoverOpen] = useState(false)

  /**
   * Fetch notifications when popover opens (capped at 10)
   */
  const handlePopoverChange = (open: boolean) => {
    setPopoverOpen(open)
    if (open) {
      fetchNotifications({ limit: 10 })
    }
  }

  /**
   * Handle notification click: mark as read and open detail dialog
   */
  const handleItemClick = async (notification: NotificationResponse) => {
    if (notification.read_at === null) {
      await markAsRead(notification.guid)
    }
    setSelected(notification)
    setPopoverOpen(false)
  }

  /**
   * Navigate to the full notifications page
   */
  const handleViewAll = () => {
    setPopoverOpen(false)
    navigate('/notifications')
  }

  return (
    <>
      <Popover open={popoverOpen} onOpenChange={handlePopoverChange}>
        <PopoverTrigger asChild>
          <button
            className="relative rounded-md p-2 hover:bg-accent transition-colors"
            aria-label={
              unreadCount > 0
                ? `Notifications (${unreadCount} unread)`
                : 'Notifications'
            }
          >
            <Bell className="h-5 w-5 text-foreground" />
            {unreadCount > 0 && (
              <Badge
                className="absolute -right-1 -top-1 h-5 min-w-5 rounded-full px-1 text-xs flex items-center justify-center"
                variant="destructive"
              >
                {unreadCount > 99 ? '99+' : unreadCount}
              </Badge>
            )}
          </button>
        </PopoverTrigger>

        <PopoverContent
          align="end"
          className="w-80 p-0 sm:w-96"
          sideOffset={8}
        >
          {/* Header with View all link */}
          <div className="flex items-center justify-between border-b px-4 py-3">
            <h3 className="text-sm font-semibold">Notifications</h3>
            <button
              onClick={handleViewAll}
              className="text-xs text-primary hover:underline"
            >
              View all
            </button>
          </div>

          {/* Notification list */}
          <ScrollArea className="max-h-[400px]">
            {loading && notifications.length === 0 ? (
              <div className="flex items-center justify-center py-8">
                <p className="text-sm text-muted-foreground">Loading...</p>
              </div>
            ) : notifications.length === 0 ? (
              <EmptyState />
            ) : (
              notifications.map((notification) => (
                <NotificationItem
                  key={notification.guid}
                  notification={notification}
                  onClick={handleItemClick}
                />
              ))
            )}
          </ScrollArea>
        </PopoverContent>
      </Popover>

      {/* Notification detail dialog */}
      <NotificationDetailDialog
        notification={selected}
        onClose={() => setSelected(null)}
      />
    </>
  )
}
