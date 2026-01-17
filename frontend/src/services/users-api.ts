/**
 * Users API client for user management operations.
 *
 * Provides functions for inviting users, listing team users,
 * and managing user status.
 *
 * Part of Issue #73 - User Story 3: User Pre-Provisioning
 */

import api from './api'

// ============================================================================
// Types
// ============================================================================

export interface TeamInfo {
  guid: string
  name: string
  slug: string
}

export interface User {
  guid: string
  email: string
  first_name: string | null
  last_name: string | null
  display_name: string | null
  picture_url: string | null
  status: 'pending' | 'active' | 'deactivated'
  is_active: boolean
  last_login_at: string | null
  created_at: string
  team: TeamInfo | null
}

export interface UserListResponse {
  users: User[]
  total: number
}

export interface UserStatsResponse {
  total_users: number
  active_users: number
  pending_users: number
  deactivated_users: number
}

export interface InviteUserRequest {
  email: string
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Invite a new user to the team.
 *
 * @param email - Email address of the user to invite
 * @returns The created user with pending status
 */
export async function inviteUser(email: string): Promise<User> {
  const response = await api.post<User>('/users', { email })
  return response.data
}

/**
 * List all users in the team.
 *
 * @param options - Optional filters
 * @returns List of users and total count
 */
export async function listUsers(options?: {
  status?: 'pending' | 'active' | 'deactivated'
  activeOnly?: boolean
}): Promise<UserListResponse> {
  const params = new URLSearchParams()
  if (options?.status) {
    params.append('status', options.status)
  }
  if (options?.activeOnly) {
    params.append('active_only', 'true')
  }

  const response = await api.get<UserListResponse>('/users', { params })
  return response.data
}

/**
 * Get user statistics for the team.
 *
 * @returns User counts by status
 */
export async function getUserStats(): Promise<UserStatsResponse> {
  const response = await api.get<UserStatsResponse>('/users/stats')
  return response.data
}

/**
 * Get a specific user by GUID.
 *
 * @param guid - User GUID
 * @returns User details
 */
export async function getUser(guid: string): Promise<User> {
  const response = await api.get<User>(`/users/${guid}`)
  return response.data
}

/**
 * Delete a pending user invitation.
 *
 * Only users with pending status can be deleted.
 *
 * @param guid - User GUID to delete
 */
export async function deletePendingUser(guid: string): Promise<void> {
  await api.delete(`/users/${guid}`)
}

/**
 * Deactivate a user.
 *
 * Deactivated users cannot log in.
 *
 * @param guid - User GUID to deactivate
 * @returns Updated user
 */
export async function deactivateUser(guid: string): Promise<User> {
  const response = await api.post<User>(`/users/${guid}/deactivate`)
  return response.data
}

/**
 * Reactivate a deactivated user.
 *
 * @param guid - User GUID to reactivate
 * @returns Updated user
 */
export async function reactivateUser(guid: string): Promise<User> {
  const response = await api.post<User>(`/users/${guid}/reactivate`)
  return response.data
}
