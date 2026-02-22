/**
 * PwaHealthPanel component
 *
 * Main panel for PWA Health Diagnostics. Renders all diagnostic
 * sections and action buttons for test notification, cache clear,
 * copy diagnostics, and re-run.
 *
 * Issue #025 - PWA Health Diagnostics
 */

import { useState } from 'react'
import {
  RefreshCw,
  Clipboard,
  Trash2,
  Send,
  Loader2,
} from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { DiagnosticSection } from './DiagnosticSection'
import { usePwaHealth } from '@/hooks/usePwaHealth'
import type { PushSubscriptionResponse } from '@/contracts/api/notification-api'

interface PwaHealthPanelProps {
  /** Current device's push endpoint for finding its subscription GUID */
  currentDeviceEndpoint: string | null
  /** All active push subscriptions (to find current device's GUID) */
  subscriptions: PushSubscriptionResponse[]
  /** Callback to send a test notification to a device */
  testDevice: (guid: string) => Promise<boolean>
  /** GUID of the device currently being tested */
  testingGuid: string | null
}

export function PwaHealthPanel({
  currentDeviceEndpoint,
  subscriptions,
  testDevice,
  testingGuid,
}: PwaHealthPanelProps) {
  const {
    result,
    running,
    checkingSection,
    runDiagnostics,
    copyDiagnostics,
    clearCacheAndReload,
  } = usePwaHealth()

  const [clearing, setClearing] = useState(false)

  // Find current device's subscription GUID
  const currentDeviceSub = currentDeviceEndpoint
    ? subscriptions.find((s) => s.endpoint === currentDeviceEndpoint)
    : null

  const handleCopy = async () => {
    const ok = await copyDiagnostics()
    if (ok) {
      toast.success('Diagnostics copied to clipboard')
    } else {
      toast.error('Failed to copy diagnostics')
    }
  }

  const handleTestNotification = async () => {
    if (!currentDeviceSub) {
      toast.error('No active subscription for this device')
      return
    }
    await testDevice(currentDeviceSub.guid)
  }

  const handleClearCache = async () => {
    setClearing(true)
    await clearCacheAndReload()
    // Page will reload, so no need to reset state
  }

  const isTesting = testingGuid === currentDeviceSub?.guid

  return (
    <div className="space-y-4">
      {/* Diagnostic Sections — rendered progressively */}
      <div className="space-y-1">
        {result?.sections.map((section) => (
          <DiagnosticSection key={section.id} section={section} />
        ))}

        {/* Active section spinner */}
        {checkingSection && (
          <div className="flex items-center gap-2 rounded-md px-3 py-2">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            <span className="text-sm text-muted-foreground">
              Checking...
            </span>
          </div>
        )}

        {/* Initial state before any result */}
        {running && !result && !checkingSection && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">
              Running diagnostics...
            </span>
          </div>
        )}
      </div>

      {/* Last checked timestamp */}
      {result && !running && (
        <p className="text-xs text-muted-foreground text-right">
          Last checked: {new Date(result.collectedAt).toLocaleTimeString()}
        </p>
      )}

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-2 border-t border-border pt-4">
        <Button
          variant="outline"
          size="sm"
          onClick={handleTestNotification}
          disabled={!currentDeviceSub || isTesting}
        >
          {isTesting ? (
            <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
          ) : (
            <Send className="mr-1.5 h-3.5 w-3.5" />
          )}
          Send Test
        </Button>

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="outline" size="sm" disabled={clearing}>
              {clearing ? (
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
              ) : (
                <Trash2 className="mr-1.5 h-3.5 w-3.5" />
              )}
              Clear Cache
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Clear cache and reload?</AlertDialogTitle>
              <AlertDialogDescription>
                This will delete all cached data, unregister the service worker,
                and reload the page. You may need to log in again and
                re-subscribe for push notifications.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleClearCache}>
                Clear & Reload
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        <Button variant="outline" size="sm" onClick={handleCopy} disabled={!result || running}>
          <Clipboard className="mr-1.5 h-3.5 w-3.5" />
          Copy Report
        </Button>

        <Button
          variant="outline"
          size="sm"
          onClick={runDiagnostics}
          disabled={running}
        >
          {running ? (
            <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
          ) : (
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
          )}
          Re-run
        </Button>
      </div>
    </div>
  )
}
