/**
 * Login Page
 *
 * OAuth login page with provider selection.
 * Part of Issue #73 - Teams/Tenants and User Management.
 */

import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { OAuthButton } from '@/components/auth/OAuthButton'
import { useAuth } from '@/hooks/useAuth'
import { getProviders } from '@/services/auth'
import { AUTH_ERROR_MESSAGES, type OAuthProvider, type AuthErrorCode } from '@/contracts/api/auth-api'
import { AlertCircle, Loader2 } from 'lucide-react'
import { AUTH_RETURN_URL_KEY } from '@/components/auth/AuthRedirectHandler'

// ============================================================================
// Component
// ============================================================================

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const { isAuthenticated, isLoading: authLoading } = useAuth()

  const [providers, setProviders] = useState<OAuthProvider[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Get error from URL query params (set by OAuth callback on failure)
  const errorCode = searchParams.get('error') as AuthErrorCode | null
  const authError = errorCode ? AUTH_ERROR_MESSAGES[errorCode] || AUTH_ERROR_MESSAGES.unknown : null

  // Store the intended destination in sessionStorage (for after OAuth redirect)
  useEffect(() => {
    const from = (location.state as { from?: { pathname: string } })?.from?.pathname
    if (from && from !== '/login') {
      sessionStorage.setItem(AUTH_RETURN_URL_KEY, from)
    }
  }, [location.state])

  // Redirect to intended destination if already authenticated
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      // Get the stored return URL, defaulting to home
      const returnUrl = sessionStorage.getItem(AUTH_RETURN_URL_KEY) || '/'
      sessionStorage.removeItem(AUTH_RETURN_URL_KEY)
      navigate(returnUrl, { replace: true })
    }
  }, [isAuthenticated, authLoading, navigate])

  // Fetch available OAuth providers
  useEffect(() => {
    const fetchProviders = async () => {
      try {
        const response = await getProviders()
        setProviders(response.providers)
      } catch (err: any) {
        setError(err.userMessage || 'Failed to load login options')
      } finally {
        setLoading(false)
      }
    }

    fetchProviders()
  }, [])

  // Show loading while checking auth status
  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  // Don't render login form if authenticated (redirect will happen)
  if (isAuthenticated) {
    return null
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md bg-[#020409]">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4">
            <picture>
              <source srcSet="/logo-login.webp" type="image/webp" />
              <img
                src="/logo-login.png"
                alt="ShutterSense.ai"
                className="h-24 w-24 object-contain"
              />
            </picture>
          </div>
          <CardTitle className="text-2xl">ShutterSense.ai</CardTitle>
          <CardDescription>
            Capture. Process. Analyze.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Auth error from OAuth callback */}
          {authError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{authError}</AlertDescription>
            </Alert>
          )}

          {/* Provider fetch error */}
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Loading state */}
          {loading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          )}

          {/* Provider buttons */}
          {!loading && !error && providers.length > 0 && (
            <div className="space-y-3">
              {providers.map((provider) => (
                <OAuthButton key={provider.name} provider={provider} />
              ))}
            </div>
          )}

          {/* No providers configured */}
          {!loading && !error && providers.length === 0 && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                No login providers are configured. Please contact your administrator.
              </AlertDescription>
            </Alert>
          )}

          {/* Footer */}
          <p className="text-center text-sm text-muted-foreground pt-4">
            Access is limited to pre-approved users.
            <br />
            Contact your administrator for access.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
