/**
 * Notification Preferences Component
 *
 * Renders notification settings on the Profile page:
 * - Master enable/disable toggle (triggers push subscription flow)
 * - Per-category toggles for each notification type
 * - Deadline days-before selector
 * - Timezone selector (auto-detected, user-overridable)
 * - Device list showing active push subscriptions
 *
 * Issue #114 - PWA with Push Notifications (US2)
 */

import { useCallback } from 'react'
import { Bell, BellOff, Info, Monitor, Smartphone } from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { TimezoneCombobox } from '@/components/ui/timezone-combobox'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { formatDate, formatRelativeTime } from '@/utils/dateFormat'
import { usePushSubscription } from '@/hooks/usePushSubscription'
import { useNotificationPreferences } from '@/hooks/useNotificationPreferences'
import type { NotificationCategory } from '@/contracts/domain-labels'
import {
  NOTIFICATION_CATEGORY_LABELS,
  NOTIFICATION_CATEGORY_DESCRIPTIONS,
  NOTIFICATION_CATEGORY_ICONS,
} from '@/contracts/domain-labels'
import type { NotificationPreferencesUpdateRequest } from '@/contracts/api/notification-api'

// ============================================================================
// Constants
// ============================================================================

/** Category toggle keys that map to preference fields */
const CATEGORY_TOGGLES: {
  key: NotificationCategory
  prefKey: keyof NotificationPreferencesUpdateRequest
}[] = [
  { key: 'job_failure', prefKey: 'job_failures' },
  { key: 'inflection_point', prefKey: 'inflection_points' },
  { key: 'agent_status', prefKey: 'agent_status' },
  { key: 'deadline', prefKey: 'deadline' },
  { key: 'retry_warning', prefKey: 'retry_warning' },
]

const DEADLINE_DAYS_OPTIONS = [1, 2, 3, 5, 7, 14, 30]

// ============================================================================
// Sub-components
// ============================================================================

function PermissionDeniedAlert() {
  return (
    <Alert className="border-amber-500/30 bg-amber-500/10">
      <Info className="h-4 w-4 text-amber-500" />
      <AlertDescription className="text-foreground">
        <p className="font-medium">Notifications blocked</p>
        <p className="text-sm text-muted-foreground">
          Your browser has blocked notifications for this site. To re-enable,
          click the lock icon in your browser&apos;s address bar, find
          &quot;Notifications&quot;, and change it to &quot;Allow&quot;.
        </p>
      </AlertDescription>
    </Alert>
  )
}

function IosNotInstalledAlert() {
  return (
    <Alert className="border-blue-500/30 bg-blue-500/10">
      <Info className="h-4 w-4 text-blue-500" />
      <AlertDescription className="text-foreground">
        <p className="font-medium">Install app for notifications</p>
        <p className="text-sm text-muted-foreground">
          Push notifications on iOS require the app to be installed. Tap the
          Share button, then &quot;Add to Home Screen&quot; to install
          ShutterSense.
        </p>
      </AlertDescription>
    </Alert>
  )
}

function UnsupportedBrowserAlert() {
  return (
    <Alert className="border-muted-foreground/30 bg-muted/50">
      <Info className="h-4 w-4 text-muted-foreground" />
      <AlertDescription className="text-foreground">
        <p className="font-medium">Push notifications not supported</p>
        <p className="text-sm text-muted-foreground">
          Your browser does not support push notifications. Try using Chrome,
          Edge, Firefox, or Safari 16.4+.
        </p>
      </AlertDescription>
    </Alert>
  )
}

// ============================================================================
// Main Component
// ============================================================================

