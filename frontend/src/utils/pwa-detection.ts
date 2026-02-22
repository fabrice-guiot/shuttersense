/**
 * PWA Detection Utilities
 *
 * Pure helpers for browser, platform, and PWA state detection.
 * Extracted from usePushSubscription.ts for reuse across PWA features.
 *
 * Issue #025 - PWA Health Diagnostics
 */

// ============================================================================
// Types
// ============================================================================

export type PermissionState = 'default' | 'granted' | 'denied' | 'unsupported'

export interface NavigatorUAData {
  brands?: { brand: string }[]
  platform?: string
}

// ============================================================================
// Permission
// ============================================================================

/**
 * Get the current notification permission state.
 */
export function getPermissionState(): PermissionState {
  if (typeof window === 'undefined') return 'unsupported'
  if (!('Notification' in window)) return 'unsupported'
  return Notification.permission as PermissionState
}

// ============================================================================
// Platform Detection
// ============================================================================

/**
 * Detect if the current device is iOS (iPhone, iPad, iPod).
 */
export function isIos(): boolean {
  if (typeof navigator === 'undefined') return false
  return /iphone|ipad|ipod/i.test(navigator.userAgent)
}

/**
 * Detect if the app is running in standalone (installed PWA) mode.
 */
export function isStandalone(): boolean {
  if (typeof window === 'undefined') return false
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    ('standalone' in navigator &&
      (navigator as Record<string, unknown>).standalone === true)
  )
}

/**
 * Get the current display mode (standalone, browser, minimal-ui, etc.).
 */
export function getDisplayMode(): string {
  if (typeof window === 'undefined') return 'unknown'

  const modes = ['standalone', 'minimal-ui', 'fullscreen', 'browser'] as const
  for (const mode of modes) {
    if (window.matchMedia(`(display-mode: ${mode})`).matches) {
      return mode
    }
  }

  // iOS standalone check (doesn't use display-mode media query)
  if (
    'standalone' in navigator &&
    (navigator as Record<string, unknown>).standalone === true
  ) {
    return 'standalone'
  }

  return 'browser'
}

/**
 * Detect if the browser is Edge running on macOS.
 * Edge/macOS requires a hidden flag for push notification support.
 */
export function isEdgeOnMacOS(): boolean {
  if (typeof navigator === 'undefined') return false
  const ua = navigator.userAgent
  return /Edg\//i.test(ua) && /Macintosh/i.test(ua)
}

/**
 * Detect if the browser is Safari (not Chrome/Edge/etc. on WebKit).
 */
export function isSafari(): boolean {
  if (typeof navigator === 'undefined') return false
  const ua = navigator.userAgent
  return /Safari\//i.test(ua) && !/Chrome\//i.test(ua) && !/Edg\//i.test(ua) && !/CriOS/i.test(ua)
}

// ============================================================================
// Browser & Device Detection
// ============================================================================

/**
 * Detect the browser name from user agent data or UA string.
 */
export function detectBrowserName(): string {
  const uaData = (navigator as { userAgentData?: NavigatorUAData }).userAgentData
  if (uaData?.brands) {
    const real = uaData.brands.find(
      (b) => !/not[^a-z]*a[^a-z]*brand/i.test(b.brand) && b.brand !== 'Chromium'
    )
    if (real) return real.brand
  }

  const ua = navigator.userAgent
  if (/Edg\//i.test(ua)) return 'Edge'
  if (/OPR\//i.test(ua) || /Opera/i.test(ua)) return 'Opera'
  if (/Firefox\//i.test(ua)) return 'Firefox'
  if (/CriOS/i.test(ua) || /Chrome\//i.test(ua)) return 'Chrome'
  if (/Safari\//i.test(ua)) return 'Safari'
  return 'Browser'
}

/**
 * Detect the platform name from user agent data or UA string.
 */
export function detectPlatformName(): string {
  const uaData = (navigator as { userAgentData?: NavigatorUAData }).userAgentData
  if (uaData?.platform) {
    const p = uaData.platform
    if (/macos/i.test(p)) return 'Mac'
    if (/windows/i.test(p)) return 'Windows'
    if (/android/i.test(p)) return 'Android'
    if (/linux/i.test(p)) return 'Linux'
    return p
  }

  const ua = navigator.userAgent
  if (/iPhone/i.test(ua)) return 'iPhone'
  if (/iPad/i.test(ua)) return 'iPad'
  if (/Android/i.test(ua)) return 'Android'
  if (/Macintosh/i.test(ua)) return 'Mac'
  if (/Windows/i.test(ua)) return 'Windows'
  if (/Linux/i.test(ua)) return 'Linux'
  return 'Unknown'
}

/**
 * Detect a friendly device name in "{browser} on {platform}" format.
 */
export function detectDeviceName(): string {
  const browser = detectBrowserName()
  const platform = detectPlatformName()
  return `${browser} on ${platform}`
}

// ============================================================================
// Crypto
// ============================================================================

/**
 * Convert a Base64url-encoded string to a Uint8Array for PushManager.subscribe().
 */
export function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  const outputArray = new Uint8Array(rawData.length)
  for (let i = 0; i < rawData.length; i++) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}
