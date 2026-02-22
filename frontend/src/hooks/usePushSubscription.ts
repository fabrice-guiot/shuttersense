/**
 * usePushSubscription React hook
 *
 * Manages browser push notification subscription lifecycle:
 * - Request notification permission
 * - Subscribe/unsubscribe via PushManager + server API
 * - Track permission state and active subscriptions
 * - Detect iOS not-installed state
 *
 * Issue #114 - PWA with Push Notifications (US2)
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { toast } from 'sonner'
import * as notificationService from '@/services/notifications'
import type {
  PushSubscriptionResponse,
  SubscriptionStatusResponse,
} from '@/contracts/api/notification-api'

// ============================================================================
// Types
// ============================================================================

type PermissionState = 'default' | 'granted' | 'denied' | 'unsupported'

interface UsePushSubscriptionReturn {
  /** Active push subscriptions for the current user */
  subscriptions: PushSubscriptionResponse[]
  /** Whether the master notifications toggle is enabled on the server */
  notificationsEnabled: boolean
  /** Browser notification permission state */
  permissionState: PermissionState
  /** Whether the browser supports push notifications */
  isSupported: boolean
  /** Whether on iOS but not in standalone PWA mode */
  isIosNotInstalled: boolean
  /** Whether the current device has an active push subscription */
  isCurrentDeviceSubscribed: boolean
  /** Push endpoint of the current device, or null if not subscribed */
  currentDeviceEndpoint: string | null
  /** Loading state for any async operation */
  loading: boolean
  /** Error message from the last failed operation */
  error: string | null
  /** GUID of the device currently being tested (null if none) */
  testingGuid: string | null
  /** Subscribe this device for push notifications */
  subscribe: () => Promise<void>
  /** Unsubscribe this device from push notifications */
  unsubscribe: () => Promise<void>
  /** Remove a specific device subscription by GUID (e.g., lost devices) */
  removeDevice: (guid: string) => Promise<void>
  /** Send a test push to a specific device */
  testDevice: (guid: string) => Promise<boolean>
  /** Rename a device subscription */
  renameDevice: (guid: string, name: string) => Promise<void>
  /** Refresh subscription status from the server */
  refreshStatus: () => Promise<void>
}

// ============================================================================
// Helpers
// ============================================================================

function getPermissionState(): PermissionState {
  if (typeof window === 'undefined') return 'unsupported'
  if (!('Notification' in window)) return 'unsupported'
  return Notification.permission as PermissionState
}

function isIos(): boolean {
  if (typeof navigator === 'undefined') return false
  return /iphone|ipad|ipod/i.test(navigator.userAgent)
}

function isStandalone(): boolean {
  if (typeof window === 'undefined') return false
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    ('standalone' in navigator &&
      (navigator as Record<string, unknown>).standalone === true)
  )
}

/**
 * Convert a Base64url-encoded string to a Uint8Array for PushManager.subscribe()
 */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  const outputArray = new Uint8Array(rawData.length)
  for (let i = 0; i < rawData.length; i++) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}

/**
 * Detect the browser name from user agent data or UA string
 */
interface NavigatorUAData {
  brands?: { brand: string }[]
  platform?: string
}

