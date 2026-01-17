/**
 * Protected Route Component
 *
 * Wraps routes that require authentication.
 * Redirects unauthenticated users to the login page.
 * Part of Issue #73 - Teams/Tenants and User Management.
 */

import { Navigate, useLocation } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'

// ============================================================================
// Props
// ============================================================================

interface ProtectedRouteProps {
  children: React.ReactNode
  /**
   * If true, only super admins can access this route.
   * Non-super-admin users will see a 403 error.
   */
  requireSuperAdmin?: boolean
}

// ============================================================================
// Component
// ============================================================================

/**
 * Route wrapper that ensures user is authenticated
 *
 * @example
 * <Route
 *   path="/dashboard"
 *   element={
 *     <ProtectedRoute>
 *       <DashboardPage />
 *     </ProtectedRoute>
 *   }
 * />
 */
export function ProtectedRoute({ children, requireSuperAdmin = false }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, user } = useAuth()
  const location = useLocation()

  // Show loading spinner while checking auth
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    // Save the attempted URL for redirecting after login
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // Check super admin requirement
  if (requireSuperAdmin && !user?.is_super_admin) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-background">
        <h1 className="text-2xl font-semibold">Access Denied</h1>
        <p className="mt-2 text-muted-foreground">
          You do not have permission to access this page.
        </p>
      </div>
    )
  }

  return <>{children}</>
}
