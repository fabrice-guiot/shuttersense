/**
 * Auth API Type Definitions
 *
 * Types for OAuth authentication endpoints.
 * Part of Issue #73 - Teams/Tenants and User Management.
 */

// ============================================================================
// OAuth Provider Types
// ============================================================================

/**
 * OAuth provider information
 */
export interface OAuthProvider {
  name: string
  display_name: string
  icon: string
}

/**
 * Response from /auth/providers endpoint
 */
export interface ProvidersResponse {
  providers: OAuthProvider[]
}

// ============================================================================
// User Info Types
// ============================================================================

/**
 * Current user information returned by /auth/me
 */
export interface UserInfo {
  user_guid: string
  email: string
  team_guid: string
  team_name: string
  display_name: string | null
  picture_url: string | null
  is_super_admin: boolean
  first_name: string | null
  last_name: string | null
}

/**
 * Authentication status response from /auth/me
 */
export interface AuthStatusResponse {
  authenticated: boolean
  user: UserInfo | null
}

// ============================================================================
// Logout Types
// ============================================================================

/**
 * Response from /auth/logout endpoint
 */
export interface LogoutResponse {
  success: boolean
  message: string
}

// ============================================================================
// Error Types
// ============================================================================

/**
 * Authentication error codes returned by the backend
 */
export type AuthErrorCode =
  | 'user_not_found'
  | 'user_inactive'
  | 'user_deactivated'
  | 'team_inactive'
  | 'invalid_provider'
  | 'no_user_info'
  | 'no_email'
  | 'callback_error'
  | 'unknown'

/**
 * User-friendly error messages for auth error codes
 */
export const AUTH_ERROR_MESSAGES: Record<AuthErrorCode, string> = {
  user_not_found: 'No account found for this email. Please contact your administrator.',
  user_inactive: 'Your account has been deactivated. Please contact your administrator.',
  user_deactivated: 'Your account has been deactivated. Please contact your administrator.',
  team_inactive: "Your organization's account is inactive. Please contact your administrator.",
  invalid_provider: 'The selected login method is not available.',
  no_user_info: 'Could not retrieve your information from the login provider.',
  no_email: 'Email address was not provided by the login provider.',
  callback_error: 'An error occurred during login. Please try again.',
  unknown: 'An unexpected error occurred. Please try again.',
}
