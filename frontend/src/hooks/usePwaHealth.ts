/**
 * usePwaHealth React hook
 *
 * Runs automated diagnostics for PWA installation, service worker,
 * cache, push notifications, and platform-specific issues.
 *
 * Issue #025 - PWA Health Diagnostics
 */

import { useState, useCallback, useEffect } from 'react'
import * as notificationService from '@/services/notifications'
import {
  getPermissionState,
  isIos,
  isStandalone,
  isEdgeOnMacOS,
  isSafari,
  getDisplayMode,
  detectBrowserName,
  detectPlatformName,
} from '@/utils/pwa-detection'
import { formatRelativeTime } from '@/utils/dateFormat'
import type {
  PwaHealthResult,
  DiagnosticSection,
  DiagnosticCheck,
  DiagnosticStatus,
} from '@/contracts/pwa-health'

// ============================================================================
// Types
// ============================================================================

export interface UsePwaHealthReturn {
  result: PwaHealthResult | null
  running: boolean
  /** ID of the section currently being evaluated (null when idle) */
  checkingSection: string | null
  runDiagnostics: () => Promise<void>
  copyDiagnostics: () => Promise<boolean>
  clearCacheAndReload: () => Promise<void>
}

// ============================================================================
// Helpers
// ============================================================================

function worstStatus(checks: DiagnosticCheck[]): DiagnosticStatus {
  if (checks.some((c) => c.status === 'fail')) return 'fail'
  if (checks.some((c) => c.status === 'warn')) return 'warn'
  if (checks.some((c) => c.status === 'unknown')) return 'unknown'
  return 'pass'
}

/**
 * Query the service worker for its build version via MessageChannel.
 * Returns the version string or null on timeout / error.
 */
async function querySWVersion(timeout = 3000): Promise<string | null> {
  const controller = navigator.serviceWorker?.controller
  if (!controller) return null

  return new Promise<string | null>((resolve) => {
    const channel = new MessageChannel()
    const timer = setTimeout(() => resolve(null), timeout)

    channel.port1.onmessage = (event) => {
      clearTimeout(timer)
      if (event.data?.type === 'SW_VERSION') {
        resolve(event.data.version ?? null)
      } else {
        resolve(null)
      }
    }

    controller.postMessage({ type: 'GET_VERSION' }, [channel.port2])
  })
}

// ============================================================================
// Diagnostic Check Runners
// ============================================================================

async function checkInstallation(): Promise<DiagnosticCheck[]> {
  const checks: DiagnosticCheck[] = []

  // Display mode
  const displayMode = getDisplayMode()
  checks.push({
    id: 'display-mode',
    label: 'Display Mode',
    status: displayMode === 'standalone' ? 'pass' : 'warn',
    message: displayMode === 'standalone'
      ? 'Running as installed PWA'
      : `Running in ${displayMode} mode`,
    remediation: displayMode !== 'standalone'
      ? 'Install the app from the browser menu or address bar for the best experience.'
      : undefined,
  })

  // Manifest validation
  try {
    const manifestLink = document.querySelector<HTMLLinkElement>('link[rel="manifest"]')
    if (manifestLink) {
      const resp = await fetch(manifestLink.href)
      if (resp.ok) {
        const manifest = await resp.json()
        const hasIcons = Array.isArray(manifest.icons) && manifest.icons.length > 0
        const hasName = !!manifest.name || !!manifest.short_name
        if (hasIcons && hasName) {
          checks.push({
            id: 'manifest',
            label: 'Web App Manifest',
            status: 'pass',
            message: `Manifest valid: "${manifest.short_name || manifest.name}"`,
          })
        } else {
          checks.push({
            id: 'manifest',
            label: 'Web App Manifest',
            status: 'warn',
            message: 'Manifest incomplete',
            remediation: !hasIcons ? 'Manifest is missing icons.' : 'Manifest is missing a name.',
          })
        }
      } else {
        checks.push({
          id: 'manifest',
          label: 'Web App Manifest',
          status: 'fail',
          message: `Manifest fetch failed (HTTP ${resp.status})`,
          remediation: 'The web app manifest could not be loaded. Check the server configuration.',
        })
      }
    } else {
      checks.push({
        id: 'manifest',
        label: 'Web App Manifest',
        status: 'fail',
        message: 'No manifest link found',
        remediation: 'The page is missing a <link rel="manifest"> tag.',
      })
    }
  } catch {
    checks.push({
      id: 'manifest',
      label: 'Web App Manifest',
      status: 'unknown',
      message: 'Could not validate manifest',
    })
  }

  // Browser detection (informational)
  const browser = detectBrowserName()
  const platform = detectPlatformName()
  checks.push({
    id: 'browser',
    label: 'Browser',
    status: 'pass',
    message: `${browser} on ${platform}`,
  })

  return checks
}

