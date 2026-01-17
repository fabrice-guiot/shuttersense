/**
 * useAuth React hook
 *
 * Provides access to authentication state and methods.
 * Part of Issue #73 - Teams/Tenants and User Management.
 */

import { useAuthContext } from '@/contexts/AuthContext'

/**
 * Hook for accessing authentication state and methods
 *
 * @example
 * const { user, isAuthenticated, logout } = useAuth()
 *
 * if (!isAuthenticated) {
 *   return <Navigate to="/login" />
 * }
 *
 * return <div>Welcome, {user?.email}</div>
 */
export function useAuth() {
  return useAuthContext()
}

/**
 * Hook to get current user info (convenience wrapper)
 *
 * @returns Current user info or null if not authenticated
 */
export function useCurrentUser() {
  const { user } = useAuthContext()
  return user
}

/**
 * Hook to check if current user is a super admin
 *
 * @returns True if user is authenticated and is a super admin
 */
export function useIsSuperAdmin() {
  const { user } = useAuthContext()
  return user?.is_super_admin ?? false
}
