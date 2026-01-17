/**
 * Teams API client for super admin team management.
 *
 * Provides functions for creating, listing, and managing teams.
 * All endpoints require super admin privileges.
 *
 * Part of Issue #73 - User Story 5: Team Management
 */

import api from './api'

// ============================================================================
// Types
// ============================================================================

export interface Team {
  guid: string
  name: string
  slug: string
  is_active: boolean
  user_count: number
  created_at: string
  updated_at: string | null
}

export interface TeamWithAdmin {
  team: Team
  admin_email: string
  admin_guid: string
}

export interface TeamListResponse {
  teams: Team[]
  total: number
}

export interface TeamStatsResponse {
  total_teams: number
  active_teams: number
  inactive_teams: number
}

export interface CreateTeamRequest {
  name: string
  admin_email: string
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Create a new team with an admin user.
 *
 * @param name - Team display name
 * @param adminEmail - Email address for the team's first admin user
 * @returns The created team and admin user information
 */
export async function createTeam(
  name: string,
  adminEmail: string
): Promise<TeamWithAdmin> {
  const response = await api.post<TeamWithAdmin>('/admin/teams', {
    name,
    admin_email: adminEmail,
  })
  return response.data
}

/**
 * List all teams.
 *
 * @param options - Optional filters
 * @returns List of teams and total count
 */
export async function listTeams(options?: {
  activeOnly?: boolean
}): Promise<TeamListResponse> {
  const params = new URLSearchParams()
  if (options?.activeOnly) {
    params.append('active_only', 'true')
  }

  const response = await api.get<TeamListResponse>('/admin/teams', { params })
  return response.data
}

/**
 * Get team statistics.
 *
 * @returns Team counts by status
 */
export async function getTeamStats(): Promise<TeamStatsResponse> {
  const response = await api.get<TeamStatsResponse>('/admin/teams/stats')
  return response.data
}

/**
 * Get a specific team by GUID.
 *
 * @param guid - Team GUID
 * @returns Team details
 */
export async function getTeam(guid: string): Promise<Team> {
  const response = await api.get<Team>(`/admin/teams/${guid}`)
  return response.data
}

/**
 * Deactivate a team.
 *
 * Deactivated teams prevent all members from logging in.
 *
 * @param guid - Team GUID to deactivate
 * @returns Updated team
 */
export async function deactivateTeam(guid: string): Promise<Team> {
  const response = await api.post<Team>(`/admin/teams/${guid}/deactivate`)
  return response.data
}

/**
 * Reactivate a deactivated team.
 *
 * @param guid - Team GUID to reactivate
 * @returns Updated team
 */
export async function reactivateTeam(guid: string): Promise<Team> {
  const response = await api.post<Team>(`/admin/teams/${guid}/reactivate`)
  return response.data
}
