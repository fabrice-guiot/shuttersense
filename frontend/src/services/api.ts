/**
 * Axios API instance configured for photo-admin backend
 *
 * Base configuration for all API calls to the FastAPI backend
 */

/// <reference types="vite/client" />

import axios, { AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios'

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * API Error response structure from FastAPI backend
 */
export interface ApiErrorResponse {
  detail?: string
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
    // Enhanced error message extraction
    const errorMessage =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.response?.data?.error?.message ||
      error.message ||
      'An unexpected error occurred'

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