async function checkServiceWorker(): Promise<DiagnosticCheck[]> {
  const checks: DiagnosticCheck[] = []

  if (!('serviceWorker' in navigator)) {
    checks.push({
      id: 'sw-support',
      label: 'Service Worker Support',
      status: 'fail',
      message: 'Service Workers are not supported in this browser',
      remediation: 'Use a modern browser that supports Service Workers.',
    })
    return checks
  }

  // Registration status
  try {
    const registration = await navigator.serviceWorker.getRegistration()
    if (registration) {
      checks.push({
        id: 'sw-registration',
        label: 'Registration',
        status: 'pass',
        message: 'Service worker is registered',
        detail: `Scope: ${registration.scope}`,
      })
    } else {
      checks.push({
        id: 'sw-registration',
        label: 'Registration',
        status: 'fail',
        message: 'No service worker registration found',
        remediation: 'The service worker may not have been installed. Try reloading the page.',
      })
      return checks
    }

    // Controller status
    const controller = navigator.serviceWorker.controller
    checks.push({
      id: 'sw-controller',
      label: 'Controller',
      status: controller ? 'pass' : 'warn',
      message: controller
        ? 'Page is controlled by service worker'
        : 'Page is not controlled (first load or update pending)',
      remediation: !controller
        ? 'Reload the page to activate the service worker controller.'
        : undefined,
    })

    // Version query
    const version = await querySWVersion()
    checks.push({
      id: 'sw-version',
      label: 'Version',
      status: version ? 'pass' : 'unknown',
      message: version ? `Build: ${version}` : 'Could not query SW version',
      remediation: !version
        ? 'The service worker did not respond to version query. It may need to be updated.'
        : undefined,
    })

    // Update status
    if (registration.waiting) {
      checks.push({
        id: 'sw-update',
        label: 'Update Status',
        status: 'warn',
        message: 'New version waiting to activate',
        remediation: 'Close all tabs and reopen the app to activate the new version.',
      })
    } else if (registration.installing) {
      checks.push({
        id: 'sw-update',
        label: 'Update Status',
        status: 'warn',
        message: 'New version installing',
      })
    } else {
      checks.push({
        id: 'sw-update',
        label: 'Update Status',
        status: 'pass',
        message: 'Up to date',
      })
    }
  } catch {
    checks.push({
      id: 'sw-registration',
      label: 'Registration',
      status: 'unknown',
      message: 'Could not check service worker status',
    })
  }

  return checks
}

async function checkCache(): Promise<DiagnosticCheck[]> {
  const checks: DiagnosticCheck[] = []

  if (!('caches' in window)) {
    checks.push({
      id: 'cache-support',
      label: 'Cache API',
      status: 'unknown',
      message: 'Cache API is not available',
    })
    return checks
  }

  try {
    const cacheNames = await caches.keys()
    let totalEntries = 0
    const cacheDetails: string[] = []

    for (const name of cacheNames) {
      const cache = await caches.open(name)
      const keys = await cache.keys()
      totalEntries += keys.length
      cacheDetails.push(`${name}: ${keys.length} entries`)
    }

    checks.push({
      id: 'cache-names',
      label: 'Caches',
      status: 'pass',
      message: `${cacheNames.length} cache(s) found`,
      detail: cacheDetails.join('\n'),
    })

    checks.push({
      id: 'cache-entries',
      label: 'Total Entries',
      status: totalEntries > 500 ? 'warn' : 'pass',
      message: `${totalEntries} cached entries`,
      remediation: totalEntries > 500
        ? 'Cache is large. Consider clearing the cache if you experience issues.'
        : undefined,
    })
  } catch {
    checks.push({
      id: 'cache-names',
      label: 'Caches',
      status: 'unknown',
      message: 'Could not enumerate caches',
    })
  }

  return checks
}

