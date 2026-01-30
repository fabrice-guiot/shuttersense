/**
 * PWA Installation Prompt
 *
 * Cross-platform install guidance:
 * - Chromium (Android/desktop): captures `beforeinstallprompt` event and shows
 *   an "Install" button that triggers the native install dialog
 * - iOS Safari: detects iOS + not-standalone and shows manual "Add to Home Screen"
 *   instructions (iOS has no programmatic install API)
 *
 * Dismissal behaviour:
 * - "X" button → sessionStorage (reappears next session / login)
 * - Successful install → localStorage (permanent, never show again on device)
 *
 * Issue #114 - PWA with Push Notifications (US1)
 */

import { useState, useEffect, useRef } from 'react'
import { X, Share, Plus, Download } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'

const DISMISSED_KEY = 'shuttersense-pwa-install-dismissed'
const INSTALLED_KEY = 'shuttersense-pwa-installed'

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

/**
 * Check if running on iOS (iPhone, iPad, iPod)
 */
function isIos(): boolean {
  if (typeof navigator === 'undefined') return false
  return /iphone|ipad|ipod/i.test(navigator.userAgent)
}

/**
 * Check if app is running in standalone mode (installed as PWA)
 */
function isStandalone(): boolean {
  if (typeof window === 'undefined') return false
  return (
    window.matchMedia('(display-mode: standalone)').matches ||
    ('standalone' in navigator && (navigator as Record<string, unknown>).standalone === true)
  )
}

export function IosPwaGuidance() {
  const [dismissed, setDismissed] = useState(false)
  const [installed, setInstalled] = useState(false)
  const [showIos, setShowIos] = useState(false)
  const deferredPrompt = useRef<BeforeInstallPromptEvent | null>(null)
  const [showChromium, setShowChromium] = useState(false)

  useEffect(() => {
    // Already installed — nothing to show
    if (isStandalone() || localStorage.getItem(INSTALLED_KEY)) {
      setInstalled(true)
      return
    }

    // Previously dismissed this session
    if (sessionStorage.getItem(DISMISSED_KEY)) {
      setDismissed(true)
      return
    }

    // iOS: show manual instructions
    if (isIos()) {
      setShowIos(true)
    }

    // Chromium: capture the deferred install prompt
    const handler = (e: Event) => {
      e.preventDefault()
      deferredPrompt.current = e as BeforeInstallPromptEvent
      setShowChromium(true)
    }

    window.addEventListener('beforeinstallprompt', handler)

    // Detect when the app gets installed — permanently suppress the banner
    const installedHandler = () => {
      deferredPrompt.current = null
      setShowChromium(false)
      setShowIos(false)
      setInstalled(true)
      localStorage.setItem(INSTALLED_KEY, 'true')
    }
    window.addEventListener('appinstalled', installedHandler)

    return () => {
      window.removeEventListener('beforeinstallprompt', handler)
      window.removeEventListener('appinstalled', installedHandler)
    }
  }, [])

  const handleDismiss = () => {
    setDismissed(true)
    sessionStorage.setItem(DISMISSED_KEY, 'true')
  }

  const handleInstall = async () => {
    if (!deferredPrompt.current) return
    await deferredPrompt.current.prompt()
    const { outcome } = await deferredPrompt.current.userChoice
    if (outcome === 'accepted') {
      deferredPrompt.current = null
      setShowChromium(false)
      setInstalled(true)
      localStorage.setItem(INSTALLED_KEY, 'true')
    }
  }

  // Nothing to show
  if (installed || dismissed || (!showIos && !showChromium)) return null

  return (
    <div className="px-4 pt-2">
      <Alert className="relative border-blue-500/30 bg-blue-500/10">
        <button
          onClick={handleDismiss}
          className="absolute right-2 top-2 rounded-md p-1 hover:bg-accent transition-colors"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4 text-muted-foreground" />
        </button>
        <AlertDescription className="pr-8 text-foreground">
          {showChromium ? (
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <p className="font-medium">Install ShutterSense</p>
                <p className="text-muted-foreground">
                  Install as an app for quick access and push notifications.
                </p>
              </div>
              <Button size="sm" onClick={handleInstall}>
                <Download className="mr-1.5 h-4 w-4" />
                Install
              </Button>
            </div>
          ) : (
            <>
              <p className="font-medium mb-1">Install ShutterSense</p>
              <p className="text-muted-foreground">
                Tap{' '}
                <Share className="inline h-4 w-4 align-text-bottom" />{' '}
                then{' '}
                <span className="inline-flex items-center gap-0.5">
                  <Plus className="inline h-3 w-3" />
                  Add to Home Screen
                </span>{' '}
                for the best experience with push notifications.
              </p>
            </>
          )}
        </AlertDescription>
      </Alert>
    </div>
  )
}
