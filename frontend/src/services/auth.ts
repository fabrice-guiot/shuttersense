/**
 * Auth API service
 *
 * Handles all API calls related to OAuth authentication.
 * Part of Issue #73 - Teams/Tenants and User Management.
 */

import api from './api'
import type {
  ProvidersResponse,
  AuthStatusResponse,
  LogoutResponse,
} from '@/contracts/api/auth-api'

/**
 * Get list of available OAuth providers
 *
 * @returns List of configured OAuth providers with display info
 */
export const getProviders = async (): Promise<ProvidersResponse> => {
  const response = await api.get<ProvidersResponse>('/auth/providers')
  return response.data
}

/**
 * Get current authentication status and user info
 *
 * This endpoint does not require authentication - it returns
 * authenticated=false if no valid session exists.
 *
 * @returns Authentication status with user info if authenticated
 */
export const getMe = async (): Promise<AuthStatusResponse> => {
  const response = await api.get<AuthStatusResponse>('/auth/me')
  return response.data
}

/**
 * Get the login URL for a specific OAuth provider
 *
 * The user should be redirected to this URL to initiate OAuth login.
 * After authorization, they will be redirected back to /auth/callback/{provider}.
 *
 * @param provider - OAuth provider name ("google" or "microsoft")
 * @returns Full login URL
 */
export const getLoginUrl = (provider: string): string => {
  // Use relative URL - will be resolved by browser
  return `/api/auth/login/${encodeURIComponent(provider)}`
}

/**
 * Logout the current user
 *
 * Clears the session cookie. Safe to call even if not authenticated.
 *
 * @returns Logout confirmation
 */
export const logout = async (): Promise<LogoutResponse> => {
  const response = await api.post<LogoutResponse>('/auth/logout')
  return response.data
}

/**
 * Check if the user is authenticated (quick status check)
 *
 * @returns True if authenticated, false otherwise
 */
export const checkAuthStatus = async (): Promise<boolean> => {
  try {
    const status = await getMe()
    return status.authenticated
  } catch {
    return false
  }
}
