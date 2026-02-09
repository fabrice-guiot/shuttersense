/**
 * Service Worker Lifecycle Management
 *
 * Ensures users always receive the latest app version silently:
 * 1. Detects when a new SW takes control and reloads the page
 * 2. Periodically checks for SW updates (every 60s + on tab focus)
 *
 * Combined with skipWaiting()/clientsClaim() in sw.ts and
 * Cache-Control: no-cache on unhashed files from the server,
 * this guarantees deployments propagate within seconds of the
 * user's next interaction.
 *
 * Issue #114 - PWA Update Lifecycle
 */

const SW_UPDATE_INTERVAL_MS = 60_000 // 60 seconds

/**
 * Initialize service worker auto-update lifecycle.
 * Call once at app startup (outside React render tree).
 */
export function initServiceWorkerLifecycle(): void {
  if (!('serviceWorker' in navigator)) return

  // When a new SW activates and claims this client, reload to load fresh assets.
  // The `controllerchange` event fires after skipWaiting() + clients.claim()
  // in the new SW, meaning the old cached JS bundles in memory are stale.
  let refreshing = false
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (refreshing) return
    refreshing = true
    window.location.reload()
  })

  // Once the SW is ready, set up periodic update checks
  navigator.serviceWorker.ready.then((registration) => {
    // Periodic check — catches updates even if the user never navigates
    setInterval(() => {
      registration.update().catch(() => {
        // Silently ignore (offline, network error, etc.)
      })
    }, SW_UPDATE_INTERVAL_MS)

    // Check on tab re-focus — catches updates when user returns after a deploy
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        registration.update().catch(() => {})
      }
    })
  })
}
