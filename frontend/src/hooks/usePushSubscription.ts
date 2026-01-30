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
  /** Loading state for any async operation */
  loading: boolean
  /** Error message from the last failed operation */
  error: string | null
  /** Subscribe this device for push notifications */
  subscribe: () => Promise<void>
  /** Unsubscribe this device from push notifications */
  unsubscribe: () => Promise<void>
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
 * Detect a friendly device name from the user agent
 */
function detectDeviceName(): string {
  const ua = navigator.userAgent
  if (/iPhone/i.test(ua)) return 'iPhone'
  if (/iPad/i.test(ua)) return 'iPad'
  if (/Android/i.test(ua)) return 'Android'
  if (/Macintosh/i.test(ua)) return 'Mac'
  if (/Windows/i.test(ua)) return 'Windows'
  if (/Linux/i.test(ua)) return 'Linux'
  return 'Browser'
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
  const [permissionState, setPermissionState] = useState<PermissionState>(
    getPermissionState
  )
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isSupported =
    typeof window !== 'undefined' &&
    'serviceWorker' in navigator &&
    'PushManager' in window

  const isIosNotInstalled = isIos() && !isStandalone()

  // Track if component is still mounted (must set true on mount for StrictMode remount)
  const mountedRef = useRef(true)
  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
    }
  }, [])

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
  }, [])

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

  return {
    subscriptions,
    notificationsEnabled,
    permissionState,
    isSupported,
    isIosNotInstalled,
    loading,
    error,
    subscribe,
    unsubscribe,
    refreshStatus,
  }
}
