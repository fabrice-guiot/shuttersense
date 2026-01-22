/**
 * Axios API instance configured for ShutterSense backend
 *
 * Base configuration for all API calls to the FastAPI backend
 */

/// <reference types="vite/client" />

import axios, { AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios'

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * Pydantic validation error item structure
 */
export interface PydanticValidationError {
  type: string
  loc: (string | number)[]
  msg: string
  input?: unknown
  ctx?: Record<string, unknown>
}

/**
 * API Error response structure from FastAPI backend
 * Note: detail can be a string OR an array of Pydantic validation errors
 */
export interface ApiErrorResponse {
  detail?: string | PydanticValidationError[]
  message?: string
  error?: {
    message: string
    code?: string
    details?: Record<string, unknown>
  }
}

/**
 * Extended Axios Error with user-friendly message
 */
export interface ApiError extends AxiosError<ApiErrorResponse> {
  userMessage: string
}

// ============================================================================
// Axios Instance Configuration
// ============================================================================

// Determine API base URL:
// - In production (served from FastAPI): Use relative URL '/api' (same origin)
// - In development with Vite proxy: Use relative URL '/api' (proxy forwards to backend)
// - Override with VITE_API_BASE_URL if needed for special setups
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api'

// Create Axios instance with default configuration
const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 30000, // 30 seconds for potentially long-running requests
  headers: {
    'Content-Type': 'application/json'
  }
})

// ============================================================================
// Request Interceptor
// ============================================================================

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (import.meta.env.DEV) {
      console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`)
    }
    return config
  },
  (error: AxiosError) => {
    console.error('[API Request Error]', error)
    return Promise.reject(error)
  }
)

// ============================================================================
// Response Interceptor
// ============================================================================

api.interceptors.response.use(
  (response: AxiosResponse) => {
    if (import.meta.env.DEV) {
      console.log(`[API Response] ${response.status} ${response.config.url}`)
    }
    return response
  },
  (error: AxiosError<ApiErrorResponse>) => {
    // Handle 401 Unauthorized - redirect to login
    // Skip redirect for auth endpoints to avoid redirect loops
    const isAuthEndpoint = error.config?.url?.startsWith('/auth')
    if (error.response?.status === 401 && !isAuthEndpoint) {
      console.warn('[API] Session expired or not authenticated, redirecting to login')

      // Store current path for redirect after login
      const currentPath = window.location.pathname + window.location.search
      if (currentPath !== '/login') {
        sessionStorage.setItem('returnUrl', currentPath)
      }

      // Redirect to login page
      window.location.href = '/login'

      // Return a rejected promise that won't trigger error handlers
      return new Promise(() => {})
    }

    // Enhanced error message extraction
    // Handle Pydantic validation errors (array of objects) vs simple string messages
    const detail = error.response?.data?.detail
    let errorMessage: string

    if (Array.isArray(detail)) {
      // Pydantic validation errors - extract msg from each error
      errorMessage = detail
        .map((err: PydanticValidationError) => {
          // Format: "field: message" or just "message" if loc is empty/body-only
          const location = err.loc.filter(l => l !== 'body').join('.')
          return location ? `${location}: ${err.msg}` : err.msg
        })
        .join('; ')
    } else {
      // detail is now string | undefined after array check
      errorMessage =
        (detail as string | undefined) ||
        error.response?.data?.message ||
        error.response?.data?.error?.message ||
        error.message ||
        'An unexpected error occurred'
    }

    console.error('[API Response Error]', {
      url: error.config?.url,
      status: error.response?.status,
      message: errorMessage
    })

    // Attach user-friendly message to error object
    const apiError = error as ApiError
    apiError.userMessage = errorMessage

    return Promise.reject(apiError)
  }
)

export default api
