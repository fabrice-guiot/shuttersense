import { useState, useEffect } from 'react'

/**
 * Hook for responsive behavior using CSS media queries.
 * SSR-safe: defaults to false on server, updates on client mount.
 *
 * @param query - CSS media query string (e.g., '(min-width: 640px)')
 * @returns boolean indicating if the media query matches
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => {
    // SSR safety: default to false on server
    if (typeof window === 'undefined') return false
    return window.matchMedia(query).matches
  })

  useEffect(() => {
    const mediaQuery = window.matchMedia(query)
    const handler = (event: MediaQueryListEvent) => setMatches(event.matches)

    // Set initial value (handles hydration)
    setMatches(mediaQuery.matches)

    // Listen for changes
    mediaQuery.addEventListener('change', handler)
    return () => mediaQuery.removeEventListener('change', handler)
  }, [query])

  return matches
}

/**
 * Convenience hook for mobile detection.
 * Returns true when viewport is less than 640px (Tailwind sm: breakpoint).
 */
export function useIsMobile(): boolean {
  return !useMediaQuery('(min-width: 640px)')
}
