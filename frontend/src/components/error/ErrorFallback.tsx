import { AlertTriangle, RefreshCw, Home } from 'lucide-react'
import { Button } from '@/components/ui/button'

export interface ErrorFallbackProps {
  /**
   * The error that was caught
   */
  error: Error | null
  /**
   * Callback to reset the error boundary state
   */
  onReset?: () => void
  /**
   * Optional title override
   */
  title?: string
}

/**
 * ErrorFallback displays a user-friendly error message when an error is caught
 * by an ErrorBoundary. It uses dark theme styling and provides recovery options.
 */
export function ErrorFallback({
  error,
  onReset,
  title = 'Something went wrong',
}: ErrorFallbackProps) {
  const handleGoHome = () => {
    window.location.href = '/'
  }

  // Extract a user-friendly message (avoid showing stack traces)
  const userMessage = error?.message || 'An unexpected error occurred'

  return (
    <div className="flex min-h-[400px] items-center justify-center bg-background p-8">
      <div className="w-full max-w-md rounded-lg border border-border bg-card p-6 text-center shadow-lg">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
          <AlertTriangle className="h-6 w-6 text-destructive" />
        </div>

        <h2 className="mb-2 text-lg font-semibold text-foreground">{title}</h2>

        <p className="mb-6 text-sm text-muted-foreground">{userMessage}</p>

        <div className="flex flex-col gap-2 sm:flex-row sm:justify-center">
          {onReset && (
            <Button onClick={onReset} className="gap-2">
              <RefreshCw className="h-4 w-4" />
              Try Again
            </Button>
          )}
          <Button variant="outline" onClick={handleGoHome} className="gap-2">
            <Home className="h-4 w-4" />
            Go Home
          </Button>
        </div>
      </div>
    </div>
  )
}

export default ErrorFallback