async function checkPushNotifications(): Promise<DiagnosticCheck[]> {
  const checks: DiagnosticCheck[] = []

  // Push API support
  const hasPush = 'PushManager' in window
  checks.push({
    id: 'push-support',
    label: 'Push API',
    status: hasPush ? 'pass' : 'fail',
    message: hasPush ? 'Push API is available' : 'Push API is not available',
    remediation: !hasPush
      ? 'This browser does not support push notifications.'
      : undefined,
  })

  // Permission state
  const permState = getPermissionState()
  checks.push({
    id: 'push-permission',
    label: 'Permission',
    status: permState === 'granted'
      ? 'pass'
      : permState === 'denied'
        ? 'fail'
        : permState === 'default'
          ? 'warn'
          : 'unknown',
    message: permState === 'granted'
      ? 'Notifications are permitted'
      : permState === 'denied'
        ? 'Notifications are blocked'
        : permState === 'default'
          ? 'Permission not yet requested'
          : 'Notifications not supported',
    remediation: permState === 'denied'
      ? 'Unblock notifications in your browser settings for this site.'
      : permState === 'default'
        ? 'Enable push notifications from the notification settings on this page.'
        : undefined,
  })

  // Server-side health (VAPID config, subscription count, last push)
  try {
    const health = await notificationService.getPushHealth()

    checks.push({
      id: 'push-vapid',
      label: 'VAPID Config',
      status: health.vapid_configured ? 'pass' : 'fail',
      message: health.vapid_configured
        ? 'VAPID keys configured on server'
        : 'VAPID keys not configured',
      remediation: !health.vapid_configured
        ? 'Server push notification keys are not set up. Contact your administrator.'
        : undefined,
    })

    // Subscription status
    checks.push({
      id: 'push-subscription',
      label: 'Subscriptions',
      status: health.subscription_count > 0 ? 'pass' : 'warn',
      message: health.subscription_count > 0
        ? `${health.subscription_count} active subscription(s)`
        : 'No active subscriptions',
      remediation: health.subscription_count === 0
        ? 'Subscribe a device from the notification settings to receive push notifications.'
        : undefined,
    })

    // Server sync — if subscriptions exist but Push API says no subscription, there may be a mismatch
    // Note: use getRegistration() instead of .ready — .ready never resolves when no SW is registered.
    if (hasPush && 'serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.getRegistration()
        const pushSub = registration?.active
          ? await registration.pushManager.getSubscription()
          : null
        const hasLocalSub = pushSub !== null
        const hasServerSub = health.subscription_count > 0

        if (hasLocalSub && hasServerSub) {
          checks.push({
            id: 'push-sync',
            label: 'Server Sync',
            status: 'pass',
            message: 'Browser and server subscriptions are in sync',
          })
        } else if (hasLocalSub && !hasServerSub) {
          checks.push({
            id: 'push-sync',
            label: 'Server Sync',
            status: 'warn',
            message: 'Browser has subscription but server does not',
            remediation: 'Try unsubscribing and re-subscribing this device.',
          })
        } else if (!hasLocalSub && hasServerSub) {
          checks.push({
            id: 'push-sync',
            label: 'Server Sync',
            status: 'warn',
            message: 'Server has subscriptions but this browser does not',
            remediation: 'This device may not be subscribed. Subscribe from the notification settings.',
          })
        }
      } catch {
        // Non-fatal
      }
    }

    // Last delivery time
    if (health.last_push_at) {
      checks.push({
        id: 'push-last-delivery',
        label: 'Last Delivery',
        status: 'pass',
        message: `Last push: ${formatRelativeTime(health.last_push_at)}`,
      })
    }
  } catch {
    checks.push({
      id: 'push-server',
      label: 'Server Health',
      status: 'unknown',
      message: 'Could not reach the server for push health status',
    })
  }

  return checks
}

function checkPlatformWarnings(): DiagnosticCheck[] {
  const checks: DiagnosticCheck[] = []

  // iOS not installed
  if (isIos() && !isStandalone()) {
    checks.push({
      id: 'platform-ios-install',
      label: 'iOS Installation',
      status: 'warn',
      message: 'App is not installed to Home Screen',
      remediation:
        'Push notifications on iOS require the app to be installed. ' +
        'Tap the Share button in Safari, then "Add to Home Screen".',
    })
  }

  // Edge on macOS
  if (isEdgeOnMacOS()) {
    checks.push({
      id: 'platform-edge-macos',
      label: 'Edge on macOS',
      status: 'warn',
      message: 'Edge/macOS may require a flag for push notifications',
      remediation:
        'If push notifications are not working, enable the flag at ' +
        'edge://flags/#enable-web-push-notifications and restart Edge.',
    })
  }

  // Safari ITP advisory
  if (isSafari()) {
    checks.push({
      id: 'platform-safari-itp',
      label: 'Safari ITP',
      status: 'warn',
      message: 'Safari Intelligent Tracking Prevention may clear service worker data',
      remediation:
        'Safari may evict service worker registrations after 7 days of inactivity. ' +
        'Open the app regularly to prevent this.',
    })
  }

  // If no warnings, show a pass
  if (checks.length === 0) {
    checks.push({
      id: 'platform-ok',
      label: 'Platform',
      status: 'pass',
      message: 'No platform-specific issues detected',
    })
  }

  return checks
}

