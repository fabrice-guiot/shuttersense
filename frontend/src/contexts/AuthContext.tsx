/**
 * Auth Context
 *
 * Provides authentication state and methods throughout the app.
 * Part of Issue #73 - Teams/Tenants and User Management.
 */

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { getMe, logout as logoutApi } from '@/services/auth'
import type { UserInfo } from '@/contracts/api/auth-api'

// ============================================================================
// Types
// ============================================================================

interface AuthContextValue {
  /** Current user info (null if not authenticated) */
  user: UserInfo | null
  /** Whether user is authenticated */
  isAuthenticated: boolean
  /** Whether auth state is being loaded */
  isLoading: boolean
  /** Error message if auth check failed */
  error: string | null
  /** Logout the user and redirect to login */
  logout: () => Promise<void>
  /** Refresh the auth state from server */
  refreshAuth: () => Promise<void>
}

// ============================================================================
// Context
// ============================================================================

const AuthContext = createContext<AuthContextValue | null>(null)

// ============================================================================
// Provider
// ============================================================================

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<UserInfo | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  /**
   * Check authentication status with the server
   */
  const checkAuth = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await getMe()
      if (response.authenticated && response.user) {
        setUser(response.user)
      } else {
        setUser(null)
      }
    } catch (err: any) {
      // Don't treat network errors as auth failures during initial load
      // This prevents logged-in users from being logged out due to brief network issues
      console.error('Auth check failed:', err)
      setError(err.userMessage || 'Failed to check authentication status')
      // On error, keep existing user state (don't clear session)
    } finally {
      setIsLoading(false)
    }
  }, [])

  /**
   * Logout and clear user state
   */
  const logout = useCallback(async () => {
    try {
      await logoutApi()
    } catch (err) {
      // Even if logout API fails, clear local state
      console.error('Logout API call failed:', err)
    }
    setUser(null)
    // Redirect to login page
    window.location.href = '/login'
  }, [])

  /**
   * Refresh auth state (for use after external events)
   */
  const refreshAuth = useCallback(async () => {
    await checkAuth()
  }, [checkAuth])

  // Check auth on mount
  useEffect(() => {
    checkAuth()
  }, [checkAuth])

  const value: AuthContextValue = {
    user,
    isAuthenticated: user !== null,
    isLoading,
    error,
    logout,
    refreshAuth,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

// ============================================================================
// Hook
// ============================================================================

/**
 * Hook to access auth context
 *
 * Must be used within AuthProvider
 */
export function useAuthContext(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuthContext must be used within an AuthProvider')
  }
  return context
}
