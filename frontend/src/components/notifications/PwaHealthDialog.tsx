/**
 * PwaHealthDialog component
 *
 * Dialog wrapper for the PWA Health Diagnostics panel.
 * Opened from the Notifications page via the "PWA Health" button.
 *
 * Issue #025 - PWA Health Diagnostics
 */

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { PwaHealthPanel } from './PwaHealthPanel'
import type { PushSubscriptionResponse } from '@/contracts/api/notification-api'

interface PwaHealthDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  currentDeviceEndpoint: string | null
  subscriptions: PushSubscriptionResponse[]
  testDevice: (guid: string) => Promise<boolean>
  testingGuid: string | null
}

export function PwaHealthDialog({
  open,
  onOpenChange,
  currentDeviceEndpoint,
  subscriptions,
  testDevice,
  testingGuid,
}: PwaHealthDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>PWA Health Diagnostics</DialogTitle>
        </DialogHeader>
        <PwaHealthPanel
          currentDeviceEndpoint={currentDeviceEndpoint}
          subscriptions={subscriptions}
          testDevice={testDevice}
          testingGuid={testingGuid}
        />
      </DialogContent>
    </Dialog>
  )
}
