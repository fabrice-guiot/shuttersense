/**
 * Tests for usePushSubscription hook
 *
 * Issue #114 - PWA with Push Notifications (US2)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { usePushSubscription } from '../usePushSubscription'
import * as notificationService from '@/services/notifications'
import type { PushSubscriptionResponse, SubscriptionStatusResponse, VapidKeyResponse } from '@/contracts/api/notification-api'

// Mock the service
vi.mock('@/services/notifications')

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

describe('usePushSubscription', () => {
  const mockSubscriptions: PushSubscriptionResponse[] = [
    {
      guid: 'psub_01hgw2bbg00000000000000001',
      endpoint: 'https://fcm.googleapis.com/fcm/send/abc123',
      device_name: 'Chrome on Mac',
      created_at: '2026-01-15T10:00:00Z',
      last_used_at: null,
    },
  ]

  const mockStatus: SubscriptionStatusResponse = {
    subscriptions: mockSubscriptions,
    notifications_enabled: true,
  }

  const mockVapidKey: VapidKeyResponse = {
    vapid_public_key: 'BKxO5lN3dqKd8I-test-key',
  }

  // Mock PushManager and service worker
  const mockPushSubscription = {
    endpoint: 'https://fcm.googleapis.com/fcm/send/xyz789',
    getKey: vi.fn((name: string) => {
      if (name === 'p256dh') return new Uint8Array([1, 2, 3])
      if (name === 'auth') return new Uint8Array([4, 5, 6])
      return null
    }),
    unsubscribe: vi.fn().mockResolvedValue(true),
  }

  const mockPushManager = {
    subscribe: vi.fn().mockResolvedValue(mockPushSubscription),
    getSubscription: vi.fn().mockResolvedValue(mockPushSubscription),
  }

  const mockRegistration = {
    pushManager: mockPushManager,
  }

  beforeEach(() => {
    vi.clearAllMocks()

    // Re-establish browser API mock implementations (reset by vi.restoreAllMocks)
    mockPushManager.getSubscription.mockResolvedValue(mockPushSubscription)
    mockPushManager.subscribe.mockResolvedValue(mockPushSubscription)
    mockPushSubscription.unsubscribe.mockResolvedValue(true)

    // Mock Notification API
    Object.defineProperty(window, 'Notification', {
      writable: true,
      configurable: true,
      value: {
        permission: 'default',
        requestPermission: vi.fn().mockResolvedValue('granted'),
      },
    })

    // Mock service worker
    Object.defineProperty(navigator, 'serviceWorker', {
      writable: true,
      configurable: true,
      value: {
        ready: Promise.resolve(mockRegistration),
      },
    })

    // Mock PushManager
    Object.defineProperty(window, 'PushManager', {
      writable: true,
      configurable: true,
      value: {},
    })

    // Mock navigator.userAgent
    Object.defineProperty(navigator, 'userAgent', {
      writable: true,
      configurable: true,
      value: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    })

    vi.mocked(notificationService.getStatus).mockResolvedValue(mockStatus)
    vi.mocked(notificationService.getVapidKey).mockResolvedValue(mockVapidKey)
    vi.mocked(notificationService.subscribe).mockResolvedValue(undefined)
    vi.mocked(notificationService.unsubscribe).mockResolvedValue(undefined)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('should fetch subscription status on mount', async () => {
    const { result } = renderHook(() => usePushSubscription())

    expect(result.current.loading).toBe(true)
    expect(result.current.subscriptions).toEqual([])

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.subscriptions).toHaveLength(1)
    expect(result.current.subscriptions[0].device_name).toBe('Chrome on Mac')
    expect(result.current.notificationsEnabled).toBe(true)
    expect(result.current.error).toBe(null)
  })

  it('should not fetch on mount when autoFetch is false', async () => {
    const { result } = renderHook(() => usePushSubscription(false))

    expect(result.current.loading).toBe(false)
    expect(result.current.subscriptions).toEqual([])
    expect(notificationService.getStatus).not.toHaveBeenCalled()
  })

  it('should detect browser support', async () => {
    const { result } = renderHook(() => usePushSubscription(false))

    expect(result.current.isSupported).toBe(true)
  })

  it('should detect lack of browser support', async () => {
    // @ts-ignore - intentionally delete for testing
    delete window.PushManager

    const { result } = renderHook(() => usePushSubscription(false))

    expect(result.current.isSupported).toBe(false)
  })

  it('should detect iOS not installed', async () => {
    Object.defineProperty(navigator, 'userAgent', {
      writable: true,
      configurable: true,
      value: 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X)',
    })

    // Mock window.matchMedia
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      configurable: true,
      value: vi.fn().mockReturnValue({
        matches: false, // Not in standalone mode
      }),
    })

    const { result } = renderHook(() => usePushSubscription(false))

    expect(result.current.isIosNotInstalled).toBe(true)
  })

  it('should subscribe to push notifications', async () => {
    const { result } = renderHook(() => usePushSubscription(false))

    await act(async () => {
      await result.current.subscribe()
    })

    expect(window.Notification.requestPermission).toHaveBeenCalled()
    expect(notificationService.getVapidKey).toHaveBeenCalled()
    expect(mockPushManager.subscribe).toHaveBeenCalled()
    expect(notificationService.subscribe).toHaveBeenCalledWith({
      endpoint: 'https://fcm.googleapis.com/fcm/send/xyz789',
      p256dh_key: expect.any(String),
      auth_key: expect.any(String),
      device_name: 'Browser on Mac',
    })
    expect(notificationService.getStatus).toHaveBeenCalled() // Refetch status
  })

  it('should handle permission denied during subscribe', async () => {
    Object.defineProperty(window.Notification, 'requestPermission', {
      value: vi.fn().mockResolvedValue('denied'),
    })

    const { result } = renderHook(() => usePushSubscription(false))

    await act(async () => {
      await result.current.subscribe()
    })

    expect(result.current.error).toBe('Notification permission was denied')
    expect(result.current.permissionState).toBe('denied')
  })

  it('should handle unsupported browser during subscribe', async () => {
    // @ts-ignore - intentionally delete for testing
    delete window.PushManager

    const { result } = renderHook(() => usePushSubscription(false))

    await act(async () => {
      await result.current.subscribe()
    })

    expect(result.current.isSupported).toBe(false)
    expect(notificationService.subscribe).not.toHaveBeenCalled()
  })

  it('should unsubscribe from push notifications', async () => {
    const { result } = renderHook(() => usePushSubscription(false))

    await act(async () => {
      await result.current.unsubscribe()
    })

    expect(mockPushSubscription.unsubscribe).toHaveBeenCalled()
    expect(notificationService.unsubscribe).toHaveBeenCalledWith({
      endpoint: 'https://fcm.googleapis.com/fcm/send/xyz789',
    })
    expect(notificationService.getStatus).toHaveBeenCalled() // Refetch status
  })

  it('should handle no active subscription during unsubscribe', async () => {
    mockPushManager.getSubscription.mockResolvedValue(null)

    const { result } = renderHook(() => usePushSubscription(false))

    await act(async () => {
      await result.current.unsubscribe()
    })

    expect(mockPushSubscription.unsubscribe).not.toHaveBeenCalled()
    expect(notificationService.unsubscribe).not.toHaveBeenCalled()
    expect(notificationService.getStatus).toHaveBeenCalled() // Still refetch status
  })

  it('should refresh subscription status', async () => {
    const { result } = renderHook(() => usePushSubscription(false))

    await act(async () => {
      await result.current.refreshStatus()
    })

    expect(notificationService.getStatus).toHaveBeenCalled()
    expect(result.current.subscriptions).toHaveLength(1)
    expect(result.current.notificationsEnabled).toBe(true)
  })

  it('should handle fetch error', async () => {
    const error = new Error('Network error')
    ;(error as any).userMessage = 'Failed to load subscription status'
    vi.mocked(notificationService.getStatus).mockRejectedValue(error)

    const { result } = renderHook(() => usePushSubscription())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Failed to load subscription status')
    expect(result.current.subscriptions).toEqual([])
  })

  it('should handle subscribe error', async () => {
    const error = new Error('Subscription failed')
    ;(error as any).userMessage = 'Failed to enable push notifications'
    vi.mocked(notificationService.subscribe).mockRejectedValue(error)

    const { result } = renderHook(() => usePushSubscription(false))

    await act(async () => {
      await result.current.subscribe()
    })

    expect(result.current.error).toBe('Failed to enable push notifications')
  })

  it('should handle unsubscribe error', async () => {
    vi.mocked(notificationService.unsubscribe).mockRejectedValue(
      Object.assign(new Error('Unsubscribe failed'), {
        userMessage: 'Failed to disable push notifications',
      })
    )

    const { result } = renderHook(() => usePushSubscription(false))

    await act(async () => {
      await result.current.unsubscribe()
    })

    expect(result.current.error).toBe('Failed to disable push notifications')
  })

  it('should detect device name from user agent', async () => {
    const deviceTests = [
      { ua: 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1 Mobile Safari/604.1', expected: 'Safari on iPhone' },
      { ua: 'Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X) AppleWebKit/605.1 Safari/604.1', expected: 'Safari on iPad' },
      { ua: 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/120.0 Mobile Safari/537.36', expected: 'Chrome on Android' },
      { ua: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36', expected: 'Chrome on Mac' },
      { ua: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0', expected: 'Firefox on Windows' },
      { ua: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36', expected: 'Chrome on Linux' },
    ]

    for (const test of deviceTests) {
      Object.defineProperty(navigator, 'userAgent', {
        writable: true,
        configurable: true,
        value: test.ua,
      })

      const { result } = renderHook(() => usePushSubscription(false))

      await act(async () => {
        await result.current.subscribe()
      })

      expect(notificationService.subscribe).toHaveBeenCalled()
      const subscribeCall = vi.mocked(notificationService.subscribe).mock.calls[0]
      expect(subscribeCall[0].device_name).toBe(test.expected)

      vi.clearAllMocks()
    }
  })

  it('should get permission state', async () => {
    const { result } = renderHook(() => usePushSubscription(false))

    expect(result.current.permissionState).toBe('default')
  })
})
