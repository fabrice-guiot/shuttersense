/**
 * Notification Panel Component
 *
 * Popover panel triggered by the bell icon in TopHeader.
 * Shows recent notifications with category icon, title, body,
 * relative timestamp, and read/unread indicator.
 * Clicking a notification opens a detail dialog with the full content.
 *
 * Issue #114 - PWA with Push Notifications (US9)
 */

import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { ArrowRight, Bell, BellOff } from 'lucide-react'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { formatRelativeTime } from '@/utils/dateFormat'
import { useNotifications } from '@/hooks/useNotifications'
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
   * Fetch notifications when popover opens
   */
  const handlePopoverChange = (open: boolean) => {
    setPopoverOpen(open)
    if (open) {
      fetchNotifications({ limit: 20 })
    }
  }

  const location = useLocation()

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
   * Navigate to the notification's URL from the detail dialog
   */
  const handleNavigate = () => {
    if (selected?.data?.url) {
      navigate(selected.data.url)
    }
    setSelected(null)
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
          {/* Header */}
          <div className="flex items-center justify-between border-b px-4 py-3">
            <h3 className="text-sm font-semibold">Notifications</h3>
            {unreadCount > 0 && (
              <span className="text-xs text-muted-foreground">
                {unreadCount} unread
              </span>
            )}
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
      <Dialog open={selected !== null} onOpenChange={(open) => { if (!open) setSelected(null) }}>
        <DialogContent className="sm:max-w-md">
          {selected && (() => {
            const Icon = NOTIFICATION_CATEGORY_ICONS[selected.category]
            const categoryLabel = NOTIFICATION_CATEGORY_LABELS[selected.category]
            return (
              <>
                <DialogHeader>
                  <div className="flex items-center gap-2">
                    {Icon && <Icon className="h-5 w-5 text-muted-foreground" />}
                    <DialogTitle>{selected.title}</DialogTitle>
                  </div>
                  <DialogDescription className="flex items-center gap-2">
                    <span>{categoryLabel}</span>
                    <span>&middot;</span>
                    <span>{formatRelativeTime(selected.created_at)}</span>
                  </DialogDescription>
                </DialogHeader>
                <div className="text-sm text-foreground whitespace-pre-wrap">
                  {selected.body}
                </div>
                {selected.data?.url && selected.data.url !== location.pathname && (
                  <DialogFooter>
                    <Button onClick={handleNavigate} size="sm">
                      <ArrowRight className="mr-1.5 h-4 w-4" />
                      Take action
                    </Button>
                  </DialogFooter>
                )}
              </>
            )
          })()}
        </DialogContent>
      </Dialog>
    </>
  )
}
