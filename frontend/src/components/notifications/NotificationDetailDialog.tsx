/**
 * Notification Detail Dialog Component
 *
 * Reusable dialog for displaying full notification content.
 * Used by both NotificationPanel (popover) and NotificationsPage (full page).
 *
 * Issue #114 - PWA with Push Notifications
 */

import { useNavigate, useLocation } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { formatRelativeTime } from '@/utils/dateFormat'
import { AuditTrailSection } from '@/components/audit'
import type { NotificationResponse } from '@/contracts/api/notification-api'
import {
  NOTIFICATION_CATEGORY_ICONS,
  NOTIFICATION_CATEGORY_LABELS,
} from '@/contracts/domain-labels'

interface NotificationDetailDialogProps {
  notification: NotificationResponse | null
  onClose: () => void
}

export function NotificationDetailDialog({
  notification,
  onClose,
}: NotificationDetailDialogProps) {
  const navigate = useNavigate()
  const location = useLocation()

  const handleNavigate = () => {
    if (notification?.data?.url) {
      navigate(notification.data.url)
    }
    onClose()
  }

  if (!notification) return null

  const Icon = NOTIFICATION_CATEGORY_ICONS[notification.category]
  const categoryLabel = NOTIFICATION_CATEGORY_LABELS[notification.category]

  return (
    <Dialog open={notification !== null} onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            {Icon && <Icon className="h-5 w-5 text-muted-foreground" />}
            <DialogTitle>{notification.title}</DialogTitle>
          </div>
          <DialogDescription className="flex items-center gap-2">
            <span>{categoryLabel}</span>
            <span>&middot;</span>
            <span>{formatRelativeTime(notification.created_at)}</span>
          </DialogDescription>
        </DialogHeader>
        <div className="text-sm text-foreground whitespace-pre-wrap">
          {notification.body}
        </div>
        <AuditTrailSection audit={notification.audit} />
        {notification.data?.url && notification.data.url !== location.pathname && (
          <DialogFooter>
            <Button onClick={handleNavigate} size="sm">
              <ArrowRight className="mr-1.5 h-4 w-4" />
              Take action
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  )
}
