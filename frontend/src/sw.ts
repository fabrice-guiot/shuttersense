/**
 * Custom Service Worker for ShutterSense PWA
 *
 * Provides:
 * - Workbox precaching of build assets (injected by vite-plugin-pwa)
 * - Push notification display (from backend Web Push delivery)
 * - Notification click handling (focus/open app window with navigation URL)
 *
 * Issue #114 - PWA with Push Notifications
 */

/// <reference lib="webworker" />

import { cleanupOutdatedCaches, createHandlerBoundToURL, precacheAndRoute } from 'workbox-precaching'
import { NavigationRoute, registerRoute } from 'workbox-routing'
import { NetworkFirst } from 'workbox-strategies'
import { ExpirationPlugin } from 'workbox-expiration'

declare let self: ServiceWorkerGlobalScope
declare const __SW_VERSION__: string

// ============================================================================
// Immediate Activation (Silent Auto-Update)
// ============================================================================

// Skip the "waiting" phase — activate new SW immediately on install.
// Without this, a new SW version stays dormant until ALL tabs are closed.
self.addEventListener('install', () => {
  self.skipWaiting()
})

// Claim all open clients immediately on activation.
// Without this, existing tabs keep using the old SW until next navigation.
self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})

// Handle messages from the app
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting()
  }

  // PWA Health Diagnostics: report SW build version (Issue #025)
  if (event.data?.type === 'GET_VERSION') {
    event.ports[0]?.postMessage({
      type: 'SW_VERSION',
      version: typeof __SW_VERSION__ !== 'undefined' ? __SW_VERSION__ : 'unknown',
    })
  }
})

// ============================================================================
// Workbox Precaching
// ============================================================================

// Precache all build assets (manifest injected by vite-plugin-pwa)
precacheAndRoute(self.__WB_MANIFEST)

// Clean up old caches from previous service worker versions
cleanupOutdatedCaches()

// ============================================================================
// Navigation Fallback
// ============================================================================

// SPA navigation fallback — serve index.html for all navigation requests
// except /api/ routes (which should go to the backend).
// Uses createHandlerBoundToURL so the precached index.html is resolved
// regardless of cache versioning / revision hashes.
const navigationRoute = new NavigationRoute(
  createHandlerBoundToURL('/index.html'),
  {
    denylist: [/^\/api\//],
  }
)
registerRoute(navigationRoute)

// ============================================================================
// Runtime Caching for API
// ============================================================================

// Cache API responses with NetworkFirst strategy
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/'),
  new NetworkFirst({
    cacheName: 'api-cache',
    plugins: [
      new ExpirationPlugin({
        maxEntries: 50,
        maxAgeSeconds: 300, // 5 minutes
      }),
    ],
  })
)

// ============================================================================
// Push Notification Handler
// ============================================================================

self.addEventListener('push', (event: PushEvent) => {
  if (!event.data) return

  let payload: Record<string, unknown>
  try {
    payload = event.data.json()
  } catch {
    // Malformed JSON — silently ignore
    return
  }

  const safeTitle = (payload.title as string) || 'Notification'
  const { body, icon, badge, tag, data } = payload as Record<string, unknown>

  const notifTag = tag as string | undefined

  const options: NotificationOptions & { renotify?: boolean } = {
    body: (body as string) || '',
    icon: (icon as string) || '/icons/icon-192x192.png',
    badge: (badge as string) || '/icons/badge-72x72.png',
    tag: notifTag,
    renotify: !!notifTag,
    requireInteraction: false,
    data,
  }

  event.waitUntil(
    Promise.all([
      self.registration.showNotification(safeTitle, options),
      // Set app badge on dock/taskbar icon (Badging API)
      self.navigator.setAppBadge?.(),
    ])
  )
})

// ============================================================================
// Notification Click Handler
// ============================================================================

self.addEventListener('notificationclick', (event: NotificationEvent) => {
  event.notification.close()

  // Validate same-origin before navigating
  const rawUrl = event.notification.data?.url || '/'
  let safeUrl = '/'
  try {
    const parsed = new URL(rawUrl, self.location.href)
    if (parsed.origin === self.location.origin) {
      safeUrl = parsed.href
    }
  } catch {
    // Invalid URL — fall back to root
  }

  // Focus an existing window or open a new one
  event.waitUntil(
    self.clients
      .matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Try to focus an existing window and navigate
        for (const client of clientList) {
          if ('focus' in client) {
            return client.focus().then((focused) => {
              if ('navigate' in focused) {
                return (focused as WindowClient).navigate(safeUrl)
              }
              return focused
            })
          }
        }

        // No existing window — open a new one
        return self.clients.openWindow(safeUrl)
      })
  )
})
