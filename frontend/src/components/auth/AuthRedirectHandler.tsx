/**
 * Auth Redirect Handler
 *
 * Handles post-OAuth redirect to the originally requested page.
 * Part of Issue #73 - Teams/Tenants and User Management.
 */

import { useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'

// Session storage key for return URL (shared with LoginPage)
export const AUTH_RETURN_URL_KEY = 'auth_return_url'

/**
 * Component that handles redirecting to the original page after OAuth login.
 *
 * This runs once after authentication is confirmed and checks if there's
 * a stored return URL from before the OAuth flow began.
 */
export function AuthRedirectHandler({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const hasRedirected = useRef(false)

  useEffect(() => {
    // Only run once, after auth is confirmed, and not on login page
    if (isLoading || !isAuthenticated || hasRedirected.current) {
      return
    }

    // Don't redirect if already on login page (LoginPage handles its own redirect)
    if (location.pathname === '/login') {
      return
    }

    const returnUrl = sessionStorage.getItem(AUTH_RETURN_URL_KEY)

    if (returnUrl && returnUrl !== location.pathname) {
      hasRedirected.current = true
      sessionStorage.removeItem(AUTH_RETURN_URL_KEY)
      navigate(returnUrl, { replace: true })
    }
  }, [isAuthenticated, isLoading, navigate, location.pathname])

  return <>{children}</>
}
