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

// App version — injected at build time by swVersionPlugin (vite.config.ts).
// The placeholder string is replaced with the git-derived version before compilation.
const SW_VERSION: string = '__SW_BUILD_VERSION__'

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
      version: SW_VERSION,
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

  // Parse both Declarative Web Push (web_push: 8030) and legacy formats.
  // Safari 18.4+ handles declarative payloads natively (this handler won't fire).
  // On Chromium, the declarative JSON arrives via the SW push event as before.
  let title: string
  let body: string
  let tag: string | undefined
  let data: Record<string, unknown> | undefined
  let appBadge: number | undefined

  if (payload.web_push === 8030 && payload.notification) {
    // Declarative Web Push format (PRD 026)
    const notif = payload.notification as Record<string, unknown>
    title = (notif.title as string) || 'Notification'
    body = (notif.body as string) || ''
    tag = notif.tag as string | undefined
    data = notif.data as Record<string, unknown> | undefined
    const navigate = notif.navigate as string | undefined
    // Merge navigate into data for notificationclick handler
    if (navigate && data) {
      data.url = navigate
    } else if (navigate) {
      data = { url: navigate }
    }
    appBadge = payload.app_badge as number | undefined
  } else {
    // Legacy format (backward compatibility)
    title = (payload.title as string) || 'Notification'
    body = (payload.body as string) || ''
    tag = payload.tag as string | undefined
    data = payload.data as Record<string, unknown> | undefined
  }

  const options: NotificationOptions & { renotify?: boolean } = {
    body,
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    tag,
    renotify: !!tag,
    requireInteraction: false,
    data,
  }

  event.waitUntil(
    Promise.all([
      self.registration.showNotification(title, options),
      // Set app badge on dock/taskbar icon (Badging API)
      appBadge !== undefined
        ? self.navigator.setAppBadge?.(appBadge)
        : self.navigator.setAppBadge?.(),
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