function detectBrowserName(): string {
  // Prefer navigator.userAgentData (Chromium-based browsers)
  const uaData = (navigator as { userAgentData?: NavigatorUAData }).userAgentData
  if (uaData?.brands) {
    // Pick the first "real" brand (skip "Not A;Brand" / "Chromium" filler entries)
    const real = uaData.brands.find(
      (b) => !/not[^a-z]*a[^a-z]*brand/i.test(b.brand) && b.brand !== 'Chromium'
    )
    if (real) return real.brand
  }

  // Fallback: parse the UA string
  const ua = navigator.userAgent
  if (/Edg\//i.test(ua)) return 'Edge'
  if (/OPR\//i.test(ua) || /Opera/i.test(ua)) return 'Opera'
  if (/Firefox\//i.test(ua)) return 'Firefox'
  if (/CriOS/i.test(ua) || /Chrome\//i.test(ua)) return 'Chrome'
  if (/Safari\//i.test(ua)) return 'Safari'
  return 'Browser'
}

/**
 * Detect a friendly device name from the user agent in "{browser} on {platform}" format
 */
function detectDeviceName(): string {
  // Prefer navigator.userAgentData.platform when available
  const uaData = (navigator as { userAgentData?: NavigatorUAData }).userAgentData
  let platform: string | undefined
  if (uaData?.platform) {
    // Normalize common platform values
    const p = uaData.platform
    if (/macos/i.test(p)) platform = 'Mac'
    else if (/windows/i.test(p)) platform = 'Windows'
    else if (/android/i.test(p)) platform = 'Android'
    else if (/linux/i.test(p)) platform = 'Linux'
    else platform = p
  }

  // Fallback: parse the UA string
  if (!platform) {
    const ua = navigator.userAgent
    if (/iPhone/i.test(ua)) platform = 'iPhone'
    else if (/iPad/i.test(ua)) platform = 'iPad'
    else if (/Android/i.test(ua)) platform = 'Android'
    else if (/Macintosh/i.test(ua)) platform = 'Mac'
    else if (/Windows/i.test(ua)) platform = 'Windows'
    else if (/Linux/i.test(ua)) platform = 'Linux'
    else platform = 'Unknown'
  }

  const browser = detectBrowserName()
  return `${browser} on ${platform}`
}

// ============================================================================
// Hook
// ============================================================================

export const usePushSubscription = (
  autoFetch = true
): UsePushSubscriptionReturn => {
  const [subscriptions, setSubscriptions] = useState<
    PushSubscriptionResponse[]
  >([])
  const [notificationsEnabled, setNotificationsEnabled] = useState(false)
  const [currentDeviceEndpoint, setCurrentDeviceEndpoint] = useState<string | null>(null)
  const [permissionState, setPermissionState] = useState<PermissionState>(
    getPermissionState
  )
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [testingGuid, setTestingGuid] = useState<string | null>(null)

  const isSupported =
    typeof window !== 'undefined' &&
    'serviceWorker' in navigator &&
    'PushManager' in window

  const isIosNotInstalled = isIos() && !isStandalone()
  const isCurrentDeviceSubscribed = currentDeviceEndpoint !== null

  // Ref for subscriptions to avoid removeDevice callback recreation on every status refresh
  const subscriptionsRef = useRef(subscriptions)
  subscriptionsRef.current = subscriptions

  // Track if component is still mounted (must set true on mount for StrictMode remount)
  const mountedRef = useRef(true)
  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

  /**
   * Resolve the current device's push endpoint if it matches a server-side subscription.
   * Returns the endpoint string or null.
   */
  const resolveCurrentDeviceEndpoint = useCallback(
    async (serverSubscriptions: PushSubscriptionResponse[]): Promise<string | null> => {
      if (!isSupported) return null
      try {
        const registration = await navigator.serviceWorker.ready
        const pushSub = await registration.pushManager.getSubscription()
        if (!pushSub) return null
        const match = serverSubscriptions.some((s) => s.endpoint === pushSub.endpoint)
        return match ? pushSub.endpoint : null
      } catch {
        return null
      }
    },
    [isSupported]
  )

  /**
   * Fetch subscription status from the server
   */
  const refreshStatus = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const status: SubscriptionStatusResponse =
        await notificationService.getStatus()
      if (mountedRef.current) {
        setSubscriptions(status.subscriptions)
        setNotificationsEnabled(status.notifications_enabled)
        const endpoint = await resolveCurrentDeviceEndpoint(status.subscriptions)
        if (mountedRef.current) {
          setCurrentDeviceEndpoint(endpoint)
        }
      }
    } catch (err: unknown) {
      if (mountedRef.current) {
        const errorMessage =
          (err as { userMessage?: string }).userMessage ||
          'Failed to load subscription status'
        setError(errorMessage)
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [resolveCurrentDeviceEndpoint])

  /**
   * Subscribe this device for push notifications
   *
   * Flow: request permission → get VAPID key → PushManager.subscribe → POST to server
   */
  const subscribe = useCallback(async () => {
    if (!isSupported) {
      toast.error('Push notifications are not supported in this browser')
      return
    }

    setLoading(true)
    setError(null)
    try {
      // 1. Request browser notification permission
      const permission = await Notification.requestPermission()
      setPermissionState(permission as PermissionState)

      if (permission !== 'granted') {
        setError('Notification permission was denied')
        toast.error('Notification permission denied', {
          description:
            'You can re-enable notifications in your browser settings.',
        })
        return
      }

      // 2. Get VAPID public key from server
      const { vapid_public_key } = await notificationService.getVapidKey()

      // 3. Get the active service worker registration
      const registration = await navigator.serviceWorker.ready

      // 4. Subscribe via PushManager
      const applicationServerKey = urlBase64ToUint8Array(vapid_public_key)
      const pushSubscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: applicationServerKey.buffer as ArrayBuffer,
      })

      // 5. Extract keys and send to server
      const p256dh = pushSubscription.getKey('p256dh')
      const auth = pushSubscription.getKey('auth')

      if (!p256dh || !auth) {
        throw new Error('Push subscription keys not available')
      }

      // Convert ArrayBuffer to Base64url
      const p256dhKey = btoa(
        String.fromCharCode(...new Uint8Array(p256dh))
      )
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=+$/, '')
      const authKey = btoa(String.fromCharCode(...new Uint8Array(auth)))
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=+$/, '')

      await notificationService.subscribe({
        endpoint: pushSubscription.endpoint,
        p256dh_key: p256dhKey,
        auth_key: authKey,
        device_name: detectDeviceName(),
      })

      // 6. Refresh status to get updated subscription list
      await refreshStatus()
      toast.success('Push notifications enabled')
    } catch (err: unknown) {
      if (mountedRef.current) {
        const errorMessage =
          (err as { userMessage?: string }).userMessage ||
          (err as Error).message ||
          'Failed to enable push notifications'
        setError(errorMessage)
        toast.error('Failed to enable notifications', {
          description: errorMessage,
        })
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [isSupported, refreshStatus])

  /**
   * Remove a specific device subscription by GUID.
   *
   * If the target device is the current browser, also unsubscribes the
   * PushManager so the browser stops receiving pushes immediately.
   */
  const removeDevice = useCallback(
    async (guid: string) => {
      setLoading(true)
      setError(null)
      try {
        // If removing the current device, unsubscribe PushManager first
        const target = subscriptionsRef.current.find((s) => s.guid === guid)
        if (target && currentDeviceEndpoint && target.endpoint === currentDeviceEndpoint) {
          try {
            const registration = await navigator.serviceWorker.ready
            const pushSub = await registration.pushManager.getSubscription()
            if (pushSub) {
              await pushSub.unsubscribe()
            }
          } catch {
            // PushManager failure is non-fatal — server removal still proceeds
          }
        }

        await notificationService.unsubscribeByGuid(guid)
        await refreshStatus()
        toast.success('Device removed')
      } catch (err: unknown) {
        if (mountedRef.current) {
          const errorMessage =
            (err as { userMessage?: string }).userMessage ||
            (err as Error).message ||
            'Failed to remove device'
          setError(errorMessage)
          toast.error('Failed to remove device', {
            description: errorMessage,
          })
        }
      } finally {
        if (mountedRef.current) {
          setLoading(false)
        }
      }
    },
    [currentDeviceEndpoint, refreshStatus]
  )

  /**
   * Send a test push notification to a specific device
   */
  const testDevice = useCallback(
    async (guid: string): Promise<boolean> => {
      setTestingGuid(guid)
      setError(null)
      try {
        const result = await notificationService.testDevice(guid)
        if (result.success) {
          toast.success('Simulated notification sent')
        } else {
          toast.error('Simulated notification failed', {
            description: result.error || 'Push delivery failed',
          })
        }
        return result.success
      } catch (err: unknown) {
        if (mountedRef.current) {
          const errorMessage =
            (err as { userMessage?: string }).userMessage ||
            (err as Error).message ||
            'Failed to send simulated notification'
          setError(errorMessage)
          toast.error('Simulated notification failed', {
            description: errorMessage,
          })
        }
        return false
      } finally {
        if (mountedRef.current) {
          setTestingGuid(null)
        }
      }
    },
    []
  )

  /**
   * Rename a device subscription
   */
  const renameDevice = useCallback(
    async (guid: string, name: string) => {
      setLoading(true)
      setError(null)
      try {
        await notificationService.renameDevice(guid, name)
        await refreshStatus()
        toast.success('Device renamed')
      } catch (err: unknown) {
        if (mountedRef.current) {
          const errorMessage =
            (err as { userMessage?: string }).userMessage ||
            (err as Error).message ||
            'Failed to rename device'
          setError(errorMessage)
          toast.error('Failed to rename device', {
            description: errorMessage,
          })
        }
      } finally {
        if (mountedRef.current) {
          setLoading(false)
        }
      }
    },
    [refreshStatus]
  )

  /**
   * Unsubscribe this device from push notifications
   *
   * Flow: PushManager.unsubscribe → DELETE on server
   */
  const unsubscribe = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      // 1. Unsubscribe from PushManager
      const registration = await navigator.serviceWorker.ready
      const pushSubscription =
        await registration.pushManager.getSubscription()

      if (pushSubscription) {
        const endpoint = pushSubscription.endpoint
        await pushSubscription.unsubscribe()

        // 2. Remove from server
        await notificationService.unsubscribe({ endpoint })
      }

      // 3. Refresh status
      await refreshStatus()
      toast.success('Push notifications disabled for this device')
    } catch (err: unknown) {
      if (mountedRef.current) {
        const errorMessage =
          (err as { userMessage?: string }).userMessage ||
          (err as Error).message ||
          'Failed to disable push notifications'
        setError(errorMessage)
        toast.error('Failed to disable notifications', {
          description: errorMessage,
        })
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [refreshStatus])

  // Auto-fetch status on mount
  useEffect(() => {
    if (autoFetch) {
      refreshStatus()
    }
  }, [autoFetch, refreshStatus])

  // Sync permission state on focus (user may change in browser settings)
  useEffect(() => {
    const handleFocus = () => {
      setPermissionState(getPermissionState())
    }
    window.addEventListener('focus', handleFocus)
    return () => window.removeEventListener('focus', handleFocus)
  }, [])

  // Real-time permission revocation detection via Permissions API (T046)
  useEffect(() => {
    if (!isSupported) return
    if (!navigator.permissions?.query) return

    let permissionStatus: PermissionStatus | null = null

    navigator.permissions
      .query({ name: 'notifications' as PermissionName })
      .then((status) => {
        permissionStatus = status
        // Sync initial state from Permissions API
        setPermissionState(status.state === 'prompt' ? 'default' : (status.state as PermissionState))

        status.onchange = () => {
          const newState = status.state === 'prompt' ? 'default' : (status.state as PermissionState)
          setPermissionState(newState)

          // If permission was revoked while notifications are active, refresh server status
          if (newState === 'denied') {
            refreshStatus()
          }
        }
      })
      .catch(() => {
        // Permissions API not available for notifications in this browser — fall back to focus listener
      })

    return () => {
      if (permissionStatus) {
        permissionStatus.onchange = null
      }
    }
  }, [isSupported, refreshStatus])

  return {
    subscriptions,
    notificationsEnabled,
    permissionState,
    isSupported,
    isIosNotInstalled,
    isCurrentDeviceSubscribed,
    currentDeviceEndpoint,
    loading,
    error,
    testingGuid,
    subscribe,
    unsubscribe,
    removeDevice,
    testDevice,
    renameDevice,
    refreshStatus,
  }
}