// ============================================================================
// Clipboard Formatter
// ============================================================================

function formatDiagnosticsText(result: PwaHealthResult): string {
  const lines: string[] = [
    `ShutterSense PWA Diagnostics \u2014 ${result.collectedAt}`,
    `Browser: ${result.browser} on ${result.platform}`,
    '',
  ]

  for (const section of result.sections) {
    lines.push(`=== ${section.title} ===`)
    for (const check of section.checks) {
      const tag = check.status.toUpperCase().padEnd(7)
      lines.push(`[${tag}] ${check.label}: ${check.message}`)
      if (check.detail) {
        for (const line of check.detail.split('\n')) {
          lines.push(`       ${line}`)
        }
      }
      if (check.remediation) {
        lines.push(`       \u2192 ${check.remediation}`)
      }
    }
    lines.push('')
  }

  return lines.join('\n')
}

// ============================================================================
// Hook
// ============================================================================

export function usePwaHealth(): UsePwaHealthReturn {
  const [result, setResult] = useState<PwaHealthResult | null>(null)
  const [running, setRunning] = useState(false)
  /** ID of the section currently being checked (shown as spinner in UI) */
  const [checkingSection, setCheckingSection] = useState<string | null>(null)

  const runDiagnostics = useCallback(async () => {
    // Clear previous results so the UI resets
    setResult(null)
    setRunning(true)

    const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))
    const STAGGER_MS = 400

    const meta = {
      collectedAt: new Date().toISOString(),
      userAgent: navigator.userAgent,
      browser: detectBrowserName(),
      platform: detectPlatformName(),
    }

    // Section definitions — each with an async runner and static metadata
    const sectionDefs: {
      id: string
      title: string
      icon: string
      run: () => Promise<DiagnosticCheck[]> | DiagnosticCheck[]
    }[] = [
      { id: 'installation', title: 'Installation', icon: 'Download', run: checkInstallation },
      { id: 'service-worker', title: 'Service Worker', icon: 'Cpu', run: checkServiceWorker },
      { id: 'cache', title: 'Cache', icon: 'Database', run: checkCache },
      { id: 'push', title: 'Push Notifications', icon: 'Bell', run: checkPushNotifications },
      { id: 'platform', title: 'Platform Warnings', icon: 'Monitor', run: checkPlatformWarnings },
    ]

    const completed: DiagnosticSection[] = []

    try {
      for (const def of sectionDefs) {
        setCheckingSection(def.id)

        const checks = await def.run()
        completed.push({
          id: def.id,
          title: def.title,
          icon: def.icon,
          overallStatus: worstStatus(checks),
          checks,
        })

        // Update result progressively so the UI shows each section as it finishes
        setResult({ sections: [...completed], ...meta })

        // Brief pause between sections so the user can see them appear
        if (def !== sectionDefs[sectionDefs.length - 1]) {
          await delay(STAGGER_MS)
        }
      }
    } finally {
      setCheckingSection(null)
      setRunning(false)
    }
  }, [])

  const copyDiagnostics = useCallback(async (): Promise<boolean> => {
    if (!result) return false
    try {
      await navigator.clipboard.writeText(formatDiagnosticsText(result))
      return true
    } catch {
      return false
    }
  }, [result])

  const clearCacheAndReload = useCallback(async () => {
    try {
      // Delete all caches
      if ('caches' in window) {
        const names = await caches.keys()
        await Promise.all(names.map((name) => caches.delete(name)))
      }

      // Unregister all service workers
      if ('serviceWorker' in navigator) {
        const registrations = await navigator.serviceWorker.getRegistrations()
        await Promise.all(registrations.map((r) => r.unregister()))
      }
    } catch {
      // Best-effort cleanup — proceed to reload regardless
    } finally {
      window.location.reload()
    }
  }, [])

  // Run automatically on mount
  useEffect(() => {
    runDiagnostics()
  }, [runDiagnostics])

  return {
    result,
    running,
    checkingSection,
    runDiagnostics,
    copyDiagnostics,
    clearCacheAndReload,
  }
}
