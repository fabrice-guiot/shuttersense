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

import { cleanupOutdatedCaches, precacheAndRoute } from 'workbox-precaching'
import { NavigationRoute, registerRoute } from 'workbox-routing'
import { NetworkFirst } from 'workbox-strategies'
import { ExpirationPlugin } from 'workbox-expiration'

declare let self: ServiceWorkerGlobalScope

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
// except /api/ routes (which should go to the backend)
const navigationRoute = new NavigationRoute(
  // The precache handler will serve the cached index.html
  // Using the strategy from precache for index.html
  async ({ request }) => {
    const cache = await caches.open('workbox-precache-v2')
    const keys = await cache.keys()
    // Find the precached index.html (may have a revision hash)
    const indexKey = keys.find((k) => k.url.endsWith('/index.html') || k.url === new URL('/', self.location.origin).href)
    if (indexKey) {
      const response = await cache.match(indexKey)
      if (response) return response
    }
    return fetch(request)
  },
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

  const payload = event.data.json()

  const { title, body, icon, badge, tag, data } = payload

  const options: NotificationOptions = {
    body,
    icon: icon || '/icons/icon-192x192.png',
    badge: badge || '/icons/badge-72x72.png',
    tag,
    data,
  }

  event.waitUntil(
    Promise.all([
      self.registration.showNotification(title, options),
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

  const url = event.notification.data?.url || '/'

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
                return (focused as WindowClient).navigate(url)
              }
              return focused
            })
          }
        }

        // No existing window — open a new one
        return self.clients.openWindow(url)
      })
  )
})