export function NotificationPreferences() {
  const {
    subscriptions,
    permissionState,
    isSupported,
    isIosNotInstalled,
    loading: subscriptionLoading,
    subscribe,
    unsubscribe,
  } = usePushSubscription()

  const {
    preferences,
    loading: preferencesLoading,
    updatePreferences,
  } = useNotificationPreferences()

  const loading = subscriptionLoading || preferencesLoading
  const isEnabled = preferences?.enabled ?? false
  const hasActiveSubscription = subscriptions.length > 0

  /**
   * Handle master toggle: enable triggers push subscription, disable removes it
   */
  const handleMasterToggle = useCallback(
    async (checked: boolean) => {
      if (checked) {
        // Enable: subscribe this device + enable on server
        await subscribe()
        await updatePreferences({ enabled: true })
      } else {
        // Disable: unsubscribe device + disable on server
        await unsubscribe()
        await updatePreferences({ enabled: false })
      }
    },
    [subscribe, unsubscribe, updatePreferences]
  )

  /**
   * Handle per-category toggle
   */
  const handleCategoryToggle = useCallback(
    async (prefKey: keyof NotificationPreferencesUpdateRequest, checked: boolean) => {
      await updatePreferences({ [prefKey]: checked })
    },
    [updatePreferences]
  )

  /**
   * Handle deadline days-before change
   */
  const handleDeadlineDaysChange = useCallback(
    async (value: string) => {
      await updatePreferences({ deadline_days_before: parseInt(value, 10) })
    },
    [updatePreferences]
  )

  /**
   * Handle timezone change
   */
  const handleTimezoneChange = useCallback(
    async (value: string) => {
      await updatePreferences({ timezone: value })
    },
    [updatePreferences]
  )

  // Determine device icon
  const getDeviceIcon = (deviceName: string | null) => {
    if (!deviceName) return Monitor
    const name = deviceName.toLowerCase()
    if (
      name.includes('iphone') ||
      name.includes('ipad') ||
      name.includes('android')
    )
      return Smartphone
    return Monitor
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          {isEnabled ? (
            <Bell className="h-5 w-5 text-primary" />
          ) : (
            <BellOff className="h-5 w-5 text-muted-foreground" />
          )}
          <div className="flex-1">
            <CardTitle className="text-lg">Notifications</CardTitle>
            <CardDescription>
              Receive push notifications for important events
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Unsupported browser warning */}
        {!isSupported && <UnsupportedBrowserAlert />}

        {/* iOS not installed warning */}
        {isSupported && isIosNotInstalled && <IosNotInstalledAlert />}

        {/* Permission denied warning */}
        {isSupported && permissionState === 'denied' && (
          <PermissionDeniedAlert />
        )}

        {/* Master toggle */}
        {isSupported && !isIosNotInstalled && (
          <>
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="notifications-enabled" className="text-base">
                  Enable notifications
                </Label>
                <p className="text-sm text-muted-foreground">
                  {isEnabled && hasActiveSubscription
                    ? `Active on ${subscriptions.length} device${subscriptions.length !== 1 ? 's' : ''}`
                    : 'Receive push notifications on this device'}
                </p>
              </div>
              <Switch
                id="notifications-enabled"
                checked={isEnabled}
                onCheckedChange={handleMasterToggle}
                disabled={loading || permissionState === 'denied'}
              />
            </div>

            {/* Category toggles — only shown when enabled */}
            {isEnabled && preferences && (
              <>
                <div className="border-t pt-4 space-y-4">
                  <p className="text-sm font-medium text-muted-foreground">
                    Notification categories
                  </p>
                  {CATEGORY_TOGGLES.map(({ key, prefKey }) => {
                    const Icon = NOTIFICATION_CATEGORY_ICONS[key]
                    const label = NOTIFICATION_CATEGORY_LABELS[key]
                    const description =
                      NOTIFICATION_CATEGORY_DESCRIPTIONS[key]
                    const checked =
                      preferences[prefKey as keyof typeof preferences] as boolean

                    return (
                      <div
                        key={key}
                        className="flex items-start justify-between gap-4"
                      >
                        <div className="flex items-start gap-3">
                          <Icon className="mt-0.5 h-4 w-4 text-muted-foreground" />
                          <div className="space-y-0.5">
                            <Label
                              htmlFor={`notify-${key}`}
                              className="text-sm font-medium"
                            >
                              {label}
                            </Label>
                            <p className="text-xs text-muted-foreground">
                              {description}
                            </p>
                          </div>
                        </div>
                        <Switch
                          id={`notify-${key}`}
                          checked={checked}
                          onCheckedChange={(c) =>
                            handleCategoryToggle(prefKey, c)
                          }
                          disabled={loading}
                        />
                      </div>
                    )
                  })}
                </div>

                {/* Deadline settings — only when deadline category is on */}
                {preferences.deadline && (
                  <div className="border-t pt-4 space-y-4">
                    <p className="text-sm font-medium text-muted-foreground">
                      Deadline settings
                    </p>

                    {/* Days before */}
                    <div className="flex items-center justify-between gap-4">
                      <div className="space-y-0.5">
                        <Label htmlFor="deadline-days" className="text-sm">
                          Remind me
                        </Label>
                        <p className="text-xs text-muted-foreground">
                          Days before an event deadline
                        </p>
                      </div>
                      <Select
                        value={String(preferences.deadline_days_before)}
                        onValueChange={handleDeadlineDaysChange}
                        disabled={loading}
                      >
                        <SelectTrigger id="deadline-days" className="w-24">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {DEADLINE_DAYS_OPTIONS.map((d) => (
                            <SelectItem key={d} value={String(d)}>
                              {d} {d === 1 ? 'day' : 'days'}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Timezone */}
                    <div className="space-y-2">
                      <Label className="text-sm">Timezone</Label>
                      <p className="text-xs text-muted-foreground">
                        Used to calculate when deadlines are approaching
                      </p>
                      <TimezoneCombobox
                        value={preferences.timezone}
                        onChange={handleTimezoneChange}
                        disabled={loading}
                      />
                    </div>
                  </div>
                )}

                {/* Device list — when subscriptions exist */}
                {subscriptions.length > 0 && (
                  <div className="border-t pt-4 space-y-3">
                    <p className="text-sm font-medium text-muted-foreground">
                      Active devices
                    </p>
                    {subscriptions.map((sub) => {
                      const DeviceIcon = getDeviceIcon(sub.device_name)
                      return (
                        <div
                          key={sub.guid}
                          className="flex items-center gap-3 text-sm"
                        >
                          <DeviceIcon className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium">
                            {sub.device_name || 'Unknown device'}
                          </span>
                          <span className="text-muted-foreground">
                            {sub.last_used_at
                              ? `Last used ${formatRelativeTime(sub.last_used_at)}`
                              : `Added ${formatDate(sub.created_at)}`}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                )}
              </>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
