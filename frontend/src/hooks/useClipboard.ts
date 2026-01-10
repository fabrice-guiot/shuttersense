/**
 * useClipboard React hook
 *
 * Provides clipboard copy functionality with success/error state tracking.
 * Uses the modern Clipboard API with fallback for older browsers.
 *
 * Usage:
 *   const { copy, copied, error } = useClipboard()
 *   await copy('text to copy')
 */

import { useState, useCallback } from 'react'

interface UseClipboardReturn {
  /**
   * Copy text to clipboard
   * @param text - Text to copy
   * @returns Promise that resolves to true on success, false on failure
   */
  copy: (text: string) => Promise<boolean>

  /**
   * Whether text was recently copied (resets after timeout)
   */
  copied: boolean

  /**
   * Error message if copy failed
   */
  error: string | null
}

interface UseClipboardOptions {
  /**
   * Duration in ms to show "copied" state
   * @default 2000
   */
  resetDelay?: number
}

/**
 * Hook for copying text to clipboard
 *
 * @param options - Configuration options
 * @returns Clipboard state and copy function
 */
export const useClipboard = (options: UseClipboardOptions = {}): UseClipboardReturn => {
  const { resetDelay = 2000 } = options

  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const copy = useCallback(
    async (text: string): Promise<boolean> => {
      // Reset state
      setError(null)
      setCopied(false)

      try {
        // Use modern Clipboard API
        if (navigator.clipboard && navigator.clipboard.writeText) {
          await navigator.clipboard.writeText(text)
        } else {
          // Fallback for older browsers
          const textArea = document.createElement('textarea')
          textArea.value = text
          textArea.style.position = 'fixed'
          textArea.style.left = '-9999px'
          document.body.appendChild(textArea)
          textArea.select()
          document.execCommand('copy')
          document.body.removeChild(textArea)
        }

        setCopied(true)

        // Reset copied state after delay
        setTimeout(() => {
          setCopied(false)
        }, resetDelay)

        return true
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to copy to clipboard'
        setError(message)
        console.error('[useClipboard] Copy failed:', message)
        return false
      }
    },
    [resetDelay]
  )

  return { copy, copied, error }
}

export default useClipboard
